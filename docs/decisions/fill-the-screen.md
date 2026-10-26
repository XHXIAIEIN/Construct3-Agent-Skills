# A Generated Game Fills the Screen, and Its Layers Read in Order

Date: 2026-10-08; the backdrop 2026-10-26
Schema: Construct 3 r495.2

## Problem

A generated game fills the screen at any aspect ratio. A *Letterbox* mode
shows bars on a screen whose shape differs from the viewport's, and a
browser window rarely has the viewport's shape.

Filling the screen has two traps, both in `prompts/pitfalls/`:

- Under *Scale outer* the screen shows more than the viewport on its longer
  side, and a layer at parallax 0 stays centred on the viewport. A HUD
  placed at the viewport's edge then floats inside a wider or taller screen
  (`coordinates-and-angles.md`).
- A backdrop or a popup's dim sized to the viewport leaves strips
  uncovered. The layer's colour shows there, and a tap there misses the
  dim (`input.md`).

A phone with a notch or rounded corners has two edges to fill to: the
physical screen's, or those of the safe area, the rectangle inside it that
is always visible. A HUD held to the physical edge can sit under the notch.

The Layout View draws a layer in the order its file lists the instances.
An order left to placement shows an order no user would choose, and a
label listed before its panel draws under it.

## Evidence

- Most official examples use a *Letterbox* mode, so the examples' habit
  does not decide the default. The examples that use the Anchor behavior
  run under *Scale outer* or *Letterbox scale*. They write *Left edge*
  `window-left` with *Top edge* `window-top` or `window-bottom`, and the
  other two edges `none`.
- The manual: *Left edge* and *Top edge* move an object to keep its
  distance from the viewport edge they name, without resizing it. *Right
  edge* and *Bottom edge* resize it. An anchored object belongs on a layer
  at parallax 0 (`behavior-reference/anchor.md`).
- The manual, *Viewport fit*: on a non-rectangular screen the default
  *Auto* adds borders so that the whole viewport is visible. *Cover* fills
  the physical screen, and a notch or a rounded corner can then hide part
  of the viewport (`project-primitives/projects.md`). Platform Info's
  `SafeAreaInsetLeft`, `Top`, `Right` and `Bottom` give the safe area's
  insets in CSS pixels, 0 on a rectangular screen
  (`plugin-reference/platform-info.md`). The editor's new project,
  `data/c3-new-project/`, writes *Auto*.
- A game generated from the template needed all three: *Scale outer*, an
  anchored hint, and layers sorted by the Y of each object's feet.
- Previews of the stand-in game at 430×932, 1280×720 and 1600×700, and at
  320×180 under *Integer scale outer* (r495.2): every label sat `MARGIN`
  from the screen's edges it hangs on, right and bottom included. The
  backdrop and a dim covered every corner of the screen.
- Previews of the stand-in at 430×932, 1600×700, 2000×500 and 300×1200,
  each again after the camera moved 300 px right and 200 px up
  (2026-10-26): the opaque Background layer's colour filled every corner
  with no backdrop object. A checker Tiled Background laid over the
  viewport on a parallax-0 layer, with Anchor's four edges on the
  viewport's, had the box of that layer's viewport each time, from
  -1200..3120 across at 4:1 to -3300..4380 down at 1:4. Its cells start
  at the screen's left edge, not at the layout's origin: at 2420×1080 the
  layout's x 0 drew 250 px in, and the cell edges at multiples of 16 from
  the screen's edge. A centred origin changed nothing.
- The manual: *Right edge* and *Bottom edge* take only *Viewport right*
  and *Viewport bottom* or *None*, and resize the object
  (`behavior-reference/anchor.md`).

## Options

1. **Keep Letterbox.** Nothing to anchor or cover, but bars on most
   screens.
2. **Scale outer, with each game placing its own HUD for it.** Every
   generated game repeats the two traps until its author meets them.
3. **Scale outer in the template, with the HUD helpers anchoring and the
   backdrop covering by default.** The helpers already know the edge each
   element hangs on. Chosen.

For the backdrop under option 3, the template laid one Tiled Background
`SCREEN_PAD` past the viewport on every side, 9600×8760 at 1920×1080. It
covered every screen, but in the editor it dwarfed the layout, and a
plain one only repeated the opaque layer's colour beneath it. Three ways
cover a one-screen layout instead:

- **The opaque layer's colour** for the plain paper. Nothing to place,
  and it fills any screen and any scroll.
- **Anchor on all four edges** for a pattern, on a layer at parallax 0.
  The object is the viewport's size in the editor and the screen's at
  run time, but its cells follow the screen's edge, so the checker is no
  longer a ruler that lines up with the grid. Chosen.
- **Anchor plus an event that sets the image offset** from the box every
  tick. It keeps the cells on the grid at the cost of an event in every
  game with a checker; the checker marks transparency, as editors draw
  it, so its alignment was not worth the event.

A level larger than the viewport keeps the padded backdrop on a layer at
parallax 1, because it is the floor that scrolls with the camera, and a
parallax-0 backdrop would stand still behind a moving world.

For pixel art, *Integer scale outer* is chosen because every pixel stays
square. The cost is a margin that varies with the screen. *Scale outer*
would fill exactly but scale the pixels unevenly.

For a notch or rounded corners, *Viewport fit* stays *Auto*. The manual
says *Auto* keeps the whole viewport visible, so the HUD that Anchor holds
to the screen's edges is not cut by the notch. The cost is a border beside
the notch. *Cover* would
fill the physical screen, but every edge element would then need an
offset by the safe-area insets, which the helpers do not compute.

## Decision

- `FULLSCREEN` is `scale-outer`, or `integer-scale-outer` when `PIXEL_ART`.
  `build_project()` writes it over the mode an editor-saved project holds.
  A game that wants another mode sets `FULLSCREEN` below the helpers' end
  marker.
- `anchored(where)` gives the Anchor behavior's block for an edge or
  corner. The left edge goes to `window-left` or `window-right`, the top
  edge to `window-top` or `window-bottom`, and a centred axis gets `none`,
  since the viewport stays centred. `hud_text()`, `hud_bar()`,
  `labelled_bar()` and `band_text()` give the block to what they place. An
  instance placed by `anchor()` or `row()` takes it as `behaviors=`.
  `build_all()` gives each type with an anchored instance the behavior, and
  that type's other instances a block that holds nothing (`anchor_types()`).
- `PROPERTY_DEFAULTS` gives `viewportFit` the value `auto`, and
  `build_project()` keeps the value a project already holds, so the edges
  `anchored()` names lie inside the safe area on a screen with a notch or
  rounded corners. A game that
  sets *Cover* in the editor offsets its edge elements by Platform Info's
  `SafeAreaInset` expressions itself. Not verified on a device: no phone
  with a notch or rounded corners has run a generated game, so this rests
  on the manual.
- The plain paper is the colour of the opaque `Background` layer, and no
  object: `pattern(name, "plain")` and `backdrop()` of a plain pattern
  stop the run and say so.
- In a one-screen layout, `backdrop()` lays its pattern over the viewport
  with `STRETCHED`, Anchor's four edges on the viewport's, on a layer at
  parallax 0 under the game's. `anchor_types()` stops the run on an
  enabled Anchor on a layer of any other parallax.
- In a layout larger than the viewport, `backdrop(type, width, height)`
  and `screen_box()` reach `SCREEN_PAD`, twice the viewport's longer
  side, past the layout on every side. This covers a screen up to 4:1 in
  either orientation. A dim is laid out over `screen_box()`. The tap that
  closes a popup is still tested against the panel, as `input.md` says.
- `layout()` turns on *Unbounded scrolling* in a layout of the viewport's
  size. Bounded, the camera keeps the layout's left and top edges on the
  screen's: a preview at 1600×700 showed the stage left of the screen's
  middle, where the HUD is centred. Unbounded, both layers share the
  centre. A larger layout keeps bounded scrolling, and its backdrop covers
  what shows past its edges.
- `build_all()` lists every layer in `z_order()`. The backdrop comes first,
  then the areas of `pattern()`, then the rest by the Y of their feet. A
  child of `link()` follows its parent. A box wholly inside another box
  follows it, unless the outer box is a label: a fill follows its frame.
  Equal keys keep the placement order. A game that draws by another rule,
  such as a 3D layer by depth, defines `z_order()` below the end marker.
- `check_look.py` warns, `screen.fill`, when `project.c3proj` is in a
  *Letterbox* mode. It is a warning, not a finding, because the editor
  accepts the mode and the bars can be a choice.
- `check_look.py` warns, `screen.safe-area`, when *Viewport fit* is
  *Cover* and no event expression or script reads the insets. It is a
  warning, because the editor accepts *Cover* and a game may move its HUD
  by other means. A preview with a notch emulated put the stand-in game's
  top HUD under the notch (`borrowed-numbers.md`, "Safe area and notch").
- `check_look.py` does not flag an edge HUD element without Anchor.
  Position alone does not tell an edge element from a centred one, so the
  check would give false findings.

## Re-evaluate when

- A preview shows an anchored HUD element off its edge, or a backdrop edge
  on screen.
- A game needs the checker's cells on the grid, which takes the image
  offset event.
- A popup's dim, still padded by `SCREEN_PAD`, gets in the way in the
  editor as the backdrop did; it can be stretched the same way.
- A small model's generated game places a HUD element without
  `anchored()`. No eval has run on this change, because it is in the
  helpers' defaults, which a run copies with the template.
- A game needs a HUD element centred on an edge that grows with the screen,
  which needs *Right edge* or *Bottom edge*.
- Users of the skill ask for bars, such as for a game designed to one
  fixed screen shape.
- A phone with a notch or rounded corners shows an anchored HUD element
  cut under *Auto*, or a game needs its art under the notch, which takes
  *Cover* and offsets by the safe-area insets.
