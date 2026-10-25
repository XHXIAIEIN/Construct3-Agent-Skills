# A Problem Report the Agent Writes from Its Own Session

Date: 2026-10-26

## Problem

A user had an agent write an effect addon with the skill. It took four or
five hand-overs before the addon installed and ran, and it failed again
several times once it was used in the user's project. The maintainers heard
of it as one sentence and a screenshot of the agent's summary, which said
the addon had passed static and numeric checks but had never been installed
or previewed in the editor. Nothing in that summary named an error the
editor showed, so none of it could become a checker rule or a fix.

## Evidence

- Every error message, its cause and its fix were in the agent's session,
  and in no other place. The user reads only the summaries.
- A checker rule matches the editor's own words
  (`references/checker-rules.md`), so a paraphrased or translated message
  cannot be matched.
- The skill already has `open_in_editor.py --install-addon --preview`,
  which installs an addon and runs a preview. A report that says which
  checks ran shows whether a run did not know of a tool or found the tool
  short.

## Options

- Ask users to describe what went wrong: users relay the summaries, which
  hold no error text.
- A template in the README for users to fill: the user does not have the
  error text, the cause or the fix either.
- A reference the agent reads to write the report from its own session,
  with the errors verbatim, the stage and round of each, what it ran, and
  whether a check could have caught the error before the hand-over.

## Decision

The third: `references/reporting-a-problem.md`, which `SKILL.md` points at
when a handed-over change came back with an error twice or the user asks how
to report a problem. The agent offers the report once, gives it to the user
and leaves the filing to the user. Since an issue is public, the agent
first replaces keys, paths, accounts, ids and the user's own content with
placeholders, and asks which of the project's names may stay, because a
name can be what the error is about. The rules are prose for now: a script
that checks the report, reusing the key scan of `secret-scan.md`, waits
until reports show what the agents miss. An addon report adds the addon's type, sample, SDK version,
renderers and files, and the stages an addon fails at.

Problems from earlier sessions, often in another project, are in no
session the user has open now. The reference says where the common agents
keep their transcripts (Claude Code, Codex, Cursor, Gemini CLI and
Antigravity, GitHub Copilot, WorkBuddy), as found on a machine that has
them, has the agent ask before it reads them, and
has it search them for the errors instead of reading them whole. Users
learn of the report from the README's "Reporting a problem" and the
problem report issue template, which both give the one sentence to tell
the agent and the reference's URL for a copy of the skill that predates it.

## Re-evaluate when

Reports arrive without verbatim errors or with the stages mixed up, or
agents offer the report on changes that did not come back.
