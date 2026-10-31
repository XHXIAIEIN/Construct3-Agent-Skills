# A Game Keeps the Facts a Check Showed, on the Events They Rest On

Date: 2026-10-31

## Problem

A check of a change starts with facts about the game: the function that
reaches a scene and the parameters it takes, the trigger that starts a flow,
the first-launch tutorial to finish or skip, the variable behind a feel
(`references/verifying-a-change.md`, steps 3 to 6). A session finds them by
reading the sheets and by probes in the preview. The kept plans of
`tools/plans/` keep the checks, not these facts, so each later session on the
same game finds them again. A fact that an edit has made false still reads as
true in an old answer or plan.

## Evidence

- Aura Autopilot, a playtesting agent for Unreal, Unity and Godot
  (<https://github.com/ramenvr/autopilot>, `autopilot/agents/session.py`),
  keeps a `notes.md` of verified facts per game. Its first message to the
  agent holds the notes and the code files changed since the last run, each
  with the lines of the notes that name it. Such a file is listed on every
  run until a run edits the note that names it.
- Event numbers move when an event is added above them. A function's name
  and a group's title stay through most edits. A sid stays through an edit in
  the editor or by `edit_sheet.py`.
- A generator run gives every sid anew. So `print_sheet.py --since` matches
  events by their content first.
- In iteration 94 (`.local/docs/evidence/skill-evals/construct3-agent-plugin/iteration-94/`),
  four runs of `check-the-third-round` each read `SKILL.md`, printed the
  sheet, read `preview_project.py --help` and wrote their plan. None opened
  `verifying-a-change.md` or ran `notes.py`, although the project held notes
  for the facts they needed. A note reaches a run only in output the run
  reads anyway.

## Options

1. A Markdown file of free lines, as in autopilot, with the sheet named in
   the text. A file name is a word that a script can find in a line, but a
   function or a group is not. So nothing marks a note whose events changed.
2. A file that a script writes, each note with its sheet and its function,
   group or event, and a stamp of those events. A note is marked when the
   events differ from the stamp, and the mark stays until the note is
   stamped again.
3. Option 2 with a commit in place of the stamp. A note that is added before
   its change is committed would compare with the commit before the change.
   Its own change would then mark it at once.

## Decision

Option 2.

- The notes are in `tools/notes.json`, beside the kept plans, committed with
  the project. The editor ignores `tools/`.
- `verify_change.py` leaves the file out of the digest of its steps, as it
  does the kept plans. So a note voids no answer and reruns no editor step.
- `scripts/notes.py` adds, prints, rewrites, confirms and removes notes. A
  note is one fact of at most 240 characters. It names its sheet and one of
  these: a function or custom action by name, a group by title, or an event
  by the number that `print_sheet.py` prints.
- The script keeps the sid of an event. It finds the event by that sid, and
  by its content when no event has the sid.
- The stamp is a hash of the events without their sids. A group's stamp
  covers every event in it.
- A changed note prints what changed under it, as `print_sheet.py --since`
  prints it. The comparison is with the last commit of the sheet whose
  events match the stamp. Without such a commit, the note prints its events
  as they are.
- The notes reach a run in the output it reads before and after a check. A
  whole print of `print_sheet.py` ends with the notes on its sheets, marks
  included. A plan of `preview_project.py` that passes prints the
  `notes.py --add` command. Once the checker passes, `verify_change.py`
  prints a `notes:` line with the marked notes on every run, until each is
  confirmed or rewritten, and `--status` names every note.
- Steps 3 and 9 of `references/verifying-a-change.md` say where the notes
  are and when a fact goes in. A fact goes in once a probe or a kept plan
  has shown it in the running game, because a fact read from the events is
  what the check tests.
- `SKILL.md` names `notes.py` only in its sentence on `references/scripts.md`,
  because the scripts print the notes where a run needs them. The Construct 3
  block of the game's instruction file stays the same for every game, and
  the notes reach a session through the scripts.

## Re-evaluate when

- A run checks a change in the preview and searches for a fact that a note
  on the printed sheet holds.
- A note goes stale with no mark, through an edit outside the event sheets,
  such as a layout or an object type that the fact depends on.
