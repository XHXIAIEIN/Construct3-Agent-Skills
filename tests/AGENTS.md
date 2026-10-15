# `tests/` Directory

The pytest suite is offline: it needs no agent, no editor and no network.
It needs the Construct3-RAG clone beside this repository, whose `data/` the
build reads and a few tests compare with the plugin's copy.

## Rules

- A script of the `construct3-agent-plugin` skill is tested in
  `test_skill_<script>.py`; the build in `test_build_plugin.py` and
  `test_plugin_folder.py`; the prompts' shape in `test_prompts.py`.
- Assert public contracts, not private implementation fields.
- The scripts get `plugin/` as the clone (`PLUGIN` in `skill_helpers.py`),
  the built folder that holds the data and the prompts, because that is
  what every install and link runs them from. Raw data files come from
  `DATA`, the sibling clone's `data/`.
- Run `python scripts/build_plugin.py` before the tests after a change to
  the skill or the prompts. The tests install the source skill into the
  stand-in game and the copy compares itself with the skill in `plugin/`,
  so a stale `plugin/` fails every check as drift, and
  `test_plugin_folder.py` names the difference.
- A skip reason names the command that supplies what is missing
  (`python scripts/bootstrap.py`, `pip install pillow`). A sibling clone's
  path comes from `siblings_folder`, as `EXAMPLES` in `skill_helpers.py`
  does: in a worktree `REPO.parent` is not the folder that holds the
  clones, and `test_sibling_paths.py` fails on it.

## Skill tests

The evals of the skill run agents, not pytest, and live with the skill:
`skills/AGENTS.md`, "Evals". `test_skill_spec.py` tests the skill's format,
the trigger runner `run_trigger_eval.py` against a stand-in client, and
`trace.py` on a written transcript. `test_skill_grade.py` grades recorded
answers from `fixtures/restart_event_answers/` and runs built from the
stand-in game with `grade.py`, pins what `grading.json` says, and tests
`trace.py`, `make_fixtures.py` and `play_cases.py` beside it. The skill's
tests share `skill_helpers.py` and, in `conftest.py`, the stand-in game,
generated once a run.

## Commands

```bash
python -m pytest tests/ -q
python -m pytest tests -q -k test_skill_
python -m pytest tests/test_plugin_folder.py -q
```
