# The User's References Are Measured and Shown Beside the Game's Screens

Date: 2026-10-30

## Problem

When the user gives a game's look by reference pictures, the agent read the
pictures once, wrote `USER_LOOK` and had three directions drawn
(`look-picker.md`). After that, nothing compared the built game with the
references. The look review judged each screenshot alone, so a game that
drifted from the user's look passed it. The colours of the directions came
from the art agent's reading of the pictures, not from a measurement.

## Evidence

- A published workflow rebuilds a generated gameplay video as a browser
  game (lovisdotio/video-to-game, MIT). Its first games were playable and
  looked nothing like their videos. They matched once the look was a spec
  with measurements: a palette measured from the frames, and a video frame
  beside the game at the same spots after every change. It takes a colour
  from a frame, not from a word such as "golden".
- On a generated game, the Haiku judge with the pair picture answers
  question 8 yes for a dark deep-sea reference beside the game's cream
  screen, naming the colours, the light and the rendering. It answers yes
  for the game's own picked look beside its stand-ins, naming the missing
  outlines and shadow, and no for a crop of the game's own screenshot. A
  judge also named the layout as a difference until the question said that
  other objects, layout or text are none. The briefs, pairs and replies are
  in `.local/docs/evidence/look-judge/reference-pairs/`.
- Eval case `look-from-references` asks the agent to give the coins game the
  look of two reference pictures. In iteration 88 both the previous skill and
  this one pass every graded assertion, two runs each: what shows behind the
  game is mostly the references' plum, and the coin is their amber with an ink
  edge. This skill's runs take the measured colours exactly and have the
  screen judged beside the references, where the previous runs name the
  colours in words.

## Options

1. **Measure only.** Print the references' colours and leave the comparison
   to the agent, which reads its own screens by what it meant to build.
2. **A mechanical colour distance.** Fail a screen whose colours lie too far
   from the references'. No measurement here sets the threshold, and colour
   is one dimension of six.
3. **A pair picture under the look judge.** The references beside each
   screenshot, the measured colours under each side, and one more question
   for the judge that has not seen the project. Chosen.

## Decision

Option 3, manifest rule `look.references`.

- The user's references are PNG, JPEG or WebP files in `art/references/` of
  the project. The headless browser that renders the art decodes them, so
  no image library is needed. A page embeds them as data URLs, because a
  `file:` picture taints the canvas that measures it.
- The colours are counted on the picture scaled to 96 px on its long side,
  3 bits per channel, the 8 commonest with their shares. Fewer bits split
  one painted gradient into many near shades.
- `pick_look.py` names the references in the draw brief, with the colours
  measured from each, and asks the art agent to take the colours of the
  two directions from the user's look from them.
- `review_look.py` writes `<layout>@reference.png` beside each screenshot
  that has references: the references on the left, the screenshot on the
  right, each fitted into a box of the screenshot's shape. A reference whose
  file name is a layout's name goes with that layout. Every other reference
  goes with the layout the game starts on, the screen `pick_look.py` draws.
  It prints the colours of both sides, names the pair in the brief and asks
  question 8, an ugly yes. In a generated game whose `USER_LOOK` is empty,
  the user picked paper and ink over the references, so the script makes no
  pair and says why.
- A yes to question 8 is marked new or before like any other
  (`look-blocks-only-what-the-change-brought.md`), so a change that leaves
  the drift as it was fails nothing.

## Re-evaluate when

- A case tells the arms apart: references whose look an agent misreads by
  eye, or a later change that drifts from a look already set.

- A judge answers question 8 yes for a difference in objects, layout or
  text, or no beside a reference in a plainly other look: the question needs
  labelled screens, as the other questions have (`look-judge-calibration.md`).
- Users give references of one screen per layout often enough that the
  pairing by file name is not enough.
- A game is paired with a reference of a scene it reaches only in play: the
  pair needs a screenshot from `preview_project.py`.
