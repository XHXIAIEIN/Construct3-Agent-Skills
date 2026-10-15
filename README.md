# Construct3-Agent-Skills

**English** | [中文](README_CN.md)

Construct3-Agent-Skills is a set of skills and data that let an AI agent make [Construct 3](https://www.construct.net) games. Any agent that runs a shell and Python can use it: Claude Code, Codex, TRAE, Cursor. The repository holds, under [`plugin/`](plugin/README.md):

- the `construct3-agent-plugin` skill, whose scripts:
  - look up the exact JSON of a condition, action or expression, and the scripting API of a Construct plugin or behavior;
  - print an event sheet as events and change it from a checked plan;
  - start a project from the empty one the editor saves, or generate a whole project from a script;
  - check a project against the rules the editor applies when it opens one;
  - open the project in the Construct 3 editor, preview it and export it;
- every condition, action, expression and effect as the Construct 3 editor defines them, in English and Chinese, which the scripts and the agent read directly;
- the prompts for event sheet design: how to think an interaction through, the pitfalls the official examples show, and the style the examples are written in.

> [!IMPORTANT]
> **AI agents: answer this question before you write a project file.** Is this repository cloned on the user's machine? Can you run `python <clone>/plugin/skills/construct3-agent-plugin/scripts/check_project.py --project <game folder>` there and read its output?
>
> - If yes, follow [Use with any agent](#use-with-any-agent), then the installed `SKILL.md`. Before you hand a project over, make sure that `check_project.py` reports no problems.
> - If no, stop. Tell the user that you cannot build a Construct 3 project from this page, and give them the commands below to run.
>
> A project written from general knowledge, without the scripts, gets values that the editor rejects. The editor then refuses to open it.

## Use with any agent

1. Install Git and Python 3.10 or later.
2. Clone this repository:

   ```bash
   git clone https://github.com/XHXIAIEIN/Construct3-Agent-Skills $HOME/Construct3/Construct3-Agent-Skills
   ```

3. If the game has no project yet, start one from the empty project the editor saves:

   ```bash
   python $HOME/Construct3/Construct3-Agent-Skills/plugin/skills/construct3-agent-plugin/scripts/new_project.py MyGame
   ```

4. Install the skill into the project:

   ```bash
   python $HOME/Construct3/Construct3-Agent-Skills/plugin/skills/construct3-agent-plugin/scripts/install.py --project MyGame
   ```

   `install.py` copies the skill into the project's `.agents/skills/`. It also adds a block to the project's `AGENTS.md`, which tells the agent where the data is. `--into .claude/skills` puts the copy where Claude Code reads it, and `--into .trae/skills` where TRAE does.
5. Read `MyGame/AGENTS.md`, then the installed `SKILL.md`. The last line that `install.py` prints gives its path.

The scripts also run from the clone without an install, with `--project <game folder>`. An installed copy says when it differs from the clone and prints the command that refreshes it.

## The Claude Code plugin

`plugin/` is also a Claude Code plugin, `construct3`. It loads the skill on its own when the user asks about a Construct 3 project. It also adds the sub-agent type `construct3:project-worker`, for a change or a lookup that the main agent hands over. Install it in one of three ways:

- From Claude's directory, for the versions that Anthropic has reviewed. On claude.ai, open **Customize** > **Plugins**, search for Construct3 and select **Add**. Claude Code signed in to the same account downloads it at its next start. Each version waits for a review, so this copy can be some commits behind this repository.
- From this repository as a marketplace, to follow the released versions:

  ```bash
  claude plugin marketplace add XHXIAIEIN/Construct3-Agent-Skills
  claude plugin install construct3@construct3-agent-skills
  ```

  To bring Claude Code's copy up to the version in `plugin/.claude-plugin/plugin.json`, run `claude plugin update construct3@construct3-agent-skills`. Claude Code updates it on its own only when auto-update is on for the marketplace. To turn it on:
  1. Run `/plugin` in a session.
  2. Open the **Marketplaces** tab and select `construct3-agent-skills`.
  3. Select **Enable auto-update**.
- From a clone, so that the next session uses what `git pull` fetched: link `plugin/` into Claude Code's skills folder.
  - PowerShell: `New-Item -ItemType Junction -Path ~/.claude/skills/construct3 -Target <the clone>/plugin`
  - Other shells: `ln -s <the clone>/plugin ~/.claude/skills/construct3`

When the marketplace install or the linked clone is present, Claude Code loads that one and ignores the copy from Claude's directory.

## What runs and what reaches the network

- The scripts run on the machine with Python, on the files of the project and of this repository. Cutting pictures out of an image tool's output needs Pillow.
- Opening, previewing, exporting or taking a picture of a project starts Edge, Chrome or Chromium, or the agent's browser tool, on the Construct 3 editor at `editor.construct.net`, with the project loaded from the machine. A preview runs at `preview.construct.net`. An export uses the Construct account that the user signs in to in that browser; the scripts store no password.
- When the skill runs from a Git clone, the checker fetches that clone's remote at most once an hour to say when it is behind. Set `CONSTRUCT3_RAG_OFFLINE=1` to turn this off.

## Repository

```
plugin/                 The skill, the data, the prompts and the plugin manifest
.claude-plugin/         The marketplace manifest for Claude Code, which names plugin/
.claude/agents/         The ace-lookup sub-agent for sessions in this repository
AGENTS.md               The guide for AI agents; CLAUDE.md imports it
```

`plugin/` is built in [Construct3-RAG](https://github.com/XHXIAIEIN/Construct3-RAG), which holds the data pipeline, the tests and the decision records. A workflow there pushes the built folder here after each change, so a change to the skill, the data or the prompts goes to that repository. The other files are this repository's own.

## License

MIT. The data comes from the Construct 3 editor, by Scirra Ltd.
