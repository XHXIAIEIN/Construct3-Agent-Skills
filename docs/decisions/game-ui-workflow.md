# A Panel's Art Is a 9-Patch with Margins Measured on Its Picture

Date: 2026-11-02

## Problem

`guiguiyan930-source/game-ui-design-workflow`, MIT-licensed, is a set of eight
Cursor skills that take a game UI from a planning document to engine JSON: a
page is generated, approved and broken into components, the components are
generated on one sheet, the sheet is cut into PNGs, and reviewed 9-slice
margins go with them into an atlas.

Task: read it against the art and look pipeline of this skill and take what
transfers. Its largest overlap is the one gap that
`art-from-the-image-tool.md` left open: `art()` covers sprites and backdrops,
so on a game with painted art the panels and frames stayed flat drawn images.

## Evidence

### What its pipeline produces

Measured on its main example, `examples/guofeng-card-rpg`, whose sprites its
strict validator passes:

| Step | What it does | Result on the example |
|------|--------------|-----------------------|
| Cut (`split_sprite_sheet.py`) | Alpha or a sampled background colour within a tolerance, one threshold, on any colour | The sheet has no pixel of part alpha. 27.9% of the area inside `primary-button-normal` is holes, where the white jade came within the tolerance of a white background |
| 9-slice | The agent writes the margins, and the validator checks that they sum to less than the side | `[48, 48, 36, 36]` on that button cuts through its side gems, and leaves the ornaments at the middle of its top and bottom edge in the stretched band, so a wider button smears them |
| Sheet | Nine subjects asked for on one picture, with state order and no text | All nine came out whole, none repeated or dropped, and the three states of the button share their outline. This is one picture |

Its other example sheet, `factory-v2-shop`, is flat vector shapes, so it does
not test a cut. Its roadmap lists finding margins from pixels as not built.

### What a pixel test finds

A 9-patch stretches one band of a side, so a band is usable when its columns
all look alike. Four kinds of panel were tried: the ornamented button above in
its three states, flat shapes, seven painted panels cropped from a reference
board and enlarged three times, and a straight frame with a gem on the middle of
its rim:

| Test | Ornamented buttons | Gem on the rim | Painted panels taken | Flat shapes |
|------|--------------------|----------------|----------------------|-------------|
| Column against its neighbour, strict (blur 1, 12 levels, 97%) | refused | refused | 1 of 7 | taken |
| Column against its neighbour, loose (blur 2, 16 levels, 95%) | refused | taken | 6 of 7 | taken |
| Column against the median of the side's middle half (blur 2, 32 levels, 90%) | refused | refused | 5 of 7 | taken |

A neighbour test misses an ornament with a soft edge, because each column
differs little from the next. The median test finds it. The two painted panels
it refuses are frames cropped at about 44 px wide before enlargement. On the
flat button it finds a left margin of 40 px, where the
corner ends 41 px in; the 36 px of the example's reviewed margins leave part of
the corner in the band.

## Options

1. **Copy the splitter and the sheet route.** Rejected for the cut: the flat
   key of `prepare_art.py` exists because a colour tolerance eats a subject's
   own colours, and the holes above are that failure. The sheet stays a
   re-evaluation case of `art-from-the-image-tool.md`, because no game here has
   shown drift, and one good sheet is one picture.
2. **Margins written by the agent, with the arithmetic checked.** Rejected: the
   example shows that this passes a button that a 9-patch ruins.
3. **`art_panel()` and margins measured on the picture.** Chosen.

## Decision

Option 3.

- `art_panel(name, w, h, role, subject)` asks for a picture on the image route
  and keeps a 16x16 stand-in until it is there, on either route. `panel_type()`
  and `panel_inst()` place it as a 9-patch at any size.
- The prompt asks for ornaments only in the four corners and the middle of every
  side bare, so that the first picture is one the test can take.
- `prepare_art.py` cuts it as it cuts a sprite, trims it and fits it into its box
  at its own shape. `stretch_band()` runs the median test above on each side. It
  looks at the outer quarters across the band only, because a frame's ornaments
  lie there and a painted inside does not. The margins go to
  `art/<name>.margins.json`.
- A picture without a band through the side's middle is refused with the
  sentence for the image tool, and counts toward the three refusals, after which
  it keeps its stand-in.
- The contact sheet shows a panel through CSS `border-image` at its box and
  again wider and lower, so that a reader sees it stretched.

What else was read, and why it changes nothing here:

| Its part | What this skill does | Change |
|----------|----------------------|--------|
| Planning documents and approval gates before any image | `tools/design.json` and `check_design.py` before a build; `art.py` prints one next step, so no picture comes before what it depends on | None: a gate that runs is stronger than a status field |
| `style-contract.yaml` shared by every prompt | `ART_STYLE` leads every prompt, and `--list` warns of each dimension it leaves open | None: the dimensions stay until a run shows drift in another |
| Marking assets `stale` when the style changes | A fingerprint of the prompt and the reference puts a picture in `restyle` by itself | None: this needs no one to write a status |
| One approved page, then components from it | `pick_look.py` picks a first play screen, and `art/look.png` is every sprite's reference | None |
| `pending-generation` instead of a fake picture | The stand-in shows until a picture exists | None |
| Screen map by player journey, no screen without an entry or an exit | The template's title and result screens; the checker has no such rule | None: a first count of layouts that no event enters over the official examples was mostly real play layouts and object stores, so it needs a better method before it can be a finding |
| Semantic names, atlas, engine JSON | Construct 3 packs its own sprite sheets on export, and the project's names are the objects' | None: not for Construct 3 |

## Open

- No picture of an image model went through `art_panel()`: a Claude Code session
  has no image tool. The test ran on the example's sprites, on enlarged crops
  from a board, and on a drawn panel in a real preview at three sizes.
- A band that a side's shading crosses, such as a gradient along a long edge, may
  be refused. None of the panels above has one.
- `art_panel()` covers panels. A bar's frame and fill keep `bar_images()`, and a
  Tiled Background keeps its drawn tile.
- The default look has no panels (`pause-menu.md`), so this serves a look the
  user gave.

## Re-evaluate when

- A real picture with bare sides is refused, or one that smears is taken: put it
  with the real-picture test and change the `BAND_*` values in `prepare_art.py`.
- Panels keep their stand-in after three refusals on most runs: the prompt's
  sentence on ornaments does not hold, so offer a panel without ornaments.
- A game shows the states of one control drifting apart: the sheet route of
  `art-from-the-image-tool.md`, with `prepare_art.py`'s cut, not a colour tolerance.
