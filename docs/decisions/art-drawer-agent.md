# The Art of a Generated Game Is Drawn by a Sub-Agent on a Fixed Model

Date: 2026-10-30

## Problem

On the SVG route the game's pictures are drawn in code
(`art-drawn-in-code.md`). The main agent that writes a game may run a small
model, and the card game whose screen showed four drawing styles and
fifteen enemies from one template was drawn by a small model. A drawing
holds a style only when one hand draws every picture with the same kit and
then looks at the result.

## Options

1. **The main agent draws.** Its model is whatever the session runs, and
   its context already holds the sheets and the checks.
2. **A sub-agent type, `construct3:art-drawer`, on a fixed strong model.**
   Its whole task is the brief that `art.py` writes: the pictures with their
   boxes, roles and subjects, the art direction, the kit, and five questions
   to answer on the contact sheet before it returns. Chosen.

## Decision

Option 2. `plugin/agents/art-drawer.md` has the tools a drawing needs (Read,
Write, Edit, Bash), starts without the project's instruction files, and
names its model by its full ID. It changes only `tools/drawings.py`, the
files that script writes under `art/`, and the roles of `PALETTE` that a
subject needs. It stops after three rounds, or once every question is
answered no, and replies with the questions still answered yes.
`art.py` names the type in its last line, and `project-worker` hands the
brief to it as it hands a judge's brief. `pick_look.py` hands it the first
play screen in three looks the same way (`look-picker.md`).

The type runs Opus. Both candidate models drew the trial's card game in
one style (`art-drawn-in-code.md`, "A drawing run measured here"), and the
owner picked Opus from those contact sheets: it ended in two rounds with no
question left as yes, where Sonnet took three and left the three buttons
alike.

## Re-evaluate when

- A newer model is released: draw the same card game again with it and
  compare the contact sheets.
- A drawing run leaves a style of its own on a screen that the look review
  finds: the brief's questions or the kit change, measured on the same
  card game.
