"""pick_look.py: the user's look picked from the first play screen in three directions. The directions are
checked, rendered behind the picker with a look-judge brief, and the pick alone is written into the generator.
The browser is replaced by a renderer that paints each page in two of its roles, so the tests run without one."""
import ast
import copy
import json
import re
import sys

import pytest

from tests.skill_helpers import png, script_module, tool

pick_look = script_module("pick_look")
prepare_art = script_module("prepare_art")
svg_kit = script_module("svg_kit")
art = script_module("art")
VIEW = [64, 36]
LOOK = "the user's words: a calm night market"


class Painter:
    """Renders a page as its --canvas with a block of its --reward, at the size asked."""

    def __init__(self, root, exe, folder="art"):
        self.pages = []

    def shot(self, html, name, w, h=None):
        self.pages.append(name)
        canvas, reward = (tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
                          for c in (re.search(rf"--{r}:#([0-9A-F]{{6}})", html)[1] for r in ("canvas", "reward")))
        return png(w, h, lambda x, y: (*(reward if 8 <= x < 24 else canvas), 255))

    def close(self):
        pass


def direction(name, look, palette, **axes):
    base = {"rendering": "flat fills", "linework": "no outlines", "colour temperature": "neutral greys",
            "light direction": "no lighting", "proportions": "geometric proportions", "framing": "top-down view"}
    style = {"Paper and ink": pick_look.PAPER_AND_INK,
             "Ink wash": "ink wash, dry brush outlines, warm amber, light from above, soft proportions, top-down view",
             "Woodblock": "flat woodblock print, thick carved outlines, cool indigo, rim light from the right, chunky "
                          "proportions, three-quarter view"}[name]
    return {"name": name, "axes": base | axes, "right_when": f"{name} suits the game", "cost": f"{name} costs",
            "USER_LOOK": look, "ART_STYLE": style, "PALETTE": palette}


@pytest.fixture
def picker(project):
    """The game with the user's look, a small viewport, and three directions drawn with svg_kit."""
    wanted_path = project / "art" / "wanted.json"
    wanted = json.loads(wanted_path.read_text(encoding="utf-8"))
    wanted.update(view=VIEW, user_look=LOOK)
    wanted_path.write_text(json.dumps(wanted), encoding="utf-8")
    ink = wanted["palette"]
    warm = {r: [min(255, c[0] + 10), c[1], max(0, c[2] - 20)] for r, c in ink.items()}
    cool = {r: [c[0] // 2, c[1] // 2, min(255, c[2] + 40)] for r, c in ink.items()}
    directions = [direction("Paper and ink", "", ink),
                  direction("Ink wash", LOOK + ": the ink", warm, rendering="ink wash", linework="dry brush outlines",
                            **{"colour temperature": "warm amber"}),
                  direction("Woodblock", LOOK + ": the night", cool, rendering="woodblock print",
                            linework="thick carved outlines", framing="three-quarter view")]
    folder = project / ".tmp" / "scripts" / "pick-look"
    folder.mkdir(parents=True)
    (folder / "directions.json").write_text(json.dumps({"directions": directions}), encoding="utf-8")
    kit = svg_kit.Kit(project)
    for name in ("paper-and-ink", "ink-wash", "woodblock"):
        with kit.screen(name) as d:
            d.rect(0, 0, *VIEW, fill="canvas")
            d.circle(16, 18, 8, fill=d.gradient("glow", "reward", "canvas") if name == "ink-wash" else "reward")
            d.text(60, 8, "SCORE", kind="name", fill="dim", anchor="end")
    return project, folder, directions


def main(monkeypatch, capsys, root, *flags):
    monkeypatch.setattr(art, "Renderer", Painter)
    monkeypatch.setattr(sys, "argv", ["pick_look.py", "--project", str(root), "--browser", "browser", *flags])
    code = pick_look.main()
    return code, capsys.readouterr().out


def test_without_directions_it_writes_the_art_agents_brief(project):
    """The art agent's whole task: the user's look, the three directions, the kit and the form of directions.json,
    whose paper and ink ART_STYLE fixes every dimension."""
    wanted = json.loads((project / "art" / "wanted.json").read_text(encoding="utf-8"))
    wanted["user_look"] = LOOK
    (project / "art" / "wanted.json").write_text(json.dumps(wanted), encoding="utf-8")
    code, out = tool(project, "pick_look")
    assert code == 0, out
    assert out.splitlines()[-1].startswith("no directions.json yet; next: start a construct3:art-drawer sub-agent")
    brief = (project / ".tmp" / "scripts" / "pick-look" / "draw-brief.md").read_text(encoding="utf-8")
    assert LOOK in brief and "kit.screen(\"ink-wash\")" in brief and "d.text(x, y, words, kind=...)" in brief
    assert "never only in their colours" in brief and "tag, name, body, title, number, display" in brief
    form = json.loads(brief.split("```json\n", 1)[1].split("\n```", 1)[0])
    assert set(form) == set(pick_look.FIELDS) and set(form["axes"]) == set(prepare_art.DIMENSIONS)
    assert form["PALETTE"]["ink"] == [33, 33, 33] and prepare_art.left_open(form["ART_STYLE"]) == []


def test_the_directions_are_rendered_behind_the_picker_and_the_last_line_stops_for_the_user(picker, monkeypatch,
                                                                                         capsys):
    project, folder, directions = picker
    code, out = main(monkeypatch, capsys, project)
    assert code == 0, out
    lines = out.splitlines()
    assert lines[0] == "checked: 3 directions, every two apart in 2 dimensions or more"
    assert lines[-1].startswith("stop: show the user ") and "--pick NAME" in lines[-1], lines[-1]
    assert any(line.startswith("brief: give ") and "construct3:look-judge" in line for line in lines), out
    header = next(i for i, line in enumerate(lines) if line.startswith("direction "))
    assert re.split(r"\s*\|\s*", lines[header]) == ["direction", "axis", "when it is right", "cost"]
    assert lines[header + 2].startswith("Ink wash ") and "ink wash; dry brush outlines; warm amber" in lines[header + 2]
    for name in ("paper-and-ink", "ink-wash", "woodblock"):
        assert (folder / f"{name}.png").is_file()
    page = (folder / "index.html").read_text(encoding="utf-8")
    assert "Copyright (c) 2026 Emil Kowalski" in page and 'aria-label="Prototype variants"' in page
    assert page.count('class="proto-picker-item"') == 3 and "proto-picker-replay\"" not in page
    assert "'<img src=\"woodblock.png\" alt=\"Woodblock\">'" in page and "ArrowRight" in page
    assert "url.searchParams.set('v', i + 1)" in page
    judge = (folder / "judge-brief.md").read_text(encoding="utf-8")
    assert "3. Woodblock: " in judge and f"{len(script_module("review_look").QUESTIONS) + 1}. {pick_look.DIFFERS}" in judge


def test_the_renders_take_each_directions_palette_and_the_kinds_of_text(picker):
    project, folder, directions = picker
    wanted = json.loads((project / "art" / "wanted.json").read_text(encoding="utf-8"))
    html = pick_look.page((folder / "ink-wash.svg").read_text(encoding="utf-8"), directions[1]["PALETTE"], wanted)
    assert "--canvas:#FFFFEB" in html and "svg text.name{font-size:%gpx !important" % (16 * 4 / 3) in html
    assert "font-weight:500 !important" in html                     # a title in its medium weight


def breaks(directions, folder):
    """Each way a direction set is refused, by what the refusal says."""
    def edit(change):
        d = copy.deepcopy(directions)
        change(d)
        return d

    def svg(name, text):
        (folder / f"{name}.svg").write_text(text, encoding="utf-8")

    yield "differ in colour temperature alone", edit(lambda d: d[2].update(axes=dict(d[1]["axes"],
                                                                                    **{"colour temperature": "cool"})))
    yield "paper and ink keeps the template's PALETTE, and its ink differ", \
        edit(lambda d: d[0]["PALETTE"].update(ink=[0, 0, 0]))
    yield "its ART_STYLE names no framing", edit(lambda d: d[1].update(ART_STYLE="ink wash, dry brush outlines, warm "
                                                                                  "amber, light from above, soft proportions"))
    yield "its PALETTE has the roles canvas", edit(lambda d: d[1]["PALETTE"].pop("flash"))
    yield "2 directions; the picker takes 3 to 5", edit(lambda d: d.pop())
    yield "2 directions have an empty USER_LOOK", edit(lambda d: d[1].update(USER_LOOK=""))
    yield "its axes are not one phrase for each of rendering", edit(lambda d: d[1]["axes"].pop("framing"))
    svg("woodblock", f'<svg xmlns="http://www.w3.org/2000/svg" width="{VIEW[0]}" height="{VIEW[1]}">'
                     f'<rect width="9" height="9" fill="#ffcc00"/><text x="1" y="9">0</text></svg>')
    yield "woodblock.svg: it names a colour, '#ffcc00'", directions
    yield "a label has no class, and every label is a kind of TEXT_SIZE", directions


@pytest.mark.parametrize("n", range(9))
def test_a_direction_set_that_breaks_a_rule_is_refused(picker, n):
    project, folder, directions = picker
    said, refused = list(breaks(directions, folder))[n]
    (folder / "directions.json").write_text(json.dumps({"directions": refused}), encoding="utf-8")
    code, out = tool(project, "pick_look")
    assert code == 1 and said in out, out
    assert out.splitlines()[-1].startswith("next: fix the directions and run ")
    assert not (folder / "index.html").exists()


def test_the_pick_writes_its_values_alone_keeps_its_screen_and_removes_the_picker(picker, monkeypatch, capsys):
    project, folder, directions = picker
    main(monkeypatch, capsys, project)
    generator = project / "tools" / "build_project.py"
    before = generator.read_text(encoding="utf-8")
    code, out = main(monkeypatch, capsys, project, "--pick", "ink")
    assert code == 1 and "no such direction; the directions are Paper and ink, Ink wash, Woodblock; closest: Ink " \
                         "wash" in out, out
    code, out = main(monkeypatch, capsys, project, "--pick", "Ink wash", "--dry-run")
    assert code == 0 and out.splitlines()[-1].startswith("dry run:") and generator.read_text(encoding="utf-8") == before
    code, out = main(monkeypatch, capsys, project, "--pick", "ink-wash")
    assert code == 0 and out.splitlines()[0] == "picked: Ink wash", out
    assert out.splitlines()[-1].startswith("next: run python tools/build_project.py, then ")
    after = generator.read_text(encoding="utf-8")
    assert ast.literal_eval(pick_look.assigned(after)["USER_LOOK"]) == LOOK + ": the ink"
    assert f'ART_STYLE = "{directions[1]["ART_STYLE"]}"' in after
    assert '    "ink": (43, 33, 13),               # player, labels, a key\'s box, a bar\'s fill' in after
    changed = [line for line in after.splitlines() if line not in before.splitlines()]
    recoloured = [r for r, c in directions[1]["PALETTE"].items() if c != directions[0]["PALETTE"][r]]
    assert len(changed) == 2 + len(recoloured), changed
    assert (project / "art" / "look.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" and not folder.exists()


def test_art_waits_for_the_pick_of_the_users_look_and_then_refers_to_it(project):
    """With USER_LOOK and no art/look.png, both routes ask for the picker first; once it is there, the drawings'
    brief names it, and on the image route it is every prompt's reference in place of the key picture."""
    wanted_path = project / "art" / "wanted.json"
    wanted = json.loads(wanted_path.read_text(encoding="utf-8"))
    wanted.update(user_look=LOOK, style="ink wash, dry brush outlines, warm amber, light from above, soft "
                                         "proportions, top-down view")
    wanted_path.write_text(json.dumps(wanted), encoding="utf-8")
    code, out = tool(project, "art")
    assert code == 0 and "it is not picked yet: run python " in out.splitlines()[-1], out
    assert "pick_look.py" in out.splitlines()[-1]
    image = dict(wanted, images=[dict(i, route="image") for i in wanted["images"]] + [
        {"file": "rose-default-000.png", "kind": "circle", "width": 64, "height": 64, "origin": [0.5, 0.5],
         "subject": "a rose", "role": "reward"}])
    assert prepare_art.list_prompts(project, image, "skill")[-1] == \
        "to make: 2, to prepare: 0, done: 0; next: python skill/scripts/pick_look.py"
    (project / "art" / "look.png").write_bytes(png(4, 4, lambda x, y: (1, 2, 3, 255)))
    lines = prepare_art.list_prompts(project, image, "skill")
    assert not any(line.startswith("key picture:") for line in lines), lines
    assert "make rose-default-000: ratio 1:1, for a 64x64 box, art/look.png as the reference image -> " \
           "art/raw/rose-default-000.png" in lines
    code, out = tool(project, "art")
    brief = (project / ".tmp" / "scripts" / "art" / "brief.md").read_text(encoding="utf-8")
    assert "The look the user picked is its first play screen in " in brief and "art/look.png" in brief


class Measurer(Painter):
    """A Painter that also stands for the script the page runs: one colour measured from each picture."""

    def __init__(self, root, exe, folder="art"):
        super().__init__(root, exe, folder)
        self.page = self
        self.pictures = 0

    def shot(self, html, name, w, h=None):
        self.pages.append(name)
        self.pictures = html.count("<img data-measure")
        return b""

    def evaluate(self, script):
        return [[{"hex": "#2B2140", "share": 0.41}, {"hex": "#E8A33C", "share": 0.12}]] * self.pictures


def test_the_draw_brief_names_the_users_references_and_the_colours_measured_from_them(project, monkeypatch):
    """The two directions from the user's look take their colours from the references, measured, not from words;
    with no browser the brief still names the references."""
    folder = project / "art" / "references"
    folder.mkdir()
    for name in ("market.jpg", "stall.png"):
        (folder / name).write_bytes(png(4, 4, lambda x, y: (40, 30, 60, 255)))
    monkeypatch.setattr(art, "Renderer", Measurer)
    refs = pick_look.reference_colours(project, "browser")
    assert [(r.name, c[0]["hex"]) for r, c in refs] == [("market.jpg", "#2B2140"), ("stall.png", "#2B2140")]
    wanted = json.loads((project / "art" / "wanted.json").read_text(encoding="utf-8"))
    brief = pick_look.draw_brief(project, wanted, project / ".tmp", "skill", refs)
    assert f"Open each with the Read tool: {(folder / 'market.jpg').as_posix()}, " in brief
    assert "- market.jpg: #2B2140 41%, #E8A33C 12%\n" in brief and "not from the words of the look" in brief
    blind = pick_look.draw_brief(project, wanted, project / ".tmp", "skill", pick_look.reference_colours(project, None))
    assert "stall.png." in blind and "measured" not in blind
    assert "references" not in pick_look.draw_brief(project, wanted, project / ".tmp", "skill")
