# The Template's Font

Date: 2026-10-14

## Problem

A generated game needs a font that is the same on every machine, and the
project needs to name it in a form the editor and the runtime accept.

## Evidence


A probe project in the editor's preview (r495.2, Chrome on Windows)
showed:

- A font file in `fonts/`, listed under `rootFileFolders.font`, loads by its
  file name without the extension: `Inter-Regular.woff` is the font
  `Inter-Regular`. WOFF and TTF both load; the manual asks for WOFF or
  WOFF2, which work on every platform (`plugin-reference/text.md`).
- Chinese text in a Text whose font is Inter falls back to the platform's
  Chinese face, a sans serif on Windows.
- A Text whose font the project lacks draws its Latin letters in the
  browser's default serif face.
- Each weight is a file and a font of its own: the official examples list
  `RobotoRegular.ttf` and `RobotoBold.ttf` and name each in a Text.
- The Text object has no letter spacing. A space of a quarter em, U+2005,
  between letters tracks a tag in one Text.

## Decision


The generator takes Inter in three weights from the user's font cache: the
folder that `CONSTRUCT3_RAG_FONT_CACHE` names, or else
`~/.cache/construct3-rag/fonts`. The repository and the plugin carry no
font file (`plugin-folder.md`). Inter is released with its SIL
Open Font License 1.1 text, and each weight is a subset of that release:

| File | Weight | Used for |
|------|--------|----------|
| `Inter-Regular.woff` | 400 | body text, names, tags, verbs |
| `Inter-Medium.woff` | 500 | titles, keys, button labels, banners |
| `InterDisplay-Light.woff` | 300 | the count the player plays for, in tabular digits |

Source: Inter 4.1, `https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip`,
sha256 `9883fdd4a49d4fb66bd8177ba6625ef9a64aa45899767dde3d36aa425756b11e`,
the static TTFs of `extras/ttf/`. Each subset holds Basic Latin, Latin-1,
Œ and œ, the spaces, dashes, quotes, bullet, ellipsis, per mille and single
guillemets of General Punctuation, the euro, the trademark, four arrows and
the minus, and keeps the copyright and license entries of the name table:

```bash
python -m fontTools.subset extras/ttf/Inter-Regular.ttf --unicodes="U+0020-007E,U+00A0-00FF,U+0152-0153,U+2002-200A,U+2013-2014,U+2018-201A,U+201C-201E,U+2022,U+2026,U+2030,U+2039-203A,U+20AC,U+2122,U+2190-2193,U+2212" --name-IDs="*" --flavor=woff --output-file=Inter-Regular.woff
```

`InterDisplay-Light.woff` is subset from a copy of its TTF whose digits
are mapped to Inter's tabular figures first, so a count keeps its width
(`tabular-count-digits.md`).

When the game has a Text or a Text input, the template copies each file
that `FONT` names from the font cache into the project's `fonts/`, unless
`fonts/` holds it already, and lists it in
`project.c3proj`. A weight whose file is in neither place draws in
`system-ui`, and the run prints a warning that names the file, because a
Text whose font the project lacks draws its Latin text in a serif face. So
on a machine whose font cache lacks the files, a game takes the look in the
platform's face until its `fonts/` holds the three files. A game with no
text type gets no font file and no warning, because the files would sit
unused in the project and the warning would ask for files it never draws.

Pixel art draws its labels in Sprite Fonts baked from a pixel font
(`pixel-art-sprite-font.md`).

## Re-evaluate when

- A release of Construct changes how a project lists or loads its fonts.
