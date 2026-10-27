# Art Drawn in Code and Rendered in the Browser: The Route to Try Next

Date: 2026-10-28
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
   `art()`.** Chosen to prototype.
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

Option 2, as a prototype. The skill, the template and `SKILL.md` stay as
they are until the prototype passes the run under "Re-evaluate when". Until
then, the rule of `assets/look-manifest.json` that art is not drawn in code
holds. The prototype has this shape:

- `art()` takes a drawing beside a picture: `art/<file>.svg`, or a page that
  draws on a canvas. A script renders it in headless Chrome at its box size
  on a clear background to `art/<file>.png`. The PNG then takes the
  picture's path, with the stand-in's box, origin and collision polygon, so
  the layouts and the events stay as they were.
- A style module is written from `PALETTE` and `SHAPE_STYLE`: the colours by
  role, the line width, the shadow and the outline. A drawing names roles,
  never colour literals, so a game's drawings share one medium. The hit,
  hover and pressed frames are the same drawing with one role swapped.
- A character is one drawing function with pose parameters, and its frames
  are calls of it.
- The module carries helpers for strokes, washes and outlines, so a drawing
  is more than plain shapes. They load from the project or the user's
  cache, never from the network at render time.
- Pixel art draws on the pixel grid at the game's size, without smoothing.
- Every drawing goes on a contact sheet at its size and enlarged. The model
  reads it with the look questions of `review_look.py` before the
  hand-over.

The image-tool route stays as it is, for painted and illustrated styles
that code does not reach.

## Open

- Whether a small model draws as well in SVG is unknown. The card game's
  four styles came from a small model.
- Which stroke library to use, under which licence, and whether the plugin
  may carry it or it goes to the user's cache, as the fonts do
  (`paper-and-ink-look.md`).
- How long a drawing takes to render, and whether the tests can render
  without Chrome on the machine.

## Re-evaluate when

- A small model runs the card-game case with the prototype. Adopt the route
  when the look judge finds one style on every screen and tells the enemies
  apart, and the frames of each object share their box and baseline.
  Otherwise record what failed here and keep the stand-ins.
- A client's image tool returns frames of one object without drift. Then
  drawn characters matter only for the clients without one.
- Construct gives SVG Picture animation frames or a collision polygon.
