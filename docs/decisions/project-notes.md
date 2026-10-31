# A Game Keeps the Facts a Check Showed, on the Events They Rest On

Date: 2026-10-31

## Problem

A check of a change starts with facts about the game: the function that
reaches a scene and the parameters it takes, the trigger that starts a flow,
the first-launch tutorial to finish or skip, the variable behind a feel
(`references/verifying-a-change.md`, steps 3 to 6). A session finds them by
reading the sheets and by probes in the preview. The kept plans of
`tools/plans/` keep the checks, not these facts, so each later session on the
same game finds them again, and a fact that an edit has made false reads as
true in an old answer or plan.

## Evidence

- Aura Autopilot, a playtesting agent for Unreal, Unity and Godot
  (<https://github.com/ramenvr/autopilot>, `autopilot/agents/session.py`),
  keeps a `notes.md` of verified facts per game. Its first message to the
  agent holds the notes and the code files changed since the last run, each
  with the lines of the notes that name it. Such a file stays listed, run
  after run, until a run edits the note that names it.
- Event numbers move when an event is added above them. A function's name
  and a group's title stay through most edits. A sid stays through an edit in
  the editor or by `edit_sheet.py`, and a generator run gives every sid
  anew, which is why `print_sheet.py --since` matches events by content
  first.

## Options

1. A Markdown file of free lines, as in autopilot, with the sheet named in
   the text. A file name is a word that a script can find in a line, but a
   function or a group is not, so nothing marks a note whose events changed.
2. A file that a script writes, each note with its sheet and its function,
   group or event, and a stamp of those events. A note is marked when the
   events differ from the stamp, and the mark stays until the note is
   stamped again.
3. Option 2 with a commit in place of the stamp. A note that is added before
   its change is committed would compare with the commit before the change,
   and its own change would mark it at once.

## Decision

Option 2.

- The notes are in `tools/notes.json`, beside the kept plans, committed with
  the project. The editor ignores `tools/`. `verify_change.py` leaves the
  file out of the digest of its steps, as it leaves out the kept plans, so a
  note voids no answer and reruns no editor step.
- `scripts/notes.py` adds, prints, rewrites, confirms and removes notes. A
  note is one fact of at most 240 characters with its sheet and a function
  or custom action by name, a group by title, or an event by the number that
  `print_sheet.py` prints. The script keeps the sid of an event and finds it
  by its sid, else by its content.
- The stamp is a hash of the events without their sids. A group's stamp
  covers every event in it. A changed note prints what changed under it, as
  `print_sheet.py --since` prints it, against the last commit of the sheet
  whose events match the stamp. Without such a commit, it prints the events
  as they are.
- The agent reads the notes where it plans a check: step 3 of
  `references/verifying-a-change.md` starts from `notes.py`, and step 9 says
  when a fact goes in. Once the checker passes, `verify_change.py` prints a
  `notes:` line that names the marked notes, run after run, until each is
  confirmed or rewritten. `verify_change.py --status` names every note.
  `SKILL.md` names the script in its sentence on `references/scripts.md`
  and holds no rule about the notes, because most runs check no game in the
  preview.
- A fact goes in once a probe or a kept plan has shown it in the running
  game, not from the events alone, because a fact read from the events is
  what the check is there to test.
- The Construct 3 block of the game's instruction file does not name the
  notes. A session that plans a check reaches them through the reference and
  `verify_change.py`, and the block stays the same for every game.

## Re-evaluate when

- A run checks a change in the preview without reading the notes that held
  the fact it searched for.
- Notes go stale with no mark, through an edit outside the event sheets,
  such as a layout or an object type that a fact depends on.
