# The Generator Removes the Files It No Longer Writes

Date: 2026-10-31

## Problem

`assets/build_project.py` writes every file of a game again on each run and
records their digests in `tools/generated.json`. It never removed a file
that the last run wrote and this run did not. A generator that stopped
making a type, for example one that no longer calls `fade_to()`, so that
`add_fade()` adds no `Fade` type, left `objectTypes/Fade.json` behind. The
run writes `project.c3proj` without the type, so the editor ignores the file
and `check_project.py` warns that `project.c3proj` does not list it. The
same holds for a family, a layout, an event sheet and an image.

## Options

1. Leave the files. Every such change ends with a warning that the agent
   clears by deleting files by hand, and an agent that does not know the
   cause may write the type back instead.
2. Remove each file that the last run recorded and this run did not write.
   A file under `files/` or `fonts/` stays listed in `project.c3proj`,
   because a run keeps the entries it did not write there, so removing it
   leaves a listed file missing, which the editor refuses to open.
   `copy_fonts()` also leaves a font that is already in `fonts/` unwritten,
   so the next run would remove a font that it still uses.
3. Remove such a file only under `objectTypes/`, `families/`, `layouts/`,
   `eventSheets/` and `images/`, the folders that only the run's own
   `project.c3proj` lists and the run's own types point into.

## Decision

Option 3. After a complete run, the generator removes each file in those
folders that the last run's `tools/generated.json` lists, that this run did
not write, and whose digest is still the recorded one, and prints
`removed <path>: the last run wrote it, and this run did not` for each. A
file changed since the last run stops the run before it writes, as before;
under `--replace-edited` such a file stays. A run that stopped part way
removes nothing, because it did not reach every file it would write. The
helpers' `REMOVABLE` names the folders.

## Re-evaluate when

- A run removes a file that the game still uses: the writer of that file
  does not call `wrote()` on every run.
- A game drops a data file or a font and the agent has to clear it by hand:
  remove it from `files/` or `fonts/` together with its entry in
  `project.c3proj`.
