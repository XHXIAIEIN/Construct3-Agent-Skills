# Motion Vocabulary

A glossary that turns the name of a motion into what to build in a
generated game: the term, the Construct mechanism, the generator
template's helper, and the value to start from. Read it when the user or a
design names a motion, such as "a pop when the coin lands", or when an
event needs a motion and the helper is not obvious.

Each class of object keeps one kind of motion, so the player can tell what
matters. `TWEEN_STYLE` in `assets/build_project.py` holds the ease and the
seconds by class; a tween helper takes `style=` and a given time or ease
wins over it. The rules and their status are in
`assets/look-manifest.json`, under the ids that start with `motion.`. A
rule whose status is `open` or `proposed` is the user's to decide: keep the
template's value.

The glossary's shape, term then meaning, follows the animation-vocabulary
skill of [emilkowalski/skills](https://github.com/emilkowalski/skills)
(MIT License, Copyright (c) 2026 Emil Kowalski). Its web values are not
taken where the official examples measure otherwise
(`Construct3-Agent-Skills/docs/decisions/motion-by-class.md`).

## Eases

- **Ease in-out** - Starts and ends slowly. `easeinoutsine` is the
  template's ease for the HUD, a bar, the camera and the world, as the
  official examples tween them.
- **Ease-out** - Starts fast and settles. `easeoutquint` opens a popup or a
  banner (`motion.tween-style`, open). It is the curve that web interfaces
  write as `cubic-bezier(0.23, 1, 0.32, 1)`.
- **Ease-in** - Starts slowly. It suits an object that leaves, never a HUD
  object that fades in (`motion.hud-ease-in`, a warning).
- **Overshoot** - Passes the end value and comes back: `easeoutback` once,
  `easeoutelastic` several times, `easeoutbounce` as a dropped ball. It is
  for world objects and the subject of a moment, such as a title card,
  never the rest of the HUD (`motion.hud-overshoot`, a warning).

## Entrances and exits

- **Fade in, fade out** - Tween *Opacity*. `tween1(obj, tag,
  "offsetOpacity", "100", style="hud_in")`, and `"0"` with
  `style="hud_out"`. Value: 0.5 s, `easeinoutsine`.
- **Scale in** - The element grows from a little under its size while it
  fades in. `popup(panel, dim)` opens a panel from `POPUP["scale"]`, 0.95,
  at opacity 0, and fades its dim in to `POPUP["dim"]`, 50 %, in 0.2 s
  `easeoutquint`. `popup(panel, dim, show=False)` closes it the way it came,
  and `popup_closed(panel, dim)` hides both when the close ends
  (`motion.popup`, open). Never from 0 (`motion.panel-from-zero`, a
  finding).
- **Pop in** - Appears with an overshoot, as if it bounced into place. Set
  the size to a share of the image's size, then tween back with
  `easeoutback` over about 0.3 s, which bounces once like something hard;
  *Ping pong* makes a pop that returns. For a world object or the subject of
  a moment. [`Construct3-Cookbook/guides/recipes/feel.md`, "Squash, pop,
  bounce on impact"]
- **Banner open** - A strip opens from its centre: tween its width from 0.
  `tween1(banner, tag, "offsetWidth", width, style="banner")`, 0.25 s
  `easeoutquint`; the Cookbook's title card uses `easeoutquart` in 0.25 s.
  A width alone from 0 passes `motion.panel-from-zero`.
  [`Construct3-Cookbook/guides/recipes/feel.md`, "A chapter or stage title
  card"]
- **Fade between layouts** - A viewport-sized `Fader` on a parallax-0 layer
  tweens its opacity, then *Wait for previous actions* and *Go to layout*.
  [`Construct3-Cookbook/guides/recipes/feel.md`, "Fade between layouts"]

## Impact

- **Squash and stretch** - The size jumps to a share of the image's size,
  holds, and tweens back. `squash(art, kind)` with `SQUASH`: a hit 0.8 x
  1.2, back in 0.25 s `easeoutback`; a landing 1.2 x 0.8, back in 0.5 s
  `easeoutelastic`; a jump 0.7 x 1.3, held 0.2 s, back in 0.75 s
  `easeoutelastic` (`motion.squash`). On the art, never on an object that
  collides (`motion.squash-art`), and never on an object that a size tween
  is destroying (`motion.size-on-dying`, a warning).
  [`Construct3-Cookbook/guides/behaviors/tween.md`]
- **Hit flash** - The object's hit frame, drawn in the `flash` role, for an
  instant. `hit_frame(file)`, then `hit_flash(obj)` or `hit(obj)`. Value:
  `HIT_FLASH["seconds"]`, 0.08 s of real time (`motion.hit`).
- **Hit stop** - The game freezes for an instant on a big hit. System *Set
  time scale* 0.1, *Wait* with *Use time scale* off, *Set time scale* 1; a
  *Tween (value)* that feeds *Set time scale* ramps it. Slow motion is 0.1
  to 0.2. No helper yet (`juice.functions`, proposed).
  [`Construct3-Cookbook/guides/recipes/feel.md`, "Hit stop, slow motion"]
- **Screen shake, in tiers** - Scroll To *Shake* with *Reducing
  magnitude*, the length from the effect. Magnitude as a share of the
  viewport's shorter side: about 0.5 % for a critical hit, 1 % for a merge,
  2 % for a kill; published games step it at about 0.3 %, 1 %, 2.8 % and
  5 %, over about 0.4 s. No helper yet (`juice.functions`, proposed).
  [`Construct3-Cookbook/guides/recipes/feel.md`, "Screen shake on impact";
  the published games are the source of `juice.functions`]
- **Impact burst** - One effect in four parts: a rise of 6 to 8 frames, a
  peak of 2 to 3, a fall to half in 5 to 6 and a tail of 4 to 6, the peak
  on the damage. [`Construct3-Cookbook/guides/recipes/vfx-timing.md`, "The
  four parts of one effect"]
- **Damage number** - Appears at twice its size and shrinks to its rest
  size in 0.15 s, flies up under Bullet gravity 500, starts to fade at
  0.4 s and fades over 0.45 s. A critical one is 1.75 times larger.
  [`Construct3-Cookbook/guides/recipes/attack-feel.md`, "Hit effects and
  damage numbers"]

## State and feedback

- **Number ticker** - A number counts to its new value. `count_up(text,
  value)` stops the running count, then tweens a value from the number shown
  over `COUNT_UP`, 0.5 s `easeoutquad`; `counting(text, value)` shows it. A
  count restarted without *Stop* jumps (`motion.value-restart`, a finding).
- **Bar slide** - A fill slides to its new width. `tween_width(fill, tag,
  bar_width(value, maximum, length))`, 0.25 s `easeinoutsine`.
- **Press** - A button sinks under the finger and springs back.
  `press(button, actions)`: 0.9 of its size at once, back in 0.1 s
  `easeoutsine`.
- **Dim once used** - A hint fades back after the first input. `hints(box)`
  dims the keys to `HINT_OPACITY`, 35 %, in 0.5 s.

## Idle

- **Float, bob** - A pickup waiting to be collected rises and falls. Sine
  *Vertical*, a period of 1 to 2 s, a magnitude of 5 to 15 % of its height;
  Sine *Size* with the same numbers makes it pulse.
  [`Construct3-Cookbook/guides/recipes/feel.md`, "A pickup waiting to be
  collected"]

## Sequences

- **Stagger** - Items that enter together start one after another. Not in
  the template: a step of 0.03 to 0.08 s is proposed (`motion.stagger`).
- **Orchestration** - Several objects move as one choreographed moment,
  such as a level clear. Timeline *Play*, with branches that start together
  in sibling sub-events. [`Construct3-Cookbook/guides/recipes/feel.md`, "A
  choreographed sequence over several objects"]
- **Title card** - Dim, banner, a title that drops and lands, a shake, a
  hold, then everything leaves together.
  [`Construct3-Cookbook/guides/recipes/feel.md`, "A chapter or stage title
  card"]
- **Camera move** - The camera moves slowly and evenly.
  `tween_value(camera, tag, start, end, style="camera")`, 1 s
  `easeinoutsine`; a camera that leads a running player is a lerp every
  tick. [`Construct3-Cookbook/guides/recipes/feel.md`, "Camera that looks
  ahead of a running player"]

## How often it happens

A HUD change that comes with every action of the player, a score tick or an
ammo count, shows at once or in the bar class; a moment of the session, a
level clear or a new record, gets the popup or banner class. World motion
on every jump or hit stays. This is `motion.frequency`, proposed: the
template does not hold it yet, and `count_up()` still counts every gain.
