"""Bake the characters a pixel-art game shows into its Sprite Font images, from a BDF pixel font.

    python scripts/bake_font.py [--project FOLDER] [--add TEXT] [--replace] [--check]
                                [--types TYPE ...] [--font NAME_OR_PATH]

A game that assets/build_project.py generates at a viewport 360 px high or less
draws its text in Sprite Fonts. Its letters keep the pixel grid and the
palette. A Sprite Font draws only the characters its image holds, and the
image holds only what the game uses, so a Chinese game carries only the
characters it shows. This script finds them and draws them:

  - the text of every instance of the Sprite Font types in layouts/;
  - every string in the event sheets: a quoted string in a parameter, and the
    initial value of a string variable;
  - every string in the data files under files/ (JSON, CSV and text);
  - printable ASCII, for the numbers and names that events build at runtime;
  - the characters of --add TEXT, for words that events build from parts;
    "added" in tools/pixel-font.json keeps them for every later run, the
    generator's among them.

Each character goes into a cell as wide and high as the font's pixel size,
white where the glyph is drawn and clear elsewhere; the instance's colour tints
it to a role of the palette. Every instance of the types gets the character set
and the spacing data, which holds each character's advance.

The types are those tools/pixel-font.json names, which the generator writes, or
those given with --types. The font is that file's "font", the name of a BDF file
in the user's font cache (CONSTRUCT3_RAG_FONT_CACHE, else
~/.cache/construct3-rag/fonts), or --font.

Modes:
  (default)   append: keep every character the images hold and add the ones
              in use that they lack; a first run generates the images
  --replace   bake only the characters in use and those of this run's --add,
              dropping the rest and the "added" of earlier runs
  --check     write nothing; list the characters in use that the images lack

Exit 0: the last line starts with ok:. Exit 1: a character in use is missing
(--check), or one that the font lacks. Exit 2: no project, no font or no
Sprite Font type to bake.
"""
import csv
import io
import json
import os
import re
import struct
import sys
import zlib
from pathlib import Path

import c3project as c3

MANIFEST = "tools/pixel-font.json"
COLUMNS = 32                                # cells a row of the image
# Spaces of U+2002 to U+200A in em, as SPACE_EMS of the template counts them; the font has none, so
# each is baked as a blank cell of its width. tracked() spaces a tag's letters with U+2005.
SPACES = {" ": 0.5, " ": 1, " ": 0.33, " ": 0.25, " ": 0.17, " ": 0.65,
          " ": 0.29, " ": 0.18, " ": 0.09}
ASCII = "".join(map(chr, range(0x21, 0x7F)))
# A quoted string in an expression; "" inside one is a quote.
QUOTED = re.compile(r'"((?:[^"]|"")*)"')


def font_cache() -> Path:
    return Path(os.environ.get("CONSTRUCT3_RAG_FONT_CACHE") or Path.home() / ".cache" / "construct3-rag" / "fonts")


def read_bdf(path: Path) -> tuple[int, dict[str, tuple[int, tuple[int, int, int, int], list[int]]]]:
    """(pixel size, {character: (advance, (w, h, x offset, y offset), rows)}) of a BDF font, each row
    an integer whose high bit is the glyph's left column."""
    size, glyphs, cur, rows = 0, {}, None, None
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            w = line.split()
            if not w:
                continue
            if rows is not None and w[0] != "ENDCHAR":
                rows.append(int(w[0], 16))
            elif w[0] == "PIXEL_SIZE":
                size = int(w[1])
            elif w[0] == "ENCODING":
                cur = {"cp": int(w[1])}
            elif w[0] == "DWIDTH" and cur is not None:
                cur["adv"] = int(w[1])
            elif w[0] == "BBX" and cur is not None:
                cur["bbx"] = tuple(map(int, w[1:5]))
            elif w[0] == "BITMAP" and cur is not None:
                rows = []
            elif w[0] == "ENDCHAR" and cur is not None:
                if 0 <= cur["cp"] <= 0x10FFFF and "bbx" in cur:
                    width = cur["bbx"][0]
                    bits = (width + 7) // 8 * 8
                    glyphs[chr(cur["cp"])] = (cur.get("adv", size), cur["bbx"],
                                              [r >> (bits - width) if width else 0 for r in rows or []])
                cur, rows = None, None
    return size, glyphs


def find_font(given: str | None, manifest: dict) -> Path | None:
    name = given or manifest.get("font")
    if not name:
        return None
    path = Path(name)
    if path.suffix.lower() == ".bdf" and path.is_file():
        return path
    cached = font_cache() / f"{path.stem if path.suffix.lower() == '.bdf' else name}.bdf"
    return cached if cached.is_file() else None


def strings_in(node, out: list[str]) -> None:
    """The quoted strings of every parameter, and the initial value of every string variable, in an
    event sheet's JSON."""
    if isinstance(node, dict):
        params = node.get("parameters")
        if isinstance(params, dict):
            for v in params.values():
                if isinstance(v, str):
                    out += [m.replace('""', '"') for m in QUOTED.findall(v)]
        if node.get("type") == "string" and isinstance(node.get("initialValue"), str):
            out.append(node["initialValue"])
        for v in node.values():
            strings_in(v, out)
    elif isinstance(node, list):
        for v in node:
            strings_in(v, out)


def json_strings(node, out: list[str]) -> None:
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, dict):
        for k, v in node.items():
            out.append(k)
            json_strings(v, out)
    elif isinstance(node, list):
        for v in node:
            json_strings(v, out)


def layouts_of(root: Path) -> dict[Path, dict]:
    return {f: c3.load(f) for f in sorted((root / "layouts").rglob("*.json"))}


def instances_of(lay: dict, types: set[str]):
    for layer, _ in c3.layers_of(lay.get("layers") or []):
        for inst in layer.get("instances") or []:
            if inst.get("type") in types:
                yield inst


def in_use(root: Path, layouts: dict[Path, dict], types: set[str]) -> str:
    """Every character the project may show in the types: their instances' texts, the strings of the
    event sheets and of files/, and printable ASCII."""
    texts = [inst.get("properties", {}).get("text", "") for lay in layouts.values() for inst in instances_of(lay, types)]
    for f in sorted((root / "eventSheets").rglob("*.json")):
        strings_in(c3.load(f), texts)
    for f in sorted((root / "files").rglob("*")) if (root / "files").is_dir() else []:
        if f.suffix.lower() == ".json":
            json_strings(c3.load(f), texts)
        elif f.suffix.lower() == ".csv":
            texts += [cell for row in csv.reader(io.StringIO(f.read_text(encoding="utf-8-sig"))) for cell in row]
        elif f.suffix.lower() in (".txt", ".md"):
            texts.append(f.read_text(encoding="utf-8-sig"))
    texts.append(ASCII)
    return chars_of("".join(t for t in texts if isinstance(t, str)))


def chars_of(text: str) -> str:
    """The distinct characters of `text` that a Sprite Font draws, in order of code point: no control
    character, and no space, which spacing data sizes, but the spaces of SPACES, baked blank."""
    return "".join(sorted({c for c in text if c in SPACES or c.isprintable() and c != " "}))


def baked(lay_by_file: dict[Path, dict], types: set[str]) -> str:
    """The characters the types' instances hold now."""
    return chars_of("".join(inst.get("properties", {}).get("character-set", "")
                            for lay in lay_by_file.values() for inst in instances_of(lay, types)))


def png(w: int, h: int, pixels: bytearray) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\0" + bytes(pixels[y * w * 4:(y + 1) * w * 4]) for y in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def sheet(chars: str, size: int, descent: int, glyphs: dict) -> tuple[int, int, bytes, dict[int, str]]:
    """(width, height, PNG, {advance: characters}) of the image that holds `chars`, a cell each, the
    baseline `descent` rows above a cell's bottom."""
    cols = min(COLUMNS, max(1, len(chars)))
    rows = max(1, -(-len(chars) // cols))
    w, h = cols * size, rows * size
    px = bytearray(w * h * 4)
    advances: dict[int, str] = {}
    for i, c in enumerate(chars):
        if c in SPACES:
            adv = max(1, round(SPACES[c] * size))
        else:
            adv, (gw, gh, gx, gy), bitmap = glyphs[c]
            top = size - descent - gy - gh             # the glyph's top row in its cell
            ox, oy = i % cols * size, i // cols * size
            for r, bits in enumerate(bitmap):
                y = top + r
                for x in range(gw):
                    if bits >> (gw - 1 - x) & 1 and 0 <= y < size and 0 <= gx + x < size:
                        at = ((oy + y) * w + ox + gx + x) * 4
                        px[at:at + 4] = b"\xff\xff\xff\xff"
        advances.setdefault(adv, "")
        advances[adv] += c
    return w, h, png(w, h, px), advances


def save(path: Path, obj) -> None:
    """Tab indent, LF, raw UTF-8 and no newline at the end, as the editor saves a project file."""
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, indent="\t", ensure_ascii=False))


def main() -> int:
    c3.utf8_output()
    ap = c3.argument_parser(__doc__.split("\n\n")[0], "examples:\n"
                            "  python scripts/bake_font.py\n"
                            "  python scripts/bake_font.py --add 第关卡\n"
                            "  python scripts/bake_font.py --replace\n"
                            "  python scripts/bake_font.py --check\n\n"
                            "exit codes: 0 when the last line starts with ok:, 1 on a missing character, "
                            "2 when there is nothing to bake")
    ap.add_argument("--add", default="", metavar="TEXT", help="characters to bake besides those in use")
    ap.add_argument("--replace", action="store_true", help="drop the baked characters that are no longer in use")
    ap.add_argument("--check", action="store_true", help="write nothing; list the characters in use that are not baked")
    ap.add_argument("--types", nargs="+", metavar="TYPE", help=f"the Sprite Font types (default: {MANIFEST})")
    ap.add_argument("--font", metavar="NAME_OR_PATH", help="a BDF file, or its name in the font cache "
                                                           f"(default: the \"font\" of {MANIFEST})")
    args = ap.parse_args()
    root = c3.find_project(args.project)
    if root is None or not (root / "project.c3proj").exists():
        print(f"no project.c3proj in {root or Path.cwd()}: run this from the project folder or pass "
              f"--project <folder>", file=sys.stderr)
        return 2
    manifest = c3.load(root / MANIFEST) if (root / MANIFEST).is_file() else {}
    types = set(args.types or manifest.get("types") or [])
    object_types = {f.stem: f for f in (root / "objectTypes").rglob("*.json")}
    fonts = sorted(n for n, f in object_types.items() if c3.load(f).get("plugin-id") == "Spritefont2")
    if not types:
        print(f"no Sprite Font type to bake: {MANIFEST} names none and --types gives none. The project's Sprite "
              f"Fonts: {', '.join(fonts) or 'none'}. Run the generator, or pass --types with one of these",
              file=sys.stderr)
        return 2
    if not types <= set(fonts):
        print(f"not Sprite Font types of this project: {', '.join(sorted(types - set(fonts)))}. Its Sprite Fonts: "
              f"{', '.join(fonts) or 'none'}; pass --types with one of these", file=sys.stderr)
        return 2
    layouts = layouts_of(root)
    added = chars_of(args.add if args.replace else manifest.get("added", "") + args.add)
    used = chars_of(in_use(root, layouts, types) + added)
    have = baked(layouts, types)
    if args.check:
        missing = "".join(c for c in used if c not in have)
        if missing:
            print(f"{len(missing)} characters in use are not in the Sprite Font images, and draw as nothing: "
                  f"{missing}")
            print(f"run {c3.script_command(root, 'bake_font.py')} to add them")
            return 1
        print(f"ok: every character in use is baked ({len(have)} baked)")
        return 0
    font = find_font(args.font, manifest)
    if font is None:
        name = args.font or manifest.get("font") or "none named"
        print(f"no font: {name} is not a BDF file, and {font_cache()} holds no {Path(name).stem}.bdf. Save the "
              f"file of that name from the 8px proportional BDF release of Fusion Pixel Font there: "
              f"https://github.com/TakWolf/fusion-pixel-font/releases", file=sys.stderr)
        return 2
    size, glyphs = read_bdf(font)
    wanted = chars_of(used + ("" if args.replace else have))
    lacking = "".join(c for c in wanted if c not in glyphs and c not in SPACES)
    chars = "".join(c for c in wanted if c in glyphs or c in SPACES)
    descent = max(0, -min(glyphs[c][1][3] for c in ASCII if c in glyphs))
    w, h, image, advances = sheet(chars, size, descent, glyphs)
    space = glyphs.get(" ", (size // 2,))[0]
    spacing = json.dumps([[adv, cs] for adv, cs in sorted(advances.items()) if adv != size] + [[space, " "]],
                         ensure_ascii=False)
    (root / "images").mkdir(exist_ok=True)
    for name in sorted(types):
        (root / "images" / f"{name.lower()}.png").write_bytes(image)
        t = c3.load(object_types[name])
        t["image"] = {**(t.get("image") or {}), "width": w, "height": h}
        save(object_types[name], t)
    for f, lay in layouts.items():
        touched = False
        for inst in instances_of(lay, types):
            inst["properties"] |= {"character-width": size, "character-height": size, "character-set": chars,
                                   "spacing-data": spacing}
            touched = True
        if touched:
            save(f, lay)
    if (root / MANIFEST).is_file() or added:
        (root / MANIFEST).parent.mkdir(exist_ok=True)
        save(root / MANIFEST, {"font": manifest.get("font") or font.stem, "types": sorted(types), "added": added})
    new = len([c for c in chars if c not in have])
    dropped = len([c for c in have if c not in chars])
    print(f"baked {len(chars)} characters into {len(types)} Sprite Font types, a {w}x{h} image each, from "
          f"{font.name}: {new} added{f', {dropped} dropped' if dropped else ''}")
    if lacking:
        print(f"the font lacks {len(lacking)} characters in use, which draw as nothing: {lacking}; change the "
              f"text, or draw it in a Text")
        return 1
    print(f"ok: {len(chars)} characters baked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
