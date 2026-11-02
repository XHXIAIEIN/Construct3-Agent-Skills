"""check_screens.py: the mechanical findings over the instances a layout holds, and
what the run prints. The browser is not started: the checks are pure functions
of what SNAPSHOT_JS reads from the runtime."""
import json
import subprocess

from tests.skill_helpers import NEEDS_GIT, SKILL, INSTALLED, png, run, script_module

LAYERS = {"Game": {"parallax": [1, 1], "shown": True, "view": [0, 0, 1280, 720]},
          "UI": {"parallax": [0, 0], "shown": True, "view": [0, 0, 1280, 720]}}


cs = script_module("check_screens")


def inst(uid, kind, box, layer="UI", **extra):
    return {"type": kind, "uid": uid, "layer": layer, "box": box, "shown": True, "angle": 0, "root": uid, **extra}


def text(uid, kind, box, words, size, layer="UI", align=("center", "center"), **extra):
    return inst(uid, kind, box, layer, text=words, textSize=size, align=list(align), **extra)


def snap(*instances, size=(1280, 720)):
    return {"layout": "Map", "size": list(size), "viewport": [1280, 720], "layers": LAYERS,
            "instances": list(instances)}


def pairs(found):
    return [(f["rule"], f["uids"]) for f in found]


def rules(cs, *instances, **kw):
    return pairs(cs.findings(snap(*instances, **kw)))


def test_check_screens_finds_a_text_its_box_cuts_or_wraps():
    """A text wider than its box is cut; one taller by a second line wraps beyond it.
    A single line a little taller than its box draws whole."""
    found = cs.findings(snap(
        text(1, "HelpText", [592, 170, 688, 202], "选择前进之路", [144, 28]),
        text(2, "ResultText", [560, 300, 720, 364], "得分 1500 最高 0", [92, 165]),
        text(3, "CardName", [580, 240, 700, 260], "金刃风暴", [85, 25]),
        text(4, "Hidden", [0, 0, 10, 10], "too long for its box", [200, 20], shown=False),
        text(5, "Turned", [0, 0, 10, 10], "too long for its box", [200, 20], angle=0.5)))
    assert pairs(found) == [("text", [1]), ("text", [2])], found
    assert 'HelpText uid 1 "选择前进之路": the text needs 144x28 px and its box is 96x32' in found[0]["line"]
    assert "make the box at least 144x32 or the font smaller" in found[0]["line"]


def test_check_screens_finds_instances_created_and_never_moved_apart():
    """The names of five cards on one card: one finding for the group, with the texts."""
    names = ["木灵护体", "金刃风暴", "剑意通玄", "苍木缠身", "水火既济"]
    found = cs.findings(snap(*[text(10 + n, "CardName", [300, 420, 420, 450], w, [80, 24], layer="Game")
                               for n, w in enumerate(names)],
                             inst(20, "Card", [100, 400, 220, 560], layer="Game")))
    assert pairs(found) == [("stacked", [10, 11, 12, 13, 14])], found
    assert found[0]["line"].startswith("CardName: 5 instances on one box at (300, 420) 120x30, uids 10, 11")
    assert "set each one's position from the instance it belongs to" in found[0]["line"]
    assert rules(cs, inst(1, "Tiles", [0, 0, 1216, 256], layer="Game"), inst(2, "Tiles", [0, 0, 1216, 256]),
                 inst(3, "Drop", [60, 180, 61, 182], layer="Game"), inst(4, "Drop", [60, 180, 61, 182], layer="Game")) == []


def test_check_screens_leaves_out_one_box_that_shows_different_frames():
    """A slot's fill frame under its rim frame, one type on one box, is drawn so on purpose;
    two of the same frame there were never moved apart."""
    slot = [100, 400, 172, 472]

    def frame(uid, animation, n):
        return inst(uid, "Slot", slot, layer="Game", animation=animation, frame=n, frames=2, playing=False)
    assert rules(cs, frame(1, "Default", 0), frame(2, "Default", 1)) == []
    assert rules(cs, frame(1, "Fill", 0), frame(2, "Rim", 0)) == []
    assert rules(cs, frame(1, "Default", 0), frame(2, "Default", 1), frame(3, "Default", 1)) == [("stacked", [2, 3])]


def test_check_screens_leaves_out_drawing_canvases_on_one_box():
    """Full-screen Drawing Canvases of one type, each drawing its own line over the one under it,
    are layered on purpose, though they have no frames to tell them apart."""
    assert rules(cs, *[inst(n, "Line", [0, 0, 1280, 720], layer="Game", canvas=True) for n in range(1, 6)]) == []


def test_check_screens_finds_overlaps_on_the_hud_but_not_a_label_on_its_button():
    assert rules(cs,
                 inst(1, "Button", [100, 600, 260, 660]),
                 text(2, "ButtonLabel", [100, 600, 260, 660], "Start", [60, 24]),    # its label
                 inst(3, "Panel", [0, 0, 400, 400]),
                 inst(4, "Icon", [20, 20, 60, 60]),                                  # an icon on its panel
                 inst(5, "Bar", [500, 20, 700, 40], root=9),
                 inst(6, "BarFill", [500, 20, 650, 40], root=9),                     # one hierarchy
                 text(7, "Score", [900, 20, 1100, 60], "Score: 10", [120, 30]),
                 text(8, "ScoreShadow", [904, 24, 1104, 64], "Score: 1", [110, 30]),  # its shadow
                 text(9, "Briefing", [40, 40, 1240, 700], "How to play ...", [1100, 600]),  # over the screen
                 ) == []
    assert rules(cs, inst(1, "BeetleIcon", [352, 0, 384, 32]),
                 text(2, "BeetleCount", [368, 0, 432, 32], "x00", [51, 21], align=("left", "center"))) == []
    found = rules(cs,
                  text(1, "Title", [440, 80, 840, 160], "第1幕", [140, 57]),
                  text(2, "Subtitle", [540, 120, 740, 160], "选择前进之路", [144, 28]),   # over the title
                  inst(3, "EndTurn", [1000, 640, 1160, 700]),
                  inst(4, "DeckCount", [1100, 630, 1180, 700]))                      # most of it over the button
    assert found == [("overlap", [1, 2]), ("overlap", [3, 4])], found


def test_check_screens_finds_text_over_text_off_the_hud_only():
    """On a layer that scrolls, a name over its body is left to the picture; a text
    over another text is not."""
    assert rules(cs, inst(1, "Enemy", [560, 100, 720, 240], layer="Game"),
                 text(2, "EnemyName", [560, 150, 720, 190], "青木妖", [90, 30], layer="Game")) == []
    assert rules(cs, text(1, "EnemyName", [560, 150, 720, 190], "青木妖", [90, 30], layer="Game"),
                 text(2, "Intent", [560, 160, 720, 200], "回复", [60, 30], layer="Game")) == [("overlap", [1, 2])]


def test_check_screens_finds_a_hud_instance_the_screen_edge_cuts():
    """Not one waiting wholly off screen to move in, one wider than the screen, or
    art on a world layer that runs off the edge."""
    found = cs.findings(snap(inst(1, "Hint", [1200, 300, 1400, 340])))
    assert pairs(found) == [("edge", [1])], found
    assert "the right edge of the screen cuts it" in found[0]["line"]
    assert rules(cs, text(5, "Counter", [1200, 0, 1300, 32], "x00", [51, 21], align=("left", "center"))) == []
    assert rules(cs, inst(2, "Popup", [400, -300, 880, -20]),
                 inst(3, "Banner", [-20, 0, 1300, 60]),
                 inst(4, "Rock", [1200, 300, 1400, 340], layer="Game")) == []


def test_check_screens_finds_kinds_drawn_with_one_frame():
    """Map nodes of three kinds all on frame 0 of 4; not when the frame plays, when
    the animation has one frame, or when a text on each tells them apart."""

    def node(uid, kind):    # COL differs too, and is no kind
        return inst(uid, "Node", [100 * uid, 300, 100 * uid + 48, 348], layer="Game", animation="Default", frame=0,
                    frames=4, playing=False, instVars={"NTYPE": kind, "COL": uid})
    kinds = ["C", "E", "C", "R", "C"]
    nodes = [node(uid, k) for uid, k in enumerate(kinds, 1)]
    found = cs.findings(snap(*nodes))
    assert pairs(found) == [("frame", [1, 2, 3, 4, 5])], found
    assert "show animation 'Default' frame 0 of 4, though their NTYPE differs" in found[0]["line"]
    assert rules(cs, dict(nodes[0], playing=True), *nodes[1:]) == []
    assert rules(cs, *[dict(one, frames=1) for one in nodes]) == []
    hidden = [dict(one, instVars={"IsMine": k == "C"}) for one, k in zip(nodes, kinds)]
    assert rules(cs, *hidden) == []         # hidden state, drawn the same on purpose
    labels = [text(10 + uid, "NodeLabel", [100 * uid + 4, 310, 100 * uid + 44, 330], k, [20, 20], layer="Game")
              for uid, k in enumerate(kinds, 1)]
    assert rules(cs, *nodes, *labels) == []


def test_check_screens_names_screenshots_by_layout():
    assert cs.file_name("第1幕 Map") == "第1幕-Map"
    assert cs.file_name("Game/Level:2") == "Game-Level-2"
    finding = cs.findings(snap(text(1, "HelpText", [592, 170, 688, 202], "选择前进之路", [144, 28])))
    lines = cs.report({"project": "Game", "status": "opened", "title": "Game - Construct 3", "editor": "e",
                       "warnings": [], "preview": {"started": True, "errors": [], "layouts": [
                           {"layout": "Map", "shot": ".tmp/look/Map.png", "findings": finding, "errors": []},
                           {"layout": "Combat", "left": "Reward", "errors": ["Event sheet 2, event 4: TypeError"]}]}})
    assert lines[1] == "layout 'Map' (1 of 2): screenshot .tmp/look/Map.png"
    assert lines[2].startswith('  text: HelpText uid 1 "选择前进之路"')
    assert lines[3].startswith("layout 'Combat' (2 of 2): started, and its events went on to 'Reward'")
    assert lines[4] == "  runtime: Event sheet 2, event 4: TypeError"


def test_check_screens_prints_its_help_and_needs_a_project(tmp_path, project):
    code, out = run(project, f"{INSTALLED}/scripts/check_screens.py", "--help")
    assert code == 0 and "stacked" in out and "exit codes:" in out, out
    empty = tmp_path / "empty"
    empty.mkdir()
    code, out = run(empty, SKILL / "scripts" / "check_screens.py")
    assert code == 2 and "no project.c3proj found" in out, out


def test_check_screens_says_what_a_clean_run_left_unseen():
    clean = {"status": "opened", "preview": {"started": True,
                                             "layouts": [{"layout": "Map", "findings": [], "errors": []}]}}
    found = {"status": "opened", "preview": {"started": True,
                                             "layouts": [{"layout": "Map", "findings": [{"rule": "text"}],
                                                                         "errors": []}]}}
    assert cs.summary_line([clean], 1.0, ".tmp/check-screens.json", ".tmp/look") == (
        "screens: 0 findings to fix on 1 layout, 0 runtime errors; each layout ran 1 s after a jump to it, without play, so a "
        "scene the game reaches only in play is unseen; full result in .tmp/check-screens.json, screenshots in .tmp/look")
    assert "unseen" not in cs.summary_line([found], 1.0, ".tmp/check-screens.json", ".tmp/look")


def test_a_screenshot_of_one_colour_dark_or_clear_is_blank():
    """Over 601 screenshots of games the most one-coloured one that showed something was 99.03%."""
    c3 = script_module("c3project")
    assert c3.blank_share(png(100, 100, lambda x, y: (30, 90, 200, 255))) == 1
    assert c3.blank_share(png(100, 100, lambda x, y: ((x * 7 + y) % 16, 0, 5, 255))) == 1      # near black, noisy
    assert c3.blank_share(png(100, 100, lambda x, y: (x % 255, y, 9, x % 15))) == 1           # clear
    coin = lambda x, y: (40, 100, 240, 255) if (x - 10) ** 2 + (y - 10) ** 2 < 36 else (0, 0, 0, 255)
    assert c3.blank_share(png(100, 100, coin)) is None          # a coin on black: 1.1% drawn
    assert c3.blank_share(png(100, 100, lambda x, y: (255, 255, 255, 255) if x else (0, 0, 0, 255))) is None


def test_a_preview_that_did_not_run_looked_at_no_layout():
    """A project that opened but whose preview stopped is a review that did not run (exit 3), not one with no
    finding on no layout, which a reader and verify_change.py would take for a pass."""
    stopped = {"project": "Game", "status": "opened", "title": "Game - Construct 3", "editor": "e", "warnings": [],
               "preview": {"started": False, "layouts": [],
                           "errors": ["the preview stopped answering: Not attached to an active page"]}}
    ran = {**stopped, "project": "Other", "preview": {"started": True, "errors": [], "layouts": []}}
    assert cs.unpreviewed([stopped, ran]) == ["Game"] and cs.unpreviewed([ran]) == []
    assert cs.report(stopped)[-1] == "  preview did not run: the preview stopped answering: Not attached to an active page"
    assert cs.summary_line([stopped], 1.0, ".tmp/check-screens.json", ".tmp/look") == (
        "screens: no layout was visited, as the preview of Game did not run; full result in .tmp/check-screens.json")


def test_check_screens_retakes_a_blank_screenshot():
    blank = {"project": "Game", "status": "opened", "title": "Game - Construct 3", "editor": "e",
             "warnings": [], "preview": {"started": True, "errors": [], "layouts": [
                 {"layout": "Objects", "shot": ".tmp/look/Objects.png", "findings": [], "errors": [],
                  "blank": {"tries": 3, "share": 0.99995}}]}}
    lines = cs.report(blank)
    assert lines[1] == ("layout 'Objects' (1 of 1): screenshot .tmp/look/Objects.png: 99.9% or more of it is one "
                        "colour after 3 shots 1 s apart, so the layout draws nothing in view at its start, or the preview "
                        "did not draw it. If it should show something, raise --settle, "
                        "or reach it in play with a shot step of a preview_project.py plan")
    lines = cs.report({"project": "Game", "status": "opened", "title": "Game - Construct 3", "editor": "e",
                       "warnings": [], "preview": {"started": True, "errors": [], "layouts": [
                           {"layout": "Map", "shot": ".tmp/look/Map.png", "findings": [], "errors": [],
                            "blank": {"tries": 2, "share": None}}]}})
    assert lines[1] == ("layout 'Map' (1 of 1): screenshot .tmp/look/Map.png, taken when the layout was drawn; the "
                        "shot before showed one colour, not drawn yet")


def test_a_finding_fails_and_a_warning_does_not():
    """A finding fails the run. unlimited warns, and so does what only a guessed longest text causes."""
    found = cs.findings(snap(text(1, "HelpText", [592, 170, 688, 202], "选择前进之路", [144, 28])))
    warn = [{"rule": "unlimited", "uids": [5], "line": "KeyText", "warn": True}]
    ranked = cs.ranked(warn + cs.placed(found, "phone") + found)
    assert [(f["rule"], f.get("at")) for f in ranked] == [("text", "phone"), ("unlimited", None)]
    result = {"status": "opened", "preview": {"started": True, "layouts": [
        {"layout": "Game", "findings": warn, "errors": []}]}}
    assert cs.counts(result) == (0, 1, 0, 1)
    assert cs.summary_line([result], 1.0, "r.json", "s").startswith("screens: 0 findings to fix and 1 that warns on 1 layout")
    assert cs.finding_line(ranked[0]).startswith('  text @phone: HelpText uid 1')
    assert cs.finding_line(ranked[1]) == "  warning unlimited: KeyText"


def test_each_layout_is_shown_on_three_shapes_of_screen_its_orientations_allow():
    assert cs.screen_shapes([1920, 1080], "landscape") == [("", [1920, 1080]), ("4x3", [1440, 1080]),
                                                          ("phone", [2340, 1080])]
    assert cs.screen_shapes([1080, 1920], "portrait") == [("", [1080, 1920]), ("3x4", [1080, 1440]),
                                                         ("phone", [1080, 2340])]
    assert cs.screen_shapes([1280, 960], "any") == [("", [1280, 960]), ("16x9", [1707, 960]), ("phone", [960, 2080])]
    assert cs.shot_name("Game", "", "demo") == "Game.png"
    assert cs.shot_name("Game", "phone", "worst") == "Game@phone-worst.png"
    assert cs.shot_name("Game", "", "empty") == "Game@empty.png"


def test_a_text_that_events_set_shows_its_declared_longest_or_a_guessed_worst(tmp_path):
    gap = " "
    tag = gap.join("ROUND") + f"{gap} {gap}·{gap} {gap}" + gap.join("01") + f"{gap} {gap}/{gap} {gap}" + gap.join("06")
    worst = cs.state_text(tag, "worst", None)
    assert worst.endswith(gap.join("9999999") + f"{gap} {gap}/{gap} {gap}" + gap.join("99")), repr(worst)
    assert cs.state_text(tag, "one", None).endswith(f"1{gap} {gap}/{gap} {gap}1")
    assert cs.state_text("Score 120", "worst", None) == "Score 9999999"
    assert cs.state_text("Score 120", "worst", "Score 999") == "Score 999"
    assert cs.state_text("Slime", "worst", None) == cs.WORST_NAME
    assert cs.state_text("史莱姆", "worst", None) == cs.WORST_WIDE
    assert cs.state_text("Play cards, then end", "worst", None) == "Play cards, then end Play cards, then end"
    assert cs.state_text("Lives 3", "empty", None) == "" and cs.state_text("Lives 3", "one", None) == "Lives 1"
    (tmp_path / "eventSheets").mkdir()
    (tmp_path / "eventSheets" / "Game.json").write_text(json.dumps({"events": [{"actions": [
        {"id": "set-text", "objectClass": "ScoreText"}, {"id": "set-position", "objectClass": "Coin"}],
        "children": [{"actions": [{"id": "append-text", "objectClass": "Log"}]}]}]}), encoding="utf-8")
    assert cs.set_by_events(tmp_path) == {"ScoreText", "Log"}
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "texts.json").write_text(json.dumps({"longest": {"ScoreText": "999"}}), encoding="utf-8")
    assert cs.declared(tmp_path) == {"ScoreText": "999"}
    shown = [text(3, "ScoreText", [0, 0, 60, 30], "0", [20, 28]), text(4, "Log", [0, 40, 60, 70], "Hit", [30, 28]),
             text(5, "Title", [0, 80, 60, 110], "Coins", [50, 28])]
    setters = {"ScoreText", "Log"}
    assert cs.state_texts(shown, setters, {"ScoreText": "999"}, "worst") == {3: "999", 4: cs.WORST_NAME}
    found = cs.unlimited_findings(shown, setters, {"ScoreText": "999"})
    assert [(f["rule"], f["uids"]) for f in found] == [("unlimited", [4])] and "Log" in found[0]["line"]
    cut = [{"rule": "text", "uids": [4], "line": "Log uid 4"}, {"rule": "text", "uids": [3], "line": "S"},
           {"rule": "overlap", "uids": [3, 5], "line": "S and Title"}]
    marked = cs.guessed(cut, shown, setters, {"ScoreText": "999"}, "worst")
    assert [bool(f.get("warn")) for f in marked] == [True, False, False]
    assert marked[0]["line"].endswith("no longest is declared")
    assert cs.guessed(cut, shown, setters, {}, "empty") == cut


def test_a_text_measured_on_what_lies_behind_it_is_faint_under_the_contrast_it_needs():
    """The colour of a text's core pixels against the same pixels with every text hidden, as WCAG 2.2 counts it."""
    grey, white = (150, 150, 150, 255), (255, 255, 255, 255)
    before = [grey if n % 4 == 0 else (200, 200, 200, 255) if n % 4 == 1 else white for n in range(64)]
    ink, behind = cs.ink_colours(before, [white] * 64)
    assert ink == (150, 150, 150) and behind == (255, 255, 255)
    assert round(cs.ratio(ink, behind), 2) == 2.96 and cs.CONTRAST == (4.5, 3)
    layers = {"UI": {"css": [0, 0, 1, 1]}}
    small = text(1, "Hint", [0, 0, 100, 20], "Tap", [30, 16], em=16)
    large = text(2, "Title", [0, 30, 300, 80], "Coins", [200, 40], em=40)
    found = cs.faint_findings([small, large], {1: (ink, behind), 2: (ink, behind)}, layers)
    assert [f["uids"] for f in found] == [[1]]
    assert "read 3.0:1 on #ffffff behind them, under the 4.5:1 a text needs" in found[0]["line"]


def test_a_text_still_showing_a_placeholder_is_a_finding():
    """A shown Text that still reads as the Text object's default or as Lorem ipsum after the
    layout has run is a finding; a hidden one, or a word that only holds "text", is not."""
    shown = [text(1, "ScoreText", [0, 0, 100, 20], " Text ", [40, 16]),
             text(2, "Hint", [0, 30, 300, 80], "Lorem ipsum dolor sit amet.", [200, 40]),
             text(3, "Help", [0, 90, 300, 120], "Tap the text to read it", [200, 20])]
    hidden = {**text(4, "End", [0, 130, 100, 150], "Text", [40, 16]), "shown": False}
    found = cs.placeholder_findings([*shown, hidden])
    assert [f["uids"] for f in found] == [[1], [2]] and "still shows a placeholder" in found[0]["line"]


