# Construct3-Agent-Skills

[English](README.md) | **中文**

Construct3-Agent-Skills 是 Claude Code 的 Construct 3 plugin。它让 Claude 制作和修改以文件夹形式保存的 [Construct 3](https://www.construct.net) 游戏。plugin 就是 [`plugin/`](plugin/README.md) 文件夹。它带着 Construct 3 编辑器定义的每一个条件、动作、表达式和效果，中英文都有，还带着 `construct3-agent-plugin` skill，它的脚本使用这些数据。有了这个 skill，Claude 可以：

- 写条件、动作或表达式之前，先查出准确的 JSON，也能查 Construct 插件和行为的脚本 API；
- 把事件表打印成事件，并按检查过的计划修改它；
- 从编辑器保存的空项目新建项目，或用脚本生成整个项目；
- 按编辑器打开项目时应用的规则检查项目；
- 在 Construct 3 编辑器里打开项目、预览和导出。

## 安装

plugin 有三种装法：

- 从 Claude 目录安装，得到 Anthropic 审核过的版本。在 claude.ai 打开 **Customize** > **Plugins**，搜索 Construct3，点 **Add**。用同一账号登录的 Claude Code 下次启动时会下载它。每个版本都要等审核，所以这份可能比本仓库落后几个提交。
- 从本仓库安装，跟上发布的版本：

  ```bash
  claude plugin marketplace add XHXIAIEIN/Construct3-Agent-Skills
  claude plugin install construct3@construct3-agent-skills
  ```

  要把 Claude Code 存的副本更新到 `plugin/.claude-plugin/plugin.json` 里的版本，运行 `claude plugin update construct3@construct3-agent-skills`。只有 marketplace 打开了自动更新，Claude Code 才会自己更新它。要打开它，在会话里运行 `/plugin`，打开 **Marketplaces** 标签，选 `construct3-agent-skills`，再选 **Enable auto-update**。
- 从本仓库的 clone 安装，让下一个会话用上 `git pull` 拉下来的文件：把 `plugin/` 链接到 Claude Code 的 skills 文件夹。
  - PowerShell：`New-Item -ItemType Junction -Path ~/.claude/skills/construct3 -Target <clone 路径>/plugin`
  - 其他 shell：`ln -s <clone 路径>/plugin ~/.claude/skills/construct3`

脚本需要 Python 3.10 或更新。从图像工具的输出里裁图需要 Pillow。

## 使用

在 Construct 3 项目的文件夹里向 Claude 提需求：一个改动，比如“加一个二段跳”；或一个问题，比如“为什么编辑器打不开这个项目”。这类请求会自动加载 skill。要开始一个游戏，在空文件夹里要一个新项目。

plugin 还会添加子 agent 类型 `construct3:project-worker`，给主 agent 交出去的改动或查询用。它只带脚本需要的工具，所以起步时占的上下文只有通用子 agent 的一小部分。

## 运行什么，联网什么

- 脚本用 Python 在本机运行，处理项目和 plugin 的文件。
- 打开、预览、导出项目或给项目截图，会启动 Edge、Chrome 或 Chromium，或 agent 的浏览器工具，打开 `editor.construct.net` 上的 Construct 3 编辑器，项目从本机载入。预览在 `preview.construct.net` 运行。导出用的是用户在那个浏览器里登录的 Construct 账号；脚本不保存密码。
- plugin 是 Git clone 时，检查器每小时最多拉取一次远端，用来提示它落后了。设 `CONSTRUCT3_RAG_OFFLINE=1` 可以关掉。

## 仓库

```
plugin/                 plugin 本身：清单、skill、数据、prompts、agents
.claude-plugin/         marketplace 清单，指向 plugin/
.claude/agents/         给本仓库会话用的 ace-lookup 子 agent
AGENTS.md               给 AI agent 的指南；CLAUDE.md 引用它
```

`plugin/` 在 [Construct3-RAG](https://github.com/XHXIAIEIN/Construct3-RAG) 构建，那边有数据管线、测试和决策记录。每次改动后，那边的工作流把构建好的文件夹推到这里，所以对 `plugin/` 的修改要去那个仓库做。其余文件是本仓库自己的。

## 许可

MIT。数据来自 Scirra Ltd 的 Construct 3 编辑器。
