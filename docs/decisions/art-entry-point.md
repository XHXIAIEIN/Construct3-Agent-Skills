# One Script Moves Every Picture of a Generated Game

Date: 2026-10-30

## Problem

A generated game took its pictures in four manual round trips:
`prepare_art.py --list` printed one step at a time (the art direction, a key
picture, a prompt per picture), the session's image tool made each picture,
`prepare_art.py` cut it out and fitted it, and the generator ran again to
take it. Claude Code has no image tool, so most runs stopped after the first
step and kept the stand-ins. Nothing drew the art of a game without one.

## Options

1. **Keep the steps, and add a second script for drawings.** Two entry
   points, each with its own round trips.
2. **One script, `scripts/art.py`, that moves each picture as far as it
   can.** It runs the game's drawings, renders them, fits the image tool's
   pictures, runs the generator when it wrote a picture, writes a contact
   sheet, and prints one table: each picture's route, its state and the
   next step. Chosen.
3. **The generator calls the renderer.** The generator is stdlib only and
   runs in a second; a browser start takes one to two seconds a run, and a
   render needs the box sizes that the generator's own `art()` calls write.
   So the generator would render the drawings of its previous run.

## Decision

Option 2. `prepare_art.py` keeps the cut-out and the fit as the image
route's module, without a command of its own.

- The generator does not call `art.py`. It prints how many sprites show
  their stand-in and names `art.py`; `art.py` runs the generator after it
  wrote a picture, so that `art()` takes it.
- Pillow is needed only to fit a picture of the image route. The SVG route
  renders in the browser that `open_in_editor.py` drives and reads the PNG
  with the standard library.
- Every failure names what to do next. A drawing or a picture refused three
  times keeps its stand-in (`art/refused.json`), and the art sub-agent stops
  after three rounds.

## Re-evaluate when

- A client gives the agent an image tool that returns frames of one object
  without drift: the image route can then take characters too.
