# The Check Loop Stays Inside the First 5000 Tokens of SKILL.md

Date: 2026-10-21
Schema: Construct 3 r495.2

## Problem

Claude Code keeps a skill across a compaction by re-attaching it: "Claude
Code re-attaches the most recent invocation of each skill after the
summary, keeping the first 5,000 tokens of each. Re-attached skills share a
combined budget of 25,000 tokens", filled from the most recently invoked
skill (<https://code.claude.com/docs/en/skills>, "Skill content
lifecycle"). The body of `plugin/skills/construct3-agent-plugin/SKILL.md` ran
past that budget, and "Check after every change" was its last section but
one. So the first compaction of a long session dropped the six steps of
the check loop, the `stop:` rule and the hand-over order, and kept the
sections on looking an ACE up and reading a sheet. The recorded eval
transcripts hold no compaction (`skills-dev/evals/token_share.py`), so the evals
never showed it.

Moving the loop up fixed that, but left its end 9 tokens under the cut: a
one-sentence change above it failed the test and had to be cut down to fit.
The sections every activation needs had no room to grow.

## Evidence

Three sources set the size of the body:

- Anthropic's skill guidance: "Keep `SKILL.md` under 500 lines. Move
  detailed reference material to separate files" (the page above, "Add
  supporting files"), and reference files linked one level deep from
  `SKILL.md`
  (<https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>,
  "Avoid deeply nested references").
- The Agent Skills specification, "Progressive disclosure": the full body
  "< 5000 tokens recommended", resources loaded only when required
  (<https://agentskills.io/specification>).
- Claude Code's re-attach: the first 5000 tokens of the body after a
  compaction.

Which tokenizer the cut uses is not published. Two proxies were at hand:

- tiktoken's `cl100k_base`: about 4 characters a token on this file.
  Claude Code's count is Claude's, not OpenAI's.
- Anthropic's glossary
  (<https://platform.claude.com/docs/en/about-claude/glossary>, "Tokens"):
  on the models before Claude 4.7 a token is about 3.5 English characters,
  and Claude 4.7 and later produce about 30 percent more tokens for the
  same text. So about 2.7 characters a token on the models the user runs,
  half again the cl100k count.

A direct measurement, `claude -p` with and without the body and the
difference of the usage, needs a signed-in CLI or an API key. Until one
measures it, the test estimates at 2.7 characters a token, the
conservative proxy, and prints the cl100k count beside it.

The body's sections in tokens at 2.7 characters a token (cl100k in
brackets), before and after the Scripts table was split:

| Section | Before | After |
|---------|--------|-------|
| Before the first command | 993 | 993 |
| Scripts | 2372 (1535) | 1017 (659) |
| Check after every change | 1413 | 1413 |
| Where the check loop ends | 4991 | 3636 |
| The four sections that teach the tools | 2292 | 2292 |
| The body | 7283 (4820) | 5928 (3944) |

The table had a row for each of 25 scripts and assets, and most rows
listed flags and outputs that the script's `--help` or its own output
gives at the moment they matter: the `open_in_editor.py` row repeated the
rule that the editor report goes out only at the user's word, which the
script prints when it offers the report. Two earlier trims of this kind
lost nothing in the evals (`project-tools-skill.md`, "What holds the design
in place": iterations 35, 64 and 65). Fifteen rows name scripts a task
needs now and then: the design checks, the look, sounds, a picture of a
sheet, Advanced Random, export, packing, art, a new project, the install,
the generator template and the runtime probe. Most of them are reached
through a reference that names them already (`designing-a-game.md`,
`generating-a-project.md`, `export-project.md`, `reading-the-runtime.md`);
`review_look.py` is step 6 of the loop.

Iteration 67 ran the split against the commit before it with Haiku, on
`design-a-catch-game`, which needs `check_design.py`, a moved row, and on
`add-countdown`, which needs only rows that stayed. Every run of both arms
reached `check_design.py` through `designing-a-game.md`, and no run opened
`references/scripts.md`. The pass rates of the two arms were equal per case,
and the split lost no more calls (scored runs):

| Case | with_skill lost calls | old_skill lost calls |
|------|-----------------------|----------------------|
| design-a-catch-game | 1 | 2, 3 |
| add-countdown | 2, 2 | 2, 3 |

The permutation test gave no verdict: three runs were void, two of them by
a write `trace.py` read wrongly (`2>/dev/null)`, and paths in the text of
an answer), one by a mistyped run folder, so a cell kept one run.

## Options

1. Bring the whole body under 5000 tokens, as the specification
   recommends. By cl100k it is; by the 2.7 estimate the four sections
   that teach the tools must move out as well, and every task that edits a
   sheet then reads one more file first.
2. Hold the end of "Check after every change", not the body's, inside 5000
   tokens at 2.7 characters a token, with the loop right after the Scripts
   table. What follows it teaches tools whose output teaches it again: a
   lookup prints the `write:` line, a print the numbered events,
   `edit_sheet.py --help` the plan, and a compacted session has run them
   already.
3. As 2, and cut every row of the Scripts table to what picks the script.
   The loop ends at about 4120 tokens, all 25 names stay in the body.
4. As 3, and move the rows of the scripts a task needs now and then to
   `references/scripts.md`, one sentence under the table naming what they
   are for. The loop ends at about 3640. An agent reads one more file
   before it uses one of those scripts, and the body names them by task,
   not by file. Guidance split over files reached fewer runs than one text
   in earlier iterations (`plugin-script-menu.md`, "Evidence"), so no
   step of the check loop depends on a moved row: the one moved script the
   loop runs, `review_look.py`, is named with its command in step 6.
5. Measure Claude's count first and decide after. The measurement needs a
   login this machine lacks.

## Decision

Option 4. The order of `SKILL.md` is: what to do before the first command,
the table of the scripts most changes use, the sentence that sends the
others to `references/scripts.md` and links `export-project.md` and
`reading-the-runtime.md` straight from the body, so no reference sits two
links deep, then the check loop, the three sections on the tools and the
generator. The moved rows keep their full wording, since that file is read
only when a task needs it. About 1360 tokens are left above the loop.

`tests/test_skill_spec.py` holds it:
`test_the_check_loop_survives_a_compaction` fails when the end of "Check
after every change" passes 5000 tokens at 2.7 characters a token, and
names the line of the cut and the sections after it;
`test_every_script_has_a_row_in_one_table_of_scripts` fails when a script
has a row in neither table or in both. The 500-line test stays.
`skills-dev/AGENTS.md`, "Rules", says which table a new script goes in.

## Re-evaluate when

- A signed-in `claude` CLI or an API key is at hand: measure the body with
  `claude -p` twice, with and without it, and replace 2.7 with the measured
  ratio in the test and here.
- An eval iteration with full cells runs on this text (`skills-dev/AGENTS.md`,
  "Evals"), above all a case that needs a moved script that no other
  reference names, such as `advanced_random.py` or the sound scripts: a
  run that never opens `references/scripts.md` and misses the script
  brings its row back to the body.
- The Claude Code page changes the 5000 or the 25,000, or names the
  tokenizer.
- A compaction appears in a recorded transcript: `skills-dev/evals/token_share.py`
  can then show what was re-attached.
