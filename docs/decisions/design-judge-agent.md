# The Design Questions Go to a Reviewer That Has Not Seen the Request

Date: 2026-10-29

## Problem

`review_design.py` asks seven fixed questions about the event sheets, and
the agent that wrote the events answered them. `verify_change.py --answered`
records that answer without reading it. That agent knows what its change
was meant to do, so it reads the events as it meant them, and a question
about its own work tends to pass. The look questions already go to a reviewer
that has not seen the game (`look-judge-agent.md`); the design questions had
no such reviewer.

The `--prepare` batches cannot be that reviewer's input. On a one-sheet
official example the batch holds 300 000 characters on one line, about
150 000 tokens, most of them object type and layout files. The Read tool
refuses it. The agent answers the questions from the question list and
the sheets as `print_sheet.py` prints them, about 30 000 characters for the
same example.

## Evidence

The new brief holds the seven questions, the events each names, the form of
the reply and every reviewed sheet as `print_sheet.py` prints it. Six briefs
were judged with the agent's body as the system prompt, Read alone and
`claude -p`, two runs per model:

- two planted projects of the test suite, with 13 labelled answers between
  them: a one-trigger decision split by globals, two sibling events that
  differ in their numbers, one fact kept in an Array and an instance
  variable, globals that one function alone uses and a UID kept in an
  instance variable;
- two official examples of 20 000 and 31 000 characters;
- a demo project, not an official example, of 39 000 characters, on
  which the rules name no event;
- a small stand-in game of 5 000 characters.

| | Sonnet 5.5 | Haiku 5.5 |
|---|---|---|
| Labelled answers right, per run | 13 of 13, both runs | 13 of 13, both runs |
| Official examples: a yes beyond the one the question names | none, both runs alike | 6 over 4 runs, unlike between runs; 4 of them change what the game does |
| The demo project | both runs: seven sibling events that do one thing for seven object types, and a variable that copies a count the engine keeps | both runs found a variable that copies a condition; neither found the seven events |
| Cost per brief | 0.017 to 0.093 USD | 0.001 to 0.009 USD |
| Seconds per brief | 11 to 29 | 14 to 59 |

The wrong yes answers of Haiku make three changes, and each changes what the game does: an
`Else` in place of the second of two axis tests, which then runs when the
axis is 0; a test of an animation dropped as a copy of a health value, when
a timer later changes the animation and not the health; and two movement
events moved under an on-floor test that one of them never meets.

On the demo project the rules of `review_design.py` named no event.
The judge found both defects by reading the whole sheet, under questions 3
and 7, which had asked about no event.

The replies, the briefs and the scripts that ran them are in
`.local/docs/evidence/design-judge/`.

## Options

1. Keep the writer answering. No cost, but the review stays a check of
   intent by the one who had it.
2. A judge on the `--prepare` batches. The batches are the complete
   evidence, but a judge cannot read them with Read, and each costs about
   150 000 input tokens for a small project.
3. A brief from `review_design.py` and a read-only judge on Haiku. Cheapest,
   but it adds yes answers that would break the game, and its answers differ
   between runs.
4. The same brief and judge on Sonnet (chosen).
5. Also check the reply with a `--reply` step, as `review_look.py` does, and
   pass `verify_change.py` only on a checked reply. Left for later.

## Decision

Option 4. Without `--prepare`, `review_design.py` writes
`.tmp/scripts/review-design/brief.md` and prints a `brief:` line above its
summary, where `verify_change.py` keeps it. Under
`CONSTRUCT3_RAG_NO_RECORD=1`, which the sweeps over the official examples
set, it prints the line and writes no file. `plugin/agents/design-judge.md`
is shown as `construct3:design-judge`, with `tools: Read`,
`model: claude-sonnet-5-5` and `omitClaudeMd: true`. `project-worker` gives a
brief of `review_design.py` to it and a brief of `review_look.py` to
`construct3:look-judge`. A session without the plugin gives the brief to
any sub-agent, or the agent answers the questions itself from
`print_sheet.py`. `verify_change.py --answered` still records the answers
without reading them.

## Re-evaluate when

- An eval iteration runs the skill with this change: the brief line and the
  reworded `next:` lines are script output, and the routing to the type is
  unmeasured. Check in the transcripts that main agents give the brief to
  the type and pass no model.
- The questions change, or structure questions join them: judge the same
  six briefs again, two runs per model.
- A sheet's brief passes about 100 000 characters: the judge then reads it
  in parts, and whether it still answers every question is unmeasured.
- `claude-sonnet-5-5` is retired or a newer Sonnet arrives.
