"""review_look.py: the mechanical findings over the instances a layout holds, and
what the run prints. The browser is not started: the checks are pure functions
of what LOOK_JS reads from the runtime, and a reviewer's reply is checked against the brief."""
import json

from tests.skill_helpers import SKILL, INSTALLED, png, run, script_module

LAYERS = {"Game": {"parallax": [1, 1], "shown": True, "view": [0, 0, 1280, 720]},
          "UI": {"parallax": [0, 0], "shown": True, "view": [0, 0, 1280, 720]}}


rl = script_module("review_look")


def inst(uid, kind, box, layer="UI", **extra):
    return {"type": kind, "uid": uid, "layer": layer, "box": box, "shown": True, "angle": 0, "root": uid, **extra}


def text(uid, kind, box, words, size, layer="UI", align=("center", "center"), **extra):
    return inst(uid, kind, box, layer, text=words, textSize=size, align=list(align), **extra)


def snap(*instances, size=(1280, 720)):
    return {"layout": "Map", "size": list(size), "viewport": [1280, 720], "layers": LAYERS,
            "instances": list(instances)}


def pairs(found):
    return [(f["rule"], f["uids"]) for f in found]


def rules(rl, *instances, **kw):
    return pairs(rl.findings(snap(*instances, **kw)))


def test_review_look_finds_a_text_its_box_cuts_or_wraps():
    """A text wider than its box is cut; one taller by a second line wraps beyond it.
    A single line a little taller than its box draws whole."""
    found = rl.findings(snap(
        text(1, "HelpText", [592, 170, 688, 202], "选择前进之路", [144, 28]),
        text(2, "ResultText", [560, 300, 720, 364], "得分 1500 最高 0", [92, 165]),
        text(3, "CardName", [580, 240, 700, 260], "金刃风暴", [85, 25]),
        text(4, "Hidden", [0, 0, 10, 10], "too long for its box", [200, 20], shown=False),
        text(5, "Turned", [0, 0, 10, 10], "too long for its box", [200, 20], angle=0.5)))
    assert pairs(found) == [("text", [1]), ("text", [2])], found
    assert 'HelpText uid 1 "选择前进之路": the text needs 144x28 px and its box is 96x32' in found[0]["line"]
    assert "make the box at least 144x32 or the font smaller" in found[0]["line"]


def test_review_look_finds_instances_created_and_never_moved_apart():
    """The names of five cards on one card: one finding for the group, with the texts."""
    names = ["木灵护体", "金刃风暴", "剑意通玄", "苍木缠身", "水火既济"]
    found = rl.findings(snap(*[text(10 + n, "CardName", [300, 420, 420, 450], w, [80, 24], layer="Game")
                               for n, w in enumerate(names)],
                             inst(20, "Card", [100, 400, 220, 560], layer="Game")))
    assert pairs(found) == [("stacked", [10, 11, 12, 13, 14])], found
    assert found[0]["line"].startswith("CardName: 5 instances on one box at (300, 420) 120x30, uids 10, 11")
    assert "set each one's position from the instance it belongs to" in found[0]["line"]
    assert rules(rl, inst(1, "Tiles", [0, 0, 1216, 256], layer="Game"), inst(2, "Tiles", [0, 0, 1216, 256]),
                 inst(3, "Drop", [60, 180, 61, 182], layer="Game"), inst(4, "Drop", [60, 180, 61, 182], layer="Game")) == []


def test_review_look_leaves_out_one_box_that_shows_different_frames():
    """A slot's fill frame under its rim frame, one type on one box, is drawn so on purpose;
    two of the same frame there were never moved apart."""
    slot = [100, 400, 172, 472]

    def frame(uid, animation, n):
        return inst(uid, "Slot", slot, layer="Game", animation=animation, frame=n, frames=2, playing=False)
    assert rules(rl, frame(1, "Default", 0), frame(2, "Default", 1)) == []
    assert rules(rl, frame(1, "Fill", 0), frame(2, "Rim", 0)) == []
    assert rules(rl, frame(1, "Default", 0), frame(2, "Default", 1), frame(3, "Default", 1)) == [("stacked", [2, 3])]


def test_review_look_leaves_out_drawing_canvases_on_one_box():
    """Full-screen Drawing Canvases of one type, each drawing its own line over the one under it,
    are layered on purpose, though they have no frames to tell them apart."""
    assert rules(rl, *[inst(n, "Line", [0, 0, 1280, 720], layer="Game", canvas=True) for n in range(1, 6)]) == []


def test_review_look_finds_overlaps_on_the_hud_but_not_a_label_on_its_button():
    assert rules(rl,
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
    assert rules(rl, inst(1, "BeetleIcon", [352, 0, 384, 32]),
                 text(2, "BeetleCount", [368, 0, 432, 32], "x00", [51, 21], align=("left", "center"))) == []
    found = rules(rl,
                  text(1, "Title", [440, 80, 840, 160], "第1幕", [140, 57]),
                  text(2, "Subtitle", [540, 120, 740, 160], "选择前进之路", [144, 28]),   # over the title
                  inst(3, "EndTurn", [1000, 640, 1160, 700]),
                  inst(4, "DeckCount", [1100, 630, 1180, 700]))                      # most of it over the button
    assert found == [("overlap", [1, 2]), ("overlap", [3, 4])], found


def test_review_look_finds_text_over_text_off_the_hud_only():
    """On a layer that scrolls, a name over its body is left to the picture; a text
    over another text is not."""
    assert rules(rl, inst(1, "Enemy", [560, 100, 720, 240], layer="Game"),
                 text(2, "EnemyName", [560, 150, 720, 190], "青木妖", [90, 30], layer="Game")) == []
    assert rules(rl, text(1, "EnemyName", [560, 150, 720, 190], "青木妖", [90, 30], layer="Game"),
                 text(2, "Intent", [560, 160, 720, 200], "回复", [60, 30], layer="Game")) == [("overlap", [1, 2])]


def test_review_look_finds_a_hud_instance_the_screen_edge_cuts():
    """Not one waiting wholly off screen to move in, one wider than the screen, or
    art on a world layer that runs off the edge."""
    found = rl.findings(snap(inst(1, "Hint", [1200, 300, 1400, 340])))
    assert pairs(found) == [("edge", [1])], found
    assert "the right edge of the screen cuts it" in found[0]["line"]
    assert rules(rl, text(5, "Counter", [1200, 0, 1300, 32], "x00", [51, 21], align=("left", "center"))) == []
    assert rules(rl, inst(2, "Popup", [400, -300, 880, -20]),
                 inst(3, "Banner", [-20, 0, 1300, 60]),
                 inst(4, "Rock", [1200, 300, 1400, 340], layer="Game")) == []


def test_review_look_finds_kinds_drawn_with_one_frame():
    """Map nodes of three kinds all on frame 0 of 4; not when the frame plays, when
    the animation has one frame, or when a text on each tells them apart."""

    def node(uid, kind):    # COL differs too, and is no kind
        return inst(uid, "Node", [100 * uid, 300, 100 * uid + 48, 348], layer="Game", animation="Default", frame=0,
                    frames=4, playing=False, instVars={"NTYPE": kind, "COL": uid})
    kinds = ["C", "E", "C", "R", "C"]
    nodes = [node(uid, k) for uid, k in enumerate(kinds, 1)]
    found = rl.findings(snap(*nodes))
    assert pairs(found) == [("frame", [1, 2, 3, 4, 5])], found
    assert "show animation 'Default' frame 0 of 4, though their NTYPE differs" in found[0]["line"]
    assert rules(rl, dict(nodes[0], playing=True), *nodes[1:]) == []
    assert rules(rl, *[dict(one, frames=1) for one in nodes]) == []
    hidden = [dict(one, instVars={"IsMine": k == "C"}) for one, k in zip(nodes, kinds)]
    assert rules(rl, *hidden) == []         # hidden state, drawn the same on purpose
    labels = [text(10 + uid, "NodeLabel", [100 * uid + 4, 310, 100 * uid + 44, 330], k, [20, 20], layer="Game")
              for uid, k in enumerate(kinds, 1)]
    assert rules(rl, *nodes, *labels) == []


def test_review_look_names_screenshots_by_layout_and_asks_the_questions_once():
    assert rl.file_name("第1幕 Map") == "第1幕-Map"
    assert rl.file_name("Game/Level:2") == "Game-Level-2"
    finding = rl.findings(snap(text(1, "HelpText", [592, 170, 688, 202], "选择前进之路", [144, 28])))
    lines = rl.report({"project": "Game", "status": "opened", "title": "Game - Construct 3", "editor": "e",
                       "warnings": [], "preview": {"started": True, "errors": [], "layouts": [
                           {"layout": "Map", "shot": ".tmp/look/Map.png", "findings": finding, "errors": []},
                           {"layout": "Combat", "left": "Reward", "errors": ["Event sheet 2, event 4: TypeError"]}]}})
    assert lines[1] == "layout 'Map' (1 of 2): screenshot .tmp/look/Map.png"
    assert lines[2].startswith('  text: HelpText uid 1 "选择前进之路"')
    assert lines[3].startswith("layout 'Combat' (2 of 2): started, and its events went on to 'Reward'")
    assert lines[4] == "  runtime: Event sheet 2, event 4: TypeError"
    assert lines[5].startswith("questions: answer every question yes or no for each screenshot above, through the brief")
    assert [line[:5] for line in lines[6:]] == [f"  {n}. " for n in range(1, 8)]
    assert all(line.isascii() for line in rl.QUESTIONS)


def test_review_look_asks_about_the_design_places_play_design_does_not_measure(tmp_path):
    import json
    (tmp_path / "tools").mkdir()
    (tmp_path / "project.c3proj").write_text(json.dumps({"objectTypes": {"items": ["ScoreText", "Board"]}}),
                                             encoding="utf-8")
    (tmp_path / "tools" / "design.json").write_text(json.dumps({"screen": {
        "score": "top-left", "board": "a 5 x 3 grid in the middle", "lives": "top-right"}}), encoding="utf-8")
    places = rl.unmeasured(tmp_path, None)
    assert places == ['board "a 5 x 3 grid in the middle"', 'lives "top-right"']
    asked = rl.ask(False, places)
    assert asked[-1] == ("  7. On a screenshot that shows it, does an object sit away from the place given for it: "
                         'board "a 5 x 3 grid in the middle"; lives "top-right"?')
    assert rl.unmeasured(tmp_path, tmp_path / "none.json") == []


def test_review_look_writes_a_brief_for_a_reviewer_that_has_not_seen_the_project():
    result = {"places": ['lives "top-right"'], "preview": {"layouts": [
        {"layout": "Map", "shot": "/g/.tmp/look/Map.png", "findings": [{"rule": "text", "line": "HelpText uid 1"}],
         "errors": []},
        {"layout": "Combat", "left": "End", "errors": []}]}}
    text = rl.brief(result)
    assert text.startswith("# Look review\n\nYou have not seen this game's project")
    assert "1. Map: /g/.tmp/look/Map.png\n" in text and "Combat" not in text
    assert "HelpText" not in text             # the findings are the builder's, not the reviewer's
    assert f"1. {rl.QUESTIONS[0]}\n" in text
    assert ("7. On a screenshot that shows it, does an object sit away from the place given for it: lives "
            "\"top-right\"?\n8. Does the same decoration") in text
    assert "Map 1: no\nMap 2: yes - " in text


REVIEWED = {"places": [], "brief": ".tmp/look/brief.md", "preview": {"layouts": [
    {"layout": "Map", "shot": ".tmp/look/Map.png", "findings": [], "errors": []},
    {"layout": "Big map", "shot": ".tmp/look/Big map.png", "findings": [], "errors": []},
    {"layout": "Combat", "left": "End", "errors": []}]}}


def test_a_reply_is_checked_against_the_brief_it_answers():
    asked = len(rl.questions(True, []))
    reply = "\n".join([f"**Map {q}:** no" for q in range(1, asked + 1) if q not in (2, 3, 4)]
                      + ["Map 2: yes - top left: the score covers the timer"]
                      + [f"- Big map Q{q}. no" for q in range(1, asked)]          # Big map 7 left out
                      + ["Big map 5: yes", "Shop 1: no", "Map 99: no", "I looked at every screenshot."])
    lines, code, verdict = rl.check_reply(REVIEWED, reply, "reply.md", None)
    assert code == 1 and verdict == {"complete": False, "yes": 2}
    assert lines == [
        f"reply: reply.md, against the brief of 2 screenshots and {asked} questions: {2 * asked} answers asked",
        "  missing: Map 3, 4; Big map 7",
        "  yes without where: Big map 5",
        "  not in the brief: Shop 1: no",              # Combat drew no screenshot, Shop is no layout
        "  not in the brief: Map 99: no",
        "  yes: Map 2 - top left: the score covers the timer",
        "  yes: Big map 5",
        f"answers: {2 * asked - 3} of {2 * asked}, 2 yes, 3 missing",
        "next: give the reviewer the same brief again and have it answer the missing questions and say where each "
        "yes is; then check its reply again"]
    every_no = "\n".join(f"{shot} {q}: no" for shot in ("Map", "Big map") for q in range(1, asked + 1))
    lines, code, verdict = rl.check_reply(REVIEWED, every_no, "reply.md", None)
    assert code == 0 and verdict == {"complete": True, "yes": 0} and lines[-1] == rl.DONE
    one_yes = every_no.replace("Map 2: no", "Map 2: yes - the coin: a grey box")
    lines, code, verdict = rl.check_reply(REVIEWED, one_yes, "r", None)
    assert code == 1 and verdict == {"complete": True, "yes": 1} and "  yes: Map 2 - the coin: a grey box" in lines
    assert lines[-1] == ("next: fix each yes: name the layout and the object type at the place it describes, change "
                         "it, then run review_look.py again and have its new brief answered")
    # While verify_change.py waits for the answers, the last line goes on with it
    lines, _, _ = rl.check_reply(REVIEWED, every_no, "reply.md", "python v.py")
    assert lines[-1] == "next: every question is answered no; run python v.py, which passes its look step on this reply"
    lines, _, _ = rl.check_reply(REVIEWED, one_yes, "r", "python v.py")
    assert lines[-1].endswith("change it, then run python v.py, which looks again; after three rounds with a yes "
                              "its look step passes, and the hand-over names each yes left"), lines[-1]


def test_review_look_checks_a_saved_reply_without_a_browser(project):
    code, out = run(project, SKILL / "scripts" / "review_look.py", "--reply", "reply.md")
    assert code == 2 and "no reply at reply.md" in out, out
    (project / "reply.md").write_text("Map 1: no\n", encoding="utf-8")
    code, out = run(project, SKILL / "scripts" / "review_look.py", "--reply", "reply.md")
    assert code == 2 and "run review_look.py first" in out, out
    (project / ".tmp" / "scripts" / "review-look").mkdir(parents=True, exist_ok=True)
    (project / ".tmp" / "scripts" / "review-look" / "result.json").write_text(json.dumps(REVIEWED), encoding="utf-8")
    code, out = run(project, SKILL / "scripts" / "review_look.py", "--reply", "reply.md")
    assert code == 1 and "  missing: Map 2-" in out and out.rstrip().splitlines()[-2].startswith("answers: 1 of "), out


def test_a_checked_reply_is_kept_on_the_run_it_answers(project):
    """--reply writes its verdict into the result of the run whose brief it answers, where verify_change.py passes
    its look step on it; while that step waits, the last line names verify_change.py, and a review run on its own
    ends with the review done."""
    (project / ".tmp" / "scripts" / "review-look").mkdir(parents=True, exist_ok=True)
    (project / ".tmp" / "scripts" / "review-look" / "result.json").write_text(json.dumps({**REVIEWED, "run": "r1"}), encoding="utf-8")
    asked = len(rl.questions(True, []))
    (project / "reply.md").write_text("\n".join(f"{shot} {q}: no" for shot in ("Map", "Big map")
                                                for q in range(1, asked + 1)), encoding="utf-8")
    code, out = run(project, SKILL / "scripts" / "review_look.py", "--reply", "reply.md")
    assert code == 0 and out.rstrip().splitlines()[-1] == rl.DONE, out
    result = json.loads((project / ".tmp" / "scripts" / "review-look" / "result.json").read_text(encoding="utf-8"))
    assert result["run"] == "r1" and result["reply"] == {"file": "reply.md", "complete": True, "yes": 0}, result
    record = project / ".tmp" / "scripts" / "verify-change" / "result.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({"steps": {"looked": {"state": "passed"}}}), encoding="utf-8")
    code, out = run(project, SKILL / "scripts" / "review_look.py", "--reply", "reply.md")
    assert code == 0 and out.rstrip().splitlines()[-1] == rl.DONE, out
    record.write_text(json.dumps({"steps": {"looked": {"state": "asked"}}}), encoding="utf-8")
    code, out = run(project, SKILL / "scripts" / "review_look.py", "--reply", "reply.md")
    last = out.rstrip().splitlines()[-1]
    assert code == 0 and last.startswith("next: every question is answered no; run python "), out
    assert last.endswith("verify_change.py, which passes its look step on this reply"), out


def test_review_look_prints_its_help_and_needs_a_project(tmp_path, project):
    code, out = run(project, f"{INSTALLED}/scripts/review_look.py", "--help")
    assert code == 0 and "stacked" in out and "exit codes:" in out, out
    empty = tmp_path / "empty"
    empty.mkdir()
    code, out = run(empty, SKILL / "scripts" / "review_look.py")
    assert code == 2 and "no project.c3proj found" in out, out


def test_review_look_says_what_a_clean_run_left_unseen():
    clean = {"status": "opened", "preview": {"started": True,
                                             "layouts": [{"layout": "Map", "findings": [], "errors": []}]}}
    found = {"status": "opened", "preview": {"started": True,
                                             "layouts": [{"layout": "Map", "findings": [{}], "errors": []}]}}
    assert rl.look_line([clean], 1.0, ".tmp/review-look.json", ".tmp/look") == (
        "look: 0 findings on 1 layout, 0 runtime errors; each layout ran 1 s after a jump to it, without play, so a "
        "scene the game reaches only in play is unseen; full result in .tmp/review-look.json, screenshots in .tmp/look")
    assert "unseen" not in rl.look_line([found], 1.0, ".tmp/review-look.json", ".tmp/look")


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
    assert rl.unpreviewed([stopped, ran]) == ["Game"] and rl.unpreviewed([ran]) == []
    assert rl.report(stopped)[-1] == "  preview did not run: the preview stopped answering: Not attached to an active page"
    assert rl.look_line([stopped], 1.0, ".tmp/review-look.json", ".tmp/look") == (
        "look: no layout was looked at, as the preview of Game did not run; full result in .tmp/review-look.json")


def test_review_look_retakes_a_blank_screenshot_and_asks_nothing_about_one_that_stays_blank():
    blank = {"project": "Game", "status": "opened", "title": "Game - Construct 3", "editor": "e",
             "warnings": [], "preview": {"started": True, "errors": [], "layouts": [
                 {"layout": "Objects", "shot": ".tmp/look/Objects.png", "findings": [], "errors": [],
                  "blank": {"tries": 3, "share": 0.99995}}]}}
    lines = rl.report(blank)
    assert "Objects.png" not in rl.brief(blank)
    assert lines[1] == ("layout 'Objects' (1 of 1): screenshot .tmp/look/Objects.png: 99.9% or more of it is one "
                        "colour after 3 shots 1 s apart, so the layout draws nothing in view at its start, or the preview "
                        "did not draw it. No question is asked about it. If it should show something, raise --settle, "
                        "or reach it in play with a shot step of a preview_project.py plan")
    assert not any(line.startswith("questions:") for line in lines)
    lines = rl.report({"project": "Game", "status": "opened", "title": "Game - Construct 3", "editor": "e",
                       "warnings": [], "preview": {"started": True, "errors": [], "layouts": [
                           {"layout": "Map", "shot": ".tmp/look/Map.png", "findings": [], "errors": [],
                            "blank": {"tries": 2, "share": None}}]}})
    assert lines[1] == ("layout 'Map' (1 of 1): screenshot .tmp/look/Map.png, taken when the layout was drawn; the "
                        "shot before showed one colour, not drawn yet")
    assert lines[2].startswith("questions:")


def test_review_look_finds_text_gathered_in_one_ninth_while_two_corners_stand_empty():
    """A title and a subtitle a line apart, each joining two facts with a middle dot, in the top-left
    with the other corners empty tell four items there: one finding naming the corners. Counts beside their
    icons, a status line across the bottom, the label of an object, texts in three corners and
    texts on a scrolling layer of a layout larger than the screen are no crowd."""
    title = text(1, "TitleText", [40, 40, 300, 80], "二十拍 · 十二种动法", [250, 36], align=("left", "top"))
    sub = text(2, "SubText", [40, 88, 360, 112], "八个空拍 · 同一套 7 / 2 / 5 / 4", [300, 22], align=("left", "top"))
    found = rl.findings(snap(title, sub))
    assert pairs(found) == [("crowd", [1, 2])], found
    assert found[0]["line"].startswith('the top-left of the screen holds 4 items of text (TitleText uid 1 "二十拍 · 十二种动法"')
    assert found[0]["line"].endswith("while the top-right, bottom-left, bottom-right corners stand empty: give each "
                                     "item its own corner or edge, and each text one thing rather than several "
                                     "joined by · or |")
    assert rl.worded("Round · 03") == 1 and rl.worded("[b]HP:[/b] 150 | ATK: 10") == 2 and rl.worded("00") == 0
    counts = [text(10 + n, "Counter", [40, 40 + 60 * n, 130, 90 + 60 * n], "00", [60, 40]) for n in range(3)]
    assert rules(rl, *counts) == []
    stats = text(20, "Stats", [2, 640, 1278, 680], "HP: 150 | ATK: 10 | DEF: 5", [400, 30], align=("left", "top"))
    keys = text(21, "Keys", [2, 680, 1278, 718], "Z Attack · X Run", [300, 30], align=("left", "top"))
    assert rules(rl, stats, keys) == []
    on_card = [inst(30, "Card", [20, 20, 400, 200]), dict(title, uid=31)]
    assert rules(rl, *on_card) == []
    corners = [text(40, "Wave", [40, 40, 200, 70], "Wave 3", [100, 30]),
               text(41, "Left", [1080, 40, 1240, 70], "12 left", [100, 30]),
               text(42, "Best", [40, 650, 200, 680], "Best 40 · Gold 7", [160, 30])]
    assert rules(rl, *corners) == []
    assert rules(rl, dict(title, layer="Game"), dict(sub, layer="Game"), size=(4000, 720)) == []


def test_review_look_pairs_each_label_text_and_glyph_with_the_shape_it_is_centred_on():
    """A label, the one text inside a shape, pairs on each axis its alignment and its box centre; a
    text beside a shape in a row pairs down; a glyph alone on a shape pairs both ways. A card that
    holds two texts and a glyph off the centre are left out, and a text set at the top of its shape
    pairs across only."""
    found = rl.optical_pairs([
        inst(1, "Button", [100, 600, 260, 660]),
        text(2, "ButtonLabel", [100, 606, 260, 660], "Start", [60, 24]),
        inst(3, "Toggle", [500, 600, 628, 664]),
        text(4, "ToggleLabel", [400, 600, 468, 664], "Sound", [60, 20], align=("left", "center")),
        inst(5, "Disc", [700, 300, 828, 428]),
        inst(6, "Play", [732, 321, 796, 385]),
        inst(7, "Card", [900, 100, 1100, 400]),
        text(8, "CardName", [900, 100, 1100, 140], "Strike", [80, 24]),
        text(9, "CardCost", [900, 360, 1100, 400], "2", [12, 24]),
        inst(10, "Panel", [100, 100, 400, 300]),
        text(11, "PanelTitle", [100, 100, 400, 140], "Shop", [80, 24]),
        inst(12, "Ring", [500, 100, 628, 228]),
        inst(13, "Gem", [500, 100, 532, 132]),
    ], LAYERS, 720)
    assert [(p["kind"], p["glyph"]["uid"], p["shape"]["uid"], p["axes"]) for p in found] == \
        [("label", 2, 1, [0, 1]), ("beside", 4, 3, [1]), ("label", 11, 10, [0]), ("glyph", 6, 5, [0, 1])]


def test_review_look_measures_ink_and_the_face_it_sits_on_from_two_shots():
    """ink() is what changed between a shot and the one with the glyph hidden, a faint fringe left
    out; face() is the part of a shape in the colour most of it shows, its shadow left out."""
    w, grey, ink_, paper, shade = 10, (117, 117, 117, 255), (255, 255, 255, 255), (239, 239, 239, 255), \
        (180, 180, 180, 255)
    bare = [grey if 1 <= n % w <= 7 and 1 <= n // w <= 7 else shade if n % w == 8 or n // w == 8 else paper
            for n in range(w * w)]
    shown = [ink_ if 3 <= n % w <= 5 and 2 <= n // w <= 4 else (130, 130, 130, 255) if n == 66 else bare[n]
             for n in range(w * w)]
    empty = [paper] * (w * w)
    box, centroid = rl.ink(w, shown, bare, [0, 0, w, w])
    assert box == [3, 2, 6, 5] and centroid == (4.5, 3.5)
    assert rl.ink(w, shown, bare, [0, 6, w, w]) is None
    assert rl.face(w, bare, empty, [0, 0, w, w]) == [1, 1, 8, 8]


def test_review_look_centres_a_label_by_its_capitals_or_chinese():
    """The line a text is centred by is that of its capitals and digits, else its Chinese: "Play"
    is centred as "P" is, and a text of short lowercase letters by all of them."""
    assert [rl.reference(t) for t in ("Play", "HP 生命", "开始游戏，", "Level 3", "menu")] == \
        ["P", "HP", "开始游戏", "L3", None]


def test_review_look_finds_a_label_or_glyph_off_the_centre_of_its_face():
    """A label whose ink sits off its face's centre by more than the larger of OPTICAL_PX and
    OPTICAL_EM of its em is named with the box change that fixes it: a label on a shape shrinks its
    box, a text beside one moves it. A glyph is named with the move that centres its area."""
    button, label = inst(1, "Button", [32, 32, 224, 128]), text(2, "Label", [32, 32, 224, 128], "Continue",
                                                                   [106, 32], em=26.7)
    disc, tri = inst(5, "Disc", [640, 288, 768, 416]), inst(6, "Tri", [672, 320, 736, 384])
    measured = [{"pair": {"kind": "label", "glyph": label, "shape": button, "axes": [0, 1]}, "offset": [0.5, -3.0]},
                {"pair": {"kind": "label", "glyph": dict(label, uid=3), "shape": button, "axes": [0, 1]},
                 "offset": [0, -1.5]},
                {"pair": {"kind": "glyph", "glyph": tri, "shape": disc, "axes": [0, 1]}, "offset": [0, 10.75]},
                {"pair": {"kind": "beside", "glyph": dict(label, uid=4), "shape": button, "axes": [1]},
                 "offset": [0, -2.0]}]
    found = rl.optical_findings(measured)
    assert pairs(found) == [("optical", [2, 1]), ("optical", [6, 5]), ("optical", [4, 1])]
    assert found[0]["line"] == ('Label uid 2 "Continue" on Button uid 1: its ink sits 3.0 px above the centre of '
                                "the shape's face, which a player sees as off centre: move its ink down 3 px by "
                                "shrinking its box from the top by 6 px")
    assert "its area sits 10.8 px below" in found[1]["line"] and "move it 11 px up" in found[1]["line"]
    assert found[2]["line"].endswith("move its ink down 2 px by moving its box as far")


def test_the_brief_asks_about_the_art_sheet_after_the_screenshots():
    """The contact sheet of art.py is one more picture under the same questions, last, and a reply must answer it."""
    result = {"preview": {"layouts": [{"layout": "Game", "shot": "shots/Game.png"}]}, "places": [],
              "art_sheet": "art/contact.png"}
    text = rl.brief(result)
    assert "1. Game: shots/Game.png\n2. Art sheet: art/contact.png" in text
    assert "The last picture, Art sheet, is no screenshot" in text
    lines, _, verdict = rl.check_reply(result, "\n".join(f"Game {q}: no" for q in range(1, 7)), "r.md", None)
    assert "  missing: Art sheet 1-6" in lines and not verdict["complete"], lines
