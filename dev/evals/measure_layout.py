"""Measure the composition of the official game examples' one-screen layouts: how much of the
screen the box around their content covers, and how much larger their largest object is than
the next. The generator template's playfield checks take their thresholds from this. With
--text, measure their texts instead: each size as a share of the viewport's shorter side, the
sizes of a layout and how far apart they step, and how near the edge the nearest text sits.

    python evals/measure_layout.py --examples <Construct-Example-Projects>/example-projects
                                   [--text] [--out ROWS.json] [--rag FOLDER]

An example counts when its tags in data/c3-examples name a game ("Game template" or "Demo
game") and not "3D". A layout counts when it is one screen, at most 5% larger than the viewport
either way, is not a store of runtime templates (a name with "repository", "bank", "objects"
or "template"), and shows at least 4 instances. Content is every visible instance of a
scrolling layer, not a Text, not rotated, clipped to the viewport, less any that cover 80% of
it both ways, which are backdrops. A text is a Text, its size in pt drawn at 4/3 px, or a Sprite
Font, its character height times its scale, that shows a non-empty text; its distance to the
edge counts on a layout of one screen or a layer that does not scroll, from the sides its
letters align to. Exit codes: 0 measured, 2 bad arguments.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev"))

from scripts.measure_examples import RAG, box_on_screen, examples_meta, layers_in, load  # noqa: E402

STORES = re.compile(r"repositor|bank|objects|template", re.I)


def games(rag: Path) -> list[str]:
    """The ids of the examples tagged as 2D games."""
    return [gid for gid, meta in examples_meta(rag).items()
            if {"Game template", "Demo game"} & set(meta.get("tags", []))]


def content(layout: dict, vw: float, vh: float) -> list[tuple[str, tuple, float]]:
    """(type, box clipped to the viewport, area) of each instance that counts as content."""
    found = []
    for layer in layers_in(layout["layers"]):
        if not layer.get("isInitiallyVisible", True) or 0 in (layer.get("parallaxX", 1), layer.get("parallaxY", 1)):
            continue
        for inst in layer["instances"]:
            props, w = inst.get("properties", {}), inst.get("world")
            if props.get("initially-visible") is False or "text" in props or not w or w.get("angle"):
                continue
            box = box_on_screen(w, vw, vh)
            if not box:
                continue
            bw, bh = box[2] - box[0], box[3] - box[1]
            if bw >= 0.8 * vw and bh >= 0.8 * vh:
                continue
            found.append((inst["type"], box, bw * bh))
    return found


def measure(examples: Path, rag: Path) -> list[dict]:
    rows = []
    for gid in games(rag):
        proj = examples / gid / "project.c3proj"
        if not proj.is_file():
            continue
        p = load(proj)
        vw, vh = p["viewportWidth"], p["viewportHeight"]
        for f in sorted((examples / gid / "layouts").glob("*.json")):
            lay = json.loads(f.read_text(encoding="utf-8"))
            if lay["width"] > 1.05 * vw or lay["height"] > 1.05 * vh or STORES.search(lay["name"]):
                continue
            found = content(lay, vw, vh)
            if len(found) < 4:
                continue
            hull = [min(b[1][0] for b in found), min(b[1][1] for b in found),
                    max(b[1][2] for b in found), max(b[1][3] for b in found)]
            ranked = sorted(found, key=lambda b: -b[2])
            rows.append({"example": gid, "layout": lay["name"], "viewport": [vw, vh], "instances": len(found),
                         "covers": round((hull[2] - hull[0]) * (hull[3] - hull[1]) / (vw * vh), 3),
                         "focal": round(ranked[0][2] / ranked[1][2], 2), "largest": ranked[0][0], "next": ranked[1][0]})
    return rows


def text_px(props: dict) -> float | None:
    """Height in px of a text's letters: a Text's size in pt at 4/3 px, a Sprite Font's character
    height times its scale; None for any other instance."""
    if "font" in props and "size" in props:
        return props["size"] * 4 / 3
    if "character-height" in props:
        return props["character-height"] * props.get("scale", 1)
    return None


def edge_gap(props: dict, w: dict, vw: float, vh: float) -> float | None:
    """Distance in px from a text's letters to the nearest edge they align to; None when no side
    they align to lies within a quarter of the shorter side."""
    left = w["x"] - w.get("originX", 0) * w["width"]
    top = w["y"] - w.get("originY", 0) * w["height"]
    side = {"left": left, "right": vw - left - w["width"]}.get(props.get("horizontal-alignment", "left"))
    end = {"top": top, "bottom": vh - top - w["height"]}.get(props.get("vertical-alignment", "top"))
    gaps = [g for g in (side, end) if g is not None and -1 <= g < 0.25 * min(vw, vh)]
    return min(gaps) if gaps else None


def measure_text(examples: Path, rag: Path) -> list[dict]:
    """One row per layout that holds text: its text sizes as shares of the shorter side, and the
    distance of the text nearest the edge as one, or None."""
    rows = []
    for gid in games(rag):
        proj = examples / gid / "project.c3proj"
        if not proj.is_file():
            continue
        p = load(proj)
        vw, vh = p["viewportWidth"], p["viewportHeight"]
        short = min(vw, vh)
        for f in sorted((examples / gid / "layouts").glob("*.json")):
            lay = json.loads(f.read_text(encoding="utf-8"))
            one_screen = lay["width"] <= 1.05 * vw and lay["height"] <= 1.05 * vh
            sizes, gaps = [], []
            for layer in layers_in(lay["layers"]):
                fixed = layer.get("parallaxX", 1) == 0 and layer.get("parallaxY", 1) == 0
                for inst in layer["instances"]:
                    props, w = inst.get("properties", {}), inst.get("world")
                    px = text_px(props)
                    if px is None or not str(props.get("text", "")).strip():
                        continue
                    sizes.append(round(px / short, 4))
                    shown = layer.get("isInitiallyVisible", True) and props.get("initially-visible") is not False
                    gap = edge_gap(props, w, vw, vh) if w and shown and (one_screen or fixed) else None
                    if gap is not None:
                        gaps.append(gap / short)
            if sizes:
                rows.append({"example": gid, "layout": lay["name"], "viewport": [vw, vh], "sizes": sizes,
                             "edge": round(min(gaps), 4) if gaps else None})
    return rows


def report_text(rows: list[dict]) -> None:
    def cuts(vals: list[float]) -> str:
        vals = sorted(vals)
        return f"{len(vals)}, min {vals[0]:g} " + " ".join(
            f"p{int(k * 100)} {vals[min(len(vals) - 1, int(k * len(vals)))]:g}" for k in (0.05, 0.25, 0.5, 0.75))
    smallest: dict[str, float] = {}
    for r in rows:
        smallest[r["example"]] = min(smallest.get(r["example"], 1), *r["sizes"])
    print(f"smallest text of each example, share of the shorter side: {cuts(list(smallest.values()))}")
    counts = [len(set(r["sizes"])) for r in rows]
    print("distinct sizes in a layout: " + ", ".join(f"{k}: {counts.count(k)}" for k in sorted(set(counts))))
    several = [sorted(r["sizes"]) for r in rows if len(set(r["sizes"])) > 1]
    tops = [s.count(s[-1]) for s in several]
    print(f"layouts with two sizes or more that show one text at their largest size: {tops.count(1)} of {len(several)}")
    steps = [round(b / a, 2) for s in several for a, b in zip(sorted(set(s)), sorted(set(s))[1:])]
    print(f"step between a layout's sizes: {cuts(steps)}")
    edges = [r["edge"] for r in rows if r["edge"] is not None]
    print(f"nearest text to the edge, share of the shorter side: {cuts(edges)}; within 5%: "
          f"{sum(e < 0.05 for e in edges)} of {len(edges)}")


def share(rows: list[dict], key: str, test) -> str:
    n = sum(1 for r in rows if test(r[key]))
    return f"{n} of {len(rows)} ({100 * n / len(rows):.0f}%)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="example: python evals/measure_layout.py --examples ../Construct-Example-Projects/"
                                        "example-projects --out .local/docs/evidence/layout.json")
    ap.add_argument("--examples", type=Path, required=True, help="the example-projects folder of the clone")
    ap.add_argument("--text", action="store_true", help="measure the layouts' texts, not their content")
    ap.add_argument("--out", type=Path, help="write every measured layout here as JSON")
    ap.add_argument("--rag", type=Path, default=RAG, help="the Construct3-RAG folder, for the examples' tags")
    args = ap.parse_args()
    if not args.examples.is_dir():
        print(f"--examples {args.examples}: not a folder; pass <Construct-Example-Projects>/example-projects", file=sys.stderr)
        return 2
    rows = (measure_text if args.text else measure)(args.examples, args.rag)
    if not rows:
        print("no layout measured: check that --examples is the example-projects folder")
        return 0
    if args.text:
        report_text(rows)
    else:
        for key in ("covers", "focal"):
            vals = sorted(r[key] for r in rows)
            cuts = " ".join(f"p{int(k * 100)} {vals[min(len(vals) - 1, int(k * len(vals)))]:g}"
                            for k in (0.05, 0.1, 0.25, 0.5, 0.75, 0.9))
            print(f"{key}: {len(vals)} layouts, {cuts}")
        print(f"covers under 0.15: {share(rows, 'covers', lambda v: v < 0.15)}; 0.25 to 0.60: "
              f"{share(rows, 'covers', lambda v: 0.25 <= v <= 0.6)}; over 0.60: {share(rows, 'covers', lambda v: v > 0.6)}")
        print(f"focal 1.5 or more: {share(rows, 'focal', lambda v: v >= 1.5)}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
        print(f"rows in {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
