"""Draw a generated game's art as SVG, for the SVG route of scripts/art.py.

A game's drawings are one script, tools/drawings.py, which scripts/art.py runs
with this folder on its path. It imports this module and draws every picture
that art() asks for:

    import svg_kit

    kit = svg_kit.Kit()            # art/wanted.json of the project the script is in

    def slime(d, squash=1.0):
        '''The slime in one pose: every frame of it is a call with other values.'''
        w, h = d.w, d.h * 0.7 * squash
        d.path(f"M {d.w * 0.1} {d.ground} Q {d.w / 2} {d.ground - 2 * h} {d.w * 0.9} {d.ground} Z",
               fill="reward", line="ink", grain=True)
        d.circle(d.w * 0.38, d.ground - h * 0.6, d.unit / 4, fill="ink")

    with kit.drawing("slime-default-000.png") as d:
        slime(d)
    with kit.drawing("slime-default-001.png") as d:
        slime(d, squash=0.8)

Colours are the roles of the game's PALETTE. A shape names a role, never a
colour, and the file holds the role as a CSS variable that art.py sets when it
renders, so a game's drawings share its colours, and a hit frame is the same
drawing with the picture's role in the flash colour. shade() and light() mix a
role towards ink or canvas for the dark and lit sides of a form.

Every drawing is the box that art() gave it, in px. `d.ground`, the bottom of
the box, is the line its feet stand on, so the frames of one object share
their box and baseline when they come from one function. In pixel art the
drawing is on the pixel grid at the game's size: pixels() lays rows of
characters, one per pixel, and every edge stays hard.

A shape can take one of the textures, each an SVG filter of this module:
grain=True for a paper grain inside the shape, rough=True for an edge drawn by
hand, wash=True for a watercolour edge; stroke() draws a brush line that
thickens in the middle. d.gradient() is a fill that runs from one role to
another along an ease curve, so it has no hard edge where it starts and ends.
Every id in a file starts with the drawing's own name, because two drawings
inlined on one page that share an id both paint with the first one's
definition.

A box drawn inside a rounded box takes inner(), which gives the inner box and
its radius, the outer radius less the gap, so the gap stays even round the
corners:

    panel = dict(x=0, y=0, w=d.w, h=d.h, r=d.unit / 2)
    d.rect(**panel, fill="ink")
    d.rect(**svg_kit.inner(**panel, pad=d.line * 2), fill="canvas")

A set of icons is drawn through one kit.icons() call, which fixes the stroke
width, the corner radius and the weight of every icon drawn through it:

    icons = kit.icons(stroke=4, radius=4, weight="line")
    with icons.drawing("heart-default-000.png") as d:
        d.path("M 8 20 ...")        # a line 4 px wide in the picture's role

A first play screen in a look of the picker (scripts/pick_look.py) is a
drawing of the viewport's size, kit.screen(name), and its labels are
d.text(..., kind=), one of the kinds of TEXT_SIZE.
"""
import json
import math
import re
import sys
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import c3project as c3

# The SVG filters a shape can take, by name; `{id}` is the drawing's prefix and the filter's name.
FILTERS = {
    "grain": ('<filter id="{id}" x="-10%" y="-10%" width="120%" height="120%">'
              '<feTurbulence type="fractalNoise" baseFrequency="{grain}" numOctaves="2" seed="{seed}" result="n"/>'
              '<feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -1.4 0.9" result="m"/>'
              '<feComposite in="SourceGraphic" in2="m" operator="in" result="g"/>'
              '<feComposite in="g" in2="SourceGraphic" operator="arithmetic" k2="0.25" k3="0.75"/></filter>'),
    "rough": ('<filter id="{id}" x="-5%" y="-5%" width="110%" height="110%">'
              '<feTurbulence type="fractalNoise" baseFrequency="{rough}" numOctaves="2" seed="{seed}"/>'
              '<feDisplacementMap in="SourceGraphic" scale="{wobble}" xChannelSelector="R" yChannelSelector="G"/></filter>'),
    "wash": ('<filter id="{id}" x="-5%" y="-5%" width="110%" height="110%">'
             '<feTurbulence type="fractalNoise" baseFrequency="{rough}" numOctaves="3" seed="{seed}"/>'
             '<feDisplacementMap in="SourceGraphic" scale="{wobble}" xChannelSelector="R" yChannelSelector="G" result="d"/>'
             '<feGaussianBlur in="d" stdDeviation="{blur}" result="b"/>'
             '<feComposite in="d" in2="b" operator="arithmetic" k1="0" k2="0.6" k3="0.4"/></filter>'),
}


# Control points of the ease curves a gradient takes, as CSS names them
EASES = {"linear": (0, 0, 1, 1), "ease": (0.25, 0.1, 0.25, 1), "ease-in": (0.42, 0, 1, 1),
         "ease-out": (0, 0, 0.58, 1), "ease-in-out": (0.42, 0, 0.58, 1)}
WEIGHTS = ("line", "solid")                  # an icon drawn as a line, or filled
PICKER = "pick-look"                         # .tmp/scripts/pick-look/, where a screen of the look picker is written


def wanted(root: Path) -> dict:
    """art/wanted.json of the project at root, which the generator writes."""
    path = root / "art" / "wanted.json"
    if not path.is_file():
        sys.exit(f"no {path}: run python tools/build_project.py, which writes what art() asks for")
    return json.loads(path.read_text(encoding="utf-8"))


def stem_of(rel: str) -> str:
    return rel[:-len(".png")] if rel.endswith(".png") else rel


def num(v: float) -> str:
    """A coordinate as SVG writes it: at most two decimals, no trailing zeros."""
    return f"{v:.2f}".rstrip("0").rstrip(".") if v != int(v) else str(int(v))


def inner(x: float, y: float, w: float, h: float, r: float, pad: float) -> dict:
    """The box `pad` px inside the rounded box (x, y, w, h) of corner radius r, with the radius r - pad,
    never below 0, as d.rect() takes it: d.rect(**inner(...), fill=...)."""
    if 2 * pad >= min(w, h):
        sys.exit(f"inner(): a gap of {num(pad)} px leaves nothing of a {num(w)}x{num(h)} box; take a smaller pad")
    return {"x": x + pad, "y": y + pad, "w": w - 2 * pad, "h": h - 2 * pad, "r": max(0, r - pad)}


def eased(t: float, ease: str) -> float:
    """How far the ease curve of that name is at the share t of its time, both from 0 to 1."""
    x1, y1, x2, y2 = EASES[ease]

    def bezier(a: float, b: float, s: float) -> float:
        return 3 * a * s * (1 - s) ** 2 + 3 * b * s * s * (1 - s) + s ** 3

    lo, hi = 0.0, 1.0
    for _ in range(40):                      # the curve's x rises with s, so halving finds the s of t
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if bezier(x1, x2, mid) < t else (lo, mid)
    return bezier(y1, y2, (lo + hi) / 2)


class Kit:
    """The game's roles, grid and pictures, read from art/wanted.json."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or c3.find_project(None) or Path.cwd()
        self.wanted = wanted(self.root)
        self.roles = list(self.wanted["palette"])
        self.unit = self.wanted["unit"]
        self.line = self.wanted["line_width"]
        self.pixel_art = self.wanted["pixel_art"]
        self.items = {item["file"]: item for item in self.wanted["images"]}

    def svg_items(self) -> list[dict]:
        """The pictures that take the SVG route."""
        return [item for item in self.items.values() if item.get("route") == "svg"]

    def drawing(self, rel: str) -> "Drawing":
        return Drawing(self, self.item(rel))

    def item(self, rel: str) -> dict:
        if rel not in self.items:
            near = ", ".join(sorted(self.items)[:8])
            sys.exit(f"drawing({rel!r}): art() asks for no such picture; art/wanted.json holds {near}")
        return self.items[rel]

    def icons(self, stroke: float | None = None, radius: float | None = None, weight: str = "line") -> "Icons":
        """A set of icons that share a stroke `stroke` px wide, the game's line width by default, corners of
        `radius` px, an eighth of a unit by default, and one weight of WEIGHTS: "line" draws every shape as a
        line in the picture's role, "solid" fills it and draws its edge in the same colour."""
        if weight not in WEIGHTS:
            sys.exit(f"icons(weight={weight!r}): the weights are {', '.join(WEIGHTS)}")
        return Icons(self, stroke or self.line, self.unit / 8 if radius is None else radius, weight)

    def screen(self, name: str) -> "Drawing":
        """The first play screen in one look of the picker, a drawing of the viewport's size, written to
        .tmp/scripts/pick-look/<name>.svg; its colours are the roles, which the picker sets per look."""
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            sys.exit(f"screen({name!r}): a screen's name is lowercase words joined by dashes, such as 'ink-wash'")
        w, h = self.wanted["view"]
        return Drawing(self, {"file": name + ".png", "width": w, "height": h, "kind": "screen"},
                       c3.script_folder(self.root, PICKER))


class Drawing:
    """One picture: shapes added in order, back to front, written to art/<name>.svg on exit."""

    def __init__(self, kit: Kit, item: dict, folder: Path | None = None) -> None:
        self.kit, self.item = kit, item
        self.folder = folder or kit.root / "art"
        self.w, self.h = item["width"], item["height"]
        self.unit, self.line, self.pixel_art = kit.unit, kit.line, kit.pixel_art
        self.prefix = stem_of(item["file"])
        self.ground = self.h
        self.body: list[str] = []
        self.defs: dict[str, str] = {}
        self.depth = 0

    def __enter__(self) -> "Drawing":
        return self

    def __exit__(self, kind, *_) -> None:
        if kind is None:
            self.save()

    # --- colours ---------------------------------------------------------------------------
    def colour(self, role: str) -> str:
        if role not in self.kit.roles:
            sys.exit(f"{self.prefix}: {role!r} is no role of PALETTE; the roles are {', '.join(self.kit.roles)}. "
                     f"A colour the game lacks is a new role of PALETTE in tools/build_project.py")
        return f"var(--{role})"

    def mixed(self, how: str) -> None:
        if self.pixel_art:
            sys.exit(f"{self.prefix}: pixel art takes the roles of PALETTE alone, so it has no {how}(); a colour the "
                     f"game lacks is a new role of PALETTE in tools/build_project.py")

    def shade(self, role: str, share: float = 0.3) -> str:
        """The role mixed `share` of the way towards ink: the side of a form away from the light."""
        self.mixed("shade")
        return f"color-mix(in srgb, {self.colour(role)}, {self.colour('ink')} {round(share * 100)}%)"

    def light(self, role: str, share: float = 0.3) -> str:
        """The role mixed `share` of the way towards canvas: the side of a form the light falls on."""
        self.mixed("light")
        return f"color-mix(in srgb, {self.colour(role)}, {self.colour('canvas')} {round(share * 100)}%)"

    def paint(self, value: str | None) -> str:
        """A role's name, or a shade() or light() of one, as a CSS value; None is no paint."""
        if value is None:
            return "none"
        return value if value.startswith(("var(", "color-mix(", "url(")) else self.colour(value)

    def gradient(self, name: str, start: str, end: str, x1: float = 0, y1: float = 0, x2: float = 0,
                 y2: float = 1, ease: str = "ease-in-out", steps: int = 8, start_opacity: float = 1,
                 end_opacity: float = 1) -> str:
        """A fill from the role `start` to the role `end`, and from one opacity to the other, along the line
        (x1, y1) to (x2, y2) in shares of the shape's box, top to bottom by default. `steps` stops between the
        two lie on the ease curve of EASES, so the change starts and ends without a hard edge. Returns the paint
        to give a shape's fill, d.rect(..., fill=d.gradient("sky", "canvas", "reward"))."""
        self.mixed("gradient")
        if ease not in EASES:
            sys.exit(f"{self.prefix}: gradient(ease={ease!r}): the curves are {', '.join(EASES)}")
        gid = f"{self.prefix}-{name}"
        stops = []
        for i in range(steps + 2):
            t = i / (steps + 1)
            k = eased(t, ease)
            colour = f"color-mix(in srgb, {self.colour(start)}, {self.colour(end)} {num(k * 100)}%)"
            opacity = start_opacity + (end_opacity - start_opacity) * k
            stops.append(f'<stop offset="{num(t * 100)}%" style="stop-color:{colour};stop-opacity:{num(opacity)}"/>')
        text = (f'<linearGradient id="{gid}" x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}">'
                + "".join(stops) + "</linearGradient>")
        if self.defs.get(gid, text) != text:
            sys.exit(f"{self.prefix}: gradient({name!r}) is defined twice, with other values; give the second "
                     f"another name")
        self.defs[gid] = text
        return f"url(#{gid})"

    # --- textures --------------------------------------------------------------------------
    def texture(self, name: str) -> str:
        fid = f"{self.prefix}-{name}"
        if fid not in self.defs:
            seed = sum(map(ord, self.prefix)) % 97
            self.defs[fid] = FILTERS[name].format(
                id=fid, seed=seed, grain=num(2.4 / max(1, self.unit / 8)), rough=num(0.9 / self.unit * 4),
                wobble=num(max(1.0, self.line * 0.9)), blur=num(max(0.5, self.line / 3)))
        return f"url(#{fid})"

    # --- shapes ----------------------------------------------------------------------------
    def shape(self, tag: str, fill: str | None = None, line: str | None = None, line_width: float | None = None,
              opacity: float | None = None, grain: bool = False, rough: bool = False, wash: bool = False,
              **attrs) -> None:
        """An SVG element of `tag`, filled with a role and drawn round with the role `line`, `line_width`
        px wide, the game's outline width by default. One texture at most."""
        style = [f"fill:{self.paint(fill)}"]
        if line is not None:
            style += [f"stroke:{self.paint(line)}", f"stroke-width:{num(line_width or self.line)}",
                      "stroke-linejoin:round", "stroke-linecap:round"]
        if opacity is not None:
            style.append(f"opacity:{num(opacity)}")
        textures = [name for name, on in (("grain", grain), ("rough", rough), ("wash", wash)) if on]
        if len(textures) > 1:
            sys.exit(f"{self.prefix}: one texture a shape, not {' and '.join(textures)}; group the shape for a second")
        if textures and self.pixel_art:
            sys.exit(f"{self.prefix}: pixel art keeps hard edges, so a shape takes no {textures[0]}")
        parts = [f'{k.rstrip("_").replace("_", "-")}="{num(v) if isinstance(v, (int, float)) else v}"'
                 for k, v in attrs.items()]
        if textures:
            parts.append(f'filter="{self.texture(textures[0])}"')
        self.body.append("  " * self.depth + f'<{tag} {" ".join(parts)} style="{";".join(style)}"/>')

    def rect(self, x: float, y: float, w: float, h: float, fill: str | None = None, r: float = 0, **kw) -> None:
        self.shape("rect", fill, x=x, y=y, width=w, height=h, **({"rx": r} if r else {}), **kw)

    def circle(self, cx: float, cy: float, r: float, fill: str | None = None, **kw) -> None:
        self.shape("circle", fill, cx=cx, cy=cy, r=r, **kw)

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, fill: str | None = None, **kw) -> None:
        self.shape("ellipse", fill, cx=cx, cy=cy, rx=rx, ry=ry, **kw)

    def polygon(self, points: list[tuple[float, float]], fill: str | None = None, **kw) -> None:
        self.shape("polygon", fill, points=" ".join(f"{num(x)},{num(y)}" for x, y in points), **kw)

    def path(self, d: str, fill: str | None = None, **kw) -> None:
        self.shape("path", fill, d=d, **kw)

    def stroke(self, points: list[tuple[float, float]], role: str, width: float | None = None,
               ends: float = 0.25) -> None:
        """A brush line through `points`, smoothed, `width` px across in the middle and `ends` of that at
        its two ends: a fold, a strand of hair, a crack."""
        if len(points) < 2:
            sys.exit(f"{self.prefix}: stroke() takes two points or more")
        width = width or self.line * 1.5
        pts = smooth(points)
        left, right = [], []
        for i, (x, y) in enumerate(pts):
            ax, ay = pts[max(0, i - 1)]
            bx, by = pts[min(len(pts) - 1, i + 1)]
            dx, dy = bx - ax, by - ay
            n = math.hypot(dx, dy) or 1
            t = i / (len(pts) - 1)
            half = width / 2 * (ends + (1 - ends) * math.sin(math.pi * t))
            left.append((x - dy / n * half, y + dx / n * half))
            right.append((x + dy / n * half, y - dx / n * half))
        outline = left + right[::-1]
        d = "M " + " L ".join(f"{num(x)} {num(y)}" for x, y in outline) + " Z"
        self.shape("path", role, d=d)

    def pixels(self, rows: list[str], legend: dict[str, str], x: int = 0, y: int = 0) -> None:
        """Pixel art: one character per pixel from (x, y), each a role of `legend`; a space or a dot is
        clear. A run of one character on a row is one rectangle."""
        for r, row in enumerate(rows):
            c = 0
            while c < len(row):
                ch = row[c]
                run = c
                while run < len(row) and row[run] == ch:
                    run += 1
                if ch not in " .":
                    if ch not in legend:
                        sys.exit(f"{self.prefix}: pixels() row {r} has {ch!r}, which the legend does not name")
                    self.rect(x + c, y + r, run - c, 1, legend[ch])
                c = run

    def text(self, x: float, y: float, words: str, kind: str, fill: str = "ink", anchor: str = "start") -> None:
        """A label whose baseline starts at (x, y), in the size of the kind `kind` of TEXT_SIZE and the game's
        font; `anchor` is "start", "middle" or "end". The look picker holds every label to its kind's size."""
        sizes = self.kit.wanted.get("text_size")
        if sizes is None:
            sys.exit(f"{self.prefix}: art/wanted.json has no text_size, which the helpers of an older template do "
                     f"not write: refresh them with the skill's install.py and run the generator")
        if kind not in sizes:
            sys.exit(f"{self.prefix}: text(kind={kind!r}): the kinds of TEXT_SIZE are {', '.join(sizes)}")
        size = sizes[kind] * (1 if self.pixel_art else 4 / 3)        # pt to px; a Sprite Font's size is in px
        words = words.replace("&", "&amp;").replace("<", "&lt;")
        self.body.append("  " * self.depth + f'<text class="{kind}" x="{num(x)}" y="{num(y)}" '
                         f'text-anchor="{anchor}" style="fill:{self.paint(fill)};font-size:{num(size)}px">'
                         f"{words}</text>")

    class _Group:
        def __init__(self, d: "Drawing", attrs: str) -> None:
            self.d, self.attrs = d, attrs

        def __enter__(self):
            self.d.body.append("  " * self.d.depth + f"<g{self.attrs}>")
            self.d.depth += 1
            return self.d

        def __exit__(self, *_):
            self.d.depth -= 1
            self.d.body.append("  " * self.d.depth + "</g>")

    def group(self, transform: str = "", opacity: float | None = None) -> "_Group":
        """Shapes drawn inside `with d.group(...)` share a transform, such as a pose's rotation:
        `rotate(-10 32 60)`, or an opacity."""
        attrs = (f' transform="{transform}"' if transform else "") + \
            (f' opacity="{num(opacity)}"' if opacity is not None else "")
        return self._Group(self, attrs)

    # --- the file --------------------------------------------------------------------------
    def svg(self) -> str:
        crisp = ' shape-rendering="crispEdges"' if self.pixel_art else ""
        defs = f"  <defs>{''.join(self.defs.values())}</defs>\n" if self.defs else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}"{crisp}>\n{defs}' + "\n".join("  " + b for b in self.body)
                + "\n</svg>\n")

    def save(self) -> Path:
        if not self.body:
            sys.exit(f"{self.prefix}: the drawing is empty")
        path = self.folder / f"{self.prefix}.svg"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.svg(), encoding="utf-8", newline="\n")
        return path


class Icons:
    """A set of icons drawn with one stroke width, one corner radius and one weight; see Kit.icons()."""

    def __init__(self, kit: Kit, stroke: float, radius: float, weight: str) -> None:
        self.kit, self.stroke, self.radius, self.weight = kit, stroke, radius, weight

    def drawing(self, rel: str) -> "Icon":
        return Icon(self, self.kit.item(rel))


class Icon(Drawing):
    """One icon of a set: every shape takes the set's stroke and weight, and every rectangle its radius."""

    def __init__(self, icons: Icons, item: dict) -> None:
        super().__init__(icons.kit, item)
        self.icons = icons
        self.line = icons.stroke

    def shape(self, tag: str, fill: str | None = None, line: str | None = None, line_width: float | None = None,
              **kw) -> None:
        """As Drawing.shape(), in the set's weight: a line icon fills nothing and draws its shapes as lines in the
        picture's role, or in `line`; a solid one fills them in the picture's role, or in `fill`, with an edge of
        the same colour. The stroke width is the set's."""
        if line_width not in (None, self.icons.stroke):
            sys.exit(f"{self.prefix}: an icon of the set takes its stroke of {num(self.icons.stroke)} px, not "
                     f"{num(line_width)}; change the stroke of kit.icons() for every icon")
        role = self.item.get("role", "ink")
        if self.icons.weight == "line":
            if fill is not None:
                sys.exit(f"{self.prefix}: a line icon fills nothing; draw it as lines, or make the set solid")
            super().shape(tag, None, line or role, self.icons.stroke, **kw)
        else:
            super().shape(tag, fill or role, fill or role, self.icons.stroke, **kw)

    def rect(self, x: float, y: float, w: float, h: float, fill: str | None = None, r: float | None = None,
             **kw) -> None:
        """A rectangle with the set's corner radius, or a smaller one for a box inside another, as inner() gives."""
        if r is not None and r > self.icons.radius:
            sys.exit(f"{self.prefix}: an icon's corners are {num(self.icons.radius)} px at most, not {num(r)}; change "
                     f"the radius of kit.icons() for every icon")
        super().rect(x, y, w, h, fill, r=self.icons.radius if r is None else r, **kw)


def smooth(points: list[tuple[float, float]], steps: int = 6) -> list[tuple[float, float]]:
    """A Catmull-Rom curve through the points, `steps` points between each two."""
    if len(points) < 3:
        (ax, ay), (bx, by) = points
        return [(ax + (bx - ax) * i / steps, ay + (by - ay) * i / steps) for i in range(steps + 1)]
    p = [points[0], *points, points[-1]]
    out = []
    for i in range(1, len(p) - 2):
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p[i - 1], p[i], p[i + 1], p[i + 2]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append((0.5 * (2 * x1 + (-x0 + x2) * t + (2 * x0 - 5 * x1 + 4 * x2 - x3) * t2
                               + (-x0 + 3 * x1 - 3 * x2 + x3) * t3),
                        0.5 * (2 * y1 + (-y0 + y2) * t + (2 * y0 - 5 * y1 + 4 * y2 - y3) * t2
                               + (-y0 + 3 * y1 - 3 * y2 + y3) * t3)))
    out.append(points[-1])
    return out
