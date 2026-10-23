# The Look Judge Is a Read-Only Sub-Agent Type on the Measured Model

Date: 2026-10-23

## Problem

`review_look.py` ends with a `brief:` line: an agent that can start a
sub-agent gives it `brief.md` as its whole task. The line names no type, so
a Claude Code main agent started a general-purpose sub-agent. That judge
has every tool of the session, Edit and Write among them, and the session's
model unless the main agent passes one. The questions were measured on one
Haiku and one Opus judge (`look-judge-calibration.md`), so a judge on
another model gives answers that nobody measured, and a judge that can edit
can change the game that it judges.

## Evidence

The regression set of `look-judge-calibration.md` is in
`.local/docs/evidence/look-judge/`, rebuilt from the transcripts that made
it. Scored against its labels, that record's Haiku and Opus replies give the
record's tables exactly. The folder also holds every reply below and the
scripts that ran them.

Each run below is a `claude -p` main session that hands each of the 30
briefs to one sub-agent, as a main agent does after `review_look.py`. The
reply comes from the sub-agent's transcript and is scored with
`dev/evals/judge_look.py --score`. Agreement is out of 35 screenshots, and a
reply that leaves a screenshot unanswered lowers it.

| Judge | Agreement, questions 1 to 6 | Yes answers on the 13 screens without a fault | Screens with a fault that get a yes, of 22 | Faults put in on purpose found, of 9 | Replies not read in full |
|-------|------|----|----|----|----|
| General-purpose, Haiku, the record's run | 28 31 34 34 31 33 | 5 | 21 | 7 | 0 |
| General-purpose, Haiku, run 1 | 27 29 33 28 31 33 | 5 | 20 | 7 | 1 |
| General-purpose, Haiku, run 2 | 28 27 32 28 27 28 | 3 | 19 | 7 | 3 |
| `construct3:look-judge`, run 1 | 30 29 33 30 29 32 | 7 | 20 | 7 | 1 |
| `construct3:look-judge`, run 2 | 25 29 35 32 30 33 | 5 | 20 | 7 | 2 |

- The type's runs lie within the spread of the general-purpose runs.
  Between its two runs, each setup moves a question by up to 5. Neither
  setup is ahead on every question.
- On the screens without a fault, the type gives 7 and 5 yes answers. The
  general-purpose runs give 5 and 3.
- One run of the record's setup scores question 4 at 34, and two later
  runs score it at 28. So compare two runs per arm or more, not one run
  against the record's numbers.
- The type starts with 2 494 tokens of context in every run, against a
  median of 56 371 and 56 765 for the general-purpose runs. The 30 briefs
  cost 0.45M and 0.44M input-token equivalents against 1.31M and 0.94M
  (`dev/evals/token_share.py`). The type also starts without the user's and
  the project's `CLAUDE.md`, which the general-purpose transcripts carry.
- A custom type's system prompt is its body alone, without Claude Code's
  own prompt. A body that does not give the answer's form leaves 3 of 30
  replies unreadable in one run: two put the screenshot's number where the
  question's number goes, and one answers two of six questions. The body
  that gives the line form leaves 1 and 2, as many as the general-purpose
  runs.
- The alias `haiku` names `claude-haiku-4-5` in an older Claude Code and
  `claude-haiku-5-5` in a current one. The full ID runs `claude-haiku-5-5`
  in both. The record's Haiku judge is `claude-haiku-5-5`.
- 12 main sessions with the plugin loaded, 6 on Sonnet 5.5 and 6 on Haiku
  5.5, got the `brief:` line as shipped or reworded to name the type. All 12
  started `construct3:look-judge`, and none passed a model. The type's
  description routes the brief, so the script's line needs no change.
- Claude Code's documentation lets a plugin's agent set `tools` and `model`
  and ignores only `hooks`, `mcpServers` and `permissionMode`. A model that
  the Agent call passes takes precedence over the definition's `model`.
  Every run opened its screenshots with Read, which returns a PNG as an
  image.

The set has 35 screenshots, Opus agents labelled it, and each arm ran
twice. On these screens the type judges as well as the general-purpose
sub-agent. The numbers are a comparison of two setups, not an accuracy to
expect on other games.

## Options

1. Keep the general-purpose sub-agent. Nothing ships, but the judge can
   edit, runs whatever model the session runs, and starts with about 56 000
   tokens.
2. A plugin type with the model alias `haiku`. Which model the alias names
   depends on the client's version, so on an older client the judge is a
   model that nobody measured.
3. A plugin type with Read alone, the full model ID of the measured Haiku,
   and no `CLAUDE.md` (chosen). Opus agrees more with the labels, but the
   labellers are Opus, so its agreement is close to a model agreeing with
   itself, and it costs more.
4. Also name the type in the `brief:` line of `review_look.py` and in
   `references/verifying-a-change.md`. Every routing run started the type
   without it, and a change to what a script prints needs an eval iteration
   of its own.

## Decision

Option 3. `plugin/agents/look-judge.md` is shown as `construct3:look-judge`,
with `tools: Read`, `model: claude-haiku-5-5` and `omitClaudeMd: true`. Its
body says to read the brief, open each screenshot, answer every question,
and give one line per screenshot and question in the brief's form. The
brief stays the whole task, so the judge sees nothing of the game but its
pictures, and it cannot write to the project.

`review_look.py` and its references name no type. A session without the
plugin gives the brief to any sub-agent, or answers it itself. The model in
the definition is a default: a model that a main agent passes takes its
place. `dev/evals/judge_look.py --model` runs the judge through `claude -p`
with Read alone.

## Re-evaluate when

- `claude-haiku-5-5` is retired or a newer Haiku arrives: run the set with
  the type on the new ID, two runs, against a general-purpose judge on the
  same day.
- Production transcripts show a main agent passing a model to this type.
  The pin then does not hold, and the `brief:` line has to say not to pass
  one.
- The questions or the brief change: compare two runs per arm or more, not
  the record's single run.
- A plugin's agent loses `omitClaudeMd`, or the type's replies come back
  unreadable more often than a general-purpose judge's.
