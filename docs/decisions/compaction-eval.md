# A Two-Turn Case Measures What a Run Keeps Across a Compaction

Date: 2026-10-23

## Problem

Every eval case was one prompt to one sub-agent, and no recorded run held a
compaction (`skill-body-budget.md`). So the evals never measured what a
long session meets: the context summarised, the skill's text cut or gone,
and a project that may have changed since the summary's last check. A
summary can carry a stale fact as well as drop one: "the checker passed"
holds for the files it checked, not for the files as they are now.

`skill-body-budget.md` keeps the whole body inside the 5000 tokens that
Claude Code re-attaches after a compaction. Claude Code's skill page states
that rule for a skill "invoked", through the Skill tool
(<https://code.claude.com/docs/en/skills>, "Skill content lifecycle"). The
Construct 3 block that `install.py` writes has the agent read
`.agents/skills/construct3-agent-plugin/SKILL.md` with Read.

## Evidence

The compactions in the Claude Code transcripts stored on one machine, after
this skill's SKILL.md had reached the model, read with
`dev/evals/trace.py`:

| How SKILL.md was loaded | Compactions | What the attachments after it carried | SKILL.md read again after it |
|-------------------------|-------------|---------------------------------------|------------------------------|
| The Skill tool | 16 | Its text, 20 000 characters, every time | 0 |
| Read or a shell read | 30 | A reference to its path, 20; nothing, 10 | 9 |

So a run that read the skill, the route the block gives every agent, keeps
at most the file's path after a compaction, and two runs in three went on
without reading it again. The 5000-token budget holds only for the Skill
tool route.

`claude -p "/compact" --resume <session>` compacts a session at a chosen
point and writes the same `compact_boundary` entry as auto-compaction, with
`trigger` manual (<https://code.claude.com/docs/en/agent-sdk/slash-commands>).

## Options

1. Wait for auto-compaction in a long case. A context has to fill first,
   which takes a long task or a small context window, and the point where
   it compacts varies from run to run.
2. Two turns of one session, `/compact` between them in the compact arms.
   The second turn always starts from a summary, and an arm without
   `/compact` runs the same two turns as the control.
3. Measure only from stored production transcripts. They show the routes
   but cannot compare arms, and nothing in them sets what changed between
   two turns.

## Decision

Option 2. `keep-checking-after-compaction` asks for the countdown of
`add-countdown` in its first turn and the larger coins in its second, so it
reuses that case's assertions and runtime plan. Between the turns
`run_session.py` compacts the session in an arm whose name has the word
compact, then inverts the sheet's first On start of layout: a change the
summary does not know, which a check run after the last edit finds. Its own
assertion fails a run that hands the project over as checked while the
checker fails on it.

The arms are `with_skill` (two turns, no compaction), `with_compact` (the
block's route, SKILL.md read) and `with_claude_compact` (the skill under
`.claude/skills`, where Claude Code finds it and can call it through the
Skill tool). The deciding column is `checked_after_last_edit`; trace.py
also gives what the compaction kept of SKILL.md (`compaction_skill`),
whether it was read again, how far the check chain got and how many lookups
came before the first edit after it.

## Re-evaluate when

- Claude Code re-attaches a file a session read, or stops re-attaching an
  invoked skill.
- The block has the agent load the skill another way than Read.
- Runs of the case show the compact arms check after their last edit as
  often as the control; then the case stops telling the arms apart, and a
  harder change between the turns is the next step.
