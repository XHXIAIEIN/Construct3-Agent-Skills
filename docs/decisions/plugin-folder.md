# The Plugin Folder Holds Only Its Sources

Date: 2026-10-05, revised 2026-11-01

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

The limit stays at 7,000,000 bytes, because the directory may refuse
anything over 7 MB. `icon.png` is stored as a 256-colour palette PNG with
its alpha, 512 × 512. Quantized by octree
without dithering, it went from 341,644 to 50,187 bytes. No pixel moved by
more than 28 of 255 and the mean was 3.9. The two look the same at full
size, and at 2× the gradient of the nose bands slightly.

The skill's data is not part of this folder. Its scripts read it from a
Construct3-RAG clone (`plugin-reads-the-clones.md`), so what the directory
validates is the skill, its sub-agents and the plugin's own files.

## Options

- The repository root as the plugin: every version waits for a reviewer.
- A plugin branch that CI builds and pushes, followed by the directory:
  main keeps one copy, but a release depends on a workflow that pushes, and
  the plugin can be validated only after that push.
- A committed subfolder that holds the plugin's sources, which a test checks.

## Decision

`plugin/` is the plugin, and it holds its sources only. The skill, the
manifest, the README, the icon, the licence and the sub-agents are edited
in place under `plugin/`, and nothing in it is built. What the plugin does
not need at run time lies beside the folder: the skill's evals under
`dev/evals/`, the maintainers' guide `dev/AGENTS.md`, the tests, the docs
and the records. The marketplace entry's source is `./plugin`, and the link
into `~/.claude/skills/` of `plugin-tracks-commits.md` points at
`<clone>/plugin`.

`dev/scripts/build_plugin.py` sets the version in
`.claude-plugin/plugin.json` as `plugin-tracks-commits.md` describes, and
checks the folder: `--check` fails when the version differs from the one
the build would set, when the plugin's files are more than 512 or more than
7,000,000 bytes in all, hold a binary file other than a PNG or a file over
256 KiB other than an image, or when `plugin/data/` exists.

The folder's own files:

- `bootstrap.py` stays outside, under `scripts/`. It clones the sibling
  repositories, and a script that downloads and runs code holds a version
  for a reviewer. The plugin's scripts print the `git clone` command of a
  missing clone instead.
- The icon goes at the plugin root, because the plugin manifest reference
  ("Manifest file") keeps only `plugin.json` in `.claude-plugin/`.
  `plugin.json` names it in `icon`, which Claude's directory reads for the
  listing and Claude Code ignores. The icon is a flat-vector portrait of
  the maintainer's English bulldog in front of a dark blue tiled wall,
  generated from a photo with a local image model and regenerated region
  by region until the dog's own markings, lids and teeth read at 32 px;
  512 px square. Construct's logo is Scirra's mark and stays out of the
  listing. No text of the plugin writes the icon's path in backticks or a
  code block, which the checklist holds for a reviewer.
- `plugin/README.md` describes the plugin route only, and states what the
  plugin runs and what reaches the network: the checker's reads of each
  clone's upstream and its pulls of the data clones, and the browser that
  the scripts open on the Construct editor and its preview. The checklist's "Prepare for the security scan"
  asks the README to describe everything the plugin runs, sends or fetches.
- `plugin/agents/` holds the sub-agent types Claude Code reads from a
  plugin's folder: `project-worker`, whose tools are the ones the skill's
  scripts need (`project-worker-agent.md`), `art-drawer`, `design-judge`, which only reads the design
  review's brief (`design-judge-agent.md`), and `recording-describer`,
  which only reads a recording's brief and frames (`recording-describer.md`).
- The skill's fonts stay out. The generator takes Inter from the user's
  font cache and draws a missing font in `system-ui`
  (`template-font.md`), so the plugin has no need of them.

The repository has no `.gitattributes` to force LF at checkout: the
directory refuses to validate a repository whose attributes could rewrite
files at checkout, and it refused this one while `* text=auto eol=lf` was
there. A test keeps the file out. The limits and the version read a
committed text file with its CRLF as LF, as Git stores it, so a checkout
with `core.autocrlf` checks the same folder as any other.

The skill names a file of the data as `Construct3-RAG/<path>`, a path in
the Construct3-RAG clone. A test fails when `SKILL.md`, `references/` or the
game-project block names such a path that the clone beside this repository
lacks. Another runs the plugin's scripts from a copy in a temporary plugin
cache: with a Construct3-RAG clone beside it they read the data, and
without one each stops with the command that clones it there.

## Trade-offs

- A file the skill's maintainers need and the plugin does not, such as an
  eval, lives beside the folder and not with the skill, so a script of the
  skill and its eval are two folders apart.
- The checker's clone-behind check (`clone-update-check.md`) looks for
  `.git` in the clone that holds the plugin folder. Run from
  `<clone>/plugin`, it starts at the clone, one folder up, which
  `c3project.clone_root` returns.

## Re-evaluate when

- Re-validation of the folder still reports a hold that this layout should
  remove.
- The directory changes its limits, or states the size limit, which this
  record reads off two scans.
