# Each Kind of Text Has Its Own Leading

Date: 2026-10-31

## Problem

The template sized every Text's line at 1.2 em, whatever the kind of
text, and left the Text's `line-height` property at 0. The runtime does
not draw 1.2 em, so a box and the text in it disagreed: the count's box
was 12 px taller than its line, and body text sat tighter than the box
assumed.

## Evidence

Measured in the preview, the `textHeight` of a Text of one, two and three
lines at 1920 × 1080:

| Kind | em | One line | Line in em |
|------|----|----------|------------|
| tag, 15 pt | 20 px | 24 px | 1.20 |
| name, 16 pt | 21.33 px | 25.33 px | 1.19 |
| body, 18 pt | 24 px | 28 px | 1.17 |
| number, 60 pt | 80 px | 84 px | 1.05 |

The runtime draws a line 1 em + 4 px high. The `line-height` property
adds px between lines only, so it moves the lines of a paragraph and
leaves a one-line label's height and pixels as they are. With it set, two
lines of the count measure 84 + 2.4 + 84 px and three lines of body text
3 × 28 + 2 × 2.72 px, as computed.

On the template's game with a paragraph of three lines added, the
paragraph's lines move from 28 to 30.7 px apart and wrap at the same
words, and the count's box shrinks from 96 to 87 px with the same glyph in
it. `review_look.py` finds the same two faults before and after, both the
template's own. The screenshots are in `.local/docs/evidence/round2-type/`.

The official 2D examples add little: 130 of their 137 texts of several
lines add no line height, and none adds 0.3 em (`ui-ux-pro-max-data.md`).
Body text at 1.28 em adds 0.11 em.

## Options

1. **1.2 em for every kind.** The box and the runtime disagree, as above.
2. **The runtime's own line, 1 em + 4 px.** The boxes match, and body text
   stays at 1.17 em, tight for a paragraph.
3. **Leading by kind.** Body text 1.28 em, the count and a banner 1.08,
   every other kind 1.2, with `line-height` set so that the runtime draws
   it. Chosen by the owner on 2026-10-31.

## Decision

Option 3. `LINE_EMS` in the template holds the leading of body text, the
number kind and the display kind, and every other kind takes 1.2. A size
names its kind through `TEXT_SIZE`, the first kind when two share a size.
`line_px()`, `label_box()` and `line_height()` size a box from it, and
`text_inst()` writes `line-height` as the leading less the runtime's line,
`leading()`: 2.72 px for body text at 1080, 2.4 for the count, 0 for a tag
(`type.leading`). A Sprite Font in pixel art keeps its cell as its line.

## Re-evaluate when

- The runtime draws a line other than 1 em + 4 px: measure `textHeight`
  again and change `RUNTIME_LINE_PX`.
- A game's text of several lines reads crowded or loose on a screenshot:
  change that kind's `LINE_EMS`.
