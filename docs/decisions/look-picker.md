# The User Picks a Given Look on the First Play Screen in Three Directions

Date: 2026-10-30

## Problem

When the user gives a game a look in words or references, the agent turned
the words into `PALETTE` and `ART_STYLE` itself, and the user first saw the
look on finished art. The image route asked for one key picture, a line-up
of four subjects, and showed it to the user only when the user was there;
the SVG route asked nothing. A sentence of art direction leaves most of a
look open, so the user's words reached the game as the agent's reading of
them.

## Evidence

- Paper and ink itself was chosen this way: the user compared mock-ups of
  one game screen in the template's look and in two directions drawn from
  the references, and took one (`paper-and-ink-look.md`, "The user's
  picks").
- The prototype skill of emilkowalski/skills (MIT) builds three to five
  variants that each differ on a named axis, shows one at a time at full
  size behind a fixed picker (keys 1 to N, the arrow keys, `?v=`), hands
  over a table of variant, axis, when it is right and its cost, and stops
  for the user. Variants that differ only in colour teach the user
  nothing, so it refuses them.
- `prepare_art.py` already names the six dimensions an art direction must
  fix (`DIMENSIONS`), from the image route's warnings
  (`art-from-the-image-tool.md`).

## Options

1. **Keep the key picture.** A line-up of subjects on a key colour, on the
   image route only, without the HUD, the board or the screen's colours.
2. **Static screenshots of finished games in several looks.** Each look
   costs a game's worth of art before the user has chosen.
3. **A live picker of the first play screen.** The art agent draws the
   screen at the viewport's size in three named directions, a script checks
   and renders them behind the picker, and the user's pick becomes the
   template's values. Chosen.

## Decision

Option 3, `scripts/pick_look.py`, manifest rule `look.picker`.

- It runs only when `USER_LOOK` is set. When the user gave no look, paper
  and ink applies directly, with no picker, as the owner decided
  (`paper-and-ink-is-the-fallback.md`).
- The directions are paper and ink, with the template's `PALETTE`, and two
  from the user's look, each with a `USER_LOOK` that says which part of the
  user's look it takes. Three to five are accepted.
- `directions.json` gives each direction its place on every dimension of
  `DIMENSIONS` in a phrase. Two directions differ on a dimension when their
  phrases hold other words, and every two must differ on two or more, so
  that a set of one look in three palettes is refused. Each `ART_STYLE`
  must fix all six dimensions by the words of `DIMENSIONS`.
- Each direction keeps the game's roles of `PALETTE` with colours of its
  own, and every label is a kind of `TEXT_SIZE`: svg_kit's `d.text(...,
  kind=)` writes the kind as its class, and the picker's page sets each
  kind's size and weight over whatever the drawing says. So the pick maps
  one to one onto `USER_LOOK`, `PALETTE` and `ART_STYLE`.
- A screen is checked as a picture of the SVG route is: its size, roles
  instead of colours, and ids under its own name.
- The script renders each screen in headless Edge or Chrome with its
  `PALETTE`, writes the picker with the markup, styles and wiring of the
  prototype skill's `PICKER.md` and its licence, and writes a brief that
  puts the look review's questions to `construct3:look-judge` on the three
  renders, with one more: whether a screen differs from another only in
  its colours. It prints the table, and its last line says to stop and ask
  the user.
- The folder is `.tmp/scripts/pick-look/`, by the layout of
  `scratch-and-build-folders.md`, not the prototype skill's own path.
- `--pick NAME` writes the picked values into `tools/build_project.py` in
  place, where each is set above the helpers, so the comments beside them
  stay. It keeps the picked render as `art/look.png` and deletes the
  folder. `art.py`'s brief then names `art/look.png` as the look every
  drawing follows, and on the image route every sprite's prompt gives it
  as the reference image in place of the key picture. Until it exists,
  both routes name the picker as the next step. The look review puts it
  beside the screenshot of the layout the game starts on and asks whether
  the screenshot differs from it (`reference-pairs.md`).
- A rule of status `open`, such as `subject.player-shape`, may be shown on
  the directions; the pick writes none of it, so it stays the owner's.
- On the template's game, three directions drawn by hand passed the
  checks, the keys and `?v=` switched them in headless Chrome, and the
  pick's values passed the generator's checks.

## Re-evaluate when

- The look judge passes two screens that differ only in colour, or a set
  is refused whose screens differ plainly: the word comparison of the
  phrases, or question 7, needs a measurement on screens labelled for it
  (`look-judge-calibration.md`).
- A picked look draws pictures that break from `art/look.png`: the brief
  of `art.py` needs more than the reference.
- A direction with a light `ink` on a dark `canvas` is picked: svg_kit's
  `shade()` mixes towards `ink` and `light()` towards `canvas`, so there
  they turn the other way. In the template's game the dark direction's
  coin edge came out lighter than its face.
- The owner decides `subject.player-shape`, which the picker may show
  but does not settle.
