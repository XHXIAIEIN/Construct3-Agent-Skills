# The Clones Live in One Home Folder, and setup.py Lists the Missing Ones

Date: 2026-11-01

## Problem

`plugin/` holds no data (`plugin-reads-the-clones.md`), so a user who
installs the plugin from Claude's directory or from the GitHub marketplace
needs clones of Construct3-RAG, Construct3-Cookbook and Construct3-Manual
before the skill works. The first run had three faults:

- It asked for the clones one level above the plugin's version folder,
  inside Claude Code's plugin cache. The user does not see that folder, and
  Claude Code cleans the cache: an old version folder of another plugin
  carries `.orphaned_at`, by a rule that is not documented.
- It reported the clones one at a time. A missing Construct3-RAG stopped
  every script. A missing Cookbook printed a note, and the agent designed
  without the pitfalls. Nothing checked the Manual, which the agent needs
  to follow each `[manual: ...]` source of the guides.
- Every user got the Chinese data, which an English user never reads.

## Evidence

The tracked files of each clone on 2026-11-01:

| Clone | Size | Files | Needed for |
|-------|-----:|------:|------------|
| Construct3-RAG | 10.1 MB | 1740 | every script |
| of it, zh-CN | 4.2 MB | 688 | `--locale zh-CN` |
| Construct3-Cookbook | 1 MB | | the design guides and pitfalls |
| Construct3-Manual | 5 MB | | the `[manual: ...]` sources |
| Construct-Example-Projects | 864 MB | | the examples as events |
| Construct-Addon-SDK | under 1 MB | | writing an addon |

A partial clone that checks out everything but zh-CN works against GitHub:
`git clone --depth 1 --filter=blob:none --no-checkout`, then
`git sparse-checkout set --no-cone '/*' '!*zh-CN*'`, then `git checkout`.
It holds 1052 files, and its `.git` 1.7 MB. With it, `lookup_ace.py`,
`new_project.py` and `check_project.py` pass in English. The pattern `'*'`
in place of `'/*'` matches every file by its name, so the exclusion of the
zh-CN folders does not apply and every zh-CN file is checked out. When the
upstream moves on, the checker's `git pull --ff-only` keeps the sparse set:
the English files change and no zh-CN file appears
(`dev/tests/test_skill_setup.py`, and a clone set one commit back and
checked on 2026-11-01).

## Options

- Keep the clones beside the plugin's folder in the cache: no setup step,
  but the folder is hidden and the cache is cleaned.
- Let the plugin clone on its first run: one step fewer, but a plugin that
  downloads makes its reviewer review every version of what it downloads
  (`plugin-folder.md`).
- One home folder outside the cache, and a script that only checks and
  prints every missing clone at once; the agent clones after the user
  agrees.

## Decision

The third option.

The clones live in one home folder, `~/Construct3`, or the folder that
`CONSTRUCT3_HOME` names. The scripts look for each clone in this order
(`clone_places`, `locate_rag` and `locate_cookbook` in `c3project.py`):

1. its flag, such as `--rag` or `--cookbook`;
2. its variable, `CONSTRUCT3_RAG` or `CONSTRUCT3_COOKBOOK`;
3. its line in the game project's `AGENTS.md` or `CLAUDE.md`;
4. the home;
5. beside the Construct3-Agent-Skills clone that the scripts run from, or
   that the project's `Construct3-Agent-Skills:` line names, as a
   developer's checkout has them;
6. beside the plugin's folder in Claude Code's plugin cache, where installs
   made before the home put the clones.

Construct3-Manual and the optional clones lie beside Construct3-RAG, or in
the home when Construct3-RAG lies elsewhere.

`scripts/setup.py` of the skill checks Python 3.10 or later, git and the
clones. It prints every missing clone at once, each with its size and the
command that clones it into the home, or beside a Construct3-RAG that lies
elsewhere. Construct3-RAG, Construct3-Cookbook and Construct3-Manual are
required, and the script exits with 1 while one is missing.
Construct-Example-Projects and Construct-Addon-SDK are optional, listed
with their sizes. Before the commands, it tells the agent to ask whether
the user already has a clone elsewhere, and how to name one: its variable,
or `CONSTRUCT3_HOME` for a folder that holds them all. A clone found in the
plugin cache gets a note to move it to the home. The script downloads
nothing.

Without an argument, the data is English: the Construct3-RAG command is the
partial clone without zh-CN. `--locales zh-CN` makes it a full clone, and
for a clone made without zh-CN it prints
`git -C <clone> sparse-checkout disable`. en-US is always checked out,
because every script reads `--locale en-US` by default. A script given a
`--locale` that the clone left out stops with that command, not with the
languages of `_index.json`, which lists zh-CN either way. `edit_sheet.py`
reads only the languages that the clone holds.

Each script that misses a clone points to `setup.py` and prints no clone
command of its own. `SKILL.md` has the agent run `setup.py` on first use,
give the user every missing clone in one message, and clone only once the
user agrees. `scripts/bootstrap.py`, outside the plugin, runs the same
commands: the three required clones by default, `--all` for the optional
ones, `--locales` for the languages.

## Trade-offs

- First use takes one approval of the clone list. After it, no script asks
  again until a clone goes missing.
- The home is a folder the user did not pick. `CONSTRUCT3_HOME` or a
  clone's variable moves it, and an existing clone is named instead of
  copied.
- The partial clone fetches file contents when it checks them out, so
  `sparse-checkout disable` needs the network.
- The commands quote the sparse patterns in single quotes, which bash and
  PowerShell read and `cmd.exe` does not.
- A clone that an earlier install put in the plugin cache stays there: the
  scripts read it in the sixth place, and `setup.py` says to move it.

## Re-evaluate when

- Claude Code gives a plugin a supported way to depend on the data of
  another repository.
- Claude's directory accepts a plugin that downloads on its first run.
- The zh-CN data shrinks so far that the full clone costs little more than
  the partial one.
