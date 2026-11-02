# Pictures Are Cut Out and Fitted to the Box

Date: 2026-10-06
Schema: Construct 3 r495.2

## Problem

A game can take pictures that the user gives or that an image tool makes.
Before Construct can use one, it needs the background removed when the picture
is opaque, the subject trimmed and fitted to the box the layouts place, the
editor's file names, a hit frame, and a clear pixel holding no colour. Left to
the agent, each run writes its own chroma key, the step a small model gets
wrong: fringes, holes, a ground shadow.

## Evidence

The cut-out was measured on eight real image-model pictures, one figure
each on magenta or green: two full-body illustrations, two in pixel art,
four small stills. Counted are the shown pixels within 3 px of a clear one
that lean to the key by more than 40 (the lowest keyed channel less the
highest other one):

| Picture | Alpha ramp on the distance from the key | Alpha from the lean to the key |
|---------|-----------------------------------------|--------------------------------|
| Illustration, green key | 255 | 0 |
| Illustration, magenta key | 116 | 1 |
| Pixel art, green and magenta | 4, 0 | 0, 0 |
| Four stills | 12 to 73 | 0 |

A ramp on the RGB distance from the key leaves half a blend of the key with a colour
far from it opaque and tinted, pink along green hair. Three ways of finding
a blend's alpha were compared on a figure whose matte is known:

| Method | Mean alpha error (levels) | Pixels off colour by over 40 |
|--------|---------------------------|------------------------------|
| Lean to the key | 0.33 | 2 |
| Tint score, the mean of the keyed channels less the others | 0.78 | 92 |
| Projection onto the subject's colour | 0.83 | 4 |

The lean is linear in the blend and leaves red under magenta and gold under
green opaque; the tint score calls red magenta and yellow green. The
projection also took more of the real pictures' edges.

Between strands of hair the key shows in shade, 66 to 89 from the edge's
colour, and does not join the background. The gap distance of 70 clears it
on the green illustration; 50 left it, and 90 cut into the subject of the
magenta illustration and into the edge of a green heart under green, 92
away. A hot-pink heart under magenta is 94 away. The edge's depth follows
the picture's size: at 1.4 and 2 times the size of the real pictures, 3 px
left key on the edge that 4 and 5 px cleared.

On white, a cut also erases the subject's whites. LANCZOS makes pixels in
colours the source never had: a light rim and a key tint.

## Options

1. **Leave the cut-out and fitting to the agent.** The faults above.
2. **`art()` in the template and `prepare_art.py` in the skill.** Chosen.
3. **The skill calls an image model.** Every client has its own tool, and
   the default path calls no model; rejected.

## Decision

Option 2.

- `art(file, kind, w, h, role, subject)` in `assets/build_project.py`
  declares a sprite by what its picture shows, in a box. It draws the stand-in
  `shape()` until `art/<file>` exists, then copies that picture in with the
  stand-in's box, origin and collision polygon: the layouts and events stay as
  they were. Kind `"scene"` is an opaque backdrop. The generator writes
  `art/wanted.json` and prints how many sprites still show their stand-in.
- `scripts/art.py`, the entry point of both routes (`art-entry-point.md`),
  fits each picture saved as `art/raw/<name>.png`, `.jpg` or `.webp` through
  `prepare_art.py`. The repository writes no prompt for an image tool
  (`mechanical-checks-only.md`).
- `scripts/prepare_art.py` keeps a picture's own transparency. Otherwise it
  refuses a picture whose edge is not one flat colour, is neither key, or
  is crossed by the subject, saying what it needs instead. It removes the
  key where it joins the edge, with a shadow cast on it (the key darker),
  and the key in shade wherever it shows through a gap. Each edge pixel,
  up to 3 px in from the background, or a pixel per 240 px of the
  picture's long side when that is more, is a blend of the background and
  the subject behind it. Its alpha is how far its lean lies below the
  background's, as a share of the gap between the background's lean and
  the subject's. Its colour is the pixel less its share of the
  background, divided by that alpha. Key light inside the
  subject gets the colour around it back. It refuses a cut that leaves
  more than 0.5% of the edge leaning to the key.
  Then it trims the subject, fits it into its box (on the box's bottom
  when the origin is at the feet) with alpha and colour scaled apart
  through a filter without negative lobes, clears the colour under alpha
  0, and writes the hit frame, the silhouette in the flash colour. It
  marks each file so that `check_project.py` lets its soft edges through.
  Its line counts the gap pixels and the recoloured ones.
- A refused picture is recorded in `art/refused.json` by a fingerprint of
  its bytes, so that a second run on it does not count it again. After three
  refusals a picture keeps its stand-in, and the run says so, counts it
  and goes on. A new subject in `art()` starts the count again.
- A raw picture is turned upright by its EXIF orientation tag before it is
  cut, because a phone or a camera can save a picture unturned and record
  the turn in the tag.

## Open

- The real pictures behind the thresholds were not made in a session of this
  skill: the full-body ones are reduced to about half their size and to a
  palette, the stills to an eighth. They stay out of
  the repository: `dev/tests/test_skill_prepare_art.py` runs on such a folder
  when `CONSTRUCT3_RAG_ART_PICTURES` names it, and on a known-truth figure
  always.
- A pixel that blends three colours, a strand over a shirt on the key, is
  unmixed as two and can take a wrong tint at part alpha. It shows where a
  palette rounds the blend.
- Pixel art: a picture is resampled and its alpha cut at half, not redrawn
  on the pixel grid.
- Tiled Backgrounds, 9-patches and the HUD's bars keep their drawn
  images; `art()` covers sprites and backdrops.
- The cap of three refusals is a choice.

## Re-evaluate when

- A real picture is refused for its edge, or leaves a fringe, a hole, a shadow
  or a tint: put it in the folder of the real-picture test and change the
  thresholds in `prepare_art.py`, whose comments give what each was measured
  against.
- A subject in the key made darker, a dark magenta cloth under magenta,
  is taken for a gap. Then the gap rule needs the region's size or its
  link to the background.
- A picture keeps its stand-in after three refusals that a fourth picture
  would have fixed: the cap needs that run's evidence.
