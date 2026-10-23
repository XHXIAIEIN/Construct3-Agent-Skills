# `dev/` Directory

The skill lives in the plugin folder,
`plugin/skills/construct3-agent-plugin/`. It is an Agent Skill in the open
format of <https://agentskills.io/specification>: a `SKILL.md` with `name`
and `description`, and `scripts/`, `references/` and `assets/` beside it. It
holds the project tools for a Construct 3 folder project, listed under
"Scripts" in its `SKILL.md` and in `references/scripts.md`, and the
Construct 3 block for the project's instruction file.

Beside the skill, `plugin/skills/<name>/SKILL.md` is one thin skill for each
user-facing script, and `plugin/skills/run.py` is the runner that they
share. These rows give the Claude Code plugin's `/` menu one row per script,
and they never load by themselves (`docs/decisions/plugin-script-menu.md`).

This folder holds what the skill's maintainers need and the plugin does not
ship:

- this guide, and `game-project-AGENTS.md`, the guide to the block in a game
  project;
- `evals/`, which tests the skill with agents;
- `tests/`, the pytest suite (`dev/tests/AGENTS.md`);
- `scripts/`, the data build and the measurements (`dev/scripts/AGENTS.md`).

The plugin folder is held to the limits of Claude's directory
(`docs/decisions/plugin-folder.md`), so a file that the skill does not read
at run time goes here. A game project holds a copy of the skill, which the
skill's `scripts/install.py` makes and refreshes. That copy reports when it
differs from the clone's.

## Change this repository

Before you edit, read the `AGENTS.md` of every directory that you touch, and
run `git status`. Keep the changes that you did not make, because other
sessions may work in the same checkout.

`plugin/` is the source of the Claude Code plugin `construct3`, so edit the
skill, the manifest, the README, the icon and the sub-agents in place. Only
`plugin/data/` is built: `dev/scripts/build_plugin.py` writes it from the
data of the Construct3-RAG clone beside this one. The files that the plugin
does not ship are beside `plugin/`: this folder, the docs and the records.
The reasons are in `docs/decisions/plugin-repository.md`,
`docs/decisions/plugin-folder.md` and `docs/decisions/dev-folder.md`.

- Edit `plugin/` in place, except `plugin/data/`. Run the build after a data
  change, because `dev/tests/test_plugin_folder.py` fails while
  `plugin/data/` differs from a fresh build.
- The build also sets the plugin's version. While the plugin's files equal
  the published files, it sets the published version. When they differ, it
  raises the patch number by one. It never sets a version below the
  committed `version`. Raise `version` in
  `plugin/.claude-plugin/plugin.json` by hand only for a minor or major
  release (`docs/decisions/plugin-tracks-commits.md`).
- Do not add a `.gitattributes` file. Claude's directory refuses to validate
  a repository whose attributes could rewrite files at checkout, and a test
  fails on the file. A checkout with `core.autocrlf` passes the checks
  without it, because the build writes text files with LF and the checks
  read a committed CRLF text file as LF (`docs/decisions/plugin-folder.md`).
- Keep `plugin/` inside the limits of Claude's directory: 512 files, 256 KiB
  for each file other than an image, and 7,000,000 bytes in all
  (`docs/decisions/plugin-folder.md`). The build fails when the folder
  exceeds them. Put what the plugin does not need at run time in this
  folder, as the evals are.
- Make a change to a schema, a language pack, an example index or a guide in
  Construct3-RAG, because the data belongs to that repository. When its
  `main` changes, pull the clone beside this one and run the build.
  `.github/workflows/refresh-plugin.yml` does the same every day, and it
  pushes the build if the data changed. `docs/dev/data-pipeline.md` in the
  Construct3-RAG clone describes that pipeline.
- Do not write the Construct 3 version or the counts of the data into text,
  because every data refresh changes them. Read them from
  `plugin/data/c3-schemas/_index.json`.
- If a merge leaves conflicts in `plugin/data/`, run the build, stage the
  folder, then commit the merge.
- The end marker line of
  `plugin/skills/construct3-agent-plugin/assets/build_project.py` conflicts
  whenever both sides changed its helpers, because the line carries their
  stamp. If it conflicts, keep either side, then paste the end line that
  `dev/tests/test_skill_build_project.py` prints.
- A change to `SKILL.md`, to a reference or to what a script prints needs an
  eval iteration of its own, as "Evals" below describes.
- If a product choice has a visible effect, record its evidence, options and
  trade-offs in `docs/decisions/`, and add its line to
  `docs/decisions/README.md`. `docs/AGENTS.md` says how to write a record.
- Change the docs and the tests together with the behaviour. The READMEs
  describe the skill and the plugin for people, with the same content in
  English and Chinese. `README.md` contains no Chinese text other than its
  link to `README_CN.md`. Write the skill, the `AGENTS.md` files and the
  agent files in English.
- In a commit message or PR text, name an issue of another repository in
  words or by its URL in backticks. Never write `owner/repo#N` or `#N`,
  because GitHub turns these forms into a public cross-reference on that
  issue's timeline, and nobody can remove it.
- `.claude/workflows/polish.js` is a verified run that polishes the skill's
  sources, docs, records and code. Start it only when no other session edits
  the repository.

## Change a project tool

Read the row of the task, then the source and the tests that it names. The
rows locate the contracts, and the source decides what a tool does. Paths
that start with `dev/` or `docs/` start at the repository root; all other
paths in the table are under `plugin/skills/construct3-agent-plugin/`.

| Task | Responsibility and interface | Read together | Constraint and source |
|------|------------------------------|---------------|-----------------------|
| Check or resume a design review | `scripts/review_design.py --check` prints findings and questions. The optional `--prepare FOLDER --resume` supplies evidence and saved judgements | `design_review.py`, `print_sheet.py`, `c3project.py`, `dev/tests/test_skill_design_review.py`, `references/design-review.md` | A saved judgement is reused only while its input version matches. An edit carries the line that `print_sheet.py` printed for its event. `docs/decisions/plan-names-the-event-line.md` |
| Check a change as a whole | `scripts/verify_change.py` runs, in order, the checker, the design review, the editor and its preview, the kept plays and the look. Its last line is the next step, and `--status` prints where the steps stand | `check_project.py`, `review_design.py`, `open_in_editor.py`, `review_look.py`, `dev/evals/trace.py`, `dev/tests/test_skill_verify_change.py` | An editor step runs again only when a file of the project changed after it passed. A question waits for `--answered`. `docs/decisions/verify-change.md` |
| Apply an event edit | `scripts/edit_sheet.py SHEET PLAN.json --dry-run` checks the whole project with the changed sheet in place of its file | `check_project.py`, `print_sheet.py`, `dev/tests/test_skill_edit_sheet.py` | It refuses a plan that adds a problem, but it can leave the problems that are already there. So keep the final full `check_project.py` run and its fix-loop record |
| Open or play a game | `scripts/open_in_editor.py --preview`. `scripts/preview_project.py PLAN.json` drives inputs and reads state | `references/editor-and-preview.md`, `dev/evals/play_cases.py`, `dev/tests/test_skill_preview_project.py` | Opening without input tests the startup only. Reaching a scene directly does not test the path to it |
| Ship the skill to a game | `scripts/install.py --project FOLDER` mirrors the skill's folder into the game | `assets/game-project-block.md`, `c3project.py`, `dev/tests/test_skill_install.py` | An edited Construct 3 block and edited generator helpers keep their edits until `--replace-edited-block` or `--replace-edited-helpers` replaces them |
| Ship the plugin | `dev/scripts/build_plugin.py` builds `plugin/` from the skill, the menu and the data of the Construct3-RAG clone beside this repository | `dev/tests/test_plugin_folder.py`, `docs/decisions/plugin-folder.md`, `docs/decisions/plugin-tracks-commits.md` | Edit the sources, then build. The build sets the version from the plugin at the commit that HEAD shares with `origin/main` |
| Give a script a row in the plugin's `/` menu | `plugin/skills/<name>/SKILL.md` runs the script with the user's arguments through `plugin/skills/run.py` | `dev/tests/test_plugin_folder.py`, `docs/decisions/plugin-script-menu.md` | See "Menu rows" under "Rules" |

## Rules

### The skill's folder

- Keep everything that the skill does not read at run time out of the
  skill's folder: scratch files, outputs, notes and evals. The folder is
  what ships, because `install.py` mirrors every file in it into the game
  project and the plugin carries it whole. What an eval run leaves goes to
  `.local/docs/evidence/skill-evals/<skill>/iteration-N/`, which Git ignores
  (`docs/AGENTS.md`).
- Write `SKILL.md` in ASCII. The reference validator and plain clients read
  it with the locale's codec, and under cp936 a UTF-8 sign stops them.
- `name` is the folder's name, in lowercase with hyphens. `description` says
  what the skill does and when to use it, in at most 1024 characters, on one
  line and without `: `, so that a client with a plain frontmatter parser
  reads it too.

### The body of `SKILL.md`

- Keep `SKILL.md` under 500 lines, the limit of Anthropic's skill guidance
  (<https://code.claude.com/docs/en/skills>, "Add supporting files").
- Keep everything through the section "Check after every change" inside the
  first 5000 tokens of the body. After a compaction, Claude Code re-attaches
  each invoked skill with only its first 5000 tokens (the same page, "Skill
  content lifecycle"). So the check loop comes before the sections that
  teach the tools, and the tools' output teaches them again.
  `dev/tests/test_skill_spec.py` holds both limits, and
  `docs/decisions/skill-body-budget.md` gives the token estimate and its
  source.
- Put into `SKILL.md` only what every activation needs and no script says at
  the moment it matters, because every run reads all of it before its first
  command.
- Name every script in one of two tables, which a test holds. A script that
  most changes use gets a row in the table of scripts in `SKILL.md`. Any
  other script gets its row in `references/scripts.md`, and the sentence
  under that table that names what those scripts are for gets its task.
- A row says what picks the script, not its flags and outputs. If the row
  needs more, one sentence says when to read the script's file in
  `references/`. Do not repeat what a script prints when it is needed.
  Evidence: `docs/decisions/project-tools-skill.md`, "What holds the design
  in place".

### Menu rows

- Name the row's folder `plugin/skills/<name>/`, where `name` is the
  script's stem with hyphens.
- Set `disable-model-invocation: true`, so that the row costs the model
  nothing. Write the description in the third person.
- Make `argument-hint` from groups of the script's usage line, in double
  quotes, because a YAML parser reads a hint that starts with `[` as a
  sequence.
- Write `allowed-tools` as a YAML list of the row's own command, one rule
  for the Bash tool and one for the PowerShell tool. Do not use the open
  format's space-separated string, because each rule holds spaces that the
  string form splits.
- Keep the body free of teaching, because the main skill teaches.
- A script without a row fails the build, unless `NOT_IN_MENU` in
  `build_plugin.py` names it.
- `disable-model-invocation` and `argument-hint` belong to Claude Code and
  are outside the open format. So the reference validator fails on a row by
  design, and the test pins its frontmatter instead.

### Paths

- Write a path inside the skill relative to the skill's folder, because a
  relative link out of the folder breaks in a copy. Write a path outside the
  folder as follows:
  - A file of the folder that the Construct 3 block names, `plugin/` with
    its `data/`: `Construct3-RAG/<path>`, as the block writes it.
  - A guide of the Cookbook clone: `Construct3-Cookbook/guides/<path>`.
  - A record of this repository:
    `Construct3-Agent-Skills/docs/decisions/<file>`. A record of
    Construct3-RAG: its URL. Neither is in `plugin/`.
- The plugin bullet of `SKILL.md` says where such a path lies in the plugin,
  so the skill's text names no file that the plugin holds only in a bundle.
- A script prints a file of that folder by its absolute path. It prints a
  TypeScript declaration that the plugin holds only in a bundle as the
  `lookup_script_api.py` command that prints it
  (`docs/decisions/plugin-folder.md`).

### Scripts

- Scripts use the standard library, with these exceptions:
  - `prepare_art.py` needs Pillow to read, cut out and resample pictures.
  - In `preview_project.py` Pillow is optional. It numbers the frames of a
    recording's contact sheet, which ffmpeg alone tiles without numbers, and
    it joins a recording into a GIF when ffmpeg is missing.
  - `open_in_editor.py` drives the machine's Edge or Chrome over the
    DevTools protocol. Where there is neither, it prints its check as steps
    for the agent's own browser tool.
  - `check_sounds.py` and `make_sounds.py` need ffmpeg and ffprobe on PATH.
    Without them the measurer measures nothing and exits 3, the code of a
    check that did not run (`docs/decisions/not-checked-is-not-a-pass.md`).
- Scripts take everything from flags and never prompt. They print `--help`
  with examples and exit codes, and every error says what to write or run
  next.
- Scripts find the project from the current directory upward, and the data
  folder through the project's `Construct3-RAG:` line. The code that they
  share is in `scripts/c3project.py`.
- Write a script's own text and the skill's text in English. `--locale`
  switches the schema wording that a script prints, not the script's own
  wording.

### Script output

A harness reads what a script prints, not a terminal, so the output follows
these rules:

- It is UTF-8 whatever the code page (`utf8_output`).
- It stops at `--limit`, about 10 000 characters, with a last line that says
  how to get the rest. A harness cuts longer output, not always at the end
  and not always with a notice.
- A miss lists the names that come near. A name that is not spelled out is
  refused with the nearest names, not taken for one of them.
- Everything prints on stdout, a miss and a note as much as a hit.
  PowerShell wraps a line of stderr in an error record, and a harness that
  shows stdout alone shows nothing of it. Only what stops the run before it
  answers goes to stderr with the exit code: an unusable flag, or a project
  or clone that was not found.

### Writing project files

- A script that changes a project file checks the result before it writes
  it. It writes the whole file or nothing, in the editor's layout: tabs, LF,
  no newline at the end, and the editor's keys in the editor's order. It
  also has `--dry-run`.
- `edit_sheet.py` does all of that, and its templates are the keys that the
  editor writes for each kind of event, in order. Two more scripts write
  `project.c3proj` and take `--dry-run`. `new_project.py` sets the name and
  `uniqueId` of the copied template and leaves the check to
  `check_project.py`. `export_project.py` replaces the version line once the
  export carries it.
- Derive a rule about what a project file must hold from the whole call
  chain of the editor's loader, not from the one message that a user pasted.
  The next assertion in the same function costs another round trip through
  the user.
- What the editor writes into every project is measured from the official
  examples. `dev/tests/test_skill_build_project.py` compares the generated
  project with that measurement, so a key missing from the generator fails
  here instead of in the editor.
- Before you write a rule about the folder, a file name or a file format,
  read Scirra's guide [Construct's project
  format](https://www.construct.net/en/tutorials/constructs-project-format-3275),
  kept in `plugin/data/c3-guides/constructs-project-format.md`. It states
  what the format keeps across releases: what `project.c3proj` indexes,
  image file names, the formats of sounds, fonts and icons, and which files
  the editor ignores.
- The `llm-context.md` that the editor writes into every project links that
  guide. The official examples were saved before the editor wrote that file
  (r477, `Construct3-Manual/releases/beta.json`), so a measurement over them
  shows neither the file nor anything else that the editor writes since
  then.

### The generator template and the block

- The generator template keeps its helpers between two marker lines. The end
  line carries the helpers' version and the stamp of the lines between the
  markers. `install.py` replaces that part of a game's
  `tools/build_project.py` when it is older and unedited, and keeps every
  other line.
- A change between the markers fails `dev/tests/test_skill_build_project.py`
  until you paste the end line that the test prints.
- A helper reads nothing outside the markers except what every game's
  generator has. So if a new helper needs a setting, give the setting its
  default between the markers.
- The block for the project's instruction file,
  `assets/game-project-block.md`, works the same way. Its end marker carries
  its version and the stamp of its text, without the lines that name a
  clone's folder. A change to its text fails
  `dev/tests/test_skill_install.py` until you paste the end line that the
  test prints.
- `PAST_BLOCKS` in `scripts/c3project.py` is a closed list of the stamps of
  the blocks that `install.py` wrote before the markers existed.
- The user of a game project and the agent that writes the game read the
  generator template. A comment or a docstring there names what the code
  does in a short phrase. A parameter gets only what its signature leaves
  open: unit, range, or what stops the run. A trap or a constraint keeps its
  reason, on a line of its own.
- Put the finding that settles a value of the template in the record under
  `docs/decisions/`, not in the template, because every agent that writes a
  game reads the whole template. So the template holds no measurement,
  source or path into this repository.
  `dev/tests/test_skill_build_project.py` fails on a path into this
  repository or its records, on "(WCAG" and "(manual:", and on the word
  "survey".

### Checker findings

- A check becomes an error only after the two steps in
  `references/checker-rules.md`: the editor's message, then a run over the
  official examples that adds no finding.
- A style finding, one that the editor accepts, is a warning behind
  `--style` and in what `edit_sheet.py` adds, never an error. Its threshold
  comes from a measurement over the official examples, recorded with the
  finding.

### Guidance for small models

- Put guidance meant for a small model where that model reads. That is the
  line that a script prints, such as a finding that names the event and the
  JSON to write, or the generator's helpers, which make the good shape the
  default.
- `lookup_ace.py` ends an entry with `pitfalls:` and `prefer:` lines, which
  point at the addon's pitfall pages and its row of the "Native first" table
  (`docs/decisions/lookup-pointers.md`).
- Prose reaches only the model that knows it needs it, so a prompt keeps a
  pointer with a when-clause, not the rule. A habit that has no mechanical
  form and passes the official corpus stays prose. Evidence: the runs read
  in `docs/decisions/event-sheet-design-guidance.md`, "What small models
  read".

### Comparing script output

- Compare a change to a script, old against new, over every official example
  and the game projects: exit code, stdout and stderr
  (`dev/evals/sweep_outputs.py`). A restructure shows no difference, and a
  change of output shows exactly the runs that it was meant for.
- `dev/scripts/output_diff.py [REF]` makes the comparison against a git ref
  in one command and prints the first differing line of each case. It covers
  the official examples and, with `--projects`, the game projects. It also
  covers two plans that `edit_sheet.py` refuses, every script's `--help`,
  `new_project.py` and the generator template.
- `output_diff.py`, `sweep_outputs.py` and `grade.py` set
  `CONSTRUCT3_RAG_NO_RECORD=1`. The checker then keeps no record of the fix
  loop (`docs/decisions/fix-loop-cap.md`), so its output does not depend on
  an earlier run.

## Checks

Before you finish, run the tests that the change reaches and the three quick
checks:

```bash
python -m pytest -q <test files>
python -m compileall -q dev scripts plugin/skills
python dev/scripts/build_plugin.py --check
git diff --check
```

Pick the test files from the paths in the diff:

- A change to a document reaches the tests that read documents:
  `test_doc_links.py`, `test_plugin_folder.py` and `test_cookbook_paths.py`.
  The last one checks that every `Construct3-Cookbook/...` path named in an
  `AGENTS.md` or a README exists in the Cookbook clone.
- A change to a script reaches its own tests and the tests of the scripts
  that import it. To find the importers, run `grep -l <module>` in the
  script folders, then find the tests that name any of them. A test that
  only names a word of the change, such as a constant that it never reads,
  is not reached. The skill's tests alone are `python -m pytest dev/tests -q
  -k test_skill_`.
- Run the whole suite with `python -m pytest -q` only when the change
  reaches most test files: when it changes what `dev/tests/skill_helpers.py`
  or `dev/tests/conftest.py` does, or when it moves the tests or the
  scripts, as a merge that moves folders does. Otherwise leave the whole
  suite to the workflow below.

`.github/workflows/checks.yml` runs the whole suite and the other checks on
every push to `main` and on every pull request, so a push needs no local run
of the whole suite. The tests need the Construct3-RAG clone beside this one.
The tests that read the official examples also need the
`Construct-Example-Projects` clone, and the tests that read the guides need
the `Construct3-Cookbook` clone. If a test lacks its clone, it skips and
names the command that supplies it.

The tests install the skill in a temporary project and run the copy, and
they pin the format's constraints offline.

If the frontmatter of a `SKILL.md` changes, or the specification does, also
run the reference validator. It checks only the frontmatter: the fields, the
name against the folder, and the lengths. Whether the skill helps is what
the evals measure. The validator fetches code from GitHub and runs it:

```bash
uvx --from "git+https://github.com/agentskills/agentskills#subdirectory=skills-ref" skills-ref validate plugin/skills/construct3-agent-plugin
```

If the session does not allow that, report the validator as not run. The
tests pin the same constraints.

## Evals

The method is <https://agentskills.io/skill-creation/evaluating-skills> and
<https://agentskills.io/skill-creation/optimizing-descriptions>. A change to
`SKILL.md`, to a reference or to what a script prints is a new iteration.

| File in `dev/evals/` | Holds |
|----------------------|-------|
| `evals.json` | The test cases: prompt, expected output, assertions that a script can check, and `held_out` on the cases kept out of tuning |
| `make_fixtures.py` | One project per case and arm, outside the clone: the stand-in game, an official example, the empty project of `new_project.py`, or a game that keeps its generator, the stand-in at 1920×1080, 720×1280 portrait or 320×180 pixel art, or the scrolling level of `platformer_game.py`, with this skill from a worktree of the tested commit, the previous one or none |
| `platformer_game.py` | The game part of the `platformer-generator` fixture: a level wider than the screen that the camera follows, which `make_fixtures.py` writes below the end marker of the arm's own template |
| `play_cases.py` | The plan of `scripts/preview_project.py` for each case whose request changes what the game does, and the runtime verdicts read from it. `play_cases.py CASE --project FOLDER` plays one |
| `trace.py` | What a run did, from its transcript, written to `trace.json` with the transcript kept beside it: every tool call, the calls that it lost, its turns, tokens and seconds, and its route. The route covers the first script, how far the check chain got, help reads, refused plans, hand edits, the calls before the first edit, reads of the clone, the Cookbook pages read, the `lookup_ace.py` and `search_guides.py` pointers followed, whether a passing check followed the last edit, and, for each compaction, what it kept of `SKILL.md` and what the run did after it |
| `run_session.py` | A case with `turns` run as one `claude -p` session, with `/compact` between the turns in an arm whose name contains the word compact, and the case's `between` change written into the project before the second turn |
| `token_share.py` | Where the tokens of one or more transcripts went: the cost, at the price ratios of each response's model, shared among the baseline, each script's output, the reads by file kind, the model's tool inputs and its output, with the sum checked against the cost from usage. `--files` gives each transcript's first context |
| `grade.py` | `grading.json` per run, with the evidence and the level of each assertion, and `benchmark.json` per iteration: the mean and deviation per case and arm of every cost and route column, the Cookbook columns among them, the runs that passed everything with a 95% interval, the difference between arms, the verdict of the iteration's `decision.json`, the runs that lack a part under `incomplete_runs`, and under `meta` the commits and flags the grading ran with. `<arm>_2` is a second run of `<arm>` |
| `compare.py` | The within-task permutation test of one column between two arms over a `benchmark.json`, which is the test that `grade.py` runs for the verdict |
| `measure_design.py` | What each rule of `scripts/review_design.py` finds over the official examples and game projects, with looser variants, and every hit as JSON to read before a rule becomes a finding |
| `measure_layout.py` | How much of the screen the one-screen layouts of the official 2D game examples cover, and how much larger their largest object is than the next: the thresholds of the generator template's playfield checks. `--text` measures their texts: each size against the viewport, the sizes of a layout, how near the edge the nearest text sits and how many items gather in one ninth of the screen |
| `label_look.py` | Briefs that have labeller agents answer the questions of `scripts/review_look.py` about a set of screenshots, and their replies merged into labels, with an adjudicator agent settling where they differ |
| `judge_look.py` | Those questions put to a judge that has not seen the games, through the brief that `review_look.py` writes, and the judge's agreement with the labels per question (`docs/decisions/look-judge-calibration.md`) |
| `sweep_outputs.py` | What the scripts print over every example and game project, including a dry run of a small plan, recorded and compared |
| `sweep_round_trip.py` | Every event of every example written back as `print_sheet.py --show` prints it, and the events after which `edit_sheet.py` would write a different sheet |
| `train_queries.json`, `validation_queries.json` | The trigger queries, in a fixed 60/40 split, with near misses as the negatives |
| `run_trigger_eval.py` | Trigger rates from `claude -p`, on Windows too |

```bash
# before the change
git worktree add --detach <folder outside the clone>/rag-old HEAD
python dev/evals/sweep_outputs.py .local/docs/evidence/skill-evals/construct3-agent-plugin/iteration-N/sweep-old.json --examples <example-projects> --projects <game folder> ...
# after the change
python dev/evals/sweep_outputs.py .local/docs/evidence/skill-evals/construct3-agent-plugin/iteration-N/sweep-new.json --examples <example-projects> --projects <game folder> ...
python dev/evals/sweep_outputs.py --compare .local/docs/evidence/skill-evals/construct3-agent-plugin/iteration-N/sweep-old.json .local/docs/evidence/skill-evals/construct3-agent-plugin/iteration-N/sweep-new.json
python dev/evals/make_fixtures.py <folder outside the clone>/iteration-N --arms with_skill old_skill --old-clone <folder outside the clone>/rag-old
# after each run has reported
python dev/evals/trace.py <transcript>.jsonl --out <run folder>
# where the tokens of the runs went, before and after a change that should save them
python dev/evals/token_share.py <transcript, folder or @list> ... --out .local/docs/evidence/skill-evals/construct3-agent-plugin/iteration-N/token-share.json
# after the last run of the iteration: the file assertions, and the plans played in the editor's preview
python dev/evals/grade.py .local/docs/evidence/skill-evals/construct3-agent-plugin/iteration-N --play
python plugin/skills/construct3-agent-plugin/scripts/open_in_editor.py .local/docs/evidence/skill-evals/construct3-agent-plugin/iteration-N --out .local/docs/evidence/skill-evals/construct3-agent-plugin/iteration-N/opened.json
# after a change to the description
python dev/evals/run_trigger_eval.py dev/evals/train_queries.json --project <game with .claude/skills>
```

### Laying out the runs

- Start each run clean, with one agent per case and arm. The run saves
  `outputs/answer.md` with the commands that it ran.
- Tell a baseline run to use nothing outside the project folder. A baseline
  started below the clone reads the clone's `AGENTS.md` and reaches for the
  checker. Then read the commands that its answer lists. If a run broke its
  arm, put the reason in its `void.txt`, and `grade.py` does not score that
  run.
- The previous version of the skill is the baseline of a change to it. Its
  arm, `old_skill`, names a checkout of the previous commit as its clone
  (`--old-clone`). An old copy that points at this clone reports that it
  differs, and the agent then refreshes it.
- Commit the change before you run `make_fixtures.py`. It lays out the
  `with_` arms from a detached worktree of the commit at `<runs
  folder>/clone-<sha>`, and their copies name that worktree as their clone.
  The commit is HEAD, unless `--pin REV` names another. So a pull of `main`
  during the iteration changes nothing that the runs read, and no later run
  finds that its copy differs from the clone's. `clone.json` in the runs
  folder and `clone.commit` in each fixture name the commit.
- `--no-pin` lays out from the checkout as it stands, uncommitted changes
  included, and its fixtures name that checkout. The checker then gives the
  runs a pull of the checkout if its branch trails its upstream.
- A case with `turns`, such as `keep-checking-after-compaction`, is not a
  sub-agent run. `run_session.py <run folder>` runs its turns as one `claude
  -p` session, writes `answer.md`, `timing.json` and `outputs/session.json`,
  and prints the `trace.py` command for its transcript. Lay it out with
  `--arms with_skill with_compact with_claude_compact`. `with_skill` runs
  the turns without a compaction, and the `with_claude` arms install the
  skill under `.claude/skills`, where Claude Code can call it through the
  Skill tool. Decide on `checked_after_last_edit`
  (`docs/decisions/compaction-eval.md`).

### Reading the runs

- Read the transcript of every run, not only its answer, because the answer
  lists only the commands that a run remembers. Claude Code keeps the
  transcript as
  `~/.claude/projects/<project>/<session>/subagents/agent-<id>.jsonl`. When
  every assertion passes, the lost calls are what is left to improve: a
  lookup that found nothing, or an edit that did not match.
- `trace.py --out <run folder>` lists in `trace.json` the writes outside
  that folder, such as a plan written to the launching session's scratchpad
  or an answer written one folder too high. `grade.py` does not score such a
  run.
- That list is a floor. It reads absolute paths from file tools and from the
  words of shell commands, so a relative path, a variable or a write made
  inside a script escapes it. The text of a heredoc or a here-string is
  input, not words, so a path in an answer written by `cat > answer.md
  <<'EOF'` is not a write. A call that failed before it wrote is not a write
  either, such as an Edit that returned "File does not exist" or a command
  that a hook refused.
- When a run's completion notice arrives, write the tokens and the duration
  that it gives into the run's `timing.json`. `trace.py` reads the turns,
  the output and input tokens and the seconds from the transcript. The
  benchmark's `tokens` come from `timing.json` alone, and its `seconds` come
  from `timing.json`, else from the trace. Nothing is estimated.

### Grading

- An assertion has a level: `checker`, `files` or `runtime`. A case whose
  request changes what the game does has a plan in `play_cases.py`, and each
  check of the plan is a runtime assertion. `grade.py --play` plays the
  plans on the runs' projects in the editor's preview, one at a time.
- A check finds what the run made by what it does, not by the name that the
  run gave it. If a file assertion and a runtime assertion disagree on a
  run, read the run before you trust either.
- Play a new or changed plan on its unfixed fixture first, where the
  requested behaviour must fail. Then play it on a project that does what
  the case asks, where every check must pass
  (`docs/decisions/runtime-graded-evals.md`).
- Keep a case marked `held_out` out of the loop that shapes a change,
  because a case that shapes the change no longer measures it.
  `make_fixtures.py` lays it out only with `--held-out`. `grade.py` reports
  it separately and prints its failures only with `--show-held-out`.
- Run the held-out cases once the change is otherwise done, and do not read
  their transcripts or gradings while the change is open. If a held-out case
  fails, reproduce the failure as a new tuning case first. The held-out case
  then joins the tuning set, and a new case takes its place.

### How many runs, and the verdict

- For each change to the skill, run the tuning cases that it targets with
  `with_skill` and `old_skill`, two or three runs each, and grade with
  `--play`. Before a change to the skill is merged, or weekly, run every
  tuning case twice with `with_skill`. After an accepted batch of changes,
  run the held-out cases with both arms, two runs each. `benchmark.json`
  records what each run cost.
- One run per case and arm gives counts, not a spread. Before you quote a
  deviation, lay a cell out more than once, as in `--arms with_skill
  with_skill_2`, because the lost calls vary widely between two runs of the
  same cell.
- The benchmark gives the runs that passed every assertion as k of n with a
  Wilson 95% interval. At two to four runs the interval spans most of 0 to
  1, so quote n with it.
- Decide a change on one column, chosen before its runs. `benchmark.json`
  holds, beside the cost, the columns that `trace.py` counts from each
  transcript, averaged per cell: `read_skill_md`, `chain_depth` and
  `chain_attempts` (how far the check chain got, and in how many calls),
  `preview_failed`, `help_reads` and `repeat_help`, `plan_refusals`,
  `hand_edits`, `lookups_before_first_edit`, `data_reads` and
  `other_clone_reads`, `entry_chars`, `printed_command_failures`,
  `print_sheet_chars`, `whole_sheet_prints`, and `cookbook_reads`,
  `pointers_printed`, `pointer_follows`, `read_design_guide` and
  `cookbook_misses` (how the run used the Cookbook). `first_script`,
  `chain_end` (the deepest step that passed) and `chain_reached` (the
  deepest step called) are counted per cell.
- The iteration's `decision.json` names the cases, the column, its
  direction, the runs per cell, the guards (such as `pass_rate` not down)
  and how many runs ran at once. `grade.py` reads it, compares the arms with
  the within-task permutation test of `compare.py`, and prints the verdict.
  A cell short of its runs gives `underpowered: k of n`, and the benchmark
  all the same.
- Quote a score only when `coverage_complete` in `benchmark.json` is true.
  A scored run that lacks its `answer.md`, its `trace.json`, its
  `timing.json` or the play of its plan is listed under `incomplete_runs`
  with what it lacks. A decision over such a run gives the verdict
  `incomplete`. Supply the missing part and grade again: grading reads only
  the files the runs left, so a run is never run again to be regraded.
- `trace.py --out` keeps the transcript as `transcript.jsonl` in the run
  folder, so a column can be counted again after the session's files are
  gone.
- Change the description on the failures of the train queries only, and
  choose between descriptions with the validation queries.
