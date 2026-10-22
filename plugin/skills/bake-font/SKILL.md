---
name: bake-font
description: Bakes the characters a pixel-art game shows into its Sprite Font images, from the pixel font in the user's font cache, and prints how many it added or dropped. Appends by default; --add keeps words that events build at runtime, --replace drops what is no longer in use, --check lists what is in use but not baked. Used after a text of a pixel-art project changes by hand.
argument-hint: "[--add TEXT] [--replace] [--check] [--types TYPE [TYPE ...]] [--font NAME_OR_PATH]"
disable-model-invocation: true
allowed-tools:
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/run.py" bake_font *)
  - PowerShell(python "${CLAUDE_PLUGIN_ROOT}/skills/run.py" bake_font *)
---

What `bake_font.py` printed for the arguments given, with its exit code on the last line:

!`python "${CLAUDE_PLUGIN_ROOT}/skills/run.py" bake_font $ARGUMENTS`

If the skill `construct3:construct3-agent-plugin` is not loaded in this session, read `${CLAUDE_PLUGIN_ROOT}/skills/construct3-agent-plugin/SKILL.md` before acting on the output.
