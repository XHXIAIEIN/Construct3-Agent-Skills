# The Game's Look: unslop's Spacing and Alignment Measured on Game Screens

Date: 2026-11-01

## Problem

[unslop](https://github.com/heydamir/unslop) (CC BY 4.0, commit `4652254`)
is a skill that redesigns a web page or an app screen that looks generated.
It lists the signs of a generated screen with a fix for each, sets a
direction from the product, then fixes the screen in nine passes: spacing,
colour, icons, copy, type, layout, details, visuals and motion. This record
reads its `SKILL.md`, its five references and its two scripts, and compares
them with the look pipeline of this repository at the level of the code:
`assets/look-manifest.json`, `assets/build_project.py`,
`scripts/check_look.py`, `scripts/review_look.py` and the `look-judge`
sub-agent.

Task: find what a fixed-size game screen can use from unslop's layout
passes, and measure it on the official examples before it becomes a rule.

## Evidence

### Each part of unslop against this repository

"Not for a game screen" names web mechanics that a Construct layout lacks or
that a game screen breaks on purpose: a sidebar and a scrolling page, a call
to action, rounded cards, a landing hero.

| unslop part | What it does | What this repository does | Change |
|-------------|--------------|---------------------------|--------|
| Run it, steps 1 to 4 | Screenshot first; audit every sign with its place; heavy, light or no slop decides how much changes; write the direction and stop for the user | `review_look.py` screenshots each layout; `look.before-the-change` blocks only what the change brought; `look.picker` lets the user pick among directions from the references | None |
| Run it, steps 5 to 7 | Nine passes in order; check; at most three renders | Findings by tier, broken before ugly (`look.severity`); `fix-loop-cap.md` caps the rounds | None |
| Direction | Product, character, world, one or two moments, one signature detail | `pick_look.py` draws directions from the user's references, measured | None. The user picks among references instead of a model deriving a world |
| Spacing: a 4 px grid | Every value a multiple of 4 | `grid.unit`, 8 or 32 px; `grid.world-placement` for world layers | None |
| Spacing: same thing, same size | All rows of a list share one height and one gap | `row()` spaces what it places; no check reads a run placed by hand | `layout.even-runs` proposed (below) |
| Spacing: grouping | Gaps inside a group smaller than between groups | `layout.proximity`, 1.5 times | None |
| Spacing: things line up | Icons in one column, labels on one line, nothing nudged off it | `grid.world-placement` checks world layers only | `layout.edge-snap` rejected (below) |
| Colour | One tinted neutral ramp, three text roles, one accent used rarely, no hue gradients or glows | `colour.palette-only`, `colour.structure`, `text.contrast`; `colour.one-accent` and `colour.neutral-ground` rejected by measurement | None |
| Icons | Emoji become line icons of one set, one size and stroke | `text.no-emoji`; the icons are the game's art | None |
| Copy | No greeting, no exclamation marks, no hype, a change says what it compares to | | Not for a game screen's look. Game text is event design |
| Type | Weights 400 to 500, sentence case, tabular figures, no negative tracking on small text | `type.scale`, `type.counting-digits`; `type.caps-labels` rejected by measurement | None |
| Layout | App proportions; a scene hero; an asymmetric split; one primary and one secondary action; the first screen composed whole | `layout.fill`, `layout.balance`, `layout.spread`, `screen.menu-axis` | None. The rest is a web page's layout |
| Details | Nested radius; stat cards hold numbers only; vary the sizes of cards | `avoid.dashboard`; `layout.focal` rejected, a grid of equal tiles is a sound game screen | None |
| Visuals | One bright element; a scene or the product instead of filler | `art.routes`, the backdrop question of `look-judge` | None |
| Motion | No loops without a reason, one ease, transform and opacity only | `TWEEN_STYLE` by class (`motion-by-class.md`) | None |
| Template look | Swap the product's name: does the screen still fit? | The reference and picked-look questions of `look-judge`; `avoid.same-decoration` | None. `look-judge-calibration.md` found that an open question makes judges report more, not more correctly |
| Checklist | One line per pass | The manifest's checks and the judge's fixed questions | None |
| Story video, `story.mjs` | The screen morphs pass by pass, with red redlines that measure gaps and corners | `review_look.py` gives its findings to the judge as text with uids | Proposal 1 (below) |
| `snapshot.mjs` | Saves a live page as one HTML file and a screenshot | | Not for a game screen |
| `visuals.md`, `effects.md`, `refs.md` | Picking and generating a hero image; glyph and duotone treatments; finished screens | `art-from-the-image-tool.md`, `art.py` | None |

### Measurements on the official examples

`dev/scripts/measure_examples.py rows` and `edges` read the screens of the
2D game examples: the layers at parallax 0, which are the HUD, and every
layer of a layout no larger than the viewport. They leave out rotated
instances, particles and boxes over 80% of the screen. Distances are pixels
of a screen 720 px on its shorter side, where `UNIT` is 32 px. The rows are
in `.local/docs/evidence/look-from-unslop/`.

`rows` finds three or more boxes that are not texts on one centre line,
within 1 px, in order along it. A run breaks where two boxes overlap and
where a gap is wider than the larger box beside it. A Text's box is wider
than its ink, so texts are left out.

| Runs of one type | Runs | Gaps within 0.5 px | 0.5 to 8 px | 8 px or more |
|------------------|------|--------------------|-------------|--------------|
| HUD | 28 | 19 | 4 | 5 |
| World of a one-screen layout | 250 | 230 | 0 | 20 |
| All | 278 | 249 | 4 | 25 |

The 25 runs of 8 px or more skip a whole grid cell, as a pipe puzzle or a
dungeon does, or set their items in pairs. The 4 between them, in 3
examples, are a row of lives with its first gap 2 px wider, a row of buy
buttons with one gap 0.7 px narrower, a column of icons with one gap 1 px
narrower, and a column of icons of unequal sizes.

`edges` takes each box and its nearest neighbour below it whose box
overlaps it across, and to its right whose box overlaps it down, no further
away than the larger box is long. It measures the distance between their
nearest pair of edges of one kind: start, centre or end, and for a Text only
the edge that its alignment holds.

| Pairs | Pairs | Within 0.5 px | 0.5 to 8 px | 8 px or more | Examples with a pair 0.5 to 8 px apart |
|-------|-------|---------------|-------------|--------------|----------------------------------------|
| HUD | 361 | 201 | 93 | 67 | 12 of 20 |
| World of a one-screen layout | 2911 | 2429 | 73 | 409 | 23 of 59 |

## Options

1. **Take unslop's passes as review questions.** The questions overlap the
   manifest's rules, and an open question was turned down by
   `look-judge-calibration.md`.
2. **Two checks on measured boxes, after a measurement.** One for uneven
   runs, one for edges a few pixels off. Chosen, with the measurement
   deciding each.
3. **Nothing.** The generator's `row()` and `anchor()` already place what
   they write, but a project that someone placed by hand gets no check of
   either kind.

## Decision

Option 2. The manifest gains two rules:

- `layout.even-runs`, proposed: three or more things of one type on one
  line sit one gap apart. The examples hold it: 249 of 278 runs are even
  within 0.5 px, and only 4 differ by less than a quarter of `UNIT`. The
  check that it proposes is a finding of `review_look.py` at the ugly tier:
  a run of one type whose gaps differ by 0.5 px to a quarter of `UNIT`, a
  difference too small to be a skipped cell or a grouping. It reads the
  boxes, so it needs no judge's calibration.
- `layout.edge-snap`, rejected: the rule that neighbouring HUD boxes share
  an edge or a centre exactly. 93 of 361 neighbouring HUD pairs, in 12 of
  20 examples, lie 0.5 to 8 px apart, so the check would flag most of the
  examples' HUDs.

One change to the review is proposed and not made:

1. **Redlines on the screenshot.** unslop draws each measured fault on the
   picture of the screen. Here `look-judge` reads the findings as text and
   sees a clean screenshot. Proposed: `review_look.py` draws the box of
   each finding and its measured distance on a copy of the screenshot. The
   judge's input changes, so both judges answer the regression set of
   `look-judge-calibration.md` again before the change.

The template and the sub-agents' prompts stay as they are.

## Re-evaluate when

- The owner takes `layout.even-runs`: add the finding to `review_look.py`
  with a test, and add it to `AGAIN` if a longer text moves a run.
- A generated game shows a misaligned HUD on a screenshot the user judges:
  measure the generated games' pairs against the examples' 93 of 361.
- The owner takes proposal 1: the judges answer the regression set again.
- The example clone updates: rerun `measure_examples.py rows` and `edges`.
