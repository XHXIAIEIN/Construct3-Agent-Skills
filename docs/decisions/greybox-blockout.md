# Greybox Blockout: The Stand-in and the Level's Pacing

Date: 2026-09-26
Schema: Construct 3 r495.2

## Problem

A generated game has no art until the user or the agent's image tool
supplies it, and until then it has to look like what it is: a blockout that
can be played and read. The template does not draw art. In place of art it drew "a stand-in of
one colour or a plain shape", and each run filled that in its own way.

A level had the same gap. The grid, `anchor()` and `no_overlap()` place a
HUD; nothing placed a level's content, so a model laid platforms, hazards
and pickups one at a time, with no measure of what the player can jump and
no order in which the level asks things of the player.

Task: a generated game starts from a blockout that holds together and a level
laid out on grids and paced like a directed sequence, both from values of
the generator template, so that a small model gets them by default.

## Evidence

### What the user decided

Over reference blockouts and mock-ups of the stand-in:

- Value carries the hierarchy; colour is kept for what must be noticed
  wherever the eye is. Deep black and white with greys between, and a few
  highly recognisable accents.
- Placeholders are three shapes: rectangle, triangle, circle.
- Pattern marks areas and edges, not objects, as Tiled Backgrounds.
- The look is neutral and costs a model no decisions: a template default it
  keeps, not a style it chooses per game.
- A game's screen is the scene, not a dashboard. Of six mock-ups of one
  coin screen, three drew an app interface, with rounded cards, a score
  pill and a shadow on everything; the user read them as a template and as
  AI-made. Flat fills with no outline and no shadow carry the stand-in.
- The coins sit on a small board centred in the play area, 5 × 3 slots;
  scattered over the screen, or on a board as wide as the screen, they
  read as untidy.
- Where something is transparent, a mask, or a background still to come,
  the backdrop is the grey-and-white checker editors show for transparency.
- Where a game turns them on, the shadow is hard at half opacity and the
  outline thin, both drawn into the images. Soft translucent
  shadows read as a smear.
- A hit is a colour set with a size punch, and landing and jumping squash;
  a shadow, when on, falls at 45°, down and to the right.
- Level zoning follows a grid and camera zones, placed from a director's
  view that controls the rhythm of tension and rest.
- The look is metadata an agent can hand a model and confirm against, with
  two strict rules: a clean alpha channel, and objects locked to one grid.

The outline, shadow, hit and squash values come from the evidence in
`published-game-visual-language.md`.

### Level design

- Koichi Hayashida on *Super Mario 3D Land* (Gamasutra, 2012, "The Structure
  of Fun"): a level introduces one idea, develops it, turns it, and
  concludes, the four-panel *kishōtenketsu*.
- Smith, Treanor, Whitehead and Mateas, "Rhythm-Based Level Generation for
  2D Platformers", FDG 2009: rhythm groups of challenges joined by rest
  platforms.
- The Platform behavior (manual, `behavior-reference/platform.md`): with
  *Jump strength* v, *Gravity* g and *Jump sustain* s, jump height is about
  `v·s + v²/2g` and air time for a landing at take-off height about
  `s + v/g + √(2h/g)`; reach is *Max speed* over that time. The
  approximation ignores acceleration, the max fall speed and frame-by-frame
  integration.

### Construct facts the design leans on

- A Tiled Background repeats its image at any size without stretching it,
  so a pattern keeps its pixel size only there. The runtime subtracts
  `image-offset / image size` from the texture coordinate (the Tiled
  Background plugin of a published export's `c3main.js`), so two pieces meet
  without a seam when their offsets align the pattern to the layout.
- None of the effects in `data/c3-schemas/_index.json` draws an outline or a
  drop shadow.
- An object's colour multiplies its image, so Set color cannot turn a yellow
  shape white, and the Set color effect would recolour a baked shadow.
- A Platform or Solid object that grows moves its collision box into the
  floor.

## Options

1. **Leave the stand-in to the model.** Each run draws its own, and a
   template default is what a small model repeats.
2. **A look section in the prompts.** Prose the repository has measured not
   to reach a small model (`event-sheet-design-guidance.md`).
3. **A fixed vocabulary and starting values in the template.** Chosen.
4. **Soft drop shadows and a light top edge.** A translucent, blurred shadow
   over the checker reads as a smear.
5. **An app interface: a stage card, a score pill, a shadow under every
   element.** It looks finished in a mock-up, and the user read it as a
   template and as AI-made: a game's screen is the scene, not a dashboard.
6. **A two-ink print or an ink line.** Both have a character of their own,
   which a neutral default does not want, and the print's overprint and
   grain cost generation steps.
7. **The checker, outline and hard shadow by default.** The look of this
   record until 2026-10-08; on the preview the checker read as an image not
   yet loaded and the grey shadow as dirt. The checker stays for
   transparency, the outline and shadow as switches.
8. **Depth layers in parallax, each farther one lighter.** A misreading of
   the checker backdrop.
9. **Shadow Light in every game.** Right where light is a mechanic; as a
   default, a cost with no role.
10. **The shadow as an ink twin of each object on a layer below.** Each
    object then needs a twin kept in step with it, one more thing a small
    model writes wrong; drawn into the image, the shadow needs nothing at
    run time.
11. **The Flash behavior for a hit.** The evidence shows none using it for
    hits, and it blinks the whole image, shadow included.

## Decision

Option 3, in `plugin/skills/construct3-agent-plugin/assets/build_project.py`.
The vocabulary and its values are where a game starts; nothing stops a game
for leaving them (`mechanical-checks-only.md`).

### The vocabulary

| Dimension | Says | Values |
|-----------|------|--------|
| Shape | What a thing is | Rectangle: the player and structure. Circle: what is collected. Triangle: what hurts. |
| Colour | What role it plays | The roles of `PALETTE` |
| Pattern | What an area or an edge does | The stripes of `PATTERNS` |

An object is `shape(file, kind, w, h, role)` in `build_images()`: one flat
colour, whole units wide and high, its collision polygon the shape's. The
outline and cast shadow of `SHAPE_STYLE` are off by default; a game that
turns them on gets them drawn into the image.

| `SHAPE_STYLE` | When on |
|---------------|---------|
| Outline | the prototype's 2 px at 720 scaled to the viewport, 3 px at 1080, of `ink`, inside the edge, so a shape keeps its size on the grid |
| Shadow | `ink` at 0.5 opacity, hard, 2.7% of the viewport's shorter side at 45° |

The shadow widens the image on its side; the origin and polygon stay on the
shape. A sprite that rotates is drawn with `shadow=False`.

The score is its name over the number, one group of `hud_stat()`. Coins
land on the board, `COLS` × `ROWS` slots a finger wide and a unit apart,
one Tiled Background of a slot tile over an area drawn as lines, in the
middle of the play area the HUD leaves. A round deals the cells
`(deal + i × STRIDE) mod CELLS`, with `STRIDE` and `CELLS` coprime, so no
two coins meet, and the run stops on a round with more coins than slots.

### Colour

`PALETTE` holds the template's colour roles and `flash`, the fill of a hit.
The player is `ink`; a bar is an `ink` fill in a `solid` frame.

### Backdrop and patterns

The plain paper is the colour of the opaque `Background` layer, `canvas`,
with no object. In a game with something transparent, a mask or a
background still to come, `backdrop()` lays the checker, cells of
`UNIT / 2` in `canvas` and `canvas_alt`: in a one-screen layout over the
viewport on a layer at parallax 0, stretched to the screen by Anchor, its
cells following the screen's edge rather than the grid
(`fill-the-screen.md`); in a level larger than the viewport on a layer at
parallax 1 from the layout's origin, so it scrolls as the floor. In a
top-down game the backdrop is the floor.

| Pattern | Colours | Marks |
|---------|---------|-------|
| Checker | `canvas`, `canvas_alt` | Empty space over transparency: the backdrop only |
| Low stripes | `solid`, `dim` | A surface that is special and harmless: a one-way platform, a safe zone |
| Caution stripes | `ink`, `canvas` | What moves, triggers or blocks on a condition |
| Hazard stripes | `danger`, `ink` | An area that hurts |

`pattern(name, kind)` draws a one-unit tile, stripes at 45°;
`pattern_type()` declares its Tiled Background and `area()` places it on
grid cells. `tiledbg_inst()` writes
`image-offset = -corner mod tile`.

### Motion

- A hit is a frame: `hit_frame(file)` draws the shape's second frame in
  `flash` inside the ink outline, which keeps a white flash visible on the
  paper, tagged `hit`; `hit_flash(obj)` shows it for
  `HIT_FLASH["seconds"]`, 0.08 s of real time so slow motion does not
  stretch it.
- `squash(obj, kind)` sets the size to the share `SQUASH` gives, holds it
  and tweens back under the tag `squash`: a hit 0.8 × 1.2 back in 0.25 s
  `easeoutback`, a landing 1.2 × 0.8 in 0.5 s `easeoutelastic`, a jump
  0.7 × 1.3 held 0.2 s, back in 0.75 s `easeoutelastic`. `hit(obj)` gives the
  hit's squash with the flash, as the coin's `Collect` does. A button's press
  is a squash too, held while the finger stays (`count-up-and-press.md`).
- A squash acts on the art: a player is an invisible mask with Platform and
  its art, drawn with `shape(..., oy=1)`, pinned to it. The run stops on a
  squash of an object whose behavior collides.

### The level

- **Unit**: `UNIT`.
- **Module**: the player's reach. `jump_reach()` computes it from
  `PLATFORM` by the approximation above, 286 px or about 8.9 units with the
  template's values; `jump(gap, rise)` says easy, medium or hard and stops
  past nine tenths of it.
- **Camera zone**: one viewport, a shot about one idea: entry, challenge and
  exit in frame, a corner of the next zone showing. A challenge does not
  straddle a zone edge.

### Pacing

`BEATS` gives each zone, or each round, wave or window of time in a
one-screen game, a `beat(type, intensity, mechanics, holds=...)`. `pace()`
stops the run when the first beat is above 0; a beat of 2 or more is not
followed by a rest holding a pickup or a checkpoint, or the climax by the
exit; a mechanic is combined before a `teach` of its own; the climax is
missing or outside the last third; or the last third is not more intense on
average than the first. A toy with no rounds, levels or waves, such as an
effect that follows the pointer, is one beat at 0, and `pace()` checks no
climax or rise for it, because the climax rule would stop every such toy.
`pace()` prints the curve, one line a beat, above `generated; checking`. The
stand-in plays its beats as rounds: `ROUND_COINS` holds each round's coins
and a global `beat` counts them.

## Re-evaluate when

- The reach from the approximation and the reach measured in a preview
  differ by more than one unit.
- Real art arrives, from the user or an image model: the blockout gives
  way, and its grids and pacing stay.
