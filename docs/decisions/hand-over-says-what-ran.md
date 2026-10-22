# The Hand-Over Says What Ran

Date: 2026-10-22

## Problem

`SKILL.md` told the agent to name the last check step that passed and then
say what that step left untested, and `verify_change.py`,
`open_in_editor.py`, `preview_project.py` and `play_design.py` ended a
passing line with what it did not test. The agent copied both into its reply: "the offline check
passes and the design review finds nothing. The editor preview did not
run, so how it behaves in Construct is not yet checked; open the project
again to see it." The second clause repeats the first as a consequence,
and the last sends the user to run a check the agent had the scripts for.

## Options

- Keep the rule and ask for shorter wording: the rule still asks for a
  sentence on what is untested, and the scripts still print one.
- Drop the report of the steps: the user then cannot tell a played change
  from a checked one.
- Make the steps the work: the agent runs the preview and the plans before
  the hand-over, the hand-over says what changed and what the plans played,
  and a step that could not run is one clause.

## Decision

The third. `SKILL.md` has the agent run `verify_change.py` to its `ok:`
line before the hand-over, which then says what changed and what the plays
played, and names a step that could not run in one clause, without what it
would have shown and without asking the user to run it.
`verifying-a-change.md` has a run extended until it reaches the event
instead of reported as saying nothing, and the hand-over list the cases
played. `generating-a-project.md` hands over how to open the folder and
what the game does, not a request to preview it. The `ok:` and `skipped:`
lines of `verify_change.py` name the steps that did not run, and a passing
preview of `open_in_editor.py` names the next step, a plan of
`preview_project.py`; a passing plan or design play ends with its counts.
A check that did not run still exits 3 or prints `skipped:`
(`not-checked-is-not-a-pass.md`).

## Re-evaluate when

Hand-overs report a change as played when no plan played it, or users ask
which checks a hand-over did not run.
