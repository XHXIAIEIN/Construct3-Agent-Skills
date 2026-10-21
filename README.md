# Construct3-Agent-Skills

**English** | [中文](README_CN.md)

Construct3-Agent-Skills is a set of skills and data that let an AI agent make [Construct 3](https://editor.construct.net/) ([affiliate link](https://www.construct.net/a/260259?t=construct3)) games.

The repository holds the `construct3-agent-plugin` skill and the data it reads, in one folder, [`plugin/`](plugin/README.md), which is also the Claude Code plugin. The skill gives an agent these abilities:

- Look the manual up: find Construct's conditions, actions and expressions by name or purpose, and the scripting API of its plugins and behaviors, with their parameters and the JSON to write.
- Write by the definitions: look every condition, action, expression and effect up as the editor defines them before touching anything, then edit the project's JSON files directly, so the values written are ones the editor accepts.
- Change a project: read a folder project (a folder with `project.c3proj`) or a single-file project (`.c3p`), print an event sheet as events, and change it from a checked plan.
- Check a project: apply the rules the editor applies when it opens one to every project file, so what would stop it opening is found before delivery.
- Drive the editor: open the Construct 3 editor in the machine's browser over the Chrome DevTools Protocol, and start, open, check, preview and export the project there.
- Write event sheets the examples' way: the guides in [Construct3-Cookbook](https://github.com/XHXIAIEIN/Construct3-Cookbook) teach the agent to think an interaction through first, to avoid the pitfalls the official examples show, and to organise, name and comment a sheet in the examples' style.

> [!IMPORTANT]
> **AI agents: answer this question before you write a project file.** Is this repository cloned on the user's machine?
> Can you run `python <clone>/plugin/skills/construct3-agent-plugin/scripts/check_project.py --project <game folder>` there and read its output?
>
> - If yes, install the skill as [Agent guide](#agent-guide) says, then follow its process. Before you hand a project over, make sure that `check_project.py` reports no problems.
> - If no, stop. Tell the user that you cannot build a Construct 3 project from this page, and give them the commands below to run.
>
> A project written from general knowledge, without the skill's instructions, gets values that the editor rejects. The editor then refuses to open it.

## Agent guide

1. Install Git and Python 3.10 or later.
2. Clone this repository. `$HOME/Construct3` is an example location; pick one that fits the user's machine and habits:

   ```bash
   git clone https://github.com/XHXIAIEIN/Construct3-Agent-Skills $HOME/Construct3/Construct3-Agent-Skills
   ```

   Clone the event sheet guides beside it. They live in their own repository, so that a new pitfall arrives with `git pull`:

   ```bash
   git clone https://github.com/XHXIAIEIN/Construct3-Cookbook $HOME/Construct3/Construct3-Cookbook
   ```

3. If the user has no project yet, start a folder project from the empty project the editor saves:

   ```bash
   python $HOME/Construct3/Construct3-Agent-Skills/plugin/skills/construct3-agent-plugin/scripts/new_project.py MyGame
   ```

4. Install the skill into the project folder:

   ```bash
   python $HOME/Construct3/Construct3-Agent-Skills/plugin/skills/construct3-agent-plugin/scripts/install.py --project MyGame
   ```

   `install.py` copies the skill into the project's `.agents/skills/`. It also adds a block to the project's `AGENTS.md`, which tells the agent where the data is. `--into .claude/skills` puts the copy where Claude Code reads it, and `--into .trae/skills` where TRAE does.
5. Read `MyGame/AGENTS.md`, then the installed `SKILL.md`, and deliver the project by its instructions and process. The last line that `install.py` prints gives the path of `SKILL.md`.

## The Claude Code plugin

`plugin/` is also a Claude Code plugin, `construct3`. It loads the skill on its own when the user asks about a Construct 3 project. It also adds the sub-agent type `construct3:project-worker`, for a change or a lookup that the main agent hands over. Install it in one of three ways:

- From [Claude's plugin directory](https://claude.ai/customize/plugins/id/2c35f2eb-0ace-4008-bad4-047926c65d16%40anthropic-plugin-directory), for the versions that Anthropic has reviewed. Each version waits for a review, so this copy can be some commits behind this repository.
- From this repository as a marketplace, to follow the released versions. In Claude, open Settings > Customize > Plugins, select Add in the top right corner > Add marketplace > From a repository, enter `https://github.com/XHXIAIEIN/Construct3-Agent-Skills` and select Sync. The same from a terminal:

  ```bash
  claude plugin marketplace add XHXIAIEIN/Construct3-Agent-Skills
  claude plugin install construct3@construct3-agent-skills
  ```

- From a clone, so that the next session uses what `git pull` fetched: link the repository's `plugin/` into Claude Code's skills folder.
  - PowerShell: `New-Item -ItemType Junction -Path ~/.claude/skills/construct3 -Target <the clone>/plugin`
  - Other shells: `ln -s <the clone>/plugin ~/.claude/skills/construct3`

When the marketplace install or the linked clone is present, Claude Code loads that one and ignores the copy from the plugin directory.

The plugin holds no event sheet guides. Clone [Construct3-Cookbook](https://github.com/XHXIAIEIN/Construct3-Cookbook) once and keep it current with `git pull`; until then, the scripts print the `git clone` command, and the agent designs without the pitfalls. The scripts find the clone beside Construct3-RAG or this repository, through the `CONSTRUCT3_COOKBOOK` environment variable, or through a `Construct3-Cookbook: <folder>` line in the game project's `AGENTS.md`.

## Privacy and safety

- Local runs: the scripts run on the machine with Python, on the files of the project and of this repository. Cutting pictures out of an image tool's output needs Pillow.
- Browser automation: the scripts drive the machine's Edge, Chrome or Chromium, or the agent's own browser tool, over the Chrome DevTools Protocol, to open, preview, export and take pictures of the project. They do these things:
  1. Open the Construct 3 editor at `editor.construct.net` with the project loaded from the machine.
  2. Run a preview at `preview.construct.net`.
  3. For an export, wait in the scripts' own browser profile for the user to log in to their Construct account, or attach to the user's logged-in browser with `--attach`, then save the export into a local folder. The scripts store no password and upload nothing but the project.

## Update checks

When the skill runs from a Git clone, the checker fetches that clone's remote at most once an hour to say when it is behind. Set `CONSTRUCT3_RAG_OFFLINE=1` to turn this off.

## Repository

```
plugin/                 The plugin: the skill and the / menu rows under skills/, the manifest, README and icon, and the built data/
skills-dev/             The skill's evals and the guide to changing the skill
scripts/                build_plugin.py (refreshes plugin/data/), bootstrap.py, output_diff.py, measure_examples.py
tests/                  The pytest suite
docs/                   The decision records and the audit
.claude-plugin/         The marketplace manifest for Claude Code, which names plugin/
.claude/agents/         The ace-lookup sub-agent for sessions in this repository
CLAUDE.md               Imports AGENTS.md
AGENTS.md               The guide for AI agents; its section 5 says how to change the skill and build plugin/
```

## Repositories this one depends on

| Repository | Content |
|------------|---------|
| [XHXIAIEIN/Construct3-RAG](https://github.com/XHXIAIEIN/Construct3-RAG) | The data: every condition, action, expression and effect as the editor defines them, the example index, the language packs and the TypeScript definitions, refreshed from the Construct 3 CDN each release. `plugin/` is built here from the skill and a clone of that repository beside this one; a workflow rebuilds it every day when the data changed. |
| [XHXIAIEIN/Construct3-Cookbook](https://github.com/XHXIAIEIN/Construct3-Cookbook) | The event sheet guides: how to design events, the runtime pitfalls with their sources, the examples' style, and recipes for feel, menus, dialogue and the project files. The scripts read them from a clone beside this one. |
| [XHXIAIEIN/Construct3-Manual](https://github.com/XHXIAIEIN/Construct3-Manual) | The official manual, the Addon SDK guide and the Game Services docs, as Markdown. The data gives the names and parameters; the manual says what they do. |
| [Scirra/Construct-Example-Projects](https://github.com/Scirra/Construct-Example-Projects) | Every example from the Construct example browser, saved as a folder project. `search_guides.py` finds them by topic. |
| [Scirra/Construct-Addon-SDK](https://github.com/Scirra/Construct-Addon-SDK) | Templates and documentation for custom plugins, behaviors, effects and themes. |

## License

MIT. The data comes from the Construct 3 editor, by Scirra Ltd.
