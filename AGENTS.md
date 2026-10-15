# Construct3-Agent-Skills for AI Agents

## 1. What this repository is

This repository is the home of the Construct 3 plugin for Claude Code. The
plugin is `plugin/`: the `construct3-agent-plugin` skill, the schemas of
every Construct 3 condition, action, expression and effect in English and
Chinese, the prompts for event sheet design, and an empty project to start
from. The files beside `plugin/` are this repository's own: this guide, the
READMEs, the Claude Code agents under `.claude/` and the marketplace
manifest under `.claude-plugin/`.

`plugin/` is built in [Construct3-RAG](https://github.com/XHXIAIEIN/Construct3-RAG)
and pushed here by its workflow after each change. Do not edit a file under
`plugin/` here, because the next push replaces the folder. A change to the
skill, the data or the prompts goes to Construct3-RAG: `skills/`, `data/`,
`prompts/` and `scripts/plugin/` there, then `python scripts/build_plugin.py`.
Its `AGENTS.md` says how. New content for this repository goes in a folder
beside `plugin/`, with an `AGENTS.md` of its own.

| Path | What it holds |
|------|---------------|
| `plugin/.claude-plugin/plugin.json` | The plugin's manifest: name, version, description, keywords |
| `plugin/skills/construct3-agent-plugin/` | The skill: `SKILL.md`, its scripts, references and assets |
| `plugin/data/c3-schemas/` | The ACEs of every plugin, behavior and effect, one JSON file each, per locale |
| `plugin/data/c3-lang/` | The editor texts the checker and a preview's inspector read |
| `plugin/data/c3-new-project/` | The empty project the editor saves, which `new_project.py` copies |
| `plugin/data/*.bundle-*.json` | The TypeScript definitions, the example projects and the index of their ACEs, as bundles the scripts read |
| `plugin/prompts/` | Event sheet thinking, pitfalls and style, and the references for game feel, menus, dialogue and hand-edited project files |
| `plugin/agents/` | The `project-worker` sub-agent type, loaded with the plugin |
| `.claude/agents/` | The `ace-lookup` sub-agent for sessions in this repository |

Do not write the Construct 3 version or the counts into text, because every
data refresh changes them; read them from `plugin/data/c3-schemas/_index.json`.

## 2. Answer a Construct 3 fact question

Answer from the data. An ACE missing from the schema does not exist, unless
`plugin/data/c3-schemas/{locale}/_deprecated.json` lists it. Then the editor
deprecated it: an old project that uses it still opens, and a new project
should not use it.

Look an ACE up with the script, never by reading `plugins/system.json` or
`plugins/_common.json`, which run to thousands of lines and a reader cuts:

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
| What a field of a project file means | `plugin/skills/construct3-agent-plugin/references/` |

To the user, an ACE is its `display-text` in their language, with the
object's name and the parameters in words. The ids and the JSON stay in the
data and the tools.

## 3. Design event sheet logic

Before you design an interaction, data storage, timing or animation, read
and follow `plugin/prompts/event-sheet-thinking.md`. Then verify the names
with section 2. Events written into a project follow
`plugin/prompts/event-sheet-style.md`. A runtime behaviour of events that
changes which events are written is recorded in Construct3-RAG, under
`prompts/pitfalls/` there.

## 4. Use from a game project

A game project uses the plugin in one of three ways; the README says how
to install each:

- From Claude's directory or from this repository as a marketplace: the
  skill loads on its own when the user asks about a Construct 3 project.
- From a clone of this repository, linked into `~/.claude/skills/`.
- Without an install, by running the scripts with `--project <folder>`:

  ```bash
  python plugin/skills/construct3-agent-plugin/scripts/check_project.py --project <game folder>
  ```

Read `plugin/skills/construct3-agent-plugin/SKILL.md` before you read or
write the first project file. Before you hand a project over, make sure
that `check_project.py` reports no problems.

## 5. Change this repository

- A change under `plugin/` is made in Construct3-RAG, as section 1 says.
- The READMEs describe the plugin for people, in English and Chinese with
  the same content. `README.md` names no Chinese text besides its link to
  `README_CN.md`.
- A commit message names an issue of another repository in words or as a
  URL in backticks, never as `owner/repo#N` or `#N`, because GitHub turns
  those into a public cross-reference on that issue's timeline.
