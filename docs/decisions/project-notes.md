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

- An open-source playtesting agent for Unreal, Unity and Godot keeps a
  `notes.md` of verified facts per game. Its first message to the
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
- In iteration 95, with the notes at the end of a whole print of the sheet,
  both runs of the changed skill got them before they planned, and neither
  run of the previous skill did. Every run of both iterations passed, so the
  case shows where the notes reach a run, not what they save.
- The case `four-coins-in-round-two` needs a fact that the notes of its
  game hold: on a first launch, the first round's coin pulses with a looping
  Tween until the first touch ends, and Input ignores a touched coin while a
  Tween plays. A plan that taps the coin first never reaches the second
  round. In iteration 96 both arms had the notes. Both runs of the previous
  skill listed `tools/` and read `tools/notes.json` themselves. In iteration
  97 only the arm of the changed skill had them. Neither run of the previous
  skill saw a note, and both still planned a tap that ends the pulse before
  the tap that collects, from the Hints group in the print. All eight runs
  passed with their first plan, and the deciding column, `chain_attempts`,
  differed by 0 in both iterations. A fact that the sheet's print states
  across two groups costs a run no search, so it shows no saving either
  (`.local/docs/evidence/skill-evals/construct3-agent-plugin/iteration-96/`
  and `iteration-97/`).
- The case `five-coins-in-round-two` needs a fact that no print of the
  sheet holds: the coins have a square hole outside their collision
  polygon, so a tap at a coin's middle collects nothing. Only
  `objectTypes/Coin.json` and a probe in the game show it. In iteration 101
  the arm of the changed skill had a note on it, and the arm of the previous
  skill had no notes, three runs each. Every run passed. Every run with the
  note read it at the end of its print of the sheet, and its first plan
  tapped the coin's ring. Every run without it first planned a tap on the
  coin, failed twice, probed two or three times and then read
  `objectTypes/Coin.json`. Up to the first passing plan, the runs with the
  note took 13.0 tool calls and 369,000 tokens on average, and the runs
  without it 20.3 and 716,000. `chain_attempts` fell from 21.3 to 16.7
  (p = 0.100). The rule written before the runs also asked that no run with
  the note play anything before its first passing plan. Two runs broke that
  rule for reasons other than the hole: one plan picked a coin that was
  already shrinking away, and one run opened the editor's preview first. So
  by that rule the result is mixed. A note saves the search for a fact that
  the print of the sheet does not hold
  (`.local/docs/evidence/skill-evals/construct3-agent-plugin/iteration-101/`).

## Options

1. A Markdown file of free lines, as in that agent, with the sheet named in
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
