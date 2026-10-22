# The Skill, the Prompts and the Plugin Live in This Repository

Date: 2026-10-16

## Problem

The skill, the prompts and the plugin's sources lived in Construct3-RAG,
beside the data pipeline, the lookup service and their tests, and `plugin/`
was built and committed there. A workflow mirrored the built folder into
this repository after each push, so this repository was a copy with a
README. A person who looked the plugin up landed in the repository of the
data pipeline. A change to the skill was made in one repository and shipped
from another. A mirror falls behind whenever its workflow does not run.

The owner decided that the sources should live with the plugin, and that
Construct3-RAG should keep the data, its pipeline and the service, and
point agents here as it points at the Construct3-Manual clone.

## Evidence

- Most of the tests in Construct3-RAG tested the skill, the prompts, the
  build or the publish, and none of them imported the service. The build
  imported one tuple from it, the two locales, which the data's index also
  states.
- The skill's scripts find the folder that holds `data/` and `prompts/`
  through `--rag`, `CONSTRUCT3_RAG`, the `Construct3-RAG:` line of the
  project's instruction file, or their own location. Every install and
  link runs them from `plugin/`, which holds both. The sources' folder
  holds the prompts and not the data.
- The data changes with each Construct release and is a small part of
  Construct3-RAG's clone, most of which is history. The skill already
  finds the example and manual clones beside the clone that holds it
  (`siblings_folder` in `c3project.py`).
- The directory needs a self-contained plugin folder (`plugin-folder.md`),
  so the data stays committed in `plugin/`.

## Options

Where the build gets `data/`:

- A Construct3-RAG clone beside this repository, as the skill finds the
  other clones. The build and the tests need the clone. A release is the
  committed `plugin/`, which is reproducible by being committed.
- A Git submodule of Construct3-RAG. A pinned commit, but every checkout
  carries that repository's history, and a data refresh is a submodule
  bump plus a build.
- A copy of `data/` committed here. Two copies that change together, and
  a refresh that someone must run in two repositories.

How a data refresh reaches `plugin/`:

- A `repository_dispatch` from Construct3-RAG's update workflow. It needs
  a token with write access to this repository stored there, one more
  secret to rotate.
- A scheduled workflow here that clones Construct3-RAG, builds, tests and
  pushes when `plugin/` changed. It needs no secret but its own
  `GITHUB_TOKEN`, and a refresh reaches the plugin within a day.

The plugin's name: `construct3`, or `construct3-agent-skills` to match the
repository. A rename changes the skill id `construct3:construct3-agent-plugin`,
which the game-project block, every installed copy, `SKILL.md` and the
directory submission carry.

## Decision

The sources live here, the build reads the data from a Construct3-RAG clone
beside this repository, a scheduled workflow refreshes the build, and the
plugin keeps its name.

- `plugin/` holds the sources: the skill under `plugin/skills/`, the
  manifest, the README, the icon and
  the sub-agents (`plugin-folder.md`). Only `plugin/data/` is built:
  `dev/scripts/build_plugin.py` writes it from the `data/` of the
  Construct3-RAG clone beside this repository; `--rag` or
  `CONSTRUCT3_RAG_DATA` names another clone. The build takes the files Git
  tracks in that clone, and `dev/tests/test_plugin_folder.py` keeps
  `plugin/data/` equal to a fresh build. The version logic of
  `plugin-tracks-commits.md` reads this repository's `origin/main`, and the
  committed version is its floor, so that no install goes back. What the
  plugin does not ship, the evals and the maintainers' guide, lies under
  `dev/`, because the directory holds the folder to 512 files and
  7,000,000 bytes.
- The tests give the scripts `plugin/` as the clone, because that is the
  folder every install and link runs them from, and read raw data files
  from the sibling clone's `data/`.
- `clone_root` in `c3project.py` treats the `plugin/` folder of a Git
  clone as that clone's. The sibling clones are looked for beside this
  repository, and the update check (`clone-update-check.md`) compares this
  repository with its upstream.
- `.github/workflows/refresh-plugin.yml` runs every day at 12:00 UTC, two
  hours after Construct3-RAG's weekly refresh, and by hand. It clones
  Construct3-RAG and builds. When `plugin/` changed, it runs the checks
  and pushes the build to `main`, with the data's commit in the message.
  `.github/workflows/checks.yml` runs the checks on every push and pull
  request, with the clone beside the checkout.
- The plugin is `construct3` (`skill-and-plugin-names.md`), and the
  marketplace is `construct3-agent-skills`.
- In the skill's text, `Construct3-RAG/` before `data/` names the folder
  that holds it, and the block's line is
  `Construct3-RAG:`, because installed blocks, their stamps and the plugin
  bullet of `SKILL.md` carry the name. For an install from this repository
  that folder is `plugin/`.
- Construct3-RAG keeps `data/`, `src/`, the update pipeline and the docs of
  those. Its instruction files name this repository, and its `README.md`,
  `README_CN.md` and `AGENTS.md` send an agent here for the skill, the
  prompts and the plugin (`skill-in-agent-skills.md` there).

## Trade-offs

- The skill's evals are two folders away from the scripts they test.
- The build and the tests need a second clone. On a machine without it
  the build stops and names the clone command; in CI the workflows clone
  it shallow.
- A data refresh reaches `plugin/` a day late at most, and only when the
  checks pass on the refreshed build. A refresh that fails the checks
  waits for a person, who sees the workflow's run.
- The history of the skill before the move is in Construct3-RAG's Git
  history; the files arrived here in one commit.
- The clone's `plugin/` and the directory's copy duplicate the data of
  Construct3-RAG; `plugin-folder.md` accepts that.

## Re-evaluate when

- A data refresh must reach the plugin within hours: add a
  `repository_dispatch` from Construct3-RAG's update workflow, with a
  token stored there.
- No user runs the scripts against a raw `data/` folder: the loader of
  `c3project.py` that reads a data folder from its files, and the printing
  of file paths instead of lookup commands, can go.
