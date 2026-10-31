"""Run a test case of several turns as one Claude Code session, compacted between the turns in a compact arm.

    python dev/evals/run_session.py RUN_DIR [--client claude] [--model MODEL] [--timeout 1800]
                                  [--allowed-tools "Bash,PowerShell,Read,Edit,Write,Glob,Grep,Skill"]

RUN_DIR is <iteration>/<case>/<arm> as make_fixtures.py laid it out, and the
case is one of evals.json with "turns": the prompts that follow its
"prompt", in the same session. Each turn runs as `claude -p` in
RUN_DIR/project, the later ones with --resume and the session id the first
one returned, and <project> in a prompt stands for that folder. Before each
later turn, an arm whose name has the word compact (with_compact,
with_claude_compact_2) sends /compact, the summary auto-compaction makes when
the context fills, so the turn starts from a summary at a known point. Then
the changes the case names under "between" (BETWEEN of make_fixtures.py) are
written into the project, before the first later turn only: a change made
outside the session, which only a check run after it finds.

RUN_DIR/outputs/session.json records each turn: its prompt, what the client
returned, whether it was an error, its time and cost, and the compaction's
context before and after it. outputs/answer.md is the last turn's answer,
and timing.json the time and tokens of all the turns. The transcript is
~/.claude/projects/<project>/<session id>.jsonl; the script prints it with the
trace.py command that reads it into the run folder.

A turn that runs past --timeout ends the case, and the turns after it do not
run. Stopping a turn, by the timeout or by Ctrl+C, stops every process the
client started.

exit codes: 0 every turn answered, 1 a turn ended in an error or a compaction
did not run, 2 the client could not run: it is not installed, not signed in
(run `claude` once and sign in), or printed no JSON result
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import make_fixtures
from run_trigger_eval import ISOLATED, stop_tree

CASES = {c["name"]: c for c in make_fixtures.CASES}
SIGNED_OUT = ("Failed to authenticate", "Not logged in", "Invalid API key", "/login")


class ClientError(RuntimeError):
    """The client cannot run a turn: main() exits 2."""


def turn(client: list[str], prompt: str, project: Path, session: str | None, args: argparse.Namespace) -> dict:
    """One `claude -p` turn in project: the JSON result the client printed."""
    cmd = [*client, "-p", prompt, "--output-format", "json", "--permission-mode", "acceptEdits",
           "--allowedTools", args.allowed_tools, *ISOLATED]
    cmd += ["--resume", session] if session else []
    cmd += ["--model", args.model] if args.model else []
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}     # set inside a session, it refuses a nested one
    try:
        proc = subprocess.Popen(cmd, cwd=project, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                encoding="utf-8", errors="replace", start_new_session=os.name != "nt",
                                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
    except OSError as e:
        raise ClientError(f"{client[0]} could not be started: {e}") from e
    # The client runs in a process group of its own, which a Ctrl+C in this console does not reach, so the turn
    # stops it on the way out.
    try:
        out, err = proc.communicate(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        return {"is_error": True, "timed_out": True, "result": f"timed out after {args.timeout} s"}
    finally:
        stop_tree(proc)
    try:
        result = json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise ClientError(f"{client[0]} printed no JSON result: {(err or out).strip()[-600:]}") from None
    if result.get("is_error") and any(s in str(result.get("result", "")) for s in SIGNED_OUT):
        raise ClientError(f"{client[0]} is not signed in: {result.get('result')}; run `claude` once and sign in")
    return result


def transcript_of(session: str) -> Path | None:
    home = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return next(iter(sorted((home / "projects").glob(f"*/{session}.jsonl"))), None)


def compaction_of(transcript: Path | None) -> dict | None:
    """The context before and after the last compaction of the transcript, or None without one."""
    found = None
    for line in transcript.read_text(encoding="utf-8").splitlines() if transcript else []:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("type") == "system" and entry.get("subtype") == "compact_boundary":
            meta = entry.get("compactMetadata") or {}
            found = {"pre_tokens": meta.get("preTokens"), "post_tokens": meta.get("postTokens")}
    return found


def tokens_of(result: dict) -> int:
    usage = result.get("usage") or {}
    return sum(usage.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens",
                                          "cache_read_input_tokens", "output_tokens"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", metavar="RUN_DIR", help="<iteration>/<case>/<arm> as make_fixtures.py laid it out")
    ap.add_argument("--client", default="claude",
                    help="the client's command, several words allowed, paths with forward slashes (default: claude)")
    ap.add_argument("--model", help="model for claude -p (default: the client's own)")
    ap.add_argument("--timeout", type=int, default=1800, help="seconds a turn may take (default 1800)")
    ap.add_argument("--allowed-tools", default="Bash,PowerShell,Read,Edit,Write,Glob,Grep,Skill",
                    help="the tools a turn runs without asking, as --allowedTools takes them")
    args = ap.parse_args()

    run = Path(args.run_dir).resolve()
    project, case = run / "project", CASES.get(run.parent.name)
    if not case or not case.get("turns"):
        sys.exit(f"{run.parent.name} is not a case of evals.json with turns; RUN_DIR is <iteration>/<case>/<arm>")
    if not project.is_dir():
        sys.exit(f"{project} does not exist; lay the run out with make_fixtures.py first")
    if (run / "outputs" / "session.json").exists():
        sys.exit(f"{run} already ran; lay out a new run folder")
    compact = "compact" in run.name.split("_")
    client = shlex.split(args.client)
    record: dict = {"case": case["name"], "arm": run.name, "compact": compact, "turns": []}
    results: list[dict] = []
    session = None
    try:
        for n, prompt in enumerate([case["prompt"], *case["turns"]]):
            if n:
                if compact:
                    done = turn(client, "/compact", project, session, args)
                    results.append(done)
                    record["turns"].append({"prompt": "/compact", "result": done.get("result"),
                                            "is_error": bool(done.get("is_error")),
                                            "compaction": compaction_of(transcript_of(session))})
                    if done.get("timed_out"):
                        print(f"turn {n + 1}: /compact timed out; the case stops")
                        break
                for name in case.get("between", []) if n == 1 else []:
                    make_fixtures.BETWEEN[name](project)
                    record["turns"].append({"between": name})
            text = prompt.replace("<project>", project.as_posix())
            done = turn(client, text, project, session, args)
            session = session or done.get("session_id")
            results.append(done)
            record["turns"].append({"prompt": text, "result": done.get("result"), "is_error": bool(done.get("is_error")),
                                    "duration_ms": done.get("duration_ms"), "cost_usd": done.get("total_cost_usd")})
            print(f"turn {n + 1}: {'error' if done.get('is_error') else 'answered'} in "
                  f"{round((done.get('duration_ms') or 0) / 1000)} s")
            if done.get("timed_out"):
                # A later turn would resume a session that never finished its turn, or start one without it.
                print(f"turn {n + 1} timed out; the case stops")
                break
    except ClientError as e:
        print(e, file=sys.stderr)
        return 2
    finally:
        transcript = transcript_of(session) if session else None
        record |= {"session_id": session, "transcript": str(transcript) if transcript else None}
        (run / "outputs").mkdir(exist_ok=True)
        (run / "outputs" / "session.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                                                     encoding="utf-8")
    answers = [t for t in record["turns"] if t.get("prompt") and t["prompt"] != "/compact"]
    (run / "outputs" / "answer.md").write_text(str(answers[-1]["result"] or ""), encoding="utf-8")
    (run / "timing.json").write_text(json.dumps({
        "duration_ms": sum(r.get("duration_ms") or 0 for r in results),
        "total_tokens": sum(map(tokens_of, results))}, indent=2) + "\n", encoding="utf-8")
    trace = Path(__file__).with_name("trace.py").as_posix()
    print(f"transcript: {transcript}\nnext: python {trace} \"{transcript}\" --out \"{run.as_posix()}\""
          if transcript else "the transcript was not found under ~/.claude/projects")
    missed = [t for t in record["turns"] if t.get("prompt") == "/compact" and not t.get("compaction")]
    failed = [t for t in record["turns"] if t.get("is_error")]
    if missed or failed:
        print(f"{len(failed)} turn(s) ended in an error, {len(missed)} compaction(s) did not run; "
              f"read {(run / 'outputs' / 'session.json').as_posix()}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
