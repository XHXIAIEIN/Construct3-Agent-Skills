---
name: make-sounds
description: Writes placeholder sounds and music from the cue table in tools/sounds.json, each set to the tier of its role and encoded WebM Opus, lists them in project.c3proj and ends with the measurer's verdict. --example prints a table to start from; a file it did not write is kept unless --replace. Needs ffmpeg.
argument-hint: "[--dry-run] [--replace] [--example]"
disable-model-invocation: true
allowed-tools:
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/run.py" make_sounds *)
  - PowerShell(python "${CLAUDE_PLUGIN_ROOT}/skills/run.py" make_sounds *)
---

What `make_sounds.py` printed for the arguments given, with its exit code on the last line:

!`python "${CLAUDE_PLUGIN_ROOT}/skills/run.py" make_sounds $ARGUMENTS`

If the skill `construct3:construct3-agent-plugin` is not loaded in this session, read `${CLAUDE_PLUGIN_ROOT}/skills/construct3-agent-plugin/SKILL.md` before acting on the output.
