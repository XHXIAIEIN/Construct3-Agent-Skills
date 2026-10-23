# AGENTS.md for a Construct 3 project

This file describes the Construct 3 block that a game project's `AGENTS.md`
holds, how `install.py` writes and refreshes it, and how to place or change
it by hand.

A game project needs the block because nothing in a Construct project links
to this repository. The `llm-context.md` that Construct writes into every
project outlines the folder layout and links Scirra's guide [Construct's
project
format](https://www.construct.net/en/tutorials/constructs-project-format-3275),
which says what `project.c3proj` indexes, how image files are named and
which formats the files take. Neither file names an ACE, the rules that the
editor applies when it opens a project, or how to design events. So an agent
in the game folder answers these from memory, and it builds a drag-and-drop
interaction from UID links, `Pick all` and globals.

## Installing

The game project needs two things: a block in its `AGENTS.md` that names the
file to read for each kind of work, and a copy of the
`construct3-agent-plugin` skill with the tools. One command in the project
folder writes both:

```bash
python <Construct3-Agent-Skills>/plugin/skills/construct3-agent-plugin/scripts/install.py
```

The command copies
[`plugin/skills/construct3-agent-plugin/`](../plugin/skills/construct3-agent-plugin/SKILL.md)
to the project's `.agents/skills/`. If no instruction file of the project
names this repository, it also appends the block to `AGENTS.md`, with the
path of this clone's `plugin/` on its `Construct3-RAG:` line. In an
instruction file that names this repository, it changes only the block that
it wrote, as "Refreshing the block" describes.

`--into .claude/skills` installs the skill where Claude Code finds skills,
and `--into .trae/skills` where TRAE does. Most other agents read
`.agents/skills/`. The block names the installed `SKILL.md` in every case,
so an agent without skill support reaches it too.

Claude Code 2.1.277 and later read `AGENTS.md` if the project has no
`CLAUDE.md`
(<https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md>). If the
project has a `CLAUDE.md`, that file needs the line `@AGENTS.md`, as this
repository's `CLAUDE.md` has. Under an earlier version, a project without a
`CLAUDE.md` needs one that holds that line, and `claude --version` prints
the version. `install.py` writes the line together with the block: it
creates `CLAUDE.md` with the line, or appends the line to a `CLAUDE.md` that
lacks it.

## Placing the block by hand

The text of the block is
[`plugin/skills/construct3-agent-plugin/assets/game-project-block.md`](../plugin/skills/construct3-agent-plugin/assets/game-project-block.md).
To place it by hand:

1. Copy it into the project's `AGENTS.md`, with its two marker lines.
2. Fill in the two paths at the top: this clone's `plugin/` and the
   Construct3-Cookbook clone, or symlinks in the project that point to them.
   Replace `<path-to>` in place, or keep it and add a line `- path-to =
   <folder>` above it for the folder that holds the clones. The skill's
   scripts read both forms.
3. The block expects the `Construct3-Manual`, `Construct-Example-Projects`
   and `Construct-Addon-SDK` clones beside this repository, where the README
   places them. If a clone is kept elsewhere, give it a line of its own.
4. Leave the rest of the block as it is, because `install.py` refreshes only
   an unedited block.

If a path is left unfilled, the checker in the block's first step stops and
says what to write.

## What the block does

The block's first step sends the agent to the installed `SKILL.md` before
the agent opens any project file. This is a step and not a row of the table,
because a small model skips such a row in about half the runs and then edits
the sheet's JSON by hand (`docs/decisions/project-tools-skill.md`).

The same step runs `check_project.py` once. If the `Construct3-RAG:` path is
wrong or the copy is behind the clone, the checker stops there and says what
to fix, before a script fails to find the schemas. The check takes well
under a second and prints at most 10 000 characters of findings.

Each row of the table then names the one file that holds the details of its
task, so a change to a tool or a data path is made in one place.

The folder that the block names keeps Scirra's guide as
`Construct3-RAG/data/c3-guides/constructs-project-format.md`, and the
section "The project folder" in
`Construct3-Cookbook/guides/project-files/hand-editing.md` applies what the
guide states to the project's files. If the agent adds, renames or moves a
file of the project, the block sends it to both.

The block ends with a rule for the project's own long Markdown files, such
as design documents: list the headings, then read the section that the work
needs. A file read whole stays in the context and is read again on every
later turn, and whole reads of design documents were the largest single cost
after the context itself in one game project's sessions
(`docs/decisions/long-docs-in-parts.md`). The rule covers the project's
files only. The files of this repository that the table names are read
whole, because each one says what to read next.

The block loads no other file at startup, and the agent reads each file when
its work needs it. If the agent keeps skipping those files, add this line
below the block's end marker:
`@<path-to>/Construct3-Cookbook/guides/design/thinking.md`. Claude Code then
inlines that file into every session of the project, at the cost of its full
length each time. Other tools ignore the line.

## Changing the block

Every session of the project reads the block, so keep out of it any
instruction for a case that `install.py` cannot produce, such as an unfilled
path.

A change to the block's text in this repository changes its stamp.
`dev/AGENTS.md`, "The generator template and the block", says how to update
the end marker.

## Refreshing the block

The block sits between two HTML comments, which a rendered `AGENTS.md` does
not show. The end marker carries the block's version and the stamp of its
text. The stamp leaves out the lines that name a clone's folder and the
folder that the skill was installed in, so filling in a path or adding a
line that names a clone's folder is not an edit.

- If the skill's block is newer and the project's text still matches the
  stamp, `install.py` replaces the block. It keeps the lines that name
  folders and every line outside the markers. `--block-only` does only that,
  for a project that uses the skill through the Claude Code plugin.
- If the block is older, or its markers are broken, `check_project.py` warns
  and prints the command.
- If the block was edited, `install.py` leaves it as it is and names the
  lines that differ. Once the project's own lines are below the end marker,
  `--replace-edited-block` takes the skill's block.
- A block written before the markers existed is refreshed when its text is
  exactly one that `install.py` wrote. Any other text belongs to the project
  (`docs/decisions/instruction-block-refresh.md`).

## Before the project exists

On a machine that has only this clone, run this repository's
`scripts/bootstrap.py --project <folder>`. It clones the sibling
repositories that the block expects, the Cookbook among them, if they are
missing. If the folder does not exist, it creates the folder as an empty
project, a copy of `plugin/data/c3-new-project`. Then it runs `install.py`
on the folder. The README's first section gives the clone command and this
command to a reader who has only the URL.
