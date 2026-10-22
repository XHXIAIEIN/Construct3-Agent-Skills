---
name: measure-timing
description: Measures a recorded effect's rise, peak, fall and tail against the four parts of vfx-timing.md, and names the kind of effect from the ratio of the rise to the fall. Used on a recording of this project's effect, made at a steady frame rate with nothing else moving.
argument-hint: "VIDEO [--from SECONDS] [--csv FILE]"
disable-model-invocation: true
allowed-tools:
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/run.py" measure_timing *)
  - PowerShell(python "${CLAUDE_PLUGIN_ROOT}/skills/run.py" measure_timing *)
---

What `measure_timing.py` printed for the arguments given, with its exit code on the last line:

!`python "${CLAUDE_PLUGIN_ROOT}/skills/run.py" measure_timing $ARGUMENTS`

If the skill `construct3:construct3-agent-plugin` is not loaded in this session, read `${CLAUDE_PLUGIN_ROOT}/skills/construct3-agent-plugin/SKILL.md` before acting on the output.
