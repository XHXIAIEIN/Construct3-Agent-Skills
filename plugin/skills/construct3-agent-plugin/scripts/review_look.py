"""Preview a project, visit every layout, and print for each a screenshot to read,
what the runtime shows wrong on it, and the questions to answer about the picture.

    python scripts/review_look.py [PATH ...] [--project FOLDER] [--layouts NAME ...] [--settle SECONDS]
                                  [--viewport W H] [--release rNNN] [--browser EXE] [--shots DIR]
                                  [--out RESULT.json] [--headed] [--profile FOLDER]
    python scripts/review_look.py --reply REPLY [--project FOLDER] [--out RESULT.json]

Run it after open_in_editor.py --preview passes. It previews the project as F5
does, then goes to each layout in turn with the runtime's goToLayout, lets it run
SETTLE seconds, takes a screenshot, and reads every instance of the layout from
the runtime. It prints one line per mechanical finding, each naming the layout,
the object type, the instance's UID and what to change:

  text      a visible Text whose text needs more room than its box: it is cut
            or wraps beyond the box
  stacked   two or more visible instances of one object type on the same box,
            showing the same frame: instances created at runtime and never
            moved apart. Instances that show different frames or animations
            there, a fill under its rim, are layered on purpose and left out
  overlap   two visible instances on a layer of parallax 0 (the HUD), or two
            texts on any layer, one covering half of the other. A Text counts
            by the part its text covers. Left out: an instance inside a larger
            non-Text one (a label on its button, an icon on a panel), instances
            of one hierarchy, a text and its shadow, an overlay over half the
            screen
  edge      a visible HUD instance that the edge of the screen cuts; one wholly
            off screen waits there to move in and is left out
  frame     every visible instance of a Sprite type shows the same frame of an
            animation that has more, though a text instance variable differs
            between them and no text on each tells them apart
  crowd     a ninth of the screen off its middle whose texts tell 3 items or more
            while two corners hold no text: texts a group's gap apart are one
            item, and each further part a text joins with " · " or " | " that
            holds a word is one more. Left out: a count with no word, the one
            text on an object (its label), a bar across two thirds of the
            screen, a message over half of it, and the texts of a scrolling
            layer of a layout larger than the screen

A screenshot is not drawn yet when 99.9% or more of it is one colour, black
or clear. It is taken again 1 s later, twice at most. A layout still of one
colour is named as drawing nothing in view, and no question is asked about it.

Then it prints the questions to answer from the screenshots, which the script
cannot judge: each is answered yes or no, and each yes names the object to
change. When the project has a design (--design, by default tools/design.json),
one question lists the design's screen entries that play_design.py cannot
measure: entries with other words before the first comma, and entries whose
key names no object of the project.

A layout reached by goToLayout starts without what the game's flow sets up
before it, so a layout that needs a run in progress may show less than in
play, or log errors that play does not: those are printed as `runtime:`
lines. Check such a scene by playing to it with preview_project.py and a
shot step.

Screenshots go to --shots, by default .tmp/look/ in the project, as
<layout>.png; the whole result to --out, by default .tmp/review-look.json.
Beside the screenshots it writes brief.md: the screenshots, the questions and
the form of the answer, for a reviewer that has not seen the project. The
agent that built the game reads its own pictures by what it meant to build.
So an agent that can start a sub-agent gives it the brief and takes the
answers from its reply, and one that cannot answers from the screenshots
itself. The last three lines are look:, with the result and the screenshots,
next:, and brief:, which says who answers the questions.

--reply checks a reviewer's reply, saved to a file, against the brief of the
last run, read from --out: it opens no browser. It names every answer the
reply lacks, each yes that does not say where it is, and each answer line
that names no screenshot of the brief, then prints every yes to fix.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
import uuid
from pathlib import Path

import c3project as c3
import game_model as gm
import open_in_editor as oe
import preview_project as play

EPILOG = """examples:
  python scripts/review_look.py
  python scripts/review_look.py --layouts Menu Map --settle 2
  python scripts/review_look.py --viewport 430 932
  python scripts/review_look.py --reply .tmp/look/reply.md

output:
  opened   <project>  (<window title>, <the editor it opened in>)
  layout 'Map' (2 of 3): screenshot .tmp/look/Map.png
    text: Text Title uid 12 "Choose your path": the text needs 212x40 px and its box is 160x40 ...
    stacked: Text CardName: 5 instances on one box at (300, 420) 120x30, uids 41, 42, 43 ...
    runtime: <an error the layout logged, with its event, and (N times) when it came more than once>
  layout 'Combat' (3 of 3): started, and its events went on to 'Map' before the screenshot; ...
  questions: answer every question yes or no for each screenshot above, through the brief as the last line ...
    1. Is any text cut off, broken onto a line of its own, too small or too faint to read, or partly hidden ...
    ...
    7. Does the same decoration, not the HUD, appear on every screenshot?
  look: 2 findings on 3 layouts, 0 runtime errors; full result in .tmp/review-look.json, screenshots in .tmp/look
  next: <what to do>
  brief: if you can start a sub-agent, give it .tmp/look/brief.md as its whole task ...

output of --reply:
  reply: .tmp/look/reply.md, against the brief of 2 screenshots and 8 questions: 16 answers asked
    missing: Map 3, 4; Combat 1-8
    yes without where: Map 5
    not in the brief: Shop 1: no
    yes: Map 2 - top left: the score covers the timer
  answers: 7 of 16, 2 yes, 9 missing
  next: <what to do>

exit codes: 0 every layout was visited with no finding and no runtime error, or with --reply every answer is
there and no; 1 a finding, a runtime error, or the project did not open, or with --reply an answer missing or
a yes; 2 the project or the editor could not be used, or with --reply the reply or the result of a run with a
brief was not found; 3 no browser here, or the preview did not run, so no layout was looked at; 5 another run
holds the browser profile, named in the line with its pid: wait for it to end, or pass --profile for a profile
of this run's own
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
# Most items the texts on the screen gather in a ninth of it off its middle while two corners stand
# empty, the generator template's HUD_CROWD; an item is a group of texts, and one more for each part
# a text joins to another with " · ", " • " or " | " that holds a word.
CROWD = 3
# A line of a reviewer's reply: the screenshot's name, the question's number and yes or no, as the brief asks,
# through the bullets, bold, "Q" and dashes a model adds; what follows a yes says where it is.
ANSWER = re.compile(r"^\W*(?P<shot>.+?)\W+(?:q(?:uestion)?\s*)?(?P<q>\d+)\s*[:.)\-][\s*]*(?P<a>yes|no)\b(?P<rest>.*)$",
                    re.I)
JOINED = re.compile(r"\s[·•|]\s")
NINTHS = {(0, 0): "top-left", (0, 1): "top", (0, 2): "top-right", (1, 0): "left", (1, 2): "right",
          (2, 0): "bottom-left", (2, 1): "bottom", (2, 2): "bottom-right"}
CORNERS = ((0, 0), (0, 2), (2, 0), (2, 2))
# Shots of one layout in all while it is one colour (c3project.BLANK), and the seconds between them.
BLANK_TRIES = 3
BLANK_WAIT = 1.0

# Each question asks what a player sees as a mistake, not a fact about the picture: worded as facts (two
# outline weights, an object over another, anything the edge cuts), a judge answered yes on most screens
# without a fault (docs/decisions/look-judge-calibration.md).
QUESTIONS = (
    "Is any text cut off, broken onto a line of its own, too small or too faint to read, or partly hidden by "
    "another object?",
    "Does an object cover a text, a number, a button or the face of a card, so that the player cannot read or "
    "use it?",
    "Is a button, a text, a counter or another part of the HUD cut off by the edge of the screen?",
    "Is any object a stand-in or drawn in a style of its own: a plain box or shape among finished art, a smooth "
    "or blurred shape among pixel art, or a blurred edge among sharp ones?",
    "Does a background, a decoration or a glow catch the eye before the objects the player taps or moves, or "
    "make them hard to pick out?",
    "Do two objects that stand for different things (two enemy types, two kinds of map node, two cards) look "
    "identical, with no label, colour or icon to tell them apart?",
)
ACROSS = "Does the same decoration, not the HUD, appear on every screenshot?"

# Evaluated where the game runs, after the probe: the layout, its layers and every
# world instance on it, with what the checks need. A Sprite's frame is read twice,
# 0.3 s apart, so an animation that plays is told from one that stands still.
LOOK_JS = r"""(async () => {
  const runtime = c3probe.runtime, layout = runtime.layout;
  const shown = layer => [layer, ...layer.parentLayers()].every(l => l.isVisible && l.opacity > 0);
  const layers = {};
  for (const layer of layout.allLayers()) {
    const v = layer.getViewport();
    layers[layer.name] = {parallax: [layer.parallaxX, layer.parallaxY], shown: shown(layer),
                          view: [v.left, v.top, v.right, v.bottom]};
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
    }
    if (frameOf(i) !== undefined) {
      r.animation = i.animationName;
      r.frame = i.animationFrame;
      r.frames = i.animation ? i.animation.frameCount : 1;
      r.playing = before.get(i.uid) !== after.get(i.uid);
    }
    if (i.instVars) r.instVars = Object.fromEntries(Object.keys(i.instVars).map(k => [k, i.instVars[k]]));
    instances.push(r);
  } catch (e) {}        // destroyed while it was read
  return {layout: layout.name, size: [layout.width, layout.height],
          viewport: [runtime.viewportWidth, runtime.viewportHeight], layers, instances};
})()"""


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


def stacked_findings(instances: list[dict]) -> list[dict]:
    """Instances of one type on one box that show the same frame: two that show different
    frames or animations, a fill under its rim, are layered on purpose."""
    groups: dict[tuple, list[dict]] = {}
    for i in instances:
        if sized(i):
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


def worded(text: str) -> int:
    """The parts of a text that hold a word, split where it joins them with " · ", " • " or " | ",
    BBCode tags left out: "Round · 03" one, "Wave 3 · 12 left" two, a bare count "00" none."""
    plain = re.sub(r"\[[^\]]*\]", "", text)
    return sum(1 for part in JOINED.split(plain) if re.search(r"[^\W\d_]", part))


def told(parts: list[int]) -> int:
    """The items a group of texts tells, their worded() each: one, and one more for each further part
    a text joins; none when no text holds a word, as a count beside its icon."""
    return 1 + sum(max(0, p - 1) for p in parts) if any(parts) else 0


def crowding(texts: list, width: float, height: float) -> dict:
    """{ninth: [indexes]} of texts on a screen of width x height px, each (box on the screen, its
    worded()), and the items each ninth holds, told(), under the key "items". Texts nearer than 1.5
    times the generator template's GAP_IN at this screen are one group, as a value under its name."""
    near = 1.5 * max(1, (8 if height <= 360 else 32) // 4)
    group = list(range(len(texts)))

    def root(n: int) -> int:
        while group[n] != n:
            n = group[n]
        return n
    for n, (a, _) in enumerate(texts):
        for m in range(n + 1, len(texts)):
            b = texts[m][0]
            if max(a[0], b[0]) - min(a[2], b[2]) < near and max(a[1], b[1]) - min(a[3], b[3]) < near:
                group[root(n)] = root(m)
    hulls: dict[int, list] = {}
    for n, (box, parts) in enumerate(texts):
        hull = hulls.setdefault(root(n), [*box, [], []])
        hull[:4] = min(hull[0], box[0]), min(hull[1], box[1]), max(hull[2], box[2]), max(hull[3], box[3])
        hull[4].append(parts)
        hull[5].append(n)
    cells: dict = {"items": {}}
    for x0, y0, x1, y1, parts, members in hulls.values():
        cell = (min(2, max(0, int(1.5 * (y0 + y1) / height))), min(2, max(0, int(1.5 * (x0 + x1) / width))))
        cells.setdefault(cell, []).extend(members)
        cells["items"][cell] = cells["items"].get(cell, 0) + told(parts)
    return cells


def bar(box, width: float, height: float) -> bool:
    """Whether a text's box spans two thirds of a width x height px screen either way: a bar along an
    edge, such as a status line across the bottom, which is in no one place."""
    return box[2] - box[0] > 2 / 3 * width or box[3] - box[1] > 2 / 3 * height


def labels(instances: list[dict], view: list[float]) -> set[int]:
    """The uids of texts that label an object: the one text drawn inside a shown instance that is
    no text and no larger than half the screen, on any layer, such as a button's word, a card's name
    or a map node's letter. A panel that holds two texts or more holds information, not a label."""
    texts = [i for i in instances if sized(i) and (i.get("text") or "").strip()]
    found = set()
    for o in instances:
        if "textSize" in o or not sized(o) or area(o["box"]) > OVERLAY * area(view):
            continue
        inner = [t["uid"] for t in texts if inside(drawn(t), o["box"])]
        if len(inner) == 1:
            found.add(inner[0])
    return found


def crowd_findings(instances: list[dict], layers: dict, one_screen: bool) -> list[dict]:
    """A ninth of the screen off its middle whose texts tell CROWD items or more while two corners
    hold no text: the HUD gathered in one place and left the screen's frame empty. The texts counted
    are on a HUD layer, or on any layer of a layout one screen large. Left out: a message over half
    the screen, a bar along an edge, whose box spans two thirds of the screen's width or height, and
    the label of an object, labels()."""
    texts, seen = [], []
    for i in instances:
        layer = layers.get(i["layer"])
        if not (layer and sized(i) and (i.get("text") or "").strip() and not i.get("angle")):
            continue
        if not (one_screen or tuple(layer["parallax"]) == (0, 0)):
            continue
        view, b = layer["view"], drawn(i)
        if area(b) > OVERLAY * area(view) or bar(i["box"], view[2] - view[0], view[3] - view[1]):
            continue
        box = [b[0] - view[0], b[1] - view[1], b[2] - view[0], b[3] - view[1]]
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        if 0 <= cx <= view[2] - view[0] and 0 <= cy <= view[3] - view[1]:
            texts.append((box, worded(i["text"])))
            seen.append((i, view))
    tagged = labels(instances, seen[0][1]) if seen else set()
    keep = [n for n, (i, _) in enumerate(seen) if i["uid"] not in tagged]
    texts, seen = [texts[n] for n in keep], [seen[n] for n in keep]
    if not texts:
        return []
    view = seen[0][1]
    cells = crowding(texts, view[2] - view[0], view[3] - view[1])
    empty = [NINTHS[c] for c in CORNERS if c not in cells]
    found = []
    for cell, count in cells["items"].items():
        if cell in NINTHS and count >= CROWD and len(empty) >= 2:
            held = [seen[n][0] for n in cells[cell]]
            found.append({"rule": "crowd", "uids": [i["uid"] for i in held], "line":
                          f"the {NINTHS[cell]} of the screen holds {count} items of text "
                          f"({', '.join(name(i) for i in held[:4])}{' ...' if len(held) > 4 else ''}) while the "
                          f"{', '.join(empty)} corners stand empty: give each item its own corner or edge, and each "
                          f"text one thing rather than several joined by · or |"})
    return found


def findings(snap: dict) -> list[dict]:
    """Every mechanical finding on a layout read by LOOK_JS, each {rule, uids, line}."""
    instances, layers = snap["instances"], snap["layers"]
    one_screen = all(s <= 1.05 * v for s, v in zip(snap["size"], snap["viewport"]))
    return (text_findings(instances) + stacked_findings(instances) + overlap_findings(instances, layers)
            + edge_findings(instances, layers) + frame_findings(instances)
            + crowd_findings(instances, layers, one_screen))


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


def review(only: list[str] | None, settle: float, viewport: list[int] | None, shots: Path):
    """The `then` of open_in_editor.open_one: preview the project and visit its layouts."""
    def run(browser: oe.Browser, target: str, page: oe.DevTools) -> dict:
        page.call("Storage.clearDataForOrigin", origin=play.PREVIEW, storageTypes="local_storage,indexeddb")
        started = oe.start_preview(browser, target, page)
        if isinstance(started, list):
            return {"started": False, "errors": started, "layouts": []}
        window, win = started
        visited: list[dict] = []
        try:
            if viewport and play.emulate(win, viewport) != tuple(viewport):
                return {"started": False, "layouts": [], "errors": [
                    f"the preview window did not take the viewport {viewport[0]}x{viewport[1]} in {play.RESIZE} s"]}
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
            for layout in [n for n in order if not only or n in only]:
                done: dict = {"layout": layout, "errors": first_errors if layout == first else []}
                went = win.evaluate(GO_JS.format(name=json.dumps(layout), settle=settle), wait=settle + 20,
                                    session=session)
                if went["now"] != layout:
                    done["left"] = went["now"] if layout in went["entered"] else None
                    win.evaluate("0", session=session)
                    done["errors"] += oe.runtime_errors(win)
                    visited.append(done)
                    continue
                shot = shots / f"{file_name(layout)}.png"
                for tries in range(1, BLANK_TRIES + 1):
                    share = oe.blank(win)
                    if share is None or tries == BLANK_TRIES:
                        break
                    time.sleep(BLANK_WAIT)
                shot.write_bytes(base64.b64decode(win.call("Page.captureScreenshot")["data"]))
                if tries > 1:
                    done["blank"] = {"tries": tries, "share": share}
                try:
                    snap = win.evaluate(LOOK_JS, wait=20, session=session)
                    done.update(shot=str(shot), findings=findings(snap), snapshot=snap)
                except oe.DevToolsError as e:     # the layout's instances could not be read
                    done.update(shot=str(shot), findings=[])
                    done["errors"].append(f"its instances were not read: {str(e).splitlines()[0]}")
                win.evaluate("0", session=session)
                done["errors"] += oe.runtime_errors(win)
                visited.append(done)
        finally:
            win.ws.close()
            browser.devtools.call("Target.closeTarget", targetId=window["targetId"])
        return {"started": True, "runtime": "worker" if session else "page", "layouts": visited, "errors": []}
    return run


def unmeasured(project: Path, design: Path | None) -> list[str]:
    """The design's screen entries play_design.py does not measure, each as key "words": in words outside its
    vocabulary, or under a key that names no object type of the project."""
    path = design or project / "tools" / "design.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return []
    types = [n for n, _ in c3.folder_items(c3.load(project / "project.c3proj").get("objectTypes", {}))]
    model = gm.Design(data)
    out = []
    for p in gm.screen_places(model):
        named = [gm.screen_objects(k, model, types) for k in [p.key] + [ref for _, ref in p.sides]]
        if not p.measured or not all(named):
            out.append(f"{p.key} {json.dumps(p.text, ensure_ascii=False)}")
    return out


def questions(several: bool, places: list[str] = ()) -> list[str]:
    """The questions the script cannot answer, about every screenshot."""
    out = list(QUESTIONS)
    if places:
        out.append(f"On a screenshot that shows it, does an object sit away from the place given for it: "
                   f"{'; '.join(places)}?")
    if several:
        out.append(ACROSS)
    return out


def ask(several: bool, places: list[str] = ()) -> list[str]:
    """The questions, put to the agent about every screenshot."""
    lines = ["questions: answer every question yes or no for each screenshot above, through the brief as the last "
             "line says, or with your image tool, one screenshot at a time, and check the answers with --reply as "
             "that line says. For each yes, name the layout, the object type to change and what to change:"]
    return lines + [f"  {n}. {q}" for n, q in enumerate(questions(several, places), 1)]


def shows_something(done: dict) -> bool:
    """Whether a layout's visit left a screenshot that shows something, one the questions are about."""
    return bool(done.get("shot")) and not (done.get("blank") or {}).get("share")


def brief(result: dict) -> str:
    """The questions as a task for a reviewer that has not seen the project: the screenshots, the questions and
    the form of the answer, and nothing of what the game was meant to show."""
    layouts = (result.get("preview") or {}).get("layouts", [])
    shots = [(d["layout"], d["shot"]) for d in layouts if shows_something(d)]
    asked = questions(len(layouts) > 1, result.get("places", []))
    lines = ["# Look review", "",
             "You have not seen this game's project, its events or how it was built, and you do not need to. Judge "
             "only what the screenshots show. If a picture does not show it, answer no. Answer yes only for "
             "what a player would see as a mistake: art layered on purpose is none, such as a character in "
             "front of the ground or scenery that runs past the edge of the screen.", "",
             "Open each screenshot with your image tool, one at a time:", ""]
    lines += [f"{n}. {layout}: {shot}" for n, (layout, shot) in enumerate(shots, 1)]
    lines += ["", "Answer every question for every screenshot, yes or no:", ""]
    lines += [f"{n}. {q}" for n, q in enumerate(asked, 1)]
    lines += ["", "Reply with one line per screenshot and question, and nothing else. Start each line with the "
                  "screenshot's name and the question's number. A yes says where on the screenshot the thing is and "
                  "what looks wrong; a no is the word alone. The form, not the content:", "", "```"]
    first = shots[0][0] if shots else "Layout"
    lines += [f"{first} 1: no", f"{first} 2: yes - <where on the screenshot>: <what looks wrong>", "...", "```", ""]
    return "\n".join(lines)


def read_reply(reply: str, names: list[str], asked: int) -> tuple[dict[tuple[str, int], tuple[bool, str]], list[str]]:
    """The answers of a reply by screenshot and question, each yes with what it says, and the answer lines that
    name no screenshot or no question of the brief."""
    exact = {n.lower(): n for n in names}
    # Longest first, so that a line about "Big map" is not taken for "Map"
    longest = sorted(names, key=len, reverse=True)
    answers, stray = {}, []
    for line in reply.splitlines():
        m = ANSWER.match(line.strip())
        if not m:
            continue
        shot = m["shot"].strip(" *`#").lower()
        name = exact.get(shot) or next((n for n in longest if shot.endswith(n.lower())), None)
        if name is None or not 1 <= int(m["q"]) <= asked:
            stray.append(line.strip())
            continue
        answers[(name, int(m["q"]))] = (m["a"].lower() == "yes", m["rest"].strip(" -:*`"))
    return answers, stray


def spans(numbers: list[int]) -> str:
    """Question numbers as runs: 1-3, 5."""
    runs: list[list[int]] = []
    for n in numbers:
        if runs and n == runs[-1][-1] + 1:
            runs[-1].append(n)
        else:
            runs.append([n])
    return ", ".join(f"{r[0]}-{r[-1]}" if len(r) > 2 else ", ".join(map(str, r)) for r in runs)


DONE = "next: every question is answered no; the look review is done"


def verify_command(root: Path) -> str | None:
    """verify_change.py for the project when its look step waits for these answers, else None."""
    try:
        record = json.loads((root / ".tmp" / c3.VERIFY_RECORD).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if ((record.get("steps") or {}).get("looked") or {}).get("state") != "asked":
        return None
    return c3.script_command(root, "verify_change.py")


def check_reply(result: dict, reply: str, where: str, verify: str | None) -> tuple[list[str], int, dict]:
    """A reviewer's reply against the brief of the result: what it lacks, then every yes to fix, and the verdict
    that verify_change.py passes its look step on; verify is the command that goes on with the check chain."""
    layouts = (result.get("preview") or {}).get("layouts", [])
    names = [d["layout"] for d in layouts if shows_something(d)]
    asked = len(questions(len(layouts) > 1, result.get("places", [])))
    answers, stray = read_reply(reply, names, asked)
    missing = [(n, [q for q in range(1, asked + 1) if (n, q) not in answers]) for n in names]
    missing = [(n, qs) for n, qs in missing if qs]
    yeses = [(n, q, said) for n in names for q in range(1, asked + 1)
             for yes, said in [answers.get((n, q), (False, ""))] if yes]
    lines = [f"reply: {where}, against the brief of {len(names)} screenshot{'' if len(names) == 1 else 's'} and "
             f"{asked} questions: {len(names) * asked} answers asked"]
    if missing:
        lines.append("  missing: " + "; ".join(f"{n} {spans(qs)}" for n, qs in missing))
    unsaid = [f"{n} {q}" for n, q, said in yeses if not said]
    if unsaid:
        lines.append("  yes without where: " + ", ".join(unsaid))
    lines += [f"  not in the brief: {line}" for line in stray]
    lines += [f"  yes: {n} {q} - {said}" if said else f"  yes: {n} {q}" for n, q, said in yeses]
    lost = sum(len(qs) for _, qs in missing)
    lines.append(f"answers: {len(answers)} of {len(names) * asked}, {len(yeses)} yes, {lost} missing")
    if lost or unsaid:
        lines.append("next: give the reviewer the same brief again and have it answer the missing questions and say "
                     "where each yes is; then check its reply again")
    elif yeses:
        lines.append("next: fix each yes: name the layout and the object type at the place it describes, change it, "
                     "then run review_look.py again and have its new brief answered"
                     + (f"; name a yes about what your change did not touch in the hand-over, then run {verify}, "
                        f"which passes its look step on this reply" if verify else ""))
    elif verify:
        lines.append(f"next: every question is answered no; run {verify}, which passes its look step on this reply")
    else:
        lines.append(DONE)
    return lines, 1 if lost or yeses else 0, {"complete": not lost and not unsaid, "yes": len(yeses)}


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
                         f"draws nothing in view at its start, or the preview did not draw it. No question is asked "
                         f"about it. If it should show something, raise --settle, or reach it in play with a shot "
                         f"step of a preview_project.py plan")
        elif shot:
            before = "the shot" if blank.get("tries") == 2 else f"the {blank.get('tries', 1) - 1} shots"
            again = f", taken when the layout was drawn; {before} before showed one colour, not drawn yet" if blank \
                else ""
            lines.append(f"layout {done['layout']!r} ({n} of {total}): screenshot {shot}{again}")
        elif done.get("left"):
            lines.append(f"layout {done['layout']!r} ({n} of {total}): started, and its events went on to "
                         f"{done['left']!r} before the screenshot; it needs what the game sets up before it: play to "
                         f"it with preview_project.py and a shot step, and read that screenshot the same way")
        else:
            lines.append(f"layout {done['layout']!r} ({n} of {total}): not reached in 10 seconds")
        lines += [f"  {f['rule']}: {f['line']}" for f in done.get("findings", [])]
        lines += oe.runtime_lines(done["errors"])
    if any(shows_something(d) for d in ran["layouts"]):
        lines += ask(total > 1, result.get("places", []))
    return lines


def counts(result: dict) -> tuple[int, int, int]:
    """Findings, runtime errors and layouts visited."""
    layouts = (result.get("preview") or {}).get("layouts", [])
    return (sum(len(d.get("findings", [])) for d in layouts), sum(len(d["errors"]) for d in layouts), len(layouts))


def unpreviewed(results: list[dict]) -> list[str]:
    """The projects that opened but whose preview did not start, so that none of their layouts was looked at."""
    return [r["project"] for r in results if r["status"] == "opened" and not (r.get("preview") or {}).get("started")]


def look_line(results: list[dict], settle: float, out: Path, base: Path) -> str:
    """The count of findings, and when there is none, what the run did not see."""
    if unpreviewed(results):
        return f"look: no layout was looked at, as the preview of {', '.join(unpreviewed(results))} did not run; " \
               f"full result in {out}"
    found, errors, layouts = map(sum, zip(*(counts(r) for r in results)))
    unseen = "" if found or errors else (f"; each layout ran {settle:g} s after a jump to it, without play, so a "
                                         f"scene the game reaches only in play is unseen")
    return (f"look: {found} finding{'' if found == 1 else 's'} on {layouts} layout{'' if layouts == 1 else 's'}, "
            f"{errors} runtime error{'' if errors == 1 else 's'}{unseen}; full result in {out}, screenshots in {base}")


def reply_main(reply: Path, out: Path, limit: int, root: Path) -> int:
    """--reply: check a saved reply against the brief of the result at out, for the project at root."""
    if not reply.is_file():
        print(f"no reply at {reply}: save the reviewer's reply to that file, then run this again", file=sys.stderr)
        return 2
    result = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else None
    if isinstance(result, list):
        print(f"{out} holds the runs of {len(result)} projects; run review_look.py on the one project the brief "
              f"belongs to, then check the reply again", file=sys.stderr)
        return 2
    if not result or not result.get("brief"):
        print(f"no run with a brief in {out}: run review_look.py first, have its brief.md answered, then check the "
              f"reply", file=sys.stderr)
        return 2
    lines, code, verdict = check_reply(result, reply.read_text(encoding="utf-8"), str(reply), verify_command(root))
    # The verdict goes on the run whose brief the reply answers: verify_change.py passes its look step on it, and
    # the next run of the review writes a result without it
    result["reply"] = {"file": str(reply), **verdict}
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    shown, _ = oe.print_part(lines, limit, 0)
    if shown < len(lines):
        print(f"{len(lines) - shown} lines not printed: --limit 0 prints them")
    return code


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
                    help="CSS pixels of the preview window (default: the project's viewport size)")
    ap.add_argument("--release", metavar="rNNN", help="open in this release of the editor, as open_in_editor.py does")
    ap.add_argument("--browser", metavar="EXE",
                    help="the Chromium-based browser to start (default: Edge, Chrome or Chromium where installed)")
    ap.add_argument("--shots", type=Path, help="the folder for the screenshots (default: .tmp/look in the project)")
    ap.add_argument("--out", type=Path, help="write the result, every instance read included, as JSON "
                                             "(default: .tmp/review-look.json in the project)")
    ap.add_argument("--design", type=Path, metavar="DESIGN.json",
                    help="the game's design; a screen entry that play_design.py does not measure becomes a question "
                         "(default: tools/design.json in the project, when there is one)")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    ap.add_argument("--profile", type=Path, metavar="FOLDER",
                    help="keep the browser profile in FOLDER/editor-<browser> instead of the project's .tmp/")
    ap.add_argument("--reply", type=Path, metavar="REPLY",
                    help="a reviewer's reply to brief.md, saved to a file: check it against the last run's brief "
                         "instead of previewing, and print every yes to fix")
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
    if args.reply:
        return reply_main(args.reply, oe.kept(args.out, args.shots, projects[0], "review-look.json", "look")[0],
                          args.limit, projects[0])
    exe = args.browser or oe.browser_path()
    if not exe:
        print("no Edge, Chrome or Chromium found here, and this script needs one it can drive: install one, or open "
              "the project with open_in_editor.py --steps and take a screenshot of each layout with a browser tool "
              "of this session.")
        return 3
    editor = oe.release_url(args.release)
    out, base = oe.kept(args.out, args.shots, projects[0], "review-look.json", "look")

    def visit(browser: oe.Browser) -> list[dict]:
        """Review each project in turn. Its result is written and printed as it ends, so the results stay
        when a later project stops the run."""
        results, printed = [], 0
        for project in projects:
            shots = base if len(projects) == 1 else base / project.name
            shots.mkdir(parents=True, exist_ok=True)
            data = c3.load(project / "project.c3proj")
            view = args.viewport or [data.get("viewportWidth"), data.get("viewportHeight")]
            view = view if all(isinstance(n, int) and n > 0 for n in view) else None
            result = oe.open_one(browser, editor, project, browser.profile / "project-look.c3p", None,
                                 bool(args.release), review(args.layouts, args.settle, view, shots))
            result["places"] = unmeasured(project, args.design)
            # Names this run, so that a reply checked against its brief is not taken for one of a later run
            result["run"] = uuid.uuid4().hex[:12]
            if any(shows_something(d) for d in (result.get("preview") or {}).get("layouts", [])):
                result["brief"] = str(shots / "brief.md")
                (shots / "brief.md").write_text(brief(result), encoding="utf-8")
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
    found, errors, _ = map(sum, zip(*(counts(r) for r in results)))
    print(look_line(results, args.settle, out, base))
    if any(r["status"] != "opened" for r in results):
        print(oe.NEXT)
        return 1
    if unpreviewed(results):
        print("next: the preview did not run, so no layout was looked at and nothing passed; run this again, and if "
              "the preview stops again, run open_in_editor.py --preview, whose lines say why")
        return 3
    briefs = [r["brief"] for r in results if r.get("brief")]
    print("next: fix every finding line; a runtime error on a layout reached straight away may need the run that "
          "leads there, so play to it with preview_project.py before blaming the events. Then have the questions "
          "answered and fix each yes. Run this again until it prints no finding and every answer is no.")
    if briefs:
        reply = Path(briefs[0]).with_name("reply.md")
        print(f"brief: if you can start a sub-agent, give it {' and '.join(briefs)} as its whole task, save its reply "
              f"to {'reply.md beside the brief' if len(briefs) > 1 else reply} and run review_look.py --reply "
              f"{reply}, which prints each yes to fix and any answer it left out. Tell it nothing more about the "
              f"game: it has not seen the project, so it judges the pictures as a player does. Otherwise open each "
              f"screenshot, answer the questions yourself in the form the brief gives, save the answers to the same "
              f"file and run review_look.py --reply on it.")
    return 1 if found or errors else 0


if __name__ == "__main__":
    sys.exit(main())
