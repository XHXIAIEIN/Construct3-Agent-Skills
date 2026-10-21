---
name: check-sounds
description: Measures every file under sounds/ and music/ with ffmpeg, its length, format, loudness, true peak and silence, and compares it with the tier and ceiling of its role in tools/sounds.json. A loudness finding names the gain and the ffmpeg command that applies it. Without ffmpeg it measures nothing.
argument-hint: "[FILE ...]"
disable-model-invocation: true
allowed-tools:
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/run.py" check_sounds *)
  - PowerShell(python "${CLAUDE_PLUGIN_ROOT}/skills/run.py" check_sounds *)
---

What `check_sounds.py` printed for the arguments given, with its exit code on the last line:

!`python "${CLAUDE_PLUGIN_ROOT}/skills/run.py" check_sounds $ARGUMENTS`

If the skill `construct3:construct3-agent-plugin` is not loaded in this session, read `${CLAUDE_PLUGIN_ROOT}/skills/construct3-agent-plugin/SKILL.md` before acting on the output.
