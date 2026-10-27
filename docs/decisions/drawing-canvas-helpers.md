# The Generator Places a Drawing Canvas over the Viewport with Antialiasing Off

Date: 2026-10-28
Schema: Construct 3 r506.3

## Problem

A game that draws lines or ribbons at runtime needs a Drawing Canvas type
and instance. Without a helper it types the four instance properties from
memory, and it chooses how many canvases to place and whether to antialias
them with nothing to say what either costs. Both choices cost frames that
the game's own events do not show.

## Evidence

- The schema `plugins/drawingcanvas.json` lists four instance properties:
  `resolution-mode` (`auto`, `fixed`), `initially-visible`, `origin` (nine
  positions) and `antialiasing` (`off`, `2x-msaa`, `4x-msaa`, `8x-msaa`).
  An instance with the origin `center` has `originX` and `originY` of 0.5
  in its world, one with `top-left` 0 and 0. The official examples leave
  antialiasing off.
- The manual says MSAA makes rendering slower and uses more memory, and
  higher levels slower still (`plugin-reference/drawing-canvas.md`,
  "Antialiasing").
- In a game project, one full-screen canvas that drew five ribbons ran
  faster and used less of the GPU than five full-screen canvases, one per
  ribbon, each cleared every tick.
- On the same game, 2x or 4x MSAA on its one canvas held the preview well
  below the display's rate on a screen of about 3840x2054 device px. At
  1280x720 off, 2x and 4x measured alike, so the cost shows on a large
  canvas.

## Options

1. No helper: each game writes the type and the instance. The property
   values stay unchecked, and nothing states the cost of a canvas.
2. A type helper and an instance helper with the schema's values, the
   viewport's size and antialiasing off by default, and the cost of extra
   canvases and of MSAA in the docstring.
3. Option 2 with a check that stops a second full-screen canvas on a layer.
   Two canvases on one layer can be a correct design, so the check would
   stop such games.

## Decision

Option 2. `drawing_canvas_type()` writes the type with the keys of the
examples' object types. `canvas_inst()` places it over the viewport from the
origin top-left by default, takes `origin`, `antialiasing` and `resolution`
as the schema spells them, stops the run on any other value, and sets the
world's origin from `origin`. Its docstring says to draw many shapes on one
canvas and to keep antialiasing off on a canvas the size of the screen.
`dev/tests/test_skill_build_project.py` compares the helper's three sets of
values with the schema. The runtime behaviour of the drawing actions, such
as *Reset polygon* and the line caps, is on the Cookbook's Drawing Canvas
page.

## Re-evaluate when

- The schema adds or renames a Drawing Canvas property or value, which the
  test then reports.
- A game needs a canvas that the helper cannot place, such as one in a
  hierarchy.
- A measurement on a phone shows MSAA cheap on a full-screen canvas.
