# Title and Result Screens Get Their Own Type Rules

Date: 2026-10-30

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

The template has no title screen. `hud_header()` names a menu or a result
screen in `text_size("title")`: 30 pt at 1080, 3.7% of the shorter side,
capitals 2.7%. Its largest kind, `display`, is 64 pt: 7.9%, capitals 5.7%.
So a generated result screen's title is smaller than the largest text of
every example result screen but one, and that one's BBCode sets a larger
size. Every example title image's capitals are larger than `display`'s.

## Options

1. **Change the template.** A centred result headline in `display` and a
   title screen helper with a name image. This changes what every
   generated game shows, so it is a product choice for the owner.
2. **Record the rules as proposed.** The manifest holds the evidence; the
   template keeps its values until the user chooses.
3. **Leave the screens alone.** The measured gap stays unrecorded.

## Decision

Option 2. The manifest holds three rules of scope every-look:

- `screen.title-name`, proposed: a title screen names the game in its
  largest letters, drawn as an image by the art route: capitals 7 to 35%
  of the shorter side, about 18% at the median, and 1.6 to 12.6 times the
  size of the screen's largest text.
- `screen.result-headline`, proposed: a result screen states the moment in
  one line at `display` size, at least 6% of the shorter side, and keeps
  to one text size where it can.
- `screen.object-over-name`, rejected: an object of the layout drawn over
  the game's name. No example does it; where a subject crosses the
  letters, the image draws it, so it belongs to the art.

## Re-evaluate when

- The user chooses the result headline or a title screen: the rule's
  status becomes adopted, and the template and its test change with it.
- The example clone updates: rerun `measure_layout.py --screens`, and read
  any new title image into `TITLE_IMAGES`.
