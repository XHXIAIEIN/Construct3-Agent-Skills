"""Write placeholder sounds and music from the cue table, the way sound.md's recipe says.

    python scripts/make_sounds.py [--project FOLDER] [--dry-run] [--replace] [--example]

tools/sounds.json is the cue table: "look" (soft or hard, the timbre by
the art), "bpm", "reference_lufs" (M, default -30) and "cues", one per
file, each with "name", "role" (reward, impact or music) and "tier" (key,
action or repeat; not for music). Optional per cue: "pitched" (a reward is,
an impact is not), "note" (MIDI, default 69), "seconds", "low" (a low layer,
on by default for the key tier), "stereo" and "bars" for music, and
"folder", sounds or music. It defaults to sounds, because only a file in
sounds/ can be scheduled on the grid. --example prints a table to start
from.

Each effect is four layers (Construct3-RAG/prompts/references/sound.md,
"Making placeholder files"): an attack of filtered noise, a body of harmonic
partials, a low layer for rare accents, and a room baked in at the ratio of
its tier, driest for the repeat tier. A music stem is one pass of chords,
each note rendered on its own and added at an integer sample, plus the
room's tail. Each file is set to the middle of its tier's window on the
measure check_sounds.py reads, limited 1 dB under its ceiling, and encoded
WebM Opus: 96 kb/s stereo for an effect and a stereo stem, 64 kb/s mono for
the rest. The pitched layers (frequency, start, time to -12 dB) go back into
the cue's "layers" in tools/sounds.json, the cue table check_sounds.py
reads the roles from. project.c3proj lists each new file.

A file it wrote carries the COMMENT tag c3-sound, so a later run replaces
it. A file without the tag is someone's, and the run refuses it unless
--replace is given. The intermediate WAVs stay in .tmp/make-sounds/.
Needs ffmpeg and ffprobe on PATH.

Exit 0: every file written passed check_sounds.py, the last line starts
with ok:. Exit 1: findings, no cue table or one that is not a table, no
project or no ffmpeg. Exit 2: a file that is not this script's is in the
way.
"""
import json
import math
import random
import shutil
import subprocess
import sys
from pathlib import Path

import c3project as c3
import check_sounds as cs

RATE = 48000
WORK = Path(".tmp") / "make-sounds"
SECONDS = {"key": 0.9, "action": 0.5, "repeat": 0.25}        # an effect's length by tier
DECAY = {"key": 0.35, "action": 0.18, "repeat": 0.08}         # the body's time constant, s
ROOM_DB = {"key": 14.0, "action": 20.0, "repeat": 28.0, "music": 12.0}   # dry over wet, sound.md
TO_12_DB = math.log(10 ** (12 / 20))                          # exp(-t/T) reaches -12 dB at t = T * this
PROGRESSION = ((0, 4, 7), (9, 12, 16), (5, 9, 12), (7, 11, 14))   # I vi IV V, semitones over the root
AUDIO_TYPE = "audio/webm; codecs=opus"
EXAMPLE = {"look": "soft", "bpm": 100, "reference_lufs": cs.REFERENCE, "cues": [
    {"name": "level_clear", "role": "reward", "tier": "key", "note": 76},
    {"name": "merge", "role": "reward", "tier": "action", "note": 69},
    {"name": "pickup", "role": "impact", "tier": "action"},
    {"name": "hit", "role": "impact", "tier": "repeat"},
    {"name": "theme", "role": "music", "stereo": True, "bars": 4}]}


def hz(note: float) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def partials(look: str, pitched: bool) -> list[tuple[float, float, float]]:
    """(ratio to the fundamental, amplitude, share of the decay) of the body's partials: a soft look
    keeps harmonic partials, a hard look takes the bell's (Fletcher and Rossing)."""
    if pitched:
        return [(1, 1.0, 1.0), (4, 0.35, 0.33)] if look == "soft" else [(1, 1.0, 1.0), (2.76, 0.5, 0.6), (5.40, 0.3, 0.4)]
    return [(1, 1.0, 1.0), (2, 0.5, 0.5)] if look == "soft" else [(1, 1.0, 1.0), (3, 0.5, 0.6), (5, 0.3, 0.5)]


def tone(freq: float, decay: float, seconds: float, parts: list[tuple[float, float, float]]) -> str:
    """An aevalsrc of parts over freq, each decaying by its share of decay."""
    terms = "+".join(f"{amp}*sin(2*PI*{freq * ratio:.3f}*t)*exp(-t/{decay * share:.4f})" for ratio, amp, share in parts)
    return f"aevalsrc=exprs='{terms}':s={RATE}:d={seconds:.3f}"


def effect_graph(cue: dict, look: str, tier: str, seconds: float) -> tuple[list[str], str, list[dict]]:
    """The lavfi inputs and the filter graph of an effect, and its pitched layers for the sidecar."""
    pitched = bool(cue.get("pitched", cue.get("role") == "reward"))
    freq = hz(float(cue.get("note", 69))) if pitched else (110.0 if look == "soft" else 150.0)
    decay = DECAY[tier] if pitched else min(DECAY[tier], 0.08)
    parts = partials(look, pitched)
    inputs = [f"anoisesrc=d={seconds:.3f}:c=pink:r={RATE}:a=0.5:s=7", tone(freq, decay, seconds, parts)]
    if look == "soft":      # no click above 1.5 kHz, no attack under 3 ms
        attack = "lowpass=f=1500,afade=t=in:d=0.005,afade=t=out:st=0.005:d=0.04,volume=-6dB"
    else:
        attack = "highpass=f=2000,afade=t=in:d=0.001,afade=t=out:st=0.001:d=0.02"
    low = bool(cue.get("low", tier == "key"))
    if low:                 # A1 with its 2nd and 3rd harmonics, so a phone speaker still plays the drop
        inputs.append(f"aevalsrc=exprs='sin(2*PI*55*t)*exp(-t/0.4)+0.5*sin(2*PI*110*t)*exp(-t/0.3)"
                      f"+0.3*sin(2*PI*165*t)*exp(-t/0.25)':s={RATE}:d={seconds:.3f}")
    graph = (f"[0:a]{attack}[att];[1:a]volume=-3dB[body];[att][body]amix=inputs=2:normalize=0[dry];"
             f"[dry]asplit[d1][d2];[d2]aecho=0:1:23|47|89:0.6|0.4|0.25,highpass=f=250,lowpass=f=5000,"
             f"volume=-{ROOM_DB[tier]:.0f}dB[wet];")
    if low:
        graph += "[d1][wet][2:a]amix=inputs=3:normalize=0[out]"
    else:
        graph += "[d1][wet]amix=inputs=2:normalize=0[out]"
    layers = [{"frequency": round(freq * ratio, 3), "start": 0.0, "decay_to_-12dB": round(decay * share * TO_12_DB, 4)}
              for ratio, _, share in parts] if pitched else []
    return inputs, graph, layers


def music_graph(cue: dict, look: str, bpm: float) -> tuple[list[str], str, list[dict], float]:
    """The inputs and graph of a stem: one pass of the progression, a note per chord tone rendered on
    its own and added at an integer sample, then the room; and its layers and length."""
    bars = int(cue.get("bars", 4))
    root = float(cue.get("note", 60))
    beat = 60.0 / bpm
    bar = 4 * beat
    tail = 1.5
    seconds = bars * bar + tail
    parts = [(1, 1.0, 1.0), (3, 1 / 9, 0.8), (5, 1 / 25, 0.6)] if look == "soft" else partials("hard", True)
    inputs, labels, layers = [], [], []
    for b in range(bars):
        chord = PROGRESSION[b % len(PROGRESSION)]
        start_sample = round(b * bar * RATE)
        for semis in chord:
            freq = hz(root + semis)
            n = len(inputs)
            inputs.append(tone(freq, bar * 0.6, seconds - b * bar, parts))
            labels.append(f"[{n}:a]adelay={start_sample}S:all=1,apad=whole_dur={seconds:.3f}[n{n}]")
            layers.append({"frequency": round(freq, 3), "start": round(b * bar, 4),
                           "decay_to_-12dB": round(bar * 0.6 * TO_12_DB, 4)})
    joined = "".join(f"[n{i}]" for i in range(len(inputs)))
    graph = (";".join(labels) + f";{joined}amix=inputs={len(inputs)}:normalize=0,highpass=f=70[dry];"
             f"[dry]asplit[d1][d2];[d2]aecho=0:1:31|67|113:0.6|0.45|0.3,highpass=f=250,lowpass=f=5000,"
             f"volume=-{ROOM_DB['music']:.0f}dB[wet];[d1][wet]amix=inputs=2:normalize=0[out]")
    return inputs, graph, layers, seconds


def render(ffmpeg: str, inputs: list[str], graph: str, wav: Path) -> str | None:
    """The graph to wav; the error text when ffmpeg fails."""
    cmd = [ffmpeg, "-nostdin", "-y", "-v", "error"]
    for src in inputs:
        cmd += ["-f", "lavfi", "-i", src]
    cmd += ["-filter_complex", graph, "-map", "[out]", "-ar", str(RATE), str(wav)]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    return None if p.returncode == 0 and wav.exists() else (p.stderr.strip() or f"ffmpeg exit {p.returncode}")


def encode(ffmpeg: str, wav: Path, out: Path, gain: float, ceiling: float, channels: int) -> str | None:
    """wav with gain dB, limited 1 dB under ceiling, as WebM Opus with the mark; the error text on failure."""
    limit = 10 ** ((ceiling - 1) / 20)
    cmd = [ffmpeg, "-nostdin", "-y", "-v", "error", "-i", str(wav), "-af",
           f"volume={gain:+.2f}dB,alimiter=limit={limit:.4f}:level=0:attack=2:release=50", "-ac", str(channels),
           "-c:a", "libopus", "-b:a", "96k" if channels == 2 else "64k", "-metadata", f"comment={cs.MARK}", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    return None if p.returncode == 0 and out.exists() else (p.stderr.strip() or f"ffmpeg exit {p.returncode}")


def list_in_project(root: Path, written: list[tuple[str, str]], dry_run: bool) -> list[str]:
    """Add each (kind, file name) that project.c3proj does not list to its rootFileFolders, as the editor
    lists an imported file; returns the names added."""
    proj = root / "project.c3proj"
    text = proj.read_text(encoding="utf-8")
    data = json.loads(text)
    used: set[int] = set()

    def sids(node) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("sid"), int):
                used.add(node["sid"])
            for v in node.values():
                sids(v)
        elif isinstance(node, list):
            for v in node:
                sids(v)
    sids(data)
    folders = data.setdefault("rootFileFolders", {})
    added = []
    for kind, name in written:
        folder = folders.setdefault(kind, {"items": [], "subfolders": []})
        items = folder.setdefault("items", [])
        if any((it.get("name") if isinstance(it, dict) else it) == name for it in items):
            continue
        while True:
            sid = random.randint(10 ** 14, 10 ** 15 - 1)
            if sid not in used:
                used.add(sid)
                break
        items.append({"name": name, "type": AUDIO_TYPE, "sid": sid, "file-info": {"purpose": "none"}})
        added.append(name)
    if added and not dry_run:
        proj.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + ("\n" if text.endswith("\n") else ""),
                        encoding="utf-8", newline="\n")
    return added


def main() -> int:
    c3.utf8_output()
    ap = c3.argument_parser(__doc__.split("\n\n")[0], "examples:\n"
                            "  python scripts/make_sounds.py --example > tools/sounds.json\n"
                            "  python scripts/make_sounds.py --dry-run\n"
                            "  python scripts/make_sounds.py --project D:/games/Coins --replace\n\n"
                            "exit codes: 0 when every file passed check_sounds.py, 1 on findings, no cue table, no "
                            "project or no ffmpeg, 2 when a file that is not this script's is in the way")
    ap.add_argument("--dry-run", action="store_true", help="say what would be written and write nothing")
    ap.add_argument("--replace", action="store_true", help="overwrite a file that does not carry the c3-sound tag")
    ap.add_argument("--example", action="store_true", help="print a cue table to start from and exit")
    args = ap.parse_args()
    if args.example:
        print(json.dumps(EXAMPLE, indent=2))
        return 0
    root = c3.find_project(args.project)
    if root is None or not (root / "project.c3proj").exists():
        print(f"no project.c3proj in {root or Path.cwd()}: run this from the project folder or pass "
              f"--project <folder>", file=sys.stderr)
        return 1
    found = cs.tools()
    if found is None:
        print(cs.INSTALL)
        return 1
    ffmpeg, ffprobe = found
    table_path = root / cs.CUES
    if not table_path.exists():
        print(f"no {cs.CUES.as_posix()} in {root}: write the cue table first; --example prints one to start from, "
              f"python {c3.shown_path(Path(__file__))} --example > {cs.CUES.as_posix()}")
        return 1
    try:
        table = json.loads(table_path.read_text(encoding="utf-8"))
        cues = table["cues"]
        assert isinstance(cues, list)
    except (json.JSONDecodeError, KeyError, AssertionError, TypeError) as e:
        print(f"{cs.CUES.as_posix()} is not a cue table ({e}); it is an object with \"cues\", a list of objects "
              f"with \"name\", \"role\" and \"tier\"; --example prints one")
        return 1
    look = table.get("look", "soft")
    bpm = float(table.get("bpm", 100))
    reference = float(table.get("reference_lufs", cs.REFERENCE))
    problems: list[str] = []
    plan: list[tuple[dict, Path, str]] = []          # cue, target, kind
    for cue in cues:
        name, role, tier = cue.get("name"), cue.get("role"), cue.get("tier")
        if not isinstance(name, str) or not name or any(ch in name for ch in '/\\:*?"<>|'):
            problems.append(f"cue {name!r}: \"name\" is the file's stem, letters, digits, - and _")
            continue
        if role not in cs.ROLES:
            problems.append(f"cue {name}: \"role\" is one of {', '.join(cs.ROLES)}, not {role!r}")
            continue
        if role != "music" and tier not in cs.TIERS:
            problems.append(f"cue {name}: \"tier\" is one of {', '.join(cs.TIERS)}, not {tier!r}")
            continue
        folder = cue.get("folder", "sounds")
        if folder not in ("sounds", "music"):
            problems.append(f"cue {name}: \"folder\" is sounds or music, not {folder!r}")
            continue
        kind = "sound" if folder == "sounds" else "music"
        plan.append((cue, root / folder / f"{name}.webm", kind))
    if problems:
        for line in problems:
            print(line)
        print(f"{len(problems)} findings: nothing written")
        return 1
    foreign = [t for _, t, _ in plan if t.exists() and not cs.marked(ffprobe, t)]
    if foreign and not args.replace:
        for t in foreign:
            print(f"{t.relative_to(root).as_posix()} exists and does not carry the {cs.MARK} tag, so it is not this "
                  f"script's; rename the cue, delete the file, or pass --replace")
        print(f"{len(foreign)} files in the way: nothing written")
        return 2
    if args.dry_run:
        for cue, target, _ in plan:
            print(f"would write {target.relative_to(root).as_posix()}: {cue.get('tier', 'music')} ({cue['role']})")
        print(f"ok: dry run, {len(plan)} files would be written")
        return 0
    work = root / WORK
    work.mkdir(parents=True, exist_ok=True)
    written: list[tuple[str, str]] = []
    for cue, target, kind in plan:
        role = cue["role"]
        if role == "music":
            inputs, graph, layers, seconds = music_graph(cue, look, bpm)
            channels = 2 if cue.get("stereo") else 1
        else:
            tier = cue["tier"]
            seconds = float(cue.get("seconds", SECONDS[tier]))
            inputs, graph, layers = effect_graph(cue, look, tier, seconds)
            channels = 2
        wav = work / f"{cue['name']}.wav"
        error = render(ffmpeg, inputs, graph, wav)
        if error:
            problems.append(f"{cue['name']}: ffmpeg could not render it: {error.splitlines()[-1]}")
            continue
        want = cs.expectation(cue, target.parent.name, reference)
        loud = cs.loudness(ffmpeg, wav)
        value = loud[want["measure"]] if loud[want["measure"]] is not None else loud["momentary"]
        if value is None:
            problems.append(f"{cue['name']}: the render is silent; raise its layers or its seconds")
            continue
        gain = (want["low"] + want["high"]) / 2 - value
        target.parent.mkdir(parents=True, exist_ok=True)
        error = encode(ffmpeg, wav, target, gain, want["ceiling"], channels)
        if error:
            problems.append(f"{cue['name']}: ffmpeg could not encode it: {error.splitlines()[-1]}")
            continue
        cue["layers"] = layers
        cue["made"] = {"file": target.relative_to(root).as_posix(), "seconds": round(seconds, 3),
                       "gain_db": round(gain, 2), "channels": channels}
        written.append((kind, target.name))
    table_path.write_text(json.dumps(table, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    added = list_in_project(root, written, dry_run=False)
    lines: list[str] = []
    findings: list[str] = list(problems)
    _, by_name = cs.cue_table(root)
    for cue, target, _ in plan:
        if target.exists() and (("sound" if target.parent.name == "sounds" else "music"), target.name) in written:
            cs.measure(ffmpeg, ffprobe, target, root, by_name, reference, lines, findings, [])
    out = lines + findings
    shown = c3.fitting(out, args.limit)
    for line in out[:shown]:
        print(line)
    if shown < len(out):
        print(f"... {len(out) - shown} more; --limit 0 prints them all")
    summary = (f"{len(written)} files written, {len(added)} listed in project.c3proj, layers in "
               f"{cs.CUES.as_posix()}; next: {c3.script_command(root, 'check_sounds.py')}")
    print(f"{len(findings)} findings: {summary}" if findings else f"ok: {summary}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
