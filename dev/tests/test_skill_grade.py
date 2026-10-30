"""evals/grade.py and the eval scripts beside it on runs of the skill's cases: what grading.json, benchmark.json
and trace.json say about a run.

The answers in fixtures/restart_event_answers/ are answer.md files of name-the-restart-event runs, with their run
folder replaced by <run>. Each of those runs has an empty project and an empty fixture.json, so the third assertion
passes throughout. An add-countdown run is the stand-in game with the events it wrote.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.skill_helpers import EVALS, NEEDS_EXAMPLES, NEEDS_GIT, SKILL, SHEET, game_rows, install, new_project, run

sys.path.insert(0, str(EVALS))
sys.path.insert(0, str(SKILL / "scripts"))
import grade as grader  # noqa: E402
import make_fixtures  # noqa: E402
import play_cases  # noqa: E402
import preview_project  # noqa: E402
import compare  # noqa: E402

# evals/trace.py by its path: the standard library has a module named trace.
tracer = importlib.util.module_from_spec(spec := importlib.util.spec_from_file_location("eval_trace", EVALS / "trace.py"))
spec.loader.exec_module(tracer)

ANSWERS = Path(__file__).parent / "fixtures" / "restart_event_answers"
CHINESE_ALL_THREE = "**事件 10**（Restart 组）：Coin.Count = 0，仅触发一次。触发后等待 1 秒，再重载场景。\n"
CASES = {c["name"]: c for c in json.loads((EVALS / "evals.json").read_text(encoding="utf-8"))["evals"]}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def answer_case(case: Path, answer: str) -> None:
    """A name-the-restart-event run at case: answer as its answer.md, an empty project and an empty fixture.json."""
    (case / "project").mkdir(parents=True)
    (case / "outputs").mkdir()
    (case / "fixture.json").write_text("{}", encoding="utf-8")
    (case / "outputs" / "answer.md").write_text(answer, encoding="utf-8")


def project_case(tmp_path: Path, project: Path, name: str) -> Path:
    """The with_skill run of case name in the iteration tmp_path/it: a copy of project and an empty fixture.json."""
    case = tmp_path / "it" / name / "with_skill"
    shutil.copytree(project, case / "project")
    (case / "fixture.json").write_text("{}", encoding="utf-8")
    return case


def grade_iteration(tmp_path: Path) -> str:
    """What grade.py prints on the iteration tmp_path/it, which it grades without an error."""
    code, out = run(tmp_path, EVALS / "grade.py", str(tmp_path / "it"))
    assert code == 0, out
    return out


def grade(tmp_path: Path, answer: str) -> list[bool]:
    case = tmp_path / "it" / "name-the-restart-event" / "with_skill"
    answer_case(case, answer)
    grade_iteration(tmp_path)
    return [g["passed"] for g in read_json(case / "grading.json")["assertion_results"]]


@pytest.mark.parametrize(("name", "passed"), [
    ("english_all_three.md", [True, True, True]),
    # "Setup (event 2) runs again" names another event after the answer, 9
    ("english_names_setup_as_context.md", [True, True, True]),
    # "事件 8" is the Restart group's row; "仅触发一次" and "等待 1 秒" are the zh-CN wording
    ("chinese_gives_the_group_number.md", [False, True, True]),
    ("english_without_the_wait.md", [True, False, True]),
])
def test_restart_event_answers(tmp_path: Path, name: str, passed: list[bool]) -> None:
    assert grade(tmp_path, (ANSWERS / name).read_text(encoding="utf-8")) == passed


def test_chinese_answer_with_all_three(tmp_path: Path) -> None:
    assert grade(tmp_path, CHINESE_ALL_THREE) == [True, True, True]


def test_group_number_first_fails(tmp_path: Path) -> None:
    assert grade(tmp_path, "Event 9 restarts it: Coin.Count = 0, Trigger once, then a 1 second wait. "
                           "Event 10 is inside it.\n")[0] is False


def add_countdown(project: Path, first_on_start: dict, setup_events: list[dict]) -> None:
    """The stand-in's sheet with a global Countdown from 30, first_on_start as the first action of On start of
    layout, and setup_events at the end of the Setup group."""
    path = project / SHEET
    sheet = read_json(path)
    sheet["events"].insert(0, {"eventType": "variable", "name": "Countdown", "type": "number", "initialValue": "30",
                               "comment": "", "isStatic": False, "isConstant": False, "sid": 767136845493875})
    setup = next(g for g in game_rows(sheet) if g.get("title") == "Setup")
    start = next(ev for ev in setup["children"] if any(c["id"] == "on-start-of-layout" for c in ev.get("conditions", [])))
    start["actions"].insert(0, first_on_start)
    setup["children"] += setup_events
    path.write_text(json.dumps(sheet, indent="\t"), encoding="utf-8")


@pytest.mark.parametrize(("kind", "counts"), [("regular", True), ("once", False)])
def test_a_countdown_on_a_one_second_timer_loses_one_per_second(tmp_path: Path, project: Path, kind: str,
                                                                counts: bool) -> None:
    """The add-countdown run of 2026-10-06 (with_q35_lean_2) started ScoreText's Timer "tick" for 1 second, Regular,
    under On start of layout, and took 1 from Countdown under On timer "tick". A Once timer fires a single time."""
    add_countdown(project, {"id": "start-timer", "objectClass": "ScoreText", "sid": 101, "behaviorType": "Timer",
                            "parameters": {"duration": "1", "type": kind, "tag": '"tick"'}}, [
        {"eventType": "block", "sid": 102, "conditions": [
            {"id": "on-timer", "objectClass": "ScoreText", "sid": 103, "behaviorType": "Timer", "parameters": {"tag": '"tick"'}}],
         "actions": [{"id": "set-eventvar-value", "objectClass": "System", "sid": 104,
                      "parameters": {"variable": "Countdown", "value": "Countdown - 1"}}]}])
    case = project_case(tmp_path, project, "add-countdown")
    grade_iteration(tmp_path)
    graded = read_json(case / "grading.json")["assertion_results"]
    result = next(g for g in graded if g["text"].startswith("The countdown loses one per second"))
    assert result["passed"] is counts, result
    assert 'on-timer("tick") -> set-eventvar-value(Countdown | Countdown - 1)' in result["evidence"]


@pytest.mark.parametrize(("comparison", "value", "inverted", "restarts"), [
    (3, "0", False, True),      # Countdown <= 0
    (2, "0", False, True),      # Countdown < 0, which a countdown losing dt passes
    (4, "0", False, False),     # Countdown > 0: holds from the start (the audit of 2026-10-07)
    (4, "0", True, True),       # not Countdown > 0
    (5, "30", False, False),    # Countdown >= 30
])
def test_the_restart_reads_the_countdown_running_out(tmp_path: Path, project: Path, comparison: int, value: str,
                                                     inverted: bool, restarts: bool) -> None:
    """A countdown from 30 that loses dt every tick, set back on start of layout and shown in ScoreText, restarts
    the layout under a comparison of the countdown: it passes only when the comparison holds at 0 and not at 30."""
    restart = {"id": "compare-eventvar", "objectClass": "System", "sid": 105,
               "parameters": {"variable": "Countdown", "comparison": comparison, "value": value}}
    if inverted:
        restart["isInverted"] = True
    add_countdown(project, {"id": "set-eventvar-value", "objectClass": "System", "sid": 101,
                            "parameters": {"variable": "Countdown", "value": "30"}}, [
        {"eventType": "block", "sid": 102, "conditions": [{"id": "every-tick", "objectClass": "System", "sid": 103}],
         "actions": [{"id": "subtract-from-eventvar", "objectClass": "System", "sid": 104,
                      "parameters": {"variable": "Countdown", "value": "dt"}}]},
        {"eventType": "block", "sid": 106, "conditions": [restart],
         "actions": [{"id": "restart-layout", "objectClass": "System", "sid": 107}]}])
    case = project_case(tmp_path, project, "add-countdown")
    grade_iteration(tmp_path)
    graded = read_json(case / "grading.json")["assertion_results"]
    result = next(g for g in graded if g["text"].startswith("An event restarts the layout"))
    assert result["passed"] is restarts, result


def test_an_old_arm_is_not_failed_on_its_older_block(tmp_path: Path, project: Path) -> None:
    """An old_ arm installed the older skill, whose Construct 3 block the current checker warns about: grade.py leaves
    that warning out of an old_ run's checker output and keeps it in a with_skill run's."""
    from tests.test_skill_install import older_block
    outs = {}
    for arm in ("old_skill_2", "with_skill"):
        root = tmp_path / arm / "project"
        shutil.copytree(project, root)
        older_block(root)
        outs[arm] = grader.checker(root)
    code, out = outs["with_skill"]
    assert code == 0 and grader.STALE_BLOCK.search(out), out
    assert [line for line in out.splitlines() if line.startswith("warning:")] == [grader.STALE_BLOCK.search(out)[0].strip()]
    code, out = outs["old_skill_2"]
    assert code == 0 and "warning:" not in out and out.splitlines()[-1].startswith("ok: "), out


def test_a_function_call_on_start_is_graded_with_the_countdown(tmp_path: Path, project: Path) -> None:
    """A call of a function lists its arguments, not named parameters: iteration 65's add-countdown/with_skill
    called ShowScore under On start of layout, and the grader stopped on the list."""
    add_countdown(project, {"callFunction": "ShowScore", "sid": 101, "parameters": []}, [])
    case = project_case(tmp_path, project, "add-countdown")
    grade_iteration(tmp_path)
    graded = read_json(case / "grading.json")["assertion_results"]
    assert any(g["text"].startswith("An event restarts the layout") for g in graded), graded


def test_a_run_that_wrote_outside_its_folder_is_not_scored(tmp_path: Path) -> None:
    """Its grade would count work that is not in its project, or that another run reads."""
    case = tmp_path / "it" / "name-the-restart-event" / "with_skill"
    answer_case(case, CHINESE_ALL_THREE)
    elsewhere = str(tmp_path / "scratchpad" / "plan.json")
    (case / "trace.json").write_text(json.dumps({"tool_calls": 3, "lost_calls": 0, "outside": [
        {"tool": "Write", "path": elsewhere}], "outside_reads": []}), encoding="utf-8")
    out = grade_iteration(tmp_path)
    assert f"name-the-restart-event/with_skill: void, not scored: it wrote outside its folder: {elsewhere}" in out
    assert read_json(case / "grading.json") == {"void": f"it wrote outside its folder: {elsewhere}"}
    benchmark = read_json(tmp_path / "it" / "benchmark.json")
    assert benchmark["void_runs"] == [{"run": "name-the-restart-event/with_skill",
                                       "reason": f"it wrote outside its folder: {elsewhere}"}]


@pytest.mark.parametrize(("read", "void"), [
    ("{it}/clone-0123456789ab/dev/evals/evals.json", True),
    ("/x/rag-old/dev/tests/fixtures/find_answers/big_sheet_compares_other_waves.md", True),
    ("{it}/name-the-restart-event/with_skill_2/outputs/answer.md", True),
    ("{it}/clone-0123456789ab/plugin/data/c3-schemas/_index.json", False),
    ("{it}/name-the-restart-event/with_skill/project/eventSheets/Game.json", False),
    ("{it}/name-the-restart-event/with_skill-1/outputs/answer.md", False),   # its own folder, misspelt
])
def test_a_run_that_read_how_it_is_graded_is_not_scored(tmp_path: Path, read: str, void: bool) -> None:
    """The cases, the plans and the graders, or another run's answer, let a run pass without doing the task."""
    case = tmp_path / "it" / "name-the-restart-event" / "with_skill"
    answer_case(case, CHINESE_ALL_THREE)
    answer_case(case.with_name("with_skill_2"), CHINESE_ALL_THREE)
    path = read.format(it=(tmp_path / "it").as_posix())
    (case / "trace.json").write_text(json.dumps({"tool_calls": 3, "lost_calls": 0, "outside": [], "outside_reads": [
        {"tool": "Read", "path": path}]}), encoding="utf-8")
    out = grade_iteration(tmp_path)
    assert (f"void, not scored: it read how it is graded: {path}" in out) is void, out
    assert ("void" in read_json(case / "grading.json")) is void


@pytest.mark.parametrize("name", sorted(play_cases.PLANS))
def test_every_plan_is_one_preview_project_plays(name: str) -> None:
    """A plan preview_project.py refuses would fail every run of its case; a check's text names its assertion."""
    assert name in CASES
    plan, problems = preview_project.check_plan(play_cases.plan_for(name))
    assert not problems, problems
    texts = play_cases.check_texts(name)
    assert len(texts) == len(set(texts)) >= 2 and texts[-1] == play_cases.NO_ERROR


def test_held_out_cases_have_a_plan() -> None:
    """A held-out case is judged by what its game does; its file assertions only say that it still opens."""
    held = [n for n, c in CASES.items() if c.get("held_out")]
    assert held and all(n in play_cases.PLANS for n in held)


@pytest.mark.parametrize(("test", "passed"), [
    ('keyboard.isKeyDown("Shift")', False),
    ('keyboard.isKeyDown("ShiftLeft") || keyboard.isKeyDown("ShiftRight")', True),
    ("keyboard.isKeyDown(16)", True)])
def test_a_shift_key_counts_only_by_a_code_iskeydown_matches(tmp_path: Path, test: str, passed: bool) -> None:
    """isKeyDown matches a key's code: a run that tests "Shift" never doubles its speed in the game."""
    (tmp_path / "project" / "scripts").mkdir(parents=True)
    (tmp_path / "fixture.json").write_text("{}", encoding="utf-8")
    (tmp_path / "project" / "scripts" / "main.ts").write_text(f"const speed = {test} ? 400 : 200;", encoding="utf-8")
    assert grader.grade_script_shift_and_edges(tmp_path)[1][0] is passed


def played(case: Path, oks: list[bool]) -> None:
    """A play/result.json in which the plan's checks returned oks in order, as preview_project.py writes it."""
    plan = play_cases.plan_for(case.parent.name)
    steps, verdicts = [], iter(oks)
    for n, step in enumerate(plan["steps"], 1):
        done = {"step": n, "line": f"{n} {next(iter(step))} ...", "ok": True, "said": "", "errors": []}
        if step.get("note", "").startswith(play_cases.CHECK):
            done["value"] = {"ok": next(verdicts), "said": f"check {n}"}
        steps.append(done)
    (case / "play").mkdir()
    (case / "play" / "result.json").write_text(json.dumps({"status": "opened", "preview": {
        "started": True, "errors": [], "steps": steps}}), encoding="utf-8")


def test_runtime_checks_are_graded_from_the_played_result(tmp_path: Path, project: Path) -> None:
    case = project_case(tmp_path, project, "fix-next-round")
    played(case, [True, False])
    out = grade_iteration(tmp_path)
    grading = read_json(case / "grading.json")
    runtime = [(g["passed"], g["evidence"]) for g in grading["assertion_results"] if g["level"] == "runtime"]
    checks = [n for n, s in enumerate(play_cases.plan_for("fix-next-round")["steps"], 1)
              if s.get("note", "").startswith(play_cases.CHECK)]
    assert runtime == [(True, f"check {checks[0]}"), (False, f"check {checks[1]}"), (True, "no runtime error")]
    assert grading["summary"]["runtime"] == {"passed": 2, "total": 3}
    assert "FAIL [runtime] The next round deals 3 coins" in out


def test_an_unplayed_plan_is_not_scored(tmp_path: Path, project: Path) -> None:
    """Grading without --play compares with iterations graded before the plans: the runtime checks are listed
    and left out of the scores."""
    case = project_case(tmp_path, project, "fix-next-round")
    grade_iteration(tmp_path)
    grading = read_json(case / "grading.json")
    assert grading["summary"]["runtime"] == "not played"
    assert grading["summary"]["total"] == len(CASES["fix-next-round"]["assertions"])
    assert {g["passed"] for g in grading["assertion_results"] if g["level"] == "runtime"} == {None}


def test_a_held_out_case_is_aggregated_apart_and_its_failures_are_not_printed(tmp_path: Path, project: Path) -> None:
    case = project_case(tmp_path, project, "coins-in-a-ring")
    played(case, [False, False, True])
    out = grade_iteration(tmp_path)
    assert "coins-in-a-ring/with_skill: held out, " in out and "FAIL" not in out
    benchmark = read_json(tmp_path / "it" / "benchmark.json")
    assert "coins-in-a-ring" not in benchmark["by_case"] and "coins-in-a-ring" in benchmark["held_out"]["by_case"]
    code, out = run(tmp_path, EVALS / "grade.py", str(tmp_path / "it"), "--show-held-out")
    assert "FAIL [runtime] Round 2's three coins sit evenly" in out


def test_make_fixtures_lays_out_a_held_out_case_only_when_asked(tmp_path: Path) -> None:
    code, out = run(tmp_path, EVALS / "make_fixtures.py", str(tmp_path / "runs"), "--cases", "coins-in-a-ring")
    assert code == 1 and "held out of tuning" in out and "--held-out" in out


def test_make_fixtures_finds_the_old_installer_under_plugin(tmp_path: Path) -> None:
    # This checkout stands in for the old one: its installer is found, so the next check, the case name, fails.
    code, out = run(tmp_path, EVALS / "make_fixtures.py", str(tmp_path / "runs"), "--arms", "old_skill",
                    "--old-clone", str(EVALS.parents[1]), "--cases", "no-such-case")
    assert code == 1 and "no test case named no-such-case" in out
    code, out = run(tmp_path, EVALS / "make_fixtures.py", str(tmp_path / "runs"), "--arms", "old_skill",
                    "--old-clone", str(tmp_path))
    assert code == 1 and "plugin/skills/construct3-agent-plugin/scripts/install.py" in out


@NEEDS_GIT
def test_make_fixtures_pins_the_with_arm_to_a_worktree_of_the_commit(tmp_path: Path) -> None:
    """The with_skill fixture is installed from a detached worktree of HEAD in the runs folder and names its commit;
    the without_skill fixture installed nothing and names none. The worktree holds no dev/, where the cases and
    their graders are, and no file of it reads as changed."""
    repo, runs = EVALS.parents[1], tmp_path / "runs"
    sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                         check=True).stdout.strip()
    folder = runs / f"clone-{sha[:12]}"
    try:
        code, out = run(tmp_path, EVALS / "make_fixtures.py", str(runs), "--cases", "name-the-restart-event",
                        "--arms", "with_skill", "without_skill")
        assert code == 0, out
        assert read_json(runs / "clone.json") == {"commit": sha, "folder": folder.resolve().as_posix(), "old_clone": None}
        case = runs / "name-the-restart-event"
        assert read_json(case / "with_skill" / "fixture.json")["clone.commit"] == sha
        assert "clone.commit" not in read_json(case / "without_skill" / "fixture.json")
        block = (case / "with_skill" / "project" / "AGENTS.md").read_text(encoding="utf-8")
        assert f"- Construct3-RAG: {(folder / 'plugin').resolve().as_posix()}" in block, block
        assert not (folder / "dev").exists() and (folder / "plugin" / "skills").is_dir() and (folder / "docs").is_dir()
        assert not subprocess.run(["git", "-C", str(folder), "status", "--porcelain", "--untracked-files=no"],
                                  capture_output=True, text=True, check=True).stdout.strip()
    finally:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(folder)], capture_output=True)


def test_sweep_outputs_runs_the_skill_scripts_of_this_checkout_by_default(tmp_path: Path) -> None:
    # Past the check of the scripts folder, the sweep stops at the empty project list.
    code, out = run(tmp_path, EVALS / "sweep_outputs.py", str(tmp_path / "out.json"), "--projects", str(tmp_path))
    assert code == 2 and "no folder with a project.c3proj" in out
    code, out = run(tmp_path, EVALS / "sweep_outputs.py", str(tmp_path / "out.json"), "--projects", str(tmp_path),
                    "--scripts", str(EVALS))
    assert code == 2 and "is not plugin/skills/<skill>/scripts of a checkout of the clone" in out


@pytest.mark.parametrize(("k", "n", "interval"), [(0, 0, [0.0, 1.0]), (2, 2, [0.342, 1.0]), (1, 2, [0.095, 0.905]),
                                                  (8, 10, [0.49, 0.943])])
def test_the_interval_of_fully_passed_runs(k: int, n: int, interval: list[float]) -> None:
    assert grader.wilson(k, n) == interval


@pytest.mark.parametrize(("levels", "reached"), [
    ({"checker": [True], "files": [True], "runtime": [True]}, "runtime"),
    ({"checker": [True], "files": [True], "runtime": [None]}, "files"),
    ({"checker": [True], "files": [False], "runtime": [True]}, "checker"),
    ({"checker": [False], "files": [True]}, "none"),
])
def test_the_level_a_run_reached(levels: dict, reached: str) -> None:
    graded = [{"level": level, "passed": p} for level, ps in levels.items() for p in ps]
    assert grader.reached(graded) == reached


def test_trace_reads_turns_tokens_and_time(tmp_path: Path) -> None:
    """A response with two content blocks is written twice with one message id: one turn."""
    def entry(t: str, mid: str | None, out: int) -> str:
        message = {"id": mid, "model": "m", "usage": {"input_tokens": 2, "cache_creation_input_tokens": 10,
                                                       "cache_read_input_tokens": 100, "output_tokens": out}}
        return json.dumps({"type": "assistant" if mid else "user", "timestamp": t, "message": message if mid else {}})
    path = tmp_path / "agent.jsonl"
    path.write_text("\n".join([entry("2026-10-08T10:00:00Z", None, 0), entry("2026-10-08T10:00:05Z", "a", 50),
                               entry("2026-10-08T10:00:05Z", "a", 50), entry("2026-10-08T10:01:30Z", "b", 70)]),
                    encoding="utf-8")
    assert tracer.usage_of(path) == {"turns": 2, "output_tokens": 120, "input_tokens": 224, "seconds": 90.0, "model": "m"}


@pytest.mark.parametrize("command", [
    "sed -i '/^function Tick/,/^}/ s/^\\r$//' /d/run/main.ts",
    "sed -i -e '/^}/d' /d/run/main.ts",
    "sed -n '/^x/p' /d/run/main.ts > /d/run/out.txt"])
def test_trace_takes_a_sed_script_for_no_path(command: str) -> None:
    """A sed script can start with /, and Git Bash's /d is D:; only the file the command names is written."""
    writes, named = tracer.shell_paths(command)
    files = [Path(p).name for p in writes + named]
    assert files == (["out.txt", "main.ts"] if ">" in command else ["main.ts"]), (writes, named)


def screenshots(tmp_path: Path, fill: Callable[[int, float], tuple], lit: tuple[float, float]) -> dict:
    """A result with before and after screenshots of a 400 px bar lit to lit[0] and then lit[1] of its length,
    its pixel at x coloured fill(x, lit), and the bar's box as the UI layer's only object."""
    from PIL import Image
    shots = []
    for name, part in zip(("before", "after"), lit):
        im = Image.new("RGB", (500, 100), (2, 48, 71))
        for x in range(50, 50 + int(400 * part)):
            im.paste(fill(x - 50, part), (x, 40, x + 1, 60))
        im.save(tmp_path / f"{name}.png")
        shots.append(tmp_path / f"{name}.png")
    box = [{"type": "Bar", "text": False, "box": {"l": 50, "t": 40, "r": 450, "b": 60}}]
    steps = [{"step": 1, "line": "1 js ... (boxes before)", "ok": True, "value": box},
             {"step": 2, "line": "2 shot before", "ok": True, "said": str(shots[0])},
             {"step": 3, "line": "3 shot after", "ok": True, "said": str(shots[1])},
             {"step": 4, "line": "4 js ... (boxes after)", "ok": True, "value": box}]
    return {"status": "opened", "preview": {"started": True, "errors": [], "steps": steps}}


def green_to_red(x: int, part: float) -> tuple:
    u = x / 400
    return round(255 * u), round(255 * (1 - u)), 0


def stretched(x: int, part: float) -> tuple:
    u = x / (400 * part)
    return round(255 * u), round(255 * (1 - u)), 0


@pytest.mark.parametrize(("fill", "kept"), [(green_to_red, True), (stretched, False)])
def test_a_gradient_bar_is_revealed_not_stretched(tmp_path: Path, fill: Callable, kept: bool) -> None:
    pytest.importorskip("PIL")
    lit, colours = play_cases.gradient_checks(screenshots(tmp_path, fill, (0.5, 0.6)))
    assert lit[0], lit
    assert colours[0] is kept, colours


def transcript_of(path: Path, calls: list[tuple[str, dict, str, bool]]) -> Path:
    """A transcript of (tool, input, result, failed) calls, each with its result in the next entry."""
    lines = []
    for n, (tool, given, result, failed) in enumerate(calls):
        lines.append(json.dumps({"message": {"content": [{"type": "tool_use", "id": f"t{n}", "name": tool, "input": given}]}}))
        lines.append(json.dumps({"message": {"content": [
            {"type": "tool_result", "tool_use_id": f"t{n}", "is_error": failed, "content": result}]}}))
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def test_trace_counts_the_route_of_a_run(tmp_path: Path) -> None:
    """Each route column of trace.json, from a transcript that holds one of everything it counts: a cat of
    SKILL.md, an instruction file whose clone line keeps <path-to>, reads of the clone, the check chain up to a
    passing plan, two --help reads of one script, a copied command that fails, a hand edit of a layout, a refused
    plan beside a dry run, a copied check and another that fail with findings, one that fails without, and a
    preview that never opened."""
    run_dir = tmp_path / "it" / "double-jump" / "with_skill"
    project, clone = run_dir / "project", tmp_path / "clone"
    (project / "layouts").mkdir(parents=True)
    block = ("path-to = " + clone.parent.as_posix() + "\n- Construct3-RAG: <path-to>/clone\n"
             "- Construct3-Cookbook: <path-to>/cookbook\n"
             "1. Run `python .agents/skills/construct3-agent-plugin/scripts/check_project.py` from the project folder.\n")
    (project / "AGENTS.md").write_text(block, encoding="utf-8")
    scripts = f"{project.as_posix()}/.agents/skills/construct3-agent-plugin/scripts"
    ok_line = ("ok: 7 object types, 0 families, 1 layouts, 1 sheets; next, review the design: python "
               ".agents/skills/construct3-agent-plugin/scripts/review_design.py, then open it: python "
               ".agents/skills/construct3-agent-plugin/scripts/open_in_editor.py --preview")
    calls = [
        ("Bash", {"command": f'cat "{project.as_posix()}/.agents/skills/construct3-agent-plugin/SKILL.md"'}, "x" * 6000, False),
        ("Read", {"file_path": f"{project.as_posix()}/AGENTS.md"}, block, False),
        ("Read", {"file_path": f"{clone.as_posix()}/data/c3-schemas/_index.json"}, "{}", False),
        ("Grep", {"pattern": "jump", "path": clone.as_posix()}, "No matches found", False),
        ("Bash", {"command": f'cd "{project.as_posix()}" && python {scripts}/check_project.py --project "{project.as_posix()}"'}, ok_line, False),
        ("Bash", {"command": f"python {scripts}/preview_project.py --help 2>&1 | head -c 6000"}, "usage: preview_project.py", False),
        ("Bash", {"command": f'S="{scripts}" && python "$S/preview_project.py" --help | tail -c +6000'}, "a plan is", False),
        ("Bash", {"command": "python scripts/review_design.py"}, "Exit code 2\npython: can't open file 'scripts/review_design.py'", True),
        ("Edit", {"file_path": f"{project.as_posix()}/layouts/x.json", "old_string": "a", "new_string": "b"}, "updated", False),
        ("Bash", {"command": f'python {scripts}/edit_sheet.py "Event sheet 1" .tmp/plan.json'},
         "Exit code 1\noperation 1: event 9 does not print the line given\nnothing was written", True),
        ("Bash", {"command": f'python {scripts}/edit_sheet.py "Event sheet 1" .tmp/plan.json --dry-run'},
         "Event sheet 1: 1 operation, 8 events before and 9 now (dry run)\ndry run: nothing was written", False),
        ("Bash", {"command": f'cd "{project.as_posix()}" && python .agents/skills/construct3-agent-plugin/scripts/check_project.py'},
         "Exit code 1\nEvent sheet 1 event 9: parameter omitted\n1 problem(s)", True),
        ("Bash", {"command": f"python {scripts}/check_project.py"},
         "Exit code 1\nwarning: Event sheet 1 event 3: no comment above it\nEvent sheet 1 event 9: parameter omitted\n1 problem(s)", True),
        ("Bash", {"command": f"python {scripts}/check_project.py --nonsense"},
         "Exit code 2\nusage: check_project.py [-h]\ncheck_project.py: error: unrecognized arguments: --nonsense", True),
        ("Bash", {"command": f"python {scripts}/open_in_editor.py --preview"},
         "no preview window in 20 seconds\n0 of 1 opened and ran without errors; full results in .tmp/open-in-editor.json", False),
        ("Bash", {"command": f"python {scripts}/preview_project.py .tmp/plan.json"},
         "opened   project\n  1 key ArrowRight 0.5 s  ok\nkeep: this plan passes; keep it with --keep NAME", False),
    ]
    transcript = transcript_of(tmp_path / "agent.jsonl", calls)
    code, out = run(tmp_path, EVALS / "trace.py", str(transcript), "--out", str(run_dir))
    assert code == 0, out
    trace = read_json(run_dir / "trace.json")
    assert {k: trace[k] for k in grader.TRACE_COLUMNS} == {
        "tool_calls": 16, "lost_calls": 4, "turns": 0, "output_tokens": 0, "read_skill_md": True,
        "first_script": "check_project", "chain_depth": 4, "chain_end": "preview_project", "chain_reached": "preview_project",
        "chain_attempts": 7, "preview_failed": 1, "help_reads": 2, "repeat_help": 1, "plan_refusals": 1, "hand_edits": 1,
        "lookups_before_first_edit": 8, "data_reads": 1, "other_clone_reads": 1, "entry_chars": 6018 + len(block),
        "printed_command_failures": 1, "print_sheet_chars": 0, "whole_sheet_prints": 0, "cookbook_reads": 0,
        "pointers_printed": 0, "pointer_follows": 0, "read_design_guide": False, "cookbook_misses": 0,
        "checked_after_last_edit": False, "compactions": 0, "compaction_skill": None,
        "reread_skill_md_after_compaction": None, "chain_depth_after_compaction": None, "lookups_after_compaction": None}
    assert trace["chain"] == {"check_project": {"calls": 4, "passed": True}, "review_design": {"calls": 1, "passed": False},
                              "open_in_editor": {"calls": 1, "passed": False}, "preview_project": {"calls": 1, "passed": True},
                              "review_look": {"calls": 0, "passed": False}}
    assert trace["help_reads_by_script"] == {"preview_project": 2}
    assert trace["outside"] == [] and len(trace["outside_reads"]) == 2
    assert Path(trace["transcript"]) == transcript.resolve()
    assert (run_dir / "transcript.jsonl").read_bytes() == transcript.read_bytes()
    assert ("first script check_project, chain to preview_project (4 of 5, 7 calls), 2 help reads, 1 refused plans, "
            "1 hand edits, 8 calls before the first edit") in out
    code, out = run(tmp_path, EVALS / "trace.py", str(transcript))
    assert code == 0, out
    assert "1 refused plans, hand edits and calls before the first edit need --out or --root with its project/" in out


def cookbook_run(tmp_path: Path, line: bool) -> tuple[Path, Path]:
    """A run folder whose project names a Cookbook clone with a few pages on its Construct3-Cookbook: line, or
    names none."""
    run_dir, cookbook = tmp_path / "run", tmp_path / "cookbook"
    (run_dir / "project" / "layouts").mkdir(parents=True, exist_ok=True)
    for page in ("pitfalls.md", "design/thinking.md", "behaviors/timer.md", "behaviors/platform.md", "behaviors/dragndrop.md"):
        (cookbook / "guides" / page).parent.mkdir(parents=True, exist_ok=True)
        (cookbook / "guides" / page).write_text("# page\n", encoding="utf-8")
    block = f"- Construct3-RAG: {(tmp_path / 'clone').as_posix()}\n"
    (run_dir / "project" / "AGENTS.md").write_text(
        block + (f"- Construct3-Cookbook: {cookbook.as_posix()}\n" if line else ""), encoding="utf-8")
    return run_dir, cookbook


def test_trace_counts_the_cookbook_pages_and_the_pointers_followed(tmp_path: Path) -> None:
    """The design guide read before the edit, a lookup_ace.py pointer followed before the edit, one followed after
    it and one never followed, a search_guides.py result path relative to the cd of its command that a later sed
    reads, and two cats of a page that is not there, both misses: one lost, one whose error a pipe hid."""
    run_dir, cookbook = cookbook_run(tmp_path, line=True)
    guides, scripts = (cookbook / "guides").as_posix(), "/s/.agents/skills/construct3-agent-plugin/scripts"
    missing, hidden = f"{cookbook.as_posix()}/pitfalls/behaviors/timer.md", f"{guides}/pitfalls/timer.md"
    calls = [
        ("Bash", {"command": f'cat "{guides}/design/thinking.md"'}, "# page", False),
        ("Bash", {"command": f"python {scripts}/lookup_ace.py Timer start"},
         f"Timer: Start timer\n  pitfalls: {guides}/behaviors/timer.md, {guides}/plugins/system.md", False),
        ("Bash", {"command": f"python {scripts}/lookup_ace.py Platform jump"},
         "Platform: Simulate control\n  pitfalls: Construct3-Cookbook/guides/behaviors/platform.md", False),
        ("Bash", {"command": f'cd "{cookbook.as_posix()}" && python {scripts}/search_guides.py drag'},
         "pitfalls:\nguides/behaviors/dragndrop.md:17\n  Drag & Drop moves the dragged instance only when ...", False),
        ("Read", {"file_path": f"{guides}/behaviors/timer.md"}, "1\t# page", False),
        ("Bash", {"command": f'cat "{missing}"'}, f"Exit code 1\ncat: {missing}: No such file or directory", True),
        ("Bash", {"command": f'cat "{hidden}" 2>&1 | head'}, f"cat: {hidden}: No such file or directory", False),
        ("Bash", {"command": f'cd "{cookbook.as_posix()}" && sed -n 1,40p guides/behaviors/dragndrop.md'}, "# page", False),
        ("Edit", {"file_path": f"{(run_dir / 'project').as_posix()}/layouts/x.json", "old_string": "a", "new_string": "b"},
         "updated", False),
        ("Read", {"file_path": f"{guides}/behaviors/platform.md"}, "1\t# page", False),
    ]
    transcript = transcript_of(tmp_path / "agent.jsonl", calls)
    code, out = run(tmp_path, EVALS / "trace.py", str(transcript), "--out", str(run_dir))
    assert code == 0, out
    trace = read_json(run_dir / "trace.json")
    assert {k: trace[k] for k in tracer.COOKBOOK_COLUMNS} == {
        "cookbook_reads": 4, "cookbook_pages": ["design/thinking.md", "behaviors/timer.md", "behaviors/dragndrop.md",
                                                "behaviors/platform.md"],
        "pointers_printed": 4, "pointer_follows": 3,
        "pointers": {"lookup_ace": {"printed": ["behaviors/timer.md", "plugins/system.md", "behaviors/platform.md"],
                                    "followed": ["behaviors/timer.md", "behaviors/platform.md"]},
                     "search_guides": {"printed": ["behaviors/dragndrop.md"], "followed": ["behaviors/dragndrop.md"]}},
        "read_design_guide": True, "cookbook_misses": 2,
        "cookbook_missed": [str(Path(missing).resolve()), str(Path(hidden).resolve())]}
    assert trace["lost_calls"] == 1 and trace["lookups_before_first_edit"] == 8
    assert "4 Cookbook reads (design/thinking.md, behaviors/timer.md" in out and "3 of 4 pointers followed" in out


def test_trace_leaves_the_cookbook_columns_null_without_a_clone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A project that names no Cookbook, where none lies beside the clones, has no Cookbook columns; one that names
    a clone has them even when the run read none of it."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CONSTRUCT3_COOKBOOK", raising=False)
    monkeypatch.setattr(tracer.c3project, "cookbook_places", lambda rag: [])
    calls = [{"tool": "Read", "what": "x", "failed": False, "result": "", "input": {"file_path": "/x/AGENTS.md"},
              "chars": 0, "loads_skill": False}]
    run_dir, _ = cookbook_run(tmp_path, line=False)
    assert all(tracer.summary(calls, run_dir)[k] is None for k in tracer.COOKBOOK_COLUMNS)
    run_dir, _ = cookbook_run(tmp_path, line=True)
    assert tracer.summary(calls, run_dir)["pointers_printed"] == 0


@pytest.mark.parametrize(("command", "edit"), [
    ('cd "{p}" && python.exe - <<\'PY\'\nimport pathlib\np = pathlib.Path("scripts/main.ts")\n'
     'p.write_bytes(p.read_bytes().replace(b"200", b"400"))\nPY', True),
    ('python.exe - <<\'PY\'\np = "{p}/scripts/main.ts"\nopen(p, "wb").write(open(p, "rb").read())\nPY', True),
    ('cd "{p}" && cat > scripts/main.ts <<\'EOF\'\nconst a = 1;\nEOF', True),
    ('cd "{p}" && python -c "import json; print(json.load(open(\'objectTypes/Player.json\'))[\'name\'])"', False),
    ('cd "{p}" && cat > .tmp/plan.json <<\'EOF\'\n[]\nEOF', False),
])
def test_trace_sees_a_write_made_inside_a_script(tmp_path: Path, command: str, edit: bool) -> None:
    """A heredoc or an inline script that writes a project file is the run's edit, relative to the cd before it;
    a read, and a write under .tmp/, are not."""
    project = tmp_path / "project"
    project.mkdir()
    call = {"tool": "Bash", "what": "", "failed": False, "result": "", "input": {"command": command.format(p=project.as_posix())}}
    assert bool(tracer.project_edits(call, project)) is edit, tracer.inline_writes(call["input"]["command"])


@pytest.mark.parametrize(("command", "reads"), [
    ('cd "{c}" && cat Construct3-Cookbook/guides/design/thinking.md | head -c 9000', ["Construct3-Cookbook/guides/design/thinking.md"]),
    ('cd "{c}" && ls data/c3-schemas/ && ls data/c3-schemas/en-US/', ["data/c3-schemas", "data/c3-schemas/en-US"]),
    ('cd "{c}" && python skills/construct3-agent-plugin/scripts/print_sheet.py --project "{c}/x" Game', []),
    ('cd "{c}" && grep -rn "isKeyDown" --include=*.md . | head', ["."]),
    ('python check.py --rag "{c}" --project "{c}/game"', []),
])
def test_trace_reads_relative_to_the_cd_of_a_command(tmp_path: Path, command: str, reads: list[str]) -> None:
    """A path after a cd is read in that folder; a script run from the clone and a folder a script is pointed
    at are not reads of it."""
    clone = tmp_path / "clone"
    found = tracer.read_paths(command.format(c=clone.as_posix()))
    assert [Path(p) for p in found] == [(clone / r).resolve() for r in reads]


def restart_runs(tmp_path: Path, depths: dict[str, list[int]]) -> Path:
    """An iteration of name-the-restart-event runs that all pass and have reported, each traced with the chain
    depth given."""
    iteration = tmp_path / "it"
    answer = (ANSWERS / "english_all_three.md").read_text(encoding="utf-8")
    ends = {1: "check_project", 2: "review_design", 4: "preview_project", 5: "review_look"}
    for arm, cell in depths.items():
        for n, depth in enumerate(cell):
            case = iteration / "name-the-restart-event" / (arm if n == 0 else f"{arm}_{n + 1}")
            answer_case(case, answer)
            (case / "timing.json").write_text(json.dumps({"total_tokens": 40000, "duration_ms": 90000}), encoding="utf-8")
            (case / "trace.json").write_text(json.dumps({
                "tool_calls": 20 + depth, "lost_calls": 1, "turns": 15, "output_tokens": 3000, "read_skill_md": True,
                "first_script": "check_project", "chain_depth": depth, "chain_end": ends[depth],
                "chain_reached": "review_look", "chain_attempts": depth + 1,
                "preview_failed": 0, "help_reads": 1, "repeat_help": 0, "plan_refusals": 0, "hand_edits": 0,
                "lookups_before_first_edit": 8, "data_reads": 1, "other_clone_reads": 0, "entry_chars": 30000,
                "printed_command_failures": 0, "print_sheet_chars": 9000, "whole_sheet_prints": 0,
                "cookbook_reads": depth - 1, "pointers_printed": 2, "pointer_follows": int(depth > 3),
                "read_design_guide": depth > 4, "cookbook_misses": 0, "checked_after_last_edit": depth > 1,
                "compactions": 1, "compaction_skill": "reference" if arm == "old_skill" else "re-attached",
                "reread_skill_md_after_compaction": False, "chain_depth_after_compaction": depth - 1,
                "lookups_after_compaction": 2, "model": "claude-opus-5-5", "outside": [], "outside_reads": []}),
                encoding="utf-8")
    return iteration


def test_grade_carries_the_route_columns_and_decides_on_one(tmp_path: Path) -> None:
    """benchmark.json holds every column per run, averaged or counted per cell and in the arm delta, and the
    verdict of decision.json; compare.py gives the same test from the file."""
    iteration = restart_runs(tmp_path, {"with_skill": [5, 5, 4], "old_skill": [1, 2, 1]})
    (iteration / "decision.json").write_text(json.dumps({
        "cases": ["name-the-restart-event"], "metric": "chain_depth", "direction": "up", "n_per_cell": 3,
        "guards": {"pass_rate": "not down"}, "concurrency": 3}), encoding="utf-8")
    out = grade_iteration(tmp_path)
    assert ("decision: chain_depth up: with_skill - old_skill = +10 over 1 case, one-sided p = 0.050 (exact, 20 "
            "reassignments); guard pass_rate not down holds (1.0 vs 1.0); verdict: holds at alpha 0.05, 3 runs at once") in out
    benchmark = read_json(iteration / "benchmark.json")
    with_skill = benchmark["by_case"]["name-the-restart-event"]["with_skill"]
    assert with_skill["chain_depth"] == {"mean": 4.667, "runs": 3, "stddev": 0.577}
    assert with_skill["chain_end"] == {"preview_project": 1, "review_look": 2} and with_skill["first_script"] == {"check_project": 3}
    assert with_skill["chain_reached"] == {"review_look": 3}
    assert with_skill["compaction_skill"] == {"re-attached": 3} and with_skill["checked_after_last_edit"]["mean"] == 1
    assert set(grader.TRACE_COLUMNS) <= set(with_skill["runs"][0])
    assert with_skill["runs"][0]["tool_calls"] == 25 and with_skill["lost_calls"]["mean"] == 1
    assert with_skill["pointer_follows"] == {"mean": 1, "runs": 3, "stddev": 0.0}
    assert with_skill["read_design_guide"]["mean"] == 0.667 and with_skill["cookbook_reads"]["mean"] == 3.667
    assert benchmark["run_summary"]["delta"]["with_skill - old_skill"]["pointer_follows"] == 1
    assert benchmark["run_summary"]["delta"]["with_skill - old_skill"]["chain_depth"] == pytest.approx(10 / 3, abs=0.01)
    assert benchmark["run_summary"]["with_skill"]["chain_end"] == {"preview_project": 1, "review_look": 2}
    assert benchmark["decision"]["verdict"] == "holds" and benchmark["decision"]["p"] == 0.05
    code, out = run(tmp_path, EVALS / "compare.py", str(iteration / "benchmark.json"), "chain_depth")
    assert code == 0 and out.strip() == ("chain_depth up: with_skill - old_skill = +10 over 1 case, one-sided p = 0.050 "
                                         "(exact, 20 reassignments)")
    code, out = run(tmp_path, EVALS / "compare.py", str(iteration / "benchmark.json"), "chain_depth", "--direction", "down")
    assert "p = 1.000" in out
    code, out = run(tmp_path, EVALS / "compare.py", str(iteration / "benchmark.json"), "pointer_follows")
    assert code == 0 and "pointer_follows up: with_skill - old_skill = +3 over 1 case, one-sided p = 0.050" in out


def test_grade_says_underpowered_and_aggregates_all_the_same(tmp_path: Path) -> None:
    iteration = restart_runs(tmp_path, {"with_skill": [5, 5, 4], "old_skill": [1, 2]})
    (iteration / "decision.json").write_text(json.dumps({
        "cases": ["name-the-restart-event"], "metric": "chain_depth", "direction": "up", "n_per_cell": 3}), encoding="utf-8")
    out = grade_iteration(tmp_path)
    assert "underpowered: name-the-restart-event/old_skill: 2 of 3; no verdict on chain_depth" in out
    benchmark = read_json(iteration / "benchmark.json")
    assert benchmark["decision"]["verdict"] == "underpowered"
    assert benchmark["by_case"]["name-the-restart-event"]["old_skill"]["chain_depth"]["mean"] == 1.5


def test_a_run_that_lacks_a_part_makes_the_coverage_incomplete(tmp_path: Path, project: Path) -> None:
    """A run graded before it reported, or before its plan was played, is scored on the fixture or on part of its
    assertions; the benchmark says so instead of counting it as a full run."""
    case = project_case(tmp_path, project, "fix-next-round")
    out = grade_iteration(tmp_path)
    assert "fix-next-round/with_skill: " in out and "(missing: answer, trace, timing, play)" in out
    assert ("coverage incomplete, so the scores of these runs do not stand: "
            "fix-next-round/with_skill (answer, trace, timing, play)") in out
    benchmark = read_json(tmp_path / "it" / "benchmark.json")
    assert benchmark["coverage_complete"] is False
    assert benchmark["incomplete_runs"] == [{"run": "fix-next-round/with_skill",
                                             "missing": ["answer", "trace", "timing", "play"]}]
    assert benchmark["by_case"]["fix-next-round"]["with_skill"]["runs"][0]["missing"] == benchmark["incomplete_runs"][0]["missing"]
    played(case, [True, True])
    (case / "outputs").mkdir()
    (case / "outputs" / "answer.md").write_text("Fixed.\n", encoding="utf-8")
    (case / "timing.json").write_text(json.dumps({"total_tokens": 1, "duration_ms": 1000}), encoding="utf-8")
    (case / "trace.json").write_text(json.dumps({"tool_calls": 1, "outside": [], "outside_reads": []}), encoding="utf-8")
    out = grade_iteration(tmp_path)
    assert "coverage complete: every scored run" in out
    assert read_json(tmp_path / "it" / "benchmark.json")["coverage_complete"] is True


def test_a_decision_over_an_incomplete_run_gives_no_verdict(tmp_path: Path) -> None:
    iteration = restart_runs(tmp_path, {"with_skill": [5, 5, 4], "old_skill": [1, 2, 1]})
    (iteration / "name-the-restart-event" / "old_skill_2" / "timing.json").unlink()
    (iteration / "decision.json").write_text(json.dumps({
        "cases": ["name-the-restart-event"], "metric": "chain_depth", "direction": "up", "n_per_cell": 3}), encoding="utf-8")
    out = grade_iteration(tmp_path)
    assert "incomplete: name-the-restart-event/old_skill_2: timing; no verdict on chain_depth" in out
    decision = read_json(iteration / "benchmark.json")["decision"]
    assert decision["verdict"] == "incomplete" and decision["incomplete"] == ["name-the-restart-event/old_skill_2: timing"]


def test_the_benchmark_flags_a_saturated_case_and_one_no_run_passed(tmp_path: Path) -> None:
    """A case every run of both arms passes cannot decide between them; one no run passes may grade correct
    answers as wrong, as the find cases did."""
    iteration = restart_runs(tmp_path, {"with_skill": [5, 4], "old_skill": [1, 2]})
    for name in ("with_skill", "with_skill_2"):
        answer_case(iteration / "find-in-a-big-sheet" / name, "Event 267 pays it: 427 points.")
    out = grade_iteration(tmp_path)
    assert "saturated, every run of every arm passed, so the case tells the arms apart no more: name-the-restart-event" in out
    assert "no run passed, so read the runs before the case is trusted: find-in-a-big-sheet" in out
    flags = read_json(iteration / "benchmark.json")["case_flags"]
    assert flags == {"saturated": ["name-the-restart-event"], "none_passed": ["find-in-a-big-sheet"]}


def test_the_benchmark_names_what_the_grading_ran_with(tmp_path: Path) -> None:
    """A score read later is traced to the grader, the data, the flags and the commit the fixtures came from."""
    iteration = restart_runs(tmp_path, {"with_skill": [5]})
    laid_out = {"commit": "abc123", "folder": "runs/clone-abc123", "old_commit": None}
    (iteration / "clone.json").write_text(json.dumps(laid_out), encoding="utf-8")
    grade_iteration(tmp_path)
    benchmark = read_json(iteration / "benchmark.json")
    meta = benchmark["meta"]
    assert meta["laid_out"] == laid_out and meta["play"] is False and meta["release"] is None
    assert meta["graded_at"].endswith("+00:00")
    assert meta["grader"] is None or set(meta["grader"]) == {"commit", "dirty"}
    assert benchmark["by_case"]["name-the-restart-event"]["with_skill"]["model"] == {"claude-opus-5-5": 1}


@pytest.mark.parametrize(("text", "error"), [
    ('{"cases": ["name-the-restart-event"], "direction": "up", "n_per_cell": 3}', 'missing key "metric"'),
    ('{"cases": [', "not JSON ("),
])
def test_grade_writes_the_benchmark_when_decision_json_cannot_be_read(tmp_path: Path, text: str, error: str) -> None:
    """A misspelled key or a broken file costs the verdict, not the aggregation."""
    iteration = restart_runs(tmp_path, {"with_skill": [5, 5, 4], "old_skill": [1, 2, 1]})
    (iteration / "decision.json").write_text(text, encoding="utf-8")
    out = grade_iteration(tmp_path)
    assert f"decision.json: {error}" in out and "benchmark written without a verdict" in out
    benchmark = read_json(iteration / "benchmark.json")
    assert benchmark["decision"]["verdict"] == "not read" and benchmark["decision"]["error"].startswith(error)
    assert benchmark["by_case"]["name-the-restart-event"]["with_skill"]["chain_depth"]["mean"] == 4.667


def test_the_permutation_test_reassigns_within_each_case() -> None:
    one = {"a": [("with", 5), ("with", 5), ("with", 4), ("old", 1), ("old", 2), ("old", 1)]}
    assert compare.permutation_test(one, "with", "up") == {"observed": 10, "p": 0.05, "permutations": 20, "exact": True}
    assert compare.permutation_test(one, "with", "down")["p"] == 1.0
    two = one | {"b": [("with", 3), ("with", 3), ("old", 3), ("old", 3)]}
    assert compare.permutation_test(two, "with", "up") == {"observed": 10, "p": 0.05, "permutations": 120, "exact": True}
    assert compare.permutation_test(one | {"c": [("with", 9)]}, "with", "up")["permutations"] == 20
    with pytest.raises(ValueError):
        compare.permutation_test({"c": [("with", 9)]}, "with", "up")
    sampled = compare.permutation_test(one, "with", "up", exact_up_to=10)
    assert sampled["exact"] is False and sampled["permutations"] == 10 and 0 < sampled["p"] <= 1


def test_find_in_a_big_sheet_grades_the_event_and_the_bonus(tmp_path: Path) -> None:
    """Wave 17's bonus is event 284 of the fixture's sheet, GiveBonus(454); the wave and the bonus written near
    "event" are not taken for event numbers."""
    run_dir = tmp_path / "run"
    (run_dir / "project").mkdir(parents=True)
    (run_dir / "outputs").mkdir()
    (run_dir / "project" / "project.c3proj").write_text("{}", encoding="utf-8")
    (run_dir / "fixture.json").write_text(json.dumps(make_fixtures.digest(run_dir / "project")), encoding="utf-8")
    answer = run_dir / "outputs" / "answer.md"
    answer.write_text("Event 284, in the group Wave 17 score (event 280), pays the bonus of wave 17: it calls "
                      "GiveBonus(454), event 410, so the bonus is 454 points.\n\n## Commands run\n"
                      "python scripts/print_sheet.py Waves --events 1-17", encoding="utf-8")
    assert [ok for ok, _ in grader.grade_find_in_a_big_sheet(run_dir)] == [True, True, True]
    answer.write_text("Event 300 pays it: 380 points.", encoding="utf-8")
    assert [ok for ok, _ in grader.grade_find_in_a_big_sheet(run_dir)] == [False, False, True]
    assert make_fixtures.wave_bonus(make_fixtures.BIG_SHEET_FOCUS) == 454 and "coins-big-sheet" in make_fixtures.SEEDS


FIND_ANSWERS = Path(__file__).parent / "fixtures" / "find_answers"


def read_only_run(tmp_path: Path, answer: str) -> Path:
    """A run of a read-only case: answer as its answer.md, and a project that matches its fixture.json."""
    run_dir = tmp_path / "run"
    (run_dir / "project").mkdir(parents=True)
    (run_dir / "outputs").mkdir()
    (run_dir / "fixture.json").write_text("{}", encoding="utf-8")
    (run_dir / "outputs" / "answer.md").write_text(answer, encoding="utf-8")
    return run_dir


@pytest.mark.parametrize(("grade_case", "answer", "passed"), [
    # Correct answers of earlier runs that also cite the events around the one asked for
    ("grade_find_in_a_long_sheet", "long_sheet_lists_what_the_restart_reruns.md", [True, True, True, True]),
    ("grade_find_in_a_long_sheet", "long_sheet_names_the_start_events.md", [True, True, True, True]),
    ("grade_find_in_a_long_sheet", "long_sheet_answers_in_chinese.md", [True, True, True, True]),
    ("grade_find_in_a_big_sheet", "big_sheet_follows_the_bonus_to_addscore.md", [True, True, True]),
    ("grade_find_in_a_big_sheet", "big_sheet_compares_other_waves.md", [True, True, True]),
    # Wrong answers: another event as the finish line and the restart, another wave's bonus
    ("grade_find_in_a_long_sheet", "Event 102 is the finish line. The layout restarts in event 107, prepareForGameOver, "
                                   "for the player (success) or any other tractor (fail).", [False, False, True, True]),
    ("grade_find_in_a_long_sheet", "事件 102 处理终点线（Finish Line）。游戏在事件107 `prepareForGameOver` 里调用 "
                                   "showGameOver，再执行 Restart layout，玩家（Player）是 success，其他是 fail。",
     [False, False, True, True]),
    ("grade_find_in_a_big_sheet", "Event 267 pays the bonus of wave 17: 427 points.", [False, False, True]),
])
def test_find_answers_are_graded_by_what_they_give(tmp_path: Path, grade_case: str, answer: str,
                                                   passed: list[bool]) -> None:
    """A correct answer passes every assertion however many other events it cites; a wrong one fails."""
    text = (FIND_ANSWERS / answer).read_text(encoding="utf-8") if answer.endswith(".md") else answer
    results = getattr(grader, grade_case)(read_only_run(tmp_path, text))
    assert [ok for ok, _ in results] == passed, [said for _, said in results]


@NEEDS_EXAMPLES
@pytest.mark.parametrize(("answer", "passed"), [
    ("drag_lists_the_drop_in_bold.md", True),
    ("drag_lists_the_drop_after_a_colon.md", True),
    ("drag_lists_place_stickers.md", True),
    ("The official example **Place stickers** (`place-stickers`) handles the drop:\n\n"
     "- **16**: `Sticker: On DragDrop drop`.\n", False),
])
def test_a_drag_answer_gives_the_drop_event_in_a_list(tmp_path: Path, answer: str, passed: bool) -> None:
    """An answer that lists the drop event as a bullet, "- **12** `On DragDrop drop`", gives its number; one that
    lists another event of the example as the drop does not."""
    text = (FIND_ANSWERS / answer).read_text(encoding="utf-8") if answer.endswith(".md") else answer
    results = grader.grade_find_a_drag_example(read_only_run(tmp_path, text))
    assert results[1][0] is passed, results[1][1]


@pytest.mark.parametrize("command, whole", [
    ("python scripts/print_sheet.py Waves --limit 0", True),
    ('python scripts/print_sheet.py "Waves" --outline --limit=0', True),
    ("python scripts/print_sheet.py Waves --limit 0 --events 1-40", False),
    ("python scripts/print_sheet.py Waves --find GiveBonus --limit 0", False),
    ("python scripts/print_sheet.py Waves", False),
    ("python scripts/print_sheet.py Waves --limit 0 | grep -c Wave; python scripts/print_sheet.py Game", True),
])
def test_trace_counts_whole_sheet_prints_and_print_sheet_characters(tmp_path: Path, command: str, whole: bool) -> None:
    """The metric of a long sheet's list (docs/decisions/long-sheet-contents.md): what print_sheet.py printed, and
    how often a run asked for whole sheets past the limit."""
    transcript = transcript_of(tmp_path / "agent.jsonl", [("Bash", {"command": command}, "x" * 1234, False)])
    code, out = run(tmp_path, EVALS / "trace.py", str(transcript), "--out", str(tmp_path))
    trace = read_json(tmp_path / "trace.json")
    assert code == 0 and trace["print_sheet_chars"] == 1234 and trace["whole_sheet_prints"] == int(whole)


def hud_results(case: Path, *words: str) -> tuple:
    """grade_lay_out_the_hud on case: the (passed, evidence) of the HUD case's first assertion holding each word."""
    results = dict(zip(CASES["lay-out-the-hud"]["assertions"], grader.grade_lay_out_the_hud(case)))
    return tuple(next(v for k, v in results.items() if word in k) for word in words)


def test_the_hud_case_grades_by_the_templates_own_rules(tmp_path: Path, project: Path) -> None:
    """A run of the HUD case is held to its own generator's MARGIN; a label inside its key's box is laid on
    purpose, not an overlap; a hollow box lies round a label and not behind it; and the stand-in's own HUD
    counts as nothing the run added."""
    pytest.importorskip("PIL")
    case = tmp_path / "it" / "lay-out-the-hud" / "with_skill"
    shutil.copytree(project, case / "project")
    assert grader.margin_of(case / "project") == 64 and grader.margin_of(tmp_path) == grader.MARGIN
    assert grader.one_colour(case / "project", "KeyBox") is None
    assert grader.one_colour(case / "project", "Coin") == (61, 90, 254)
    added, overlap, sizes, edges = hud_results(case, "besides", "overlap", "multiples", "held against")
    assert added[0] is False and "0 added instance(s)" in added[1]
    assert overlap == (True, "overlapping boxes: none")
    assert sizes[0] is False and "0 added non-text instance(s)" in sizes[1] and edges[0] is False


def test_the_hud_case_lines_a_small_drawing_up_by_what_it_draws(tmp_path: Path, project: Path) -> None:
    """A sprite the run adds to the HUD is sized in units and lines up by its box or by its drawing: a button
    drawn 64 px across in the middle of a 160 px box a finger hits has its drawing MARGIN inside the corner,
    and its box 16 px from the edge. The stand-in's texts are measured to their text and stay out of both."""
    pytest.importorskip("PIL")
    from PIL import Image, ImageDraw
    case = tmp_path / "it" / "lay-out-the-hud" / "with_skill"
    shutil.copytree(project, case / "project")
    image = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(image).ellipse([48, 48, 111, 111], fill=(20, 19, 17, 255))
    image.save(case / "project" / "images" / "pausebutton-default-000.png")
    (case / "project" / "objectTypes" / "PauseButton.json").write_text(
        json.dumps({"name": "PauseButton", "plugin-id": "Sprite"}), encoding="utf-8")
    path = case / "project" / "layouts" / "Game.json"
    layout = json.loads(path.read_text(encoding="utf-8"))
    ui = next(layer for layer in layout["layers"] if layer["name"] == "UI")["instances"]
    button = json.loads(json.dumps(next(i for i in ui if i["type"] == "KeyBox")))
    button["type"] = "PauseButton"
    ui.append(button)

    def graded(x: int, y: int) -> tuple:
        button["world"].update({"x": x, "y": y, "width": 160, "height": 160, "originX": 0, "originY": 0})
        path.write_text(json.dumps(layout), encoding="utf-8")
        return hud_results(case, "multiples", "held against")

    sizes, edges = graded(1920 - 64 - 112, 1080 - 64 - 112)
    assert sizes[0] is True and "1 added non-text instance(s)" in sizes[1]
    assert edges == (True, "added non-text types neither 64 px inside an edge, nor centred, nor one unit under a "
                           "held box, by box or drawing: none")
    sizes, edges = graded(1920 - 64 - 112 - 8, 1080 - 64 - 112)
    assert edges[0] is False and "PauseButton box (1736,904)-(1896,1064), drawn (1784,952)-(1848,1016)" in edges[1]


def test_a_step_handed_to_a_function_counts_by_the_constant_it_names() -> None:
    """`Call AddHealth(HP_PER_COIN)`, a constant at 10, whose body sets hp to `clamp(hp + amount, ...)`, adds 10
    to hp; handed a constant at 5 it does not."""
    def rows(per_coin: int) -> list:
        return [({"eventType": "variable", "name": "HP_PER_COIN", "initialValue": per_coin}, []),
                ({"eventType": "variable", "name": "hp", "initialValue": 40}, []),
                ({"eventType": "block", "actions": [{"callFunction": "AddHealth", "parameters": ["HP_PER_COIN"]}]}, []),
                ({"eventType": "function-block", "actions": [
                    {"id": "set-eventvar-value", "objectClass": "System",
                     "parameters": {"variable": "hp", "value": "clamp(hp + amount, 0, HP_MAX)"}}]}, [])]

    assert [a["parameters"]["value"] for a in grader.steps_by(rows(10), {"hp"}, "10")] == ["clamp(hp + amount, 0, HP_MAX)"]
    assert grader.steps_by(rows(5), {"hp"}, "10") == []


def test_the_lives_plan_counts_the_hearts_that_still_look_full() -> None:
    """Lives kept in a static local or drawn from a count of coins are no number the runtime shows, so the lives
    plan also watches, per sprite type of three or more on the UI layer, how many instances look like the
    leftmost one, leaving the stand-in's HUD out."""
    plan = play_cases.plan_for("lives-as-hearts")
    code = "\n".join(line for step in plan["steps"] if "js" in step for line in step["js"])
    assert "vars.h.fullHearts = () =>" in code and f"stand = {json.dumps(play_cases.STAND_IN_HUD)}" in code
    assert "vars.watch.numbers = () => Object.assign(vars.h.numbers(), vars.h.fullHearts())" in code


def test_lives_drawn_from_a_count_of_coins_start_at_5_and_drop_by_one() -> None:
    """`HEARTS - floor(taken / COINS_PER_LIFE)`, with HEARTS a constant at 5 and `Add 1 to taken` on a collect, are
    lives that start at 5 and drop by one, as a variable at 5 that loses 1 is; a count nothing adds 1 to is not."""
    def rows(step: str) -> list:
        return [({"eventType": "variable", "name": "HEARTS", "initialValue": 5}, []),
                ({"eventType": "variable", "name": "taken", "initialValue": 0}, []),
                ({"eventType": "block", "actions": [
                    {"id": "add-to-eventvar", "objectClass": "System", "parameters": {"variable": "taken", "value": step}}]}, []),
                ({"eventType": "block", "conditions": [
                    {"id": "compare-instance-variable", "objectClass": "Heart",
                     "parameters": {"instance-variable": "slot", "comparison": 4,
                                    "value": "HEARTS - floor(taken / COINS_PER_LIFE)"}}]}, [])]

    assert grader.lives_from_count(rows("1"), {"HEARTS", "slot"}) == [("HEARTS", "taken")]
    assert grader.lives_from_count(rows("2"), {"HEARTS", "slot"}) == []


def compacted_transcript(path: Path, before: list, after: list, kept: dict) -> Path:
    """A transcript of (tool, input, result) calls before and after a compaction whose attachment is kept."""
    def lines(calls: list, prefix: str) -> list[str]:
        return [json.dumps(entry) for n, (name, given, result) in enumerate(calls) for entry in (
            {"message": {"content": [{"type": "tool_use", "id": f"{prefix}{n}", "name": name, "input": given}]}},
            {"message": {"content": [{"type": "tool_result", "tool_use_id": f"{prefix}{n}", "content": result}]}})]
    boundary = {"type": "system", "subtype": "compact_boundary",
                "compactMetadata": {"trigger": "manual", "preTokens": 48000, "postTokens": 6000}}
    path.write_text("\n".join([*lines(before, "b"), json.dumps(boundary), json.dumps({"type": "attachment", "attachment": kept}),
                               json.dumps({"type": "assistant", "message": {"content": []}}), *lines(after, "a")]),
                    encoding="utf-8")
    return path


@pytest.mark.parametrize(("kept", "skill", "checked"), [
    ({"type": "compact_file_reference", "filename": "C:\\g\\.agents\\skills\\construct3-agent-plugin\\SKILL.md"},
     "reference", True),
    ({"type": "invoked_skills", "skills": [{"name": "construct3:construct3-agent-plugin", "content": "x"}]},
     "re-attached", False)])
def test_trace_reads_what_a_compaction_kept_and_the_calls_after_it(tmp_path: Path, kept: dict, skill: str,
                                                                    checked: bool) -> None:
    """A SKILL.md the run read is kept as a reference to its path, one called through the Skill tool as its text.
    The columns after the compaction count the calls after it: a lookup before its first edit, then the edit, then
    a passing check, or none."""
    run_dir = tmp_path / "it" / "keep-checking-after-compaction" / "with_compact"
    project = run_dir / "project"
    (project / "eventSheets").mkdir(parents=True)
    skill_dir = f"{project.as_posix()}/.agents/skills/construct3-agent-plugin"
    sheet = f"{project.as_posix()}/eventSheets/Game.json"
    ok_line = "ok: 7 object types, 0 families, 1 layouts, 1 sheets"
    before = [("Read", {"file_path": f"{skill_dir}/SKILL.md"}, "x" * 6000),
              ("Edit", {"file_path": sheet, "old_string": "a", "new_string": "b"}, "updated"),
              ("Bash", {"command": f"python {skill_dir}/scripts/check_project.py"}, ok_line)]
    after = [("Bash", {"command": f"python {skill_dir}/scripts/lookup_ace.py Sprite set-scale"}, "set-scale"),
             ("Edit", {"file_path": sheet, "old_string": "b", "new_string": "c"}, "updated"),
             *([("Bash", {"command": f"python {skill_dir}/scripts/check_project.py"}, ok_line)] if checked else [])]
    transcript = compacted_transcript(tmp_path / "session.jsonl", before, after, kept)
    code, out = run(tmp_path, EVALS / "trace.py", str(transcript), "--out", str(run_dir))
    assert code == 0, out
    trace = read_json(run_dir / "trace.json")
    assert {k: trace[k] for k in ("compactions", "compaction_skill", "reread_skill_md_after_compaction",
                                  "chain_depth_after_compaction", "lookups_after_compaction",
                                  "checked_after_last_edit")} == {
        "compactions": 1, "compaction_skill": skill, "reread_skill_md_after_compaction": False,
        "chain_depth_after_compaction": int(checked), "lookups_after_compaction": 1, "checked_after_last_edit": checked}
    assert trace["compaction"] == [{"trigger": "manual", "pre_tokens": 48000, "post_tokens": 6000, "skill": skill}]
    assert f"compaction 1 (manual): 48000 to 6000 tokens, skill {skill}" in out


# A stand-in for claude -p: it logs each call and the sheet as it found it, writes a compaction into the session's
# transcript on /compact, and prints a JSON result, or the error of a client that is signed out.
FAKE_CLIENT = """
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
prompt = args[args.index("-p") + 1]
session = args[args.index("--resume") + 1] if "--resume" in args else None
sheet = Path("eventSheets/Game.json").read_text(encoding="utf-8")
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({"prompt": prompt, "resume": session, "inverted": "isInverted" in sheet,
                          "sources": args[args.index("--setting-sources") + 1]}) + "\\n")
if os.environ.get("FAKE_HANG"):
    import subprocess, time
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    Path(os.environ["FAKE_HANG"]).write_text(str(child.pid), encoding="utf-8")
    time.sleep(60)
if os.environ.get("FAKE_SIGNED_OUT"):
    print(json.dumps({"is_error": True, "result": "Failed to authenticate: OAuth session expired"}))
    sys.exit(1)
transcript = Path.home() / ".claude" / "projects" / "p" / "s1.jsonl"
transcript.parent.mkdir(parents=True, exist_ok=True)
with transcript.open("a", encoding="utf-8") as t:
    if prompt == "/compact":
        t.write(json.dumps({"type": "system", "subtype": "compact_boundary",
                            "compactMetadata": {"trigger": "manual", "preTokens": 40000, "postTokens": 5000}}) + "\\n")
print(json.dumps({"session_id": "s1", "result": "answered " + prompt[:12], "is_error": False, "duration_ms": 1000,
                  "total_cost_usd": 0.1, "usage": {"input_tokens": 10, "output_tokens": 5}}))
"""


def session_run(tmp_path: Path, arm: str) -> tuple[Path, str]:
    """A run folder of the compaction case whose project holds one On start of layout, and the fake client's command."""
    run_dir = tmp_path / "it" / "keep-checking-after-compaction" / arm
    (run_dir / "project" / "eventSheets").mkdir(parents=True)
    (run_dir / "project" / "eventSheets" / "Game.json").write_text(json.dumps({"events": [
        {"eventType": "block", "conditions": [{"id": "on-start-of-layout", "objectClass": "System"}], "actions": []}]}),
        encoding="utf-8")
    (tmp_path / "fake.py").write_text(FAKE_CLIENT, encoding="utf-8")
    return run_dir, f"{Path(sys.executable).as_posix()} {(tmp_path / 'fake.py').as_posix()}"


@pytest.mark.parametrize(("arm", "prompts"), [
    ("with_compact", ["in my coins ", "/compact", "one more thi"]),
    ("with_skill_2", ["in my coins ", "one more thi"])])
def test_run_session_compacts_between_turns_and_writes_the_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                                   arm: str, prompts: list[str]) -> None:
    """The second turn resumes the first one's session, after /compact in a compact arm, and finds the project
    changed: its On start of layout inverted. answer.md is the last answer, timing.json the turns' sum."""
    run_dir, client = session_run(tmp_path, arm)
    monkeypatch.setenv("FAKE_LOG", str(tmp_path / "log.jsonl"))
    code, out = run(tmp_path, EVALS / "run_session.py", str(run_dir), "--client", client)
    assert code == 0, out
    log = [json.loads(line) for line in (tmp_path / "log.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [entry["prompt"][:12] for entry in log] == prompts
    assert [entry["resume"] for entry in log] == [None, *["s1"] * (len(prompts) - 1)]
    assert [entry["inverted"] for entry in log] == [False] * (len(prompts) - 1) + [True]
    assert {entry["sources"] for entry in log} == {"project,local"}
    session = read_json(run_dir / "outputs" / "session.json")
    compactions = [t["compaction"] for t in session["turns"] if t.get("prompt") == "/compact"]
    assert compactions == ([{"pre_tokens": 40000, "post_tokens": 5000}] if "compact" in arm else [])
    assert (run_dir / "outputs" / "answer.md").read_text(encoding="utf-8") == "answered one more thi"
    assert read_json(run_dir / "timing.json") == {"duration_ms": 1000 * len(prompts), "total_tokens": 15 * len(prompts)}
    assert f"--out \"{run_dir.resolve().as_posix()}\"" in out


def test_run_session_stops_when_the_client_is_signed_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir, client = session_run(tmp_path, "with_compact")
    monkeypatch.setenv("FAKE_LOG", str(tmp_path / "log.jsonl"))
    monkeypatch.setenv("FAKE_SIGNED_OUT", "1")
    code, out = run(tmp_path, EVALS / "run_session.py", str(run_dir), "--client", client)
    assert code == 2 and "is not signed in" in out, out


def running(pid: int) -> bool:
    if os.name == "nt":
        listed = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, timeout=60)
        return str(pid) in listed.stdout
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def test_run_session_stops_the_case_and_the_client_tree_at_a_timeout(tmp_path: Path,
                                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    """A turn past --timeout ends the case: no later turn starts a session without the first one's, and the
    process the client started is stopped with it."""
    run_dir, client = session_run(tmp_path, "with_compact")
    monkeypatch.setenv("FAKE_LOG", str(tmp_path / "log.jsonl"))
    monkeypatch.setenv("FAKE_HANG", str(tmp_path / "child.pid"))
    code, out = run(tmp_path, EVALS / "run_session.py", str(run_dir), "--client", client, "--timeout", "3")
    assert code == 1 and "turn 1 timed out; the case stops" in out, out
    assert len((tmp_path / "log.jsonl").read_text(encoding="utf-8").splitlines()) == 1
    assert not running(int((tmp_path / "child.pid").read_text(encoding="utf-8")))


@pytest.mark.parametrize(("answer", "passed"), [
    ("Done: the coins worth 5 are 1.5x bigger, and everything checks out.", False),
    ("Done, but the check fails: On start of layout in Setup is inverted, which the editor refuses.", True),
    ("完成了，但检查没通过：Setup 里的 On start of layout 被取反了。", True)])
def test_a_project_that_fails_the_checker_is_not_handed_over_as_checked(tmp_path: Path, project: Path, answer: str,
                                                                          passed: bool) -> None:
    """The change written between the turns inverts On start of layout; an answer that says it all checks out
    fails the last assertion, one that names the failure passes it."""
    make_fixtures.seed_inverted_start(project)
    case = project_case(tmp_path, project, "keep-checking-after-compaction")
    (case / "outputs").mkdir()
    (case / "outputs" / "answer.md").write_text(answer, encoding="utf-8")
    grade_iteration(tmp_path)
    graded = read_json(case / "grading.json")["assertion_results"]
    handed = graded[len(CASES["keep-checking-after-compaction"]["assertions"]) - 1]
    assert graded[0]["passed"] is False and handed["passed"] is passed, handed


# --- the generator fixtures of the visual cases: the stand-in on other screens, and a level that scrolls ---------

@pytest.fixture(scope="session")
def generated(tmp_path_factory) -> Callable[[str], Path]:
    """The project a run on a fixture of make_fixtures.GENERATED starts from, built once per fixture: the
    template as the fixture changes it, run once with the skill installed."""
    built: dict[str, Path] = {}

    def build(name: str) -> Path:
        if name not in built:
            root = new_project(tmp_path_factory.mktemp(name))
            code, out = install(root)
            assert code == 0, out
            (root / "tools").mkdir()
            template = (SKILL / "assets" / "build_project.py").read_bytes().decode("utf-8")
            (root / "tools" / "build_project.py").write_bytes(make_fixtures.GENERATED[name](template).encode("utf-8"))
            code, out = run(root, "tools/build_project.py")
            assert code == 0 and out.splitlines()[-1].startswith("ok:"), out
            built[name] = root
        return built[name]
    return build


def generated_case(tmp_path: Path, generated: Callable[[str], Path], case: str) -> Path:
    """The with_skill run of case in the iteration tmp_path/it, its project a copy of the case's fixture as
    make_fixtures lays it out, with the fixture.json it writes."""
    run_dir = tmp_path / "it" / case / "with_skill"
    shutil.copytree(generated(CASES[case]["fixture"]), run_dir / "project")
    (run_dir / "fixture.json").write_text(json.dumps(make_fixtures.digest(run_dir / "project")), encoding="utf-8")
    return run_dir


def ui_instance(project: Path, kind: str, plugin: str, box: tuple, layer: str = "UI", **properties) -> None:
    """An instance of a new type kind, of plugin, with its top-left box (x, y, w, h), added to a layer of the
    Game layout."""
    (project / "objectTypes" / f"{kind}.json").write_text(json.dumps({"name": kind, "plugin-id": plugin}),
                                                          encoding="utf-8")
    path = project / "layouts" / "Game.json"
    layout = read_json(path)
    x, y, w, h = box
    next(lay for lay in layout["layers"] if lay["name"] == layer)["instances"].append(
        {"type": kind, "properties": properties, "world": {"x": x, "y": y, "width": w, "height": h,
                                                           "originX": 0, "originY": 0}})
    path.write_text(json.dumps(layout), encoding="utf-8")


def graded_by(run_dir: Path) -> dict:
    """The case's grader on the run: (passed, evidence) by assertion."""
    case = run_dir.parent.name
    results = grader.GRADERS[case](run_dir)
    assert len(results) == len(CASES[case]["assertions"])
    return dict(zip(CASES[case]["assertions"], results))


def by_words(results: dict, *words: str) -> tuple:
    return tuple(next(v for k, v in results.items() if word in k) for word in words)


def test_a_fixture_sets_a_setting_and_keeps_its_comment_and_line_ending() -> None:
    template = ('VIEW_W, VIEW_H = 1920, 1080\r\n'
                'ORIENTATION = "landscape"                  # "portrait", "landscape" or "any"\r\n')
    changed = make_fixtures.with_settings(template, VIEW="720, 1280", ORIENTATION='"portrait"').split("\r\n")
    assert changed[0] == "VIEW_W, VIEW_H = 720, 1280" and changed[-1] == ""
    assert changed[1].startswith('ORIENTATION = "portrait" ') and changed[1].index("#") == template.index("#") - 29


@pytest.mark.parametrize(("case", "settings", "screen"), [
    ("lay-out-the-hud-portrait", (720, 1280, 32, 32, 96), ("scale-outer", "trilinear")),
    ("lives-as-hearts-pixel", (320, 180, 8, 8, 24), ("integer-scale-outer", "nearest")),
    ("hud-over-a-scrolling-level", (1920, 1080, 32, 64, 160), ("scale-outer", "trilinear"))])
def test_a_generator_fixture_is_graded_by_its_own_screen(tmp_path: Path, generated: Callable, case: str,
                                                          settings: tuple, screen: tuple) -> None:
    """Each fixture's generator passes the checker, and the grader reads its viewport, unit, MARGIN and TOUCH from
    it. On the fixture as laid out the checker and the rerun pass, and what the run is asked to add is missing."""
    run_dir = generated_case(tmp_path, generated, case)
    got = grader.settings_of(run_dir / "project")
    assert tuple(got[k] for k in ("VIEW_W", "VIEW_H", "UNIT", "MARGIN", "TOUCH")) == settings and got["PALETTE"]
    props = read_json(run_dir / "project" / "project.c3proj")["properties"]
    assert (props["fullscreenMode"], props["sampling"]) == screen
    results = list(graded_by(run_dir).values())
    assert results[0][0] is True and results[-1][0] is True, results
    assert not all(ok for ok, _ in results)


def test_the_portrait_hud_takes_the_finger_of_its_own_screen(tmp_path: Path, generated: Callable) -> None:
    """At 720x1280 a finger is 96 px, a unit 32 and MARGIN 32: a 96 px pause button MARGIN inside the bottom-right
    corner passes, which the 160 px finger of 1920x1080 would refuse; 8 px further in, it is not held."""
    pytest.importorskip("PIL")
    from PIL import Image
    run_dir = generated_case(tmp_path, generated, "lay-out-the-hud-portrait")
    project = run_dir / "project"
    Image.new("RGBA", (96, 96), (33, 33, 33, 255)).save(project / "images" / "pausebutton-default-000.png")
    ui_instance(project, "PauseButton", "Sprite", (720 - 32 - 96, 1280 - 32 - 96, 96, 96))
    button, edges = by_words(graded_by(run_dir), "at least 96 px", "held against")
    assert button == (True, "button(s) ['PauseButton']; under 96 px: none") and edges[0] is True, edges
    layout = read_json(project / "layouts" / "Game.json")
    next(i for lay in layout["layers"] for i in lay["instances"] if i["type"] == "PauseButton")["world"]["x"] -= 8
    (project / "layouts" / "Game.json").write_text(json.dumps(layout), encoding="utf-8")
    assert by_words(graded_by(run_dir), "held against")[0][0] is False


def test_pixel_hearts_are_hard_edged_on_whole_pixels_in_a_nearest_project(tmp_path: Path, generated: Callable) -> None:
    """A heart of 8 x 8 px in the ink of PALETTE with clear corners passes; one with soft edges, or off whole
    pixels, does not; nor does the project once it samples other than Nearest."""
    pytest.importorskip("PIL")
    from PIL import Image
    run_dir = generated_case(tmp_path, generated, "lives-as-hearts-pixel")
    project = run_dir / "project"
    heart = Image.new("RGBA", (8, 8), (33, 33, 33, 255))
    heart.putpixel((0, 0), (0, 0, 0, 0))
    heart.save(project / "images" / "heart-default-000.png")
    ui_instance(project, "Heart", "Sprite", (136, 8, 8, 8))
    grid, drawn, scaled = by_words(graded_by(run_dir), "whole pixels", "is pixel art", "integer-scale-outer")
    assert grid[0] is True and drawn == (True, "1 image(s) of ['Heart']; not pixel art: none") and scaled[0] is True
    for x, alpha in ((1, 64), (2, 128), (3, 200)):
        heart.putpixel((x, 0), (33, 33, 33, alpha))
    heart.save(project / "images" / "heart-default-000.png")
    path = project / "project.c3proj"
    path.write_text(json.dumps(read_json(path) | {"properties": read_json(path)["properties"] | {"sampling": "trilinear"}}),
                    encoding="utf-8")
    drawn, scaled = by_words(graded_by(run_dir), "is pixel art", "integer-scale-outer")
    assert drawn[0] is False and "heart-default-000.png: alpha [64, 128, 200]" in drawn[1]
    assert scaled == (False, "fullscreenMode integer-scale-outer, sampling trilinear")


def scrolling_hud(project: Path, goal_layer: str = "UI", text: str = '"Goal " & round((Goal.X - Player.X) / 32)') -> None:
    """A health bar under the level tag and a goal label top centre, the label set every tick from text."""
    layout = read_json(project / "layouts" / "Game.json")
    tag = next(i for lay in layout["layers"] for i in lay["instances"] if i["type"] == "LevelTag")
    bottom = grader.box_of(tag)[3]
    ui_instance(project, "HpFrame", "NinePatch", (64, bottom + 32, 384, 32))
    ui_instance(project, "GoalText", "Text", (860, 64, 200, 48), goal_layer, text="Goal 170")
    path = project / "eventSheets" / "Game.json"
    sheet = read_json(path)
    sheet["events"].append({"eventType": "block", "conditions": [{"id": "every-tick", "objectClass": "System"}],
                            "actions": [{"id": "set-text", "objectClass": "GoalText", "parameters": {"text": text}}]})
    path.write_text(json.dumps(sheet), encoding="utf-8")


SCROLL_WORDS = ("parallax 0", "health bar", "says Goal", "Player.X", "no two overlap")


def test_a_hud_over_a_scrolling_level_stays_on_the_ui_layer(tmp_path: Path, generated: Callable) -> None:
    """A bar under the level tag MARGIN inside the left edge and a goal label top centre set from Player.X, both
    on the UI layer, pass; the label on the Game layer, which scrolls, fails."""
    run_dir = generated_case(tmp_path, generated, "hud-over-a-scrolling-level")
    scrolling_hud(run_dir / "project")
    results = graded_by(run_dir)
    assert by_words(results, "still scrolls")[0][0] is True
    assert all(ok for ok, _ in by_words(results, *SCROLL_WORDS)), by_words(results, *SCROLL_WORDS)
    other = generated_case(tmp_path / "other", generated, "hud-over-a-scrolling-level")
    scrolling_hud(other / "project", goal_layer="Game")
    layer, label = by_words(graded_by(other), "parallax 0", "says Goal")
    assert layer[0] is False and "added on a world layer: ['GoalText']" in layer[1] and label[0] is False


@pytest.mark.parametrize(("value", "passed"), [("left", True), ("score", False)])
def test_the_goal_label_may_read_player_x_through_a_variable(tmp_path: Path, generated: Callable, value: str,
                                                              passed: bool) -> None:
    """`left` set from Goal.X - Player.X and shown in the label counts as the player's position; the score does not."""
    run_dir = generated_case(tmp_path, generated, "hud-over-a-scrolling-level")
    project = run_dir / "project"
    scrolling_hud(project, text=f'"Goal " & {value}')
    path = project / "eventSheets" / "Game.json"
    sheet = read_json(path)
    sheet["events"].append({"eventType": "block", "conditions": [], "actions": [
        {"id": "set-eventvar-value", "objectClass": "System",
         "parameters": {"variable": "left", "value": "round((Goal.X - Player.X) / 32)"}}]})
    path.write_text(json.dumps(sheet), encoding="utf-8")
    assert by_words(graded_by(run_dir), "Player.X")[0][0] is passed


def test_make_fixtures_lays_out_the_generator_fixtures(tmp_path: Path) -> None:
    """Each visual case on another screen gets its fixture's generator, run once: the portrait viewport, the pixel
    one, the platformer's game below the helpers."""
    runs = tmp_path / "runs"
    cases = ("lay-out-the-hud-portrait", "lives-as-hearts-pixel", "hud-over-a-scrolling-level")
    code, out = run(tmp_path, EVALS / "make_fixtures.py", str(runs), "--cases", *cases, "--arms", "with_skill",
                    "--no-pin")
    assert code == 0, out
    tools = {case: (runs / case / "with_skill" / "project" / "tools" / "build_project.py").read_text(encoding="utf-8")
             for case in cases}
    assert "\nVIEW_W, VIEW_H = 720, 1280\n" in tools[cases[0]].replace("\r\n", "\n")
    assert "\nVIEW_W, VIEW_H = 320, 180\n" in tools[cases[1]].replace("\r\n", "\n")
    assert "def module_pickups()" in tools[cases[2]] and "def module_restart()" not in tools[cases[2]]
    assert read_json(runs / cases[2] / "with_skill" / "fixture.json")["objectTypes/LevelTag.json"]


# --- the cases of the checker's fixes: a sid and a name the editor refuses, a text at a boolean, two press() buttons

def seeded_case(tmp_path: Path, project: Path, case: str, seed: Callable[[Path], None]) -> Path:
    """The with_skill run of case on the stand-in with seed written into it, and the fixture.json of that seed."""
    seed(project)
    run_dir = tmp_path / "it" / case / "with_skill"
    shutil.copytree(project, run_dir / "project")
    (run_dir / "fixture.json").write_text(json.dumps(make_fixtures.digest(run_dir / "project")), encoding="utf-8")
    return run_dir


def actions_of(rows: list):
    for ev in rows:
        yield from ev.get("actions", [])
        yield from actions_of(ev.get("children", []))


def give_spark_a_sid(project: Path) -> None:
    edit_file(project / "objectTypes" / "Spark.json", lambda t: t.update(sid=677777777777701))


def rename_z(project: Path) -> None:
    """Spark's z renamed rise, in its type and in every action that sets or reads it."""
    edit_file(project / "objectTypes" / "Spark.json", lambda t: t["instanceVariables"][0].update(name="rise"))

    def change(sheet: dict) -> None:
        for a in actions_of(sheet["events"]):
            given = a.get("parameters")
            if isinstance(given, dict):
                if a.get("objectClass") == "Spark" and given.get("instance-variable") == "z":
                    given["instance-variable"] = "rise"
                given.update({k: v.replace("Spark.z", "Spark.rise") for k, v in given.items() if isinstance(v, str)})
    edit_file(project / SHEET, change)


def edit_file(path: Path, change: Callable[[dict], object]) -> None:
    data = read_json(path)
    change(data)
    path.write_text(json.dumps(data, indent="\t"), encoding="utf-8")


@pytest.mark.parametrize(("fixes", "passed"), [
    ((), [False, False, False, True, True]),
    # The fix the editor's message asks for: its next open stops on z
    ((give_spark_a_sid,), [False, True, False, True, True]),
    ((give_spark_a_sid, rename_z), [True, True, True, True, True]),
])
def test_the_spark_case_needs_both_its_mistakes_fixed(tmp_path: Path, project: Path, fixes: tuple, passed: list) -> None:
    """The spark copied from Coin's JSON shares Coin's sid, which the editor names, and has an instance variable z,
    which every Sprite has as an expression whether a layout holds one or not."""
    run_dir = seeded_case(tmp_path, project, "fix-open-errors-past-the-message", make_fixtures.seed_name_collision)
    for fix in fixes:
        fix(run_dir / "project")
    assert [ok for ok, _ in graded_by(run_dir).values()] == passed, graded_by(run_dir)


@pytest.mark.parametrize(("value", "passed"), [("0", [False, False, False, True]), ("false", [False, False, False, True]),
                                               (False, [True, True, True, True])])
def test_the_pulse_case_wants_the_json_false_on_a_collect(tmp_path: Path, project: Path, value, passed: list) -> None:
    """AddScore passes the text "0" to Pulse's boolean looping, which reads as true; "false" reads as true too, and the
    JSON false is the fix. The round's end keeps its JSON true."""
    run_dir = seeded_case(tmp_path, project, "fix-endless-pulse", make_fixtures.seed_loop_flag)

    def change(sheet: dict) -> None:
        for a in actions_of(sheet["events"]):
            if a.get("callFunction") == "Pulse" and a["parameters"] == ["0"]:
                a["parameters"] = [value]
    edit_file(run_dir / "project" / SHEET, change)
    assert [ok for ok, _ in graded_by(run_dir).values()] == passed, graded_by(run_dir)


REPORT_ANSWERS = Path(__file__).parent / "fixtures" / "report_answers"


@pytest.mark.parametrize(("answer", "passed"), [
    # The prose to the user may name Goblin and Orc; only the code block is the report
    ("two_roles.md", [True, True, True]),
    # Enemy for both: the two actions no longer tell Goblin's object from Orc's
    ("one_role.md", [False, True, True]),
    ("keeps_a_name.md", [False, True, True]),
    ("drops_a_line.md", [True, False, True]),
    # The answers of the runs of iteration 78. One block quotes "text " + Enemy.IID and Enemy2.IID
    ("recorded_two_roles.md", [True, True, True]),
    # It names the replacement Enemy2 in its prose, but its report quotes one action, so Orc's is not in it
    ("recorded_one_action.md", [False, True, True]),
    # No code block: the whole answer is the report, and it quotes the sheet lines with Goblin and Orc
    ("recorded_no_block.md", [False, False, True]),
    # The issue body is prose that quotes Goblin.IID; its blocks are the editor's dialog and the editor
    # script's own report, neither in the template
    ("recorded_body_outside_the_block.md", [False, True, True]),
])
def test_the_report_numbers_two_enemies_and_quotes_the_editor(tmp_path: Path, project: Path, answer: str,
                                                             passed: list) -> None:
    shutil.rmtree(project / "tools")     # as make_fixtures.stand_in() leaves the game, so nothing differs
    run_dir = seeded_case(tmp_path, project, "report-two-enemies", make_fixtures.seed_two_enemies)
    (run_dir / "outputs").mkdir()
    shutil.copy(REPORT_ANSWERS / answer, run_dir / "outputs" / "answer.md")
    assert [ok for ok, _ in graded_by(run_dir).values()] == passed, graded_by(run_dir)


@pytest.mark.parametrize("join", ["&", "+"])
def test_the_checker_passes_the_two_enemies_before_and_after_the_fix(project: Path, join: str) -> None:
    """The fixture joins the labels with &. The prompt quotes the editor refusing the + of the session before,
    which the checker let through: once the checker reports it, the case no longer asks for a report of a miss."""
    make_fixtures.seed_two_enemies(project, join=join)
    code, out = grader.checker(project)
    assert code == 0, out


BUTTON_ANSWERS = Path(__file__).parent / "fixtures" / "button_answers"


@pytest.mark.parametrize(("answer", "passed"), [
    (None, [True, True, False, True]),
    ("press_each_button.py", [True, True, True, True]),
    # The same buttons with one On any touch end and a sub-event per button, as the earlier checker's warning advised
    ("merge_the_touch_ends.py", [True, True, False, True]),
])
def test_two_buttons_are_each_pressed_by_press(tmp_path: Path, generated: Callable, answer: str | None,
                                               passed: list) -> None:
    """Two buttons that press() writes each have their own On any touch end testing their own pressed: the checker
    passes them without a warning, and the generator rerun gives the same layout."""
    run_dir = generated_case(tmp_path, generated, "two-buttons-in-the-generator")
    if answer:
        source = run_dir / "project" / "tools" / "build_project.py"
        text = source.read_text(encoding="utf-8")
        end = text.index("\n", text.index(make_fixtures.END_MARKER)) + 1
        source.write_text(text[:end] + "\n\n" + (BUTTON_ANSWERS / answer).read_text(encoding="utf-8"), encoding="utf-8")
        code, out = run(run_dir / "project", "tools/build_project.py")
        assert code == 0 and out.splitlines()[-1].startswith("ok:"), out
    assert [ok for ok, _ in graded_by(run_dir).values()] == passed, graded_by(run_dir)


def test_make_fixtures_lays_out_the_checker_fix_seeds(tmp_path: Path) -> None:
    """The spark and the pulse are seeded into the stand-in; the fixture records the checker's warning on the
    spark that no layout holds, which a run is not charged for."""
    runs = tmp_path / "runs"
    code, out = run(tmp_path, EVALS / "make_fixtures.py", str(runs), "--cases", "fix-open-errors-past-the-message",
                    "fix-endless-pulse", "--arms", "with_skill", "--no-pin")
    assert code == 0, out
    spark = read_json(runs / "fix-open-errors-past-the-message" / "with_skill" / "project" / "objectTypes" / "Spark.json")
    coin = read_json(runs / "fix-open-errors-past-the-message" / "with_skill" / "project" / "objectTypes" / "Coin.json")
    assert spark["sid"] == coin["sid"] and [v["name"] for v in spark["instanceVariables"]] == ["z"]
    warned = read_json(runs / "fix-open-errors-past-the-message" / "with_skill" / "fixture.json")["check_project.warnings"]
    assert [w for w in warned if w.startswith("warning: Spark is created at runtime")], warned
    sheet = read_json(runs / "fix-endless-pulse" / "with_skill" / "project" / SHEET)
    assert sorted(json.dumps(a["parameters"]) for a in actions_of(sheet["events"])
                  if a.get("callFunction") == "Pulse") == ['["0"]', "[true]"]
