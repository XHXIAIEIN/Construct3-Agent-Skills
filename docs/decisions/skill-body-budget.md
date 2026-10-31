# SKILL.md Holds Facts and Tool Entries Inside 5000 Tokens

Date: 2026-10-30
Schema: Construct 3 r495.2

## Problem

Claude Code keeps a skill across a compaction by re-attaching it: "Claude
Code re-attaches the most recent invocation of each skill after the
summary, keeping the first 5,000 tokens of each. Re-attached skills share a
combined budget of 25,000 tokens", filled from the most recently invoked
skill (<https://code.claude.com/docs/en/skills>, "Skill content
lifecycle"). The body of `plugin/skills/construct3-agent-plugin/SKILL.md`
was about 5400 tokens. It held the check loop inside the first 5000 by
order alone, and a one-sentence change above the loop could push its end
past the cut.

Much of the body told the agent to take steps that the scripts already
name. `verify_change.py` ends with the next thing to do, `edit_sheet.py`
ends with the `verify_change.py` command, and `search_guides.py` prints the
`git clone` of a missing Cookbook. Anthropic reports that newer models need
less of this: over 80% of the Claude Code system prompt was removed for
Claude Opus 5 with no measurable loss on its coding evals
(<https://x.com/addyosmani/status/2115688494865465370>).

## Evidence

The cut uses Claude's tokenizer, which is not published. Anthropic's
glossary gives about 3.5 English characters a token before Claude 4.7 and
about 30 percent more tokens since
(<https://platform.claude.com/docs/en/about-claude/glossary>, "Tokens"),
so the test estimates 2.7 characters a token. tiktoken's `cl100k_base`
counts about a third fewer and is printed beside the estimate.

Iterations 80 and 81 ran a body cut to facts and tool entries against the
full body: countdown-between-rounds, fix-wasd-twitch, lay-out-the-hud and
find-in-a-long-sheet, two runs a cell. The cut body left out the check
loop, the design reading, the `agents` branch and the hand-over wording,
and stated the gotchas as facts.

| | Opus 5.5 (80) | Haiku 5.5 (81) |
|---|---|---|
| Runs that passed everything, full / cut | 7 of 8 / 6 of 8 | 8 of 8 / 8 of 8 |
| Change runs that reached the look check | 12 of 12 | 12 of 12 |
| Change runs that committed on `agents`, full / cut | 6 of 6 / 0 of 6 | 6 of 6 / 0 of 6 |
| Runs that read `design/thinking.md` on the two sheet cases, full / cut | 1 of 4 / 1 of 4 | 2 of 4 / 0 of 4 |

The Opus difference is lay-out-the-hud. Three runs of both arms put the
hearts 97 to 114 px down, and every Haiku run of both arms passed it. The
check chain held without the loop because the scripts print each next
step. The `agents` branch is a convention that nothing in the files or the
output teaches, and it was lost on both models. Haiku skipped the design
guide without its sentence.

Iteration 84 ran the body with those two rules kept against the full one on
Haiku 5.5. Every change run of both arms committed on `agents`, and the
runs passed alike: the one failed run gave the right events in Chinese,
which the grader does not read.

## Options

1. Keep the full body and hold only the end of the check loop inside 5000
   tokens. The loop is text that the scripts repeat, and the sections above
   it have no room to grow.
2. Cut the body to facts and tool entries. It loses the `agents` branch and,
   on a small model, the design reading.
3. As 2, and keep as instructions the two rules that the files and the
   output do not teach: the `agents` branch with `git init`, and reading
   `design/thinking.md` with a `search_guides.py` run before an
   interaction is designed.

## Decision

Option 3. `SKILL.md` gives where things are, the rules before the first
edit (git and the design guide), the table of the scripts that most changes
use, a short legend of `verify_change.py`'s output, the facts once written
as gotchas, the sections on looking up an ACE, reading a sheet and changing
it with a plan, and a table of the references and Cookbook pages. The body
is about 4000 tokens at 2.7 characters a token (2691 by cl100k), so a
compaction keeps all of it.

`dev/tests/test_skill_spec.py` holds it.
`test_the_whole_body_survives_a_compaction` fails when the body passes 5000
tokens at 2.7 characters a token, and it names the line of the cut and the
sections after it. `test_every_script_has_a_row_in_one_table_of_scripts`
fails when a script has a row in neither table or in both. The 500-line
test stays. `dev/AGENTS.md`, "Rules", says when a line is a fact and when it
stays an instruction.

## Re-evaluate when

- A case that the four cases above do not cover fails without an
  instruction that the cut removed, such as one where the editor is open or
  where the hand-over needs the events that changed. That line comes back.
- A rule is added that the scripts do not print and the files do not show.
  It goes in "Before the first edit".
- A signed-in `claude` CLI or an API key is at hand: measure the body with
  `claude -p` twice, with and without it, and replace 2.7 with the measured
  ratio in the test and here.
- The Claude Code page changes the 5000 or the 25,000, or names the
  tokenizer.
