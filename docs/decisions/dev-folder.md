# What Only Maintainers Use Lives Under `dev/`

Date: 2026-10-23

## Problem

The root held `plugin/`, what users get, beside three folders that only the
skill's maintainers use: `skills-dev/` (the evals and the guide to changing
the skill), `tests/` and `scripts/`. A reader of the root could not tell at
a glance which folders reach a user. The repository is public because it is
the plugin's distribution channel: Claude's directory reviews `plugin/`, the
marketplace manifest points at it, and other agents clone it for
`install.py`.

## Options

- A hidden `.dev/` folder. Rejected: ripgrep, the Grep tool and many globs
  skip dot folders, so an agent would not find the evals or the tests.
- One visible folder for everything maintainers use. Chosen, named `dev/`,
  a name that says what the folder is for without naming who uses it.

## Decision

`dev/` holds `AGENTS.md` (the guide to changing the skill, formerly
`skills-dev/AGENTS.md`), `game-project-AGENTS.md`, `evals/`, `tests/` and
`scripts/`. The root shows `plugin/`, `dev/`, `docs/` and `scripts/`.

- `scripts/bootstrap.py` stays at the root, because the README and
  `bootstrap-from-the-url.md` print the path
  `Construct3-Agent-Skills/scripts/bootstrap.py` for a user to run.
- `docs/` stays at the root, because the shipped skill text cites
  `Construct3-Agent-Skills/docs/decisions/...`, and a change to that text
  needs an eval iteration of its own.
- `dev/` has no `__init__.py`, so pytest puts `dev/` on `sys.path` and the
  tests keep importing `tests.` and `scripts.` modules.

No user-facing behaviour changes: the boundary that keeps maintainer files
out of a game project is `plugin/`, which the plugin and `install.py` copy
alone.

## Re-evaluate when

A file under `dev/` is needed at run time by the plugin, or a user-facing
path besides `scripts/bootstrap.py` points into a moved folder.
