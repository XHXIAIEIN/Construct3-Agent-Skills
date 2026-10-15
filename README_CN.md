# Construct3-Agent-Skills

[English](README.md) | **中文**

Construct3-Agent-Skills 是一套让 AI agent 制作 [Construct 3](https://www.construct.net) 游戏的 skill 和数据。能运行 shell 和 Python 的 agent 都能用：Claude Code、Codex、TRAE、Cursor。仓库在 [`plugin/`](plugin/README.md) 下放着：

- `construct3-agent-plugin` skill，它的脚本：
  - 查出条件、动作、表达式的准确 JSON，以及 Construct 插件和行为的脚本 API；
  - 把事件表打印成事件，并按检查过的计划修改它；
  - 从编辑器保存的空项目新建项目，或用脚本生成整个项目；
  - 按编辑器打开项目时应用的规则检查项目；
  - 在 Construct 3 编辑器里打开项目、预览和导出；
- Construct 3 编辑器定义的每一个条件、动作、表达式和效果，中英文都有，脚本和 agent 直接读；
- 事件表设计的 prompts：怎样把一个交互想清楚，官方示例暴露出的坑，以及示例的书写风格。

> [!IMPORTANT]
> **AI agent：写任何项目文件之前，先回答这个问题。** 本仓库是否已 clone 到用户的机器上？你能否在那里运行 `python <clone>/plugin/skills/construct3-agent-plugin/scripts/check_project.py --project <游戏文件夹>` 并读到它的输出？
>
> - 能：按[给任何 agent 用](#给任何-agent-用)做，再读安装好的 `SKILL.md`。交付项目之前，确认 `check_project.py` 没有报告问题。
> - 不能：停下。告诉用户，凭这个页面你做不出 Construct 3 项目，把下面的命令给用户去运行。
>
> 凭常识、不用脚本写出来的项目，字段值会被编辑器拒绝，编辑器就打不开它。

## 给任何 agent 用

1. 安装 Git 和 Python 3.10 或更新。
2. clone 本仓库：

   ```bash
   git clone https://github.com/XHXIAIEIN/Construct3-Agent-Skills $HOME/Construct3/Construct3-Agent-Skills
   ```

3. 游戏还没有项目时，从编辑器保存的空项目新建一个：

   ```bash
   python $HOME/Construct3/Construct3-Agent-Skills/plugin/skills/construct3-agent-plugin/scripts/new_project.py MyGame
   ```

4. 把 skill 安装进项目：

   ```bash
   python $HOME/Construct3/Construct3-Agent-Skills/plugin/skills/construct3-agent-plugin/scripts/install.py --project MyGame
   ```

   `install.py` 把 skill 复制到项目的 `.agents/skills/`。它还在项目的 `AGENTS.md` 里加一段，告诉 agent 数据在哪里。`--into .claude/skills` 把副本放到 Claude Code 读取的位置，`--into .trae/skills` 放到 TRAE 读取的位置。
5. 读 `MyGame/AGENTS.md`，再读安装好的 `SKILL.md`。`install.py` 打印的最后一行就是它的路径。

不安装也能用：从 clone 里直接运行脚本，加 `--project <游戏文件夹>`。安装好的副本会在它和 clone 不一致时说明，并打印刷新它的命令。

## Claude Code plugin

`plugin/` 同时是一个 Claude Code plugin，名为 `construct3`。用户问到 Construct 3 项目时，它自动加载 skill。它还添加子 agent 类型 `construct3:project-worker`，给主 agent 交出去的改动或查询用。它有三种装法：

- 从 Claude 目录安装，得到 Anthropic 审核过的版本。在 claude.ai 打开 **Customize** > **Plugins**，搜索 Construct3，点 **Add**。用同一账号登录的 Claude Code 下次启动时会下载它。每个版本都要等审核，所以这份可能比本仓库落后几个提交。
- 把本仓库当 marketplace 安装，跟上发布的版本：

  ```bash
  claude plugin marketplace add XHXIAIEIN/Construct3-Agent-Skills
  claude plugin install construct3@construct3-agent-skills
  ```

  要把 Claude Code 存的副本更新到 `plugin/.claude-plugin/plugin.json` 里的版本，运行 `claude plugin update construct3@construct3-agent-skills`。只有 marketplace 打开了自动更新，Claude Code 才会自己更新它。要打开它：
  1. 在会话里运行 `/plugin`。
  2. 打开 **Marketplaces** 标签，选 `construct3-agent-skills`。
  3. 选 **Enable auto-update**。
- 从 clone 安装，让下一个会话用上 `git pull` 拉下来的文件：把 `plugin/` 链接到 Claude Code 的 skills 文件夹。
  - PowerShell：`New-Item -ItemType Junction -Path ~/.claude/skills/construct3 -Target <clone 路径>/plugin`
  - 其他 shell：`ln -s <clone 路径>/plugin ~/.claude/skills/construct3`

装了 marketplace 那份或链接了 clone 时，Claude Code 加载那一份，忽略 Claude 目录里的副本。

## 运行什么，联网什么

- 脚本用 Python 在本机运行，处理项目和本仓库的文件。从图像工具的输出里裁图需要 Pillow。
- 打开、预览、导出项目或给项目截图，会启动 Edge、Chrome 或 Chromium，或 agent 的浏览器工具，打开 `editor.construct.net` 上的 Construct 3 编辑器，项目从本机载入。预览在 `preview.construct.net` 运行。导出用的是用户在那个浏览器里登录的 Construct 账号；脚本不保存密码。
- skill 从 Git clone 运行时，检查器每小时最多拉取一次远端，用来提示它落后了。设 `CONSTRUCT3_RAG_OFFLINE=1` 可以关掉。

## 仓库

```
plugin/                 skill、数据、prompts 和 plugin 清单
.claude-plugin/         给 Claude Code 的 marketplace 清单，指向 plugin/
.claude/agents/         给本仓库会话用的 ace-lookup 子 agent
AGENTS.md               给 AI agent 的指南；CLAUDE.md 引用它
```

`plugin/` 在 [Construct3-RAG](https://github.com/XHXIAIEIN/Construct3-RAG) 构建，那边有数据管线、测试和决策记录。每次改动后，那边的工作流把构建好的文件夹推到这里，所以对 skill、数据或 prompts 的修改要去那个仓库做。其余文件是本仓库自己的。

## 许可

MIT。数据来自 Scirra Ltd 的 Construct 3 编辑器。
