"""check_sounds.py: the sound and music files of a project measured against sound.md's tiers and ceilings.

The fixtures are synthesized by ffmpeg at test time: a tone at a chosen level, with silence
where a case needs it, encoded as the project's sounds are. Without ffmpeg every test here
skips, except the one that says what the script does without it.
"""
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.skill_helpers import tool, INSTALLED

FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")
NEEDS_FFMPEG = pytest.mark.skipif(not FFMPEG, reason="ffmpeg and ffprobe are not installed")


def synth(path: Path, seconds: float, db: float, head_silence: float = 0.0, freq: int = 440, codec: str = "libopus",
          channels: int = 2) -> None:
    """A sine of seconds at db dBFS peak, after head_silence of silence, encoded to path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    filters = f"volume={db}dB"
    if head_silence:
        ms = int(head_silence * 1000)
        filters = f"adelay={ms}|{ms},{filters}"
    tone = f"sin(2*PI*{freq}*t)"
    source = f"aevalsrc=exprs='{'|'.join([tone] * channels)}':s=48000:d={seconds}"   # stereo made as stereo: an upmix is -3 dB
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "lavfi", "-i", source, "-af", filters, "-c:a", codec,
                    str(path)], check=True, capture_output=True, timeout=60)


def cue_table(project: Path, cues: list[dict]) -> None:
    (project / "tools").mkdir(exist_ok=True)
    (project / "tools" / "sounds.json").write_text(json.dumps({"cues": cues}), encoding="utf-8")


@NEEDS_FFMPEG
def test_check_sounds_measures_each_file_and_names_the_gain(project):
    cue_table(project, [{"name": "hit", "role": "impact", "tier": "repeat"},
                        {"name": "chord", "role": "reward", "tier": "action", "pitched": True}])
    synth(project / "sounds" / "hit.webm", 0.3, -2)                     # far too loud for the repeat tier
    synth(project / "sounds" / "chord.webm", 0.5, -40)                  # too quiet for the action tier
    synth(project / "sounds" / "late.webm", 0.5, -30, head_silence=0.12)   # no cue, and it starts late
    synth(project / "sounds" / "old.mp3", 0.5, -30, codec="libmp3lame")
    synth(project / "music" / "song.webm", 5, -2)                       # over the music ceiling and its window
    code, out = tool(project, "check_sounds")
    assert code == 1, out
    lines = out.splitlines()
    assert re.search(r"^sounds/hit\.webm: 0\.3\d\d s, 2 ch, 48000 Hz, opus \d+ kb/s; loudest 400 ms -\d+\.\d LUFS, "
                     r"integrated -\d+\.\d LUFS, true peak -\d+\.\d dBFS, silence head 0\.0\d\d s tail 0\.\d\d\d s; "
                     r"repeat \(impact\): -37 to -29 LUFS, ceiling -3 dBFS$", out, re.M), out
    assert re.search(r"^music/song\.webm: 5\.0\d\d s, .*; loudest 3 s -\d+\.\d LUFS, .*; music: -31 to -29 LUFS, "
                     r"ceiling -12 dBFS$", out, re.M), out
    assert re.search(r"^loudness: sounds/hit\.webm is at -\d+\.\d LUFS on its loudest 400 ms above 150 Hz; "
                     r"repeat \(impact\) is -37 to -29\. Apply -\d+\.\d dB: ffmpeg -i sounds/hit\.webm "
                     r"-af volume=-\d+\.\ddB -c:a libopus -b:a 96k sounds/hit\.gained\.webm$", out, re.M), out
    assert "peak: sounds/hit.webm has a true peak of " in out and "over the -3 dBFS ceiling of an effect" in out
    assert re.search(r"^peak: music/song\.webm has a true peak of -\d\.\d dBFS, over the -12 dBFS ceiling of music; .*"
                     r"alimiter=limit=0\.224 -c:a libopus -b:a 96k music/song\.limited\.webm", out, re.M), out
    assert re.search(r"^silence: sounds/late\.webm starts with 0\.1\d\d s of silence, more than the 0\.03 s lead a play "
                     r"scheduled on the music grid gets \(sound\.md, \"Immediate or on the grid\"\), so it lands late by that "
                     r"much; trim it, ffmpeg -i sounds/late\.webm -af atrim=start=0\.1\d\d,asetpts=PTS-STARTPTS -c:a libopus "
                     r"-b:a 96k sounds/late\.trimmed\.webm$", out, re.M), out
    assert re.search(r"^codec: sounds/old\.mp3 is mp3, and a project's sound and music are WebM Opus; encode it, "
                     r"ffmpeg -i sounds/old\.mp3 -c:a libopus -b:a 96k old\.webm$", out, re.M), out
    assert re.search(r"^tier: 2 files under sounds/ have no entry in tools/sounds\.json \(late, old\), so each is "
                     r"measured against the whole span of the tiers, -37 to -16 LUFS\. Add a cue per file, "
                     r'\{"name": "late", "role": "reward\|impact", "tier": "key\|action\|repeat"\}, under "cues"$',
                     out, re.M), out
    assert lines[-1].startswith("8 findings: 5 files measured against M = -30 LUFS"), lines[-1]
    # The gain a loudness finding names, applied with the command it prints, puts the file in its window
    gain_line = next(l for l in lines if l.startswith("loudness: sounds/chord.webm"))
    gain = float(re.search(r"Apply ([-+]\d+\.\d) dB", gain_line).group(1))
    assert 10 < gain < 25, gain_line
    command = shlex.split(gain_line.split("dB: ", 1)[1])
    subprocess.run(command, cwd=project, check=True, capture_output=True, timeout=60)
    gained = project / "sounds" / "chord.gained.webm"
    assert gained.exists()
    shutil.move(gained, project / "sounds" / "chord.webm")
    code, out = tool(project, "check_sounds", "sounds/chord.webm")
    assert code == 0, out
    assert "loudness:" not in out
    assert re.search(r"^sounds/chord\.webm: .*; loudest 400 ms -2[3-7]\.\d LUFS, .*; action \(reward, pitched\): "
                     r"-30 to -21 LUFS, ceiling -3 dBFS$", out, re.M), out
    assert out.splitlines()[-1] == "ok: 1 files measured against M = -30 LUFS"


@NEEDS_FFMPEG
def test_check_sounds_reads_the_roles_from_the_cue_table_and_the_folder(project):
    """A stem in sounds/ is music through its cue; a file in music/ is music without one; a cue table's
    reference moves every window; a short file is still measured; a named file that is missing is said."""
    (project / "tools").mkdir(exist_ok=True)
    (project / "tools" / "sounds.json").write_text(json.dumps(
        {"reference_lufs": -24, "cues": [{"name": "stem", "role": "music"}]}), encoding="utf-8")
    synth(project / "sounds" / "stem.webm", 4, -40, channels=1)
    synth(project / "music" / "loop.webm", 4, -40)
    synth(project / "sounds" / "tick.webm", 0.08, -30)
    code, out = tool(project, "check_sounds")
    assert code == 1, out
    assert re.search(r"^sounds/stem\.webm: 4\.0\d\d s, 1 ch, .*; loudest 3 s -\d+\.\d LUFS, .*; music: -25 to -23 LUFS, "
                     r"ceiling -12 dBFS$", out, re.M), out
    assert re.search(r"^music/loop\.webm: .*; music: -25 to -23 LUFS", out, re.M), out
    assert re.search(r"^sounds/tick\.webm: 0\.0\d\d s, .*; loudest 400 ms -\d+\.\d LUFS, integrated -\d+\.\d LUFS, "
                     r"true peak -\d+\.\d dBFS, .*; no tier: -31 to -10 LUFS", out, re.M), out
    assert "loudness: sounds/stem.webm is at " in out and "-b:a 64k sounds/stem.gained.webm" in out
    assert out.splitlines()[-1].startswith("4 findings: 3 files measured against M = -24 LUFS")
    code, out = tool(project, "check_sounds", "sounds/none.webm")
    assert code == 1 and "missing: sounds/none.webm does not exist; name a file under sounds/ or music/" in out
    code, out = tool(project, "check_sounds", "sounds/tick.webm")
    assert code == 1 and out.splitlines()[-1] == "2 findings: 1 files measured against M = -24 LUFS", out


@NEEDS_FFMPEG
def test_check_sounds_passes_a_project_without_audio_and_caps_its_output(project):
    code, out = tool(project, "check_sounds")
    assert code == 0 and out.splitlines()[-1] == "ok: no audio files under sounds/ or music/", out
    cue_table(project, [])
    for n in range(6):
        synth(project / "sounds" / f"s{n}.webm", 0.2, -1)
    code, out = tool(project, "check_sounds", "--limit", "600")
    assert code == 1, out
    assert re.search(r"^\.\.\. \d+ more; --limit 0 prints them all$", out, re.M), out
    assert out.splitlines()[-1].startswith("13 findings: 6 files measured"), out


def test_check_sounds_without_ffmpeg_measures_nothing_and_passes(project):
    env = {k: v for k, v in os.environ.items() if k not in ("CONSTRUCT3_RAG", "PATH")}
    env.update(PATH="", PYTHONIOENCODING="utf-8", CONSTRUCT3_RAG_OFFLINE="1")
    p = subprocess.run([sys.executable, f"{INSTALLED}/scripts/check_sounds.py", "--rag", str(Path(__file__).parents[1])],
                       cwd=project, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert p.returncode == 0, p.stdout + p.stderr
    lines = p.stdout.splitlines()
    assert lines[0].startswith("ffmpeg and ffprobe are not on PATH: install ffmpeg (")
    assert lines[-1] == "nothing measured: no ffmpeg"


def test_check_sounds_help_names_examples_and_exit_codes(project):
    code, out = tool(project, "check_sounds", "--help")
    assert code == 0
    assert "examples:" in out and "sounds/merge.webm" in out and "exit codes:" in out
    assert "--limit" in out and "FILE" in out
