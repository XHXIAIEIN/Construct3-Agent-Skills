"""Move every picture that a generated game's art() asks for as far as it can go.

    python scripts/art.py              draw, render and fit what is ready, run the generator, print the table
    python scripts/art.py --status     the table only: each picture's route, its state and the next step

The generator's art() asks for each sprite by what it shows, in a box of whole
units, and writes the list to art/wanted.json; until its picture is there, the
sprite shows its stand-in shape. Each picture takes one of two routes, which
ART_ROUTE and art(..., route=) choose:

  svg     drawn in code: tools/drawings.py draws art/<name>.svg with the
          skill's scripts/svg_kit.py, and this script renders each drawing in
          headless Edge or Chrome at its box size on a clear background, with
          its hit frame, the same drawing with the picture's role in the flash
          colour. A drawing is refused when it names a colour instead of a
          role, holds an id that does not start with its own name, or is not
          the size of its box. Pillow is not needed
  image   a picture the user or the session's image tool gives, saved as
          art/raw/<name>.png; this script cuts it out of a transparent, magenta
          or green background and fits it to its box (prepare_art.py), which
          needs Pillow

A run runs tools/drawings.py when it is there, renders every drawing newer than
its picture, fits every picture of art/raw/ newer than its fitted copy, runs
tools/build_project.py when it wrote a picture, so that art() takes them, and
writes a contact sheet of every picture at its size and enlarged, on the
game's canvas, frames of one object side by side, in pages of at most
1600x2240 px that a model reads without scaling them down:
.tmp/scripts/art/contact-N.png, N from 1.

When drawings are still to make, it writes .tmp/scripts/art/brief.md, the
whole task of the construct3:art-drawer sub-agent: the pictures, the kit and
the roles.

A picture refused three times keeps its stand-in, recorded in
art/refused.json; change its subject in art() to try again. The frames of one
animation that differ in box, feet or middle are named as art.frames.

Exit 0: no picture failed, the last line starting with ok: once every picture
is in art/. Exit 1: a drawing or a picture was refused, or tools/drawings.py or
the generator failed. Exit 2: no art/wanted.json. Exit 3: drawings wait to be
rendered and there is no Edge, Chrome or Chromium here.
"""
import base64
import json
import os
import re
import struct
import subprocess
import sys
import time
import zlib
from pathlib import Path

# python -I leaves this script's folder off sys.path, and the modules beside it are imported from there
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import c3project as c3
import prepare_art as image_route

DRAWINGS = Path("tools") / "drawings.py"
FOLDER = "art"                               # .tmp/scripts/art/ of the project
TRIES = image_route.TRIES
# A colour written in a drawing instead of a role: a hex, a functional or a named colour
LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(|"
                     r"(?:fill|stroke|stop-color|flood-color|lighting-color|color)\s*[:=]\s*\"?\s*"
                     r"(?!none|transparent|currentColor|inherit|var\(|color-mix\(|url\()[a-z]+", re.I)
IDS = re.compile(r"\bid\s*=\s*\"([^\"]*)\"")
SIZE = re.compile(r"<svg\b[^>]*?\bwidth=\"(\d+(?:\.\d+)?)\"[^>]*?\bheight=\"(\d+(?:\.\d+)?)\"")
SCALE = 4                                    # the contact sheet's largest enlargement; a small picture is at least doubled
LARGE = 256                                  # px: a picture larger than this shows once, without its enlargement
SHEET_W = 1600                               # px: the contact sheet's width
PAGE_H = 2240                                # px: the most a page of the contact sheet is high
# Claude scales an image down above 2576 px on its long side or 4784 tiles of 28 px; 1600x2240 is 4640 tiles
HEADING_H = 160                              # px: room for an object's heading above a scene on its page
RENDER_WAIT = 10                             # seconds a drawing may take to render
FINDINGS = "findings.json"                   # the versions of each picture art.frames found, in .tmp/scripts/art/


def stem_of(rel: str) -> str:
    return image_route.stem_of(rel)


def png(w: int, h: int, pixels: list[tuple], painted: bool) -> bytes:
    """An 8-bit RGBA PNG, a clear pixel written as (0, 0, 0, 0). A painted one carries the text chunk
    that check_project.py reads as a picture with soft edges."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    rows = b"".join(b"\0" + b"".join(bytes(p if p[3] else (0, 0, 0, 0)) for p in pixels[y * w:(y + 1) * w])
                    for y in range(h))
    text = chunk(b"tEXt", image_route.MARK.encode() + b"\0painted") if painted else b""
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + text
            + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def hexes(palette: dict) -> dict:
    return {role: "#%02X%02X%02X" % tuple(c) for role, c in palette.items()}


# --- the SVG route ----------------------------------------------------------------------------
def svg_problems(text: str, item: dict) -> list[str]:
    """What keeps a drawing from its box and the game's colours."""
    stem = stem_of(item["file"])
    found = []
    size = SIZE.search(text)
    if not size or (float(size[1]), float(size[2])) != (item["width"], item["height"]):
        got = f"{size[1]}x{size[2]}" if size else "no width and height"
        found.append(f"it is {got}, and art() asks {item['width']}x{item['height']}: draw it with "
                     f"svg_kit's kit.drawing({item['file']!r}), which takes the box")
    literal = LITERAL.search(text)
    if literal:
        found.append(f"it names a colour, {literal[0].strip()!r}, where a role of PALETTE goes: write fill=\"ink\" "
                     f"or another role with svg_kit, or d.shade(role) for a darker side")
    foreign = [i for i in IDS.findall(text) if not i.startswith(stem + "-")]
    if foreign:
        found.append(f"its id {foreign[0]!r} does not start with {stem + '-'!r}; two drawings on one page that share "
                     f"an id paint with the first one's definition")
    return found


def page(svg: str, roles: dict) -> str:
    """A page that shows the drawing at its size on a clear background, its roles as CSS variables."""
    css = ";".join(f"--{role}:{colour}" for role, colour in roles.items())
    return (f"<!doctype html><html><head><meta charset=\"utf-8\"><style>:root{{{css}}}"
            f"html,body{{margin:0;background:transparent;overflow:hidden}}svg{{display:block}}</style></head>"
            f"<body>{svg}</body></html>")


class Renderer:
    """One headless browser for the run, with a page that renders a drawing or a contact sheet."""

    def __init__(self, root: Path, exe: str, folder: str = FOLDER) -> None:
        import open_in_editor as oe
        import pack_project as pp
        self.oe, self.root = oe, root
        self.folder = pp.script_folder(root, folder)
        self.browser = oe.Browser(exe, pp.browser_profile(root, "art", exe), False)
        _, self.page = self.browser.page("about:blank")
        self.page.call("Emulation.setDefaultBackgroundColorOverride", color={"r": 0, "g": 0, "b": 0, "a": 0})

    def shot(self, html: str, name: str, w: int, h: int | None = None) -> bytes:
        """The page as a PNG, `w` px wide and `h` high, or as high as the page with h None."""
        h = self.load(html, name, w, h)
        return self.capture(w, 0, h)

    def pages(self, html: str, name: str, w: int, tall: int) -> list[bytes]:
        """The page as PNGs `w` px wide and at most `tall` high, cut between its headings and figures."""
        height = self.load(html, name, w)
        blocks = self.page.evaluate(
            "[...document.querySelectorAll('h2, figure')].map(e => { const r = e.getBoundingClientRect(); "
            "return [Math.floor(r.top + scrollY), Math.ceil(r.bottom + scrollY), e.tagName == 'H2']; })")
        return [self.capture(w, top, bottom - top) for top, bottom in page_spans(blocks, height, tall)]

    def load(self, html: str, name: str, w: int, h: int | None = None) -> int:
        """Loads the page `w` px wide and `h` high, or as high as the page with h None; returns its height."""
        path = self.folder / "render" / f"{name}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        self.page.call("Emulation.setDeviceMetricsOverride", width=w, height=h or 16, deviceScaleFactor=1,
                       mobile=False)
        self.page.call("Page.navigate", url=path.as_uri())
        end = time.monotonic() + RENDER_WAIT
        while self.page.evaluate("document.readyState") != "complete":
            if time.monotonic() > end:
                raise self.oe.DevToolsError(f"{name} did not load in {RENDER_WAIT} seconds")
            time.sleep(0.05)
        # Images decoded and two frames painted, so the screenshot holds what the page draws
        self.page.evaluate("Promise.all([...document.images].map(i => i.decode().catch(() => 0)))"
                           ".then(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))))")
        if h is None:
            h = int(self.page.evaluate("Math.ceil(document.documentElement.scrollHeight)"))
            self.page.call("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1,
                           mobile=False)
        return h

    def capture(self, w: int, top: int, h: int) -> bytes:
        """The loaded page's rows top to top + h as a PNG."""
        shot = self.page.call("Page.captureScreenshot", format="png", captureBeyondViewport=True,
                              clip={"x": 0, "y": top, "width": w, "height": h, "scale": 1})
        return base64.b64decode(shot["data"])

    def close(self) -> None:
        self.browser.close()


def pixels_of(data: bytes, pixel_art: bool) -> tuple[int, int, list[tuple]]:
    w, h, px = c3.png_rgba(data)
    if pixel_art:
        # Each edge pixel in or out, because nearest sampling shows a soft edge as a fringe
        px = [(*p[:3], 255) if p[3] >= 128 else (0, 0, 0, 0) for p in px]
    return w, h, px


def render(renderer: Renderer, root: Path, item: dict, wanted: dict) -> list[str]:
    """art/<file> and art/<name>.hit.png from art/<name>.svg; returns notes on them."""
    stem, w, h = stem_of(item["file"]), item["width"], item["height"]
    svg = (root / "art" / f"{stem}.svg").read_text(encoding="utf-8")
    roles = hexes(wanted["palette"])
    pixel_art = wanted["pixel_art"]
    _, _, picture = pixels_of(renderer.shot(page(svg, roles), stem, w, h), pixel_art)
    if not any(p[3] for p in picture):
        raise image_route.Unusable("it renders as nothing: draw its shapes inside the box")
    path = root / "art" / item["file"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png(w, h, picture, not pixel_art))
    if item["kind"] == "scene":                    # a backdrop is never hit
        return [f"{stem}: art/{stem}.svg -> art/{item['file']} {w}x{h}"]
    flash = {**roles, item["role"]: roles[wanted["flash_role"]]}
    _, _, hit = pixels_of(renderer.shot(page(svg, flash), stem + ".hit", w, h), pixel_art)
    notes = []
    if hit == picture:
        notes.append(f"  note: its hit frame shows no change, because no shape is in its role {item['role']!r}: "
                     f"draw its body in that role, or give art() the role it is drawn in")
    (root / "art" / f"{stem}.hit.png").write_bytes(png(w, h, hit, not pixel_art))
    return [f"{stem}: art/{stem}.svg -> art/{item['file']} {w}x{h} and its hit frame"] + notes


def svg_state(root: Path, item: dict, refused: dict) -> str:
    """draw: no drawing yet; redraw: its drawings were refused, fewer than TRIES; stand-in: TRIES were;
    render: a drawing newer than its picture and not refused; done."""
    svg, out = root / "art" / f"{stem_of(item['file'])}.svg", root / "art" / item["file"]
    r = refused.get(item["file"])
    if not svg.exists():
        return "stand-in" if r and len(r["pictures"]) >= TRIES else ("redraw" if r else "draw")
    if out.exists() and out.stat().st_mtime >= svg.stat().st_mtime:
        return "done"
    if r is None or image_route.fingerprint(svg) not in r["pictures"]:
        return "render"
    return "stand-in" if len(r["pictures"]) >= TRIES else "redraw"


# --- the frames of one animation --------------------------------------------------------------
def baseline(root: Path, item: dict) -> tuple[int, int] | None:
    """The lowest shown row of a picture and the middle of its shown columns."""
    w, h, px = c3.png_rgba((root / "art" / item["file"]).read_bytes())
    shown = [(i % w, i // w) for i, p in enumerate(px) if p[3] >= 128]
    if not shown:
        return None
    xs = [x for x, _ in shown]
    return max(y for _, y in shown), (min(xs) + max(xs)) // 2


def frame_findings(root: Path, wanted: dict, done: list[dict]) -> list[tuple[str, str]]:
    """(picture, line) for the frames of one animation whose box, feet or middle differ (art.frames)."""
    found = []
    # A picture the PNG reader cannot read is the generator's to refuse, when art() takes it
    done = [i for i in done if c3.png_rgba((root / "art" / i["file"]).read_bytes())]
    animations: dict[str, list[dict]] = {}
    for item in done:
        animations.setdefault(item["file"].rsplit("-", 1)[0], []).append(item)
    slack = max(1, wanted["unit"] // 16)          # px the feet of two frames may differ by: 2 at 1080, 1 in pixel art
    for name, frames in animations.items():
        # The frames of a Default animation are often kinds that events pick, a card per frame, not poses
        if len(frames) < 2 or name.split("-")[1:2] == ["default"]:
            continue
        boxes = {(f["width"], f["height"]) for f in frames}
        if len(boxes) > 1:
            found.append((frames[0]["file"], f"art.frames: {name}: its frames are {', '.join(f'{w}x{h}' for w, h in sorted(boxes))}; "
                                             f"give every frame of an animation one box in art()"))
            continue
        lines = {f["file"]: baseline(root, f) for f in frames}
        feet = [b[0] for b in lines.values() if b]
        middles = [b[1] for b in lines.values() if b]
        if feet and (max(feet) - min(feet) > slack or max(middles) - min(middles) > frames[0]["width"] // 4):
            found.append((frames[0]["file"], f"art.frames: {name}: its frames stand on rows {min(feet)} to "
                                             f"{max(feet)} and are centred from x {min(middles)} to {max(middles)}; "
                                             f"draw them with one function from the same d.ground and centre"))
    return found


def counted(root: Path, found: list[tuple[str, str]]) -> tuple[list[str], list[str]]:
    """The findings to fix, and those that three versions of their picture kept, for the hand-over."""
    path = c3.script_folder(root, FOLDER) / FINDINGS
    try:
        seen = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        seen = {}
    fix, kept = [], []
    for rel, line in found:
        key = line.split(":")[0] + " " + rel
        versions = seen.setdefault(key, [])
        print_ = image_route.fingerprint(root / "art" / rel)
        if print_ not in versions:
            versions.append(print_)
        (kept if len(versions) >= TRIES else fix).append(line + (f" ({len(versions)} of {TRIES})" if len(versions) < TRIES else
                                                                f"; still so after {TRIES} versions: name it in the hand-over"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({k: v for k, v in seen.items() if any(k.endswith(" " + rel) for rel, _ in found)},
                               indent=1), encoding="utf-8")
    return fix, kept


# --- the contact sheet ---------------------------------------------------------------------
def objects(items: list[dict]) -> dict[str, list[dict]]:
    """The pictures by object type, the part of the file name before its first dash."""
    out: dict[str, list[dict]] = {}
    for item in items:
        out.setdefault(item["file"].split("-")[0], []).append(item)
    return out


def page_spans(blocks: list[list], height: int, tall: int) -> list[tuple[int, int]]:
    """The (top, bottom) rows of each page, at most `tall` px high, of a contact sheet `height` px high, from its
    blocks [top, bottom, is_heading]. A page ends halfway between two rows of blocks, and a heading stays with
    the row under it."""
    bands: list[list] = []
    for top, bottom, heading in sorted(blocks):
        if bands and (top < bands[-1][1] or bands[-1][2]):
            bands[-1] = [bands[-1][0], max(bands[-1][1], bottom), heading]
        else:
            bands.append([top, bottom, heading])
    cuts = [(a[1] + b[0]) // 2 for a, b in zip(bands, bands[1:])] + [height]
    spans, start, last = [], 0, 0
    for cut in cuts:
        if cut - start > tall and last > start:
            spans.append((start, last))
            start = last
        last = cut
    return spans + [(start, height)]


def sheet_pages(root: Path) -> list[Path]:
    """The pages of the contact sheet, in order."""
    folder = c3.script_folder(root, FOLDER)
    return sorted(folder.glob("contact-[0-9]*.png"), key=lambda p: int(p.stem.split("-")[1]))


def contact_page(root: Path, wanted: dict, done: list[dict]) -> str:
    roles = hexes(wanted["palette"])
    pixel = "image-rendering:pixelated;" if wanted["pixel_art"] else ""
    rows = []
    for name, items in objects(done).items():
        cells = []
        for item in items:
            src = (root / "art" / item["file"]).as_uri()
            w, h = item["width"], item["height"]
            if max(w, h) > LARGE:                  # a scene or a panel: once, at most half the sheet's width
                f = min(1, SHEET_W / 2 / w, (PAGE_H - HEADING_H) / h)
                shown = f"<img src=\"{src}\" width=\"{round(w * f)}\" height=\"{round(h * f)}\" style=\"{pixel}\">"
            else:
                k = max(2, min(SCALE, 512 // max(w, h)))
                shown = (f"<img src=\"{src}\" width=\"{w}\" height=\"{h}\" style=\"{pixel}\">"
                         f"<img src=\"{src}\" width=\"{w * k}\" height=\"{h * k}\" class=\"big\" style=\"{pixel}\">")
            cells.append(f"<figure>{shown}<figcaption>{stem_of(item['file'])}</figcaption></figure>")
        rows.append(f"<section><h2>{name}</h2><div class=\"row\">{''.join(cells)}</div></section>")
    return (f"<!doctype html><html><head><meta charset=\"utf-8\"><style>"
            f"body{{margin:0;padding:24px;background:{roles['canvas']};color:{roles['ink']};font:14px system-ui}}"
            f"h2{{font-size:14px;margin:16px 0 8px}}.row{{display:flex;flex-wrap:wrap;gap:24px;align-items:flex-end}}"
            f"figure{{margin:0;display:flex;gap:12px;align-items:flex-end}}"
            f".big{{outline:1px dashed {roles['line']}}}figcaption{{font-size:12px;color:{roles['dim']}}}"
            f"</style></head><body>{''.join(rows)}</body></html>")


# --- the brief of the art sub-agent --------------------------------------------------------
def brief(root: Path, wanted: dict, items: list[dict], skill: str) -> str:
    lines = [
        "# Draw the art of a Construct 3 game as SVG",
        "",
        f"The game is the project at {root.as_posix()}. Draw every picture of the table below with the skill's "
        f"svg_kit, in the script {(root / DRAWINGS).as_posix()}, which draws them all; read the docstring of "
        f"{(c3.SKILL_DIR / 'scripts' / 'svg_kit.py').as_posix()} first. Its pictures, boxes and roles are in "
        f"{(root / 'art' / 'wanted.json').as_posix()}.",
        "",
        f"Roles: {', '.join(f'{r} {c}' for r, c in hexes(wanted['palette']).items())}. The canvas behind the "
        f"game is {hexes(wanted['palette'])['canvas']}.",
        "",
        "| Picture | Box px | Origin | Role | Shows |",
        "|---------|--------|--------|------|-------|",
        *(f"| {item['file']} | {item['width']}x{item['height']} | {item['origin'][0]:g}, {item['origin'][1]:g} | "
          f"{item['role']} | {item['subject']} |" for item in items),
        "",
        "How to draw:",
        "- One function per object; each frame of the object is a call of it with other values, so its frames share "
        "the box and the line `d.ground` the feet stand on.",
        "- Every colour is a role, `fill=\"reward\"`, or a d.shade() or d.light() of one; the body in the picture's "
        "role, so its hit frame shows the flash. A colour the subjects need and the roles lack is a new role: add it "
        "to PALETTE in tools/build_project.py, above the helpers' begin marker, named by what it plays (`slime`, "
        "`bone`, `gold`), then run the generator.",
        "- Fill most of the box: a picture is fitted to nothing, it is the box.",
        "",
        f"Then run python {skill}/scripts/art.py --project {root.as_posix()}, which runs your script, renders the "
        f"drawings, runs the generator and writes the contact sheet as pages "
        f"{(c3.script_folder(root, FOLDER) / 'contact-N.png').as_posix()}, N from 1, which its output lists. Open "
        f"every page with the Read tool to see what you drew.",
        "",
        "Fix what its output refuses or names as art.frames and run art.py again: three rounds at most. Reply with "
        "what it still refuses or names after the last round, or `none`.",
    ]
    return "\n".join(lines) + "\n"


# --- the run -------------------------------------------------------------------------------
def run_drawings(root: Path, script: Path = DRAWINGS) -> tuple[int, str]:
    """Runs the drawing script at root/script with svg_kit on its path: its exit code and what it said."""
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(filter(None, [str(c3.SKILL_DIR / "scripts"),
                                                                       os.environ.get("PYTHONPATH")]))}
    p = subprocess.run([sys.executable, str(root / script)], cwd=root, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    return p.returncode, (p.stdout + p.stderr).strip()


def run_generator(root: Path) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(root / c3.GENERATOR)], cwd=root, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    out = (p.stdout + p.stderr).strip()
    return p.returncode, out.splitlines()[-1] if out else ""


def table(rows: list[tuple[str, str, str, str]]) -> list[str]:
    widths = [max(len(r[i]) for r in rows) for i in range(3)]
    return [f"{a:<{widths[0]}}  {b:<{widths[1]}}  {c:<{widths[2]}}  {d}" for a, b, c, d in rows]


NEXT = {"draw": "draw art/{stem}.svg", "redraw": "draw art/{stem}.svg again, as its line above says",
        "render": "run art.py", "make": "save its picture as art/raw/{stem}.png",
        "again": "save another picture as art/raw/{stem}.png, as its line above says", "prepare": "run art.py",
        "stand-in": "keeps its stand-in: change its subject in art() to try again", "done": "-"}


def states(root: Path, wanted: dict) -> dict[str, str]:
    refused = image_route.refusals(root, wanted)
    return {item["file"]: svg_state(root, item, refused) if item.get("route") == "svg"
            else image_route.state(root, item, refused) for item in wanted["images"]}


def main() -> int:
    c3.utf8_output()
    ap = c3.argument_parser(__doc__.split("\n\n")[0], "examples:\n"
                            "  python scripts/art.py\n"
                            "  python scripts/art.py --status --project D:/games/Coins\n\n"
                            "exit codes: 0 when no picture failed, the last line starting with ok: once all are in "
                            "art/; 1 when a drawing, a picture, tools/drawings.py or the generator failed; 2 when "
                            "art/wanted.json is missing; 3 when drawings wait and no browser is here")
    ap.add_argument("--status", action="store_true", help="print the table only, and change nothing")
    ap.add_argument("--browser", metavar="EXE", help="the Edge, Chrome or Chromium to render with")
    args = ap.parse_args()
    root = c3.find_project(args.project)
    where = root or Path.cwd()
    wanted_path = where / "art" / "wanted.json"
    if root is None or not wanted_path.exists():
        print(f"no art/wanted.json in {where}: give every sprite an art() in build_images() of "
              f"tools/build_project.py and run it, which writes the list", file=sys.stderr)
        return 2
    wanted = json.loads(wanted_path.read_text(encoding="utf-8"))
    skill = (c3.SKILL_DIR.relative_to(root) if c3.SKILL_DIR.is_relative_to(root) else c3.SKILL_DIR).as_posix()
    out, failed, wrote, code = [], 0, 0, 0
    if not args.status:
        if (root / DRAWINGS).is_file():
            ran, said = run_drawings(root)
            if ran:
                tail = said.splitlines()[-6:]
                out += [f"{DRAWINGS.as_posix()} failed with code {ran}:", *(f"  {line}" for line in tail)]
                failed += 1
        refused = image_route.refusals(root, wanted)
        to_render = [item for item in wanted["images"] if item.get("route") == "svg"
                     and svg_state(root, item, refused) == "render"]
        good = []
        for item in to_render:
            svg = root / "art" / f"{stem_of(item['file'])}.svg"
            problems = svg_problems(svg.read_text(encoding="utf-8"), item)
            if problems:
                failed += 1
                r = refused.setdefault(item["file"], {"subject": item["subject"], "pictures": []})
                if (seen := image_route.fingerprint(svg)) not in r["pictures"]:
                    r["pictures"].append(seen)
                out.append(f"{stem_of(item['file'])}: art/{svg.name} refused "
                           f"{image_route.refusal(len(r['pictures']))}: " + "; ".join(problems))
            else:
                good.append(item)
        exe = args.browser or None
        if good:
            import open_in_editor as oe
            exe = exe or oe.browser_path()
            if not exe:
                print("no Edge, Chrome or Chromium here to render the drawings: install one, or pass --browser EXE",
                      file=sys.stderr)
                return 3
            try:
                renderer = Renderer(root, exe)
            except (oe.DevToolsError, OSError) as e:
                print(f"{Path(exe).name} could not render the drawings: {e}", file=sys.stderr)
                return 3
            try:
                for item in good:
                    try:
                        out += render(renderer, root, item, wanted)
                        wrote += 1
                        refused.pop(item["file"], None)
                    except image_route.Unusable as e:
                        failed += 1
                        out.append(f"{stem_of(item['file'])}: art/{stem_of(item['file'])}.svg: {e}")
            finally:
                renderer.close()
        raw = [item for item in wanted["images"] if item.get("route") != "svg"
               and image_route.state(root, item, refused) == "prepare"]
        if raw:
            try:
                import PIL  # noqa: F401
            except ImportError:
                out.append(f"{len(raw)} pictures of art/raw/ wait to be fitted, which needs Pillow: pip install pillow")
                raw = []
            for item in raw:
                lines, ok = image_route.fit(root, item, wanted, refused)
                out += lines
                wrote += ok
                failed += not ok and image_route.state(root, item, refused) != "stand-in"
        image_route.keep_refusals(root, refused)
        if wrote:
            ran, last = run_generator(root)
            out.append(f"generator: {last}")
            if ran:
                failed += 1
    now = states(root, wanted)
    rows = [("picture", "route", "state", "next")] + [
        (stem_of(item["file"]), item.get("route", "image"), now[item["file"]],
         NEXT[now[item["file"]]].format(stem=stem_of(item["file"]))) for item in wanted["images"]]
    out += table(rows)
    to_save = [item for item in wanted["images"] if item.get("route") != "svg"
               and now[item["file"]] in ("make", "again")]
    if to_save:
        (root / "art" / "raw").mkdir(parents=True, exist_ok=True)      # where the pictures are saved
    done = [item for item in wanted["images"] if now[item["file"]] == "done"]
    folder = c3.script_folder(root, FOLDER)
    if done and wrote:
        import open_in_editor as oe
        exe = args.browser or oe.browser_path()
        for old in folder.glob("contact*.png"):
            old.unlink()
        folder.mkdir(parents=True, exist_ok=True)
        if exe:
            try:
                renderer = Renderer(root, exe)
                try:
                    for n, data in enumerate(renderer.pages(contact_page(root, wanted, done), "contact", SHEET_W,
                                                            PAGE_H), 1):
                        (folder / f"contact-{n}.png").write_bytes(data)
                finally:
                    renderer.close()
            except (oe.DevToolsError, OSError) as e:
                out.append(f"contact sheet: not made, {Path(exe).name} could not be driven: {e}")
    sheets = sheet_pages(root) if done else []
    if sheets:
        out.append(f"contact sheet: {len(sheets)} page{'s' * (len(sheets) > 1)}, " + ", ".join(map(str, sheets)))
    fix, kept = counted(root, frame_findings(root, wanted, done)) if done else ([], [])
    out += fix + kept
    drawings = [item for item in wanted["images"] if item.get("route") == "svg"
                and now[item["file"]] in ("draw", "redraw")]
    counts = {s: list(now.values()).count(s) for s in set(now.values())}
    count = ", ".join(f"{s}: {n}" for s, n in sorted(counts.items()))
    if drawings:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "brief.md").write_text(brief(root, wanted, [i for i in wanted["images"] if i.get("route") == "svg"],
                                               skill), encoding="utf-8")
        out.append(f"{count}; next: start a construct3:art-drawer sub-agent with {folder / 'brief.md'} as its whole "
                   f"task, or draw them as that brief says yourself; then run {c3.script_command(root, 'art.py')}")
    elif to_save:
        out.append(f"{count}; next: save each picture the table names in art/raw/, then run "
                   f"{c3.script_command(root, 'art.py')}")
    elif any(s in ("render", "prepare") for s in now.values()):
        out.append(f"{count}; next: run {c3.script_command(root, 'art.py')}")
    elif failed or fix:
        failed += bool(fix)
        out.append(f"{count}; next: fix what the lines above name, then run {c3.script_command(root, 'art.py')}")
    else:
        kept = counts.get("stand-in", 0)
        out.append(f"ok: {counts.get('done', 0)} pictures from art/" + (f", {kept} keep their stand-in" if kept else "")
                   + ("; read every page of the contact sheet, listed above" if sheets else ""))
    shown = c3.fitting(out, args.limit)
    for line in out[:shown]:
        print(line)
    if shown < len(out):
        print(f"... {len(out) - shown} more lines; --limit 0 prints them all")
        print(out[-1])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
