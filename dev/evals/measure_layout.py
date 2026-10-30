"""Measure the composition of the official game examples' one-screen layouts: how much of the
screen the box around their content covers, and how much larger their largest object is than
the next. The generator template's playfield checks take their thresholds from this. With
--text, measure their texts instead: each size as a share of the viewport's shorter side, the
sizes of a layout and how far apart they step, how near the edge the nearest text sits, and how
many items the screen's texts gather in one ninth of it while its corners stand empty. With
--screens, group the texts by kind of screen: title or menu, result, and play. Then measure the
largest text of each kind and the title image of each title screen. With --frame, measure how each
kind of screen frames its texts: how many sit on its vertical centre line, which corners they hold,
how many are set in capitals, their faces, and the colour of the screen's ground.

    python evals/measure_layout.py --examples <Construct-Example-Projects>/example-projects
                                   [--text | --screens | --frame] [--out ROWS.json]
                                   [--rag FOLDER]

An example counts when its tags in data/c3-examples name a game ("Game template" or "Demo
game") and not "3D". A layout counts when it is one screen, at most 5% larger than the viewport
either way, is not a store of runtime templates (a name with "repository", "bank", "objects"
or "template"), and shows at least 4 instances. Content is every visible instance of a
scrolling layer, not a Text, not rotated, clipped to the viewport, less any that cover 80% of
it both ways, which are backdrops. A text is a Text, its size in pt drawn at 4/3 px, or a Sprite
Font, its character height times its scale, that shows a non-empty text; its distance to the
edge counts on a layout of one screen or a layer that does not scroll, from the sides its
letters align to. A screen is a layout whose name says what it is. On a layout of play, a layer
whose name says so is a screen too. NO_SCREEN names the layouts and layers that are no screen.
A title image is the image of the game's name that TITLE_IMAGES names for a title screen. A
screen's ground is its lowest visible layer's colour when that layer is opaque, else the mean
colour, by alpha, of the first image that covers 80% of the viewport both ways, else none; --frame
needs Pillow to read that image. Exit codes: 0 measured, 2 bad arguments or no Pillow for --frame.
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
import review_look as rl  # noqa: E402  (on the path measure_examples sets)

STORES = re.compile(r"repositor|bank|objects|template", re.I)
NO_SCREEN = re.compile(r"repositor|bank|objects|template|credits|tutorial|debug|loading|login|palette", re.I)
RESULT = re.compile(r"gameover|levelover|success|congrat|^win$|finish|ending|endgame|finalscore|result|"
                    r"endoflevel|levelup", re.I)
TITLE = re.compile(r"title|menu|opening|intro|selection|pause|settings|options|clickanywhere", re.I)
# Each title screen's image, and the share of the image's height that its tallest line of capitals
# takes. Both were read by eye: the examples name their title images differently, and an image
# holds glow, plates and art around its letters.
TITLE_IMAGES = {("glokar", "TitleScreen"): ("Logo", 0.85), ("grukkle-onslaught", "MainMenu"): ("MMTitleGrukkle", 0.33),
                ("kitty-katcher", "TitleScreen"): ("Logo", 0.24), ("kiwi-story", "TitleScreen"): ("Logo", 0.5),
                ("overloaded-underqualified", "Menu"): ("MenuTitle", 0.34), ("poplab", "TitleScreen"): ("Logo_Large", 0.47),
                ("rat-purrsuit", "Menu"): ("MenuTitle", 0.31), ("selene", "MainMenu"): ("Menu_Title", 0.13),
                ("space-blaster", "Title"): ("logo", 0.75)}


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


def crowd(screen: list, holders: list, vw: float, vh: float) -> tuple[int, int]:
    """(most items in a ninth of the screen off its middle, corners holding none) of the texts on
    the screen, (box, layer, text) each, counted as review_look.py's crowd finding counts them: the
    one text inside a box of `holders`, the other instances on any layer, no larger than half the
    screen, is that object's label and is left out."""
    tagged = set()
    for hb, _ in holders:
        inner = [n for n, (box, _, _) in enumerate(screen) if rl.inside(box, hb)]
        if len(inner) == 1 and rl.area(hb) <= rl.OVERLAY * vw * vh:
            tagged.add(inner[0])
    texts = [(box, rl.worded(text)) for n, (box, _, text) in enumerate(screen)
             if n not in tagged and not rl.bar(box, vw, vh)]
    if not texts:
        return 0, 4
    held = rl.crowding(texts, vw, vh)["items"]
    return max((n for c, n in held.items() if c in rl.NINTHS), default=0), sum(c not in held for c in rl.CORNERS)


def measure_text(examples: Path, rag: Path) -> list[dict]:
    """One row per layout that holds text: its text sizes as shares of the shorter side, the
    distance of the text nearest the edge as one, or None, and, on a layout that is no store of
    templates, how crowded the screen's texts are."""
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
            sizes, gaps, screen, holders = [], [], [], []
            for n, layer in enumerate(layers_in(lay["layers"])):
                fixed = layer.get("parallaxX", 1) == 0 and layer.get("parallaxY", 1) == 0
                for inst in layer["instances"]:
                    props, w = inst.get("properties", {}), inst.get("world")
                    px = text_px(props)
                    if px is None and w and props.get("initially-visible") is not False and not w.get("angle"):
                        left, top = w["x"] - w.get("originX", 0) * w["width"], w["y"] - w.get("originY", 0) * w["height"]
                        holders.append(([left, top, left + w["width"], top + w["height"]], n))
                    if px is None or not str(props.get("text", "")).strip():
                        continue
                    sizes.append(round(px / short, 4))
                    shown = layer.get("isInitiallyVisible", True) and props.get("initially-visible") is not False
                    if not (w and shown and (one_screen or fixed)):
                        continue
                    gap = edge_gap(props, w, vw, vh)
                    if gap is not None:
                        gaps.append(gap / short)
                    left, top = w["x"] - w.get("originX", 0) * w["width"], w["y"] - w.get("originY", 0) * w["height"]
                    if 0 <= left + w["width"] / 2 <= vw and 0 <= top + w["height"] / 2 <= vh:
                        screen.append(([left, top, left + w["width"], top + w["height"]], n, str(props["text"])))
            if sizes:
                crowded = None if STORES.search(lay["name"]) or not screen else crowd(screen, holders, vw, vh)
                rows.append({"example": gid, "layout": lay["name"], "viewport": [vw, vh], "sizes": sizes,
                             "edge": round(min(gaps), 4) if gaps else None, "crowd": crowded})
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
    crowds = [(r["example"], r["layout"], *r["crowd"]) for r in rows if r["crowd"]]
    most = [c[2] for c in crowds]
    print("most items of the screen's texts in a ninth off its middle: "
          + ", ".join(f"{k}: {most.count(k)}" for k in sorted(set(most))))
    crowded = [f"{e} {lay}" for e, lay, n, empty in crowds if n >= 3 and empty >= 2]
    print(f"3 items or more in a ninth while 2 corners or more stand empty: {len(crowded)} of {len(crowds)}"
          + (f" ({'; '.join(crowded)})" if crowded else ""))


def screen_kind(name: str) -> str | None:
    """"title", "result" or "play" for a layout or layer of that name; None for no screen."""
    if NO_SCREEN.search(name):
        return None
    return "result" if RESULT.search(name) else "title" if TITLE.search(name) else "play"


def world_box(w: dict) -> list[float]:
    left, top = w["x"] - w.get("originX", 0) * w["width"], w["y"] - w.get("originY", 0) * w["height"]
    return [left, top, left + w["width"], top + w["height"]]


def met(a: list[float], b: list[float]) -> float:
    """Area where two boxes meet."""
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def title_image(image: tuple[str, float], drawn: list[tuple[str, dict, dict]], text_px_max: float,
                vw: float, vh: float) -> dict:
    """Measure the title image of a title screen.

    image: (object type, share of the image's height its capitals take), from TITLE_IMAGES.
    drawn: the screen's instances back to front, as (type, world, properties).
    Returns caps, the height of the capitals as a share of the shorter side; over_text, that
    height over the size of the screen's largest text; and covered, the largest share of the image
    that one instance drawn after it covers. Backdrops and fades, which cover 80% of the screen
    both ways, do not count."""
    otype, caps = image
    n = next(n for n, (t, _, _) in enumerate(drawn) if t == otype)
    w = drawn[n][1]
    box, h = world_box(w), abs(w["height"]) * caps
    covered = 0.0
    for other, ow, props in drawn[n + 1:]:
        # An object whose name holds the image's name is a layer of the title itself
        if otype in other or props.get("initially-visible") is False or (
                ow["width"] >= 0.8 * vw and ow["height"] >= 0.8 * vh):
            continue
        covered = max(covered, met(world_box(ow), box) / abs(w["width"] * w["height"]))
    return {"type": otype, "caps": round(h / min(vw, vh), 3), "over_text": round(h / text_px_max, 1),
            "covered": round(covered, 2)}


def measure_screens(examples: Path, rag: Path) -> list[dict]:
    """One row per screen that holds text: its kind, its text sizes as shares of the shorter side,
    and, on a title screen with an image in TITLE_IMAGES, its title image."""
    rows = []
    for gid in games(rag):
        proj = examples / gid / "project.c3proj"
        if not proj.is_file():
            continue
        p = load(proj)
        vw, vh = p["viewportWidth"], p["viewportHeight"]
        for f in sorted((examples / gid / "layouts").glob("*.json")):
            lay = json.loads(f.read_text(encoding="utf-8"))
            kind = screen_kind(lay["name"])
            if kind is None:
                continue
            screens: dict[tuple[str, str], list[float]] = {}
            drawn = []
            for layer in layers_in(lay["layers"]):
                own = kind if kind != "play" else screen_kind(layer["name"])
                for inst in layer["instances"]:
                    props, w = inst.get("properties", {}), inst.get("world")
                    if w and layer.get("isInitiallyVisible", True):
                        drawn.append((inst["type"], w, props))
                    px = text_px(props)
                    if own is None or px is None or not str(props.get("text", "")).strip():
                        continue
                    name = lay["name"] if kind != "play" or own == "play" else f"{lay['name']}/{layer['name']}"
                    screens.setdefault((name, own), []).append(px)
            for (name, own), sizes in screens.items():
                row = {"example": gid, "screen": name, "kind": own, "viewport": [vw, vh],
                       "sizes": sorted({round(px / min(vw, vh), 4) for px in sizes})}
                if (gid, name) in TITLE_IMAGES:
                    row["image"] = title_image(TITLE_IMAGES[gid, name], drawn, max(sizes), vw, vh)
                rows.append(row)
    return rows


def report_screens(rows: list[dict]) -> None:
    def cuts(vals: list[float]) -> str:
        vals = sorted(vals)
        return (f"{len(vals)}, min {vals[0]:g} " + " ".join(
            f"p{int(k * 100)} {vals[min(len(vals) - 1, int(k * len(vals)))]:g}" for k in (0.25, 0.5, 0.75))
            + f" max {vals[-1]:g}") if vals else "none"
    for kind in ("title", "result", "play"):
        some = [r for r in rows if r["kind"] == kind]
        print(f"{kind}: {len(some)} screens of {len({r['example'] for r in some})} examples; largest text, share of "
              f"the shorter side: {cuts([r['sizes'][-1] for r in some])}; one size: "
              f"{sum(len(r['sizes']) == 1 for r in some)}; largest over smallest: "
              f"{cuts([r['sizes'][-1] / r['sizes'][0] for r in some if len(r['sizes']) > 1])}")
    images = [r["image"] for r in rows if "image" in r]
    print(f"title images: {len(images)}; height of their capitals, share of the shorter side: "
          f"{cuts([i['caps'] for i in images])}; over the size of the screen's largest text: "
          f"{cuts([i['over_text'] for i in images])}; covered 5% or more by something drawn after it: "
          f"{sum(i['covered'] >= 0.05 for i in images)}")


MONO = re.compile(r"mono|courier|consol|menlo|3270|7segment", re.I)


def ground(folder: Path, layout: dict, vw: float, vh: float) -> tuple[float, float] | None:
    """(lightness, chroma) of a screen's ground, each 0 to 1, as the module's docstring defines the
    ground; None when it has none."""
    from PIL import Image
    for layer in layers_in(layout["layers"]):
        if not layer.get("isInitiallyVisible", True):
            continue
        if not layer.get("isTransparent", True):
            rgb = layer["backgroundColor"][:3]
            break
        backdrop = next((i for i in layer["instances"] if i.get("world")
                         and abs(i["world"]["width"]) >= 0.8 * vw and abs(i["world"]["height"]) >= 0.8 * vh
                         and i.get("properties", {}).get("initially-visible") is not False), None)
        if backdrop is None:
            continue
        stem = backdrop["type"].lower()
        image = next((f for f in (folder / "images").glob("*.png")
                      if f.stem.lower() == stem or f.stem.lower().startswith(stem + "-") and f.stem.endswith("-000")),
                     None)
        if image is None:
            return None
        raw = Image.open(image).convert("RGBA").resize((64, 64)).tobytes()
        px = [raw[k:k + 4] for k in range(0, len(raw), 4) if raw[k + 3]]
        if not px:
            return None
        rgb = [sum(q[k] * q[3] for q in px) / sum(q[3] for q in px) / 255 for k in range(3)]
        break
    else:
        return None
    return round((max(rgb) + min(rgb)) / 2, 3), round(max(rgb) - min(rgb), 3)


def measure_frame(examples: Path, rag: Path) -> list[dict]:
    """One row per screen with a text shown on it, grouped as measure_screens() groups them: its
    kind; how many texts it shows, how many of them are centred on the vertical centre line within
    2% of the viewport's width, and how many of those with letters are set in capitals; the corners
    of a 3 x 3 grid that hold a text's centre; the faces of its texts, a Sprite Font as "sprite
    font"; and its ground."""
    rows = []
    for gid in games(rag):
        folder = examples / gid
        if not (folder / "project.c3proj").is_file():
            continue
        p = load(folder / "project.c3proj")
        vw, vh = p["viewportWidth"], p["viewportHeight"]
        for f in sorted((folder / "layouts").glob("*.json")):
            lay = json.loads(f.read_text(encoding="utf-8"))
            kind = screen_kind(lay["name"])
            if kind is None:
                continue
            one_screen = lay["width"] <= 1.05 * vw and lay["height"] <= 1.05 * vh
            screens: dict[tuple[str, str], list] = {}
            for layer in layers_in(lay["layers"]):
                own = kind if kind != "play" else screen_kind(layer["name"])
                fixed = layer.get("parallaxX", 1) == 0 and layer.get("parallaxY", 1) == 0
                if own is None or not layer.get("isInitiallyVisible", True) or not (one_screen or fixed):
                    continue
                for inst in layer["instances"]:
                    props, w = inst.get("properties", {}), inst.get("world")
                    text = str(props.get("text", "")).strip()
                    if text_px(props) is None or not text or not w or props.get("initially-visible") is False:
                        continue
                    box = world_box(w)
                    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                    if not (0 <= cx <= vw and 0 <= cy <= vh):
                        continue
                    name = lay["name"] if kind != "play" or own == "play" else f"{lay['name']}/{layer['name']}"
                    screens.setdefault((name, own), []).append((cx, cy, text, props.get("font", "sprite font")))
            if not screens:
                continue
            under = ground(folder, lay, vw, vh)
            for (name, own), texts in screens.items():
                lettered = [t for _, _, t, _ in texts if any(c.isalpha() for c in t)]
                corners = {("left" if cx < vw / 3 else "right") + ("-top" if cy < vh / 3 else "-bottom")
                           for cx, cy, _, _ in texts
                           if (cx < vw / 3 or cx > 2 * vw / 3) and (cy < vh / 3 or cy > 2 * vh / 3)}
                rows.append({"example": gid, "screen": name, "kind": own, "texts": len(texts),
                             "centred": sum(abs(cx - vw / 2) <= 0.02 * vw for cx, _, _, _ in texts),
                             "lettered": len(lettered), "caps": sum(t == t.upper() for t in lettered),
                             "corners": sorted(corners), "faces": sorted({face for *_, face in texts}),
                             "ground": under})
    return rows


def report_frame(rows: list[dict]) -> None:
    def cuts(vals: list[float]) -> str:
        vals = sorted(vals)
        return (f"{len(vals)}, min {vals[0]:g} " + " ".join(
            f"p{int(k * 100)} {vals[min(len(vals) - 1, int(k * len(vals)))]:g}" for k in (0.25, 0.5, 0.75))
            + f" max {vals[-1]:g}") if vals else "none"
    for kind in ("title", "result", "play"):
        some = [r for r in rows if r["kind"] == kind]
        several = [r for r in some if r["texts"] >= 2]
        held = [len(r["corners"]) for r in some]
        print(f"{kind}: {len(some)} screens of {len({r['example'] for r in some})} examples; texts centred: "
              f"{sum(r['centred'] for r in some)} of {sum(r['texts'] for r in some)}; of the {len(several)} screens "
              f"with two texts or more, all centred: {sum(r['centred'] == r['texts'] for r in several)}, none "
              f"centred: {sum(r['centred'] == 0 for r in several)}; corners holding a text: "
              + ", ".join(f"{k}: {held.count(k)}" for k in range(5)))
        lettered = [r for r in some if r["lettered"]]
        capped = [r for r in lettered if r["caps"] == r["lettered"]]
        print(f"  texts in capitals: {sum(r['caps'] for r in lettered)} of {sum(r['lettered'] for r in lettered)}; "
              f"screens all in capitals: {len(capped)} of {len(lettered)}, in "
              f"{len({r['example'] for r in capped})} examples")
        grounds = [r["ground"] for r in some if r["ground"]]
        print(f"  ground: {len(grounds)} measured; lightness {cuts([g[0] for g in grounds])}; chroma "
              f"{cuts([g[1] for g in grounds])}; dark (under 0.25): {sum(g[0] < 0.25 for g in grounds)}, light "
              f"(over 0.75): {sum(g[0] > 0.75 for g in grounds)}")
    faces: dict[str, set] = {}
    for r in rows:
        faces.setdefault(r["example"], set()).update(r["faces"])
    counts = [len(v) for v in faces.values()]
    print("faces in an example's screens: " + ", ".join(f"{k}: {counts.count(k)}" for k in sorted(set(counts)))
          + f"; examples with a monospaced face: {sum(any(MONO.search(f) for f in v) for v in faces.values())} "
          f"of {len(faces)}")


def share(rows: list[dict], key: str, test) -> str:
    n = sum(1 for r in rows if test(r[key]))
    return f"{n} of {len(rows)} ({100 * n / len(rows):.0f}%)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="example: python evals/measure_layout.py --examples ../Construct-Example-Projects/"
                                        "example-projects --out .local/docs/evidence/layout.json")
    ap.add_argument("--examples", type=Path, required=True, help="the example-projects folder of the clone")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--text", action="store_true", help="measure the layouts' texts, not their content")
    mode.add_argument("--screens", action="store_true", help="measure the texts and title images by kind of screen")
    mode.add_argument("--frame", action="store_true", help="measure the axis, corners, case, faces and ground by "
                                                           "kind of screen")
    ap.add_argument("--out", type=Path, help="write every measured layout here as JSON")
    ap.add_argument("--rag", type=Path, default=RAG, help="the Construct3-RAG folder, for the examples' tags")
    args = ap.parse_args()
    if not args.examples.is_dir():
        print(f"--examples {args.examples}: not a folder; pass <Construct-Example-Projects>/example-projects", file=sys.stderr)
        return 2
    if args.frame:
        try:
            import PIL  # noqa: F401
        except ImportError:
            print("--frame needs Pillow, to read a screen's ground: pip install pillow", file=sys.stderr)
            return 2
    rows = (measure_text if args.text else measure_screens if args.screens else measure_frame if args.frame
            else measure)(args.examples, args.rag)
    if not rows:
        print("no layout measured: check that --examples is the example-projects folder")
        return 0
    if args.text:
        report_text(rows)
    elif args.screens:
        report_screens(rows)
    elif args.frame:
        report_frame(rows)
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
