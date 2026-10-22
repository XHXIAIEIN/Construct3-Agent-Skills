---
name: verify-change
description: Runs every check of a change to the Construct 3 folder project in order, the checker, the design review, the editor and its preview, the kept plays and the look, and runs a step that opens the editor again only when a file changed. The last line is the one thing to do next, or ok and the steps that did not run. --status prints where the checks stand without running them.
argument-hint: "[--status] [--answered] [--upto STEP] [--project FOLDER]"
disable-model-invocation: true
allowed-tools:
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/run.py" verify_change *)
  - PowerShell(python "${CLAUDE_PLUGIN_ROOT}/skills/run.py" verify_change *)
---

What `verify_change.py` printed for the arguments given, with its exit code on the last line:

!`python "${CLAUDE_PLUGIN_ROOT}/skills/run.py" verify_change $ARGUMENTS`

If the skill `construct3:construct3-agent-plugin` is not loaded in this session, read `${CLAUDE_PLUGIN_ROOT}/skills/construct3-agent-plugin/SKILL.md` before acting on the output.
