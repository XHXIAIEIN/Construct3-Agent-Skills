# The Game's Look: What impeccable Adds to the Review and the Manifest

Date: 2026-10-31

## Problem

[impeccable](https://github.com/pbakaus/impeccable) (Apache-2.0, skill
version 4.8.0, commit `df3a4ab`) is a web design skill for coding agents. It
has 24 commands, one of them a deprecated alias, a rule engine of 62
detectors and a finishing reviewer.
`game-look-from-design-skills.md` read it once among fifteen design skills.
This record reads every file of its skill and its detector registry, and
compares each with the look pipeline of this repository at the level of
the code: `assets/look-manifest.json`, `assets/build_project.py`,
`scripts/check_look.py`, `scripts/review_look.py`, `scripts/pick_look.py`,
`scripts/art.py` and the sub-agents `look-judge`, `art-drawer` and
`design-judge`.

Task: take each mechanism that a fixed-size game screen can use. A rule
that survives becomes a rule of the manifest with a measurement on the
official examples behind it. A rule that the manifest turned down by
measurement stays rejected unless new evidence says otherwise.

## Evidence

### How impeccable works

- **Setup.** A launcher binary loads the project's `PRODUCT.md` and
  `DESIGN.md`. Before any UI edit, the agent reads `craft-floor.md`: checks
  on the rendered result and a list of refused defaults.
- **Modes.** The surface sets how much the visual world may take. On a
  working screen (Operate), the world lends type, palette, density and one
  signature move, and never the layout or the controls. On a landing page
  (Persuade), the world may carry the page.
- **World choice.** `new-work.md` lists the category's default page and its
  opposite as a rut, and neither may be a candidate. It lists seven
  candidate worlds over at least three material families. A world is dealt
  by dice from a catalogue that impeccable's `CLAUDE.md` keeps in a private
  repository. Font and palette ban lists and four
  named generated looks catch the model's prior, and the model's first
  palette counts as spent.
- **Judging a render.** `critique.md` runs a design review and the
  detector as two isolated sub-agents and joins them afterwards. It scores
  Nielsen's ten heuristics from 0 to 4, ranks issues P0 to P3 and walks
  personas. A run without sub-agents must print a degraded banner.
- **Finishing.** A fresh reviewer (`degraded/finish-reviewer.md`, the
  `impeccable-finish-reviewer` agent) first checks that every capture is
  valid. Then it lists the comp's elements in its own words before it
  reads the builder's contract. It classifies each element against the
  approved comp, with fixed rows for type, material and ground colour. Its
  verdict is one of four words, derived from the matrix: recapture,
  rebuild, fix or ship. A second pass scores each earlier fix as resolved,
  partial or unresolved, and finds no new faults.
- **Detector.** 62 rules over HTML, CSS and the rendered DOM, 31 marked as
  generated-UI tells and 31 as quality faults. A hook runs the cheap rules
  after each edit and the rest when the session stops.

### Each reference against this repository

"Not for a game screen" names web mechanics that a Construct layout lacks:
a scrolling document, CSS breakpoints, forms, the DOM.

| impeccable file | What it does | What this repository does | Change |
|-----------------|--------------|---------------------------|--------|
| `SKILL.md` | Routes the commands; loads the product and design files; makes the craft floor the last read before an edit | The manifest holds every look rule with its status and scope, and the generator's checks stop its run (`look-manifest-owns-the-rules.md`) | None. The manifest's checks run where the agent writes, while the craft floor is prose read before an edit |
| `mode-persuade.md`, `mode-operate.md`, `mode-read.md`, `operate.md` | The surface's mode limits what the world may take; on a working screen the world lends four things and never the controls; a render with its name covered must still read as its category | Play, title and result screens are measured apart (`title-and-result-screens.md`). Question 7 of `review_look.py` asks the play screen's category test: a game, not an app's dashboard (`avoid.dashboard`). Question 5 keeps the backdrop behind what the player acts on | None. The split by screen kind already holds, with measurements. Read mode is not for a game screen |
| `new-work.md` | Rut list, seven candidates, dice-dealt world, challengers on two axes, colour strategy by coverage, ban lists of fonts and generated looks, direction contract, comp to plates to a measured hero gate | No free choice of world: paper and ink when the user gave no look (`paper-and-ink-is-the-fallback.md`), else `pick_look.py` draws three directions, two of them from the user's references with their measured colours, and the user picks (`look-picker.md`) | None. The ban lists counter a prior that picks the world; here the user picks among directions tied to the references. The catalogue is not public. The colour strategies are not measured on the examples |
| `craft.md` | Deprecated alias of `new-work.md` | | None |
| `shape.md`, `init.md` | An interview of two or three questions a round; product facts with no aesthetic question; nothing recorded that the user did not answer | `USER_LOOK` names where a given look comes from; a rule the user has not decided stays `open` with its options | None. The same principle holds |
| `document.md`, `extract.md` | Write `DESIGN.md` from the built code; pull repeated values into tokens | `PALETTE` roles and `TEXT_SIZE` kinds. `write_png()` stops a colour outside `PALETTE` and `on_scale()` a size outside `TEXT_SIZE` (`colour.palette-only`, `type.scale`) | None. Drift stops at write time |
| `critique.md` | Two isolated assessments; heuristic scores 0 to 4; cognitive load with at most four options per decision; personas; P0 to P3; degraded banner | `review_look.py` prints the measured findings and writes a brief with fixed yes/no questions and nothing of the game's intent for `look-judge`. Each question has a tier (`look-severity.md`). `--reply` names every missing answer | Scores and personas stay out: a loose question made judges report more, not more correctly (`look-judge-calibration.md`). Four options per decision is not for a game screen, where a level select shows the game's levels. The degraded banner matches proposal 2, who answered |
| `audit.md` | Five dimensions scored 0 to 4: accessibility, performance, theming, responsive design, implementation integrity | `check_project.py`, `check_look.py` and the findings of `review_look.py` | None. Scores as above; theming and responsive design are not for a game screen |
| `audit.native.md`, `adapt.native.md`, `ios.md`, `android.md` | Native apps: safe areas, 44 pt and 48 dp targets, system controls, text scaling | `touch.target` (48 dp, 44 pt), `screen.safe-area`, `look.screen-shapes` | None. A game draws its own controls |
| `polish.md` | Refines the world it has; fixes broken before cosmetic; closes a critique when the file's bytes change | Broken before ugly (`look.severity`); a yes from before the change only warns (`look-blocks-only-what-the-change-brought.md`); a saved judgement holds while its input version matches | None |
| `bolder.md`, `quieter.md`, `distill.md` | Change intensity inside the system; quieter sets 70 to 85% saturation, distill one or two colours and three or four sizes | A colour is a role of `PALETTE`, a size a kind of `TEXT_SIZE`. The examples' labels use one to three colours and about two sizes (`colour.palette-only`) | None. The numbers are web taste, and the examples' counts already hold |
| `colorize.md` | Colour by role; OKLCH ramps; WCAG table | `text.contrast`, `colour.structure`, `colour.accent-contrast` | None |
| `typeset.md` | Type roles, a 45 to 75 character measure, more weight for light text on dark | `type.scale`, `type.min-size`; `type.modular-scale` and `type.one-display` rejected by measurement | None. A game screen holds few lines of prose. A Text holds only a bold flag, so the weight step cannot be measured on the examples |
| `layout.md` | Squint test, grouping by proximity, rhythm, a 4-unit scale | `layout.proximity` (1.5), `grid.unit` measured, the `crowd` finding | None |
| `animate.md` | One authored moment; durations by job, 100 ms to 800 ms; exits faster than entrances; no bounce by reflex; reduced motion | `TWEEN_STYLE` by class, measured (`motion-by-class.md`); `motion.hud-overshoot` warns; `motion.reduced` and `motion.frequency` proposed | `motion.exit-faster` rejected: the examples fade the HUD out as long as in (table below) |
| `delight.md` | Delight at moments that earn it, in proportion to how often they happen | `motion.frequency` proposed | None |
| `overdrive.md` | Two or three directions; the user picks before code | `look.picker` | None |
| `clarify.md` | Labels name their action; errors name the problem and the way out | No look rule covers game text | None. No generated game has shown the fault. A text fault of events belongs in the Cookbook's pitfalls |
| `harden.md` | Extreme input, translation growth, right-to-left text, error states | `look.worst-data`: the declared longest text, else 9999999, a long hyphenated name and a long Chinese one; empty; one | None |
| `onboard.md`, `optimize.md` | First-run flows and empty states; Core Web Vitals | | Not for a game screen's look. A tutorial is event design |
| `adapt.md` | Breakpoints, 44 px targets, thumb zone | `look.screen-shapes`, `touch.target`, `screen.fill` | None. Breakpoints are not for a game screen |
| `visualize.md` | Three comps; the second and third from words, not from the first image; one dominant move | The art agent draws three directions from `directions.json`. The judge's question `DIFFERS` refuses directions that differ only in colour | None. One dominant move is `layout.focal`, rejected by measurement |
| `generate.md`, `live.md`, `live-setup.md` | Variants of a page element in a browser overlay, with tuning knobs | | Not for a game screen. The picker's three directions are the variant step |
| `component-review.md`, `region-map.md` | Cut the approved comp into painted plates and code-drawn regions; the user reviews the plates | Each object type has its box and subject in `art/wanted.json`; `art.py` writes a contact sheet; the art agent answers its questions | None |
| `routing.md`, `doctor.md`, `hooks.md` | A menu from the project's signals; repair of stale files; the detector after each edit and at the end | The last line of each script names the next step; the generator checks on every run; `install.py` reports a copy that differs | None |
| `craft-floor.md`, Verify | Contrast, depth, spacing, type, motion, states, the parts the page did not draw (selection, caret, scrollbars), copy, coverage | Each has a check here, except the parts the game did not draw: a generated game keeps Construct's icons | `art.icon` proposed (table below) |
| `craft-floor.md`, Refuse | Cards as structure, gradient text, glass, side stripes, hard offset shadows, a system display face, emoji or glyphs as icons, geometric masks, light or dark by category | `avoid.dashboard`; `screen.title-name` proposed draws the name as an image; paper and ink casts no shadow by default (`shadow.form`) | `text.no-emoji` proposed (table below) |
| `degraded/finish-reviewer.md` | Capture validity first; inventory before the contract; type, material and ground against the approved comp; four derived verdicts; a pass that scores earlier fixes | A layout that draws nothing gets no question; the judge never sees intent; the tier of each question decides the verdict; three rounds, each yes marked new or before. The pair picture shows the user's references, not the picked screen | Proposal 1, the picked screen as the pair |
| `degraded/asset-producer.md`, `degraded/documenter.md`, `degraded/manual-edit-applier.md` | Plates cut from the comp without redesign; `DESIGN.md` after the build; edits from the overlay | Every drawing follows `art/look.png` | None |
| Detector, `antipatterns.json` | 62 rules over CSS and the DOM (below) | The findings of `review_look.py` (`text`, `overlap`, `edge`, `faint`, `crowd`, `frame`) and `check_look.py` | Mapped below |

The detector's rules by what a game screen has:

- **Held already.** Low contrast, tiny text, text overflow and occlusion
  are the findings `faint`, `text` and `overlap` and the rules
  `text.contrast` and `type.min-size`. Monotonous spacing is
  `layout.proximity`; drift from the design system is
  `colour.palette-only` and `type.scale`. Bounce easing is
  `motion.hud-overshoot`; nested cards, icon tiles and a thin border with a
  wide shadow are `avoid.dashboard`. A broken image and hidden content are
  the blank screenshot that gets no question.
- **Rejected by measurement here.** A flat type hierarchy, steps under
  1.25, matches `type.modular-scale`, which the examples turned down.
- **Inside a user decision.** `overused-font` names Inter, which paper and
  ink uses by the user's choice (`type.inter`). impeccable's own working
  screens permit a familiar sans, and a HUD is the game's working screen.
  `repeating-stripes-gradient` names decorative stripes; paper and ink's
  stripes mark areas with a rule of their own (`pattern.areas`), the use
  the detector exempts.
- **Not measurable without renders of the examples.** The generated
  palettes `ai-color-palette`, `cream-palette`, `dark-glow` and
  `radial-halo`. A game screen reaches them only through a direction of the
  picker, which takes its colours from the references.
- **Not for a game screen.** The rest: headings, measure, justification,
  eyebrows, section numbers, marketing phrases, scroll containers and DOM
  structure.

### Measurements on the official examples

`dev/scripts/measure_examples.py` reads the 544 projects of the
`Construct-Example-Projects` clone; the rows are in
`.local/docs/evidence/look-from-impeccable/`.

`glyphs` reads every string of every layout and event sheet:

| What | Strings | Examples |
|------|---------|----------|
| An emoji (U+1F000 to U+1FAFF) | 0 | 0 |
| A symbol from the arrow, technical, shape, miscellaneous or dingbat blocks | 13 | 5 |

The symbols are arrows that name keys or point at a field in instructions,
and a credits screen whose Sprite Font draws its own heart and face. No
example shows a symbol as an icon in a Text.

`icons` compares each project's `icons/icon-*.png` with the empty project's:

| Examples | Projects | Construct's icons kept | Splash loader |
|----------|----------|------------------------|---------------|
| All | 544 | 268 | 434 |
| 2D games | 113 | 54 | 106 |
| The studio's (Viridino or Forsteri) | 29 | 0 | 29 |
| The studio's 2D games | 13 | 0 | 13 |

Every finished game of the studio draws its own icons and keeps the
splash loader. The skill writes no icon, so a generated game ships
Construct's.

`fades` reads every opacity tween to 100 or to 0 on a HUD object that
does not ping-pong: 325 tweens in 46 examples.

| Fade | Tweens | Seconds: p25, median, p75 |
|------|--------|---------------------------|
| In | 169 | 0.5, 0.5, 1 |
| Out | 156 | 0.5, 0.5, 1 |

Of the 92 HUD objects that fade both ways, the median fade out is shorter
than the median fade in on 17, equal on 62 and longer on 13.

## Options

1. **Take impeccable's scoring critique.** Heuristic scores, personas and
   P0 to P3 are the free critic that the calibration turned down.
2. **Take its ban lists into the picker.** They fight a prior that chooses
   the world. The picker's directions come from the user's references, and
   the lists' hues and fonts are not measured on a game screen.
3. **Take the mechanisms that a game screen shares and the examples
   support, as proposed rules, and record the review changes as
   proposals.** Chosen.

## Decision

Option 3. The manifest gains three rules:

- `text.no-emoji`, enforced since the owner chose it on 2026-10-31: no
  Text shows an emoji. An emoji draws from the device's emoji font, so its
  picture differs between systems and from `ART_STYLE`, and a Sprite Font
  draws nothing for it (`type.pixel-font`). An icon is art in its own box.
  No string of the 544 examples holds one. The generator's
  `check_texts()` stops the run on an emoji in a layout's Text or in a text
  the events set, naming each: one regular expression of Unicode's
  Emoji_Presentation characters and U+FE0F, so an arrow that names a key
  passes. A text that someone edits by hand after the run is not checked.
- `art.icon`, proposed: the game's icons are drawn from its look by the art
  route, as every studio game draws them. The splash loader stays, as every
  studio game keeps it. `web-landing-and-redesign-skills.md` leaves a
  website's favicon out of the look review; the icon of a game is the
  picture of it on a home screen or a store page, which the studio's games
  draw.
- `motion.exit-faster`, rejected: the rule that a HUD object leaves faster
  than it enters. The examples fade 62 of 92 HUD objects out in the same
  median time as in.

Two changes to the review are proposed and not made, because the brief of
`look-judge` changes with them and each change needs the calibration of
`look-judge-calibration.md`:

1. **The picked screen as the pair.** After a pick, `art/look.png` is the
   approved comp of impeccable's finishing reviewer. The pair picture shows
   the user's references only, so nothing asks whether a finished screen
   kept the picked direction's rendering, linework and ground. Proposed:
   when `art/look.png` exists, the pair picture of each play screen shows
   it, and the reference question asks about it.
2. **Who answered.** impeccable marks a review that one context ran
   alone. Here the agent that built the game may answer its own brief, and
   the model that built the card game of `game-look-from-design-skills.md`
   judged its screenshots by what it meant to build. Proposed: the reply
   names its reviewer, and the `ok:` line of `verify_change.py` says when
   the builder answered its own brief.

The template, `pick_look.py` and the sub-agents' prompts stay as they are.

## Re-evaluate when

- The owner decides `art.icon`: the rule becomes adopted, with its art
  and its test.
- A game's text needs a symbol the regular expression misses, or shows an
  emoji after a hand edit: move the check into `check_look.py`, which
  reads the project's files.
- The owner takes proposal 1 or 2: the questions or the reply change, and
  both judges answer the regression set again.
- A generated game shows an emoji, a glyph icon or Construct's icons on a
  screenshot the user judges: the matching rule is due.
- A look picked from references is judged generic on the user's
  screenshots, such as a near-black ground with a neon glow: impeccable's
  list of generated looks becomes a question for the picker's judge.
- impeccable publishes the evaluations behind its rules, which its
  `CLAUDE.md` places in a private repository: read them for a measured
  threshold.
- The example clone updates: rerun `measure_examples.py glyphs`, `icons`
  and `fades`.
