# Construct3-Agent-Skills for AI Agents

## 1. What this repository is

This repository holds what an AI agent needs to make Construct 3 games, and
the sources it is built from:

- `plugin/`, the built folder that every install runs: the
  `construct3-agent-plugin` skill, the schemas of every Construct 3
  condition, action, expression and effect in English and Chinese, the
  prompts for event sheet design, and an empty project to start from. Any
  agent that runs a shell and Python uses them through the skill. `plugin/`
  is also the Claude Code plugin `construct3`.
- `skills/construct3-agent-plugin/`, `prompts/` and `scripts/plugin/`, the
  sources of the skill, the prompts and the plugin's manifest, README, icon
  and sub-agents. `scripts/build_plugin.py` builds `plugin/` from them and
  from the data of [Construct3-RAG](https://github.com/XHXIAIEIN/Construct3-RAG),
  a clone beside this one. That repository holds the data, its update
  pipeline and the lookup service; this one holds everything an agent
  runs. Why: `docs/decisions/plugin-repository.md`.
- `tests/`, the skill's tests and the plugin's, and `docs/decisions/`, one
  record per product choice of the skill, the prompts and the plugin.

| Path | What it holds |
|------|---------------|
| `plugin/.claude-plugin/plugin.json` | The plugin's manifest: name, version, description, keywords |
| `plugin/skills/construct3-agent-plugin/` | The skill as installed: `SKILL.md`, its scripts, references and assets |
| `plugin/data/c3-schemas/` | The ACEs of every plugin, behavior and effect, one JSON file each, per locale |
| `plugin/data/c3-lang/` | The editor texts the checker and a preview's inspector read |
| `plugin/data/c3-new-project/` | The empty project the editor saves, which `new_project.py` copies |
| `plugin/data/*.bundle-*.json` | The TypeScript definitions, the example projects and the index of their ACEs, as bundles the scripts read |
| `plugin/prompts/` | Event sheet thinking, pitfalls and style, and the references for game feel, menus, dialogue and hand-edited project files |
| `plugin/agents/` | The `project-worker` sub-agent type, loaded with the plugin |
| `skills/construct3-agent-plugin/` | The skill's source, with its `evals/`, which the plugin leaves out; `skills/AGENTS.md` says how to change it |
| `prompts/` | The prompts' source; `prompts/event-sheet-pitfalls.md` is the index of the pitfalls |
| `scripts/` | The build, `bootstrap.py`, the output comparison and the measurements; `scripts/AGENTS.md` lists them |
| `scripts/plugin/` | The plugin's manifest (its `version` is the floor), README, icon and `agents/` |
| `tests/` | The pytest suite; `tests/AGENTS.md` |
| `docs/decisions/` | The records, indexed in `docs/AGENTS.md` |
| `.claude/agents/` | The `ace-lookup` sub-agent for sessions in this repository |
| `.claude-plugin/marketplace.json` | The marketplace manifest, which names `plugin/` |

Do not write the Construct 3 version or the counts into text, because every
data refresh changes them; read them from `plugin/data/c3-schemas/_index.json`.

## 2. Answer a Construct 3 fact question

Answer from the data. An ACE missing from the schema does not exist, unless
`plugin/data/c3-schemas/{locale}/_deprecated.json` lists it. Then the editor
deprecated it: an old project that uses it still opens, and a new project
should not use it.

Look an ACE up with the script, never by reading `plugins/system.json` or
`plugins/_common.json`. They run to thousands of lines, and a reader that
stops at 2000 lines shows only part of them, so an ACE below the cut looks
missing:

```bash
python plugin/skills/construct3-agent-plugin/scripts/lookup_ace.py System wait
```

It prints the matching conditions, actions and expressions of `System`, or
of a plugin or behavior given by id or display name, each with its
parameters and the JSON to write. Given an effect, it prints the effect's
parameters. `--locale zh-CN` gives the Chinese wording.

| Question | Where |
|----------|-------|
| Which plugins, behaviors, effects exist | `plugin/data/c3-schemas/_index.json` |
| Addon names in one language | `plugin/data/c3-schemas/{locale}/_index.json` |
| ACEs of a plugin or behavior | `lookup_ace.py`, or `plugin/data/c3-schemas/{locale}/plugins/{id}.json` and `behaviors/{id}.json` |
| ACEs shared by every world object | `plugin/data/c3-schemas/{locale}/plugins/_common.json`, whose entries a plugin's `commonAces` lists |
| JavaScript or TypeScript API | `python plugin/skills/construct3-agent-plugin/scripts/lookup_script_api.py NAME` |
| Example projects for a topic | `python plugin/skills/construct3-agent-plugin/scripts/search_guides.py WORD ...` |
| Translation of an editor string | `plugin/data/c3-lang/{locale}.json` |
| What a field of a project file means | `skills/construct3-agent-plugin/references/` |
| What a data file holds, field by field | `docs/guide/data-format.md` in the Construct3-RAG clone |

To the user, an ACE is its `display-text` in their language, with the
object's name and the parameters in words. The ids and the JSON stay in the
data and the tools.

## 3. Design event sheet logic

Before you design an interaction, data storage, timing or animation, read
and follow `prompts/event-sheet-thinking.md`. Then verify the names with
section 2. Events written into a project follow
`prompts/event-sheet-style.md`, which describes how the official examples
organise, name and comment a sheet.

If a project shows a runtime behaviour of events that changes which events
are written, record it in the topic file of its group under
`prompts/pitfalls/`, with its source, and record its conclusion as one line
in `prompts/event-sheet-pitfalls.md`. A lesson about the project file
format, the editor, the preview or the look goes where "Adding an entry"
there says.

## 4. Use from a game project

A game project reaches the skill in one of these ways; the README says
how to set each one up. Before you place the block in a project's
instruction file by hand or change it, read `prompts/game-project-AGENTS.md`.

- To use the skill with any agent, run `install.py` from `plugin/`. It
  copies the skill into the project and adds a block to the project's
  `AGENTS.md`, whose `Construct3-RAG:` line names this clone's `plugin/`,
  the folder that holds the data and the prompts:

  ```bash
  python plugin/skills/construct3-agent-plugin/scripts/install.py --project <game folder>
  ```

  `python scripts/bootstrap.py --project <folder>` clones the sibling
  repositories beside this one, creates the folder as an empty project when
  it does not exist, and runs `install.py` on it.
- To use it in Claude Code, install the plugin from Claude's directory,
  from this repository as a marketplace, or from a clone linked into
  `~/.claude/skills/`. The skill then loads on its own when the user asks
  about a Construct 3 project, and the project needs no copy.
- To use it without an install, run the scripts from `plugin/` with
  `--project <folder>`.

Read `plugin/skills/construct3-agent-plugin/SKILL.md` before you read or
write the first project file. Before you hand a project over, make sure
that `check_project.py` reports no problems.

## 5. Change this repository

Before you edit, read the `AGENTS.md` of every directory you touch, run
`git status`, and keep the changes you did not make.

- Edit the sources, then build. `plugin/` is built from
  `skills/construct3-agent-plugin/`, `prompts/`, `scripts/plugin/` and the
  `data/` of the Construct3-RAG clone beside this one by
  `python scripts/build_plugin.py`, and committed with them. Never edit a
  file under `plugin/`, because the next build overwrites it and
  `tests/test_plugin_folder.py` fails until the build is run. The build
  sets the plugin's version and raises its patch itself. Raise `version`
  in `scripts/plugin/plugin.json` only for a minor or major release
  (`docs/decisions/plugin-tracks-commits.md`).
- The data is Construct3-RAG's. A change to a schema, a language pack, an
  example index or a guide goes to that repository; when its `main`
  changes, pull the clone beside this one and build. The workflow
  `.github/workflows/refresh-plugin.yml` does the same every day and pushes
  the build when the data changed.
- If a merge leaves conflicts in `plugin/`, resolve the sources, run the
  build, stage `plugin/`, then commit the merge. The end marker line of
  `skills/construct3-agent-plugin/assets/build_project.py` conflicts
  whenever both sides changed its helpers, because it carries their stamp.
  Keep either side, and before the build paste the end line that
  `tests/test_skill_build_project.py` prints.
- A change to `SKILL.md`, to a reference or to what a script prints is a
  new eval iteration (`skills/AGENTS.md`, "Evals").
- A product choice with a visible effect gets its evidence, options and
  trade-offs in `docs/decisions/`, with a row in `docs/AGENTS.md`.
- Docs and tests change with the behavior. The READMEs describe the skill
  and the plugin for people, in English and Chinese with the same content.
  `README.md` names no Chinese text besides its link to `README_CN.md`.
  The skill, the prompts, the `AGENTS.md` files and the agent files are
  English.
- A commit message or PR text names an issue of another repository in
  words or as a URL in backticks, never as `owner/repo#N` or `#N`, because
  GitHub turns those into a public cross-reference on that issue's
  timeline, which cannot be taken back.

Before you finish, run these:

```bash
python -m pytest -q
python -m compileall -q scripts tests skills
python scripts/build_plugin.py --check
git diff --check
```

They need the Construct3-RAG clone beside this one and, for the tests that
read the official examples, the `Construct-Example-Projects` clone; a test
that lacks it skips and names the command. `.github/workflows/checks.yml`
runs the same on every push to `main` and every pull request.

## 6. Where to read more

| Need | Document |
|------|----------|
| Install and use the skill or the plugin | `README.md` |
| The project tools the skill carries into a game project, and changing and evaluating them | `skills/construct3-agent-plugin/SKILL.md`, `skills/AGENTS.md` |
| Event sheet design, sourced pitfalls, the examples' authoring style | `prompts/event-sheet-thinking.md`, `prompts/event-sheet-pitfalls.md` and its topic files in `prompts/pitfalls/`, `prompts/event-sheet-style.md`, `docs/decisions/event-sheet-design-guidance.md` |
| A new project's sheets, layers, objects and look | `prompts/references/new-project.md`, `docs/decisions/paper-and-ink-look.md`, `docs/decisions/game-look-from-design-skills.md`, `docs/decisions/art-from-the-image-tool.md` |
| Slot case as a program, hand-editing project JSON, feel recipes, sequences and dialogue, menus | `prompts/references/` |
| The visual language of published games, their motion statistics and the analyzer | `docs/decisions/published-game-visual-language.md`, `docs/dev/published-game-analysis.md` and `scripts/reference_games/` in the Construct3-RAG clone |
| Why the plugin is a built folder, how its version is set, why it has this repository | `docs/decisions/plugin-folder.md`, `plugin-tracks-commits.md`, `plugin-repository.md` |
| Why features were kept or removed | `docs/AGENTS.md`, the index of the records |
| Project and skill audit findings | `docs/dev/skills-audit.md` |
| The data files, their fields and their update pipeline | `docs/guide/data-format.md` and `docs/dev/data-pipeline.md` in the Construct3-RAG clone |
| Delegating an ACE lookup to a Claude Code sub-agent | `.claude/agents/ace-lookup.md` |
| Polishing the skill's sources, prompts, docs, records and code in one verified run; start it when no other session edits the repository | `.claude/workflows/polish.js` |
