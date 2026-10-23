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


def ramp(start: int, end: int, steps: int) -> list[int]:
    """`steps` values from start to end, both ends kept, no repeats."""
    span = end - start
    return [round(start + span * i / (steps - 1)) for i in range(steps)]


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


# A charge: 28 frames of small steps, then a fall of 6. The steps are the size
# the event floor sits on, and a strict test at the floor drops the first two
# of them, which moves the baseline into the rise and shortens the fall too.
CHARGE = ([128] * 10 + ramp(136, 255, 29)
          + [255, 245, 225, 210, 200, 192, 185, 160, 145, 138, 132] + [128] * 20)


@NEEDS_FFMPEG
def test_a_slow_rise_keeps_its_first_frames(tmp_path):
    video = tmp_path / "charge.mp4"
    synth(video, CHARGE)
    code, text = run(str(video))
    assert "a charge" in text, text
    assert "rise 28" in text, text
    assert "fall  6" in text, text


@NEEDS_FFMPEG
def test_an_effect_that_holds_is_an_ambient_field_without_a_ratio(tmp_path):
    """A rise of 90 that then holds: the event ends at its peak, so there is no
    fall to divide the rise by, and a ratio would be the rise over a forced 1."""
    video = tmp_path / "hold.mp4"
    synth(video, [128] * 10 + ramp(130, 255, 91) + [255] * 40 + [128] * 20)
    code, text = run(str(video))
    assert "ambient" in text, text
    assert "rise:fall   -" in text, text
    assert code == 1, text


# A rise of 90 to a peak that does not stay still: the frames after it are
# what is left of the event, still over half of the gain, and a ratio over
# them would read 4.50, a charge, for the wobble and 9.00 for the sag.
WOBBLE = [128] * 10 + ramp(130, 255, 91) + [255, 250] * 10 + [250] * 40 + [128] * 20
SAG = [128] * 10 + ramp(130, 255, 91) + ramp(254, 245, 10) + [245] * 40 + [128] * 20


@NEEDS_FFMPEG
@pytest.mark.parametrize("name, lums", [("wobble", WOBBLE), ("sag", SAG)])
def test_a_peak_that_moves_but_does_not_fall_is_a_hold(tmp_path, name, lums):
    video = tmp_path / f"{name}.mp4"
    synth(video, lums)
    code, text = run(str(video))
    assert "ambient" in text, text
    assert "a charge" not in text, text
    assert "rise:fall   -" in text, text
    assert code == 1, text


@NEEDS_FFMPEG
def test_a_fade_with_no_rise_says_so(tmp_path):
    video = tmp_path / "fade.mp4"
    synth(video, [128] * 10 + [255] * 6 + ramp(250, 128, 12) + [128] * 20)
    code, text = run(str(video))
    assert "no rise" in text, text
    assert code == 1, text


@NEEDS_FFMPEG
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
    assert mt.kind(0.0, False, True)[0] == "ambient"        # an event that never falls to half
    assert mt.kind(0.0, False, False, 0)[0] == "no rise"   # a fade with no rise
