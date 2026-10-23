# Construct3-Agent-Skills for AI Agents

## 1. What this repository is

This repository holds what an AI agent needs to make Construct 3 games. All
of it is in one folder, `plugin/`:

- the `construct3-agent-plugin` skill under `plugin/skills/`, with the rows
  of the Claude Code plugin's `/` menu beside it;
- under `plugin/data/`, the schemas of every Construct 3 condition, action,
  expression and effect in English and Chinese, the editor texts, the
  example index, the TypeScript definitions and an empty project to start
  from.

Any agent that runs a shell and Python uses these files through the skill.
`plugin/` is also the Claude Code plugin `construct3`. Its data comes from
[Construct3-RAG](https://github.com/XHXIAIEIN/Construct3-RAG), which holds
the data, its update pipeline and the lookup service; this repository holds
everything an agent runs.

The guides for event sheet design, the pitfalls among them, live in
[Construct3-Cookbook](https://github.com/XHXIAIEIN/Construct3-Cookbook), a
public repository whose clone the scripts find beside this one, so that a
new pitfall reaches users by `git pull` without a plugin release. Below,
`Construct3-Cookbook/...` names a file of that clone. Why:
`docs/decisions/guides-in-cookbook.md`.

| Path | What it holds |
|------|---------------|
| `plugin/.claude-plugin/plugin.json` | The plugin's manifest: name, version, description, keywords |
| `plugin/skills/construct3-agent-plugin/` | The skill: `SKILL.md`, its scripts, references and assets |
| `plugin/skills/<name>/SKILL.md`, `plugin/skills/run.py` | One row of the `/` menu for each user-facing script, and the runner that they share |
| `plugin/data/c3-schemas/` | The ACEs of every plugin, behavior and effect, one JSON file each, for each locale (built) |
| `plugin/data/c3-lang/` | The editor texts that the checker and a preview's inspector read (built) |
| `plugin/data/c3-new-project/` | The empty project that the editor saves, which `new_project.py` copies (built) |
| `plugin/data/*.bundle-*.json` | The TypeScript definitions, the example projects and the index of their ACEs, as bundles that the scripts read (built) |
| `plugin/agents/` | The `project-worker` sub-agent type, which loads with the plugin |
| `plugin/README.md`, `plugin/icon.png`, `plugin/LICENSE` | The plugin's page in Claude's directory, its listing icon and its licence |
| `scripts/bootstrap.py` | Clones the sibling repositories and installs the skill in a game project (section 4) |
| `docs/decisions/` | The reasons behind the skill's choices, indexed in `docs/decisions/README.md` |
| `.claude/agents/` | The `ace-lookup` sub-agent for sessions in this repository |
| `.claude-plugin/marketplace.json` | The marketplace manifest, which names `plugin/` |
| `dev/` | What only the maintainers use: the evals, the tests and the data build (section 5) |

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
and follow `Construct3-Cookbook/guides/design/thinking.md`. Then verify the
names with section 2. Write the events into a project as
`Construct3-Cookbook/guides/design/style.md` describes. That file shows how
the official examples organise, name and comment a sheet. Without a
Cookbook clone, give the user the `git clone` command that
`search_guides.py` prints, and clone it once they agree.

A runtime behaviour of events that changes which events are written is a
pitfall. Record it in Construct3-Cookbook, not here. Its entry and source go
on the page that owns it there: an add-on's id, a category or a manual page,
as that repository's `AGENTS.md` says. Then add its conclusion as one line
to `guides/pitfalls.md`. If a lesson is about the project file format, the
editor, the preview or the look, put it where "Adding an entry" in that
index says.

## 4. Use from a game project

A game project reaches the skill in one of the ways below, and the README
says how to set up each one. Before you place the block in a project's
instruction file by hand, or change the block, read
`dev/game-project-AGENTS.md`.

- To use the skill with any agent, run `install.py`. It copies the skill
  into the project and adds a block to the project's `AGENTS.md`. The
  block's `Construct3-RAG:` line names this clone's `plugin/`, the folder
  that holds the data. Its `Construct3-Cookbook:` line names the Cookbook
  clone:

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

To change the skill, the plugin, the tests or the docs of this repository,
read `dev/AGENTS.md` first.

## 6. Where to read more

| Need | Document |
|------|----------|
| Install and use the skill or the plugin | `README.md` |
| The project tools that the skill carries into a game project | `plugin/skills/construct3-agent-plugin/SKILL.md` |
| Event sheet design, the sourced pitfalls, the examples' authoring style | `design/thinking.md`, `pitfalls.md` with its pages and `design/style.md` under `Construct3-Cookbook/guides/`, `docs/decisions/event-sheet-design-guidance.md` |
| The sheets, layers, objects and look of a new project | `Construct3-Cookbook/guides/project-files/new-project.md`, `docs/decisions/paper-and-ink-look.md`, `docs/decisions/game-look-from-design-skills.md`, `docs/decisions/art-from-the-image-tool.md` |
| The slot case as a program, hand-editing project JSON, feel recipes, sequences and dialogue, menus, flat layers in depth under a 3D camera | `Construct3-Cookbook/guides/recipes/` and `project-files/` |
| The visual language of published games, their motion statistics and the analyzer | `docs/decisions/published-game-visual-language.md`, `docs/dev/published-game-analysis.md` and `scripts/reference_games/` in the Construct3-RAG clone |
| Why features were kept or removed | `docs/decisions/README.md`, the index of the records |
| The data files and their fields | `docs/guide/data-format.md` in the Construct3-RAG clone |
| How to hand an ACE lookup to a Claude Code sub-agent | `.claude/agents/ace-lookup.md` |
