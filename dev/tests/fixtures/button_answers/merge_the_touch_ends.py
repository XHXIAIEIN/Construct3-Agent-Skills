# --- the game ---------------------------------------------------------------------------
# Pacing, then what build_all() calls: images, data files, object types, layouts, the event sheet


# --- pacing ---------------------------------------------------------------------------
# What the game asks of the player, a beat at a time: a camera zone of a level, or here a round.
# A beat has a type, an intensity from 0 to 3, the mechanics it asks for, and for a rest what it
# holds; other keys are the game's own, here the coins a round deals. pace() checks the curve.
BEATS = [
    beat("intro", 0, ["tap"], coins=1),
    beat("teach", 1, ["tap"], coins=3),
    beat("practice", 2, ["tap"], coins=6),
    beat("rest", 0, ["tap"], holds="pickup", coins=2),
    beat("climax", 3, ["tap"], coins=10),
    beat("exit", 0, ["tap"], coins=1),
]
# Board: COLS x ROWS slots, each a disc TOUCH wide that a coin fills, a unit apart
# A round deals cells (deal + i * STRIDE) mod CELLS; STRIDE shares no factor with CELLS, so no two
# coins land on one cell
COLS, ROWS = 5, 3
CELLS = COLS * ROWS
STRIDE = next(s for s in (7, 11, 13, 17, 19, 23) if math.gcd(s, CELLS) == 1)
PITCH = TOUCH + UNIT
BOARD_W, BOARD_H = COLS * PITCH - UNIT, ROWS * PITCH - UNIT
# The round's buttons: (object type, label), left to right
BUTTONS = [("Restart", "Restart"), ("Skip", "Skip")]
# HUD groups, built first so the board can be centred in the room they leave: the round as a tag
# top left, the score top right, the controls bottom left, which dim once used (hints())
HUD = [[hud_tag("RoundTag", "Round · 01 / 06", longest="Round · 10 / 10")],
       hud_stat("ScoreLabel", "ScoreText", "SCORE", "top-right", longest="999"),
       hud_keys("KeyBox", "KeyText", "KeyVerb", [("Tap", "collect")])]
PLAY_AREA = play_area(flat(HUD))
BOARD_LEFT, BOARD_TOP = centred(BOARD_W, BOARD_H, PLAY_AREA)
if max(b["coins"] for b in BEATS) > CELLS:
    sys.exit(f"BEATS deal up to {max(b['coins'] for b in BEATS)} coins and the board has {CELLS} slots; "
             f"widen COLS or ROWS")


def build_files() -> None:
    """The game's data files, written before the object types. For example
    record_table("CardTable", {"strike": {...}}), with nonworld_type("CardTable", "Arr") and
    nonworld_type("Cards", "Dictionary"), their nonworld_inst() in the layout that loads them,
    load_data_file("CardTable", "CardTable.json") first in that layout's On start, and
    *table_to_dictionary("CardTable", "Cards") among its sub-events.
    The stand-in has none."""


def build_images() -> None:
    zone_image("KeyBox", None, "ink")
    # Board slot: a coin-sized disc in canvas_alt and a unit of space, repeated by the Tiled
    # Background; a ring as thick as it is wide, so its edge is antialiased
    write_png("board.png", PITCH, PITCH, lambda x, y: (
        *rgb("canvas_alt"), round(255 * ring_cover(x, y, COIN_SIZE / 2, COIN_SIZE / 2, COIN_SIZE, COIN_SIZE))))
    art("coin-default-000.png", "circle", COIN_SIZE, COIN_SIZE, "reward", "a gold coin seen from the front")
    hit_frame("coin-default-000.png")
    # The coin's hover and pressed colours, when POINTER is on
    pointer_frames("coin-default-000.png")
    # The round's buttons, each as wide as its label needs
    for name, label in BUTTONS:
        shape(f"{name.lower()}-default-000.png", "rect", *button_size(label), "solid")


def build_object_types() -> tuple[dict, dict, list]:
    types = {
        "Coin": sprite_type("Coin", [animation("Default", [drawn("coin-default-000.png"), drawn("coin-default-001.png"),
                                                          *pointer_drawn("coin-default-000.png")])],
                            ivars=[ivar_def("value", "number", "Points it is worth."),
                                   ivar_def("kind", "string", "Which coin: \"gold\" or \"silver\".")],
                            behaviors=[beh_def("Tween")]),
        "Board": image_type("Board", "TiledBg", PITCH, PITCH, 0, 0),
        "RoundTag": text_type("RoundTag"),
        "ScoreLabel": text_type("ScoreLabel"),
        "ScoreText": text_type("ScoreText"),
        "KeyBox": zone_type("KeyBox", behaviors=[beh_def("Tween")]),
        "KeyText": text_type("KeyText"),
        "KeyVerb": text_type("KeyVerb"),
        "Touch": single_global_type("Touch", "Touch", {"use-mouse-input": True}),
    }
    for name, _ in BUTTONS:
        types[name] = sprite_type(name, [animation("Default", [drawn(f"{name.lower()}-default-000.png")])],
                                  behaviors=[beh_def("Tween")])
        types[f"{name}Label"] = text_type(f"{name}Label")
    types |= pointer_types()
    families = {}
    containers = []
    return types, families, containers


def build_layouts() -> dict[str, dict]:
    game = layout("Game", [
        layer("Background", transparent=False),
        layer("Game"),
        layer("UI", parallax=0),
    ], sheet="Game")
    # The board. A patterned area or edge is area(type, col, row, cols, rows) on the Game
    # layer; an area or a range drawn as lines is zone(), a reach a ring(). Add instances in any
    # order: build_all() sorts each layer
    board = tiledbg_inst("Board", BOARD_LEFT, BOARD_TOP, BOARD_W, BOARD_H, 0, 0)
    game["layers"][0]["instances"].append(board)
    # HUD on the edges: a tag by hud_tag(), a value under its name by hud_stat(), keys by hud_keys(),
    # a label by hud_text(), repeated items by row(), anything else by anchor(). The middle of the
    # screen is the game's
    ui = game["layers"][2]["instances"]
    ui.extend(flat(HUD))
    # The round's buttons in a row in the bottom-right corner, each held there by Anchor
    buttons = []
    right = VIEW_W - MARGIN
    for name, label in reversed(BUTTONS):
        w, h = button_size(label)
        col, row = (right - w) // UNIT, (VIEW_H - MARGIN - h) // UNIT
        pair = button(name, f"{name.lower()}-default-000.png", f"{name}Label", label, col, row,
                      behaviors={**TWEEN, **anchored("bottom-right")}, label_behaviors=anchored("bottom-right"))
        buttons.append(list(pair))
        right = col * UNIT - UNIT
    ui.extend(flat(buttons))
    # A value as a bar: ui.extend(hud_bar("HpFrame", "HpFill", "top-left", units(12), dy=3))
    # Layout checks: HUD overlap, spacing between groups, the board centred and large enough
    no_overlap(ui)
    spaced([*HUD, *buttons, [board]])
    balanced([board], PLAY_AREA)
    filled([board])
    # Off the HUD, everything starts on the grid: shape_inst() on a cell, grid_random() at runtime
    on_grid(game["layers"][1]["instances"], "layer Game")
    # Template instances of runtime-created objects, in a layout that never runs
    objects = layout("Objects", [layer("Objects")], sheet=None)
    coin = shape_inst("Coin", "coin-default-000.png", MARGIN // UNIT, MARGIN // UNIT,
                      ivars={"value": 1, "kind": "gold"}, behaviors=dict(TWEEN))
    objects["layers"][0]["instances"].append(coin)
    on_grid(objects["layers"][0]["instances"], "layout Objects")
    return {"Game": game, "Objects": objects}


# --- the event sheet -------------------------------------------------------------------
# One function per group, in play order
def module_setup() -> dict:
    return module("Setup", events=[
        # Restart layout keeps globals, so the round's values are reset here, before any text shows them
        event("Empty the score and deal this round's coins",
              [on_start()], [set_var("score", "0"), set_text("ScoreText", q("0")),
                             set_text("RoundTag", tracked_expr(f'{q("Round · ")} & zeropad(beat + 1, 2) & '
                                                               f'{q(" / ")} & zeropad(tokencount(ROUND_COINS, '
                                                               f'{q(",")}), 2)')),
                             set_var("deal", f"floor(random({CELLS}))")], children=[
                  block([for_loop("i", "0", f"int(tokenat(ROUND_COINS, beat, {q(',')})) - 1")], [
                      create("Coin", "Game",
                             f'{BOARD_LEFT + TOUCH // 2} + {PITCH} * ((deal + (loopindex("i") * {STRIDE})) % {COLS})',
                             f'{BOARD_TOP + TOUCH // 2} + {PITCH} * floor(((deal + (loopindex("i") * {STRIDE})) '
                             f'% {CELLS}) / {COLS})'),
                      set_ivar("Coin", "value", "choose(1, 5)"),
                  ]),
              ]),
    ])


def module_input() -> dict:
    return module("Input", events=[
        event("A touched coin collects itself, once", [on_touched("Coin"), cond("is-any-playing", "Coin", beh="Tween",
                                                                           inverted=True)],
              [call_custom("Coin", "Collect")]),
    ])


def scoring() -> list:
    """What the groups call: a custom action to act on the caller's picked instances, a function
    for a value or for logic that picks its own."""
    return [
        *procedure("Score the coin, show the hit, then shrink it away", custom_action("Coin", "Collect", steps(
            ("Score it, then show the hit", [call("AddScore", "Coin.value"),
                                               *hit("Coin", frame="pressed" if POINTER else "hit")]),
            ("Shrink it away once the punch is over", [
                wait(f"{SQUASH['hit']['seconds'] - HIT_FLASH['seconds']:g}", use_timescale=False),
                tween2("Coin", "collect", "size", "0", "0", "0.25", "easeinback", destroy=True)]),
        ))),
        *procedure("Add points and show the score", func("AddScore", [
            add_var("score", "points"),
            set_text("ScoreText", "score"),
        ], params=[param("points", "number", 0)])),
    ]


def module_restart() -> dict:
    return module("Restart", events=[
        event("Start the next round when the last coin is gone",
              [cmp2("Coin.Count", EQ, "0"), trigger_once()],
              [set_var("beat", f"(beat + 1) % tokencount(ROUND_COINS, {q(',')})"), wait("1"), restart_layout()]),
    ])


def module_buttons() -> dict:
    # One touch end for both buttons, each a sub-event, as the same-trigger warning advises
    def released(obj: str, acts: list) -> dict:
        return block([is_bool(obj, "pressed")], [set_bool(obj, "pressed", False), *squash(obj, "press", "Tween", "back")],
                     [block([cond("is-touching-object", "Touch", {"object": obj})], acts)])
    PRESSED.update({"Restart", "Skip"})
    return module("Buttons", events=[
        *event("Press a button down under the finger", [on_touched("Restart")],
               [set_bool("Restart", "pressed", True), *squash("Restart", "press", "Tween", "down")]),
        *event("Press a button down under the finger", [on_touched("Skip")],
               [set_bool("Skip", "pressed", True), *squash("Skip", "press", "Tween", "down")]),
        *event("Let the pressed button spring back and act", [cond("on-any-touch-end", "Touch")], [], children=[
            released("Restart", [restart_layout()]),
            released("Skip", [set_var("beat", f"(beat + 1) % tokencount(ROUND_COINS, {q(',')})"), restart_layout()])]),
    ])


def build_event_sheet() -> dict:
    """The sheet: what it covers, the constants under Settings, the shared state, then the groups.
    A variable that one group owns is declared in its module."""
    events = [
        comment("Coins. Tap a coin to collect it; when the last one is gone the next round starts.\n"
                "The touched coin is the trigger's pick: Collect runs on it and nothing else"),
        comment("Settings"),
        var("ROUND_COINS", "string", ",".join(str(b["coins"]) for b in BEATS),
            "Coins dealt in each round, one round a beat of the generator's BEATS", const=True),
        comment("Gameplay variables"),
        var("score", "number", 0, "Points collected this round"),
        var("beat", "number", 0, "The round being played, from 0; a global keeps it across the restart"),
        var("deal", "number", 0, "The grid cell this round's first coin lands on; the others step from it"),
        module_setup(),
        module_input(),
        *scoring(),
        module_restart(),
        module_buttons(),
        # A touch collects the coin and its hit shows the pressed colour, so the group leaves the press to it
        *pointer_module("Coin", pressed=False),
        hints("KeyBox"),
    ]
    return {"name": "Game", "events": events, "sid": sid()}


if __name__ == "__main__":
    build_and_check()
