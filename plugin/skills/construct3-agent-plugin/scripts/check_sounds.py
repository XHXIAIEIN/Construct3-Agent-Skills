"""Measure the sound and music files of a project against the tiers and ceilings of sound.md.

    python scripts/check_sounds.py [--project FOLDER] [FILE ...]

It prints one line of measurements per file under sounds/ and music/, or
per FILE named. The line holds the duration, channels, sample rate, codec
and bit rate, the loudest 400 ms (3 s for music) K-weighted above 150 Hz,
the integrated loudness, the true peak, and the silence at the head and the
tail. Then it compares the file with the tier and the ceiling of its role
(Construct3-Cookbook/guides/recipes/sound.md, "Tiers and loudness"):

  tools/sounds.json   the cue table: one entry per file, with "role"
                      (reward, impact or music) and "tier" (key, action or
                      repeat); make_sounds.py writes it, or write it by hand
  music/              a file without an entry is a music stem
  sounds/             a file without an entry is an effect of unknown tier,
                      measured against the whole span of the three tiers

The reference M is the music at its in-game level, -30 LUFS, the loudest
3 s above 150 Hz. The tiers are key +8 to +14 dB over M, action 0 to +9,
repeat -7 to +1, each on the loudest 400 ms; a music file is within 1 dB of
M. The true peak ceiling is -3 dBFS for an effect and -12 dBFS for music.
Head silence over 0.03 s, the lead of a play scheduled on the music grid,
delays it and is a finding; tail silence is printed only. A loudness finding names the gain in
dB and the ffmpeg command that applies it.

Needs ffmpeg and ffprobe on PATH. Without them nothing is measured, and the
script says so and exits 0.

Exit 0: the last line starts with ok:, or nothing was measured. Exit 1:
findings, or no project.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import c3project as c3

AUDIO = (".webm", ".ogg", ".opus", ".mp3", ".m4a", ".wav", ".flac", ".aac")
CUES = Path("tools") / "sounds.json"           # the cue table, written by make_sounds.py or by hand
MARK = "c3-sound"                               # the COMMENT tag make_sounds.py writes into its files
REFERENCE = -30.0                               # M: the music at its in-game level, LUFS
TIERS = {"key": (8.0, 14.0), "action": (0.0, 9.0), "repeat": (-7.0, 1.0)}   # dB over M, sound.md
MUSIC_TOLERANCE = 1.0                           # dB either side of M for a music file
CEILINGS = {"effect": -3.0, "music": -12.0}     # true peak, dBFS
LEAD = 0.03                                     # s, the lead of a play scheduled on the grid, sound.md
SILENCE_FLOOR = "-60dB"
INSTALL = ("ffmpeg and ffprobe are not on PATH: install ffmpeg (winget install Gyan.FFmpeg, brew install ffmpeg, "
           "apt install ffmpeg) and run again")
ROLES = ("reward", "impact", "music")


def tools() -> tuple[str, str] | None:
    """ffmpeg and ffprobe, or None when either is missing."""
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    return (ffmpeg, ffprobe) if ffmpeg and ffprobe else None


def run(cmd: list[str]) -> str:
    """stdout and stderr of an ffmpeg tool, joined; ffmpeg writes its filters' reports to stderr."""
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    return p.stdout + p.stderr


def probe(ffprobe: str, path: Path) -> dict:
    """Duration, channels, sample rate, codec, bit rate and tags of path's first audio stream."""
    text = run([ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries",
                "format=duration,bit_rate:format_tags:stream=codec_name,channels,sample_rate", "-of", "json", str(path)])
    try:
        data = json.loads(text[text.index("{"):])
    except (ValueError, json.JSONDecodeError):
        return {}
    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}
    tags = {k.lower(): v for k, v in (fmt.get("tags") or {}).items()}
    return {"duration": float(fmt.get("duration") or 0), "bit_rate": int(fmt.get("bit_rate") or 0),
            "codec": stream.get("codec_name", "?"), "channels": int(stream.get("channels") or 0),
            "sample_rate": int(stream.get("sample_rate") or 0), "tags": tags}


def marked(ffprobe: str, path: Path) -> bool:
    """Whether path carries the COMMENT tag make_sounds.py writes, as check_look.py knows a painting by its chunk."""
    return probe(ffprobe, path).get("tags", {}).get("comment") == MARK


LINE = re.compile(r"M:\s*(-?[\d.]+)\s+S:\s*(-?[\d.]+)")
SUMMARY = re.compile(r"I:\s*(-?[\d.]+) LUFS.*?Peak:\s*(-?[\d.]+) dBFS", re.S)
LOUDNORM = re.compile(r'"input_i"\s*:\s*"(-?[\d.]+)".*?"input_tp"\s*:\s*"(-?[\d.]+)"', re.S)


def loudness(ffmpeg: str, path: Path) -> dict:
    """momentary: the loudest 400 ms and short_term: the loudest 3 s, both K-weighted above 150 Hz,
    the measure of sound.md; integrated and true_peak of the whole file, from loudnorm. A window that
    never fills (a file under 3 s has no short-term value) is None."""
    # Padded with 3 s of silence: a window that never fills gives no value for a sound shorter than it,
    # and silence changes neither the loudest window nor the gated integrated loudness nor the peak.
    text = run([ffmpeg, "-nostdin", "-v", "info", "-i", str(path), "-af",
                "apad=pad_dur=3,highpass=f=150,ebur128=peak=true", "-f", "null", "-"])
    m_values = [float(m.group(1)) for m in LINE.finditer(text) if float(m.group(1)) > -100]
    s_values = [float(m.group(2)) for m in LINE.finditer(text) if float(m.group(2)) > -100]
    result = {"momentary": max(m_values) if m_values else None, "short_term": max(s_values) if s_values else None,
              "integrated": None, "true_peak": None}
    text = run([ffmpeg, "-nostdin", "-v", "info", "-i", str(path), "-af", "apad=pad_dur=3,loudnorm=print_format=json",
                "-f", "null", "-"])
    found = LOUDNORM.search(text)
    if found:
        result["integrated"], result["true_peak"] = float(found.group(1)), float(found.group(2))
    return result


SILENCE = re.compile(r"silence_(start|end): ([\d.]+)")


def silences(ffmpeg: str, path: Path, duration: float) -> tuple[float, float]:
    """Seconds of silence (under SILENCE_FLOOR) at the head and at the tail of path."""
    text = run([ffmpeg, "-nostdin", "-v", "info", "-i", str(path), "-af", f"silencedetect=n={SILENCE_FLOOR}:d=0.005",
                "-f", "null", "-"])
    marks = [(kind, float(t)) for kind, t in SILENCE.findall(text)]
    head = tail = 0.0
    if marks and marks[0][0] == "start" and marks[0][1] <= 0.01:
        head = marks[1][1] if len(marks) > 1 and marks[1][0] == "end" else duration
    if marks and marks[-1][0] == "start":                       # a silence that runs to the end has no end mark
        tail = max(0.0, duration - marks[-1][1])
    elif len(marks) >= 2 and marks[-1][0] == "end" and marks[-1][1] >= duration - 0.01:
        tail = marks[-1][1] - marks[-2][1]
    return round(head, 3), round(tail, 3)


def cue_table(root: Path) -> tuple[dict, dict[str, dict]]:
    """The cue table of tools/sounds.json and its cues by file stem, both empty when there is none."""
    path = root / CUES
    if not path.exists():
        return {}, {}
    try:
        table = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, {}
    cues = table.get("cues") if isinstance(table, dict) else None
    return table, {c["name"]: c for c in (cues or []) if isinstance(c, dict) and isinstance(c.get("name"), str)}


def expectation(cue: dict | None, folder: str, reference: float) -> dict:
    """What the file's role asks of it: the loudness window (LUFS), the measure it is read on,
    the true peak ceiling and a label for the line."""
    role = (cue or {}).get("role") if cue else ("music" if folder == "music" else None)
    tier = (cue or {}).get("tier")
    if role == "music":
        return {"role": "music", "measure": "short_term", "low": reference - MUSIC_TOLERANCE,
                "high": reference + MUSIC_TOLERANCE, "ceiling": CEILINGS["music"], "label": "music"}
    if tier in TIERS:
        lo, hi = TIERS[tier]
        label = f"{tier} ({role}{', pitched' if cue.get('pitched') else ''})" if role else tier
        return {"role": role or "effect", "measure": "momentary", "low": reference + lo, "high": reference + hi,
                "ceiling": CEILINGS["effect"], "label": label}
    lows, highs = zip(*TIERS.values())
    return {"role": role or "effect", "measure": "momentary", "low": reference + min(lows),
            "high": reference + max(highs), "ceiling": CEILINGS["effect"], "label": "no tier"}


def audio_files(root: Path, named: list[str]) -> list[Path]:
    """The audio files under sounds/ and music/, or the named ones, each as a path under root."""
    if named:
        return [root / n if not Path(n).is_absolute() else Path(n) for n in named]
    return [p for folder in ("sounds", "music") for p in sorted((root / folder).rglob("*"))
            if p.is_file() and p.suffix.lower() in AUDIO]


def encode_command(rel: str, filters: str, suffix: str, channels: int) -> str:
    """The ffmpeg command that runs filters on rel and writes the result beside it as WebM Opus at the
    rate sound.md gives: 96 kb/s for stereo, 64 kb/s for mono."""
    out = Path(rel).with_suffix("").as_posix() + f".{suffix}.webm"
    return f"ffmpeg -i {rel} -af {filters} -c:a libopus -b:a {'96k' if channels == 2 else '64k'} {out}"


def measure(ffmpeg: str, ffprobe: str, path: Path, root: Path, cues: dict[str, dict], reference: float,
            lines: list[str], findings: list[str], untiered: list[str]) -> None:
    """One line of measurements for path into lines, its findings into findings, and its stem into
    untiered when no cue names it."""
    rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix()
    info = probe(ffprobe, path)
    if not info or not info["channels"]:
        findings.append(f"unreadable: {rel} holds no audio stream ffprobe can read; encode it, "
                        f"ffmpeg -i {rel} -c:a libopus {Path(rel).stem}.webm")
        return
    loud = loudness(ffmpeg, path)
    head, tail = silences(ffmpeg, path, info["duration"])
    want = expectation(cues.get(path.stem), path.parent.name, reference)
    value = loud[want["measure"]]
    if value is None and want["measure"] == "short_term":        # a stem under 3 s: its loudest 400 ms stands in
        value = loud["momentary"]

    def db(v: float | None, unit: str) -> str:
        return f"{v:.1f} {unit}" if v is not None else "n/a"

    kbps = f" {info['bit_rate'] / 1000:.0f} kb/s" if info["bit_rate"] else ""
    lines.append(f"{rel}: {info['duration']:.3f} s, {info['channels']} ch, {info['sample_rate']} Hz, "
                 f"{info['codec']}{kbps}; loudest {'3 s' if want['measure'] == 'short_term' else '400 ms'} "
                 f"{db(value, 'LUFS')}, integrated {db(loud['integrated'], 'LUFS')}, true peak "
                 f"{db(loud['true_peak'], 'dBFS')}, silence head {head:.3f} s tail {tail:.3f} s; "
                 f"{want['label']}: {want['low']:.0f} to {want['high']:.0f} LUFS, ceiling {want['ceiling']:.0f} dBFS")
    if want["label"] == "no tier":
        if path.stem in cues:
            findings.append(f"tier: {rel} has a cue in {CUES.as_posix()} without a tier, so it is measured against "
                            f"the whole span of the tiers; give the cue \"tier\": \"key\", \"action\" or "
                            f"\"repeat\" ({cues[path.stem].get('tier')!r} is none of them)")
        else:
            untiered.append(path.stem)
    if value is not None and not want["low"] <= value <= want["high"]:
        gain = (want["low"] + want["high"]) / 2 - value
        findings.append(f"loudness: {rel} is at {value:.1f} LUFS on its loudest "
                        f"{'3 s' if want['measure'] == 'short_term' else '400 ms'} above 150 Hz; {want['label']} "
                        f"is {want['low']:.0f} to {want['high']:.0f}. Apply {gain:+.1f} dB: "
                        f"{encode_command(rel, f'volume={gain:+.1f}dB', 'gained', info['channels'])}")
    if loud["true_peak"] is not None and loud["true_peak"] > want["ceiling"]:
        limit = 10 ** ((want["ceiling"] - 1) / 20)          # 1 dB under the ceiling: the encoder overshoots a little
        findings.append(f"peak: {rel} has a true peak of {loud['true_peak']:.1f} dBFS, over the "
                        f"{want['ceiling']:.0f} dBFS ceiling of {'music' if want['role'] == 'music' else 'an effect'}; "
                        f"there is no master limiter, so peaks add. Limit it, "
                        f"{encode_command(rel, f'alimiter=limit={limit:.3f}', 'limited', info['channels'])}, "
                        f"or lower the whole file")
    if head > LEAD and want["role"] != "music":
        findings.append(f"silence: {rel} starts with {head:.3f} s of silence, more than the {LEAD} s lead a play "
                        f"scheduled on the music grid gets (sound.md, \"Immediate or on the grid\"), so it lands "
                        f"late by that much; trim it, "
                        f"{encode_command(rel, f'atrim=start={head:.3f},asetpts=PTS-STARTPTS', 'trimmed', info['channels'])}")
    if info["codec"] != "opus":
        findings.append(f"codec: {rel} is {info['codec']}, and a project's sound and music are WebM Opus; encode it, "
                        f"ffmpeg -i {rel} -c:a libopus -b:a {'96k' if info['channels'] == 2 else '64k'} "
                        f"{Path(rel).stem}.webm")


def main() -> int:
    c3.utf8_output()
    ap = c3.argument_parser(__doc__.split("\n\n")[0], "examples:\n"
                            "  python scripts/check_sounds.py\n"
                            "  python scripts/check_sounds.py --project D:/games/Coins sounds/merge.webm\n\n"
                            "exit codes: 0 when the last line starts with ok: or nothing was measured, 1 on "
                            "findings or no project")
    ap.add_argument("files", nargs="*", metavar="FILE", help="measure only these files, named from the project root")
    args = ap.parse_args()
    root = c3.find_project(args.project)
    if root is None or not (root / "project.c3proj").exists():
        print(f"no project.c3proj in {root or Path.cwd()}: run this from the project folder or pass "
              f"--project <folder>", file=sys.stderr)
        return 1
    found = tools()
    if found is None:
        print(INSTALL)
        print("nothing measured: no ffmpeg")
        return 0
    ffmpeg, ffprobe = found
    files = audio_files(root, args.files)
    table, cues = cue_table(root)
    reference = float(table.get("reference_lufs", REFERENCE)) if isinstance(table, dict) else REFERENCE
    lines: list[str] = []
    findings: list[str] = []
    untiered: list[str] = []
    for path in files:
        if not path.exists():
            findings.append(f"missing: {path.relative_to(root).as_posix() if path.is_relative_to(root) else path} "
                            f"does not exist; name a file under sounds/ or music/")
            continue
        measure(ffmpeg, ffprobe, path, root, cues, reference, lines, findings, untiered)
    if untiered:
        lows, highs = zip(*TIERS.values())
        findings.append(f"tier: {len(untiered)} file{'s' if len(untiered) > 1 else ''} under sounds/ "
                        f"{'have' if len(untiered) > 1 else 'has'} no entry in {CUES.as_posix()} "
                        f"({', '.join(untiered[:8])}{', ...' if len(untiered) > 8 else ''}), so each is measured "
                        f"against the whole span of the tiers, {reference + min(lows):.0f} to "
                        f"{reference + max(highs):.0f} LUFS. Add a cue per file, {{\"name\": \"{untiered[0]}\", "
                        f"\"role\": \"reward|impact\", \"tier\": \"key|action|repeat\"}}, under \"cues\"")
    out = lines + findings
    shown = c3.fitting(out, args.limit)
    for line in out[:shown]:
        print(line)
    if shown < len(out):
        print(f"... {len(out) - shown} more; --limit 0 prints them all")
    summary = f"{len(lines)} files measured against M = {reference:.0f} LUFS"
    if not files:
        summary = "no audio files under sounds/ or music/"
    print(f"{len(findings)} findings: {summary}" if findings else f"ok: {summary}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
