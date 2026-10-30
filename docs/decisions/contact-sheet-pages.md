# The Contact Sheet Comes in Pages a Model Reads at Their Own Size

Date: 2026-10-31

## Problem

A contact sheet of one PNG 1600 px wide and as high as its page reaches
thousands of px on a game with many pictures: 7430 px on the card game of
the art-route runs. A model scales an image taller than 2576 px down before
it reads it. The art agent and the look judge then see each picture at the
sheet's scale, not at the enlarged size that the sheet gives it.

## Evidence

- Claude's vision guide
  (<https://platform.claude.com/docs/en/build-with-claude/vision>,
  "Resolution and token cost", read 2026-10-31): Claude 4.7 and later
  models read an image at up to 2576 px on its long side and 4784 visual
  tokens of 28x28 px, other models at up to 1568 px and 1568 tokens, and
  scale a larger image down to fit. A request with more than 20 images
  refuses an image over 3000 px on a side.
- A 7430 px sheet is read at 2576/7430, about 0.35 of its size. A 10 px
  caption written at the bottom of the card game's sheet could not be read
  on the whole sheet and read clearly on a 1600x2240 crop of it.
- 1600x2240 px is 58x80 = 4640 tiles, under 4784, and under 2576 px on its
  long side, so a high-resolution model reads such a page at its own size.

## Options

1. **One sheet, scaled down by the script.** Small, but every picture is
   then read smaller, which is what the sheet's enlargement is there to
   undo.
2. **One sheet with fewer, smaller enlargements.** The sheet of a game of
   forty pictures still passes 2576 px.
3. **Pages of at most 1600x2240 px.** Chosen.

## Decision

Option 3.

- `art.py` lays the sheet out and measures the box of each heading and
  figure in the browser. It cuts the sheet into pages of at most `PAGE_H`
  = 2240 px, halfway between two rows of pictures, and a heading stays
  with the row under it. It writes the pages as PNG files
  `.tmp/scripts/art/contact-N.png`, where N counts from 1, and lists
  them.
- A scene or a panel on the sheet is at most half the sheet's width and
  `PAGE_H` less 160 px high, so that it shares a page with its heading.
- The art agent's brief asks it to open every page and to answer the
  questions over all the pages together. `review_look.py` names each page
  `Art sheet N` in the look review's brief, a picture of its own under the
  same questions, and says that the pages are one sheet.
- `dev/tests/test_skill_art.py` renders a sheet of forty pictures and a
  tall scene in the machine's browser and checks the size of each page.

## Re-evaluate when

- The vision guide changes its limits: `PAGE_H` follows the token limit of
  the models the art agent and the look judge run.
- A run asks for more than 20 images in one request: a page stays under
  3000 px, so this limit is met already.
- An agent judges two pictures alike or apart across two pages wrongly:
  the pages then need the frames of one object kept on one page.
