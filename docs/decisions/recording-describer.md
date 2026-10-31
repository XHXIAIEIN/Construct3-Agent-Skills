# What a Recording Shows Is Described by a Reviewer That Has Not Seen the Change

Date: 2026-10-31

## Problem

Step 7 of `references/verifying-a-change.md` had the agent that wrote the
events open its recording's contact sheet and judge the motion itself. The
look review already sends its screenshots to a reviewer that has not seen
the project (`look-judge-agent.md`), because the agent that wrote the events
reads its own screenshots by what it meant them to show. The same holds for
the frames of a recording. The look judge answers fixed yes/no questions
about layouts at rest, so it cannot take a claim of one change, such as "the
bar slides to its new length and never passes it".

A second gap was in how a check's result is stated. A plan that failed to
reach a ledge or open a door was read as proof that the game cannot do it,
although the plan is as likely at fault as the events.

## Evidence

- Aura Autopilot, a playtesting agent for Unreal, Unity and Godot
  (`github.com/ramenvr/autopilot`, Apache 2.0, read 2026-10-31), checks a
  visual claim this way. Before it looks, the agent writes what true and
  what false would look like as visible features. It then sends frames
  and open questions to a describer that never sees the request, and holds
  the description against what it wrote. A description in which the thing
  is not seen is no contradiction: the agent brings it into view and plays
  again. Its describer answers each question by number, names what moves
  and what stays still, quotes text or says it is unreadable, says what it
  cannot make out, never judges, and stays under 400 words.
- The same project states a claim that something can happen as shown once
  it happened, and refuses "impossible" unless the game's own numbers prove
  it, because a harness that fails is as likely at fault as the game.
- A question a yes answers names what to look for, so a describer that
  wants to help sees it. An open question ("what moves between the frames,
  which way and how far?") does not.
- The name of a record step says what it checks ("hp-bar-slides"), and the
  recording's frames lie in a folder of that name. A reviewer reads the
  frames' paths, so a brief that pointed at that folder would tell it.

## Options

1. **Keep the self-review of the contact sheet.** No cost, and the bias the
   look review was built to avoid.
2. **Send the sheet to `look-judge`.** Its questions are fixed yes/no
   questions about layouts, and its model was measured on those alone.
3. **Expectations and questions on the `record` step, a brief of the frames
   beside the recording, and a read-only describer type.** Chosen.
4. **A separate command over an existing recording**, such as
   `preview_project.py --describe NN-NAME`. It serves a recording the user
   selected on the review page too, but the expectations could then be
   written after the agent saw the sheet that the run prints.

## Decision

Option 3.

- A `record` step takes `expect`, `{"works": [...], "broken": [...]}`,
  what a frame would show if the change works and if it does not, and
  `ask`, open questions about the frames. `check_plan` takes both or
  neither, only on a step that starts a recording, and refuses a question
  that starts with a verb a yes answers (`is`, `does`, `can` and the rest)
  or ends with `吗`. The plan is written, and kept with `--keep`, before the
  run takes a frame, so the expectations cannot follow the frames.
- The run copies the frames of the contact sheet, up to 12 at the window's
  size, into `described-<hash>/` beside the recording, with `brief.md`: the
  frames by absolute path and time, the questions, a last fixed question on
  what else moves and what stays still, the rules of a description and the
  reply's form. The folder's name is a hash of the recording's folder. The
  expectations go to `described-<hash>-expect.json` beside it. The frames
  go one by one, not as the sheet, because a sheet of 12 frames of a
  1920x1080 window shrinks each to 0.275 of its width (`make_sheet`, 3
  columns in 1600 px), and a describer has to read a text to quote it.
- A run prints a `brief:` line for such a recording. `construct3:project-worker`
  gives that brief to `construct3:recording-describer`: `tools: Read`,
  `omitClaudeMd: true`, the description rules and the reply form in its
  body. Without the plugin, any sub-agent can answer the brief, or the agent
  answers it from the frames before it reads `expect` again.
- `preview_project.py --reply described-<hash>/reply.md` names each
  question without an answer, exits 1 on one, and names each answer that
  says cannot make out or unreadable. It prints the answers beside
  `expect`. The agent then holds them against each other: a feature that no
  answer shows is open, and an answer that cannot see the thing leads to a
  closer or slower recording, not to a verdict.
- A recording without `expect` and `ask` prints its sheet with a line on how
  to have the frames described. `verify_change.py` does not wait for a
  description: its play step replays the kept plans for their `until`
  checks, and a description belongs to the change's own check in step 7.
- Step 7 states a claim that something can happen as shown when a run did
  it once. A plan that did not get there leaves it open, and only the
  game's own values, named, show it impossible. The hand-over names each
  open claim.
- The describer runs `claude-sonnet-5-5`. Nothing has measured a
  describer's answers yet: the model is the one the design judge runs, a
  middle step between the look judge's Haiku and the art drawer's Opus.

## Re-evaluate when

- A set of recordings with known motion exists: measure the describer's
  answers on Haiku, Sonnet and Opus, two runs each, and pin the model that
  the measurement supports.
- A describer's reply names a feature of `expect` in its own words more
  often than the frames show it: the brief then leaks the claim, through a
  path, a text on screen or the questions.
- Runs write closed questions in another form than the refused verbs, or
  write `expect` after the run in a plan they play again.
- The user asks to have a recording selected on the review page described:
  the separate command of option 4 then has a caller.
