# A game project's scratch goes in `.tmp/` by use, its products in `.build/`

Date: 2026-10-28

## Problem

The scripts write two kinds of file into a game project: scratch that only an
agent reads again, and products handed to people.

Products first. `pack_project.py` wrote its `.c3p` to `.tmp/<folder>.c3p`
and `export_project.py` its export to `.tmp/export-web`, among screenshots,
recordings and browser profiles. A generating agent did not take `.tmp/` for
the place of a deliverable, passed `--out` with a file name in the project
root, and the 1.3 MB `.c3p` was committed in the game's repository.

Then the scratch. Every script wrote into `.tmp/` flat, each by a scheme of
its own: a result beside a folder of another name (`open-in-editor.json`
with `shots/`, `preview-project.json` with `preview/`, `play-design.json`
with `design/`), browser profiles beside them, and the `.c3p` handed to the
editor in three places, one of them inside the browser profile. An agent
looking for what a script left could not tell from the names, nor delete one
script's leftovers without reading the others'. Opening `.build/<folder>.c3p`
in the editor took `.build/` for the project and wrote a whole `.tmp/`,
browser profile included, inside `.build/`. With no place named for a
recording or a picture meant for the user, an agent put its `.mp4` files and
a comparison picture loose in `.build/`.

## Options

- Keep `.tmp/` flat and say in the docs that products go there: the folder's
  name says scratch, and an agent that wants to keep a file moves it out.
- Refuse an `--out` inside the project: it breaks a user who wants the file
  there on purpose.
- A folder for products, ignored like `.tmp/`, a note when `--out` lands
  elsewhere in the project, and `.tmp/` divided by use, one folder per
  script.

## Decision

The third.

`.tmp/` holds, by use:

- `scripts/<script>/`, what one script writes: its `result.json`, its
  screenshots and recordings in `shots/`, and the `.c3p` it hands the
  editor. The folder is named after the script, `check-project` for
  `check_project.py`, so the folder says which script wrote it.
  `c3project.script_folder` gives it; `RECORD` and `VERIFY_RECORD` are the
  checker's and `verify_change.py`'s `result.json`.
- `browsers/<use>-<browser>/`, the profiles that several scripts share and
  that keep a sign-in between runs: `editor-msedge` for the editor and its
  preview, `export-msedge` for the export, the latter in the main clone so
  that every worktree exports in the same window.
- `drafts/`, the plans and notes an agent writes itself, which the help
  examples use.

`.build/` holds what is handed to people, each kind in a fixed place: the
packed `<folder>.c3p`, the export in `web/`, the sheet pictures in `sheets/`
(`sheet-screenshot.md`), and in `media/` a recording or picture an agent
copies out of `.tmp/` for the user. Each script writes a `.gitignore` of `*`
into the folder it makes, so both are ignored without a line in the
project's `.gitignore`; `references/generating-a-project.md` names them in
its gitignore block as well.

A folder inside a project's `.build/` or `.tmp/`, such as the folder of a
packed `.c3p`, keeps its scratch in that project's `.tmp/`
(`c3project.project_folder`). The search upward stops at the first folder
that holds `project.c3proj`, so a test project that lives in another
repository's `.tmp/` keeps its scratch in its own `.tmp/`, where
`verify_change.py` reads it. A pack leaves both folders out, and
`open_in_editor.py` skips them when it searches a folder for projects. An
`--out` inside the project but outside both is written, with a note on
stdout that Git commits it.

A project's records from before the change stay where they were and are not
read: the fix loop of the checker and the steps of `verify_change.py` start
again once.

## Re-evaluate when

A product is still committed from a project root, a file lands in `.tmp/`
outside these three folders, or a client or engine convention claims
`.build/` for something else.
