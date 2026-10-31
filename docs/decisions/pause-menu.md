# The Pause Menu Is a Column of Rows Over a Paper Veil, Without a Panel

Date: 2026-11-01
Schema: Construct 3 r506.3

## Problem

The template had `popup()`, which opened a panel over a dim, and no pause
menu. A panel on a dim is a card, which `avoid.dashboard` names as an app's
look. A game made from the template also had no way to stop the game's
time, and nothing that a key, a gamepad, a pointer and a finger could all
steer.

## Evidence

### The mockups

Mockups of the stand-in game at 1920 × 1080, drawn from the template's
values, put three layouts side by side: A, the menu on the screen itself
over a veil; B, a card of the menu on a dim; C, a band across the middle of
the screen. Five rounds of A followed. The mockups and their renders are in
`.local/docs/evidence/pause-menu/mockups/`.

- The owner picked A and asked to drop the key labels beside the rows and
  to set the rows' heights again. A label of a key beside each row named
  three inputs on a menu that a finger uses as often.
- The owner rejected a sky-blue hover and asked for black. A round that
  filled the second row in grey at rest was read as that row being
  hovered, so a grey fill cannot mark a secondary row: the only fill a row
  shows is the ink of the current row.
- B is a card on a dim, which `avoid.dashboard` rules out. C is a band of
  the full width, which a portrait screen has no room for beside the HUD.

### The stand-in game in a preview

The stand-in game was built with the pause menu and played in the editor's
preview, with every input driven by a plan (`plan-pause.json` and
`plan-pause2.json` in the evidence folder).

- Esc opened the menu with the time scale at 0, the playfield not
  interactive and Resume current. Down made Restart current, the pointer
  over the third row made Quit current, and Down from the bottom row made
  Resume current again.
- Sampled on real time, since the recorder runs on game time, which stops
  at time scale 0: the menu's layer went from opacity 0 and scale 0.95 to 1
  and 1, and the veil from 0 to 0.92, in about 180 ms, and back the same way
  on a close, after which both layers were hidden (`motion-samples.json`).
- A coin moved out from under the rows and tapped through the veil stayed
  uncollected. Restart restarted the round, and Quit to title started the
  run again from round 1.
- Restart layout kept the layers' visibility, opacity and interactivity
  from before it: after a Restart, the menu stayed drawn over the game and
  the coins took no touch. The layout's start now closes the menu at once.
  `Construct3-Cookbook/guides/plugins/system.md` records this pitfall.
- A pause during the first 0.3 s of a layout froze the fade cover over the
  screen, because the cover tweened on game time.

`review_look.py` on a copy of the game that opens the menu as it starts
found only the template's two optical warnings on the row of keys, and the
reviewer answered no to all seven questions (`review-paused-1920.png`,
`review-reply.md`). The screenshots before and after the change are
`before.png` and `after-*.png`.

## Options

1. **A panel on a dim.** The old `popup()`. It is option B, a card.
2. **A band across the screen.** Option C. It does not fit a portrait
   screen.
3. **Rows on the screen over a paper veil.** Option A, chosen by the owner
   on 2026-11-01.

## Decision

Option 3 (`menu.pause`). `popup()` now opens a layer, not a panel, and
the panel and dim path is gone, so the template has one way to open a
popup:

- `popup_layer()` makes the popup's layer and its veil, both of parallax
  0, hidden, at opacity 0 and not interactive. The veil is opaque canvas at
  `POPUP["veil"]`, 92 %, between the playfield and the HUD, so the round and
  the score stay readable. The menu's layer sits above the HUD.
- `popup()` runs a value tween on a manager object in the popup class,
  `easeoutquint` in 0.2 s. `popup_events()` draws the layer at that opacity
  and from `POPUP["scale"]`, 0.95, to its size, and the veil at that share
  of 92 %. A close runs the same way back and then hides both layers.
- `pause_menu()` sets the title "Paused" by `hud_header()`, on the HUD's
  top margin, and a column of rows on the vertical centre line, each
  `TOUCH` high and `PAUSE["cols"]`, 14, units wide, a unit apart, centred
  and snapped to the grid. In pixel art at 640 × 360, 14 units are 112 px
  and "Quit to title" needs 128 px at the title's size, so `pause_width()`
  widens the rows to the whole units the longest label needs. Each row is its own tap target, labelled at the
  title's size and weight. At rest a row is outlined in ink, `LINE` wide,
  with an ink label. The quiet row, which leaves the game, has no outline
  and a dim label. The current row is filled in ink with a canvas label.
- `pause_events()` stops the game's time, keeps the rows' and the
  manager's tweens on, and turns the playfield's layers off for touches.
  Esc, P or the gamepad's Start opens and closes the menu, and the gamepad's
  B closes it. Up, Down and the d-pad move the current row and wrap. The
  pointer makes the row under it current once it moves, so a pointer that
  stays put keeps Resume current as the menu opens. Enter, Space or A runs
  the current row, and a tap runs its row through `press()`. The highlight
  comes from the current row's id every tick, as
  `Construct3-Cookbook/guides/recipes/menus.md` says. `POINTER_STYLE` is
  unchanged: the current row is the hover.
- The stand-in game has no title screen, so its Quit to title starts the
  run again from round 1. A game with a title layout fades to it.
- `add_fade()` runs its cover on real time, as the wait of `fade_to()`
  already did.

`test_template_pauses_over_a_veil_with_a_column_of_rows` keeps the layers,
the rows' size, spacing and looks, the labels and the events of the
stand-in game, and
`test_template_opens_a_popup_from_near_its_size_and_closes_it_the_way_it_came`
keeps the popup's actions.

## Re-evaluate when

- A game needs a pause on a touch screen without keys or a gamepad: the
  stand-in has no pause button, so a finger cannot open the menu.
- A Construct release resets a layer's state on Restart layout: the close
  on the layout's start can go.
