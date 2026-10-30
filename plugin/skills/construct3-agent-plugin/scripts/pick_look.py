"""Pick a generated game's look with the user from its first play screen drawn in three directions.

    python scripts/pick_look.py              check and render the directions, write the picker, print the table
    python scripts/pick_look.py --pick NAME  write the picked direction into tools/build_project.py

When the user gave the game a look, in words or references, USER_LOOK names
where it comes from, and the look is picked before any art is drawn. The art
agent draws the game's first play screen at its viewport size in three named
directions: paper and ink, the fallback, and two from the user's look. Each
differs from every other in two or more of the dimensions of an art direction
(rendering, linework, colour temperature, light direction, proportions,
framing), never only in its colours, and keeps the roles of PALETTE and the
kinds of TEXT_SIZE, so that the pick is the values USER_LOOK, PALETTE and
ART_STYLE of the template and nothing else.

Everything lies in .tmp/scripts/pick-look/ of the project:

  screens.py       the art agent's script: draws each direction with the
                   skill's svg_kit, kit.screen(<name>), into <name>.svg
  directions.json  the art agent's: {"directions": [...]}, each with name,
                   axes (its place on each dimension), right_when, cost,
                   USER_LOOK, ART_STYLE and PALETTE; draw-brief.md gives the
                   form
  <name>.png       each screen rendered in headless Edge or Chrome with its
                   PALETTE
  index.html       the picker: one direction at a time, full size; the keys 1
                   to N and the arrow keys switch, ?v=2 opens the second
  judge-brief.md   the look questions on the renders, for the
                   construct3:look-judge sub-agent

A run runs screens.py when it is there and checks every direction: its
fields, that one of them is paper and ink with the template's PALETTE, that
each ART_STYLE fixes all six dimensions, that every two directions differ in
two or more of them, and that each drawing is the viewport's size, names
roles and no colour, prefixes its ids with its name and gives every label a
kind of TEXT_SIZE. Without directions.json it writes draw-brief.md, the whole
task of the construct3:art-drawer sub-agent. Its last line says to stop and
ask the user which direction to take.

--pick NAME writes the picked direction's USER_LOOK, PALETTE's colours by
role and ART_STYLE into tools/build_project.py, keeps its render as
art/look.png, the look the pictures are drawn and made in, and deletes the
picker's folder.

Exit 0: the picker is written, the draw brief is written, or the pick is
written. Exit 1: a direction or the pick was refused, or screens.py failed.
Exit 2: no project or no art/wanted.json. Exit 3: no Edge, Chrome or Chromium
to render with.
"""
import ast
import json
import re
import shutil
import sys
from pathlib import Path

# python -I leaves this script's folder off sys.path, and the modules beside it are imported from there
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import art
import c3project as c3
import prepare_art
from svg_kit import PICKER

SCREENS = "screens.py"
DIRECTIONS = "directions.json"
FEWEST, MOST = 3, 5                          # directions: paper and ink and two from the user's look; five at most
MIN_AXES = 2                                 # dimensions in which every two directions differ, at least
FIELDS = ("name", "axes", "right_when", "cost", "USER_LOOK", "ART_STYLE", "PALETTE")
SETTINGS = ("USER_LOOK", "PALETTE", "ART_STYLE")
TEXTS = re.compile(r"<text\b([^>]*)>")
WEIGHTS = {"light": 300, "regular": 400, "medium": 500}
# Paper and ink as a direction's ART_STYLE, from the template's look; the art agent may word it otherwise
PAPER_AND_INK = ("flat fills on white paper, no outlines, areas and ranges as thin lines, neutral greys with two "
                 "saturated accents, no lighting or shading, simple geometric proportions on the grid, straight-on "
                 "top-down view of the whole board")
# Asked of every render besides the look review's questions
DIFFERS = ("Does this screenshot differ from another of them only in its colours, with the same shapes, lines, light "
           "and framing?")


def slug(name: str) -> str:
    """A direction's name as the name of its drawing: lowercase words joined by dashes."""
    return "-".join(re.findall(r"[a-z0-9]+", name.lower()))


def paper_and_ink_palette() -> dict:
    """PALETTE of the skill's template, paper and ink's colours by role."""
    tree = ast.parse((c3.SKILL_DIR / "assets" / "build_project.py").read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "PALETTE")
    return {role: list(c) for role, c in ast.literal_eval(node.value).items()}


def words(value: str) -> set[str]:
    return set(re.findall(r"\w+", value.lower()))


# --- the check of the directions -----------------------------------------------------------------
def field_problems(d: dict, roles: list[str]) -> list[str]:
    """What a direction lacks or holds wrong, each with what to write."""
    found = [f"it has no {f}" for f in FIELDS if f not in d]
    if found:
        return found
    axes = d["axes"]
    if not isinstance(axes, dict) or set(axes) != set(prepare_art.DIMENSIONS) or not all(
            isinstance(v, str) and v.strip() for v in axes.values()):
        found.append(f"its axes are not one phrase for each of {', '.join(prepare_art.DIMENSIONS)}: write where the "
                     f"direction stands on each, such as \"rendering\": \"ink wash on rough paper\"")
    for f in ("name", "right_when", "cost", "ART_STYLE"):
        if not isinstance(d[f], str) or not d[f].strip():
            found.append(f"its {f} is empty: write it in a sentence")
    if not isinstance(d["USER_LOOK"], str):
        found.append("its USER_LOOK is not a string")
    palette = d["PALETTE"]
    if not isinstance(palette, dict) or set(palette) != set(roles):
        got = ", ".join(palette) if isinstance(palette, dict) else "none"
        found.append(f"its PALETTE has the roles {got}, and the game has {', '.join(roles)}: give each role of the "
                     f"game a colour and no other role, so the pick maps onto the template's PALETTE")
    elif not all(isinstance(c, list) and len(c) == 3 and all(isinstance(v, int) and 0 <= v <= 255 for v in c)
                 for c in palette.values()):
        found.append("a colour of its PALETTE is not [red, green, blue] in whole numbers from 0 to 255")
    if isinstance(d["ART_STYLE"], str) and d["ART_STYLE"].strip():
        left = prepare_art.left_open(d["ART_STYLE"])
        if left:
            found.append(f"its ART_STYLE names no {prepare_art.joined(left, 'or')}: name each of the six dimensions "
                         f"in it, so the pictures drawn or made in it share them")
    return found


def svg_problems(text: str, name: str, view: list[int], kinds: list[str]) -> list[str]:
    """What keeps a screen from the viewport, the roles and the kinds of text."""
    found = []
    size = art.SIZE.search(text)
    if not size or (float(size[1]), float(size[2])) != tuple(view):
        got = f"{size[1]}x{size[2]}" if size else "no width and height"
        found.append(f"it is {got}, and the viewport is {view[0]}x{view[1]}: draw it with svg_kit's "
                     f"kit.screen({name!r}), which takes the viewport")
    literal = art.LITERAL.search(text)
    if literal:
        found.append(f"it names a colour, {literal[0].strip()!r}, where a role of PALETTE goes: write fill=\"ink\" or "
                     f"another role, which the picker sets from the direction's PALETTE")
    foreign = [i for i in art.IDS.findall(text) if not i.startswith(name + "-")]
    if foreign:
        found.append(f"its id {foreign[0]!r} does not start with {name + '-'!r}")
    for attrs in TEXTS.findall(text):
        kind = re.search(r'\bclass="([^"]*)"', attrs)
        if not kind or kind[1] not in kinds:
            found.append(f"a label has {'the class ' + repr(kind[1]) if kind else 'no class'}, and every label is a "
                         f"kind of TEXT_SIZE ({', '.join(kinds)}): write it with d.text(..., kind=)")
            break
    return found


def differing(a: dict, b: dict) -> list[str]:
    """The dimensions in which two directions stand apart: their phrases hold other words."""
    return [dim for dim in prepare_art.DIMENSIONS if words(a["axes"][dim]) != words(b["axes"][dim])]


def check(root: Path, wanted: dict, folder: Path) -> tuple[list[dict], list[str]]:
    """The directions of directions.json, and what refuses them."""
    try:
        data = json.loads((folder / DIRECTIONS).read_text(encoding="utf-8"))
        directions = data["directions"]
    except (ValueError, KeyError, TypeError) as e:
        return [], [f"{DIRECTIONS}: not a JSON object with a list \"directions\" ({e}); draw-brief.md gives the form"]
    if not isinstance(directions, list) or not all(isinstance(d, dict) for d in directions):
        return [], [f"{DIRECTIONS}: \"directions\" is not a list of objects; draw-brief.md gives the form"]
    roles, kinds = list(wanted["palette"]), list(wanted.get("text_size") or {})
    out = []
    if not FEWEST <= len(directions) <= MOST:
        out.append(f"{DIRECTIONS}: {len(directions)} directions; the picker takes {FEWEST} to {MOST}, paper and ink "
                   f"and two or more from the user's look")
    for i, d in enumerate(directions, 1):
        out += [f"direction {i} {d.get('name', '')!r}: {p}" for p in field_problems(d, roles)]
    if out:
        return directions, out
    names = [slug(d["name"]) for d in directions]
    if len(set(names)) < len(names):
        out.append(f"{DIRECTIONS}: two directions share the name {next(n for n in names if names.count(n) > 1)!r}; "
                   f"name each by its direction, such as \"Ink wash\"")
    plain = [d for d in directions if not d["USER_LOOK"].strip()]
    if len(plain) != 1:
        out.append(f"{DIRECTIONS}: {len(plain)} directions have an empty USER_LOOK; exactly one is paper and ink, "
                   f"the fallback, and each other names where it comes from in the user's look")
    elif changed := [r for r, c in paper_and_ink_palette().items() if r in roles and plain[0]["PALETTE"][r] != c]:
        out.append(f"{plain[0]['name']}: paper and ink keeps the template's PALETTE, and its {', '.join(changed)} "
                   f"differ; a direction with colours of its own takes a USER_LOOK")
    for i, a in enumerate(directions):
        for b in directions[i + 1:]:
            apart = differing(a, b)
            if len(apart) < MIN_AXES:
                out.append(f"{a['name']} and {b['name']} differ in {', '.join(apart) or 'no dimension'} alone: every "
                           f"two directions differ in {MIN_AXES} of the six dimensions or more, never only in their "
                           f"colours; move one of them on another dimension, in its axes, its ART_STYLE and its "
                           f"drawing")
    view = wanted["view"]
    for d, name in zip(directions, names):
        svg = folder / f"{name}.svg"
        if not svg.is_file():
            out.append(f"{d['name']}: no {svg.name}; draw it in {SCREENS} with kit.screen({name!r})")
            continue
        out += [f"{d['name']}: {svg.name}: {p}" for p in svg_problems(svg.read_text(encoding="utf-8"), name, view, kinds)]
    return directions, out


# --- the renders, the picker and the briefs ----------------------------------------------------
def page(svg: str, palette: dict, wanted: dict) -> str:
    """A page that shows a screen at the viewport's size, its roles as CSS variables and every label in the size
    and weight of its kind."""
    roles = ";".join(f"--{role}:#%02X%02X%02X" % tuple(c) for role, c in palette.items())
    px = 1 if wanted["pixel_art"] else 4 / 3
    weights = wanted.get("text_weight") or {}
    kinds = "".join(f"svg text.{k}{{font-size:{v * px:g}px !important;font-weight:"
                    f"{WEIGHTS.get(weights.get(k, 'regular'), 400)} !important}}"
                    for k, v in (wanted.get("text_size") or {}).items())
    return (f"<!doctype html><html><head><meta charset=\"utf-8\"><style>:root{{{roles}}}"
            f"html,body{{margin:0;background:var(--canvas);overflow:hidden}}svg{{display:block}}"
            f"svg text{{font-family:Inter,system-ui,sans-serif}}{kinds}</style></head><body>{svg}</body></html>")


def render(root: Path, exe: str, wanted: dict, directions: list[dict], folder: Path) -> list[str]:
    """<name>.png of every direction; returns what refuses a render."""
    w, h = wanted["view"]
    out = []
    renderer = art.Renderer(root, exe, PICKER)
    try:
        for d in directions:
            name = slug(d["name"])
            data = renderer.shot(page((folder / f"{name}.svg").read_text(encoding="utf-8"), d["PALETTE"], wanted),
                                 name, w, h)
            _, _, px = c3.png_rgba(data)
            if len({p[:3] for p in px[::97]}) < 2:
                out.append(f"{d['name']}: {name}.svg renders as one colour: draw the screen's objects and labels on it")
            (folder / f"{name}.png").write_bytes(data)
    finally:
        renderer.close()
    return out


# The picker's markup, styles and wiring are those of skills/prototype/PICKER.md of
# emilkowalski/skills, as that spec says, without the replay button, since a render has no
# animation to replay. They come under this licence, which the page carries too:
LICENSE = """MIT License

Copyright (c) 2026 Emil Kowalski

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
PICKER_CSS = """
.proto-picker {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2147483647;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px;
  border-radius: 999px;
  background: rgba(10, 10, 10, 0.82);
  -webkit-backdrop-filter: blur(12px) saturate(1.4);
  backdrop-filter: blur(12px) saturate(1.4);
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.08) inset,
    0 8px 24px rgba(0, 0, 0, 0.24),
    0 2px 6px rgba(0, 0, 0, 0.12);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 13px;
  line-height: 1;
  -webkit-font-smoothing: antialiased;
  user-select: none;
  -webkit-user-select: none;
}

.proto-picker-highlight {
  position: absolute;
  top: 4px;
  left: 0;
  height: 28px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  will-change: transform;
}

/* The slide is enabled only after first paint (data-ready), so load doesn't animate. */
.proto-picker[data-ready] .proto-picker-highlight {
  transition:
    transform 250ms cubic-bezier(0.23, 1, 0.32, 1),
    width 250ms cubic-bezier(0.23, 1, 0.32, 1);
}

@media (prefers-reduced-motion: reduce) {
  .proto-picker[data-ready] .proto-picker-highlight { transition: none; }
}

.proto-picker-item {
  position: relative; /* sits above the highlight */
  display: flex;
  align-items: center;
  height: 28px;
  padding: 0 12px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: rgba(255, 255, 255, 0.55);
  font: inherit;
  cursor: pointer;
  transition: color 150ms ease-out;
}

.proto-picker-item:hover {
  color: rgba(255, 255, 255, 0.85);
}

.proto-picker-item:active {
  transform: scale(0.97);
}

.proto-picker-item:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.4);
  outline-offset: 2px;
}

.proto-picker-item[data-active] {
  color: #fff;
}

.proto-picker-divider {
  width: 1px;
  height: 16px;
  margin: 0 4px;
  background: rgba(255, 255, 255, 0.12);
}

.proto-picker-replay {
  padding: 0 10px;
  font-size: 14px;
}

.proto-picker[data-position="top"] {
  bottom: auto;
  top: 24px;
}
"""
PICKER_JS = """
const stage = document.getElementById('stage');
const picker = document.querySelector('.proto-picker');
const highlight = picker.querySelector('.proto-picker-highlight');
const items = [...picker.querySelectorAll('.proto-picker-item:not(.proto-picker-replay)')];
const replay = picker.querySelector('.proto-picker-replay');
let current = 0;

function moveHighlight() {
  const el = items[current];
  highlight.style.width = el.offsetWidth + 'px';
  highlight.style.transform = `translateX(${el.offsetLeft}px)`;
}

function mount(i) {
  stage.innerHTML = '';
  // Clear first, render next frame, so entrance animations re-run.
  requestAnimationFrame(() => { stage.innerHTML = variants[i](); });
}

function setActive(i) {
  if (i < 0 || i >= variants.length) return;
  current = i;
  items.forEach((el, j) => {
    el.toggleAttribute('data-active', j === i);
    if (j === i) el.setAttribute('aria-current', 'true');
    else el.removeAttribute('aria-current');
  });
  moveHighlight();
  const url = new URL(location);
  url.searchParams.set('v', i + 1);
  history.replaceState(null, '', url);
  mount(i);
}

items.forEach((el, i) => el.addEventListener('click', () => setActive(i)));
replay?.addEventListener('click', () => mount(current));
window.addEventListener('resize', moveHighlight);

document.addEventListener('keydown', (e) => {
  if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) || e.target.isContentEditable) return;
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const num = parseInt(e.key, 10);
  if (num >= 1 && num <= variants.length) setActive(num - 1);
  else if (e.key === 'ArrowRight') setActive((current + 1) % variants.length);
  else if (e.key === 'ArrowLeft') setActive((current - 1 + variants.length) % variants.length);
  else if (e.key === 'r' || e.key === 'R') mount(current);
});

setActive((parseInt(new URLSearchParams(location.search).get('v'), 10) || 1) - 1);
// Enable the slide only after first paint, so load doesn't animate.
requestAnimationFrame(() => requestAnimationFrame(() => picker.setAttribute('data-ready', '')));
"""


def picker_page(directions: list[dict]) -> str:
    """index.html: one render at a time, as large as the window lets it, behind the picker."""
    names = [slug(d["name"]) for d in directions]
    buttons = "\n".join(f'  <button class="proto-picker-item"{" data-active aria-current=\"true\"" if i == 0 else ""}>'
                        f'{html(d["name"])}</button>' for i, d in enumerate(directions))
    variants = ",\n".join(f"  () => '<img src=\"{n}.png\" alt=\"{html(d['name'])}\">'"
                          for d, n in zip(directions, names))
    return (f"<!doctype html>\n<!--\n{LICENSE}\n-->\n<html><head><meta charset=\"utf-8\"><title>Look picker</title>"
            f"<style>html,body{{margin:0;height:100%;background:#202020}}"
            f"#stage{{position:fixed;inset:0;display:flex;align-items:center;justify-content:center}}"
            f"#stage img{{display:block;max-width:100vw;max-height:100vh}}{PICKER_CSS}</style></head><body>\n"
            f'<main id="stage"></main>\n<nav class="proto-picker" aria-label="Prototype variants">\n'
            f'  <span class="proto-picker-highlight" aria-hidden="true"></span>\n{buttons}\n</nav>\n'
            f"<script>\nconst variants = [\n{variants}\n];\n{PICKER_JS}</script>\n</body></html>\n")


def html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;").replace("'", "&#39;")


def judge_brief(directions: list[dict], folder: Path) -> str:
    """The look questions on every render, for a judge that has not seen the game, in review_look.py's form."""
    import review_look
    asked = [*review_look.QUESTIONS, DIFFERS]
    lines = ["# Look review", "",
             "You have not seen this game's project, its events or how it was built, and you do not need to. Judge "
             "only what the screenshots show. Each is the first screen of one game drawn in another look. If a "
             "picture does not show it, answer no. Answer yes only for what a player would see as a mistake.", "",
             "Open each screenshot with your image tool, one at a time:", ""]
    lines += [f"{n}. {d['name']}: {(folder / (slug(d['name']) + '.png')).as_posix()}" for n, d in enumerate(directions, 1)]
    lines += ["", "Answer every question for every screenshot, yes or no:", ""]
    lines += [f"{n}. {q}" for n, q in enumerate(asked, 1)]
    first = directions[0]["name"]
    lines += ["", "Reply with one line per screenshot and question, and nothing else. Start each line with the "
                  "screenshot's name and the question's number. A yes says where on the screenshot the thing is and "
                  "what looks wrong; a no is the word alone. The form, not the content:", "", "```",
              f"{first} 1: no", f"{first} 2: yes - <where on the screenshot>: <what looks wrong>", "...", "```", ""]
    return "\n".join(lines)


def draw_brief(root: Path, wanted: dict, folder: Path, skill: str) -> str:
    """The art agent's whole task: the first play screen in three directions, and the form of directions.json."""
    c3proj = c3.load(root / "project.c3proj")
    first = c3proj.get("firstLayout") or "the first layout of project.c3proj"
    ink = paper_and_ink_palette()
    roles = ", ".join(f"{r} {c}" for r, c in wanted["palette"].items())
    w, h = wanted["view"]
    example = {"name": "Paper and ink", "axes": {dim: "..." for dim in prepare_art.DIMENSIONS},
               "right_when": "...", "cost": "...", "USER_LOOK": "", "ART_STYLE": PAPER_AND_INK,
               "PALETTE": {r: wanted["palette"][r] if r not in ink else ink[r] for r in wanted["palette"]}}
    lines = [
        "# Draw the first play screen of a Construct 3 game in three looks",
        "",
        f"The game is the project at {root.as_posix()}, {w}x{h} px. The user gave it a look: "
        f"{wanted.get('user_look') or '(see USER_LOOK in tools/build_project.py)'}. The user picks one of three "
        f"directions on the screen the player sees first, {first}, as the generator lays it out: "
        f"python {skill}/scripts/print_layout.py {first} --project {root.as_posix()} prints its objects, boxes and "
        f"labels, and art/wanted.json names what each sprite shows.",
        "",
        "The three directions:",
        "1. Paper and ink, the game's fallback look: USER_LOOK \"\", the template's PALETTE as it is, and an "
        f"ART_STYLE such as \"{PAPER_AND_INK}\".",
        "2. and 3. Two directions from the user's look, each named by what it is (\"Ink wash\", \"Neon arcade\"), "
        "each with a USER_LOOK that says where in the user's look it comes from.",
        "",
        f"Every two directions differ in {MIN_AXES} or more of the six dimensions of an art direction "
        f"({', '.join(prepare_art.DIMENSIONS)}), never only in their colours. Each keeps the roles of PALETTE ({roles}) "
        "with colours of its own, and the kinds of TEXT_SIZE "
        f"({', '.join(wanted.get('text_size') or {})}): the pick becomes the game's USER_LOOK, PALETTE and ART_STYLE "
        "and nothing else.",
        "",
        f"Draw each screen in {(folder / SCREENS).as_posix()}, one script for the three, with the skill's svg_kit: "
        f"read the docstring of {(c3.SKILL_DIR / 'scripts' / 'svg_kit.py').as_posix()} first. kit = svg_kit.Kit(); "
        "with kit.screen(\"ink-wash\") as d: draws the screen of the direction named \"Ink wash\", its name in lowercase "
        "words joined by dashes. Draw the objects of the screen where the layout has them and every label with "
        "d.text(x, y, words, kind=...) in its kind; every colour is a role, which the picker sets from the "
        "direction's PALETTE.",
        "",
        f"Write {(folder / DIRECTIONS).as_posix()}: {{\"directions\": [...]}}, one object per direction in this form, "
        "axes giving where it stands on each dimension in a phrase:",
        "",
        "```json",
        json.dumps(example, ensure_ascii=False),
        "```",
        "",
        f"Then run python {skill}/scripts/pick_look.py --project {root.as_posix()}, which runs your script, checks the "
        "directions, renders them and writes the picker. Fix what it refuses and run it again: three rounds at most. "
        "Open each render it names with the Read tool and ask of it what a player would see as a mistake: a label "
        "cut off or too faint, an object covering a label, two things that stand for different things drawn alike. "
        "Reply with the names of the three directions, or with what still fails after the last round.",
    ]
    return "\n".join(lines) + "\n"


def axis(d: dict, directions: list[dict]) -> str:
    """Where a direction stands on the dimensions in which it differs from every other direction, else on those
    in which it differs from any."""
    others = [o for o in directions if o is not d]
    dims = [dim for dim in prepare_art.DIMENSIONS if all(dim in differing(d, o) for o in others)] or \
        [dim for dim in prepare_art.DIMENSIONS if any(dim in differing(d, o) for o in others)]
    return "; ".join(d["axes"][dim] for dim in dims)


def table(rows: list[tuple[str, ...]]) -> list[str]:
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]) - 1)]
    return [" | ".join(f"{c:<{widths[i]}}" for i, c in enumerate(r[:-1])) + " | " + r[-1] for r in rows]


# --- the pick -------------------------------------------------------------------------------------
def assigned(text: str) -> dict:
    """The value of each of SETTINGS where the generator's text first sets it above the helpers, as a node."""
    lines = text.splitlines()
    begin = next((i + 1 for i, line in enumerate(lines) if c3.HELPERS_BEGIN.match(line)), len(lines) + 1)
    found = {}
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and node.lineno < begin:
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in SETTINGS:
                    found.setdefault(t.id, node.value)
    return found


def written(text: str, d: dict) -> str:
    """The generator's text with the direction's USER_LOOK, PALETTE's colour of each role and ART_STYLE, each
    value replaced where it stands, so the comments beside them stay."""
    data = text.encode("utf-8")
    starts = [0]                             # the byte offset of each line, which ast's columns count in
    for line in data.split(b"\n"):
        starts.append(starts[-1] + len(line) + 1)
    found = assigned(text)
    missing = [s for s in SETTINGS if s not in found]
    if missing:
        raise ValueError(f"it sets no {', '.join(missing)} above the helpers' begin marker")
    palette = found["PALETTE"]
    keys = [k.value if isinstance(k, ast.Constant) else None for k in palette.keys] \
        if isinstance(palette, ast.Dict) else []
    if set(keys) != set(d["PALETTE"]):
        raise ValueError(f"its PALETTE is not a dict of the roles {', '.join(d['PALETTE'])}; write the colours of "
                         f"the direction by hand")
    edits = [(found["USER_LOOK"], json.dumps(d["USER_LOOK"], ensure_ascii=False)),
             (found["ART_STYLE"], json.dumps(d["ART_STYLE"], ensure_ascii=False))]
    edits += [(v, "(%d, %d, %d)" % tuple(d["PALETTE"][k])) for k, v in zip(keys, palette.values)]
    for node, new in sorted(edits, key=lambda e: (e[0].lineno, e[0].col_offset), reverse=True):
        a = starts[node.lineno - 1] + node.col_offset
        b = starts[node.end_lineno - 1] + node.end_col_offset
        data = data[:a] + new.encode("utf-8") + data[b:]
    return data.decode("utf-8")


def pick(root: Path, wanted: dict, folder: Path, name: str, dry_run: bool) -> tuple[int, list[str]]:
    directions, problems = check(root, wanted, folder)
    if problems:
        return 1, problems + [f"next: fix the directions and run {c3.script_command(root, 'pick_look.py')} again"]
    by_name = {slug(d["name"]): d for d in directions}
    d = by_name.get(slug(name))
    if d is None:
        return 1, [f"--pick {name!r}: no such direction; the directions are "
                   f"{', '.join(x['name'] for x in directions)}{c3.closest(name, [x['name'] for x in directions])}"]
    render = folder / f"{slug(d['name'])}.png"
    if not render.is_file():
        return 1, [f"--pick: no {render.name}; run {c3.script_command(root, 'pick_look.py')} first, which renders it"]
    generator = root / c3.GENERATOR
    text = generator.read_text(encoding="utf-8")
    try:
        new = written(text, d)
    except (ValueError, SyntaxError) as e:
        return 1, [f"{c3.GENERATOR}: {e}"]
    got = {k: ast.literal_eval(v) for k, v in assigned(new).items()}
    want = {"USER_LOOK": d["USER_LOOK"], "ART_STYLE": d["ART_STYLE"],
            "PALETTE": {r: tuple(c) for r, c in d["PALETTE"].items()}}
    assert got == want, f"the rewritten generator sets {got}, not {want}"
    out = [f"picked: {d['name']}", f"  USER_LOOK = {json.dumps(d['USER_LOOK'], ensure_ascii=False)}",
           f"  ART_STYLE = {json.dumps(d['ART_STYLE'], ensure_ascii=False)}",
           "  PALETTE: " + ", ".join(f"{r} {tuple(c)}" for r, c in d["PALETTE"].items())]
    if dry_run:
        return 0, out + [f"dry run: {c3.GENERATOR} and {folder} are as they were"]
    generator.write_bytes(new.encode("utf-8"))
    look = root / prepare_art.LOOK
    look.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(render, look)
    shutil.rmtree(folder)
    return 0, out + [f"wrote them into {c3.GENERATOR}, kept its screen as {prepare_art.LOOK}, the look every picture "
                     f"is drawn or made in, and removed {folder}",
                     f"next: run python {c3.GENERATOR}, then {c3.script_command(root, 'art.py')}"]


# --- the run -------------------------------------------------------------------------------------
def run(root: Path, wanted: dict, folder: Path, skill: str, exe: str | None) -> tuple[int, list[str]]:
    out = []
    if (folder / SCREENS).is_file():
        ran, said = art.run_drawings(root, (folder / SCREENS).relative_to(root))
        if ran:
            return 1, [f"{SCREENS} failed with code {ran}:", *(f"  {line}" for line in said.splitlines()[-6:]),
                       f"next: fix {(folder / SCREENS).as_posix()} and run {c3.script_command(root, 'pick_look.py')}"]
    if not (folder / DIRECTIONS).is_file():
        folder.mkdir(parents=True, exist_ok=True)
        brief = folder / "draw-brief.md"
        brief.write_text(draw_brief(root, wanted, folder, skill), encoding="utf-8")
        return 0, [f"no {DIRECTIONS} yet; next: start a construct3:art-drawer sub-agent with {brief} as its whole "
                   f"task, or draw the three directions as that brief says yourself; then run "
                   f"{c3.script_command(root, 'pick_look.py')}"]
    directions, problems = check(root, wanted, folder)
    if problems:
        return 1, problems + [f"next: fix the directions and run {c3.script_command(root, 'pick_look.py')} again"]
    import open_in_editor as oe
    exe = exe or oe.browser_path()
    if not exe:
        return 3, ["no Edge, Chrome or Chromium here to render the directions: install one, or pass --browser EXE"]
    try:
        problems = render(root, exe, wanted, directions, folder)
    except (oe.DevToolsError, OSError) as e:
        return 3, [f"{Path(exe).name} could not render the directions: {e}"]
    if problems:
        return 1, problems + [f"next: fix the drawings and run {c3.script_command(root, 'pick_look.py')} again"]
    index = folder / "index.html"
    index.write_text(picker_page(directions), encoding="utf-8")
    judge = folder / "judge-brief.md"
    judge.write_text(judge_brief(directions, folder), encoding="utf-8")
    out += [f"checked: {len(directions)} directions, every two apart in {MIN_AXES} dimensions or more",
            *(f"render: {folder / (slug(d['name']) + '.png')}" for d in directions),
            f"picker: {index}: the keys 1 to {len(directions)} or the arrow keys switch the direction, "
            f"?v=2 opens the second",
            f"brief: give {judge} as its whole task to a construct3:look-judge sub-agent; fix each yes in that "
            f"direction's drawing and run this script again, before the user sees the picker",
            ""]
    out += table([("direction", "axis", "when it is right", "cost")]
                 + [(d["name"], axis(d, directions), d["right_when"], d["cost"]) for d in directions])
    out.append(f"stop: show the user {index} and ask which direction the game takes; then run "
               f"{c3.script_command(root, 'pick_look.py', ' --pick NAME')}")
    return 0, out


def main() -> int:
    c3.utf8_output()
    ap = c3.argument_parser(__doc__.split("\n\n")[0], "examples:\n"
                            "  python scripts/pick_look.py\n"
                            "  python scripts/pick_look.py --pick \"Ink wash\" --project D:/games/Coins\n\n"
                            "exit codes: 0 when the picker, the draw brief or the pick is written; 1 when a direction, "
                            "the pick or screens.py failed; 2 when no project or art/wanted.json is found; 3 when no "
                            "browser can render")
    ap.add_argument("--pick", metavar="NAME", help="the direction the user picked, by its name")
    ap.add_argument("--dry-run", action="store_true", help="with --pick: print the values, and change nothing")
    ap.add_argument("--browser", metavar="EXE", help="the Edge, Chrome or Chromium to render with")
    args = ap.parse_args()
    root = c3.find_project(args.project)
    where = root or Path.cwd()
    if root is None or not (where / "art" / "wanted.json").exists():
        print(f"no art/wanted.json in {where}: give every sprite an art() in build_images() of "
              f"tools/build_project.py and run it, which writes the list", file=sys.stderr)
        return 2
    wanted = json.loads((root / "art" / "wanted.json").read_text(encoding="utf-8"))
    folder = c3.script_folder(root, PICKER)
    skill = (c3.SKILL_DIR.relative_to(root) if c3.SKILL_DIR.is_relative_to(root) else c3.SKILL_DIR).as_posix()
    if args.pick:
        code, out = pick(root, wanted, folder, args.pick, args.dry_run)
    else:
        code, out = run(root, wanted, folder, skill, args.browser)
    shown = c3.fitting(out, args.limit)
    for line in out[:shown]:
        print(line)
    if shown < len(out):
        print(f"... {len(out) - shown} more lines; --limit 0 prints them all")
        print(out[-1])
    return code


if __name__ == "__main__":
    sys.exit(main())
