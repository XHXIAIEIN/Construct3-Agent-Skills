# Construct3-Agent-Skills for AI Agents

## 1. What this repository is

This repository holds what an AI agent needs to make Construct 3 games, and
all of it is in one folder, `plugin/`:

- `plugin/skills/` holds the `construct3-agent-plugin` skill and, beside it,
  the rows of the Claude Code plugin's `/` menu.
- `plugin/data/` holds the schemas of every Construct 3 condition, action,
  expression and effect in English and Chinese, the editor texts, the
  example index, the TypeScript definitions and an empty project to start
  from.

Any agent that runs a shell and Python uses these files through the skill.
`plugin/` is also the source of the Claude Code plugin `construct3`, so edit
the skill, the manifest, the README, the icon and the sub-agents in place.
Only `plugin/data/` is built: `dev/scripts/build_plugin.py` writes it from
the data of [Construct3-RAG](https://github.com/XHXIAIEIN/Construct3-RAG), a
clone beside this one. That repository holds the data, its update pipeline
and the lookup service, and this repository holds everything an agent runs.

The files that the plugin does not ship are beside `plugin/`. `dev/` holds
what only the skill's maintainers use: the evals, the tests, the build and
the guides to changing the skill. `docs/` holds the decision records. The
reasons are in `docs/decisions/plugin-repository.md`,
`docs/decisions/plugin-folder.md` and `docs/decisions/dev-folder.md`.

The guides to event sheet design, the pitfalls among them, live in
[Construct3-Cookbook](https://github.com/XHXIAIEIN/Construct3-Cookbook). The
scripts find its clone beside this one, so a new pitfall reaches users
through `git pull` without a plugin release
(`docs/decisions/guides-in-cookbook.md`). Below, `Construct3-Cookbook/...`
names a file of that clone.

| Path | What it holds |
|------|---------------|
| `plugin/.claude-plugin/plugin.json` | The plugin's manifest: name, version, description and keywords |
| `plugin/skills/construct3-agent-plugin/` | The skill: `SKILL.md`, its scripts, references and assets. `dev/AGENTS.md` says how to change it |
| `plugin/skills/<name>/SKILL.md`, `plugin/skills/run.py` | One row of the `/` menu for each user-facing script, and the runner that the rows share |
| `plugin/data/c3-schemas/` | The ACEs of every plugin, behavior and effect, one JSON file each, for each locale (built) |
| `plugin/data/c3-lang/` | The editor texts that the checker and a preview's inspector read (built) |
| `plugin/data/c3-new-project/` | The empty project that the editor saves, which `new_project.py` copies (built) |
| `plugin/data/*.bundle-*.json` | The TypeScript definitions, the example projects and the index of their ACEs, as bundles that the scripts read (built) |
| `plugin/agents/` | The `project-worker` sub-agent type, which loads with the plugin |
| `plugin/README.md`, `plugin/icon.png`, `plugin/LICENSE` | The plugin's page in Claude's directory, its listing icon and its licence |
| `dev/AGENTS.md` | The guide to changing the skill and running its evals |
| `dev/game-project-AGENTS.md` | How the skill's block reaches a game project's `AGENTS.md`, and how to place or change it by hand |
| `dev/evals/` | The evals that test the skill with agents |
| `dev/scripts/` | The data build, the output comparison and the measurements, listed in `dev/scripts/AGENTS.md` |
| `dev/tests/` | The pytest suite, described in `dev/tests/AGENTS.md` |
| `scripts/bootstrap.py` | The setup of a machine from this clone alone. It stays at the root because the README prints its path |
| `docs/decisions/` | The records, indexed in `docs/decisions/README.md`. `docs/AGENTS.md` says how to write one |
| `.claude/agents/` | The `ace-lookup` sub-agent for sessions in this repository |
| `.claude-plugin/marketplace.json` | The marketplace manifest, which names `plugin/` |

Do not write the Construct 3 version or the counts of the data into text,
because every data refresh changes them. Read them from
`plugin/data/c3-schemas/_index.json`.

## 2. Answer a Construct 3 fact question

Answer from the data. If an ACE is missing from the schema, it does not
exist, unless `plugin/data/c3-schemas/{locale}/_deprecated.json` lists it. A
listed ACE is deprecated in the editor: an old project that uses it still
opens, but a new project must not use it.

Look an ACE up with the script:

```bash
python plugin/skills/construct3-agent-plugin/scripts/lookup_ace.py System wait
```

Do not read `plugins/system.json` or `plugins/_common.json` to find an ACE.
These files have thousands of lines, and a reader that stops at 2000 lines
shows only part of them, so an ACE below that line looks missing.

The script prints the matching conditions, actions and expressions of
`System`, or of a plugin or behavior given by ID or display name. Each one
comes with its parameters and the JSON to write. For an effect, the script
prints the effect's parameters. `--locale zh-CN` prints the Chinese wording.

| Question | Where |
|----------|-------|
| Which plugins, behaviors and effects exist | `plugin/data/c3-schemas/_index.json` |
| Addon names in one language | `plugin/data/c3-schemas/{locale}/_index.json` |
| ACEs of a plugin or behavior | `lookup_ace.py`, or `plugin/data/c3-schemas/{locale}/plugins/{id}.json` and `behaviors/{id}.json` |
| ACEs that every world object shares | `plugin/data/c3-schemas/{locale}/plugins/_common.json`. A plugin's `commonAces` lists entries of this file |
| JavaScript or TypeScript API | `python plugin/skills/construct3-agent-plugin/scripts/lookup_script_api.py NAME` |
| Example projects for a topic | `python plugin/skills/construct3-agent-plugin/scripts/search_guides.py WORD ...` |
| Translation of an editor string | `plugin/data/c3-lang/{locale}.json` |
| What a field of a project file means | `plugin/skills/construct3-agent-plugin/references/` |
| What a data file holds, field by field | `docs/guide/data-format.md` in the Construct3-RAG clone |

When you name an ACE to the user, use its `display-text` in the user's
language, and give the object's name and the parameters in words. The IDs
and the JSON stay in the data and the tools.

## 3. Design event sheet logic

Before you design an interaction, data storage, timing or animation, read
and follow `Construct3-Cookbook/guides/design/thinking.md`. Then verify the
names as section 2 describes. Write the events into a project as
`Construct3-Cookbook/guides/design/style.md` describes, because that file
shows how the official examples organise, name and comment a sheet. If there
is no Cookbook clone, give the user the `git clone` command that
`search_guides.py` prints, and clone it once the user agrees.

A runtime behaviour of events that changes which events an agent writes is a
pitfall. Record it in Construct3-Cookbook, not here, as that repository's
`AGENTS.md` describes: the entry and its source go on the page that owns it,
and its conclusion goes as one line into `guides/pitfalls.md`. A lesson
about the project file format, the editor, the preview or the look goes
where the section "Adding an entry" of that index says.

## 4. Use from a game project

A game project reaches the skill in one of the three ways below, and the
README says how to set up each one. Before you place the block in a
project's instruction file by hand, or change the block, read
`dev/game-project-AGENTS.md`.

- **Any agent.** Run `install.py`. It copies the skill into the project and
  adds a block to the project's `AGENTS.md`. The block's `Construct3-RAG:`
  line names this clone's `plugin/`, the folder that holds the data, and its
  `Construct3-Cookbook:` line names the Cookbook clone:

  ```bash
  python plugin/skills/construct3-agent-plugin/scripts/install.py --project <game folder>
  ```

  `python scripts/bootstrap.py --project <folder>` clones the missing
  sibling repositories beside this one. If the folder does not exist, it
  creates the folder as an empty project. Then it runs `install.py` on the
  folder.
- **Claude Code.** Install the plugin from Claude's directory, from this
  repository as a marketplace, or from a clone linked into
  `~/.claude/skills/`. The skill then loads by itself when the user asks
  about a Construct 3 project, so the project needs no copy of the skill.
- **No install.** Run the scripts from `plugin/` with `--project <folder>`.

Read `plugin/skills/construct3-agent-plugin/SKILL.md` before you read or
write the first project file. Before you hand a project over, make sure that
`check_project.py` reports no problems.

## 5. Change this repository

Before you edit, read the `AGENTS.md` of every directory that you touch, and
run `git status`. Keep the changes that you did not make, because other
sessions may work in the same checkout.

- Edit `plugin/` in place, except `plugin/data/`. `python
  dev/scripts/build_plugin.py` writes that folder from the `data/` of the
  Construct3-RAG clone. Run the build after a data change, because
  `dev/tests/test_plugin_folder.py` fails while `plugin/data/` differs from
  a fresh build.
- The build also sets the plugin's version. While the plugin's files equal
  the published files, it sets the published version. When they differ, it
  raises the patch number by one. It never sets a version below the
  committed `version`. Raise `version` in
  `plugin/.claude-plugin/plugin.json` by hand only for a minor or major
  release (`docs/decisions/plugin-tracks-commits.md`).
- Do not add a `.gitattributes` file. Claude's directory refuses to validate
  a repository whose attributes could rewrite files at checkout, and a test
  fails on the file. A checkout with `core.autocrlf` passes the checks
  without it, because the build writes text files with LF and the checks
  read a committed CRLF text file as LF (`docs/decisions/plugin-folder.md`).
- Keep `plugin/` inside the limits of Claude's directory: 512 files, 256 KiB
  for each file other than an image, and 7,000,000 bytes in all
  (`docs/decisions/plugin-folder.md`). The build fails when the folder
  exceeds them. Put what the plugin does not need at run time under `dev/`.
- Make a change to a schema, a language pack, an example index or a guide in
  Construct3-RAG, because the data belongs to that repository. When its
  `main` changes, pull the clone beside this one and run the build.
  `.github/workflows/refresh-plugin.yml` does the same every day, and it
  pushes the build if the data changed.
- If a merge leaves conflicts in `plugin/data/`, run the build, stage the
  folder, then commit the merge.
- The end marker line of
  `plugin/skills/construct3-agent-plugin/assets/build_project.py` conflicts
  whenever both sides changed its helpers, because the line carries their
  stamp. If it conflicts, keep either side, then paste the end line that
  `dev/tests/test_skill_build_project.py` prints.
- A change to `SKILL.md`, to a reference or to what a script prints needs an
  eval iteration of its own, as the section "Evals" of `dev/AGENTS.md`
  describes.
- If a product choice has a visible effect, record its evidence, options and
  trade-offs in `docs/decisions/`, and add its line to
  `docs/decisions/README.md`.
- Change the docs and the tests together with the behaviour. The READMEs
  describe the skill and the plugin for people, with the same content in
  English and Chinese. `README.md` contains no Chinese text other than its
  link to `README_CN.md`. Write the skill, the `AGENTS.md` files and the
  agent files in English.
- In a commit message or PR text, name an issue of another repository in
  words or by its URL in backticks. Never write `owner/repo#N` or `#N`,
  because GitHub turns these forms into a public cross-reference on that
  issue's timeline, and nobody can remove it.

Before you finish, run the tests that the change reaches and the three quick
checks:

```bash
python -m pytest -q <test files>
python -m compileall -q dev scripts plugin/skills
python dev/scripts/build_plugin.py --check
git diff --check
```

Pick the test files from the paths in the diff:

- A change to a document reaches the tests that read documents:
  `test_doc_links.py`, `test_plugin_folder.py` and `test_cookbook_paths.py`.
  The last one checks that every `Construct3-Cookbook/...` path named here
  exists in the Cookbook clone.
- A change to a script reaches its own tests and the tests of the scripts
  that import it. To find the importers, run `grep -l <module>` in the
  script folders, then find the tests that name any of them.
- If a change reaches most test files, as a change to
  `dev/tests/skill_helpers.py` or `dev/tests/conftest.py` does, run the
  whole suite with `python -m pytest -q`.

`.github/workflows/checks.yml` runs the whole suite and the other checks on
every push to `main` and on every pull request, so a push needs no local run
of the whole suite. The tests need the Construct3-RAG clone beside this one.
The tests that read the official examples also need the
`Construct-Example-Projects` clone, and the tests that read the guides need
the `Construct3-Cookbook` clone. If a test lacks its clone, it skips and
names the command that supplies it.

## 6. Where to read more

| Need | Document |
|------|----------|
| Install and use the skill or the plugin | `README.md` |
| The project tools that the skill carries into a game project, and how to change and evaluate them | `plugin/skills/construct3-agent-plugin/SKILL.md`, `dev/AGENTS.md` |
| Event sheet design, the sourced pitfalls and the examples' authoring style | `design/thinking.md`, `pitfalls.md` with its pages and `design/style.md` under `Construct3-Cookbook/guides/`; `docs/decisions/event-sheet-design-guidance.md` |
| The sheets, layers, objects and look of a new project | `Construct3-Cookbook/guides/project-files/new-project.md`, `docs/decisions/paper-and-ink-look.md`, `docs/decisions/game-look-from-design-skills.md`, `docs/decisions/art-from-the-image-tool.md` |
| The slot case as a program, hand-editing project JSON, feel recipes, sequences and dialogue, menus, and flat layers in depth under a 3D camera | `Construct3-Cookbook/guides/recipes/` and `Construct3-Cookbook/guides/project-files/` |
| The visual language of published games, their motion statistics and the analyzer | `docs/decisions/published-game-visual-language.md`, `docs/dev/published-game-analysis.md` and `scripts/reference_games/`, all in the Construct3-RAG clone |
| Why the plugin folder holds its sources, how the build sets the version, and why the plugin has this repository | `docs/decisions/plugin-folder.md`, `docs/decisions/plugin-tracks-commits.md`, `docs/decisions/plugin-repository.md` |
| Why features were kept or removed | `docs/decisions/README.md`, the index of the records |
| The data files, their fields and their update pipeline | `docs/guide/data-format.md` and `docs/dev/data-pipeline.md` in the Construct3-RAG clone |
| How to hand an ACE lookup to a Claude Code sub-agent | `.claude/agents/ace-lookup.md` |
| A verified run that polishes the skill's sources, docs, records and code. Start it only when no other session edits the repository | `.claude/workflows/polish.js` |
