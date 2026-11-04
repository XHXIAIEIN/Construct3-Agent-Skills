# The Scripts Check What Is Wrong, Not What Looks Good

Date: 2026-11-02

## Problem

The repository wrote image prompts, judged a game's look through a reviewer's
answers, and held a manifest of rules on how a game should look, some of them
blocking. The owner reversed that on 2026-11-02: an agent's look comes from
the user and the design tools the user chooses, not from this repository.

## Options

1. **Keep the rules as warnings.** A warning that names a look still tells an
   agent how a game should look.
2. **Keep the checks whose answer does not depend on taste, and remove the
   rest.** Chosen.

## Decision

Option 2. The test: if a script gives right or wrong for the same input, it
stays. If it judges whether something looks good, or says what a game should
look like, it goes.

- `check_screens.py` reports what the runtime shows wrong: `text`, `stacked`,
  `overlap`, `edge`, `frame`, `placeholder`, `faint`, `unlimited`. `faint`
  stays because 4.5:1 and 3:1 are fixed thresholds for text that cannot be read.
- `check_project.py` holds a generated project's images (`alpha.pure`), its
  Sprite Font characters (`type.pixel-font`) and restarted value tweens
  (`motion.value-restart`).
- `art.py` keeps `art.roles`, `art.ids` and `art.frames`. A drawing that names
  a colour, shares an id or drifts between frames breaks the game whatever it
  looks like.
- The template's palette, text sizes and motion values stay as starting values,
  because a game needs some value to start from. Nothing stops a game for
  changing them.
- `spaced()`, `balanced()`, `filled()` and `on_grid()` stay in the template as
  names that check nothing, because a game's generator keeps calling them after
  `install.py` refreshes its helpers. `ART_STYLE` and `USER_LOOK` in such a
  generator are read by nothing.
- `art()` keeps its `subject`, because the drawings' brief names it and a new
  subject restarts a refused picture's count.

No script now looks at a game's look, so an ugly screen passes
`verify_change.py`. That is the accepted cost.

`design-judge` and `review_design.py` stay: they judge event logic, not looks.

## Re-evaluate when

- A check here reports a look that the user accepts: it is not mechanical, and
  it goes.
- A mechanical fault reaches a user that a fixed threshold could have caught:
  add that check to `check_screens.py` or `check_project.py`.
