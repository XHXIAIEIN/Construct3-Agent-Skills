# A Check That Did Not Run Does Not Pass

Date: 2026-10-22

## Problem

An agent reads a script's exit code and its last line, and `SKILL.md`
counts a step as passed when that line starts with `ok:` or the code is 0.
Three checks said in words that they had checked nothing and still gave a
pass: `check_sounds.py` and `measure_timing.py` without ffmpeg printed
that they measured nothing and exited 0, and `check_design.py` without the
Construct3-RAG clone left the reference example unchecked and printed
nothing about it. A hand-over could then name a check that never ran.

Evidence: the scripts that drive the editor already exit 3 when no browser
is there, and `pack_project.py` exits 3 when no passing check covers the
files, so 3 already means "not checked" here. NVIDIA's SkillSpector records
each work item of a scan as completed, partial, skipped, failed or out of
scope, so its report never reads a skipped analyzer as clean.

## Options

- Keep the exit code and let the line say it: the line is there, and an
  agent that reads the code alone still counts a pass.
- Fail with exit 1: the same code as a finding, so the agent looks for a
  fix in files that have none.
- Exit 3, the code that already means a check did not run, and keep the
  last line from starting with `ok:`.

## Decision

The third for a whole check that did not run: `check_sounds.py` and
`measure_timing.py` without ffmpeg and ffprobe say that nothing was
measured, and exit 3.

A part of a check that did not run, while the rest did, keeps the run's
code and names the part: `check_design.py` without the clone prints
`skipped: reference.example is not checked:` with the reason and the flag
to pass, and its `ok:` line ends by saying the reference example is not
checked. The design's rules and tests ran, so the design can be built; the
line names the part to run once the clone is there.

## Re-evaluate when

A caller of these scripts needs a pass from a machine without ffmpeg, or a
second part of a check is skipped often enough that a line per part no
longer reads well.
