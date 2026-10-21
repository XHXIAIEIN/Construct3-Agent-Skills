# The Event Sheet Guides Live in Construct3-Cookbook

Date: 2026-10-21

## Problem

The event sheet prompts, the pitfalls among them, lived in `plugin/prompts/`
and shipped with the plugin. A pitfall is usually one line found in a game
project on a given day, and it changes which events every later session
writes. Through the plugin it reached a user only with a plugin release:
from Claude's plugin directory, after a manual review that takes days, and
from a clone or the marketplace, after the build raised the version. A
pitfall waited for a release that held nothing else.

## Evidence

- `plugin/prompts/` held the design, style and pitfalls guides, a topic
  file per group of pitfalls and the references.
- The plugin folder was close to the directory's limits on files and bytes
  (`plugin-folder.md`), and the guides were a share of both.
- The scripts read the guides in three places: `search_guides.py` searches
  the pitfall files, `check_project.py` cites a pitfall file in its
  findings, and `design_review.py` hashes the design and style guides and
  quotes the design guide's model. All three already found the guides
  through `prompts_folder()`, so one function decides where they are.
- The scripts already work without a clone they want: without
  Construct-Example-Projects, `search_guides.py` prints the command that
  clones it and goes on (`EXAMPLES_URL` in `c3project.py`).
- The maintainer's private Construct3-Cookbook workspace names private,
  paid and third-party projects in its records and its history, so it
  cannot be the public repository.

## Options

1. Keep the guides in the plugin. Every user has them, and every pitfall
   waits for a release and a review.
2. Keep a copy in the plugin and read a Cookbook clone first when there is
   one. Users without a clone still get guides, but two copies drift, the
   build has to copy them, and a stale copy looks current.
3. Move the guides to a public Construct3-Cookbook repository, and let the
   scripts read a clone of it. A pitfall reaches a user with `git pull`;
   a user who installed only from the plugin directory has no guides until
   they clone it.

## Decision

Option 3.

- Construct3-Cookbook is a new public repository with a new history: the
  history of `prompts/` and `plugin/prompts/` from this repository, which
  was public already, rewritten by `git filter-repo`, and nothing of the
  private workspace. Under `guides/`, a pitfall lives on the page of what
  owns it, named only by a Construct3-RAG id (`plugins/system.md`,
  `behaviors/tween.md`), a c3-lang category key
  (`behavior-category/movements.md`) or a page of the manual's
  `project-primitives/` (`primitives/events/how-events-work.md`), so that a
  name is never a noun of the repository's own; `guides/pitfalls.md` is the
  one-line index. `design/`, `recipes/` and `project-files/` sit beside
  them. Its CI checks the links, the index against the pages and each page
  name against those three sources.
- `plugin/prompts/` is gone, and the build copies nothing in its place.
  The note on placing the game project's block, which is about this
  repository and not about events, moved to
  `skills-dev/game-project-AGENTS.md`.
- `c3project.locate_cookbook()` finds the clone in this order:
  `--cookbook` (on `search_guides.py`), `CONSTRUCT3_COOKBOOK`, the
  `Construct3-Cookbook:` line of the project's `AGENTS.md` or `CLAUDE.md`,
  and a `Construct3-Cookbook` folder beside the data's clone or beside this
  repository. A folder counts only when it holds
  `guides/pitfalls.md`, so a folder of that name
  without the guides, such as the private workspace, is passed over.
- Without a clone, `search_guides.py` prints a `note:` with the
  `git clone` command and still prints the examples; `check_project.py`
  prints the same note and runs every check, and its findings cite a
  pitfall as `Construct3-Cookbook/guides/<page>`.
  The skill tells the agent to give the user the command and to clone
  only once they agree.
- `install.py` writes a `Construct3-Cookbook:` line into the block, with
  the clone it finds or the folder beside the clones where the command
  would put it. A refresh keeps the block's lines and adds the new one.
  `bootstrap.py` and both workflows clone Construct3-Cookbook beside this
  repository, so the tests that read the guides run in CI; without the
  clone they skip and name the command.
- A new pitfall is committed to Construct3-Cookbook, not here.
- `lookup_ace.py` ends an entry with the Cookbook page of its addon and the
  Native first row of `guides/design/native-first.json` (`lookup-pointers.md`).

What it costs:

- A user who installed the plugin only from Claude's directory and never
  cloned Construct3-Cookbook designs events without the guides and the
  pitfalls until they clone it. The scripts say so on each run that would
  read them; nothing else stops the work.
- The plugin and the guides can now disagree: a script that cites a guide
  by path breaks when the guide is renamed there. `tests/test_cookbook_paths.py`
  checks every `Construct3-Cookbook/...` path named here against the clone,
  and the Cookbook's `AGENTS.md` says that a rename is a change here too.
- Construct3-Cookbook must be on GitHub before a branch with this change
  merges, or the checks and the daily refresh fail to clone it.
- On a machine where `Construct3-Cookbook` beside the clones is some other
  folder, the clone command the scripts print names a folder that exists;
  the clone then goes elsewhere and `CONSTRUCT3_COOKBOOK` or the line names it.

## Re-evaluate when

- The directory reviews plugin versions within hours, or a plugin can
  fetch content at install time, so that a release no longer delays a
  pitfall.
- Users report designing without the guides because they never cloned the
  Cookbook.
