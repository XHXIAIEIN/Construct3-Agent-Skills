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
    assert out.splitlines()[-1].startswith("next: have the ") and out.splitlines()[-1].endswith(" --answered")
    assert any(line.startswith("brief: ") and "review-design/brief.md" in line for line in out.splitlines()), out
    code, out = tool(project, "verify_change", "--upto", "reviewed", "--answered")
    lines = out.splitlines()
    assert code == 0 and steps(out) == {"checked": "passed", "reviewed": "passed"}, out
    assert lines[0].startswith("answered: ") and "answered earlier" in out
    assert lines[-1].startswith("ok: reviewed on these files; not run: opened, previewed, played, looked."), lines[-1]
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
                   "check_look.py": (0, "ok: 4 images, 2 world instances on a 32 px grid, 1 runtime creations"),
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
    """Without a kept plan the play does not run and does not stop the run; the ok: line names it as not run. A
    second run runs the file steps again and not the editor's. A kept plan runs the play alone."""
    editor = Editor()
    code, out = drive(project, monkeypatch, editor)
    assert code == 0 and steps(out) == {"checked": "passed", "reviewed": "passed", "opened": "passed",
                                        "previewed": "passed", "played": "not run", "looked": "passed"}, out
    assert out.splitlines()[-1].startswith("ok: looked on these files; not run: played.")
    code, out = drive(project, monkeypatch, editor)
    assert code == 0 and editor.runs == {"check_project.py": 2, "review_design.py": 2, "open_in_editor.py": 1,
                                         "check_look.py": 1, "review_look.py": 1}, editor.runs
    assert "opened    passed: on these files, earlier" in out
    (project / "tools" / "plans").mkdir()
    (project / "tools" / "plans" / "collect.json").write_text("{}", encoding="utf-8")
    code, out = drive(project, monkeypatch, editor)
    assert code == 0 and steps(out)["played"] == "passed" and editor.runs["preview_project.py"] == 1, out
    assert editor.runs["open_in_editor.py"] == 1 and editor.runs["review_look.py"] == 1, editor.runs
    assert "not run" not in out.splitlines()[-1]
    (project / "tools" / "plans" / "collect.json").write_text('{"steps": []}', encoding="utf-8")
    code, out = drive(project, monkeypatch, editor)
    assert code == 0 and editor.runs["preview_project.py"] == 2 and editor.runs["open_in_editor.py"] == 1, editor.runs


def test_no_browser_hands_over_the_last_step_that_passed(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code, out = drive(project, monkeypatch, Editor(**{"open_in_editor.py": (3, "no browser here: no Edge, Chrome or "
                                                                               "Chromium was found")}))
    assert code == 3 and steps(out) == {"checked": "passed", "reviewed": "passed", "opened": "skipped"}, out
    assert out.splitlines()[-1].startswith("skipped: opened, previewed, played, looked did not run: no browser here")
    assert "The last step that passed on these files is reviewed" in out.splitlines()[-1]


def test_a_preview_error_stops_after_the_project_opened(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code, out = drive(project, monkeypatch, Editor(**{"open_in_editor.py": (1, (
        "opened   coins  (coins, r506)\n  preview: layout 'Game', 1 error\n  runtime: Event sheet 1, event 3\n"
        "next: a runtime error names its place\n0 of 1 opened and ran without errors"))}))
    assert code == 1 and steps(out) == {"checked": "passed", "reviewed": "passed", "opened": "passed",
                                        "previewed": "failed"}, out
    assert out.splitlines()[-1].startswith("next: fix what open_in_editor.py names above, as its next: line says")


ASKS = (0, "questions: answer every question yes or no for each screenshot\n  1. Is any text cut off?\n"
           "look: 0 findings on 2 layouts, 0 runtime errors\nnext: hand the brief to a reviewer.")


class Look(Editor):
    """An editor whose review_look.py asks its questions and writes a result named for the run, as the script
    does in the project's .tmp/scripts/."""

    def __init__(self, project: Path) -> None:
        super().__init__(**{"review_look.py": ASKS})
        self.result = project / ".tmp" / "scripts" / "review-look" / "result.json"
        self.result.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, name: str, *extra: str) -> tuple[int, str]:
        if name == "review_look.py":
            self.result.write_text(json.dumps({"run": f"r{self.runs.get(name, 0) + 1}"}), encoding="utf-8")
        return super().__call__(name, *extra)

    def replied(self, **verdict) -> None:
        """--reply checked a reply against the brief of the last run."""
        result = json.loads(self.result.read_text(encoding="utf-8"))
        self.result.write_text(json.dumps({**result, "reply": {"file": "reply.md", **verdict}}), encoding="utf-8")


def test_the_look_step_passes_on_a_checked_reply_alone(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--answered records the design questions; the look questions wait for a reply that review_look.py --reply
    checked against the brief of the run that asked them, and that reply passes the step without a new review."""
    editor = Look(project)
    code, out = drive(project, monkeypatch, editor)
    assert code == 1 and steps(out)["looked"] == "asked", out
    last = out.splitlines()[-1]
    assert last.startswith("next: hand the brief to a reviewer; then run python ") and "verify_change.py" in last \
        and "--answered" not in last, last
    code, out = drive(project, monkeypatch, editor, "--answered")
    assert code == 1 and steps(out)["looked"] == "asked" and editor.runs["review_look.py"] == 2, out
    editor.replied(complete=False, yes=0)
    code, out = drive(project, monkeypatch, editor)
    assert code == 1 and steps(out)["looked"] == "asked" and editor.runs["review_look.py"] == 3, out
    # A yes is a fault to fix: the step fails and looks again, and passes with the yes left after three rounds
    for round in (1, 2):
        editor.replied(complete=True, yes=1)
        code, out = drive(project, monkeypatch, editor)
        assert code == 1 and steps(out)["looked"] == "failed", out
        assert f"looked    failed: look: reply.md has 1 yes, round {round} of 3" in out
        assert out.splitlines()[-1].startswith("next: fix each yes that review_look.py --reply printed"), out
        code, out = drive(project, monkeypatch, editor)
        assert code == 1 and steps(out)["looked"] == "asked" and editor.runs["review_look.py"] == 3 + round, out
    editor.replied(complete=True, yes=1, yeses=["Game 4, ugly - the coin: a grey box"])
    result = json.loads(editor.result.read_text(encoding="utf-8"))
    editor.result.write_text(json.dumps({**result, "preview": {"layouts": [{"layout": "Game", "findings": [
        {"rule": "optical", "tier": "fragile"}, {"rule": "text", "tier": "broken"}]}]}}), encoding="utf-8")
    code, out = drive(project, monkeypatch, editor)
    assert code == 0 and steps(out)["looked"] == "passed" and editor.runs["review_look.py"] == 5, out
    assert ("looked    passed: look: reply.md answers every question and still has 1 yes after 3 rounds: name each "
            "in the hand-over") in out
    assert "  left: Game 4, ugly - the coin: a grey box" in out
    # The ok: line names what the look left: the yes after three rounds and the fragile findings, which warn
    assert out.splitlines()[-1].split(". Hand over")[0].endswith(
        "name in the hand-over, with each fix as before, after and why: look yes Game 4, ugly - the coin: a grey "
        "box; warns Game: optical"), out
    record = json.loads((project / verify_change.RECORD).read_text(encoding="utf-8"))
    assert record["steps"]["looked"]["state"] == "passed" and record["look_rounds"] == 0


def test_the_look_step_stops_on_a_finding_of_check_look(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A generated game's look check runs before the look review, and a finding stops the step there."""
    editor = Editor(**{"check_look.py": (1, "grid.world-placement: layout Game, layer Game: Coin uid 3 is off the "
                                            "32 px grid\n1 findings: 4 images")})
    code, out = drive(project, monkeypatch, editor)
    assert code == 1 and steps(out)["looked"] == "failed" and "review_look.py" not in editor.runs, out
    assert "grid.world-placement: layout Game" in out
    assert out.splitlines()[-1].startswith("next: fix every line above in tools/build_project.py"), out


def test_a_look_whose_preview_did_not_run_is_skipped(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """review_look.py exits 3 when its preview did not run: the look step is skipped, never passed."""
    code, out = drive(project, monkeypatch, Editor(**{"review_look.py": (3, (
        "opened   coins  (coins, r506)\n  preview did not run: the preview stopped answering\nlook: no layout was "
        "looked at, as the preview of coins did not run; full result in .tmp/scripts/review-look/result.json\nnext: the preview did "
        "not run, so no layout was looked at and nothing passed; run this again"))}))
    assert code == 3 and steps(out)["looked"] == "skipped", out
    assert out.splitlines()[-1].startswith("skipped: looked did not run"), out.splitlines()[-1]


def test_a_plan_kept_after_the_look_questions_keeps_the_reply(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The run that asks the look questions also asks for a kept plan. Keeping it changes no file the game runs, so
    a reply to that run's brief still passes the step, and the play step runs the plan."""
    editor = Look(project)
    code, out = drive(project, monkeypatch, editor)
    assert code == 1 and steps(out)["played"] == "not run" and steps(out)["looked"] == "asked", out
    (project / "tools" / "plans").mkdir()
    (project / "tools" / "plans" / "collect.json").write_text("{}", encoding="utf-8")
    editor.replied(complete=True, yes=0)
    code, out = drive(project, monkeypatch, editor)
    assert code == 0 and steps(out)["played"] == "passed" and steps(out)["looked"] == "passed", out
    assert editor.runs["review_look.py"] == 1 and "looked    passed: look: reply.md answers every question no" in out


def test_trace_counts_a_verify_change_run_as_the_steps_it_printed() -> None:
    call = {"tool": "Bash", "what": "python .agents/skills/construct3-agent-plugin/scripts/verify_change.py",
            "failed": True, "result": f"checked   passed: {OK}\nreviewed  passed: design: 0 findings\n"
                                      "opened    passed: opened coins\npreviewed failed: 1 error\nnext: fix it"}
    assert tracer.chain_steps(call) == {"check_project": True, "review_design": True, "open_in_editor": False}
    assert not tracer.is_lost(call)
