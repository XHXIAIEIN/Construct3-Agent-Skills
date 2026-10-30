# The Look Manifest Owns Every Look Rule

Date: 2026-10-30

## Problem

The rules of a generated game's look were written in six places:
`assets/look-manifest.json`, `SKILL.md`, `references/generating-a-project.md`,
the comments of `assets/build_project.py`, the section "Viewport, look and
HUD" of `Construct3-Cookbook/guides/project-files/new-project.md`, and the
records. No script read the manifest. A read on 2026-10-30 found about a
dozen places where two of them disagreed:

- `landscape-viewport.md` gave `MARGIN` as 32 at 1080, and the template
  computes 64.
- The template's fallback for `POINTER_STYLE` set the hover to ink, the
  hover the user turned down (`paper-and-ink-look.md`), while the setting
  above it says the hover role.
- The manifest's deliver step drew the plain backdrop with `backdrop()`,
  and the template stops that call: the plain paper is the layer's colour.
- The manifest and the Cookbook said the skill ships Inter, and the fonts
  come from the user's font cache.
- The manifest asked 3:1 of a title, and the code asks it of any text from
  18 pt up.
- `layout-by-name.md` gave the body size at a 32 px grid as 32 pt; it is
  18 pt at 1920×1080.
- `paper-and-ink-is-the-fallback.md` said the look judge reads
  `USER_LOOK`, and neither the brief nor the agent gives it.
- `SKILL.md` blamed Pillow for code-drawn art, and
  `art-drawn-in-code.md` found the method at fault.
- An eval case described a grey checkered backdrop that the template no
  longer draws, and three records cited a guide by its old path.

## Options

1. **Fix the disagreements in place.** Each copy then drifts again with the
   next change.
2. **One owner.** The manifest holds every rule with an id, its value or
   the template setting that holds it, its scope and its record. Every
   other place cites the id. A script that enforces a rule reads the value
   from the manifest, and a test holds each value equal to the template's.
   Chosen.

## Decision

Option 2.

- Each rule of the manifest carries `source`, its record, and
  `decisions` lists every record that a rule cites.
  `test_look_manifest_matches_the_template` fails on a rule without a
  listed source, on a listed record that does not exist, and on a value
  that differs from the template's.
- `check_look.py` reads `grid.unit`, `pixel-art.sampling` and
  `motion.squash-art` from the manifest, and the test holds them equal to
  the template's at 320×180, 720×1280 and 1920×1080.
- The references cite rules by id where they restated values. The Cookbook
  section keeps the Construct facts (Anchor, *Unbounded scrolling*, the
  1 px line that drops out) and lists the rule ids by topic with a link to
  the manifest.
- The player's stand-in shape is the rule `subject.player-shape`, open:
  the prototype drew a disc and the shape vocabulary says rectangle. The
  user picks on screenshots, and until then the deliver steps keep the
  rectangle.

The evidence that the Cookbook section carried moves here, because it
settles the values of these rules:

| Rule | Evidence |
|------|----------|
| `grid.unit` | Three quarters of the official examples' x positions and five sixths of their widths sit on 8 px at 320×180; half of their x and three fifths of their widths on 32 px at 1920×1080 |
| `hud.paper` | The examples' HUD edge offsets are 0, one unit or two. On a TV, graphics stay 5% inside every edge (EBU R95) |
| `touch.target` | 48 dp (Android accessibility help), 44 pt (Apple HIG, *Accessibility*, the iOS default control size), 44 px (WCAG 2.5.5), with 8 dp between two targets. A phone shows its shorter side across about 360 dp, so 48 dp is 48 × the shorter side / 360 viewport px |
| `layout.proximity` | Layout guides for slides and posters ask the gap between groups to be at least 1.5 times the gap inside one |
| `layout.fill` | The one-screen layouts of the official game examples cover 80% of the screen at the median |
| `colour.palette-only` | The median pixel-art project draws its art with hard edges in 35 colours, and 9 of them cover 95% of its opaque pixels. Labels use one to three colours, white in two of three, and two sizes, rarely more than four |
| `pixel-art.sampling` | Every studio project at 360 px or less samples *Nearest*, and most scale by whole numbers |

## Re-evaluate when

- A rule is enforced by a script other than the template and
  `check_look.py`: that script reads its value from the manifest too.
- The user picks the player's shape: `subject.player-shape` becomes
  adopted with that value.
