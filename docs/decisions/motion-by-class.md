# Motion by Class: Eases by What Moves, a Popup Helper and Five Motion Checks

Date: 2026-10-30
Schema: Construct 3 r506.3

## Problem

Every tween helper of the generator template, `tween1()`, `tween2()`,
`tween_width()` and `tween_value()`, defaulted to `easeinoutsine`, and only
`tween_width()` had a default time. A game's HUD, its bars, its camera and
its world objects therefore moved alike unless the agent chose each ease,
and nothing opened a popup. The owner asked to learn from Emil Kowalski's
animation skills ([emilkowalski/skills](https://github.com/emilkowalski/skills),
commit `a81dbca`, MIT), whose web values disagree with the official
examples in places. `check_look.py` checked no motion but the hit and the
squash, while two traps of the Tween behavior
(`Construct3-Cookbook/guides/behaviors/tween.md`) break a game silently: a
count restarted without *Stop*, and a size tween that cancels the tween
destroying the same instance.

## Evidence

### The official examples

Every Tween action of the 544 projects of the Construct-Example-Projects
clone, read on 2026-10-30. An object type is on the HUD when every
instance the layouts place lies on a layer at parallax 0.

| Class | One-shot tweens | Sine ease | Seconds, quartiles |
|-------|-----------------|-----------|--------------------|
| HUD | 650 | 92 % | 0.25, 0.5, 1 |
| World | 2128 | 77 % | 0.25, 0.5, 0.5 |

The HUD's fades, 419 of its tweens, take 0.5 s at the median. A popup's
objects fade with `easeinoutsine` in 0.25 to 1 s in the middle half, and
none scales a popup ([borrowed-numbers.md](borrowed-numbers.md), "Popups and idle motion"). The
camera moves for 1 s or more with `easeinoutsine`
(`Construct3-Cookbook/guides/project-files/new-project.md`, the section on
motion by class).

### Emil Kowalski's skills

`review-animations/STANDARDS.md` and `animate/SKILL.md` of the clone ask
for an element that enters or leaves to ease out, under 0.3 s, with
`cubic-bezier(0.23, 1, 0.32, 1)`, the standard easeOutQuint, which
Construct has as `easeoutquint`. They forbid an ease-in on an interface
and an entrance from `scale(0)`, starting it from 0.9 to 0.97 at opacity 0.
They decide by frequency: no motion for what happens a hundred times a day,
delight only for rare moments. They stagger a group 30 to 80 ms apart,
hold a destructive confirm for 2 s, and keep fewer and gentler motions
under reduced motion. Published games, read in
[published-game-visual-language.md](https://github.com/XHXIAIEIN/Construct3-RAG/blob/main/docs/decisions/published-game-visual-language.md),
squash, shake and flash on every jump and hit, which the frequency rule
would cut.

### The checks over the examples

Each check ran over the same 544 projects, and over the template's
stand-in game and a popup demo built from it, before it was kept. A
check that fires on a sound sheet is a warning.

| Check | Fires on the examples | Kept as |
|-------|-----------------------|---------|
| An overshoot ease on a HUD object | 6 tweens in 4 projects: a winner's text, an outcome text, a transition title and a pressed button, each the subject of its moment | a warning |
| Any ease-in on a HUD object | 62 tweens in 38 projects, nearly all a tutorial text sliding off or a fader closing the screen | dropped |
| An ease-in fade in on a HUD object that does not cover the viewport | 5 tweens in 3 projects, two of them one game in JavaScript and TypeScript | a warning |
| A size or scale tween from a size of 0 on a HUD object | none; a gauge whose width alone grows from 0 passes | a finding |
| Any value tween without *Stop* first | 248 tweens in 90 projects, mostly flashes and shakes that never restart mid-way | dropped |
| A value tween from the number a Text shows, or from a tween's value, without *Stop* first | none | a finding |
| Any size tween beside one that destroys the instance | 16 in 14 projects, each a sequence through *On finished*, a Timer or a creation, or in the same actions | dropped |
| A squash back to the image's size in another event, not after a creation, *On created* or *On finished* | none | a warning, since a condition that keeps the squash off a dying instance is not readable |

The stand-in game's three tweens and the demo's twelve raise none.

### The popup in a preview

A demo game opened a panel 512 x 256 px with a label over a dim, closed it
1.2 s later and opened it again, recorded at a time scale of 0.2 and 60
frames a second of game time. The panel grew from 487 to 512 px and from
opacity 0 to 1 in 0.2 s while the dim reached 0.5; the label followed the
panel's opacity as its child. The panel and the dim were hidden when the
close ended, and shown again at the next open. Recordings and the
measurements: `.local/docs/evidence/motion-by-class/`.

## Options

1. **One default ease.** Keep `easeinoutsine` and leave the class to each
   game. Every game's HUD and world keep moving alike.
2. **Emil's values everywhere.** A strong ease-out under 0.3 s for every
   tween. It contradicts how the examples move the HUD, the bars and the
   camera, and the frequency rule would cut the world's juice.
3. **A table by class.** `TWEEN_STYLE` keeps the measured `easeinoutsine`
   and durations for the HUD, a bar, the camera and the world, and gives a
   popup and a banner `easeoutquint` in 0.2 and 0.25 s, the one class where
   the two sources agree that the motion is a moment.

## Decision

Option 3, with the popup class and `popup()` left open for the owner, who
judges both on a recording:

- `motion.tween-style`, open: the measured `easeinoutsine` in 0.5 s for a
  popup and a banner, or the strong ease-out the template holds.
- `motion.popup`, open: a panel from 0.95 of its size and opacity 0, which
  the template holds, or a fade at its size as the examples do.
- `motion.frequency`, proposed: on the HUD only, instant for what each
  action changes and the popup class for a moment of the session; the
  world keeps its juice. `count_up()` would change under it.
- `motion.reduced`, `motion.stagger` and `menu.hold-to-confirm`, proposed:
  a scale that tones down the shake, the camera and the squash and keeps
  the hit flash, a stagger step of 0.03 to 0.08 s, and a held press for a
  destructive menu action, each until the examples are read for it.

The five checks are in `check_look.py` under the ids of the table above.
`references/motion-vocabulary.md` names each motion with its mechanism,
helper and value, in the glossary shape of Emil's animation-vocabulary
skill; its values come from the Cookbook's feel, attack-feel and vfx-timing
recipes.

## Re-evaluate when

- The owner judges the popup and banner class and the popup's scale on a
  recording: write the pick into `TWEEN_STYLE` and `POPUP`, and set the two
  rules to adopted.
- A read of the examples finds a reduced-motion setting, a stagger or a
  held confirm.
- A Construct release changes when a property tween releases another, which
  `motion.size-on-dying` relies on.
