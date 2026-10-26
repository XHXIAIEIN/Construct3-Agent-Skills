# The game part of the platformer-generator fixture: make_fixtures.py writes it below the end marker of
# the arm's own build_project.py, in place of the coins game, so the helpers above it are that arm's.
# It runs only there, after the template's settings and helpers.


# --- the game ---------------------------------------------------------------------------
# A level that scrolls sideways: run right over the ground, jump its gaps, collect the gems, reach
# the goal. Pacing, then what build_all() calls: images, data files, object types, layouts, the sheet


# --- pacing ---------------------------------------------------------------------------
# One beat per camera zone of the level, ZONE units wide; gap is the hole in the ground the zone
# ends with, in units, measured with jump() where build_layouts() places it.
BEATS = [
    beat("intro", 0, ["run"], gap=0),
    beat("teach", 1, ["jump"], gap=3),
    beat("practice", 2, ["jump"], gap=5),
    beat("rest", 0, ["run"], holds="pickup", gap=0),
    beat("climax", 3, ["jump"], gap=7),
    beat("exit", 0, ["run"], gap=0),
]
ZONE = 30                                  # units of level a beat takes: half a screen
LEVEL_W = units(ZONE * len(BEATS))         # px; the layout scrolls over it, one screen high
GROUND_ROW = 28                            # the ground's top row; the player stands on it
GROUND_ROWS = 6                            # down past the viewport's bottom edge
GOAL_COLS = 4
# HUD groups: the level as a tag top left, the score top right, the controls bottom left, which dim
# once used (hints())
HUD = [[hud_tag("LevelTag", "Level · 01", longest="Level · 10")],
       hud_stat("ScoreLabel", "ScoreText", "SCORE", "top-right", longest="999"),
       hud_keys("KeyBox", "KeyText", "KeyVerb", [("Arrows", "run"), ("Up", "jump")])]


def build_files() -> None:
    """The game's data files. The level has none."""


def build_images() -> None:
    zone_image("Ground")
    zone_image("Goal", "canvas_alt", "reward")
    zone_image("KeyBox", None, "ink")
    art("player-default-000.png", "rect", SUBJECT, SUBJECT, "ink", "a small runner seen from the side")
    art("gem-default-000.png", "circle", SUBJECT, SUBJECT, "reward", "a blue gem")


def build_object_types() -> tuple[dict, dict, list]:
    types = {
        "Player": sprite_type("Player", [animation("Default", [drawn("player-default-000.png")])],
                              behaviors=[beh_def("Platform"), beh_def("scrollto", "ScrollTo")]),
        "Gem": sprite_type("Gem", [animation("Default", [drawn("gem-default-000.png")])]),
        "Ground": zone_type("Ground", behaviors=[beh_def("solid", "Solid")]),
        "Goal": zone_type("Goal"),
        "LevelTag": text_type("LevelTag"),
        "ScoreLabel": text_type("ScoreLabel"),
        "ScoreText": text_type("ScoreText"),
        "KeyBox": zone_type("KeyBox", behaviors=[beh_def("Tween")]),
        "KeyText": text_type("KeyText"),
        "KeyVerb": text_type("KeyVerb"),
        "Keyboard": single_global_type("Keyboard", "Keyboard", {}),
    }
    return types, {}, []


def build_layouts() -> dict[str, dict]:
    game = layout("Game", [
        layer("Background", transparent=False),
        layer("Game"),
        layer("UI", parallax=0),
    ], sheet="Game", width=LEVEL_W, height=VIEW_H)
    world_ = game["layers"][1]["instances"]
    # The ground, one piece from gap to gap, so no seam shows where two zones meet; a gem over every gap, one on
    # the rest
    col = start = 0
    for b in BEATS:
        if b["holds"] == "pickup":
            world_.append(shape_inst("Gem", "gem-default-000.png", col + ZONE // 2 - 1, GROUND_ROW - 3))
        col += ZONE
        if b["gap"]:
            jump(b["gap"])
            world_.append(zone("Ground", start, GROUND_ROW, col - b["gap"] - start, GROUND_ROWS, behaviors=dict(SOLID)))
            world_.append(shape_inst("Gem", "gem-default-000.png", col - b["gap"] + b["gap"] // 2 - 1, GROUND_ROW - 6))
            start = col
    world_.append(zone("Ground", start, GROUND_ROW, col - start, GROUND_ROWS, behaviors=dict(SOLID)))
    world_.append(zone("Goal", col - GOAL_COLS - 4, GROUND_ROW - 6, GOAL_COLS, 6))
    world_.append(shape_inst("Player", "player-default-000.png", 4, GROUND_ROW - SUBJECT // UNIT,
                             behaviors={**PLATFORM, "ScrollTo": SCROLL_TO["ScrollTo"]}))
    on_grid(world_, "layer Game")
    ui = game["layers"][2]["instances"]
    ui.extend(flat(HUD))
    no_overlap(ui)
    spaced(HUD)
    return {"Game": game}


# --- the event sheet -------------------------------------------------------------------
def module_setup() -> dict:
    return module("Setup", events=[
        event("Empty the score at the start of the level", [on_start()],
              [set_var("score", "0"), set_text("ScoreText", q("0"))]),
    ])


def module_pickups() -> dict:
    return module("Pickups", events=[
        event("A gem the player touches scores a point and goes",
              [cond("on-collision-with-another-object", "Player", {"object": "Gem"})],
              [call("AddScore", "1"), destroy("Gem")]),
    ])


def module_level() -> dict:
    return module("Level", events=[
        event("Start the level again when the player reaches the goal",
              [is_overlapping("Player", "Goal"), trigger_once()], [wait("1"), restart_layout()]),
        event("Start the level again when the player falls off the screen",
              [cond("compare-y", "Player", {"comparison": 4, "y-co-ordinate": str(VIEW_H)}), trigger_once()],
              [restart_layout()]),
    ])


def scoring() -> list:
    return [
        *procedure("Add points and show the score", func("AddScore", [
            add_var("score", "points"),
            set_text("ScoreText", "score"),
        ], params=[param("points", "number", 0)])),
    ]


def build_event_sheet() -> dict:
    events = [
        comment("Hills. Run right with the arrows, jump the gaps with Up, collect the gems and reach the goal.\n"
                "The camera follows the player; the HUD stays on its layer at parallax 0"),
        comment("Gameplay variables"),
        var("score", "number", 0, "Gems collected this run"),
        module_setup(),
        module_pickups(),
        *scoring(),
        module_level(),
        hints("KeyBox", [cond("on-any-key-pressed", "Keyboard")]),
    ]
    return {"name": "Game", "events": events, "sid": sid()}


if __name__ == "__main__":
    build_and_check()
