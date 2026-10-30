"""bake_font.py and the template's Sprite Fonts in pixel art: the characters a game uses, baked from a
BDF pixel font into the images of its text types."""
import json
from pathlib import Path

from tests.skill_helpers import SKILL, edit, install, new_project, run, template_module, tool
import c3project as c3

FONT = "fusion-pixel-8px-proportional-zh_hans"


def bdf(path: Path, glyphs: dict[str, tuple[int, list[str]]]) -> Path:
    """A BDF font of pixel size 8: each glyph its advance and its rows top to bottom, '#' drawn, one
    character a column, its box's bottom on the baseline."""
    out = ["STARTFONT 2.1", "FONT -test-Pixel-Medium-R-Normal--8-80-75-75-P-50-ISO10646-1", "SIZE 8 75 75",
           "FONTBOUNDINGBOX 8 8 0 -2", "STARTPROPERTIES 1", "PIXEL_SIZE 8", "ENDPROPERTIES", f"CHARS {len(glyphs)}"]
    for c, (adv, rows) in glyphs.items():
        w = max((len(r) for r in rows), default=0)
        out += [f"STARTCHAR U+{ord(c):04X}", f"ENCODING {ord(c)}", f"DWIDTH {adv} 0", f"BBX {w} {len(rows)} 0 0",
                "BITMAP", *(f"{int(r.replace('#', '1').replace('.', '0').ljust(8, '0'), 2):02X}" for r in rows),
                "ENDCHAR"]
    path.write_text("\n".join(out + ["ENDFONT", ""]), encoding="utf-8")
    return path


def ascii_font(path: Path, **extra: tuple[int, list[str]]) -> Path:
    """Printable ASCII as 4x6 boxes 5 px apart, a space 3 px wide, and the glyphs of `extra`."""
    glyphs = {" ": (3, [])} | {chr(c): (5, ["####"] * 6) for c in range(0x21, 0x7F)}
    return bdf(path, glyphs | {c: g for c, g in extra.items()})


def pixel_cache(tmp_path: Path, monkeypatch) -> Path:
    cache = tmp_path / "fonts"
    cache.mkdir()
    ascii_font(cache / f"{FONT}.bdf", **{"中": (8, ["########"] * 7), "文": (8, ["#.#.#.#."] * 7), "·": (3, ["#"])})
    monkeypatch.setenv("CONSTRUCT3_RAG_FONT_CACHE", str(cache))
    return cache


def label_project(root: Path, text: str) -> Path:
    """A project with one Sprite Font type, Label, whose instance shows `text`, a sheet that sets it to
    "得" & a number, and tools/pixel-font.json naming Label."""
    new_project(root)
    for folder in ("objectTypes", "layouts", "eventSheets", "tools", "images"):
        (root / folder).mkdir()
    (root / "objectTypes" / "Label.json").write_text(json.dumps(
        {"name": "Label", "plugin-id": "Spritefont2", "sid": 1, "image": {"width": 8, "height": 8}}), encoding="utf-8")
    (root / "layouts" / "Game.json").write_text(json.dumps({"name": "Game", "layers": [{"name": "HUD", "instances": [
        {"type": "Label", "properties": {"text": text, "character-set": ""}, "world": {}}]}]}), encoding="utf-8")
    (root / "eventSheets" / "Game.json").write_text(json.dumps({"name": "Game", "events": [{"actions": [
        {"id": "set-text", "objectClass": "Label", "parameters": {"text": '"得""" & Score'}}]}]}), encoding="utf-8")
    (root / "tools" / "pixel-font.json").write_text(json.dumps({"font": FONT, "types": ["Label"]}), encoding="utf-8")
    return root


def label(root: Path) -> dict:
    return c3.load(root / "layouts" / "Game.json")["layers"][0]["instances"][0]["properties"]


def test_bake_font_bakes_the_characters_in_use_and_keeps_what_it_is_told_to_add(tmp_path, monkeypatch):
    """A run bakes the instance's text, the sheet's strings and printable ASCII, a cell of the font's
    pixel size each, white where the glyph draws; the advances that differ from the cell go into the
    spacing data. --add keeps its characters in tools/pixel-font.json, --replace drops what is not in
    use, --check lists what is not baked, and a character the font lacks fails the run."""
    pixel_cache(tmp_path, monkeypatch)
    root = label_project(tmp_path / "game", "中 A")
    script = SKILL / "scripts" / "bake_font.py"
    code, out = run(root, script)
    # The font has no 得, which the sheet's string holds
    assert code == 1 and "the font lacks 1 characters in use, which draw as nothing: 得" in out, out
    props = label(root)
    chars = props["character-set"]
    assert "中" in chars and '"' in chars and "A" in chars and " " not in chars and "得" not in chars
    assert (props["character-width"], props["character-height"]) == (8, 8)
    assert [5, "".join(c for c in chars if c != "中")] in json.loads(props["spacing-data"])
    assert json.loads(props["spacing-data"])[-1] == [3, " "]
    w, h, px = c3.png_rgba((root / "images" / "label.png").read_bytes())
    assert (w, h) == (256, -(-len(chars) // 32) * 8)
    at = chars.index("中")
    cell = [px[(at // 32 * 8 + y) * w + at % 32 * 8 + x] for y in range(8) for x in range(8)]
    # The font draws nothing under its baseline, so the seven rows end at the cell's bottom
    assert cell[8:] == [(255, 255, 255, 255)] * 56 and set(cell[:8]) == {(0, 0, 0, 0)}
    image = c3.load(root / "objectTypes" / "Label.json")["image"]
    assert (image["width"], image["height"]) == (w, h)

    code, out = run(root, script, "--check")
    assert code == 1 and "1 characters in use are not in the Sprite Font images" in out and "得" in out, out
    edit(root, "eventSheets/Game.json", lambda d: d["events"][0]["actions"][0]["parameters"].update(text="Score"))
    code, out = run(root, script, "--add", "文")
    assert code == 0 and out.splitlines()[-1].startswith("ok:") and "文" in label(root)["character-set"], out
    assert c3.load(root / "tools" / "pixel-font.json")["added"] == "文"
    code, out = run(root, script, "--check")
    assert code == 0, out
    # The manifest's added characters outlive a run that does not name them
    edit(root, "layouts/Game.json", lambda d: d["layers"][0]["instances"][0]["properties"].update(text="A"))
    run(root, script, "--replace", "--add", "")
    assert "中" not in label(root)["character-set"] and "文" not in label(root)["character-set"]
    assert c3.load(root / "tools" / "pixel-font.json")["added"] == ""


def test_bake_font_needs_a_font_and_a_type(tmp_path, monkeypatch):
    monkeypatch.setenv("CONSTRUCT3_RAG_FONT_CACHE", str(tmp_path / "empty"))
    root = label_project(tmp_path / "game", "A")
    code, out = run(root, SKILL / "scripts" / "bake_font.py")
    assert code == 2 and f"no font: {FONT} is not a BDF file, and" in out and f"holds no {FONT}.bdf" in out, out
    code, out = run(root, SKILL / "scripts" / "bake_font.py", "--types", "Score")
    assert code == 2 and "not Sprite Font types of this project: Score. Its Sprite Fonts: Label" in out, out


def test_template_draws_pixel_art_text_in_sprite_fonts_sized_by_the_font(tmp_path, monkeypatch):
    """In pixel art with the font in the cache a text type is a Sprite Font and a label an instance at
    scale size / UNIT, tinted to its role; its box is the font's advances, in whole units. Without the
    font it stays a Text."""
    cache = pixel_cache(tmp_path, monkeypatch)
    t = template_module(VIEW="VIEW_W, VIEW_H = 320, 180")
    t.ROOT = tmp_path
    assert t.text_type("Score")["plugin-id"] == "Spritefont2" and t._sprite_fonts == ["Score"]
    inst = t.text_inst("Score", "AB", 0, 0, 16, 16, size=16, color="ink", on="canvas")
    assert inst["properties"]["scale"] == 2 and "font" not in inst["properties"]
    assert inst["world"]["color"] == [*(v / 255 for v in t.PALETTE["ink"]), 1]
    # "中A" is 8 + 5 px at scale 1, two units; a line is one
    assert t.label_box("中A", 8) == (16, 8) and t.line_height(16) == 16 and t.text_px(" ", 8) == 2
    (cache / f"{FONT}.bdf").unlink()
    t = template_module(VIEW="VIEW_W, VIEW_H = 320, 180")
    assert t.text_type("Score")["plugin-id"] == "Text"


def test_template_lowers_a_sprite_font_label_by_whole_font_pixels(tmp_path, monkeypatch):
    """A Sprite Font cell holds its baseline as far above its bottom as the deepest ASCII descender, so
    optical_drop() is the cell's centre less the centre of "H" in font pixels, times the scale."""
    cache = pixel_cache(tmp_path, monkeypatch)
    font = cache / f"{FONT}.bdf"
    # "g" hangs 2 px below the baseline, so "H", 6 px high, fills the cell's top 6 rows and sits 1 px
    # above the cell's centre
    font.write_text(font.read_text(encoding="utf-8").replace("ENCODING 103\nDWIDTH 5 0\nBBX 4 6 0 0",
                                                             "ENCODING 103\nDWIDTH 5 0\nBBX 4 6 0 -2"), encoding="utf-8")
    t = template_module(VIEW="VIEW_W, VIEW_H = 320, 180")
    assert [t.optical_drop("Play", size) for size in (8, 16)] == [1, 2]
    assert t.optical_drop("menu", 16) == 0


def test_pixel_art_game_bakes_its_fonts_and_check_look_finds_a_character_left_out(tmp_path, monkeypatch):
    """The stand-in game at 320x180 with the font in the cache: its labels are Sprite Fonts, the run
    bakes them and passes its check, and check_look.py names a character that a later edit leaves
    unbaked."""
    pixel_cache(tmp_path, monkeypatch)
    root = new_project(tmp_path / "pixel")
    code, out = install(root)
    assert code == 0, out
    (root / "tools").mkdir()
    source = (SKILL / "assets" / "build_project.py").read_text(encoding="utf-8")
    (root / "tools" / "build_project.py").write_text(
        source.replace("VIEW_W, VIEW_H = 1920, 1080", "VIEW_W, VIEW_H = 320, 180"), encoding="utf-8")
    code, out = run(root, "tools/build_project.py")
    assert code == 0 and out.splitlines()[-1].startswith("ok:"), out
    assert "baked 96 characters into 5 Sprite Font types" in out, out
    manifest = c3.load(root / "tools" / "pixel-font.json")
    assert manifest["types"] == ["KeyText", "KeyVerb", "RoundTag", "ScoreLabel", "ScoreText"]
    assert all(c3.load(root / "objectTypes" / f"{n}.json")["plugin-id"] == "Spritefont2" for n in manifest["types"])
    code, out = tool(root, "check_look")
    assert code == 0, out
    edit(root, "layouts/Game.json", lambda d: [i["properties"].update(text="中文") for layer in d["layers"]
                                               for i in layer.get("instances", []) if i["type"] == "ScoreLabel"])
    code, out = tool(root, "check_look")
    assert code == 1 and "type.pixel-font: 2 characters in use are not baked into the Sprite Fonts" in out, out
    code, out = tool(root, "bake_font")
    assert code == 0, out
    code, out = tool(root, "check_look")
    assert code == 0, out
