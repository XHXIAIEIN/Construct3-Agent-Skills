# The Look Review Ranks Its Faults and Looks Past the Demo Screen

Date: 2026-10-30

## Problem

Every finding of `review_look.py` and every yes of its judge failed the look
step alike. So a label 1.5 px above the centre of its key failed the step as
a cut score did. The template's own key hints fail by 1.5-2 px in a project
whose font cache lacks Inter. Every screenshot also showed the data the game
starts with, a score of 0 or round 01, on the project's own viewport. A box
sized for the text shown at build time looked right, but the box of a
counter too narrow for 999 passed, and so did a HUD that a phone's screen
moves onto another one.

The owner had already rejected some looks: an app dashboard (cards, a score
pill, a shadow under everything), several drawing styles on one screen, one
decoration on every screen, and kinds drawn alike. These were reasons in
records, not rules that a check names.

## Options

1. **One tier.** Every finding blocks, as before.
2. **Tiers that the judge assigns** to each yes, as Emil Kowalski's
   `break-ui` skill (MIT) has its reviewer write **Broken**, **Ugly** or
   **Fragile** per row. This needs a second judgement from the judge, which
   must be calibrated as well.
3. **A tier per rule and per question.** A finding takes the tier of its
   rule, and a yes takes the tier of its question. Chosen, because the
   question already says which kind of fault it asks about, and the tier
   costs the judge nothing.

The tiers merge break-ui's three with sloplint's Floor, Reflex and Finish,
as Chinese UI designers use them: Floor is what must hold, Reflex the look
a generator reaches for, Finish the polish.

| Tier | Merges | What it is | In the look step |
|------|--------|------------|------------------|
| `broken` | Broken, Floor | the player cannot read, reach or tell apart what the screen shows, at some data or screen shape | fails; fixed first |
| `ugly` | Ugly, Reflex | it reads but looks wrong; the rejected looks `avoid.*` are among them | fails |
| `fragile` | Fragile, Finish | right as shown and one realistic step from broken, as a text with no declared limit; or a finish of a pixel or two | warns; named in the hand-over |

A finding takes its tier by rule. `text`, `stacked`, `overlap`, `edge`,
`frame` and `faint` are broken. `crowd` is ugly. `optical` and `unlimited`
are fragile. A yes to questions 1-3 (text, cover, edge) is broken, and a yes
to the others is ugly.

The same review looks past the demo screen, after break-ui's worst-case
data and its several widths:

- **Data states.** Each Text that events set is shown at its longest
  declared text, then empty, then with every count at 1. The text, overlap,
  edge and crowd rules run again at each state. A Text's longest text comes
  from `tools/texts.json`, which the generator writes from each helper's
  `longest=`. A Text that events set and no helper gives a longest stops
  the generator. In a project of other making, the worst text is a guess: a
  count at 9999999, a long hyphenated name or a long Chinese one. A finding
  that only a guess causes warns, because the guess can be longer than
  anything the game shows: in a generated card game, a result word guessed
  as a 25-letter name cut a box that holds "VICTORY".
- **Screen shapes.** Without `--viewport`, each layout is also looked at
  on two shapes that the project's orientations allow, at the viewport's
  shorter side: 4:3 and a phone's 19.5:9 for landscape. Scale outer and
  Anchor place the HUD differently on each. In the same card game, the
  phone shape gathered three items of text at the top while both bottom
  corners stood empty, which the 16:9 shot did not show.
- **Contrast on screen** (`faint`). The checker and the generator test a
  Text's role against the role behind it. The review measures the core
  pixels of the letters against the same pixels with every text hidden, so
  it also measures a text on a picture or a gradient. It allows 10% under
  `text.contrast` for antialiasing. On the template and the card game it
  found nothing, and every measured text read 5:1 or more.

A yes with more than one right fix, such as cutting a text short or wrapping
it, is the user's to pick, so the next line says to ask before spending a
round on it. The rounds stay three. One fault per round, as the designers
suggested, would leave most faults of a first screen past the cap, so the
next line orders the fixes broken first instead.

The rejected looks became rules `avoid.dashboard`, `avoid.style-mix`,
`avoid.same-decoration` and `avoid.kinds-alike`, each with a Before, an After
and a Why. Three are asked by existing questions. `avoid.kinds-alike` also
gets a measure, `art.alike` in `art.py`. It compares two drawn pictures of
one box for different subjects over 16 x 16 cells. On the evals' walk cycle
it first matched a standing pose to a walking one, so two pictures of one
object are left out unless both are kinds in its Default animation.

The dashboard look is a new question, 7. It was calibrated with
`dev/evals/judge_look.py` on the 35-screenshot regression set, two Haiku runs
each:

| Run | Q7 yes | Agreement of Q1-Q6 with the labels | Ship |
|-----|--------|------------------------------------|------|
| 3 dashboard mock-ups, 3 clean game screens | 6 of 6 mock-ups, 0 of 6 clean | | |
| the regression set with Q7 | 5 of 70 answers, on 3 screenshots whose labels already fail them | 84, 87, 97, 83, 80, 93% | 86% |
| the regression set without Q7, same day | | 81, 80, 96, 87, 77, 91% | 87% |

The replies are in `.local/docs/evidence/look-judge/round2/`.

Q7 adds no yes to a screenshot that would ship. So it blocks as an ugly
question.

## Decision

Option 3, with the data states, the screen shapes, `faint`, `art.alike` and
question 7 as above. The rules are `look.severity`, `look.worst-data`,
`look.screen-shapes`, `art.alike` and `avoid.*` in
`assets/look-manifest.json`. `verify_change.py` keeps the yes left after
three rounds. Its `ok:` line names those yes and each fragile finding, for
the hand-over to give with each fix as before, after and why.

## Re-evaluate when

- A clean screen gets a broken or ugly finding at a data state or a screen
  shape: the guess, the shapes or a rule's exceptions are wrong.
- Haiku's agreement on the regression set falls below the round-2 judges of
  `look-judge-calibration.md` with question 7 in the brief.
- The owner judges an `optical` offset a fault that must block.
