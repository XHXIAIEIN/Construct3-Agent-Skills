"""Grade the runs of one eval iteration and aggregate them.

    python evals/grade.py ITERATION_DIR [--play] [--release rNNN] [--browser EXE] [--show-held-out]

ITERATION_DIR holds <case>/<arm>/ with project/, outputs/answer.md,
fixture.json and, once the run has reported, timing.json. Every assertion of
evals/evals.json is checked by code against the files the run left, with the
clone's own checker, and written to <case>/<arm>/grading.json with the
evidence and its level: checker or files. A run of an old_ arm installed
the older skill, so the checker's warning that the project's Construct 3
block is older than the skill's is left out of its output, and nothing
else is. A case whose request changes what
the game does also has the runtime assertions of its plan in
evals/play_cases.py. --play plays the plan on the run's project in the
editor's preview, into <case>/<arm>/play/. Without --play, grade.py reads a
play/result.json that the run already has. Runtime assertions that were not
played are listed with passed null and left out of the scores.
level_reached is the highest level up to which every scored assertion
passed.

benchmark.json gives, per case and arm, the mean of every measure and its
deviation once a cell has more than one run (<arm>_2, <arm>_3 are further
runs of <arm>), the runs that passed every assertion with a Wilson 95%
interval, and with_skill less each other arm. A run with a trace.json
(evals/trace.py --out) adds its tool calls, the ones it lost, its turns and
output tokens, and the route columns of its transcript: read_skill_md,
chain_depth, chain_attempts, preview_failed, help_reads, repeat_help,
plan_refusals, hand_edits, lookups_before_first_edit, data_reads,
other_clone_reads, entry_chars, printed_command_failures, print_sheet_chars,
whole_sheet_prints, cookbook_reads, pointers_printed, pointer_follows,
read_design_guide, cookbook_misses, checked_after_last_edit and, for a run
compacted between its turns (run_session.py), compactions,
reread_skill_md_after_compaction, chain_depth_after_compaction and
lookups_after_compaction, averaged like the cost columns; first_script,
chain_end, chain_reached and compaction_skill are counted per cell. Time
comes from timing.json, else from the trace; tokens come from timing.json. A
case marked held_out in evals.json is reported separately, under held_out,
and its failed assertions are printed only with --show-held-out.

An iteration decides on one column chosen before its runs: decision.json
in ITERATION_DIR holds {"cases": [...], "metric": "chain_depth",
"direction": "up", "n_per_cell": 3, "guards": {"pass_rate": "not down"},
"concurrency": 3, "arms": ["with_skill", "old_skill"]} (arms optional,
"alpha" optional, 0.05). grade.py compares the arms on the metric with the
within-task permutation test of evals/compare.py, checks each guard on the
means (not down: the first arm's is not lower; not up: not higher), prints
the verdict and writes it to benchmark.json under decision. A cell with
fewer scored runs than n_per_cell makes the verdict "underpowered: k of n"
and the benchmark is aggregated all the same; so does a decision.json that
is not JSON or lacks a key, with the verdict "not read" and the reason.

A run that did not keep to its arm is not scored: put the reason in
<case>/<arm>/void.txt, for example a baseline whose answer lists a script of
this skill among its commands. A run whose trace.json lists a write outside
its folder is not scored either, with the paths as the reason; nor is one
that read how it is graded: a dev/evals or dev/tests folder of any clone, or
another run's folder of this iteration. Both lists are a floor
(evals/trace.py).

benchmark.json lists under case_flags the cases that tell the arms apart no
more: saturated, where two or more arms ran and every run passed every
assertion, and none_passed, where no run did, whose runs are read before the
case is trusted. A run without timing.json has no tokens in the
benchmark, and no time unless its trace has one; nothing is estimated.

A scored run that lacks its outputs/answer.md, its trace.json, its
timing.json or the play of its plan is listed under incomplete_runs with
what it lacks, and coverage_complete is then false: its scores are counted
but do not stand. A decision over such a run gives the verdict
"incomplete". benchmark.json also holds meta, what the grading ran with:
the commits of this checkout and of the Construct3-RAG data, with whether
the files the grader reads differ from them, the flags, and the iteration's
clone.json. Grading reads only the files the runs left, so a run is graded
again, with another grader or --play, without running it again.

exit codes: 0 graded, 1 ITERATION_DIR holds no run of a known case
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import compare
import play_cases

REPO = Path(__file__).resolve().parents[2]
SKILL = REPO / "plugin" / "skills" / "construct3-agent-plugin"
sys.path.insert(0, str(SKILL / "scripts"))
import c3project as c3              # noqa: E402
# The scripts get plugin/ as the clone, which holds the skill and the built data; the raw data
# files are in the Construct3-RAG clone beside this one (docs/decisions/plugin-repository.md)
PLUGIN = REPO / "plugin"
DATA = c3.siblings_folder(REPO) / "Construct3-RAG" / "data"
CASES = {c["name"]: c for c in json.loads((Path(__file__).parent / "evals.json").read_text(encoding="utf-8"))["evals"]}
ORIGINAL_GLOBALS = {"score", "COIN_COUNT", "ROUND_COINS", "beat"}   # the stand-in's, before and after BEATS
SIZE_ACTIONS = {"set-size", "set-scale", "set-width", "set-height"}
TWEEN_ENDS = {"on-tweens-finished", "on-any-tweens-finished"}
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
COMPARE = {0: lambda a, b: a == b, 1: lambda a, b: a != b, 2: lambda a, b: a < b,      # the cmp parameter
           3: lambda a, b: a <= b, 4: lambda a, b: a > b, 5: lambda a, b: a >= b}


# check_project.py's block_behind warning on an instruction file whose Construct 3 block is older than the skill's.
STALE_BLOCK = re.compile(r"^warning: [^\n]*: its Construct 3 block is the skill's of [^\n]* and the skill's is now "
                         r"of [^\n]*; refresh it,[^\n]*\n?", re.M)


def checker(project: Path) -> tuple[int, str]:
    """check_project.py's exit code and output on the project. A run of an old_ arm installed the older skill,
    whose block the current checker warns about, so that one warning is left out of its output."""
    p = subprocess.run([sys.executable, str(SKILL / "scripts" / "check_project.py"),
                        "--project", str(project), "--rag", str(PLUGIN)],
                       capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8", CONSTRUCT3_RAG_NO_RECORD="1"))
    out = (p.stdout + p.stderr).strip()
    if project.parent.name.startswith("old_"):
        out = STALE_BLOCK.sub("", out).strip()
    return p.returncode, out


def walk(events: list, above: tuple = ()):
    """Every event with the events it sits under."""
    for ev in events:
        yield ev, above
        yield from walk(ev.get("children", []), (*above, ev))


def params(ace: dict) -> dict:
    """The named parameters of a condition or action; a function or custom action call lists its arguments
    instead, and names none."""
    p = ace.get("parameters")
    return p if isinstance(p, dict) else {}


def values(aces: list) -> str:
    """Every parameter value of some conditions or actions, as one searchable string."""
    out = []
    for a in aces:
        given = a.get("parameters", {})
        out += [str(v) for v in (given.values() if isinstance(given, dict) else given)]
    return " | ".join(out)


def conditions_over(ev: dict, above: tuple) -> list:
    return [c for e in (*above, ev) for c in e.get("conditions", [])]


def sheet_of(project: Path) -> list | None:
    try:
        return json.loads((project / "eventSheets" / "Game.json").read_text(encoding="utf-8"))["events"]
    except (OSError, ValueError, KeyError):
        return None


def grade_add_countdown(run: Path) -> list[tuple[bool, str]]:
    project = run / "project"
    code, out = checker(project)
    last = out.splitlines()[-1] if out else ""
    warnings = [line for line in out.splitlines() if line.startswith("warning:")]
    results = [(code == 0, f"exit {code}: {out.splitlines()[0] if code else last}"),
               (not warnings, warnings[0] if warnings else "no warning line")]
    events = sheet_of(project)
    if events is None:
        return results + [(False, "eventSheets/Game.json is not readable JSON")] * 6
    rows = list(walk(events))
    timers = [ev["name"] for ev, _ in rows if ev.get("eventType") == "variable" and ev["name"] not in ORIGINAL_GLOBALS]
    # The Timer behavior is the other way, the one event-sheet-thinking.md names for a countdown: started for 30
    # seconds, restarting on On timer, the time left read from its expressions.
    holders = variables_starting_at(rows, "30")
    acts = [(a, conditions_over(ev, above)) for ev, above in rows for a in ev.get("actions", [])]
    started = [a for a, conds in acts if a.get("id") == "start-timer"
               and str(params(a).get("duration", "")).strip() in {"30", "30.0", *holders}]
    tags = {str(a["parameters"].get("tag", "")) for a in started}
    names = re.compile("|".join([*map(re.escape, timers), r"\b(?:Duration|CurrentTime|TotalTime|NormalizedProgress)\s*\("])
                       if timers or started else r"$^", re.I)

    # A Timer started for 1 second, Regular, fires On timer once a second: the variable it takes 1 from counts down.
    ticks = {str(a["parameters"].get("tag", "")) for a, _ in acts if a.get("id") == "start-timer"
             and str(params(a).get("duration", "")).strip() in {"1", "1.0"}
             and str(a["parameters"].get("type", "")).lower() == "regular"}

    def by_one(a: dict) -> bool:
        p = params(a)
        value = str(p.get("value", "")).strip()
        return (a.get("id") == "subtract-from-eventvar" and value in ("1", "1.0")
                or a.get("id") == "add-to-eventvar" and value in ("-1", "-1.0")
                or a.get("id") == "set-eventvar-value"
                and re.fullmatch(rf"{re.escape(str(p.get('variable', '')))}\s*-\s*1(?:\.0)?", value) is not None)

    ticking = [(ev, above, a) for ev, above in rows for a in ev.get("actions", [])
               if a.get("id") in ("subtract-from-eventvar", "add-to-eventvar", "set-eventvar-value") and names.search(values([a]))]
    per_second, seen = False, "no action writes a countdown variable"
    for ev, above, a in ticking:
        conds = conditions_over(ev, above)
        every = [c for c in conds if c.get("id") == "every-x-seconds"]
        on_tick = any(c.get("id") == "on-timer" and str(params(c).get("tag", "")) in ticks for c in conds)
        worded = "; ".join(c.get("id", "?") + "(" + values([c]) + ")" for c in conds) or "no condition"
        seen = f"{worded} -> {a['id']}({values([a])})"
        if (any(values([c]).strip() in ("1", "1.0") for c in every) or re.search(r"\bdt\b", values([a]), re.I)
                or on_tick and by_one(a)):
            per_second = True
            break
    if not per_second and started:
        per_second, seen = True, f"Timer started for {started[0]['parameters']['duration']} seconds, tag {sorted(tags)}"
    results.append((per_second, seen))

    # A comparison of a countdown variable with a number has a direction: it holds once the countdown has
    # run out and not while 30 seconds are left. Countdown > 0 reads the variable and restarts at once.
    def runs_out(conds: list) -> bool | None:
        """False when a comparison of a countdown variable with a number holds at 30 or never at 0;
        None when no condition is such a comparison."""
        verdicts = []
        for c in conds:
            p = params(c)
            if c.get("id") == "compare-eventvar":
                left, right = str(p.get("variable", "")), str(p.get("value", ""))
            elif c.get("id") == "compare-two-values":
                left, right = str(p.get("first-value", "")), str(p.get("second-value", ""))
            else:
                continue
            left, right, op = left.strip(), right.strip(), COMPARE.get(p.get("comparison"))
            if op is None:
                continue
            if left in timers and NUMBER.fullmatch(right):
                at = {x: op(x, float(right)) for x in (30, 0, -0.5)}    # -0.5: a countdown that loses dt passes 0
            elif right in timers and NUMBER.fullmatch(left):
                at = {x: op(float(left), x) for x in (30, 0, -0.5)}
            else:
                continue
            if c.get("isInverted"):
                at = {x: not v for x, v in at.items()}
            verdicts.append(not at[30] and (at[0] or at[-0.5]))
        return all(verdicts) if verdicts else None

    restarts = [(ev, above) for ev, above in rows if any(a.get("id") == "restart-layout" for a in ev.get("actions", []))]
    hit = next((ev for ev, above in restarts if names.search(values(conditions_over(ev, above)))
                and runs_out(conditions_over(ev, above)) is not False
                or any(c.get("id") == "on-timer" and str(params(c).get("tag", "")) in tags
                       for c in conditions_over(ev, above))), None)
    backwards = [ev for ev, above in restarts if runs_out(conditions_over(ev, above)) is False]
    results.append((hit is not None, f"restart-layout under {values(hit['conditions'])}" if hit else
                    f"restart-layout under {values(backwards[0]['conditions'])}, which holds while 30 seconds are "
                    f"left or never at 0" if backwards else
                    f"{len(restarts)} event(s) restart the layout, none reads {timers or 'a countdown variable'}"
                    + (f" or is On timer {sorted(tags)}" if tags else "")))

    texts = [(a, conditions_over(ev, above)) for ev, above in rows for a in ev.get("actions", [])
             if a.get("id") == "set-text" and a.get("objectClass") == "ScoreText"]
    later = [a for a, conds in texts if not any(c.get("id") == "on-start-of-layout" for c in conds)]
    both = [a for a in later if names.search(values([a])) and re.search(r"\bscore\b", values([a]))]
    results.append((bool(later) and len(both) == len(later),
                    f"{len(both)} of {len(later)} set-text after the start hold score and time: "
                    + "; ".join(values([a]) for a in later)))

    sized = [(a, conditions_over(ev, above)) for ev, above in rows for a in ev.get("actions", [])
             if a.get("objectClass") == "Coin" and a.get("id") in SIZE_ACTIONS]
    by_value = next(((a, conds) for a, conds in sized if re.search(r"value", values([a]) + values(conds), re.I)), None)
    results.append((by_value is not None, f"{by_value[0]['id']}({values([by_value[0]])}) under "
                    f"{values(by_value[1]) or 'no condition'}" if by_value else
                    f"{len(sized)} size or scale action(s) on Coin, none reads value"))

    results.append(original_sids(run, rows, "Game.json"))

    # Restart layout keeps global variables (Construct3-Manual system-reference/system-actions.md): a countdown
    # set only by its declaration is still 0 once the layout has restarted, and never runs 30 seconds again.
    # A Timer started under On start of layout starts over with it: Start timer on a running tag restarts it.
    def starts_over(a: dict) -> bool:
        p = params(a)
        value = str(p.get("value", "")).strip()
        return a.get("id") == "reset-global-variables" or (
            a.get("id") == "set-eventvar-value" and p.get("variable") in timers
            and (value in ("30", "30.0") or (value in holders and value != p.get("variable"))))

    on_start = [a for a, conds in acts if any(c.get("id") == "on-start-of-layout" for c in conds)
                and (starts_over(a) or a in started)]
    at_restart = [a for a in (hit or {}).get("actions", []) if starts_over(a)]
    results.append((bool(on_start or at_restart),
                    "set back under On start of layout" if on_start else "set back in the restart on the countdown"
                    if at_restart else f"{timers} set back nowhere: after the first restart it is still 0"
                    if timers else "no countdown variable and no Timer started for 30 seconds on start"))
    return results


# What an answer says when it hands over a project that does not pass: the check failed, or N problems.
SAYS_IT_FAILS = re.compile(r"\b(?:fail(?:s|ed|ing)?|does(?:n't| not) pass|did(?:n't| not) pass|[1-9]\d* problems?|"
                           r"inverted|not invertible)\b|未通过|没通过|失败|取反|反转", re.I)


def grade_keep_checking_after_compaction(run: Path) -> list[tuple[bool, str]]:
    """add-countdown's assertions over the two turns, and whether a project that fails the checker is handed over
    as one: the answer must name the failure, as a word that says the check failed or the ACE a finding names."""
    code, out = checker(run / "project")
    if not code:
        return grade_add_countdown(run) + [(True, "the checker passes")]
    findings = [line for line in out.splitlines() if line and not line.startswith("warning:")][:-1]
    aces = {m.replace("-", " ") for line in findings for m in re.findall(r"\w+:([a-z][a-z0-9-]+)", line)}
    answer = answer_of(run)
    hit = SAYS_IT_FAILS.search(answer)
    said = hit.group(0) if hit else next((a for a in aces if a in answer.lower()), None)
    return grade_add_countdown(run) + [(bool(said), f"the checker fails ({findings[0] if findings else out[-200:]}); "
                                        + (f"the answer says {said!r}" if said else "the answer names no failure"))]


def grade_fix_load_errors(run: Path) -> list[tuple[bool, str]]:
    project = run / "project"
    code, out = checker(project)
    results = [(code == 0, f"exit {code}: {out.splitlines()[-1] if out else ''}")]
    events = sheet_of(project)
    if events is None:
        return results + [(False, "eventSheets/Game.json is not readable JSON")] * 7
    rows = list(walk(events))
    conds = [(c, ev, above) for ev, above in rows for c in ev.get("conditions", [])]
    acts = [(a, ev, above) for ev, above in rows for a in ev.get("actions", [])]

    start = [c for c, _, _ in conds if c.get("id") == "on-start-of-layout"]
    results.append((bool(start) and not any(c.get("isInverted") for c in start),
                    f"isInverted: {[c.get('isInverted', False) for c in start]}"))
    touched = [c for c, _, _ in conds if c.get("id") == "on-touched-object"]
    results.append((bool(touched) and all(c["parameters"].get("type") == "start" for c in touched),
                    f"type: {[c['parameters'].get('type') for c in touched]}"))
    tweens = [a for a, _, _ in acts if a.get("id") == "tween-two-properties"]
    results.append((bool(tweens) and all(a.get("behaviorType") == "Tween" for a in tweens),
                    f"behaviorType: {[a.get('behaviorType') for a in tweens]}"))

    collect = next((ev for ev, _ in rows if ev.get("eventType") == "custom-ace-block"), None)
    inside = [c.get("id") for ev, above in rows if collect in above or ev is collect
              for c in ev.get("conditions", []) if c.get("id") in TWEEN_ENDS]
    results.append((collect is not None and not inside,
                    f"triggers inside Collect: {inside or 'none'}" if collect else "the custom action Collect is gone"))

    ids = [a.get("id") for a, _, _ in acts if a.get("objectClass") == "ScoreText"]
    results.append(("set-txt" not in ids and "set-text" in ids, f"ScoreText action ids: {ids}"))

    calls = [(ev, above) for a, ev, above in acts if a.get("callFunction") == "AddScore"]
    on_collect = [("Collect" if ev is collect or collect in above else "tween end")
                  for ev, above in calls
                  if ev is collect or collect in above
                  or any(c.get("id") in TWEEN_ENDS and c.get("objectClass") == "Coin" for c in conditions_over(ev, above))]
    in_broken = [w for w, (ev, above) in zip(on_collect, calls) if w == "tween end" and collect in above]
    results.append((bool(on_collect) and not in_broken, f"AddScore called from: {on_collect or 'nowhere on collect'}"
                    + (" (still inside Collect, under the trigger)" if in_broken else "")))
    kept = [a for a in (collect or {}).get("actions", []) if a.get("id") == "tween-two-properties"
            and "collect" in str(params(a).get("tags", ""))]
    results.append((bool(kept), f"tween actions in Collect tagged collect: {len(kept)}"))
    return results


def system_text(locale: str, kind: str, ace: str) -> str:
    """The display text of a System condition or action in one locale, without its markup."""
    aces = json.loads((DATA / "c3-schemas" / locale / "plugins" / "system.json").read_text(encoding="utf-8"))[kind]
    return re.sub(r"\[/?[bi]\]", "", next(a["display-text"] for a in aces if a["id"] == ace))


# A run that answers in Chinese uses the zh-CN editor's wording: "事件 9", "仅触发一次", "等待 1 秒".
ZH_TRIGGER_ONCE = system_text("zh-CN", "conditions", "trigger-once-while-true")
ZH_SECONDS = system_text("zh-CN", "actions", "wait").split("{0}")[1].split()[0]
EVENT_NUMBER = re.compile(r"(?:\bevent(?:\s+number)?|事件(?:编号)?)[\s:：*#`]*(\d+)", re.I)


def grade_name_the_restart_event(run: Path) -> list[tuple[bool, str]]:
    answer = answer_of(run)
    numbers = [int(n) for n in EVENT_NUMBER.findall(answer)]
    # 9 restarts and 8 is the group it sits in. The first number is the answer; a later one may name another
    # event as context ("Setup (event 2) runs again"), and 8 may stand on a line that calls it the group.
    as_event = {int(n) for line in answer.splitlines() if not re.search(r"\bgroup\b|组", line, re.I)
                for n in EVENT_NUMBER.findall(line)}
    results = [(numbers[:1] == [9] and 8 not in as_event, f"event numbers the answer gives, in order: {numbers or 'none'}"
                + ("; 8 as the event, not as its group" if 8 in as_event else ""))]
    # "仅" is "only"; answers drop it.
    trigger_once = rf"trigger\s+once|{re.escape(ZH_TRIGGER_ONCE).replace('仅', '仅?')}"
    parts = {"Coin.Count = 0": re.search(r"coin\.count`?\s*=+\s*`?0", answer, re.I),
             "Trigger once": re.search(trigger_once, answer, re.I),
             "1 second wait": re.search(rf"\b(1|one)[\s-]*(s\b|sec)|(1|一)\s*{ZH_SECONDS}", answer, re.I)}
    results.append((all(parts.values()), "stated: " + ", ".join(k for k, v in parts.items() if v)
                    + ("; missing: " + ", ".join(k for k, v in parts.items() if not v) if not all(parts.values()) else "")))
    results.append(unchanged(run))
    return results


def unchanged(run: Path, allowed: tuple[str, ...] = ()) -> tuple[bool, str]:
    """Whether no project file differs from the fixture, with the list of those that do. A path that starts
    with one of `allowed` is skipped, and so are .tmp, where the skill's scripts write their results, and .git,
    which SKILL.md tells a run to create."""
    want = {k: v for k, v in json.loads((run / "fixture.json").read_text(encoding="utf-8")).items() if not k.endswith((".sids", ".warnings", ".commit"))}
    project = run / "project"
    have = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for p in sorted(project.rglob("*"))
            if p.is_file() and p.name != "AGENTS.md" and not {".agents", "__pycache__", ".tmp", ".git"} & set(p.parts)}
    changed = sorted(k for k in set(want) | set(have) if want.get(k) != have.get(k) and not k.startswith(allowed))
    return not changed, f"files that differ from the fixture: {changed or 'none'}"


def answer_of(run: Path) -> str:
    """The run's answer, without the list of commands it ran."""
    path = run / "outputs" / "answer.md"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    return re.split(r"^#+\s*commands?\s+run", text, flags=re.I | re.M)[0]


def event_numbers(answer: str) -> list[int]:
    """Every number that follows "event" or "events" in the answer: "event 103", "events 104 and 105",
    "Events 103-105"; and the number that opens a bullet of a list of events: "- **12** `On drop`", "- 15: ..."."""
    after_word = {int(n) for span in re.findall(r"\bevents?\b[^.\n]{0,40}", answer, re.I)
                  for n in re.findall(r"(?<![\w.])\d{1,3}(?![\w.]|\s*(?:seconds?|s\b|px|%))", span)}
    bullets = {int(n) for n in re.findall(r"^\s*[-*+]\s+\*{0,2}(\d{1,3})\*{0,2}(?=[:\s])", answer, re.M)}
    return sorted(after_word | bullets)


# A correct answer also cites the events around the one asked for: the start-of-layout events a restart runs
# again, the function a bonus reaches. So no assertion holds every event number to the asked-for range
# (dev/tests/fixtures/find_answers/).
def grade_find_in_a_long_sheet(run: Path) -> list[tuple[bool, str]]:
    answer = answer_of(run)
    numbers = event_numbers(answer)
    said = f"event numbers the answer gives: {numbers or 'none'}"
    return [(103 in numbers and bool(re.search(r"finish\s*line", answer, re.I)), said),
            (108 in numbers and "showgameover" in answer.lower() and bool(re.search(r"restart", answer, re.I)), said),
            (all(re.search(word, answer, re.I) for word in ("player", "success", "fail")),
             "stated: " + ", ".join(w for w in ("player", "success", "fail") if re.search(w, answer, re.I))),
            unchanged(run)]


def grade_find_in_a_big_sheet(run: Path) -> list[tuple[bool, str]]:
    """The sheet of make_fixtures.big_sheet(): wave 17's bonus is event 284, which calls GiveBonus(454)."""
    answer = answer_of(run)
    # The wave and the bonus can stand near the word "event" ("event 284, wave 17, gives 454"): not event numbers.
    numbers = [n for n in event_numbers(answer) if n not in (17, 454)]
    said = f"event numbers the answer gives: {numbers or 'none'}"
    return [(284 in numbers, said),
            (bool(re.search(r"(?<![\d.])454(?![\d.])", answer)), "454 stated" if "454" in answer else "454 not stated"),
            unchanged(run)]


# The stand-in's viewport, grid and finger, what settings_of() falls back on; MARGIN is the plain sheet's
VIEW_W, VIEW_H, UNIT, MARGIN, TOUCH = 1920, 1080, 32, 32, 160
HUD_LAYERS = {"ui", "hud"}


def settings_of(project: Path) -> dict:
    """VIEW_W, VIEW_H, UNIT, MARGIN, TOUCH and PALETTE of the run's generator, from the settings above its
    helpers; the stand-in's, and no PALETTE, when they cannot be run. Each arm's generator sets its own MARGIN
    and each fixture its viewport, so each run is graded by its own."""
    fallback = {"VIEW_W": VIEW_W, "VIEW_H": VIEW_H, "UNIT": UNIT, "MARGIN": MARGIN, "TOUCH": TOUCH, "PALETTE": {}}
    try:
        path = project / "tools" / "build_project.py"
        text = path.read_text(encoding="utf-8")
        settings: dict = {"__file__": str(path)}
        exec(text.split("# ==== construct3-agent-plugin helpers: begin")[0], settings)
        return {k: int(settings[k]) for k in ("VIEW_W", "VIEW_H", "UNIT", "MARGIN", "TOUCH")} | {
            "PALETTE": dict(settings.get("PALETTE") or {})}
    except (OSError, SyntaxError, NameError, KeyError, TypeError, ValueError, ArithmeticError):
        return fallback


def margin_of(project: Path) -> int:
    """The MARGIN the run's generator holds its HUD by (settings_of())."""
    return settings_of(project)["MARGIN"]


def view_of(project: Path) -> tuple[int, int]:
    """The viewport of the run's generator (settings_of())."""
    settings = settings_of(project)
    return settings["VIEW_W"], settings["VIEW_H"]


def drawn_box(project: Path, inst: dict) -> tuple[float, float, float, float]:
    """The part of an instance's box its type's first image draws, the pixels that are not clear, scaled to
    the box: a small drawing in a box a finger hits lines up by its drawing. The whole box when the image
    cannot be read or PIL is missing."""
    whole = box_of(inst)
    try:
        from PIL import Image
    except ImportError:
        return whole
    for png in sorted((project / "images").glob(f"{inst['type'].lower()}*.png")):
        try:
            with Image.open(png) as im:
                bounds = im.convert("RGBA").getchannel("A").getbbox()
                size = im.size
        except OSError:
            continue
        if not bounds:
            return whole
        l, t, r, b = whole
        sx, sy = (r - l) / size[0], (b - t) / size[1]
        return l + bounds[0] * sx, t + bounds[1] * sy, l + bounds[2] * sx, t + bounds[3] * sy
    return whole


def grade_lay_out_the_hud(run: Path) -> list[tuple[bool, str]]:
    """The HUD the run added through the generator: on the UI layer, whole numbers, the sprites it
    added sized in units and their drawings held against an edge or centred, the tapped button a
    finger wide, and tools/build_project.py the source of layouts/Game.json. A text's box is measured
    to its text by the template, so the size and edge rules leave texts and the stand-in's HUD out. The
    viewport, the unit, MARGIN and TOUCH are those of the run's generator."""
    project = run / "project"
    settings = settings_of(project)
    view_w, view_h, unit, margin, touch = (settings[k] for k in ("VIEW_W", "VIEW_H", "UNIT", "MARGIN", "TOUCH"))
    code, out = checker(project)
    results = [(code == 0, f"exit {code}: {out.splitlines()[0] if code else (out.splitlines() or [''])[-1]}")]
    try:
        layout = json.loads((project / "layouts" / "Game.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return results + [(False, "layouts/Game.json is not readable JSON")] * (
            len(CASES["lay-out-the-hud"]["assertions"]) - len(results))
    hud = hud_of(layout)
    added = [i for i in hud if i["type"] not in play_cases.STAND_IN_HUD]
    kinds = sorted({i["type"] for i in added})
    listed = ", ".join(f"{i['type']}@({i['world']['x']},{i['world']['y']} {i['world']['width']}x{i['world']['height']})"
                       for i in hud) or "no instance on a layer named UI or HUD"
    results.append((len(added) >= 3 and len(kinds) >= 2, f"{len(added)} added instance(s) of {kinds}: {listed}"))

    def whole(v) -> bool:
        return isinstance(v, (int, float)) and float(v).is_integer()

    fractions = [i["type"] for i in hud if not all(whole(i["world"][k]) for k in ("x", "y", "width", "height"))]
    results.append((bool(hud) and not fractions, f"fractional coordinates or sizes on: {fractions or 'none'}"))
    shapes = [i for i in added if plugin_id(project, i["type"]) != "Text"]
    off = [f"{i['type']} {i['world']['width']}x{i['world']['height']}" for i in shapes
           if not all(whole(i["world"][k]) and int(i["world"][k]) % unit == 0 for k in ("width", "height"))]
    results.append((bool(shapes) and not off, f"{len(shapes)} added non-text instance(s); sizes not in {unit} px "
                                               f"units: {off or 'none'}"))

    def held(lo: float, hi: float, size: float, slack: float = 0.5) -> bool:
        return abs(lo - margin) <= slack or abs(hi - (size - margin)) <= slack or abs((lo + hi) / 2 - size / 2) <= slack

    type_boxes = {kind: box_around([i for i in hud if i["type"] == kind]) for kind in sorted({i["type"] for i in hud})}
    loose, drawn = [], {}
    for i in shapes:
        dl, dt, dr, db = drawn_box(project, i)
        l, t, r, b = drawn.get(i["type"], (dl, dt, dr, db))
        drawn[i["type"]] = (min(l, dl), min(t, dt), max(r, dr), max(b, db))

    def lined_up(kind: str, edges: tuple, slack: float) -> bool:
        l, t, r, b = edges
        # A second row: its top one unit under a box of another type that is itself held to the top or bottom.
        stacked = any(abs(t - (ob + unit)) <= slack and held(ot, ob, view_h)
                      for other, (ol, ot, orr, ob) in type_boxes.items() if other != kind)
        return held(l, r, view_w, slack) and (held(t, b, view_h, slack) or stacked)

    # A type lines up by its box, or by its drawing when that is smaller than a box a finger hits. A drawing's
    # edge is its outermost pixel that is not clear, which an antialiased curve leaves a pixel or two inside the
    # line it was drawn to.
    for kind, edges in drawn.items():
        if not (lined_up(kind, type_boxes[kind], 0.5) or lined_up(kind, edges, 2)):
            l, t, r, b = type_boxes[kind]
            dl, dt, dr, db = edges
            loose.append(f"{kind} box ({l:g},{t:g})-({r:g},{b:g}), drawn ({dl:g},{dt:g})-({dr:g},{db:g})")
    results.append((bool(drawn) and not loose, f"added non-text types neither {margin} px inside an edge, nor centred, "
                                               f"nor one unit under a held box, by box or drawing: {loose or 'none'}"))

    outside = outside_of(hud, view_w, view_h)
    results.append((bool(hud) and not outside, f"boxes reaching past the viewport: {outside or 'none'}"))
    overlaps = overlaps_of(project, hud)
    results.append((bool(hud) and not overlaps, f"overlapping boxes: {overlaps or 'none'}"))

    button = [i for i in added if re.search(r"pause|button|btn", i["type"], re.I)]
    small = [f"{i['type']} {i['world']['width']}x{i['world']['height']}" for i in button
             if min(i["world"]["width"], i["world"]["height"]) < touch]
    results.append((bool(button) and not small,
                    f"button(s) {[i['type'] for i in button] or 'none found by name'}; under {touch} px: {small or 'none'}"))

    lives = [i for i in added if plugin_id(project, i["type"]) == "Sprite" and i not in button]
    per_type: dict[str, int] = {}
    for i in lives:
        per_type[i["type"]] = per_type.get(i["type"], 0) + 1
    three = [k for k, n in per_type.items() if n >= 3]
    wide = sorted({i["type"] for i in lives if i["world"]["width"] >= 3 * i["world"]["height"] - 0.5})
    results.append((bool(three or wide), f"sprite instances besides the button, by type: {per_type or 'none'}; "
                                          f"three of one type: {three or 'none'}; three times as wide as high: {wide or 'none'}"))

    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "game"
        shutil.copytree(project, copy, ignore=shutil.ignore_patterns("__pycache__", ".tmp", ".build"))
        try:
            p = subprocess.run([sys.executable, "tools/build_project.py"], cwd=copy, capture_output=True, text=True,
                               encoding="utf-8", timeout=180, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            same = ((copy / "layouts" / "Game.json").read_bytes().replace(b"\r\n", b"\n")
                    == (project / "layouts" / "Game.json").read_bytes().replace(b"\r\n", b"\n"))
            said = (f"rerun exit {p.returncode}; layouts/Game.json {'identical' if same else 'differs'}"
                    + ("" if p.returncode == 0 else ": " + (p.stdout + p.stderr).strip().splitlines()[-1]))
            results.append((p.returncode == 0 and same, said))
        except (OSError, subprocess.TimeoutExpired) as e:
            results.append((False, f"rerun of tools/build_project.py: {type(e).__name__}: {e}"))
    return results


WIDTH_ACTIONS = {"set-width", "set-size", "set-scale"}
TWEEN_SIZE = {"width", "size", "scale", "offsetwidth", "offsetscalex"}      # the Tween combo's keys, lower-cased


def hud_of(layout: dict) -> list:
    """The instances on the layout's UI or HUD layer."""
    return [inst for layer in layout.get("layers", []) if layer.get("name", "").lower() in HUD_LAYERS
            for inst in layer.get("instances", []) if "world" in inst]


def hud_instances(project: Path) -> list:
    try:
        layout = json.loads((project / "layouts" / "Game.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return hud_of(layout)


def box_of(inst: dict) -> tuple[float, float, float, float]:
    w = inst["world"]
    left = w["x"] - w.get("originX", 0) * w["width"]
    top = w["y"] - w.get("originY", 0) * w["height"]
    return left, top, left + w["width"], top + w["height"]


def box_around(insts: list) -> tuple[float, float, float, float]:
    """The box around the instances' boxes."""
    boxes = [box_of(i) for i in insts]
    return min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)


def contains(outer: tuple, inner: tuple, slack: float = 1) -> bool:
    return (outer[0] - slack <= inner[0] and outer[1] - slack <= inner[1]
            and outer[2] + slack >= inner[2] and outer[3] + slack >= inner[3])


def outside_of(hud: list, view_w: float, view_h: float) -> list[str]:
    """The boxes on the UI layer that reach past the viewport."""
    return [f"{i['type']} ({l:g},{t:g})-({r:g},{b:g})" for i in hud for l, t, r, b in [box_of(i)]
            if l < 0 or t < 0 or r > view_w or b > view_h]


def overlaps_of(project: Path, hud: list) -> list[str]:
    """The pairs of boxes on the UI layer that meet. A box inside one that is not a label, a label on its button
    or key or a bar's fill in its frame, is laid there on purpose."""
    boxes = [(i["type"], *box_of(i)) for i in hud]
    is_text = {i["type"]: plugin_id(project, i["type"]) == "Text" for i in hud}

    def layered(inner: tuple, outer: tuple) -> bool:
        return not is_text[outer[0]] and contains(outer[1:], inner[1:], 0.5)

    return [f"{a[0]} ({a[1]:g},{a[2]:g})-({a[3]:g},{a[4]:g}) and {b[0]} ({b[1]:g},{b[2]:g})-({b[3]:g},{b[4]:g})"
            for n, a in enumerate(boxes) for b in boxes[n + 1:]
            if min(a[3], b[3]) - max(a[1], b[1]) > 0.5 and min(a[4], b[4]) - max(a[2], b[2]) > 0.5
            and not layered(a, b) and not layered(b, a)]


def plugin_id(project: Path, kind: str) -> str | None:
    try:
        return json.loads((project / "objectTypes" / f"{kind}.json").read_text(encoding="utf-8")).get("plugin-id")
    except (OSError, ValueError):
        return None


def frames_of(project: Path, kind: str) -> int:
    try:
        anims = json.loads((project / "objectTypes" / f"{kind}.json").read_text(encoding="utf-8")).get("animations")
    except (OSError, ValueError):
        return 0
    return sum(len(a.get("frames", [])) for a in anims.get("items", [])) if isinstance(anims, dict) else 0


def sheet_rows(project: Path) -> list:
    """Every event of every sheet with the events above it; [] when none is readable."""
    rows = []
    for path in sorted((project / "eventSheets").glob("*.json")):
        if path.name.endswith(".uistate.json"):
            continue
        try:
            rows += list(walk(json.loads(path.read_text(encoding="utf-8"))["events"]))
        except (OSError, ValueError, KeyError):
            pass
    return rows


def variables_starting_at(rows: list, initial: str) -> set[str]:
    return {ev["name"] for ev, _ in rows if ev.get("eventType") == "variable" and str(ev.get("initialValue")) == initial}


def ivars_starting_at(project: Path, initial) -> set[str]:
    """Instance variables whose initial value on the type, or whose value on a layout
    instance, is `initial`."""
    names = set()
    for path in (project / "objectTypes").glob("*.json"):
        try:
            for v in json.loads(path.read_text(encoding="utf-8")).get("instanceVariables", []):
                if str(v.get("initialValue")) == str(initial):
                    names.add(v["name"])
        except (OSError, ValueError):
            pass
    for path in (project / "layouts").glob("*.json"):
        try:
            layout = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for layer in layout.get("layers", []):
            for inst in layer.get("instances", []):
                for k, v in inst.get("instanceVariables", {}).items():
                    if str(v) == str(initial):
                        names.add(k)
    return names


SET_VALUE = {"add-to-eventvar", "add-to-instvar", "subtract-from-eventvar", "subtract-from-instvar",
             "set-eventvar-value", "set-instvar-value"}


def value_actions(rows: list, names: set[str], ids: set[str] = SET_VALUE) -> list:
    pat = re.compile("|".join(map(re.escape, names)) or r"$^")
    return [a for ev, _ in rows for a in ev.get("actions", []) if a.get("id") in ids and pat.search(values([a]))]


def steps_by(rows: list, names: set[str], amount: str) -> list:
    """Actions that move one of the names by `amount`: a literal, a variable holding it, or the
    same with the sign in the action (`Add -1`, `Subtract 1`, `Set x - 1`)."""
    magnitude = amount.lstrip("-")
    holders = variables_starting_at(rows, amount) | variables_starting_at(rows, magnitude)
    number = re.compile(r"(?<![\w.])-?" + re.escape(magnitude) + r"(?![\w.])")
    holder = re.compile("|".join(map(re.escape, holders)) or r"$^")
    # A function handed the amount, `AddHealth(10)` or `AddHealth(HP_PER_COIN)`, whose body adds its parameter.
    passed = any(number.search(values([a])) or holder.search(values([a])) for ev, _ in rows for a in ev.get("actions", [])
                 if "callFunction" in a or a.get("id") in ("call-function", "call-custom-action"))
    out = []
    for a in value_actions(rows, names):
        text = values([a])
        if number.search(text) or holder.search(text) or (passed and re.search(r"[+-]\s*[A-Za-z_]\w*", text)):
            out.append(a)
    return out


def aliases_of(rows: list, names: set[str]) -> set[str]:
    """The names plus every variable set from one of them: `lives` set to `MAX_LIVES`."""
    out = set(names)
    pat = re.compile("|".join(map(re.escape, names)) or r"$^")
    for ev, _ in rows:
        for a in ev.get("actions", []):
            p = params(a)
            if a.get("id") in ("set-eventvar-value", "set-instvar-value") and pat.search(str(p.get("value", ""))):
                out.add(p.get("variable") or p.get("instance-variable") or "")
    return {n for n in out if n}


def width_drivers(rows: list, names: set[str]) -> dict[str, list]:
    """Objects whose width an action sets from one of the names, by object, with the actions."""
    pat = re.compile("|".join(map(re.escape, names)) or r"$^")
    out: dict[str, list] = {}
    for ev, _ in rows:
        for a in ev.get("actions", []):
            given = params(a)
            is_width = a.get("id") in WIDTH_ACTIONS or (a.get("id") == "tween-one-property"
                                                       and str(given.get("property", "")).lower() in TWEEN_SIZE)
            if is_width and pat.search(values([a])):
                out.setdefault(a.get("objectClass"), []).append(a)
    return out


def generator_is_source(run: Path) -> tuple[bool, str]:
    project = run / "project"
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "game"
        shutil.copytree(project, copy, ignore=shutil.ignore_patterns("__pycache__", ".tmp", ".build"))
        try:
            p = subprocess.run([sys.executable, "tools/build_project.py"], cwd=copy, capture_output=True, text=True,
                               encoding="utf-8", timeout=180, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, f"rerun of tools/build_project.py: {type(e).__name__}: {e}"
        same = ((copy / "layouts" / "Game.json").read_bytes().replace(b"\r\n", b"\n")
                == (project / "layouts" / "Game.json").read_bytes().replace(b"\r\n", b"\n"))
        said = f"rerun exit {p.returncode}; layouts/Game.json {'identical' if same else 'differs'}"
        if p.returncode:
            said += ": " + ((p.stdout + p.stderr).strip().splitlines() or ["?"])[-1]
        return p.returncode == 0 and same, said


def checker_line(project: Path) -> tuple[bool, str]:
    code, out = checker(project)
    lines = out.splitlines() or [""]
    return code == 0, f"exit {code}: {lines[0] if code else lines[-1]}"


def checker_and_warnings(project: Path) -> list[tuple[bool, str]]:
    """Whether the checker passes, and whether it prints no warning line."""
    code, out = checker(project)
    warnings = [line for line in out.splitlines() if line.startswith("warning:")]
    return [(code == 0, f"exit {code}: {out.splitlines()[0] if code else out.splitlines()[-1]}"),
            (not warnings, warnings[0] if warnings else "no warning line")]


def grade_show_hp_as_a_bar(run: Path) -> list[tuple[bool, str]]:
    project = run / "project"
    results = [checker_line(project)]
    rows = sheet_rows(project)
    hp = aliases_of(rows, variables_starting_at(rows, "40") | ivars_starting_at(project, 40))
    adds10 = steps_by(rows, hp, "10")
    results.append((bool(hp) and bool(adds10), f"variables at 40: {sorted(hp) or 'none'}; actions adding 10: {len(adds10)}"))
    pat = re.compile("|".join(map(re.escape, hp)) or r"$^")
    capped = [a for ev, _ in rows for a in ev.get("actions", []) if pat.search(values([a]))
              and re.search(r"\b(min|clamp)\s*\(", values([a]))]
    compared = [c for ev, _ in rows for c in ev.get("conditions", []) if pat.search(values([c])) and re.search(r"(?<![\d.])100(?![\d.])", values([c]))]
    results.append((bool(hp) and bool(capped or compared), f"min/clamp on it: {len(capped)}; comparisons with 100: {len(compared)}"))
    drivers = width_drivers(rows, hp)
    with_max = {k: v for k, v in drivers.items() if any(re.search(r"(?<![\d.])100(?![\d.])|max|/", values([a])) for a in v)}
    results.append((bool(with_max), f"width set from hp: {sorted(drivers) or 'none'}; with a maximum: {sorted(with_max) or 'none'}"))
    hud = hud_instances(project)
    fill = next((i for i in hud if i["type"] in with_max), None) or next((i for i in hud if i["type"] in drivers), None)
    ox = fill["world"].get("originX", 0) if fill else None
    results.append((fill is not None and ox in (0, 1), f"fill {fill['type'] if fill else 'none on the UI layer'} originX {ox}"))
    frame = next((i for i in hud if fill and i is not fill and i["type"] != fill["type"] and contains(box_of(i), box_of(fill))), None)
    results.append((frame is not None, f"frame around the fill: {frame['type'] if frame else 'none'}"))
    slides = [a for a in sum(drivers.values(), []) if a.get("id") == "tween-one-property"
              or (a.get("id") in WIDTH_ACTIONS and re.search(r"lerp\s*\(.*\bdt\b", values([a])))]
    results.append((bool(slides), f"sliding actions on the fill: {[a.get('id') for a in slides] or 'none'}"))
    score = next((i for i in hud if i["type"] == "ScoreText"), None)
    under = frame is not None and score is not None and box_of(frame)[1] >= box_of(score)[3] - 0.5
    inside = frame is not None and box_of(frame)[0] >= 0 and box_of(frame)[1] >= 0 and box_of(frame)[2] <= view_of(project)[0] and box_of(frame)[3] <= view_of(project)[1]
    results.append((under and inside, f"frame box {box_of(frame) if frame else None}, score bottom {box_of(score)[3] if score else None}"))
    results.append(generator_is_source(run))
    return results


def gradient_images(project: Path) -> set[str]:
    """Object types whose first image runs from one colour to another left to right."""
    try:
        from PIL import Image
    except ImportError:
        return set()
    out = set()
    for png in (project / "images").glob("*.png"):
        try:
            with Image.open(png) as im:
                im = im.convert("RGB")
                w, h = im.size
                if w < 16:
                    continue
                left = [im.getpixel((x, h // 2)) for x in range(0, max(1, w // 10))]
                right = [im.getpixel((x, h // 2)) for x in range(w - max(1, w // 10), w)]
                l = [sum(c[i] for c in left) / len(left) for i in range(3)]
                r = [sum(c[i] for c in right) / len(right) for i in range(3)]
                if sum(abs(a - b) for a, b in zip(l, r)) > 120:
                    out.add(png.stem.split("-")[0].lower())
        except OSError:
            pass
    return out


def painted_border(project: Path, kind: str) -> list[str]:
    """Images of the type whose outermost rows are dark while the middle row is not: a frame
    painted into the picture instead of a second object."""
    try:
        from PIL import Image
    except ImportError:
        return []
    out = []
    for png in (project / "images").glob(f"{kind.lower()}*.png"):
        try:
            with Image.open(png) as im:
                im = im.convert("RGB")
                w, h = im.size
                if w < 8 or h < 8:
                    continue
                def row(y: int) -> float:
                    return sum(sum(im.getpixel((x, y))) for x in range(w)) / w
                if max(row(0), row(h - 1)) + 60 < row(h // 2):
                    out.append(png.name)
        except OSError:
            pass
    return out


def grade_reveal_the_gradient(run: Path) -> list[tuple[bool, str]]:
    project = run / "project"
    results = [checker_line(project)]
    rows = sheet_rows(project)
    hp = aliases_of(rows, variables_starting_at(rows, "40") | ivars_starting_at(project, 40))
    adds = steps_by(rows, hp, "10")
    results.append((bool(hp) and bool(adds), f"variables at 40: {sorted(hp) or 'none'}; actions adding 10: {len(adds)}"))
    hud = hud_instances(project)
    grads = gradient_images(project)
    shown = [i for i in hud if i["type"].lower() in grads]
    results.append((bool(shown), f"gradient images: {sorted(grads) or 'none'}; shown on the UI layer by: {sorted({i['type'] for i in shown}) or 'none'}"))
    drivers = width_drivers(rows, hp)
    all_width = {a.get("objectClass") for ev, _ in rows for a in ev.get("actions", []) if a.get("id") in WIDTH_ACTIONS
                 or (a.get("id") == "tween-one-property" and str(params(a).get("property", "")).lower() in TWEEN_SIZE)}
    verdicts = []
    ok = False
    hp_pat = re.compile("|".join(map(re.escape, hp)) or r"$^")
    for i in shown:
        kind, plug = i["type"], plugin_id(project, i["type"])
        framed = [a for ev, _ in rows for a in ev.get("actions", []) if a.get("objectClass") == kind
                  and a.get("id") in ("set-animation-frame", "set-animation") and hp_pat.search(values([a]))]
        if kind in all_width:
            if plug == "TiledBg":
                ok = True; verdicts.append(f"{kind}: Tiled Background set by width, a cut of the painting")
            else:
                verdicts.append(f"{kind}: {plug} set by width, stretched")
        elif frames_of(project, kind) >= 2 and framed:
            ok = True; verdicts.append(f"{kind}: a strip of {frames_of(project, kind)} frames, the frame set from hp")
        else:
            cover = [j for j in hud if j["type"] in all_width and j is not i and j["world"].get("originX") == 1
                     and box_of(i)[0] - 1 <= box_of(j)[0] and box_of(j)[2] <= box_of(i)[2] + 1]
            atop = [j for j in hud if j["type"] in all_width and j["world"].get("blendMode") in ("source-atop", "source-in", "destination-in")]
            if cover:
                ok = True; verdicts.append(f"{kind} static, covered from the right by {cover[0]['type']}")
            elif atop:
                ok = True; verdicts.append(f"{kind} static, {atop[0]['type']} drawn {atop[0]['world']['blendMode']} over it")
            else:
                verdicts.append(f"{kind} static and nothing reveals it")
    results.append((ok and not any("stretched" in v for v in verdicts), "; ".join(verdicts) or "no gradient object"))
    framed_from_hp = {a.get("objectClass") for ev, _ in rows for a in ev.get("actions", [])
                      if a.get("id") in ("set-animation-frame", "set-animation") and hp_pat.search(values([a]))}
    readers = set(drivers) | framed_from_hp
    results.append((bool(readers), f"objects whose width or frame is set from hp: {sorted(readers) or 'none'}"))
    frame = None
    painted = []
    for i in shown:
        frame = next((j for j in hud if j is not i and j["type"] != i["type"] and contains(box_of(j), box_of(i))), None)
        if frame:
            break
        painted += painted_border(project, i["type"])
    results.append((frame is not None or bool(painted),
                    f"frame around the gradient: {frame['type'] if frame else 'no object'}; border painted into the image: {painted or 'none'}"))
    results.append(generator_is_source(run))
    return results


def lives_from_count(rows: list, starts: set[str]) -> list[tuple[str, str]]:
    """Lives that follow from a count instead of a variable of their own: an expression that takes from one of
    `starts` a variable the events add 1 to, divided by what a life costs, `HEARTS - floor(taken / 3)`. The pairs
    (start, count) found."""
    counts = {n for n in variables_starting_at(rows, "0")
              if any(a.get("id", "").startswith("add") or "+" in values([a]) for a in steps_by(rows, {n}, "1"))}
    text = " | ".join(values(ev.get("conditions", []) + ev.get("actions", [])) for ev, _ in rows)
    return sorted((s, c) for s in starts for c in counts
                  if re.search(rf"(?<![\w.]){re.escape(s)}\s*-\s*(?:floor|int|round|ceil)?\s*\(?\s*{re.escape(c)}\s*/", text))


def grade_lives_as_hearts(run: Path) -> list[tuple[bool, str]]:
    project = run / "project"
    results = [checker_line(project)]
    rows = sheet_rows(project)
    lives = aliases_of(rows, variables_starting_at(rows, "5") | ivars_starting_at(project, 5))
    subs = [a for a in steps_by(rows, lives, "1") if a.get("id").startswith("subtract") or "-" in values([a])]
    counted = lives_from_count(rows, lives)
    results.append((bool(lives) and bool(subs or counted), f"variables at 5: {sorted(lives) or 'none'}; actions taking 1: "
                                                           f"{len(subs)}; lives drawn from a count: {counted or 'none'}"))
    pat = re.compile("|".join(map(re.escape, lives)) or r"$^")
    by_width = width_drivers(rows, lives)
    # A count of icons on a Sprite whose frame is the count, or on instances picked against it: the
    # count itself, a loop index compared with it, or an index variable compared with what a
    # function was handed.
    by_frame = [a for ev, _ in rows for a in ev.get("actions", []) if a.get("id") in ("set-animation-frame", "set-animation") and pat.search(values([a]))]
    SHOWS = ("destroy", "set-visible", "set-animation-frame", "set-animation", "set-opacity")
    by_pick = [(ev, c) for ev, _ in rows for c in ev.get("conditions", [])
               if c.get("id") in ("pick-by-evaluate", "compare-instance-variable", "evaluate-expression", "compare-eventvar", "compare-two-values")
               and (pat.search(values([c])) or re.search(r"index|idx|slot|loopindex", values([c]) + str(params(c).get("instance-variable", "")), re.I))
               and any(a.get("id") in SHOWS for a in ev.get("actions", []))]
    how = [k for k, v in (("width", by_width), ("frame", by_frame), ("pick", by_pick)) if v]
    results.append((bool(how), f"driven by the count through: {how or 'nothing'}"))
    hud = hud_instances(project)
    hearts = [i for i in hud if re.search(r"heart|life|lives", i["type"], re.I)]
    kinds = sorted({i["type"] for i in hearts})
    empty = []
    for kind in kinds:
        others = [i for i in hud if i["type"] != kind and any(contains(box_of(i), box_of(h), 2) or contains(box_of(h), box_of(i), 2) for h in hearts if h["type"] == kind)]
        if others:
            empty.append(f"{kind}: under it {sorted({o['type'] for o in others})}")
        if frames_of(project, kind) >= 2:
            empty.append(f"{kind}: {frames_of(project, kind)} frames")
    picked_shows = [ev for ev, c in by_pick if any(a.get("id") in ("set-animation-frame", "set-animation", "set-opacity", "set-visible") for a in ev.get("actions", []))]
    picked_destroys = [ev for ev, c in by_pick if any(a.get("id") == "destroy" for a in ev.get("actions", []))]
    if picked_shows:
        empty.append("picked hearts are shown empty, not destroyed")
    results.append((bool(empty) and not (picked_destroys and not picked_shows), "; ".join(empty) or f"no empty state found for {kinds or 'no heart type'}"))
    literal_compares = set()
    for ev, _ in rows:
        for c in ev.get("conditions", []):
            if pat.search(values([c])):
                # The operator is a number too ("comparison": 4 is "greater or equal"); only the operands count.
                operands = " | ".join(str(v) for k, v in params(c).items() if k != "comparison")
                literal_compares |= set(re.findall(r"(?<![\w.])\d+(?![\w.])", operands))
    literal_compares -= {"0", "1"}
    results.append((bool(lives) and len(literal_compares) <= 2, f"literal numbers the count is compared with: {sorted(literal_compares) or 'none'}"))
    texts = [i for i in hud if i["type"] in ("ScoreText", "TimerText") or plugin_id(project, i["type"]) == "Text"]
    if hearts:
        l, t, r, b = box_around(hearts)
        view_w, view_h = view_of(project)
        centred = abs((l + r) / 2 - view_w / 2) <= 0.5
        inside = l >= 0 and t >= 0 and r <= view_w and b <= view_h
        clear = not any(min(r, box_of(x)[2]) - max(l, box_of(x)[0]) > 0.5 and min(b, box_of(x)[3]) - max(t, box_of(x)[1]) > 0.5 for x in texts)
        results.append((centred and inside and clear, f"hearts box ({l:g},{t:g})-({r:g},{b:g}) centred {centred}, inside {inside}, clear of text {clear}"))
    else:
        results.append((False, "no heart instance on the UI layer"))
    results.append(generator_is_source(run))
    return results


def grade_lives_as_hearts_pixel(run: Path) -> list[tuple[bool, str]]:
    """The hearts case on the stand-in at 320x180, then what pixel art asks of them, before the generator's
    rerun: whole pixels in 8 px units, images with the alpha values and the colours write_png() allows a
    pixel-art image, and the project still scaled by whole numbers and sampled Nearest."""
    results = grade_lives_as_hearts(run)
    project = run / "project"
    settings = settings_of(project)
    unit, palette = settings["UNIT"], {tuple(c) for c in settings["PALETTE"].values()}
    hearts = [i for i in hud_instances(project) if re.search(r"heart|life|lives", i["type"], re.I)]
    off = [f"{i['type']}@({i['world']['x']:g},{i['world']['y']:g} {i['world']['width']:g}x{i['world']['height']:g})"
           for i in hearts if not all(float(i["world"][k]).is_integer() for k in ("x", "y"))
           or any(float(i["world"][k]) % unit for k in ("width", "height"))]
    grid = (bool(hearts) and not off, f"{len(hearts)} heart instance(s); off whole pixels or {unit} px units: "
                                      f"{off or 'none'}")
    drawn = pixel_art_images(project, sorted({i["type"] for i in hearts}), palette)
    try:
        props = json.loads((project / "project.c3proj").read_text(encoding="utf-8-sig"))["properties"]
    except (OSError, ValueError, KeyError):
        props = {}
    scaled = (props.get("fullscreenMode") == "integer-scale-outer" and props.get("sampling") == "nearest",
              f"fullscreenMode {props.get('fullscreenMode')}, sampling {props.get('sampling')}")
    return results[:-1] + [grid, drawn, scaled] + results[-1:]


def pixel_art_images(project: Path, kinds: list[str], palette: set[tuple]) -> tuple[bool, str]:
    """Whether every image of the types is drawn as pixel art: at most one alpha value besides clear and opaque,
    the shadow's, and every opaque colour a colour of the generator's PALETTE when it is known."""
    try:
        from PIL import Image
    except ImportError:
        return False, "Pillow is not installed: pip install pillow"
    found, bad = 0, []
    for kind in kinds:
        for png in sorted((project / "images").glob(f"{kind.lower()}*.png")):
            try:
                with Image.open(png) as im:
                    counts = im.convert("RGBA").getcolors(1 << 20) or []
            except OSError:
                continue
            found += 1
            alphas = {c[3] for _, c in counts} - {0, 255}
            stray = sorted({c[:3] for _, c in counts if c[3] == 255} - palette) if palette else []
            if len(alphas) > 1 or stray:
                bad.append(f"{png.name}: alpha {sorted(alphas) or 'clear and opaque'}"
                           + (f", colours off PALETTE {stray[:3]}" if stray else ""))
    return (found > 0 and not bad, f"{found} image(s) of {kinds or 'no heart type'}; "
                                   f"not pixel art: {bad or 'none'}")


NAVY = (0x02, 0x30, 0x47)


def contrast(a: tuple, b: tuple) -> float:
    """The contrast ratio of two RGB colours, 1 to 21 (WCAG 2.2, relative luminance)."""
    def luminance(c: tuple) -> float:
        lin = [v / 255 / 12.92 if v / 255 <= 0.04045 else ((v / 255 + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def rgb255(colour: list) -> tuple:
    return tuple(round(c * 255) for c in colour[:3])


def one_colour(project: Path, kind: str) -> tuple | None:
    """The colour of a type whose first image shows one colour and is opaque in its middle, else None: a
    hollow box, a key's frame, lies round a label and not behind it."""
    try:
        from PIL import Image
    except ImportError:
        return None
    for png in sorted((project / "images").glob(f"{kind.lower()}*.png")):
        try:
            with Image.open(png) as im:
                rgba = im.convert("RGBA")
                shown = {c[:3] for n, c in (rgba.getcolors(1 << 20) or []) if c[3] == 255}
                middle = rgba.getpixel((rgba.width // 2, rgba.height // 2))[3] == 255
        except OSError:
            continue
        return next(iter(shown)) if len(shown) == 1 and middle else None
    return None


def colours_of(project: Path, kind: str) -> set[tuple]:
    """The opaque colours of a type's first image; empty when it has none or PIL is missing."""
    try:
        from PIL import Image
    except ImportError:
        return set()
    for png in sorted((project / "images").glob(f"{kind.lower()}*.png")):
        try:
            with Image.open(png) as im:
                return {c[:3] for n, c in (im.convert("RGBA").getcolors(1 << 20) or []) if c[3] == 255}
        except OSError:
            continue
    return set()


def background_colours(layout: dict, project: Path) -> tuple[set[tuple], str]:
    """What the viewport shows behind the game: from the Background layer down through the layers under it,
    such as the template's parallax-0 layer of a checker, the image of the first instance that covers the
    viewport (a backdrop), else the colour of the first opaque layer (the template's paper)."""
    layers = layout.get("layers", [])
    names = [layer.get("name", "").lower() for layer in layers]
    if "background" not in names:
        return set(), "no Background layer"
    for layer in reversed(layers[:names.index("background") + 1]):
        cover = next((i for i in reversed(layer.get("instances", []))
                      if contains(box_of(i), (0, 0, *view_of(project))) and colours_of(project, i["type"])), None)
        if cover:
            return colours_of(project, cover["type"]), f"{cover['type']} covering the viewport"
        if not layer.get("isTransparent", True):
            return {rgb255(layer["backgroundColor"])}, f"the {layer['name']} layer's colour"
    return set(), "a transparent Background layer and nothing covering the viewport"


def grade_readable_on_a_dark_background(run: Path) -> list[tuple[bool, str]]:
    project = run / "project"
    results = [checker_line(project)]
    try:
        layout = json.loads((project / "layouts" / "Game.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return results + [(False, "layouts/Game.json is not readable JSON")] * 5
    # The template's paper is the Background layer's colour, unless a backdrop covers the layer. Its labels
    # are dark ink on white, so the navy is what puts readability at stake.
    shown, source = background_colours(layout, project)
    dark = bool(shown) and all(abs(a - b) <= 40 for colour in shown for a, b in zip(colour, NAVY))
    results.append((dark, f"{source}: {sorted(shown) or 'no colour'}"))
    hud = hud_of(layout)
    texts = [i for i in hud if plugin_id(project, i["type"]) == "Text"]
    # The first round deals fewer coins than six; the label starts from the count, not a number.
    left = [i for i in texts if re.search(r"left", str(i["properties"].get("text", "")), re.I)]
    rows = sheet_rows(project)
    changed = {params(a).get("variable") or params(a).get("instance-variable")
               for ev, _ in rows for a in ev.get("actions", []) if a.get("id") in SET_VALUE}
    setters = [a for ev, _ in rows for a in ev.get("actions", []) if a.get("id") == "set-text"
               and a.get("objectClass") in {i["type"] for i in left}]
    counted = [a for a in setters if re.search(r"\.Count\b", values([a]))
               or set(re.findall(r"[A-Za-z_]\w*", values([a]))) & {c for c in changed if c}]
    results.append((bool(left) and bool(counted), f"labels saying Left: {[i['type'] for i in left] or 'none'}; "
                                                  f"set-text from the coins left: {len(counted)} of {len(setters)}"))
    score = next((i for i in texts if i["type"] == "ScoreText"), None)
    if left:
        l, t, r, b = box_of(left[0])
        off = score is None or not (min(r, box_of(score)[2]) - max(l, box_of(score)[0]) > 0.5
                                    and min(b, box_of(score)[3]) - max(t, box_of(score)[1]) > 0.5)
        view_w, view_h = view_of(project)
        placed = l >= 0 and t >= 0 and r <= view_w and b <= view_h and r >= view_w * 3 / 4 and t <= view_h / 4 and off
        results.append((placed, f"{left[0]['type']} box ({l:g},{t:g})-({r:g},{b:g}), clear of ScoreText {off}"))
    else:
        results.append((False, "no Left label on the UI layer"))
    verdicts, ok = [], bool(texts) and bool(shown)
    for i in texts:
        fg = rgb255(i["properties"].get("color", [1, 1, 1, 1]))
        panel = next((colour for j in hud if j is not i and plugin_id(project, j["type"]) != "Text"
                      and contains(box_of(j), box_of(i)) and (colour := one_colour(project, j["type"]))), None)
        behind = {panel} if panel else shown
        ratio = min((contrast(fg, b) for b in behind), default=0)
        ok = ok and ratio >= 4.5
        verdicts.append(f"{i['type']} {fg} on {'panel ' if panel else ''}{sorted(behind)}: {ratio:.1f}:1")
    results.append((ok, "; ".join(verdicts) or "no Text on the UI layer"))
    results.append(generator_is_source(run))
    return results


def fixture_types(run: Path) -> set[str]:
    """The object types the case's fixture had, from fixture.json; empty when it lists none."""
    try:
        listed = json.loads((run / "fixture.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    return {Path(k).stem for k in listed if k.startswith("objectTypes/") and k.endswith(".json")}


def grade_hud_over_a_scrolling_level(run: Path) -> list[tuple[bool, str]]:
    """A health bar and a goal label the run added to the scrolling level's HUD through the generator: the
    level still scrolls, what it added is on the UI layer at parallax 0, the bar MARGIN inside the left edge
    under the level tag, the label top centre and set from Player.X, the HUD inside the viewport and apart."""
    project = run / "project"
    results = [checker_line(project)]
    try:
        layout = json.loads((project / "layouts" / "Game.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return results + [(False, "layouts/Game.json is not readable JSON")] * (
            len(CASES["hud-over-a-scrolling-level"]["assertions"]) - 2) + [generator_is_source(run)]
    settings = settings_of(project)
    view_w, view_h, margin = settings["VIEW_W"], settings["VIEW_H"], settings["MARGIN"]
    layers = layout.get("layers", [])
    player = next((i for layer in layers for i in layer.get("instances", []) if i.get("type") == "Player"), None)
    behaviors = sorted((player or {}).get("behaviors", {}))
    results.append((layout.get("width", 0) > view_w and {"Platform", "ScrollTo"} <= set(behaviors),
                    f"layout {layout.get('width')}x{layout.get('height')} on a {view_w}x{view_h} viewport; Player's "
                    f"behaviors: {behaviors if player else 'no Player'}"))

    had = fixture_types(run) or set(play_cases.STAND_IN_HUD)
    ui = next((layer for layer in layers if layer.get("name", "").lower() in HUD_LAYERS), None)
    hud = hud_of(layout)
    added = [i for i in hud if i["type"] not in had]
    shown = {i["type"] for i in added}
    elsewhere = sorted({i["type"] for layer in layers if layer is not ui for i in layer.get("instances", [])
                        if i["type"] in shown or (i["type"] not in had and plugin_id(project, i["type"]) == "Text")})
    still = ui is not None and ui.get("parallaxX") == 0 and ui.get("parallaxY") == 0
    results.append((still and bool(added) and not elsewhere,
                    f"UI layer parallax {(ui or {}).get('parallaxX')}, {(ui or {}).get('parallaxY')}; added there: "
                    f"{sorted(shown) or 'nothing'}; added on a world layer: {elsewhere or 'none'}"))

    tag = next((i for i in hud if i["type"] == "LevelTag"), None)
    bar = [i for i in added if plugin_id(project, i["type"]) != "Text"]
    if bar and tag:
        l, t, r, b = box_around(bar)
        under = t >= box_of(tag)[3] - 0.5 and t <= view_h / 4
        results.append((abs(l - margin) <= 0.5 and under, f"bar {sorted({i['type'] for i in bar})} box ({l:g},{t:g})-"
                                                           f"({r:g},{b:g}); LevelTag's bottom {box_of(tag)[3]:g}, "
                                                           f"MARGIN {margin}"))
    else:
        results.append((False, "no LevelTag on the UI layer" if not tag else "no non-text instance added to the UI layer"))

    goal = [i for i in added if plugin_id(project, i["type"]) == "Text"
            and re.search(r"goal", str(i["properties"].get("text", "")), re.I)]
    if goal:
        l, t, r, b = box_of(goal[0])
        results.append((abs((l + r) / 2 - view_w / 2) <= 0.5 and t <= view_h / 4,
                        f"{goal[0]['type']} box ({l:g},{t:g})-({r:g},{b:g}) in a {view_w}x{view_h} viewport"))
    else:
        results.append((False, "no added Text on the UI layer says Goal"))
    # The text reads Player.X, or a variable an action sets from it, or a function whose events read it
    rows = sheet_rows(project)
    reads_x = re.compile(r"\bPlayer\.X\b")
    derived = {params(a).get("variable") for ev, _ in rows for a in ev.get("actions", [])
               if a.get("id") in SET_VALUE and reads_x.search(values([a]))}
    derived |= {ev.get("functionName") for ev, _ in rows if ev.get("eventType") == "function-block"
                and any(reads_x.search(values(e.get("conditions", []) + e.get("actions", []))) for e, _ in walk([ev]))}
    words = re.compile("|".join([r"\bPlayer\.X\b", *(rf"\b{re.escape(n)}\b" for n in sorted(derived - {None, ""}))]))
    setters = [a for ev, _ in rows for a in ev.get("actions", []) if a.get("id") == "set-text"
               and a.get("objectClass") in {i["type"] for i in goal}]
    from_x = [a for a in setters if words.search(values([a]))]
    results.append((bool(from_x), f"set-text on the goal label: {len(setters)}, from Player.X: {len(from_x)}; "
                                  f"names set from Player.X: {sorted(derived - {None, ''}) or 'none'}"))

    apart = outside_of(hud, view_w, view_h) + overlaps_of(project, hud)
    results.append((bool(hud) and not apart, f"past the viewport or overlapping: {apart or 'none'}"))
    results.append(generator_is_source(run))
    return results


def triggered(project: Path):
    """A test of whether a condition is a trigger, from the clone's schemas."""
    p = c3.Project(project, PLUGIN, "en-US", c3.Findings())
    return lambda c: bool((p.ace_entry("conditions", c) or {}).get("isTrigger"))


def original_sids(run: Path, rows: list, sheet: str) -> tuple[bool, str]:
    original = json.loads((run / "fixture.json").read_text(encoding="utf-8")).get(f"eventSheets/{sheet}.sids", [])
    have = {ev.get("sid") for ev, _ in rows}
    lost = [s for s in original if s not in have]
    return bool(original) and not lost, f"{len(original) - len(lost)} of {len(original)} original event sids present"


WASD = {87: "up", 65: "left", 83: "down", 68: "right"}
ARROWS = {38: "up", 37: "left", 40: "down", 39: "right"}


def grade_walk_with_wasd(run: Path) -> list[tuple[bool, str]]:
    """Each letter holds its control: Simulate control under Key is down with no trigger in the branch,
    since a simulated control holds for the tick it runs in."""
    project = run / "project"
    code, out = checker(project)
    original = set(json.loads((run / "fixture.json").read_text(encoding="utf-8")).get("eventSheets/event sheet 1.json.sids", []))
    # The example warns on a Spawn another object of its own; a warning on an event the run added names a new sid.
    warnings = [line for line in out.splitlines() if line.startswith("warning:")
                and not ((m := re.search(r"\(sid (\d+)\)", line)) and int(m.group(1)) in original)]
    results = [(code == 0, f"exit {code}: {out.splitlines()[0] if code else out.splitlines()[-1]}"),
               (not warnings, warnings[0] if warnings else "no warning line on an added event")]
    try:
        events = json.loads((project / "eventSheets" / "event sheet 1.json").read_text(encoding="utf-8"))["events"]
    except (OSError, ValueError, KeyError):
        return results + [(False, "eventSheets/event sheet 1.json is not readable JSON")] * 3
    rows = list(walk(events))
    is_trigger = triggered(project)
    held: dict[int, set[str]] = {}      # key code -> the controls simulated while it is down
    pressed = []
    for ev, above in rows:
        conds = conditions_over(ev, above)
        moves = [a for a in ev.get("actions", []) if a.get("id") == "simulate-control" and a.get("objectClass") == "Player"]
        if not moves:
            continue
        # Key is down takes the key as a code, Key code is down as an expression.
        keys = [params(c).get("key") for c in conds if c.get("id") == "key-is-down"] + \
            [int(k) for c in conds if c.get("id") == "key-code-is-down"
             if (k := str(params(c).get("keycode", "")).strip()).isdigit()]
        triggers = [c for c in conds if is_trigger(c)]
        for a in moves:
            control = params(a).get("control")
            if triggers:
                pressed.append(f"{control} under {triggers[0].get('id')}")
                continue
            for k in keys:
                if isinstance(k, int):
                    held.setdefault(k, set()).add(control)
    missing = [f"{chr(k)} {d}" for k, d in WASD.items() if d not in held.get(k, set())]
    results.append((not missing and not pressed, "held: " + ", ".join(f"{chr(k)} {d}" for k, d in WASD.items()
                    if d in held.get(k, set())) + (f"; missing: {missing}" if missing else "")
                    + (f"; under a trigger: {pressed}" if pressed else "")))
    layout = json.loads((project / "layouts" / "layout 1.json").read_text(encoding="utf-8"))
    on = [i.get("behaviors", {}).get("8Direction", {}).get("properties", {}).get("default-controls")
          for layer in layout["layers"] for i in layer.get("instances", []) if i.get("type") == "Player"]
    arrows = all(d in held.get(k, set()) for k, d in ARROWS.items())
    results.append((bool(on) and all(on) or arrows, f"Default controls {on}, arrows held under Key is down: {arrows}"))
    results.append(original_sids(run, rows, "event sheet 1.json"))
    return results


def seconds_of(a: dict) -> float:
    try:
        return float(str(params(a).get("seconds", "")).strip())
    except ValueError:
        return 0.0


# Conditions that keep a Start timer from running in every tick, besides a trigger
PACED = {"trigger-once-while-true", "every-x-seconds", "is-timer-running"}


def grade_countdown_between_rounds(run: Path) -> list[tuple[bool, str]]:
    """The countdown starts once when the round ends, shows 3, 2 and 1, and the restart waits for it."""
    project = run / "project"
    results = checker_and_warnings(project)
    events = sheet_of(project)
    if events is None:
        return results + [(False, "eventSheets/Game.json is not readable JSON")] * 4
    rows = list(walk(events))
    is_trigger = triggered(project)
    starts = [(a, conditions_over(ev, above)) for ev, above in rows for a in ev.get("actions", []) if a.get("id") == "start-timer"]
    every_tick = [a for a, conds in starts if not any(is_trigger(c) or c.get("id") in PACED for c in conds)]
    results.append((not every_tick, f"{len(starts)} Start timer, {len(every_tick)} in an event that runs every tick"
                    + (": " + "; ".join(values([a]) for a in every_tick) if every_tick else "")))

    texts = [a for ev, _ in rows for a in ev.get("actions", []) if a.get("id") == "set-text"
             and a.get("objectClass") == "ScoreText" and re.search(r"next\s*round", values([a]), re.I)]
    reads = [a for a in texts if re.search(r"&\s*[A-Za-z(]", values([a]))]
    counted = {n for a in texts for n in re.findall(r"\b([123])\b", values([a]))}
    results.append((bool(reads) or counted >= {"1", "2", "3"},
                    f"{len(texts)} Set text with Next round; " + ("reads " + values(reads[:1]) if reads else f"literals {sorted(counted)}")))

    after = []
    for ev, above in rows:
        actions = ev.get("actions", [])
        for i, a in enumerate(actions):
            if a.get("id") != "restart-layout":
                continue
            conds = conditions_over(ev, above)
            waited = sum(seconds_of(w) for w in actions[:i] if w.get("id") == "wait") + \
                sum(seconds_of(w) for e in above for w in e.get("actions", []) if w.get("id") == "wait")
            on_timer = any(c.get("id") == "on-timer" for c in conds)
            reaches_0 = any(re.search(r"(?:^|\|\s*)0(?:\.0)?\s*(?:\||$)", values([c])) for c in conds
                            if c.get("id") in ("compare-eventvar", "compare-two-values", "compare-instance-variable")
                            and ".count" not in values([c]).lower())
            after.append((on_timer or waited >= 3 or reaches_0,
                          f"Restart layout {'under On timer' if on_timer else f'after {waited:g} s of Wait'}"
                          + (", under a test of 0" if reaches_0 else "")))
    results.append((any(ok for ok, _ in after), "; ".join(said for _, said in after) or "no Restart layout"))
    results.append(original_sids(run, rows, "Game.json"))
    return results


SEEDED = re.compile(r"^6(?:333|444|555|777|888)\d{11}$")     # the sids make_fixtures.py gives the entries it seeds


def game_sids(run: Path, rows: list) -> tuple[bool, str]:
    """Whether every event of the fixture's Game.json is still there, the seeded ones left out."""
    original = json.loads((run / "fixture.json").read_text(encoding="utf-8")).get("eventSheets/Game.json.sids", [])
    game = [s for s in original if not SEEDED.match(str(s))]
    have = {ev.get("sid") for ev, _ in rows}
    lost = [s for s in game if s not in have]
    return bool(game) and not lost, f"{len(game) - len(lost)} of {len(game)} game event sids present"


def grade_fix_wasd_twitch(run: Path) -> list[tuple[bool, str]]:
    """The seeded On key pressed events walk for one tick a press; the fix holds each key with Key is down.
    The checks are walk-with-wasd's, with the seeded events counted as the run's own."""
    results = grade_walk_with_wasd(run)
    original = json.loads((run / "fixture.json").read_text(encoding="utf-8")).get("eventSheets/event sheet 1.json.sids", [])
    example = {s for s in original if not SEEDED.match(str(s))}
    code, out = checker(run / "project")
    warnings = [line for line in out.splitlines() if line.startswith("warning:")
                and not ((m := re.search(r"\(sid (\d+)\)", line)) and int(m.group(1)) in example)]
    results[1] = (not warnings, warnings[0] if warnings else "no warning line on an added or seeded event")
    events = json.loads((run / "project" / "eventSheets" / "event sheet 1.json").read_text(encoding="utf-8"))["events"]
    have = {ev.get("sid") for ev, _ in walk(events)}
    lost = [s for s in example if s not in have]
    results[4] = (bool(example) and not lost, f"{len(example) - len(lost)} of {len(example)} example event sids present")
    return results


def grade_fix_next_round(run: Path) -> list[tuple[bool, str]]:
    """The seeded round end starts its Timer in every tick; the fix starts it once, and Restart layout
    and Set beat still run once per round."""
    project = run / "project"
    results = checker_and_warnings(project)
    events = sheet_of(project)
    if events is None:
        return results + [(False, "eventSheets/Game.json is not readable JSON")] * 3
    rows = list(walk(events))
    is_trigger = triggered(project)
    acts = [(a, conditions_over(ev, above)) for ev, above in rows for a in ev.get("actions", [])]
    every_tick = [a for a, conds in acts if a.get("id") == "start-timer"
                  and not any(is_trigger(c) or c.get("id") in PACED for c in conds)]
    results.append((not every_tick, f"{sum(a.get('id') == 'start-timer' for a, _ in acts)} Start timer, "
                    f"{len(every_tick)} in an event that runs every tick"))
    once = [(a, conds) for a, conds in acts if a.get("id") == "restart-layout"
            or (a.get("id") == "set-eventvar-value" and params(a).get("variable") == "beat")]
    loose = [a["id"] for a, conds in once if not any(is_trigger(c) or c.get("id") == "trigger-once-while-true" for c in conds)]
    results.append((bool(once) and not loose, f"{len(once)} Restart layout or Set beat, every tick: {loose or 'none'}"))
    results.append(game_sids(run, rows))
    return results


TURN_CHANGES = {"set-eventvar-value", "toggle-boolean-eventvar", "add-to-eventvar", "subtract-from-eventvar"}


def grade_fix_turn_flip(run: Path) -> list[tuple[bool, str]]:
    """The seeded Else passes the turn in every tick; the fix passes it once per tapped coin: in the tap's
    branch or another trigger's, in the custom action or function the tap calls, or in an event that resets
    a variable it tests."""
    project = run / "project"
    results = checker_and_warnings(project)
    events = sheet_of(project)
    if events is None:
        return results + [(False, "eventSheets/Game.json is not readable JSON")] * 2
    rows = list(walk(events))
    is_trigger = triggered(project)
    once, every_tick = [], []
    for ev, above in rows:
        for a in ev.get("actions", []):
            given = params(a)
            if given.get("variable") != "side" or a.get("id") not in TURN_CHANGES \
                    or (a.get("id") == "set-eventvar-value" and str(given.get("value")).strip() == "1"):
                continue
            conds = conditions_over(ev, above)
            in_block = any(e.get("eventType") in ("function-block", "custom-ace-block") for e in (*above, ev))
            tested = {params(c).get("variable") for c in conds if c.get("id") == "compare-eventvar"}
            reset = {params(b).get("variable") for e in (*above, ev) for b in e.get("actions", [])
                     if b.get("id") == "set-eventvar-value"} - {"side"}
            (once if in_block or any(is_trigger(c) for c in conds) or tested & reset else every_tick).append(values([a]))
    results.append((bool(once) and not every_tick, f"side changes once per tap: {once or 'nowhere'}"
                    + (f"; in every tick: {every_tick}" if every_tick else "")))
    results.append(game_sids(run, rows))
    return results


TURN_NAME = re.compile(r"turn|player|side|current|whose|active", re.I)
# A time or a score is not the turn, though its name may say player or current: turnTimeLeft, player1Score.
NOT_TURN = re.compile(r"time|timer|sec|clock|left|limit|count|remain|score|point", re.I)


def grade_two_player_turns(run: Path) -> list[tuple[bool, str]]:
    """The turn variable is the run's own: its name says whose turn it is, or ScoreText's text reads it, and it
    is not named for a time or a score. Each change of it runs once: under a trigger, in a function or custom
    action, or in an event that resets a variable it tests, a function the event calls included. A flip reads
    the variable (3 - turn, Toggle) or runs under a condition that tests it; a set to a fixed value is a reset,
    which also runs once under Trigger once or Every X seconds. One flip sits under the tap or in a function or
    custom action. A change under On start of layout is not read."""
    project = run / "project"
    results = checker_and_warnings(project)
    events = sheet_of(project)
    if events is None:
        return results + [(False, "eventSheets/Game.json is not readable JSON")] * 3
    rows = list(walk(events))
    texts = [a for ev, _ in rows for a in ev.get("actions", [])
             if a.get("objectClass") == "ScoreText" and a.get("id") == "set-text"]

    def reads(name: str, text: str) -> bool:
        return bool(re.search(rf"(?<![\w.]){re.escape(name)}(?!\w)", text, re.I))

    new = {ev["name"] for ev, _ in rows if ev.get("eventType") == "variable"} - ORIGINAL_GLOBALS
    turns = {n for n in new if (TURN_NAME.search(n) or reads(n, values(texts))) and not NOT_TURN.search(n)}
    sets_in = {ev.get("functionName"): {params(a).get("variable") for e, _ in walk([ev])
                                        for a in e.get("actions", []) if a.get("id") == "set-eventvar-value"}
               for ev, _ in rows if ev.get("eventType") == "function-block"}
    is_trigger = triggered(project)
    once, every_tick, on_tap = [], [], []
    for ev, above in rows:
        conds = conditions_over(ev, above)
        if any(c.get("id") == "on-start-of-layout" for c in conds):
            continue
        for a in ev.get("actions", []):
            given = params(a)
            name = given.get("variable")
            if name not in turns or a.get("id") not in TURN_CHANGES:
                continue
            in_block = any(e.get("eventType") in ("function-block", "custom-ace-block") for e in (*above, ev))
            # the variables its conditions test, and those its branch or the functions it calls set
            tested = {params(c).get("variable") for c in conds if c.get("id") == "compare-eventvar"}
            tested |= {w for c in conds if c.get("id") in ("compare-two-values", "evaluate-expression")
                       for w in re.findall(r"[A-Za-z_]\w*", values([c]))}
            branch = [b for e in (*above, ev) for b in e.get("actions", [])]
            reset = {params(b).get("variable") for b in branch if b.get("id") == "set-eventvar-value"}
            reset = (reset | {v for b in branch for v in sets_in.get(b.get("callFunction"), ())}) - {name}
            flip = a.get("id") != "set-eventvar-value" or reads(name, str(given.get("value", ""))) or name in tested
            # Trigger once runs a reset once, but a flip once a round
            paced = any(is_trigger(c) for c in conds) or (not flip and any(
                c.get("id") in ("trigger-once-while-true", "every-x-seconds") for c in conds))
            (once if in_block or paced or tested & reset else every_tick).append(f"{name}: {values([a])}")
            if flip and (in_block or any(is_trigger(c) and c.get("objectClass") in ("Touch", "Mouse") for c in conds)):
                on_tap.append(f"{name}: {values([a])}")
    results.append((bool(on_tap) and not every_tick, f"turn variables {sorted(turns) or 'none'}; changed once: "
                    f"{once or 'nowhere'}; on a tap: {on_tap or 'nowhere'}"
                    + (f"; in every tick: {every_tick}" if every_tick else "")))
    said = [values([a]) for a in texts if any(reads(n, values([a])) for n in turns) or re.search(r"player", values([a]), re.I)]
    results.append((bool(said), f"ScoreText texts that say whose turn: {said or 'none'}"))
    results.append(original_sids(run, rows, "Game.json"))
    return results


def drag_examples() -> dict[str, str]:
    """The official examples that use the Drag & Drop behavior, id to name."""
    out = {}
    for path in sorted((DATA / "c3-examples" / "en-US").glob("*.json")):
        e = json.loads(path.read_text(encoding="utf-8"))
        if "DragnDrop" in e.get("used-addons", {}).get("behaviors", []):
            out[e["id"]] = e.get("name", "")
    return out


def drop_events(example: str) -> set[int]:
    """The event numbers at which an example's sheets hold On drop, as print_sheet.py numbers them, over its
    folders: <id>, or <id>-js and <id>-ts."""
    folder = c3.siblings_folder(REPO) / "Construct-Example-Projects" / "example-projects"
    numbers = set()
    for end in ("", "-js", "-ts"):
        if (folder / f"{example}{end}" / "project.c3proj").is_file():
            out = subprocess.run([sys.executable, str(SKILL / "scripts" / "print_sheet.py"), "--project",
                                  str(folder / f"{example}{end}"), "--rag", str(PLUGIN), "--limit", "0"],
                                 capture_output=True, text=True, encoding="utf-8",
                                 env=dict(os.environ, PYTHONIOENCODING="utf-8")).stdout
            numbers |= {int(n) for n in re.findall(r"^\s*(\d+)\s+.*\bOn \w+ drop\b", out, re.M)}
    return numbers


# The words an answer uses for each trap in the pitfall entries on dragging
DRAG_TRAPS = {"moves only when the pointer moves": r"only\s+(?:when|while|if)\s+the\s+(?:pointer|mouse|finger|cursor)\s+"
              r"(?:moves|is\s+moving)|set\s+position\b.{0,80}\boverwrit",
              "a slot reads empty": r"collisions?\s+(?:are\s+|is\s+)?(?:disabled|off)|reads?\s+(?:as\s+)?empty|lands?\s+on\s+top",
              "the Mouse object ignores a finger": r"\bmouse\b.{0,80}\b(?:ignores?|only)\b.{0,40}\b(?:finger|touch|pen)",
              "Pick children in On drop": r"pick\s+children"}


def grade_find_a_drag_example(run: Path) -> list[tuple[bool, str]]:
    answer = answer_of(run)
    named = {i: n for i, n in drag_examples().items()
             if re.search(rf"(?<![\w-]){re.escape(i)}(?![\w-])", answer, re.I) or (n and re.search(re.escape(n), answer, re.I))}
    numbers = event_numbers(answer)
    drops = {i: sorted(drop_events(i)) for i in named}
    hit = {i: sorted(set(d) & set(numbers)) for i, d in drops.items() if set(d) & set(numbers)}
    traps = [k for k, pattern in DRAG_TRAPS.items() if re.search(pattern, answer, re.I | re.S)]
    return [(bool(named), f"Drag & Drop examples the answer names: {sorted(named) or 'none'}"),
            (bool(hit), f"event numbers the answer gives: {numbers or 'none'}; On drop in the named examples: "
                        f"{drops or 'none'}"),
            (bool(traps), f"traps named: {traps or 'none'}"),
            unchanged(run)]


def grade_script_shift_and_edges(run: Path) -> list[tuple[bool, str]]:
    path = run / "project" / "scripts" / "main.ts"
    code = path.read_text(encoding="utf-8") if path.exists() else ""
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", code, flags=re.S)      # a comment can name what the code does not do
    code = re.sub(r"getLayout\([^)]*\)", "layout", code)            # a layout got by name is read as runtime.layout
    keys = [k or n for k, n in re.findall(r"isKeyDown\(\s*(?:[\"'`](\w+)[\"'`]|(\d+))\s*\)", code)]
    arrows = {"ArrowRight", "ArrowLeft", "ArrowUp", "ArrowDown"} - set(keys)
    named = [k for k in keys if k.lower().startswith("shift") or k == "16"]
    shift = [k for k in named if k in ("ShiftLeft", "ShiftRight", "16")]      # isKeyDown matches a code, never "Shift"
    double = re.search(r"\*\s*2(?![\d.])|(?<![\w.])2\s*\*|\?\s*2(?![\d.])|=\s*2\s*;|\b400\b", code)
    layout = [w for w in ("width", "height") if re.search(rf"layout\.{w}\b", code)]
    own = re.search(r"(?<!layout)\.(?:width|height)\b|getBoundingBox", code)
    return [(bool(code) and not arrows, f"arrow keys tested: {sorted(set(keys) & {'ArrowRight', 'ArrowLeft', 'ArrowUp', 'ArrowDown'})}"
                                        + (f"; missing: {sorted(arrows)}" if arrows else "")),
            (bool(shift and double), f"Shift keys tested: {named or 'none'}"
                                     + ("; isKeyDown matches none of them" if named and not shift else "")
                                     + f"; doubled: {double.group(0) if double else 'no'}"),
            (len(layout) == 2 and bool(own), f"layout sides read: {layout or 'none'}; the player's size: "
                                             f"{own.group(0) if own else 'not read'}"),
            # open_in_editor.py --typescript writes scripts/ts-defs/ and scripts/tsconfig.json
            unchanged(run, ("scripts/main.ts", "scripts/ts-defs/", "scripts/tsconfig.json"))]


def grade_platform_state_in_chinese(run: Path) -> list[tuple[bool, str]]:
    project = run / "project"
    read = [p.relative_to(project).as_posix() for p in sorted((project / ".tmp").rglob("*.json"))
            if "behaviors.platform.properties.max-speed" in p.read_text(encoding="utf-8", errors="replace")]
    answer = answer_of(run)
    floor = re.search(r"地面上|站在地|落地|着地|落在地|on\s+the\s+(?:floor|ground)", answer, re.I)
    numbers = [n for n in ("330", "650", "1500") if re.search(rf"(?<!\d){n}(?!\d)", answer)]
    texts = json.loads((DATA / "c3-lang" / "zh-CN.json").read_text(encoding="utf-8"))["text"]
    names = [texts["behaviors"]["platform"]["properties"][k]["name"] for k in ("max-speed", "jump-strength", "gravity")]
    return [(bool(read), f"state files that hold Platform's values: {read or 'none'}"),
            (bool(floor), f"on the floor: {floor.group(0) if floor else 'not said'}"),
            (len(numbers) == 3, f"values given: {numbers}"),
            (all(n in answer for n in names), "names given: " + ", ".join(n for n in names if n in answer)
             + ("; missing: " + ", ".join(n for n in names if n not in answer) if not all(n in answer for n in names) else "")),
            unchanged(run)]


def grade_design_a_catch_game(run: Path) -> list[tuple[bool, str]]:
    project = run / "project"
    design = project / "tools" / "design.json"
    if design.exists():
        p = subprocess.run([sys.executable, str(SKILL / "scripts" / "check_design.py"), str(design), "--project",
                            str(project), "--rag", str(PLUGIN), "--limit", "0"],
                           capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        lines = (p.stdout + p.stderr).strip().splitlines()
        checked = (p.returncode == 0, f"exit {p.returncode}: {lines[-1] if lines else 'no output'}")
        try:
            example = (json.loads(design.read_text(encoding="utf-8")).get("reference") or {}).get("example")
        except (ValueError, AttributeError):
            example = None
    else:
        checked, example = (False, "no tools/design.json"), None
    ids = {path.stem for path in (DATA / "c3-examples" / "en-US").glob("*.json")}
    return [checked,
            (isinstance(example, str) and example in ids, f"reference.example: {example!r}"),
            unchanged(run, ("tools/",))]


def object_types(project: Path) -> dict[str, dict]:
    """Every readable object type file of the project, by its type's name."""
    out = {}
    for path in sorted((project / "objectTypes").glob("*.json")):
        try:
            t = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out[t.get("name", path.stem)] = t
    return out


def grade_fix_open_errors_past_the_message(run: Path) -> list[tuple[bool, str]]:
    """The spark is the Sprite that Collect creates, found by that and not by its name: it needs a sid of its
    own, which the editor's message named, and an instance variable named unlike every expression of its
    plugin, the shared ones of commonAces among them, which the editor names only once the sid is fixed."""
    project = run / "project"
    results = [checker_line(project)]
    types = object_types(project)
    sids: dict = {}
    for name, t in types.items():
        sids.setdefault(t.get("sid"), []).append(name)
    shared = [names for names in sids.values() if len(names) > 1]
    results.append((bool(types) and not shared, f"object types that share a sid: {shared or 'none'}"))
    events = sheet_of(project)
    if events is None:
        return results + [(False, "eventSheets/Game.json is not readable JSON")] * 3
    rows = list(walk(events))
    collect = next((ev for ev, _ in rows if ev.get("eventType") == "custom-ace-block"), None)
    made = {params(a).get("object-to-create") for ev, above in rows if ev is collect or collect in above
            for a in ev.get("actions", []) if a.get("id") == "create-object"} - {"Coin", None}
    spark = next((n for n in sorted(made) if types.get(n, {}).get("plugin-id") == "Sprite"), None)
    if spark is None:
        return results + [(False, f"Collect creates no Sprite but the coin: {sorted(made) or 'nothing'}")] * 2 \
            + [game_sids(run, rows)]
    p = c3.Project(project, PLUGIN, "en-US", c3.Findings())
    plugin = p.schema("plugins", "Sprite")
    expressions = p.expressions_of(plugin) | p.common_expressions_of(plugin)
    ivars = [v["name"] for v in types[spark].get("instanceVariables", [])]
    clash = [v for v in ivars if v.lower() in expressions]
    results.append((not clash, f"{spark}'s instance variables {ivars}; named like an expression: {clash or 'none'}"))
    reads = re.compile(rf"\b(?:{re.escape(spark)}|self)\s*\.\s*(?:{'|'.join(map(re.escape, ivars)) or '(?!)'})\b", re.I)
    lifts = [values([a]) for ev, _ in rows for a in ev.get("actions", [])
             if a.get("objectClass") == spark and str(a.get("id", "")).startswith("tween-") and reads.search(values([a]))]
    results.append((bool(lifts), f"Collect creates {spark}; tweens of it that read its variables: {lifts or 'none'}"))
    results.append(game_sids(run, rows))
    return results


def callee_of(a: dict) -> tuple | None:
    """What a call action calls, ("function", name) or ("custom", object, name), names in lower case; None for
    any other action."""
    if "callFunction" in a:
        return "function", str(a["callFunction"]).lower()
    if "customAction" in a:
        return "custom", a.get("objectClass"), str(a["customAction"]).lower()
    return None


def defined_as(ev: dict) -> tuple | None:
    """What a function or custom action block defines, keyed as callee_of() keys its calls; None for any other
    event."""
    if ev.get("eventType") == "function-block":
        return "function", str(ev.get("functionName")).lower()
    if ev.get("eventType") == "custom-ace-block":
        return "custom", ev.get("objectClass"), str(ev.get("aceName")).lower()
    return None


def grade_fix_endless_pulse(run: Path) -> list[tuple[bool, str]]:
    """A boolean argument is the JSON true or false; the text "0" reads as true. The calls made when a coin is
    collected are those of the events under Coin's On touched and of every function or custom action reached
    from them, Collect and AddScore among them, and each passes false at a boolean parameter."""
    project = run / "project"
    results = [checker_line(project)]
    events = sheet_of(project)
    if events is None:
        return results + [(False, "eventSheets/Game.json is not readable JSON")] * 3
    rows = list(walk(events))
    blocks = {defined_as(ev): ev for ev, _ in rows if defined_as(ev)}
    slots = {key: [n for n, q in enumerate(ev.get("functionParameters", [])) if q.get("type") == "boolean"]
             for key, ev in blocks.items()}
    calls = [(callee_of(a), a.get("parameters") if isinstance(a.get("parameters"), list) else [], ev, above)
             for ev, above in rows for a in ev.get("actions", []) if callee_of(a)]

    def said(c: tuple, args: list) -> str:
        return f"{c[-1]}({', '.join(json.dumps(v) for v in args)})"
    texts = [said(c, args) for c, args, _, _ in calls
             if any(not isinstance(args[n], bool) for n in slots.get(c, []) if n < len(args))]
    results.append((not texts, f"calls with a non-boolean at a boolean parameter: {texts or 'none'}"))
    # The events a collect runs, by id: those under Coin's On touched, then the blocks their calls reach
    tops = {id(ev) for ev, above in rows if any(c.get("id") == "on-touched-object" and params(c).get("object") == "Coin"
                                                for c in conditions_over(ev, above))}
    while True:
        collected = [(c, args) for c, args, ev, above in calls if any(id(e) in tops for e in (ev, *above))]
        more = {id(blocks[c]) for c, _ in collected if c in blocks} - tops
        if not more:
            break
        tops |= more
    loose = [said(c, args) for c, args in collected
             if any(args[n] is not False for n in slots.get(c, []) if n < len(args))]
    flagged = [c[-1] for c, _ in collected if slots.get(c)]
    results.append((not loose, f"calls on a collect to a callee with a boolean parameter: {flagged or 'none'}; "
                               f"passing other than false: {loose or 'none'}"))
    results.append(game_sids(run, rows))
    return results


def grade_two_buttons_in_the_generator(run: Path) -> list[tuple[bool, str]]:
    """press() writes, for each button type, an On touched of it and an On any touch end that tests a boolean
    instance variable of that type; two types the fixture lacks have both. The checker passes them without the
    warning that the second touch end repeats the first one's trigger."""
    project = run / "project"
    results = checker_and_warnings(project)
    before = fixture_types(run)
    new = [n for n, t in object_types(project).items() if n not in before]
    rows = sheet_rows(project)
    touched = {params(c).get("object") for ev, _ in rows for c in ev.get("conditions", [])
               if c.get("id") == "on-touched-object"}
    released = {c.get("objectClass") for ev, _ in rows if any(x.get("id") == "on-any-touch-end" for x in ev.get("conditions", []))
                for c in ev.get("conditions", []) if c.get("id") == "is-boolean-instance-variable-set"}
    pressed = [n for n in new if n in touched and n in released]
    results.append((len(pressed) >= 2, f"new object types {new or 'none'}; pressed as press() writes: {pressed or 'none'}"))
    results.append(generator_is_source(run))
    return results


def grade_kept(run: Path, own_warnings: bool = True) -> list[tuple[bool, str]]:
    """The file assertions of a case whose request the plan judges: the checker passes, it warns on no event the
    run added (on none at all without own_warnings), and every event of the fixture's sheets is still there."""
    project = run / "project"
    code, out = checker(project)
    fixture = json.loads((run / "fixture.json").read_text(encoding="utf-8"))
    original = [s for k, v in fixture.items() if k.endswith(".sids") for s in v]
    # The fixture's own: the lines make_fixtures.py recorded, or a line on an event of the fixture.
    own = set(fixture.get("check_project.warnings", [])) if own_warnings else set()
    warnings = [line for line in out.splitlines() if line.startswith("warning:") and line not in own and not (
        own_warnings and (m := re.search(r"\(sid (\d+)\)", line)) and int(m.group(1)) in set(original))]
    have = {ev.get("sid") for ev, _ in sheet_rows(project)}
    lost = [s for s in original if s not in have]
    lines = out.splitlines() or [""]
    return [(code == 0, f"exit {code}: {lines[0] if code else lines[-1]}"),
            (not warnings, warnings[0] if warnings else "no warning line" + (" on an added event" if own_warnings else "")),
            (bool(original) and not lost, f"{len(original) - len(lost)} of {len(original)} original event sids present")]


def report_of(answer: str) -> str:
    """The report in the answer: its code blocks, or the whole answer when it has none."""
    blocks = re.findall(r"^\s*```[^\n]*\n(.*?)^\s*```", answer, re.M | re.S)
    return "\n".join(blocks) if blocks else answer


def grade_report_two_enemies(run: Path) -> list[tuple[bool, str]]:
    """The report of the editor's refusal that the prompt quotes: two Type mismatch lines that name only their
    place, and the two actions there, Goblin's and Orc's, each joining a label to its own IID. The objects are
    found by the IID each action reads, not by the role given them: one role for both merges the two actions."""
    report = report_of(answer_of(run))
    roles = sorted(set(re.findall(r"([\w<>]+)\.IID\b", report)))
    named = sorted({m.lower() for m in re.findall(r"\b(goblin|orc)s?\b", report, re.I)})
    results = [(len(roles) >= 2 and not named,
                f"roles whose IID the report quotes: {roles or 'none'}; names left in the report: {named or 'none'}")]
    quoted = len(re.findall(r"Type mismatch: \+ does not work with 'string' and 'number'", report))
    results.append((quoted >= 2, f"the editor's Type mismatch line {quoted} times in the report"))
    return results + [unchanged(run)]


GRADERS = {"add-countdown": grade_add_countdown, "fix-load-errors": grade_fix_load_errors,
           "keep-checking-after-compaction": grade_keep_checking_after_compaction,
           "name-the-restart-event": grade_name_the_restart_event, "find-in-a-long-sheet": grade_find_in_a_long_sheet,
           "find-in-a-big-sheet": grade_find_in_a_big_sheet,
           "lay-out-the-hud": grade_lay_out_the_hud, "show-hp-as-a-bar": grade_show_hp_as_a_bar,
           "reveal-the-gradient": grade_reveal_the_gradient, "lives-as-hearts": grade_lives_as_hearts,
           "readable-on-a-dark-background": grade_readable_on_a_dark_background,
           "lay-out-the-hud-portrait": grade_lay_out_the_hud, "lives-as-hearts-pixel": grade_lives_as_hearts_pixel,
           "hud-over-a-scrolling-level": grade_hud_over_a_scrolling_level,
           "walk-with-wasd": grade_walk_with_wasd, "countdown-between-rounds": grade_countdown_between_rounds,
           "fix-wasd-twitch": grade_fix_wasd_twitch, "fix-next-round": grade_fix_next_round,
           "fix-turn-flip": grade_fix_turn_flip, "two-player-turns": grade_two_player_turns,
           "fix-open-errors-past-the-message": grade_fix_open_errors_past_the_message,
           "fix-endless-pulse": grade_fix_endless_pulse,
           "two-buttons-in-the-generator": grade_two_buttons_in_the_generator,
           "two-player-turn-limit": grade_two_player_turns, "find-a-drag-example": grade_find_a_drag_example,
           "script-shift-and-edges": grade_script_shift_and_edges,
           "platform-state-in-chinese": grade_platform_state_in_chinese,
           "design-a-catch-game": grade_design_a_catch_game, "report-two-enemies": grade_report_two_enemies,
           "double-jump": grade_kept, "key-opens-door": grade_kept, "stay-on-screen": grade_kept, "walls-stop-the-player": grade_kept,
           "coins-in-a-ring": lambda run: grade_kept(run, own_warnings=False)}


# The columns trace.py counts from a transcript: four cost columns, then the route columns.
TRACE_COLUMNS = ("tool_calls", "lost_calls", "turns", "output_tokens", "read_skill_md", "first_script", "chain_depth",
                 "chain_end", "chain_reached", "chain_attempts", "preview_failed", "help_reads", "repeat_help",
                 "plan_refusals", "hand_edits", "lookups_before_first_edit", "data_reads", "other_clone_reads",
                 "entry_chars", "printed_command_failures", "print_sheet_chars", "whole_sheet_prints",
                 "cookbook_reads", "pointers_printed", "pointer_follows", "read_design_guide", "cookbook_misses",
                 "checked_after_last_edit", "compactions", "compaction_skill", "reread_skill_md_after_compaction",
                 "chain_depth_after_compaction", "lookups_after_compaction")
METRICS = ("pass_rate", "runtime_rate", "seconds", "tokens", "turns", "output_tokens", "tool_calls", "lost_calls",
           "play_seconds", "read_skill_md", "chain_depth", "chain_attempts", "preview_failed", "help_reads",
           "repeat_help", "plan_refusals", "hand_edits", "lookups_before_first_edit", "data_reads",
           "other_clone_reads", "entry_chars", "printed_command_failures", "print_sheet_chars", "whole_sheet_prints",
           "cookbook_reads", "pointers_printed", "pointer_follows", "read_design_guide", "cookbook_misses",
           "checked_after_last_edit", "compactions", "reread_skill_md_after_compaction",
           "chain_depth_after_compaction", "lookups_after_compaction")
COUNTED = ("first_script", "chain_end", "chain_reached", "compaction_skill", "model")    # per cell: how many runs had each
LEVELS = ("checker", "files", "runtime")      # in the order a run reaches them


def level_of(text: str) -> str:
    return "checker" if "check_project.py" in text else "files"


def spread(numbers: list[float]) -> dict | None:
    """The mean over the runs of one case and arm, with their deviation once there is more than one."""
    if not numbers:
        return None
    out = {"mean": round(statistics.mean(numbers), 3), "runs": len(numbers)}
    if len(numbers) > 1:
        out["stddev"] = round(statistics.stdev(numbers), 3)
    return out


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    """The Wilson score interval of k successes in n runs; z = 1.96 gives 95%. It stays within 0..1, and it is
    not a single point when k is 0 or n."""
    if not n:
        return [0.0, 1.0]
    p, d = k / n, 1 + z * z / n
    mid, half = (p + z * z / (2 * n)) / d, z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5 / d
    return [round(max(0.0, mid - half), 3), round(min(1.0, mid + half), 3)]


def full_runs(runs: list[dict]) -> dict:
    """How many runs passed every assertion they were scored on, of how many, with the interval."""
    k, n = sum(r["full"] for r in runs), len(runs)
    return {"k": k, "n": n, "interval_95": wilson(k, n)}


def deltas(by_case: dict[str, dict[str, dict]]) -> dict:
    """with_skill less each other arm, over the cases both ran: what the skill
    buys in pass rate and costs in seconds, tokens and tool calls."""
    out = {}
    for other in sorted({arm for arms in by_case.values() for arm in arms} - {"with_skill"}):
        both = [arms for arms in by_case.values() if "with_skill" in arms and other in arms]
        out[f"with_skill - {other}"] = {"cases": len(both), **{
            key: round(statistics.mean(arms["with_skill"][key]["mean"] - arms[other][key]["mean"] for arms in pairs), 3)
            for key in METRICS if (pairs := [a for a in both if a["with_skill"].get(key) and a[other].get(key)])}}
    return out


def counted(runs: list[dict], key: str) -> dict[str, int] | None:
    """How many of the runs have each value of key; a run without a trace does not count, one that reached no step
    counts as none."""
    traced = [r for r in runs if "tool_calls" in r]
    return dict(sorted(Counter(str(r.get(key) or "none") for r in traced).items())) if traced else None


def aggregate(cells: dict[str, dict[str, list[dict]]]) -> tuple[dict, dict]:
    """Per case and arm, the spread of each measure, the counts of the counted columns and the fully passed runs;
    per arm, the mean of its cases' means (a deviation across different cases would measure the cases), the
    counts pooled and the fully passed runs pooled."""
    by_case = {name: {arm: {"runs": runs, "full_runs": full_runs(runs),
                            **{key: spread([r[key] for r in runs if r.get(key) is not None]) for key in METRICS},
                            **{key: counted(runs, key) for key in COUNTED}}
                      for arm, runs in arms.items()} for name, arms in cells.items()}
    arms = sorted({arm for case in by_case.values() for arm in case})
    summary = {arm: {**{key: round(statistics.mean(means), 3) for key in METRICS
                        if (means := [case[arm][key]["mean"] for case in by_case.values() if arm in case and case[arm].get(key)])},
                     **{key: counted([r for case in cells.values() for r in case.get(arm, [])], key) for key in COUNTED},
                     "full_runs": full_runs([r for case in cells.values() for r in case.get(arm, [])])}
               for arm in arms}
    summary["delta"] = deltas(by_case)
    return by_case, summary


def case_flags(cells: dict[str, dict[str, list[dict]]]) -> dict[str, list[str]]:
    """The cases that tell the arms apart no more: saturated, where two or more arms ran and every run passed
    every assertion; and the cases where no run of any arm did, which are read before the case is trusted."""
    full = {name: [r["full"] for runs in arms.values() for r in runs] for name, arms in cells.items()}
    return {"saturated": sorted(n for n, f in full.items() if len(cells[n]) > 1 and all(f)),
            "none_passed": sorted(n for n, f in full.items() if len(f) > 1 and not any(f))}


def decide(iteration: Path, cells: dict[str, dict[str, list[dict]]]) -> dict | None:
    """The verdict of the iteration's decision.json over the scored runs, printed and returned; None without
    the file. A cell short of n_per_cell makes it underpowered, and a file that is not JSON or lacks a key makes
    it "not read", with the benchmark still aggregated either way."""
    path = iteration / "decision.json"
    if not path.exists():
        return None
    try:
        given = json.loads(path.read_text(encoding="utf-8"))
        arms, metric, direction, n = given.get("arms", ["with_skill", "old_skill"]), given["metric"], given["direction"], given["n_per_cell"]
        cases = given["cases"]
    except (ValueError, KeyError) as e:
        error = f'missing key "{e.args[0]}"' if isinstance(e, KeyError) else f"not JSON ({e})"
        print(f"decision.json: {error}; benchmark written without a verdict")
        return {"verdict": "not read", "error": error}
    runs = {case: {arm: [r for r in cells.get(case, {}).get(arm, []) if r.get(metric) is not None] for arm in arms}
            for case in cases}
    record = {"cases": cases, "metric": metric, "direction": direction, "arms": arms, "n_per_cell": n,
              "concurrency": given.get("concurrency")}
    gaps = [f"{case}/{r['run']}: {', '.join(r['missing'])}" for case in cases for arm in arms
            for r in cells.get(case, {}).get(arm, []) if r["missing"]]
    if gaps:
        record |= {"verdict": "incomplete", "incomplete": gaps}
        print(f"incomplete: {'; '.join(gaps)}; no verdict on {metric} until these runs are complete")
        return record
    short =[f"{case}/{arm}: {len(cell)} of {n}" for case, by_arm in runs.items() for arm, cell in by_arm.items()
             if len(cell) < n]
    if short:
        record |= {"verdict": "underpowered", "short": short}
        print(f"underpowered: {', '.join(short)}; no verdict on {metric} until the cells are full")
        return record
    test = compare.permutation_test({case: [(arm, r[metric]) for arm in arms for r in by_arm[arm]]
                                     for case, by_arm in runs.items()}, arms[0], direction)
    guards = {}
    for key, rule in given.get("guards", {}).items():
        means = [statistics.mean(statistics.mean(r[key] for r in by_arm[arm]) for by_arm in runs.values()
                                 if all(r.get(key) is not None for r in by_arm[arm])) for arm in arms]
        guards[key] = {"rule": rule, arms[0]: round(means[0], 3), arms[1]: round(means[1], 3),
                       "holds": means[0] >= means[1] if rule == "not down" else means[0] <= means[1]}
    alpha = given.get("alpha", 0.05)
    verdict = "holds" if test["p"] <= alpha and all(g["holds"] for g in guards.values()) else "does not hold"
    record |= test | {"alpha": alpha, "guards": guards, "verdict": verdict}
    print(f"decision: {compare.said(test, metric, arms, direction, len(runs))}"
          + "".join(f"; guard {k} {g['rule']} {'holds' if g['holds'] else 'fails'} ({g[arms[0]]} vs {g[arms[1]]})"
                    for k, g in guards.items())
          + f"; verdict: {verdict} at alpha {alpha}"
          + (f", {record['concurrency']} runs at once" if record["concurrency"] else ""))
    return record


def optional_json(path: Path) -> dict:
    """A file a run has only once it has reported (timing.json) or been traced (trace.json); {} without it."""
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def posix(path: str) -> str:
    """A path as a lowercase POSIX string, with a Git Bash drive (/d/...) as d:/...; for comparing paths that
    transcripts write in either form."""
    out = path.replace("\\", "/").lower()
    return f"{out[1]}:{out[2:]}" if re.match(r"^/[a-z]/", out) else out


def leaked_reads(trace: dict, iteration: Path, run: Path) -> list[str]:
    """The paths a run read that hold how it is graded: the cases, plans and graders under a dev/evals or
    dev/tests folder, of any clone, and another run's folder of this iteration. A misspelt name of the run's own
    folder (with_skill-2 for with_skill_2) names no other run."""
    others = [posix(p.as_posix()) + "/" for p in iteration.glob("*/*") if (p / "project").is_dir() and p != run]
    out = []
    for read in trace.get("outside_reads", []):
        path = posix(read["path"]).rstrip("/") + "/"
        if re.search(r"/dev/(?:evals|tests)/", path) or any(path.startswith(o) for o in others):
            out.append(read["path"])
    return list(dict.fromkeys(out))


def missing_of(run: Path, timing: dict, trace: dict, runtime: list[dict]) -> list[str]:
    """What a scored run lacks for its scores to stand: its answer, its trace (without which a write outside its
    folder goes unseen), its timing, and the play of its plan."""
    lacks = {"answer": not (run / "outputs" / "answer.md").exists(), "trace": not trace, "timing": not timing,
             "play": any(g["passed"] is None for g in runtime)}
    return [k for k, lacking in lacks.items() if lacking]


def git_state(folder: Path, *paths: str) -> dict | None:
    """The commit of the checkout at folder and whether paths in it differ from that commit; None without git."""
    try:
        head = subprocess.run(["git", "-C", str(folder), "rev-parse", "HEAD"], capture_output=True, text=True)
        status = subprocess.run(["git", "-C", str(folder), "status", "--porcelain", "--", *paths],
                                capture_output=True, text=True)
    except FileNotFoundError:   # no git on PATH: the meta names no commit rather than stopping the grading
        return None
    return {"commit": head.stdout.strip(), "dirty": bool(status.stdout.strip())} if head.returncode == 0 else None


def grading_meta(iteration: Path, args: argparse.Namespace) -> dict:
    """What this grading ran with: the grader's and the data's commits, the flags, and the commits the fixtures
    were laid out from (clone.json of make_fixtures.py)."""
    return {"graded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "grader": git_state(REPO, "dev/evals", "plugin"), "data": git_state(DATA.parent, "data"),
            "play": args.play, "release": args.release, "browser": args.browser,
            "laid_out": optional_json(iteration / "clone.json") or None}


def runtime_of(name: str, run: Path, args: argparse.Namespace) -> tuple[list[dict], float | None]:
    """The run's runtime assertions, played with --play or read from play/result.json. A case without a plan
    has none. When the plan was not played, each is listed with passed null and left out of the scores."""
    texts = play_cases.check_texts(name)
    if not texts:
        return [], None
    folder, seconds = run / "play", None
    if args.play:
        began = time.monotonic()
        result, said = play_cases.play(play_cases.plan_for(name), run / "project", folder, args.release, args.browser)
        seconds = round(time.monotonic() - began, 1)
        (folder / "seconds.txt").write_text(f"{seconds}\n", encoding="utf-8")
    elif (folder / "result.json").exists():
        result = json.loads((folder / "result.json").read_text(encoding="utf-8"))
        said = ""
        seconds = float((folder / "seconds.txt").read_text(encoding="utf-8")) if (folder / "seconds.txt").exists() else None
    else:
        return [{"text": t, "passed": None, "evidence": "not played: grade.py --play plays it", "level": "runtime"}
                for t in texts], None
    return [{"text": t, "passed": ok, "evidence": evidence, "level": "runtime"}
            for t, (ok, evidence) in zip(texts, play_cases.verdicts(name, result, said), strict=True)], seconds


def reached(graded: list[dict]) -> str:
    """The highest level up to which every scored assertion passed: checker, files, runtime, or none. The
    runtime level needs at least one scored runtime assertion, so a case without a plan, or with an unplayed
    one, stops at files."""
    out = "none"
    for level in LEVELS:
        mine = [g for g in graded if g["level"] == level and g["passed"] is not None]
        if not mine and level == "runtime":
            break
        if not all(g["passed"] for g in mine):
            break
        out = level
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("iteration", metavar="ITERATION_DIR")
    ap.add_argument("--play", action="store_true",
                    help="play each run's plan in the editor's preview (evals/play_cases.py); without it, "
                         "grade.py reads a play/result.json that the run already has")
    ap.add_argument("--release", metavar="rNNN", help="the editor release the plans open in (default: the current one)")
    ap.add_argument("--browser", metavar="EXE", help="the Chromium-based browser preview_project.py starts")
    ap.add_argument("--show-held-out", action="store_true",
                    help="print the failed assertions of held-out cases too; leave it off while a change is open")
    args = ap.parse_args()
    iteration = Path(args.iteration).resolve()
    cells: dict[str, dict[str, list[dict]]] = {}      # case -> arm -> its runs
    held: dict[str, dict[str, list[dict]]] = {}
    void, incomplete = [], []
    for name, case in CASES.items():
        for run in sorted(p for p in (iteration / name).glob("*") if (p / "project").is_dir()):
            reason = (run / "void.txt").read_text(encoding="utf-8").strip() if (run / "void.txt").exists() else None
            wrote = [w["path"] for w in optional_json(run / "trace.json").get("outside", [])]
            reason = reason or (f"it wrote outside its folder: {', '.join(dict.fromkeys(wrote))}" if wrote else None)
            leaked = leaked_reads(optional_json(run / "trace.json"), iteration, run)
            reason = reason or (f"it read how it is graded: {', '.join(leaked)}" if leaked else None)
            if reason:
                (run / "grading.json").write_text(json.dumps({"void": reason}, indent=2) + "\n", encoding="utf-8")
                void.append({"run": f"{name}/{run.name}", "reason": reason})
                print(f"{name}/{run.name}: void, not scored" + (f": {reason}" if wrote or leaked else ""))
                continue
            graded = [{"text": text, "passed": ok, "evidence": evidence, "level": level_of(text)}
                      for text, (ok, evidence) in zip(case["assertions"], GRADERS[name](run), strict=True)]
            runtime, play_seconds = runtime_of(name, run, args)
            graded += runtime
            scored = [g for g in graded if g["passed"] is not None]
            passed = sum(g["passed"] for g in scored)
            played = [g for g in runtime if g["passed"] is not None]
            summary = {"passed": passed, "failed": len(scored) - passed, "total": len(scored),
                       "pass_rate": round(passed / len(scored), 3), "level_reached": reached(graded),
                       "runtime": ({"passed": sum(g["passed"] for g in played), "total": len(played)} if played
                                   else "not played" if runtime else "no plan")}
            (run / "grading.json").write_text(json.dumps({"assertion_results": graded, "summary": summary},
                                                         indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            timing = optional_json(run / "timing.json")
            trace = optional_json(run / "trace.json")
            arm = re.sub(r"_\d+$", "", run.name)           # with_skill_2 is a second run of with_skill
            seconds = round(timing["duration_ms"] / 1000, 1) if timing else trace.get("seconds")
            missing = missing_of(run, timing, trace, runtime)
            if missing:
                incomplete.append({"run": f"{name}/{run.name}", "missing": missing})
            (held if case.get("held_out") else cells).setdefault(name, {}).setdefault(arm, []).append({
                "run": run.name, "passed": f"{passed}/{len(scored)}", "pass_rate": summary["pass_rate"],
                "full": passed == len(scored), "level_reached": summary["level_reached"],
                "runtime_rate": round(summary["runtime"]["passed"] / summary["runtime"]["total"], 3) if played else None,
                "tokens": timing.get("total_tokens"), "seconds": seconds, "play_seconds": play_seconds,
                "model": trace.get("model"), "missing": missing, **{k: trace[k] for k in TRACE_COLUMNS if k in trace}})
            note = f"  (missing: {', '.join(missing)})" if missing else ""
            runtime_said = (f", runtime {summary['runtime']['passed']}/{summary['runtime']['total']}" if played
                            else ", runtime not played" if runtime else "")
            if case.get("held_out") and not args.show_held_out:
                print(f"{name}/{run.name}: held out, {passed}/{len(scored)}{runtime_said}")
                continue
            print(f"{name}/{run.name}: {passed}/{len(scored)}{runtime_said}, reached {summary['level_reached']}{note}")
            for g in scored:
                if not g["passed"]:
                    print(f"    FAIL [{g['level']}] {g['text']}\n         {g['evidence']}")
    if not cells and not held and not void:
        sys.exit(f"{iteration} holds no <case>/<arm>/project of a case in evals.json")

    by_case, run_summary = aggregate(cells)
    flags = case_flags(cells)
    out = {"meta": grading_meta(iteration, args), "coverage_complete": not incomplete, "incomplete_runs": incomplete,
           "case_flags": flags, "run_summary": run_summary, "by_case": by_case, "void_runs": void}
    if held:
        held_cases, held_summary = aggregate(held)
        out["held_out"] = {"run_summary": held_summary, "by_case": held_cases}
    for label, summary in (("", run_summary), ("held out, ", out.get("held_out", {}).get("run_summary", {}))):
        for arm, s in summary.items():
            if arm != "delta":
                f = s["full_runs"]
                print(f"{label}{arm}: {f['k']} of {f['n']} runs passed every assertion they were scored on, "
                      f"95% interval {f['interval_95'][0]:.2f}-{f['interval_95'][1]:.2f}")
    if incomplete:
        print("coverage incomplete, so the scores of these runs do not stand: "
              + "; ".join(f"{r['run']} ({', '.join(r['missing'])})" for r in incomplete))
    else:
        print("coverage complete: every scored run has its answer, trace and timing, and every plan was played")
    if flags["saturated"]:
        print(f"saturated, every run of every arm passed, so the case tells the arms apart no more: "
              f"{', '.join(flags['saturated'])}")
    if flags["none_passed"]:
        print(f"no run passed, so read the runs before the case is trusted: {', '.join(flags['none_passed'])}")
    decision = decide(iteration, cells)
    if decision:
        out["decision"] = decision
    (iteration / "benchmark.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {iteration / 'benchmark.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
