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

Every drawing is the box that art() gave it, in px. `d.ground` is the line its
feet stand on when its origin is at its feet, so the frames of one object share
their box and baseline when they come from one function. In pixel art the
drawing is on the pixel grid at the game's size: pixels() lays rows of
characters, one per pixel, and every edge stays hard.

A shape can take one of the textures, each an SVG filter of this module:
grain=True for a paper grain inside the shape, rough=True for an edge drawn by
hand, wash=True for a watercolour edge; stroke() draws a brush line that
thickens in the middle. Every id in a file starts with the drawing's own name,
because two drawings inlined on one page that share an id both paint with the
first one's definition.
"""
import json
import math
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
        if rel not in self.items:
            near = ", ".join(sorted(self.items)[:8])
            sys.exit(f"drawing({rel!r}): art() asks for no such picture; art/wanted.json holds {near}")
        return Drawing(self, self.items[rel])


class Drawing:
    """One picture: shapes added in order, back to front, written to art/<name>.svg on exit."""

    def __init__(self, kit: Kit, item: dict) -> None:
        self.kit, self.item = kit, item
        self.w, self.h = item["width"], item["height"]
        self.unit, self.line, self.pixel_art = kit.unit, kit.line, kit.pixel_art
        self.prefix = stem_of(item["file"])
        ox, oy = item.get("origin", [0.5, 0.5])
        self.ground = self.h if oy >= 0.75 else self.h * oy
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
        return value if value.startswith(("var(", "color-mix(")) else self.colour(value)

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
        path = self.kit.root / "art" / f"{self.prefix}.svg"
        path.write_text(self.svg(), encoding="utf-8", newline="\n")
        return path


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
