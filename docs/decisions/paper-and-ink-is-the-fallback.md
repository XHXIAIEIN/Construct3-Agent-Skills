# Paper and Ink Is the Fallback Look

Date: 2026-10-23

## Problem

The generator template holds one look, paper and ink
(`paper-and-ink-look.md`, `greybox-blockout.md`), which the user chose on
screenshots. The skill, the manifest and the records presented it as the
look of every generated game until its art arrives. None of them said that
a style the user gives replaces it. Several rules marked `enforced` and
strict stopped the generator on a game that departed from it, whatever the
user had asked for.

On 2026-10-23 the user stated that their look templates are a fallback:
the default design when the user gives no style, no art direction and no
context to take one from.

Task: paper and ink holds only when the user gave no look. When the user
gave one, the user's look comes first, and no rule of paper and ink's taste
stops or flags the game, while the rules that keep any look readable and on
the grid still hold.

## Evidence

What each strict or stopping rule of `assets/look-manifest.json` did to a
game with a palette and a backdrop of the user's, read from the template's
helpers and `scripts/check_look.py`:

| Rule | What stopped | Held to paper and ink? |
|------|--------------|------------------------|
| `palette.greys` | `check_palette()`: `canvas` and `canvas_alt` over 1.2:1 | Yes. A night sky of two blues 1.32:1 apart stopped the run, though the ratio only keeps the transparency checker reading as texture |
| `backdrop.sheet` | `backdrop()` of any type but the plain or checker pattern | Yes. A backdrop tile of the user's could not be laid |
| `pattern.areas` | `area()` of any type but `pattern()` stripes; caution and hazard stripes over a quarter of the viewport | Yes |
| `motion.hit` | `beh_def("Flash")`, and `check_look.py` on a Flash behavior | Yes. The Flash behavior was turned down because no published game in the evidence uses it for a hit and it blinks the shadow too: taste, not a fault |
| `colour.palette-only` | `write_png()` on a colour outside `PALETTE` | No: `PALETTE` holds whichever colours the look has, and a painting passes `painted=True` |
| `colour.accent-contrast`, `text.contrast`, `control.parts` | `shape()`, `readable()`, the controls: under 3:1 or 4.5:1 on the role behind | No: contrast against the look's own colours (WCAG 2.2, 1.4.3 and 1.4.11) |
| `solid` 3:1 on `canvas_alt`, part of `palette.greys` | `check_palette()` | No: structure shows without an outline in any colours |
| `alpha.pure`, `grid.*`, `pixel-art.sampling`, `motion.squash-art` | `write_png()`, `shape()`, `on_grid()`, `check_look.py` | No: clean edges, placement and a collision box that does not sink are no matter of taste |

So a user's palette passed every check but the paper's 1.2:1, and a user's
backdrop, area tiles or blinking hit could not pass at all.

## Options

1. **Leave the checks; the agent edits the helpers when the user gives a
   look.** A helper redefined below the end marker wins, but every game
   with a style of its own would carry copies of the helpers, and a small
   model meets the stop before it thinks of that.
2. **Make paper and ink adopted, not enforced.** The fallback would lose
   its checks too, and the user chose that look to be held by default.
3. **A setting the generator holds when the user gave a look, read by the
   checks.** Chosen.

## Decision

Option 3.

- `USER_LOOK`, a setting of the template's look part, names where the
  user's look comes from: a style or an art direction the user named, or
  references or an existing project to take it from. Empty, the game takes
  paper and ink. A generator older than the setting gets `""` between the
  markers, so it keeps paper and ink.
- `paper_and_ink()` is true while `USER_LOOK` is empty. Only then do
  `check_palette()`'s 1.2:1, `backdrop()`'s checker pattern,
  `area()`'s pattern and stripe size, and `beh_def()`'s refusal of the Flash
  behavior stop the run, each with a message that names `USER_LOOK`. With it
  set, `backdrop()` and `area()` take any Tiled Background type, and
  `z_order()` still puts the backdrop first and the areas next.
- `check_look.py` reads `USER_LOOK` from `tools/build_project.py` and leaves
  `motion.hit` out when it is set, saying so in a line of its output.
- Every rule of the manifest has a `scope`: `every-look` for legibility,
  contrast, the grid, a clean alpha channel, the screen, the layout's
  spacing, the art's route and the pacing; `paper-and-ink` for the
  fallback's taste: its colours, type, HUD, lines, shadows, outline,
  pointer colours, squash values, backdrop, stripes and hit. The `solid`
  3:1 of `palette.greys` became a rule of its own, `colour.structure`, in
  every look. The `deliver` steps start by settling the look.
- `SKILL.md`, `references/generating-a-project.md` and the Cookbook's
  "Viewport, look and HUD" say the same.

The questions of the look judge, `construct3:look-judge`, name no rule of
paper and ink, so they hold in every look, and its brief carries no
`USER_LOOK`: a game whose look the user gave is not judged against paper
and ink.

## Re-evaluate when

- A run with a look the user gave is stopped by a rule of scope
  `paper-and-ink`: a helper still holds the fallback's taste.
- A run sets `USER_LOOK` when the user gave no look, to pass a stop: the
  setting needs a source a check can see, such as the references' files.
- The user picks a second template look: `USER_LOOK` then chooses among
  looks, not between one look and the user's.
