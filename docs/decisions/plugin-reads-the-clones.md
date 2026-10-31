# The Plugin Holds No Data; Its Scripts Read the Construct3-RAG Clone

Date: 2026-11-01

## Problem

`plugin/data/` held a built copy of the data of Construct3-RAG: the
schemas, the editor texts, the empty project, and the TypeScript
definitions and the examples as bundles. The copy took most of the room
under the size limit of Claude's directory, so each new skill file had to
win back bytes elsewhere. A data refresh reached the plugin only through a
daily workflow that rebuilt and pushed `plugin/`, and each refresh raised
the plugin's version and added a large diff. The bundles made the
TypeScript definitions and the examples readable through their scripts
only, and the skill's text had to avoid naming them.

## Evidence

| `plugin/` at | Files | Bytes |
|--------------|------:|------:|
| `main` before this change | 463 | 6,721,753 |
| of which `plugin/data/` | 399 | 4,476,104 |
| after this change | 64 | 2,252,330 |

The directory refuses a folder over about 7,000,000 bytes
(`plugin-folder.md`), so the data left less than 300,000 bytes for the
skill. Without it the folder holds about a third of the limit.

The skill already reads three repositories from their clones beside the
one that holds it: Construct-Example-Projects, Construct3-Manual and
Construct3-Cookbook (`guides-in-cookbook.md`). A missing clone prints the
`git clone` command, and the agent asks the user before it runs it.

## Options

- Keep the full data in `plugin/data/`: the plugin works with no other
  clone, but the room under the limit and the daily rebuild stay as they
  were.
- Keep the data, with the zh-CN schemas stored as an overlay on the en-US
  ones: on a branch that tried it, the folder held 279 files and
  6,181,493 bytes, still near the limit, and every schema read went through
  code that merges the overlay.
- Keep no data: the scripts read every data file from a Construct3-RAG
  clone, as they read the other clones.

## Decision

`plugin/` holds no data. Every script reads the data from a Construct3-RAG
clone, which `c3project.locate_rag` finds in this order:

1. `--rag`;
2. the `CONSTRUCT3_RAG` environment variable;
3. the `Construct3-RAG:` line of the game project's `AGENTS.md` or
   `CLAUDE.md`;
4. a `Construct3-RAG` folder beside the clones: beside the clone of
   Construct3-Agent-Skills that holds the running plugin, or beside the one
   that the project's `Construct3-Agent-Skills:` line names. An installed
   plugin has no clone above it, so its own folder in Claude Code's plugin
   cache stands for one, and the clone goes beside that folder.

A script that finds no clone stops with the command that puts one in the
first place of step 4, such as
`git clone --depth 1 https://github.com/XHXIAIEIN/Construct3-RAG "<folder>"`,
and with the places it tried. The plugin clones and downloads nothing
itself.

The clone that the skill comes from is apart from the data. The
Construct 3 block of a game project names it on its own line,
`Construct3-Agent-Skills:`, and `install.py`, the checker's drift check and
the refresh command read it from there. A copy of the skill run from a game
project finds its source through that line, and the data through the
`Construct3-RAG:` line.

Each repository the scripts read has one clone, in a fixed place, which
the checker keeps current:

- The place is beside the clone of Construct3-Agent-Skills, or for a
  plugin installed from a marketplace, in
  `~/.claude/plugins/cache/<marketplace>/construct3/`, beside the version
  folders. Claude Code puts each plugin version in a folder of its own, so
  a clone inside one would stay behind with it at the next update, and the
  new version would ask for a second clone. Beside them, every version
  finds the same clone. Construct-Example-Projects and Construct3-Cookbook
  go beside Construct3-RAG.
- `check_project.py` compares Construct3-RAG, Construct-Example-Projects
  and Construct3-Cookbook with their upstream branches by their newest
  commits, read anonymously over HTTPS from GitHub's API
  (`clone-update-check.md`). A clone that is behind and holds no work of
  its own is pulled there, fast-forward only, and the check prints a note.
  A clone with the user's commits or changes is left for the user.
- `RAG_DATA_FLOOR` in `c3project.py` names the oldest data the scripts read
  correctly, as the Construct release in the clone's
  `data/c3-schemas/_index.json`, such as `r506.3`. The checker fails on a
  clone with older data, also offline, and gives the pull. A script change
  that reads what a newer refresh added raises the floor.
- Nothing downloads at install time. `install.py` writes the clone's place
  into the block and clones nothing; a missing clone is a printed command,
  and only an existing clone is pulled.

`dev/scripts/build_plugin.py` keeps the version (`plugin-tracks-commits.md`)
and the limits, and `--check` fails while `plugin/data/` exists.

## Trade-offs

- A first install needs a second clone, whose checkout is mostly `data/`.
  Until the clone exists, every script that reads the data stops with the
  clone command.
- The scripts and the data come from two repositories and can drift. The
  floor catches data older than the scripts; a script that reads a field a
  new refresh dropped fails until the skill follows it, and the tests read
  the clone beside this repository.
- The checker writes to the user's clones: a fast-forward pull, only where
  the clone holds no work of its own. A pull of Construct-Example-Projects
  can move a few megabytes when Scirra adds examples.
- A game copy whose `Construct3-RAG:` line names `plugin/` of the
  Agent-Skills clone finds no data there after a pull. Its scripts stop with "Construct3-RAG not found" until the
  clone's `install.py` refreshes the copy, which replaces that line with the
  Construct3-RAG clone and adds the `Construct3-Agent-Skills:` line.
- The TypeScript definitions and the examples are files again, so the
  skill's text names them by path and `lookup_script_api.py` prints a
  declaration's file and line.

## Re-evaluate when

- The directory states that a plugin must work with no clone beside it.
- Claude Code gives a plugin a supported way to depend on a second
  repository, such as a plugin dependency that carries data.
- Claude Code removes folders it did not write from a plugin's cache
  folder; the clone then needs a place outside the cache.
