"""make_sounds.py: placeholder sounds and music from the cue table, which check_sounds.py then passes."""
import json
import re
import shutil
import subprocess

import pytest

from tests.skill_helpers import tool, check

FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")
NEEDS_FFMPEG = pytest.mark.skipif(not FFMPEG, reason="ffmpeg and ffprobe are not installed")


def example_table(project) -> dict:
    code, out = tool(project, "make_sounds", "--example")
    assert code == 0, out
    table = json.loads(out)
    (project / "tools").mkdir(exist_ok=True)
    (project / "tools" / "sounds.json").write_text(json.dumps(table), encoding="utf-8")
    return table


@NEEDS_FFMPEG
def test_make_sounds_writes_files_that_check_sounds_passes(project):
    table = example_table(project)
    names = [c["name"] for c in table["cues"]]
    code, out = tool(project, "make_sounds", "--dry-run")
    assert code == 0 and out.splitlines()[-1] == f"ok: dry run, {len(names)} files would be written", out
    assert not (project / "sounds").exists() or not list((project / "sounds").glob("*.webm"))
    code, out = tool(project, "make_sounds")
    assert code == 0, out
    assert out.splitlines()[-1].startswith(f"ok: {len(names)} files written, {len(names)} listed in project.c3proj, "
                                            f"layers in tools/sounds.json; next: python "), out
    for name in names:
        assert (project / "sounds" / f"{name}.webm").exists(), name
        assert re.search(rf"^sounds/{name}\.webm: \d+\.\d\d\d s, [12] ch, 48000 Hz, opus \d+ kb/s; ", out, re.M), name
    assert re.search(r"^sounds/theme\.webm: 1\d\.\d\d\d s, 2 ch, .*; loudest 3 s -(29|30)\.\d LUFS, .*; "
                     r"music: -31 to -29 LUFS, ceiling -12 dBFS$", out, re.M), out
    assert re.search(r"^sounds/hit\.webm: .*; repeat \(impact\): -37 to -29 LUFS, ceiling -3 dBFS$", out, re.M), out
    # The measurer passes every file, and the checker finds each listed
    code, out = tool(project, "check_sounds")
    assert code == 0 and out.splitlines()[-1] == f"ok: {len(names)} files measured against M = -30 LUFS", out
    proj = json.loads((project / "project.c3proj").read_text(encoding="utf-8"))
    items = proj["rootFileFolders"]["sound"]["items"]
    assert sorted(i["name"] for i in items) == sorted(f"{n}.webm" for n in names)
    assert all(i["type"] == "audio/webm; codecs=opus" and 10 ** 14 <= i["sid"] < 10 ** 15 for i in items)
    assert "is not listed in project.c3proj" not in check(project)[1]
    # The pitched layers went back into the cue table; an impact has none
    written = json.loads((project / "tools" / "sounds.json").read_text(encoding="utf-8"))
    by_name = {c["name"]: c for c in written["cues"]}
    assert by_name["merge"]["layers"][0] == {"frequency": 440.0, "start": 0.0, "decay_to_-12dB": pytest.approx(0.2487, abs=1e-3)}
    assert by_name["hit"]["layers"] == [] and by_name["hit"]["made"]["file"] == "sounds/hit.webm"
    assert len(by_name["theme"]["layers"]) == 12 and by_name["theme"]["layers"][3]["start"] == pytest.approx(2.4)
    # A second run replaces its own files
    code, out = tool(project, "make_sounds")
    assert code == 0 and out.splitlines()[-1].startswith(f"ok: {len(names)} files written, 0 listed"), out


@NEEDS_FFMPEG
def test_make_sounds_refuses_a_file_that_is_not_its_own(project):
    example_table(project)
    foreign = project / "sounds" / "hit.webm"
    foreign.parent.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=300:duration=0.2",
                    "-c:a", "libopus", str(foreign)], check=True, capture_output=True, timeout=60)
    before = foreign.read_bytes()
    code, out = tool(project, "make_sounds")
    assert code == 2, out
    assert out.splitlines()[0] == ("sounds/hit.webm exists and does not carry the c3-sound tag, so it is not this "
                                   "script's; rename the cue, delete the file, or pass --replace")
    assert out.splitlines()[-1] == "1 files in the way: nothing written"
    assert foreign.read_bytes() == before and not (project / "sounds" / "merge.webm").exists()
    code, out = tool(project, "make_sounds", "--replace")
    assert code == 0 and foreign.read_bytes() != before, out


@NEEDS_FFMPEG
def test_make_sounds_renders_the_hard_look(project):
    table = example_table(project)
    table["look"] = "hard"
    table["cues"] = [c for c in table["cues"] if c["name"] in ("level_clear", "hit")]
    (project / "tools" / "sounds.json").write_text(json.dumps(table), encoding="utf-8")
    code, out = tool(project, "make_sounds")
    assert code == 0 and out.splitlines()[-1].startswith("ok: 2 files written"), out
    layers = {c["name"]: c["layers"] for c in json.loads((project / "tools" / "sounds.json").read_text("utf-8"))["cues"]}
    assert [round(l["frequency"] / layers["level_clear"][0]["frequency"], 2) for l in layers["level_clear"]] == [1, 2.76, 5.4]


def test_make_sounds_refuses_a_table_it_cannot_read(project):
    code, out = tool(project, "make_sounds")
    assert code == 1 and out.startswith("no tools/sounds.json in ") and "--example > tools/sounds.json" in out, out
    (project / "tools").mkdir(exist_ok=True)
    (project / "tools" / "sounds.json").write_text(json.dumps({"cues": [
        {"name": "a", "role": "noise", "tier": "key"}, {"name": "b", "role": "impact", "tier": "loud"},
        {"name": "c/d", "role": "impact", "tier": "key"}]}), encoding="utf-8")
    code, out = tool(project, "make_sounds")
    if not FFMPEG:
        assert code == 1 and out.startswith("ffmpeg and ffprobe are not on PATH")
        return
    assert code == 1, out
    assert 'cue a: "role" is one of reward, impact, music, not \'noise\'' in out
    assert 'cue b: "tier" is one of key, action, repeat, not \'loud\'' in out
    assert "cue 'c/d': \"name\" is the file's stem" in out
    assert out.splitlines()[-1] == "3 findings: nothing written"


def test_make_sounds_help_names_examples_and_exit_codes(project):
    code, out = tool(project, "make_sounds", "--help")
    assert code == 0 and "examples:" in out and "--example > tools/sounds.json" in out and "exit codes:" in out
