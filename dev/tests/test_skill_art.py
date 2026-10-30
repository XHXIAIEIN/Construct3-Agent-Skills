"""art.py and svg_kit.py: the SVG route, drawings checked, rendered with their hit frames and taken by
the generator in place of the stand-ins. The browser is replaced by a renderer that paints each page
in the colour of the picture's role, so the tests run without one."""
import json
import re
import sys

import pytest

from tests.skill_helpers import SKILL, png, png_pixels, run, script_module, tool

art = script_module("art")
svg_kit = script_module("svg_kit")
COIN = "coin-default-000.png"


class Painter:
    """Renders a page as one colour, the value its CSS gives the role --reward, over the drawing's box."""

    def __init__(self, root, exe):
        self.pages = []

    def shot(self, html, name, w, h=None):
        self.pages.append(name)
        if h is None:
            return png(w, 8, lambda x, y: (255, 255, 255, 255))
        colour = re.search(r"--reward:#([0-9A-F]{6})", html)[1]
        rgb = tuple(int(colour[i:i + 2], 16) for i in (0, 2, 4))
        return png(w, h, lambda x, y: (*rgb, 255) if 8 <= x < w - 8 and 8 <= y < h - 8 else (0, 0, 0, 0))

    def close(self):
        pass


def main(monkeypatch, capsys, root, *flags):
    monkeypatch.setattr(art, "Renderer", Painter)
    monkeypatch.setattr(sys, "argv", ["art.py", "--project", str(root), "--browser", "browser", *flags])
    code = art.main()
    return code, capsys.readouterr().out


def drawing(root, text):
    (root / "art").mkdir(exist_ok=True)
    (root / "art" / "coin-default-000.svg").write_text(text, encoding="utf-8")


def test_the_generator_asks_for_drawings_on_the_svg_route(project):
    """The template's pictures take the SVG route, and wanted.json carries what a drawing needs: the
    roles, the grid, the line width and each picture's role."""
    wanted = json.loads((project / "art" / "wanted.json").read_text(encoding="utf-8"))
    assert wanted["images"][0]["route"] == "svg" and wanted["images"][0]["role"] == "reward"
    assert wanted["palette"]["ink"] == [33, 33, 33] and wanted["unit"] == 32 and wanted["line_width"] == 3
    code, out = tool(project, "art")
    assert code == 0, out
    assert re.search(r"^coin-default-000\s+svg\s+draw\s+draw art/coin-default-000.svg$", out, re.M), out
    brief = project / ".tmp" / "scripts" / "art" / "brief.md"
    assert out.splitlines()[-1].startswith("draw: 1; next: start a construct3:art-drawer sub-agent with ")
    text = brief.read_text(encoding="utf-8")
    assert "| coin-default-000.png | 160x160 | 0.5, 0.5 | reward | a gold coin seen from the front |" in text
    assert "svg_kit.py" in text and "three rounds at most" in text


def test_a_drawing_is_rendered_with_its_hit_frame_and_the_generator_takes_it(project, monkeypatch, capsys):
    (project / "tools" / "drawings.py").write_text(
        "import svg_kit\nkit = svg_kit.Kit()\n"
        "with kit.drawing('coin-default-000.png') as d:\n"
        "    d.circle(80, 80, 64, fill='reward', line='ink', grain=True)\n", encoding="utf-8")
    code, out = main(monkeypatch, capsys, project)
    assert code == 0, out
    assert "coin-default-000: art/coin-default-000.svg -> art/coin-default-000.png 160x160 and its hit frame" in out
    assert "generator: ok:" in out and out.splitlines()[-1].startswith("ok: 1 pictures from art/"), out
    picture, hit = png_pixels(project / "art" / COIN), png_pixels(project / "art" / "coin-default-000.hit.png")
    assert picture[80][80] == (61, 90, 254, 255) and hit[80][80] == (255, 255, 255, 255)
    assert picture[0][0] == (0, 0, 0, 0)
    assert (project / "images" / COIN).read_bytes() == (project / "art" / COIN).read_bytes()
    svg = (project / "art" / "coin-default-000.svg").read_text(encoding="utf-8")
    assert 'filter="url(#coin-default-000-grain)"' in svg and "fill:var(--reward)" in svg
    assert (project / ".tmp" / "scripts" / "art" / "contact.png").is_file()
    code, out = main(monkeypatch, capsys, project, "--status")
    assert re.search(r"^coin-default-000\s+svg\s+done\s+-$", out, re.M), out


@pytest.mark.parametrize("text, problem", [
    ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64"/></svg>',
     "it is 64x64, and art() asks 160x160"),
    ('<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160"><circle r="9" fill="#ffcc00"/></svg>',
     "it names a colour, '#ffcc00', where a role of PALETTE goes"),
    ('<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160"><circle r="9" style="fill:gold"/></svg>',
     "it names a colour, 'fill:gold'"),
    ('<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160"><defs><linearGradient id="g"/></defs>'
     '<circle r="9" style="fill:var(--reward)"/></svg>',
     "its id 'g' does not start with 'coin-default-000-'"),
])
def test_a_drawing_that_leaves_its_box_or_its_roles_is_refused(project, monkeypatch, capsys, text, problem):
    """Refused before it is rendered, counted as a refusal of the picture, and after three it keeps its
    stand-in."""
    drawing(project, text)
    code, out = main(monkeypatch, capsys, project)
    assert code == 1 and "coin-default-000: art/coin-default-000.svg refused (refusal 1 of 3" in out, out
    assert problem in out, out
    assert not (project / "art" / COIN).exists()


def test_a_drawing_refused_three_times_keeps_its_stand_in(project, monkeypatch, capsys):
    for n in range(3):
        drawing(project, f'<svg xmlns="http://www.w3.org/2000/svg" width="{n + 1}" height="1"></svg>')
        code, out = main(monkeypatch, capsys, project)
    assert re.search(r"^coin-default-000\s+svg\s+stand-in\s+keeps its stand-in", out, re.M), out
    code, out = main(monkeypatch, capsys, project)
    assert code == 0 and out.splitlines()[-1] == "ok: 0 pictures from art/, 1 keep their stand-in", out


def test_the_kit_names_roles_and_prefixes_its_ids(project):
    kit = svg_kit.Kit(project)
    with kit.drawing(COIN) as d:
        d.rect(8, 8, 32, 32, fill=d.shade("reward"), line="ink", rough=True)
        d.stroke([(10, 10), (40, 30), (70, 20)], "ink")
        with d.group(transform="rotate(10 80 80)"):
            d.ellipse(80, 80, 40, 30, fill="reward", wash=True)
    svg = (project / "art" / "coin-default-000.svg").read_text(encoding="utf-8")
    assert art.svg_problems(svg, kit.items[COIN]) == []
    assert "color-mix(in srgb, var(--reward), var(--ink) 30%)" in svg
    assert set(re.findall(r'id="([^"]+)"', svg)) == {"coin-default-000-rough", "coin-default-000-wash"}
    with pytest.raises(SystemExit, match="'gold' is no role of PALETTE"):
        kit.drawing(COIN).circle(1, 1, 1, fill="gold")
    with pytest.raises(SystemExit, match="art\\(\\) asks for no such picture"):
        kit.drawing("gem-default-000.png")


def test_the_kit_draws_pixel_art_on_the_grid_in_roles_alone(project):
    """In pixel art a drawing is rows of pixels in roles, with hard edges: no texture and no mixed shade."""
    wanted = json.loads((project / "art" / "wanted.json").read_text(encoding="utf-8"))
    wanted.update(pixel_art=True, unit=8)
    wanted["images"][0].update(width=16, height=16)
    (project / "art" / "wanted.json").write_text(json.dumps(wanted), encoding="utf-8")
    kit = svg_kit.Kit(project)
    with kit.drawing(COIN) as d:
        d.pixels([" rr ", "rrrr", "rkkr", " rr "], {"r": "reward", "k": "ink"}, 6, 6)
    svg = (project / "art" / "coin-default-000.svg").read_text(encoding="utf-8")
    assert 'shape-rendering="crispEdges"' in svg and svg.count("<rect") == 6
    with pytest.raises(SystemExit, match="pixel art keeps hard edges"):
        kit.drawing(COIN).circle(1, 1, 1, fill="ink", grain=True)
    with pytest.raises(SystemExit, match="pixel art takes the roles of PALETTE alone"):
        kit.drawing(COIN).shade("reward")


def test_a_picture_lost_on_the_canvas_and_frames_that_drift_are_found(project):
    """art.contrast: a pale picture on the white canvas; art.frames: two frames of one animation whose feet stand
    on different rows. Three versions that keep a finding leave it for the hand-over."""
    wanted = json.loads((project / "art" / "wanted.json").read_text(encoding="utf-8"))
    item = wanted["images"][0]
    frames = [dict(item, file=f"hero-walk-00{i}.png", width=32, height=32) for i in range(2)]
    pale = png(160, 160, lambda x, y: (240, 240, 240, 255) if 20 <= x < 140 and 20 <= y < 140 else (0, 0, 0, 0))
    (project / "art" / COIN).write_bytes(pale)
    for i, f in enumerate(frames):
        (project / "art" / f["file"]).write_bytes(
            png(32, 32, lambda x, y, i=i: (33, 33, 33, 255) if 8 <= x < 24 and 4 <= y < 28 - 3 * i else (0, 0, 0, 0)))
    found = art.look_findings(project, wanted, [item, *frames])
    assert [line.split(":")[0] for _, line in found] == ["art.contrast", "art.frames"], found
    assert "0% of its edge reads 3:1 on the canvas #FFFFFF" in found[0][1]
    assert "hero-walk: its frames stand on rows 24 to 27" in found[1][1]
    for n in range(3):
        (project / "art" / COIN).write_bytes(pale[:-12] + bytes([n]) + pale[-11:])     # another version, as pale
        fix, kept = art.counted(project, found[:1])
    assert fix == [] and kept[0].endswith("still so after 3 versions: name it in the hand-over"), kept


def test_two_kinds_drawn_alike_are_found_and_poses_of_one_are_not(project):
    """art.alike: two pictures of one box for different subjects that look the same cell by cell; a colour of
    its own tells one apart, and the frames of one animation are poses of one subject."""
    wanted = json.loads((project / "art" / "wanted.json").read_text(encoding="utf-8"))
    item = wanted["images"][0]
    blob = lambda colour: png(32, 32, lambda x, y: colour if 6 <= x < 26 and 6 <= y < 26 else (0, 0, 0, 0))
    kinds = [dict(item, file="goblin-default-000.png", width=32, height=32, subject="a goblin"),
             dict(item, file="orc-default-000.png", width=32, height=32, subject="an orc"),
             dict(item, file="slime-default-000.png", width=32, height=32, subject="a slime"),
             dict(item, file="hero-walk-000.png", width=32, height=32, subject="the hero, walk 1"),
             dict(item, file="hero-walk-001.png", width=32, height=32, subject="the hero, walk 2"),
             dict(item, file="hero-default-000.png", width=32, height=32, subject="the hero, standing")]
    for k, colour in zip(kinds, [(200, 40, 40, 255), (201, 40, 40, 255), (40, 160, 60, 255), (9, 9, 9, 255),
                                 (9, 9, 9, 255), (9, 9, 9, 255)]):
        (project / "art" / k["file"]).write_bytes(blob(colour))
    found = art.alike_findings(project, kinds)
    assert [line for _, line in found] == [
        "art.alike: orc-default-000 and goblin-default-000 look the same, though one is 'a goblin' and the other "
        "'an orc': give each a shape, a colour or a mark of its own"], found
