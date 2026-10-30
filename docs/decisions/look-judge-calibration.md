# Look Questions Measured Against Agent Labels

Date: 2026-10-08

## Problem

`scripts/review_look.py` ends with fixed yes/no questions about its
screenshots. Its brief gives them to a sub-agent that has not seen the
project, and the agent fixes each yes. Nothing showed how often a judge's
answers are right, or which questions it answers wrongly.

## Evidence

The set has 35 screenshots of 14 games and generated projects:

- 17 first screens, taken as `review_look.py` takes them
- 9 screens reached in play by a `preview_project.py` plan
- 9 copies broken on purpose in one way each: text over text, the HUD past
  the screen's edge, a text cut by its box, HUD text close to its
  background, stand-in boxes among finished art (twice), a bright patterned
  backdrop, a smooth gradient sign in a pixel-art scene, every kind of map
  node drawn alike

Most of these games are throwaway projects that small models built with
early versions of the skill. Their faults are many and plain, and few of
their screens are finished. Layouts that only store object types are left
out.

Agents play every role, each a Claude Code sub-agent that gets one brief
and nothing else:

- Labellers: two Opus agents label each screenshot apart, through the
  brief of `dev/evals/label_look.py`. They answer each question with a reason,
  a no included, and say whether the screen would ship.
- Adjudicator: an Opus agent settles each question the two labellers
  answered differently. It sees their answers and reasons only, never a
  judge's. The labellers differed on 6 of the 35 screenshots.
- Judges: a Haiku agent and an Opus agent answer the brief that
  `review_look.brief` writes, one run per brief, the screenshots under
  neutral names.

`dev/evals/judge_look.py --score` counts how often a judge agrees with the
labels. Most answers are no, so the baseline is a judge that answers no to
everything. The labels find a fault on 22 screenshots and none on 13.
Every broken copy got a yes on the question its break was made for.

The first wording asked about facts in the picture: two outline weights,
an object over another, anything the edge of the screen cuts. The second
asks what a player sees as a mistake, and names what each question is
about. Its brief adds that art layered on purpose is no mistake. Its
question 4 asks about stand-ins and objects drawn in a style of their own,
and its question 1 adds text too small or too faint to read. The labels
answer the second wording, so the first is compared by what a judge says
about the screens without a fault and about the faults put in on purpose:

| Wording | Judge | Yes answers on the 13 screens without a fault | Of those screens, with a yes | Screens with a fault that get a yes, of 22 | Faults put in on purpose found, of 9 |
|---------|-------|----|----|----|----|
| Facts | Haiku | 19 | 8 | 20 | 5 |
| Facts | Opus | 25 | 11 | 22 | 8 |
| Mistakes | Haiku | 5 | 5 | 21 | 7 |
| Mistakes | Opus | 2 | 2 | 22 | 8 |

The second wording cuts the yeses on screens without a fault from 25 to 2
(Opus) and from 19 to 5 (Haiku), and it finds as many faults. An agent that
fixes every yes no longer changes screens that are done.

Agreement with the labels under the second wording, out of 35 screenshots.
A yes, a fault, is the positive class. The true positive rate (TPR) counts
the labels' yes answers that the judge also said yes to. The true negative
rate (TNR) counts their no answers that it also said no to.

| Question | Labels yes | Haiku agrees | Haiku TPR | Haiku TNR | Opus agrees | Opus TPR | Opus TNR | All no agrees |
|----------|------------|--------------|-----------|-----------|-------------|----------|----------|---------------|
| 1. Text cut, wrapped, too small or faint, or partly hidden | 11 | 28 | 9/11 | 19/24 | 33 | 11/11 | 22/24 | 24 |
| 2. An object hides a text, a number, a button or a card's face | 5 | 31 | 1/5 | 30/30 | 34 | 5/5 | 29/30 | 30 |
| 3. A button, a text or the HUD cut by the screen's edge | 7 | 34 | 7/7 | 27/28 | 35 | 7/7 | 28/28 | 28 |
| 4. A stand-in or an object drawn in a style of its own | 11 | 34 | 10/11 | 24/24 | 35 | 11/11 | 24/24 | 24 |
| 5. A background or glow catches the eye first | 3 | 31 | 1/3 | 30/32 | 35 | 3/3 | 32/32 | 32 |
| 6. Two kinds look identical with nothing to tell them apart | 1 | 33 | 0/1 | 33/34 | 34 | 0/1 | 34/34 | 34 |

- Opus agrees with the labels on 33 to 35 screenshots a question, but the
  labellers are Opus too, so this is close to a model agreeing with itself.
  Haiku measures a judge that differs from the labellers.
- Agreement hides what a question misses, because most labels are no. On
  question 2 Haiku agrees on 31 of 35, above the baseline's 30, yet it
  finds 1 of the 5 hidden objects. For the small model the question is too
  narrow.
- Haiku stays below the baseline on question 5, with 2 missed and 2 extra,
  and on question 6. The one screenshot with two kinds alike is the copy
  whose map nodes all look the same. Both labellers found it, and neither
  judge did: a judge that gives no reason per question looks less closely.
  The `frame` finding of `review_look.py` measures that case from the
  instances.
- The question about decoration repeated on every screenshot had one brief
  to answer it and is not measured.

Every question has fewer than 30 yes labels, and questions 5 and 6 have 3
and 1. One answer moves the TPR of question 5 by a third, and that of
question 6 from none to all. A TPR over so few screenshots cannot rank one
wording or judge above another. The judge-validation method of the
evals-skills repository (`github.com/ai-evals-course/evals-skills`) asks
for 30 to 50 labels of each answer. `judge_look.py --score` marks a line
"few" when it has fewer than 30 of either.

The second wording was written after the first was read on the same set,
so every number above was measured on the screenshots it was tuned on.
The labels also come from the model family of one judge, with one run per
brief. The numbers show a direction for these games, not a rate to expect
elsewhere. The set, every reply, the labels and the scores are in
`.local/docs/evidence/look-judge/`. `judge_look.py --model` runs `claude
-p` as the judge when the client is signed in. The runs here used
sub-agents.

## Options

1. Keep the questions about facts. The judges flag most screens that are
   done.
2. Score each screen with a rubric or a free critic. That is another model
   to calibrate, and the first wording shows that a loose question makes a
   model report more, not more correctly.
3. Ask what a player sees as a mistake, each question naming the things it
   is about.
4. Keep only the measured finding lines. They miss stand-ins and faint text,
   which the labels find.

## Decision

Option 3. `review_look.py` asks the second wording, and its brief says that
art layered on purpose is no mistake. The set in
`.local/docs/evidence/look-judge/` is the regression set, labelled by agents
with `label_look.py`. A change to the questions or the brief has both
judges answer the set with `judge_look.py`. The change keeps Haiku's TPR
and TNR on each question at or above these numbers, and the yeses on
screens without a fault at or below them. These numbers are a floor that
stops a change that makes the judge worse. They do not rank two wordings
that both pass it. Agreement alone does not pass a change, because it
rises when a question finds fewer faults.

A new screenshot gets its labels the same way: two labellers apart, and the
adjudicator where they differ. It enters the set with `"held_out": true`,
because no wording has been shaped on it yet. The 35 screenshots above
have all steered the wording, so none of them is held out. `judge_look.py`
leaves the held-out briefs out until `--held-out`. A change is shaped and
scored on the other briefs. Once its wording is settled, both judges answer
the held-out briefs once, and that score is the change's measure on
screenshots it was not shaped on. A held-out screenshot that the change
gets wrong then joins the tuning part, and a new screenshot takes its
place, as `docs/decisions/runtime-graded-evals.md` does with held-out
cases.

## Re-evaluate when

- Labels from another model family or from a person differ from the Opus
  labels on more than a few answers. The labels lean toward how Opus sees,
  so the agreement of an Opus judge then means little.
- Haiku stays below the baseline on question 5 or 6 over a larger set.
  Reword the question, or replace it with a measurement.
- A question's line is no longer marked "few". Its TPR and TNR then
  replace the direction above with a rate.
- A small-model judge keeps missing question 2. It then needs examples of
  what counts as hidden.
