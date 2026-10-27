# Editor refused a project the checker passed: `+` between text and a number

Reproduced. `check_project.py` passes the version with `+`, and the editor refuses it with your message. The `&` version opens in the editor. I did not change your project; the tests ran on copies.

## Why the checker passed it

- `references/checker-rules.md`, section "What it does not see", says the checker does not judge expression types beyond the local-variable shadowing cases. The editor does. So the `ok:` line is correct for what the checker reads, and it does not cover this error.
- `SKILL.md` says a project the checker passes "is opened once before it is handed over", and `open_in_editor.py` is the step that does that. I cannot tell whether the earlier session ran it: [unknown].
- The `ok:` line does not say that expression types were not checked. Read alone, it sounds like a full pass. That wording is the part to change.
- `&` joins text with a number. The editor accepts that; `+` between text and a number is the error.

## Suggested changes for the maintainers

1. The `ok:` line of `check_project.py` says expression types are checked only by the editor, and names `open_in_editor.py` as the next step. This is a small change.
2. A checker rule for `+` with a text literal on one side and a number expression (such as `.IID` or a numeric ACE) on the other. This needs the checker to know the type of an expression, which it does not do today. I have not checked how much of the expression grammar that would take: [unknown].

## Report for the issue

```
env:   r506.3 editor | Edge (headless) | Windows 11 | Claude Code, claude-haiku-5-5 | skill [unknown], Construct3-RAG b3124e7
task:  a coin game with two enemy objects, each setting a label at layout start
ran:   check_project.py ok (version with +); open_in_editor.py failed (version with +), opened (version with &)

[unknown][project] Invalid expressions In some circumstances, previous versions of Construct allow invalid expressions to be used. These expressions must be corrected the prior version before using the project in this version of Construct 3. A list of the invalid expressions is provided below. Main, event 13, action 1: Type mismatch: + does not work with 'string' and 'number' Main, event 13, action 2: Type mismatch: + does not work with 'string' and 'number'
  cause: the expression "text " + Enemy.IID adds text to a number, and the editor rejects + for that pair. check_project.py reads no expression types, so it passes this.
  fix:   eventSheets/Main.json: both expressions "text " + ... changed to "text " & ...
  catch: open_in_editor.py catches it; check_project.py does not

state: works with &; open: the + version
gaps:  [unknown] round and project version history; whether an earlier session ran open_in_editor.py
```

Replaced: the sheet name `Game` is now `Main`, the objects `Goblin` and `Orc` are now `Enemy` and `Enemy2`, the label words are now generic text in quotes, and the project title is left out. The editor message and the `IID` names are verbatim. Read the report before you file it.

## Changes

None to your project. Two copies sit in the outputs folder, `repro-plus` (the `+` version, which the editor refused) and `check-amp` (the `&` version, which opened). The editor script wrote its own report to `repro-plus\.tmp\editor-report-9481904ae9d5.md`. It also printed a `gh issue create` command; I did not run it, and nothing was sent.

## Commands run

Run from `<run>\project` unless a path is given.

- `python .agents\skills\construct3-agent-plugin\scripts\check_project.py`: `ok:` line
- `python .agents\skills\construct3-agent-plugin\scripts\print_sheet.py Game --events 13`: event 13 with `&`
- PowerShell `Get-ChildItem` / `Measure-Object` on the project, `Select-String` on `eventSheets\Game.json` and the skill's references and scripts
- PowerShell `Get-Content` on `references\checker-rules.md` lines 420-440 and the head of `scripts\open_in_editor.py`
- `Copy-Item` of the project to `outputs\repro-plus`, then a text replace of `&` with `+` in its `eventSheets\Game.json` (a `Remove-Item` with a variable target was blocked by the `rm_target_guard` hook; it did not run)
- `python ...\check_project.py --project <run>\outputs\repro-plus`: `ok:` line
- `python ...\print_sheet.py Game --events 13 --project ...\outputs\repro-plus`: event 13 with `+`
- `python ...\open_in_editor.py --project ...\outputs\repro-plus`: `failed`, with the editor message
- `Copy-Item` of the project to `outputs\check-amp`
- `python ...\open_in_editor.py --project ...\outputs\check-amp`: `opened`
