# ui-ux-pro-max's Data Describes a Game's Store Page, and Its Web Rules Fail on Game Screens

Date: 2026-10-31

## Problem

`game-look-from-design-skills.md` read fifteen design skills for what they
share and kept only that. One of them,
[ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
(MIT, read at its `main` of 2026-10-31), is the largest: seven skills and a
searchable data set of styles, palettes, font pairings and UX guidelines,
which picks a design system for a request. This record is the deep read:
whether its data holds anything about games and how good it is, how its
search picks a look against `scripts/pick_look.py`, and which of its UX
rules a game screen keeps.

## Evidence

### What the data holds about games

Seven of its 192 product rows are games: Gaming, Casual Puzzle, Trivia and
Quiz, Card and Board, Idle and Clicker, Word and Crossword, and Arcade and
Retro. Each has a row in `products.csv`, `colors.csv` and
`ui-reasoning.csv`. Two of its 74 font pairings name games (Russo One with
Chakra Petch, Press Start 2P with VT323), and `styles.csv` has a Pixel Art
style and a HUD / Sci-Fi FUI style. None of its 119 UX guidelines or 32 app
guidelines names a game.

Every game row describes the game's web page, not its screens. Each one's
landing pattern is a "Feature-Rich Showcase", with "Social Proof" for two.
The decision rule of the puzzle and quiz rows adds testimonials when trust
is needed. The idle row's effects are scroll animations, parallax and page
transitions. The palettes are shadcn tokens: primary, card, muted, border
and a focus ring. `#0F172A`, Tailwind's slate-900, is the ground or the text
of six of the seven. Its provenance file sources 51 records, none of them a
game row. A game palette here has the roles of a web page and no role for a
game's kinds, such as reward or danger. `PALETTE` in
`assets/build_project.py` gives every colour such a role, and
`avoid.dashboard` turns down the cards, pills and soft shadows that
the tokens build.

### How its search picks a look

`scripts/design_system.py`, traced from its code: running its scripts was
not allowed in this session. BM25 ranks the product rows against the request
and takes the first as the category. The category's reasoning row names
the style, the colour mood and the type mood. The style is the first of the
row's style priorities that names a style. The palette is the row of the
category, darkened when the style is dark, and the font pairing is the
first BM25 hit. Every game of one category therefore gets the same palette
and style, whatever its viewport, its scenes or the user's references, and
the output is text the agent applies with no picture.

`scripts/pick_look.py` has the art-drawer sub-agent draw the game's first
play screen in three directions at the viewport's size. Each pair of
directions differs in two or more dimensions of an art direction:
rendering, linework, colour temperature, light, proportions or framing. The
directions keep `PALETTE`'s roles and `TEXT_SIZE`'s kinds. The user picks
one on the rendered screens (`look-picker.md`). Its style rows are CSS
treatments (radius, blur, glow, shadows). A direction taken from one would
differ from the others mostly in effects, and the check of
`pick_look.py` refuses a direction that differs only in its colours.

### Its UX rules on the official examples

Most rules that a game screen can use are already in the look manifest, in a
form for games:

- touch size: `touch.target`;
- pressed feedback: `POINTER_STYLE`, 0.15 s;
- safe areas: `screen.safe-area`;
- the 8 dp rhythm: `grid.unit`;
- 3:1 icon and control contrast: `art.contrast` and `control.parts`;
- 4.5:1 text contrast: `text.contrast`;
- one icon style: `avoid.style-mix`;
- text cut by its box: `review_look.py`.

Four rules have no counterpart, and each was measured on the official 2D
game examples with `dev/evals/measure_layout.py`. A dp is the viewport's
shorter side over 360. The rows are in `.local/docs/evidence/uupm/`.

| Its rule | Measured on the examples | Result |
|----------|--------------------------|--------|
| 8 dp or more between touch targets | `--taps`: of 295 tapped objects on a screen, 215 lie under 8 dp from the next, 175 touching or overlapping it; 9 of 16 examples set buttons, tabs, pickers or icons that close | rejected, `touch.spacing` |
| Body line height 1.5 to 1.75 | `--lines`: 130 of 137 texts of several lines add no line height to the font's own, about 1.15 em; none adds 0.3 em | rejected, `type.line-height` |
| 65 to 75 characters a line | `--lines`: a median 43, 32 to 50 for the middle half; 47 of 137 in 45 to 75 | rejected, `type.measure` |
| Body text 16 px or more on a phone | `--text`: the smallest text of 45 of 105 examples is under 4.4% of the shorter side | rejected, `type.body-16` |

The same `--taps` run found 101 of 300 tapped objects under 48 dp on their
smaller side, the median at 53 dp. `touch.target` stays as the user adopted
it. The template keeps a 48 dp box around a smaller drawing, so the rule
costs a game no look.

### Every part, against this repository

| Part | What it holds | This repository today | Change |
|------|---------------|-----------------------|--------|
| `ui-ux-pro-max` skill and `search.py` | Query contract, priority table of ten rule categories, `--design-system` with three 1–10 dials, Master + page overrides persisted to `design-system/` | `pick_look.py`, three drawn directions; the look persists as `USER_LOOK`, `PALETTE` and `ART_STYLE` in `tools/build_project.py` | None: a look picked from keywords with no picture is what `look-picker.md` replaced |
| `products.csv` | 192 product types, 7 games, each with a landing pattern and styles | No product table; the genre comes from the request | None: the game rows choose a store page |
| `ui-reasoning.csv` | Per category: pattern, style priority, colour and type mood, effects, JSON decision rules, anti-patterns | `look-manifest.json`: every rule with status, scope and source | None: the game rows' rules are web conversion rules |
| `colors.csv` | 192 palettes in shadcn tokens | `PALETTE` by role, `rgb()` and `write_png()` stop on a colour without one | None: tokens of a page, not roles of a game; `avoid.dashboard` |
| `styles.csv` | 88 styles with CSS keywords, accessibility risk and an implementation checklist; Pixel Art and HUD for games | `ART_STYLE` fixes six dimensions of an art direction; `pixel-art.sampling`, `type.pixel-font` | None: the Pixel Art row's sharp edges and limited palette are already enforced; the rest are CSS effects |
| `typography.csv`, `google-fonts.csv` | 74 pairings from Google Fonts by mood; 1 934 families with licences | `FONT`: Inter in three weights from the user's font cache; Fusion Pixel Font for pixel art, with Chinese | None: a pairing is a heading and a body face for a page; a game's type is sizes by kind (`type.sizes`, `type.min-size`) |
| `ux-guidelines.csv`, `quick-reference.md` | 119 guidelines, 62 for all platforms, 47 for the web | `review_look.py` findings and questions, the manifest | Four rejected rules above; the rest exist or are web: forms, ARIA, SEO, bundles, deep links, breadcrumbs |
| `app-interface.csv`, `pro-rules.md` | 32 rules for iOS, Android and React Native; a pre-delivery checklist | `touch.target`, `screen.safe-area`, `POINTER_STYLE`, `control.parts`, `art.contrast` | None: covered, or for native controls a Construct game does not have |
| `motion.csv` | 17 GSAP presets in three tiers: hover, scroll reveal, stagger, page transition, parallax, skeleton loader | Motion by class (`motion-by-class.md`), five motion checks | Not for a game screen: hover, scroll and page motion of a web page |
| `charts.csv`, `landing.csv`, `icons.csv`, `react-performance.csv`, `stacks/` | Chart types, 34 landing patterns, 105 icons with import code, React rules, 22 front-end stacks | Nothing of the kind | Not for a game screen: pages, components and frameworks of the web |
| `design` skill | Logos, corporate identity, slides, banners, icons and social photos, through image models | `art.py` and the art routes (`art-from-the-image-tool.md`) | Not for a game screen: brand deliverables |
| `design-system` skill | Primitive, semantic and component tokens; slide decision tables | `PALETTE`, `TEXT_SIZE`, `UNIT`: one layer of values by role | None: three token layers serve a component library, and a generated game has none |
| `ui-styling` skill | shadcn/ui, Tailwind, a canvas poster method and 54 font files | Construct 3 objects, no DOM | Not for a game screen: a web component stack |
| `brand` skill | Voice, messaging, logo use, approval and consistency checklists | `USER_LOOK` names the user's look | Not for a game screen: brand governance |
| `banner-design` skill | Banner sizes per platform, art direction styles, export to images | None | Not for a game screen: a banner is an ad, not a screen |
| `slides` skill | HTML decks with Chart.js and copy formulas | None | Not for a game screen: a deck |

The copies under `cli/assets/skills/` match these skills. The one
difference is `ui-styling`, which lacks the font files there.

## Options

1. **Take its game palettes or styles as directions for the picker.** The
   palettes are web tokens with no role for a game's kinds, and the styles
   are CSS effects. A direction from one would differ mostly in its colours
   and effects.
2. **Search its data for a look by genre.** The same look for every game of a
   genre, chosen with no picture, which `look-picker.md` replaced.
3. **Adopt its UX rules that have no counterpart here.** All four are
   contradicted by the examples.
4. **Record what was measured as rejected rules, and change nothing else.**

## Decision

Option 4. The look manifest gains `touch.spacing`, `type.line-height`,
`type.measure` and `type.body-16` as rejected, each with the measurement
above, so that a later read of a web skill does not bring them back. `dev/evals/measure_layout.py`
gains `--taps` and `--lines`, which measure them. The template, the
checks, `pick_look.py` and the sub-agents' prompts are unchanged.

## Re-evaluate when

- The data adds rows for a game's screens rather than its web page: a HUD,
  a pause menu, a result screen, a palette with roles of a game's kinds.
- A user's game puts two tapped buttons so close that players hit the wrong
  one: measure the gap on that game, and `touch.spacing` may come back as a
  warning for buttons alone, not for a board's cells.
- A generator helper starts writing paragraphs of text, such as a dialogue
  box: measure line height and line length on the examples' dialogue texts
  alone.
- Kinds told apart by colour alone confuse a user's players: guideline 37,
  "colour only", would then tighten the sixth question of `review_look.py`,
  which accepts a colour as the difference.
