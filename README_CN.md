# Construct3-Agent-Skills

[English](README.md) | **中文**

Construct3-Agent-Skills 是一套让 AI agent 制作 [Construct 3](https://editor.construct.net/)（[推荐链接](https://www.construct.net/a/260259?t=construct3)）游戏的 skill 和数据集。

仓库把 `construct3-agent-plugin` skill 和它读取的数据放在一个文件夹里：[`plugin/`](plugin/README.md)。这个文件夹同时就是 Claude Code plugin。有了 skill，agent 能做这些事：

- 查手册：按名字或用途找到 Construct 的条件、动作和表达式，以及插件和行为的脚本 API。每个结果都带着参数和要写的 JSON。
- 按定义写：动手之前，agent 先查编辑器定义的每一个条件、动作、表达式和滤镜。然后它直接编辑项目的 JSON 文件，所以写出的值都是编辑器接受的值。
- 改项目：读文件夹项目（含 `project.c3proj`）或单文件项目（`.c3p`），把事件表打印成事件，再按检查过的计划改这个事件表。
- 查项目：按编辑器打开项目时应用的规则，检查每一个项目文件。这样 agent 在交付前就能找到让项目打不开的原因。
- 驱动编辑器：通过 Chrome DevTools Protocol 在本机浏览器里打开 Construct 3 编辑器，再在那里新建、打开、检查、预览和导出项目。
- 按示例的方式写事件表：[Construct3-Cookbook](https://github.com/XHXIAIEIN/Construct3-Cookbook) 里的指引教 agent 先把一个交互想清楚。它们还教 agent 避开官方示例暴露的坑，并按示例的风格组织、命名和注释事件表。

> [!IMPORTANT]
> **AI agent：写任何项目文件之前，先回答这个问题。** 本仓库是否已 clone 到用户的机器上？
> 你能否在那里运行 `python <clone>/plugin/skills/construct3-agent-plugin/scripts/lookup_ace.py System wait`，并在输出里读到 `action wait - Wait [system]` 这一行？
>
> - 能：按 [Agent 使用指南](#agent-使用指南) 的步骤安装 skill，再按它的流程做。交付项目之前，确认 `check_project.py` 没有报告问题。
> - 不能：停下。告诉用户，凭这个页面你做不出 Construct 3 项目，再把下面的命令给用户去运行。
>
> 如果不按 skill 的指令、仅凭常识写项目，字段值会被编辑器拒绝，编辑器就打不开这个项目。

## Agent 使用指南

1. 安装 Git 和 Python 3.10 或更新。
2. clone 本仓库。`$HOME/Construct3` 是示例位置，所以按用户的机器和习惯选一个位置：

   ```bash
   git clone https://github.com/XHXIAIEIN/Construct3-Agent-Skills $HOME/Construct3/Construct3-Agent-Skills
   ```

   把事件表指引 clone 到它旁边。指引单独放在一个仓库里，新的陷阱条目 `git pull` 就能拿到：

   ```bash
   git clone https://github.com/XHXIAIEIN/Construct3-Cookbook $HOME/Construct3/Construct3-Cookbook
   ```

3. 如果用户还没有项目，从编辑器保存的空项目新建一个文件夹项目：

   ```bash
   python $HOME/Construct3/Construct3-Agent-Skills/plugin/skills/construct3-agent-plugin/scripts/new_project.py MyGame
   ```

4. 把 skill 安装进项目文件夹：

   ```bash
   python $HOME/Construct3/Construct3-Agent-Skills/plugin/skills/construct3-agent-plugin/scripts/install.py --project MyGame
   ```

   `install.py` 把 skill 复制到项目的 `.agents/skills/`。它还在项目的 `AGENTS.md` 里加一段，这一段告诉 agent 数据在哪里。要把副本放到 Claude Code 读取的位置，加 `--into .claude/skills`。

   其他 agent 读各自的文件夹：TRAE 加 `--into .trae/skills`，WorkBuddy 加 `--into .workbuddy/skills`，Cursor 加 `--into .cursor/skills`。Cursor 也读 `.agents/skills/`，所以默认位置的副本它已经能读到；TRAE 在设置里打开这一项后，也会读这个文件夹。
5. 读 `MyGame/AGENTS.md`，再读安装好的 `SKILL.md`。按 `SKILL.md` 的指令和流程向用户交付项目。`install.py` 打印的最后一行就是 `SKILL.md` 的路径。

## Claude Code plugin

`plugin/` 同时是一个 Claude Code plugin，名为 `construct3`。用户问到 Construct 3 项目时，它自动加载 skill。它还添加子 agent 类型 `construct3:project-worker`，接手主 agent 交出去的改动或查询。这个 plugin 有三种安装方式：

- 从 [Claude 插件目录](https://claude.ai/customize/plugins/id/2c35f2eb-0ace-4008-bad4-047926c65d16%40anthropic-plugin-directory)安装，得到 Anthropic 审核过的版本。每个版本都要等审核，所以这份副本可能比本仓库落后几个提交。
- 把本仓库作为插件市场安装，跟上发布的版本。在 Claude 里打开 设置 > 自定义 > 插件。点右上角的 添加 > 添加市场 > 从仓库添加，填入 `https://github.com/XHXIAIEIN/Construct3-Agent-Skills`，再点同步。在终端里做同样的事，运行：

  ```bash
  claude plugin marketplace add XHXIAIEIN/Construct3-Agent-Skills
  claude plugin install construct3@construct3-agent-skills
  ```

- 从 clone 安装，让下一个会话用上 `git pull` 拉下来的文件。把仓库里的 `plugin/` 链接到 Claude Code 的 skills 文件夹：
  - PowerShell：`New-Item -ItemType Junction -Path ~/.claude/skills/construct3 -Target <clone 路径>/plugin`
  - 其他 shell：`ln -s <clone 路径>/plugin ~/.claude/skills/construct3`

如果装了市场那份或链接了 clone，Claude Code 加载那一份，忽略插件目录里的副本。

插件里不带事件表指引。先 clone 一次 [Construct3-Cookbook](https://github.com/XHXIAIEIN/Construct3-Cookbook)，之后用 `git pull` 保持最新；没 clone 之前，脚本会打印 `git clone` 命令，agent 设计时就读不到陷阱条目。脚本在 Construct3-RAG 或本仓库旁边找这个 clone，也认环境变量 `CONSTRUCT3_COOKBOOK` 和游戏项目 `AGENTS.md` 里的 `Construct3-Cookbook: <文件夹>` 行。

## 隐私和安全性

- 本机运行：脚本用 Python 在本机运行，处理项目和本仓库的文件。要从图像工具的输出里裁图，脚本需要 Pillow。
- 浏览器自动化：脚本通过 Chrome DevTools Protocol 驱动本机的 Edge、Chrome 或 Chromium，或 agent 自带的浏览器工具。它们用浏览器打开、预览和导出项目，并给项目截图。它们打开 `editor.construct.net` 上的 Construct 3 编辑器，从本机载入项目，并在 `preview.construct.net` 运行预览。
- 导出：脚本在自己的浏览器配置里等用户登录 Construct 账号，或者用 `--attach` 接入用户已登录的浏览器。然后把导出结果保存到本地文件夹。密码由用户在 Construct 自己的登录页里输入，脚本不读取也不保存。脚本只把编辑器要读的项目文件交给编辑器；项目里有形似密钥的字符串时，导出在浏览器启动前就会停下。

## 自动检查更新

如果 skill 从 GitHub 的 Git clone 运行，检查器会读取 clone 上游分支的插件版本号。它通过 HTTPS 读取，每小时最多一次，不使用用户的 Git 凭据。如果上游的版本较新，检查器把更新 clone 的 `git pull --ff-only` 交给 agent 执行。如果 clone 里有它自己的改动，检查器让 agent 询问用户。对存放坑点的 Construct3-Cookbook clone，检查器也这样做：它用同样的方式从 GitHub 的 API 读取 clone 上游分支的最新提交，如果 clone 里没有这个提交，就把 `git pull --ff-only` 交给 agent。要关掉这些检查，设 `CONSTRUCT3_RAG_OFFLINE=1`。

## 仓库结构

```
plugin/                 plugin 本身：skills/ 下是 skill 和 / 菜单的条目，还有清单、README、图标，以及构建出的 data/
dev/                    只有维护者用的东西：evals、tests/、scripts/（build_plugin.py 刷新 plugin/data/），以及 AGENTS.md：改 skill 和构建 plugin/ 的指南
scripts/                bootstrap.py：clone 兄弟仓库并安装 skill
docs/                   决策记录和审查
.claude-plugin/         给 Claude Code 的 marketplace 清单，指向 plugin/
.claude/agents/         给本仓库会话用的 ace-lookup 子 agent
CLAUDE.md               引用 AGENTS.md
AGENTS.md               给 AI agent 的指南；维护者从 dev/AGENTS.md 开始
```

## 其他依赖仓库

| 仓库 | 内容 |
|------|------|
| [XHXIAIEIN/Construct3-RAG](https://github.com/XHXIAIEIN/Construct3-RAG) | 数据：编辑器定义的每一个条件、动作、表达式和滤镜，示例索引、语言包和 TypeScript 定义。每个版本发布时，数据从 Construct 3 CDN 刷新。本仓库用 skill 和放在旁边的那个仓库的 clone 构建 `plugin/`。如果数据变了，工作流每天重新构建一次 `plugin/`。 |
| [XHXIAIEIN/Construct3-Cookbook](https://github.com/XHXIAIEIN/Construct3-Cookbook) | 事件表指引：怎么设计事件、带出处的运行时陷阱、官方示例的写法，以及手感、菜单、对话和工程文件的做法。脚本从放在本仓库旁边的 clone 里读取。 |
| [XHXIAIEIN/Construct3-Manual](https://github.com/XHXIAIEIN/Construct3-Manual) | 官方手册、Addon SDK 指南和 Game Services 文档的 Markdown 版。数据给出名称和参数，手册说明它们做什么。 |
| [Scirra/Construct-Example-Projects](https://github.com/Scirra/Construct-Example-Projects) | 示例浏览器里的每一个官方示例，保存为文件夹项目。`search_guides.py` 按主题找到它们。 |
| [Scirra/Construct-Addon-SDK](https://github.com/Scirra/Construct-Addon-SDK) | 自定义插件、行为、滤镜和主题的模板和文档。 |

## 许可

MIT。数据来自 Scirra Ltd 的 Construct 3 编辑器。
