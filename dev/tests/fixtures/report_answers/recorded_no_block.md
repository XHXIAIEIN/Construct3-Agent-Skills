Summary: check_project.py passed a Coins project that the Construct 3 editor refuses. Cause: the checker's expression model treats `+` between a text and a number as concatenation, and the checker has no argument-type rule. The editor enforces the rule. Your fix (`&`) is correct, and the project now opens in the editor (verified).

Findings

1. The checker accepts the `+` form. A copy of the project with the two `+` lines passes check_project.py ("ok:", exit 0).
2. The editor refuses that copy. open_in_editor.py reports: "Game, event 13, action 1: Type mismatch: + does not work with 'string' and 'number'" and the same for action 2 (exit 1).
3. The current project, with `&`, opens: open_in_editor.py prints "opened ... (Coins - Construct 3)" (exit 0).
4. Why the checker misses it: scripts/game_model.py, the `+` operator (around lines 1377-1379), returns `show_plain(a) + show_plain(b)` whenever either operand is text. So the checker's own evaluator treats the invalid expression as valid. The `&` branch is around lines 1392-1400.
5. The checker documents the gap but the wording overstates coverage. references/checker-rules.md, section "What it does not see", says argument types are not checked and the editor judges them. But SKILL.md describes check_project.py as checking "the editor's load rules", and the `ok:` line implies the project will open.
6. Step 5 of the workflow is the step that would have caught this. verify_change.py runs open_in_editor.py after the checker. I do not know whether the session that wrote event 13 ran verify_change.py or only check_project.py.

Suggested fixes for the maintainers
- Make `+` with a text operand a checker error, with the editor's message text, since the editor's text is the reference. Alternatively, treat `+` on text as an error in game_model.py, the way the editor does.
- Narrow the SKILL.md wording of check_project.py to what it checks, and say that the editor step is required before a hand-over.

Reproduction (for the issue)
1. Event sheet Game, event 13: System, On start of layout, with `Goblin: Set label to "goblin " + Goblin.IID` and `Orc: Set label to "orc " + Orc.IID`.
2. Run check_project.py: prints `ok:`, exit 0.
3. Run open_in_editor.py: prints `failed`, with the two Type mismatch messages.
4. Replace `+` with `&`, run open_in_editor.py: `opened`.

Environment (from the editor report the skill wrote): editor r506.3, project saved with r495.2, Construct3-RAG 86a8a7f.

Files
- Current project (unchanged by me, opens in the editor): <run>\project\eventSheets\Game.json
- Repro copy with `+`, made inside the project: <run>\project\.tmp\repro-plus. Delete it when you no longer need it.
- Editor report the script wrote for the repro (not sent): <run>\project\.tmp\repro-plus\.tmp\editor-report-9481904ae9d5.md. Nothing was sent to GitHub.
- Command log: <run>\outputs\commands.txt

Notes on the output request
- I did not write answer.md. The agent rules I run under forbid writing report files; this report is my final return. The command log is saved as commands.txt in the outputs folder.
- I did not run verify_change.py, because the task was a diagnosis, not a change to the project.

Commands run
- python <run>/project/.agents/skills/construct3-agent-plugin/scripts/check_project.py --project <run>/project
- python ...scripts/print_sheet.py Game --project ...\project --events 13-13
- Select-String over the skill's scripts and references for type-mismatch and `+` rules; read checker-rules.md, open_in_editor.py, game_model.py
- Copied the project to .tmp\repro-plus, changed the two `&` to `+` in eventSheets/Game.json
- python .tmp/repro-plus/.agents/skills/construct3-agent-plugin/scripts/check_project.py --project .tmp/repro-plus (ok, exit 0)
- python .tmp/repro-plus/.agents/skills/construct3-agent-plugin/scripts/open_in_editor.py --project .tmp/repro-plus (failed, exit 1)
- python ...scripts/open_in_editor.py --project ...\project (opened, exit 0)