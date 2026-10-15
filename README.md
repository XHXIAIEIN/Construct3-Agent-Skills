# Construct3-Agent-Skills

**English** | [中文](README_CN.md)

Construct3-Agent-Skills is the Construct 3 plugin for Claude Code. It lets Claude make and change [Construct 3](https://www.construct.net) games saved as folder projects. The plugin is the [`plugin/`](plugin/README.md) folder. It carries every condition, action, expression and effect as the Construct 3 editor defines them, in English and Chinese, and the `construct3-agent-plugin` skill, whose scripts use them. With the skill, Claude:

- looks up the exact JSON of a condition, action or expression before writing it, and the scripting API of a Construct plugin or behavior;
- prints an event sheet as events and changes it from a checked plan;
- starts a new project from the empty one the editor saves, or generates a whole project from a script;
- checks a project against the rules the editor applies when it opens one;
- opens the project in the Construct 3 editor, previews it and exports it.

## Install

Install the plugin in one of three ways:

- From Claude's directory, for the versions that Anthropic has reviewed. On claude.ai, open **Customize** > **Plugins**, search for Construct3 and select **Add**. Claude Code signed in to the same account downloads it at its next start. Each version waits for a review, so this copy can be some commits behind this repository.
- From this repository, to follow the released versions:

  ```bash
  claude plugin marketplace add XHXIAIEIN/Construct3-Agent-Skills
  claude plugin install construct3@construct3-agent-skills
  ```

  To bring Claude Code's copy up to the version in `plugin/.claude-plugin/plugin.json`, run `claude plugin update construct3@construct3-agent-skills`. Claude Code updates it on its own only when auto-update is on for the marketplace. To turn it on, run `/plugin` in a session, open the **Marketplaces** tab, select `construct3-agent-skills`, then select **Enable auto-update**.
- From a clone of this repository, so that the next session uses what `git pull` fetched: link `plugin/` into Claude Code's skills folder.
  - PowerShell: `New-Item -ItemType Junction -Path ~/.claude/skills/construct3 -Target <the clone>/plugin`
  - Other shells: `ln -s <the clone>/plugin ~/.claude/skills/construct3`

The scripts need Python 3.10 or later. Cutting pictures out of an image tool's output needs Pillow.

## Use

Ask Claude about a Construct 3 project in its folder: a change such as "add a double jump", or a problem such as "why does the editor refuse to open this project". The skill loads on its own for such a request. To start a game, ask for a new project in an empty folder.

The plugin also adds the sub-agent type `construct3:project-worker`, for a change or a lookup that the main agent hands over. It has only the tools the scripts need, so it starts with a fraction of the context a general-purpose sub-agent starts with.

## What runs and what reaches the network

- The scripts run on the machine with Python, on the files of the project and of the plugin.
- Opening, previewing, exporting or taking a picture of a project starts Edge, Chrome or Chromium, or the agent's browser tool, on the Construct 3 editor at `editor.construct.net`, with the project loaded from the machine. A preview runs at `preview.construct.net`. An export uses the Construct account that the user signs in to in that browser; the scripts store no password.
- When the plugin is a Git clone, the checker fetches that clone's remote at most once an hour to say when it is behind. Set `CONSTRUCT3_RAG_OFFLINE=1` to turn this off.

## Repository

```
plugin/                 The plugin: manifest, skill, data, prompts, agents
.claude-plugin/         The marketplace manifest, which names plugin/
.claude/agents/         The ace-lookup sub-agent for sessions in this repository
AGENTS.md               The guide for AI agents; CLAUDE.md imports it
```

`plugin/` is built in [Construct3-RAG](https://github.com/XHXIAIEIN/Construct3-RAG), which holds the data pipeline, the tests and the decision records. A workflow there pushes the built folder here after each change, so edits to `plugin/` go to that repository. The other files are this repository's own.

## License

MIT. The data comes from the Construct 3 editor, by Scirra Ltd.
