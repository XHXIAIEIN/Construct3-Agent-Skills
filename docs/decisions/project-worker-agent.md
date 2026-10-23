# A sub-agent type that carries only the tools the scripts need

Date: 2026-10-24

## Problem

A main agent that hands a sheet change or a lookup to a sub-agent starts a
general-purpose one, and every eval run is a general-purpose sub-agent. Such
a sub-agent starts with every tool, every connected server and the lists of
skills and agents of the session before its first step. A sub-agent type
whose definition names its tools starts with the definitions of those tools
alone.

Besides the shells, the file tools and search, the scripts ask for a
sub-agent. `review_look.py` ends with a `brief:` line for a reviewer that
has not seen the project, and only an agent with the Agent tool can start
one.

## Evidence

First context of the sub-agent transcripts stored on one machine, by type,
measured with `dev/evals/token_share.py --files`:

| Type | Transcripts | Median first context, tokens |
|------|-------------|------------------------------|
| general-purpose | 1 210 | 42 400 |
| workflow sub-agent | 1 362 | 52 000 |
| Explore | 9 | 34 200 |
| writing-reviewer, its tools named | 147 | 13 000 |
| ace-lookup, Bash, Read, Grep and Glob | 2 | 12 800 |

In one production game project, most sub-agent responses came from
general-purpose and workflow sub-agents.

A comparison on one eval case ran three Haiku runs an arm, graded with
`grade.py --play`, in a Linux container off the owner's machine. The
`project-worker` arm started with half the context, 18 200 against 37 200
tokens, and cost about a third less. The route is what the comparison
watched: the first script a run calls, whether the check chain reaches
`review_look.py`, and how many plans were refused. A prompt that listed the
steps became the route, and its runs skipped `review_look.py`, which the
list left out. With a prompt that sends the run to `SKILL.md` and the
scripts' last lines, the route stayed within the spread of the
general-purpose runs. Three runs an arm, one of them void, cannot show the
two routes equal. The runs are in
`.local/docs/evidence/skill-evals/construct3-agent-plugin/`.

Iterations 71 and 72 measured whether a worker gives the brief of
`review_look.py` to `construct3:look-judge`. Each ran two cases,
`fix-next-round` and `fix-wasd-twitch`, whose runs all reach
`review_look.py`. Each case and arm has two runs, graded with
`grade.py --play`. Each run is a `claude -p` main session on Haiku 5.5 that
loads the plugin with `--plugin-dir` and hands the case to the worker. The
arms of an iteration differ only in the worker's definition:

| Iteration | Worker | Gave the brief to the judge | Passed every assertion | Tool calls | Ended with the look step not passed |
|-----------|--------|-----------------------------|------------------------|------------|-------------------------------------|
| 72 | Agent, and the prompt's sentence on the brief | 3 of 4 | 4 of 4 | 19 to 23 | 2 of 4 |
| 72 | Neither | 0 of 4 | 4 of 4 | 21 to 35 | 0 of 4 |
| 71 | Agent alone | 0 of 4 | 4 of 4 | 20 to 28 | 2 of 4 |
| 71 | Neither | 0 of 4 | 4 of 4 | 26 to 35 | 0 of 4 |

- Every run reached `review_look.py` and started with `check_project.py`,
  and each arm of iteration 72 has one refused plan.
- Each judge ran on `claude-haiku-5-5`, as no worker passed a model. It read
  the brief and each screenshot and answered in the brief's line form. The
  worker saved the reply as `reply.md`.
- With Agent alone, every worker read the screenshots itself, the path that
  the brief line gives after "Otherwise". Asked to list its tools, that
  worker names Agent, so the tool reaches it. The one worker of iteration 72
  that kept the brief read the screenshots itself too.
- "Ended with the look step not passed" is the look step of the check
  chain as `dev/evals/trace.py` counts it. The workers that did so left the
  last `verify_change.py` run with the look step asked. The assertions grade
  the fix, which the preview plays, and every run passes them.

The runs are in
`.local/docs/evidence/skill-evals/construct3-agent-plugin/iteration-71/`
and `iteration-72/`.

## Options

- Keep general-purpose sub-agents: nothing to ship, and every response of a
  sub-agent reads the whole session's tool list again.
- A sub-agent type in the plugin's `agents/` folder, its tools named
  (chosen). Claude Code reads it from the plugin; `tools` is a list of the
  tools it may use, and a plugin's agent cannot set servers, hooks or a
  permission mode of its own.
- The same type without Agent: the worker can only answer the brief of
  `review_look.py` itself, on the session's model.
- Agent without a sentence on the brief in the worker's prompt: no worker
  started the judge in iteration 71.
- The same definition written by `install.py` into a game project's
  `.claude/agents/`: it reaches a project that holds a copy of the skill and
  no plugin, but it is one more file `install.py` keeps current.

## Decision

The plugin ships `agents/project-worker.md`, shown as
`construct3:project-worker`. Its tools are Bash, PowerShell, Read, Edit,
Write, Grep, Glob, Skill and Agent: the shells the scripts run in, the
reads and edits of project files and plans, search, the Skill tool for the
plugin's skill, and the Agent tool for the sub-agent that the brief of
`review_look.py` asks for. Its prompt sends it to the skill's `SKILL.md`
before the first project file and keeps its files inside the project. When
a script prints a `brief:` line, the prompt has the worker give the brief
to `construct3:look-judge` as its whole task, without a model, because the
judge has not seen the project (`look-judge-agent.md`). The worker starts
the judge two layers below the main session. Claude Code allows three
layers by default (<https://code.claude.com/docs/en/sub-agents>, "Let
subagents spawn their own subagents").

The eval iterations of the skill stay general-purpose: the first comparison
above is small and ran off the owner's machine, and the runs of every
iteration before it are general-purpose, so a switch changes what new runs
are compared against.

`SKILL.md`'s plugin bullet names the type for a sheet change or a lookup
handed to a sub-agent. A change to that sentence is an eval iteration
(`dev/AGENTS.md`, "Evals"). Its runs are main sessions started with
`claude -p --plugin-dir`, as in iterations 71 and 72, because the type
exists only in a session that loads the plugin.

## Re-evaluate when

- A comparison on the owner's machine with every run valid shows this
  type's route within the spread of general-purpose runs: then evals start
  their runs as this type. A route that falls short of the general-purpose
  runs', there or in a week of production transcripts read with
  `token_share.py`, means a tool the scripts need is missing from the list,
  or the prompt is steering the route again.
- Workers with Agent end with the look step not passed in 4 of 8 runs of
  iterations 71 and 72, and workers without it in 0 of 8. The step passes
  only when `verify_change.py --answered` records the answers.
  `review_look.py --reply` does not record them, and when every answer is
  no it ends with "the look review is done". One worker of iteration 72 ran
  `--reply` with the judge's reply and then `verify_change.py` without
  `--answered`. If more runs or production transcripts show the same, the
  line that `review_look.py --reply` ends with is the place to name
  `verify_change.py --answered`.
- Workers keep the brief in most runs: the sentence on the brief does not
  reach them, and the brief line of `review_look.py` is the next place to
  name the judge.
- A game project without the plugin that delegates sheet changes is the
  case for writing the definition from `install.py`.
