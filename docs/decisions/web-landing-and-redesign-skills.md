# What a Web Landing Page Skill and a Redesign Skill Add to the Game's Look

Date: 2026-10-31

## Problem

elayadesign publishes two MIT-licensed Agent Skills for web interfaces. In
`elayadesign/ai-design-skills`, `skills/landing-page-design/SKILL.md` builds
a landing page: intake questions, page structure, conversion copy and a
visual system of type, spacing, radius and motion. In
`elayadesign/redesign-skill`, `skills/redesign-existing-projects/SKILL.md`
audits an existing interface and upgrades it in place. Both say that parts
of them come from taste-skill, which `game-look-from-design-skills.md`
already read.

Task: read both files heading by heading against the look pipeline: the
rules of `assets/look-manifest.json`, the generator template
`assets/build_project.py`, `scripts/check_look.py`, `scripts/review_look.py`
and its questions, `scripts/pick_look.py`, and the `art-drawer` and
`look-judge` sub-agents. Take what a game screen needs. A threshold comes
from a measurement on the official 2D game examples. A rule that the look
manifest rejected by measurement stays rejected unless new evidence says
otherwise. The redesign skill's method for auditing and upgrading an
interface is compared with the way this repository reviews and fixes a
generated game's look.

## Evidence

### What the official examples do

`dev/evals/measure_layout.py` and a reading of the same examples' layouts
and event sheets, over the official examples tagged as 2D games, on
2026-10-31:

| Rule from the skills | What the examples do |
|----------------------|----------------------|
| One typeface on a site, a second only on request | Of 109 layouts that hold a Text, 95 use one face and 14 use two, none three. Of 50 projects, 38 use one face and 12 use two |
| No italic | 8 of 448 Texts are italic |
| Sentence case, not capitals everywhere | 17 of 381 Texts with three letters or more are all capitals |
| No placeholder text | 21 of 448 Texts in the layout files show `Text` or Lorem ipsum, and events set them at runtime, such as a score that starts as `Text` |
| A paragraph at most about 65 characters wide | 19 of 139 wrapped Texts of more than 80 characters run over 65 characters a line, counting a character as half an em |
| Bottom padding larger than top, so the content sits a little high | The content of 81 one-screen layouts is centred a median 0% off the screen's middle: 44 within 3% of its height, 25 lower and 12 higher, 3 of those by 4 to 6% |
| No transition shorter than 200 ms | 183 of 1275 tween times written as numbers are under 0.2 s; the quartiles are 0.25, 0.5 and 0.5 s |

Only 4 of the 81 one-screen layouts hold a HUD on a layer at parallax 0, so
the space the HUD leaves is the whole screen in nearly all of them.

### The landing page skill, heading by heading

| Heading | What it says | What this repository does | Change |
|---------|--------------|---------------------------|--------|
| Landing Page Design | A landing page wins one intent: one offer, one audience, one action | A game screen has no single action; `colour.one-accent` and `layout.focal` were rejected for that reason | None: not for a game screen, which shows many things to act on |
| Scope | All web UI; the file wins over a framework default, the user wins over the file | `look-manifest.json` `about`: the user's look in `USER_LOOK` replaces every rule of scope `paper-and-ink`, and the `every-look` rules still hold | None: the same order, already held |
| Part A, Strategy and structure | Decide what the page says before its look | The design review (`review_design.py`) and `tools/design.json` decide what the game does before its look | None |
| A1. Intake | Ask in one batch only for what is missing; if there is no answer, assume, state it in one line and go on | `look.picker`: the user picks from three drawn directions instead of answering questions; with no look given the game takes paper and ink without asking (`paper-and-ink-is-the-fallback.md`) | None: a picture to pick from replaces the questions, and the fallback keeps the build going |
| A2. Page structure | Hero, argument, objections, a final CTA | Screens by kind: play, title and result (`title-and-result-screens.md`) | None: not for a game screen, a page's sections |
| A3. Layout selection | Pick one of four page layouts and say why | The layout follows the game; `layout.fill` and `layout.spread` hold what the examples measure | None: not for a game screen |
| A4. Conversion rules | One CTA, benefits, specific claims, risk reversal | No counterpart | None: not for a game screen, conversion copy |
| A5. Copywriting | Headline formulas, CTA verbs, benefit bullets | No counterpart | None: not for a game screen, conversion copy |
| A6. Build order | Section by section; never rebuild the whole page | The generator rebuilds the whole project on every run, and `look.before-the-change` fails only a yes the change brought | None: a generator's full rebuild is deterministic, and the look review already limits a change to what it brought |
| A7. SEO and AEO | Index or noindex, meta, FAQ schema | No counterpart | None: not for a game screen, search |
| A8. Pitfalls | Too many CTAs, vague copy, proof at the bottom, broken mobile layout | `look.screen-shapes` looks at a phone's shape for every layout | None: the mobile part is held, the rest is conversion copy |
| Part B, Visual system | Every value comes from the rules, never ad hoc | `colour.palette-only` and `type.scale` stop a colour or a size that is not a role of `PALETTE` or a kind of `TEXT_SIZE`; `grid.*` holds every position to `UNIT` | None: held, enforced |
| B1. Typography | Fonts, copy, scale and button type | See the four rows below | — |
| Fonts | Four named fonts, five banned ones, Inter among them; no italic; one typeface; no weight above bold | `type.inter`, adopted by the user: Inter in three weights in paper and ink; `text_inst()` writes no italic; `FONT` names weights, not families | `type.two-families`, proposed: the examples use one face in 95 of 109 layouts and two in the rest, so one fails 13% and two holds them all. The named and banned fonts are taste, and the user chose Inter. No italic rule, since the template writes none and a look the user gives may want it |
| Copy rules | No hyphens; no word alone on the last line | `review_look.py` question 1 asks for a text broken onto a line of its own; the worst data state uses a long hyphenated name | None: the orphan is asked already; a hyphen is a matter of copy, and a game's names have them |
| Type scale | Snap every size to Tailwind's thirteen steps, down to the nearest | `type.scale`, enforced: a size is a kind of `TEXT_SIZE`; `type.modular-scale` rejected by measurement | None: held; a fixed web scale is a ratio scale, which the examples turned down |
| Button type | Main buttons 16 px semibold, header buttons 14 px | `button()` takes `label_size()`, title or body, in the key's weight, medium | None: held by kind; px values of a web page do not scale with a viewport |
| B2. Spacing | Thirteen spacing values from 0 to 96 px; buttons padded 8 by 12 px | `grid.unit`: every position on `UNIT`, 8 or 32 px; `GAP_IN`, `MARGIN`; `button_size()` pads a unit on each side and half above and below, at least `TOUCH` | None: held, as a grid that scales with the viewport |
| B3. Corner radius | Tailwind radii; an inner radius is the outer one less the gap | The template draws no rounded corners; `avoid.dashboard` turns rounded cards down; concentric radii were left out in `look-from-aesthetics-skills.md`, option 8 | None: not for a game screen, web cards |
| B4. Borders and backgrounds | No border on one side of a card; no background gradient | `backdrop.sheet` and `palette.greys` keep paper and ink flat; a look the user gives sets its own backdrop | None: held in the fallback; a gradient sky is a game's look, not a fault |
| Dark mode background colors | Six approved dark greys | `PALETTE` by role, `colour.structure` and `text.contrast` in every look | None: a fixed list is a brand's palette, and the user's look gives the colours |
| B5. Hero section | Heading colour and layout | — | — |
| Heading color | A grey text gradient on the hero heading | `screen.title-name`, proposed: the title is an image drawn by the art route | None: not for a game screen, where the art draws the title |
| Layout | Heading and subheading at most 680 px wide, broken where the thought breaks | `band_text()` stops a text its band cannot hold; `result_headline()` sets one line | None: a game screen holds labels, not paragraphs, and no paragraph helper exists |
| B6. Icons | Three icon sets allowed, Material banned | `svg_kit.icons()` draws a set of icons with one stroke and radius | None: the art draws its own icons, in one stroke |
| B7. Motion | One ease-out curve, 500 ms for movement, 300 for colour, never under 200 ms; only transform and opacity; reduced motion | `TWEEN_STYLE` by class, from the examples' tweens (`motion-by-class.md`); `popup` takes `easeoutquint`, the same curve; `motion.reduced` proposed | `motion.duration-floor`, rejected: 183 of 1275 of the examples' tweens are under 0.2 s, and a hit flash of 0.08 s and a press of 0.1 s are measured choices (`count-up-and-press.md`). Transform and opacity only is a browser's reflow rule, and Construct lays out nothing |
| Navigation | A floating nav bar, an animated menu toggle, a full-height mobile menu whose links arrive 60 ms apart within 400 ms | `motion.stagger`, proposed, 0.03 to 0.08 s apart | None: not for a game screen, web navigation. The 400 ms cap of a sequence joins `motion.stagger` when the examples are read for a step |
| Scroll reveals | Sections rise 32 px and fade in once over 600 to 800 ms; no scroll listener | No counterpart | None: not for a game screen, which does not scroll as a page |
| B8. Content realism | Real copy, specific names, numbers that are not round, no filler words, calm system messages, sentence case | `look.worst-data`: each layout is shown with the longest text, no text and counts of 1 | `text.placeholder`, proposed: a Text still showing the Text object's default text or Lorem ipsum once the layout has run. The rest is marketing copy |
| B9. States | Hover, active, focus, loading, empty and error states on every control | `POINTER`: the hover and pressed roles; `press()` squashes a pressed object to 0.9 for 0.1 s; `look.worst-data` shows the empty state | None: held for the pointer and the press. A focus ring needs a menu moved by keys or a pad, which the template does not have (`input-controls.md`) |
| B10. Ship requirements | Legal links, a 404, form validation, skip link, cookies, favicon, meta tags, alt text, semantic HTML | No counterpart in the look | None: not for a game screen, a website's furniture |
| B11. Tagline reveal section | A large tagline, word by word from 30% to full colour as it scrolls in | Text at 35% in `hints()`, the dim of a used key | None: not for a game screen, scroll-driven |
| Output format | An outline, hero copy, benefits, steps, FAQ, SEO and a layout before code | `tools/design.json` and the design review before the events | None: not for a game screen, a page's copy |
| Quick checklist | A checklist the author ticks | `review_look.py` writes the questions into `brief.md` for `construct3:look-judge`, which has not seen the game, because the agent that built it reads its pictures by what it meant (`look-judge-agent.md`) | None: held more strictly, by a reviewer that has not seen the request |
| Credits | Parts come from taste-skill | taste-skill was read in `game-look-from-design-skills.md` | None |

### The redesign skill, heading by heading

| Heading | What it says | What this repository does | Change |
|---------|--------------|---------------------------|--------|
| Redesign Existing Projects | A diagnostic: find what is wrong and fix it in place | `review_look.py` finds faults on the game's screenshots, and `verify_change.py` runs it after each change | None |
| Design values (at the top) | Every value lives in one section; never invent one; to adapt the skill, edit only that section | `look-manifest-owns-the-rules.md`: the manifest owns every rule; `PALETTE`, `TEXT_SIZE` and `UNIT` hold the values; `USER_LOOK` swaps the fallback's taste for the user's look, and the `every-look` rules still hold | None: the same design, held. The redesign skill asks before a value it lacks; `type.scale` adds a new kind to `TEXT_SIZE`, which keeps the value in one place |
| How this works | Scan the stack, diagnose everything and report it before fixing, then fix in priority order without a rewrite | `review_look.py` reads every instance from the runtime and prints every finding ranked by tier; its next line says to fix the broken ones first and to ask the user when a yes has more than one right fix; `look.before-the-change` fails only what the change brought | None for a generated game. For an existing project, see "The method compared" |
| Design audit | The checklist by area | Seven questions with tiers, the mechanical findings, and `check_look.py` | — |
| Typography | Fonts, one typeface, no italic or black weights, more weights, display presence, 65-character measure, tabular figures, tracking, sentence case, orphans, hyphens, scale, button type | As in the landing page rows; tracking is `tracked()`, a quarter-em space, since the Text object has no letter spacing; tabular figures were left out because the Text object sets no font features (`look-from-aesthetics-skills.md`, option 8) | `type.two-families`, proposed. The measure is not taken: 19 of 139 of the examples' long wrapped texts run over 65 characters, and the template has no paragraph helper |
| Color and surfaces | An approved palette, no background gradient, no purple-blue AI gradient, saturation under 80%, one accent, one grey family, tinted shadows, grain, one light direction, no stray dark section, imagery for empty sections | `PALETTE` by role; `colour.one-accent` rejected; `palette.greys` neutral; `shadow.form`: one direction for the whole scene; `avoid.same-decoration`; `depth.parallax-layers` rejected in paper and ink | None. A saturation cap fails paper and ink's adopted accents, three of them fully saturated, and a game's accents mark kinds of content. A grey family and tinted shadows are the user's look, with no measurement to set a threshold |
| Layout | Break symmetry, no three equal cards, `100dvh`, grid, max width, variable heights, the radius formula, the spacing scale, overlap, more bottom padding, aligned rows, optical alignment | Grid on `UNIT`; `result_headline()` centred by measurement; `layout.focal` rejected because a grid of equal tiles is a sound game screen; `optical-label-centring.md` centres a label by its ink; `layout.balance` centres the playfield in what the HUD leaves | `OPTICAL_LIFT` set to 0, the user's choice: the examples centre their content, a median 0% off the middle with 44 of 81 within 3%. The rest is a web page's layout |
| Interactivity and states | Eases and durations, scroll reveals, a floating nav, menu motion, reduced motion, hover, press, focus, loading, empty, error, dead links, current page, smooth scroll, transform only | As in the landing page rows B7 and B9 | `motion.duration-floor`, rejected, as above |
| Content | Specific people, numbers and brands; no filler; specific CTAs and value; calm messages; active voice; no placeholder; sentence case | `look.worst-data` | `text.placeholder`, proposed. The rest is a page's copy |
| Component patterns | No generic card, no one-sided border, fewer ghost buttons, no pill badges, no accordion FAQ, no carousel, no tower pricing, fewer modals, no avatar circles, no sun-moon toggle, no link-farm footer | `avoid.dashboard`, enforced: no rounded cards, no score pill, no soft shadow under every panel; `popup()` for a panel | None: the game's form of the same fault is held; the rest are web components |
| Iconography and imagery | Approved icon sets, no cliché metaphors, one stroke width, a favicon, no stock team photos | `svg_kit.icons()`: one stroke and radius for a set; `avoid.style-mix`; `avoid.kinds-alike` | None: held for drawn icons. An export's icon is not part of the look review |
| Code quality | Semantic HTML, no inline styles, no fixed pixel widths, alt text, a z-index scale, no dead code, real imports, meta tags | `layer.z-order` orders each layer; `check_project.py` refuses an ACE that does not exist; `type.scale` and `colour.palette-only` refuse a hand-set value | None: the game's forms are held; the rest is HTML |
| Strategic omissions | Legal links, back navigation, a 404, validation, skip link, cookies, indexing | No look rule reads the game's flow | None: a way back from every screen belongs to the game's design, `tools/design.json`, not to its look; the rest is a website's furniture |
| Fix priority | Fix in order of impact per risk: fonts, colour, states, layout, motion, components, empty states, copy, type scale | `look.severity`: broken, then ugly, then fragile, by what the player cannot read, reach or tell apart | None: an order by harm to the player keeps a cut-off score ahead of a font swap |
| Rules | Keep the stack, keep it working and test after each change, report the diagnosis and let the user veto, small changes, never invent a value | `verify_change.py` runs the checker, the design review, the editor, the plays and the look after each change; the hand-over writes each fix as before, after and why; `LOOK_ROUNDS` stops after three rounds with a yes left | None for a generated game |
| Design values (at the bottom) | The values themselves: fonts, dark greys, the heading gradient, spacing, radius, icons, motion, the type scale | As in the landing page rows | None: a web brand's values |
| Credits | Parts come from taste-skill | As above | None |

### The method compared

The redesign skill and the look pipeline share the shape of the work: a
fixed list of faults, one source of every value, a diagnosis before a fix,
and a check after each fix. The pipeline is stricter in three places. A
reviewer that has not seen the game answers the questions, not the agent
that built it. Each fault has a tier by what it costs the player. A fix is
looked at again by a script, three rounds at most.

The two differ on an existing project. The redesign skill takes an
existing interface as the thing to upgrade. `look.before-the-change` takes
a yes from before the change as the project's own look: `verify_change.py`
passes it and names it in the hand-over. So when the user asks for an
existing game's look to be upgraded, the faults from before are what the
user asked to fix, and no step of the pipeline makes them the work list.

## Options

1. **Take the skills' visual systems as values.** Their fonts, greys,
   spacing, radii and type scale are a web brand's. The template's values
   scale with the viewport and come from the user's look or from paper and
   ink, which the user chose.
2. **Propose the rules the examples support and the template lacks.** At
   most two type families on a screen holds on every example layout. A
   placeholder still on screen after the layout has run is a fault on any
   screen, and the layout files show that only the runtime can find it.
3. **Reject a duration floor of 200 ms by measurement.** A game's feedback
   is faster than a web page's hover.
4. **Centre the playfield in what the HUD leaves, without a lift.**
   `layout.balance` raised it by 5% of that space, a rule of thumb with no
   measurement behind it, and the examples centre their content. The rule
   was open, its value the user's choice.
5. **Treat the yeses from before as the work list when the user asks to
   upgrade an existing game's look.** This changes what the skill and
   `verify_change.py` do, so it needs the user's word first.

## Decision

Options 2, 3 and 4, in `assets/look-manifest.json`:

- `type.two-families`, proposed: the texts of a screen use at most two type
  families, as every official 2D game example layout does.
- `text.placeholder`, proposed: no Text shows the Text object's default text
  or Lorem ipsum once its layout has run. It is proposed until
  `review_look.py` runs over the examples whose layouts hold such a text and
  shows that their events replace each one.
- `motion.duration-floor`, rejected, with its measurement.
- `layout.balance`, adopted: the user set `OPTICAL_LIFT` to 0 on
  2026-10-31, so `centred()` puts the playfield in the middle of the play
  area and `balanced()` warns on a centre off that middle.

Option 1 is not taken, for the reason above. Option 5 waits for the user.
No sub-agent's prompt changes.

## Re-evaluate when

- A look the user gives sets three type families and the user likes it on
  screenshots: the two-family limit is taste, not legibility.
- `review_look.py` runs over the examples that hold a placeholder in their
  layouts: adopt `text.placeholder` as a finding if none is left once the
  layout has run.
- The user asks for an existing game's look to be upgraded: decide option 5.
- A user finds a centred playfield low on screenshots: the lift comes back as the user's look.
- The template gets a menu moved by keys or a pad: it needs a focus state.
- The example clone updates: rerun the measurements of the first table.
