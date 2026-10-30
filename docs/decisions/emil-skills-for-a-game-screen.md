# Emil Kowalski's Other Skills Checked Against a Game Screen

Date: 2026-10-31
Schema: Construct 3 r506.3

## Problem

[motion-by-class.md](motion-by-class.md) took the animation standards of
[emilkowalski/skills](https://github.com/emilkowalski/skills) (MIT) and
[look-picker.md](look-picker.md) took its prototype skill. The other
skills of the repository were not read against the look pipeline: the
manifest (`assets/look-manifest.json`), the generator template
(`assets/build_project.py`), `check_look.py`, `review_look.py`,
`pick_look.py` and the sub-agents in `plugin/agents/`. Most of them are
written for a web page, a React app or iOS, so each idea needs a
mechanism that a Construct 3 game screen has before it can become a rule.

## Evidence

### The repository

Read at commit `a81dbca` (2026-10-28), the commit that
[motion-by-class.md](motion-by-class.md) read. Nothing changed since, so
its decisions stand. `remove-animations` was added in that commit and is
read below.

### What each skill says and what this repository does

| Skill, heading | What it says | What this repository does | Change |
|----------------|--------------|---------------------------|--------|
| `break-ui` | Feed a component plausible worst data through the same boundary as the demo data, behind a Demo / Worst / Empty / One toggle; nonsense data proves nothing; check at the narrowest and widest widths | `review_look.py --data` shows each layout at demo, worst, empty and one, and on three more screen shapes; the worst text is the longest that `tools/texts.json` declares, and a guessed one only warns (`look.worst-data`, `look.screen-shapes`) | None: the same mechanism |
| `break-ui`, catalog, numbers | A value that changes live jitters without tabular figures | `count_up()` counts a score for 0.5 s. Inter's digits are 0.42 to 0.66 em wide (`LATIN_EMS`), so a centred or right-aligned count moves its other digits on every tick. Construct's Text has no tabular figures | `type.counting-digits`, adopted |
| `break-ui`, catalog, collections, plurals, time, media, RTL, zoom | 1,000 rows, "1 members", relative dates, broken avatars, right-to-left text, browser zoom | A game draws its text on a canvas at the viewport's scale. Its HUD shows counts beside an icon or a label, not a noun after a number | None: not for a game screen |
| `emil-design-eng`, press | Scale 0.95 to 0.98 on `:active`, 100 to 160 ms | `press()` squashes to 0.9 at once, back in 0.1 s `easeoutsine`; the examples pop a button to 0.85 to 1.25 ([count-up-and-press.md](count-up-and-press.md)) | None: the examples decide |
| `emil-design-eng`, origin-aware popovers | A popover grows from its trigger; a modal stays centred | `popup()` opens a centred modal panel | None: the modal exemption |
| `emil-design-eng`, interruptibility | Transitions retarget, keyframes restart from zero | A Tween action always starts from the current value. A second value tween under one tag is the trap, which `motion.value-restart` checks | None |
| `emil-design-eng` checklist, asymmetric timing | An exit faster than its enter | The examples close a popup no faster than they open it: open 0.25, 0.5, 1 s and close 0.5, 0.5, 1 s (quartiles, `measure_examples.py popups`); `popup()` closes as it opened | None |
| `emil-design-eng`, blur over a crossfade; clip-path reveals; CSS performance | A 2 px blur hides a double exposure; `clip-path` hold-to-delete; animate `transform` and `opacity` | No helper crossfades two states. `menu.hold-to-confirm` holds the fill idea | None: no crossfade to mask |
| `emil-design-eng`, gestures; `apple-design` 2, 5, 6, 9; `animate-expo` recipes | Grab offset, velocity hand-off, momentum projection `v/1000 * d / (1 - d)` with `d = 0.998`, rubber-band `o*dim*c / (dim + c*abs(o))` with `c = 0.55`, dismiss on 0.11 px/ms | The template has no drag or swipe helper; a game drags with the Drag & Drop behavior | None until a helper drags; the values are here for it |
| `apple-design` 1, 10; `animate-expo` 7; `mobile-native` 5 | Feedback on press-down, commit on release, cancel by dragging off; 10 to 16 px of slack before a slide cancels | `press()` squashes on the touch's start and acts on its end under *Is touching*, as the examples do; a slide off the button cancels with no slack | None: the examples cancel the same way |
| `apple-design` 4; `animate-expo` 5 | Critically damped springs, bounce only after a flick | Construct's Tween has no spring. Overshoot eases are for the world and the subject of a moment (`motion.hud-overshoot`) | None |
| `apple-design` 7 | Enter and leave by the same path | `popup()` closes the way it came | None |
| `apple-design` 12 | Translucent blurred material, a dim to focus a modal | `popup()` dims to 50 %; paper and ink rejects soft shadows (`shadow.soft`); `avoid.dashboard` asks about panels | None |
| `apple-design` 13; `animate-expo` 8 | Sound, haptics and motion on the same frame; one per action | A sound played in the same event starts on that tick. The template has no sound helper. The examples' Audio object, in every one of the 23 that set it, has *Latency hint* Interactive | None |
| `apple-design` 14 | Avoid slow loops near 0.2 Hz and moving full-screen backgrounds | The examples' vertical Sine takes 1, 3, 4 s and their horizontal Sine 2, 4, 4.1 s (quartiles, `measure_examples.py sine`) | None: games loop at that rate |
| `apple-design` 14; `emil-design-eng` accessibility | Reduced motion keeps fades and drops movement | No condition or expression of the schemas reads `prefers-reduced-motion`; only a script can. `motion.reduced` stays proposed | None |
| `apple-design` 15 | Tracking and leading by size | Construct's Text has no letter spacing; `tracked()` spaces the tags | None |
| `apple-design` 16, wayfinding and confirmations | Every screen says how to get out; confirm only what cannot be undone | A screen's flow belongs to the design review; `menu.hold-to-confirm` holds the confirm | None for the look |
| `apple-design` 17; `emil-design-eng`, debugging | Play motion slowed and frame by frame | `preview_project.py` slows a recording with `runtime.timeScale`, as [motion-by-class.md](motion-by-class.md) recorded the popup at 0.2 | None |
| `find-animation-opportunities` | A four-question gate (frequency, purpose, speed, function), at most five to seven proposals, rejected candidates listed | `motion.frequency` holds the frequency question for the HUD; `references/motion-vocabulary.md` names each motion | None |
| `remove-animations`, the gate and the reductions | Delete motion on keyboard and frequent actions; stagger at most 30 ms per item or 300 ms in all; loops on a persistent element run once | The world keeps its juice on every jump and hit ([motion-by-class.md](motion-by-class.md)). The examples stagger a median 0.125 s, their menus 0.1 to 0.25 s ([motion-atlas-layouts.md](motion-atlas-layouts.md)) | None: `motion.stagger` holds the measured step and stays proposed |
| `remove-animations`, hazards | A start state at opacity 0 that only the removed animation ended | Over the 422 examples without scripts, 603 object types start hidden and no action shows them, 38 of them on a HUD layer: managers, spawners and zones hidden on purpose. A check cannot tell those from a forgotten panel | None: no check |
| `improve-animations` | Audit, vet, then self-contained plans with exact values and a feel check | `edit_sheet.py` takes a plan with the event's line; `verify_change.py` runs the checks and the look review in order | None: the workflow exists |
| `animation-performance` | Composite-only properties, the main thread, CSS variables, blur under 20 px | A game draws to one canvas; none of these properties exist | None: not for a game screen |
| `mobile-native` | Tap highlight, `100dvh`, 16 px inputs, overscroll, safe areas, sticky hover | The export sets the page; `screen.safe-area` keeps the viewport inside the safe area. A hover frame shows only with `POINTER` on | None |
| `animate-expo` | Reanimated, worklets, haptics, sheets and toasts in React Native | The toast's enter 300 ms and exit 250 ms fit the banner class | None: not for a game screen |
| `ask-sonner` | Sonner's API: 4 s default, three toasts at once, update by id | No helper shows a stack of messages | None: not for a game screen |
| `pick-ui-library` | React libraries by task | A game uses Construct's plugins and behaviors | None: not for a game screen |
| `write-swift` | Swift 6 language and concurrency | No mapping | None: not for a game screen |

### Counting numbers in the examples

A Text set from a tween's value or from its own number plus a step: two
Texts of one project, both centred, both padded to three digits with
`zeropad`, which keeps the count of digits but not their widths.

Scripts and rows: `.local/docs/evidence/emil-skills-for-a-game-screen/`.

## Options

1. **Adopt the web rules.** Faster exits, slack on a press, no slow loops:
   each contradicts what the examples do, measured above.
2. **Nothing.** Leaves the count's moving digits, which no rule holds.
3. **A proposal for the count.** `type.counting-digits`, from the
   font's measured widths. Chosen.

## Decision

Option 3. `type.counting-digits` is adopted, as the owner chose on
2026-10-31: a number that `count_up()` counts is left-aligned, so the
digits before the one that changes stay, or set in a font whose digits
share one width. `counting()` records the Text it counts, and the
generator's `check_texts()` warns of one that is not left-aligned. It
warns and does not stop, because a right-aligned score in a corner still
reads; it moves for the 0.5 s of a count.

## Re-evaluate when

- A recording of a counted score shows its digits move by more than the
  owner accepts, or a font with equal digit widths replaces Inter: make the
  warning a stop, or drop it.
- The template gets a drag, a swipe or a list that scrolls: take the
  projection, the rubber-band and the velocity threshold above.
- The template gets a sound helper: fire it in the event of its cause.
- emilkowalski/skills moves past `a81dbca`.
