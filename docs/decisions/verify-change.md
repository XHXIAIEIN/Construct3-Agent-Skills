# One Script Runs the Checks of a Change and Says the Next Step

Date: 2026-10-24

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

- The checker already keeps its state on disk:
  `.tmp/scripts/check-project/result.json` holds a digest of the files, the
  problems and the fix-loop counts (`fix-loop-cap.md`), and `pack_project.py`
  packs only against it (`pack-after-check.md`). No later step recorded which
  files it checked.
- The step scripts give a usable signal for each outcome: exit 0 on a pass,
  1 on a finding, 3 for a check that did not run
  (`not-checked-is-not-a-pass.md`), 5 for a browser profile another run
  holds, and a summary line (`design:`, `look:`) with a questions block.
- The editor steps take the time: the first open takes up to 40 seconds,
  and the look visits every layout. The checker and the design review read
  the files in seconds. On a warm profile each editor script spends about
  1 second starting the browser and loading the editor, and 4 seconds
  opening the project, before its own preview work.
- When no plan is kept, the run that asks the look questions also asks for
  one. Eval iterations 73 to 75 ran `fix-next-round` and `fix-wasd-twitch`
  through `construct3:project-worker` on Haiku 5.5, two runs a cell,
  against main of the day. The column is the runs that end with the look
  step not passed, as `dev/evals/trace.py` counts it:

  | Iteration | The script as | Ended with the look step not passed | Gave the brief to the judge | Passed every assertion |
  |-----------|---------------|-------------------------------------|-----------------------------|------------------------|
  | 73 | the answers' digest holding `tools/plans/` | 3 of 4 | 3 of 4 | 4 of 4 |
  | 73 | main | 3 of 4 | 4 of 4 | 4 of 4 |
  | 74 | the digest without `tools/plans/` | 1 of 4 | 1 of 4 | 4 of 4 |
  | 74 | main | 3 of 4 | 4 of 4 | 4 of 4 |
  | 75 | that digest, and the look step passing on a checked reply | 0 of 4 | 4 of 4 | 4 of 4 |
  | 75 | main | 2 of 4 | 3 of 4 | 4 of 4 |

  - With `tools/plans/` in the digest, each run that ended so kept its plan
    after the look questions were asked. The plan changed the digest, every
    answer recorded before it counted no more, and the design and look
    questions came again; the workers stopped there.
  - With the plans out of the digest and `--answered` recording every
    question the last run asked, 2 runs of iteration 74 passed the look step
    with no judge started, no screenshot read and no reply: they kept the
    plan and ran `--answered`.
  - In iteration 75, one run passed the look step on a review whose preview
    had stopped answering: no layout was visited, so no question was asked,
    and the script exited 0.
  - A judge's reply can say yes about art that the change did not touch, as
    in `fix-wasd-twitch`, whose enemies look alike in the official example.

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
  folders and `tools/plans/` differs from the one they passed on; images
  and scripts count, because the preview reads them. A kept plan changes
  nothing the game runs. The play step also compares a digest of the kept
  plans, so a changed plan plays again.
- The editor scripts share one browser and one open project. The run sets
  `CONSTRUCT3_SHARED_EDITOR` to the project, so each script leaves the
  browser running and keeps the project's editor page, marked with a digest
  of the packed files. The next script takes that page while it holds the
  same files, and opens the project again otherwise; each still starts a
  preview of its own. The run closes the browser as it ends. On a warm
  profile the three editor scripts took 22.5 seconds instead of 33.1, with
  the same output.
- A design question is answered with an explicit `--answered`, so a run
  that answers is visible in its transcript, and the eval can count one
  that skipped. An answer holds for the files it was asked about: a change
  asks the questions again, as the old loop's "repeat step 2" did.
- The look questions pass on a reply, not on `--answered`. Each run of
  `review_look.py` names itself in its result, and `review_look.py --reply`
  writes its verdict onto the run whose brief the reply answers. The look
  step passes on that run's reply when it answers every question with no
  new yes, and the files are the ones it was asked about. A yes from before
  the change goes into the hand-over
  (`look-blocks-only-what-the-change-brought.md`). A new yes fails the step,
  and the agent fixes it, which asks again. The owner chose this on 2026-10-30,
  because a step that passed with "name its yes in the hand-over" let a
  yes about a stand-in among drawn art reach the user. After three replies
  with a yes the step passes, and the hand-over names each yes left, so a
  judge that keeps a wrong yes cannot hold the chain forever. In a
  generated game the step runs `check_look.py` before the review. An agent that answers the brief itself saves its answers as
  `reply.md` and checks them with `--reply` too. When the look step waits,
  a reply that answers every question no ends with the command that goes
  on.
- A missing play does not stop the run. Without `tools/plans/` or
  `tools/design.json`, played does not run, and the `ok:` line names `played`
  among the steps that did not run. A plan for every change would also be demanded
  for a rename.
- Exit 3 and a `skipped:` last line name the steps that did not run and the
  last one that passed. `review_look.py` exits 3 when the project opened but
  its preview did not run, since no layout was looked at. `--status` prints
  where the steps stand without running them, which is what an agent needs
  after a compaction.
- The checker's `ok:` line names `verify_change.py` as the next step, and
  names none under it (`CONSTRUCT3_RAG_IN_VERIFY=1`). `edit_sheet.py` ends
  its line with the same command. The design review's `next:` line points
  at it too.

The section of `SKILL.md` went from six steps to one command and three
rules. `dev/evals/trace.py` counts a run of the script as a call of
each step it printed a line for. The runs of iterations 73 to 75 are in
`.local/docs/evidence/skill-evals/construct3-agent-plugin/`.

## Re-evaluate when

- Eval runs show agents stopping at a `next:` line of the script without
  doing it, or running the step scripts by hand instead.
- The compaction case (`compaction-eval.md`) shows the compact arms check
  after their last edit no more often than before this change.
- A step's outcome depends on something outside the project's files, such
  as an addon installed in the editor, and a cached pass hides a change.
- Runs pass the look step on replies that no judge and no reading of the
  screenshots produced, such as a `reply.md` written without opening them.
- The exit 3 of a preview that did not run has no eval run behind it,
  because the eval cannot make a preview stop. A run that meets it shows
  whether agents run the review again or hand over the step as skipped.
