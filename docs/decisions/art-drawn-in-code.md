# Art Drawn in Code as SVG: The Route Without an Image Tool

Date: 2026-10-30
Schema: Construct 3 r506.3

## Problem

A game's art comes from two places. The generator template draws stand-ins
with `shape()`. `art()` takes the pictures of the client's image tool, and
`prepare_art.py` cuts them out and fits them (`art-from-the-image-tool.md`).
A game without an image tool keeps its stand-ins.

The skill says that art is not drawn in code. A small model drew a card
game's art pixel by pixel in Python, and the screen showed four drawing
styles and fifteen enemies made from one template. The template writes its
PNGs with the standard library, and only `prepare_art.py` and the
recording's contact sheet use Pillow. So the method failed, not the
library: the model computed pixels with nothing to hold a style, and it
never looked at the result.

Task: find out whether a model can make art that looks finished without an
image model, and what that route would take, before the skill changes.

## Evidence

### Code-drawn art that holds a style

Agent projects that draw pictures and films with code and no image model
hold one style across a whole piece. They draw in SVG, Canvas or WebGL and
render in headless Chrome. Four things carry the style:

- a palette as named constants, and drawing functions that every picture
  shares;
- a medium richer than plain shapes, such as brush strokes, washes and ink
  outlines, because plain geometric shapes read as dated and crude;
- a character drawn by one function, whose poses and views are calls of it
  with other parameters;
- a render that the model reads, on a contact sheet or a model sheet,
  against written review questions.

The card game had none of the four.

### A drawing loop measured here

An experiment drew pixel art for Construct frames through the template's
own PNG path, with the standard library only. It drew a character in three
poses and two items. Drawn blind, the first version had faults that showed
only when the frames were enlarged. The model then read a contact sheet of
its own render, twice, and each round removed the faults it saw. So the
look loop fixes what the drawing alone misses. The drawings and the sheets
are in the evidence folder of Construct3-RAG,
`.local/docs/evidence/art-look-loop/`.

### Frames of one object

Pictures of one character drift between frames when an image tool makes
them, because each picture is generated and fitted on its own. A character
drawn by one function with pose parameters keeps its proportions, box and
baseline in every frame by construction.

### Rendering without Pillow

Chrome headless renders a page that holds an SVG to an RGBA PNG when its
default background is clear (`--default-background-color=00000000
--screenshot`). The corners come out clear and the edge keeps a soft
alpha. The skill already drives Chrome through its own DevTools client in
`open_in_editor.py`, so the renderer adds no dependency. A drawing rendered
at its box size needs no cut-out and no resample.

### Inside Construct

- SVG Picture shows one SVG file at any resolution. It has no animation
  frames, no collision polygon and no hit frame, and few official examples
  use it.
- Drawing Canvas draws at runtime. The editor's layout view shows nothing
  until the game runs, and a resize stretches the drawing until the next
  redraw.
- Effects change pictures that exist, and none makes one.

## Options

1. **Keep the routes as they are.** A game without an image tool keeps
   stand-ins that read as a sketch. The frames of one object from an image
   tool keep their drift.
2. **Code drawn and rendered in the browser, as a second source for
   `art()`.** Chosen.
3. **SVG Picture objects at runtime.** They have no frames and no collision
   polygon, so they suit a backdrop or a decoration at most.
4. **Drawing Canvas at runtime.** The editor shows an empty layout, and the
   look checks have nothing to judge before the game runs.
5. **Pixels drawn in Python with a look loop, as in the experiment.** It
   converges, but the model computes every shape by hand. Option 2 keeps
   the loop and adds paths, gradients and strokes.
6. **CC0 packs, the editor's bundled asset packs, or an example's art.** Not
   used. The look is Construct's own, not a pack's. The bundled packs import
   as new object types that an agent cannot fetch. An example's images carry
   no names that say what part they play.
7. **A paid pixel-art model, or an image model on the user's machine.**
   These are image tools, so they feed the existing route unchanged.

## Decision

Option 2, as the second route of `art()` and its default, which the owner
chose on 2026-10-30 (`art-entry-point.md` gives the entry point):

- `ART_ROUTE = "svg"` in the template, and `art(..., route=)` for one
  object. The game's `tools/drawings.py` draws `art/<name>.svg` with
  `scripts/svg_kit.py`, and `scripts/art.py` renders each drawing in
  headless Edge or Chrome at its box size on a clear background, with its
  hit frame, then runs the generator, which takes the PNG with the
  stand-in's box, origin and collision polygon.
- svg_kit writes each role of `PALETTE` as a CSS variable that `art.py`
  sets when it renders, so a drawing names roles, never colours; `shade()`
  and `light()` mix a role towards ink or canvas. The hit frame is the
  same drawing with the picture's role in the flash colour. `art.py`
  refuses a drawing that names a colour (rule `art.roles`).
- Every id in a drawing starts with the drawing's name (rule `art.ids`):
  measured on 2026-10-30 in Chrome 152, two inline SVGs on one page that
  both define `id="g"` both paint with the first one's gradient.
- The kit carries textures as SVG filters of its own, a paper grain, a
  hand-drawn edge and a watercolour wash, and `stroke()`, a brush line that
  thickens in the middle. They need no library, so nothing loads from the
  network and no licence is added.
- A character is one drawing function with pose parameters, its frames
  calls of it from the same `d.ground`; `art.py` finds frames of one
  animation whose box, feet or middle differ (rule `art.frames`).
- Pixel art draws `pixels()` on the grid at the game's size with
  `crispEdges`, in roles alone, and no texture.
- `art.py` writes a contact sheet of every picture at its size and
  enlarged. The `construct3:art-drawer` sub-agent reads it against five
  questions before it returns (`art-drawer-agent.md`), and the look review
  shows it after the screenshots under the same questions.

The image-tool route stays, for painted and illustrated styles that code
does not reach.

### A drawing run measured here

A card game of 14 pictures (two scenes, five cards, four enemies, three
buttons), whose stand-ins a Haiku run had replaced with pictures computed
in Pillow, was drawn again from `art.py`'s brief by one agent on each
candidate model, with its art direction and subjects unchanged:

| Model | Rounds | Tokens | Seconds | Left as yes |
|-------|--------|--------|---------|-------------|
| Opus | 2 | 157 032 | 530 | none |
| Sonnet | 3 | 179 029 | 554 | the three buttons differ only in width |

Both drew every picture in one style: an ink outline, a shade and a
highlight per form, the grain texture and brush strokes, and the four
enemies apart by shape. Both added the colours the subjects needed as new
roles of `PALETTE`. Both met the cards' role, `canvas`, whose flash is the
same white, so a card's hit frame shows no change; `art.py` says so in a
note. The drawings and the contact sheets are in
`.local/docs/evidence/art-route/`.

### The eval cases, a small main model

`dev/evals/evals.json` holds three cases of the route, each run once as a
`claude -p` session on Haiku with the plugin loaded, so the main agent
could start `construct3:art-drawer` (Opus); every run did:

| Case | Grader | Cost | Seconds | Look judge, two Haiku runs |
|------|--------|------|---------|----------------------------|
| `art-without-an-image-tool` | 5 of 5 | $0.40 | 209 | not run |
| `walk-cycle-frames` | 6 of 6, four frames on one row | $0.62 | 427 | not run |
| `card-game-art` | 4 of 4 file assertions | $3.15 | 1 490 | question 6 no on every picture in both; question 4 yes on the art sheet in both, for an empty card slot drawn as a dashed outline, and on the battle screen in one, for the enemy's health bar, a flat bar of the template |

So on the card game the judge told the four enemies apart and found one
style among the drawn pictures; what it called a style of its own was a
slot meant to stay empty and a bar the template draws, not a drawing. The
runs and their transcripts' ids are in `.local/docs/evidence/art-route/`.

## Open

- Which model the art sub-agent runs. The owner picks after the runs
  above; until then it names Opus.
- Whether a stroke library such as a freehand-stroke one should replace
  the kit's own `stroke()`, under which licence, and whether the plugin may
  carry it or it goes to the user's cache, as the fonts do.

## Re-evaluate when

- A run of `card-game-art` or `walk-cycle-frames` leaves a drawing in a
  style of its own on a screen, or enemies the judge takes for one another:
  record it here and change the brief or the kit, measured on the same
  case.
- The template's bars and slots read as stand-ins beside drawn art on more
  screens: draw them through `art()` too.
- A client's image tool returns frames of one object without drift. Then
  drawn characters matter only for the clients without one.
- Construct gives SVG Picture animation frames or a collision polygon.
