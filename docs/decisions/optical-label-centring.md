# A Label Is Centred on Its Shape by Its Ink

Date: 2026-10-30
Schema: Construct 3 r506.3

## Problem

A label centred on its shape by geometry looks high. A button's label box
is the shape's box, the name box of a toggle or a bar is as high as the
control beside it, and all of them have Vertical alignment Center. A player
sees the ink, not the box, and the ink of capitals, digits and Chinese sits
above the box's centre. A triangle placed on a disc by its box looks low,
because its area is heavier at its base.

The runtime places a Text as follows. A Text without BBCode draws each line
on a canvas with `textBaseline` "top", one em high, and Center puts the
first line at half the box's height less half the lines' height, but never
above the box's top (`lib/gfx/text.js` of r506.3). So Center centres the em
box, not the capitals, not the Chinese and not the font's ascent and
descent.

The generator's labels, bars, toggles, stage labels and Sprite Font labels
must look centred on what they sit on or beside.

## Evidence

### The offsets in the preview

A probe project from the template, previewed in the editor's preview
(Edge on Windows 11), is measured by hide-and-diff: shots of each label
shown, set to its capitals or Chinese, and hidden, and of its shape hidden.
The offset runs from the centre of the shape's face to the centre of that
ink, in px, negative upwards. At 1280×720 the Texts draw in system-ui,
with Chinese in the platform's fallback face. At 640×360 they are Sprite Fonts of Fusion Pixel 8 px
(`pixel-art-sprite-font.md`). These are the labels centred by their box:

| Viewport | Label | Size | Capitals | Chinese |
|----------|-------|------|----------|---------|
| 720 | button | title, 26.7 px | -2.5 (0.094 em) | -3.0 (0.112 em) |
| 720 | button, toggle, bar | body, 16 px | -1.5 (0.094 em) | -2.0 (0.125 em) |
| 360 | button | 16 px, scale 2 | -2.0 (1 font px) | -1.0 (0.5 font px) |
| 360 | button, toggle, bar | 8 px, scale 1 | -1.0 (1 font px) | -0.5 (0.5 font px) |

The shots resolve half a pixel. Capitals and Chinese differ by 0.5 px at
720 and by half a font pixel at 360. Measured on its whole ink, "Play"
sits centred, because its descender balances the capital; measured by its
capital, it sits as high as "Continue". A canvas probe in headless Chrome
that draws as the runtime draws puts capitals and Chinese 2.5 to 3.5 px
high at 27 px in Segoe UI, Microsoft YaHei and Arial too (0.09 to 0.13 em),
and a lowercase "x" within 1 px of the centre.

In Inter 4.1, the subsets of `template-font.md`, the same probe lowered by
system-ui's value measures every label 1.0 px low at both sizes, capitals
and Chinese alike, because Chinese falls back to the platform's face but
stands on Inter's line. Centred by their box, they would sit 2 px high at
the title size (0.075 em) and 1 px high at the body size (0.063 em).

A triangle 64 px high centred on a disc by its box has its area's centroid
10.75 px below the disc's centre, a sixth of its height. The template's
triangle points up, so its centroid is two thirds down from its apex.

A line taller than its box draws from the box's top: a bar's name whose
8 px Sprite Font box is shrunk to 6 px moves 2.5 px, not 1.

### With the helpers

A probe from the template measures every label within 0.5 px of its face's
centre, down and across, at both viewports, and each triangle within
0.31 px. In Inter every label measures 0.0 px off centre down.
The shots, the
results and the probe are in `.local/docs/evidence/optical-align/`.

## Options

1. **Centre each string by its own ink.** The label moves by what its
   letters happen to be, so "Play" and "Continue" on two buttons of one
   menu stand on two lines.
2. **One offset per face and size, set by the capitals and the Chinese.**
   They differ by at most half a pixel at 720 and half a font pixel at 360,
   and not at all in Inter,
   so one value serves both, and every label of one size stands on one
   line. Chosen.
3. **One offset per script.** It would separate values that differ by no
   more than the measurement can tell.

A label moves down in one of two ways. Shrinking its box from the top by
twice the offset keeps a button's label inside its shape, so the overlap
check, which passes a box wholly inside another, still passes. Moving its
box keeps the box a line high, which a box of exactly one line needs. A
label inside a shape or a control's row shrinks its box; a bar's name and a
stage label move it.

For the triangle, drawing it shorter so that its centroid is its box's
centre changes its proportions. Its origin at the centroid, and
`shape_inst()` raising it by a sixth of its height, centre its area and
keep its size.

## Decision

The template keeps `OPTICAL_EMS`, the share of the em by which capitals
and Chinese sit high, by face: 0.11 for system-ui, between 0.094 and 0.125,
and 0.07 for Inter Regular and Medium, between 0.063 and 0.075. A face that
the table does not list, InterDisplay Light among them, takes system-ui's
value.
`optical_drop()` returns the px for a text, a size and a weight: 0 for a
text of short lowercase letters only, which sits centred. In pixel art it
is the Sprite Font cell's centre less the centre of "H" as `bake_font.py`
bakes it, in whole font pixels times the scale. `button()` and the label of
`toggle()` and the other controls shrink their box from the top by twice
it; `labelled_bar()` and the stage band of `band_text()` move their box
down by it. A triangle of `shape()` has its origin at its centroid, and
`shape_inst()` raises it by a sixth of its height.

## Re-evaluate when

- `FONT` names another face, or a label is set in InterDisplay Light:
  measure it and give it its own line in `OPTICAL_EMS` if it differs from
  system-ui by more than the shots resolve at the title size.
- A release changes how `lib/gfx/text.js` places a line, such as its
  `textBaseline`.
