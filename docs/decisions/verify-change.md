# One Script Runs the Checks of a Change and Says the Next Step

Date: 2026-10-23

## Problem

`SKILL.md` gave the check loop as six numbered steps, about fifty lines: the
checker, the design review and its questions, the editor and its preview,
the kept plays, the look, and the hand-over that names the last step that
passed. Each script's last line named a different next step, so the order
lived only in that text and in the agent's memory.

A long session loses that text. After a compaction, a SKILL.md the agent
read keeps at most its path, and two runs in three went on without reading
it again (`compaction-eval.md`). What a script prints reaches the agent on
every run, compacted or not, and what a script records on disk outlives the
summary.

## Evidence

- The checker already keeps its state on disk: `.tmp/check-project.json`
  holds a digest of the files, the problems and the fix-loop counts
  (`fix-loop-cap.md`), and `pack_project.py` packs only against it
  (`pack-after-check.md`). No later step recorded which files it checked.
- The step scripts give a usable signal for each outcome: exit 0 on a pass,
  1 on a finding, 3 for a check that did not run
  (`not-checked-is-not-a-pass.md`), 5 for a browser profile another run
  holds, and a summary line (`design:`, `look:`) with a questions block.
- The editor steps take the time: the first open takes up to 40 seconds,
  and the look visits every layout. The checker and the design review read
  the files in seconds.

## Options

1. Shorten the six steps in SKILL.md. The text is cheaper, but compaction
   drops a short text as it drops a long one.
2. Make each script's last line name the next script. The order is then
   spread over six scripts, and nothing records which files a step passed
   on, so the hand-over still rests on the agent's memory.
3. One script runs the steps in order and keeps each step's outcome with a
   digest of the files. It reruns an editor step only when a file changed,
   stops at the first step that finds or asks something, and its last line
   is the one thing to do.

## Decision

Option 3, `scripts/verify_change.py`. The steps keep the names the
hand-over already used: checked, reviewed, opened, previewed, played, looked.

- The checker and the design review run on every call. The editor steps
  run again only when the digest of every project file outside its dot
  folders differs from the one they passed on; images and scripts count,
  because the preview reads them.
- A question is answered with an explicit `--answered`, so a run that
  answers is visible in its transcript, and the eval can count one that
  skipped. An answer holds for the files it was asked about: a change asks
  the questions again, as the old loop's "repeat step 2" did.
- A missing play does not stop the run. Without `tools/plans/` or
  `tools/design.json`, played does not run, and the `ok:` line names what a
  player does as untested. A plan for every change would also be demanded
  for a rename.
- Exit 3 and a `skipped:` last line name the steps that did not run and the
  last one that passed. `--status` prints where the steps stand without
  running them, which is what an agent needs after a compaction.
- The checker's `ok:` line names `verify_change.py` as the next step, and
  names none under it (`CONSTRUCT3_RAG_IN_VERIFY=1`). `edit_sheet.py` ends
  its line with the same command. The design review's `next:` line points
  at it too.

The section of `SKILL.md` went from six steps to one command and three
rules. `skills-dev/evals/trace.py` counts a run of the script as a call of
each step it printed a line for.

## Re-evaluate when

- Eval runs show agents stopping at a `next:` line of the script without
  doing it, or running the step scripts by hand instead.
- The compaction case (`compaction-eval.md`) shows the compact arms check
  after their last edit no more often than before this change.
- A step's outcome depends on something outside the project's files, such
  as an addon installed in the editor, and a cached pass hides a change.
