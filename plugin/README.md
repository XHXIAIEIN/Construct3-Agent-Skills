# Construct3

Construct3 lets Claude make and change [Construct 3](https://www.construct.net) games saved as folder projects. It carries the `construct3-agent-plugin` skill, whose scripts read every condition, action, expression and effect as the Construct 3 editor defines them, in English and Chinese, from a clone of [Construct3-RAG](https://github.com/XHXIAIEIN/Construct3-RAG). With the skill, Claude:

- looks up the exact JSON of a condition, action or expression before writing it, and the scripting API of a Construct plugin or behavior;
- prints an event sheet as events and changes it from a checked plan;
- starts a new project from the empty one the editor saves, or generates a whole project from a script;
- checks a project against the rules the editor applies when it opens one;
- opens the project in the Construct 3 editor, previews it and exports it.

## Use

1. Install the plugin.
2. Ask Claude to set Construct3 up. Claude runs the skill's `setup.py`, which checks Python 3.10 or later and git, and lists at once every repository the skill reads that is missing, each with its size. Construct3-RAG (the editor's data), Construct3-Cookbook (the event sheet guides) and Construct3-Manual are required; Construct-Example-Projects (864 MB) and Construct-Addon-SDK are optional. Claude asks whether you already have any of them elsewhere, then clones the ones you agree to into `~/Construct3`, or into the folder that `CONSTRUCT3_HOME` names. The data is English; ask for Chinese to get the editor's Chinese wording too.
3. Ask Claude about a Construct 3 project in its folder: a change such as "add a double jump", or a problem such as "why does the editor refuse to open this project". The skill loads on its own for such a request. To start a game, ask for a new project in an empty folder.

A clone you keep elsewhere is named with `CONSTRUCT3_RAG` or `CONSTRUCT3_COOKBOOK`. Cutting pictures out of an image tool's output needs Pillow.

The plugin also adds the sub-agent type `construct3:project-worker`, for a change or a lookup that the main agent hands over. It has only the tools the scripts need (shell, file reading and editing, search, the skill, and starting the sub-agent that `review_design.py` or `preview_project.py` asks for), so it starts with a fraction of the context a general-purpose sub-agent starts with. The type `construct3:art-drawer` draws the pictures of a generated game as SVG in code, from the brief that `art.py` writes: it writes the game's `tools/drawings.py`, renders it and fixes what `art.py` refuses, three rounds at most. The type `construct3:design-judge` answers the questions that `review_design.py` asks about the event sheets, through the brief that the script writes: it has not seen the project or the request, and it can only read. It runs the Sonnet model, whose answers were measured on planted faults and on sheets without them. The type `construct3:recording-describer` describes the frames of a recording that `preview_project.py` made of a change, through the brief that the script writes: it answers open questions about what moves and what the screen shows, without being told what the change should look like, and it can only read. It runs the Sonnet model.

## What runs and what reaches the network

- The scripts run on the machine with Python, on the files of the project, of this plugin and of the clones in the home folder. The plugin downloads nothing itself: `setup.py` only checks, and prints the `git clone` commands that Claude runs once the user agrees. A script that misses a clone points to `setup.py`.
- Opening, previewing, exporting or taking a picture of a project starts Edge, Chrome or Chromium, or the agent's browser tool, on the Construct 3 editor at `editor.construct.net`, with the project loaded from the machine. A preview runs at `preview.construct.net`. An export uses the Construct account that the user signs in to in that browser; the scripts store no password.
- When the plugin is a Git clone of its GitHub repository, the checker reads the plugin version on the clone's upstream branch from `raw.githubusercontent.com`, at most once every two hours and without the user's Git credentials, to say when the clone is behind. In the same way it reads the newest commit of the upstream branch of the Construct3-RAG, Construct3-Cookbook and Construct-Example-Projects clones from `api.github.com`, and runs `git pull --ff-only` in a clone that is behind and holds no work of its own. Set `CONSTRUCT3_RAG_OFFLINE=1` to turn this off; the checker then says that it did not compare the clones.

## Source

The plugin is built in [Construct3-Agent-Skills](https://github.com/XHXIAIEIN/Construct3-Agent-Skills), which holds the skill, the tests and the decision records. The event sheet guides the skill reads live in [Construct3-Cookbook](https://github.com/XHXIAIEIN/Construct3-Cookbook): `setup.py` clones it into the home folder, and the checker pulls it for new pitfalls. The data comes from [Construct3-RAG](https://github.com/XHXIAIEIN/Construct3-RAG), which holds it and its update pipeline. License: MIT.
