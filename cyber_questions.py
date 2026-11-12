"""Fetch and validate cybersecurity questions from the online question service."""

import re

import requests


QUESTION_API_URL = "https://maze-game-beta-eight.vercel.app/question"

DIFFICULTY_GUIDANCE = {
    "Easy": (
        "Ask a very simple general cyber security question that anyone with "
        "basic computer knowledge could answer. Focus on everyday topics such "
        "as passwords, online safety, suspicious links, and protecting personal "
        "information. The answer should be obvious and require little to no "
        "cyber security knowledge."
    ),
    "Medium": (
        "Ask a straightforward general cyber security question that someone "
        "with basic computer knowledge could answer with a little thought. "
        "Focus on phishing emails, malware, strong passwords, two-factor "
        "authentication, and safe internet browsing. Require some understanding "
        "but no specialist cyber security knowledge."
    ),
    "Hard": (
        "Ask a slightly more challenging general cyber security question that "
        "requires some basic cyber security knowledge and an extra step of "
        "reasoning. Focus on identifying cyber attacks, network security, data "
        "protection, social engineering, encryption, and common security "
        "vulnerabilities. Avoid advanced technical concepts; it should suit "
        "someone with introductory cyber security knowledge."
    ),
}

RECENT_QUESTIONS = []
RECENT_QUESTION_LIMIT = 30


def _normalize_question(data, difficulty):
    """Validate a question and return the format expected by the game."""
    if not isinstance(data, dict):
        raise ValueError(
            "The question service returned a question that was not a JSON object."
        )

    question_text = data.get("question")
    if not isinstance(question_text, str) or not question_text.strip():
        raise ValueError("The question service did not include question text.")

    question_text = question_text.strip()
    raw_options = data.get("options")

    if isinstance(raw_options, dict):
        options = {
            str(key).strip().upper(): value
            for key, value in raw_options.items()
        }

    elif isinstance(raw_options, list):
        if len(raw_options) != 4:
            raise ValueError(
                "The question service must return exactly four answer choices."
            )

        options = {}

        for index, option in enumerate(raw_options):
            letter = chr(65 + index)

            if isinstance(option, dict):
                letter = str(option.get("letter", letter)).strip().upper()
                option = option.get("text", option.get("answer", ""))

            if letter in options:
                raise ValueError(
                    "The question service returned duplicate option labels."
                )

            options[letter] = option

    else:
        raise ValueError(
            "The question service returned options in an unsupported format."
        )

    if set(options) != set("ABCD"):
        raise ValueError(
            "The question service must return four options labelled A, B, C, and D."
        )

    cleaned_options = {}

    for letter in "ABCD":
        option = options[letter]

        if not isinstance(option, str):
            raise ValueError("Each answer choice must contain text.")

        # The game adds A/B/C/D labels itself.
        option = re.sub(
            rf"^{letter}[.)]\s*",
            "",
            option.strip(),
            flags=re.IGNORECASE,
        ).strip()

        if len(option) < 3 or option.upper() in {"A", "B", "C", "D"}:
            raise ValueError(
                "The question service returned an incomplete answer choice."
            )

        cleaned_options[letter] = option

    if len({text.casefold() for text in cleaned_options.values()}) != 4:
        raise ValueError(
            "The question service returned duplicate answer choices."
        )

    raw_answer = data.get("correct_answer")
    if not isinstance(raw_answer, str):
        raise ValueError(
            "The question service did not identify the correct answer."
        )

    raw_answer = raw_answer.strip()
    answer = raw_answer.upper()

    # Also accept the full correct answer text.
    if answer not in cleaned_options:
        answer = next(
            (
                letter
                for letter, option in cleaned_options.items()
                if option.casefold() == raw_answer.casefold()
            ),
            "",
        )

    if answer not in cleaned_options:
        raise ValueError(
            "The question service did not identify the correct answer "
            "as A, B, C, or D."
        )

    explanation = data.get("explanation", "")
    if not isinstance(explanation, str):
        explanation = ""

    return {
        "difficulty": difficulty,
        "question": question_text,
        "options": cleaned_options,
        "correct_answer": answer,
        "explanation": explanation.strip(),
    }


def generate_question(difficulty="Easy"):
    """Request one question from the hosted backend."""
    difficulty = str(difficulty).strip().title()

    if difficulty not in DIFFICULTY_GUIDANCE:
        raise ValueError("Difficulty must be Easy, Medium, or Hard.")

    try:
        response = requests.post(
            QUESTION_API_URL,
            json={
                "difficulty": difficulty,
                "recent": RECENT_QUESTIONS[-RECENT_QUESTION_LIMIT:],
            },
            timeout=(10, 110),
        )

    except requests.Timeout as error:
        raise RuntimeError(
            "The question server took too long to respond. Please retry."
        ) from error

    except requests.RequestException as error:
        raise RuntimeError(
            "Cannot connect to the question server. "
            "Check your internet connection."
        ) from error

    if response.status_code == 429:
        raise RuntimeError(
            "Question request limit reached. Wait a minute and try again."
        )

    if response.status_code in (401, 403):
        raise RuntimeError(
            "Access to the question server was denied. "
            "Check Vercel's deployment protection settings."
        )

    if not response.ok:
        raise RuntimeError(
            f"Question generation failed (HTTP {response.status_code}). "
            "Check the backend's Vercel logs."
        )

    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError(
            "The question server returned an invalid response. "
            "Check the API URL and Vercel logs."
        ) from error

    question = _normalize_question(data, difficulty)

    if question["question"].casefold() in {
        text.casefold() for text in RECENT_QUESTIONS
    }:
        raise ValueError(
            "The question service repeated a recent question. Please retry."
        )

    RECENT_QUESTIONS.append(question["question"])
    del RECENT_QUESTIONS[:-RECENT_QUESTION_LIMIT]

    return question


if __name__ == "__main__":
    try:
        question = generate_question("Easy")

        print("\n=== CYBER CHALLENGE ===")
        print(f"Difficulty: {question['difficulty']}")
        print(question["question"])

        for letter, option in question["options"].items():
            print(f"{letter}. {option}")

        answer = input("\nYour answer (A/B/C/D): ").strip().upper()

        if answer == question["correct_answer"]:
            print("\nCorrect! Door unlocked.")
        else:
            correct_letter = question["correct_answer"]
            correct_text = question["options"][correct_letter]
            print(
                f"\nIncorrect. The correct answer was "
                f"{correct_letter}. {correct_text}"
            )

        if question["explanation"]:
            print("\nExplanation:")
            print(question["explanation"])

    except Exception as error:
        print(f"\nError: {error}")
