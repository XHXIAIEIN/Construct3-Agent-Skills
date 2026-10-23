# The Game's Look: What Aesthetics Skills Add to the Template

Date: 2026-10-23

## Problem

`game-look-from-design-skills.md` read fifteen agent design skills and put
the look into the generator template as values and checks. A second
collection, gathered on 2026-10-23, holds skills and corpora about
aesthetics from video, motion graphics, desktop design systems and brand
design systems. Each rule it states was read for the generator template:
layout and type, colour and palettes, proportion, the grid, spacing and
balance.

Task: take what a game screen needs. A rule becomes a value or a check
where the generator writes, a rule of `assets/look-manifest.json` with a
status and a scope, and a test. A threshold comes from a measurement on the
official examples, because web, slide, poster and video rules often do not
hold on a game screen (`greybox-blockout.md`, "Spacing and balance").

## Evidence

### What the collection holds

The files themselves were read, not their READMEs, and nothing in them was
run.

| Collection | What it is | What it says that a check could hold |
|------------|------------|--------------------------------------|
| awesome-design-md | 84 `DESIGN.md` files in Google Stitch's format: the tokens of a brand's website, scraped, with prose around them | Every one of the 71 with token front matter names its text sizes as a type scale. 80 of 84 state a base spacing unit of 4 or 8 px. Between the canvas and its faint surfaces the median contrast is 1.07 to 1.09:1, at most 1.35:1. One element in the primary colour per screen; one display text per page |
| open-claude-ui | A desktop app's design system, reconstructed from its bundle; its own tables disagree | The gap between groups is 0.75 of a line and inside a group 0.5, a ratio of 1.5. One closed border on any line of sight. Its muted text and accent read about 3.1 to 3.4:1 on white |
| Desktop-Agent-UI | An Agent Skill for desktop agent apps, with its tokens from open-claude-ui | A script that finds a shadow its clipping parent cuts in half |
| lemo-opuscar | A skill for films in 51 styles, each style a prose `STYLE.md` and a demo with check scripts | Nothing meant to be read under 1/54 of the frame's height; a reading time per text of characters / 4.5 for CJK plus / 15 for others plus 1.5 s, which a script measures while the text is wholly on screen; a subtitle's width measured in its font against a safe width; safe margins of 5% |
| mg-styles-15 | Fifteen ten-second motion-graphics films, a prompt and source each | 2 to 6 colours per style; no check script |
| awesome-claude-5-5-videos | A survey of about 1 400 videos, with a colour-mode study | Each video binned by lightness and six hues; the light, neutral modes are 90% neutral and under 5% colourful, game videos 30 to 51% colourful. Its check script compares its own published files, not pixels |
| awesome-opus5-5-videos, opus-video-prompts | Prompts of shared videos | A few prompts state margins, 3 or 4 colours, an 8 px baseline or a 64 px reading floor at 1080 |
| ClaudeAnimationBase, PDoomVideo, pdoom-video | Animation starter kits and music video projects | A character's height per shot; an outline proportional to the character's size, with a floor and a cap; title-safe 90%; inactive text at 30 to 40% |

Most of it restates what the template already holds: few colours, each
with a role (`PALETTE`); spacing on a unit (`UNIT`); text contrast
(`readable()`); a gap between groups 1.5 times the gap inside one
(`GROUP_RATIO`, which open-claude-ui reaches from line heights); a faint
surface at most 1.2:1 from the canvas (`palette.greys`, inside the brands'
1.07 to 1.35); hints dimmed to 35% (`hints()`, inside pdoom-video's 30 to
40%). What is new is about type: a scale every text takes its size from,
and a floor for the smallest text.

### What the official examples do

`dev/evals/measure_layout.py --text` reads the texts of the official
examples tagged as 2D games: 105 projects, 204 layouts.

| Rule from the collection | What the examples do |
|--------------------------|----------------------|
| Every text size is a token of a type scale | A layout uses one size in 135 of 204, two in 52, three or more in 17 |
| Sizes step by a modular ratio, such as 1.2 | The step between a layout's sizes runs from 1.03 to 3, a quarter of the steps under 1.25, the median 1.5; the brands' scales step a median 1.17 |
| One display text per screen | Of the 69 layouts with two sizes or more, 41 show one text at their largest size |
| Nothing read under 1/54 of the frame's height, 1.85% | The smallest text of every example is at least 1.78% of the viewport's shorter side; the median example's smallest is 5.9% |
| A title-safe margin of 5 to 10% | The text nearest the edge sits a median 3% of the shorter side in; 52 of 75 layouts hold one within 5% |

Paper and ink's `TEXT_SIZE` at 1080 set a tag of 11 pt, 1.4% of the
shorter side, a name of 12 pt, 1.5%, and body text of 14 pt, 1.7%: all three
under the smallest text of any official 2D game example. The fallback's
record had left them open, as sizes set for a desktop window.

## Options

1. **A type scale: every label takes a size of `TEXT_SIZE`.** The brands'
   systems and the examples' one or two sizes a layout agree, and the
   template's helpers already take every size from `TEXT_SIZE`, so the check
   finds only a size a model wrote by hand. It is the type's twin of
   `colour.palette-only`.
2. **A floor for the smallest text, from the examples and the video
   styles.** The fallback's three small kinds failed it, and the user had
   chosen those sizes on screenshots, so the floor was the user's call: to
   keep them, or to scale paper and ink by 4/3 and hold the floor in every
   look.
3. **A modular ratio between sizes, one display text per screen, or a
   title-safe margin.** The examples fail each, as the table shows.
4. **One accent per screen**, from the brands' one call to action. A game's
   accents mark kinds of content, every coin in `reward` and every hazard
   in `danger`, so a screen shows many.
5. **A reading time for text that leaves by itself.** It holds on a game,
   but the template has no helper that shows a text for a time; the events
   that hide a text are the game's own. It belongs with the pitfalls of
   event sheets, not here.
6. **A colour fingerprint of a screenshot**: its share of neutral and of
   colourful pixels, against the look's mode. It would tell a fallback that
   drifted from paper and ink, but `write_png()` already holds every drawn
   pixel to `PALETTE`, and the study's numbers describe its sample, not a
   threshold.
7. **A shadow cut by its container, measured at the end of each tween.**
   `review_look.py` finds a HUD instance the screen's edge cuts, and the
   instance's box holds the shadow that `shape()` draws into its image.
   Nothing in a game clips an instance to a parent, so nothing more is cut.
8. **One closed border on any line of sight; concentric corner radii;
   figures of one width for a changing number.** No project file says
   where a border is drawn, since borders are in the images; the template
   draws no rounded corners; the Text plugin sets no font features.

## Decision

Option 1, as `type.scale`, enforced in every look:

- `on_scale()` stops the run when `text_inst()` gets a size that is none of
  `TEXT_SIZE`'s values, naming the kinds and their sizes, `text_size(kind)`,
  and the way out: a kind of text the look lacks is a new key of
  `TEXT_SIZE`, as a colour is a new role of `PALETTE`. Every helper passes
  it, so it stops as `spaced()` does, on a size placed by hand.
- It holds in every look, because `TEXT_SIZE` is the look's own scale: a
  look the user gave sets its sizes by kind, as it sets its colours by role.

Option 2 as `type.min-size`, enforced in every look, which the user chose
on 2026-10-23:

- `TEXT_SIZE` takes the prototype's px at 720 as points, 4/3 its former
  size: at 1080 a tag of 15 pt, a name of 16, body text of 18, a title of 30
  and the count of 60. The tag is 1.85% of the shorter side at every
  viewport over 360 px high, give or take the rounding to whole points.
- `on_scale()` stops a label whose em is under `TEXT_MIN`, 1.75% of the
  viewport's shorter side, naming the kinds of `TEXT_SIZE` under it and the
  size they need. The floor sits under the examples' 1.78% so the rounding
  of a whole point passes at every viewport the template draws. A pixel-art
  letter, one unit, is 2.2% or more of a viewport 360 px high or less.
- It holds in every look, because it is legibility, not taste: a look the
  user gave with smaller text stops until its sizes are raised.
- Body text at 18 pt is large-scale text under WCAG 2.2, so
  `text_contrast()` asks it 3:1 where it asked 14 pt 4.5:1.
- The HUD grows with its text: the stand-in's score group ends 30 px lower
  at 1080, and the stand-in's board no longer fits the play area of an
  800×450 viewport, as it did not fit 640×400 or 960×540 before.

Options 3 and 4 as rejected rules of the manifest, `type.modular-scale`,
`type.one-display`, `layout.title-safe` and `colour.one-accent`, each with
the measurement that turned it down. Options 5 to 8 are left out for the
reasons above.

## Re-evaluate when

- A game needs a size between two kinds and adds a kind for it more than
  once: the kinds of `TEXT_SIZE` are too few for some kind of screen.
- Generated games are played on phones: a phone's smallest text, about
  11 to 12 dp, is a higher floor than the examples' (`paper-and-ink-look.md`).
- A look the user gave stops on the floor and its text reads well on the
  user's screenshots: the floor is too high for that kind of screen.
- A generated game shows a text for a time and the player cannot read it
  before it leaves: a helper for a timed text, with the reading time as its
  check.
- The example clone updates: rerun `measure_layout.py --text`.
