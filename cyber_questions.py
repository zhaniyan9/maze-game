"""Generate and validate multiple-choice cybersecurity questions with Ollama."""

import json
import re


DIFFICULTY_GUIDANCE = {
    "Easy": (
        "Ask a very simple general cyber security question that anyone with basic computer knowledge could answer. "
        "Focus on everyday topics such as passwords, online safety, suspicious links, and protecting personal information. "
        "The answer should be obvious and require little to no cyber security knowledge."
    ),
    "Medium": (
        "Ask a straightforward general cyber security question that someone with basic computer knowledge could answer "
        "with a little thought. Focus on phishing emails, malware, strong passwords, two-factor authentication, and safe "
        "internet browsing. Require some understanding but no specialist cyber security knowledge."
    ),
    "Hard": (
        "Ask a slightly more challenging general cyber security question that requires some basic cyber security "
        "knowledge and an extra step of reasoning. Focus on identifying cyber attacks, network security, data protection, "
        "social engineering, encryption, and common security vulnerabilities. Avoid advanced technical concepts; it "
        "should suit someone with introductory cyber security knowledge."
    ),
}

RECENT_QUESTIONS = []
RECENT_QUESTION_LIMIT = 30


def _normalize_question(data, difficulty):
    """Return a predictable question shape for the game UI."""
    if not isinstance(data, dict):
        raise ValueError("Ollama returned a question that was not a JSON object.")

    question_text = str(data.get("question", "")).strip()
    if not question_text:
        raise ValueError("Ollama did not include question text.")

    raw_options = data.get("options")
    if isinstance(raw_options, dict):
        options = {str(key).strip().upper(): str(value).strip() for key, value in raw_options.items()}
    elif isinstance(raw_options, list):
        options = {}
        for index, option in enumerate(raw_options[:4]):
            letter = chr(65 + index)
            if isinstance(option, dict):
                letter = str(option.get("letter", letter)).strip().upper()
                option = option.get("text", option.get("answer", ""))
            options[letter] = str(option).strip()
    else:
        raise ValueError("Ollama returned options in an unsupported format.")

    options = {letter: options.get(letter, "") for letter in "ABCD"}
    if any(not options[letter] for letter in "ABCD"):
        raise ValueError("Ollama must return four options labelled A, B, C, and D.")

    # The UI adds the A./B./C./D. labels itself. Models sometimes include
    # those labels in the option text too (or return only the letters), which
    # produced choices such as “A. A” in the game. Strip duplicated labels,
    # then reject incomplete/duplicate choices before they reach the UI.
    for letter, option in options.items():
        options[letter] = re.sub(rf"^{letter}[.)]\s*", "", option, flags=re.IGNORECASE).strip()
        if not options[letter] or options[letter].upper() in "ABCD" or len(options[letter]) < 3:
            raise ValueError("Ollama returned an incomplete answer choice.")
    if len({option.casefold() for option in options.values()}) != 4:
        raise ValueError("Ollama returned duplicate answer choices.")

    raw_answer = str(data.get("correct_answer", "")).strip()
    answer = raw_answer.upper()
    if answer not in options:
        answer = next(
            (letter for letter, option in options.items() if option.casefold() == raw_answer.casefold()),
            "",
        )
    if answer not in options:
        raise ValueError("Ollama did not identify the correct answer as A, B, C, or D.")

    return {
        "difficulty": difficulty,
        "question": question_text,
        "options": options,
        "correct_answer": answer,
        "explanation": str(data.get("explanation", "")).strip(),
    }


def generate_question(difficulty="Easy"):
    """Generate one general cyber security question at the requested difficulty."""
    difficulty = str(difficulty).title()
    if difficulty not in DIFFICULTY_GUIDANCE:
        raise ValueError("Difficulty must be Easy, Medium, or Hard.")

    # Import requests only when generation is requested so the maze can still
    # launch and display a helpful error if the optional package is missing.
    import requests

    previous_questions = "\n".join(f"- {question}" for question in RECENT_QUESTIONS)
    if not previous_questions:
        previous_questions = "- None yet."

    prompt = f"""Generate exactly one general cyber security multiple-choice question.
Difficulty: {difficulty}. {DIFFICULTY_GUIDANCE[difficulty]}
Use four concise and plausible options, and exactly one clearly correct answer.
Do not repeat or closely paraphrase any of these recent questions:
{previous_questions}
For options, return only the answer text; do not put A/B/C/D labels inside the text.
Make all four options complete and distinct phrases, not single letters.
Return only a JSON object with: question, options (A, B, C, D), correct_answer (letter), and a one-sentence explanation.
Avoid unnecessarily complicated wording and advanced professional cyber security knowledge."""

    last_error = None
    for _attempt in range(3):
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2:3b",
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "keep_alive": "10m",
                    "options": {"num_predict": 220},
                },
                timeout=120,
            )
            response.raise_for_status()
            question = _normalize_question(json.loads(response.json()["response"]), difficulty)
            if question["question"].casefold() in {item.casefold() for item in RECENT_QUESTIONS}:
                raise ValueError("Ollama repeated a recent question.")
            RECENT_QUESTIONS.append(question["question"])
            del RECENT_QUESTIONS[:-RECENT_QUESTION_LIMIT]
            return question
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            last_error = error
    raise ValueError(f"Ollama failed to generate a valid question after 3 attempts: {last_error}")


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
            print(f"\nIncorrect. The correct answer was {question['correct_answer']}.")
        print("Explanation:", question["explanation"])
    except Exception as error:
        print("Error:", error)
