# The Plugin Folder Holds Its Sources; Only Its Data Is Built

Date: 2026-10-05

## Problem

With the repository root as the plugin folder, the folder that Claude's
directory validates holds the whole repository: the data, the lookup
service, the tests, the docs and the maintainer's `/polish` workflow.
Validation then holds each version for a reviewer on four findings, and each
one comes from a file that a plugin user does not reach through the skill:

- "Files or downloads the validator couldn't inspect": more than 512 files,
  and the two language packs of `data/c3-lang/`, about 2 MiB each.
- "Image or font file that the plugin's code could run": the PNG icons of
  `data/c3-new-project/`, which `scripts/bootstrap.py` copies into a new
  project. The checker, its tests and `checker-rules.md` also name image
  paths of a game project, such as `icons/icon-16.png`; the checklist's rule
  covers images bundled in the plugin, which the icons are and a game
  project's images are not.
- "Uses a credential from the user's machine" and "Contains a download-and-run
  command": `.claude/workflows/polish.js`. The workflow tells its sub-agents
  to fetch documentation pages and to run local commands; it reads no
  credential and runs nothing it fetches.

The directory repeats a hold on each version it picks up, so every release
waits for a reviewer.

## Evidence

Claude's "Plugin pre-submission checklist", "Files in the plugin folder",
holds a version whose plugin folder has more than 512 files, a file other
than an image or a font over 256 KiB, or a script that refers to a bundled
image.

The folder has a size limit too, which the checklist does not state. On
2026-10-14 and 2026-10-15 the directory refused to fetch four commits in a
row with "Files in the repository the scanner won't accept", a message
that names OS metadata files, symbolic links, submodules, special files
and "a plugin folder over the size limit". None of the commits held a file
of the first four kinds. The commit before them, 44b8add, had passed the
scan with 6,908,884 bytes in `plugin/`; the four refused commits held
7,107,992 to 7,199,082. One of them held the skill's three WOFF fonts and
three held none, so the fonts were not the cause. The limit lies between
the two figures, so the build takes it as 7,000,000 bytes.

The skill reads these parts of the repository outside its own folder, by the
paths in its scripts, `SKILL.md`, `references/` and the Construct 3 block:

| Part | Read by | Kept as |
|------|---------|---------|
| `data/c3-schemas/` | every script, and agents directly | its files, a few hundred |
| `data/c3-ts-defs/` except `sdk/` | `lookup_script_api.py`, which skips `sdk/` | one bundle |
| `data/c3-examples/` | `search_guides.py`, `check_design.py` | two bundles per locale, from about a thousand small files |
| `data/c3-example-usage/` | `lookup_ace.py` | one bundle, from about a hundred small files |
| `data/c3-lang/` | `check_project.py`, two subtrees of about 10 KiB; `open_in_editor.py`, `preview_project.py` and agents, the texts of the plugins and behaviors that label a preview's inspector values (`reading-the-runtime.md`) | the two subtrees and those texts, about 100 KiB per locale |
| `data/c3-guides/` | agents, from `SKILL.md` and the block | its files |
| `data/c3-new-project/` | `new_project.py`; `check_project.py` names its `project.c3proj` for a project file without a `properties` block | its files, the icons included |
| `plugin/skills/construct3-agent-plugin/` except `skills-dev/evals/` | | its files |

Copied as they are, these parts come to well over 512 files, most of them
the examples. The schemas fit as files, and agents open them by path, so
they stay as files.

## Options

- The repository root as the plugin: every version waits for a reviewer.
- A plugin branch that CI builds and pushes, followed by the directory:
  main keeps one copy, but a release depends on a workflow that pushes, and
  the plugin can be validated only after that push.
- A committed subfolder that a script builds and a test checks.

## Decision

`plugin/` is the plugin, and the plugin folder holds its sources. The
skill, the rows of the `/` menu, the manifest, the README, the
icon, the licence and the sub-agents are edited in place under `plugin/`.
Only `plugin/data/` is built: `scripts/build_plugin.py` writes it from the
`data/` of the Construct3-RAG clone beside this repository, and the result
is committed. What the plugin does not need at run time lies beside the
folder: the skill's evals under `skills-dev/evals/`, the maintainers' guide
`skills-dev/AGENTS.md`, the tests, the docs and the records. The
marketplace entry's source is `./plugin`, and the link into
`~/.claude/skills/` of `plugin-tracks-commits.md` points at
`<clone>/plugin`.

The build of `plugin/data/`:

- Copies `data/c3-schemas/`, `data/c3-guides/`, `data/c3-new-project/` and
  `data/c3-ts-defs/autocomplete-data.json` to the same paths. The skill's
  scripts find `data/` in the folder above them, and an agent opens a
  schema at the same relative path as in the Construct3-RAG clone. A
  schema is written as the same JSON with an indent of one space instead
  of the source's two, which takes 400 KiB off the folder and changes
  nothing an agent or a script reads.
- Writes `data/c3-ts-defs/` except `sdk/`, each locale of
  `data/c3-examples/`, and `data/c3-example-usage/`, as bundles: JSON
  objects from relative path to file content, each under 256 KiB. One
  loader in `c3project.py` reads a data folder from its files, as in the
  Construct3-RAG clone, and from its bundles, as here. `lookup_script_api.py`,
  `search_guides.py`, `check_design.py` and `lookup_ace.py` read through
  it, so in the plugin the TypeScript definitions, the examples and their
  index are read through those scripts only. A bundled JSON file is
  written without its indent, since only those scripts parse it: on
  2026-10-20 that took 200 KiB off the folder, which had passed
  7,000,000 bytes with `check_sounds.py` and `make_sounds.py`.
- Writes `data/c3-lang/{locale}.json` with the two subtrees that
  `check_project.py` reads. It also keeps the `name`, `properties` and
  `debugger` texts of every plugin and behavior, at the same JSON paths.
  Every key of a preview's inspector values is a path into those texts
  below `text`, such as `behaviors.platform.debugger.vector-x`.
  `open_in_editor.py --state` and a `state` step of `preview_project.py`
  print each value under its text, and `reading-the-runtime.md` sends an
  agent that reads `inspector` itself to the language pack for the label.
- Copies `data/c3-new-project/`, Construct's icons included. A new project
  is made by `new_project.py` of the skill, which copies the empty project
  and gives it its own name and `uniqueId`. The icons are the ones the
  editor's Project > New writes, so a new project looks as one made in the
  editor.
- Sets the version in `.claude-plugin/plugin.json` as
  `plugin-tracks-commits.md` describes, and fails when a script and the
  rows of the `/` menu disagree (`plugin-script-menu.md`).

The folder's own files:

- `bootstrap.py` stays outside, under `scripts/`. It clones the sibling
  repositories beside the folder that holds `data/`, which for an install
  is Claude Code's plugin cache, and a script that downloads and runs code
  holds a version for a reviewer. A plugin user works without the siblings,
  as the skill does wherever they are missing.
- The icon goes at the plugin root, because the plugin manifest reference
  ("Manifest file") keeps only `plugin.json` in `.claude-plugin/`.
  `plugin.json` names it in `icon`, which Claude's directory reads for the
  listing and Claude Code ignores. The icon is a flat-vector portrait of
  the maintainer's English bulldog in front of a dark blue tiled wall,
  generated from a photo with a local image model and regenerated region
  by region until the dog's own markings, lids and teeth read at 32 px;
  512 px square and about 330 KiB. Construct's logo is Scirra's mark and
  stays out of the listing. No text of the plugin writes the icon's path
  in backticks or a code block, which the checklist holds for a reviewer.
- `plugin/README.md` describes the plugin route only, and states what the
  plugin runs and what reaches the network: the checker's fetch of a
  clone, and the browser that the scripts open on the Construct editor and
  its preview. The checklist's "Prepare for the security scan" asks the
  README to describe everything the plugin runs, sends or fetches.
- `plugin/agents/` holds the sub-agent types Claude Code reads from a
  plugin's folder: `project-worker`, whose tools are the ones the skill's
  scripts need (`project-worker-agent.md`).
- The skill's fonts stay out. The generator takes Inter from the user's
  font cache and draws a missing font in `system-ui`
  (`paper-and-ink-look.md`), so the plugin has no need of them, and their
  91 KiB count against the size limit.

Text files under `plugin/data/` are written with LF line endings, as Git
stores them, so a checkout with CRLF files builds the same folder as any
other, and `--check` and the version read a committed text file with its
CRLF as LF. The repository has no `.gitattributes` to force LF at checkout:
the directory refuses to validate a repository whose attributes could
rewrite files at checkout, and it refused this one while
`* text=auto eol=lf` was there. A test keeps the file out.

The skill names a file of the data folder as
`Construct3-RAG/<path>`. A game project resolves it through its
`Construct3-RAG:` line, which a plugin user's project often lacks. So the
plugin bullet of `SKILL.md` says that `Construct3-RAG/` before `data/`
stands for `${CLAUDE_PLUGIN_ROOT}/`, and the skill's text names
no file that the plugin holds only in a bundle. Claude Code replaces that
variable with the plugin's folder in the Markdown body of a skill when it
loads the skill (Claude Code docs, "Plugin manifest reference",
"Environment variables"). It does not replace the variable in a reference
that the agent reads with a file tool, and a Bash command does not get it.
So only `SKILL.md` can carry the variable, and its one sentence also covers
the paths of the references.

The scripts print a file of that folder by its absolute path. A TypeScript
declaration that the plugin holds only in a bundle is printed as the
`lookup_script_api.py` command that prints it.

The folder stays under 512 files and 7,000,000 bytes. A test builds the data
folder into a temporary directory and fails when it differs from
`plugin/data/`, when the plugin's files are more than 512 or more than
7,000,000 bytes in all, hold a binary file other than a PNG or a file over
256 KiB other than an image, name in `icon` a file the folder does not hold,
or lack a file or folder under `data/` that `SKILL.md`,
`references/` or the game-project block names as `Construct3-RAG/<path>`.
Another runs the plugin's scripts with no other clone, and fails when
`search_guides.py` does not print the command that clones Construct3-Cookbook
(`guides-in-cookbook.md`), or when
`lookup_script_api.py` prints a file path instead of a command. The refresh
workflow builds the data folder again from the current data of
Construct3-RAG every day and pushes the build when it changed
(`plugin-repository.md`).

Edit the skill and the plugin's own files under `plugin/`;
never edit `plugin/data/` by hand, because the next build overwrites it and
the test fails until then.

## Trade-offs

- A data refresh is a large diff under `plugin/data/`: the bundles and the
  reindented schemas add a blob on each change.
- A file the skill's maintainers need and the plugin does not, such as an
  eval, lives beside the folder and not with the skill, so a script of the
  skill and its eval are two folders apart.
- In the plugin, the TypeScript definitions and the examples are read
  through their scripts only. The clone keeps them as files.
- The checker's clone-behind check (`clone-update-check.md`) looks for
  `.git` in the clone that holds the plugin folder. `search_guides.py`
  looks for the example projects beside that clone. Run from
  `<clone>/plugin`, both start at the clone, one folder up, which
  `c3project.clone_root` returns.
- The icons are bundled images that `new_project.py` copies, which the
  checklist holds for a reviewer when a script refers to them. The script
  copies the empty project as a folder and names no image file.
- The room under 512 files and under 7,000,000 bytes shrinks with each new
  addon, which adds one schema file per locale, and with each release,
  whose data grows.

## Re-evaluate when

- The plugin folder nears 512 files. The next part to bundle is
  `data/c3-schemas/{locale}/effects/`, the small files of the effects, which
  agents reach through `lookup_ace.py`.
- Re-validation of the built folder still reports a hold that this layout
  should remove. If the icons are the only hold left, the next step is to
  draw placeholder icons in code and bundle no image.
- The plugin folder nears 7,000,000 bytes. The next cuts, in order: the
  bundles' own indent, which saves little; the empty project's
  icons drawn in code, 140 KiB; the schemas without the fields no script
  or agent reads, which needs a survey of what the skill's text and the
  scripts read first.
- The directory changes its limits, or states the size limit, which this
  record reads off two scans.
- A reason appears for the plugin to carry Inter: its 91 KiB fit under
  the limit.
