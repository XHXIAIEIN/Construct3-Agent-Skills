"""verify_change.py: the checks of a change run in order, each step that opens the editor run again only on
changed files, and the last line the one thing to do next (docs/decisions/verify-change.md). The file steps run
for real on the stand-in game; the editor steps are stood in for, since they start a browser."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from tests.skill_helpers import EVALS, RAG, SHEET, SKILL, edit, tool

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
    assert out.splitlines()[-1].startswith("next: have the ") and out.splitlines()[-1].endswith(" --answered")
    assert any(line.startswith("brief: ") and "review-design/brief.md" in line for line in out.splitlines()), out
    code, out = tool(project, "verify_change", "--upto", "reviewed", "--answered")
    lines = out.splitlines()
    assert code == 0 and steps(out) == {"checked": "passed", "reviewed": "passed"}, out
    assert lines[0].startswith("answered: ") and "answered earlier" in out
    assert lines[-1].startswith("ok: reviewed on these files; not run: opened, previewed, played, screened."), lines[-1]
    code, out = tool(project, "verify_change", "--status")
    assert code == 0 and steps(out) == {"checked": "passed", "reviewed": "passed", "opened": "not run",
                                        "previewed": "not run", "played": "not run", "screened": "not run"}, out
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
                   "check_screens.py": (0, "screens: 0 findings on 2 layouts, 0 runtime errors")}
        return self.given.get(name, passing[name])


def drive(project: Path, monkeypatch: pytest.MonkeyPatch, editor: Editor, *args: str) -> tuple[int, str]:
    monkeypatch.setattr(verify_change.Run, "script", editor)
    monkeypatch.setattr(sys, "argv", ["verify_change.py", "--project", str(project), "--rag", str(RAG), *args])
    out = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: out.append(" ".join(map(str, a))))
    code = verify_change.main()
    return code, "\n".join(out)


def test_an_editor_step_that_passed_is_not_run_again_on_the_same_files(project: Path,
                                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a kept plan the play does not run and does not stop the run; the ok: line names it as not run. A
    second run runs the file steps again and not the editor's. A kept plan runs the play alone."""
    editor = Editor()
    code, out = drive(project, monkeypatch, editor)
    assert code == 0 and steps(out) == {"checked": "passed", "reviewed": "passed", "opened": "passed",
                                        "previewed": "passed", "played": "not run", "screened": "passed"}, out
    assert out.splitlines()[-1].startswith("ok: screened on these files; not run: played.")
    code, out = drive(project, monkeypatch, editor)
    assert code == 0 and editor.runs == {"check_project.py": 2, "review_design.py": 2, "open_in_editor.py": 1,
                                         "check_screens.py": 1}, editor.runs
    assert "opened    passed: on these files, earlier" in out
    (project / "tools" / "plans").mkdir()
    (project / "tools" / "plans" / "collect.json").write_text("{}", encoding="utf-8")
    code, out = drive(project, monkeypatch, editor)
    assert code == 0 and steps(out)["played"] == "passed" and editor.runs["preview_project.py"] == 1, out
    assert editor.runs["open_in_editor.py"] == 1 and editor.runs["check_screens.py"] == 1, editor.runs
    assert "not run" not in out.splitlines()[-1]
    (project / "tools" / "plans" / "collect.json").write_text('{"steps": []}', encoding="utf-8")
    code, out = drive(project, monkeypatch, editor)
    assert code == 0 and editor.runs["preview_project.py"] == 2 and editor.runs["open_in_editor.py"] == 1, editor.runs


def test_a_run_cut_off_in_the_screen_check_keeps_the_steps_that_passed(project: Path,
                                                                monkeypatch: pytest.MonkeyPatch) -> None:
    """A caller's timeout can kill the run in its longest step; the next run does not open the editor again."""
    class CutOff(Editor):
        def __call__(self, name: str, *extra: str) -> tuple[int, str]:
            if name == "check_screens.py":
                raise KeyboardInterrupt
            return editor(name, *extra)

    editor = Editor()
    with pytest.raises(KeyboardInterrupt):
        drive(project, monkeypatch, CutOff())
    code, out = drive(project, monkeypatch, editor)
    assert code == 0 and "opened    passed: on these files, earlier" in out, out
    assert editor.runs["open_in_editor.py"] == 1 and editor.runs["check_screens.py"] == 1, editor.runs


def test_no_browser_hands_over_the_last_step_that_passed(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code, out = drive(project, monkeypatch, Editor(**{"open_in_editor.py": (3, "no browser here: no Edge, Chrome or "
                                                                               "Chromium was found")}))
    assert code == 3 and steps(out) == {"checked": "passed", "reviewed": "passed", "opened": "skipped"}, out
    assert out.splitlines()[-1].startswith("skipped: opened, previewed, played, screened did not run: no browser here")
    assert "The last step that passed on these files is reviewed" in out.splitlines()[-1]


def test_a_preview_error_stops_after_the_project_opened(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code, out = drive(project, monkeypatch, Editor(**{"open_in_editor.py": (1, (
        "opened   coins  (coins, r506)\n  preview: layout 'Game', 1 error\n  runtime: Event sheet 1, event 3\n"
        "next: a runtime error names its place\n0 of 1 opened and ran without errors"))}))
    assert code == 1 and steps(out) == {"checked": "passed", "reviewed": "passed", "opened": "passed",
                                        "previewed": "failed"}, out
    assert out.splitlines()[-1].startswith("next: fix what open_in_editor.py names above, as its next: line says")


def test_the_editor_steps_share_one_browser_closed_as_the_run_ends(project: Path,
                                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    """The scripts run with SHARED naming the project, so each leaves the browser and the open project to the
    next; the run closes that browser as it ends, also when a step stops it."""
    seen, closed = {}, []
    init = verify_change.Run.__init__

    def spy(self, *a) -> None:
        init(self, *a)
        seen.update(self.env)
    monkeypatch.setattr(verify_change.Run, "__init__", spy)
    monkeypatch.setattr(verify_change.oe, "browser_path", lambda: "msedge.exe")
    monkeypatch.setattr(verify_change.oe, "close_shared", lambda exe, profile: closed.append((exe, profile)))
    code, out = drive(project, monkeypatch, Editor(**{"check_screens.py": (1, "screens: 1 finding to fix")}))
    assert code == 1 and steps(out)["screened"] == "failed", out
    assert Path(seen[verify_change.oe.SHARED]).resolve() == project.resolve()
    assert [exe for exe, _ in closed] == ["msedge.exe"] and closed[0][1].name == "editor-msedge"


def test_a_screen_check_whose_preview_did_not_run_is_skipped(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """check_screens.py exits 3 when its preview did not run: the step is skipped, never passed."""
    code, out = drive(project, monkeypatch, Editor(**{"check_screens.py": (3, (
        "opened   coins  (coins, r506)\n  preview did not run: the preview stopped answering\nscreens: no layout was "
        "visited, as the preview of coins did not run; full result in .tmp/scripts/check-screens/result.json\nnext: the preview did "
        "not run, so no layout was visited and nothing passed; run this again"))}))
    assert code == 3 and steps(out)["screened"] == "skipped", out
    assert out.splitlines()[-1].startswith("skipped: screened did not run"), out.splitlines()[-1]


def test_a_finding_of_the_screen_check_fails_the_step(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A finding of check_screens.py stops the run, and a run that finds nothing passes the step."""
    code, out = drive(project, monkeypatch, Editor(**{"check_screens.py": (1, (
        "layout 'Game' (1 of 1): screenshot Game.png\n  text: Title uid 1: the text needs 200x40 px and its box is "
        "100x40\nscreens: 1 finding to fix on 1 layout, 0 runtime errors\nnext: fix every finding"))}))
    assert code == 1 and steps(out)["screened"] == "failed", out
    assert "text: Title uid 1" in out and out.splitlines()[-1].startswith("next: fix every finding above, then run")
    code, out = drive(project, monkeypatch, Editor())
    assert code == 0 and steps(out)["screened"] == "passed", out


def test_a_warning_of_the_screen_check_goes_in_the_hand_over(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = project / verify_change.SCREENS_RESULT
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text(json.dumps({"preview": {"layouts": [{"layout": "Game", "findings": [
        {"rule": "unlimited", "warn": True}, {"rule": "text"}]}]}}), encoding="utf-8")
    code, out = drive(project, monkeypatch, Editor())
    assert code == 0, out
    assert "name in the hand-over, these warn: Game: unlimited." in out.splitlines()[-1], out


def test_trace_counts_a_verify_change_run_as_the_steps_it_printed() -> None:
    call = {"tool": "Bash", "what": "python .agents/skills/construct3-agent-plugin/scripts/verify_change.py",
            "failed": True, "result": f"checked   passed: {OK}\nreviewed  passed: design: 0 findings\n"
                                      "opened    passed: opened coins\npreviewed failed: 1 error\nnext: fix it"}
    assert tracer.chain_steps(call) == {"check_project": True, "review_design": True, "open_in_editor": False}
    assert not tracer.is_lost(call)
    assert tracer.chain_steps({**call, "result": "looked    passed: look: 0 findings on 1 layout, 0 runtime errors"}) == {
        "check_screens": True}, "a run of the older skill prints the step as looked"
    old = {"tool": "Bash", "what": "python scripts/review_look.py", "failed": False,
           "result": "look: 0 findings on 1 layout, 0 runtime errors"}
    assert tracer.chain_steps(old) == {"check_screens": True}, "and runs the check as review_look.py"
