# Construct3-Agent-Skills for AI Agents

## 1. What this repository is

This repository holds the scripts an AI agent runs to make Construct 3
games, all of them in one folder, `plugin/`. `plugin/skills/` holds the
`construct3-agent-plugin` skill, and `plugin/` is also the Claude Code
plugin `construct3`. Any agent that runs a shell and Python uses the skill.

The plugin holds no data. The scripts read it from a clone of
[Construct3-RAG](https://github.com/XHXIAIEIN/Construct3-RAG), which holds
the schemas of every Construct 3 condition, action, expression and effect in
English and Chinese, the editor texts, the example index, the TypeScript
definitions and an empty project to start from, with their update pipeline.
They find the clone in the home folder of the clones, `~/Construct3`, or
beside this one. Without one they point to `setup.py`, which lists every
missing clone with its command (`docs/decisions/plugin-reads-the-clones.md`,
`docs/decisions/clones-home.md`). Below,
`Construct3-RAG/...` names a file of that clone.

The guides to event sheet design, the pitfalls among them, live in
[Construct3-Cookbook](https://github.com/XHXIAIEIN/Construct3-Cookbook). The
scripts find its clone beside this one, so a new pitfall reaches users
through `git pull` without a plugin release
(`docs/decisions/guides-in-cookbook.md`). Below, `Construct3-Cookbook/...`
names a file of that clone.

| Path | What it holds |
|------|---------------|
| `plugin/.claude-plugin/plugin.json` | The plugin's manifest: name, version, description and keywords |
| `plugin/skills/construct3-agent-plugin/` | The skill: `SKILL.md`, its scripts, references and assets |
| `plugin/agents/` | The `project-worker`, `art-drawer`, `design-judge` and `recording-describer` sub-agent types, which load with the plugin |
| `plugin/README.md`, `plugin/icon.png`, `plugin/LICENSE` | The plugin's page in Claude's directory, its listing icon and its licence |
| `scripts/bootstrap.py` | The script that clones the sibling repositories and installs the skill in a game project (section 4) |
| `docs/decisions/` | The reasons behind the skill's choices, indexed in `docs/decisions/README.md` |
| `.claude/agents/` | The `ace-lookup` sub-agent for sessions in this repository |
| `.claude-plugin/marketplace.json` | The marketplace manifest, which names `plugin/` |
| `dev/` | What only the maintainers use: the evals, the tests and the data build (section 5) |

## 2. Answer a Construct 3 fact question

Answer from the data. If an ACE is missing from the schema, it does not
exist, unless `Construct3-RAG/data/c3-schemas/{locale}/_deprecated.json` lists it. A
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
| Which plugins, behaviors and effects exist | `Construct3-RAG/data/c3-schemas/_index.json` |
| Addon names in one language | `Construct3-RAG/data/c3-schemas/{locale}/_index.json` |
| ACEs of a plugin or behavior | `lookup_ace.py`, or `Construct3-RAG/data/c3-schemas/{locale}/plugins/{id}.json` and `behaviors/{id}.json` |
| ACEs that every world object shares | `Construct3-RAG/data/c3-schemas/{locale}/plugins/_common.json`. A plugin's `commonAces` lists entries of this file |
| JavaScript or TypeScript API | `python plugin/skills/construct3-agent-plugin/scripts/lookup_script_api.py NAME` |
| Example projects for a topic | `python plugin/skills/construct3-agent-plugin/scripts/search_guides.py WORD ...` |
| Translation of an editor string | `Construct3-RAG/data/c3-lang/{locale}.json` |
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
is no Cookbook clone, run `plugin/skills/construct3-agent-plugin/scripts/setup.py`,
give the user every clone it lists, and clone them once the user agrees.

A runtime behaviour of events that changes which events an agent writes is a
pitfall. Record it in Construct3-Cookbook, not here, as that repository's
`AGENTS.md` describes: the entry and its source go on the page that owns it,
and the section "Adding an entry" of `guides/pitfalls.md` says what the
index gets. A lesson about the project file format, the editor or the preview
goes where that section says.

## 4. Use from a game project

A game project reaches the skill in one of the three ways below, and the
README says how to set up each one. Before you place the block in a
project's instruction file by hand, or change the block, read
`dev/game-project-AGENTS.md`.

- **Any agent.** Run `install.py`. It copies the skill into the project and
  adds a block to the project's `AGENTS.md`. The block's `Construct3-RAG:`
  line names the Construct3-RAG clone, its `Construct3-Agent-Skills:` line
  this clone, and its `Construct3-Cookbook:` line the Cookbook clone:

  ```bash
  python plugin/skills/construct3-agent-plugin/scripts/install.py --project <game folder>
  ```

  `python scripts/bootstrap.py --project <folder>` clones the required
  repositories that are missing into the home folder, `~/Construct3`, and
  `--all` the optional ones. If the folder does not exist, it creates the
  folder as an empty project. Then it runs `install.py` on the folder.
- **Claude Code.** Install the plugin from Claude's directory, from this
  repository as a marketplace, or from a clone linked into
  `~/.claude/skills/`. The skill then loads by itself when the user asks
  about a Construct 3 project, so the project needs no copy of the skill.
- **No install.** Run the scripts from `plugin/` with `--project <folder>`.

Read `plugin/skills/construct3-agent-plugin/SKILL.md` before you read or
write the first project file. Before you hand a project over, make sure that
`check_project.py` reports no problems.

## 5. Change this repository

Before you change the skill, the plugin, the tests or the docs of this
repository, read `dev/AGENTS.md`.

## 6. Where to read more

| Need | Document |
|------|----------|
| Install and use the skill or the plugin | `README.md` |
| The project tools that the skill carries into a game project | `plugin/skills/construct3-agent-plugin/SKILL.md` |
| Event sheet design, the sourced pitfalls and the examples' authoring style | `design/thinking.md`, `pitfalls.md` with its pages and `design/style.md` under `Construct3-Cookbook/guides/`; `docs/decisions/event-sheet-design-guidance.md` |
| The sheets, layers and objects of a new project | `Construct3-Cookbook/guides/project-files/new-project.md` |
| Why the repository checks no looks | `docs/decisions/mechanical-checks-only.md` |
| How a game gets its pictures | `docs/decisions/art-entry-point.md`, `docs/decisions/art-drawn-in-code.md`, `docs/decisions/art-from-the-image-tool.md` |
| The slot case as a program, hand-editing project JSON, feel recipes, sequences and dialogue, menus, flat layers in depth under a 3D camera, and porting a web or WebGL effect | `Construct3-Cookbook/guides/recipes/` and `Construct3-Cookbook/guides/project-files/` |
| The visual language of published games, their motion statistics and the analyzer | `docs/decisions/published-game-visual-language.md`, `docs/dev/published-game-analysis.md` and `scripts/reference_games/`, all in the Construct3-RAG clone |
| Why features were kept or removed | `docs/decisions/README.md`, the index of the records |
| The data files and their fields | `docs/guide/data-format.md` in the Construct3-RAG clone |
| How to hand an ACE lookup to a Claude Code sub-agent | `.claude/agents/ace-lookup.md` |
