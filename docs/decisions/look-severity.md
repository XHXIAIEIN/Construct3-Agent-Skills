# The Look Review Ranks Its Faults and Checks Worst Data and Other Screens

Date: 2026-10-30

## Problem

A look review that fails on every finding alike fails a label a pixel or two
above the centre of its key as it fails a cut score. The template's own key
hints sit that far off in a project whose font cache lacks Inter. A review
of the start of each layout on the project's viewport sees only the data the
game starts with, such as a score of 0. A counter whose box is too narrow
for 999 then passes, and so does a HUD that a phone's screen moves.

The owner rejected some looks: an app dashboard (cards, a score pill, a
shadow under everything), several drawing styles on one screen, one
decoration on every screen, and kinds drawn alike. A check needs them as
rules with names.

## Options

1. **One tier.** Every finding blocks.
2. **Tiers that the judge assigns** to each yes. The judge then makes a
   second judgement per yes, which needs its own calibration.
3. **A tier per rule and per question.** A finding takes the tier of its
   rule, and a yes takes the tier of its question. Chosen, because each
   question already names the kind of fault it asks about, so the tier
   costs the judge nothing.

The tiers merge two schemes of design review: Broken, Ugly and Fragile, and
Floor (what must hold), Reflex (the look a generator reaches for) and Finish
(the polish).

| Tier | Merges | What it is | In the look step |
|------|--------|------------|------------------|
| `broken` | Broken, Floor | the player cannot read, reach or tell apart what the screen shows, in some data state or on some screen shape | fails; fixed first |
| `ugly` | Ugly, Reflex | it reads but looks wrong; the rejected looks `avoid.*` are among them | fails |
| `fragile` | Fragile, Finish | right as shown and one realistic step from broken, as a text with no declared limit; or a finish of a pixel or two | warns; named in the hand-over |

`text`, `stacked`, `overlap`, `edge`, `frame` and `faint` are broken.
`crowd` is ugly. `optical` and `unlimited` are fragile. A yes to questions
1-3 (text, cover, edge) is broken, and a yes to the others is ugly. A yes
from before the change warns whatever its tier
(`look-blocks-only-what-the-change-brought.md`).

The review also looks past the start of each layout:

- **Data states.** Each Text that events set shows its longest declared
  text, then no text, then every count at 1. The text, overlap, edge and
  crowd rules run again in each state. The generator writes each Text's
  longest text to `tools/texts.json` from its helper's `longest=`, and it
  warns of a Text that events set with no `longest`. Without `longest`, as in
  a project of other making, the worst text is a guess: a count at 9999999, a
  long hyphenated name or a long Chinese one. The review reports such a Text
  as `unlimited`, and a finding that only a guess causes warns, because a
  guessed name can be longer than any text the game shows. The generator
  goes on, as the owner chose, so a missing `longest` costs a guessed worst
  text and not the build.
- **Screen shapes.** Without `--viewport`, each layout is also looked at on
  two shapes that the project's orientations allow, at the viewport's
  shorter side, such as 4:3 and a phone's 19.5:9 for landscape. Scale outer
  and Anchor place the HUD differently on each.
- **Contrast on screen** (`faint`). The checker and the generator test a
  Text's role against the role behind it. The review measures the core
  pixels of the letters against the same pixels with every text hidden, so
  it also measures a text on a picture or a gradient. It allows 10% under
  `text.contrast` for antialiasing.

A yes with more than one right fix, such as cutting a text short or wrapping
it, is the user's to pick, so the next line says to ask before a round goes
to it. The look step allows three rounds, because one fault per round would
leave most faults of a first screen past the cap, so the next line orders
the fixes broken first.

The rejected looks are the rules `avoid.dashboard`, `avoid.style-mix`,
`avoid.same-decoration` and `avoid.kinds-alike`, each with a Before, an After
and a Why. Questions ask about each. `avoid.kinds-alike` also has a measure,
`art.alike` in `art.py`, which compares two drawn pictures of one box for
different subjects over 16 x 16 cells. Two pictures of one object are left
out unless both are kinds in its Default animation, because one pose looks
much like the next.

Question 7 asks for the dashboard look. On calibration with
`dev/evals/judge_look.py` and Haiku, it answered yes on every dashboard
mock-up and on no clean game screen. On the 35-screenshot regression set,
its yes fell only on screenshots whose labels already fail them, and the
agreement of questions 1-6 with the labels stayed within the spread of two
runs without it. The replies are in `.local/docs/evidence/look-judge/round2/`.

## Decision

Option 3, with the data states, the screen shapes, `faint`, `art.alike` and
question 7. The rules are `look.severity`, `look.worst-data`,
`look.screen-shapes`, `art.alike` and `avoid.*` in
`assets/look-manifest.json`. `verify_change.py` keeps the yes left after
three rounds. Its `ok:` line names those yes and each fragile finding, for
the hand-over to give each fix in three parts: before, after and why.

## Re-evaluate when

- A clean screen gets a broken or ugly finding in a data state or on a
  screen shape: the guess, the shapes or a rule's exceptions are wrong.
- Haiku's agreement on the regression set with question 7 in the brief
  falls below the round-2 judges of `look-judge-calibration.md`.
- The owner judges an `optical` offset a fault that must block.
