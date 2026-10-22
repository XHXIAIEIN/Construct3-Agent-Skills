"""verify_change.py: the checks of a change run in order, each step that opens the editor run again only on
changed files, and the last line the one thing to do next (docs/decisions/verify-change.md). The file steps run
for real on the stand-in game; the editor steps are stood in for, since they start a browser."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from tests.skill_helpers import EVALS, PLUGIN, SHEET, SKILL, edit, tool

sys.path.insert(0, str(SKILL / "scripts"))
sys.path.insert(0, str(EVALS))
import make_fixtures  # noqa: E402
import verify_change  # noqa: E402

tracer = importlib.util.module_from_spec(spec := importlib.util.spec_from_file_location("eval_trace", EVALS / "trace.py"))
spec.loader.exec_module(tracer)

OK = "ok: 10 object types, 0 families, 2 layouts, 1 sheets"


def steps(out: str) -> dict[str, str]:
    """The state each step line of the output gives, by step."""
    return {m.group(1): m.group(2) for m in tracer.VERIFY_STEP.finditer(out)}


def test_a_failing_check_stops_before_the_review(project: Path) -> None:
    make_fixtures.seed_inverted_start(project)
    code, out = tool(project, "verify_change", "--upto", "reviewed")
    lines = out.splitlines()
    assert code == 1 and steps(out) == {"checked": "failed"}, out
    assert "on-start-of-layout is inverted" in out and "1 problem(s)" in lines[0]
    assert lines[-1].startswith("next: fix every finding above in one plan of edit_sheet.py") and \
        lines[-1].endswith("verify_change.py"), lines[-1]


def test_questions_are_answered_once_for_the_files_they_were_asked_about(project: Path) -> None:
    """The stand-in's sheet raises design questions: they stop the run until --answered records them, and a
    change to a file asks them again."""
    code, out = tool(project, "verify_change", "--upto", "reviewed")
    assert code == 1 and steps(out) == {"checked": "passed", "reviewed": "asked"}, out
    assert out.splitlines()[-1].startswith("next: answer the ") and out.splitlines()[-1].endswith(" --answered")
    code, out = tool(project, "verify_change", "--upto", "reviewed", "--answered")
    lines = out.splitlines()
    assert code == 0 and steps(out) == {"checked": "passed", "reviewed": "passed"}, out
    assert lines[0].startswith("answered: ") and "answered earlier" in out
    assert lines[-1].startswith("ok: reviewed on these files; untested: whether the editor opens it"), lines[-1]
    code, out = tool(project, "verify_change", "--status")
    assert code == 0 and steps(out) == {"checked": "passed", "reviewed": "passed", "opened": "not run",
                                        "previewed": "not run", "played": "not run", "looked": "not run"}, out
    assert out.splitlines()[-1].startswith("status: the last step that passed on these files is reviewed")
    edit(project, SHEET, lambda sheet: sheet["events"].append({"eventType": "comment", "text": "Changed."}))
    code, out = tool(project, "verify_change", "--upto", "reviewed")
    assert code == 1 and steps(out)["reviewed"] == "asked", out


class Editor:
    """Stands in for the scripts verify_change.py runs: the file steps pass, and each editor step prints what
    it is given, or passes. It counts the runs of each script."""

    def __init__(self, **given: tuple[int, str]) -> None:
        self.given, self.runs = given, {}

    def __call__(self, name: str, *extra: str) -> tuple[int, str]:
        self.runs[name] = self.runs.get(name, 0) + 1
        passing = {"check_project.py": (0, OK),
                   "review_design.py": (0, "design: 0 findings on 0 of 1 sheets; the questions name 0 events"),
                   "open_in_editor.py": (0, "opened   coins  (coins, r506)\n  preview: layout 'Game', 0 errors\n"
                                            "1 of 1 opened and ran without errors"),
                   "preview_project.py": (0, "keep: every kept plan passes"),
                   "review_look.py": (0, "look: 0 findings on 2 layouts, 0 runtime errors")}
        return self.given.get(name, passing[name])


def drive(project: Path, monkeypatch: pytest.MonkeyPatch, editor: Editor, *args: str) -> tuple[int, str]:
    monkeypatch.setattr(verify_change.Run, "script", editor)
    monkeypatch.setattr(sys, "argv", ["verify_change.py", "--project", str(project), "--rag", str(PLUGIN), *args])
    out = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: out.append(" ".join(map(str, a))))
    code = verify_change.main()
    return code, "\n".join(out)


def test_an_editor_step_that_passed_is_not_run_again_on_the_same_files(project: Path,
                                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a kept plan the play does not run and does not stop the run; the ok: line names it untested. A
    second run runs the file steps again and not the editor's."""
    editor = Editor()
    code, out = drive(project, monkeypatch, editor)
    assert code == 0 and steps(out) == {"checked": "passed", "reviewed": "passed", "opened": "passed",
                                        "previewed": "passed", "played": "not run", "looked": "passed"}, out
    assert out.splitlines()[-1].startswith("ok: looked on these files; untested: what a player does.")
    code, out = drive(project, monkeypatch, editor)
    assert code == 0 and editor.runs == {"check_project.py": 2, "review_design.py": 2, "open_in_editor.py": 1,
                                         "review_look.py": 1}, editor.runs
    assert "opened    passed: on these files, earlier" in out
    (project / "tools" / "plans").mkdir()
    (project / "tools" / "plans" / "collect.json").write_text("{}", encoding="utf-8")
    code, out = drive(project, monkeypatch, editor)
    assert code == 0 and steps(out)["played"] == "passed" and editor.runs["open_in_editor.py"] == 2, out
    assert "untested" not in out.splitlines()[-1]


def test_no_browser_hands_over_the_last_step_that_passed(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code, out = drive(project, monkeypatch, Editor(**{"open_in_editor.py": (3, "no browser here: no Edge, Chrome or "
                                                                               "Chromium was found")}))
    assert code == 3 and steps(out) == {"checked": "passed", "reviewed": "passed", "opened": "skipped"}, out
    assert out.splitlines()[-1].startswith("skipped: opened, previewed, played, looked did not run: no browser here")
    assert "Hand over as reviewed, the last step that passed on these files" in out.splitlines()[-1]


def test_a_preview_error_stops_after_the_project_opened(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code, out = drive(project, monkeypatch, Editor(**{"open_in_editor.py": (1, (
        "opened   coins  (coins, r506)\n  preview: layout 'Game', 1 error\n  runtime: Event sheet 1, event 3\n"
        "next: a runtime error names its place\n0 of 1 opened and ran without errors"))}))
    assert code == 1 and steps(out) == {"checked": "passed", "reviewed": "passed", "opened": "passed",
                                        "previewed": "failed"}, out
    assert out.splitlines()[-1].startswith("next: fix what open_in_editor.py names above, as its next: line says")


def test_look_questions_wait_for_answered(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    editor = Editor(**{"review_look.py": (0, "questions: answer every question yes or no for each screenshot\n"
                                             "  1. Is any text cut off?\nlook: 0 findings on 2 layouts, 0 runtime "
                                             "errors\nnext: hand the brief to a reviewer.")})
    code, out = drive(project, monkeypatch, editor)
    assert code == 1 and steps(out)["looked"] == "asked", out
    assert out.splitlines()[-1].startswith("next: hand the brief to a reviewer; then run") and \
        out.splitlines()[-1].endswith(" --answered"), out.splitlines()[-1]
    code, out = drive(project, monkeypatch, editor, "--answered")
    assert code == 0 and steps(out)["looked"] == "passed", out
    record = json.loads((project / ".tmp" / verify_change.RECORD).read_text(encoding="utf-8"))
    assert record["steps"]["looked"]["state"] == "passed" and record["pending"] == []


def test_trace_counts_a_verify_change_run_as_the_steps_it_printed() -> None:
    call = {"tool": "Bash", "what": "python .agents/skills/construct3-agent-plugin/scripts/verify_change.py",
            "failed": True, "result": f"checked   passed: {OK}\nreviewed  passed: design: 0 findings\n"
                                      "opened    passed: opened coins\npreviewed failed: 1 error\nnext: fix it"}
    assert tracer.chain_steps(call) == {"check_project": True, "review_design": True, "open_in_editor": False}
    assert not tracer.is_lost(call)
