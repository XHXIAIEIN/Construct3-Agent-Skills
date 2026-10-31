"""Preview a project in the Construct 3 editor and play it from a plan: tap, hold
and drag the game's own instances, press keys, wait for what the events do, run
scripts against the runtime, and read the state, take screenshots and record between steps.

Use it to check what a player does: a merge, a drop, a jump, a purchase. The
plan is JSON, the steps run in order, and a step that fails stops the run:

  {"viewport": [430, 932], "touch": true,
   "steps": [
     {"until": "runtime.objects.Enemy.getAllInstances().length >= 3", "timeout": 10},
     {"js": "runtime.callFunction('finishTutorial')"},
     {"tap": "StartButton"},
     {"drag": "Piece 0", "to": "BattleSlot 1", "seconds": 0.4},
     {"drag": "Ball", "through": [{"x": 300, "y": 200}], "to": "Ball", "seconds": 0.8},
     {"drag": "Card", "to": {"x": 215, "y": 100}, "seconds": 0.15, "rest": 0},
     {"hold": {"x": 40, "y": 600, "layer": "UI"}, "seconds": 1},
     {"key": "ArrowRight", "seconds": 0.5},
     {"key": ["ShiftLeft", "ArrowRight"], "seconds": 0.5},
     {"wait": 1.5, "note": "the merge animation"},
     {"state": ["Piece", "BattleSlot"]},
     {"shot": "after-merge"}]}

viewport     CSS pixels of the preview window, [width, height]; a phone's is 430 x 932 (default: the editor's)
touch        taps, holds and drags as touches instead of the mouse (default: false)
keep_saves   start from what earlier runs saved in Local Storage and IndexedDB (default: false)
pixel_ratio  device pixels per CSS pixel, 2 or 3 for a phone; screenshots come out at that scale (default: 1)

Steps, each an object with one of these keys, and "note" for a label:
  tap TARGET                    press and release
  hold TARGET, seconds          press, wait, release (default 0.5 s)
  drag TARGET, to TARGET, seconds, through, rest
                                press, move in steps, release (default 0.4 s); through is a list of
                                TARGETs passed on the way, and rest the seconds the pointer stays still
                                on "to" before the release (default 0.05; 0 for a flick)
  move TARGET, seconds, through, rest
                                a drag with no button, a hover, from where the pointer is; rest 0; no touch
  key NAME or [NAME, ...], seconds
                                press a key for the time (default 0.1 s): ArrowLeft, Space, Enter, Escape,
                                KeyA or a, Digit1 or 1, ShiftLeft; a list holds the keys together
  wait SECONDS                  let the game run
  until EXPRESSION, timeout     wait until the JavaScript expression is true (default 10 s)
  js CODE                       run JavaScript against the runtime and print what it returns
  state [TYPE ...]              the globals, every type's count, the named types' instances with
                                their inspector values, named in --locale
  shot NAME                     a screenshot, NN-NAME.png in --shots; named as not drawn yet when it
                                is one colour and flat
  record NAME, watch, fps, expect, ask
                                record from here to the next record step or the end: NN-NAME.mp4 with
                                ffmpeg or .gif with Pillow, the frames, a contact sheet of up to 12
                                numbered frames, and NN-NAME.html to review it; watch is
                                {"label": EXPRESSION, ...}, read at every frame; fps 60 makes the video
                                60 frames a second of game time, for a game that a js step slowed with
                                runtime.timeScale; false stops; expect {"works": [...], "broken": [...]}
                                and open questions in ask write a brief of the frames for a reviewer

TARGET is where to press, the middle of an instance's bounding box:
  "Button"                      the first instance of an object type, as the project spells it
  "Piece 2"                     its instance of index 2, in creation order
  "uid 12"                      an instance by UID
  {"x": 40, "y": 600, "layer": "UI"}   a position on a layer (default: the layout's first layer)
  {"js": "CODE"}                JavaScript that returns an instance, a UID, or {x, y, layer}

CODE and EXPRESSION see `runtime`, the scripting API (IRuntime), `vars`, an object
kept from step to step, and `wait(seconds)`. A single expression is returned as it
is; longer code says `return`. A list of strings is joined into lines.

The game starts on the layout the editor opens on, as with F5. A game that reloads
its page goes on in the new page: the step the reload broke off runs again, except
a js step whose code had started, which fails.

The browser runs headless and silent; --headed shows it. A failed step leaves
NN-failed.png. Screenshots and recordings go to --shots (default
.tmp/scripts/preview-project/shots/ in the project), the whole result to --out
(default result.json beside it); the last line names both, so read a cut-off
result there instead of playing the plan again.

A plan that passes is kept with --keep NAME as tools/plans/NAME.json in the project,
committed with the change it checks; it needs an until after an input or wait. --all
replays each kept plan from a first launch, into .tmp/scripts/preview-project/plans.json.

The result is what open_in_editor.py writes, plus "preview": {"started", "layout", "runtime",
"viewport", "pixel_ratio", "touch", "seconds", "planned", "errors", "recorded", "steps": [{"step",
"line", "ok", "said", "errors", "layout", "value" of a js step, "state" of a state step, "reloaded"}]}.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

# python -I leaves this script's folder off sys.path, and the modules beside it are imported from there
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import c3project as c3
import open_in_editor as oe

EPILOG = """examples:
  python scripts/preview_project.py .tmp/drafts/merge-plan.json
  python scripts/preview_project.py .tmp/drafts/merge-plan.json --keep merge-two-pieces
  python scripts/preview_project.py --all

output:
  opened   <project>  (<window title>, <the editor it opened in>)
    warning: <a notice the editor showed, as open_in_editor.py prints it>
    preview: layout 'Game', runtime in the worker, viewport 430x932, touch
    1 until runtime.objects.Enemy.getAllInstances().length >= 3: true after 1.4 s
    2 drag Piece 0 to BattleSlot 1: (120, 712) to (215, 388) in 0.4 s
      runtime: <an error the game logged in the step, with its event, and (N times) if it repeated>
    3 key ShiftLeft+ArrowRight: held 0.5 s
    4 state Piece: <as open_in_editor.py --state prints it>
    5 shot after-merge: shots/05-after-merge.png
    recorded merge: 95 frames in 3.4 s, shots/02-merge.mp4
      sheet shots/02-merge-sheet.png: 10 frames, numbered left to right, top down: 1 at 0 ms (start),
      2 at 35 ms (largest change), ..., 10 at 3380 ms (end)
      brief: <who answers shots/described-3f9a1c2e4b/brief.md>
      review shots/02-merge.html: <where the user plays it>; shots/index.html lists every recording
      frames and timeline.json in shots/02-merge
      watch coins: 40 at 0 ms, 30 at 900 ms
    ran: 5 of 5 steps in 9.6 s, 1 runtime error

--all prints one line per kept plan instead of its steps:
    ok    merge-two-pieces: 6 steps, 2 until checks in 4.1 s
    FAIL  hint-after-idle (tools/plans/hint-after-idle.json): step 3 until ...: FAILED, false after 10 s
  replayed: 1 of 2 kept plans pass with 2 until checks, no runtime errors

exit codes: 0 every step ran and the game logged no error (--all: in every kept plan); 1 a step failed, the
game logged an error or a request failed, or the project did not open; 2 the plan, the project, the editor
or --locale could not be used, or --all found no kept plan; --reply: 0 all answered, 1 one is not, 2 no
reply or brief; 3 no browser here; 5 another run holds the
browser profile, named in the line with its pid: wait for it to end, or pass --profile for a profile of
this run's own
"""

STEPS = ("tap", "hold", "drag", "move", "key", "wait", "until", "js", "state", "shot", "record")
# Where a project keeps the plans that passed, one per change they checked.
KEPT = Path("tools") / "plans"
FIELDS = {"tap": set(), "hold": {"seconds"}, "drag": {"to", "seconds", "through", "rest"},
          "move": {"seconds", "through", "rest"}, "key": {"seconds"}, "wait": set(),
          "until": {"timeout"}, "js": {"timeout"}, "state": set(), "shot": set(),
          "record": {"watch", "fps", "expect", "ask"}}
# Seconds a hold, a drag, a move and a key press last when the step gives none.
PRESS = {"hold": 0.5, "drag": 0.4, "move": 0.4, "key": 0.1}
# Seconds the preview window gets to take the plan's viewport.
RESIZE = 5
# Seconds a page the game reloaded gets to run its runtime again.
RELOAD = 30
# Seconds the game's page or worker gets to answer after a step; past them its thread is held.
ANSWER = 5
# Seconds between two ticks past which a step fails, the game having stopped. In previews of 12
# official examples and a converted game on a 143 Hz display, the longest gap over 78 changes of
# layout was 0.27 s, as a layout with many objects started; within a running layout 0.05 s, and
# while screenshots were taken one after another as a record step takes them 0.014 s.
STALL = 1.0
FROZEN = (f"the game stopped answering for {ANSWER} s: an endless loop in its events or a script holds its thread, "
          f"such as a While whose condition stays true or a function that calls itself; find the loop and give it "
          f"an end")
# Where the editor serves a preview, and where a game's saves live.
PREVIEW = "https://preview.construct.net"
# The page that reviews a recording, its timeline put where it says TIMELINE.
REVIEW = (c3.SKILL_DIR / "assets" / "recording-review.html").read_text(encoding="utf-8")

# Left in the session that runs the game, after the probe: where a target is on the
# page, and what a step's code returns, as JSON. layerToCssPx gives the client
# position an input event of the page carries.
PLAY_JS = r"""(() => {
  if (globalThis.c3play) return true;
  const runtime = c3probe.runtime;
  const types = () => Object.keys(runtime.objects);
  const find = spec => {
    if (typeof spec === 'number') return runtime.getInstanceByUid(spec) || {error: `no instance has UID ${spec}`};
    const uid = /^uid\s+(\d+)$/i.exec(spec);
    if (uid) return runtime.getInstanceByUid(+uid[1]) || {error: `no instance has UID ${uid[1]}`};
    const [, name, index] = /^(.*?)(?:\s+(\d+))?$/.exec(spec.trim());
    const type = runtime.objects[name];
    if (!type) return {error: `no object type ${name}`, name, types: types()};
    const all = type.getAllInstances(), i = Number(index || 0);
    return all[i] || {error: `${name} has ${all.length} instance${all.length == 1 ? '' : 's'}, none of index ${i}`};
  };
  globalThis.c3play = {
    vars: {},
    wait: s => new Promise(r => setTimeout(r, s * 1000)),
    aim(spec) {
      let inst = spec;
      if (typeof spec === 'string' || typeof spec === 'number') inst = find(spec);
      if (inst && inst.error) return inst;
      if (inst && typeof inst.getBoundingBox === 'function') {
        const box = inst.getBoundingBox(), [x, y] = inst.layer.layerToCssPx(box.x + box.width / 2, box.y + box.height / 2);
        return {x, y, uid: inst.uid};
      }
      if (inst && typeof inst.x === 'number' && typeof inst.y === 'number') {
        const layer = inst.layer === undefined ? runtime.layout.getLayer(0) : runtime.layout.getLayer(inst.layer);
        if (!layer) return {error: `the layout ${runtime.layout.name} has no layer ${inst.layer}`};
        const [x, y] = layer.layerToCssPx(inst.x, inst.y);
        return {x, y};
      }
      return {error: `the target is ${JSON.stringify(inst) ?? String(inst)}: give an instance, a UID or {x, y, layer}`};
    },
    plain(v) {
      if (v && typeof v.getBoundingBox === 'function')
        return {uid: v.uid, type: v.objectType.name, x: v.x, y: v.y};
      if (Array.isArray(v)) return v.map(c3play.plain);
      try { return JSON.parse(JSON.stringify(v ?? null)); } catch (e) { return String(v); }
    },
  };
  return true;
})()"""

# A js step that failed so: its code never started, the page having reloaded before it.
NOT_STARTED = re.compile(r"ReferenceError: c3(probe|play) is not defined")

# The key, its code and the Windows key code a keyboard event carries.
NAMED_KEYS = {"ArrowLeft": 37, "ArrowUp": 38, "ArrowRight": 39, "ArrowDown": 40, "Space": 32, "Enter": 13,
              "Escape": 27, "Tab": 9, "Backspace": 8, "ShiftLeft": 16, "ShiftRight": 16, "ControlLeft": 17,
              "ControlRight": 17, "AltLeft": 18, "AltRight": 18}
# A modifier's code, its key and the side of the keyboard it is on, the protocol's location
SIDES = {f"{key}{side}": (key, location) for key in ("Shift", "Control", "Alt")
         for side, location in (("Left", 1), ("Right", 2))}


def key_event(name: str) -> dict | None:
    """What Input.dispatchKeyEvent needs for a key named by its code or its character."""
    if name in NAMED_KEYS:
        key, location = SIDES.get(name, (" " if name == "Space" else name, 0))
        return {"key": key, "code": name, "windowsVirtualKeyCode": NAMED_KEYS[name],
                **({"location": location} if location else {}), **({"text": " "} if key == " " else {})}
    char = name[-1] if (name.startswith("Key") or name.startswith("Digit")) and len(name) in (4, 6) else name
    if len(char) == 1 and char.isalnum():
        code = f"Key{char.upper()}" if char.isalpha() else f"Digit{char}"
        return {"key": char.lower(), "code": code, "windowsVirtualKeyCode": ord(char.upper()), "text": char.lower()}
    return None


def key_names(value: object) -> list:
    """The keys a key step holds together: one name, or a list of names."""
    return value if isinstance(value, list) else [value]


# The bit of the DevTools protocol's "modifiers" that a held key adds to each key event.
MODIFIERS = {"Alt": 1, "Control": 2, "Shift": 8}


def modifiers(held: list[dict]) -> int:
    """The modifiers value of a key event sent while the keys of `held` are down."""
    bits = 0
    for event in held:
        bits |= MODIFIERS.get(event["key"], 0)
    return bits


def statements(line: str) -> bool:
    """Whether a line holds a `;` outside brackets and strings, so more than one statement."""
    depth, quote, escaped = 0, "", False
    for ch in line:
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = ""
        elif ch in "'\"`":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == ";" and depth == 0:
            return True
    return False


def code(text: str | list[str]) -> str:
    """The body of an async function: a single expression is returned as it is."""
    body = "\n".join(text) if isinstance(text, list) else text
    one = body.strip().rstrip(";")
    if "\n" not in one and not statements(one) and \
            not one.startswith(("return ", "return;", "const ", "let ", "var ", "if ", "for ", "while ", "throw ")):
        return f"return ({one});"
    return body


def scope(text: str | list[str]) -> str:
    """A step's code as an async function of no arguments, with what the code sees."""
    return ("(async () => { const runtime = c3probe.runtime, vars = c3play.vars, wait = c3play.wait;\n"
            f"{code(text)}\n}})")


def check_plan(plan: object) -> tuple[dict, list[str]]:
    """The plan as {viewport, touch, steps}, and what is wrong with it."""
    problems: list[str] = []
    if isinstance(plan, list):
        plan = {"steps": plan}
    if not isinstance(plan, dict) or not isinstance(plan.get("steps"), list) or not plan["steps"]:
        return {}, ['the plan is {"steps": [...]} or a list of steps, with at least one step']
    for extra in set(plan) - {"steps", "viewport", "touch", "keep_saves", "pixel_ratio"}:
        problems.append(f"the plan has {extra!r}; it takes steps, viewport, touch, keep_saves and pixel_ratio")
    view = plan.get("viewport")
    if view is not None and not (isinstance(view, list) and len(view) == 2 and all(isinstance(n, int) and n > 0
                                                                                   for n in view)):
        problems.append("viewport is [width, height] in CSS pixels, such as [430, 932]")
    ratio = plan.get("pixel_ratio", 1)
    if not (isinstance(ratio, (int, float)) and not isinstance(ratio, bool) and 0 < ratio <= 4):
        problems.append("pixel_ratio is device pixels per CSS pixel, a number up to 4, such as 2")
    for n, step in enumerate(plan["steps"], 1):
        kinds = [k for k in STEPS if isinstance(step, dict) and k in step]
        if len(kinds) != 1:
            near = "".join(c3.closest(k, STEPS) for k in step) if isinstance(step, dict) and not kinds else ""
            problems.append(f"step {n} has {'none' if not kinds else ' and '.join(kinds)} of {', '.join(STEPS)}; "
                            f"give one{near}")
            continue
        kind = kinds[0]
        for extra in set(step) - {kind, "note"} - FIELDS[kind]:
            problems.append(f"step {n} ({kind}) has {extra!r}{c3.closest(extra, FIELDS[kind] | {'note'})}")
        value = step[kind]
        if kind in ("tap", "hold", "drag", "move") and not target_ok(value):
            problems.append(f"step {n} ({kind}): the target is a type name, \"Type 2\", \"uid 12\", "
                            f"{{\"x\": .., \"y\": .., \"layer\": ..}} or {{\"js\": ..}}")
        if kind == "drag" and not target_ok(step.get("to")):
            problems.append(f"step {n} (drag) needs \"to\", a target like the one it drags")
        if kind in ("drag", "move") and "through" in step and not (
                isinstance(step["through"], list) and step["through"] and all(map(target_ok, step["through"]))):
            problems.append(f"step {n} ({kind}): through is a list of targets like the one it "
                            + ("drags" if kind == "drag" else "moves to"))
        if kind == "move" and plan.get("touch"):
            problems.append(f"step {n} (move) moves the mouse with no button held, and a touch plan has no mouse: a "
                            f"finger cannot hover, so play the hover in a plan without \"touch\"")
        if kind == "key":
            names = key_names(value)
            wrong = [k for k in names if not (isinstance(k, str) and key_event(k))]
            if wrong or not names:
                what = (f"{', '.join(map(repr, wrong))} {'is not a key' if len(wrong) == 1 else 'are not keys'} this "
                        f"script presses" if wrong else "the list is empty")
                problems.append(f"step {n} (key): {what}; a key is a letter (a or KeyA), a digit (1 or Digit1) or one "
                                f"of {', '.join(NAMED_KEYS)}, and a list of keys holds them together")
            elif len({key_event(k)["code"] for k in names}) < len(names):
                problems.append(f"step {n} (key) names a key twice: {value!r}; list each key once (a and KeyA are "
                                f"one key)")
        if kind == "wait" and not (isinstance(value, (int, float)) and value >= 0):
            problems.append(f"step {n} (wait) takes seconds, a number")
        if kind in ("until", "js") and not (isinstance(value, str) or isinstance(value, list) and value
                                            and all(isinstance(v, str) for v in value)):
            problems.append(f"step {n} ({kind}) takes JavaScript, a string or a list of lines")
        if kind == "state" and not (isinstance(value, list) and all(isinstance(v, str) for v in value)
                                    or isinstance(value, str)):
            problems.append(f"step {n} (state) takes the object types to list, [] for counts only")
        if kind in ("shot", "record") and not (isinstance(value, str) and value
                                               and all(c.isalnum() or c in "-_" for c in value)
                                               or kind == "record" and value is False):
            problems.append(f"step {n} ({kind}) takes a file name of letters, digits, - and _"
                            + (", or false to stop" if kind == "record" else ""))
        watch = step.get("watch") if kind == "record" else None
        if watch is not None and not (value and isinstance(watch, dict) and watch and all(
                isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in watch.items())):
            problems.append(f"step {n} (record): watch is {{\"label\": \"EXPRESSION\", ...}} on a step that starts "
                            f"a recording")
        fps = step.get("fps") if kind == "record" else None
        if fps is not None and not (value and isinstance(fps, (int, float)) and not isinstance(fps, bool)
                                    and 0 < fps <= 240):
            problems.append(f"step {n} (record): fps is frames per second of game time, up to 240, on a step that "
                            f"starts a recording")
        if kind == "record":
            problems += [f"step {n} (record): {p}" for p in described(step)]
        for field in ("seconds", "timeout", "rest"):
            if field in step and not (isinstance(step[field], (int, float)) and step[field] >= 0):
                problems.append(f"step {n} ({kind}): {field} is a number of seconds")
    return plan, problems


# A question that a yes or a no answers, which tells the reviewer what to look for
CLOSED = re.compile(r"^(is|are|was|were|do|does|did|can|could|will|would|should|has|have|had)\b|吗[?？]?$", re.I)


def described(step: dict) -> list[str]:
    """What is wrong with the expect and ask of a record step: what the frames would show if the change works and
    if it does not, written before the run, and open questions for a reviewer that sees only the frames."""
    expect, ask = step.get("expect"), step.get("ask")
    if expect is None and ask is None:
        return []
    if not step["record"]:
        return ["expect and ask go on a step that starts a recording"]
    problems = []
    if not (isinstance(expect, dict) and set(expect) == {"works", "broken"} and all(
            isinstance(v, list) and v and all(isinstance(t, str) and t.strip() for t in v) for v in expect.values())):
        problems.append('expect is {"works": [...], "broken": [...]}, each a list of what a frame would show, such as '
                        '"the bar\'s right edge moves right over several frames and stops", written before the run')
    if not (isinstance(ask, list) and ask and all(isinstance(q, str) and q.strip() for q in ask)):
        problems.append('ask is a list of open questions about the frames, such as "What moves between the frames, '
                        'which way and how far?"')
    else:
        problems += [f"ask: {q!r} is answered yes or no and tells the reviewer what to look for; ask what is there: "
                     f"what moves and which way, what is at a place, what a text says" for q in ask
                     if CLOSED.search(q.strip())]
    return problems


def target_ok(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return set(value) == {"js"} and isinstance(value["js"], (str, list)) or \
            {"x", "y"} <= set(value) <= {"x", "y", "layer"} and all(isinstance(value[k], (int, float)) for k in "xy")
    return False


def target_text(value: str | dict) -> str:
    if isinstance(value, str):
        return value
    if "js" in value:
        return "{js}"
    return f"({value['x']}, {value['y']}) on {value.get('layer', 'the first layer')}"


class Game:
    """A running preview: the window's page for input and screenshots, the session
    that runs the game for code."""

    def __init__(self, win: oe.DevTools, live: str | None, touch: bool, size: tuple[int, int], url: str,
                 viewport: list[int] | None, project: Path, ratio: float = 1) -> None:
        self.win, self.live, self.touch, self.size, self.url, self.viewport = win, live, touch, size, url, viewport
        self.project, self.ratio = project, ratio
        self.recording: Recorder | None = None
        self.recorded: list[Recorder] = []      # finished, their connections closed after the window (Recorder)
        self.pointer: tuple[float, float] | None = None     # where the last mouse event put the pointer

    def record(self, name: str, video: Path, watch: dict[str, str], fps: float | None, asked: dict) -> None:
        self.recording = Recorder(self.url, name, video, self.viewport, watch, self.project, self.ratio, fps, asked)

    def stop_recording(self) -> str:
        """What the recording that ran made, or "" when none ran."""
        if not self.recording:
            return ""
        recorder, self.recording = self.recording, None
        self.recorded.append(recorder)
        return f"recorded {recorder.name}: {recorder.finish()}"

    def close(self) -> None:
        for recorder in self.recorded:
            recorder.page.ws.close()

    def run(self, js: str, wait: float = 60) -> Any:
        return self.win.evaluate(js, wait=wait, session=self.live)

    def reloaded(self) -> float | None:
        """None while the page the probe was left in still runs. After the game
        reloaded its page (Browser *Reload*), the probe and c3play are left again in
        the new page once its runtime ticks, and the seconds that took are returned.
        Raises StepFailed when no runtime ticks in the new page, or when the page or
        worker that runs the game is there and does not answer: its thread is held.
        The answer is also what the errors a step caused arrive before."""
        try:
            if self.run("typeof c3play === 'object'", wait=ANSWER):
                return None
        except oe.NoAnswer:
            raise StepFailed(FROZEN) from None
        except oe.DevToolsError:    # the page's context or the worker went with the reload
            pass
        began = time.monotonic()
        sessions, live, stalled = oe.attach(self.win, patience=RELOAD)
        if not live:
            raise StepFailed("the page reloaded, and " + ("its runtime did not tick for 3 seconds" if stalled else
                                                          f"no runtime ran in it in {RELOAD} seconds"))
        self.live = live[0]
        self.win.evaluate(PLAY_JS, session=self.live)
        enable(self.win, sessions)
        if self.recording and self.recording.read:
            self.recording.session = self.recording.game_session()
        return time.monotonic() - began

    def pulse(self) -> dict | None:
        """The layout that runs, and the ticks since the last call (runtime-probe.js ticks()):
        None while the game's page reloads. Raises StepFailed when the game does not answer."""
        try:
            return self.run("({...c3probe.ticks(), layout: c3probe.runtime.layout.name})", wait=ANSWER)
        except oe.NoAnswer:
            raise StepFailed(FROZEN) from None
        except oe.DevToolsError:    # the page reloads; reloaded() leaves the probe again after the next step
            return None

    def aim(self, target: str | dict) -> tuple[float, float]:
        if isinstance(target, dict) and "js" in target:
            got = self.run(f"(async () => c3play.aim(await {scope(target['js'])}()))()")
        else:
            got = self.run(f"c3play.aim({json.dumps(target)})")
        if not isinstance(got, dict) or "error" in got:
            error = got.get("error") if isinstance(got, dict) else f"the target gave {got!r}"
            if isinstance(got, dict) and got.get("types"):
                error += c3.closest(got["name"], got["types"])
            raise StepFailed(error)
        x, y = got["x"], got["y"]
        if not (0 <= x < self.size[0] and 0 <= y < self.size[1]):
            raise StepFailed(f"{target_text(target)} is at ({x:.0f}, {y:.0f}), outside the window, "
                             f"{self.size[0]}x{self.size[1]}: it is off screen, or the layer scrolled")
        return x, y

    def mouse(self, kind: str, x: float, y: float, down: bool) -> None:
        extra = {"button": "left", "clickCount": 1} if kind != "mouseMoved" else {"button": "left"} if down else {}
        self.win.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, buttons=1 if down else 0, **extra)
        self.pointer = (x, y)

    def finger(self, kind: str, x: float = 0, y: float = 0) -> None:
        points = [] if kind == "touchEnd" else [{"x": x, "y": y, "id": 1}]
        self.win.call("Input.dispatchTouchEvent", type=kind, touchPoints=points)

    def press(self, x: float, y: float) -> None:
        if self.touch:
            self.finger("touchStart", x, y)
        else:
            self.mouse("mouseMoved", x, y, False)
            self.mouse("mousePressed", x, y, True)

    def move(self, x: float, y: float) -> None:
        if self.touch:
            self.finger("touchMove", x, y)
        else:
            self.mouse("mouseMoved", x, y, True)

    def release(self, x: float, y: float) -> None:
        if self.touch:
            self.finger("touchEnd")
        else:
            self.mouse("mouseReleased", x, y, False)


class Recorder(threading.Thread):
    """Screenshots of the window, one after another, on a connection of its own while
    the steps run, each with the game time and the values the record step watches,
    read right after it.
    The browser's screencast sends no frame, or a strip, once the window's size is
    emulated. This connection emulates the plan's viewport too, since one without an
    emulated size of its own takes a headed window's screenshots at the display's
    scale; and it stays open until the window closes, since closing a connection
    that emulated a size clears the size for the page, the steps' connection included."""

    def __init__(self, url: str, name: str, video: Path, viewport: list[int] | None, watch: dict[str, str],
                 project: Path, ratio: float = 1, fps: float | None = None, asked: dict | None = None) -> None:
        super().__init__(name=name, daemon=True)
        self.video, self.folder, self.project, self.fps = video, video.with_suffix(""), project, fps
        self.asked = asked or {}
        self.frames, self.steps, self.done, self.first = [], [], threading.Event(), threading.Event()
        shutil.rmtree(self.folder, ignore_errors=True)
        self.folder.mkdir(parents=True)
        self.page = oe.DevTools(url)
        if viewport or ratio != 1:
            emulate(self.page, viewport, ratio)
        self.session, self.watch, self.read = None, bool(watch), None
        if watch or fps:
            self.session = self.game_session()
            body = ", ".join(f"[{json.dumps(label)}, await read(async () => ({expression}))]"
                             for label, expression in watch.items())
            self.read = ("(async () => { const runtime = c3probe.runtime, vars = c3play.vars;\n"
                         "  const read = async f => { try { return c3play.plain(await f()); }"
                         " catch (e) { return `error: ${e.message}`; } };\n"
                         f"  return {{game: runtime.gameTime, watch: Object.fromEntries([{body}])}}; }})()")
        self.start()
        self.first.wait(5)      # the next step starts after the state before it is on record

    def game_session(self) -> str | None:
        """The page or the worker where the probe was left: the same globals as the
        steps see, through this connection."""
        self.page.call("Target.setAutoAttach", autoAttach=True, waitForDebuggerOnStart=False, flatten=True)
        workers = [e["params"]["sessionId"] for e in self.page.events if e["method"] == "Target.attachedToTarget"
                   and e["params"]["targetInfo"]["type"] == "worker"]
        for session in [None, *workers]:
            try:
                if self.page.evaluate("typeof c3probe === 'object'", wait=3, session=session):
                    return session
            except oe.DevToolsError:
                pass
        return None

    def run(self) -> None:
        try:
            while not self.done.is_set():
                taken = time.monotonic()
                shot = self.page.call("Page.captureScreenshot", format="jpeg", quality=70, optimizeForSpeed=True)
                frame = {"file": f"{len(self.frames) + 1:04d}.jpg", "t": taken}
                if self.read:
                    try:
                        got = self.page.evaluate(self.read, wait=5, session=self.session)
                        frame["game"] = got["game"]
                        if self.watch:
                            frame["watch"] = got["watch"]
                    except oe.DevToolsError as e:
                        if self.watch:
                            frame["watch"] = {"error": str(e).splitlines()[0]}
                (self.folder / frame["file"]).write_bytes(base64.b64decode(shot["data"]))
                self.frames.append(frame)
                self.first.set()
        except (oe.DevToolsError, OSError):     # the window closed
            return

    def finish(self) -> str:
        """Stop, and leave the frames, the timeline, a video and the review page: what
        to print about them."""
        self.done.set()
        self.join(10)
        frames = self.frames
        if not frames:
            return f"no frames: the window answered no screenshot; {self.folder} is empty"
        start = frames[0]["t"]
        seconds = [max(b["t"] - a["t"], 0.001) for a, b in zip(frames, frames[1:])] + [0.05]
        paths = [self.folder / f["file"] for f in frames]
        game = game_frames(frames, self.fps) if self.fps else None
        made = make_video([paths[i] for i in game["shots"]], self.video, fps=self.fps) if game else \
            make_video(paths, self.video, seconds)
        timeline = {"name": self.name, "folder": self.folder.name, "path": self.folder.resolve().as_posix(),
                    "project": self.project.resolve().as_posix(), "video": made,
                    "frames": [{**f, "t": round(f["t"] - start, 3)} for f in frames],
                    "steps": [{**s, "start": round(s["start"] - start, 3), "end": round(s["end"] - start, 3)}
                              for s in self.steps]}
        if game:
            timeline["game_video"] = {"fps": self.fps, "start": game["start"],
                                      "frames": [frames[i]["file"] for i in game["shots"]]}
        (self.folder / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1), encoding="utf-8")
        page = self.video.with_suffix(".html")
        page.write_text(REVIEW.replace("/*TIMELINE*/null", script_json(timeline)), encoding="utf-8")
        index = write_index(self.video.parent)
        said = game_lines(game, self.fps, seconds) if game else [
            "no frame of game time passed, or the game time was not read, so the video keeps the clock: "
            if self.fps else ""]
        lines = [f"{len(frames)} frames in {sum(seconds):.1f} s, {said[0]}"
                 f"{made or 'no ffmpeg or Pillow here to join them'}", *said[1:], *tick_lines(self.steps)]
        cells = sheet_frames(timeline["frames"], timeline["steps"], frame_change(paths, timeline["frames"]))
        sheet = make_sheet([paths[i] for i, _ in cells], [timeline["frames"][i]["t"] for i, _ in cells],
                           self.folder.with_name(self.folder.name + "-sheet.png"))
        if sheet:
            listed = ", ".join(f"{k} at {round(timeline['frames'][i]['t'] * 1000)} ms" + (f" ({why})" if why else "")
                               for k, (i, why) in enumerate(cells, 1))
            lines.append(f"sheet {sheet}: {len(cells)} frames, numbered left to right, top down: {listed}")
        if self.asked:
            lines += self.write_brief([(paths[i], timeline["frames"][i]["t"]) for i, _ in cells])
        elif sheet:
            lines.append("  to judge what these frames show, give this record step expect and ask and play it again: "
                         "the run then writes a brief for a reviewer that has not seen the change")
        lines += [f"review {page}: the user plays it there, selects the part that looks wrong and copies it to you "
                  f"as a task; {index} lists every recording",
                  f"frames and timeline.json in {self.folder}"]
        return "\n    ".join(lines + watch_lines(timeline["frames"]))

    def write_brief(self, frames: list[tuple[Path, float]]) -> list[str]:
        """brief.md and copies of the sheet's frames in a folder of their own, with the step's questions and
        nothing of what the frames should show, and the expectations beside that folder for --reply: what to print
        about them. The folder's name is a hash of the recording's, since the reviewer reads the frames' paths and
        the recording's name says what it checks."""
        asked = [*self.asked["ask"], LAST_QUESTION]
        named = hashlib.sha1(self.folder.resolve().as_posix().encode()).hexdigest()[:10]
        blind = self.folder.with_name(f"described-{named}")
        shutil.rmtree(blind, ignore_errors=True)
        blind.mkdir(parents=True)
        copies = []
        for k, (path, t) in enumerate(frames, 1):
            copies.append((blind / f"{k:02d}{path.suffix}", t))
            shutil.copyfile(path, copies[-1][0])
        brief, reply = blind / "brief.md", blind / "reply.md"
        brief.write_text(describe_brief(copies, asked), encoding="utf-8")
        blind.with_name(blind.name + EXPECT).write_text(json.dumps(
            {"recording": self.folder.resolve().as_posix(), "brief": brief.resolve().as_posix(), "ask": asked,
             "expect": self.asked["expect"]}, ensure_ascii=False, indent=1), encoding="utf-8")
        check = c3.script_command(self.project, "preview_project.py", f" --reply {c3.quoted(reply.resolve().as_posix())}")
        return [f"described: {brief.resolve()} holds {len(frames)} frames and {len(asked)} questions, and nothing of "
                f"the change or of what the frames should show",
                f"brief: if you can start a sub-agent, give it {brief.resolve()} as its whole task and tell it nothing "
                f"of the game or the change; save its reply to {reply.resolve()} and check it with {check}. Otherwise "
                f"open each frame it lists with the image tool and answer its questions from the frames alone, before "
                f"you read the plan's expect again"]


# The question every description of a recording ends with, so that a change it was not asked about shows too
LAST_QUESTION = "What else moves or changes between the frames, and what stays still?"
# Beside a recording's folder: its questions and what the plan said the frames would show, which --reply prints
EXPECT = "-expect.json"
# An answer that says it cannot see what it was asked about, in the words the brief gives for it
UNSEEN = re.compile(r"can(?:no|')t make out|unreadable", re.I)
# The start of an answer in a reply: its question's number, then a colon, a full stop or a bracket
ANSWER_START = re.compile(r"^[\W_]*(?:q(?:uestion)?\s*)?(\d+)\s*[:.)]\s*(.*)$", re.I)


def describe_brief(frames: list[tuple[Path, float]], asked: list[str]) -> str:
    """The task of a reviewer that sees only the frames: the frames by absolute path and time, the questions and
    the form of the answer."""
    lines = ["# Frames to describe", "",
             "These are frames of a video game, taken one after another while it ran. You are not told what anyone "
             "is checking in them, and you do not guess it: say what is visible, as exactly as you can.", "",
             "Open each frame with your image tool, in order:", ""]
    lines += [f"{k}. at {round(t * 1000)} ms: {path.resolve().as_posix()}" for k, (path, t) in enumerate(frames, 1)]
    lines += ["", "Answer each question from the frames alone:", ""]
    lines += [f"{k}. {q}" for k, q in enumerate(asked, 1)]
    lines += ["",
              "- For a motion, name what moves, which way and how far, from which frame to which by the numbers "
              "above, what everyday motion it looks most like, and what stays still.",
              "- Quote a text exactly where you can read it. Where you cannot, write unreadable.",
              "- Where you cannot see something, because it is too small, too dark, blurred, covered or past the edge "
              "of the frame, write cannot make out and say what. Say so when a frame is nearly black or blank.",
              "- Do not say whether anything is correct, broken, working or intended. Describe it.", "",
              "Reply with one answer per question, each starting with the question's number, in at most 400 words "
              "and nothing else. The form, not the content:", "", "```", "1: <what the frames show>",
              "2: <what the frames show>", "...", "```", ""]
    return "\n".join(lines)


def read_answers(reply: str, asked: int) -> tuple[dict[int, str], list[str]]:
    """The answers of a reply by question, an answer running on until the next one starts, and the lines that
    start an answer to no question of the brief."""
    answers: dict[int, str] = {}
    stray, current = [], None
    for line in reply.splitlines():
        m = ANSWER_START.match(line.strip())
        if m and int(m[1]) not in answers and 1 <= int(m[1]) <= asked:
            current = int(m[1])
            answers[current] = m[2].strip(" *`")
        elif m and not 1 <= int(m[1]) <= asked:
            stray.append(line.strip())
            current = None
        elif current and line.strip():
            answers[current] = f"{answers[current]} {line.strip()}".strip()
    return {k: v for k, v in answers.items() if v}, stray


def check_described(described: dict, reply: str, where: str) -> tuple[list[str], int]:
    """A reviewer's description against its brief: what it lacks and what it could not see, then what the plan
    said the frames would show, to hold the answers against."""
    asked = described["ask"]
    answers, stray = read_answers(reply, len(asked))
    missing = [k for k in range(1, len(asked) + 1) if k not in answers]
    unseen = [k for k, said in answers.items() if UNSEEN.search(said)]
    lines = [f"reply: {where}, against the brief {described['brief']} of {len(asked)} questions"]
    if missing:
        lines.append("  missing: " + ", ".join(map(str, missing)))
    lines += [f"  not in the brief: {line}" for line in stray]
    for k in sorted(answers):
        lines += [f"  {k}. {asked[k - 1]}", f"    {answers[k]}"]
    lines += [f"  answer {k} cannot make out part of what it was asked" for k in unseen]
    lines += [f"expect, works: {said}" for said in described["expect"]["works"]]
    lines += [f"expect, broken: {said}" for said in described["expect"]["broken"]]
    lines.append(f"answers: {len(answers)} of {len(asked)}, {len(missing)} missing, {len(unseen)} cannot make out")
    if missing:
        lines.append("next: give the reviewer the same brief again and have it answer every question by its number; "
                     "then check its reply again")
        return lines, 1
    lines.append("next: hold the answers against expect, which the plan wrote before the frames were taken. A works "
                 "feature that an answer shows holds. A broken feature that an answer shows is a defect: fix it at "
                 "the frame and the time the answer names, and record that part again. A feature that no answer "
                 "shows is open, not false: ask about it in a new question, or record that part closer"
                 + (". An answer that cannot make out the thing asked about is no verdict: bring it into view, "
                    "with a closer viewport or a slower runtime.timeScale, and record it again" if unseen else ""))
    return lines, 0


def reply_main(reply: Path, limit: int) -> int:
    """--reply: check a saved description against the brief of the recording whose folder holds it."""
    beside = reply.parent.with_name(reply.parent.name + EXPECT)
    try:
        described = json.loads(beside.read_text(encoding="utf-8"))
        said = reply.read_text(encoding="utf-8")
    except OSError as e:
        print(f"{e}: save the reply in the folder of the recording whose brief.md it answers, as reply.md, as the "
              f"brief: line of preview_project.py says, and check it again", file=sys.stderr)
        return 2
    lines, code = check_described(described, said, str(reply))
    shown = c3.fitting(lines, limit)
    print("\n".join(lines[:shown]))
    if shown < len(lines):
        print(f"{len(lines) - shown} lines not printed: --limit 0 prints them")
    return code


def script_json(value: object) -> str:
    """JSON to put in the page's script, with no </script> inside it."""
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def write_index(shots: Path) -> Path:
    """index.html in the shots folder: every recording there with its review page, the
    newest first, so the user opens one from a page instead of a folder chooser."""
    found = []
    for timeline in shots.glob("*/timeline.json"):
        page = timeline.parent.with_suffix(".html")
        try:
            data = json.loads(timeline.read_text(encoding="utf-8"))
            frames, steps, when = data["frames"], data.get("steps", []), timeline.stat().st_mtime
        except (OSError, ValueError, KeyError, TypeError):     # a folder that is not a recording
            continue
        if not page.exists():
            continue
        found.append((when, {"name": timeline.parent.name, "page": page.name, "project": data.get("project"),
                             "when": time.strftime("%Y-%m-%d %H:%M", time.localtime(when)), "frames": len(frames),
                             "seconds": frames[-1]["t"] if frames else 0, "steps": len(steps),
                             "failed": sum(not s.get("ok", True) for s in steps),
                             "errors": sum(len(s.get("errors", [])) for s in steps)}))
    index = shots / "index.html"
    recordings = [r for _, r in sorted(found, key=lambda pair: pair[0], reverse=True)]
    index.write_text(REVIEW.replace("/*RECORDINGS*/null", script_json(recordings)), encoding="utf-8")
    return index


def tick_lines(steps: list[dict]) -> list[str]:
    """How the game ticked over the steps a recording covered: from each step's ticks, read after it."""
    read = [s["ticks"] for s in steps if s.get("ticks")]
    seconds = sum(r["seconds"] for r in read)
    if not seconds:
        return []
    ticks = sum(r["ticks"] for r in read)
    return [f"the game ticked {ticks} times in {seconds:.1f} s, {ticks / seconds:.0f} a second, at most "
            f"{max(r['longest'] for r in read) * 1000:.0f} ms apart"]


def watch_lines(frames: list[dict]) -> list[str]:
    """How each watched value changed over the recording, at most eight changes each."""
    lines = []
    for name in frames[0].get("watch") or {}:
        changes, last = [], object()
        for f in frames:
            value = json.dumps((f.get("watch") or {}).get(name), ensure_ascii=False)
            if value != last:
                changes.append(f"{value if len(value) <= 40 else value[:37] + '...'} at {round(f['t'] * 1000)} ms")
                last = value
        more = f", and {len(changes) - 8} more in timeline.json" if len(changes) > 8 else ""
        lines.append(f"watch {name}: " + ", ".join(changes[:8]) + more)
    return lines


def game_frames(frames: list[dict], fps: float) -> dict | None:
    """The screenshots of a video at fps frames a second of game time: for each instant
    start + k / fps up to the last screenshot's game time, the last screenshot whose game
    time is at or before it. Also how far the chosen screenshots fall before their
    instants, and how many frames repeat the one before because no screenshot fell in
    them. None when less than a frame of game time passed."""
    timed, top = [], -math.inf
    for i, f in enumerate(frames):
        g = f.get("game")
        if isinstance(g, (int, float)) and g >= top:    # a page the game reloaded starts its game time again
            timed.append((g, i))
            top = g
    if len(timed) < 2 or timed[-1][0] - timed[0][0] < 1 / fps:
        return None
    start, shots, lags, j, k = timed[0][0], [], [], 0, 0
    while start + k / fps <= timed[-1][0]:
        at = start + k / fps
        while j + 1 < len(timed) and timed[j + 1][0] <= at:
            j += 1
        shots.append(timed[j][1])
        lags.append(at - timed[j][0])
        k += 1
    return {"start": start, "shots": shots, "lag": max(lags),
            "repeats": sum(a == b for a, b in zip(shots, shots[1:]))}


def game_lines(game: dict, fps: float, seconds: list[float]) -> list[str]:
    """What a video in game time holds: the start of the recording's first line, then
    how to slow the game when frames repeat. The scale asked for puts a quarter of a
    frame of game time or less between two screenshots."""
    n = len(game["shots"])
    said = [f"{n} frames at {fps:g} fps of game time from {game['start']:.2f} s, each the last screenshot at or "
            f"before its instant, at most {game['lag'] * 1000:.1f} ms of game time before it: "]
    if game["repeats"]:
        scale = 1 / (4 * fps * sorted(seconds[:-1])[len(seconds[:-1]) // 2])
        unit = 10 ** math.floor(math.log10(scale))
        said.append(f"{game['repeats']} of {n} frames repeat the one before, since no screenshot fell in them: set "
                    f"runtime.timeScale = {math.floor(scale / unit) * unit:.2g} in a js step before this record step, "
                    f"and record again")
    return said


def make_video(frames: list[Path], video: Path, seconds: list[float] | None = None, fps: float = 30) -> str | None:
    """An .mp4 at fps frames a second through ffmpeg where it is installed, else a .gif
    through Pillow; None with neither. Each frame stays up for its seconds, or with no
    seconds for one frame of the video."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        listing = video.with_suffix(".txt")
        lines = ["ffconcat version 1.0"]
        for i, frame in enumerate(frames):
            lines += [f"file '{frame.resolve().as_posix()}'"] + ([f"duration {seconds[i]:.4f}"] if seconds else [])
        if seconds:
            lines.append(f"file '{frames[-1].resolve().as_posix()}'")     # concat drops the last duration otherwise
        listing.write_text("\n".join(lines) + "\n", encoding="utf-8")
        # Durations of 1/fps come out with frames doubled: concat times them in its own base and -r rounds
        steady = "" if seconds else f"settb=1/{fps:g},setpts=N,fps={fps:g},"
        mp4 = video.with_suffix(".mp4")
        done = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
                               "-vf", steady + "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-pix_fmt", "yuv420p",
                               "-r", f"{fps:g}", str(mp4)],
                              capture_output=True, text=True, timeout=120)
        listing.unlink(missing_ok=True)
        if done.returncode == 0:
            return str(mp4)
    try:
        from PIL import Image
    except ImportError:
        return None
    gif = video.with_suffix(".gif")
    images = [Image.open(f) for f in frames]
    images[0].save(gif, save_all=True, append_images=images[1:], loop=0,
                   duration=[max(20, round(s * 1000)) for s in seconds or [1 / fps] * len(frames)])
    return str(gif)


# A recording's contact sheet: at most 12 frames, at most 1600 px a side, 4 px between the frames.
SHEET_CELLS, SHEET_SIDE, SHEET_GAP = 12, 1600, 4


def frame_change(paths: list[Path], frames: list[dict]) -> list[float]:
    """How much each frame differs from the one before it, 0 for the first: the mean
    difference of small grey copies with Pillow, else the watched numbers' changes,
    each over its own range; all 0 when neither tells."""
    try:
        from PIL import Image, ImageChops, ImageStat
        if not paths or len(paths) != len(frames):
            raise OSError("no frame for each time")
        small = []
        for p in paths:
            with Image.open(p) as image:
                image.draft("L", (64, 64))
                small.append(image.convert("L").resize((64, 64)))
        return [0.0] + [ImageStat.Stat(ImageChops.difference(a, b)).mean[0] for a, b in zip(small, small[1:])]
    except (ImportError, OSError):
        pass
    numbers: dict[str, list[float | None]] = {}
    for f in frames:
        for name, value in (f.get("watch") or {}).items():
            numbers.setdefault(name, [])
    for name, values in numbers.items():
        for f in frames:
            value = (f.get("watch") or {}).get(name)
            values.append(value if isinstance(value, (int, float)) and not isinstance(value, bool) else None)
    change = [0.0] * len(frames)
    for values in numbers.values():
        known = [v for v in values if v is not None]
        span = (max(known) - min(known)) if known else 0
        if not span:
            continue
        for i in range(1, len(values)):
            if values[i] is not None and values[i - 1] is not None:
                change[i] += abs(values[i] - values[i - 1]) / span
    return change


def sheet_frames(frames: list[dict], steps: list[dict], change: list[float]) -> list[tuple[int, str]]:
    """The frames of a recording's contact sheet, in order, each with why it is there:
    the first and the last, the frames around the largest change, then the start and end
    of each step, thinned evenly to fit; the cells left over go where the picture changes
    most, so a motion between two steps is on the sheet too."""
    if not frames:
        return []
    times = [f["t"] for f in frames]

    def nearest(t: float) -> int:
        return min(range(len(times)), key=lambda i: abs(times[i] - t))

    kept = {0: "start", len(frames) - 1: "end"}
    peak = max(range(len(change)), key=change.__getitem__) if change and max(change) > 0 else None
    if peak is not None:
        for i in (peak - 1, peak + 1):
            if 0 <= i < len(frames):
                kept.setdefault(i, "")
        kept[peak] = "largest change"
    rest: dict[int, str] = {}
    for s in steps:
        rest.setdefault(nearest(s["start"]), f"step {s['step']} starts")
        rest.setdefault(nearest(s["end"]), f"step {s['step']} ends")
    rest = {i: why for i, why in rest.items() if i not in kept}
    room = SHEET_CELLS - len(kept)
    chosen = sorted(rest)
    if len(chosen) > room:
        chosen = [chosen[round(k * (len(chosen) - 1) / max(room - 1, 1))] for k in range(room)] if room > 0 else []
    kept |= {i: rest[i] for i in chosen}
    spare = min(SHEET_CELLS, len(frames)) - len(kept)
    if spare > 0:       # spread over the change, so the frames fall where the picture moves
        total, run = sum(change), []
        for c in change:
            run.append((run[-1] if run else 0) + c)
        for k in range(spare):
            share = (k + 0.5) / spare
            kept.setdefault(next(j for j, r in enumerate(run) if r >= share * total) if total
                            else round(share * (len(frames) - 1)), "")
    return sorted(kept.items())


def make_sheet(paths: list[Path], times: list[float], out: Path) -> str | None:
    """The frames side by side in one image of at most SHEET_SIDE pixels a side, each
    numbered with its time: with Pillow, else unnumbered with ffmpeg; None with neither."""
    if not paths:
        return None
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        Image = None
    if Image:
        with Image.open(paths[0]) as first:
            w, h = first.size
    else:
        ffprobe = shutil.which("ffprobe")
        if not ffprobe or not shutil.which("ffmpeg"):
            return None
        probe = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                "-of", "csv=p=0", str(paths[0])], capture_output=True, text=True, timeout=60)
        try:
            w, h = (int(v) for v in probe.stdout.strip().split(","))
        except ValueError:
            return None
    n = len(paths)

    def scale(cols: int) -> float:
        rows = math.ceil(n / cols)
        return min(1.0, (SHEET_SIDE - SHEET_GAP * (cols + 1)) / (cols * w), (SHEET_SIDE - SHEET_GAP * (rows + 1)) / (rows * h))

    cols = max(range(1, n + 1), key=scale)
    rows, s = math.ceil(n / cols), scale(cols)
    cw, ch = max(2, int(w * s) // 2 * 2), max(2, int(h * s) // 2 * 2)
    if Image:
        sheet = Image.new("RGB", (cols * cw + (cols + 1) * SHEET_GAP, rows * ch + (rows + 1) * SHEET_GAP), (34, 34, 34))
        draw = ImageDraw.Draw(sheet)
        try:
            font = ImageFont.load_default(size=max(12, min(cw, ch) // 16))
        except TypeError:       # Pillow before 10.1 has one size
            font = ImageFont.load_default()
        for k, (p, t) in enumerate(zip(paths, times)):
            x, y = SHEET_GAP + (k % cols) * (cw + SHEET_GAP), SHEET_GAP + (k // cols) * (ch + SHEET_GAP)
            with Image.open(p) as frame:
                sheet.paste(frame.convert("RGB").resize((cw, ch)), (x, y))
            label = f"{k + 1}  {round(t * 1000)} ms"
            box = draw.textbbox((x + 4, y + 4), label, font=font)
            draw.rectangle((box[0] - 3, box[1] - 3, box[2] + 3, box[3] + 3), fill=(0, 0, 0))
            draw.text((x + 4, y + 4), label, fill=(255, 255, 255), font=font)
        sheet.save(out)
        return str(out)
    listing = out.with_suffix(".txt")
    listing.write_text("ffconcat version 1.0\n" + "".join(f"file '{p.resolve().as_posix()}'\n" for p in paths),
                       encoding="utf-8")
    g = SHEET_GAP
    done = subprocess.run([shutil.which("ffmpeg"), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                           "-i", str(listing), "-vf", f"scale={cw}:{ch},tile={cols}x{rows}:padding={g}:margin={g}"
                           ":color=0x222222", "-frames:v", "1", str(out)], capture_output=True, text=True, timeout=120)
    listing.unlink(missing_ok=True)
    return str(out) if done.returncode == 0 and out.exists() else None


def emulate(page: oe.DevTools, viewport: list[int] | None, ratio: float = 1) -> tuple[int, int] | None:
    """Give the window the plan's viewport and pixel ratio, and the size the page then
    reports, None when it answered nothing; without a viewport the window keeps its
    own size. The browser answers before the page has resized, by as much as 0.4 s:
    a size read at once can be the window's own while the runtime already places its
    layers in the viewport."""
    width, height = viewport or (0, 0)     # 0 keeps the window's own
    page.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=ratio,
              mobile=False)
    size, scale, end = None, None, time.monotonic() + RESIZE
    while time.monotonic() < end:
        try:
            got = page.evaluate("[innerWidth, innerHeight, devicePixelRatio]")
            size, scale = tuple(got[:2]), got[2]
        except oe.DevToolsError:    # the preview page replaced its document while loading
            pass
        if scale == ratio and (not viewport or size == tuple(viewport)):
            break
        time.sleep(0.05)
    return size


def path(points: list[tuple[float, float]], seconds: float) -> list[tuple[float, float, float]]:
    """The moves of a drag through `points`, each (seconds before it, x, y): every
    0.03 s and at least 8 a leg, each leg given time in proportion to its length."""
    legs = list(zip(points, points[1:]))
    lengths = [math.dist(a, b) for a, b in legs]
    moves = []
    for ((x1, y1), (x2, y2)), length in zip(legs, lengths):
        share = seconds * (length / sum(lengths) if sum(lengths) else 1 / len(legs))
        count = max(8, round(share / 0.03))
        moves += [(share / count, x1 + (x2 - x1) * k / count, y1 + (y2 - y1) * k / count) for k in range(1, count + 1)]
    return moves


class StepFailed(Exception):
    pass


def step_line(n: int, step: dict) -> str:
    kind = next(k for k in STEPS if k in step)
    value = step[kind]
    what = {"tap": lambda: target_text(value), "hold": lambda: target_text(value),
            "drag": lambda: " through ".join(map(target_text, [value, *step.get("through", [])]))
            + f" to {target_text(step['to'])}",
            "move": lambda: "".join(f"through {target_text(t)} " for t in step.get("through", []))
            + f"to {target_text(value)}", "key": lambda: "+".join(key_names(value)),
            "wait": lambda: f"{value:g} s", "until": lambda: one_line(value), "js": lambda: one_line(value),
            "state": lambda: " ".join([value] if isinstance(value, str) else value) or "counts",
            "shot": lambda: value, "record": lambda: value or "stop"}[kind]()
    note = f" ({step['note']})" if step.get("note") else ""
    return f"{n} {kind} {what}{note}"


def one_line(text: str | list[str]) -> str:
    text = " ".join(t.strip() for t in text) if isinstance(text, list) else " ".join(text.split())
    return text if len(text) <= 80 else text[:77] + "..."


def do_step(game: Game, step: dict, n: int, shots: Path) -> tuple[str, dict | None]:
    """Run one step; what to print after its line, and what it read: {"value"} or {"state"}."""
    kind = next(k for k in STEPS if k in step)
    value = step[kind]
    if kind == "wait":
        time.sleep(value)
        return "ok", None
    if kind == "tap":
        x, y = game.aim(value)
        game.press(x, y)
        time.sleep(0.05)
        game.release(x, y)
        return f"at ({x:.0f}, {y:.0f})", None
    if kind == "hold":
        x, y = game.aim(value)
        seconds = step.get("seconds", PRESS["hold"])
        game.press(x, y)
        time.sleep(seconds)
        game.release(x, y)
        return f"at ({x:.0f}, {y:.0f}) for {seconds:g} s", None
    if kind == "drag":
        points = [game.aim(t) for t in [value, *step.get("through", []), step["to"]]]
        seconds, rest = step.get("seconds", PRESS["drag"]), step.get("rest", 0.05)
        game.press(*points[0])
        for delay, x, y in path(points, seconds):
            time.sleep(delay)
            game.move(x, y)
        time.sleep(rest)
        game.release(*points[-1])
        where = " through ".join(f"({x:.0f}, {y:.0f})" for x, y in points[:-1])
        moving = ", released moving" if rest == 0 else ""
        return f"{where} to ({points[-1][0]:.0f}, {points[-1][1]:.0f}) in {seconds:g} s{moving}", None
    if kind == "move":
        points = [game.aim(t) for t in [*step.get("through", []), value]]
        seconds, rest = step.get("seconds", PRESS["move"]), step.get("rest", 0)
        if game.pointer is None:    # no mouse event yet, so the move starts on its first point
            game.mouse("mouseMoved", *points[0], False)
            points = points[1:]
        points = [game.pointer, *points]
        for delay, x, y in path(points, seconds) if seconds else [(0, x, y) for x, y in points[1:]]:
            time.sleep(delay)
            game.mouse("mouseMoved", x, y, False)
        time.sleep(rest)
        still = f", then still {rest:g} s" if rest else ""
        if len(points) == 1:
            return f"at ({points[0][0]:.0f}, {points[0][1]:.0f}), the run's first mouse event{still}", None
        where = " through ".join(f"({x:.0f}, {y:.0f})" for x, y in points[:-1])
        took = f"in {seconds:g} s" if seconds else "at once"
        return f"{where} to ({points[-1][0]:.0f}, {points[-1][1]:.0f}) {took}{still}", None
    if kind == "key":
        events = [key_event(k) for k in key_names(value)]
        seconds = step.get("seconds", PRESS["key"])
        for i, event in enumerate(events):
            down = "keyDown" if "text" in event else "rawKeyDown"
            game.win.call("Input.dispatchKeyEvent", type=down, modifiers=modifiers(events[:i + 1]), **event)
        time.sleep(seconds)
        for i in reversed(range(len(events))):
            game.win.call("Input.dispatchKeyEvent", type="keyUp", modifiers=modifiers(events[:i]),
                          **{k: v for k, v in events[i].items() if k != "text"})
        return f"held {seconds:g} s", None
    if kind == "until":
        timeout = step.get("timeout", 10)
        got = game.run(f"""(async () => {{ const test = {scope(value)}, t0 = performance.now();
          for (;;) {{ if (await test()) return (performance.now() - t0) / 1000;
            if (performance.now() - t0 > {timeout * 1000}) return null; await c3play.wait(0.05); }} }})()""",
                       wait=timeout + 10)
        if got is None:
            raise StepFailed(f"still false after {timeout:g} s")
        return f"true after {got:.1f} s", None
    if kind == "js":
        got = game.run(f"(async () => c3play.plain(await {scope(value)}()))()", wait=step.get("timeout", 60))
        text = json.dumps(got, ensure_ascii=False)
        return text if len(text) <= 1500 else text[:1500] + " ... (--out keeps it all)", {"value": got}
    if kind == "state":
        names = [value] if isinstance(value, str) else value
        read = oe.read_state(game.win, game.live, names)
        if "error" in read:
            raise StepFailed(read["error"].splitlines()[0])
        return "", {"state": read}
    if kind == "record":
        said = game.stop_recording()
        if value:
            game.record(value, shots / f"{n:02d}-{value}", step.get("watch") or {}, step.get("fps"),
                        {k: step[k] for k in ("expect", "ask") if k in step})
        return "; ".join(filter(None, ["recording" if value else "", said])), None
    return screenshot(game, shots / f"{n:02d}-{value}.png"), None


def screenshot(game: Game, path: Path) -> str:
    """The screenshot's path, with how much it shows: the share of it that is one colour and the
    deviation of its luminance, which together tell a frame with nothing drawn."""
    path.write_bytes(base64.b64decode(game.win.call("Page.captureScreenshot")["data"]))
    got = oe.fill(game.win)
    if not got:
        return str(path)
    share, spread = got
    if c3.is_blank(share, spread):
        return (f"{path}: {share:.2%} of it is one colour and its luminance deviates {spread:.1f}, under "
                f"{c3.SPREAD:g}, so the game had not drawn yet or draws nothing in view here; add a wait or until "
                f"step before this shot")
    return f"{path} ({share:.2%} one colour, luminance deviation {spread:.1f})"


def play(plan: dict, shots: Path, project: Path) -> Callable[[oe.Browser, str, oe.DevTools], dict]:
    """The `then` of open_in_editor.open_one: preview the project and run the plan."""
    def run(browser: oe.Browser, target: str, page: oe.DevTools) -> dict:
        if not plan.get("keep_saves"):     # a game reads its save on start, so the profile's would carry over
            page.call("Storage.clearDataForOrigin", origin=PREVIEW, storageTypes="local_storage,indexeddb")
        started = oe.start_preview(browser, target, page)
        if isinstance(started, list):
            return {"started": False, "layout": None, "runtime": None, "errors": started, "steps": []}
        window, win = started
        touch, view, ratio = bool(plan.get("touch")), plan.get("viewport"), plan.get("pixel_ratio", 1)
        game = None
        try:
            oe.watch_network(win)
            if view or ratio != 1:
                size = emulate(win, view, ratio)
                if view and size != tuple(view):
                    return {"started": False, "layout": None, "runtime": None, "steps": [], "errors": [
                        f"the preview window did not take the viewport {view[0]}x{view[1]} in {RESIZE} seconds; "
                        f"it reports {'nothing' if size is None else f'{size[0]}x{size[1]}'}"]}
            if not view:
                size = tuple(win.evaluate("[innerWidth, innerHeight]"))     # a headed window loses its frame's share
            if touch:
                win.call("Emulation.setTouchEmulationEnabled", enabled=True, maxTouchPoints=5)
            sessions, live, stalled = oe.attach(win, patience=30)
            if not live:
                return {"started": False, "layout": None, "runtime": None, "steps": [], "errors": [
                    "the runtime loaded but did not tick for 3 seconds" if stalled
                    else "the preview window opened but no runtime was found in it in 30 seconds"]}
            win.evaluate(PLAY_JS, session=live[0])
            enable(win, sessions)
            win.evaluate("0")
            before = oe.runtime_errors(win)
            game = Game(win, live[0], touch, size, f"ws://127.0.0.1:{browser.port}/devtools/page/{window['targetId']}",
                        view, project, ratio)
            try:
                first = game.pulse()    # the steps' ticks are counted from here
            except StepFailed as e:
                return {"started": False, "layout": None, "runtime": None, "steps": [], "errors": [*before, str(e)]}
            first = first and first["layout"]
            began = time.monotonic()
            steps = play_steps(game, plan["steps"], shots, first)
            seconds = time.monotonic() - began
            recorded = game.stop_recording()
            try:
                layout = win.evaluate("c3probe.snapshot([], 0)", wait=6, session=game.live)["layout"]
            except oe.DevToolsError:    # the last step left the page reloading
                layout = None
        finally:
            win.ws.close()
            browser.devtools.call("Target.closeTarget", targetId=window["targetId"])
            if game:
                game.close()
        return {"started": True, "layout": layout, "first_layout": first, "runtime": "worker" if game.live else "page",
                "seconds": round(seconds, 1), "viewport": list(size), "pixel_ratio": ratio, "touch": touch,
                "errors": before, "steps": steps, "planned": len(plan["steps"]), "recorded": recorded}
    return run


def enable(win: oe.DevTools, sessions: list[str | None]) -> None:
    """Have the page and each worker hand over the errors they log."""
    for s in sessions:
        try:
            win.call("Runtime.enable", session=s)
        except oe.DevToolsError:    # a worker that ended since
            pass


def play_steps(game: Game, steps: list[dict], shots: Path, layout: str | None = None) -> list[dict]:
    """Run the steps in order until one fails: what each said, read and caused.

    A game that reloads its page loses the probe with it. After each step the
    probe is looked for, and left again in the new page; the step's `reloaded`
    lists the seconds the game took to start again. A step the reload broke
    off runs again in the new page, except a js step whose code had started:
    it may have done part of its work, so it fails.

    Then the layout and the ticks are read: a step that leaves the game on
    another layout than `layout`, the one before it, says so, and a step in
    which the game did not tick for STALL seconds fails."""
    played: list[dict] = []
    for n, step in enumerate(steps, 1):
        started_at = time.monotonic()
        ok, said, extra = attempt(game, step, n, shots)
        reloads: list[float] = []
        pulse = None
        try:
            back = game.reloaded()
            if back is not None:
                reloads.append(back)
                if ok:
                    said += f"; then the page reloaded, and the game started again {back:.1f} s later"
                elif "js" not in step or NOT_STARTED.search(said):
                    ok, said, extra = attempt(game, step, n, shots)
                    said = f"the page reloaded during the step, so it ran again {back:.1f} s later: {said}"
                    back = game.reloaded()
                    if back is not None:
                        reloads.append(back)
                        said += f"; then the page reloaded again, and the game started {back:.1f} s later"
                else:
                    said += "; the page reloaded while the code ran, so the step did not run again"
            pulse = game.pulse()
        except StepFailed as e:     # the reloaded page ran no game, or the game stopped answering
            ok, said = False, f"{said}; {e}"
        if pulse:
            if pulse["layout"] != layout:
                said += f"; layout {layout!r} -> {pulse['layout']!r}"
                layout = pulse["layout"]
            if ok and pulse["longest"] > STALL:
                ok, said = False, (f"{said}; the game did not tick for {pulse['longest']:.1f} s during the step, "
                                   f"as when a long loop in its events or a script holds its thread; find the loop, and spread its work "
                                   f"over ticks or end it sooner")
        done = {"step": n, "line": step_line(n, step), "ok": ok, "said": said, **extra, "layout": layout}
        if pulse:
            done["ticks"] = {k: round(pulse[k], 3) for k in ("ticks", "seconds", "longest")}
        if reloads:
            done["reloaded"] = [round(s, 1) for s in reloads]
        if not ok:
            try:
                done["said"] += f"; the window then: {screenshot(game, shots / f'{n:02d}-failed.png')}"
            except oe.DevToolsError:
                pass
        done["errors"] = oe.runtime_errors(game.win)    # they arrived before reloaded() was answered
        played.append(done)
        if game.recording:      # its timeline places the step
            game.recording.steps.append({k: done[k] for k in ("step", "line", "ok", "said", "errors", "ticks")
                                         if k in done} | {"start": started_at, "end": time.monotonic()})
        if not ok:
            break
    return played


def attempt(game: Game, step: dict, n: int, shots: Path) -> tuple[bool, str, dict]:
    """Run one step: whether it ran, what to print after its line, and what it read."""
    try:
        said, extra = do_step(game, step, n, shots)
        return True, said, extra or {}
    except (StepFailed, oe.DevToolsError) as e:     # the code threw, or the page stopped answering
        return False, str(e).splitlines()[0], {}


def report(result: dict, label: Callable[[str], str] = oe.key_name) -> list[str]:
    if result["status"] != "opened":
        return oe.report(result, label)
    lines = oe.opened_lines(result)
    ran = result.get("preview")
    if not ran or not ran["started"]:
        return lines + [f"  preview did not run: {e}" for e in (ran or {}).get("errors", ["no preview"])]
    touch = ", touch" if ran["touch"] else ""
    ratio = f" at pixel ratio {ran['pixel_ratio']:g}" if ran.get("pixel_ratio", 1) != 1 else ""
    lines.append(f"  preview: layout {ran['layout']!r} at the end, runtime in the {ran['runtime']}, "
                 f"viewport {ran['viewport'][0]}x{ran['viewport'][1]}{ratio}{touch}")
    lines += oe.runtime_lines(ran["errors"])
    for done in ran["steps"]:
        said = f": {done['said']}" if done["said"] else ""
        lines.append(f"  {done['line']}{said}" if done["ok"] else f"  {done['line']}: FAILED, {done['said']}")
        if not done["ok"] and ran.get("first_layout"):
            lines.append(f"    trail: {trail(ran['first_layout'], ran['steps'])}")
        if "state" in done:
            lines += ["  " + line for line in oe.state_lines(done["state"], label)]
        lines += oe.runtime_lines(done["errors"], "    ")
    if ran.get("recorded"):
        lines.append(f"  {ran['recorded']}")
    ok = sum(d["ok"] for d in ran["steps"])
    lines.append(f"  ran: {ok} of {ran['planned']} steps in {ran['seconds']:.1f} s, "
                 f"{errors_text(ran['errors'] + [e for d in ran['steps'] for e in d['errors']])}")
    return lines


def errors_text(errors: list[str]) -> str:
    """How many runtime errors and failed requests a run logged, for its last line."""
    failed = sum(e.startswith(oe.NETWORK) for e in errors)
    logged = len(errors) - failed
    return (f"{logged or 'no'} runtime error{'' if logged == 1 else 's'}"
            + (f" and {failed} failed request{'' if failed == 1 else 's'}" if failed else ""))


def trail(first: str, steps: list[dict]) -> str:
    """The layouts the game went through: the one it started on, then each one it went to, with the step
    after which it ran there."""
    went, now = [f"{first!r} at the start"], first
    for done in steps:
        if done.get("layout") and done["layout"] != now:
            now = done["layout"]
            went.append(f"{now!r} after step {done['step']}")
    return ", ".join(went)


def kept(out: Path | None, shots: Path | None, project: Path) -> tuple[Path, Path]:
    return oe.kept(out, shots, project, "preview-project")


def where(out: Path, shots: Path) -> str:
    return f"full result in {out}, screenshots in {shots}"


def print_report(lines: list[str], limit: int, out: Path, shots: Path) -> None:
    """Print the lines that fit in --limit, how many did not, and where the whole result is."""
    shown = c3.fitting(lines, limit)
    print("\n".join(lines[:shown]))
    if shown < len(lines):
        print(f"{len(lines) - shown} lines not printed: {out} keeps everything, --limit 0 prints it")
    print(where(out, shots))


def kept_plans(project: Path) -> list[Path]:
    folder = project / KEPT
    return sorted(folder.glob("*.json")) if folder.is_dir() else []


# The steps after which the game has done something a check can read: an input, or time passing.
DOING = ("tap", "hold", "drag", "key", "wait")


def checks(plan: dict) -> int:
    """The until steps after the first input or wait: the only steps that fail when the game does not do what
    the change should make it do. An until before them reads the start, such as an instance that exists."""
    first = next((i for i, step in enumerate(plan["steps"]) if any(k in step for k in DOING)), len(plan["steps"]))
    return sum("until" in step for step in plan["steps"][first + 1:])


def keep(plan: Path, project: Path, name: str) -> Path:
    """The plan copied as it was written into the project's kept plans."""
    to = project / KEPT / f"{name}.json"
    to.parent.mkdir(parents=True, exist_ok=True)
    to.write_bytes(plan.read_bytes())
    return to


def play_all(plans: dict[str, dict], shots: Path, project: Path) -> Callable[[oe.Browser, str, oe.DevTools], dict]:
    """The `then` of open_in_editor.open_one: each plan previews the game afresh, in one editor session."""
    def run(browser: oe.Browser, target: str, page: oe.DevTools) -> dict:
        ran = {}
        for name, plan in plans.items():
            (shots / name).mkdir(parents=True, exist_ok=True)
            ran[name] = play(plan, shots / name, project)(browser, target, page)
        return {"started": True, "plans": ran}
    return run


def replay_report(result: dict, refused: dict[str, list[str]], until: dict[str, int],
                  label: Callable[[str], str] = oe.key_name) -> tuple[list[str], int]:
    """One line per kept plan, ok or FAIL with the step that failed or the first runtime error, and how many
    failed; `until` holds each plan's until checks."""
    if result["status"] != "opened":
        return oe.report(result, label), len(refused) + 1
    lines = oe.opened_lines(result)
    ran = (result.get("preview") or {}).get("plans", {})
    failed, errors, held = 0, [], 0
    for name in sorted(set(ran) | set(refused)):
        where = (KEPT / f"{name}.json").as_posix()
        if name in refused:
            failed += 1
            lines.append(f"  FAIL  {name} ({where}): the plan is refused: {'; '.join(refused[name])}")
            continue
        done = ran[name]
        if not done["started"]:
            failed += 1
            lines.append(f"  FAIL  {name} ({where}): the preview did not run: {'; '.join(done['errors'])}")
            continue
        raw = done["errors"] + [e for d in done["steps"] for e in d["errors"]]
        logged = oe.runtime_lines(raw, "    ")
        errors += raw
        bad = next((d for d in done["steps"] if not d["ok"]), None)
        if bad or logged or len(done["steps"]) < done["planned"]:
            failed += 1
            why = (f"{bad['line']}: FAILED, {bad['said']}" if bad else logged[0].strip() if logged
                   else f"stopped after {len(done['steps'])} of {done['planned']} steps")
            lines.append(f"  FAIL  {name} ({where}): {why}")
            lines += logged[1 if not bad else 0:][:3]
        else:
            held += until[name]
            lines.append(f"  ok    {name}: {done['planned']} step{'s' if done['planned'] != 1 else ''}, "
                         + (f"{until[name]} until check{'s' if until[name] != 1 else ''}" if until[name] else
                            "no until after an input or wait, so it checks nothing,")
                         + f" in {done['seconds']:.1f} s")
    total = len(ran) + len(refused)
    lines.append(f"  replayed: {total - failed} of {total} kept plans pass with {held} until "
                 f"check{'' if held == 1 else 's'}, {errors_text(errors)}")
    return lines, failed


def replay(args: argparse.Namespace, project: Path, exe: str, editor: str) -> int:
    """--all: every kept plan, one editor session."""
    plans, refused = {}, {}
    for path in kept_plans(project):
        try:
            plan, problems = check_plan(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as e:
            plan, problems = {}, [str(e)]
        if problems:
            refused[path.stem] = problems
        else:
            plans[path.stem] = plan
    if not plans and not refused:
        print(f"no kept plan in {project / KEPT}: when a plan passes, run it again with --keep NAME to keep it there",
              file=sys.stderr)
        return 2
    out, shots = oe.kept(args.out, args.shots, project, "preview-project", "plans.json", "plans")
    shots.mkdir(parents=True, exist_ok=True)
    if plans:
        try:
            result = oe.drive(exe, oe.profile_folder(args.profile, project, exe), args.headed,
                              lambda b: oe.open_one(b, editor, project, oe.staged(project, "preview-project"), None,
                                                    bool(args.release), play_all(plans, shots, project)))
        except oe.ProfileBusy as e:
            print(e, file=sys.stderr)
            return oe.BUSY
        if result is None:
            return 2
    else:
        result = {"status": "opened", "project": str(project), "title": "not opened: every kept plan is refused",
                  "editor": "-", "preview": {"plans": {}}}
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    lines, failed = replay_report(result, refused, {name: checks(plan) for name, plan in plans.items()})
    print_report(lines, args.limit, out, shots)
    if result["status"] != "opened":
        print(oe.NEXT)
    elif failed:
        print("next: a kept plan passed when the change it checks was made, so one that fails now names what a later "
              "change broke. Read its failing step and the events that step reads, fix the events, not the plan, and "
              "run --all again. Change a kept plan only when the game was meant to change what it checks.")
    return 1 if failed or result["status"] != "opened" else 0


def main() -> int:
    c3.utf8_output()
    ap = argparse.ArgumentParser(description=__doc__, epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan", type=Path, nargs="?", metavar="PLAN.json",
                    help="the steps to play, as described above (none with --all)")
    ap.add_argument("--keep", metavar="NAME",
                    help="when every step passes, keep the plan as tools/plans/NAME.json in the project, to commit "
                         "with the change it checks; NAME is letters, digits, - and _")
    ap.add_argument("--all", action="store_true",
                    help="replay every plan kept in tools/plans of the project, each from a first launch, and name "
                         "each one that fails")
    ap.add_argument("--reply", type=Path, metavar="REPLY",
                    help="a reply.md beside a recording's brief.md: check it answers every question, print it "
                         "with expect")
    ap.add_argument("--project", metavar="FOLDER",
                    help="the folder that holds project.c3proj (default: found from the current directory upward)")
    ap.add_argument("--release", metavar="rNNN", help="open in this release of the editor, as open_in_editor.py does")
    ap.add_argument("--browser", metavar="EXE",
                    help="the Chromium-based browser to start (default: Edge, Chrome or Chromium where installed)")
    ap.add_argument("--shots", type=Path, help="the folder for the screenshots "
                                               "(default: shots/ beside the result)")
    ap.add_argument("--out", type=Path, help="write the result, every value and state included, as JSON "
                                             "(default: result.json in .tmp/scripts/preview-project/)")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    ap.add_argument("--profile", type=Path, metavar="FOLDER",
                    help="keep the browser profile in FOLDER/editor-<browser> instead of .tmp/browsers/")
    ap.add_argument("--locale", default="en-US",
                    help="the language pack in data/c3-lang of Construct3-RAG or the plugin that names the inspector "
                         "values; a key the pack lacks keeps its last word (default: en-US)")
    ap.add_argument("--limit", type=int, default=c3.LIMIT, metavar="CHARS",
                    help=f"stop printing after about this many characters; --out keeps everything, 0 prints "
                         f"everything (default: {c3.LIMIT})")
    args = ap.parse_args()

    if [bool(args.plan), args.all, bool(args.reply)].count(True) != 1:
        ap.error("give a PLAN.json to play, or --all to replay the kept plans, or --reply REPLY to check a "
                 "description of a recording")
    if args.keep is not None and (args.all or args.reply or not re.fullmatch(r"[A-Za-z0-9_-]+", args.keep)):
        ap.error("--keep takes a NAME of letters, digits, - and _, with a PLAN.json")
    if args.reply:
        return reply_main(args.reply, args.limit)
    if args.all:
        project = c3.find_project(args.project)
        if not project:
            print(f"no project.c3proj found from {args.project or Path.cwd()} upward; run this in the project folder "
                  f"or pass --project <folder>", file=sys.stderr)
            return 2
        exe = args.browser or oe.browser_path()
        if not exe:
            print("no Edge, Chrome or Chromium found here, and replaying the kept plans needs one this script can "
                  "drive: install one, or play each plan in tools/plans with a browser tool of this session.")
            return 3
        return replay(args, project, exe, oe.release_url(args.release))
    try:
        plan, problems = check_plan(json.loads(args.plan.read_text(encoding="utf-8")))
    except (OSError, ValueError) as e:
        print(f"{args.plan}: {e}. Write the plan as JSON, as --help describes.", file=sys.stderr)
        return 2
    if problems:
        print("\n".join([f"{args.plan}: {p}" for p in problems] + ["See --help for the steps."]), file=sys.stderr)
        return 2
    if args.keep and not checks(plan):
        print(f"{args.plan}: not kept: no until step comes after an input or a wait, so the plan passes whatever "
              f"the game does, and a replay of it after a later change shows nothing. An until before the first "
              f"input reads the start, and a js, state or shot step prints what it reads and checks nothing. Write "
              f"what the change must make true as an until step after the input, such as "
              f"{{\"until\": \"runtime.objects.Player.getFirstInstance().x > 200\", \"timeout\": 2}}, then run "
              f"this again with --keep {args.keep}", file=sys.stderr)
        return 2
    project = c3.find_project(args.project)
    if not project:
        print(f"no project.c3proj found from {args.project or Path.cwd()} upward; run this in the project folder or "
              f"pass --project <folder>", file=sys.stderr)
        return 2
    label, note = oe.key_name, None
    if any("state" in step for step in plan["steps"]):     # the only step that prints inspector values
        try:
            label, note = oe.labeler(project, args.locale)
        except ValueError as e:
            print(e, file=sys.stderr)
            return 2
    if note:
        print(note)
    exe = args.browser or oe.browser_path()
    if not exe:
        print("no Edge, Chrome or Chromium found here, and a plan needs one this script can drive: install one, or "
              "drive the preview with a browser tool of this session as references/reading-the-runtime.md says.")
        return 3
    editor = oe.release_url(args.release)
    out, shots = kept(args.out, args.shots, project)
    shots.mkdir(parents=True, exist_ok=True)
    try:
        result = oe.drive(exe, oe.profile_folder(args.profile, project, exe), args.headed,
                          lambda b: oe.open_one(b, editor, project, oe.staged(project, "preview-project"), None,
                                                bool(args.release), play(plan, shots, project)))
    except oe.ProfileBusy as e:
        print(e, file=sys.stderr)
        return oe.BUSY
    if result is None:
        return 2
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print_report(report(result, label), args.limit, out, shots)
    ran = result.get("preview") or {}
    failed = [d for d in ran.get("steps", []) if not d["ok"]]
    errors = ran.get("started") and (ran["errors"] or any(d["errors"] for d in ran["steps"]))
    if result["status"] != "opened":
        print(oe.NEXT)
    if failed:
        print(f"next: step {failed[0]['step']} failed and the steps after it did not run. A target that is not "
              f"there, or a condition that stays false, is what the events did or did not do: read the state "
              f"(add a state step before it) and the sheet, fix the events or the plan, and run this again.")
    if errors:
        print(oe.NEXT_PREVIEW.replace("run this again with --preview", "run this again"))
    passed = result["status"] == "opened" and ran.get("started") and not failed and not errors
    others = [p for p in kept_plans(project) if args.keep is None or p.stem != args.keep]
    if passed and args.keep:
        all_kept = c3.script_command(project, "preview_project.py", " --all")
        print(f"kept: {keep(args.plan, project, args.keep)}; commit it with the change it checks"
              + (f", and replay it with the {len(others)} other kept plan{'s' if len(others) != 1 else ''} after "
                 f"every change: {all_kept}" if others else
                 f"; after every change, replay the kept plans: {all_kept}"))
    elif args.keep:
        print(f"not kept: only a plan that passes is kept. A plan that checks a bug fails until the fix works: fix "
              f"the events until it passes, then run it again with --keep {args.keep}")
    elif passed:
        print("keep: this plan passes; keep it as a check of this change with --keep NAME, and replay every kept plan "
              "after the next change with --all" + (f" ({len(others)} kept)" if others else ""))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
