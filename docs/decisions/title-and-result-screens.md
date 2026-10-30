# Title and Result Screens Get Their Own Type Rules

Date: 2026-10-31

## Problem

Poster design sets one huge title across the frame, small light captions
beside it, and a subject that crosses the title's letters. The look
manifest turned down the nearest rules for a game: `type.one-display`,
`type.modular-scale` and `layout.focal`. The examples that turned them down
were mostly screens the player plays on, where a menu of equal options or
two players' scores share the largest size. A title, menu or result screen
is closer to a poster, so its type was measured on its own.

## Evidence

`dev/evals/measure_layout.py --screens` sorts the texts of the official 2D
game examples by the screen they make, from the name of the layout or of
the layer that holds them. Credits, tutorials and stores are left out. A
size is a Text's size in px, or a Sprite Font's character height, as a
share of the viewport's shorter side.

| Screen | Screens | Largest text, median (range) | One text size |
|--------|---------|------------------------------|---------------|
| Title or menu | 25 | 4.4% (2.7 to 12.5%) | 17 |
| Result | 23 | 8.3% (3.6 to 16.7%); a quarter at 6.25% or less | 21 |
| Play | 123 | 7.9% (2.5 to 22%) | 84 |

Nine title screens draw the game's name as an image, and one sets it as a
Text at 9.9%. The texts of a title screen are its prompts and buttons. An image holds glow, plates and art around its letters, so
the height of its tallest line of capitals was read from each image by eye
and is recorded in the script.

| Title image | Median | Range |
|-------------|--------|-------|
| Capitals, share of the shorter side | 17.8% | 7.2 to 34.9% |
| Capitals over the size of the screen's largest text | 3.3 | 1.6 to 12.6 |

No title image has another object drawn over 5% of it, apart from the
screen's fades and the image's own shine. One logo draws its mascot over
its letters inside the image.

The template has no title screen. `hud_header()` names a menu in
`text_size("title")`: 30 pt at 1080, 3.7% of the shorter side, capitals
2.7%. A result screen's title at that size is smaller than the largest
text of every example result screen but one, and that one's BBCode sets a
larger size. The template's largest kind, `display`, is 64 pt: 7.9% at
1080, capitals 5.7%. Every example title image's capitals are larger.

## Options

1. **A result headline in `display`, centred.** It falls inside the
   examples' range, and a result screen has one moment to state.
2. **A title screen helper with a name image.** It needs the art route to
   draw the name, and the template has no title screen to put it on.
3. **Leave both screens alone.** A generated result screen keeps a title
   smaller than the examples'.

## Decision

The owner chose option 1; option 2 waits. The manifest holds three rules
of scope every-look:

- `screen.result-headline`, adopted: `result_headline()` sets a result
  screen's moment in one line at `text_size("display")`, centred on the
  screen, with an optional small tag under it. That is 7.9% of the
  shorter side at 1080; pixel art's `display` is two units, 4.4% at 360.
  A menu keeps `hud_header()`.
- `screen.title-name`, proposed: a title screen names the game in its
  largest letters, drawn as an image by the art route: capitals 7 to 35%
  of the shorter side, about 18% at the median, and 1.6 to 12.6 times the
  size of the screen's largest text.
- `screen.object-over-name`, rejected: an object of the layout drawn over
  the game's name. No example does it; where a subject crosses the
  letters, the image draws it, so it belongs to the art.

## Re-evaluate when

- The owner chooses a title screen: `screen.title-name` becomes adopted,
  and the template and its test change with it.
- A result screen needs a second line at `display` size, such as two
  players' scores.
- The example clone updates: rerun `measure_layout.py --screens`, and read
  any new title image into `TITLE_IMAGES`.
