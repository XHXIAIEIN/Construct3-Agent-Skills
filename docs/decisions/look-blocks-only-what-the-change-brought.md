# The Look Step Fails Only on What the Change Brought

Date: 2026-10-30

## Problem

The look step of `verify_change.py` fails on a broken or ugly yes of the look
judge (`look-severity.md`). In a project with art of its own, the judge
answers yes about art that the change did not touch: a template's plain
tiles taken for stand-ins, a shadow disc under a character, two instances of
one enemy type taken for two kinds that look alike. The step then fails on
the user's own look. A strong agent names such a yes and hands over a check
that did not pass. A weaker agent that follows the yes restyles the project
to pass the step.

## Options

1. Fail the step only in a generated game. A change to a user's project then
   loses the review of what the change itself put on the screen.
2. Judge the project before the change in a second brief, and pass a yes that
   both briefs give for the same layout and question. One yes per layout and
   question hides a new fault behind an old one of the same question.
3. Show the judge each layout before the change beside its screenshot in the
   same brief, and have it mark each yes new or before.

## Evidence

With a picture from before the change beside each screenshot, the judge
gave no new yes where the screenshot equalled the picture from before. It
marked new each fault drawn into a screenshot: a plain grey box, a score
running off the edge and a magenta glow. The runs are in
`.local/docs/evidence/look-judge/before-the-change/` and in
`.local/docs/evidence/skill-evals/construct3-agent-plugin/iteration-85/`.

## Decision

Option 3 (`look.before-the-change` in `assets/look-manifest.json`). In a git
repository, `review_look.py` takes the commit where the change starts. That
commit is the newest one of HEAD's history that another local branch holds,
which is where the branch `agents` left the user's branch, or HEAD when no
other branch holds one. The script copies the project of that commit with
`git archive` into `.tmp/scripts/review-look/before/<commit>/`. It previews
the copy once on the project's own screen in demo data and keeps the shots
for later runs. The brief names the picture from before beside each
screenshot, and asks the judge to write new when it is not sure. `--reply`
asks again for a yes that does not say new or before. A yes from before
fails nothing, and the `ok:` line of `verify_change.py` names it for the
hand-over.

Without git, or on a layout the change added, every yes is new. `SKILL.md`
has the agent run `git init` before the first edit, so a project without git
is rare. The cost is one more preview for each starting commit.

## Re-evaluate when

- A judge marks a fault before that the picture from before does not show,
  or marks the project's own look new, where the screenshot and the picture
  from before differ only by the change.
- The mechanical findings of the review, which are not compared with the
  project before the change, stop a change on objects it did not touch.
