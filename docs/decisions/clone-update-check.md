# A Clone Behind Its Upstream Fails the Check

Date: 2026-10-04, revised 2026-10-16

## Problem

The skill and the schemas change often, and a game project reads them from a
local clone of this repository, through a copy of the skill that `install.py`
made. `bootstrap.py` clones a repository only when its folder is missing, and
`install.py` copies the skill from the clone as it is. Neither fetches, so an
agent can work for weeks from a clone that lacks the checks and data of later
commits, and nothing tells it so.

## Decision

`check_project.py`, which the block in a game project runs at the start of
each session and the skill runs after every change, compares the plugin
version of the clone with the one on its upstream branch, and reports a
clone that is behind as a problem, with the commands that update it:

```
Construct3-Agent-Skills at <clone> holds version 1.1.27 of the plugin, and origin/main holds 1.1.30, so the scripts lack the fixes and checks of the newer version. Run git -C "<clone>" pull --ff-only, then python "<clone>/plugin/skills/construct3-agent-plugin/scripts/install.py" --into "<game>/.agents/skills", then run this check again
```

- The users of a clone have Git installed but do not run it themselves, so
  the agent runs the update. The line is an error, so the check exits 1
  and the line is the first problem. An agent takes the last line of a
  passing check, `ok: ...; next, ...`, for its next step (`ok_line` in
  `check_project.py`). Small-model runs in the skill evals left a warning
  that printed on every run unacted, so a warning above that last line
  goes unread.
- One line carries both steps: the pull, and for a game project that holds
  a copy of the skill, the `install.py` that refreshes the copy. Run from
  the clone itself (the Claude Code plugin linked to a clone, or the
  scripts run in place), the line gives the pull alone.
- The upstream's version is read over HTTPS from
  `raw.githubusercontent.com`, the `plugin/.claude-plugin/plugin.json` of
  the branch the clone tracks, at the GitHub repository its remote names.
  The read is anonymous: the scripts run no `git fetch`, so they use no SSH
  key or credential helper of the user's. Claude's directory held a version
  for "uses a credential from the user's machine" while the check fetched.
  A remote off GitHub gets no comparison.
- The version is the build's (`plugin-tracks-commits.md`): it rises with
  every commit that changes `plugin/`, the folder whose scripts, data and
  prompts the user's agent reads. A commit that changes only the sources'
  tests or records leaves it, and the clone is not called behind for it.
- The check reads the version at most once an hour per clone, with an
  eight-second limit. The last read's version is a file in
  `construct3-rag-version/` of the system's temporary folder, written
  empty before the read, so that an offline machine waits once per hour
  and not on every check. In between, the check compares with that
  version, which costs a file read.
- The line is an error only when the version was read in this run. From an
  earlier read it is a warning, so that a pull that failed offline, after
  a read that succeeded, does not fail every check of the hour; the next
  read makes it an error again.
- A clone that holds commits or uncommitted changes of its own gets a
  warning instead, which names them and asks the agent to tell the user. A
  pull there could merge into the user's work or refuse over it, and an
  agent told to clear an error may reset the clone to get past it.
- A copy that differs from the clone it was made from is an error of the
  checker too, with the `install.py` command. `lookup_ace.py`,
  `lookup_script_api.py`, `search_guides.py`, `print_sheet.py`,
  `edit_sheet.py` and `review_design.py` print that command as their first
  line and go on. They do not compare versions: a pull in the middle of a
  lookup would interrupt the task.
- Nothing is said for a clone that is not a Git repository (the plugin
  cache), a detached HEAD, a branch with no upstream, a remote off GitHub,
  a failed read, or a clone with no plugin version.
- `CONSTRUCT3_RAG_OFFLINE=1` skips the check, and `check_project.py` then
  prints a `note:` line saying the clone was not compared with its
  upstream. Only `1` sets it, so that `0` keeps the check. The tests set it,
  so that a test run reads no network and its output does not depend on the
  remote.

## The Claude Code plugin

A plugin installed from the `construct3-rag` marketplace is a copy in Claude
Code's plugin cache, with no `.git`, so the check above says nothing there.
`plugin.json` carries a `version`, so an update reaches that copy only
when the version is raised (`plugin-tracks-commits.md`). Claude Code
updates a plugin from a third-party marketplace on its own only when the
user turns on the marketplace's auto-update. The user can also run
`claude plugin update construct3@construct3-rag`. The README gives both
(Claude Code docs, "Keep plugins updated",
`https://code.claude.com/docs/en/plugins/install`).

## Trade-offs

- The checker is not fully offline: it makes one HTTPS request an hour per
  clone, and `CONSTRUCT3_RAG_OFFLINE=1` turns it off.
- The checker reads but does not move the clone's branch: the clone
  belongs to the user, and the line hands the pull to the agent only for a
  clone with no work of its own.
- The pull needs the network, where the merge of a fetched upstream did
  not. A pull that fails offline leaves a warning for the rest of the hour,
  not a failing check.
- A clone behind its upstream fails a check whose project is sound. The
  failure lasts one round trip, the pull and the refresh, and the check
  that follows reads the project with the current rules.
- An eval run follows the line too, so fixtures come from a clone that does
  not trail its upstream (`skills/AGENTS.md`, "Evals").
- Only the clone that holds the data folder is checked, this repository
  through its `plugin/`. The sibling clones change rarely, and their
  content reaches the agent through the data. A clone of Construct3-RAG
  named by an older block has no plugin version and gets no comparison.
- A commit reaches users only after it is pushed and has changed `plugin/`.
