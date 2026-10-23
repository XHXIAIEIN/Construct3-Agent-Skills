# Pixel Art Draws Its Text in a Baked Sprite Font

Date: 2026-10-22
Schema: Construct 3 r506.3

## Problem

At a viewport 360 px high or less the generator template draws pixel art:
*Nearest* sampling at a whole-number scale, images in the roles of
`PALETTE` with hard edges. A label in a Text draws at the screen's
resolution with antialiased edges: a smooth shape among pixel art, whose
edges blend the role and the paper into colours of no palette.
`review_look.py` asks about exactly that mix.

Task: in pixel art the labels keep the pixel grid and the palette's
colours, in Latin and in Chinese, without a step the agent has to remember.

## Evidence

### What the screen shows

A 320×180 game from the template with Texts, previewed at twice its
size: the board of shapes held no colour outside the palette, and the
three labels held every colour the screen had outside it.

### What the official examples do

Among the official examples at a viewport 360 px high or less with
*Nearest* sampling that show text, most draw it in Sprite Fonts, and none
mixes the two plugins. They fade a Sprite Font in and out by its
opacity, through Tween or the Fade behavior, and dim the screen behind a
message with a translucent Tiled Background; one holds the labels it plays
down at 25%. So the runtime blends colours on every one of these screens:
what stays in the palette is the image, not the frame.

### The font

Fusion Pixel Font (`https://github.com/TakWolf/fusion-pixel-font`), under
the SIL Open Font License 1.1; the fonts it is assembled from are under
the same license, and misaki permits any use with or without change. The
8 px proportional build has a Simplified Chinese variant whose glyphs, the
Latin ones among them, are one design. Its pixel size is the template's
`UNIT` in pixel art, so the template's text sizes of one and two units are
scales 1 and 2. Every glyph of printable ASCII, the common CJK punctuation
and both levels of GB2312 fits a cell of 8×8 px, six rows above the
baseline and two below, within its own advance.

The user's font cache holds it, as it holds Inter
(`paper-and-ink-look.md`, "The font"); the repository and the plugin carry
no font file. Source: release 2026.10.16,
`https://github.com/TakWolf/fusion-pixel-font/releases/download/2026.10.16/fusion-pixel-font-8px-proportional-bdf-v2026.10.16.zip`,
sha256 `f26864c613cf502e6ea9f5d397469584b27bd49a1cee7c2c0c996b6900fcbe2d`;
the file is its `fusion-pixel-8px-proportional-zh_hans.bdf`, saved under
that name in the font cache. BDF is text, so a script reads its bitmaps
without a font library.

## Options

1. **Keep Texts, and accept the blend.** The examples blend colours too.
   But they draw letters on the pixel grid, and a smooth label among pixel
   art is the mistake the look review asks about.
2. **A Latin pixel font in a Sprite Font, Chinese in a Text.** Two drawing
   styles on one screen whenever a game is in Chinese.
3. **One pixel font for both, every common character baked.** The first
   level of the common table in the image of every text type, whatever
   the game says.
4. **One pixel font for both, the characters in use baked, by a script
   that can run again.** The images stay small. A character that events
   build at runtime and no string holds draws as nothing, unless the check
   finds it or the agent adds it.

## Decision

Option 4: pixel art and Chinese in one style, with images that hold only
what the game shows.

- `PIXEL_FONT` in `assets/build_project.py` names the font. In pixel art
  with the file in the font cache, `text_type()` makes a Sprite Font and
  `text_inst()` an instance of it at scale size / `UNIT`, its glyphs white
  and tinted to the label's role by the instance's colour, so a label is
  the role's colour exactly. Boxes are sized by the font's own advances.
- `build_all()` writes `tools/pixel-font.json`, the font and the types,
  and runs `scripts/bake_font.py`. The script bakes:
  - the texts of the types' instances;
  - every string in the event sheets and in `files/`;
  - printable ASCII;
  - the characters that `--add` kept in the file's `added`.

  Its default run appends to what the images hold; `--replace` drops what
  is no longer in use; `--check` writes nothing. The spaces of U+2002 to
  U+200A, which the font lacks and `tracked()` uses, are baked as blank
  cells of their em width.
- `check_look.py` reports a character in use that is not baked
  (`type.pixel-font`), and `check_project.py` holds a Sprite Font to the
  edge, contrast and banner checks it holds a Text to.
- A key's box holds a pixel of paper above and below the line inside its
  outline, since a Sprite Font's line is exactly its cell.
- `colour.palette-only` covers the images the template draws. What the
  runtime blends, an opacity, a fade or the shadow's alpha, is outside it,
  as it is in the examples; the keys still dim to 35% by opacity.
- Without the font file the run warns and draws Texts, as a weight of
  `FONT` without its file draws in `system-ui`.

## Re-evaluate when

- A game's text is built at runtime from characters no string holds, such
  as names a player types: bake the first level of the common table for
  it, or keep that text in a Text.
- Players read 8 px Chinese poorly on a phone: the 10 px and 12 px builds
  of the same font need text sizes of their own in pixel art.
- An agent adds a word without `--add` and ships it blank although the
  check names it: run the check where the generator runs it.
