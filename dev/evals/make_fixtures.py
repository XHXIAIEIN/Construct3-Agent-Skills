"""Lay out the project folders of one eval iteration, one per test case and arm.

    python dev/evals/make_fixtures.py RUNS_DIR [--arms with_skill without_skill] [--cases NAME ...] [--held-out]
                                  [--old-clone FOLDER] [--examples FOLDER] [--pin REV | --no-pin]

RUNS_DIR must lie outside the Construct3-Agent-Skills clone: an agent started below
the clone reads its AGENTS.md, which routes to this skill, and a baseline
that has the skill is not a baseline. A project is one of four kinds. The
default is the stand-in game of assets/build_project.py, without tools/, so
that the task is a hand edit of a project made in the editor. A fixture
`example:<id>` is a copy of that official example from --examples. A fixture
`empty` is the project that new_project.py creates, for a case that designs a
game before any file exists. A fixture of SEEDS is a stand-in game or an
example with a fault written into it, most of them a mistake small models
make, for a case that asks to fix it. A fixture of GENERATED keeps its
generator, for a case that asks for a change to tools/build_project.py: the
arm's own template, as it is (coins-generator), on another screen
(coins-portrait at 720x1280, coins-pixel at 320x180), or with the level of
platformer_game.py, which scrolls, in place of its game
(platformer-generator), run once. A case marked held_out in evals.json is
left out unless --held-out is given (dev/AGENTS.md, Evals).

An arm named with_... holds the skill and the block as install.py leaves
them, under .agents/skills, or under .claude/skills for an arm named
with_claude..., where Claude Code finds it as a skill of its own;
without_... holds neither, and old_... holds the previous version of
the skill, installed by the install.py of --old-clone: a checkout of the
commit before the change, such as `git worktree add --detach FOLDER HEAD`
made before editing. The old copy then names the old checkout as its clone;
pointed at this one it would report that it differs and be refreshed.

The with_... arms are pinned to one commit: the fixtures are laid out from
a detached worktree of --pin (HEAD by default) at RUNS_DIR/clone-<sha>, so
their copies name that worktree as their clone, and a pull of main during
the iteration changes nothing the runs read. The worktree leaves out dev/,
by a sparse checkout, because dev/ holds the cases, the plans and the
graders: a run that reads them can pass without doing the task. grade.py
voids a run that read them all the same, from --old-clone too
(dev/AGENTS.md, Evals). RUNS_DIR/clone.json records
the commit, the folder and the commit of --old-clone, and each
fixture.json the commit of the clone
its arm installed from, as clone.commit. A change that is not committed is
not in the worktree, so commit it first; --no-pin lays out from this
checkout as it stands.

exit codes: 0 laid out, 1 RUNS_DIR is inside the clone, a target exists, or
an example or the old clone is missing
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / "plugin"        # what the scripts get as the clone: the skill and the built data
SKILL = PLUGIN / "skills" / "construct3-agent-plugin"
sys.path.insert(0, str(SKILL / "scripts"))
import c3project as c3              # noqa: E402
CASES = json.loads((Path(__file__).parent / "evals.json").read_text(encoding="utf-8"))["evals"]


def run(*cmd: str, cwd: Path) -> str:
    p = subprocess.run([sys.executable, *cmd], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if p.returncode:
        sys.exit(f"{' '.join(cmd)} failed in {cwd}:\n{p.stdout}{p.stderr}")
    return p.stdout


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    """data in the editor's layout: tab indents, LF, no newline at the end."""
    path.write_text(json.dumps(data, indent="\t", ensure_ascii=False), encoding="utf-8", newline="\n")


def edit_json(path: Path, change: Callable[[dict], object]) -> None:
    """The JSON file at path, changed in place by change."""
    data = read_json(path)
    change(data)
    write_json(path, data)


def commit_of(folder: Path) -> str | None:
    """The commit a checkout is at, or None when it is not one."""
    p = subprocess.run(["git", "-C", str(folder), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=60)
    return p.stdout.strip() if p.returncode == 0 else None


def pin(out: Path, rev: str) -> tuple[Path, str]:
    """A detached worktree of rev at out/clone-<sha> without dev/, made once, and its commit. A note goes out when
    plugin/ has changes that the commit does not hold."""
    p = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--verify", f"{rev}^{{commit}}"],
                       capture_output=True, text=True, timeout=60)
    if p.returncode:
        sys.exit(f"--pin {rev} names no commit of {REPO}: {p.stderr.strip()}")
    sha = p.stdout.strip()
    folder = out / f"clone-{sha[:12]}"
    if commit_of(folder) != sha:
        p = subprocess.run(["git", "-C", str(REPO), "worktree", "add", "--detach", "--no-checkout", str(folder), sha],
                           capture_output=True, text=True, timeout=300)
        if p.returncode:
            sys.exit(f"git worktree add {folder} {sha} failed: {p.stderr.strip()}")
    # Applied to a worktree made before dev/ was left out too, which it empties of dev/
    for cmd in (["sparse-checkout", "set", "--no-cone", "/*", "!/dev/*"], ["checkout", "--detach", sha]):
        p = subprocess.run(["git", "-C", str(folder), *cmd], capture_output=True, text=True, timeout=300)
        if p.returncode:
            sys.exit(f"git {' '.join(cmd)} in {folder} failed: {p.stderr.strip()}")
    if subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", sha, "--", "plugin"], timeout=60).returncode:
        print(f"note: plugin/ has changes that {sha[:12]} does not hold; the with_... arms read {sha[:12]}")
    return folder, sha


def stand_in(root: Path, skill: Path = SKILL) -> Path:
    """The generated game, as dev/tests/conftest.py builds it, with the
    generator and the skill taken out again: each arm installs its own. The
    seed holds what the editor would not write itself; the generator fills the
    rest of project.c3proj, so the fixture opens in the editor."""
    (root / "tools").mkdir(parents=True)
    (root / "project.c3proj").write_text(json.dumps({"uniqueId": "eval", "properties": {}}), encoding="utf-8")
    run(str(skill / "scripts" / "install.py"), "--project", str(root), cwd=root)
    shutil.copy(skill / "assets" / "build_project.py", root / "tools" / "build_project.py")
    run("tools/build_project.py", cwd=root)
    for left in ("tools", ".agents"):
        shutil.rmtree(root / left)
    (root / "AGENTS.md").unlink()
    return root


def game_rows(sheet: dict) -> list:
    """The rows of the stand-in's outer group Coins, which hold its groups and procedures; the sheet's own
    rows in a template of before that group (--pin)."""
    outer = next((e for e in sheet["events"] if e.get("eventType") == "group" and e.get("title") == "Coins"), None)
    return outer["children"] if outer else sheet["events"]


def seed_load_errors(root: Path) -> None:
    """Five mistakes the editor refuses, each one a small model has made
    (docs/decisions/checker-editor-load-rules.md)."""
    path = root / "eventSheets" / "Game.json"
    sheet = read_json(path)
    rows = game_rows(sheet)
    groups = {e.get("title"): e for e in rows if e["eventType"] == "group"}
    collect = next(e for e in rows if e["eventType"] == "custom-ace-block")
    add_score = next(e for e in rows if e["eventType"] == "function-block")

    def first_block(group: dict) -> dict:    # the comment above it is the group's first child
        return next(e for e in group["children"] if e["eventType"] == "block")

    call = next(a for a in collect["actions"] if a.get("callFunction") == "AddScore")
    tween = next(a for a in collect["actions"] if isinstance(a.get("parameters"), dict)
                 and a["parameters"].get("tags") == '"collect"')
    collect["actions"] = [a for a in collect["actions"] if a is not call]   # a trigger inside a custom action
    collect["children"] = [{
        "eventType": "block",
        "conditions": [{"id": "on-tweens-finished", "objectClass": "Coin", "sid": 611111111111111,
                        "behaviorType": "Tween", "parameters": {"tags": "\"collect\""}}],
        "actions": [call],
        "sid": 622222222222222,
    }]
    first_block(groups["Input"])["conditions"][0]["parameters"]["type"] = "\"start\""   # a quoted combo value
    del tween["behaviorType"]                                                             # a behavior action without it
    next(a for a in add_score["actions"] if a.get("id") == "set-text")["id"] = "set-txt"  # a misspelt id
    first_block(groups["Setup"])["conditions"][0]["isInverted"] = True                  # an inverted trigger
    write_json(path, sheet)


def seed_key_pressed(root: Path) -> None:
    """W, A, S and D under Keyboard On key pressed, each simulating its 8 Direction control on Player:
    the player moves for the one tick of each press (docs/decisions/event-sheet-design-guidance.md)."""
    path = root / "eventSheets" / "event sheet 1.json"
    sheet = read_json(path)
    sid = iter(range(633333333333301, 633333333333399))
    for key, control in ((87, "up"), (65, "left"), (83, "down"), (68, "right")):
        sheet["events"] += [
            {"eventType": "comment", "text": f"Walk {control} with {chr(key)}", "sid": next(sid)},
            {"eventType": "block", "sid": next(sid),
             "conditions": [{"id": "on-key-pressed", "objectClass": "Keyboard", "sid": next(sid), "parameters": {"key": key}}],
             "actions": [{"id": "simulate-control", "objectClass": "Player", "sid": next(sid), "behaviorType": "8Direction",
                          "parameters": {"control": control}}]}]
    write_json(path, sheet)


def seed_timer_restart(root: Path) -> None:
    """The round ends on a Timer started with no trigger: Coin.Count = 0 -> ScoreText Start timer, which
    starts the timer over each tick, so On timer never restarts the layout
    (docs/decisions/event-sheet-design-guidance.md)."""
    edit_json(root / "objectTypes" / "ScoreText.json",
              lambda t: t["behaviorTypes"].append({"behaviorId": "Timer", "name": "Timer", "sid": 644444444444401}))
    edit_json(root / "layouts" / "Game.json",
              lambda d: next(i for layer in d["layers"] for i in layer["instances"]
                             if i["type"] == "ScoreText").setdefault("behaviors", {}).update(Timer={"properties": {}}))
    edit_json(root / "project.c3proj",
              lambda p: p["usedAddons"].append({"type": "behavior", "id": "Timer", "name": "Timer",
                                                "author": "Scirra", "bundled": False}))

    def round_end(sheet: dict) -> None:
        restart = next(e for e in game_rows(sheet) if e.get("eventType") == "group" and e.get("title") == "Restart")
        old = next(e for e in restart["children"] if e["eventType"] == "block")
        timer = {"objectClass": "ScoreText", "behaviorType": "Timer"}
        restart["children"] = [
            {"eventType": "comment", "text": "When the last coin is gone, count down to the next round", "sid": 644444444444402},
            {"eventType": "block", "sid": 644444444444408, "conditions": [c for c in old["conditions"] if c["id"] != "trigger-once-while-true"],
             "actions": [{"id": "set-text", "objectClass": "ScoreText", "sid": 644444444444403,
                          "parameters": {"text": "\"Next round soon\""}},
                         {"id": "start-timer", **timer, "sid": 644444444444404,
                          "parameters": {"duration": "3", "type": "once", "tag": "\"next\""}}]},
            {"eventType": "comment", "text": "Then deal the next round", "sid": 644444444444405},
            {"eventType": "block", "sid": 644444444444406,
             "conditions": [{"id": "on-timer", **timer, "sid": 644444444444407, "parameters": {"tag": "\"next\""}}],
             "actions": [a for a in old["actions"] if a["id"] != "wait"]}]
    edit_json(root / "eventSheets" / "Game.json", round_end)


def seed_turn_flip(root: Path) -> None:
    """Two players take turns, and the turn passes in a top-level Else after a test of the round's end:
    Coin.Count = 0 / Else -> Set side to 3 - side runs in every tick while coins are left, so the turn
    flips every tick (docs/decisions/event-sheet-design-guidance.md)."""
    path = root / "eventSheets" / "Game.json"
    sheet = read_json(path)
    rows = game_rows(sheet)
    at = next(i for i, e in enumerate(rows) if e.get("eventType") == "variable" and e.get("name") == "beat") + 1
    rows.insert(at, {"eventType": "variable", "name": "side", "type": "number", "initialValue": "1",
                     "comment": "Whose turn it is, 1 or 2", "isStatic": rows is not sheet["events"], "isConstant": False,
                     "sid": 655555555555501})
    text = {"id": "set-text", "objectClass": "ScoreText"}
    rows.append({"eventType": "group", "disabled": False, "title": "Turns", "description": "",
                 "isActiveOnStart": True, "sid": 655555555555502, "children": [
                     {"eventType": "comment", "text": "When the round is over, nobody taps", "sid": 655555555555503},
                     {"eventType": "block", "sid": 655555555555504,
                      "conditions": [{"id": "compare-two-values", "objectClass": "System", "sid": 655555555555505,
                                      "parameters": {"first-value": "Coin.Count", "comparison": 0,
                                                     "second-value": "0"}}],
                      "actions": [{**text, "sid": 655555555555506,
                                   "parameters": {"text": "\"Round over. Score: \" & score"}}]},
                     {"eventType": "comment", "text": "Otherwise the turn passes to the other player",
                      "sid": 655555555555507},
                     {"eventType": "block", "sid": 655555555555508,
                      "conditions": [{"id": "else", "objectClass": "System", "sid": 655555555555509}],
                      "actions": [{"id": "set-eventvar-value", "objectClass": "System", "sid": 655555555555510,
                                   "parameters": {"variable": "side", "value": "3 - side"}},
                                  {**text, "sid": 655555555555511,
                                   "parameters": {"text": "\"Player \" & side & \" to tap. Score: \" & score"}}]}]})
    write_json(path, sheet)


def seed_no_solid(root: Path) -> None:
    """SolidBarrier without its Solid behavior, on the type and on every instance, and in the used addons when
    no other type uses it: the player's 8 Direction walks through the walls that stop it in the example."""
    types = {p: read_json(p) for p in (root / "objectTypes").glob("*.json")}
    wall = next(p for p, t in types.items() if t.get("name") == "SolidBarrier")
    edit_json(wall, lambda t: t.update(behaviorTypes=[b for b in t["behaviorTypes"] if b["behaviorId"] != "solid"]))
    for path in (root / "layouts").glob("*.json"):
        if not path.name.endswith(".uistate.json"):
            edit_json(path, lambda d: [i.get("behaviors", {}).pop("Solid", None) for layer in d["layers"]
                                       for i in layer["instances"] if i["type"] == "SolidBarrier"])
    if not any(b["behaviorId"] == "solid" for p, t in types.items() if p != wall for b in t.get("behaviorTypes", [])):
        edit_json(root / "project.c3proj",
                  lambda p: p.update(usedAddons=[a for a in p["usedAddons"] if a["id"] != "solid"]))


def seed_door(root: Path) -> None:
    """A Door, a TiledBg with Solid standing on the first floor between the player and the floor's end, and a
    Key, a Sprite with no behaviors behind the player: the platformer template with the art of a locked door
    and no events for it."""
    types = root / "objectTypes"
    all_types = [read_json(p) for p in types.glob("*.json")]
    sprite_ids = [t["image"]["imageSpriteId"] for t in all_types if "image" in t] + \
                 [f["imageSpriteId"] for t in all_types for a in t.get("animations", {}).get("items", []) for f in a["frames"]]
    door = read_json(types / "solidtile.json")
    door.update(name="Door", sid=6666000000001)
    door["behaviorTypes"][0]["sid"] = 6666000000002
    door["image"]["imageSpriteId"] = max(sprite_ids) + 1
    write_json(types / "door.json", door)
    shutil.copy(root / "images" / "solidtile.png", root / "images" / "door.png")
    key = read_json(types / "player.json")
    key.update(name="Key", sid=6666000000003, behaviorTypes=[])
    key["animations"]["items"][0]["sid"] = 6666000000004
    key["animations"]["items"][0]["frames"][0]["imageSpriteId"] = max(sprite_ids) + 2
    write_json(types / "key.json", key)
    shutil.copy(root / "images" / "player-default-000.png", root / "images" / "key-default-000.png")

    edit_json(root / "project.c3proj", lambda p: p["objectTypes"]["items"].extend(["Door", "Key"]))
    layout_path = root / "layouts" / "layout 1.json"
    layout = read_json(layout_path)
    game = next(layer for layer in layout["layers"] if layer["name"] == "Game")
    # Single-global objects (Keyboard) keep their uid in their object type file.
    uid = max([i["uid"] for layer in layout["layers"] for i in layer["instances"]]
              + [t["singleglobal-inst"]["uid"] for t in all_types if "singleglobal-inst" in t])
    tile = next(i for i in game["instances"] if i["type"] == "SolidTile")
    player = next(i for i in game["instances"] if i["type"] == "Player")
    game["instances"] += [
        {**json.loads(json.dumps(tile)), "type": "Door", "uid": uid + 1,
         "world": {**tile["world"], "x": 288, "y": 704, "width": 32, "height": 64, "color": [0.6, 0.35, 0.15, 1]}},
        {**json.loads(json.dumps(player)), "type": "Key", "uid": uid + 2, "behaviors": {},
         "world": {**player["world"], "x": 80, "y": 768, "width": 24, "height": 24, "color": [1, 0.85, 0.2, 1]}}]
    write_json(layout_path, layout)


def seed_name_collision(root: Path) -> None:
    """Spark, a Sprite copied from Coin's JSON that only Collect creates and no layout holds, with two mistakes
    the editor refuses. It kept Coin's sid, which the editor names first: "object class sid already in use".
    Its instance variable z the editor refuses next, as "the name of an expression in Sprite objects", because
    every Sprite has Z whether a layout holds one or not. The spark rises from the collected coin by its z."""
    path = root / "eventSheets" / "Game.json"
    sheet = read_json(path)
    types = [read_json(p) for p in (root / "objectTypes").glob("*.json")]
    sprite_ids = [f["imageSpriteId"] for t in types for a in t.get("animations", {}).get("items", []) for f in a["frames"]]
    spark = read_json(root / "objectTypes" / "Coin.json")
    first = spark["animations"]["items"][0]
    spark.update(name="Spark",
                 instanceVariables=[{"name": "z", "type": "number", "desc": "How far the spark rises, in px.",
                                     "show": True, "sid": 677777777777702}],
                 behaviorTypes=[{"behaviorId": "Tween", "name": "Tween", "sid": 677777777777703}],
                 animations={"items": [{**first, "sid": 677777777777704,
                                        "frames": [{**first["frames"][0], "imageSpriteId": max(sprite_ids) + 1}]}],
                             "subfolders": []})
    write_json(root / "objectTypes" / "Spark.json", spark)
    shutil.copy(root / "images" / "coin-default-000.png", root / "images" / "spark-default-000.png")
    edit_json(root / "project.c3proj", lambda p: p["objectTypes"]["items"].append("Spark"))
    collect = next(e for e in game_rows(sheet) if e.get("eventType") == "custom-ace-block")
    at = next(n for n, a in enumerate(collect["actions"]) if a.get("callFunction") == "AddScore") + 1
    collect["actions"][at:at] = [
        {"id": "create-object", "objectClass": "System", "sid": 677777777777705,
         "parameters": {"object-to-create": "Spark", "layer": "\"Game\"", "x": "Coin.X", "y": "Coin.Y",
                        "create-hierarchy": False, "template-name": "\"\""}},
        {"id": "set-size", "objectClass": "Spark", "sid": 677777777777706,
         "parameters": {"width": "Coin.Width / 3", "height": "Coin.Height / 3"}},
        {"id": "set-instvar-value", "objectClass": "Spark", "sid": 677777777777707,
         "parameters": {"instance-variable": "z", "value": "Coin.Height"}},
        {"id": "tween-one-property", "objectClass": "Spark", "behaviorType": "Tween", "sid": 677777777777708,
         "parameters": {"tags": "\"rise\"", "property": "offsetY", "end-value": "Spark.Y - Spark.z", "time": "0.4",
                        "ease": "easeoutsine", "destroy-on-complete": "yes", "loop": "no", "ping-pong": "no",
                        "repeat-count": "1"}}]
    write_json(path, sheet)


def seed_two_enemies(root: Path, join: str = "&") -> None:
    """Goblin and Orc, two Sprites copied from Coin's JSON, each of which an event 14 on start of layout gives a
    label of its name and IID, as another session left them after the editor refused the project. That session
    had joined the text with +, which the checker passed and the editor refused as a type mismatch: the prompt
    of report-two-enemies quotes the editor's dialog and the sheet lines of join="+"."""
    types = [read_json(p) for p in (root / "objectTypes").glob("*.json")]
    sprite_ids = [f["imageSpriteId"] for t in types for a in t.get("animations", {}).get("items", []) for f in a["frames"]]
    coin = read_json(root / "objectTypes" / "Coin.json")
    first = coin["animations"]["items"][0]
    for n, name in enumerate(("Goblin", "Orc")):
        write_json(root / "objectTypes" / f"{name}.json", {
            **coin, "name": name, "sid": 699999999999910 + n, "behaviorTypes": [],
            "instanceVariables": [{"name": "label", "type": "string", "desc": "Its name and IID, for debugging.",
                                   "show": True, "sid": 699999999999930 + n}],
            "animations": {"items": [{**first, "sid": 699999999999920 + n,
                                      "frames": [{**first["frames"][0], "imageSpriteId": max(sprite_ids) + 1 + n}]}],
                           "subfolders": []}})
        shutil.copy(root / "images" / "coin-default-000.png", root / "images" / f"{name.lower()}-default-000.png")
        edit_json(root / "project.c3proj", lambda p: p["objectTypes"]["items"].append(name))
    edit_json(root / "eventSheets" / "Game.json", lambda sheet: sheet["events"].append({
        "eventType": "block", "sid": 699999999999901,
        "conditions": [{"id": "on-start-of-layout", "objectClass": "System", "sid": 699999999999902}],
        "actions": [{"id": "set-instvar-value", "objectClass": name, "sid": 699999999999903 + n,
                     "parameters": {"instance-variable": "label", "value": f'"{name.lower()} " {join} {name}.IID'}}
                    for n, name in enumerate(("Goblin", "Orc"))]}))


def seed_loop_flag(root: Path) -> None:
    """ScoreText pulses through a function Pulse(looping), whose boolean parameter picks a pulse that loops or
    one that plays once. The round's end calls Pulse(true), and AddScore calls Pulse("0"), a text, which
    reaches the function as true. So after the first coin the score pulses until the round ends."""
    edit_json(root / "objectTypes" / "ScoreText.json",
              lambda t: t["behaviorTypes"].append({"behaviorId": "Tween", "name": "Tween", "sid": 688888888888801}))
    edit_json(root / "layouts" / "Game.json",
              lambda d: next(i for layer in d["layers"] for i in layer["instances"]
                             if i["type"] == "ScoreText")["behaviors"].update(Tween={"properties": {"enabled": True}}))
    sid = iter(range(688888888888802, 688888888888899))
    tween = {"objectClass": "ScoreText", "behaviorType": "Tween"}

    def pulse(loop: str) -> dict:
        return {"id": "tween-one-property", **tween, "sid": next(sid),
                "parameters": {"tags": "\"pulse\"", "property": "offsetOpacity", "end-value": "30", "time": "0.2",
                               "ease": "easeinoutsine", "destroy-on-complete": "no", "loop": loop,
                               "ping-pong": "yes", "repeat-count": "1"}}

    def change(sheet: dict) -> None:
        rows = game_rows(sheet)
        add_score = next(e for e in rows if e.get("eventType") == "function-block")
        add_score["actions"].append({"callFunction": "Pulse", "sid": next(sid), "parameters": ["0"]})
        restart = next(e for e in rows if e.get("eventType") == "group" and e.get("title") == "Restart")
        end = next(e for e in restart["children"] if e["eventType"] == "block")
        end["actions"].insert(0, {"callFunction": "Pulse", "sid": next(sid), "parameters": [True]})
        at = rows.index(add_score) + 1
        rows[at:at] = [
            {"eventType": "comment", "text": "Pulse the score: once for a coin, or on and on while the next round "
                                             "waits", "sid": next(sid)},
            {"functionName": "Pulse", "functionDescription": "Fade the score out and back in", "functionCategory": "",
             "functionReturnType": "none", "functionCopyPicked": False, "functionIsAsync": False,
             "functionParameters": [{"name": "looping", "type": "boolean", "initialValue": "false",
                                     "comment": "Pulse until the layout ends, not once", "sid": next(sid)}],
             "eventType": "function-block", "conditions": [],
             "actions": [{"id": "stop-tweens", **tween, "sid": next(sid), "parameters": {"tags": "\"pulse\""}},
                         {"id": "set-opacity", "objectClass": "ScoreText", "sid": next(sid),
                          "parameters": {"opacity": "100"}}],
             "children": [
                 {"eventType": "block", "sid": next(sid),
                  "conditions": [{"id": "compare-boolean-eventvar", "objectClass": "System", "sid": next(sid),
                                  "parameters": {"variable": "looping"}}],
                  "actions": [pulse("yes")]},
                 {"eventType": "block", "sid": next(sid),
                  "conditions": [{"id": "else", "objectClass": "System", "sid": next(sid)}],
                  "actions": [pulse("no")]}],
             "sid": next(sid)}]
    edit_json(root / "eventSheets" / "Game.json", change)


BIG_SHEET = "Waves"
WAVES = 24
BIG_SHEET_FOCUS = 17


def wave_bonus(wave: int) -> int:
    """The points the end of a wave adds: a different number for each wave, rising with it."""
    return 100 + 20 * wave + (wave % 3) * 7


def big_sheet() -> dict:
    """A sheet of 24 waves in the shape a long game's sheets take, 400 and more numbered events, every group and
    most events under a comment in Chinese, the language whose comments make an outline long: a group per wave
    with a spawn group and a scoring group inside, then the functions the waves call. Built here, from numbers,
    not copied from anyone's game."""
    sid = iter(range(666666666600001, 666666666699999))

    def ace(id_: str, obj: str = "System", **params: object) -> dict:
        return {"id": id_, "objectClass": obj, "sid": next(sid), **({"parameters": params} if params else {})}

    def block(conditions: list, actions: list, children: list | None = None) -> dict:
        ev = {"eventType": "block", "conditions": conditions, "actions": actions, "sid": next(sid)}
        return ev | ({"children": children} if children else {})

    def comment(text: str) -> dict:
        return {"eventType": "comment", "text": text}

    def group(title: str, description: str, children: list) -> dict:
        return {"eventType": "group", "disabled": False, "title": title, "description": description,
                "isActiveOnStart": True, "children": children, "sid": next(sid)}

    def variable(name: str, value: str, note: str, kind: str = "number") -> dict:
        return {"eventType": "variable", "name": name, "type": kind, "initialValue": value, "comment": note,
                "isStatic": False, "isConstant": False, "sid": next(sid)}

    def wave_is(n: int) -> dict:
        return ace("compare-eventvar", variable="wave", comparison=0, value=str(n))

    events: list = [
        comment("波次表：每一波生成的金币数量、生成间隔和结束奖励都写在这里，按波次分组，改数值时只改对应的那一组"),
        variable("wave", "1", "当前波次，从 1 开始，打完最后一波后回到 1"),
        variable("spawnLeft", "0", "本波还要生成的金币数量，生成一个减一"),
        variable("spawnGap", "1", "本波两次生成之间的秒数"),
        variable("waveScore", "0", "本波已经拿到的分数，换波时清零"),
    ]
    for n in range(1, WAVES + 1):
        count, gap = 4 + n % 5 + n // 6, round(1.6 - 0.04 * n, 2)
        spawn = group(f"Wave {n} spawn", f"第{n}波的生成规则：数量 {count}，间隔 {gap} 秒", [
            comment(f"第{n}波开始：设定本波数量和间隔，清空本波分数"),
            block([wave_is(n), ace("trigger-once-while-true")],
                  [ace("set-eventvar-value", variable="spawnLeft", value=str(count)),
                   ace("set-eventvar-value", variable="spawnGap", value=str(gap)),
                   ace("set-eventvar-value", variable="waveScore", value="0")],
                  [block([ace("compare-eventvar", variable="spawnLeft", comparison=4, value="6")],
                         [ace("set-eventvar-value", variable="spawnGap", value=str(round(gap * 0.9, 2)))])]),
            comment("按间隔生成金币，生成一个就把剩余数量减一"),
            block([wave_is(n), ace("every-x-seconds", **{"interval-seconds": "spawnGap"}),
                   ace("compare-eventvar", variable="spawnLeft", comparison=4, value="0")],
                  [ace("subtract-from-eventvar", variable="spawnLeft", value="1")],
                  [block([], [{"callFunction": "SpawnCoin", "sid": next(sid),
                               "parameters": [f"{n % 3}", f"{(n * 7) % 5}"]}])]),
            comment("剩下最后两个的时候加快生成，让波次的结尾更紧张"),
            block([wave_is(n), ace("compare-eventvar", variable="spawnLeft", comparison=3, value="2")],
                  [ace("set-eventvar-value", variable="spawnGap", value=str(round(gap / 2, 2)))]),
        ])
        score = group(f"Wave {n} score", f"第{n}波的计分：每个金币的分数和本波结束时的奖励", [
            comment("本波每拿到一个金币，本波分数加上这一波的倍数"),
            block([wave_is(n), ace("compare-two-values", **{"first-value": "Coin.Count", "comparison": 2,
                                                             "second-value": "spawnLeft + 1"})],
                  [ace("add-to-eventvar", variable="waveScore", value=str(1 + n // 4))]),
            comment("本波分数超过门槛时额外加一分，门槛随波次升高"),
            block([wave_is(n), ace("compare-eventvar", variable="waveScore", comparison=5, value=str(10 + 2 * n)),
                   ace("trigger-once-while-true")],
                  [ace("add-to-eventvar", variable="waveScore", value="1")]),
            block([wave_is(n), ace("compare-eventvar", variable="waveScore", comparison=5, value=str(20 + 3 * n)),
                   ace("trigger-once-while-true")],
                  [ace("add-to-eventvar", variable="waveScore", value="2")]),
            comment(f"第{n}波结束：金币全部生成并且被收走，发放本波奖励，然后进入下一波"),
            block([wave_is(n), ace("compare-eventvar", variable="spawnLeft", comparison=0, value="0"),
                   ace("compare-two-values", **{"first-value": "Coin.Count", "comparison": 0, "second-value": "0"}),
                   ace("trigger-once-while-true")],
                  [{"callFunction": "GiveBonus", "sid": next(sid), "parameters": [str(wave_bonus(n))]},
                   ace("add-to-eventvar", variable="wave", value="1")]),
            comment("最后一波之后回到第一波"),
            block([ace("compare-eventvar", variable="wave", comparison=4, value=str(WAVES))],
                  [ace("set-eventvar-value", variable="wave", value="1")]),
        ])
        text = group(f"Wave {n} text", f"第{n}波的提示文字", [
            comment("波次开始时在回合文字上显示第几波，清场时换成清场提示"),
            block([wave_is(n), ace("trigger-once-while-true")],
                  [ace("set-text", "RoundTag", text=f'"第{n}波"')]),
            block([wave_is(n), ace("compare-eventvar", variable="spawnLeft", comparison=0, value="0"),
                   ace("compare-two-values", **{"first-value": "Coin.Count", "comparison": 0, "second-value": "0"})],
                  [ace("set-text", "RoundTag", text='"清场"')]),
            block([wave_is(n), ace("compare-eventvar", variable="waveScore", comparison=5, value=str(30 + 3 * n))],
                  [ace("set-text", "ScoreLabel", text='"好"')]),
        ])
        events.append(group(f"Wave {n}", f"第{n}波：先生成，再计分", [spawn, score, text]))
    events += [
        comment("生成一个金币：列和行由调用的波次给出，位置落在棋盘的格子上"),
        {"functionName": "SpawnCoin", "functionDescription": "在棋盘的一个格子上生成一个金币", "functionCategory": "",
         "functionReturnType": "none", "functionCopyPicked": False, "functionIsAsync": False,
         "functionParameters": [{"name": "column", "type": "number", "initialValue": "0", "comment": "列", "sid": next(sid)},
                                {"name": "row", "type": "number", "initialValue": "0", "comment": "行", "sid": next(sid)}],
         "eventType": "function-block", "conditions": [],
         "actions": [ace("create-object", **{"object-to-create": "Coin", "layer": "\"Game\"",
                                             "x": "592 + 192 * column", "y": "400 + 192 * row",
                                             "create-hierarchy": False, "template-name": "\"\""})],
         "sid": next(sid)},
        comment("发放奖励：把奖励加进总分，并在分数文字上显示出来"),
        {"functionName": "GiveBonus", "functionDescription": "加上一波的奖励分数", "functionCategory": "",
         "functionReturnType": "none", "functionCopyPicked": False, "functionIsAsync": False,
         "functionParameters": [{"name": "points", "type": "number", "initialValue": "0", "comment": "奖励的分数",
                                 "sid": next(sid)}],
         "eventType": "function-block", "conditions": [],
         "actions": [{"callFunction": "AddScore", "sid": next(sid), "parameters": ["points"]}],
         "sid": next(sid)},
    ]
    return {"name": BIG_SHEET, "events": events, "sid": next(sid)}


def seed_big_sheet(root: Path) -> None:
    """A second sheet of 400 and more events beside the stand-in's own, listed in project.c3proj and used by no
    layout, so the coins game plays as before; the case reads it."""
    write_json(root / "eventSheets" / f"{BIG_SHEET}.json", big_sheet())
    edit_json(root / "project.c3proj", lambda p: p["eventSheets"]["items"].append(BIG_SHEET))


# fixture -> (the fixture it starts from, the fault written into it). The seeded entries' sids start
# with 6333, 6444, 6555, 6666, 6777, 6888 or 6999, so a grader can tell the example's own events from them.
SEEDS = {"families-key-pressed": ("example:families", seed_key_pressed),
         "coins-timer-restart": ("coins", seed_timer_restart),
         "coins-turn-flip": ("coins", seed_turn_flip),
         "coins-name-collision": ("coins", seed_name_collision),
         "coins-two-enemies": ("coins", seed_two_enemies),
         "coins-loop-flag": ("coins", seed_loop_flag),
         "persistent-walls": ("example:persistent-layouts", seed_no_solid),
         "platformer-door": ("example:template-platformer", seed_door),
         "coins-big-sheet": ("coins", seed_big_sheet)}


def seed_inverted_start(root: Path) -> None:
    """The first On start of layout of eventSheets/Game.json inverted, a trigger the editor refuses to load: a
    change made between two turns of a session, which only a check run after it finds. It keeps every sid."""
    path = root / "eventSheets" / "Game.json"
    sheet = read_json(path)

    def conditions(events: list):
        for ev in events:
            yield from ev.get("conditions", [])
            yield from conditions(ev.get("children", []))

    next(c for c in conditions(sheet["events"]) if c.get("id") == "on-start-of-layout")["isInverted"] = True
    write_json(path, sheet)


# A case's "between": the change run_session.py writes into the project between two turns.
BETWEEN = {"inverted-start": seed_inverted_start}


END_MARKER = "# ==== construct3-agent-plugin helpers: end"
PLATFORMER_GAME = Path(__file__).parent / "platformer_game.py"


def with_settings(template: str, **values: str) -> str:
    """The template with each setting line `NAME = ...` given a new value, its comment kept. VIEW is the line
    `VIEW_W, VIEW_H = ...`."""
    for name, value in values.items():
        key = "VIEW_W, VIEW_H" if name == "VIEW" else name
        lines = template.split("\n")
        at = next(n for n, line in enumerate(lines) if line.startswith(f"{key} = "))
        line = lines[at].rstrip("\r")
        old, hash_, comment = line[len(key) + 3:].partition("#")
        lines[at] = (f"{key} = " + (f"{value.ljust(len(old) - 1)} {hash_}{comment}" if hash_ else value)
                     + lines[at][len(line):])
        template = "\n".join(lines)
    return template


def platformer(template: str) -> str:
    """The template's settings and helpers with the game part of platformer_game.py below its end marker."""
    at = template.index(END_MARKER)
    end = template.index("\n", at) + 1
    newline = "\r\n" if template[at:end].endswith("\r\n") else "\n"
    game = PLATFORMER_GAME.read_text(encoding="utf-8").replace("\n", newline)
    return with_settings(template[:at], PROJECT_NAME='"Hills"') + template[at:end] + newline * 2 + game


# fixture -> what it changes in the arm's own template before the first run: the viewport for a stand-in on
# another screen, or the game. Each keeps its generator, the task being a change to tools/build_project.py.
GENERATED: dict[str, Callable[[str], str]] = {
    "coins-generator": lambda template: template,
    "coins-portrait": lambda template: with_settings(template, VIEW="720, 1280", ORIENTATION='"portrait"'),
    "coins-pixel": lambda template: with_settings(template, VIEW="320, 180"),
    "platformer-generator": platformer,
    "coins-look-refs": lambda template: template,
}
# fixture of GENERATED -> the folder of pictures copied into the project after its generator ran, and its name there:
# the user's references, which the user leaves where they like
PICTURES = {"coins-look-refs": (Path(__file__).parent / "look-refs", "look-refs")}


def digest(project: Path) -> dict:
    """The game's own files by hash, line endings aside, and the sids of the
    sheet's events; grade.py reads it to see what a run changed or lost."""
    def sids(events: list) -> list[int]:
        return [s for ev in events for s in ([ev["sid"]] if "sid" in ev else []) + sids(ev.get("children", []))]

    out: dict = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                 for p in sorted(project.rglob("*"))
                 if p.is_file() and p.name != "AGENTS.md"
                 and not {".agents", "__pycache__", "tools", ".git", ".tmp"} & set(p.parts)}
    for path in sorted((project / "eventSheets").rglob("*.json")):
        if not path.name.endswith(".uistate.json"):
            out[f"{path.relative_to(project).as_posix()}.sids"] = sids(read_json(path)["events"])
    return out


def warnings_of(project: Path, plugin: Path = PLUGIN) -> list[str]:
    """The checker's warning lines on the fixture: the project's own, which grade.py does not charge to a run."""
    p = subprocess.run([sys.executable, str(plugin / SKILL.relative_to(PLUGIN) / "scripts" / "check_project.py"),
                        "--project", str(project), "--rag", str(plugin), "--limit", "0"], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return [line for line in p.stdout.splitlines() if line.startswith("warning:")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs_dir", metavar="RUNS_DIR", help="a new or empty folder outside the clone, one per iteration")
    ap.add_argument("--arms", nargs="+", default=["with_skill", "without_skill"], metavar="ARM",
                    help="folders to lay out per test case; without_... gets no skill, old_... the one of --old-clone")
    ap.add_argument("--cases", nargs="+", metavar="NAME",
                    help="test cases by name (default: all of evals.json but the held-out ones)")
    ap.add_argument("--held-out", action="store_true",
                    help="lay out the held-out cases too, or the ones --cases names. Use it once a change is otherwise done")
    ap.add_argument("--old-clone", metavar="FOLDER", help="a checkout of the clone before the change, for old_... arms")
    ap.add_argument("--examples", metavar="FOLDER",
                    default=str(c3.siblings_folder(REPO) / "Construct-Example-Projects" / "example-projects"),
                    help="the example-projects folder of the Construct-Example-Projects clone (default: beside this "
                         "clone, or beside its main working tree from a worktree)")
    pinning = ap.add_mutually_exclusive_group()
    pinning.add_argument("--pin", default="HEAD", metavar="REV",
                         help="the commit the with_... arms are laid out from, as a detached worktree in RUNS_DIR "
                              "(default: HEAD)")
    pinning.add_argument("--no-pin", action="store_true", help="lay out from this checkout as it stands")
    args = ap.parse_args()

    out = Path(args.runs_dir).resolve()
    if out.is_relative_to(REPO):
        sys.exit(f"{out} is inside the clone {REPO}: an agent started there reads the clone's AGENTS.md; "
                 f"name a folder outside it, such as one under the system's temporary directory")

    installers = {}
    if any(arm.startswith("old_") for arm in args.arms):
        installers["old_"] = Path(args.old_clone or "") / SKILL.relative_to(REPO) / "scripts" / "install.py"
        if not args.old_clone or not installers["old_"].exists():
            sys.exit(f"an old_... arm needs --old-clone, a checkout that holds "
                     f"{SKILL.relative_to(REPO).as_posix()}/scripts/install.py")
    unknown = set(args.cases or []) - {c["name"] for c in CASES}
    if unknown:
        sys.exit(f"no test case named {', '.join(sorted(unknown))}; evals.json has: {', '.join(c['name'] for c in CASES)}")
    held = sorted(c["name"] for c in CASES if c.get("held_out") and c["name"] in (args.cases or []))
    if held and not args.held_out:
        sys.exit(f"{', '.join(held)} {'is' if len(held) == 1 else 'are'} held out of tuning (dev/AGENTS.md, Evals): "
                 f"add --held-out once the change is otherwise done, or name the other cases")
    chosen = [c for c in CASES if (c["name"] in args.cases if args.cases else args.held_out or not c.get("held_out"))]

    plugin, commits = PLUGIN, {"with_": None, "old_": commit_of(Path(args.old_clone)) if "old_" in installers else None}
    if not args.no_pin:
        out.mkdir(parents=True, exist_ok=True)
        folder, commits["with_"] = pin(out, args.pin)
        plugin = folder / PLUGIN.relative_to(REPO)
        (out / "clone.json").write_text(json.dumps({"commit": commits["with_"], "folder": folder.as_posix(),
                                                    "old_clone": commits["old_"]}, indent=2), encoding="utf-8")
    skill = plugin / SKILL.relative_to(PLUGIN)
    installers["with_"] = skill / "scripts" / "install.py"

    with tempfile.TemporaryDirectory() as tmp:
        game = stand_in(Path(tmp) / "coins", skill)
        for case in chosen:
            fixture, seed = SEEDS.get(case["fixture"], (case["fixture"], None))
            source = game
            if fixture == "empty":
                source = Path(tmp) / "empty"
                if not source.exists():
                    run(str(skill / "scripts" / "new_project.py"), str(source), cwd=Path(tmp))
            elif fixture.startswith("example:"):
                source = Path(args.examples) / fixture.split(":", 1)[1]
                if not (source / "project.c3proj").exists():
                    sys.exit(f"{source} is not a folder project; --examples is the example-projects folder of the "
                             f"Construct-Example-Projects clone")
            for arm in args.arms:
                target = out / case["name"] / arm / "project"
                if target.exists():
                    sys.exit(f"{target} exists; name a new folder for a new iteration")
                shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.uistate.json"))
                (target.parent / "outputs").mkdir()
                if case["fixture"] == "coins-load-errors":
                    seed_load_errors(target)
                if seed:
                    seed(target)
                prefix = next((prefix for prefix in installers if arm.startswith(prefix)), None)
                installer = installers.get(prefix)
                if installer:
                    into = ["--into", ".claude/skills"] if arm.startswith("with_claude") else []
                    run(str(installer), "--project", str(target), *into, cwd=target)
                if case["fixture"] in GENERATED:
                    # The game keeps its generator, the template of the arm's own skill as GENERATED changes
                    # it, run once so the files are that generator's: the task is a change to
                    # tools/build_project.py and a rerun.
                    if not installer:
                        sys.exit(f"{case['name']} needs a skill: its generator checks with the skill's checker; "
                                 f"lay it out with with_... and old_... arms only")
                    # The stand-in of the arm's own template, from the seed stand_in() starts with: what
                    # another template generated would stay beside it, unlisted.
                    for item in target.iterdir():
                        if item.name not in (".agents", ".claude", ".git", "AGENTS.md", "CLAUDE.md"):
                            shutil.rmtree(item) if item.is_dir() else item.unlink()
                    (target / "project.c3proj").write_text(json.dumps({"uniqueId": "eval", "properties": {}}),
                                                           encoding="utf-8")
                    (target / "tools").mkdir()
                    # Bytes, so the template keeps its line endings and its helpers their stamp
                    template = (installer.parent.parent / "assets" / "build_project.py").read_bytes().decode("utf-8")
                    (target / "tools" / "build_project.py").write_bytes(
                        GENERATED[case["fixture"]](template).encode("utf-8"))
                    run("tools/build_project.py", cwd=target)
                    if case["fixture"] in PICTURES:
                        source_folder, name = PICTURES[case["fixture"]]
                        shutil.copytree(source_folder, target / name, ignore=shutil.ignore_patterns("*.svg"))
                commit = {"clone.commit": commits[prefix]} if commits.get(prefix) else {}
                (target.parent / "fixture.json").write_text(json.dumps(digest(target) | commit | {
                    "check_project.warnings": warnings_of(target, plugin)}, indent=2), encoding="utf-8")
                print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
