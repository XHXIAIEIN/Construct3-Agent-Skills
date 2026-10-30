# taste-skill and frontend-design Read in Full, Against the Game's Look

Date: 2026-10-31

## Problem

`game-look-from-design-skills.md` skimmed fifteen design skills and kept
only what they share: decide the look first as named values, give every
colour a role, look at the rendered result. Two of them aim directly at an
agent's output looking generic, and were read here in full:

- [taste-skill](https://github.com/Leonxlnx/taste-skill) v2.1.5 (commit
  `12af471`, MIT): `skills/taste-skill/SKILL.md`, its eleven references, its
  scripts (`draw.mjs`, `inspect.mjs`, `lint.mjs`, `scenes.mjs`, `assets.mjs`
  and `lib/`), its library and `evals/evals.json`.
- Anthropic's
  [frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md)
  (commit `41bbe19`, Apache 2.0, per its `LICENSE.txt`).

Task: for each heading of the two skills, what the look pipeline of this
repository can take from it, measured on the official 2D game examples where
a rule would hold a threshold. No copy of either skill's text is kept here.

## Evidence

### How taste-skill works, from its scripts

- **Art direction is dealt, not drawn from reference images.**
  `draw.mjs` filters 20 text directions by sector, the assets the project
  has and the tone, then picks at random, preferring those it did not deal
  in its last five draws (a history file in the user's home folder). Three
  are offered with `--options 3`; the *agent* picks one by holding it
  against an inventory of the subject. The library holds prose and numbers
  measured from 202 gallery sites; their screenshots stay private, so no
  agent ever sees a picture of a reference. Nothing checks that the built
  page follows the dealt sheet, except a warning when neither dealt typeface
  rendered.
- **The browser check measures house rules.** `inspect.mjs` drives Chrome
  over CDP at 1440, 768 and 390 px, scrolls with real wheel input, takes
  screenshots, and fails a page on about 40 rules: an eyebrow label,
  monospace, 01/02 numbering, tiny tracked capitals, gradients, shadows,
  hairlines, a violet or a cream-and-terracotta palette, fewer than four
  raster pictures, fewer than eight moving elements, unequal outer margins,
  two near-empty screens, a large text 20% covered by another element.
  Most thresholds are stated as the owner's taste; a few cite the study.
- **The look is judged by the builder.** After the gate the same agent reads
  its screenshots through fourteen passes and scores itself on the Awwwards
  weights with caps, three rounds at most.
- **Its own blind test.** In five rounds over six briefs, a separate model
  juror scored the skill's builds below the no-skill baseline in four rounds
  and level in one; the skill won 5 of 16 briefs. Its final builds measured
  no FAIL against 8 to 13 for the baselines (`references/research.md` §11).
  The jurors punished a quiet page that read as empty and rewarded an idea
  only this subject could own. One juror per brief, so a score carries about
  half a point of noise.

### How frontend-design works

Prose only. The agent plays a design lead, takes the look from the
subject's world, writes a plan of 4 to 6 named colours, type roles, a layout
and principles, then reviews the plan against what it would produce for any
similar prompt and revises the generic parts before building. It names five
clusters of generated design, among them a warm cream ground with a
terracotta accent and "template chrome": tracked capital labels, parts
joined with middle dots, zero-padded index numbers. It spends boldness in
one place and critiques screenshots as it builds.

### What the official 2D game examples set in their texts

`dev/evals/measure_layout.py --labels` counts how the texts of the 113
examples tagged as 2D games are set, BBCode tags left out, in the layouts
and in the events' `zeropad()` calls:

| Device | Examples |
|--------|----------|
| Labels of 20 characters or fewer in capitals ("GAME OVER", "START", "SCORE:") | 138 of 323 labels, in 18 examples; 84 of 185 under 5% of the shorter side, in 13 |
| Letters spaced apart (tracked) | 0 of 679 texts; the Text object has no letter spacing |
| Parts joined by a middle dot or a bar | 2 of 679 texts, neither a middle dot |
| Zero padding in the layouts' texts | 16 of 679, all a score or a clock ("Score: 000", "00:00") |
| `zeropad()` in the events | 28 examples; 11 on a clock's part; at most 4 on a level, round or wave |

So capitals and zero-padded scores and clocks are a game's idiom, not a
web tell. Tracked capitals, middle-dot joins and a zero-padded round number,
the three parts of the fallback's HUD tag (`hud_tag("RoundTag", "Round · 01
/ 06")`), are each absent or nearly absent from the examples.

### Heading by heading

taste-skill, `SKILL.md`:

| Heading | What it says | This repository today | Change |
|---------|--------------|-----------------------|--------|
| Intro, the four ways | A script deals directions; the idea comes from the subject; a house style checked in a browser; look at the screenshots | `pick_look.py` renders three directions; `check_look.py` and the template's stops; `review_look.py` and `construct3:look-judge` | None; the parts exist, with the user picking instead of the agent |
| Page or app screen | Two runs; an app screen has its own rules against a generated dashboard | `avoid.dashboard`, question 7 of `review_look.py` | None. Its app-screen list (KPI tiles, icons in tinted circles, a shadow under every panel) is what question 7 already names |
| 1. Read the brief and the project | Find what imagery really exists; inventory 8 to 12 things only this client has | `USER_LOOK` names where the look comes from; `art/references/` holds the user's pictures (`look.references`) | Proposed below for the draw brief: each direction names the game's own thing it comes from |
| 2. Write the argument | Sections as claims with proof | — | Not for a game screen: a game has no sections to order |
| 3. Draw the direction | Deal three directions, the agent picks against the inventory, adopt the sheet, record redraws | `look.picker`: three directions that differ in two of six dimensions; the *user* picks on screenshots; the pick writes `USER_LOOK`, `PALETTE`, `ART_STYLE` | None. The user's pick on a render is stronger than an agent's pick on prose; taste-skill records redraws only as a count |
| 4. Find the idea | "On this page, X becomes Y", the competitor test, one live thing | `directions.json` holds `right_when` and `cost` per direction, no source in the game's subject | Proposed below: the competitor test in the draw brief. The live thing is not for a game screen: the whole screen is live |
| 5. Write the words | Two-line headlines, one supporting sentence, full content | `screen.result-headline`: one line at `display`; `hud.paper` | None; result screens were measured in `title-and-result-screens.md` |
| 6. Build it, still | Tokens first; imagery order own > generated > found > drawn; at least four raster pictures; equal margins; no blank stretch | `PALETTE`, `TEXT_SIZE`, `FONT`; `art.routes` (image tool, user's art, SVG drawn by `construct3:art-drawer`); `layout.fill` 15%; `MARGIN` on both sides through `anchor()` | None. The picture floor and found archival pictures are not for a game screen: a game's pictures are its sprites, drawn in one `ART_STYLE`. Its drawing rules (one graphic language, three levels of detail) match `avoid.style-mix` |
| 7. Gate | `lint.mjs`, `inspect.mjs`, `scenes.mjs`; fix every FAIL | `check_look.py`, the template's stops, `review_look.py`'s measured findings | None |
| 8. Look | The builder critiques its own screenshots, Awwwards score with caps, three rounds | `review_look.py` writes `brief.md` for a judge that has not seen the project; fixed yes/no questions, tiers by `look.severity` | None. A scored rubric was turned down as option 6 of `game-look-from-design-skills.md`; the builder judged its own card game by what it meant to build |
| 9. Move | At least 8 moving elements, entrances staggered 60 to 90 ms | `motion-by-class.md`, `motion.stagger` proposed | Not for a game screen: the floor counts page entrances. The stagger is already a proposal of its own |
| 10. Report | Report only after 0 FAIL and every screenshot opened | `verify_change.py` and the look step | None |
| House rules | No eyebrows, monospace, index numbers, thin rules, gradients, shadows at rest, glass, cream and terracotta, violet, tiny tracked capitals, icon cards, accent word, more than two faces | `avoid.dashboard`; paper and ink draws thin lines for areas (`lines.areas`) and a cast shadow (`shadow.*`), both of the fallback's scope | Rejected for a game: `type.caps-labels` and `type.no-index-numbers` below. Its own study finds thin rules no rarer on strong sites (61% against 52%), and in a game a line marks an area's range. Shadows, gradients and monospace or pixel score fonts are a game's means, and a user's look may use any of them |
| Laws of the craft: type | Two or three sizes, one large and one small; five at most; left-aligned | `type.scale` holds the kinds of `TEXT_SIZE`; `type.modular-scale` and `type.one-display` rejected | None; measured in `look-from-aesthetics-skills.md` |
| Laws of the craft: space | One grid, equal outer margins, large gap between sections | `grid.*`, `MARGIN`, `layout.spread` | None |
| Laws of the craft: colour | One ground, one ink, one accent on the action | `colour.one-accent` rejected: a game's accents mark kinds of content | None |
| Laws of the craft: imagery | One dominant image; one crop and treatment | `layout.focal` rejected (31% of one-screen layouts pass); `avoid.style-mix` | None |
| Laws of the craft: components | Square or fully round buttons, decided once | `control.parts` | Not for a game screen: the 9 to 16 px radius it calls weak is a count of web buttons in a gallery |
| Special cases | Keep a brand's colours and type, take only composition; record the before | `USER_LOOK`; `look.before-the-change` | None |
| Files | The library, the scripts | — | None |

taste-skill, beyond `SKILL.md`:

| Heading | What it says | This repository today | Change |
|---------|--------------|-----------------------|--------|
| `critique.md`, the fourteen passes | One second then five; squint; cover the logo; edges; fullness; collisions | Questions 1 to 7, the reference question and the question across screens | None. "Cover the logo" is the reference question turned around and has no measure here |
| `tells.md` | A dated registry; it names procedures, not replacement fonts or colours, because a list of replacements becomes the next tell | Paper and ink names Inter and fixed colours | None as a rule; the warning stands behind the proposal on the tag below |
| `research.md` §11 | The blind test above | `look-judge-calibration.md` measures the judge against labels | Re-evaluate line below |
| `app-screens.md` | A generated dashboard: KPI cards with icons in circles, a coloured sidebar pill, a gradient area chart; the "face step" against "a well-applied kit" | `avoid.dashboard` | None |
| `inspect.mjs`, `scenes.mjs` | CDP, three widths, wheel scrolling, contact sheets | `open_in_editor.py` drives Edge or Chrome over CDP; `review_look.py` visits every layout and its data states | None. The game has one viewport, and `look.screen-shapes` covers other screens |
| `lint.mjs` | Source regexes for banned classes and stock phrases | `check_look.py` reads the project | Not for a game screen: it scans CSS and marketing copy |

frontend-design:

| Heading | What it says | This repository today | Change |
|---------|--------------|-----------------------|--------|
| Intro | A design lead with a distinct point of view, for a client who rejected templated work | Paper and ink, the same look for every game with no look given (`paper-and-ink-is-the-fallback.md`) | None: the user keeps paper and ink as the only fallback (option 2) |
| Ground your designs in the subject matter | The subject's materials and vernacular decide the look; propose the subject and confirm | The game's request names the subject; `pick_look.py` runs only when the user gave a look | The draw-brief proposal below |
| Design principles: the first thing seen | Open with what is most characteristic of the subject | The first play screen is what the picker draws | None |
| Design principles: typography | One or two families; a scale; avoid one accented word, capitals for labels, labels above content | `type.inter`, `TEXT_SIZE`; the fallback's tag is tracked capitals | `type.caps-labels` rejected for a game; `hud.tag-plain` proposed for the fallback |
| Design principles: structure is information | Numbering only for a real sequence | A round is a real sequence; the tag pads it to two digits | Part of `hud.tag-plain` |
| Design principles: motion | One orchestrated moment; motion that answers an action is welcome | `motion-by-class.md`, `motion.frequency` proposed | None |
| Process: the five clusters | Cream and terracotta; near-black with one acid accent; broadsheet hairlines; the SaaS card kit; template chrome | `PALETTE` is white, greys, electric blue and deep orange; `avoid.dashboard` covers the card kit | `hud.tag-plain` for the chrome; the hairlines are the fallback's area lines, which carry an area's range |
| Process: plan as tokens, then review against a similar prompt | 4 to 6 named hex values, type roles, a layout in ASCII; revise what any similar prompt would give | `directions.json`: `axes` on six dimensions, `ART_STYLE`, `PALETTE` by role; `pick_look.py` refuses two directions apart in fewer than two dimensions | The draw-brief proposal below; the check of difference between directions is already mechanical |
| Process: CSS specificity | Selectors that cancel each other | — | Not for a game screen: there is no CSS |
| Restraint and self-critique | Boldness in one place; a quality floor; screenshots; notes of what was tried | `layout.focal` rejected; contrast stops; `review_look.py` | None |
| More on writing in design | Name actions by what they do; one name through a flow; errors say what to fix | `hints()` pairs each key with its verb | Not a look rule; a menu's wording belongs to the design review, whose questions do not ask it yet |

### Proposed, not made

- **The draw brief of `pick_look.py`**, the task of `construct3:art-drawer`:
  each direction of the user's look names, in `right_when`, the thing of
  this game's own world it comes from (a material, a place, a printed
  object of its fiction), and says why the direction would not suit another
  game of the same genre. Both skills put the source of a distinct look in
  the subject; taste-skill's jurors named it first. This changes a
  sub-agent's prompt, so it waits for the user.
- **No new look-judge question.** taste-skill's passes either repeat the
  seven questions (cut text, collisions, a stand-in among art, a dashboard
  look) or ask a web question. Its "quiet page reads as empty" has its
  measure in `layout.fill`.

## Options

1. **Adopt taste-skill's house rules as checks.** They fail on what a game
   uses on purpose: capitals in 18 examples, zero-padded scores and clocks in
   28, shadows and gradients in any painted look. Its own blind test shows
   the rules met without the page winning.
2. **Replace the fixed fallback with directions taken from the subject**,
   as both skills would, or show them in the picker beside paper and ink
   when the user gave no look. Turned down by the user on 2026-10-31: paper
   and ink stays the only fallback, with no picker.
3. **Record the measured rules, propose the rest.** Chosen.

## Decision

Option 3. The look manifest gets:

- `type.caps-labels`, rejected: a ban on labels in capitals.
- `type.no-index-numbers`, rejected: a ban on zero-padded numbers.
- `hud.tag-plain`, proposed, scope `paper-and-ink`: the fallback's tag
  without the middle dot, the tracking and the zero padding, with the
  options for the user to choose.

The template, the sub-agents and the review questions do not change. A
game given no look keeps paper and ink alone, as
`paper-and-ink-is-the-fallback.md` says, and `hud.tag-plain` stays proposed
until the user picks one of its options.

## Re-evaluate when

- The user picks an option of `hud.tag-plain`: rewrite this record and
  the rule.
- A blind comparison of generated games, the kind taste-skill ran, is
  set up: score paper and ink against a direction taken from the subject.
- The example clone updates: rerun `measure_layout.py --labels`.
