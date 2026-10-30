---
name: construct3-agent-plugin
description: Check, read, look up and generate the JSON of a Construct 3 folder project (project.c3proj, eventSheets, layouts, objectTypes, families) against the schemas of every Construct 3 condition, action, expression and effect and the rules the Construct 3 editor applies when it opens a project. Use this skill whenever you write or edit an event sheet or any other project file of a Construct 3 game, need the exact id, parameters and JSON of a condition, action or expression, want to read an event sheet or an official example as events instead of JSON, generate a whole project from a script, or the editor refuses to open or preview a project, even if the user only says "add a mechanic", "fix this event" or pastes an editor error.
compatibility: Requires Python 3.10+ and the plugin folder of a Construct3-Agent-Skills clone or the installed Claude Code plugin, whose data/c3-schemas the scripts read. art.py needs Pillow for the pictures of an image tool, and the other scripts say when an optional tool is missing. Opening the project in the editor takes a network connection and Edge, Chrome or Chromium, or a browser tool of the agent.
metadata:
  source: https://github.com/XHXIAIEIN/Construct3-Agent-Skills
---

# Construct 3 project files

Scripts for the JSON of a Construct 3 project saved as a folder. They read
the Construct3-RAG schemas, so a name they accept exists and a name they
reject does not. The checker reads the files alone. The editor also reads
the expressions, so it can refuse a project that the checker passes.

## Where things are

- Commands here are written from this skill's folder. From the project
  root, the folder this file is in goes before them, for example
  `python .agents/skills/construct3-agent-plugin/scripts/check_project.py`.
  The scripts find the project from the current directory upward;
  `--project <folder>` names another one.
- The scripts find the data folder through `--rag`, the `CONSTRUCT3_RAG`
  environment variable, or the `Construct3-RAG: <folder>` line in the
  project's `AGENTS.md` or `CLAUDE.md`. `Construct3-RAG not found` means
  that line is empty; its value is the Agent-Skills clone's `plugin/`
  folder. `CONSTRUCT3_RAG_OFFLINE=1` stops the hourly update check of
  `check_project.py`.
- As the Claude Code plugin, the skill is `construct3:construct3-agent-plugin`
  and the scripts run from this folder, so the game project needs no copy.
  In the files of this skill, `Construct3-RAG/` before `data/` stands for
  `${CLAUDE_PLUGIN_ROOT}/`, and `Construct3-Agent-Skills/docs/` paths are not
  in the plugin. The sub-agent `construct3:project-worker` has only the
  tools these scripts need.
- `python scripts/install.py --project <game folder>` copies this folder to
  the project's `.agents/skills/` and adds the Construct 3 block to its
  `AGENTS.md` (`--into .claude/skills` for Claude Code, `.trae/skills` for
  TRAE). A copy that differs from the clone's prints the command that
  refreshes it.

## Before the first edit

- The project has no `.git`: `git init` in it before the first edit, so that
  every change can be seen and undone.
- Commit on the branch `agents`, never on the user's own branch: `git switch
  agents`, or `git switch -c agents` the first time. Commit after each
  finished change, one commit per fix or review item, the message naming it;
  the user reviews `agents` and merges it. At the hand-over, give the user
  the events that changed, not the JSON diff:
  `python scripts/print_sheet.py --since <the user's branch>`.
- Before you design an interaction, read
  `Construct3-Cookbook/guides/design/thinking.md` and run
  `scripts/search_guides.py` with the interaction's words.

## Scripts

| Script | Use |
|--------|-----|
| `scripts/lookup_ace.py OBJECT [WORD ...]` | The conditions, actions and expressions of a project object, `System`, a plugin or a behavior, with their parameters and the JSON to write; or an effect's parameters |
| `scripts/lookup_script_api.py NAME ...` | The scripting API: an interface's members, or a member's declaration |
| `scripts/search_guides.py WORD ...` | The pitfalls and official examples that hold the words |
| `scripts/print_sheet.py [SHEET ...] [--events A-B]` | A sheet as the editor words it, under its event numbers; `--map` the layouts that run each sheet, `--find NAME` the events that use a name, `--since COMMIT` what changed |
| `scripts/print_layout.py [LAYOUT ...]` | Layers and instances in Z order with box, size and text, `on no object` for a label off its button |
| `scripts/edit_sheet.py SHEET PLAN.json` | A change to a sheet, as a plan on its event numbers, checked before anything is written; `--new` creates the sheet |
| `scripts/verify_change.py` | Runs the four scripts below and the look in order, each again only when the files changed; its last line names the next step. `--status` prints where the checks stand |
| `scripts/check_project.py` | Its first step: every project file against the schemas and the editor's load rules; it passes when the last line starts with `ok:`. Alone: `--style` for a project the agent wrote, `--review` for one someone asks about |
| `scripts/review_design.py` | Its second step, `--check`: the full checker, then design findings and questions; [references/design-review.md](references/design-review.md) covers `--prepare` |
| `scripts/open_in_editor.py` | Its editor step: `opened`, or `failed` with the editor's message; `--preview` also runs the game for a few seconds and prints its errors, `--install-addon` installs a custom addon first. The first run takes up to 40 seconds |
| `scripts/preview_project.py PLAN.json` | Play the preview from a plan: tap, drag, press keys, wait `until` an expression holds, read the state, take screenshots. `--keep NAME` keeps a plan that passes; `verify_change.py` replays the kept ones |

[references/scripts.md](references/scripts.md) lists the scripts for a new
game's design, the look, sounds, a picture of a sheet, Advanced Random,
export, packing, art, a new project and the install, with the generator
template and the runtime probe.

Each script prints its options and examples with `--help`. A script stops
at about 10 000 characters and its last line says how to get the rest;
`--limit 0` prints everything.

`verify_change.py` takes minutes once it opens the editor. A finding names
its place, `sheet Game event 15 action 2`, and what to write. `stop:` names
a finding that two changes left standing. A yes of the look review fails
the look step until the third round, which passes it. Exit code 3 or a
`skipped:` line is a check that did not run; exit code 2 and `stopped at`
give the cause. `pack_project.py` refuses files that the check has not
passed.

## Facts

- The Construct 3 editor keeps the files as it loaded them. A save there
  writes each file edited in the editor over a change made on disk, with no
  warning.
- A sheet's JSON is indented seven to seventeen tabs deep, and an
  exact-match edit of several lines there fails one time in three.
  `edit_sheet.py` edits by event number instead.
- `plugins/system.json` and `plugins/_common.json` run to thousands of
  lines, more than most file tools return at once, so an ACE below the cut
  looks missing there. `lookup_ace.py` reads the whole file.
- *Pick nearest/furthest*, *Is overlapping* and *Set color* belong to every
  world object, not to System or the plugin: `lookup_ace.py Coin nearest`
  finds them on an object of the project.
- A trigger fires only in a sheet that the running layout runs, by its own
  sheet or an include.
- In pixel art the labels are Sprite Fonts, which draw only the characters
  baked into them. `python scripts/bake_font.py` bakes the characters of a
  changed text.
- A generated game's pictures come through `art()`, and
  `python scripts/art.py` runs after the generator. Without an image
  generation tool, it hands the drawings to a `construct3:art-drawer`
  sub-agent. Never compute a picture pixel by pixel in Python: with nothing
  to hold a style, it mixes styles.

## Look an ACE up

An ACE missing from the schema does not exist, unless the lookup says it is
deprecated: the editor still opens a project that uses it.

```bash
python scripts/lookup_ace.py Coin tween two
```

```
action tween-two-properties - Tween (two properties) [behavior Tween, tween]  <isAsync>
  Tween two properties, such as the position (consisting of an X and Y co-ordinate).
  write: {"id": "tween-two-properties", "objectClass": "Coin", "behaviorType": "Tween", "sid": <new sid>, "parameters": {"tags": "\"\"", "property": "position", ...}}
    tags                   string     Optional space-separated list of many tags to identify a tween.
                                      (expression string, text in inner quotes: "\"hello\"")
    property               combo      The properties to tween.  (position | size | scale)
    ease                   ease       The easing function to use.  (bare id of a built-in ease: noease, easeinoutsine, easeoutback ...)
```

The `write:` line is the JSON with its values to replace. `edit_sheet.py`
gives every new entry its sid, so a plan leaves `"sid"` out; in a hand edit
it is a 15-digit number the project does not use yet. A combo item whose
name differs from its id prints both, `id: name`: the id goes in the JSON,
the name is what the editor shows. An expression prints the way it is
reached, `Coin.Tween.Progress(tags)`.

## Read a sheet as events

```bash
python scripts/print_sheet.py Game
```

```
   5   Touch: On touched Coin (start)
           -> Coin: Collect()
   9   System: Coin.Count = 0
       System: Trigger once
           -> System: Wait 1 seconds (use time scale: True)
```

The numbers are the editor's: the margin of the event sheet and the
**Where** column of its Find results. An official example prints the same
way, `--project <Construct-Example-Projects>/example-projects/template-snake`.
A long sheet prints in parts; `--events 40-80` starts with the events the
range sits in.

## Change a sheet with a plan

A plan holds the operations as JSON in a file of their own.
`python scripts/edit_sheet.py --help` gives every operation with its JSON.

```json
[
  {"before": 2, "line": "group Setup", "events": [{"eventType": "variable", "name": "best", "initialValue": "0", "isStatic": true}]},
  {"event": 10, "line": "Coin.Count = 0", "position": 1, "add-actions": [
    {"id": "set-eventvar-value", "objectClass": "System", "parameters": {"variable": "best", "value": "max(best, score)"}}]}
]
```

```bash
python scripts/edit_sheet.py Game plan.json
```

Every number is an event number of the sheet as it prints now, whatever the
operations above it do. `"line"` is the line the print shows for that
event, so a number from an older print is refused. Nothing is written
unless the whole plan holds: a problem the plan would add is printed under
its operation with the file left as it was. A pass ends with the changed
events under their new numbers and the checker's last line. `--dry-run`
writes nothing.

## Where the rest is

| File | Holds |
|------|-------|
| [references/designing-a-game.md](references/designing-a-game.md) | A new game as a design, checked and played as a prototype |
| [references/generating-a-project.md](references/generating-a-project.md) | A project written as one Python generator: its markers, the art, the look and the look checks |
| [references/checker-rules.md](references/checker-rules.md) | What each checker finding means, and editor errors the checker lets through |
| [references/export-project.md](references/export-project.md) | Export |
| [references/reading-the-runtime.md](references/reading-the-runtime.md) | What an event did in the preview |
| [references/reporting-a-problem.md](references/reporting-a-problem.md) | A problem report about the skill |
| `Construct3-Cookbook/guides/design/thinking.md` | The built-in to use before a variable or an *Every tick*, and what replaces a superseded feature |
| `Construct3-Cookbook/guides/design/style.md` | How the official sheets are organised, named and commented |
| `Construct3-Cookbook/guides/project-files/hand-editing.md` | Function and custom action blocks and their calls, `projectfile` parameters, a family's behavior through a member type |
