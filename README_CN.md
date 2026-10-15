# Construct3-Agent-Skills

[English](README.md) | **中文**

Construct3-Agent-Skills 是一套让 AI agent 制作 [Construct 3](https://editor.construct.net/) 游戏的 skill 和数据集。

仓库在 [`plugin/`](plugin/README.md) 下放着 `construct3-agent-plugin` skill，它给 agent 这些能力：

- 查手册：按名字或用途找到 Construct 的条件、动作和表达式，以及插件和行为的脚本 API，连同参数和要写的 JSON。
- 按定义写：动手之前先查编辑器定义的每一个条件、动作、表达式和效果，再直接编辑项目的 JSON 文件，所以写出的值编辑器认得。
- 改项目：读文件夹项目（含 `project.c3proj`）或单文件项目（`.c3p`），把事件表打印成事件，按检查过的计划改它。
- 查项目：按编辑器打开项目时应用的规则检查每个项目文件，打不开的原因在交付前就找到。
- 驱动编辑器：通过 Chrome DevTools Protocol 驱动本机浏览器打开 Construct 3 编辑器，新建、打开、检查、预览和导出项目。
- 事件表的写法：prompts 教 agent 先把一个交互想清楚，避开官方示例暴露的坑，按示例的风格组织、命名和注释事件表。

> [!IMPORTANT]
> **AI agent：写任何项目文件之前，先回答这个问题。** 本仓库是否已 clone 到用户的机器上？
> 你能否在那里运行 `python <clone>/plugin/skills/construct3-agent-plugin/scripts/check_project.py --project <游戏文件夹>` 并读到它的输出？
>
> - 能：按 [Agent 使用指南](#agent-使用指南) 的步骤安装 skill，再按它的流程做。交付项目之前，确认 `check_project.py` 没有报告问题。
> - 不能：停下。告诉用户，凭这个页面你做不出 Construct 3 项目，把下面的命令给用户去运行。
>
> 不按 skill 的指令、仅凭常识写出来的项目，字段值会被编辑器拒绝，编辑器就打不开它。

## Agent 使用指南

1. 安装 Git 和 Python 3.10 或更新。
2. clone 本仓库。`$HOME/Construct3` 是示例位置，按用户的环境和习惯选：

   ```bash
   git clone https://github.com/XHXIAIEIN/Construct3-Agent-Skills $HOME/Construct3/Construct3-Agent-Skills
   ```

3. 用户还没有项目时，从编辑器保存的空项目新建一个文件夹项目：

   ```bash
   python $HOME/Construct3/Construct3-Agent-Skills/plugin/skills/construct3-agent-plugin/scripts/new_project.py MyGame
   ```

4. 把 skill 安装进项目文件夹：

   ```bash
   python $HOME/Construct3/Construct3-Agent-Skills/plugin/skills/construct3-agent-plugin/scripts/install.py --project MyGame
   ```

   `install.py` 把 skill 复制到项目的 `.agents/skills/`。它还在项目的 `AGENTS.md` 里加一段，告诉 agent 数据在哪里。`--into .claude/skills` 把副本放到 Claude Code 读取的位置，`--into .trae/skills` 放到 TRAE 读取的位置。
5. 读 `MyGame/AGENTS.md`，再读安装好的 `SKILL.md`，按它的指令和流程向用户交付项目。`install.py` 打印的最后一行就是 `SKILL.md` 的路径。

## Claude Code plugin

`plugin/` 同时是一个 Claude Code plugin，名为 `construct3`。用户问到 Construct 3 项目时，它自动加载 skill。它还添加子 agent 类型 `construct3:project-worker`，给主 agent 交出去的改动或查询用。它有三种安装方式：

- 从 [Claude 插件目录](https://claude.ai/customize/plugins/id/2c35f2eb-0ace-4008-bad4-047926c65d16%40anthropic-plugin-directory)安装，得到 Anthropic 审核过的版本。每个版本都要等审核，所以这份可能比本仓库落后几个提交。
- 把本仓库作为插件市场安装，跟上发布的版本。在 Claude 里打开 设置 > 自定义 > 插件，点右上角的 添加 > 添加市场 > 从仓库添加，填入 `https://github.com/XHXIAIEIN/Construct3-Agent-Skills`，点同步。终端里的等价命令：

  ```bash
  claude plugin marketplace add XHXIAIEIN/Construct3-Agent-Skills
  claude plugin install construct3@construct3-agent-skills
  ```

- 从 clone 安装，让下一个会话用上 `git pull` 拉下来的文件：把仓库里的 `plugin/` 链接到 Claude Code 的 skills 文件夹。
  - PowerShell：`New-Item -ItemType Junction -Path ~/.claude/skills/construct3 -Target <clone 路径>/plugin`
  - 其他 shell：`ln -s <clone 路径>/plugin ~/.claude/skills/construct3`

装了市场那份或链接了 clone 时，Claude Code 加载那一份，忽略插件目录里的副本。

## 隐私和安全性

- 本机运行：脚本用 Python 在本机运行，处理项目和本仓库的文件。从图像工具的输出里裁图需要 Pillow。
- 浏览器自动化：脚本通过 Chrome DevTools Protocol 驱动本机的 Edge、Chrome 或 Chromium，或 agent 自带的浏览器工具，用它打开、预览、导出项目和截图。它做这些事：
  1. 打开 `editor.construct.net` 上的 Construct 3 编辑器，从本机载入项目。
  2. 在 `preview.construct.net` 运行预览。
  3. 导出项目时，在脚本自己的浏览器配置里等用户登录 Construct 账号，或者用 `--attach` 接入用户已登录的浏览器，再把导出结果保存到本地文件夹。脚本不保存密码，也不上传项目之外的任何数据。

## 自动检查更新

skill 从 Git clone 运行时，检查器每小时最多拉取一次远端，用来提示它落后了。设 `CONSTRUCT3_RAG_OFFLINE=1` 可以关掉。

## 仓库结构

```
plugin/                 skill、数据、prompts 和 plugin 清单
.claude-plugin/         给 Claude Code 的 marketplace 清单，指向 plugin/
.claude/agents/         给本仓库会话用的 ace-lookup 子 agent
CLAUDE.md               引用 AGENTS.md
AGENTS.md               给 AI agent 的指南
```

## 其他依赖仓库

| 仓库 | 内容 |
|------|------|
| [XHXIAIEIN/Construct3-RAG](https://github.com/XHXIAIEIN/Construct3-RAG) | 构建 `plugin/` 的地方：数据管线、测试和决策记录。每次改动后，那边的工作流把构建好的文件夹推到这里，所以对 skill、数据或 prompts 的修改要去那个仓库做。 |
| [XHXIAIEIN/Construct3-Manual](https://github.com/XHXIAIEIN/Construct3-Manual) | 官方手册、Addon SDK 指南和 Game Services 文档的 Markdown 版。数据给出名称和参数，手册说明它们做什么。 |
| [Scirra/Construct-Example-Projects](https://github.com/Scirra/Construct-Example-Projects) | 示例浏览器里的每一个官方示例，保存为文件夹项目。`search_guides.py` 按主题找到它们。 |
| [Scirra/Construct-Addon-SDK](https://github.com/Scirra/Construct-Addon-SDK) | 自定义插件、行为、效果和主题的模板和文档。 |

## 许可

MIT。数据来自 Scirra Ltd 的 Construct 3 编辑器。
