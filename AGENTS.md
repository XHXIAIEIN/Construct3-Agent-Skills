# Construct3-Agent-Skills for AI Agents

## 1. What this repository is

This repository holds what an AI agent needs to make Construct 3 games. All
of it is in one folder, `plugin/`:

- the `construct3-agent-plugin` skill under `plugin/skills/`, with the rows
  of the Claude Code plugin's `/` menu beside it;
- the prompts for event sheet design under `plugin/prompts/`;
- under `plugin/data/`, the schemas of every Construct 3 condition, action,
  expression and effect in English and Chinese, the editor texts, the
  example index, the TypeScript definitions and an empty project to start
  from.

Any agent that runs a shell and Python uses these files through the skill.
`plugin/` is also the Claude Code plugin `construct3`, and the folder is the
source. So edit the skill, the prompts, the manifest, the README, the icon
and the sub-agents in place. Only `plugin/data/` is built:
`scripts/build_plugin.py` writes it from the data of
[Construct3-RAG](https://github.com/XHXIAIEIN/Construct3-RAG), a clone
beside this one. That repository holds the data, its update pipeline and
the lookup service, and this repository holds everything an agent runs.
The files that the plugin does not ship are beside it: the skill's evals
and the maintainers' guide under `skills-dev/`, the tests, the docs and the
records. The reasons are in `docs/decisions/plugin-repository.md` and
`docs/decisions/plugin-folder.md`.

| Path | What it holds |
|------|---------------|
| `plugin/.claude-plugin/plugin.json` | The plugin's manifest: name, version, description, keywords. The build never sets a version below the committed `version` |
| `plugin/skills/construct3-agent-plugin/` | The skill: `SKILL.md`, its scripts, references and assets. `skills-dev/AGENTS.md` says how to change it |
| `plugin/skills/<name>/SKILL.md`, `plugin/skills/run.py` | One row of the `/` menu for each user-facing script, and the runner that they share |
| `plugin/prompts/` | Event sheet thinking, pitfalls and style, and the references for game feel, menus, dialogue, layers in depth and hand-edited project files. `event-sheet-pitfalls.md` is the index of the pitfalls |
| `plugin/data/c3-schemas/` | The ACEs of every plugin, behavior and effect, one JSON file each, for each locale (built) |
| `plugin/data/c3-lang/` | The editor texts that the checker and a preview's inspector read (built) |
| `plugin/data/c3-new-project/` | The empty project that the editor saves, which `new_project.py` copies (built) |
| `plugin/data/*.bundle-*.json` | The TypeScript definitions, the example projects and the index of their ACEs, as bundles that the scripts read (built) |
| `plugin/agents/` | The `project-worker` sub-agent type, which loads with the plugin |
| `plugin/README.md`, `plugin/icon.png`, `plugin/LICENSE` | The plugin's page in Claude's directory, its listing icon and its licence |
| `skills-dev/` | The skill's evals under `evals/`, and `AGENTS.md`, the guide to changing the skill |
| `scripts/` | The data build, `bootstrap.py`, the output comparison and the measurements. `scripts/AGENTS.md` lists them |
| `tests/` | The pytest suite, described in `tests/AGENTS.md` |
| `docs/decisions/` | The records, indexed in `docs/AGENTS.md` |
| `.claude/agents/` | The `ace-lookup` sub-agent for sessions in this repository |
| `.claude-plugin/marketplace.json` | The marketplace manifest, which names `plugin/` |

Do not write the Construct 3 version or the counts into text, because every
data refresh changes them. Read them from `plugin/data/c3-schemas/_index.json`.

## 2. Answer a Construct 3 fact question

Answer from the data. If an ACE is missing from the schema, it does not
exist, unless `plugin/data/c3-schemas/{locale}/_deprecated.json` lists it.
A listed ACE is deprecated in the editor. An old project that uses it still
opens, but do not use it in a new project.

Look an ACE up with the script:

```bash
python plugin/skills/construct3-agent-plugin/scripts/lookup_ace.py System wait
```

Do not read `plugins/system.json` or `plugins/_common.json` to find an ACE,
because these files have thousands of lines. A reader that stops at 2000
lines shows only part of them, so an ACE below that line looks missing.

The script prints the matching conditions, actions and expressions of
`System`, or of a plugin or behavior given by id or display name. Each one
comes with its parameters and the JSON to write. If you give an effect, it
prints the effect's parameters. `--locale zh-CN` gives the Chinese wording.

| Question | Where |
|----------|-------|
| Which plugins, behaviors, effects exist | `plugin/data/c3-schemas/_index.json` |
| Addon names in one language | `plugin/data/c3-schemas/{locale}/_index.json` |
| ACEs of a plugin or behavior | `lookup_ace.py`, or `plugin/data/c3-schemas/{locale}/plugins/{id}.json` and `behaviors/{id}.json` |
| ACEs shared by every world object | `plugin/data/c3-schemas/{locale}/plugins/_common.json`. A plugin's `commonAces` lists entries of this file |
| JavaScript or TypeScript API | `python plugin/skills/construct3-agent-plugin/scripts/lookup_script_api.py NAME` |
| Example projects for a topic | `python plugin/skills/construct3-agent-plugin/scripts/search_guides.py WORD ...` |
| Translation of an editor string | `plugin/data/c3-lang/{locale}.json` |
| What a field of a project file means | `plugin/skills/construct3-agent-plugin/references/` |
| What a data file holds, field by field | `docs/guide/data-format.md` in the Construct3-RAG clone |

When you name an ACE to the user, use its `display-text` in their language,
and give the object's name and the parameters in words. Keep the ids and the
JSON in the data and the tools.

## 3. Design event sheet logic

Before you design an interaction, data storage, timing or animation, read
and follow `plugin/prompts/event-sheet-thinking.md`. Then verify the names
with section 2. Write the events into a project as
`plugin/prompts/event-sheet-style.md` describes. That file shows how the
official examples organise, name and comment a sheet.

If a project shows a runtime behaviour of events that changes which events
are written, record it in the topic file of its group under
`plugin/prompts/pitfalls/`, with its source. Then add its conclusion as one
line to `plugin/prompts/event-sheet-pitfalls.md`. If a lesson is about the
project file format, the editor, the preview or the look, put it where
"Adding an entry" in that index says.

## 4. Use from a game project

A game project reaches the skill in one of the ways below, and the README
says how to set up each one. Before you place the block in a project's
instruction file by hand, or change the block, read
`plugin/prompts/game-project-AGENTS.md`.

- To use the skill with any agent, run `install.py`. It copies the skill
  into the project and adds a block to the project's `AGENTS.md`. The
  block's `Construct3-RAG:` line names this clone's `plugin/`, the folder
  that holds the data and the prompts:

  ```bash
  python plugin/skills/construct3-agent-plugin/scripts/install.py --project <game folder>
  ```

  `python scripts/bootstrap.py --project <folder>` clones the sibling
  repositories beside this one. If the folder does not exist, it creates the
  folder as an empty project. Then it runs `install.py` on the folder.
- To use the skill in Claude Code, install the plugin in one of three ways:
  from Claude's directory, from this repository as a marketplace, or from a
  clone linked into `~/.claude/skills/`. The skill then loads on its own when
  the user asks about a Construct 3 project, so the project does not need a
  copy of the skill.
- To use the skill without an install, run the scripts from `plugin/` with
  `--project <folder>`.

Read `plugin/skills/construct3-agent-plugin/SKILL.md` before you read or
write the first project file. Before you hand a project over, make sure
that `check_project.py` reports no problems.

## 5. Change this repository

Before you edit, read the `AGENTS.md` of every directory you touch and run
`git status`. Keep the changes that you did not make.

- Edit `plugin/` in place, except `plugin/data/`.
  `python scripts/build_plugin.py` writes that folder from the `data/` of
  the Construct3-RAG clone beside this one. Run the build after a data
  change, because `tests/test_plugin_folder.py` fails while `plugin/data/`
  differs from a fresh build.
- The build also sets the plugin's version. While the plugin's files equal
  the published files, it sets the published version. When they differ, it
  raises the patch number by one. It never sets a version below the
  committed one. Raise `version` in `plugin/.claude-plugin/plugin.json` by
  hand only for a minor or major release (`docs/decisions/plugin-tracks-commits.md`).
- Do not add a `.gitattributes` file to this repository. Claude's directory
  refuses to validate a repository whose attributes could rewrite files at
  checkout, and a test fails on the file. The build writes text files with
  LF, and the checks read a committed text file with CRLF as LF. So a
  checkout with `core.autocrlf` passes the checks (`docs/decisions/plugin-folder.md`).
- Keep `plugin/` inside the limits of Claude's directory: 512 files, 256 KiB
  for each file other than an image, and 7,000,000 bytes in all
  (`docs/decisions/plugin-folder.md`). The build fails when the folder goes
  past them. Put what the plugin does not need at run time beside it, as
  the evals are under `skills-dev/`.
- The data belongs to Construct3-RAG. Make a change to a schema, a language
  pack, an example index or a guide in that repository. When its `main`
  changes, pull the clone beside this one and run the build. The workflow
  `.github/workflows/refresh-plugin.yml` does the same every day, and it
  pushes the build if the data changed.
- If a merge leaves conflicts in `plugin/data/`, run the build, stage the
  folder, then commit the merge.
- The end marker line of
  `plugin/skills/construct3-agent-plugin/assets/build_project.py` conflicts
  whenever both sides changed its helpers, because the line carries their
  stamp. If it conflicts, keep either side, then paste the end line that
  `tests/test_skill_build_project.py` prints.
- A change to `SKILL.md`, to a reference or to what a script prints needs an
  eval iteration of its own (`skills-dev/AGENTS.md`, "Evals").
- If a product choice has a visible effect, record its evidence, options and
  trade-offs in `docs/decisions/`, and add a row for it to `docs/AGENTS.md`.
- Change the docs and the tests together with the behavior. The READMEs
  describe the skill and the plugin for people. They hold the same content
  in English and Chinese, and `README.md` names no Chinese text besides its
  link to `README_CN.md`. Write the skill, the prompts, the `AGENTS.md` files
  and the agent files in English.
- In a commit message or PR text, name an issue of another repository in
  words or as a URL in backticks. Never write `owner/repo#N` or `#N`, because
  GitHub turns these forms into a public cross-reference on that issue's
  timeline, and nobody can remove it.

Before you finish, run the tests that the change reaches and the three
quick checks:

```bash
python -m pytest -q <test files>
python -m compileall -q scripts tests skills-dev plugin/skills
python scripts/build_plugin.py --check
git diff --check
```

Pick the test files from the paths in the diff:

- A change to `plugin/prompts/` or to a document reaches the tests that read
  them: `test_prompts.py`, `test_doc_links.py`, `test_plugin_folder.py` and
  `test_skill_search_guides.py`.
- A change to a script reaches its own tests and the tests of the scripts
  that import it. To find the importers, run `grep -l <module>` in the
  scripts' folders. Then find the tests that name any of them.
- If a change reaches most test files, as a change to
  `tests/skill_helpers.py` or `tests/conftest.py` does, run the whole suite
  with `python -m pytest -q`.

`.github/workflows/checks.yml` runs the whole suite and the other checks on
every push to `main` and on every pull request. So a push needs no local
run of its own. The tests need the Construct3-RAG clone beside this one.
The tests that read the official examples also need the
`Construct-Example-Projects` clone. If a test lacks its clone, it skips and
names the command.

## 6. Where to read more

| Need | Document |
|------|----------|
| Install and use the skill or the plugin | `README.md` |
| The project tools that the skill carries into a game project, and how to change and evaluate them | `plugin/skills/construct3-agent-plugin/SKILL.md`, `skills-dev/AGENTS.md` |
| Event sheet design, the sourced pitfalls, the examples' authoring style | `plugin/prompts/event-sheet-thinking.md`, `plugin/prompts/event-sheet-pitfalls.md` and its topic files in `plugin/prompts/pitfalls/`, `plugin/prompts/event-sheet-style.md`, `docs/decisions/event-sheet-design-guidance.md` |
| The sheets, layers, objects and look of a new project | `plugin/prompts/references/new-project.md`, `docs/decisions/paper-and-ink-look.md`, `docs/decisions/game-look-from-design-skills.md`, `docs/decisions/art-from-the-image-tool.md` |
| The slot case as a program, hand-editing project JSON, feel recipes, sequences and dialogue, menus, flat layers in depth under a 3D camera | `plugin/prompts/references/` |
| The visual language of published games, their motion statistics and the analyzer | `docs/decisions/published-game-visual-language.md`, `docs/dev/published-game-analysis.md` and `scripts/reference_games/` in the Construct3-RAG clone |
| Why the plugin folder holds its sources, how the build sets its version, why it has this repository | `docs/decisions/plugin-folder.md`, `plugin-tracks-commits.md`, `plugin-repository.md` |
| Why features were kept or removed | `docs/AGENTS.md`, the index of the records |
| The audit findings for the project and the skill | `docs/dev/skills-audit.md` |
| The data files, their fields and their update pipeline | `docs/guide/data-format.md` and `docs/dev/data-pipeline.md` in the Construct3-RAG clone |
| How to hand an ACE lookup to a Claude Code sub-agent | `.claude/agents/ace-lookup.md` |
| A verified run that polishes the skill's sources, prompts, docs, records and code. Start it only when no other session edits the repository | `.claude/workflows/polish.js` |
