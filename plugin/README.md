# Construct3

Construct3 lets Claude make and change [Construct 3](https://www.construct.net) games saved as folder projects. It carries every condition, action, expression and effect as the Construct 3 editor defines them, in English and Chinese. It also carries the `construct3-agent-plugin` skill, whose scripts use them. With the skill, Claude:

- looks up the exact JSON of a condition, action or expression before writing it, and the scripting API of a Construct plugin or behavior;
- prints an event sheet as events and changes it from a checked plan;
- starts a new project from the empty one the editor saves, or generates a whole project from a script;
- checks a project against the rules the editor applies when it opens one;
- opens the project in the Construct 3 editor, previews it and exports it.

## Use

Install the plugin, then ask Claude about a Construct 3 project in its folder: a change such as "add a double jump", or a problem such as "why does the editor refuse to open this project". The skill loads on its own for such a request. To start a game, ask for a new project in an empty folder.

The scripts need Python 3.10 or later. Cutting pictures out of an image tool's output needs Pillow.

The plugin also adds the sub-agent type `construct3:project-worker`, for a change or a lookup that the main agent hands over. It has only the tools the scripts need (shell, file reading and editing, search, the skill, and starting the sub-agent that `review_look.py`, `review_design.py` or `preview_project.py` asks for), so it starts with a fraction of the context a general-purpose sub-agent starts with. The type `construct3:look-judge` answers the questions that `review_look.py` asks about its screenshots: it has not seen the project, and it can only read. It runs the Haiku model whose answers were measured against labelled screenshots. The type `construct3:art-drawer` draws the pictures of a generated game as SVG in code, from the brief that `art.py` writes: it writes the game's `tools/drawings.py`, renders it, reads the contact sheet and fixes what it sees, three rounds at most. When the user gave the game a look, it first draws the game's first screen in three looks from the brief that `pick_look.py` writes, and the user picks one. The type `construct3:design-judge` answers the questions that `review_design.py` asks about the event sheets, through the brief that the script writes: it has not seen the project or the request, and it can only read. It runs the Sonnet model, whose answers were measured on planted faults and on sheets without them. The type `construct3:recording-describer` describes the frames of a recording that `preview_project.py` made of a change, through the brief that the script writes: it answers open questions about what moves and what the screen shows, without being told what the change should look like, and it can only read. It runs the Sonnet model, which nothing has measured for this task yet.

## What runs and what reaches the network

- The scripts run on the machine with Python, on the files of the project and of this plugin.
- Opening, previewing, exporting or taking a picture of a project starts Edge, Chrome or Chromium, or the agent's browser tool, on the Construct 3 editor at `editor.construct.net`, with the project loaded from the machine. A preview runs at `preview.construct.net`. An export uses the Construct account that the user signs in to in that browser; the scripts store no password.
- When the plugin is a Git clone of its GitHub repository, the checker reads the plugin version on the clone's upstream branch from `raw.githubusercontent.com`, at most once every two hours and without the user's Git credentials, to say when the clone is behind. In the same way it reads the newest commit of the Construct3-Cookbook clone's upstream branch from `api.github.com`. Set `CONSTRUCT3_RAG_OFFLINE=1` to turn this off; the checker then says that it did not compare the clones.

## Source

The plugin is built in [Construct3-Agent-Skills](https://github.com/XHXIAIEIN/Construct3-Agent-Skills), which holds the skill, the tests and the decision records. The event sheet guides the skill reads live in [Construct3-Cookbook](https://github.com/XHXIAIEIN/Construct3-Cookbook): clone it beside the plugin's clone, or name it with `CONSTRUCT3_COOKBOOK`, and `git pull` it for new pitfalls. The data comes from [Construct3-RAG](https://github.com/XHXIAIEIN/Construct3-RAG), which holds the data pipeline. License: MIT.
