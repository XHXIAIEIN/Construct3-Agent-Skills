"""Measure the timing of a recorded effect against the four parts of vfx-timing.md.

    python scripts/measure_timing.py VIDEO [--fps 60] [--from SECONDS] [--csv FILE]

The video is a recording of this project's effect, at a steady frame rate,
with nothing else moving on screen. The script decodes it to grey frames,
measures each frame, finds the effect's events and splits each into the
four parts that Construct3-Cookbook/guides/recipes/vfx-timing.md names: a
rise, a peak, a fall and an ember. It prints, per event, the frame of each
boundary, the count of each part, and the ratio of the rise to the fall.

The ratio separates the two kinds of effect that the page's table holds:

  an impact   rise : fall of 1.0 to 2.0
  a charge    rise : fall of 4.4 to 5.4

A ratio between the rows is not an error; the page's sample holds no
effect there. The script names it as such, because the shape is then one
the page does not cover.

An event that ends at its peak has no fall inside it: the effect holds, or
the recording ends before it falls. A ratio there would be the rise over a
forced 1, which is not a ratio of two parts, so the script names the effect
an ambient field and says which of the two readings it cannot tell apart.

--from leaves out a title card. A reel that opens on a white card shows a
brightness jump at the cut, and a measure that starts at the card takes
the cut for the effect's peak.

Each frame is measured on a grid, not per pixel: the brightness total, the
count of bright cells, and the brightness-weighted centre and radius. That
is enough for the four parts and the ratio, and it keeps the script to the
standard library. The numbers are therefore coarser than a per-pixel
measure, and a count of cells is not a count of particles.

Needs ffmpeg and ffprobe on PATH. Without them nothing is measured, and the
script says so and exits 3: the video is not checked, which is not a pass.

Exit 0: the last line starts with ok:. Exit 1: an event differs from the
recipe, or the video could not be read. Exit 3: no ffmpeg, nothing measured.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import c3project as c3

GRID = 8                     # cells across, and down
IMPACT = (1.0, 2.0)          # rise : fall, from vfx-timing.md
CHARGE = (4.4, 5.4)
BRIGHT = 0.55                # a cell over this share of full brightness counts as lit

# A cell's mean grey -> 255 when lit, else 0, so sum(translated) / 255 counts cells.
LIT = bytes(255 if v >= int(BRIGHT * 255) else 0 for v in range(256))


def probe(ffprobe: str, path: Path) -> dict | None:
    """The stream's width, height, frame rate and frame count, or None."""
    out = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate,nb_frames,duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=False)
    if out.returncode != 0 or not out.stdout.strip():
        return None
    try:
        stream = json.loads(out.stdout)["streams"][0]
    except (KeyError, IndexError, json.JSONDecodeError):
        return None
    num, _, den = stream.get("r_frame_rate", "0/1").partition("/")
    try:
        fps = float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    try:
        width = int(stream["width"])
        height = int(stream["height"])
    except (KeyError, ValueError):
        return None
    return {"width": width, "height": height, "fps": fps,
            "frames": int(stream.get("nb_frames") or 0)}


def grey_frames(ffmpeg: str, path: Path, width: int, height: int, skip: float):
    """Yield (index, bytes) of grey frames at the given size, aspect kept."""
    cmd = [ffmpeg, "-v", "error"]
    if skip > 0:
        cmd += ["-ss", f"{skip:.3f}"]
    cmd += ["-i", str(path), "-vf", f"scale={width}:{height}:flags=area",
            "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=width * height * 4)
    size = width * height
    index = 0
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        yield index, buf
        index += 1
    proc.stdout.close()
    proc.wait()


def cells(grey: bytes, width: int, height: int) -> list[float]:
    """The mean brightness of each grid cell, 0 to 1, row by row."""
    cw, ch = width / GRID, height / GRID
    out: list[float] = []
    for gy in range(GRID):
        y0, y1 = int(gy * ch), int((gy + 1) * ch)
        if y1 <= y0:
            y1 = y0 + 1
        for gx in range(GRID):
            x0, x1 = int(gx * cw), int((gx + 1) * cw)
            if x1 <= x0:
                x1 = x0 + 1
            total = 0
            count = 0
            for y in range(y0, min(y1, height)):
                row = grey[y * width + x0: y * width + min(x1, width)]
                total += sum(row)
                count += len(row)
            out.append(total / (count * 255) if count else 0.0)
    return out


def measure(grey: bytes, width: int, height: int) -> dict:
    """One frame's brightness total, lit cells, centre and radius."""
    grid = cells(grey, width, height)
    total = sum(grid) / len(grid)
    lit = sum(1 for v in grid if v >= BRIGHT)
    # The brightness-weighted centre and radius, in cells from the grid's centre.
    weight = 0.0
    sx = sy = 0.0
    for i, v in enumerate(grid):
        w = v if v > 0.04 else 0.0
        if not w:
            continue
        gx, gy = i % GRID, i // GRID
        weight += w
        sx += w * gx
        sy += w * gy
    if weight <= 1e-6:
        return {"lum": total, "lit": lit, "cx": GRID / 2, "cy": GRID / 2, "rad": 0.0}
    cx, cy = sx / weight, sy / weight
    var = 0.0
    for i, v in enumerate(grid):
        w = v if v > 0.04 else 0.0
        if not w:
            continue
        gx, gy = i % GRID, i // GRID
        var += w * ((gx - cx) ** 2 + (gy - cy) ** 2)
    return {"lum": total, "lit": lit, "cx": cx, "cy": cy, "rad": (var / weight) ** 0.5}


def diff(prev: bytes | None, grey: bytes) -> float:
    """The share of bits that changed since the previous frame."""
    if prev is None or len(prev) != len(grey):
        return 0.0
    a = int.from_bytes(prev, "big")
    b = int.from_bytes(grey, "big")
    return (a ^ b).bit_count() / (len(grey) * 8)


def events(rows: list[dict], floor: float) -> list[tuple[int, int]]:
    """The runs of frames whose change is at or over the floor, merged across short gaps.

    A frame at the floor counts. The floor is the 60th percentile of every
    frame's change, and a slow ramp makes many frames whose change is the same
    size, so that size is the floor. A strict test would drop every one of
    them and lose the first frames of a charge or an ambient field, which moves
    the baseline into the rise and shortens the fall as well.
    """
    spans: list[list[int]] = []
    start = None
    for i, r in enumerate(rows):
        if r["mo"] >= floor:
            if start is None:
                start = i
        elif start is not None:
            spans.append([start, i - 1])
            start = None
    if start is not None:
        spans.append([start, len(rows) - 1])
    merged: list[list[int]] = []
    for s, e in spans:
        if merged and s - merged[-1][1] <= 6:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return [(rise_start(rows, s), e) for s, e in merged if e - s >= 4]


def rise_start(rows: list[dict], a: int, cap: int = 30) -> int:
    """The frame where the rise begins, walked back from the detected start.

    A rise that starts in the dark changes few bits a frame, so its first
    frames can fall under the floor and be left out: the baseline then takes
    them for the background, which lifts it into the rise and shortens the
    fall as well. Those frames are still dimmer than the frame after them and
    brighter than the plateau before them, so the walk stops at the plateau.
    """
    steps = 0
    while a >= 2 and steps < cap:
        before, before_that = rows[a - 1]["lum"], rows[a - 2]["lum"]
        if not (before < rows[a]["lum"] and before > before_that):
            break
        a -= 1
        steps += 1
    return a


def parts(rows: list[dict], a: int, b: int) -> dict:
    """Split one event into a rise, a peak, a fall and a tail.

    The rise ends at the brightest frame. The fall runs from that frame to
    the frame where the brightness is back to half of what the event added,
    and holds the peak in its first frames. The tail runs from there to the
    frame where the brightness is back within 5 % of the gain.
    """
    seg = rows[a:b + 1]
    lums = [r["lum"] for r in seg]
    before = rows[max(0, a - 4):a]
    base = sum(r["lum"] for r in before) / len(before) if before else lums[0]
    top = max(lums)
    gain = top - base
    pk = lums.index(top)
    if gain <= 1e-6:
        return {"frames": len(seg), "base": base, "top": top, "rise": 0, "peak": 0,
                "fall": 0, "tail": 0, "ratio": 0.0, "flat": True, "hold": False, "peak_at": pk}
    # The peak part ends where the brightness has lost 8 % of the gain.
    peak_end = pk
    while peak_end + 1 < len(lums) and lums[peak_end + 1] >= base + gain * 0.92:
        peak_end += 1
    # The fall ends at half of the gain, counted from the peak.
    half = base + gain * 0.5
    fall_end = pk
    while fall_end + 1 < len(lums) and lums[fall_end + 1] >= half:
        fall_end += 1
    # An event that ends on its peak has no fall inside it: the effect holds,
    # or the recording stops before it falls. There is nothing to divide the
    # rise by, so the ratio stays 0 rather than becoming the rise over 1.
    hold = fall_end == pk and pk == len(lums) - 1
    # The tail ends where the brightness is back within 5 % of the gain.
    tail_end = fall_end
    while tail_end + 1 < len(lums) and lums[tail_end + 1] >= base + gain * 0.05:
        tail_end += 1
    fall = 0 if hold else max(1, fall_end - pk)
    return {"frames": len(seg), "base": base, "top": top, "rise": pk,
            "peak": max(1, peak_end - pk + 1), "fall": fall,
            "tail": 0 if hold else max(0, tail_end - fall_end),
            "ratio": 0.0 if hold else pk / fall,
            "flat": False, "hold": hold, "peak_at": pk}


def kind(ratio: float, flat: bool, hold: bool = False, rise: int = 1) -> tuple[str, str]:
    """The kind of effect a ratio names, and a finding when the page has no row for it."""
    if flat:
        return "ambient", ""
    if hold:
        return "ambient", ("the event ends at its peak, so it has no fall to count: either the "
                           "effect holds, which vfx-timing.md builds as a state with its own on "
                           "and off, or the recording stops before the effect falls; record past "
                           "the end of the effect to tell the two apart")
    if rise <= 0:
        return "no rise", ("the effect is at its brightest in its first frame and only fades, so "
                           "there is no rise to count; vfx-timing.md starts the measure after a "
                           "title card, whose cut reads the same way")
    if IMPACT[0] <= ratio <= IMPACT[1]:
        return "an impact", ""
    if CHARGE[0] <= ratio <= CHARGE[1]:
        return "a charge", ""
    if ratio < IMPACT[0]:
        return "unusual", (f"rise : fall = {ratio:.2f} is under the impact row's {IMPACT[0]}, "
                           f"so the effect rises and falls in about one length; "
                           f"vfx-timing.md says that reads as a sprite that blinks")
    if ratio > CHARGE[1]:
        return "unusual", (f"rise : fall = {ratio:.2f} is over the charge row's {CHARGE[1]}, "
                           f"so the effect holds longer than the page's sample")
    return "unusual", (f"rise : fall = {ratio:.2f} falls between the page's rows "
                       f"(an impact ends at {IMPACT[1]}, a charge starts at {CHARGE[0]}); "
                       f"the page's sample holds no effect there, so read this as a shape it does not cover")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("video", type=Path, metavar="VIDEO")
    ap.add_argument("--fps", type=float, default=0.0, help="the recording's frame rate; default: read from the file")
    ap.add_argument("--from", dest="skip", type=float, default=0.0, metavar="SECONDS",
                    help="start this many seconds in, to leave out a title card")
    ap.add_argument("--width", type=int, default=192, help="decode at this width; default: 192")
    ap.add_argument("--csv", type=Path, metavar="FILE", help="write one row per frame to this file")
    ap.add_argument("--limit", type=int, default=2000, help="print at most this many characters; 0 prints all")
    args = ap.parse_args(argv)

    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        print("ffmpeg and ffprobe are needed on PATH; nothing was measured")
        return 3
    if not args.video.is_file():
        print(f"no video at {args.video}; name a recording of the effect")
        return 1
    info = probe(ffprobe, args.video)
    if not info:
        print(f"could not read the video stream of {args.video}")
        return 1
    fps = args.fps or info["fps"]
    if fps <= 0:
        print(f"could not read the frame rate of {args.video}; give --fps")
        return 1
    width = max(GRID * 4, args.width)
    height = max(GRID * 4, round(width * info["height"] / info["width"]))

    rows: list[dict] = []
    prev = None
    for index, grey in grey_frames(ffmpeg, args.video, width, height, args.skip):
        if len(grey) != width * height:
            break
        m = measure(grey, width, height)
        m["i"] = index
        m["ms"] = round(index * 1000.0 / fps, 1)
        m["mo"] = round(diff(prev, grey), 5)
        rows.append(m)
        prev = grey
    if not rows:
        print(f"no frames decoded from {args.video}")
        return 1
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", encoding="utf-8") as fh:
            fh.write("frame,ms,lum,lit,change,radius,cx,cy\n")
            for r in rows:
                fh.write(f"{r['i']},{r['ms']},{r['lum']:.4f},{r['lit']},{r['mo']:.5f},"
                         f"{r['rad']:.3f},{r['cx']:.2f},{r['cy']:.2f}\n")

    changes = sorted(r["mo"] for r in rows)
    floor = max(0.0015, changes[int(len(changes) * 0.6)])
    found = events(rows, floor)
    lines: list[str] = []
    findings: list[str] = []
    if not found:
        print(f"ok: {len(rows)} frames measured at {fps:g} fps, no event over a change of {floor:.4f}; "
              f"record the effect alone, with nothing else moving")
        return 0
    for a, b in found:
        p = parts(rows, a, b)
        name, finding = kind(p["ratio"], p["flat"], p["hold"], p["rise"])
        ratio_text = "  -  " if p["hold"] else f"{p['ratio']:.2f}"
        lines.append(
            f"{rows[a]['ms']:8.1f}-{rows[b]['ms']:8.1f} ms  {p['frames']:3d} frames  "
            f"rise {p['rise']:2d}  peak {p['peak']:2d}  fall {p['fall']:2d}  tail {p['tail']:2d}  "
            f"rise:fall {ratio_text}  {name}")
        if finding:
            findings.append(f"event at {rows[a]['ms']:.1f} ms: {finding}")
    out = lines + findings
    shown = c3.fitting(out, args.limit)
    for line in out[:shown]:
        print(line)
    if shown < len(out):
        print(f"... {len(out) - shown} more; --limit 0 prints them all")
    frame_note = f"{len(rows)} frames at {fps:g} fps, {len(found)} event{'s' if len(found) != 1 else ''}"
    if findings:
        print(f"{len(findings)} findings: {frame_note}; the four parts are in "
              f"Construct3-Cookbook/guides/recipes/vfx-timing.md")
        return 1
    print(f"ok: {frame_note}, each within the rows of vfx-timing.md")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
