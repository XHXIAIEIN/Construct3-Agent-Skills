"""Preview a project, visit every layout, and print for each a screenshot to read,
what the runtime shows wrong on it, and the questions to answer about the picture.

    python scripts/review_look.py [PATH ...] [--project FOLDER] [--layouts NAME ...] [--settle SECONDS]
                                  [--viewport W H] [--data STATE ...] [--release rNNN] [--browser EXE] [--shots DIR]
                                  [--out RESULT.json] [--headed] [--profile FOLDER]
    python scripts/review_look.py --reply REPLY [--project FOLDER] [--out RESULT.json]

Run it after open_in_editor.py --preview passes. It previews the project as F5
does, then goes to each layout in turn with the runtime's goToLayout, lets it run
SETTLE seconds, takes a screenshot, and reads every instance of the layout from
the runtime. It prints one line per mechanical finding, each naming the layout,
the object type, the instance's UID and what to change:

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
  crowd     a ninth of the screen off its middle whose texts tell 3 items or more
            while two corners hold no text; a label on its object, a bar along
            an edge and a message over half the screen are left out
  optical   a label, a text beside a shape in a row, or a glyph alone on a
            shape, whose ink sits off the face's centre by more than the larger
            of 1.5 px and 0.06 em
  faint     a text that reads under text.contrast on what lies behind it on
            screen: its strokes' core pixels against them with every text hidden
  unlimited Texts that events set with no longest text in tools/texts.json

Each finding has its rule's tier (look.severity in assets/look-manifest.json):
broken and ugly ones fail the review, fragile ones (optical, unlimited) warn.
Each layout is also shown in the other data states of --data: the longest
text (or a guess), no text, and counts of 1. Without --viewport, it is also
shown on two more screen shapes that its orientations allow. There text,
overlap, edge and crowd run again, printed with @ and where; what only a
guessed text causes warns.

A screenshot 99.9% of one colour, black or clear, is taken again 1 s later,
twice at most; a layout still so draws nothing in view and gets no question.

Then it prints the questions to answer from the screenshots, which the script
cannot judge: each is answered yes or no, and each yes names the object to
change; a yes to the first three is broken, to the rest ugly. When the
project has a design (--design, by default tools/design.json),
one question lists the design's screen entries that play_design.py cannot
measure: entries with other words before the first comma, and entries whose
key names no object of the project.

The user's references (art/references/, PNG, JPEG or WebP) go beside the
screenshot of the layout they are named after, else of the first, and the
picked look (art/look.png) beside the first: <layout>@reference.png, with
their colours, under a question for each.

A layout reached by goToLayout starts without what the game's flow sets up
before it; play to such a scene with preview_project.py and a shot step.

Screenshots go to --shots as <layout>.png, the whole result to --out.
Beside them it writes brief.md: the screenshots, the questions and the form
of the answer, for a reviewer that has not seen the project, since the game's
builder reads its pictures by what it meant to build.
The last three lines are look:, next:, and brief:, which says who answers.

With git, the brief also shows each layout as it was where the branch agents
left the user's, and a yes the reviewer marks before fails nothing.

--reply checks a reviewer's saved reply against the brief of the last run in
--out, without a browser: every answer missing, each yes that does not say
where (or new or before), each line naming no screenshot of the brief, then
every yes, worst first.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import re
import subprocess
import sys
import tarfile
import time
import unicodedata
import uuid
from pathlib import Path

# python -I leaves this script's folder off sys.path, and the modules beside it are imported from there
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import art
import c3project as c3
import check_look as cl
import game_model as gm
import open_in_editor as oe
import preview_project as play

EPILOG = """examples:
  python scripts/review_look.py
  python scripts/review_look.py --layouts Menu Map --settle 2
  python scripts/review_look.py --viewport 430 932 --data demo
  python scripts/review_look.py --reply .tmp/scripts/review-look/reply.md

output:
  opened   <project>  (<window title>, <the editor it opened in>)
  layout 'Map' (2 of 3): screenshot .tmp/scripts/review-look/shots/Map.png
    broken text: Text Title uid 12 "Choose your path": the text needs 212x40 px and its box is 160x40 ...
    broken stacked: Text CardName: 5 instances on one box at (300, 420) 120x30, uids 41, 42, 43 ...
    broken edge @phone worst: ScoreText uid 9 "9999999": the right edge of the screen cuts it ...
    fragile optical: PlayLabel uid 7 "Play" on PlayButton uid 6: its ink sits 3.0 px above the centre of the ...
    runtime: <an error the layout logged, with its event, and (N times) when it came more than once>
  layout 'Combat' (3 of 3): started, and its events went on to 'Map' before the screenshot; ...
  questions: answer every question yes or no for each screenshot above, through the brief as the last line ...
    1. Is any text cut off, broken onto a line of its own, too small or too faint to read, or partly hidden ...
    ...
    8. Does the same decoration, not the HUD, appear on every screenshot?
  look: 3 findings to fix and 1 that warns on 3 layouts, 0 runtime errors; full result in .tmp/scripts/review-look/result.json,
    screenshots in .tmp/scripts/review-look/shots
  next: <what to do>
  brief: if you can start a sub-agent, give it .tmp/scripts/review-look/shots/brief.md as its whole task ...

output of --reply:
  reply: .tmp/scripts/review-look/reply.md, against the brief of 2 screenshots and 8 questions: 16 answers asked
    missing: Map 3, 4; Combat 1-8
    yes without where: Map 5
    not in the brief: Shop 1: no
    yes, broken: Map 2 - top left: the score covers the timer
  answers: 7 of 16, 2 yes, 9 missing
  next: <what to do>

exit codes: 0 every layout was visited with no broken or ugly finding and no runtime error, or with --reply
every answer is there and no; 1 a broken or ugly finding, a runtime error, or the project did not open, or with --reply an answer missing or
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
ANSWER = re.compile(r"^\W*(?P<shot>.+?)\W+(?:q(?:uestion)?\s*)?(?P<q>\d+)\s*[:.)\-][\s*]*(?P<a>yes|no)\b"
                    r"(?:[\s,;(*]*(?P<when>new|before)\b)?(?P<rest>.*)$", re.I)
JOINED = re.compile(r"\s[·•|]\s")
NINTHS = {(0, 0): "top-left", (0, 1): "top", (0, 2): "top-right", (1, 0): "left", (1, 2): "right",
          (2, 0): "bottom-left", (2, 1): "bottom", (2, 2): "bottom-right"}
CORNERS = ((0, 0), (0, 2), (2, 0), (2, 2))
# Shots of one layout in all while it is one colour (c3project.BLANK), and the seconds between them.
BLANK_TRIES = 3
BLANK_WAIT = 1.0

# The tiers of look.severity, worst first; broken and ugly fail the review, fragile warns.
TIERS = ("broken", "ugly", "fragile")
BLOCKING = ("broken", "ugly")
TIER = {"text": "broken", "stacked": "broken", "overlap": "broken", "edge": "broken", "frame": "broken",
        "faint": "broken", "crowd": "ugly", "unlimited": "fragile", "optical": "fragile"}

# Each question asks what a player sees as a mistake, not a fact about the picture: worded as facts (two
# outline weights, an object over another, anything the edge cuts), a judge answered yes on most screens
# without a fault (docs/decisions/look-judge-calibration.md). A yes to each is of the tier beside it.
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
    "Does the screen look like an app's dashboard rather than a game: its parts set in rounded cards, a count in a "
    "pill, a soft shadow under every panel?",
)
QUESTION_TIERS = ("broken", "broken", "broken", "ugly", "ugly", "ugly", "ugly")
ACROSS = "Does the same decoration, not the HUD, appear on every screenshot?"
# Asked when art/references/ holds the user's references, which the pair picture shows beside a screenshot
# It names the dimensions of prepare_art.DIMENSIONS, so that a yes names one
REFERENCE = ("Beside the user's reference in its pair picture, does the screenshot look like another game: other "
             "colours, another light, another way of rendering or outlining, other proportions or another view? Other "
             "objects, another layout or other text is no difference. A picture without a pair picture: no.")
# Asked when the user picked a look with pick_look.py: art/look.png, the first play screen drawn in it, is in the
# pair picture of the screenshot of the layout the game starts on
PICKED = ("Beside the picked look in its pair picture, does the screenshot differ from it in its colours, light, "
          "rendering, outlining, proportions or view? A yes names each place where it differs and how. Other "
          "objects, another layout or other text is no difference. A picture without the picked look in its pair "
          "picture: no.")

# The data states a layout is looked at in.
DATA_STATES = ("demo", "worst", "empty", "one")
# The worst text guessed for a Text with no declared longest: a count, a name, a Chinese name.
WORST_NUMBER = "9999999"
WORST_NAME = "Wolfeschlegel-Steinhausen"
WORST_WIDE = "最长的名字也要放得下才行"
# A count in a text: digits, each spaced from the next by one narrow space in a tracked() tag.
COUNT = re.compile(r"\d(?:([   ])?\d)*")
# Actions that set a Text's text, by their id in an event sheet.
SETS_TEXT = ("set-text", "append-text", "typewriter-text")
# The text of each Text type at its longest, which the generator template writes from its helpers' `longest`, and
# a project of any other making may write by hand: {"longest": {"ScoreText": "999999"}}.
DECLARED = Path("tools", "texts.json")

# The shapes of screen each layout is looked at in without --viewport, besides the project's own, by the
# orientations the project allows: Scale outer and Anchor put the HUD in another place on each. The shorter side
# stays the project's.
SHAPES = {"landscape": (("4x3", 4 / 3), ("16x9", 16 / 9), ("phone", 19.5 / 9)),
          "portrait": (("3x4", 3 / 4), ("9x16", 9 / 16), ("phone", 9 / 19.5)),
          "any": (("4x3", 4 / 3), ("16x9", 16 / 9), ("phone", 9 / 19.5))}
# Rules that run again at each other data state and screen shape: what a longer text or another screen moves.
AGAIN = ("text", "overlap", "edge", "crowd")

# Evaluated where the game runs, after the probe: the layout, its layers and every
# world instance on it, with what the checks need. A Sprite's frame is read twice,
# 0.3 s apart, so an animation that plays is told from one that stands still.
LOOK_JS = r"""(async () => {
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


def centred(a, b, axis: int) -> bool:
    """Whether box a's centre lies on box b's, across (axis 0) or down (axis 1): within TOLERANCE px
    or a tenth of b's extent, so a label laid on a shape's face counts though a shadow widens the
    shape's box."""
    lo, hi = b[axis], b[axis + 2]
    return abs((a[axis] + a[axis + 2]) / 2 - (lo + hi) / 2) <= max(TOLERANCE, (hi - lo) / 10)


def optical_pairs(instances: list[dict], layers: dict, height: float) -> list[dict]:
    """What the layout centres on a shape, each {kind, glyph, shape, axes}, where `glyph` is the
    text or the non-text instance centred on `shape`. The kinds:
        label   the one text inside a shape, on each axis where its alignment centres it and its
                box is centred
        beside  a text in a row with a shape (a toggle's, a checkbox's, a bar's name), centred
                down, a unit apart or less, its box overlapping the shape's by half or more down
        glyph   a non-text instance of half the shape's area or less, alone on it and centred
                both ways"""
    unit = 8 if height <= 360 else 32
    shown = [i for i in instances if sized(i) and not i.get("angle") and i["layer"] in layers]
    texts = [i for i in shown if (i.get("text") or "").strip()]
    shapes = [i for i in shown if "textSize" not in i and area(i["box"]) <= OVERLAY * area(layers[i["layer"]]["view"])]
    pairs = []
    for t in texts:
        h_align, v_align = t.get("align") or ("left", "top")
        on = [o for o in shapes if o["layer"] == t["layer"] and inside(drawn(t), o["box"])]
        if on:
            o = min(on, key=lambda o: area(o["box"]))
            axes = [axis for axis, align in ((0, h_align), (1, v_align))
                    if align == "center" and centred(t["box"], o["box"], axis)]
            if axes and sum(inside(drawn(x), o["box"]) for x in texts) == 1:
                pairs.append({"kind": "label", "glyph": t, "shape": o, "axes": axes})
            continue
        if v_align != "center":
            continue
        a = t["box"]
        beside = [(max(o["box"][0] - a[2], a[0] - o["box"][2]), o) for o in shapes if o["layer"] == t["layer"]
                  and min(a[3], o["box"][3]) - max(a[1], o["box"][1]) >= min(a[3] - a[1], o["box"][3] - o["box"][1]) / 2
                  and -TOLERANCE <= max(o["box"][0] - a[2], a[0] - o["box"][2]) <= unit + TOLERANCE
                  and centred(a, o["box"], 1)]
        if beside:
            pairs.append({"kind": "beside", "glyph": t, "shape": min(beside, key=lambda g: g[0])[1], "axes": [1]})
    for g in shapes:
        on = [o for o in shapes if o is not g and o["layer"] == g["layer"] and inside(g["box"], o["box"])
              and area(g["box"]) <= area(o["box"]) / 2]
        if not on:
            continue
        o = min(on, key=lambda o: area(o["box"]))
        alone = not any(x is not g and x is not o and inside(drawn(x), o["box"]) for x in shown)
        if alone and centred(g["box"], o["box"], 0) and centred(g["box"], o["box"], 1):
            pairs.append({"kind": "glyph", "glyph": g, "shape": o, "axes": [0, 1]})
    return pairs


# One step of the shots of optical(), with the time scale at 0 so that nothing moves between them.
# `step` sets the texts of {uid: text} and hides the uids of `hide`; null restores the texts, the
# visibility and the time scale. The layout's events still run at time scale 0 and can destroy an
# instance between two steps.
OPTICAL_JS = """(async () => {{ const runtime = c3probe.runtime, step = {step};
  const kept = globalThis.c3optical ??= {{shown: new Map(), texts: new Map(), timeScale: runtime.timeScale}};
  runtime.timeScale = 0;
  if (step === null) {{
    for (const [uid, text] of kept.texts) {{ const i = runtime.getInstanceByUid(uid); if (i) i.text = text; }}
    for (const [uid, shown] of [...kept.shown].reverse()) {{
      const i = runtime.getInstanceByUid(uid); if (i) i.isVisible = shown; }}
    runtime.timeScale = kept.timeScale;
    delete globalThis.c3optical;
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


def reference(text: str) -> str | None:
    """The characters of a text whose ink sets the line it is centred by: its capitals and digits,
    else its wide letters (Chinese, Japanese, Korean); None for a text of neither, which is centred
    by all its ink. Capitals stand on the baseline at cap height and an ideograph sits as high as a
    capital, so a descender or a short letter does not move the line: "Play" is centred as "P" is."""
    caps = "".join(c for c in text if c.isascii() and (c.isupper() or c.isdigit()))
    wide = "".join(c for c in text if unicodedata.east_asian_width(c) in ("W", "F")
                   and unicodedata.category(c).startswith("L"))
    return caps or wide or None


# Least change of a colour channel, of 255, that counts as ink; and the share of the largest change in
# a clip below which a pixel is the antialiased fringe of a glyph, not its ink.
INK_LEAST = 16
INK_SHARE = 0.3


def within(w: int, n: int, region) -> bool:
    """Whether pixel n of a clip w px wide lies in the box `region` of the clip."""
    return region[0] <= n % w < region[2] and region[1] <= n // w < region[3]


def ink(w: int, before: list, after: list, region) -> tuple[list[float], tuple[float, float]] | None:
    """Box and centroid, weighted by the change, of the pixels in `region` that differ between two
    shots of a clip w px wide: what was hidden between them. None when nothing changed there."""
    change = [max(abs(p - q) for p, q in zip(u[:3], v[:3])) if within(w, n, region) else 0
              for n, (u, v) in enumerate(zip(before, after))]
    top = max(change, default=0)
    if top < INK_LEAST:
        return None
    cut = max(INK_LEAST, INK_SHARE * top)
    xs, ys, sx, sy, total = [], [], 0.0, 0.0, 0.0
    for n, d in enumerate(change):
        if d >= cut:
            x, y = n % w, n // w
            xs.append(x)
            ys.append(y)
            sx, sy, total = sx + d * (x + 0.5), sy + d * (y + 0.5), total + d
    return [min(xs), min(ys), max(xs) + 1, max(ys) + 1], (sx / total, sy / total)


def face(w: int, shape: list, bare: list, region) -> list[float] | None:
    """The box, in px of the clip, of a shape's face in the box `region` of the clip: of the pixels
    that differ between the shot with the shape and the one without it, those in the colour most of
    them show. A shadow, an outline and the antialiased edge are left out, so a label is measured
    against the face it sits on."""
    changed = [n for n, (u, v) in enumerate(zip(shape, bare))
               if within(w, n, region) and max(abs(p - q) for p, q in zip(u[:3], v[:3])) >= INK_LEAST]
    if not changed:
        return None
    colours: dict[tuple, int] = {}
    for n in changed:
        key = tuple(c // 8 for c in shape[n][:3])
        colours[key] = colours.get(key, 0) + 1
    mode = max(colours, key=colours.get)
    held = [n for n in changed if all(abs(c // 8 - m) <= 2 for c, m in zip(shape[n][:3], mode))]
    xs, ys = [n % w for n in held], [n // w for n in held]
    return [min(xs), min(ys), max(xs) + 1, max(ys) + 1]


def optical(win: oe.DevTools, session: str | None, pairs: list[dict], layers: dict) -> list[dict]:
    """Measures each pair of optical_pairs() by hide-and-diff, in shots of each pair's clip: as it
    is, with each text set to its reference(), with the glyphs hidden, and with their shapes hidden
    too. Returns {pair, ink, line, face, offset} for each pair whose glyph and face were both found:
    the glyph's ink, the ink of its reference and the shape's face(), each a box in layer px. The
    offset [dx, dy] runs from the face's centre to the glyph's: across, to the centre of a text's ink;
    down, to the centre of its reference's ink; both ways, to a glyph's centroid."""
    clips = []
    for p in pairs:
        ax, ay, sx, sy = layers[p["glyph"]["layer"]]["css"]
        box = [min(p["glyph"]["box"][0], p["shape"]["box"][0]), min(p["glyph"]["box"][1], p["shape"]["box"][1]),
               max(p["glyph"]["box"][2], p["shape"]["box"][2]), max(p["glyph"]["box"][3], p["shape"]["box"][3])]
        x0, y0 = max(0.0, ax + sx * box[0] - 2), max(0.0, ay + sy * box[1] - 2)
        clips.append({"x": x0, "y": y0, "width": ax + sx * box[2] + 2 - x0, "height": ay + sy * box[3] + 2 - y0,
                      "scale": 1})

    def shoot(step) -> list[tuple[int, int, list]]:
        win.evaluate(OPTICAL_JS.format(step=json.dumps(step)), wait=10, session=session)
        return [c3.png_rgba(base64.b64decode(win.call("Page.captureScreenshot", format="png", clip=c)["data"]))
                for c in clips] if step is not None else []
    texts = {p["glyph"]["uid"]: reference(p["glyph"]["text"]) for p in pairs if p["kind"] != "glyph"}
    try:
        shots = [shoot({}), shoot({"texts": {u: t for u, t in texts.items() if t}}),
                 shoot({"hide": [p["glyph"]["uid"] for p in pairs]}), shoot({"hide": [p["shape"]["uid"] for p in pairs]})]
    finally:
        shoot(None)
    measured = []
    for p, c, *taken in zip(pairs, clips, *shots):
        (w, _, shown), (_, _, ref), (_, _, bare), (_, _, empty) = taken
        ax, ay, sx, sy = layers[p["glyph"]["layer"]]["css"]
        k = w / c["width"]

        def layer_px(box):
            return [(c["x"] + box[0] / k - ax) / sx, (c["y"] + box[1] / k - ay) / sy,
                    (c["x"] + box[2] / k - ax) / sx, (c["y"] + box[3] / k - ay) / sy]

        def clip_px(box):
            return [(ax + sx * box[0] - c["x"]) * k, (ay + sy * box[1] - c["y"]) * k,
                    (ax + sx * box[2] - c["x"]) * k, (ay + sy * box[3] - c["y"]) * k]
        region = clip_px(p["glyph"]["box"])
        found, line, under = ink(w, shown, bare, region), ink(w, ref, bare, region),             face(w, bare, empty, clip_px(p["shape"]["box"]))
        if not (found and line and under):
            continue
        f = layer_px(under)
        if p["kind"] == "glyph":
            cx, cy = found[1]
            across = down = layer_px([cx, cy, cx, cy])
        else:
            across, down = layer_px(found[0]), layer_px(line[0])
        measured.append({"pair": p, "ink": layer_px(found[0]), "line": layer_px(line[0]), "face": f,
                         "offset": [(across[0] + across[2] - f[0] - f[2]) / 2, (down[1] + down[3] - f[1] - f[3]) / 2]})
    return measured


# Px, and share of the text's em, by which the ink of a label may sit off the centre of the face it is
# centred on, the larger of the two: past it the label looks set high or to one side. The runtime
# centres a Text's em box, where capitals and Chinese sit about a tenth of an em high.
OPTICAL_PX = 1.5
OPTICAL_EM = 0.06


def optical_findings(measured: list[dict]) -> list[dict]:
    """A finding for each measured pair whose glyph sits off its face's centre, on an axis the pair
    centres, by more than the larger of OPTICAL_PX and OPTICAL_EM of the text's em; a glyph's em
    is its box's shorter side. A label inside its shape is lowered by shrinking its box, so it stays
    inside; a text beside a shape by moving its box, which keeps it a line high."""
    found = []
    for m in measured:
        p = m["pair"]
        g, o = p["glyph"], p["shape"]
        em = g.get("em") or min(g["box"][2] - g["box"][0], g["box"][3] - g["box"][1])
        limit = max(OPTICAL_PX, OPTICAL_EM * em)
        off = [(axis, m["offset"][axis]) for axis in p["axes"] if abs(m["offset"][axis]) > limit]
        if not off:
            continue
        where = " and ".join(f"{abs(d):.1f} px {('left of', 'right of', 'above', 'below')[2 * axis + (d > 0)]}"
                             for axis, d in off)
        if p["kind"] == "glyph":
            move = " and ".join(f"{max(1, round(abs(d)))} px {('right', 'left', 'down', 'up')[2 * axis + (d > 0)]}"
                                for axis, d in off)
            fix = (f"move it {move}, so the centre of its area, not of its box, sits on the shape's centre; or "
                   f"set its image's origin at that centre")
        elif p["kind"] == "label":
            fix = "; ".join(f"move its ink {('right', 'left', 'down', 'up')[2 * axis + (d > 0)]} "
                            f"{max(1, round(abs(d)))} px by shrinking its box from the "
                            f"{('left', 'right', 'top', 'bottom')[2 * axis + (d > 0)]} by "
                            f"{2 * max(1, round(abs(d)))} px" for axis, d in off)
        else:
            fix = "; ".join(f"move its ink {('right', 'left', 'down', 'up')[2 * axis + (d > 0)]} "
                            f"{max(1, round(abs(d)))} px by moving its box as far" for axis, d in off)
        what = {"label": "on", "beside": "beside", "glyph": "on"}[p["kind"]]
        found.append({"rule": "optical", "uids": [g["uid"], o["uid"]], "line":
                      f"{name(g)} {what} {name(o)}: its {'area' if p['kind'] == 'glyph' else 'ink'} sits {where} "
                      f"the centre of the shape's face, which a player sees as off centre: {fix}"})
    return found


def luminance(rgb) -> float:
    """WCAG 2.2's relative luminance of an sRGB colour of 0-255 channels."""
    lin = [c / 255 / 12.92 if c / 255 <= 0.04045 else ((c / 255 + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a, b) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


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
        win.evaluate(OPTICAL_JS.format(step=json.dumps(step)), wait=10, session=session)
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


# Contrast a text needs, small and from LARGE_PX css px of em up, WCAG's 18 pt: the manifest's text.contrast;
# and the share of it a measure may fall short by, for the antialiasing that mixes the core of a thin stroke
CONTRAST = cl.rule_value("text.contrast")
LARGE_PX = 24
CONTRAST_SLACK = 0.9


def faint_findings(texts: list[dict], measured: dict[int, tuple], layers: dict) -> list[dict]:
    """A finding for each text whose colour, measured on what lies behind it, reads under text.contrast."""
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
            gap = m[1] or ""      # tracked() spaces each letter of a tag with a narrow space
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
             f"text it shows, or declare it in {DECLARED.as_posix()}"}]


def findings(snap: dict, only: tuple[str, ...] | None = None) -> list[dict]:
    """Every mechanical finding on a layout read by LOOK_JS, each {rule, tier, uids, line}; with `only`, those
    of these rules."""
    instances, layers = snap["instances"], snap["layers"]
    one_screen = all(s <= 1.05 * v for s, v in zip(snap["size"], snap["viewport"]))
    run = {"text": lambda: text_findings(instances), "stacked": lambda: stacked_findings(instances),
           "overlap": lambda: overlap_findings(instances, layers), "edge": lambda: edge_findings(instances, layers),
           "frame": lambda: frame_findings(instances),
           "crowd": lambda: crowd_findings(instances, layers, one_screen)}
    return tiered([f for rule, find in run.items() if only is None or rule in only for f in find()])


def tiered(found: list[dict], at: str | None = None) -> list[dict]:
    """The findings with the tier of their rule, and where they arose when not on the shot as it is."""
    return [{**f, "tier": TIER[f["rule"]], **({"at": at} if at else {})} for f in found]


def guessed(found: list[dict], instances: list[dict], setters: set[str], longest: dict[str, str],
            state: str) -> list[dict]:
    """The findings of a data state, each that a worst text guessed for an undeclared type caused only warning:
    the guess may be longer than anything the game shows."""
    if state != "worst":
        return found
    types = {i["uid"]: i["type"] for i in instances}
    return [{**f, "tier": "fragile", "line": f"{f['line']}; the worst text was guessed, as no longest is declared"}
            if any(types.get(u) in setters - set(longest) for u in f["uids"]) else f for f in found]


def ranked(found: list[dict]) -> list[dict]:
    """The findings worst tier first, in their order within a tier, one of each rule and uids: the first that
    arose, on the shot as it is before another data state or screen shape."""
    seen, out = set(), []
    for f in sorted(found, key=lambda f: TIERS.index(f["tier"])):
        key = (f["rule"], tuple(f["uids"]))
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def blocking(found: list[dict]) -> list[dict]:
    return [f for f in found if f["tier"] in BLOCKING]


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
    """(name, [w, h]) of each screen a layout is looked at on: the project's own viewport, named "", then the
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


def review(only: list[str] | None, settle: float, shapes: list[tuple[str, list[int]]], shots: Path,
           states: tuple[str, ...], setters: set[str], longest: dict[str, str]):
    """The `then` of open_in_editor.open_one: preview the project and visit its layouts on each screen shape, the
    first being the project's own, at each data state."""
    def visit(win: oe.DevTools, session: str | None, layout: str, shape: str, errors: list[str]) -> dict:
        """One layout on the screen shape as it is: its screenshot, what LOOK_JS reads and the findings, then each
        other data state's. The label centring and the text contrast are measured on the project's own shape."""
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
            snap = win.evaluate(LOOK_JS, wait=20, session=session)
            found = tiered(findings(snap, AGAIN if shape else None), shape or None)
            if not shape:
                done["snapshot"] = snap
                found += tiered(unlimited_findings(snap["instances"], setters, longest))
                pairs = optical_pairs(snap["instances"], snap["layers"], snap["viewport"][1])
                if pairs:
                    measured = optical(win, session, pairs, snap["layers"])
                    done["optical"] = [{"glyph": m["pair"]["glyph"]["uid"], "shape": m["pair"]["shape"]["uid"],
                                        **{k: m[k] for k in ("ink", "line", "face", "offset")}} for m in measured]
                    found += tiered(optical_findings(measured))
                texts = legible_texts(snap["instances"], snap["layers"])
                if texts:
                    colours = contrasts(win, session, texts, snap["layers"])
                    done["contrast"] = {str(u): [list(a), list(b)] for u, (a, b) in colours.items()}
                    found += tiered(faint_findings(texts, colours, snap["layers"]))
            done["states"] = {}
            for state in [s for s in states if s != "demo"]:
                set_to = state_texts(snap["instances"], setters, longest, state)
                if not set_to:
                    continue
                path = shots / shot_name(layout, shape, state)
                try:
                    win.evaluate(OPTICAL_JS.format(step=json.dumps({"texts": set_to})), wait=10, session=session)
                    path.write_bytes(base64.b64decode(win.call("Page.captureScreenshot")["data"]))
                    again = win.evaluate(LOOK_JS, wait=20, session=session)
                finally:
                    win.evaluate(OPTICAL_JS.format(step="null"), wait=10, session=session)
                done["states"][state] = {"shot": str(path), "texts": {str(u): t for u, t in set_to.items()}}
                found += guessed(tiered(findings(again, AGAIN), " ".join(p for p in (shape, state) if p)),
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


def questions(several: bool, places: list[str] = (), referenced: bool = False, picked: bool = False) -> list[str]:
    """The questions the script cannot answer, about every screenshot."""
    out = list(QUESTIONS) + [REFERENCE] * referenced + [PICKED] * picked
    if places:
        out.append(f"On a screenshot that shows it, does an object sit away from the place given for it: "
                   f"{'; '.join(places)}?")
    if several:
        out.append(ACROSS)
    return out


def question_tiers(several: bool, places: list[str] = (), referenced: bool = False,
                   picked: bool = False) -> list[str]:
    """The tier of a yes to each of questions(): a screen in another look than the user's references or the picked
    look, an object away from its place and a decoration on every screen look wrong, as the questions about style
    do."""
    return list(QUESTION_TIERS) + ["ugly"] * (referenced + picked + bool(places) + several)


def ask(several: bool, places: list[str] = (), referenced: bool = False, picked: bool = False) -> list[str]:
    """The questions, put to the agent about every screenshot."""
    lines = ["questions: answer every question yes or no for each screenshot above, through the brief as the last "
             "line says, or with your image tool, one screenshot at a time, and check the answers with --reply as "
             "that line says. For each yes, name the layout, the object type to change and what to change:"]
    return lines + [f"  {n}. {q}" for n, q in enumerate(questions(several, places, referenced, picked), 1)]


def shows_something(done: dict) -> bool:
    """Whether a layout's visit left a screenshot that shows something, one the questions are about."""
    return bool(done.get("shot")) and not (done.get("blank") or {}).get("share")


# The pages of the contact sheet of the generated game's pictures that the skill's art.py writes, judged with the
# screenshots: question 4 then asks whether one picture is drawn in a style of its own, question 6 whether two look
# alike. Each page is named ART_SHEET and its number
ART_SHEET = "Art sheet"


def pictures(result: dict) -> list[tuple[str, str]]:
    """(name, file) of every picture the questions are about: the screenshots that show something, then the
    pages of the contact sheet of the game's art when the run found one."""
    layouts = (result.get("preview") or {}).get("layouts", [])
    shots = [(d["layout"], d["shot"]) for d in layouts if shows_something(d)]
    return shots + [(f"{ART_SHEET} {n}", page) for n, page in enumerate(result.get("art_sheets", []), 1)
                    if shots]


def before_commit(project: Path) -> str | None:
    """The commit the change under review starts from: the newest commit of HEAD's history that another local
    branch holds, where the branch agents left the user's branch (SKILL.md), else HEAD. None outside git or before
    the first commit."""
    head = c3.git_out(project, "rev-parse", "--verify", "-q", "HEAD^{commit}")
    if not head:
        return None
    current = c3.git_out(project, "symbolic-ref", "-q", "HEAD") or ""
    others = [r for r in (c3.git_out(project, "for-each-ref", "--format=%(refname)", "refs/heads") or "").split()
              if r != current]
    if not others:
        return head
    own = set((c3.git_out(project, "rev-list", "HEAD", "--not", *others) or "").split())
    history = (c3.git_out(project, "rev-list", "--topo-order", "HEAD") or "").split()
    return next((c for c in history if c not in own), head)


def before_copy(project: Path, commit: str) -> Path | None:
    """The project's folder as it was at commit, written once into .tmp/scripts/review-look/before/<commit>/;
    None when the commit holds no project there."""
    copy = c3.script_folder(project, "review-look") / "before" / commit[:12] / "project"
    if (copy / "project.c3proj").is_file():
        return copy
    prefix = c3.git_out(project, "rev-parse", "--show-prefix")
    if prefix is None:
        return None
    p = subprocess.run(["git", "-C", str(project), "archive", "--format=tar", f"{commit}:{prefix}"],
                       capture_output=True, timeout=120)
    if p.returncode:
        return None
    with tarfile.open(fileobj=io.BytesIO(p.stdout)) as tar:
        tar.extractall(copy, filter="data")
    return copy if (copy / "project.c3proj").is_file() else None


def before_shots(project: Path, commit: str, key: dict, preview) -> dict:
    """The screenshot of each layout before the change, by layout: the project at commit, previewed by
    preview(copy, shots) once for each key (the layouts, the screen and the settle) and kept beside the copy."""
    copy = before_copy(project, commit)
    if copy is None:
        return {"commit": commit, "shots": {}, "errors": [f"the commit {commit[:12]} holds no project.c3proj here"]}
    kept = copy.parent / "result.json"
    if kept.is_file():
        old = json.loads(kept.read_text(encoding="utf-8"))
        if old.get("key") == key:
            return old
    (copy.parent / "shots").mkdir(exist_ok=True)
    ran = preview(copy, copy.parent / "shots")
    layouts = (ran.get("preview") or {}).get("layouts", [])
    got = {"commit": commit, "key": key, "shots": {d["layout"]: d["shot"] for d in layouts if shows_something(d)},
           "errors": oe.report(ran) if ran["status"] != "opened" else (ran.get("preview") or {}).get("errors", [])}
    if got["shots"]:
        kept.write_text(json.dumps(got, ensure_ascii=False, indent=1), encoding="utf-8")
    return got


def paired(refs: list[Path], layouts: list[str], first: str | None, look: Path | None = None) -> dict[str, list[Path]]:
    """The references of each layout: one whose file name without the extension is a layout's name goes with
    that layout, and every other with the layout the game starts on, the screen pick_look.py draws, or else with the
    first layout looked at. The picked look, art/look.png, goes with that layout too, last."""
    named = {k: layout for layout in layouts for k in (layout.lower(), file_name(layout).lower())}
    start = first if first in layouts else (layouts[0] if layouts else None)
    out: dict[str, list[Path]] = {}
    for ref in refs:
        layout = named.get(ref.stem.lower(), start)
        if layout:
            out.setdefault(layout, []).append(ref)
    if look and start:
        out.setdefault(start, []).append(look)
    return out


def reference_pairs(project: Path, exe: str, result: dict, shots: Path, look: Path | None) -> dict:
    """The pair picture of each screenshot that has references or the picked look, <layout>@reference.png in shots,
    with the colours measured from each side, by layout."""
    refs, _ = art.references(project)
    layouts = {d["layout"]: d["shot"] for d in (result.get("preview") or {}).get("layouts", []) if shows_something(d)}
    out = {}
    renderer = art.Renderer(project, exe, "review-look")
    try:
        first = c3.load(project / "project.c3proj").get("firstLayout")
        for layout, given in paired(refs, list(layouts), first, look).items():
            captions = [(f"picked look: {r.name}" if r == look else f"reference: {r.name}", r) for r in given]
            data, colours, own = art.reference_pair(renderer, captions, Path(layouts[layout]), f"game: {layout}")
            pair = shots / f"{file_name(layout)}@reference.png"
            pair.write_bytes(data)
            out[layout] = {"pair": str(pair), "colours": own,
                           "references": [{"file": str(r), "colours": c, **({"picked": True} if r == look else {})}
                                          for r, c in zip(given, colours)]}
    finally:
        renderer.close()
    return out


def paired_pictures(result: dict) -> dict[str, str]:
    """The pair picture of each screenshot that has the user's references or the picked look, by layout."""
    return {layout: p["pair"] for layout, p in (result.get("references") or {}).items()}


def compared(result: dict) -> tuple[bool, bool]:
    """Whether a pair picture shows the user's references, and whether one shows the picked look: whether their
    questions are asked."""
    shown = [r for p in (result.get("references") or {}).values() for r in p["references"]]
    return any(not r.get("picked") for r in shown), any(r.get("picked") for r in shown)


def reference_lines(result: dict, layout: str) -> list[str]:
    """The pair picture of a layout's screenshot and the colours measured on each side of it."""
    got = (result.get("references") or {}).get(layout)
    if not got:
        return []
    shown = " and ".join(what for what, there in (
        ("the user's references", any(not r.get("picked") for r in got["references"])),
        ("the picked look", any(r.get("picked") for r in got["references"]))) if there)
    return ([f"  reference: pair picture {got['pair']}, {shown} beside the screenshot"]
            + [f"    colours of {'the picked look ' * bool(r.get('picked'))}{Path(r['file']).name}: "
               f"{art.colours(r['colours'])}" for r in got["references"]]
            + [f"    colours of the screenshot: {art.colours(got['colours'])}"])


def befores(result: dict) -> dict[str, str]:
    """The picture from before the change of each screenshot that has one, by layout."""
    return (result.get("before") or {}).get("shots", {})


def brief(result: dict) -> str:
    """The questions as a task for a reviewer that has not seen the project: the screenshots, the questions and
    the form of the answer, and nothing of what the game was meant to show."""
    layouts = (result.get("preview") or {}).get("layouts", [])
    shots = pictures(result)
    pairs = paired_pictures(result)
    referenced, picked = compared(result)
    asked = questions(len(layouts) > 1, result.get("places", []), referenced, picked)
    before = befores(result)
    lines = ["# Look review", "",
             "You have not seen this game's project, its events or how it was built, and you do not need to. Judge "
             "only what the screenshots show. If a picture does not show it, answer no. Answer yes only for "
             "what a player would see as a mistake: art layered on purpose is none, such as a character in "
             "front of the ground or scenery that runs past the edge of the screen.", ""]
    if result.get("art_sheets") and shots:
        lines += [f"The last pictures, {ART_SHEET} 1 and on, are no screenshots: they are the pages of one sheet "
                  "that shows each picture of the game on its own, at its size and enlarged, the frames of one object "
                  "side by side. Ask of them what a player would see once the pictures are on screen together, taking "
                  "all the pages as one: a yes about two pictures on two pages goes on the page of either. Answer no "
                  "to a question about text or the HUD. A button or a panel drawn without words gets its label from "
                  "the game, so two of them that differ only in size are no fault.",
                  ""]
    if before:
        lines += ["A screenshot that names a picture from before the change shows the same screen as it was before "
                  "the change under review. Answer the questions about the screenshot, not about the picture from "
                  "before. After each yes on such a screenshot, write new or before: before when the picture from "
                  "before shows the same thing at the same place, new when it does not. A yes marked before does not "
                  "fail the change, so mark before only when the picture from before shows the fault; if you are not "
                  "sure, write new. A yes on a screenshot without a picture from before is new.", ""]
    if pairs:
        lines += ["A screenshot that names a pair picture belongs to a game whose look the user gave. The pair shows "
                  "on the left the user's references, each captioned reference, or the look the user picked, "
                  "captioned picked look: the game's first play screen as drawn for the pick. The screenshot is on "
                  "the right, with the colours measured from each picture under it, commonest first. A reference need "
                  "not show the same objects, layout or text. "
                  + " ".join(f"Question {asked.index(q) + 1} asks about the look of the {what} alone, and a yes to "
                             f"it names what differs." for q, what in ((REFERENCE, "references"),
                                                                       (PICKED, "picked look")) if q in asked), ""]
    lines += ["Open each screenshot" + (" and its picture from before" if before else "")
              + (" and its pair picture" if pairs else "") + " with your image tool, one at a time:", ""]
    lines += [f"{n}. {layout}: {shot}" + (f" (before the change: {before[layout]})" if layout in before else "")
              + (f" (pair picture: {pairs[layout]})" if layout in pairs else "")
              for n, (layout, shot) in enumerate(shots, 1)]
    lines += ["", "Answer every question for every screenshot, yes or no:", ""]
    lines += [f"{n}. {q}" for n, q in enumerate(asked, 1)]
    when = (" On a screenshot with a picture from before, a yes starts with new or before, then says where on the "
            "screenshot the thing is and what looks wrong." if before else
            " A yes says where on the screenshot the thing is and what looks wrong.")
    lines += ["", "Reply with one line per screenshot and question, and nothing else. Start each line with the "
                  f"screenshot's name and the question's number.{when} A no is the word alone. The form, not the "
                  "content:", "", "```"]
    first = shots[0][0] if shots else "Layout"
    lines += [f"{first} 1: no"]
    lines += ([f"{first} 2: yes, new - <where on the screenshot>: <what looks wrong>",
               f"{first} 3: yes, before - <where on the screenshot>: <what looks wrong>"] if first in before else
              [f"{first} 2: yes - <where on the screenshot>: <what looks wrong>"])
    lines += ["...", "```", ""]
    return "\n".join(lines)


def read_reply(reply: str, names: list[str],
               asked: int) -> tuple[dict[tuple[str, int], tuple[bool, str, str | None]], list[str]]:
    """The answers of a reply by screenshot and question, each yes with what it says and whether it is new or from
    before the change (None when it does not say), and the answer lines that name no screenshot or no question of
    the brief."""
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
        answers[(name, int(m["q"]))] = (m["a"].lower() == "yes", m["rest"].strip(" -:*`)"),
                                        m["when"].lower() if m["when"] else None)
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
FROM_BEFORE = "no yes is new, so the change made no fault to fix; name each yes from before in the hand-over"


def verify_command(root: Path) -> str | None:
    """verify_change.py for the project when its look step waits for these answers, else None."""
    try:
        record = json.loads((root / c3.VERIFY_RECORD).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if ((record.get("steps") or {}).get("looked") or {}).get("state") != "asked":
        return None
    return c3.script_command(root, "verify_change.py")


def check_reply(result: dict, reply: str, where: str, verify: str | None) -> tuple[list[str], int, dict]:
    """A reviewer's reply against the brief of the result: what it lacks, then every yes to fix, and the verdict
    that verify_change.py passes its look step on; verify is the command that goes on with the check chain."""
    layouts = (result.get("preview") or {}).get("layouts", [])
    names = [name for name, _ in pictures(result)]
    tiers = question_tiers(len(layouts) > 1, result.get("places", []), *compared(result))
    asked = len(tiers)
    answers, stray = read_reply(reply, names, asked)
    before = befores(result)
    missing = [(n, [q for q in range(1, asked + 1) if (n, q) not in answers]) for n in names]
    missing = [(n, qs) for n, qs in missing if qs]
    every = sorted([(n, q, said, when if n in before else "new") for n in names for q in range(1, asked + 1)
                    for yes, said, when in [answers.get((n, q), (False, "", None))] if yes],
                   key=lambda y: TIERS.index(tiers[y[1] - 1]))
    # A yes from before goes to the hand-over
    yeses = [(n, q, said) for n, q, said, when in every if when != "before"]
    from_before = [(n, q, said) for n, q, said, when in every if when == "before"]
    lines = [f"reply: {where}, against the brief of {len(names)} screenshot{'' if len(names) == 1 else 's'} and "
             f"{asked} questions: {len(names) * asked} answers asked"]
    if missing:
        lines.append("  missing: " + "; ".join(f"{n} {spans(qs)}" for n, qs in missing))
    unsaid = [f"{n} {q}" for n, q, said, _ in every if not said]
    if unsaid:
        lines.append("  yes without where: " + ", ".join(unsaid))
    untold = [f"{n} {q}" for n, q, _, when in every if when is None]
    if untold:
        lines.append("  yes without new or before: " + ", ".join(untold))
    lines += [f"  not in the brief: {line}" for line in stray]
    lines += [f"  yes, {tiers[q - 1]}: {n} {q}" + (f" - {said}" if said else "") for n, q, said in yeses]
    lines += [f"  yes from before, for the hand-over: {n} {q}" + (f" - {said}" if said else "")
              for n, q, said in from_before]
    lost = sum(len(qs) for _, qs in missing)
    lines.append(f"answers: {len(answers)} of {len(names) * asked}, {len(yeses)} yes"
                 + (f" and {len(from_before)} from before" if from_before else "") + f", {lost} missing")
    if lost or unsaid or untold:
        lines.append("next: give the reviewer the same brief again and have it answer the missing questions and say "
                     "where each yes is" + (", and whether it is new or from before" if untold else "")
                     + "; then check its reply again")
    elif yeses:
        asked = questions(len(layouts) > 1, result.get("places", []), *compared(result))
        for q, toward in ((REFERENCE, "the colours measured from the references"),
                          (PICKED, "the picked look, art/look.png")):
            if q in asked and any(n == asked.index(q) + 1 for _, n, _ in yeses):
                lines.append(f"  a yes to question {asked.index(q) + 1} is fixed in the look, not in one object: "
                             f"PALETTE, ART_STYLE and the drawings, toward {toward}")
        lines.append("next: fix each yes, the broken ones first: name the layout and the object type at the place it "
                     "describes and change it. A yes with more than one right fix, such as cutting a text short or "
                     "wrapping it, or which corner a counter takes, is the user's to pick: ask before you spend a "
                     "round on it. Write each fix in three parts for the hand-over: before, after and why; "
                     + (f"then run {verify}, which looks again; after three rounds with a yes its look step passes, "
                        f"and the hand-over names each yes left" if verify else
                        "then run review_look.py again and have its new brief answered"))
    elif verify:
        lines.append(f"next: {FROM_BEFORE if from_before else 'every question is answered no'}; run {verify}, "
                     f"which passes its "
                     f"look step on this reply")
    else:
        lines.append(f"next: {FROM_BEFORE}; the look review is done" if from_before else DONE)

    def listed(found: list[tuple[str, int, str]]) -> list[str]:
        return [f"{n} {q}, {tiers[q - 1]}" + (f" - {said}" if said else "") for n, q, said in found]
    return lines, 1 if lost or yeses else 0, {"complete": not lost and not unsaid and not untold, "yes": len(yeses),
                                              "yeses": listed(yeses), "before": listed(from_before)}


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
        lines += reference_lines(result, done["layout"])
        lines += [finding_line(f) for f in done.get("findings", [])]
        lines += [f"  unseen: the preview window did not take the screen {s}, so the layouts were not looked at on it"
                  for s in done.get("unseen", [])]
        lines += oe.runtime_lines(done["errors"])
    lines += [f"reference: {f} is not read, so no pair picture shows it: save it as PNG, JPEG or WebP"
              for f in result.get("unread_references", [])]
    if result.get("unpaired_references"):
        lines.append(f"reference: USER_LOOK is empty, so the game takes paper and ink, and no pair picture is made "
                     f"for the {result['unpaired_references']} pictures in {art.REFERENCES.as_posix()}/. If the "
                     f"user wants their look, run pick_look.py again")
    if any(shows_something(d) for d in ran["layouts"]):
        lines += before_lines(result)
        lines += ask(total > 1, result.get("places", []), *compared(result))
    return lines


def before_lines(result: dict) -> list[str]:
    """Where the pictures from before the change came from, or why there are none."""
    got = result.get("before")
    if not got:
        return []
    shots = got.get("shots", {})
    if shots:
        return [f"before: {len(shots)} layout{'' if len(shots) == 1 else 's'} as at commit {got['commit'][:12]}, "
                f"the start of the change, in {Path(next(iter(shots.values()))).parent}",
                "before: a yes from before goes into the hand-over and fails nothing"]
    return [f"before: no picture of commit {got['commit'][:12]}, the start of the change, so every yes counts as new: "
            + "; ".join(got.get("errors") or ["it showed no layout"])]


def finding_line(f: dict) -> str:
    """A finding as the run prints it: its tier, its rule, where it arose when not on the shot as it is, and what
    to change."""
    return f"  {f['tier']} {f['rule']}{' @' + f['at'] if f.get('at') else ''}: {f['line']}"


def counts(result: dict) -> tuple[int, int, int, int]:
    """Findings that fail the review, findings that warn, runtime errors and layouts visited."""
    layouts = (result.get("preview") or {}).get("layouts", [])
    found = [f for d in layouts for f in d.get("findings", [])]
    return (len(blocking(found)), len(found) - len(blocking(found)), sum(len(d["errors"]) for d in layouts),
            len(layouts))


def unpreviewed(results: list[dict]) -> list[str]:
    """The projects that opened but whose preview did not start, so that none of their layouts was looked at."""
    return [r["project"] for r in results if r["status"] == "opened" and not (r.get("preview") or {}).get("started")]


def look_line(results: list[dict], settle: float, out: Path, base: Path) -> str:
    """The count of findings, and when there is none, what the run did not see."""
    if unpreviewed(results):
        return f"look: no layout was looked at, as the preview of {', '.join(unpreviewed(results))} did not run; " \
               f"full result in {out}"
    found, warned, errors, layouts = map(sum, zip(*(counts(r) for r in results)))
    unseen = "" if found or errors else (f"; each layout ran {settle:g} s after a jump to it, without play, so a "
                                         f"scene the game reaches only in play is unseen")
    warns = f" and {warned} that warn{'s' if warned == 1 else ''}" if warned else ""
    return (f"look: {found} finding{'' if found == 1 else 's'} to fix{warns} on {layouts} "
            f"layout{'' if layouts == 1 else 's'}, {errors} runtime error{'' if errors == 1 else 's'}{unseen}; full "
            f"result in {out}, screenshots in {base}")


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
                    help="CSS pixels of the preview window, the one screen looked at (default: the project's "
                         "viewport size, then two other shapes of screen its orientations allow)")
    ap.add_argument("--data", nargs="+", choices=DATA_STATES, default=list(DATA_STATES), metavar="STATE",
                    help="the data states to look at each layout in: demo as it starts, worst, empty, one "
                         "(default: all four)")
    ap.add_argument("--release", metavar="rNNN", help="open in this release of the editor, as open_in_editor.py does")
    ap.add_argument("--browser", metavar="EXE",
                    help="the Chromium-based browser to start (default: Edge, Chrome or Chromium where installed)")
    ap.add_argument("--shots", type=Path, help="the folder for the screenshots (default: shots/ beside the result)")
    ap.add_argument("--out", type=Path, help="write the result, every instance read included, as JSON "
                                             "(default: result.json in .tmp/scripts/review-look/)")
    ap.add_argument("--design", type=Path, metavar="DESIGN.json",
                    help="the game's design (default: tools/design.json in the project, when there is one)")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    ap.add_argument("--profile", type=Path, metavar="FOLDER",
                    help="keep the browser profile in FOLDER/editor-<browser> instead of .tmp/browsers/")
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
        return reply_main(args.reply, oe.kept(args.out, args.shots, projects[0], "review-look")[0],
                          args.limit, projects[0])
    exe = args.browser or oe.browser_path()
    if not exe:
        print("no Edge, Chrome or Chromium found here, and this script needs one it can drive: install one, or open "
              "the project with open_in_editor.py --steps and take a screenshot of each layout with a browser tool "
              "of this session.")
        return 3
    editor = oe.release_url(args.release)
    out, base = oe.kept(args.out, args.shots, projects[0], "review-look")

    def visit(browser: oe.Browser) -> list[dict]:
        """Review each project in turn. Its result is written and printed as it ends, so the results stay
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
            result = oe.open_one(browser, editor, project, oe.staged(project, "review-look"), None,
                                 bool(args.release), review(args.layouts, args.settle, shapes, shots,
                                                            tuple(args.data), set_by_events(project),
                                                            declared(project)))
            result["places"] = unmeasured(project, args.design)
            # Names this run, so that a reply checked against its brief is not taken for one of a later run
            result["run"] = uuid.uuid4().hex[:12]
            if sheets := art.sheet_pages(project):
                result["art_sheets"] = [str(p) for p in sheets]
            commit = before_commit(project)
            if commit and any(shows_something(d) for d in (result.get("preview") or {}).get("layouts", [])):
                key = {"layouts": args.layouts, "settle": args.settle, "screen": shapes[0][1]}
                result["before"] = before_shots(project, commit, key, lambda copy, into: oe.open_one(
                    browser, editor, copy, oe.staged(copy, "review-look"), None, bool(args.release),
                    review(args.layouts, args.settle, shapes[:1], into, ("demo",), set(), {})))
            refs, unread = art.references(project)
            if unread:
                result["unread_references"] = [str(p) for p in unread]
            # The look the user picked on the first play screen, held to the start layout's screenshot
            look = project / art.image_route.LOOK if cl.user_look(project) else None
            look = look if look and look.is_file() else None
            # The user picked paper and ink over the look of the references, so the screen is meant to differ
            if refs and (project / c3.GENERATOR).is_file() and not cl.user_look(project):
                result["unpaired_references"] = len(refs)
            elif (refs or look) and any(shows_something(d) for d in (result.get("preview") or {}).get("layouts", [])):
                result["references"] = reference_pairs(project, exe, result, shots, look)
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
    found, _, errors, _ = map(sum, zip(*(counts(r) for r in results)))
    print(look_line(results, args.settle, out, base))
    if any(r["status"] != "opened" for r in results):
        print(oe.NEXT)
        return 1
    if unpreviewed(results):
        print("next: the preview did not run, so no layout was looked at and nothing passed; run this again, and if "
              "the preview stops again, run open_in_editor.py --preview, whose lines say why")
        return 3
    briefs = [r["brief"] for r in results if r.get("brief")]
    print("next: fix every broken finding, then every ugly one; a fragile one warns, so fix it or name it in the "
          "hand-over. A runtime error on a layout reached straight away may need the run that leads there, so play "
          "to it with preview_project.py before blaming the events. Then have the questions answered and fix each "
          "yes. Run this again until it prints no finding to fix and every answer is no.")
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
