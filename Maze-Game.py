"""A Pygame maze adventure with five connected levels and cave side areas.

Controls: use WASD to move and E to interact with nearby objects. Number keys
select a level directly, which is useful for exploring and debugging the game.
The maps and their gameplay coordinates are defined near the top of this file;
the drawing helpers and main game loop follow them.
"""

import math
import queue
import random
import threading
from pathlib import Path

import pygame

from cyber_questions import generate_question


CELL_SIZE = 25
PLAYER_KEY_REPEAT_INTERVAL_MS = 100
WALL_INSET = 0

# Colors are grouped by the cave theme that uses them. RGB values can be tuned
# here without changing the maze logic or the drawing routines.
CAVE_FLOOR = (14, 17, 20)
FLOOR_FLECKS = ((22, 25, 27), (27, 28, 27), (19, 23, 25))
STONE_SHADES = ((76, 72, 62), (86, 79, 65), (69, 70, 64), (94, 83, 66))
STONE_HIGHLIGHT = (126, 112, 84)
STONE_SHADOW = (37, 39, 37)
CHARACTER_YELLOW = (255, 211, 0)
CHARACTER_HIGHLIGHT = (255, 239, 83)
SHOE_BLUE = (0, 105, 255)
SHOE_DARK_BLUE = (0, 49, 200)
CHARACTER_BLACK = (8, 8, 8)
EYE_WHITE = (255, 255, 255)
DOT = (255, 230, 170)
BUTTON_OUTLINE = (32, 31, 29)
BUTTON_RIM = (69, 67, 60)
BUTTON_LIGHT = (83, 79, 68)
BUTTON_DARK = (49, 47, 42)
BUTTON_SHADOW = (25, 24, 23)
BUTTON_HIGHLIGHT = (97, 90, 73)

LEVEL_THREE_FLOOR = (22, 30, 33)
LEVEL_THREE_FLOOR_FLECKS = ((35, 47, 49), (40, 53, 54), (28, 38, 41))
LEVEL_THREE_ROCK_HIGHLIGHTS = ((61, 78, 79), (56, 72, 75), (68, 83, 84))
LEVEL_THREE_STONE_SHADES = ((40, 58, 62), (46, 65, 69), (37, 53, 61), (52, 70, 73))
LEVEL_THREE_STONE_HIGHLIGHT = (81, 111, 112)
LEVEL_THREE_STONE_SHADOW = (18, 31, 35)

ORIGINAL_CAVE_FLOOR = (15, 12, 13)
ORIGINAL_CAVE_FLOOR_FLECKS = ((24, 18, 17), (29, 21, 18), (20, 17, 18))
ORIGINAL_CAVE_STONE_SHADES = ((68, 49, 41), (77, 55, 44), (62, 47, 43), (83, 59, 45))
ORIGINAL_CAVE_STONE_HIGHLIGHT = (126, 91, 65)
ORIGINAL_CAVE_STONE_SHADOW = (30, 24, 24)

WARM_CAVE_FLOOR = (10, 9, 15)
WARM_CAVE_FLOOR_FLECKS = ((22, 16, 24), (27, 19, 25), (17, 15, 24))
WARM_CAVE_STONE_SHADES = ((48, 35, 48), (57, 39, 51), (43, 34, 48), (62, 42, 52))
WARM_CAVE_STONE_HIGHLIGHT = (116, 77, 76)
WARM_CAVE_STONE_SHADOW = (20, 16, 25)

# Main maze map data. A # is a wall, a dot marks a pellet tile, and a space is
# a walkable tile. The first map is padded and sealed below before play begins.
MAZE = [
    "###############################",
    "#                        #   ##",
    "# #####################    #  #",
    "#   #                 # #######",
    "# # #   # # ##### # # # #     #",
    "# # #   # # ##    # # # # ### #",
    "# # ### # ######### ### # # # #",
    "# # #   ###       #     # # # #",
    "# # # ####### # # # ### # # # #",
    "# # #   #   # # # # # # # # # #",
    "# # ### # # # # # #   # # # # #",
    "# # #   # # # # # ####### # # #",
    "#   # # #   # # #      ## # # #",
    "# ### ### ##### ## ### ## # # #",
    "# #   #      #   # #   ## # # #",
    "# # ### ######   # # #### # # #",
    "# # # # #   ##   # #      # # #",
    "# # # # # # ############### # #",
    "# #   # # # #######   #       #",
    "# # ### # #       # # # #######",
    "#     # # ### ### # # # #     #",
    "# # # # # # # # # # ### # # # #",
    "# # ### # #     #       # # # #",
    "# # # # # ##################  #",
    "# # # # #             #   ## ##",
    "# # # # ####### ##### # #    ##",
    "# # #         # #   # # #### ##",
    "# # ##### ### # # # #      #  #",
    "# # ##### ##### # # ###### ####",
    "#                 #           #",
    "###############################",
]

# Normalize the editable Level 1 rows so every row has a solid border and the
# same width. The center room is carved out and its middle tile becomes the exit.
maze_width = max(len(row) for row in MAZE)
maze_tiles = [list(row.ljust(maze_width, "#")) for row in MAZE]
for row_index, row in enumerate(maze_tiles):
    row[0] = "#"
    row[-1] = "#"
    if row_index in (0, len(maze_tiles) - 1):
        row[:] = ["#"] * maze_width

center_row = len(maze_tiles) // 2
center_column = maze_width // 2
for row_index in range(center_row - 2, center_row + 3):
    for column in range(center_column - 2, center_column + 3):
        maze_tiles[row_index][column] = "#"
for row_index in range(center_row - 1, center_row + 2):
    for column in range(center_column - 1, center_column + 2):
        maze_tiles[row_index][column] = " "
maze_tiles[center_row - 2][center_column] = " "
maze_tiles[center_row - 3][center_column] = " "
# The bottom-center tile is the start; the center tile is the level exit.
START_ROW = len(maze_tiles) - 2
START_COLUMN = 15
EXIT_ROW = center_row
EXIT_COLUMN = center_column
maze_tiles[EXIT_ROW][EXIT_COLUMN] = "G"
# Level 1 route adjustment: open the tile marked white and close the tile
# marked red in the player's map reference.
maze_tiles[17][20] = " "
maze_tiles[15][25] = "#"
MAZE = ["".join(row) for row in maze_tiles]

# Size the window to the complete maze so there is no surrounding black border.
WINDOW_WIDTH = maze_width * CELL_SIZE
WINDOW_HEIGHT = len(MAZE) * CELL_SIZE
WINDOW_SCALE = 1.2


# Each later map uses the same row/column tile coordinates as the main map.
LEVEL_TWO_MAZE = [
    "###############################",
    "#    #                        #",
    "#  #    ########## ########## #",
    "####### #                 #   #",
    "#     # # #    #### # #   # # #",
    "# ### # # #    #### # #   # # #",
    "# # # # ### ######### # ### # #",
    "# # # #     #       ###   # # #",
    "# # # # ### # # # ####### # # #",
    "# # # # # # # # # #   #   # # #",
    "# # # # #   # # # # # # ### # #",
    "# # # ####### # # # # #   # # #",
    "# # # ##      # # #   # # #   #",
    "# # # ## ### ## ##### ### ### #",
    "# # # ##   # #   #      #   # #",
    "# # # #### # # G ###### ### # #",
    "# # #      # #   ##   # # # # #",
    "# # ############### # # # # # #",
    "#           ######  # # #   # #",
    "####### # # #      ## # ### # #",
    "#     # # # # ### ### # #     #",
    "# # # # ### # # # # # # # # # #",
    "# # # #       #     # # ### # #",
    "#  ################## # # # # #",
    "## ##   #             # # # # #",
    "##    # # ##### ####### # # # #",
    "## #### # #   # #         # # #",
    "#  #      # # # # ### ##### # #",
    "#### ###### # # ##### ##### # #",
    "#           #                 #",
    "###############################",
]

# Open the Level 2 wall marked in the player's screenshot.
_level_two_tiles = [list(row) for row in LEVEL_TWO_MAZE]
_level_two_tiles[17][5] = " "
_level_two_tiles[15][5] = "#"
LEVEL_TWO_MAZE = ["".join(row) for row in _level_two_tiles]


def generate_new_maze():
    """Return a copy of the manually editable second-level map."""
    return LEVEL_TWO_MAZE.copy()


LEVEL_TWO_EXIT_COLUMN = EXIT_COLUMN
LEVEL_THREE_START_ROW = START_ROW
LEVEL_THREE_START_COLUMN = START_COLUMN
GATE_TILE = (17, 15)
GATE_SLIDE_DURATION = 450
LEVEL_TRANSITION_COVER_DURATION = 100
LEVEL_TRANSITION_HOLD_DURATION = 300
LEVEL_TRANSITION_REVEAL_DURATION = 100
LEVEL_THREE_MAZE = [
    "###############################",
    "#           #                 #",
    "#### ###### # # ##### ####### #",
    "# ##      # # # # ### ####### #",
    "## #### # #   # #         # # #",
    "##    # # ##### ####### # # # #",
    "## ##   #             # # # # #",
    "#  ################## # # # # #",
    "# # # #       #     # # ### # #",
    "# # # # ### # # # # # # # # # #",
    "#     # # # # ### ### # #     #",
    "####### # # #      ## # ### # #",
    "#           ######  # # #   # #",
    "# # ############### # # # # # #",
    "# # #      # #   ##   # # # # #",
    "# # # #### # # G ###### ### # #",
    "# # # ##   # #   #      #   # #",
    "# # # ## ### ######## ### ### #",
    "# # # ##      # # #   # # #   #",
    "# # # ####### # # # # #   # # #",
    "# # # # #   # # # # # # ### # #",
    "# # # # # # # # # #   #   # # #",
    "# # # # ### # # # ####### # # #",
    "# # # #     #       ###   # # #",
    "# # # # ### ######### # ### # #",
    "# ### # # #    #### # #   # # #",
    "#     # # # ## #### # # # # # #",
    "####### #                 ### #",
    "# ##    ########## ########## #",
    "#    #                        #",
    "###############################",
]
_level_three_tiles = [list(row) for row in LEVEL_THREE_MAZE]
for _row, _column in ((7, 5), (20, 6), (21, 22), (23, 12)):
    _level_three_tiles[_row][_column] = " "
for _row, _column in ((10, 2), (24, 11), (25, 24), (24, 7), (17, 8)):
    _level_three_tiles[_row][_column] = "#"
LEVEL_THREE_MAZE = ["".join(row) for row in _level_three_tiles]

# Level 4 maze: edit one quoted string per row (31 characters each).
# # is a wall, spaces are paths, and G is behind the central 3x3 goal room.
LEVEL_FOUR_MAZE = [
    "###############################",
    "# #   #     #       #         #",
    "# # # # # # ### ### # ##### # #",
    "#   #   # #   # #   #   #   # #",
    "# ####### ### ### ##### # ### #",
    "#     #   #       #   # # #   #",
    "##### # ########### # # # ### #",
    "# #   #     #   #   # # #   # #",
    "# # ####### # # # ### # ### # #",
    "#   #   # #   #   # #   #   # #",
    "# ### # # ######### ##### ### #",
    "#   # #                 #   # #",
    "### # ####### ############# ###",
    "#   # #   #  #####  #     #   #",
    "# ### # # ####   ## # ### ### #",
    "# # #   #    # G ##   # # #   #",
    "# # # ########   ###### # # # #",
    "# # #   #     # ##  #   #   # #",
    "# # ### # ### #     ### ##### #",
    "# #     # # #     #   #     # #",
    "# # ##### # # ##### # ### # # #",
    "# # #     # # #   # # #   # # #",
    "# # # ##### # # # ### # ### # #",
    "# # # #     # # #     #   # # #",
    "# ### # ##### # ####### # ### #",
    "#   # # #     #   # #   #     #",
    "### # # # ####### # # #########",
    "# # # #   #     # # # #     # #",
    "# # # # ##### ### # # # ### # #",
    "#     #       #   #     #     #",
    "###############################",
]
_level_four_tiles = [list(row) for row in LEVEL_FOUR_MAZE]
for _row, _column in ((3, 20), (10, 23), (12, 23), (16, 19)):
    _level_four_tiles[_row][_column] = " "
for _row, _column in ((4, 9), (12, 3)):
    _level_four_tiles[_row][_column] = "#"
for _row, _column in ((2, 27), (10, 23), (12, 23)):
    _level_four_tiles[_row][_column] = "#"
for _row, _column in ((12, 29), (13, 26)):
    _level_four_tiles[_row][_column] = " "
_level_four_tiles[2][25] = " "
for _row, _column in ((15, 28), (13, 26)):
    _level_four_tiles[_row][_column] = "#"
_level_four_tiles[13][26] = " "
LEVEL_FOUR_MAZE = ["".join(row) for row in _level_four_tiles]

# Level 5 maze: edit one quoted string per row (31 characters each).
# # is a wall, spaces are paths, and G is the goal inside the center room.
LEVEL_FIVE_MAZE = [
    "############### ###############",
    "#         #                   #",
    "# # # # ### # ####### # # ### #",
    "# # # # #   #   #     # # #   #",
    "# ### # # ### # # ### ### # # #",
    "# #   # # #   # #   # #   # # #",
    "# # ### # # # ##### ### # # ###",
    "# #   # # # #     # #   # #   #",
    "# # # # # ##### ### # ### ### #",
    "# # # # # #     #   # #     # #",
    "# ### # # # # # # # # # ##### #",
    "#   # # # # # # #   # # #   # #",
    "### # ### # ### # # ### # ### #",
    "#   #     #  ## ###   # #   #  ",
    "  ####### ####   #### # ### # #",
    "#       #    # G #    #   # # #",
    "####### ######   ######## # # #",
    "#   #   #   ######  #     # # #",
    "# ### ### #   ##### # ##### # #",
    "#   # #   # #     # # # #   # #",
    "# # # # ### ##### # # # # ### #",
    "# #   # #   #   # #     # # # #",
    "# ##### # ### # ####### # # # #",
    "# #     #     # #     # # #   #",
    "# ##### ####### # ### # # ### #",
    "# #   # #   #   # #   # #   # #",
    "# # # # # # # ### # ####### # #",
    "# # # # # # #   # #       # # #",
    "# # # # # # ### # ####### # # #",
    "#   #   # #       #         # #",
    "############### ###############",
]
# The lower axe chamber is a three-tile-wide corridor bounded by solid walls.
_level_five_tiles = [list(row) for row in LEVEL_FIVE_MAZE]
for _row in range(19, 30):
    _level_five_tiles[_row][6] = "#"
    _level_five_tiles[_row][10] = "#"
    if _row >= 20:
        _level_five_tiles[_row][7:10] = [" ", " ", " "]
# Open the two Level 5 wall tiles marked in the reference image.
_level_five_tiles[22][11] = " "
_level_five_tiles[29][6] = " "
LEVEL_FIVE_MAZE = ["".join(row) for row in _level_five_tiles]
LEVEL_FIVE_START_ROW = len(LEVEL_FIVE_MAZE) - 1
LEVEL_FIVE_START_COLUMN = 15
LEVEL_FIVE_EXIT_ROW = 15
LEVEL_FIVE_EXIT_COLUMN = 15

# Level 5 side areas: edit one quoted string per row (16 characters each).
# # is a wall and spaces are paths. The starting tile becomes the exit after it is left.
LEVEL_FIVE_NORTH_MAZE = [
    "################",
    "#   #         ##",
    "# # # ##### # ##",
    "# #   #   # # ##",
    "# ##### # # # ##",
    "# #     #   # ##",
    "# ##### ##### ##",
    "# #     # #   ##",
    "# # ##### # ####",
    "# # #   #   # ##",
    "# # ### # ### ##",
    "# #   # # #   ##",
    "# ### # # # # ##",
    "#     #     # ##",
    "######## #######",
    "################",
]
LEVEL_FIVE_WEST_MAZE = [
    "################",
    "# #       #   ##",
    "# # ##### # # ##",
    "# # #   #   # ##",
    "# # # # # ### ##",
    "#   # #   #   ##",
    "# ### ##### # ##",
    "# # # #   # # ##",
    "# # # # ### # ##",
    "# #     #   # ##",
    "# # ##### ### ##",
    "# #   #   #   ##",
    "# ##### ### ####",
    "#             ##",
    "######## #######",
    "################",
]
LEVEL_FIVE_EAST_MAZE = [
    "################",
    "#     #       ##",
    "# ### # # ######",
    "#   # # #     ##",
    "##### # # ### ##",
    "#     # #   # ##",
    "# ##### ##### ##",
    "#     # #     ##",
    "# ### # # ### ##",
    "#   #   # # # ##",
    "### ##### # # ##",
    "# #       # # ##",
    "# ######### # ##",
    "#             ##",
    "######## #######",
    "################",
]
# The East Cave arrow corridor runs between two continuous stone walls.
_east_cave_tiles = [list(row) for row in LEVEL_FIVE_EAST_MAZE]
for _row in range(1, 14):
    _east_cave_tiles[_row][12:15] = [" ", " ", " "]
for _row in range(2, 13):
    _east_cave_tiles[_row][11] = "#"
LEVEL_FIVE_EAST_MAZE = ["".join(row) for row in _east_cave_tiles]
# Gameplay locations use (row, column) tile coordinates. Paths are ordered
# waypoint lists; hazards travel between those points after their plate starts.
LEVEL_FIVE_EAST_ARROW_DISPENSERS = (
    (3, 11, 1), (5, 15, -1), (7, 11, 1), (9, 15, -1), (11, 11, 1),
)
LEVEL_FIVE_EAST_ARROW_PRESSURE_PLATE_TILE = (13, 11)
LEVEL_FIVE_EAST_ARROW_INTERVAL_MS = 800
LEVEL_FIVE_EAST_ARROW_SPEED = 220
LEVEL_FIVE_SECTION_START = (14, 8)
WEST_CAVE_ARTIFACT_TILE = (7, 9)
NORTH_CAVE_ARTIFACT_TILE = (5, 3)
EAST_CAVE_ARTIFACT_TILE = (3, 3)
LEVEL_FIVE_ROCKS = ((15, 14), (15, 16), (16, 15))
LEVEL_FIVE_PRESSURE_PLATE_TILE = (7, 29)
LEVEL_FIVE_BOULDER_SPAWN_TILE = (30, 29)
LEVEL_FIVE_BOULDER_PATH = (
    LEVEL_FIVE_BOULDER_SPAWN_TILE,
    (13, 29), (13, 30), (13, 29), (7, 29), (7, 27),
    (3, 27), (3, 29), (5, 29), (6, 29),
)
LEVEL_FIVE_BOULDER_RUBBLE_TILE = (5, 29)
# This trap reaches the East Cave entrance after 18 path tiles. At 400 px/s it
# takes 1.125 s, leaving time for the player to reach the entrance from the plate.
LEVEL_FIVE_BOULDER_SPEED = 400
LEVEL_FIVE_BOULDER_IMPACT_DURATION = 260
LEVEL_FIVE_UPPER_LEFT_PRESSURE_PLATE_TILE = (1, 1)
LEVEL_FIVE_UPPER_LEFT_BOULDER_SPAWN_TILE = (0, 9)
LEVEL_FIVE_UPPER_LEFT_BOULDER_PATH = (LEVEL_FIVE_UPPER_LEFT_BOULDER_SPAWN_TILE, (1, 9), (1, 3), (3, 3), (4, 3))
LEVEL_FIVE_UPPER_LEFT_BOULDER_RUBBLE_TILE = (3, 3)
LEVEL_FIVE_AXE_PRESSURE_PLATE_TILE = (17, 10)
# One axe sweeps across the three-tile lane on each marked row; direction
# alternates to match the arrows in the reference image.
LEVEL_FIVE_AXE_ROW_DIRECTIONS = ((20, 1), (22, -1), (24, 1), (26, -1), (28, 1))
LEVEL_FIVE_SWINGING_AXES = tuple(
    (row, 8, direction) for row, direction in LEVEL_FIVE_AXE_ROW_DIRECTIONS
)
# Portal tiles in the main Level 5 map link to these smaller cave mazes.
# Each section's return coordinate is where the player reappears on Level 5.
LEVEL_FIVE_SECTIONS = {
    (0, 15): {
        "level": 6,
        "name": "North Cave",
        "maze": LEVEL_FIVE_NORTH_MAZE,
        "return": (0, 15),
    },
    (14, 0): {
        "level": 7,
        "name": "West Cave",
        "maze": LEVEL_FIVE_WEST_MAZE,
        "return": (14, 0),
    },
    (13, 30): {
        "level": 8,
        "name": "East Cave",
        "maze": LEVEL_FIVE_EAST_MAZE,
        "return": (13, 30),
    },
}
LEVEL_FIVE_SECTIONS_BY_LEVEL = {section["level"]: section for section in LEVEL_FIVE_SECTIONS.values()}

# Level-specific interactables: Level 3 switches and Level 4 puzzle objects.
LEVEL_THREE_BUTTONS = [
    {"wall": (8, 4)},
    {"wall": (18, 16)},
    {"wall": (22, 20)},
    {"wall": (28, 0)},
]
LEVEL_FOUR_PILLARS = ((14, 14), (14, 16), (16, 14), (16, 16))
LEVEL_FOUR_EXIT_TILE = (EXIT_ROW, EXIT_COLUMN)
LEVEL_FOUR_TORCHES = ((1, 30, "surface"), (18, 21, "surface"), (27, 0, "surface"), (28, 15, "surface"))
LEVEL_FOUR_PRESSURE_PLATE_TILE = (13, 29)
LEVEL_FOUR_BOULDER_SPAWN_TILE = (25, 30)
LEVEL_FOUR_BOULDER_PATH = (
    LEVEL_FOUR_BOULDER_SPAWN_TILE,
    (25, 29), LEVEL_FOUR_PRESSURE_PLATE_TILE, (1, 29),
    (1, 21), (3, 21), (3, 23), (9, 23),
)
LEVEL_FOUR_BOULDER_RUBBLE_TILE = (9, 23)
# At this speed, it reaches the plate about 1.1 seconds after the trigger,
# leaving the player time to step away while making the boulder feel close.
LEVEL_FOUR_BOULDER_SPEED = 300


def tiles_are_adjacent(first, second):
    """Return True when two tiles share an edge; diagonal tiles do not count."""
    return abs(first[0] - second[0]) + abs(first[1] - second[1]) == 1


def draw_maze(
    screen,
    maze,
    player_row,
    player_column,
    buttons=(),
    gate_slide_started_at=None,
    level_three=False,
    floor_texture=None,
    pillars=(),
    torches=(),
    carried_torch=False,
    lit_pillars=(),
    animation_time=0,
    player_name="",
    player_label_font=None,
    walking=False,
    warm_cave=False,
    classic_cave=False,
    viewport_size=None,
    section_exit_tile=None,
    rocks=(),
    artifact_tile=None,
    section_portal_tiles=(),
    carrying_artifact=None,
    placed_artifacts=(),
    north_artifact_tile=None,
    east_artifact_tile=None,
    pressure_plate_tile=None,
    pressure_plate_pressed=False,
    boulder_path=(),
    boulder_started_at=None,
    boulder_speed=LEVEL_FIVE_BOULDER_SPEED,
    additional_boulder_traps=(),
    axe_pressure_plate_tile=None,
    axes_started_at=None,
    swinging_axes=(),
    arrow_dispenser_tiles=(),
    arrows=(),
    arrow_pressure_plate_tile=None,
    arrow_pressure_plate_pressed=False,
    draw_player=True,
):
    """Draw a rocky cave maze with a dim, mottled stone floor."""
    maze_width = max(len(row) for row in maze) * CELL_SIZE
    maze_height = len(maze) * CELL_SIZE
    viewport_width, viewport_height = viewport_size or (WINDOW_WIDTH, WINDOW_HEIGHT)
    offset_x = (viewport_width - maze_width) // 2
    offset_y = (viewport_height - maze_height) // 2

    # Select matching wall/floor colors independently of wall shape. This lets
    # Levels 3–4 keep their teal palette while sharing the common rounded walls.
    if level_three:
        floor_color = LEVEL_THREE_FLOOR
        floor_flecks = LEVEL_THREE_FLOOR_FLECKS
        stone_shades = LEVEL_THREE_STONE_SHADES
        stone_highlight = LEVEL_THREE_STONE_HIGHLIGHT
        stone_shadow = LEVEL_THREE_STONE_SHADOW
    elif classic_cave:
        floor_color = ORIGINAL_CAVE_FLOOR
        floor_flecks = ORIGINAL_CAVE_FLOOR_FLECKS
        stone_shades = ORIGINAL_CAVE_STONE_SHADES
        stone_highlight = ORIGINAL_CAVE_STONE_HIGHLIGHT
        stone_shadow = ORIGINAL_CAVE_STONE_SHADOW
    elif warm_cave:
        floor_color = WARM_CAVE_FLOOR
        floor_flecks = WARM_CAVE_FLOOR_FLECKS
        stone_shades = WARM_CAVE_STONE_SHADES
        stone_highlight = WARM_CAVE_STONE_HIGHLIGHT
        stone_shadow = WARM_CAVE_STONE_SHADOW
    else:
        floor_color = CAVE_FLOOR
        floor_flecks = FLOOR_FLECKS
        stone_shades = STONE_SHADES
        stone_highlight = STONE_HIGHLIGHT
        stone_shadow = STONE_SHADOW
    feature_style = "teal" if level_three else "violet" if warm_cave else "rust"
    if (level_three or warm_cave or classic_cave) and floor_texture is not None:
        screen.blit(floor_texture, (0, 0))
    else:
        screen.fill(floor_color)

    # Floor details give each cave section its own atmosphere.
    if level_three and floor_texture is None:
        # Irregular low-contrast chips make the floor read as grey cave rock.
        for i in range(190):
            x = (i * 191 + 37) % WINDOW_WIDTH
            y = (i * 113 + 59) % WINDOW_HEIGHT
            color = floor_flecks[i % len(floor_flecks)]
            width = 2 + i % 5
            height = 1 + (i // 3) % 3
            pygame.draw.ellipse(screen, color, (x, y, width, height))
            if i % 5 == 0:
                highlight = LEVEL_THREE_ROCK_HIGHLIGHTS[(i // 5) % len(LEVEL_THREE_ROCK_HIGHLIGHTS)]
                pygame.draw.line(screen, highlight, (x, y), (x + width, y), 1)
    elif not level_three:
        # Subtle floor speckles make the original cave feel like rough stone.
        for i in range(260):
            x = (i * 191 + 37) % WINDOW_WIDTH
            y = (i * 113 + 59) % WINDOW_HEIGHT
            pygame.draw.circle(screen, floor_flecks[i % len(floor_flecks)], (x, y), 1 + (i % 3 == 0))

    # Draw the tile map first; moving gates are clipped to their own tile while
    # they slide away so they never paint over neighboring floor or walls.
    for row, line in enumerate(maze):
        for column, tile in enumerate(line):
            x = offset_x + column * CELL_SIZE
            y = offset_y + row * CELL_SIZE

            if tile == "#":
                wall_y = y
                is_level_three_gate = (row, column) == GATE_TILE
                gate_started_at = gate_slide_started_at if is_level_three_gate else None
                is_gate = is_level_three_gate
                if is_gate and gate_started_at is not None:
                    elapsed = pygame.time.get_ticks() - gate_started_at
                    slide = min(CELL_SIZE, int(CELL_SIZE * elapsed / GATE_SLIDE_DURATION))
                    if slide >= CELL_SIZE:
                        continue
                    wall_y += slide
                    previous_clip = screen.get_clip()
                    screen.set_clip(pygame.Rect(x, y, CELL_SIZE, CELL_SIZE))
                shade = stone_shades[(row * 7 + column * 11) % len(stone_shades)]
                pygame.draw.rect(
                    screen,
                    stone_shadow,
                    (x + WALL_INSET, wall_y + WALL_INSET, CELL_SIZE - 2 * WALL_INSET, CELL_SIZE - 2 * WALL_INSET),
                )
                rock_points = (
                    (x + 3, wall_y + 5), (x + 7, wall_y + 2),
                    (x + 18, wall_y + 3), (x + 22, wall_y + 7),
                    (x + 21, wall_y + 18), (x + 18, wall_y + 22),
                    (x + 6, wall_y + 21), (x + 2, wall_y + 16),
                )
                pygame.draw.polygon(screen, shade, rock_points)
                pygame.draw.lines(screen, stone_shadow, True, rock_points, 1)
                pygame.draw.line(screen, stone_highlight, rock_points[1], rock_points[2], 2)
                pygame.draw.line(screen, stone_highlight, rock_points[7], rock_points[0], 1)
                pygame.draw.line(screen, stone_shadow, rock_points[4], rock_points[5], 2)
                if (row * 7 + column * 11) % 6 == 0:
                    pygame.draw.line(screen, stone_shadow, (x + 9, wall_y + 8), (x + 12, wall_y + 12), 1)
                    pygame.draw.line(screen, stone_shadow, (x + 12, wall_y + 12), (x + 16, wall_y + 9), 1)
                if is_gate and gate_started_at is not None:
                    screen.set_clip(previous_clip)
            elif tile == ".":
                pygame.draw.circle(screen, DOT, (x + CELL_SIZE // 2, y + CELL_SIZE // 2), 3)

    # Portals and armed exits share the same pulsing marker treatment.
    indicator_tiles = list(section_portal_tiles)
    if section_exit_tile is not None:
        indicator_tiles.append(section_exit_tile)
    for row, column in indicator_tiles:
        center = (
            offset_x + column * CELL_SIZE + CELL_SIZE // 2,
            offset_y + row * CELL_SIZE + CELL_SIZE // 2,
        )
        pulse = int(animation_time * 5) % 2
        pygame.draw.circle(screen, (54, 34, 24), center, 8 + pulse)
        pygame.draw.circle(screen, (163, 111, 57), center, 7 + pulse, 2)
        pygame.draw.circle(screen, (239, 186, 100), center, 2)

    if pressure_plate_tile is not None:
        plate_x = offset_x + pressure_plate_tile[1] * CELL_SIZE
        plate_y = offset_y + pressure_plate_tile[0] * CELL_SIZE
        draw_pressure_plate(screen, plate_x, plate_y, pressure_plate_pressed, feature_style)

    if boulder_path:
        draw_boulder_trap(
            screen, boulder_path, boulder_started_at, boulder_speed,
            LEVEL_FIVE_BOULDER_RUBBLE_TILE, offset_x, offset_y,
        )

    for trap in additional_boulder_traps:
        plate = trap["plate"]
        draw_pressure_plate(
            screen,
            offset_x + plate[1] * CELL_SIZE,
            offset_y + plate[0] * CELL_SIZE,
            trap["started_at"] is not None,
            feature_style,
        )
        draw_boulder_trap(
            screen, trap["path"], trap["started_at"], trap["speed"],
            trap["rubble"], offset_x, offset_y,
        )

    if axe_pressure_plate_tile is not None:
        draw_pressure_plate(
            screen,
            offset_x + axe_pressure_plate_tile[1] * CELL_SIZE,
            offset_y + axe_pressure_plate_tile[0] * CELL_SIZE,
            axes_started_at is not None,
            feature_style,
        )
    if axes_started_at is not None:
        for row, column, phase in swinging_axes:
            draw_swinging_axe(screen, row, column, phase, animation_time, offset_x, offset_y)

    for row, column, direction in arrow_dispenser_tiles:
        draw_arrow_dispenser(screen, row, column, direction, offset_x, offset_y, feature_style)
    if arrow_pressure_plate_tile is not None:
        draw_pressure_plate(
            screen,
            offset_x + arrow_pressure_plate_tile[1] * CELL_SIZE,
            offset_y + arrow_pressure_plate_tile[0] * CELL_SIZE,
            arrow_pressure_plate_pressed,
            feature_style,
        )
    for arrow_x, arrow_y, direction in arrows:
        draw_flying_arrow(screen, arrow_x + offset_x, arrow_y + offset_y, direction)

    if artifact_tile is not None:
        draw_cave_medallion(
            screen,
            offset_x + artifact_tile[1] * CELL_SIZE,
            offset_y + artifact_tile[0] * CELL_SIZE,
            animation_time,
        )
    if north_artifact_tile is not None:
        draw_north_cave_artifact(
            screen,
            offset_x + north_artifact_tile[1] * CELL_SIZE,
            offset_y + north_artifact_tile[0] * CELL_SIZE,
            animation_time,
        )
    if east_artifact_tile is not None:
        draw_east_cave_artifact(
            screen,
            offset_x + east_artifact_tile[1] * CELL_SIZE,
            offset_y + east_artifact_tile[0] * CELL_SIZE,
            animation_time,
        )

    for row, column in pillars:
        draw_pillar(
            screen,
            offset_x + column * CELL_SIZE,
            offset_y + row * CELL_SIZE,
            lit=(row, column) in lit_pillars,
            animation_time=animation_time,
        )

    for row, column, wall_side in torches:
        draw_torch(screen, offset_x + column * CELL_SIZE, offset_y + row * CELL_SIZE, wall_side, animation_time=animation_time)

    for button in buttons:
        row, column = button["wall"]
        x = offset_x + column * CELL_SIZE
        y = offset_y + row * CELL_SIZE
        pygame.draw.rect(screen, BUTTON_SHADOW, (x + 5, y + 7, 15, 14))
        pygame.draw.rect(screen, BUTTON_OUTLINE, (x + 6, y + 5, 13, 13))
        if button["pressed"]:
            pygame.draw.rect(screen, BUTTON_RIM, (x + 8, y + 7, 9, 9))
            pygame.draw.rect(screen, BUTTON_DARK, (x + 9, y + 9, 7, 6))
            pygame.draw.rect(screen, BUTTON_LIGHT, (x + 10, y + 10, 3, 2))
            pygame.draw.rect(screen, BUTTON_SHADOW, (x + 9, y + 14, 7, 2))
        else:
            pygame.draw.rect(screen, BUTTON_RIM, (x + 7, y + 6, 11, 11))
            pygame.draw.rect(screen, BUTTON_DARK, (x + 8, y + 7, 9, 9))
            pygame.draw.rect(screen, BUTTON_LIGHT, (x + 9, y + 7, 7, 7))
            pygame.draw.rect(screen, BUTTON_HIGHLIGHT, (x + 9, y + 8, 3, 2))
            pygame.draw.rect(screen, BUTTON_SHADOW, (x + 8, y + 14, 9, 2))

    # Keep the character fully inside and centred on its current maze tile.
    walk_frame = int(animation_time * 10) % 2
    idle_bob = int(animation_time * 2) % 2 if not walking else 0
    character_y = player_row * CELL_SIZE + 2 + (-2 if walking and walk_frame else -idle_bob)
    if draw_player:
        draw_character(
            screen,
            offset_x + player_column * CELL_SIZE + 1,
            offset_y + character_y,
            animation_time=animation_time,
            walking=walking,
            walk_frame=walk_frame,
        )
        if player_name:
            name_font = player_label_font or pygame.font.Font(None, 15)
            name_surface = name_font.render(player_name, True, (255, 232, 190))
            name_rect = name_surface.get_rect(
                midbottom=(
                    offset_x + player_column * CELL_SIZE + CELL_SIZE // 2,
                    offset_y + character_y - 4,
                )
            )
            shadow_surface = name_font.render(player_name, True, (15, 12, 10))
            screen.blit(shadow_surface, name_rect.move(1, 1))
            screen.blit(name_surface, name_rect)
        if carried_torch:
            draw_carried_torch(
                screen,
                offset_x + player_column * CELL_SIZE,
                offset_y + character_y - 2,
                animation_time=animation_time,
            )
        if carrying_artifact == "west":
            draw_cave_medallion(
                screen,
                offset_x + player_column * CELL_SIZE + 6,
                offset_y + character_y - 4,
                animation_time,
            )
        elif carrying_artifact == "north":
            draw_north_artifact_carried(
                screen,
                offset_x + player_column * CELL_SIZE,
                offset_y + character_y,
            )
        elif carrying_artifact == "east":
            draw_east_artifact_carried(
                screen,
                offset_x + player_column * CELL_SIZE,
                offset_y + character_y,
            )
    for row, column in rocks:
        draw_rounded_rock(screen, offset_x + column * CELL_SIZE, offset_y + row * CELL_SIZE)
    for artifact_name, tile in placed_artifacts:
        artifact_x = offset_x + tile[1] * CELL_SIZE
        artifact_y = offset_y + tile[0] * CELL_SIZE
        if artifact_name == "west":
            draw_cave_medallion(screen, artifact_x, artifact_y, animation_time)
        elif artifact_name == "north":
            draw_north_cave_artifact(screen, artifact_x, artifact_y, animation_time)
        elif artifact_name == "east":
            draw_east_cave_artifact(screen, artifact_x, artifact_y, animation_time)


def draw_flame(screen, x, y, animation_time, width=10, height=12):
    """Draw a small flame whose shape and colour flicker over time."""
    frame = int(animation_time * 9) % 4
    sway = (0, 1, 0, -1)[frame]
    tip_y = y + (frame % 2)
    center_x = x + width // 2
    outer_colors = ((255, 104, 28), (255, 94, 22), (244, 91, 22), (255, 112, 31))
    inner_colors = ((255, 190, 61), (255, 174, 48), (255, 181, 53), (255, 201, 72))
    outer = (
        (center_x + sway, tip_y),
        (center_x + width // 3, y + height // 2),
        (x + width, y + height * 2 // 3),
        (center_x, y + height),
        (x, y + height * 2 // 3),
        (center_x - width // 3, y + height // 2),
    )
    inner = (
        (center_x + sway, y + height // 2),
        (x + width - width // 4, y + height * 2 // 3),
        (center_x, y + height - 1),
        (x + width // 4, y + height * 2 // 3),
    )
    pygame.draw.polygon(screen, outer_colors[frame], outer)
    pygame.draw.polygon(screen, inner_colors[frame], inner)
    pygame.draw.rect(screen, (255, 232, 143), (center_x, y + height * 2 // 3, max(1, width // 5), max(1, height // 5)))


def draw_pillar(screen, x, y, lit=False, animation_time=0):
    """Draw a squat carved-stone pillar in one maze tile."""
    pygame.draw.rect(screen, (18, 29, 33), (x + 2, y + 4, 21, 20))
    pygame.draw.rect(screen, (40, 58, 62), (x + 5, y + 6, 15, 15))
    pygame.draw.polygon(screen, (56, 76, 78), ((x + 3, y + 6), (x + 7, y + 2), (x + 19, y + 2), (x + 22, y + 6)))
    pygame.draw.rect(screen, (46, 66, 69), (x + 4, y + 6, 18, 4))
    pygame.draw.rect(screen, (66, 86, 87), (x + 6, y + 10, 3, 8))
    pygame.draw.line(screen, (27, 42, 46), (x + 10, y + 12), (x + 19, y + 12), 1)
    pygame.draw.rect(screen, (29, 44, 48), (x + 4, y + 19, 18, 4))
    pygame.draw.line(screen, (61, 81, 82), (x + 5, y + 20), (x + 20, y + 20), 1)
    pygame.draw.line(screen, (74, 96, 96), (x + 7, y + 7), (x + 18, y + 7), 1)
    if lit:
        draw_flame(screen, x + 10, y + 2, animation_time, width=9, height=10)


def draw_rounded_rock(screen, x, y):
    """Draw a subdued violet stone obstruction for the deepest cave level."""
    pygame.draw.ellipse(screen, (13, 11, 18), (x + 3, y + 18, 20, 6))
    pygame.draw.ellipse(screen, (31, 25, 37), (x + 5, y + 8, 16, 15))
    pygame.draw.ellipse(screen, (47, 36, 51), (x + 5, y + 6, 15, 15))
    pygame.draw.ellipse(screen, (58, 43, 61), (x + 7, y + 5, 11, 12))
    pygame.draw.ellipse(screen, (70, 50, 66), (x + 8, y + 6, 7, 5))
    pygame.draw.ellipse(screen, (38, 30, 45), (x + 4, y + 13, 8, 8))
    pygame.draw.ellipse(screen, (29, 24, 37), (x + 14, y + 14, 7, 7))
    pygame.draw.line(screen, (83, 59, 73), (x + 8, y + 8), (x + 11, y + 6), 1)
    pygame.draw.line(screen, (19, 15, 25), (x + 16, y + 12), (x + 18, y + 15), 1)


def draw_pressure_plate(screen, x, y, pressed=False, style="rust"):
    """Draw a small stone pressure plate in the path."""
    palettes = {
        "rust": ((24, 18, 16), (53, 39, 31), (73, 57, 45), (151, 110, 73), (36, 29, 26), (193, 143, 87), (255, 194, 98)),
        "teal": ((17, 27, 31), (34, 49, 53), (48, 67, 70), (81, 108, 108), (24, 37, 41), (119, 151, 146), (178, 210, 193)),
        "violet": ((14, 12, 20), (31, 25, 37), (43, 34, 48), (83, 59, 73), (22, 18, 29), (133, 95, 113), (201, 139, 130)),
    }
    shadow, base, top, edge, inset, rivet, pressed_glow = palettes.get(style, palettes["rust"])
    pygame.draw.ellipse(screen, shadow, (x + 3, y + 15, 19, 7))
    pygame.draw.rect(screen, base, (x + 4, y + 7, 17, 12))
    plate_top = y + (10 if pressed else 7)
    pygame.draw.rect(screen, top, (x + 4, plate_top, 17, 9))
    pygame.draw.rect(screen, edge, (x + 5, plate_top + 1, 15, 2))
    pygame.draw.rect(screen, inset, (x + 6, plate_top + 4, 13, 3))
    pygame.draw.circle(screen, rivet, (x + 7, plate_top + 5), 1)
    pygame.draw.circle(screen, rivet, (x + 18, plate_top + 5), 1)
    if pressed:
        pygame.draw.line(screen, pressed_glow, (x + 8, plate_top + 3), (x + 17, plate_top + 3), 1)


def draw_arrow_dispenser(screen, row, column, direction, offset_x=0, offset_y=0, style="violet"):
    """Draw a metal arrow slot built into a corridor wall."""
    x = offset_x + column * CELL_SIZE
    y = offset_y + row * CELL_SIZE
    center_y = y + CELL_SIZE // 2
    if direction > 0:
        body = pygame.Rect(x + 7, center_y - 7, 15, 14)
        opening = pygame.Rect(x + 18, center_y - 3, 7, 6)
    else:
        body = pygame.Rect(x + 3, center_y - 7, 15, 14)
        opening = pygame.Rect(x, center_y - 3, 7, 6)
    if style == "violet":
        shadow, metal, opening_color, highlight = (19, 15, 25), (73, 54, 70), (12, 12, 18), (121, 82, 91)
    else:
        shadow, metal, opening_color, highlight = (20, 30, 34), (51, 70, 73), (12, 17, 20), (91, 113, 111)
    pygame.draw.rect(screen, shadow, body)
    pygame.draw.rect(screen, metal, body, 2)
    pygame.draw.rect(screen, opening_color, opening)
    pygame.draw.line(screen, highlight, (body.left + 3, body.top + 2), (body.right - 3, body.top + 2), 1)


def draw_flying_arrow(screen, x, y, direction):
    """Draw a small steel arrow in flight through the East Cave corridor."""
    x, y = int(x), int(y)
    tail_x = x - direction * 9
    tip_x = x + direction * 9
    pygame.draw.line(screen, (48, 35, 26), (tail_x, y + 1), (tip_x, y + 1), 3)
    pygame.draw.line(screen, (151, 112, 72), (tail_x, y), (tip_x, y), 1)
    pygame.draw.polygon(
        screen,
        (180, 187, 190),
        ((tip_x, y), (tip_x - direction * 6, y - 4), (tip_x - direction * 6, y + 4)),
    )


def draw_rolling_boulder(screen, cx, cy):
    """Draw the moving grey boulder with its pale centre mark."""
    cx, cy = int(cx), int(cy)
    pygame.draw.ellipse(screen, (24, 19, 17), (cx - 12, cy + 7, 24, 7))
    points = (
        (cx - 8, cy - 8), (cx - 2, cy - 11), (cx + 7, cy - 9),
        (cx + 11, cy - 3), (cx + 10, cy + 6), (cx + 4, cy + 10),
        (cx - 6, cy + 9), (cx - 11, cy + 3),
    )
    pygame.draw.polygon(screen, (65, 64, 60), points)
    pygame.draw.lines(screen, (34, 33, 31), True, points, 2)
    pygame.draw.polygon(screen, (116, 115, 108), ((cx - 7, cy - 7), (cx - 1, cy - 9), (cx + 5, cy - 7), (cx, cy - 2), (cx - 6, cy - 2)))
    pygame.draw.circle(screen, (177, 177, 170), (cx + 2, cy - 1), 3)
    pygame.draw.circle(screen, (218, 216, 207), (cx + 1, cy - 2), 1)
    pygame.draw.line(screen, (42, 42, 39), (cx - 5, cy + 3), (cx - 1, cy + 6), 1)


def draw_boulder_impact(screen, cx, cy):
    """Draw a brief stone-chip burst where the boulder breaks against the wall."""
    cx, cy = int(cx), int(cy)
    pygame.draw.line(screen, (230, 194, 131), (cx - 8, cy - 5), (cx - 3, cy - 2), 2)
    pygame.draw.line(screen, (230, 194, 131), (cx + 8, cy - 7), (cx + 3, cy - 3), 2)
    pygame.draw.line(screen, (194, 177, 145), (cx - 7, cy + 5), (cx - 3, cy + 2), 2)
    pygame.draw.line(screen, (194, 177, 145), (cx + 7, cy + 5), (cx + 3, cy + 2), 2)
    pygame.draw.circle(screen, (177, 177, 170), (cx - 5, cy - 9), 2)
    pygame.draw.circle(screen, (177, 177, 170), (cx + 6, cy + 8), 2)


def draw_boulder_rubble(screen, x, y):
    """Draw the lasting debris pile left after the boulder breaks."""
    pygame.draw.ellipse(screen, (25, 21, 19), (x + 3, y + 15, 20, 7))
    pygame.draw.polygon(screen, (67, 65, 60), ((x + 3, y + 16), (x + 5, y + 11), (x + 10, y + 12), (x + 12, y + 17)))
    pygame.draw.polygon(screen, (86, 84, 78), ((x + 9, y + 17), (x + 12, y + 9), (x + 18, y + 10), (x + 20, y + 17)))
    pygame.draw.polygon(screen, (58, 57, 53), ((x + 17, y + 17), (x + 19, y + 12), (x + 23, y + 14), (x + 22, y + 18)))
    pygame.draw.polygon(screen, (117, 115, 106), ((x + 5, y + 13), (x + 7, y + 12), (x + 9, y + 15), (x + 5, y + 15)))
    pygame.draw.line(screen, (135, 132, 121), (x + 13, y + 11), (x + 16, y + 12), 1)
    pygame.draw.circle(screen, (44, 43, 40), (x + 8, y + 18), 1)


def draw_boulder_trap(screen, path, started_at, speed, rubble_tile, offset_x=0, offset_y=0):
    """Draw an activated boulder, its impact burst, or its lasting rubble."""
    if started_at is None:
        return
    elapsed_ms = pygame.time.get_ticks() - started_at
    boulder_position = get_boulder_position(path, elapsed_ms, speed, offset_x, offset_y)
    if boulder_position is not None:
        draw_rolling_boulder(screen, *boulder_position)
        return
    route_duration = get_boulder_path_length(path) * 1000 / speed
    if elapsed_ms < route_duration + LEVEL_FIVE_BOULDER_IMPACT_DURATION:
        impact_row, impact_column = path[-1]
        impact_x = offset_x + impact_column * CELL_SIZE + CELL_SIZE // 2
        impact_y = offset_y + impact_row * CELL_SIZE + CELL_SIZE // 2
        draw_boulder_impact(screen, impact_x, impact_y)
    else:
        rubble_x = offset_x + rubble_tile[1] * CELL_SIZE
        rubble_y = offset_y + rubble_tile[0] * CELL_SIZE
        draw_boulder_rubble(screen, rubble_x, rubble_y)


def get_swinging_axe_pose(row, column, phase, animation_time, offset_x=0, offset_y=0):
    """Return the hinge, blade tip, and angle for a swinging axe."""
    angle = math.sin(animation_time * 3.8 * phase) * 1.45
    pivot = (
        offset_x + column * CELL_SIZE + CELL_SIZE // 2,
        offset_y + row * CELL_SIZE + 3,
    )
    length = CELL_SIZE
    tip = (pivot[0] + math.sin(angle) * length, pivot[1] + math.cos(angle) * length)
    return pivot, tip, angle


def draw_swinging_axe(screen, row, column, phase, animation_time, offset_x=0, offset_y=0):
    """Draw a pixel-art axe swinging beneath a stone ceiling hinge."""
    pivot, tip, angle = get_swinging_axe_pose(row, column, phase, animation_time, offset_x, offset_y)
    direction = (math.sin(angle), math.cos(angle))
    perpendicular = (math.cos(angle), -math.sin(angle))
    pygame.draw.rect(screen, (35, 29, 26), (pivot[0] - 4, pivot[1] - 2, 8, 4))
    pygame.draw.rect(screen, (125, 94, 61), (pivot[0] - 2, pivot[1] - 1, 4, 2))
    pygame.draw.line(screen, (43, 32, 26), pivot, (int(tip[0]), int(tip[1])), 3)
    pygame.draw.line(screen, (157, 111, 67), (pivot[0], pivot[1] + 2), (int(tip[0]), int(tip[1])), 1)
    head_center = (tip[0] + direction[0], tip[1] + direction[1])
    def point(side, along):
        return (
            int(head_center[0] + perpendicular[0] * side + direction[0] * along),
            int(head_center[1] + perpendicular[1] * side + direction[1] * along),
        )
    blade = (point(-7, -3), point(3, -5), point(7, -1), point(5, 3), point(-3, 4), point(-6, 1))
    pygame.draw.polygon(screen, (39, 37, 35), blade)
    pygame.draw.polygon(screen, (137, 143, 143), (point(-5, -2), point(2, -4), point(5, -1), point(3, 2), point(-3, 3)))
    pygame.draw.line(screen, (218, 218, 205), point(-5, -2), point(2, -4), 1)


def swinging_axe_hits_player(row, column, phase, animation_time, player_x, player_y):
    """Check whether the swinging axe blade or handle overlaps the player."""
    pivot, tip, angle = get_swinging_axe_pose(row, column, phase, animation_time)
    head_x = tip[0] + math.sin(angle)
    head_y = tip[1] + math.cos(angle)
    dx = tip[0] - pivot[0]
    dy = tip[1] - pivot[1]
    segment_length_squared = dx * dx + dy * dy
    projection = ((player_x - pivot[0]) * dx + (player_y - pivot[1]) * dy) / segment_length_squared
    projection = max(0, min(1, projection))
    closest_x = pivot[0] + projection * dx
    closest_y = pivot[1] + projection * dy
    handle_distance_squared = (player_x - closest_x) ** 2 + (player_y - closest_y) ** 2
    blade_distance_squared = (player_x - head_x) ** 2 + (player_y - head_y) ** 2
    return handle_distance_squared <= 6 ** 2 or blade_distance_squared <= 10 ** 2


def get_boulder_position(path, elapsed_ms, speed, offset_x=0, offset_y=0):
    """Interpolate the boulder's screen position along a row-column path."""
    points = [
        (offset_x + column * CELL_SIZE + CELL_SIZE // 2, offset_y + row * CELL_SIZE + CELL_SIZE // 2)
        for row, column in path
    ]
    distance_left = max(0, elapsed_ms) * speed / 1000
    for start, end in zip(points, points[1:]):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        segment_length = (dx * dx + dy * dy) ** 0.5
        if distance_left <= segment_length:
            fraction = distance_left / segment_length if segment_length else 0
            return start[0] + dx * fraction, start[1] + dy * fraction
        distance_left -= segment_length
    return None


def get_boulder_path_length(path):
    """Return the complete boulder route length in pixels."""
    total = 0
    for (start_row, start_column), (end_row, end_column) in zip(path, path[1:]):
        row_delta = end_row - start_row
        column_delta = end_column - start_column
        total += (row_delta * row_delta + column_delta * column_delta) ** 0.5 * CELL_SIZE
    return total


def draw_cave_medallion(screen, x, y, animation_time=0):
    """Draw the small gold-rimmed cave artifact shown in the West Cave reference."""
    cx = x + CELL_SIZE // 2
    cy = y + CELL_SIZE // 2 + int(animation_time * 2) % 2
    pygame.draw.ellipse(screen, (24, 18, 15), (cx - 10, cy - 7, 20, 15))
    pygame.draw.circle(screen, (83, 50, 29), (cx, cy), 8)
    pygame.draw.circle(screen, (195, 126, 54), (cx, cy), 7, 2)
    pygame.draw.circle(screen, (237, 171, 79), (cx, cy), 4)
    pygame.draw.circle(screen, (106, 65, 34), (cx, cy), 2)
    pygame.draw.circle(screen, (255, 211, 126), (cx - 2, cy - 2), 1)


def draw_north_cave_artifact(screen, x, y, animation_time=0):
    """Draw a frosted turquoise crystal relic on its small carved-stone mount."""
    cx = x + CELL_SIZE // 2
    cy = y + CELL_SIZE // 2 + int(animation_time * 2) % 2
    pygame.draw.ellipse(screen, (20, 22, 21), (cx - 10, cy + 6, 20, 5))
    pygame.draw.ellipse(screen, (65, 54, 42), (cx - 9, cy + 2, 18, 7))
    pygame.draw.ellipse(screen, (143, 103, 60), (cx - 8, cy + 2, 16, 5), 1)
    crystal = ((cx, cy - 11), (cx + 6, cy - 3), (cx + 4, cy + 4), (cx, cy + 7), (cx - 5, cy + 3), (cx - 7, cy - 4))
    pygame.draw.polygon(screen, (29, 104, 103), crystal)
    pygame.draw.polygon(screen, (58, 174, 163), ((cx, cy - 9), (cx + 4, cy - 3), (cx, cy + 4), (cx - 4, cy + 2), (cx - 5, cy - 4)))
    pygame.draw.polygon(screen, (155, 242, 221), ((cx, cy - 8), (cx + 1, cy - 3), (cx, cy + 3), (cx - 2, cy - 2)))
    pygame.draw.line(screen, (201, 255, 234), (cx, cy - 8), (cx + 1, cy - 4), 1)
    pygame.draw.circle(screen, (116, 220, 196), (cx + 8, cy - 7), 1)


def draw_east_cave_artifact(screen, x, y, animation_time=0):
    """Draw a violet stormglass relic on a small carved-stone mount."""
    cx = x + CELL_SIZE // 2
    cy = y + CELL_SIZE // 2 + int(animation_time * 2) % 2
    pygame.draw.ellipse(screen, (24, 18, 20), (cx - 10, cy + 6, 20, 5))
    pygame.draw.ellipse(screen, (39, 30, 48), (cx - 9, cy + 2, 18, 7))
    pygame.draw.ellipse(screen, (94, 68, 108), (cx - 8, cy + 2, 16, 5), 1)
    crystal = ((cx, cy - 12), (cx + 7, cy - 7), (cx + 10, cy - 1), (cx + 6, cy + 7), (cx, cy + 10), (cx - 6, cy + 7), (cx - 10, cy - 1), (cx - 7, cy - 7))
    pygame.draw.polygon(screen, (70, 48, 112), crystal)
    pygame.draw.polygon(screen, (135, 98, 190), ((cx, cy - 10), (cx + 5, cy - 6), (cx + 7, cy - 1), (cx + 4, cy + 5), (cx, cy + 7)))
    pygame.draw.polygon(screen, (185, 154, 232), ((cx - 1, cy - 8), (cx - 5, cy - 5), (cx - 7, cy - 1), (cx - 4, cy + 4), (cx - 1, cy + 5)))
    pygame.draw.polygon(screen, (255, 213, 116), ((cx + 2, cy - 8), (cx - 2, cy - 1), (cx + 1, cy - 1), (cx - 2, cy + 6), (cx + 5, cy - 3), (cx + 1, cy - 3)))
    pygame.draw.line(screen, (255, 242, 183), (cx + 1, cy - 7), (cx - 1, cy - 2), 1)
    pygame.draw.polygon(screen, (236, 224, 255), ((cx - 5, cy - 5), (cx - 2, cy - 7), (cx - 1, cy - 5), (cx - 3, cy - 2)))
    pygame.draw.line(screen, (255, 255, 255), (cx - 5, cy - 5), (cx - 3, cy - 3), 1)
    pygame.draw.circle(screen, (255, 255, 240), (cx + 6, cy - 7), 1)
    pygame.draw.line(screen, (229, 249, 255), (cx + 8, cy - 5), (cx + 8, cy - 2), 1)
    pygame.draw.line(screen, (229, 249, 255), (cx + 7, cy - 4), (cx + 9, cy - 4), 1)


def draw_north_artifact_carried(screen, x, y):
    """Draw the turquoise crystal in the character's hand without its stone mount."""
    cx, cy = x + 20, y + 9
    pygame.draw.polygon(screen, (29, 104, 103), ((cx, cy - 7), (cx + 4, cy - 2), (cx + 3, cy + 4), (cx - 2, cy + 3), (cx - 4, cy - 2)))
    pygame.draw.polygon(screen, (80, 197, 179), ((cx, cy - 5), (cx + 2, cy - 1), (cx, cy + 2), (cx - 2, cy - 2)))
    pygame.draw.line(screen, (201, 255, 234), (cx, cy - 5), (cx + 1, cy - 2), 1)


def draw_east_artifact_carried(screen, x, y):
    """Draw the violet stormglass relic in the character's hand."""
    cx, cy = x + 20, y + 8
    pygame.draw.polygon(screen, (70, 48, 112), ((cx, cy - 7), (cx + 4, cy - 4), (cx + 6, cy), (cx + 3, cy + 5), (cx, cy + 7), (cx - 4, cy + 4), (cx - 6, cy), (cx - 4, cy - 4)))
    pygame.draw.polygon(screen, (144, 108, 198), ((cx, cy - 5), (cx + 3, cy - 3), (cx + 4, cy), (cx + 2, cy + 4), (cx, cy + 5)))
    pygame.draw.polygon(screen, (205, 177, 241), ((cx - 1, cy - 4), (cx - 4, cy - 2), (cx - 4, cy + 1), (cx - 1, cy + 3)))
    pygame.draw.polygon(screen, (255, 213, 116), ((cx + 1, cy - 4), (cx - 2, cy), (cx, cy), (cx - 2, cy + 4), (cx + 3, cy - 1), (cx, cy - 1)))
    pygame.draw.line(screen, (255, 242, 183), (cx, cy - 3), (cx - 1, cy - 1), 1)
    pygame.draw.line(screen, (240, 231, 255), (cx - 3, cy - 3), (cx - 1, cy - 4), 1)
    pygame.draw.circle(screen, (255, 255, 240), (cx + 4, cy - 4), 1)


def draw_torch(screen, x, y, wall_side="surface", animation_time=0):
    """Draw a warm pixel-art cave torch against the stone background."""
    if wall_side == "right":
        pygame.draw.rect(screen, (31, 34, 34), (x + 20, y + 12, 5, 7))
        pygame.draw.line(screen, (43, 45, 43), (x + 15, y + 15), (x + 24, y + 15), 3)
    elif wall_side == "left":
        pygame.draw.rect(screen, (31, 34, 34), (x, y + 12, 5, 7))
        pygame.draw.line(screen, (43, 45, 43), (x + 1, y + 15), (x + 10, y + 15), 3)
    else:
        pygame.draw.rect(screen, (28, 29, 28), (x + 8, y + 14, 11, 5))
    pygame.draw.polygon(screen, (105, 68, 42), ((x + 12, y + 22), (x + 15, y + 22), (x + 14, y + 10), (x + 11, y + 10)))
    pygame.draw.line(screen, (160, 112, 67), (x + 12, y + 13), (x + 14, y + 20), 1)
    draw_flame(screen, x + 9, y + 2, animation_time, width=9, height=12)


def draw_carried_torch(screen, x, y, animation_time=0):
    """Draw the picked-up torch in the character's hand."""
    pygame.draw.line(screen, (68, 43, 29), (x + 17, y + 19), (x + 21, y + 9), 3)
    pygame.draw.line(screen, (166, 112, 65), (x + 18, y + 17), (x + 21, y + 10), 1)
    draw_flame(screen, x + 17, y + 1, animation_time, width=8, height=12)


def make_level_three_floor():
    """Create a dark blue-grey cobblestone floor for the later cave levels."""
    floor = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    floor.fill((13, 20, 23))
    rng = random.Random(31)
    stone_width = 43
    stone_height = 35
    rows = (WINDOW_HEIGHT + stone_height - 1) // stone_height
    columns = (WINDOW_WIDTH + stone_width - 1) // stone_width + 1

    for row in range(rows):
        for column in range(columns):
            x = column * stone_width - (stone_width // 2 if row % 2 else 0)
            y = row * stone_height
            inset = rng.randint(2, 5)
            left = x + inset
            top = y + rng.randint(2, 5)
            right = x + stone_width - rng.randint(2, 5)
            bottom = y + stone_height - rng.randint(2, 5)
            points = [
                (left + rng.randint(4, 9), top),
                (right - rng.randint(5, 10), top + rng.randint(-1, 2)),
                (right, top + rng.randint(5, 10)),
                (right + rng.randint(-1, 2), bottom - rng.randint(5, 10)),
                (right - rng.randint(6, 11), bottom),
                (left + rng.randint(6, 11), bottom + rng.randint(-2, 1)),
                (left, bottom - rng.randint(5, 10)),
                (left + rng.randint(-2, 1), top + rng.randint(6, 11)),
            ]
            shade = rng.randint(26, 48)
            pygame.draw.polygon(floor, (shade - 2, shade + 2, shade + rng.randint(8, 14)), points)
            pygame.draw.lines(floor, (12, 19, 23), True, points, 2)

            # Cool, broken bevels give the dark stones a readable worn edge.
            highlight = shade + rng.randint(12, 20)
            pygame.draw.line(floor, (highlight - 3, highlight + 2, highlight + 8), points[0], points[1], 1)
            pygame.draw.line(floor, (highlight - 8, highlight - 3, highlight + 2), points[7], points[0], 1)
            shadow = max(14, shade - 15)
            pygame.draw.line(floor, (shadow, shadow + 3, shadow + 7), points[3], points[4], 2)

            if rng.random() < 0.35:
                chip_x = rng.randint(left + 7, max(left + 7, right - 8))
                chip_y = rng.randint(top + 7, max(top + 7, bottom - 7))
                chip_size = rng.randint(2, 4)
                pygame.draw.line(
                    floor,
                    (max(20, shade - 10), max(23, shade - 7), max(28, shade - 3)),
                    (chip_x, chip_y),
                    (chip_x + chip_size, chip_y + 1),
                    1,
                )

    return floor


def make_warm_cave_floor(width=WINDOW_WIDTH, height=WINDOW_HEIGHT, original=False, stone_width=43, stone_height=35):
    """Create the original rust cave floor or Level 5's deep violet stone floor."""
    floor = pygame.Surface((width, height))
    floor.fill(ORIGINAL_CAVE_FLOOR if original else WARM_CAVE_FLOOR)
    rng = random.Random(58)
    rows = (height + stone_height - 1) // stone_height
    columns = (width + stone_width - 1) // stone_width + 1

    for row in range(rows):
        for column in range(columns):
            x = column * stone_width - (stone_width // 2 if row % 2 else 0)
            y = row * stone_height
            inset = rng.randint(2, 5)
            left = x + inset
            top = y + rng.randint(2, 5)
            right = x + stone_width - rng.randint(2, 5)
            bottom = y + stone_height - rng.randint(2, 5)
            points = [
                (left + rng.randint(4, 9), top),
                (right - rng.randint(5, 10), top + rng.randint(-1, 2)),
                (right, top + rng.randint(5, 10)),
                (right + rng.randint(-1, 2), bottom - rng.randint(5, 10)),
                (right - rng.randint(6, 11), bottom),
                (left + rng.randint(6, 11), bottom + rng.randint(-2, 1)),
                (left, bottom - rng.randint(5, 10)),
                (left + rng.randint(-2, 1), top + rng.randint(6, 11)),
            ]
            if original:
                shade = rng.randint(30, 55)
                pygame.draw.polygon(floor, (shade + 5, shade, max(22, shade - 5)), points)
                pygame.draw.lines(floor, (19, 16, 17), True, points, 2)
            else:
                shade = rng.randint(20, 42)
                pygame.draw.polygon(floor, (shade + 6, shade, shade + 9), points)
                pygame.draw.lines(floor, (13, 10, 19), True, points, 2)

            highlight = shade + rng.randint(11, 20 if original else 19)
            if original:
                pygame.draw.line(floor, (highlight + 5, highlight, highlight - 4), points[0], points[1], 1)
                pygame.draw.line(floor, (highlight, highlight - 4, highlight - 8), points[7], points[0], 1)
            else:
                pygame.draw.line(floor, (highlight + 10, highlight + 1, highlight + 2), points[0], points[1], 1)
                pygame.draw.line(floor, (highlight + 4, highlight - 3, highlight + 2), points[7], points[0], 1)
            shadow = max(15, shade - 14)
            pygame.draw.line(floor, (shadow + 3, shadow, shadow), points[3], points[4], 2)

            if rng.random() < 0.35:
                chip_x = rng.randint(left + 7, max(left + 7, right - 8))
                chip_y = rng.randint(top + 7, max(top + 7, bottom - 7))
                chip_size = rng.randint(2, 4)
                chip_color = (
                    (max(21, shade - 8), max(17, shade - 12), max(16, shade - 13))
                    if original else
                    (max(34, shade + 8), max(20, shade - 3), max(24, shade + 3))
                )
                pygame.draw.line(floor, chip_color, (chip_x, chip_y), (chip_x + chip_size, chip_y + 1), 1)

    return floor


def make_cave_wall_backdrop(width, height, stone_scale):
    """Create a dark rocky cave wall with warm torches for the outer margins."""
    backdrop = pygame.Surface((width, height))
    backdrop.fill((8, 9, 10))
    rng = random.Random(91)
    stone_width = max(1, round(43 * stone_scale))
    stone_height = max(1, round(35 * stone_scale))
    rows = (height + stone_height - 1) // stone_height
    columns = (width + stone_width - 1) // stone_width + 1
    gap = max(1, round(3 * stone_scale))

    for row in range(rows):
        for column in range(columns):
            x = column * stone_width - (stone_width // 2 if row % 2 else 0)
            y = row * stone_height
            inset = max(1, round(rng.randint(2, 5) * stone_scale))
            left = x + inset
            top = y + inset
            right = x + stone_width - inset
            bottom = y + stone_height - inset
            points = [
                (left + rng.randint(4, 9) * stone_scale, top),
                (right - rng.randint(5, 10) * stone_scale, top + rng.randint(-1, 2) * stone_scale),
                (right, top + rng.randint(5, 10) * stone_scale),
                (right + rng.randint(-1, 2) * stone_scale, bottom - rng.randint(5, 10) * stone_scale),
                (right - rng.randint(6, 11) * stone_scale, bottom),
                (left + rng.randint(6, 11) * stone_scale, bottom),
                (left, bottom - rng.randint(5, 10) * stone_scale),
                (left, top + rng.randint(6, 11) * stone_scale),
            ]
            points = [(round(px), round(py)) for px, py in points]
            shade = rng.randint(25, 43)
            pygame.draw.polygon(backdrop, (shade + 2, shade + 1, shade), points)
            pygame.draw.lines(backdrop, (5, 6, 7), True, points, gap)
            edge = min(255, shade + rng.randint(9, 16))
            pygame.draw.line(backdrop, (edge, edge - 1, edge - 2), points[0], points[1], max(1, round(stone_scale)))
            pygame.draw.line(backdrop, (max(8, shade - 12), max(8, shade - 12), max(9, shade - 10)), points[3], points[4], gap)
            facet = (points[0], points[1], (round((points[1][0] + points[2][0]) / 2), round((points[1][1] + points[2][1]) / 2)))
            pygame.draw.polygon(backdrop, (shade + 6, shade + 6, shade + 7), facet)
            if rng.random() < 0.58:
                crack_x = x + round(stone_width * rng.uniform(0.35, 0.7))
                crack_y = y + round(stone_height * rng.uniform(0.3, 0.65))
                crack = (
                    (crack_x, crack_y),
                    (crack_x + round(rng.randint(-5, 5) * stone_scale), crack_y + round(rng.randint(3, 7) * stone_scale)),
                    (crack_x + round(rng.randint(-7, 7) * stone_scale), crack_y + round(rng.randint(7, 12) * stone_scale)),
                )
                pygame.draw.lines(backdrop, (11, 12, 13), False, crack, max(1, round(2 * stone_scale)))
                pygame.draw.line(backdrop, (shade + 7, shade + 6, shade + 5), crack[0], crack[1], max(1, round(stone_scale)))
            for _ in range(rng.randint(2, 5)):
                fleck_x = rng.randint(left + 2, max(left + 2, right - 2))
                fleck_y = rng.randint(top + 2, max(top + 2, bottom - 2))
                fleck = rng.choice(((shade + 8, shade + 8, shade + 9), (shade - 7, shade - 6, shade - 5), (17, 18, 19)))
                pygame.draw.circle(backdrop, fleck, (fleck_x, fleck_y), max(1, round(stone_scale)))

    # Add soft pools of torchlight behind small torches in the side margins.
    side_width = (width - round(WINDOW_WIDTH * stone_scale)) // 2
    if side_width > round(45 * stone_scale):
        glow = pygame.Surface((width, height), pygame.SRCALPHA)
        torch_sprite = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        draw_torch(torch_sprite, 0, 0)
        torch_size = max(1, round(CELL_SIZE * 2 * stone_scale))
        torch_sprite = pygame.transform.scale(torch_sprite, (torch_size, torch_size))
        for side_x in (side_width // 2, width - side_width // 2):
            for y in (round(height * 0.25), round(height * 0.76)):
                glow_radius = round(85 * stone_scale)
                for radius, alpha in ((glow_radius, 12), (round(glow_radius * 0.65), 17), (round(glow_radius * 0.35), 22)):
                    pygame.draw.circle(glow, (235, 112, 40, alpha), (side_x, y), radius)
        backdrop.blit(glow, (0, 0))
        for side_x in (side_width // 2, width - side_width // 2):
            for y in (round(height * 0.25), round(height * 0.76)):
                backdrop.blit(torch_sprite, torch_sprite.get_rect(center=(side_x, y)))

        # Jagged boulders at the far edges make the side panels feel like a
        # passage through a cave, instead of a flat tiled wall.
        rock_rng = random.Random(17)
        for edge_x, direction in ((0, 1), (width, -1)):
            for row in range(9):
                rock_y = row * height // 8 - round(25 * stone_scale)
                rock_w = round(52 * stone_scale * rock_rng.uniform(0.8, 1.35))
                rock_h = round(72 * stone_scale * rock_rng.uniform(0.75, 1.45))
                points = [
                    (edge_x, rock_y),
                    (edge_x + direction * round(rock_w * 0.52), rock_y + round(rock_h * 0.08)),
                    (edge_x + direction * rock_w, rock_y + round(rock_h * 0.34)),
                    (edge_x + direction * round(rock_w * 0.86), rock_y + round(rock_h * 0.78)),
                    (edge_x + direction * round(rock_w * 0.45), rock_y + rock_h),
                    (edge_x, rock_y + round(rock_h * 0.83)),
                ]
                shade = rock_rng.randint(25, 39)
                pygame.draw.polygon(backdrop, (shade + 1, shade + 2, shade + 4), points)
                pygame.draw.lines(backdrop, (8, 9, 11), True, points, max(2, round(3 * stone_scale)))
                pygame.draw.line(backdrop, (shade + 12, shade + 13, shade + 15), points[0], points[1], max(1, round(stone_scale)))

        def draw_barrel(center_x, center_y, size):
            barrel_w, barrel_h = round(30 * size), round(39 * size)
            bounds = pygame.Rect(0, 0, barrel_w, barrel_h)
            bounds.center = (center_x, center_y)
            pygame.draw.ellipse(backdrop, (37, 23, 14), bounds)
            pygame.draw.rect(backdrop, (81, 47, 25), bounds.inflate(-round(4 * size), -round(4 * size)))
            pygame.draw.ellipse(backdrop, (119, 76, 39), (bounds.x + 2, bounds.y, bounds.w - 4, round(10 * size)))
            for plank_x in (bounds.x + round(9 * size), bounds.x + round(19 * size)):
                pygame.draw.line(backdrop, (49, 30, 18), (plank_x, bounds.y + round(6 * size)), (plank_x, bounds.bottom - round(5 * size)), max(1, round(size)))
            for band_y in (bounds.y + round(9 * size), bounds.bottom - round(10 * size)):
                pygame.draw.line(backdrop, (137, 91, 48), (bounds.x + 2, band_y), (bounds.right - 2, band_y), max(2, round(3 * size)))
                pygame.draw.line(backdrop, (48, 48, 45), (bounds.x + 3, band_y + round(2 * size)), (bounds.right - 3, band_y + round(2 * size)), max(1, round(size)))
            pygame.draw.line(backdrop, (177, 119, 61), (bounds.x + round(5 * size), bounds.y + round(13 * size)), (bounds.x + round(5 * size), bounds.bottom - round(13 * size)), max(1, round(size)))
            pygame.draw.ellipse(backdrop, (44, 27, 16), (bounds.x + round(5 * size), bounds.y + round(2 * size), bounds.w - round(10 * size), round(6 * size)))

        def draw_crate(center_x, center_y, size):
            box = pygame.Rect(0, 0, round(39 * size), round(35 * size))
            box.center = (center_x, center_y)
            pygame.draw.rect(backdrop, (75, 43, 21), box)
            pygame.draw.rect(backdrop, (139, 84, 37), box, max(2, round(3 * size)))
            pygame.draw.line(backdrop, (166, 105, 48), box.topleft, box.bottomright, max(2, round(4 * size)))
            pygame.draw.line(backdrop, (166, 105, 48), box.topright, box.bottomleft, max(2, round(4 * size)))
            pygame.draw.rect(backdrop, (57, 34, 20), box.inflate(-round(9 * size), -round(9 * size)), max(1, round(size)))
            nail = (206, 154, 83)
            for nail_point in (box.topleft, box.topright, box.bottomleft, box.bottomright):
                pygame.draw.circle(backdrop, nail, nail_point, max(1, round(size)))

        def draw_skull(center_x, center_y, size):
            radius = max(2, round(7 * size))
            bone = (173, 157, 125)
            pygame.draw.circle(backdrop, bone, (center_x, center_y), radius)
            pygame.draw.ellipse(backdrop, bone, (center_x - radius, center_y + round(3 * size), radius * 2, round(8 * size)))
            eye_radius = max(1, round(2 * size))
            pygame.draw.circle(backdrop, (25, 21, 18), (center_x - round(3 * size), center_y), eye_radius)
            pygame.draw.circle(backdrop, (25, 21, 18), (center_x + round(3 * size), center_y), eye_radius)
            pygame.draw.line(backdrop, (70, 58, 43), (center_x - round(3 * size), center_y + round(6 * size)), (center_x + round(3 * size), center_y + round(6 * size)), max(1, round(size)))
            for tooth_x in (center_x - round(2 * size), center_x, center_x + round(2 * size)):
                pygame.draw.line(backdrop, (220, 204, 169), (tooth_x, center_y + round(6 * size)), (tooth_x, center_y + round(8 * size)), max(1, round(size)))

        def draw_web(anchor_x, anchor_y, size, flip_x=1, flip_y=1):
            radius = round(34 * size)
            origin = (anchor_x, anchor_y)
            for spoke in range(6):
                angle = spoke / 5
                end = (anchor_x + flip_x * round(radius * angle), anchor_y + flip_y * round(radius * (1 - angle)))
                pygame.draw.line(backdrop, (72, 67, 61), origin, end, max(1, round(size)))
            for ring in (0.35, 0.62, 0.88):
                points = []
                for spoke in range(6):
                    angle = spoke / 5
                    points.append((
                        anchor_x + flip_x * round(radius * angle * ring),
                        anchor_y + flip_y * round(radius * (1 - angle) * ring),
                    ))
                pygame.draw.lines(backdrop, (68, 63, 58), False, points, max(1, round(size)))

        prop_scale = max(0.7, stone_scale)
        for side_x, inward in ((side_width // 2, 1), (width - side_width // 2, -1)):
            draw_barrel(side_x + inward * round(side_width * 0.27), round(height * 0.13), prop_scale)
            draw_skull(side_x - inward * round(side_width * 0.25), round(height * 0.32), prop_scale)
            draw_crate(side_x - inward * round(side_width * 0.24), round(height * 0.48), prop_scale)
            draw_barrel(side_x + inward * round(side_width * 0.29), round(height * 0.83), prop_scale)
            draw_skull(side_x - inward * round(side_width * 0.25), round(height * 0.91), prop_scale)
        draw_web(0, 0, prop_scale, 1, 1)
        draw_web(width, height, prop_scale, -1, -1)

    return backdrop


def draw_character(screen, x, y, animation_time=0, walking=False, walk_frame=0):
    """Draw the yellow, blue-shoed character from the supplied reference."""
    pixel = 2

    # A stepped silhouette keeps the round body pixelated.
    body = [
        "..YYYYYYY..",
        ".YYYYYYYYY.",
        "YYYYYYYYYYY",
        "YYYYYYYYYYY",
        "YYYYYYYYYYY",
        ".YYYYYYYYY.",
        "..YYYYYYY..",
    ]
    for row, line in enumerate(body):
        for column, cell in enumerate(line):
            if cell == "Y":
                pygame.draw.rect(screen, CHARACTER_YELLOW, (x + column * pixel, y + row * pixel, pixel, pixel))

    # Glossy highlight and large black eyes with white glints.
    for column, row in ((3, 0), (2, 1), (1, 2)):
        pygame.draw.rect(screen, CHARACTER_HIGHLIGHT, (x + column * pixel, y + row * pixel, pixel, pixel))
    blinking = not walking and animation_time % 4.2 > 4.05
    if blinking:
        pygame.draw.line(screen, CHARACTER_BLACK, (x + 6, y + 8), (x + 9, y + 8), 2)
        pygame.draw.line(screen, CHARACTER_BLACK, (x + 14, y + 8), (x + 17, y + 8), 2)
    else:
        pygame.draw.rect(screen, CHARACTER_BLACK, (x + 3 * pixel, y + 3 * pixel, 2 * pixel, 3 * pixel))
        pygame.draw.rect(screen, CHARACTER_BLACK, (x + 7 * pixel, y + 3 * pixel, 2 * pixel, 3 * pixel))
        pygame.draw.rect(screen, EYE_WHITE, (x + 3 * pixel, y + 3 * pixel, pixel, pixel))
        pygame.draw.rect(screen, EYE_WHITE, (x + 7 * pixel, y + 3 * pixel, pixel, pixel))

    # Bright blue shoes with darker soles.
    left_lift = -pixel if walking and walk_frame else 0
    right_lift = -pixel if walking and not walk_frame else 0
    pygame.draw.rect(screen, SHOE_BLUE, (x + pixel, y + 7 * pixel + left_lift, 4 * pixel, 2 * pixel))
    pygame.draw.rect(screen, SHOE_BLUE, (x + 7 * pixel, y + 7 * pixel + right_lift, 4 * pixel, 2 * pixel))
    pygame.draw.rect(screen, SHOE_DARK_BLUE, (x + pixel, y + 9 * pixel + left_lift, 4 * pixel, pixel))
    pygame.draw.rect(screen, SHOE_DARK_BLUE, (x + 7 * pixel, y + 9 * pixel + right_lift, 4 * pixel, pixel))


def draw_death_animation(screen, elapsed_ms, player_position, animation_time):
    """Animate the character jumping up, then falling off the bottom of the maze."""
    x, base_y = map(int, player_position)
    jump_duration = 360
    total_duration = 1350

    if elapsed_ms < jump_duration:
        jump_progress = max(0.0, elapsed_ms / jump_duration)
        vertical_offset = -round(48 * math.sin(jump_progress * math.pi / 2))
        shadow_width = max(3, round(15 * (1 - jump_progress * 0.65)))
        pygame.draw.ellipse(
            screen, (10, 9, 8),
            (x + 10 - shadow_width // 2, base_y + 19, shadow_width, 4),
        )
    else:
        fall_progress = min(1.0, (elapsed_ms - jump_duration) / (total_duration - jump_duration))
        # Accelerating descent gives the familiar high jump followed by a fast fall.
        vertical_offset = -48 + round((screen.get_height() + 80) * fall_progress ** 2)

    draw_character(
        screen,
        x,
        base_y + vertical_offset,
        animation_time=animation_time,
        walking=False,
        walk_frame=0,
    )


def wrap_text_lines(text, font, max_width):
    """Wrap text to a pixel width, including breaking unusually long words."""
    lines = []
    current_line = ""
    for word in str(text).split():
        candidate = f"{current_line} {word}".strip()
        if font.size(candidate)[0] <= max_width:
            current_line = candidate
            continue

        if current_line:
            lines.append(current_line)
            current_line = ""
        for character in word:
            candidate = current_line + character
            if current_line and font.size(candidate)[0] > max_width:
                lines.append(current_line)
                current_line = character
            else:
                current_line = candidate
    if current_line:
        lines.append(current_line)
    return lines or [""]


def main():
    pygame.init()
    pygame.key.set_repeat(180, PLAYER_KEY_REPEAT_INTERVAL_MS)
    display_surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    display_width, display_height = display_surface.get_size()
    fit_scale = min(display_width / WINDOW_WIDTH, display_height / WINDOW_HEIGHT)
    fit_size = (int(WINDOW_WIDTH * fit_scale), int(WINDOW_HEIGHT * fit_scale))
    project_dir = Path(__file__).resolve().parent
    left_cave_art = pygame.image.load(str(project_dir / "assets" / "maze_cave_left.png")).convert()
    right_cave_art = pygame.image.load(str(project_dir / "assets" / "maze_cave_right.png")).convert()
    how_to_play_panel = pygame.image.load(
        str(project_dir / "assets" / "how_to_play_panel.png")
    ).convert_alpha()
    backdrop = pygame.Surface(display_surface.get_size())
    backdrop.fill((8, 9, 10))
    side_width = (display_width - fit_size[0]) // 2
    if side_width > 0:
        left_panel = pygame.transform.smoothscale(left_cave_art, (side_width + 1, display_height))
        right_panel = pygame.transform.smoothscale(right_cave_art, (side_width + 1, display_height))
        backdrop.blit(left_panel, (0, 0))
        backdrop.blit(right_panel, (display_width - side_width - 1, 0))
    screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    # Build static floor textures once; their stone patterns do not change
    # during play, so they do not need to be recreated every frame.
    floor_texture = make_level_three_floor()
    warm_cave_floor_texture = make_warm_cave_floor()
    warm_cave_section_floor_texture = make_warm_cave_floor(16 * CELL_SIZE, 16 * CELL_SIZE)
    original_cave_floor_texture = make_warm_cave_floor(original=True)
    small_section_surface = pygame.Surface((16 * CELL_SIZE, 16 * CELL_SIZE))
    transition_font = pygame.font.Font(None, 46)
    quiz_title_font = pygame.font.Font(None, 42)
    quiz_body_font = pygame.font.Font(None, 30)
    hud_font = pygame.font.Font(None, 27)
    name_ui_scale = min(display_width / 582, display_height / 292)
    name_title_font = pygame.font.SysFont("georgia", max(1, round(21 * name_ui_scale)), bold=True)
    name_subtitle_font = pygame.font.SysFont("georgia", max(1, round(12 * name_ui_scale)))
    name_entry_font = pygame.font.SysFont("georgia", max(1, round(16 * name_ui_scale)), bold=True)
    name_key_font = pygame.font.SysFont("georgia", max(1, round(13 * name_ui_scale)), bold=True)
    name_hint_font = pygame.font.SysFont("georgia", max(1, round(10 * name_ui_scale)))
    player_label_font = pygame.font.Font(None, 15)
    score_hud_base_size = max(34, round(display_height * 0.045))
    score_font_cache = {}
    pygame.display.set_caption("Arcade Maze")
    clock = pygame.time.Clock()
    running = True
    name_entry = True
    how_to_play_screen = False
    player_name = ""
    keyboard_row = 0
    keyboard_column = 2
    name_keyboard = [
        list("QWERTYUIOP"),
        list("ASDFGHJKLZ"),
        [*list("XCVBNM"), "SPACE", "DEL"],
        ["START"],
    ]
    # These variables hold the active map and its puzzle/hazard progress.
    # A value of None means a timed hazard has not been triggered yet.
    maze = MAZE
    player_row = START_ROW
    player_column = START_COLUMN
    player_facing = (-1, 0)
    level = 1
    buttons = [dict(button, pressed=False) for button in LEVEL_THREE_BUTTONS]
    gate_slide_started_at = None
    torches = []
    carrying_torch = False
    lit_pillars = set()
    section_exit_armed = False
    carrying_cave_artifact = None
    placed_cave_artifacts = {}
    game_finished = False
    boulder_started_at = None
    upper_left_boulder_started_at = None
    level_four_boulder_started_at = None
    axes_started_at = None
    east_arrows = []
    east_arrows_last_fired_at = None
    east_arrows_last_updated_at = None
    level_transition_started_at = None
    level_transition_title = ""
    pending_quiz_reason = None
    quiz_phase = None
    quiz_reason = ""
    quiz_difficulty = ""
    quiz_feedback = ""
    quiz_question = None
    quiz_selected_option = 0
    death_animation_type = None
    death_animation_started_at = None
    death_animation_last_update_at = None
    death_animation_world_time = None
    question_cache = {difficulty: [] for difficulty in ("Easy", "Medium", "Hard")}
    question_cache_target = 1
    question_cache_lock = threading.Lock()
    question_generation_queue = queue.Queue()
    question_generation_in_progress = set()
    question_generation_errors = {}
    quiz_started_at = None
    score = 0
    level_one_started_at = None
    level_two_started_at = None
    level_three_started_at = None
    level_four_started_at = None
    level_five_started_at = None
    last_move_at = 0
    pygame.display.set_caption(f"Arcade Maze - Level {level}")
    movement = {
        pygame.K_w: (-1, 0),
        pygame.K_s: (1, 0),
        pygame.K_a: (0, -1),
        pygame.K_d: (0, 1),
    }

    def queue_question_generation(difficulty):
        """Keep at most one ready or in-progress question for each difficulty."""
        with question_cache_lock:
            if (
                len(question_cache[difficulty])
                + (difficulty in question_generation_in_progress)
                >= question_cache_target
            ):
                return
            question_generation_in_progress.add(difficulty)
            question_generation_errors.pop(difficulty, None)
        question_generation_queue.put(difficulty)

    def question_generation_worker():
        while True:
            difficulty = question_generation_queue.get()
            try:
                question = generate_question(difficulty)
            except Exception as error:
                with question_cache_lock:
                    question_generation_errors[difficulty] = str(error)
                    question_generation_in_progress.discard(difficulty)
            else:
                with question_cache_lock:
                    question_cache[difficulty].append(question)
                    question_generation_errors.pop(difficulty, None)
                    question_generation_in_progress.discard(difficulty)
            finally:
                question_generation_queue.task_done()

    threading.Thread(target=question_generation_worker, daemon=True).start()
    # Generate one question for each difficulty while the player enters their name.
    for question_difficulty in question_cache:
        queue_question_generation(question_difficulty)

    def begin_level_transition(title, quiz_reason=None):
        nonlocal level_transition_started_at, level_transition_title, pending_quiz_reason
        level_transition_started_at = pygame.time.get_ticks()
        level_transition_title = title
        if quiz_reason is not None:
            pending_quiz_reason = quiz_reason

    def begin_quiz(reason):
        nonlocal quiz_phase, quiz_reason, quiz_difficulty, quiz_feedback, quiz_started_at
        nonlocal quiz_question, quiz_selected_option
        quiz_reason = reason
        quiz_phase = "difficulty"
        quiz_difficulty = ""
        quiz_feedback = ""
        quiz_selected_option = 0
        quiz_started_at = pygame.time.get_ticks()
        quiz_question = None

    def choose_quiz_difficulty(difficulty):
        nonlocal quiz_phase, quiz_difficulty, quiz_question, quiz_selected_option
        quiz_difficulty = difficulty
        load_next_quiz_question()

    def load_next_quiz_question():
        nonlocal quiz_phase, quiz_question, quiz_selected_option
        quiz_selected_option = 0
        quiz_question = None
        with question_cache_lock:
            if question_cache[quiz_difficulty]:
                quiz_question = question_cache[quiz_difficulty].pop(0)
            generation_error = question_generation_errors.get(quiz_difficulty)
        if quiz_question is not None:
            quiz_phase = "question"
        elif generation_error:
            quiz_phase = "error"
        else:
            quiz_phase = "loading"
            queue_question_generation(quiz_difficulty)

    def close_quiz():
        nonlocal quiz_phase, quiz_started_at
        nonlocal level_two_started_at
        nonlocal level_three_started_at
        nonlocal level_four_started_at
        nonlocal level_five_started_at
        nonlocal boulder_started_at, upper_left_boulder_started_at
        nonlocal level_four_boulder_started_at, axes_started_at
        nonlocal east_arrows_last_fired_at, east_arrows_last_updated_at
        paused_ms = pygame.time.get_ticks() - quiz_started_at if quiz_started_at is not None else 0
        # Keep timed hazards paused while the modal question flow is open.
        if boulder_started_at is not None:
            boulder_started_at += paused_ms
        if upper_left_boulder_started_at is not None:
            upper_left_boulder_started_at += paused_ms
        if level_four_boulder_started_at is not None:
            level_four_boulder_started_at += paused_ms
        if axes_started_at is not None:
            axes_started_at += paused_ms
        if east_arrows_last_fired_at is not None:
            east_arrows_last_fired_at += paused_ms
        if east_arrows_last_updated_at is not None:
            east_arrows_last_updated_at += paused_ms
        if level == 2 and quiz_reason.startswith("Level 1 complete"):
            level_two_started_at = pygame.time.get_ticks()
        if level == 3 and quiz_reason.startswith("Level 2 complete"):
            level_three_started_at = pygame.time.get_ticks()
        if level == 4 and quiz_reason.startswith("Level 3 complete"):
            level_four_started_at = pygame.time.get_ticks()
        if level == 5 and quiz_reason.startswith("Level 4 complete"):
            level_five_started_at = pygame.time.get_ticks()
        quiz_phase = None
        quiz_started_at = None

    def start_death_animation():
        nonlocal death_animation_type, death_animation_started_at
        nonlocal death_animation_last_update_at, death_animation_world_time
        if death_animation_type is None:
            death_animation_type = "universal"
            death_animation_started_at = pygame.time.get_ticks()
            death_animation_last_update_at = death_animation_started_at
            death_animation_world_time = death_animation_started_at

    def reset_after_death():
        """Restart the whole active level, including Level 5's cave sections."""
        nonlocal level, maze, player_row, player_column, player_facing
        nonlocal torches, carrying_torch, lit_pillars
        nonlocal level_four_boulder_started_at, section_exit_armed
        nonlocal boulder_started_at, upper_left_boulder_started_at, axes_started_at
        nonlocal carrying_cave_artifact, placed_cave_artifacts
        nonlocal east_arrows, east_arrows_last_fired_at, east_arrows_last_updated_at
        nonlocal death_animation_type, death_animation_started_at
        nonlocal death_animation_last_update_at, death_animation_world_time

        # Death inside a Level 5 side cave resets the whole Level 5 quest,
        # including relics, placed objects, traps, and arrows.
        if level in LEVEL_FIVE_SECTIONS_BY_LEVEL:
            level = 5

        if level == 4:
            maze = LEVEL_FOUR_MAZE.copy()
            player_row, player_column = START_ROW, START_COLUMN
            torches = list(LEVEL_FOUR_TORCHES)
            carrying_torch = False
            lit_pillars = set()
            level_four_boulder_started_at = None
        else:
            level = 5
            maze = LEVEL_FIVE_MAZE.copy()
            player_row, player_column = LEVEL_FIVE_START_ROW, LEVEL_FIVE_START_COLUMN
            boulder_started_at = None
            upper_left_boulder_started_at = None
            axes_started_at = None
            carrying_cave_artifact = None
            placed_cave_artifacts = {}
            east_arrows = []
            east_arrows_last_fired_at = None
            east_arrows_last_updated_at = None
        player_facing = (-1, 0)
        section_exit_armed = False
        death_animation_type = None
        death_animation_started_at = None
        death_animation_last_update_at = None
        death_animation_world_time = None
        last_move_at = pygame.time.get_ticks()
        pygame.display.set_caption(f"Arcade Maze - Level {level}")
        begin_level_transition("You Died", quiz_reason="Player died")

    while running:
        # Keep the exact hazard that caused the collision visible in its impact
        # pose for the duration of the death animation.
        if death_animation_type is not None and death_animation_last_update_at is not None:
            now = pygame.time.get_ticks()
            frozen_ms = now - death_animation_last_update_at
            if boulder_started_at is not None:
                boulder_started_at += frozen_ms
            if upper_left_boulder_started_at is not None:
                upper_left_boulder_started_at += frozen_ms
            if level_four_boulder_started_at is not None:
                level_four_boulder_started_at += frozen_ms
            if axes_started_at is not None:
                axes_started_at += frozen_ms
            death_animation_last_update_at = now

        if (
            death_animation_type is not None
            and death_animation_started_at is not None
            and pygame.time.get_ticks() - death_animation_started_at >= 1350
        ):
            reset_after_death()

        if quiz_phase == "loading":
            with question_cache_lock:
                if question_cache[quiz_difficulty]:
                    quiz_question = question_cache[quiz_difficulty].pop(0)
                    generation_error = None
                else:
                    generation_error = question_generation_errors.get(quiz_difficulty)
            if quiz_question is not None:
                quiz_phase = "question"
                quiz_selected_option = 0
            elif generation_error:
                quiz_phase = "error"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and death_animation_type is not None:
                continue
            elif event.type == pygame.KEYDOWN and name_entry:
                if event.key in (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d):
                    row_step, column_step = {
                        pygame.K_w: (-1, 0), pygame.K_s: (1, 0),
                        pygame.K_a: (0, -1), pygame.K_d: (0, 1),
                    }[event.key]
                    next_row = keyboard_row + row_step
                    next_column = keyboard_column + column_step
                    if 0 <= next_row < len(name_keyboard):
                        if row_step:
                            valid_columns = [
                                index for index, label in enumerate(name_keyboard[next_row]) if label
                            ]
                            next_column = min(valid_columns, key=lambda index: abs(index - keyboard_column))
                        else:
                            while (
                                0 <= next_column < len(name_keyboard[next_row])
                                and not name_keyboard[next_row][next_column]
                            ):
                                next_column += column_step
                            if not 0 <= next_column < len(name_keyboard[next_row]):
                                continue
                        keyboard_row, keyboard_column = next_row, next_column
                elif event.key in (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    selected_key = name_keyboard[keyboard_row][keyboard_column]
                    if selected_key == "START":
                        if player_name.strip():
                            player_name = player_name.strip()
                            name_entry = False
                            how_to_play_screen = True
                    elif selected_key == "DEL":
                        player_name = player_name[:-1]
                    elif selected_key == "SPACE":
                        if player_name and not player_name.endswith(" ") and len(player_name) < 16:
                            player_name += " "
                    elif selected_key and len(player_name) < 16:
                        player_name += selected_key
            elif event.type == pygame.KEYDOWN and how_to_play_screen:
                if event.key in (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    how_to_play_screen = False
                    level_one_started_at = pygame.time.get_ticks()
            elif event.type == pygame.KEYDOWN and (
                level_transition_started_at is not None
                or (game_finished and quiz_phase is None)
            ):
                continue
            elif event.type == pygame.KEYDOWN and quiz_phase is not None:
                if quiz_phase == "difficulty":
                    if event.key in (pygame.K_w, pygame.K_a):
                        quiz_selected_option = max(0, quiz_selected_option - 1)
                    elif event.key in (pygame.K_s, pygame.K_d):
                        quiz_selected_option = min(2, quiz_selected_option + 1)
                    if event.key in (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        choose_quiz_difficulty(("Easy", "Medium", "Hard")[quiz_selected_option])
                elif quiz_phase == "question":
                    row, column = divmod(quiz_selected_option, 2)
                    if event.key == pygame.K_w:
                        row = max(0, row - 1)
                    elif event.key == pygame.K_s:
                        row = min(1, row + 1)
                    elif event.key == pygame.K_a:
                        column = max(0, column - 1)
                    elif event.key == pygame.K_d:
                        column = min(1, column + 1)
                    elif event.key in (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        selected_answer = "ABCD"[quiz_selected_option]
                        reward = {"Easy": 10, "Medium": 25, "Hard": 50}[quiz_difficulty]
                        if selected_answer == quiz_question["correct_answer"]:
                            if quiz_reason != "Player died":
                                score += reward
                                quiz_feedback = f"Correct! {selected_answer} is right. Reward: {reward} points"
                            else:
                                quiz_feedback = f"Correct! {selected_answer} is right. No points awarded for respawning."
                            quiz_phase = "result"
                        else:
                            deduction = min(score, reward)
                            score = max(0, score - reward)
                            correct_answer = quiz_question["correct_answer"]
                            if deduction:
                                quiz_feedback = f"Incorrect. The correct answer was {correct_answer}. Deducted {deduction} points"
                            else:
                                quiz_feedback = f"Incorrect. The correct answer was {correct_answer}. Score stays at 0"
                            quiz_phase = "retry_result"
                        queue_question_generation(quiz_difficulty)
                    quiz_selected_option = row * 2 + column
                elif quiz_phase == "error" and event.key in (pygame.K_r, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    with question_cache_lock:
                        question_generation_errors.pop(quiz_difficulty, None)
                    quiz_phase = "loading"
                    queue_question_generation(quiz_difficulty)
                elif quiz_phase == "retry_result" and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    quiz_phase = "difficulty"
                    quiz_difficulty = ""
                    quiz_question = None
                    quiz_selected_option = 0
                    quiz_feedback = ""
                elif quiz_phase == "result" and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    close_quiz()
            # Number keys are direct level selectors. Each branch sets up the
            # selected map and resets the puzzle state needed for that area.
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_1:
                level = 1
                maze = MAZE
                player_row = START_ROW
                player_column = START_COLUMN
                pygame.display.set_caption(f"Arcade Maze - Level {level}")
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_2:
                level = 2
                maze = generate_new_maze()
                player_row = START_ROW
                player_column = START_COLUMN
                level_two_started_at = pygame.time.get_ticks()
                pygame.display.set_caption(f"Arcade Maze - Level {level}")
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_3:
                level = 3
                maze = LEVEL_THREE_MAZE.copy()
                player_row = LEVEL_THREE_START_ROW
                player_column = LEVEL_THREE_START_COLUMN
                level_three_started_at = pygame.time.get_ticks()
                player_facing = (-1, 0)
                buttons = [dict(button, pressed=False) for button in LEVEL_THREE_BUTTONS]
                gate_slide_started_at = None
                pygame.display.set_caption(f"Arcade Maze - Level {level}")
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_4:
                level = 4
                maze = LEVEL_FOUR_MAZE.copy()
                player_row = START_ROW
                player_column = START_COLUMN
                level_four_started_at = pygame.time.get_ticks()
                player_facing = (-1, 0)
                buttons = []
                gate_slide_started_at = None
                torches = list(LEVEL_FOUR_TORCHES)
                carrying_torch = False
                lit_pillars = set()
                section_exit_armed = False
                level_four_boulder_started_at = None
                pygame.display.set_caption(f"Arcade Maze - Level {level}")
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_5:
                level = 5
                maze = LEVEL_FIVE_MAZE.copy()
                player_row = LEVEL_FIVE_START_ROW
                player_column = LEVEL_FIVE_START_COLUMN
                level_five_started_at = pygame.time.get_ticks()
                player_facing = (-1, 0)
                buttons = []
                torches = []
                carrying_torch = False
                lit_pillars = set()
                section_exit_armed = False
                boulder_started_at = None
                upper_left_boulder_started_at = None
                level_four_boulder_started_at = None
                axes_started_at = None
                pygame.display.set_caption(f"Arcade Maze - Level {level}")
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_6, pygame.K_7, pygame.K_8):
                # 6 opens West, 7 opens North, and 8 opens East. The internal
                # section IDs stay linked to their matching relic and return tile.
                level = {
                    pygame.K_6: 7,
                    pygame.K_7: 6,
                    pygame.K_8: 8,
                }[event.key]
                section = LEVEL_FIVE_SECTIONS_BY_LEVEL[level]
                maze = section["maze"].copy()
                player_row, player_column = LEVEL_FIVE_SECTION_START
                player_facing = (-1, 0)
                buttons = []
                torches = []
                carrying_torch = False
                lit_pillars = set()
                section_exit_armed = False
                east_arrows = []
                east_arrows_last_fired_at = None
                east_arrows_last_updated_at = None
                pygame.display.set_caption(f"Arcade Maze - Level 5: {section['name']}")
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_e:
                # E works from any orthogonally neighboring tile, so the player
                # does not need to turn toward an object first.
                player_position = (player_row, player_column)
                if (
                    level == 5
                    and carrying_cave_artifact is not None
                ):
                    rock = next(
                        (
                            tile for tile in LEVEL_FIVE_ROCKS
                            if tiles_are_adjacent(player_position, tile)
                            and tile not in placed_cave_artifacts.values()
                        ),
                        None,
                    )
                    if rock is not None:
                        placed_cave_artifacts[carrying_cave_artifact] = rock
                        carrying_cave_artifact = None
                elif level == 3:
                    for button in buttons:
                        if (
                            not button["pressed"]
                            and tiles_are_adjacent(player_position, button["wall"])
                        ):
                            button["pressed"] = True
                            if all(item["pressed"] for item in buttons) and gate_slide_started_at is None:
                                gate_slide_started_at = pygame.time.get_ticks()
                            break
                elif level == 4:
                    if carrying_torch:
                        pillar = next(
                            (
                                tile for tile in LEVEL_FOUR_PILLARS
                                if tiles_are_adjacent(player_position, tile)
                                and tile not in lit_pillars
                            ),
                            None,
                        )
                        if pillar is not None:
                            lit_pillars.add(pillar)
                            carrying_torch = False
                    else:
                        torch = next(
                            (item for item in torches if tiles_are_adjacent(player_position, item[:2])),
                            None,
                        )
                        if torch is not None:
                            torches.remove(torch)
                            carrying_torch = True
            elif event.type == pygame.KEYDOWN and event.key in movement:
                # Movement is tile-based; puzzle gates are passable only after
                # their opening animation has completed.
                row_step, column_step = movement[event.key]
                player_facing = (row_step, column_step)
                next_row = player_row + row_step
                next_column = player_column + column_step
                in_bounds = 0 <= next_row < len(maze) and 0 <= next_column < len(maze[next_row])
                destination = maze[next_row][next_column] if in_bounds else "#"
                gate_is_open = (
                    level == 3
                    and gate_slide_started_at is not None
                    and pygame.time.get_ticks() - gate_slide_started_at >= GATE_SLIDE_DURATION
                )
                pillar_blocked = level == 4 and (next_row, next_column) in LEVEL_FOUR_PILLARS
                rock_blocked = level == 5 and (next_row, next_column) in LEVEL_FIVE_ROCKS
                level_four_exit_unlocked = (
                    level == 4 and len(lit_pillars) == len(LEVEL_FOUR_PILLARS)
                )
                if (
                    (destination != "#" and not pillar_blocked and not rock_blocked)
                    or ((next_row, next_column) == GATE_TILE and gate_is_open)
                ):
                    previous_position = (player_row, player_column)
                    player_row = next_row
                    player_column = next_column
                    last_move_at = pygame.time.get_ticks()
                    # Only successful moves can start a trap or collect a relic.
                    if (
                        level == 8
                        and (player_row, player_column) == LEVEL_FIVE_EAST_ARROW_PRESSURE_PLATE_TILE
                        and east_arrows_last_fired_at is None
                    ):
                        east_arrows_last_updated_at = pygame.time.get_ticks()
                        east_arrows_last_fired_at = (
                            east_arrows_last_updated_at - LEVEL_FIVE_EAST_ARROW_INTERVAL_MS
                        )
                    elif (
                        level == 4
                        and (player_row, player_column) == LEVEL_FOUR_PRESSURE_PLATE_TILE
                        and level_four_boulder_started_at is None
                    ):
                        level_four_boulder_started_at = pygame.time.get_ticks()
                    elif (
                        level == 5
                        and (player_row, player_column) == LEVEL_FIVE_PRESSURE_PLATE_TILE
                        and boulder_started_at is None
                    ):
                        boulder_started_at = pygame.time.get_ticks()
                    elif (
                        level == 5
                        and (player_row, player_column) == LEVEL_FIVE_UPPER_LEFT_PRESSURE_PLATE_TILE
                        and upper_left_boulder_started_at is None
                    ):
                        upper_left_boulder_started_at = pygame.time.get_ticks()
                    if (
                        level == 5
                        and (player_row, player_column) == LEVEL_FIVE_AXE_PRESSURE_PLATE_TILE
                        and axes_started_at is None
                    ):
                        axes_started_at = pygame.time.get_ticks()
                    if carrying_cave_artifact is None:
                        if (
                            level == 7
                            and (player_row, player_column) == WEST_CAVE_ARTIFACT_TILE
                            and "west" not in placed_cave_artifacts
                        ):
                            carrying_cave_artifact = "west"
                        elif (
                            level == 6
                            and (player_row, player_column) == NORTH_CAVE_ARTIFACT_TILE
                            and "north" not in placed_cave_artifacts
                        ):
                            carrying_cave_artifact = "north"
                        elif (
                            level == 8
                            and (player_row, player_column) == EAST_CAVE_ARTIFACT_TILE
                            and "east" not in placed_cave_artifacts
                        ):
                            carrying_cave_artifact = "east"
                    if (
                        level == 5
                        and (player_row, player_column) == (LEVEL_FIVE_EXIT_ROW, LEVEL_FIVE_EXIT_COLUMN)
                        and len(placed_cave_artifacts) == len(LEVEL_FIVE_ROCKS)
                    ):
                        elapsed_ms = (
                            pygame.time.get_ticks() - level_five_started_at
                            if level_five_started_at is not None else 0
                        )
                        speed_bonus = 100 if elapsed_ms <= 105_000 else 50 if elapsed_ms < 135_000 else 25
                        score += speed_bonus
                        game_finished = True
                        begin_level_transition(
                            "Game Finished!",
                            quiz_reason=f"Level 5 complete — {speed_bonus} speed bonus points",
                        )
                    # Exit tiles load the next map and use a short transition
                    # animation so the level change is clear to the player.
                    elif (player_row, player_column) == (EXIT_ROW, EXIT_COLUMN) and level == 1:
                        elapsed_seconds = (
                            (pygame.time.get_ticks() - level_one_started_at) / 1000
                            if level_one_started_at is not None else 0
                        )
                        speed_bonus = 100 if elapsed_seconds <= 15 else 50 if elapsed_seconds <= 30 else 25
                        score += speed_bonus
                        level = 2
                        maze = generate_new_maze()
                        player_row = START_ROW
                        player_column = START_COLUMN
                        level_two_started_at = None
                        pygame.display.set_caption(f"Arcade Maze - Level {level}")
                        begin_level_transition(
                            f"Level {level}",
                            quiz_reason=f"Level 1 complete — {speed_bonus} speed bonus points",
                        )
                    elif (player_row, player_column) == (EXIT_ROW, LEVEL_TWO_EXIT_COLUMN) and level == 2:
                        elapsed_seconds = (
                            (pygame.time.get_ticks() - level_two_started_at) / 1000
                            if level_two_started_at is not None else 0
                        )
                        speed_bonus = 100 if elapsed_seconds <= 15 else 50 if elapsed_seconds <= 30 else 25
                        score += speed_bonus
                        level = 3
                        maze = LEVEL_THREE_MAZE.copy()
                        player_row = LEVEL_THREE_START_ROW
                        player_column = LEVEL_THREE_START_COLUMN
                        level_three_started_at = None
                        player_facing = (-1, 0)
                        buttons = [dict(button, pressed=False) for button in LEVEL_THREE_BUTTONS]
                        gate_slide_started_at = None
                        pygame.display.set_caption(f"Arcade Maze - Level {level}")
                        begin_level_transition(
                            f"Level {level}",
                            quiz_reason=f"Level 2 complete — {speed_bonus} speed bonus points",
                        )
                    elif (player_row, player_column) == (EXIT_ROW, EXIT_COLUMN) and level == 3:
                        elapsed_seconds = (
                            (pygame.time.get_ticks() - level_three_started_at) / 1000
                            if level_three_started_at is not None else 0
                        )
                        speed_bonus = 100 if elapsed_seconds <= 35 else 50 if elapsed_seconds <= 60 else 25
                        score += speed_bonus
                        level = 4
                        maze = LEVEL_FOUR_MAZE.copy()
                        player_row = START_ROW
                        player_column = START_COLUMN
                        level_four_started_at = None
                        player_facing = (-1, 0)
                        buttons = []
                        gate_slide_started_at = None
                        torches = list(LEVEL_FOUR_TORCHES)
                        carrying_torch = False
                        lit_pillars = set()
                        level_four_boulder_started_at = None
                        pygame.display.set_caption(f"Arcade Maze - Level {level}")
                        begin_level_transition(
                            f"Level {level}",
                            quiz_reason=f"Level 3 complete — {speed_bonus} speed bonus points",
                        )
                    elif (
                        (player_row, player_column) == LEVEL_FOUR_EXIT_TILE
                        and level == 4
                        and len(lit_pillars) == len(LEVEL_FOUR_PILLARS)
                    ):
                        elapsed_seconds = (
                            (pygame.time.get_ticks() - level_four_started_at) / 1000
                            if level_four_started_at is not None else 0
                        )
                        speed_bonus = 100 if elapsed_seconds <= 35 else 50 if elapsed_seconds <= 60 else 25
                        score += speed_bonus
                        level = 5
                        maze = LEVEL_FIVE_MAZE.copy()
                        player_row = LEVEL_FIVE_START_ROW
                        player_column = LEVEL_FIVE_START_COLUMN
                        level_five_started_at = None
                        player_facing = (-1, 0)
                        torches = []
                        carrying_torch = False
                        lit_pillars = set()
                        section_exit_armed = False
                        boulder_started_at = None
                        upper_left_boulder_started_at = None
                        level_four_boulder_started_at = None
                        axes_started_at = None
                        pygame.display.set_caption(f"Arcade Maze - Level {level}")
                        begin_level_transition(
                            f"Level {level}",
                            quiz_reason=f"Level 4 complete — {speed_bonus} speed bonus points",
                        )
                    elif level == 5 and (player_row, player_column) in LEVEL_FIVE_SECTIONS:
                        section = LEVEL_FIVE_SECTIONS[(player_row, player_column)]
                        level = section["level"]
                        maze = section["maze"].copy()
                        player_row, player_column = LEVEL_FIVE_SECTION_START
                        player_facing = (-1, 0)
                        buttons = []
                        torches = []
                        carrying_torch = False
                        lit_pillars = set()
                        section_exit_armed = False
                        east_arrows = []
                        east_arrows_last_fired_at = None
                        east_arrows_last_updated_at = None
                        pygame.display.set_caption(f"Arcade Maze - Level 5: {section['name']}")
                        begin_level_transition(
                            f"Level 5: {section['name']}"
                        )
                    elif level in LEVEL_FIVE_SECTIONS_BY_LEVEL:
                        section = LEVEL_FIVE_SECTIONS_BY_LEVEL[level]
                        if previous_position == LEVEL_FIVE_SECTION_START:
                            section_exit_armed = True
                        elif (
                            (player_row, player_column) == LEVEL_FIVE_SECTION_START
                            and section_exit_armed
                        ):
                            level = 5
                            maze = LEVEL_FIVE_MAZE.copy()
                            east_arrows = []
                            east_arrows_last_fired_at = None
                            east_arrows_last_updated_at = None
                            player_row, player_column = section["return"]
                            section_exit_armed = False
                            if player_row == 0:
                                player_facing = (1, 0)
                            elif player_row == len(maze) - 1:
                                player_facing = (-1, 0)
                            elif player_column == 0:
                                player_facing = (0, 1)
                            else:
                                player_facing = (0, -1)
                            pygame.display.set_caption(f"Arcade Maze - Level {level}")
                            begin_level_transition("Level 5")

        # East Cave arrows spawn on a timer, travel through the corridor, and
        # reset Level 5 if any arrow overlaps the player.
        if (
            level == 8
            and quiz_phase is None
            and death_animation_type is None
            and level_transition_started_at is None
            and east_arrows_last_fired_at is not None
        ):
            now = pygame.time.get_ticks()
            while now - east_arrows_last_fired_at >= LEVEL_FIVE_EAST_ARROW_INTERVAL_MS:
                east_arrows_last_fired_at += LEVEL_FIVE_EAST_ARROW_INTERVAL_MS
                for row, column, direction in LEVEL_FIVE_EAST_ARROW_DISPENSERS:
                    east_arrows.append({
                        "x": (column + 1) * CELL_SIZE if direction > 0 else column * CELL_SIZE,
                        "y": row * CELL_SIZE + CELL_SIZE // 2,
                        "direction": direction,
                    })

            elapsed_seconds = (now - east_arrows_last_updated_at) / 1000
            east_arrows_last_updated_at = now
            for arrow in east_arrows:
                arrow["x"] += arrow["direction"] * LEVEL_FIVE_EAST_ARROW_SPEED * elapsed_seconds
            east_arrows = [
                arrow for arrow in east_arrows
                if 11 * CELL_SIZE <= arrow["x"] <= 15 * CELL_SIZE
            ]

            player_x = player_column * CELL_SIZE + CELL_SIZE // 2
            player_y = player_row * CELL_SIZE + CELL_SIZE // 2
            if any(
                abs(arrow["x"] - player_x) <= CELL_SIZE * 0.8
                and abs(arrow["y"] - player_y) <= CELL_SIZE * 0.48
                for arrow in east_arrows
            ):
                start_death_animation()

        # Active boulders and swinging axes are checked for collisions each frame.
        if level in (4, 5) and not game_finished and quiz_phase is None and death_animation_type is None:
            active_boulders = (
                ((LEVEL_FOUR_BOULDER_PATH, level_four_boulder_started_at, LEVEL_FOUR_BOULDER_SPEED),)
                if level == 4 else
                (
                    (LEVEL_FIVE_BOULDER_PATH, boulder_started_at, LEVEL_FIVE_BOULDER_SPEED),
                    (LEVEL_FIVE_UPPER_LEFT_BOULDER_PATH, upper_left_boulder_started_at, LEVEL_FIVE_BOULDER_SPEED),
                )
            )
            player_x = player_column * CELL_SIZE + CELL_SIZE // 2
            player_y = player_row * CELL_SIZE + CELL_SIZE // 2
            collision_distance = CELL_SIZE * 0.72
            for path, started_at, speed in active_boulders:
                if started_at is None:
                    continue
                boulder_position = get_boulder_position(
                    path, pygame.time.get_ticks() - started_at, speed
                )
                if boulder_position is None:
                    continue
                boulder_x, boulder_y = boulder_position
                if (boulder_x - player_x) ** 2 + (boulder_y - player_y) ** 2 <= collision_distance ** 2:
                    start_death_animation()
                    break
            if axes_started_at is not None:
                animation_time = pygame.time.get_ticks() / 1000
                if any(
                    swinging_axe_hits_player(
                        row, column, phase, animation_time, player_x, player_y
                    )
                    for row, column, phase in LEVEL_FIVE_SWINGING_AXES
                    if player_row == row
                ):
                    start_death_animation()

        # Side caves use a smaller render surface so each complete map fits on screen.
        small_section = level in LEVEL_FIVE_SECTIONS_BY_LEVEL
        section_view_size = (len(maze[0]) * CELL_SIZE, len(maze) * CELL_SIZE) if small_section else None
        maze_surface = small_section_surface if small_section else screen
        level_five_portal_tiles = tuple(LEVEL_FIVE_SECTIONS) if level == 5 else ()
        if level == 5 and len(placed_cave_artifacts) == len(LEVEL_FIVE_ROCKS):
            level_five_portal_tiles += ((LEVEL_FIVE_EXIT_ROW, LEVEL_FIVE_EXIT_COLUMN),)
        if level == 4 and len(lit_pillars) == len(LEVEL_FOUR_PILLARS):
            level_five_portal_tiles += (LEVEL_FOUR_EXIT_TILE,)
        # The shared renderer receives only the props and effects for this level.
        draw_maze(
            maze_surface,
            maze,
            player_row,
            player_column,
            buttons if level == 3 else (),
            gate_slide_started_at if level == 3 else None,
            level_three=level in (3, 4),
            floor_texture=(
                floor_texture if level in (3, 4) else
                warm_cave_section_floor_texture if small_section else
                warm_cave_floor_texture if level == 5 else
                original_cave_floor_texture if level in (1, 2) else None
            ),
            pillars=LEVEL_FOUR_PILLARS if level == 4 else (),
            torches=torches if level == 4 else (),
            carried_torch=carrying_torch if level == 4 else False,
            lit_pillars=lit_pillars if level == 4 else (),
            animation_time=(
                death_animation_world_time if death_animation_world_time is not None
                else pygame.time.get_ticks()
            ) / 1000,
            player_name=player_name if not name_entry and death_animation_type is None else "",
            player_label_font=player_label_font,
            walking=pygame.time.get_ticks() - last_move_at < 220,
            warm_cave=level == 5 or small_section,
            classic_cave=level in (1, 2),
            viewport_size=section_view_size,
            section_exit_tile=LEVEL_FIVE_SECTION_START if small_section and section_exit_armed else None,
            rocks=LEVEL_FIVE_ROCKS if level == 5 else (),
            artifact_tile=(
                WEST_CAVE_ARTIFACT_TILE
                if level == 7 and carrying_cave_artifact != "west" and "west" not in placed_cave_artifacts
                else None
            ),
            north_artifact_tile=(
                NORTH_CAVE_ARTIFACT_TILE
                if level == 6 and carrying_cave_artifact != "north" and "north" not in placed_cave_artifacts
                else None
            ),
            east_artifact_tile=(
                EAST_CAVE_ARTIFACT_TILE
                if level == 8 and carrying_cave_artifact != "east" and "east" not in placed_cave_artifacts
                else None
            ),
            section_portal_tiles=level_five_portal_tiles,
            carrying_artifact=carrying_cave_artifact,
            placed_artifacts=tuple(placed_cave_artifacts.items()) if level == 5 else (),
            pressure_plate_tile=LEVEL_FIVE_PRESSURE_PLATE_TILE if level == 5 else None,
            pressure_plate_pressed=boulder_started_at is not None if level == 5 else False,
            boulder_path=LEVEL_FIVE_BOULDER_PATH if level == 5 else (),
            boulder_started_at=boulder_started_at if level == 5 else None,
            axe_pressure_plate_tile=LEVEL_FIVE_AXE_PRESSURE_PLATE_TILE if level == 5 else None,
            axes_started_at=axes_started_at if level == 5 else None,
            swinging_axes=LEVEL_FIVE_SWINGING_AXES if level == 5 else (),
            arrow_dispenser_tiles=LEVEL_FIVE_EAST_ARROW_DISPENSERS if level == 8 else (),
            arrows=tuple(
                (arrow["x"], arrow["y"], arrow["direction"])
                for arrow in east_arrows
            ) if level == 8 else (),
            arrow_pressure_plate_tile=LEVEL_FIVE_EAST_ARROW_PRESSURE_PLATE_TILE if level == 8 else None,
            arrow_pressure_plate_pressed=east_arrows_last_fired_at is not None if level == 8 else False,
            draw_player=death_animation_type is None,
            additional_boulder_traps=(
                ({
                    "plate": LEVEL_FOUR_PRESSURE_PLATE_TILE,
                    "path": LEVEL_FOUR_BOULDER_PATH,
                    "started_at": level_four_boulder_started_at,
                    "speed": LEVEL_FOUR_BOULDER_SPEED,
                    "rubble": LEVEL_FOUR_BOULDER_RUBBLE_TILE,
                },) if level == 4 else ()
            ) + (
                ({
                    "plate": LEVEL_FIVE_UPPER_LEFT_PRESSURE_PLATE_TILE,
                    "path": LEVEL_FIVE_UPPER_LEFT_BOULDER_PATH,
                    "started_at": upper_left_boulder_started_at,
                    "speed": LEVEL_FIVE_BOULDER_SPEED,
                    "rubble": LEVEL_FIVE_UPPER_LEFT_BOULDER_RUBBLE_TILE,
                },) if level == 5 else ()
            ),
        )
        if death_animation_type is not None and death_animation_started_at is not None:
            maze_offset_x = (maze_surface.get_width() - len(maze[0]) * CELL_SIZE) // 2
            maze_offset_y = (maze_surface.get_height() - len(maze) * CELL_SIZE) // 2
            death_animation_time = (
                death_animation_world_time if death_animation_world_time is not None
                else pygame.time.get_ticks()
            ) / 1000
            character_idle_bob = int(death_animation_time * 2) % 2
            draw_death_animation(
                maze_surface,
                pygame.time.get_ticks() - death_animation_started_at,
                (
                    maze_offset_x + player_column * CELL_SIZE + 1,
                    maze_offset_y + player_row * CELL_SIZE + 2 - character_idle_bob,
                ),
                death_animation_time,
            )
        if small_section:
            screen.blit(pygame.transform.scale(maze_surface, screen.get_size()), (0, 0))

        if level_transition_started_at is not None:
            transition_elapsed = pygame.time.get_ticks() - level_transition_started_at
            cover_end = LEVEL_TRANSITION_COVER_DURATION
            hold_end = cover_end + LEVEL_TRANSITION_HOLD_DURATION
            reveal_end = hold_end + LEVEL_TRANSITION_REVEAL_DURATION
            screen_width, screen_height = screen.get_size()
            if transition_elapsed < cover_end:
                progress = max(0.0, min(1.0, transition_elapsed / cover_end))
                eased_progress = progress * progress * (3 - 2 * progress)
                fade = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                fade.fill((0, 0, 0, int(255 * eased_progress)))
                screen.blit(fade, (0, 0))
            elif transition_elapsed < hold_end:
                screen.fill((0, 0, 0))
                hold_progress = (transition_elapsed - cover_end) / LEVEL_TRANSITION_HOLD_DURATION
                title_progress = min(1.0, hold_progress * 5, (1.0 - hold_progress) * 5)
                title_alpha = int(255 * title_progress * title_progress * (3 - 2 * title_progress))
                title_surface = transition_font.render(level_transition_title, True, (255, 211, 126))
                title_surface.set_alpha(title_alpha)
                title_rect = title_surface.get_rect(center=(screen_width // 2, screen_height // 2))
                shadow_surface = transition_font.render(level_transition_title, True, (77, 51, 35))
                shadow_surface.set_alpha(title_alpha)
                screen.blit(shadow_surface, title_rect.move(2, 3))
                screen.blit(title_surface, title_rect)
            elif transition_elapsed < reveal_end:
                reveal_elapsed = transition_elapsed - hold_end
                progress = max(0.0, min(1.0, reveal_elapsed / LEVEL_TRANSITION_REVEAL_DURATION))
                eased_progress = progress * progress * (3 - 2 * progress)
                fade = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                fade.fill((0, 0, 0, int(255 * (1.0 - eased_progress))))
                screen.blit(fade, (0, 0))
            else:
                level_transition_started_at = None
                if pending_quiz_reason is not None:
                    reason = pending_quiz_reason
                    pending_quiz_reason = None
                    begin_quiz(reason)

        if game_finished and level_transition_started_at is None and quiz_phase is None:
            screen_width, screen_height = screen.get_size()
            screen.fill((0, 0, 0))
            title_surface = transition_font.render("Game Finished!", True, (255, 211, 126))
            title_rect = title_surface.get_rect(center=(screen_width // 2, screen_height // 2))
            shadow_surface = transition_font.render("Game Finished!", True, (77, 51, 35))
            screen.blit(shadow_surface, title_rect.move(2, 3))
            screen.blit(title_surface, title_rect)

        if quiz_phase is not None:
            screen_width, screen_height = screen.get_size()
            overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            overlay.fill((5, 5, 7, 205))
            screen.blit(overlay, (0, 0))
            panel_width = min(680, screen_width - 48)
            panel_height = min(470, screen_height - 32)
            if quiz_phase == "question" and quiz_question:
                estimate_card_width = (panel_width - 56 - 14) // 2
                estimate_question_font = pygame.font.Font(None, 30)
                estimate_option_font = pygame.font.Font(None, 28)
                estimate_question_lines = wrap_text_lines(
                    quiz_question["question"], estimate_question_font, panel_width - 72
                )
                estimate_option_lines = [
                    wrap_text_lines(
                        f"{letter}. {quiz_question['options'][letter]}",
                        estimate_option_font,
                        estimate_card_width - 22,
                    )
                    for letter in "ABCD"
                ]
                estimate_question_height = len(estimate_question_lines) * estimate_question_font.get_linesize()
                estimate_row_heights = [
                    max(len(estimate_option_lines[index]) for index in row_indices)
                    * estimate_option_font.get_linesize()
                    + 22
                    for row_indices in ((0, 1), (2, 3))
                ]
                estimated_content_height = (
                    estimate_question_height + 15 + sum(estimate_row_heights) + 12
                )
                panel_height = min(
                    screen_height - 32,
                    max(360, 108 + estimated_content_height + 54),
                )
            panel = pygame.Rect(
                (screen_width - panel_width) // 2,
                (screen_height - panel_height) // 2,
                panel_width,
                panel_height,
            )
            pygame.draw.rect(screen, (26, 24, 24), panel, border_radius=12)
            pygame.draw.rect(screen, (173, 121, 69), panel, 3, border_radius=12)
            heading = quiz_title_font.render(quiz_reason, True, (255, 211, 126))
            screen.blit(heading, heading.get_rect(center=(panel.centerx, panel.top + 45)))

            if quiz_phase == "difficulty":
                difficulty_title = quiz_body_font.render("Choose a question difficulty", True, (225, 210, 188))
                screen.blit(
                    difficulty_title,
                    difficulty_title.get_rect(center=(panel.centerx, panel.top + 91)),
                )
                difficulty_options = (
                    ("EASY", "Safety basics"),
                    ("MEDIUM", "Everyday situations"),
                    ("HARD", "Challenge"),
                )
                difficulty_fills = ((78, 56, 45), (69, 53, 46), (82, 58, 43))
                difficulty_width = panel.width - 110
                difficulty_height = 70
                difficulty_x = panel.left + 55
                difficulty_start_y = panel.top + 132
                difficulty_gap = 13
                for index, (label, description) in enumerate(difficulty_options):
                    button = pygame.Rect(
                        difficulty_x,
                        difficulty_start_y + index * (difficulty_height + difficulty_gap),
                        difficulty_width,
                        difficulty_height,
                    )
                    pygame.draw.rect(screen, (17, 14, 14), button.move(0, 5), border_radius=5)
                    pygame.draw.rect(screen, difficulty_fills[index], button, border_radius=5)
                    pygame.draw.rect(screen, (112, 79, 59), button, 2, border_radius=5)
                    pygame.draw.line(
                        screen,
                        (143, 104, 75),
                        (button.left + 8, button.top + 4),
                        (button.right - 8, button.top + 4),
                        2,
                    )
                    if index == quiz_selected_option:
                        pygame.draw.rect(screen, (239, 188, 111), button, 3, border_radius=5)
                        pygame.draw.rect(screen, (255, 226, 179), button.inflate(-8, -8), 1, border_radius=4)
                    label_surface = quiz_body_font.render(label, True, (255, 218, 163))
                    detail_surface = pygame.font.Font(None, 24).render(description, True, (218, 203, 185))
                    screen.blit(label_surface, label_surface.get_rect(center=(button.centerx, button.centery - 9)))
                    screen.blit(detail_surface, detail_surface.get_rect(center=(button.centerx, button.centery + 20)))
                choice_hint = pygame.font.Font(None, 25).render("W A S D choose  ·  E confirm", True, (205, 190, 171))
                screen.blit(choice_hint, choice_hint.get_rect(center=(panel.centerx, panel.bottom - 23)))
                lines = []
            elif quiz_phase == "question" and quiz_question:
                difficulty_label = quiz_body_font.render(
                    f"{quiz_difficulty} question", True, (210, 198, 177)
                )
                screen.blit(
                    difficulty_label,
                    difficulty_label.get_rect(center=(panel.centerx, panel.top + 82)),
                )

                gap = 14
                card_width = (panel_width - 56 - gap) // 2
                card_x = (panel.left + 20, panel.left + 20 + card_width + gap)
                text_top = panel.top + 108
                content_bottom = panel.bottom - 54
                available_content_height = content_bottom - text_top

                # Find the largest readable font sizes that let the entire
                # prompt and all four options fit inside the modal.
                layout = None
                for question_size in range(30, 13, -1):
                    question_font = pygame.font.Font(None, question_size)
                    option_font = pygame.font.Font(None, max(14, question_size - 2))
                    question_lines = wrap_text_lines(
                        quiz_question["question"], question_font, panel_width - 72
                    )
                    option_lines_by_index = [
                        wrap_text_lines(
                            f"{letter}. {quiz_question['options'][letter]}",
                            option_font,
                            card_width - 22,
                        )
                        for letter in "ABCD"
                    ]
                    question_height = len(question_lines) * question_font.get_linesize()
                    row_heights = [
                        max(len(option_lines_by_index[index]) for index in row_indices)
                        * option_font.get_linesize()
                        + 22
                        for row_indices in ((0, 1), (2, 3))
                    ]
                    total_content_height = question_height + 15 + sum(row_heights) + 12
                    layout = (
                        question_font,
                        option_font,
                        question_lines,
                        option_lines_by_index,
                        row_heights,
                        question_height,
                    )
                    if total_content_height <= available_content_height:
                        break

                question_font, option_font, question_lines, option_lines_by_index, row_heights, question_height = layout
                for index, line in enumerate(question_lines):
                    rendered_question = question_font.render(line, True, (248, 244, 236))
                    screen.blit(
                        rendered_question,
                        rendered_question.get_rect(center=(panel.centerx, text_top + index * question_font.get_linesize() + question_font.get_linesize() // 2)),
                    )

                first_row_y = text_top + question_height + 15
                card_y = (first_row_y, first_row_y + row_heights[0] + 12)
                card_heights = (row_heights[0], row_heights[1])
                card_colors = ((78, 56, 45), (69, 53, 46), (82, 58, 43), (72, 51, 43))
                for index, letter in enumerate("ABCD"):
                    row, column = divmod(index, 2)
                    card = pygame.Rect(card_x[column], card_y[row], card_width, card_heights[row])
                    pygame.draw.rect(screen, (17, 14, 14), card.move(0, 5), border_radius=5)
                    pygame.draw.rect(screen, card_colors[index], card, border_radius=5)
                    pygame.draw.rect(screen, (112, 79, 59), card, 2, border_radius=5)
                    pygame.draw.line(
                        screen,
                        (143, 104, 75),
                        (card.left + 6, card.top + 4),
                        (card.right - 6, card.top + 4),
                        2,
                    )
                    pygame.draw.line(
                        screen,
                        (42, 32, 29),
                        (card.left + 6, card.bottom - 4),
                        (card.right - 6, card.bottom - 4),
                        2,
                    )
                    if index == quiz_selected_option:
                        pygame.draw.rect(screen, (239, 188, 111), card, 3, border_radius=5)
                        pygame.draw.rect(screen, (255, 226, 179), card.inflate(-8, -8), 1, border_radius=4)

                    option_lines = option_lines_by_index[index]
                    option_text_height = len(option_lines) * option_font.get_linesize()
                    option_text_top = card.centery - option_text_height // 2
                    for line_index, line in enumerate(option_lines):
                        rendered_option = option_font.render(line, True, (255, 255, 255))
                        screen.blit(
                            rendered_option,
                            rendered_option.get_rect(center=(card.centerx, option_text_top + line_index * option_font.get_linesize() + option_font.get_linesize() // 2)),
                        )

                answer_hint = quiz_body_font.render("W A S D move  ·  E select", True, (219, 201, 178))
                screen.blit(answer_hint, answer_hint.get_rect(center=(panel.centerx, panel.bottom - 26)))
                lines = []
            elif quiz_phase == "loading":
                lines = [f"Generating a {quiz_difficulty.lower()} question with Ollama...", "Please wait"]
            elif quiz_phase == "error":
                lines = [
                    "Could not generate a question.",
                    question_generation_errors.get(quiz_difficulty, "Ollama did not return a question."),
                    "Press R or ENTER to retry",
                ]
            elif quiz_phase in ("result", "retry_result"):
                lines = [quiz_feedback, f"Current score: {score}"]
                if quiz_question and quiz_question.get("explanation"):
                    lines.append(f"Why: {quiz_question['explanation']}")
                if quiz_phase == "retry_result":
                    lines.append("Press ENTER to choose a difficulty and try again")
                else:
                    lines.append("Press ENTER to continue")
            else:
                lines = []

            # Wrap status and result text to fit the modal instead of clipping long
            # questions or explanations at the edges of the game window.
            wrapped_lines = []
            max_text_width = panel_width - 56
            for line in lines:
                words = str(line).split()
                current_line = ""
                for word in words:
                    candidate = f"{current_line} {word}".strip()
                    if current_line and quiz_body_font.size(candidate)[0] > max_text_width:
                        wrapped_lines.append(current_line)
                        current_line = word
                    else:
                        current_line = candidate
                if current_line:
                    wrapped_lines.append(current_line)

            line_y = panel.top + 96
            line_spacing = 31
            available_bottom = panel.bottom - 24
            for line in wrapped_lines:
                if line_y + line_spacing > available_bottom:
                    break
                rendered_line = quiz_body_font.render(line, True, (238, 232, 219))
                screen.blit(rendered_line, rendered_line.get_rect(center=(panel.centerx, line_y)))
                line_y += line_spacing

        display_surface.blit(backdrop, (0, 0))
        scaled_screen = pygame.transform.scale(screen, fit_size)
        display_surface.blit(scaled_screen, scaled_screen.get_rect(center=display_surface.get_rect().center))
        if name_entry:
            ui_scale = name_ui_scale
            origin_x = round((display_width - 582 * ui_scale) / 2)
            origin_y = round((display_height - 292 * ui_scale) / 2)
            point = lambda x, y: (origin_x + round(x * ui_scale), origin_y + round(y * ui_scale))
            scaled = lambda value: max(1, round(value * ui_scale))

            display_surface.fill((15, 15, 16))
            edge_color = (58, 59, 60)
            pygame.draw.line(display_surface, edge_color, point(0, 2), point(581, 2), scaled(1))
            pygame.draw.line(display_surface, edge_color, point(0, 290), point(581, 290), scaled(1))
            pygame.draw.line(display_surface, (31, 31, 32), point(1, 2), point(1, 290), scaled(1))
            pygame.draw.line(display_surface, (31, 31, 32), point(580, 2), point(580, 290), scaled(1))
            glow_layer = pygame.Surface(display_surface.get_size(), pygame.SRCALPHA)
            for glow_x in (35, 547):
                for radius, alpha in ((46, 8), (36, 12), (27, 18), (19, 26), (11, 38)):
                    pygame.draw.circle(glow_layer, (226, 126, 54, alpha), point(glow_x, 29), scaled(radius))
            display_surface.blit(glow_layer, (0, 0))

            outer = pygame.Rect(*point(28, 28), scaled(526), scaled(238))
            pygame.draw.rect(display_surface, (155, 99, 52), outer, border_radius=scaled(11))
            inner = outer.inflate(-scaled(4), -scaled(4))
            pygame.draw.rect(display_surface, (48, 35, 25), inner, border_radius=scaled(9))
            panel = inner.inflate(-scaled(6), -scaled(6))
            pygame.draw.rect(display_surface, (26, 24, 22), panel, border_radius=scaled(7))
            pygame.draw.rect(display_surface, (76, 54, 37), panel, width=scaled(1), border_radius=scaled(7))

            title_surface = name_title_font.render("ENTER YOUR NAME", True, (255, 199, 101))
            display_surface.blit(title_surface, title_surface.get_rect(center=point(291, 59)))
            subtitle_surface = name_subtitle_font.render("Your adventure begins here", True, (239, 223, 203))
            display_surface.blit(subtitle_surface, subtitle_surface.get_rect(center=point(291, 81)))

            name_box = pygame.Rect(*point(162, 102), scaled(260), scaled(36))
            pygame.draw.rect(display_surface, (10, 10, 10), name_box, border_radius=scaled(5))
            pygame.draw.rect(display_surface, (147, 96, 49), name_box, width=scaled(1), border_radius=scaled(5))
            cursor = "_"
            displayed_name = player_name + cursor if player_name else "Enter name here"
            name_surface = name_entry_font.render(displayed_name, True, (239, 222, 196))
            display_surface.blit(name_surface, name_surface.get_rect(midleft=(name_box.x + scaled(9), name_box.centery)))

            for row_index, row in enumerate(name_keyboard):
                for column_index, label in enumerate(row):
                    if row_index == 0:
                        x, y, width, height = 142 + column_index * 30, 150, 25, 24
                    elif row_index == 1:
                        x, y, width, height = 142 + column_index * 30, 178, 25, 24
                    elif row_index == 2 and label in "XCVBNM":
                        x, y, width, height = 142 + column_index * 30, 206, 25, 24
                    elif row_index == 2:
                        x, y, width, height = (324 if label == "SPACE" else 387), 206, (57 if label == "SPACE" else 54), 24
                    else:
                        x, y, width, height = 142, 234, 55, 23

                    selected = (row_index, column_index) == (keyboard_row, keyboard_column)
                    key_rect = pygame.Rect(*point(x, y), scaled(width), scaled(height))
                    fill = (246, 184, 83) if selected else (51, 42, 34)
                    edge = (255, 223, 161) if selected else (124, 89, 55)
                    pygame.draw.rect(display_surface, fill, key_rect, border_radius=scaled(4))
                    pygame.draw.rect(display_surface, edge, key_rect, width=scaled(1), border_radius=scaled(4))
                    key_surface = name_key_font.render(label, True, (49, 34, 19) if selected else (238, 222, 201))
                    display_surface.blit(key_surface, key_surface.get_rect(center=key_rect.center))
            hint_surface = name_hint_font.render("W A S D move · E select", True, (226, 205, 177))
            display_surface.blit(hint_surface, hint_surface.get_rect(center=point(291, 272)))
        elif how_to_play_screen:
            panel_scale = min(
                (fit_size[0] - 16) / how_to_play_panel.get_width(),
                (display_height - 24) / how_to_play_panel.get_height(),
            )
            panel_size = (
                round(how_to_play_panel.get_width() * panel_scale),
                round(how_to_play_panel.get_height() * panel_scale),
            )
            scaled_panel = pygame.transform.smoothscale(how_to_play_panel, panel_size)
            panel_rect = scaled_panel.get_rect(center=display_surface.get_rect().center)
            display_surface.blit(scaled_panel, panel_rect)

        if not name_entry:
            score_text = f"{player_name}  |  Score: {score}"
            score_font_size = score_hud_base_size
            if score_font_size not in score_font_cache:
                score_font_cache[score_font_size] = pygame.font.Font(None, score_font_size)
            score_hud_font = score_font_cache[score_font_size]
            score_surface = score_hud_font.render(score_text, True, (255, 225, 165))
            max_score_width = max(220, side_width - 42)
            while score_surface.get_width() + 30 > max_score_width and score_font_size > 20:
                score_font_size -= 1
                if score_font_size not in score_font_cache:
                    score_font_cache[score_font_size] = pygame.font.Font(None, score_font_size)
                score_hud_font = score_font_cache[score_font_size]
                score_surface = score_hud_font.render(score_text, True, (255, 225, 165))
            score_box = score_surface.get_rect(topleft=(26, 28)).inflate(30, 20)
            pygame.draw.rect(display_surface, (25, 20, 18), score_box, border_radius=7)
            pygame.draw.rect(display_surface, (143, 98, 57), score_box, width=3, border_radius=7)
            display_surface.blit(score_surface, score_surface.get_rect(center=score_box.center))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
