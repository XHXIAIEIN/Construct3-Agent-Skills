# The Count Draws in Inter's Tabular Digits

Date: 2026-10-31

## Problem

`count_up()` counts a score to its new value in 0.5 s. The count draws in
Inter Display Light, whose digits differ in width: the 1 is 703 units of
2048 and the 4 is 1239. So a centred or right-aligned count changes its
width on almost every tick, and its other digits move. Construct's Text
sets no OpenType feature, so a project cannot turn Inter's tabular figures
(`tnum`) on.

## Evidence

The template's count of 0 to 487 to 999 at 1920 × 1080, slowed to a fifth
and recorded at 60 frames a second, with the Text's width read on every
tick:

| | Proportional digits | Tabular digits |
|--|--|--|
| Widths of a 3-digit count | 96.2 to 145.2 px, 213 values | 154.69 px, one value |
| Width change from one tick to the next, same number of digits | up to 37.7 px; 77% of changes are 1 px or more | 0 |
| Left edge of the ink, 3-digit frames | 30 px of travel | 5 px, the shape of the first digit |

Inter's `tnum` lookup also maps the space, the hyphen, brackets,
punctuation and the math signs to tabular widths, the hyphen from 842 to
1320 units. So only the digits change: the file with tabular digits is
27 408 bytes, 1 204 fewer than the proportional one. The strips, the GIFs
and the measurements are in `.local/docs/evidence/round2-type/`.

## Options

1. **Left-align the count.** The digits before the one that changes stay,
   but the count's right side still moves, and a count in a corner or a
   centre must hang left.
2. **Tabular digits in the font file.** The cmap of
   `InterDisplay-Light.woff` points the digits 0 to 9 at Inter's tabular
   glyphs, so they are the default. Chosen by the owner on 2026-10-31.

## Decision

Option 2. The subset of `InterDisplay-Light.woff` in the user's font cache
is made from a copy of `InterDisplay-Light.ttf` whose digits are mapped
first. This script does the mapping with fontTools:

```python
import sys
from fontTools.ttLib import TTFont
src, dst = sys.argv[1:3]
f = TTFont(src)
gsub = f["GSUB"].table
lookups = {i for r in gsub.FeatureList.FeatureRecord if r.FeatureTag == "tnum" for i in r.Feature.LookupListIndex}
tabular = {}
for i in lookups:
    for st in gsub.LookupList.Lookup[i].SubTable:
        tabular.update(getattr(getattr(st, "ExtSubTable", st), "mapping", {}) or {})
for t in f["cmap"].tables:
    for cp, g in list(t.cmap.items()):
        if 0x30 <= cp <= 0x39 and g in tabular:
            t.cmap[cp] = tabular[g]
f.save(dst)
```

The subset command of `default-look.md` then runs on the mapped file. The
other two weights keep proportional digits.

The template reads the digits' advances from the font file
(`digit_ems()`, the cmap and the horizontal metrics, with the standard
library), so it does not trust the file's name:

- `text_px()` sizes the digits of a label at the number kind's size at
  the font's tabular width, 0.645 em, so the box of `"999"` holds the
  count. Inter Medium's proportional widths, which size every other label,
  are 2% narrower for a 9.
- `check_texts()` warns of a Text that `counting()` counts when it is not
  left-aligned and its font's digits differ in width: a weight other than
  light, a platform face, or a cache file made before this change. The
  warning names the light weight and left alignment as the two ways out
  (`type.counting-digits`).

## Re-evaluate when

- Construct's Text gains a setting for OpenType features: turn on `tnum`
  there and ship the subset unchanged.
- Another weight shows a number that changes live, a timer in regular:
  map its digits too.
- Inter releases a version whose `tnum` lookup moves: check that the
  script still maps ten digits.
