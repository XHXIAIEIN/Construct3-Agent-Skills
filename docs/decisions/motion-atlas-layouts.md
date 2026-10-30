# Layout, Type, Colour and Motion Rules of Motion-Design Websites, Measured on Game Screens

Date: 2026-10-31

## Problem

Motion Atlas (<https://beyond-media.ai/aiweb-design>) breaks down 200
award-winning motion-design websites, each with a palette and fonts that
the site measured, a layout label, its techniques and a build prompt. The
prompts state where text sits, how large the type is, which colours play
which role and how things move. Each recurring rule was read for the game
screen it could apply to: title, menu, result, pause, a panel, or the play
screen's HUD. `title-and-result-screens.md` and
`look-from-aesthetics-skills.md` showed that web and poster rules often do
not hold on a game screen, so each rule was measured on the official 2D
game examples before it entered the look manifest.

## Evidence

The atlas's data was read in the browser and counted with patterns over
its prompts, so a count says how many prompts state a rule, not how many
sites follow it. Sizes in px are shares of a 900 px high desktop viewport;
a size in `vw` is read at 1440 px wide. The palettes are the site's
extraction, six colours a site. Every prompt asks for a reduced-motion
fallback, so that count is the atlas's template, not a design fact. The
poster prompts of vip.xiaoxiaodong.ai, the first source, refused the
browser as automated, and none of them was read.

The examples were measured with `dev/evals/measure_layout.py --frame`, by
the kinds of screen of `--screens`, and with
`dev/scripts/measure_examples.py stagger`, `eases` and `transitions`. A
title screen here is any title, menu, pause or settings screen.

| Rule | Prompts (of 200) | Official examples | Template | Decision |
|------|------------------|-------------------|----------|----------|
| A title, menu or pause screen sets its texts on the vertical centre line | 82 centre their headline or stack | 51 of 63 texts on 16 title screens of 11 examples are centred within 2% of the width; of the 10 such screens with two texts or more, 8 centre all and none centres none | `hud_header()` holds a menu's title top left; no title screen | `screen.menu-axis`, proposed |
| Text sits a small inset from the edge | Median inset 24 px, 2.7% of the shorter side | The text nearest the edge sits a median 3% in, 52 of 75 layouts within 5% (`look-from-aesthetics-skills.md`) | `MARGIN` is a fifteenth of the shorter side in whole units: 4.4% at 720, 5.9% at 1080, 6.7% in pixel art | `screen.edge-inset`, proposed |
| A change of page passes through a wipe or a fade | 41 page transitions, median 0.8 s; 38 loaders | 31 of the 51 examples that go to another layout have an object type named as a fade, transition, curtain or wipe | `go_to_layout()` cuts | `screen.transition`, proposed |
| Items that enter together start a step apart | 96 state a stagger; per site a median 70 ms, 60 to 80 ms between the quartiles | 18 waits of a constant times `loopindex` in 12 examples: median 0.125 s, a quarter at 0.1 s or less; the menus step 0.1 to 0.25 s | No stagger helper | `motion.stagger` stays proposed with both ranges |
| The display type is about 8 times the smallest label | Display median 10.7% of the shorter side; over the smallest label a median 8.4, 5.1 to 14.4 between the quartiles | A screen's largest text over its smallest: a median 2 on play screens, at most 5.3 (`--screens`); title images are 1.6 to 12.6 times the screen's largest text | `display` over `tag`: 4.3 at 1080, 6.4 at 720, 2 in pixel art | `type.scale-contrast`, rejected |
| Labels at 11 px | Smallest label a median 1.2% of the shorter side | The smallest text of every example is at least 1.78% | `type.min-size` holds 1.75% | `type.small-labels`, rejected |
| Counters and labels in a monospaced face | 37 | 4 of 81 examples show a monospaced face on a screen | Inter, light for the count | `type.mono-labels`, rejected |
| Small labels in tracked capitals | 84 uppercase, 21 also tracked | 46 of 59 lettered texts on title screens are capitals, but the 9 screens set all in capitals belong to 4 examples; 20 of 219 on play screens | `tracked()` sets a tag in tracked capitals | `type.caps-menu`, rejected |
| One family for display and body | 105 one family, 95 two | 77 of 81 examples show one face on their screens | Inter in three weights | Already held by `type.inter` |
| A dark ground | 105 dark, 66 light, 29 between | Play screens: lightness a median 0.37, 36 of 99 dark and 14 light; title screens 9 of 15 dark | Paper and ink is white; a picked look sets its own | `colour.dark-ground`, rejected |
| A neutral ground, the hue left to the accents | Ground chroma a median 0.02, 0.07 at the third quartile | Play screens' ground chroma a median 0.055, 0.19 at the third quartile | Paper and ink's grounds are grey | `colour.neutral-ground`, rejected for every look |
| One accent hue | 113 palettes hold one strong hue, 49 none, 38 two or more | Not measured: the examples' colours are in their images | Four accent roles, each a kind of thing | `colour.one-hue`, rejected |
| Small labels frame the content from the corners | 72 place labels in corners, 4 in all four | Of 103 play screens, 50 hold a text in no corner, 31 in one, 19 in two and 3 in three or four | The play HUD holds three: the tag, the count and the keys | `layout.corner-frame`, rejected |
| Entrances ease out, mostly `expo.out` | `expo.out` 91, `power3.out` 50, `power2.out` 41, `back.out` 23 | 1181 of 2196 tweens in 138 examples use `easeinoutsine`; `easeoutsine` 309, `easeoutback` 84, an expo ease 3 | `TWEEN_STYLE` by class (`motion.tween-style`, open) | `motion.ease-out-entrance`, rejected |
| Headlines reveal by line, word or letter | 78, of which 31 by letter, 15 scramble, 7 typewriter | One example uses the Text typewriter action | None | `motion.text-reveal`, rejected |
| The pointer tilts or drifts the scene | 57 | — | — | `motion.pointer-drift`, rejected |

Film grain (19) and hairline rules (25) are the art's choice, which
`ART_STYLE` and the picker carry, so they are no rule here.

The prompts are written in one pattern: a reference to recreate the feeling
of without copying it, then fixed relations in numbers (colour roles in
hex, type sizes, insets, eases and durations), then the page's parts.
`pick_look.py`'s draw brief already splits a direction the same way: the
roles of `PALETTE` and the kinds of `TEXT_SIZE` are fixed, the colours and
the six dimensions of `ART_STYLE` vary, and the pick replaces nothing else.

## Options

1. **Propose the rules the examples agree with, reject the rest.** The
   centred menu, the small inset and the fade between layouts hold on both
   the websites and the examples. Each changes a helper or a constant, so
   each waits for the owner.
2. **Adopt the three now.** It changes every generated menu and every HUD's
   margin without the owner's choice.
3. **Take the atlas's numbers as they are.** The type contrast, the 11 px
   labels, the eases and the stagger would contradict the examples.

## Decision

Option 1. The look manifest holds each rule above under its id, with the
evidence in its `says`:

- `screen.menu-axis`, `screen.edge-inset` and `screen.transition` are
  proposed. Adopting one changes `hud_header()` or a new menu helper,
  `MARGIN`, or `go_to_layout()`, and the test that holds it.
- `motion.stagger` stays proposed. The websites step 60 to 80 ms and the
  examples 0.1 to 0.25 s; the owner picks the step.
- The others are rejected, each for the measurement in the table. A
  rejected rule is no reason to change a look the user gives: a dark
  ground or a monospaced counter is right when the user's look asks for it.

## Re-evaluate when

- The owner picks one of the proposed rules: set it to adopted and change
  the template and its test with it.
- The template gains a title screen: measure its axis against
  `screen.menu-axis`.
- The example clone updates: rerun `measure_layout.py --frame` and the
  three subcommands of `measure_examples.py`.
- The play HUD changes its corners: compare it with the examples' one or
  two corners again.
