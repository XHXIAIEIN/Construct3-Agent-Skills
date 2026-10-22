"""measure_timing.py: a recorded effect's four parts measured against vfx-timing.md.

The fixtures are synthesized by ffmpeg at test time: flat grey frames whose
brightness follows a chosen curve, encoded as a recording is. Without ffmpeg
every test here skips, except the one that says what the script does without
it.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.skill_helpers import SKILL

SCRIPT = SKILL / "scripts" / "measure_timing.py"
FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")
NEEDS_FFMPEG = pytest.mark.skipif(not FFMPEG, reason="ffmpeg and ffprobe are not installed")


def synth(path: Path, lums: list[int], fps: int = 60, width: int = 192, height: int = 108) -> None:
    """A video of flat grey frames at the given brightness, 0 to 255."""
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = b"".join(bytes([v]) * (width * height) for v in lums)
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray",
         "-s", f"{width}x{height}", "-r", str(fps), "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-qp", "0", str(path)],
        input=raw, check=True, capture_output=True, timeout=120)


def run(*args: str) -> tuple[int, str]:
    """The script's exit code and its two streams joined, run as the skill runs it."""
    p = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent), timeout=180)
    return p.returncode, p.stdout + p.stderr


# The effect's first frame is 140 and its brightest is 255, seven frames
# later. Its fall reaches half of the gain (191) on its sixth frame, then a
# tail runs back to the base.
IMPACT = ([128] * 10
          + [140, 155, 175, 195, 215, 235, 248, 255]
          + [250, 245, 240, 230, 215, 200, 190, 150, 128]
          + [128] * 20)


@NEEDS_FFMPEG
def test_an_impact_rises_in_seven_frames_and_falls_in_six(tmp_path):
    video = tmp_path / "impact.mp4"
    synth(video, IMPACT)
    code, text = run(str(video))
    assert "an impact" in text, text
    assert "rise  7" in text, text
    assert "fall  6" in text, text


@NEEDS_FFMPEG
def test_a_flat_video_has_no_event(tmp_path):
    video = tmp_path / "flat.mp4"
    synth(video, [128] * 60)
    code, text = run(str(video))
    assert "no event" in text, text
    assert code == 0, text


def test_a_video_that_is_not_there_is_a_finding(tmp_path):
    code, text = run(str(tmp_path / "nothing.mp4"))
    assert "no video at" in text, text
    assert code == 1, text


def test_without_ffmpeg_nothing_is_measured(monkeypatch, tmp_path):
    """The script says so and exits 3, as check_sounds.py does: a check that did not run is no pass."""
    monkeypatch.setenv("PATH", str(tmp_path))
    code, text = run(str(tmp_path / "any.mp4"))
    assert "nothing was measured" in text, text
    assert code == 3, text


def test_the_ratio_rows_are_the_ones_the_page_states():
    """vfx-timing.md's two rows, read from the script's own constants."""
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        import measure_timing as mt
    finally:
        sys.path.pop(0)
    assert mt.IMPACT == (1.0, 2.0)
    assert mt.CHARGE == (4.4, 5.4)
    assert mt.kind(1.4, False)[0] == "an impact"
    assert mt.kind(5.0, False)[0] == "a charge"
    assert mt.kind(3.0, False)[0] == "unusual"
    assert mt.kind(0.8, False)[0] == "unusual"
    assert mt.kind(0.0, True)[0] == "ambient"
