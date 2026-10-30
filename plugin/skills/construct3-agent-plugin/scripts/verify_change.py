"""Run the checks of a change in their order, and end on the one thing to do next.

    python scripts/verify_change.py [--project FOLDER] [--style] [--upto STEP] [--answered] [--status]
                                    [--browser EXE] [--limit CHARS]

The steps, by the words a hand-over names them with:

  checked    check_project.py, every file against the schemas and the editor's load rules
  reviewed   review_design.py, the design of the sheets: findings, and questions to answer
  opened     open_in_editor.py --preview opened the project in the editor
  previewed  and its preview ran the start layout without an error
  played     preview_project.py --all, the kept plans of tools/plans/, and play_design.py
             tools/design.json; with neither, the step does not run and does not stop the others
  looked     review_look.py, a screenshot of every layout: findings, and questions to answer

It runs them in order and stops at the first that finds something, asks
something or cannot run, and its last line says what to do next. A step that
opens the editor is run again only when a file of the project changed since
it passed: the record, .tmp/scripts/verify-change/result.json, keeps each step's outcome with
a digest of every file of the project outside its dot folders and
tools/plans/. The play step also runs again when a kept plan changed. The
checker and the design review always run, because they take seconds.

A question is answered for the files it was asked about. Have the design
questions it printed answered, through the brief of review_design.py, then run
it with --answered, which records them. The look
questions pass on a reply that review_look.py --reply checked against the brief
of the run that asked them: one that answers every question, each yes saying
where. A change to the project asks them again, as it reruns the checks;
keeping a plan does not. --status runs nothing and
prints each step's outcome on the files as they are now. The steps run with
CONSTRUCT3_RAG set to the clone and CONSTRUCT3_RAG_IN_VERIFY=1, under which
the checker's ok: line names no next step.

exit codes: 0 every step up to --upto passed on these files, or --status; 1 a step found something or asked
questions; 2 the project, the clone or the editor could not be used; 3 a step did not run, as with no browser
here: its line names the steps that did not run and the last that passed; 5 another run holds the browser
profile
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# python -I leaves this script's folder off sys.path, and the modules beside it are imported from there
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import c3project as c3
import open_in_editor as oe

STEPS = ("checked", "reviewed", "opened", "previewed", "played", "looked")
EDITOR_STEPS = ("opened", "previewed", "played", "looked")      # rerun only when the files changed
RECORD = c3.VERIFY_RECORD
PLANS = Path("tools") / "plans"
# Where review_look.py writes its result by default.
LOOK_RESULT = c3.script_folder(Path(), "review-look") / "result.json"
LOOK_ROUNDS = 3              # replies with a yes before the look step passes with the yes left for the hand-over
DESIGN = Path("tools") / "design.json"
QUESTION = re.compile(r"^\s+\d+\.\s+(.*\S)")
SCRIPT_OF = {"checked": "check_project.py", "reviewed": "review_design.py", "opened": "open_in_editor.py",
             "previewed": "open_in_editor.py", "played": "preview_project.py", "looked": "review_look.py"}
EPILOG = """examples:
  python scripts/verify_change.py
  python scripts/verify_change.py --answered
  python scripts/verify_change.py --upto reviewed       # the files alone, without the editor
  python scripts/verify_change.py --status

output, one line per step it ran or found passed, the output of the step that stopped it, then next:
  checked   passed: ok: 10 object types, 0 families, 2 layouts, 1 sheets, ...
  reviewed  passed: design: 0 findings on 0 of 1 sheets; 2 questions answered earlier
  opened    passed: on these files, earlier
  previewed passed: on these files, earlier
  played    not run: no kept plan in tools/plans/ and no tools/design.json
  looked    asked: look: 0 findings on 2 layouts, 0 runtime errors; 7 questions
  ...
  next: <the one thing to do>
the last line on a pass: ok: and the steps that did not run; with a step that did not run: skipped:

exit codes: 0 passed, or --status; 1 findings or questions; 2 the project, the clone or the editor could not be
used; 3 a step did not run; 5 another run holds the browser profile"""


def digest(files) -> str:
    h = hashlib.sha256()
    for f, rel in files:
        h.update(rel.as_posix().encode("utf-8") + b"\0" + f.read_bytes())
    return h.hexdigest()[:16]


def files_digest(root: Path) -> str:
    """Every file of the project outside its dot folders (.tmp, .git, the skill's copy) and its kept plans: what
    the steps read, images and scripts included, which the checker's own digest leaves out."""
    # A kept plan changes nothing the game runs, and the play step asks for one in the run that asks the design and
    # look questions: a plan in this digest would void every answer recorded before it
    return digest((f, rel) for f in sorted(root.rglob("*")) for rel in [f.relative_to(root)]
                  if f.is_file() and not any(part.startswith(".") for part in rel.parts)
                  and "__pycache__" not in rel.parts and not rel.is_relative_to(PLANS))


def plans_digest(root: Path) -> str:
    """The kept plans, which the play step plays."""
    return digest((f, f.relative_to(root)) for f in sorted((root / PLANS).rglob("*")) if f.is_file())


def last_line(out: str) -> str:
    lines = [line for line in out.splitlines() if line.strip()]
    return lines[-1].strip() if lines else ""


def without_next(out: str) -> str:
    """A step's output without its next: lines, for a step whose next step this script says."""
    return "\n".join(line for line in out.splitlines() if not line.startswith("next:"))


def questions_of(out: str) -> list[str]:
    """The numbered questions under a questions: line, by their text."""
    asked, inside = [], False
    for line in out.splitlines():
        if line.startswith(("questions:", "  questions:")):
            inside = True
        elif inside and QUESTION.match(line):
            asked.append(QUESTION.match(line).group(1))
        elif inside and not line.startswith(" "):
            inside = False
    return asked


class Run:
    """One run of the steps on one project: the record, the digest of the files, how the scripts are called."""

    def __init__(self, project: c3.Project, args) -> None:
        self.root, self.args = project.root, args
        self.path = self.root / RECORD
        try:
            self.record = json.loads(self.path.read_text(encoding="utf-8"))
            assert isinstance(self.record.get("steps"), dict)
        except (OSError, ValueError, AssertionError, AttributeError):
            self.record = {"steps": {}, "pending": [], "answered": []}
        self.digest, self.plans = files_digest(self.root), plans_digest(self.root)
        self.env = dict(os.environ, CONSTRUCT3_RAG=str(project.rag), **{c3.IN_VERIFY: "1", oe.SHARED: str(self.root)},
                        PYTHONIOENCODING="utf-8")
        self.style = args.style or (self.root / c3.GENERATOR).is_file()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not (self.root / c3.SCRATCH / ".gitignore").exists():
            (self.root / c3.SCRATCH / ".gitignore").write_text("*\n", encoding="utf-8")
        self.path.write_text(json.dumps(self.record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    def script(self, name: str, *extra: str) -> tuple[int, str]:
        """A script of this folder on the project, its exit code and its output, stdout then stderr."""
        limit = max(self.args.limit - 1500, 2000) if self.args.limit else 0
        command = [sys.executable, str(Path(__file__).with_name(name)), "--project", str(self.root),
                   "--limit", str(limit), *extra]
        p = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=self.env, cwd=self.root)
        return p.returncode, (p.stdout + p.stderr).strip()

    def browser(self) -> list[str]:
        return ["--browser", self.args.browser] if self.args.browser else []

    def keep(self, step: str, state: str, line: str, code: int | None = None) -> None:
        self.record["steps"][step] = {"state": state, "digest": self.digest, "plans": self.plans, "exit": code,
                                      "line": line[:400]}

    def on_these_files(self, step: str, kept: dict) -> bool:
        """Whether a kept outcome is of the files as they are now, the play step's of the kept plans too."""
        return kept.get("digest") == self.digest and (step != "played" or kept.get("plans") == self.plans)

    def passed_here(self, step: str) -> bool:
        kept = self.record["steps"].get(step) or {}
        return kept.get("state") == "passed" and self.on_these_files(step, kept)

    def key(self, step: str, question: str) -> str:
        return f"{step}: {question} @{self.digest}"

    def unanswered(self, step: str, asked: list[str]) -> list[str]:
        return [q for q in asked if self.key(step, q) not in self.record["answered"]]


# --- the steps: each returns the exit code of this script and the next: line, or None to go on ----------------
def show(step: str, state: str, line: str) -> None:
    print(f"{step:<9} {state}: {line}", flush=True)


def stopped(run: Run, step: str, code: int, out: str, next_line: str, state: str = "failed") -> tuple[int, str]:
    run.keep(step, state, last_line(out), code)
    show(step, state, last_line(out))
    print(out.rstrip().removesuffix(last_line(out)).rstrip(), flush=True)      # its last line heads it
    return (1 if state in ("failed", "asked") else code), next_line


def again(run: Run) -> str:
    return c3.script_command(run.root, "verify_change.py")


def could_not(run: Run, step: str, name: str, code: int, out: str) -> tuple[int, str]:
    """A step that did not run: no browser here (exit 3), the editor or the project unusable (2), or the browser
    profile held by another run (5)."""
    if code == 3:
        run.keep(step, "skipped", last_line(out), code)
        return code, skipped(run, step, out)
    run.keep(step, "not run", last_line(out), code)
    show(step, "not run", last_line(out))
    print(out, flush=True)
    return code, f"stopped: {name} could not run, as its line above says; do what it says, then run {again(run)}"


def checked(run: Run) -> tuple[int, str] | None:
    code, out = run.script("check_project.py", "--locale", run.args.locale, *(["--style"] if run.style else []))
    line = last_line(out)
    if code == 0 and line.startswith("ok:"):
        run.keep("checked", "passed", line, code)
        show("checked", "passed", line)
        return None
    if code == 2 or not re.search(r"^\d+ problem\(s\)$|^stop: ", out, re.M):
        return stopped(run, "checked", 2, out, f"stopped: check_project.py could not check the project; do what "
                                                f"its line above says, then run {again(run)}", "not run")
    stop = "stop: " in out
    return stopped(run, "checked", code, out, (
        "next: fix every finding above in one plan of edit_sheet.py, each names its place and what to write"
        + ("; do not change a place a stop: line names again: tell the user that finding as the line says, and "
           "hand over with it once the others are fixed" if stop else "")
        + f"; then run {again(run)}"))


def reviewed(run: Run) -> tuple[int, str] | None:
    code, out = run.script("review_design.py", "--locale", run.args.locale)
    out = without_next(out)
    summary = next((line for line in out.splitlines() if line.startswith("design: ")), last_line(out))
    if code:
        return stopped(run, "reviewed", 2 if code == 2 else 1, out,
                       f"stopped: review_design.py could not review the sheets; do what its line above says, "
                       f"then run {again(run)}", "not run")
    found = int(m.group(1)) if (m := re.match(r"design: (\d+) finding", summary)) else 0
    open_ = run.unanswered("reviewed", questions_of(out))
    run.record["pending"] = [run.key("reviewed", q) for q in open_]
    if not found and not open_:
        answered = len(questions_of(out))
        line = summary + (f"; {answered} question{'s' if answered != 1 else ''} answered earlier" if answered else "")
        run.keep("reviewed", "passed", line, code)
        show("reviewed", "passed", line)
        return None
    todo = []
    if found:
        todo.append(f"fix the {found} finding line{'s' if found != 1 else ''} above in one plan of edit_sheet.py, "
                    f"each names the event and what to write; a finding the user asked for on purpose stays, and "
                    f"the hand-over says why")
    if open_:
        todo.append(f"have the {len(open_)} question{'s' if len(open_) != 1 else ''} above answered yes or no as "
                    f"the brief: line above says; change what was answered yes about the events and globals your "
                    f"change wrote, and name a yes about any other in the hand-over")
    flag = " --answered" if open_ else ""
    return stopped(run, "reviewed", 1, out, f"next: {'; '.join(todo)}; then run {again(run)}{flag}",
                   "failed" if found else "asked")


def opened(run: Run) -> tuple[int, str] | None:
    """open_in_editor.py --preview: opened and previewed, which one run of it decides."""
    if run.passed_here("opened") and run.passed_here("previewed"):
        for step in ("opened", "previewed"):
            show(step, "passed", "on these files, earlier")
        return None
    code, out = run.script("open_in_editor.py", "--preview", *run.browser())
    line = last_line(out)
    shots = sorted((c3.script_folder(run.root, "open-in-editor") / "shots").glob("*.png"),
                   key=lambda f: f.stat().st_mtime)
    shot = (f"\n          screenshot {c3.shown_path(shots[-1])}: show it to the user, since the editor runs headless "
            f"and they saw no window") if shots else ""
    if code == 0:
        for step in ("opened", "previewed"):
            run.keep(step, "passed", line, code)
        show("opened", "passed", next((x.strip() for x in out.splitlines() if x.startswith("opened")), line))
        show("previewed", "passed", next((x.strip() for x in out.splitlines() if x.strip().startswith("preview:")),
                                         line) + shot)
        return None
    if code in (2, 3, 5):
        run.keep("previewed", "skipped" if code == 3 else "not run", line, code)
        return could_not(run, "opened", "open_in_editor.py", code, out)
    was_opened = bool(re.search(r"^opened\s", out, re.M))
    if was_opened:
        run.keep("opened", "passed", line, code)
        show("opened", "passed", next(x.strip() for x in out.splitlines() if x.startswith("opened")))
    if shot:
        print(shot.strip(), flush=True)
    return stopped(run, "previewed" if was_opened else "opened", code, out,
                   f"next: fix what open_in_editor.py names above, as its next: line says, then run {again(run)}, "
                   f"which runs the checker and this step again")


def played(run: Run) -> tuple[int, str] | None:
    plans, design = sorted((run.root / PLANS).glob("*.json")), run.root / DESIGN
    if not plans and not design.is_file():
        run.keep("played", "not run", f"no kept plan in {PLANS.as_posix()}/ and no {DESIGN.as_posix()}")
        show("played", "not run", f"no kept plan in {PLANS.as_posix()}/ and no {DESIGN.as_posix()}: write a "
                                  f"plan that does what the change does "
                                  f"(references/verifying-a-change.md; references/editor-and-preview.md for one that "
                                  f"starts on another layout), play it with "
                                  f"{c3.script_command(run.root, 'preview_project.py', ' PLAN.json --keep NAME')}, "
                                  f"then run this again")
        return None
    if run.passed_here("played"):
        show("played", "passed", "on these files, earlier")
        return None
    runs = ([("preview_project.py", ["--all"])] if plans else []) + (
        [("play_design.py", [DESIGN.as_posix()])] if design.is_file() else [])
    outs = []
    for name, extra in runs:
        code, out = run.script(name, *extra, *run.browser())
        outs.append(out)
        if code in (2, 3, 5):
            return could_not(run, "played", name, code, out)
        if code:
            return stopped(run, "played", code, out, f"next: fix what {name} names above, as its next: line says, "
                                                     f"then run {again(run)}, which plays it again")
    line = "; ".join(last_line(out) for out in outs)
    run.keep("played", "passed", line, 0)
    show("played", "passed", line)
    return None


def look_result(run: Run) -> dict:
    """The result of the last run of review_look.py on the project, with the verdict of the reply checked
    against its brief; {} without one."""
    try:
        result = json.loads((run.root / LOOK_RESULT).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return result if isinstance(result, dict) else {}


def looked(run: Run) -> tuple[int, str] | None:
    if run.passed_here("looked"):
        show("looked", "passed", "on these files, earlier")
        return None
    # The look questions pass on a reply that review_look.py --reply checked against the brief of the run that
    # asked them, on the same files; --answered records the design questions alone
    kept, result = run.record["steps"].get("looked") or {}, look_result(run)
    reply = result.get("reply") or {}
    if kept.get("state") == "asked" and run.on_these_files("looked", kept) and kept.get("run") \
            and result.get("run") == kept["run"] and reply.get("complete"):
        # A yes is a fault to fix and look at again; the rounds count the replies with a yes, across file changes
        rounds = run.record.get("look_rounds", 0) + bool(reply.get("yes"))
        if not reply.get("yes") or rounds >= LOOK_ROUNDS:
            run.record["look_rounds"] = 0
            run.record["look_left"] = reply.get("yeses", []) if reply.get("yes") else []
            # A yes from before passes
            run.record["look_before"] = reply.get("before", [])
            from_before = len(run.record["look_before"])
            line = (f"look: {reply['file']} answers every question" + (
                f" and still has {reply['yes']} yes after {rounds} rounds: name each in the hand-over"
                if reply.get("yes") else f" with no new yes; name the {from_before} yes from before in the hand-over"
                if from_before else " no"))
            run.keep("looked", "passed", line, 0)
            show("looked", "passed", line)
            for left in run.record["look_left"]:
                print(f"  left: {left}")
            for left in run.record["look_before"]:
                print(f"  from before: {left}")
            return None
        run.record["look_rounds"] = rounds
        line = f"look: {reply['file']} has {reply['yes']} yes, round {rounds} of {LOOK_ROUNDS}"
        run.keep("looked", "failed", line, 1)
        show("looked", "failed", line)
        return 1, (f"next: fix each yes that review_look.py --reply printed, in the generator or the drawings, then run "
                   f"{again(run)}, which looks again")
    if (run.root / c3.GENERATOR).is_file():
        code, out = run.script("check_look.py")
        if code:
            return stopped(run, "looked", code, out, f"next: fix every line above in tools/build_project.py, run it, "
                                                     f"then run {again(run)}")
    code, out = run.script("review_look.py", *run.browser())
    if code in (2, 3, 5):
        return could_not(run, "looked", "review_look.py", code, out)
    told = next((line for line in out.splitlines() if line.startswith("next:")), "")
    shown = without_next(out)
    summary = next((line for line in shown.splitlines() if line.startswith("look: ")), last_line(shown))
    if code == 0 and not questions_of(shown):
        run.keep("looked", "passed", summary, code)
        show("looked", "passed", summary)
        return None
    how = told.removeprefix("next: ").rstrip(".")
    ended = stopped(run, "looked", code or 1, shown,
                    f"next: {how}; then run {again(run)}" if how else
                    f"next: fix every finding above and have the questions answered as the brief: line says, then "
                    f"run {again(run)}", "failed" if code else "asked")
    run.record["steps"]["looked"]["run"] = look_result(run).get("run")
    return ended


def skipped(run: Run, step: str, out: str) -> str:
    show(step, "skipped", last_line(out))
    print(out, flush=True)
    done = [s for s in STEPS if run.passed_here(s)]
    left = [s for s in STEPS[STEPS.index(step):] if s not in done]
    return (f"skipped: {', '.join(left)} did not run: {last_line(out)}. "
            + (f"The last step that passed on these files is {done[-1]}; run this again once the step can run"
               if done else "Nothing passed on these files"))


RUNNERS = (("checked", checked), ("reviewed", reviewed), ("opened", opened), ("played", played), ("looked", looked))


def look_warnings(run: Run) -> list[str]:
    """What the look step leaves for the hand-over once it passed: each yes still there after its rounds, each yes
    the screen showed before the change, and the fragile findings of the review it passed on, which warn and do not
    stop it."""
    if not run.passed_here("looked"):
        return []
    layouts = (look_result(run).get("preview") or {}).get("layouts", [])
    fragile = [f"{d['layout']}: {f['rule']}" for d in layouts for f in d.get("findings", []) if f.get("tier") == "fragile"]
    return ([f"look yes {y}" for y in run.record.get("look_left", [])]
            + [f"look yes from before {y}" for y in run.record.get("look_before", [])]
            + [f"warns {w}" for w in fragile])


def handed_over(run: Run, upto: str) -> str:
    """The ok: line: the last step that passed on these files, the steps that did not run on them, and what the
    look left to name."""
    done = [s for s in STEPS[:STEPS.index(upto) + 1] if run.passed_here(s)]
    left = [s for s in STEPS if not run.passed_here(s)]
    named = look_warnings(run)
    return (f"ok: {done[-1]} on these files"
            + (f"; not run: {', '.join(left)}" if left else "")
            + (f"; name in the hand-over, each fix in three parts, before, after and why: {'; '.join(named)}"
               if named else "")
            + f". Hand over with the events that changed: "
            + c3.script_command(run.root, "print_sheet.py", " --since <the user's branch>")
            + "; pack a project handed over as a file with pack_project.py")


def status(run: Run) -> int:
    for step in STEPS:
        kept = run.record["steps"].get(step)
        if not kept:
            show(step, "not run", "no run recorded")
            continue
        here = "on these files" if run.on_these_files(step, kept) else "on files changed since"
        show(step, kept["state"], f"{here}; {kept.get('line', '')}")
    done = [s for s in STEPS if run.passed_here(s)]
    no_play = (run.record["steps"].get("played") or {}).get("state") == "not run"
    if all(run.passed_here(s) or s == "played" and no_play for s in STEPS):
        print(handed_over(run, "looked"))
    else:
        print(f"status: {'the last step that passed on these files is ' + done[-1] if done else 'no step passed on these files'}; "
              f"run {again(run)} to go on")
    return 0


def main() -> int:
    ap = c3.argument_parser(
        "Run the checks of a change in order: the checker, the design review, the editor and its preview, the kept "
        "plays and the look. A step that opens the editor runs again only when a file changed since it passed. It "
        "stops at the first step that finds something or asks something, and its last line says what to do next.",
        EPILOG)
    ap.add_argument("--style", action="store_true",
                    help="pass --style to the checker; on by itself when tools/build_project.py generates the project")
    ap.add_argument("--upto", choices=STEPS, default="looked", metavar="STEP",
                    help=f"stop after this step, one of {', '.join(STEPS)} (default: looked)")
    ap.add_argument("--answered", action="store_true",
                    help="the questions the last run printed are answered: record them, then run the steps")
    ap.add_argument("--status", action="store_true", help="run nothing; print each step's outcome on these files")
    ap.add_argument("--browser", metavar="EXE", help="the Chromium-based browser the editor steps start")
    args = ap.parse_args()
    c3.utf8_output()
    findings = c3.Findings()
    c3.stop_with_a_sentence("verify_change.py", findings)
    run = Run(c3.Project.open(args, findings), args)
    if args.status:
        return status(run)
    if args.answered:
        pending = run.record.get("pending") or []
        # An answer about files that have changed since is asked again, so only these files' answers are kept
        here = {a for a in run.record.get("answered") or [] if a.endswith(f" @{run.digest}")}
        run.record["answered"] = sorted(here | set(pending))
        run.record["pending"] = []
        print(f"answered: {len(pending)} question{'s' if len(pending) != 1 else ''} recorded"
              if pending else "answered: no question was waiting for an answer", flush=True)
    try:
        for name, step in RUNNERS:
            if STEPS.index(name) > STEPS.index(args.upto):
                break
            ended = step(run)
            if ended:
                run.save()
                code, line = ended
                print(line)
                return code
    finally:
        # The editor steps leave the browser running for each other
        exe = args.browser or oe.browser_path()
        if exe:
            oe.close_shared(exe, oe.profile_folder(None, run.root, exe))
    run.save()
    print(handed_over(run, args.upto))
    return 0


if __name__ == "__main__":
    sys.exit(main())
