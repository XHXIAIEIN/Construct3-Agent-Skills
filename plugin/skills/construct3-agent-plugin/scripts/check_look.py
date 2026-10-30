"""Confirm the strict rules of assets/look-manifest.json on a project's files.

    python scripts/check_look.py [--project FOLDER] [--painted FILE ...] [--unit PX]

Run it after the generator's own check ends with ok:, on a project built from
assets/build_project.py, whoever edited the generator. It reads the images,
layouts and event sheets the editor would load and checks:

  alpha.pure            a clear pixel holds no colour, and a pixel-art
                        project's images hold one alpha value between clear
                        and opaque, the shadow's; in a viewport taller than
                        360 px the images keep the antialiased edges the
                        template draws. A
                        painting meant to keep soft edges in pixel art is
                        named with --painted, and the art that art.py
                        wrote is known by the mark it leaves in the file
  grid.world-placement  an instance of a world layer starts on the grid: its
                        box's left or right edge and top or bottom edge are
                        whole UNITs, the other side being the shadow's
  grid.runtime-spawn    an object created at runtime is not placed at a raw
                        random(): the template's grid_random() rounds it
  type.pixel-font       every character that the Sprite Fonts of
                        tools/pixel-font.json may show is baked into their
                        images, as scripts/bake_font.py --check reports;
                        one that is not draws as nothing
  motion.hit            no object type or family has the Flash behavior: a
                        hit shows as a colour, the template's hit_frame() and
                        hit_flash(). A rule of paper and ink, the fallback
                        look, so not checked when USER_LOOK in
                        tools/build_project.py names a look the user gave
  motion.squash-art     a squash, a size set to a share of the rest size that
                        the template's squash() keeps or of the image's size,
                        acts on the drawn art, not on an object whose
                        behavior collides
  motion.panel-from-zero
                        a HUD object does not grow its size or scale from
                        0 in both directions; the template's popup() opens
                        a panel near its size
  motion.value-restart  a value tween that starts from the number a Text
                        shows, or from a tween's value, stops its tag first,
                        as the template's count_up() does
  motion.hud-overshoot  a warning: a HUD object tweens with an overshoot
                        ease, which is for the world and the subject of a
                        moment, such as a title card
  motion.hud-ease-in    a warning: a HUD object fades in with an ease-in;
                        a fader or a dim that covers the viewport is left out
  motion.size-on-dying  a warning: an object that a size tween destroys is
                        squashed back to its rest size by another event,
                        whose size tween stops the destroying one
  screen.fill           a warning, not a finding: the project fills the
                        screen, Scale outer or Integer scale outer, not a
                        Letterbox mode, which shows bars
  screen.safe-area      a warning, not a finding: a project whose Viewport
                        fit is Cover, which draws under a phone's notch,
                        reads the safe area's insets in its events or scripts

UNIT and the behaviors that collide are the values of grid.unit and
motion.squash-art in the manifest, which the template holds too.
A layer at parallax 0 is the HUD, held to the viewport's edges, and is not
checked for the grid; neither is a rotated instance. An object type is on
the HUD when every instance the layouts place lies on such a layer. Whether the look works is the user's
call on a screenshot.

Exit 0: the last line starts with ok:. Exit 1: findings, or no project.
"""
import ast
import fnmatch
import json
import re
import struct
import sys
from pathlib import Path

# python -I leaves this script's folder off sys.path, and the modules beside it are imported from there
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import bake_font
import c3project as c3


def painted_mark(path: Path) -> bool:
    """Whether the PNG carries the text chunk scripts/art.py writes into a picture."""
    data = path.read_bytes()
    pos = 8
    while pos + 8 <= len(data):
        n, tag = struct.unpack(">I", data[pos:pos + 4])[0], data[pos + 4:pos + 8]
        if tag == b"tEXt" and data[pos + 8:pos + 8 + n].startswith(b"c3-art\0"):
            return True
        if tag == b"IDAT":
            return False
        pos += 12 + n
    return False


def check_alpha(root: Path, painted: list[str], out: list[str], soft: bool = False) -> int:
    """alpha.pure over images/; returns how many images were read. `soft`: the viewport is taller
    than 360 px, where the template antialiases every edge, so only a colour hidden under a clear
    pixel is a finding."""
    partial: dict[str, dict[int, tuple[int, int]]] = {}      # image: {alpha: first (x, y)}
    read = 0
    for png in sorted((root / "images").rglob("*.png")):
        rel = png.relative_to(root).as_posix()
        if any(fnmatch.fnmatch(png.name, p) or fnmatch.fnmatch(rel, p) for p in painted):
            continue
        img = c3.png_rgba(png.read_bytes())
        if img is None:
            out.append(f"alpha.pure: {rel} is not an 8-bit non-interlaced PNG; write it as the template's "
                       f"write_png() does, or name it with --painted")
            continue
        read += 1
        w, _, pixels = img
        hidden = [i for i, p in enumerate(pixels) if p[3] == 0 and p[:3] != (0, 0, 0)]
        if hidden:
            out.append(f"alpha.pure: {rel} has {len(hidden)} clear pixels that hold a colour, the first at "
                       f"({hidden[0] % w},{hidden[0] // w}); write a clear pixel as (0, 0, 0, 0)")
        if soft or painted_mark(png):       # an antialiased edge, or the soft edges of a picture of art.py
            continue
        for i, p in enumerate(pixels):
            if 0 < p[3] < 255:
                partial.setdefault(rel, {}).setdefault(p[3], (i % w, i // w))
    # The shadow is the alpha the most images hold; any other is a soft edge.
    held = [a for alphas in partial.values() for a in alphas]
    shadow = max(set(held), key=held.count) if held else None
    for rel, alphas in partial.items():
        others = sorted(a for a in alphas if a != shadow)
        if others:
            x, y = alphas[others[0]]
            more = f" and {len(others) - 1} more values" if len(others) > 1 else ""
            out.append(f"alpha.pure: {rel} has alpha {others[0]} at ({x},{y}){more}; the project's shadow is "
                       f"{shadow}, and a drawn image is clear, opaque or the shadow. A painting meant to keep soft "
                       f"edges: --painted {Path(rel).name}")
    return read


def on_grid(v: float, unit: int) -> bool:
    return abs(v / unit - round(v / unit)) < 1e-6


def json_files(root: Path, *folders: str) -> list[Path]:
    """The JSON files under these folders of the project, folder by folder and sorted, without the
    .uistate.json files the editor writes beside them."""
    return [path for folder in folders for path in sorted((root / folder).rglob("*.json"))
            if not path.name.endswith(".uistate.json")]


def check_grid(root: Path, unit: int, out: list[str]) -> int:
    """grid.world-placement over layouts/; returns how many instances were checked."""
    checked = 0
    for path in json_files(root, "layouts"):
        layout = c3.load(path)
        for layer, _ in c3.layers_of(layout.get("layers", [])):
            if layer.get("parallaxX", 1) == 0 and layer.get("parallaxY", 1) == 0:
                continue
            for inst in layer.get("instances", []):
                w = inst.get("world")
                if not w or w.get("angle"):
                    continue
                checked += 1
                left = w["x"] - w.get("originX", 0) * w["width"]
                top = w["y"] - w.get("originY", 0) * w["height"]
                if not ((on_grid(left, unit) or on_grid(left + w["width"], unit))
                        and (on_grid(top, unit) or on_grid(top + w["height"], unit))):
                    out.append(f"grid.world-placement: layout {layout.get('name', path.stem)} layer "
                               f"{layer.get('name')}: {inst.get('type')} at ({left:g},{top:g}) "
                               f"{w['width']:g}x{w['height']:g} is off the {unit} px grid; place a shape with "
                               f"shape_inst(type, image, col, row) and anything else with units() or snap()")
    return checked


def actions_of(node):
    if isinstance(node, dict):
        for a in node.get("actions", []) or []:
            if isinstance(a, dict):
                yield a
        for v in node.values():
            if isinstance(v, (dict, list)):
                yield from actions_of(v)
    elif isinstance(node, list):
        for v in node:
            yield from actions_of(v)


def check_spawn(root: Path, out: list[str]) -> int:
    """grid.runtime-spawn over eventSheets/; returns how many create actions were read."""
    read = 0
    for path in json_files(root, "eventSheets"):
        sheet = c3.load(path)
        for a in actions_of(sheet.get("events", [])):
            if a.get("id") != "create-object":
                continue
            read += 1
            params = a.get("parameters", {})
            for axis in ("x", "y"):
                expr = str(params.get(axis, ""))
                if "random(" in expr and not re.search(r"\b(floor|round|ceil)\(", expr):
                    out.append(f"grid.runtime-spawn: sheet {sheet.get('name', path.stem)}: create "
                               f"{params.get('object-to-create')} at {axis} = {expr}, a raw random(); write "
                               f"grid_random(lo, hi) plus the origin's offset, as the template's module_setup() does")
    return read


MANIFEST = Path(__file__).resolve().parent.parent / "assets" / "look-manifest.json"
RULES = {r["id"]: r for r in json.loads(MANIFEST.read_text(encoding="utf-8"))["rules"]}


def rule_value(rule: str, **view: int):
    """The value of a rule of assets/look-manifest.json, its expression read over the viewport's
    VIEW_W and VIEW_H, so the check holds the value the template holds."""
    return eval(RULES[rule]["value"], {"__builtins__": {}}, view)


# The behaviors that make an object collide, so a squash of its size moves its collision box.
COLLIDING = rule_value("motion.squash-art")
# The size a squash starts from and returns to: the rest size that squash() keeps, or the image's
REST_SIZE = re.compile(r"\b(ImageWidth|ImageHeight|restWidth|restHeight)\b")


def colliding_items(root: Path) -> dict[str, list[str]]:
    """Object types and families by name, with the behaviors that make them collide."""
    found = {}
    for path in json_files(root, "objectTypes", "families"):
        item = c3.load(path)
        ids = [b.get("behaviorId") for b in item.get("behaviorTypes", []) if b.get("behaviorId") in COLLIDING]
        if ids:
            found[item.get("name", path.stem)] = ids
    return found


def check_squash(root: Path, out: list[str]) -> None:
    """motion.squash-art over eventSheets/."""
    colliding = colliding_items(root)
    for path in json_files(root, "eventSheets"):
        sheet = c3.load(path)
        for a in actions_of(sheet.get("events", [])):
            obj = a.get("objectClass")
            if a.get("id") == "set-size" and obj in colliding and REST_SIZE.search(str(a.get("parameters", {}))):
                out.append(f"motion.squash-art: sheet {sheet.get('name', path.stem)}: {obj} is squashed but has "
                           f"{', '.join(colliding[obj])}, so its collision box grows into the floor; squash its art, "
                           f"a second object drawn with shape(..., oy=1) and pinned to {obj}")


# Eases that pass their end value and come back
OVERSHOOT = re.compile(r"back|elastic|bounce", re.I)
# Property tweens that change an instance's width and height together
SIZE_TWEENS = ("size", "scale")
# Property tweens whose next start releases a running one on the same property
SIZE_PROPERTIES = ("size", "scale", "offsetWidth", "offsetHeight", "offsetScaleX", "offsetScaleY")
# Triggers after which the picked instance cannot be one a tween is destroying: it is new, or its
# own tween has just ended
FRESH = ("on-created", "on-start-of-layout", "on-tweens-finished", "on-any-tweens-finished")
CREATES = {"create-object": "object-to-create", "spawn-another-object": "object"}


def action_lists(events: list, conds: tuple = (), above: tuple = ()):
    """(conditions, actions, actions of the enclosing blocks) of every block, a sub-event with its
    parents' conditions."""
    for ev in events or []:
        if not isinstance(ev, dict):
            continue
        here = (*conds, *(ev.get("conditions") or []))
        acts = [a for a in ev.get("actions") or [] if isinstance(a, dict)]
        if acts:
            yield here, acts, above
        yield from action_lists(ev.get("children"), here, (*above, *acts))


def hud_types(root: Path) -> tuple[set[str], set[str]]:
    """The object types every placed instance of which lies on a layer at parallax 0, the HUD, and
    of these the ones an instance of which covers the viewport, a fader or a dim."""
    project = c3.load(root / "project.c3proj")
    vw, vh = project.get("viewportWidth", 1920), project.get("viewportHeight", 1080)
    places: dict[str, set[bool]] = {}
    covers = set()
    for path in json_files(root, "layouts"):
        for layer, _ in c3.layers_of(c3.load(path).get("layers", [])):
            hud = layer.get("parallaxX", 1) == 0 and layer.get("parallaxY", 1) == 0
            for inst in layer.get("instances", []):
                places.setdefault(inst.get("type"), set()).add(hud)
                w = inst.get("world") or {}
                if hud and w.get("width", 0) >= vw and w.get("height", 0) >= vh:
                    covers.add(inst.get("type"))
    hud = {t for t, on in places.items() if on == {True}}
    return hud, covers & hud


def zero(expr) -> bool:
    return str(expr).strip() in ("0", "0.0")


def params_of(action: dict) -> dict:
    """An action's parameters by id; a call of a function lists its parameters instead."""
    p = action.get("parameters")
    return p if isinstance(p, dict) else {}


def tag_of(params: dict) -> str:
    return str(params.get("tags", "")).strip().strip('"')


def check_motion(root: Path, out: list[str], warned: list[str]) -> int:
    """motion.hud-overshoot, motion.hud-ease-in and motion.size-on-dying, warnings, and
    motion.panel-from-zero and motion.value-restart over eventSheets/; returns how many tweens were
    read."""
    hud, covers = hud_types(root)
    read = 0
    for path in json_files(root, "eventSheets"):
        sheet = c3.load(path)
        name = sheet.get("name", path.stem)
        # object: (size property, action list) of a tween that destroys it, and of a tween back to its rest size
        dying: dict[str, set[tuple[str, int]]] = {}
        squashed: dict[str, set[tuple[str, int]]] = {}
        for n, (conds, acts, above) in enumerate(action_lists(sheet.get("events", []))):
            for i, a in enumerate(acts):
                kind = a.get("id")
                if kind not in ("tween-one-property", "tween-two-properties", "tween-value"):
                    continue
                read += 1
                obj, p = a.get("objectClass"), params_of(a)
                prop, ease = p.get("property", "value"), str(p.get("ease", ""))
                before = [*above, *acts[:i]]
                if p.get("loop") == "yes" or p.get("ping-pong") == "yes":
                    continue
                if kind == "tween-value":
                    start, tag = str(p.get("start-value", "")), tag_of(p)
                    stopped = any(b.get("objectClass") == obj and (b.get("id") == "stop-all-tweens" or (
                        b.get("id") == "stop-tweens" and tag_of(params_of(b)) == tag)) for b in before)
                    guarded = any(c.get("id") in ("is-playing", "is-any-playing") and c.get("objectClass") == obj
                                  and c.get("isInverted") for c in conds)
                    if re.search(r"\.Text\b|\.Value\(", start) and not stopped and not guarded:
                        out.append(f"motion.value-restart: sheet {name}: {obj} starts the value tween {tag!r} from "
                                   f"{start}, the number it shows, without Stop {tag!r} first; a second value tween "
                                   f"under a tag that still plays runs beside the first, and the shown number jumps "
                                   f"when the first ends. Put stop_tweens({obj!r}, {tag!r}) before it, as the "
                                   f"template's count_up() does")
                    continue
                if prop in SIZE_PROPERTIES:
                    if p.get("destroy-on-complete") == "yes":
                        dying.setdefault(obj, set()).add((prop, n))
                    elif (REST_SIZE.search(str(p.get("end-value", "")) + str(p.get("end-x", "")))
                          and not any(c.get("id") in FRESH for c in conds)
                          and not any(params_of(b).get(CREATES.get(b.get("id"), "")) == obj for b in before)):
                        squashed.setdefault(obj, set()).add((prop, n))
                if obj not in hud:
                    continue
                if OVERSHOOT.search(ease):
                    warned.append(f"warning: motion.hud-overshoot: sheet {name}: {obj}, on the HUD, tweens {prop} "
                                  f"with {ease}. An overshoot ease is for world objects and the subject of a moment, "
                                  f"such as a title card or a banner; if {obj} is not that, give the tween "
                                  f"style=\"hud_in\" or \"hud_out\" of TWEEN_STYLE")
                if (re.match(r"easein(?!out)", ease) and prop == "offsetOpacity" and not zero(p.get("end-value"))
                        and obj not in covers):
                    warned.append(f"warning: motion.hud-ease-in: sheet {name}: {obj}, on the HUD, fades in with "
                                  f"{ease}, which starts slowest at the moment the player looks for it; give the "
                                  f"tween style=\"hud_in\" of TWEEN_STYLE, or an ease-out")
                if prop in SIZE_TWEENS and not (zero(p.get("end-x")) and zero(p.get("end-y"))):
                    wanted = {"size": ("set-size",), "scale": ("set-scale",)}[prop]
                    if any(b.get("objectClass") == obj and b.get("id") in wanted
                           and all(zero(v) for v in params_of(b).values()) for b in before):
                        out.append(f"motion.panel-from-zero: sheet {name}: {obj}, on the HUD, grows its {prop} from "
                                   f"0; a panel that opens from nothing reads as a jump. Start it near its size and "
                                   f"at opacity 0, as the template's popup() does from POPUP[\"scale\"]")
        for obj in sorted(dying):
            for prop in sorted({p for p, n in dying[obj] for q, m in squashed.get(obj, ()) if q == p and m != n}):
                warned.append(f"warning: motion.size-on-dying: sheet {name}: {obj} is destroyed by a {prop} tween, "
                              f"and another event tweens its {prop} back to its rest size. A {prop} tween stops "
                              f"the one running on that property, which then never destroys the instance; destroy it "
                              f"with a Timer or a Wait, or keep the squash off a dying instance")
    return read


def check_hit(root: Path, out: list[str]) -> None:
    """motion.hit over objectTypes/ and families/."""
    for path in json_files(root, "objectTypes", "families"):
        item = c3.load(path)
        for b in item.get("behaviorTypes", []):
            if b.get("behaviorId") == "Flash":
                out.append(f"motion.hit: {item.get('name', path.stem)} has the Flash behavior "
                           f"{b.get('name')}; a hit shows as a colour for an instant: draw a hit frame with "
                           f"hit_frame() and show it with hit_flash(), then remove the behavior")


def user_look(root: Path) -> str:
    """USER_LOOK of the project's generator: where the look the user gave comes from, or "" for
    paper and ink. A value that is not a plain string counts as a look the user gave."""
    generator = root / c3.GENERATOR
    if not generator.is_file():
        return ""
    for node in ast.parse(generator.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "USER_LOOK" for t in node.targets):
            try:
                return str(ast.literal_eval(node.value)).strip()
            except ValueError:
                return ast.unparse(node.value)
    return ""


def check_screen(project: dict, warned: list[str]) -> None:
    """screen.fill over project.c3proj, a warning: a Letterbox mode shows bars around the game on a
    screen whose shape differs from the viewport's, where the template fills the screen."""
    mode = (project.get("properties") or {}).get("fullscreenMode", "")
    if mode.startswith("letterbox"):
        want = "integer-scale-outer" if "integer" in mode else "scale-outer"
        warned.append(f"warning: screen.fill: project.c3proj has fullscreenMode {mode}, which shows bars where the "
                      f"screen's shape differs from the viewport's; the template's build_project() writes {want} "
                      f"(FULLSCREEN). Run the generator again, or remove the line that sets another mode. The "
                      f"generator also holds the HUD to the screen's edges (anchored()) and stretches the backdrop "
                      f"to them (backdrop()).")


# PlatformInfo's four SafeAreaInset expressions in an event, or the CSS env() names in a script.
SAFE_AREA = re.compile(r"safe.?area.?inset", re.I)


def check_safe_area(root: Path, project: dict, warned: list[str]) -> None:
    """screen.safe-area over project.c3proj, a warning. Viewport fit Cover draws the viewport under a
    notch and rounded corners, where the HUD that anchored() holds MARGIN from the edges then lies.
    An event expression or a script that reads the insets silences it."""
    if (project.get("properties") or {}).get("viewportFit") != "cover":
        return
    def expressions(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "parameters" and isinstance(value, dict):
                    yield from (str(v) for v in value.values())
                else:
                    yield from expressions(value)
        elif isinstance(node, list):
            for item in node:
                yield from expressions(item)
    texts = [e for f in json_files(root, "eventSheets") for e in expressions(c3.load(f))]
    texts += [f.read_text(encoding="utf-8", errors="replace") for f in (root / "scripts").rglob("*.[jt]s")]
    if any(SAFE_AREA.search(t) for t in texts):
        return
    warned.append("warning: screen.safe-area: project.c3proj has viewportFit cover, which draws the game under a "
                  "phone's notch and rounded corners. No event or script reads the safe area's insets, so the HUD "
                  "held to the screen's edges lies under the notch. Set viewportFit to auto, which keeps the whole "
                  "viewport visible, or move the HUD in by PlatformInfo.SafeAreaInsetTop and the other three insets, "
                  "which are CSS pixels.")


def check_pixel_font(root: Path, out: list[str]) -> None:
    """type.pixel-font: the characters in use that the Sprite Fonts of bake_font.MANIFEST lack."""
    if not (root / bake_font.MANIFEST).is_file():
        return
    manifest = c3.load(root / bake_font.MANIFEST)
    types = set(manifest.get("types") or [])
    layouts = bake_font.layouts_of(root)
    used = bake_font.chars_of(bake_font.in_use(root, layouts, types) + manifest.get("added", ""))
    have = bake_font.baked(layouts, types)
    missing = "".join(c for c in used if c not in have)
    if missing:
        out.append(f"type.pixel-font: {len(missing)} characters in use are not baked into the Sprite Fonts, and "
                   f"draw as nothing: {missing}; run {c3.script_command(root, 'bake_font.py')}")


def main() -> int:
    c3.utf8_output()
    ap = c3.argument_parser(__doc__.split("\n\n")[0], "examples:\n"
                            "  python scripts/check_look.py\n"
                            "  python scripts/check_look.py --project D:/games/Coins --painted title-*.png\n\n"
                            "exit codes: 0 when the last line starts with ok:, 1 on findings or no project")
    ap.add_argument("--painted", nargs="*", default=[], metavar="FILE",
                    help="image names or globs under images/ meant to keep their own soft edges")
    ap.add_argument("--unit", type=int, metavar="PX", help="the grid in px (default: from the viewport)")
    args = ap.parse_args()
    root = c3.find_project(args.project)
    if root is None or not (root / "project.c3proj").exists():
        print(f"no project.c3proj in {root or Path.cwd()}: run this from the project folder or pass "
              f"--project <folder>", file=sys.stderr)
        return 1
    project = c3.load(root / "project.c3proj")
    view = {"VIEW_W": project.get("viewportWidth", 1920), "VIEW_H": project.get("viewportHeight", 1080)}
    unit = args.unit or rule_value("grid.unit", **view)
    out: list[str] = []
    pixel_unit = rule_value("grid.unit", VIEW_W=0, VIEW_H=0)     # the grid of a pixel-art viewport
    images = check_alpha(root, args.painted, out, soft=unit != pixel_unit)
    instances = check_grid(root, unit, out)
    creates = check_spawn(root, out)
    check_pixel_font(root, out)
    look = user_look(root)
    if not look:
        check_hit(root, out)
    check_squash(root, out)
    warned: list[str] = []
    tweens = check_motion(root, out, warned)
    if look:
        print(f"look: the user's, from USER_LOOK ({look}); motion.hit, a rule of paper and ink, is not checked")
    check_screen(project, warned)
    check_safe_area(root, project, warned)
    for line in warned:
        print(line)
    shown = c3.fitting(out, args.limit)
    for line in out[:shown]:
        print(line)
    if shown < len(out):
        print(f"... {len(out) - shown} more; --limit 0 prints them all")
    summary = (f"{images} images, {instances} world instances on a {unit} px grid, {creates} runtime creations, "
               f"{tweens} tweens")
    print(f"{len(out)} findings: {summary}" if out else f"ok: {summary}")
    return 1 if out else 0


if __name__ == "__main__":
    sys.exit(main())
