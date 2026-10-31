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
- The skill's scripts find the data through `--rag`, `CONSTRUCT3_RAG`,
  the `Construct3-RAG:` line of the project's instruction file, or a
  clone beside their own.
- The data changes with each Construct release and is a small part of
  Construct3-RAG's clone, most of which is history. The skill already
  finds the example and manual clones beside the clone that holds it
  (`siblings_folder` in `c3project.py`).

## Options

Where the scripts and the tests get `data/`:

- A Construct3-RAG clone beside this repository, as the skill finds the
  other clones.
- A Git submodule of Construct3-RAG. A pinned commit, but every checkout
  carries that repository's history, and a data refresh is a submodule
  bump.
- A copy of `data/` committed here. Two copies that change together, and
  a refresh that someone must run in two repositories.

The plugin's name: `construct3`, or `construct3-agent-skills` to match the
repository. A rename changes the skill id `construct3:construct3-agent-plugin`,
which the game-project block, every installed copy, `SKILL.md` and the
directory submission carry.

## Decision

The sources live here, the scripts read the data from a Construct3-RAG
clone beside this repository (`plugin-reads-the-clones.md`), and the plugin
keeps its name.

- `plugin/` holds the sources: the skill under `plugin/skills/`, the
  manifest, the README, the icon and the sub-agents (`plugin-folder.md`).
  The version logic of `plugin-tracks-commits.md` reads this repository's
  `origin/main`, and the committed version is its floor, so that no
  install goes back. What the plugin does not ship, the evals and the
  maintainers' guide, lies under `dev/`, because the directory holds the
  folder to 512 files and 7,000,000 bytes.
- The tests run the scripts from `plugin/`, because that is the folder
  every install and link runs them from, and give them the sibling
  Construct3-RAG clone as `--rag`.
- `clone_root` in `c3project.py` treats the `plugin/` folder of a Git
  clone as that clone's. The sibling clones are looked for beside this
  repository, and the update check (`clone-update-check.md`) compares this
  repository and the Construct3-RAG clone with their upstreams.
- `.github/workflows/checks.yml` runs the checks on every push and pull
  request, with the Construct3-RAG clone beside the checkout.
- The plugin is `construct3` (`skill-and-plugin-names.md`), and the
  marketplace is `construct3-agent-skills`.
- In the skill's text, `Construct3-RAG/` names the Construct3-RAG clone,
  and the block's line is `Construct3-RAG:`. The block names this
  repository's clone on its own line, `Construct3-Agent-Skills:`.
- Construct3-RAG keeps `data/`, `src/`, the update pipeline and the docs of
  those. Its instruction files name this repository, and its `README.md`,
  `README_CN.md` and `AGENTS.md` send an agent here for the skill, the
  prompts and the plugin (`skill-in-agent-skills.md` there).

## Trade-offs

- The skill's evals are two folders away from the scripts they test.
- The scripts and the tests need a second clone. On a machine without it
  the scripts stop and name the clone command; in CI the workflow clones
  it shallow.
- The history of the skill before the move is in Construct3-RAG's Git
  history; the files arrived here in one commit.

## Re-evaluate when

- The skill's tests stop needing the scripts of this repository and the
  data together, which would let either repository's checks run alone.
