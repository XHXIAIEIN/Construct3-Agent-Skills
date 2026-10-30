"""art.py and svg_kit.py: the SVG route, drawings checked, rendered with their hit frames and taken by
the generator in place of the stand-ins. The browser is replaced by a renderer that paints each page
in the colour of the picture's role, so the tests run without one."""
import json
import re
import struct
import sys

import pytest

from tests.skill_helpers import SKILL, png, png_pixels, run, script_module, tool

art = script_module("art")
oe = script_module("open_in_editor")
svg_kit = script_module("svg_kit")
COIN = "coin-default-000.png"


class Painter:
    """Renders a page as one colour, the value its CSS gives the role --reward, over the drawing's box."""

    def __init__(self, root, exe):
        self.shots = []

    def shot(self, html, name, w, h=None):
        self.shots.append(name)
        if h is None:
            return png(w, 8, lambda x, y: (255, 255, 255, 255))
        colour = re.search(r"--reward:#([0-9A-F]{6})", html)[1]
        rgb = tuple(int(colour[i:i + 2], 16) for i in (0, 2, 4))
        return png(w, h, lambda x, y: (*rgb, 255) if 8 <= x < w - 8 and 8 <= y < h - 8 else (0, 0, 0, 0))

    def pages(self, html, name, w, tall):
        return [png(w, 8, lambda x, y: (255, 255, 255, 255))] * 2

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
    sheets = project / ".tmp" / "scripts" / "art"
    assert [p.name for p in art.sheet_pages(project)] == ["contact-1.png", "contact-2.png"]
    assert f"contact sheet: 2 pages, {sheets / 'contact-1.png'}, {sheets / 'contact-2.png'}" in out, out
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


def test_a_box_inside_a_rounded_box_takes_its_radius_less_the_gap():
    assert svg_kit.inner(0, 0, 100, 60, 16, 6) == {"x": 6, "y": 6, "w": 88, "h": 48, "r": 10}
    assert svg_kit.inner(**svg_kit.inner(0, 0, 100, 60, 8, 6), pad=4)["r"] == 0
    with pytest.raises(SystemExit, match="a gap of 30 px leaves nothing of a 100x60 box"):
        svg_kit.inner(0, 0, 100, 60, 16, 30)


def test_an_icon_set_fixes_the_stroke_radius_and_weight_of_every_icon(project):
    kit = svg_kit.Kit(project)
    icons = kit.icons(stroke=4, radius=6)
    with icons.drawing(COIN) as d:
        d.rect(20, 20, 120, 120)
        d.rect(**svg_kit.inner(20, 20, 120, 120, 6, 10))
        d.circle(80, 80, 20, line="ink")
    svg = (project / "art" / "coin-default-000.svg").read_text(encoding="utf-8")
    assert svg.count("fill:none;stroke:var(--reward);stroke-width:4;") == 2, svg
    assert 'rx="6"' in svg and "stroke:var(--ink);stroke-width:4" in svg
    with pytest.raises(SystemExit, match="takes its stroke of 4 px, not 2"):
        icons.drawing(COIN).circle(1, 1, 1, line_width=2)
    with pytest.raises(SystemExit, match="corners are 6 px at most, not 9"):
        icons.drawing(COIN).rect(0, 0, 9, 9, r=9)
    with pytest.raises(SystemExit, match="a line icon fills nothing"):
        icons.drawing(COIN).circle(1, 1, 1, fill="ink")
    with kit.icons(stroke=4, weight="solid").drawing(COIN) as d:
        d.circle(80, 80, 40)
    svg = (project / "art" / "coin-default-000.svg").read_text(encoding="utf-8")
    assert "fill:var(--reward);stroke:var(--reward);stroke-width:4" in svg
    with pytest.raises(SystemExit, match="the weights are line, solid"):
        kit.icons(weight="bold")


def test_an_eased_gradient_runs_between_two_roles_on_its_curve(project):
    kit = svg_kit.Kit(project)
    with kit.drawing(COIN) as d:
        d.rect(0, 0, 160, 160, fill=d.gradient("sky", "canvas", "reward", steps=3))
    svg = (project / "art" / "coin-default-000.svg").read_text(encoding="utf-8")
    assert art.svg_problems(svg, kit.items[COIN]) == []
    assert "fill:url(#coin-default-000-sky)" in svg and svg.count("<stop ") == 5
    mixes = [float(m) for m in re.findall(r"var\(--reward\) ([\d.]+)%", svg)]
    offsets = [float(m) for m in re.findall(r'offset="([\d.]+)%"', svg)]
    assert offsets == [0, 25, 50, 75, 100] and mixes[0] == 0 and mixes[-1] == 100
    assert mixes[1] < offsets[1] and abs(mixes[2] - 50) < 0.5 and mixes[3] > offsets[3], mixes
    with pytest.raises(SystemExit, match="defined twice"):
        d.gradient("sky", "canvas", "ink")
    with pytest.raises(SystemExit, match="the curves are linear, ease"):
        d.gradient("dusk", "canvas", "ink", ease="bounce")


def test_the_users_references_are_the_pictures_of_art_references_measured_on_one_page(tmp_path):
    """PNG, JPEG and WebP are references, embedded as data URLs, as a file: picture would taint the canvas that
    measures them; any other file there is named as not read."""
    folder = tmp_path / "art" / "references"
    assert art.references(tmp_path) == ([], [])
    folder.mkdir(parents=True)
    for name in ("b.JPG", "a.png", "c.webp", "d.bmp"):
        (folder / name).write_bytes(png(4, 2, lambda x, y: (255, 0, 0, 255)))
    refs, unread = art.references(tmp_path)
    assert [p.name for p in refs] == ["a.png", "b.JPG", "c.webp"] and [p.name for p in unread] == ["d.bmp"]
    assert art.png_size(refs[0]) == (4, 2)
    page = art.measure_page([[("reference: a.png", refs[0]), ("reference: b.JPG", refs[1])], [("game: <Map>", refs[0])]],
                            320, 180)
    assert page.count("<img data-measure src=\"data:image/png;base64,") == 2 and "data:image/jpeg;base64," in page
    assert "height:75px" in page and "game: &lt;Map&gt;" in page and "%%" not in art.MEASURE_JS


class Measurer:
    """Stands for the browser: the shot of a page, and the colours its script would have measured."""

    def __init__(self):
        self.page = self
        self.asked = []

    def shot(self, html, name, w, h=None):
        self.asked.append((name, w, h, html.count("<img data-measure")))
        return b"pair"

    def evaluate(self, script):
        assert script == "window.palettes"
        return [[{"hex": f"#00000{n}", "share": 1.0}] for n in range(self.asked[-1][3])]


def test_a_reference_pair_fits_the_references_and_the_screenshot_into_the_screenshots_shape(tmp_path):
    shot = tmp_path / "Map.png"
    shot.write_bytes(png(16, 9, lambda x, y: (0, 0, 0, 255)))
    renderer = Measurer()
    data, refs, own = art.reference_pair(renderer, [("reference: Map.png", shot), ("picked look: look.png", shot)],
                                         shot, "game: Map")
    assert data == b"pair" and refs == [[{"hex": "#000000", "share": 1.0}], [{"hex": "#000001", "share": 1.0}]]
    assert own == [{"hex": "#000002", "share": 1.0}]
    assert renderer.asked == [("pair-game-Map", 2 * (1067 + 12) + 12, None, 3)]


def test_the_contact_sheet_is_cut_into_pages_between_rows_and_a_heading_keeps_its_row():
    """A page ends halfway between two rows, never inside a figure, and is no taller than asked unless one row
    is; a heading goes onto the page of the row under it."""
    blocks = [[24, 50, True], [70, 600, False], [100, 600, False], [624, 1100, False],
              [1130, 1156, True], [1176, 1700, False], [1724, 2000, False]]
    spans = art.page_spans(blocks, 2024, 800)
    assert spans == [(0, 612), (612, 1115), (1115, 1712), (1712, 2024)]
    assert all(bottom - top <= 800 for top, bottom in spans)
    assert art.page_spans(blocks, 2024, 1200) == [(0, 1115), (1115, 2024)]
    assert art.page_spans(blocks, 2024, 4000) == [(0, 2024)]


@pytest.mark.skipif(not oe.browser_path(), reason="the contact sheet is rendered in Edge, Chrome or Chromium; "
                                                  "install one")
def test_every_page_of_the_contact_sheet_fits_what_a_model_reads_at_its_own_size(tmp_path):
    """Rendered in the machine's browser: forty pictures and a tall scene make several pages, each SHEET_W wide
    and no more than PAGE_H high."""
    (tmp_path / "art").mkdir()
    done = [{"file": f"thing{n // 4}-default-{n % 4:03d}.png", "width": 128, "height": 128} for n in range(40)]
    done.append({"file": "hall-default-000.png", "width": 1080, "height": 4000})
    for item in done:
        (tmp_path / "art" / item["file"]).write_bytes(png(item["width"] // 8, item["height"] // 8,
                                                          lambda x, y: (200, 60, 60, 255)))
    roles = {"canvas": (245, 240, 230), "ink": (33, 33, 33), "line": (120, 120, 120), "dim": (90, 90, 90)}
    renderer = art.Renderer(tmp_path, oe.browser_path())
    try:
        pages = renderer.pages(art.contact_page(tmp_path, {"palette": roles, "pixel_art": False}, done), "contact",
                               art.SHEET_W, art.PAGE_H)
    finally:
        renderer.close()
    sizes = [struct.unpack(">II", page[16:24]) for page in pages]
    assert len(sizes) >= 3 and all(w == art.SHEET_W and h <= art.PAGE_H for w, h in sizes), sizes
