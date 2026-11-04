"""Preview a project, visit every layout, and print for each a screenshot and the
mechanical faults on it: what the runtime shows wrong.

    python scripts/check_screens.py [PATH ...] [--project FOLDER] [--layouts NAME ...] [--settle SECONDS]
                                    [--viewport W H] [--data STATE ...] [--release rNNN] [--browser EXE] [--shots DIR]
                                    [--out RESULT.json] [--headed] [--profile FOLDER]

Run it after open_in_editor.py --preview passes. It previews the project as F5
does, then goes to each layout in turn with the runtime's goToLayout, lets it run
SETTLE seconds, takes a screenshot, and reads every instance of the layout from
the runtime. It prints one line per finding, each naming the layout, the object
type, the instance's UID and what to change:

  text      a visible Text whose text needs more room than its box
  stacked   instances of one object type on one box, showing one frame: created
            at runtime and never moved apart. Different frames there (a fill
            under its rim) and Drawing Canvases are left out
  overlap   two visible instances on a layer of parallax 0 (the HUD), or two
            texts on any layer, one covering half of the other. Left out: one
            inside a larger non-Text one (a label on its button), one
            hierarchy, a text and its shadow, an overlay over half the screen
  edge      a visible HUD instance that the edge of the screen cuts
  frame     every instance of a Sprite type shows one frame of an animation
            that has more, though a text instance variable differs between them
  placeholder  a visible text still "Text" or Lorem ipsum after the start
  faint     a text that reads under 4.5:1, or 3:1 when large, on what lies behind
            it on screen: its strokes' core pixels against them with every text
            hidden
  unlimited Texts that events set with no longest text in tools/texts.json

A finding fails the run. A warning does not: unlimited warns, and so does a
finding that only a guessed longest text causes, because the guess may be longer
than anything the game shows.

Each layout is also shown in the other data states of --data: the longest
text (or a guess), no text, and counts of 1. Without --viewport, it is also
shown on two more screen shapes that its orientations allow. There text,
overlap and edge run again, printed with @ and where.

A screenshot 99.9% of one colour, black or clear, is taken again 1 s later,
twice at most.

Screenshots go to --shots as <layout>.png, the whole result to --out.
The last two lines are screens: and next:.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

# python -I leaves this script's folder off sys.path, and the modules beside it are imported from there
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import c3project as c3
import open_in_editor as oe
import preview_project as play

EPILOG = """examples:
  python scripts/check_screens.py
  python scripts/check_screens.py --layouts Menu Map --settle 2
  python scripts/check_screens.py --viewport 430 932 --data demo

output:
  opened   <project>  (<window title>, <the editor it opened in>)
  layout 'Map' (2 of 3): screenshot .tmp/scripts/check-screens/shots/Map.png
    text: Text Title uid 12 "Choose your path": the text needs 212x40 px and its box is 160x40 ...
    stacked: Text CardName: 5 instances on one box at (300, 420) 120x30, uids 41, 42, 43 ...
    edge @phone worst: ScoreText uid 9 "9999999": the right edge of the screen cuts it ...
    warning unlimited: events set the text of ScoreText, and nothing says how long it gets ...
    runtime: <an error the layout logged, with its event, and (N times) when it came more than once>
  layout 'Combat' (3 of 3): started, and its events went on to 'Map' before the screenshot; ...
  screens: 3 findings to fix and 1 that warns on 3 layouts, 0 runtime errors; full result in
    .tmp/scripts/check-screens/result.json, screenshots in .tmp/scripts/check-screens/shots
  next: <what to do>

exit codes: 0 every layout was visited with no finding and no runtime error; 1 a finding, a runtime error, or the
project did not open; 2 the project or the editor could not be used; 3 no browser here, or the preview did not run,
so no layout was visited; 5 another run holds the browser profile, named in the line with its pid: wait for it to
end, or pass --profile for a profile of this run's own
"""

# Pixels of slack before a text, an overlap or a box on screen counts.
TOLERANCE = 4
# How many times its box's height a text may take: a line a little taller than its
# box still draws whole, a second line does not.
WRAPPED = 1.5
# Share of the smaller drawn box two instances may overlap by: a counter may touch
# its icon, but not cover half of it.
OVERLAP_SHARE = 0.5
# Share of the screen past which an instance is an overlay drawn over the HUD on purpose.
OVERLAY = 0.5
# Shots of one layout in all while it is one colour (c3project.BLANK), and the seconds between them.
BLANK_TRIES = 3
BLANK_WAIT = 1.0

# A Text's default text, in any case, or Lorem ipsum anywhere in it
PLACEHOLDER = re.compile(r"^\s*text\s*$|lorem ipsum", re.I)

# The data states a layout is shown in.
DATA_STATES = ("demo", "worst", "empty", "one")
# The worst text guessed for a Text with no declared longest: a count, a name, a Chinese name.
WORST_NUMBER = "9999999"
WORST_NAME = "Wolfeschlegel-Steinhausen"
WORST_WIDE = "最长的名字也要放得下才行"
# A count in a text: digits, each spaced from the next by one narrow space in a tag whose letters are spaced apart.
COUNT = re.compile(r"\d(?:([   ])?\d)*")
# Actions that set a Text's text, by their id in an event sheet.
SETS_TEXT = ("set-text", "append-text", "typewriter-text")
# The text of each Text type at its longest, which the generator template writes from its helpers' `longest`, and
# a project of any other making may write by hand: {"longest": {"ScoreText": "999999"}}.
DECLARED = Path("tools", "texts.json")

# The shapes of screen each layout is shown on without --viewport, besides the project's own, by the
# orientations the project allows: Scale outer and Anchor put the HUD in another place on each. The shorter side
# stays the project's.
SHAPES = {"landscape": (("4x3", 4 / 3), ("16x9", 16 / 9), ("phone", 19.5 / 9)),
          "portrait": (("3x4", 3 / 4), ("9x16", 9 / 16), ("phone", 9 / 19.5)),
          "any": (("4x3", 4 / 3), ("16x9", 16 / 9), ("phone", 9 / 19.5))}
# Rules that run again at each other data state and screen shape: what a longer text or another screen moves.
AGAIN = ("text", "overlap", "edge")

# Evaluated where the game runs, after the probe: the layout, its layers and every
# world instance on it, with what the checks need. A Sprite's frame is read twice,
# 0.3 s apart, so an animation that plays is told from one that stands still.
SNAPSHOT_JS = r"""(async () => {
  const runtime = c3probe.runtime, layout = runtime.layout;
  const shown = layer => [layer, ...layer.parentLayers()].every(l => l.isVisible && l.opacity > 0);
  const layers = {};
  for (const layer of layout.allLayers()) {
    const v = layer.getViewport(), a = layer.layerToCssPx(0, 0), b = layer.layerToCssPx(1000, 1000);
    layers[layer.name] = {parallax: [layer.parallaxX, layer.parallaxY], shown: shown(layer),
                          view: [v.left, v.top, v.right, v.bottom],
                          css: [a[0], a[1], (b[0] - a[0]) / 1000, (b[1] - a[1]) / 1000]};
  }
  // A Sprite whose animation is not set yet throws on animationName.
  const frameOf = i => { try { return typeof i.animationFrame === 'number' ? `${i.animationName}/${i.animationFrame}`
                                                                              : undefined; } catch (e) { return undefined; } };
  const seen = new Map(), frames = () => new Map([...seen.values()].map(i => [i.uid, frameOf(i)]));
  for (const name of Object.keys(runtime.objects))
    for (const i of runtime.objects[name].getAllInstances())
      try { if (typeof i.getBoundingBox === 'function' && i.layer && !seen.has(i.uid)) seen.set(i.uid, i); }
      catch (e) {}      // an instance between layouts, whose layer is gone
  const before = frames();
  await new Promise(r => setTimeout(r, 300));
  const after = frames(), instances = [];
  for (const i of seen.values()) try {
    const b = i.getBoundingBox();
    let root = i;
    while (root.getParent && root.getParent()) root = root.getParent();
    const r = {type: i.objectType.name, uid: i.uid, layer: i.layer.name, box: [b.left, b.top, b.right, b.bottom],
               shown: !!(i.isVisible && i.opacity > 0 && layers[i.layer.name]?.shown), angle: i.angle,
               root: root.uid};
    if (typeof i.textWidth === 'number') {
      r.text = String(i.text ?? '');
      r.textSize = [i.textWidth, i.textHeight];
      r.align = [i.horizontalAlign, i.verticalAlign];
      // A Text's size is in points; a Sprite Font's one line is its em
      r.em = typeof i.sizePt === 'number' ? i.sizePt * 4 / 3 : i.textHeight;
    }
    if (frameOf(i) !== undefined) {
      r.animation = i.animationName;
      r.frame = i.animationFrame;
      r.frames = i.animation ? i.animation.frameCount : 1;
      r.playing = before.get(i.uid) !== after.get(i.uid);
    }
    if (typeof i.pasteInstances === 'function') r.canvas = true;     // a Drawing Canvas
    if (i.instVars) r.instVars = Object.fromEntries(Object.keys(i.instVars).map(k => [k, i.instVars[k]]));
    instances.push(r);
  } catch (e) {}        // destroyed while it was read
  return {layout: layout.name, size: [layout.width, layout.height],
          viewport: [runtime.viewportWidth, runtime.viewportHeight], layers, instances};
})()"""

# The instances as a played frame shows them, read at once: what a moment shows may be gone after SNAPSHOT_JS's wait.
FRAME_JS = SNAPSHOT_JS.replace("  await new Promise(r => setTimeout(r, 300));\n", "")
# The findings that hold on any frame: the others read a settled layout or its measured ink.
PLAYED = ("text", "stacked", "overlap", "edge")


def area(box) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def sized(inst: dict) -> bool:
    """Whether an instance is shown at a size to judge: not a speck, nor one a
    tween is growing from nothing."""
    box = inst["box"]
    return inst["shown"] and box[2] - box[0] > TOLERANCE and box[3] - box[1] > TOLERANCE


def meet(a, b) -> list[float]:
    """The box two boxes share, empty when they do not touch."""
    return [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]


def inside(a, b, slack: float = 1) -> bool:
    """Whether box a lies within box b."""
    return a[0] >= b[0] - slack and a[1] >= b[1] - slack and a[2] <= b[2] + slack and a[3] <= b[3] + slack


def drawn(inst: dict) -> list[float]:
    """The part of an instance's box its picture covers: for a Text, where its text
    sits in the box by its alignment, never past the box."""
    box = inst["box"]
    if "textSize" not in inst:
        return box
    w, h = min(inst["textSize"][0], box[2] - box[0]), min(inst["textSize"][1], box[3] - box[1])
    h_align, v_align = inst.get("align") or ("left", "top")
    left = {"center": (box[0] + box[2] - w) / 2, "right": box[2] - w}.get(h_align, box[0])
    top = {"center": (box[1] + box[3] - h) / 2, "bottom": box[3] - h}.get(v_align, box[1])
    return [left, top, left + w, top + h]


def name(inst: dict) -> str:
    text = inst.get("text")
    words = f"{inst['type']} uid {inst['uid']}"
    if text and text.strip():
        one = " ".join(text.split())
        words += " " + json.dumps(one if len(one) <= 24 else one[:21] + "...", ensure_ascii=False)
    return words


def px(n: float) -> str:
    return str(round(n))


def text_findings(instances: list[dict]) -> list[dict]:
    found = []
    for i in instances:
        if not (sized(i) and "textSize" in i and (i.get("text") or "").strip() and not i.get("angle")):
            continue
        (tw, th), w, h = i["textSize"], i["box"][2] - i["box"][0], i["box"][3] - i["box"][1]
        if tw > w + TOLERANCE or th > h * WRAPPED:
            found.append({"rule": "text", "uids": [i["uid"]], "line":
                          f"{name(i)}: the text needs {px(tw)}x{px(th)} px and its box is {px(w)}x{px(h)}, so it "
                          f"is cut or wraps: make the box at least {px(max(tw, w))}x{px(max(th, h))} or the font "
                          f"smaller"})
    return found


def placeholder_findings(instances: list[dict]) -> list[dict]:
    """Shown texts that still read as the Text object's default, "Text", or as Lorem ipsum once the layout has run
    (text.placeholder): the layout files of the examples hold such texts, which their events replace."""
    return [{"rule": "placeholder", "uids": [i["uid"]], "line":
             f"{name(i)} still shows a placeholder after the layout has run: set its text in the layout or in an "
             f"On start of layout event"}
            for i in instances if "textSize" in i and i["shown"] and PLACEHOLDER.search(i.get("text") or "")]


def stacked_findings(instances: list[dict]) -> list[dict]:
    """Instances of one type on one box that show the same frame: two that show different
    frames or animations, a fill under its rim, are layered on purpose, and so are Drawing
    Canvases, each drawing its own picture at runtime."""
    groups: dict[tuple, list[dict]] = {}
    for i in instances:
        if sized(i) and not i.get("canvas"):
            box = tuple(round(v) for v in i["box"])
            groups.setdefault((i["type"], i["layer"], box, i.get("animation"), i.get("frame")), []).append(i)
    found = []
    for (kind, _, (left, top, right, bottom), *_), same in groups.items():
        if len(same) < 2:
            continue
        uids = [i["uid"] for i in same]
        texts = sorted({" ".join(i["text"].split()) for i in same if (i.get("text") or "").strip()})
        said = f", texts {', '.join(json.dumps(t[:20], ensure_ascii=False) for t in texts[:4])}" if len(texts) > 1 else ""
        found.append({"rule": "stacked", "uids": uids, "line":
                      f"{kind}: {len(same)} instances on one box at ({left}, {top}) {right - left}x{bottom - top}, "
                      f"uids {', '.join(map(str, uids[:6]))}{' ...' if len(uids) > 6 else ''}{said}: they were "
                      f"created and never moved apart; set each one's position from the instance it belongs to"})
    return found


def overlap_findings(instances: list[dict], layers: dict) -> list[dict]:
    def hud(i: dict) -> bool:
        return tuple(layers.get(i["layer"], {}).get("parallax", (1, 1))) == (0, 0)
    seen = [i for i in instances if sized(i) and not i.get("angle")
            and (hud(i) or (i.get("text") or "").strip())]
    found = []
    for n, a in enumerate(seen):
        for b in seen[n + 1:]:
            if a["layer"] != b["layer"] or a["root"] == b["root"] or not hud(a) and "textSize" not in b:
                continue
            if a["type"] == b["type"] and [round(v) for v in a["box"]] == [round(v) for v in b["box"]]:
                continue        # stacked, reported as such
            if "textSize" in a and "textSize" in b and (a["text"] == b["text"] or all(
                    abs(u - v) <= 2 * TOLERANCE for u, v in zip(a["box"], b["box"]))):
                continue        # a text and its shadow or outline
            da, db = drawn(a), drawn(b)
            screen = area(layers[a["layer"]]["view"])
            if area(da) > OVERLAY * screen or area(db) > OVERLAY * screen:
                continue        # a message or a backdrop over the whole screen
            if inside(da, b["box"]) and "textSize" not in b or inside(db, a["box"]) and "textSize" not in a:
                continue        # a label on its button, an icon on its panel
            shared = meet(da, db)
            w, h = shared[2] - shared[0], shared[3] - shared[1]
            if w <= TOLERANCE or h <= TOLERANCE or w * h < OVERLAP_SHARE * min(area(da), area(db)):
                continue
            found.append({"rule": "overlap", "uids": [a["uid"], b["uid"]], "line":
                          f"{name(a)} and {name(b)} overlap by {px(w)}x{px(h)} px on "
                          f"{'HUD ' if hud(a) else ''}layer {a['layer']!r}: "
                          f"move one of them clear of the other, or make the smaller a child of the one it "
                          f"belongs to"})
    return found


def edge_findings(instances: list[dict], layers: dict) -> list[dict]:
    """HUD instances the screen's edge cuts. One wholly off screen waits there to
    move in, and art on a world layer may run off the edge on purpose."""
    found = []
    for i in instances:
        layer = layers.get(i["layer"])
        if not (sized(i) and layer and tuple(layer["parallax"]) == (0, 0)):
            continue
        b, view = drawn(i), layer["view"]
        shared = meet(b, view)
        if shared[2] - shared[0] <= TOLERANCE or shared[3] - shared[1] <= TOLERANCE:
            continue            # off screen, or a sliver of it
        wide, tall = b[2] - b[0] >= view[2] - view[0], b[3] - b[1] >= view[3] - view[1]
        cut = [side for side, over, spans in (("left", view[0] - b[0], wide), ("top", view[1] - b[1], tall),
                                              ("right", b[2] - view[2], wide), ("bottom", b[3] - view[3], tall))
               if over > TOLERANCE and not spans]
        if cut:
            found.append({"rule": "edge", "uids": [i["uid"]], "line":
                          f"{name(i)}: the {' and '.join(cut)} edge of the screen cuts it, its box ({px(b[0])}, "
                          f"{px(b[1])}) to ({px(b[2])}, {px(b[3])}) and the screen ({px(view[0])}, {px(view[1])}) to "
                          f"({px(view[2])}, {px(view[3])}) on HUD layer {i['layer']!r}: move it inside the screen"})
    return found


def frame_findings(instances: list[dict]) -> list[dict]:
    kinds: dict[str, list[dict]] = {}
    for i in instances:
        if i["shown"] and "frame" in i:
            kinds.setdefault(i["type"], []).append(i)
    texts = [drawn(i) for i in instances if i["shown"] and (i.get("text") or "").strip()]
    found = []
    for kind, same in kinds.items():
        if len(same) < 2 or any(i["playing"] or i["frames"] < 2 for i in same):
            continue
        if all(any(inside(t, i["box"]) for t in texts) for i in same):
            continue        # each one carries a text that tells it apart
        if len({(i["animation"], i["frame"]) for i in same}) > 1:
            continue
        differ = {}
        for var in same[0].get("instVars") or {}:
            values = [i.get("instVars", {}).get(var) for i in same]
            distinct = {json.dumps(v) for v in values}
            if 1 < len(distinct) and all(isinstance(v, str) for v in values):
                differ[var] = sorted(distinct)
        if not differ:
            continue
        var, values = next(iter(differ.items()))
        shown_values = ", ".join(values[:4]) + (" ..." if len(values) > 4 else "")
        found.append({"rule": "frame", "uids": [i["uid"] for i in same], "line":
                      f"{kind}: all {len(same)} instances show animation {same[0]['animation']!r} frame "
                      f"{same[0]['frame']} of {same[0]['frames']}, though their {var} differs ({shown_values}): set "
                      f"each one's frame or animation from {var} where it is created"})
    return found


# One step of a measured shot, with the time scale at 0 so that nothing moves between them.
# `step` sets the texts of {uid: text} and hides the uids of `hide`; null restores the texts, the
# visibility and the time scale. The layout's events still run at time scale 0 and can destroy an
# instance between two steps.
STEP_JS = """(async () => {{ const runtime = c3probe.runtime, step = {step};
  const kept = globalThis.c3held ??= {{shown: new Map(), texts: new Map(), timeScale: runtime.timeScale}};
  runtime.timeScale = 0;
  if (step === null) {{
    for (const [uid, text] of kept.texts) {{ const i = runtime.getInstanceByUid(uid); if (i) i.text = text; }}
    for (const [uid, shown] of [...kept.shown].reverse()) {{
      const i = runtime.getInstanceByUid(uid); if (i) i.isVisible = shown; }}
    runtime.timeScale = kept.timeScale;
    delete globalThis.c3held;
  }} else {{
    for (const [uid, text] of Object.entries(step.texts ?? {{}})) {{
      const i = runtime.getInstanceByUid(Number(uid));
      if (i) {{ if (!kept.texts.has(i.uid)) kept.texts.set(i.uid, i.text); i.text = text; }} }}
    for (const uid of step.hide ?? []) {{
      const i = runtime.getInstanceByUid(uid);
      if (i && !kept.shown.has(uid)) {{ kept.shown.set(uid, i.isVisible); i.isVisible = false; }} }}
  }}
  await new Promise(r => setTimeout(r, 200));
  return true; }})()"""


def luminance(rgb) -> float:
    """WCAG 2.2's relative luminance of an sRGB colour of 0-255 channels."""
    lin = [c / 255 / 12.92 if c / 255 <= 0.04045 else ((c / 255 + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a, b) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# Least change of a colour channel, of 255, that counts as ink.
INK_LEAST = 16
# Share of the largest change in a clip from which a pixel is the core of a glyph's stroke, whose colour is the
# text's own and not mixed with what is behind it by antialiasing.
INK_CORE = 0.85


def ink_colours(before: list, after: list) -> tuple[tuple, tuple] | None:
    """(the text's colour, the colour behind it) over the core pixels of what differs between a clip with its
    text and without: each the mean over those pixels. None when nothing differs."""
    change = [max(abs(p - q) for p, q in zip(u[:3], v[:3])) for u, v in zip(before, after)]
    top = max(change, default=0)
    if top < INK_LEAST:
        return None
    core = [n for n, d in enumerate(change) if d >= INK_CORE * top]
    return (tuple(sum(before[n][c] for n in core) / len(core) for c in range(3)),
            tuple(sum(after[n][c] for n in core) / len(core) for c in range(3)))


def legible_texts(instances: list[dict], layers: dict) -> list[dict]:
    """The texts whose contrast faint_findings() measures: shown, sized, unturned, holding a word or a number."""
    return [i for i in instances if sized(i) and not i.get("angle") and (i.get("text") or "").strip()
            and i["layer"] in layers]


def contrasts(win: oe.DevTools, session: str | None, texts: list[dict], layers: dict) -> dict[int, tuple]:
    """{uid: (text colour, colour behind it)} of each text, measured in a clip of its drawn box as it is and
    with every text hidden, so a text on a picture, a gradient or a panel is measured on what it lies on."""
    clips = []
    for t in texts:
        ax, ay, sx, sy = layers[t["layer"]]["css"]
        b = drawn(t)
        x0, y0 = max(0.0, ax + sx * b[0]), max(0.0, ay + sy * b[1])
        clips.append({"x": x0, "y": y0, "width": max(1.0, ax + sx * b[2] - x0),
                      "height": max(1.0, ay + sy * b[3] - y0), "scale": 1})

    def shoot(step) -> list:
        win.evaluate(STEP_JS.format(step=json.dumps(step)), wait=10, session=session)
        return [c3.png_rgba(base64.b64decode(win.call("Page.captureScreenshot", format="png", clip=c)["data"]))
                for c in clips] if step is not None else []
    try:
        shown, bare = shoot({}), shoot({"hide": [t["uid"] for t in texts]})
    finally:
        shoot(None)
    out = {}
    for t, (_, _, a), (_, _, b) in zip(texts, shown, bare):
        found = ink_colours(a, b)
        if found:
            out[t["uid"]] = found
    return out


# Contrast a text needs, small and from LARGE_PX css px of em up, WCAG's 18 pt;
# and the share of it a measure may fall short by, for the antialiasing that mixes the core of a thin stroke
CONTRAST = (4.5, 3)
LARGE_PX = 24
CONTRAST_SLACK = 0.9


def faint_findings(texts: list[dict], measured: dict[int, tuple], layers: dict) -> list[dict]:
    """A finding for each text whose colour, measured on what lies behind it, reads under CONTRAST."""
    found = []
    for t in texts:
        if t["uid"] not in measured:
            continue
        ink_rgb, behind = measured[t["uid"]]
        em = (t.get("em") or 0) * layers[t["layer"]]["css"][3]
        need = CONTRAST[1] if em >= LARGE_PX else CONTRAST[0]
        got = ratio(ink_rgb, behind)
        if got < CONTRAST_SLACK * need:
            found.append({"rule": "faint", "uids": [t["uid"]], "line":
                          f"{name(t)}: its letters, {'#%02x%02x%02x' % tuple(round(c) for c in ink_rgb)}, read "
                          f"{got:.1f}:1 on {'#%02x%02x%02x' % tuple(round(c) for c in behind)} behind them, under "
                          f"the {need:g}:1 a {'large ' if em >= LARGE_PX else ''}text needs: give it a colour of "
                          f"PALETTE that reads on what lies behind it, or put a panel under it"})
    return found


def set_by_events(project: Path) -> set[str]:
    """The object types whose text an event sheet's action sets."""
    found: set[str] = set()

    def walk(node) -> None:
        if isinstance(node, dict):
            if node.get("id") in SETS_TEXT and isinstance(node.get("objectClass"), str):
                found.add(node["objectClass"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    for sheet in sorted((project / "eventSheets").rglob("*.json")):
        try:
            walk(c3.load(sheet))
        except ValueError:
            continue
    return found


def declared(project: Path) -> dict[str, str]:
    """The longest text of each Text type, from tools/texts.json; {} without one."""
    try:
        data = json.loads((project / DECLARED).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in (data.get("longest") or {}).items() if isinstance(v, str)}


def wide(text: str) -> bool:
    return any(unicodedata.east_asian_width(c) in ("W", "F") for c in text)


def state_text(text: str, state: str, longest: str | None) -> str:
    """What a Text that events set shows at a data state: worst, its declared longest, else its first count at
    WORST_NUMBER and the rest at all nines, or a long name; empty, nothing; one, every count at 1."""
    if state == "empty":
        return ""
    if state == "one":
        return re.sub(COUNT, "1", text)
    if longest:
        return longest
    if re.search(r"\d", text):
        first = iter([True])

        def nines(m: re.Match) -> str:
            gap = m[1] or ""      # a tag may space each letter with a narrow space
            digits = WORST_NUMBER if next(first, False) else "9" * len(m[0].replace(gap, "") if gap else m[0])
            return gap.join(digits) if gap else digits
        return re.sub(COUNT, nines, text)
    if wide(text):
        return WORST_WIDE
    return f"{text} {text}" if len(text.split()) > 1 else WORST_NAME


def state_texts(instances: list[dict], setters: set[str], longest: dict[str, str], state: str) -> dict[int, str]:
    """{uid: text} for each shown Text whose type events set, at the data state."""
    return {i["uid"]: state_text(i["text"], state, longest.get(i["type"])) for i in instances
            if "textSize" in i and i["shown"] and i["type"] in setters and (i.get("text") or "").strip()}


def unlimited_findings(instances: list[dict], setters: set[str], longest: dict[str, str]) -> list[dict]:
    """One finding for the Text types shown that events set and nothing declares the longest text of."""
    seen: dict[str, dict] = {}
    for i in instances:
        if "textSize" in i and i["shown"] and i["type"] in setters and i["type"] not in longest:
            seen.setdefault(i["type"], i)
    if not seen:
        return []
    return [{"rule": "unlimited", "uids": [i["uid"] for i in seen.values()], "line":
             f"events set the text of {', '.join(seen)}, and nothing says how long it gets, so each box fits only "
             f"the text it starts with and its worst text is a guess. Give each one's helper longest=, the widest "
             f"text it shows, or declare it in {DECLARED.as_posix()}", "warn": True}]


def findings(snap: dict, only: tuple[str, ...] | None = None) -> list[dict]:
    """Every finding on a layout read by SNAPSHOT_JS, each {rule, uids, line}; with `only`, those of these rules."""
    instances, layers = snap["instances"], snap["layers"]
    run = {"text": lambda: text_findings(instances), "stacked": lambda: stacked_findings(instances),
           "overlap": lambda: overlap_findings(instances, layers), "edge": lambda: edge_findings(instances, layers),
           "frame": lambda: frame_findings(instances), "placeholder": lambda: placeholder_findings(instances)}
    return [f for rule, find in run.items() if only is None or rule in only for f in find()]


def played_lines(win, session: str | None) -> list[str]:
    """The finding lines of the frame a plan's shot step is on."""
    return [finding_line(f) for f in findings(win.evaluate(FRAME_JS, wait=20, session=session), PLAYED)]


def placed(found: list[dict], at: str | None) -> list[dict]:
    """The findings with where they arose when not on the shot as it is."""
    return [{**f, "at": at} for f in found] if at else found


def guessed(found: list[dict], instances: list[dict], setters: set[str], longest: dict[str, str],
            state: str) -> list[dict]:
    """The findings of a data state, each that a worst text guessed for an undeclared type caused only warning:
    the guess may be longer than anything the game shows."""
    if state != "worst":
        return found
    types = {i["uid"]: i["type"] for i in instances}
    return [{**f, "warn": True, "line": f"{f['line']}; the worst text was guessed, as no longest is declared"}
            if any(types.get(u) in setters - set(longest) for u in f["uids"]) else f for f in found]


def ranked(found: list[dict]) -> list[dict]:
    """The findings before the warnings, in their order, one of each rule and uids: the first that arose, on the
    shot as it is before another data state or screen shape."""
    seen, out = set(), []
    for f in sorted(found, key=lambda f: bool(f.get("warn"))):
        key = (f["rule"], tuple(f["uids"]))
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def blocking(found: list[dict]) -> list[dict]:
    return [f for f in found if not f.get("warn")]


def file_name(layout: str) -> str:
    """A layout's name as a file name: letters and digits of any script, the rest as -."""
    return re.sub(r"[^\w-]+", "-", layout, flags=re.UNICODE).strip("-") or "layout"


# Goes to a layout, lets it run SETTLE seconds, and says which layouts started on
# the way and which one runs at the end: a layout whose start events go on to
# another shows as started and left.
GO_JS = """(async () => {{ const runtime = c3probe.runtime, want = {name}, entered = [];
  const on = () => entered.push(runtime.layout.name);
  runtime.addEventListener('afteranylayoutstart', on);
  try {{
    if (runtime.layout.name === want) entered.push(want); else runtime.goToLayout(want);
    const t0 = performance.now();
    while (!entered.includes(want)) {{ if (performance.now() - t0 > 10000) break;
      await new Promise(r => setTimeout(r, 20)); }}
    if (entered.includes(want)) await new Promise(r => setTimeout(r, {settle} * 1000));
  }} finally {{ runtime.removeEventListener('afteranylayoutstart', on); }}
  return {{entered, now: runtime.layout.name}}; }})()"""


def screen_shapes(view: list[int], orientation: str) -> list[tuple[str, list[int]]]:
    """(name, [w, h]) of each screen a layout is shown on: the project's own viewport, named "", then the
    first two SHAPES of its orientations whose ratio is not the viewport's, at the viewport's shorter side."""
    w, h = view
    short, out = min(w, h), [("", list(view))]
    for name, r in SHAPES.get(orientation, SHAPES["any"]):
        if abs(r - w / h) > 0.03 * w / h and len(out) < 3:
            out.append((name, [round(short * r), short] if r >= 1 else [short, round(short / r)]))
    return out


def shot_name(layout: str, shape: str, state: str) -> str:
    """The file name of a layout's screenshot: Map.png, and Map@phone-worst.png at another shape or data state."""
    at = "-".join(part for part in (shape, "" if state == "demo" else state) if part)
    return f"{file_name(layout)}{'@' + at if at else ''}.png"


def visits(only: list[str] | None, settle: float, shapes: list[tuple[str, list[int]]], shots: Path,
           states: tuple[str, ...], setters: set[str], longest: dict[str, str]):
    """The `then` of open_in_editor.open_one: preview the project and visit its layouts on each screen shape, the
    first being the project's own, at each data state."""
    def visit(win: oe.DevTools, session: str | None, layout: str, shape: str, errors: list[str]) -> dict:
        """One layout on the screen shape as it is: its screenshot, what SNAPSHOT_JS reads and the findings, then each
        other data state's. The text contrast is measured on the project's own shape."""
        done: dict = {"layout": layout, "errors": list(errors)}
        went = win.evaluate(GO_JS.format(name=json.dumps(layout), settle=settle), wait=settle + 20, session=session)
        if went["now"] != layout:
            done["left"] = went["now"] if layout in went["entered"] else None
            win.evaluate("0", session=session)
            done["errors"] += oe.runtime_errors(win)
            return done
        shot = shots / shot_name(layout, shape, "demo")
        for tries in range(1, BLANK_TRIES + 1):
            share = oe.blank(win)
            if share is None or tries == BLANK_TRIES:
                break
            time.sleep(BLANK_WAIT)
        shot.write_bytes(base64.b64decode(win.call("Page.captureScreenshot")["data"]))
        if tries > 1:
            done["blank"] = {"tries": tries, "share": share}
        try:
            snap = win.evaluate(SNAPSHOT_JS, wait=20, session=session)
            found = placed(findings(snap, AGAIN if shape else None), shape or None)
            if not shape:
                done["snapshot"] = snap
                found += unlimited_findings(snap["instances"], setters, longest)
                texts = legible_texts(snap["instances"], snap["layers"])
                if texts:
                    colours = contrasts(win, session, texts, snap["layers"])
                    done["contrast"] = {str(u): [list(a), list(b)] for u, (a, b) in colours.items()}
                    found += faint_findings(texts, colours, snap["layers"])
            done["states"] = {}
            for state in [s for s in states if s != "demo"]:
                set_to = state_texts(snap["instances"], setters, longest, state)
                if not set_to:
                    continue
                path = shots / shot_name(layout, shape, state)
                try:
                    win.evaluate(STEP_JS.format(step=json.dumps({"texts": set_to})), wait=10, session=session)
                    path.write_bytes(base64.b64decode(win.call("Page.captureScreenshot")["data"]))
                    again = win.evaluate(SNAPSHOT_JS, wait=20, session=session)
                finally:
                    win.evaluate(STEP_JS.format(step="null"), wait=10, session=session)
                done["states"][state] = {"shot": str(path), "texts": {str(u): t for u, t in set_to.items()}}
                found += guessed(placed(findings(again, AGAIN), " ".join(p for p in (shape, state) if p)),
                                 snap["instances"], setters, longest, state)
            done.update(shot=str(shot), findings=ranked(found))
        except oe.DevToolsError as e:     # the layout's instances could not be read
            done.update(shot=str(shot), findings=[])
            done["errors"].append(f"its instances were not read: {str(e).splitlines()[0]}")
        win.evaluate("0", session=session)
        done["errors"] += oe.runtime_errors(win)
        return done

    def run(browser: oe.Browser, target: str, page: oe.DevTools) -> dict:
        page.call("Storage.clearDataForOrigin", origin=play.PREVIEW, storageTypes="local_storage,indexeddb")
        started = oe.start_preview(browser, target, page)
        if isinstance(started, list):
            return {"started": False, "errors": started, "layouts": []}
        window, win = started
        visited: list[dict] = []
        try:
            own = shapes[0][1]
            if play.emulate(win, own) != tuple(own):
                return {"started": False, "layouts": [], "errors": [
                    f"the preview window did not take the viewport {own[0]}x{own[1]} in {play.RESIZE} s"]}
            sessions, live, stalled = oe.attach(win, patience=30)
            if not live:
                return {"started": False, "layouts": [], "errors": [
                    "the runtime loaded but did not tick for 3 seconds" if stalled
                    else "the preview window opened but no runtime was found in it in 30 seconds"]}
            session = live[0]
            play.enable(win, sessions)
            win.evaluate("0")
            first_errors = oe.runtime_errors(win)
            names = win.evaluate("c3probe.runtime.getAllLayouts().map(l => l.name)", session=session)
            first = win.evaluate("c3probe.runtime.layout.name", session=session)
            order = [first] + [n for n in names if n != first]
            missing = [n for n in only or [] if n not in names]
            if missing:
                return {"started": False, "layouts": [], "errors": [
                    f"no layout {m!r}{c3.closest(m, names)}" for m in missing]}
            for shape, size in shapes:
                if shape and play.emulate(win, size) != tuple(size):
                    for done in visited:
                        done.setdefault("unseen", []).append(f"{shape} {size[0]}x{size[1]}")
                    continue
                for layout in [n for n in order if not only or n in only]:
                    done = visit(win, session, layout, shape, first_errors if layout == first and not shape else [])
                    if not shape:
                        visited.append(done)
                        continue
                    kept = next(d for d in visited if d["layout"] == layout)
                    kept.setdefault("shapes", {})[shape] = {k: done[k] for k in ("shot", "states", "left")
                                                            if k in done}
                    kept["findings"] = ranked(kept.get("findings", []) + done.get("findings", []))
                    kept["errors"] += [e for e in done["errors"] if e not in kept["errors"]]
        finally:
            win.ws.close()
            browser.devtools.call("Target.closeTarget", targetId=window["targetId"])
        return {"started": True, "runtime": "worker" if session else "page", "layouts": visited, "errors": [],
                "shapes": [{"name": n or "project", "size": s} for n, s in shapes], "states": list(states)}
    return run


def report(result: dict) -> list[str]:
    if result["status"] != "opened":
        return oe.report(result)
    lines = oe.opened_lines(result)
    ran = result.get("preview") or {"started": False, "errors": ["no preview"]}
    if not ran["started"]:
        return lines + [f"  preview did not run: {e}" for e in ran["errors"]]
    total = len(ran["layouts"])
    for n, done in enumerate(ran["layouts"], 1):
        shot, blank = done.get("shot"), done.get("blank") or {}
        if shot and blank.get("share"):
            lines.append(f"layout {done['layout']!r} ({n} of {total}): screenshot {shot}: {c3.BLANK:.1%} or more "
                         f"of it is one colour after {blank['tries']} shots {BLANK_WAIT:g} s apart, so the layout "
                         f"draws nothing in view at its start, or the preview did not draw it. "
                         f"If it should show something, raise --settle, or reach it in play with a shot "
                         f"step of a preview_project.py plan")
        elif shot:
            before = "the shot" if blank.get("tries") == 2 else f"the {blank.get('tries', 1) - 1} shots"
            again = f", taken when the layout was drawn; {before} before showed one colour, not drawn yet" if blank \
                else ""
            lines.append(f"layout {done['layout']!r} ({n} of {total}): screenshot {shot}{again}")
        elif done.get("left"):
            lines.append(f"layout {done['layout']!r} ({n} of {total}): started, and its events went on to "
                         f"{done['left']!r} before the screenshot; it needs what the game sets up before it: play to "
                         f"it with preview_project.py and a shot step")
        else:
            lines.append(f"layout {done['layout']!r} ({n} of {total}): not reached in 10 seconds")
        lines += [finding_line(f) for f in done.get("findings", [])]
        lines += [f"  unseen: the preview window did not take the screen {s}, so the layouts were not visited on it"
                  for s in done.get("unseen", [])]
        lines += oe.runtime_lines(done["errors"])
    return lines


def finding_line(f: dict) -> str:
    """A finding as the run prints it: warning when it warns, its rule, where it arose when not on the shot as it
    is, and what to change."""
    return f"  {'warning ' if f.get('warn') else ''}{f['rule']}{' @' + f['at'] if f.get('at') else ''}: {f['line']}"


def counts(result: dict) -> tuple[int, int, int, int]:
    """Findings that fail the review, findings that warn, runtime errors and layouts visited."""
    layouts = (result.get("preview") or {}).get("layouts", [])
    found = [f for d in layouts for f in d.get("findings", [])]
    return (len(blocking(found)), len(found) - len(blocking(found)), sum(len(d["errors"]) for d in layouts),
            len(layouts))


def unpreviewed(results: list[dict]) -> list[str]:
    """The projects that opened but whose preview did not start, so that none of their layouts was visited."""
    return [r["project"] for r in results if r["status"] == "opened" and not (r.get("preview") or {}).get("started")]


def summary_line(results: list[dict], settle: float, out: Path, base: Path) -> str:
    """The count of findings, and when there is none, what the run did not see."""
    if unpreviewed(results):
        return f"screens: no layout was visited, as the preview of {', '.join(unpreviewed(results))} did not run; " \
               f"full result in {out}"
    found, warned, errors, layouts = map(sum, zip(*(counts(r) for r in results)))
    unseen = "" if found or errors else (f"; each layout ran {settle:g} s after a jump to it, without play, so a "
                                         f"scene the game reaches only in play is unseen")
    warns = f" and {warned} that warn{'s' if warned == 1 else ''}" if warned else ""
    return (f"screens: {found} finding{'' if found == 1 else 's'} to fix{warns} on {layouts} "
            f"layout{'' if layouts == 1 else 's'}, {errors} runtime error{'' if errors == 1 else 's'}{unseen}; full "
            f"result in {out}, screenshots in {base}")


def main() -> int:
    c3.utf8_output()
    ap = argparse.ArgumentParser(description=__doc__, epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", type=Path, metavar="PATH",
                    help="a folder project, or a folder above several (default: the project of --project, else "
                         "the one the current directory is in)")
    ap.add_argument("--project", metavar="FOLDER",
                    help="the folder that holds project.c3proj (default: found from the current directory upward)")
    ap.add_argument("--layouts", nargs="+", metavar="NAME", help="visit only these layouts (default: every layout, "
                                                                "the one the editor opens on first)")
    ap.add_argument("--settle", type=float, default=1.0, metavar="SECONDS",
                    help="how long each layout runs before its screenshot, for its start events and tweens "
                         "(default 1)")
    ap.add_argument("--viewport", type=int, nargs=2, metavar=("W", "H"),
                    help="CSS pixels of the preview window, the one screen shown (default: the project's "
                         "viewport size, then two other shapes of screen its orientations allow)")
    ap.add_argument("--data", nargs="+", choices=DATA_STATES, default=list(DATA_STATES), metavar="STATE",
                    help="the data states to show each layout in: demo as it starts, worst, empty, one "
                         "(default: all four)")
    ap.add_argument("--release", metavar="rNNN", help="open in this release of the editor, as open_in_editor.py does")
    ap.add_argument("--browser", metavar="EXE",
                    help="the Chromium-based browser to start (default: Edge, Chrome or Chromium where installed)")
    ap.add_argument("--shots", type=Path, help="the folder for the screenshots (default: shots/ beside the result)")
    ap.add_argument("--out", type=Path, help="write the result, every instance read included, as JSON "
                                             "(default: result.json in .tmp/scripts/check-screens/)")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    ap.add_argument("--profile", type=Path, metavar="FOLDER",
                    help="keep the browser profile in FOLDER/editor-<browser> instead of .tmp/browsers/")
    ap.add_argument("--limit", type=int, default=c3.LIMIT, metavar="CHARS",
                    help=f"stop printing after about this many characters; --out keeps everything, 0 prints "
                         f"everything (default: {c3.LIMIT})")
    args = ap.parse_args()

    if args.paths:
        projects = [p for p in oe.find_projects(args.paths) if p.is_dir()]
    else:
        project = c3.find_project(args.project)
        projects = [project] if project and (project / "project.c3proj").is_file() else []
    if not projects:
        print(f"no project.c3proj found under {', '.join(map(str, args.paths)) or args.project or Path.cwd()}; run "
              f"this in the project folder or pass --project <folder>", file=sys.stderr)
        return 2
    exe = args.browser or oe.browser_path()
    if not exe:
        print("no Edge, Chrome or Chromium found here, and this script needs one it can drive: install one, or open "
              "the project with open_in_editor.py --steps and take a screenshot of each layout with a browser tool "
              "of this session.")
        return 3
    editor = oe.release_url(args.release)
    out, base = oe.kept(args.out, args.shots, projects[0], "check-screens")

    def visit(browser: oe.Browser) -> list[dict]:
        """Check each project in turn. Its result is written and printed as it ends, so the results stay
        when a later project stops the run."""
        results, printed = [], 0
        for project in projects:
            shots = base if len(projects) == 1 else base / project.name
            shots.mkdir(parents=True, exist_ok=True)
            data = c3.load(project / "project.c3proj")
            own = [data.get("viewportWidth"), data.get("viewportHeight")]
            own = own if all(isinstance(n, int) and n > 0 for n in own) else [1280, 720]
            shapes = [("", args.viewport)] if args.viewport else screen_shapes(
                own, (data.get("properties") or {}).get("orientations", "any"))
            result = oe.open_one(browser, editor, project, oe.staged(project, "check-screens"), None,
                                 bool(args.release), visits(args.layouts, args.settle, shapes, shots,
                                                            tuple(args.data), set_by_events(project),
                                                            declared(project)))
            results.append(result)
            out.write_text(json.dumps(results if len(projects) > 1 else result, ensure_ascii=False, indent=1),
                           encoding="utf-8")
            lines = report(result)
            shown, printed = oe.print_part(lines, args.limit, printed)
            if shown < len(lines):
                print(f"{len(lines) - shown} lines not printed: {out} keeps everything, --limit 0 prints it")
        return results

    try:
        results = oe.drive(exe, oe.profile_folder(args.profile, projects[0], exe), args.headed, visit)
    except oe.ProfileBusy as e:
        print(e, file=sys.stderr)
        return oe.BUSY
    if results is None:
        return 2
    found, _, errors, _ = map(sum, zip(*(counts(r) for r in results)))
    print(summary_line(results, args.settle, out, base))
    if any(r["status"] != "opened" for r in results):
        print(oe.NEXT)
        return 1
    if unpreviewed(results):
        print("next: the preview did not run, so no layout was visited and nothing passed; run this again, and if "
              "the preview stops again, run open_in_editor.py --preview, whose lines say why")
        return 3
    print("next: fix every finding; name each warning in the hand-over or fix it. A runtime error on a layout reached "
          "straight away may need the run that leads there, so play to it with preview_project.py before blaming the "
          "events. Run this again until it prints no finding to fix.")
    return 1 if found or errors else 0


if __name__ == "__main__":
    sys.exit(main())
