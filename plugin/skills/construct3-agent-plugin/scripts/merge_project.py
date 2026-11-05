"""Finish a Git merge or cherry-pick that stopped on Construct 3 project files, field by field.

    python scripts/merge_project.py [--project FOLDER] [--dry-run]

Git merges these JSON files by line, so two branches that each add an instance, an
event or an object type stop on the same few lines. Each element of a list has an
identity here, its sid, uid or name, so the two additions are told apart: the script
merges each unmerged file under layouts/, eventSheets/, objectTypes/, families/ and
timelines/, and project.c3proj, from the three versions Git holds. An element that one
side added or removed follows that side, and order follows the side that changed it.
Where both sides added at one place, the current branch's comes first and the output
says so, because the order of events and of instances changes what the game does.

Two branches can also give the same uid to two instances, or the same imageSpriteId to
two images, which stops the editor, without any line in conflict. The script keeps the
number on what the current branch already holds and gives the other a free number, with
the references to a uid in its hierarchy.

Each file it merges or renumbers is staged. A file where both sides changed one value
stays in conflict, and the script prints each such value with both sides, for you to
resolve by hand. Other files, such as tuning data under files/, are left to you. Then
run check_project.py, and go on with git cherry-pick --continue or git commit.

Nothing is committed. --dry-run says what would be done and writes nothing.

exit codes: 0 no conflict left in the project files it merges; 1 some left, each named;
2 bad arguments, or not inside a Git repository
"""
import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# python -I leaves this script's folder off sys.path, and the modules beside it are imported from there
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import c3project as c3

FOLDERS = ("layouts", "eventSheets", "objectTypes", "families", "timelines")
ABSENT = object()
# What names an element of a list; an element with none of them is named by its whole value
IDENTITY = ("sid", "uid", "imageSpriteId", "name", "id")
SHARED_PLACES: list[str] = []   # each list where both sides added at one place, so their order is a choice


class Disagreement(Exception):
    """Both sides changed one value: its path and the two values."""

    def __init__(self, path: str, ours: Any, theirs: Any) -> None:
        super().__init__(path)
        self.path, self.ours, self.theirs = path, ours, theirs


def shown(value: Any) -> str:
    """A value as one short line."""
    text = "(removed)" if value is ABSENT else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= 80 else text[:77] + "..."


def by_element(*lists: list) -> bool:
    """Whether a list is a set of named things, not one value: the three numbers of a position or
    the points of a polygon change as a whole, and merging their elements would make a new value."""
    return any(isinstance(item, str) or (isinstance(item, dict) and any(k in item for k in IDENTITY))
               for items in lists for item in items)


def identities(items: list) -> list:
    """A name for each element of a list, the same on each side for the same element. Elements that share a
    whole value, as two equal comments do, are told apart by their place among them."""
    seen: Counter = Counter()
    names = []
    for item in items:
        key = next((item[k] for k in IDENTITY if isinstance(item, dict) and k in item), None)
        name = key if key is not None else json.dumps(item, sort_keys=True, ensure_ascii=False)
        names.append((name, seen[name]))
        seen[name] += 1
    return names


def merge_order(path: str, base: list, ours: list, theirs: list, kept: set) -> list:
    """The order of the merged list: the order of the side that changed it, with each element only the other
    side added placed after the element that comes before it on that side."""
    shared = set(base) & set(ours) & set(theirs) & kept

    def common(order: list) -> list:
        return [x for x in order if x in shared]

    if common(ours) == common(theirs) or common(theirs) == common(base):
        lead, other = ours, theirs
    elif common(ours) == common(base):
        lead, other = theirs, ours
    else:
        raise Disagreement(path + " (order)", ABSENT, ABSENT)
    result = [x for x in lead if x in kept]
    placed, others = set(result), set(other)
    last = None
    for x in other:
        if x in kept and x not in placed:
            at = result.index(last) + 1 if last in placed else 0
            while at < len(result) and result[at] not in others:     # what the leading side added here comes first
                at += 1
                SHARED_PLACES.append(path)
            result.insert(at, x)
            placed.add(x)
        last = x if x in placed else last
    return result


def merge_lists(path: str, base: list, ours: list, theirs: list) -> list:
    ids = {side: identities(items) for side, items in (("b", base), ("o", ours), ("t", theirs))}
    by_id = {side: dict(zip(ids[side], items)) for side, items in (("b", base), ("o", ours), ("t", theirs))}
    merged: dict = {}
    for x in {*ids["b"], *ids["o"], *ids["t"]}:
        value = merge_values(f"{path}[{x[0]}]", by_id["b"].get(x, ABSENT), by_id["o"].get(x, ABSENT),
                             by_id["t"].get(x, ABSENT))
        if value is not ABSENT:
            merged[x] = value
    return [merged[x] for x in merge_order(path, ids["b"], ids["o"], ids["t"], set(merged))]


def merge_values(path: str, base: Any, ours: Any, theirs: Any) -> Any:
    """The three-way merge of one value; ABSENT where the merged file has none. Raises Disagreement."""
    if ours == theirs or base == theirs:
        return ours
    if base == ours:
        return theirs
    for kind, empty in ((dict, {}), (list, [])):
        if isinstance(ours, kind) and isinstance(theirs, kind) and (base is ABSENT or isinstance(base, kind)):
            before = empty if base is ABSENT else base
            if kind is list:
                if not by_element(before, ours, theirs):
                    break
                return merge_lists(path, before, ours, theirs)
            result = {}
            for key in [*ours, *(k for k in theirs if k not in ours), *(k for k in before if k not in ours and k not in theirs)]:
                value = merge_values(f"{path}.{key}" if path else key, before.get(key, ABSENT), ours.get(key, ABSENT),
                                     theirs.get(key, ABSENT))
                if value is not ABSENT:
                    result[key] = value
            return result
    raise Disagreement(path, ours, theirs)


def git(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(project), *args], capture_output=True, encoding="utf-8", errors="replace")


def stage(project: Path, number: int, rel: str) -> str | None:
    """The file as Git holds it in a stage of the merge: 1 the base, 2 ours, 3 theirs."""
    done = git(project, "show", f":{number}:{rel}")
    return done.stdout.removeprefix("\ufeff") if done.returncode == 0 else None


def is_project_file(rel: str) -> bool:
    return rel == "project.c3proj" or (rel.endswith(".json") and rel.split("/")[0] in FOLDERS)


def written(value: Any, like: str) -> str:
    """The value as the editor writes it, with the line ends of the text it replaces."""
    text = json.dumps(value, indent="\t", ensure_ascii=False) + ("\n" if like.endswith("\n") else "")
    return text.replace("\n", "\r\n") if "\r\n" in like else text


def walk_dicts(value: Any):
    """Each dictionary inside a value."""
    if isinstance(value, dict):
        yield value
        value = list(value.values())
    if isinstance(value, list):
        for item in value:
            yield from walk_dicts(item)


def layout_instances(layout: dict) -> list[dict]:
    """The instances of a layout, those of sub-layers and the non-world ones too."""
    return [d for d in walk_dicts(layout) if "uid" in d and "type" in d]


def head_version(project: Path, rel: str) -> Any:
    """A file as the current branch's last commit holds it; None when it has no such file."""
    done = git(project, "show", f"HEAD:./{rel}")
    return json.loads(done.stdout.removeprefix("\ufeff")) if done.returncode == 0 else None


def renumber_uid(instances: list[dict], inst: dict, new: int) -> None:
    """Give an instance a new uid, with the references to it from its parent and its children."""
    old = inst["uid"]
    inst["uid"] = new
    graph = inst.get("sceneGraphData")
    if not graph:
        return
    graph["uid"] = new
    for child in graph.get("children") or []:
        for other in instances:
            if other["uid"] == child["uid"] and (other.get("sceneGraphData") or {}).get("parent-uid") == old:
                other["sceneGraphData"]["parent-uid"] = new
    for other in instances:
        for child in (other.get("sceneGraphData") or {}).get("children") or []:
            if child["uid"] == old and other["uid"] == graph.get("parent-uid"):
                child["uid"] = new


def renumber(project: Path, changed: set[str], unmerged: set[str]) -> list[str]:
    """Give a free number to each instance or image that shares its uid or imageSpriteId with another, keeping
    the number on what the last commit holds; add each file changed to `changed`. A file still unmerged holds
    conflict markers, so it is skipped. Returns what it did."""
    def read(*folders: str) -> dict[str, Any]:
        files = {path.relative_to(project).as_posix(): path for folder in folders
                 for path in sorted((project / folder).rglob("*.json"))}
        return {rel: c3.load(path) for rel, path in files.items() if rel not in unmerged}

    done = []
    layouts, objects = read("layouts"), read("objectTypes", "families")

    # Uids
    placed = [(rel, inst) for rel, layout in layouts.items() for inst in layout_instances(layout)]
    uids = Counter(inst["uid"] for _, inst in placed)
    free = max(uids, default=0) + 1
    for number in [n for n, count in uids.items() if count > 1]:
        holders = [(rel, inst) for rel, inst in placed if inst["uid"] == number]
        held = [(rel, inst) for rel, inst in holders if any(
            d["uid"] == number and d.get("sid") == inst.get("sid")
            for d in layout_instances(head_version(project, rel) or {}))]
        keep = held[0] if held else holders[0]
        for rel, inst in holders:
            if inst is not keep[1]:
                renumber_uid(layout_instances(layouts[rel]), inst, free)
                done.append(f"{rel}: {inst['type']} uid {number} -> {free}")
                changed.add(rel)
                free += 1

    # Images
    frames = [(rel, d) for rel, data in objects.items() for d in walk_dicts(data) if "imageSpriteId" in d]
    ids = Counter(d["imageSpriteId"] for _, d in frames)
    free = max(ids, default=0) + 1
    for number in [n for n, count in ids.items() if count > 1]:
        holders = [(rel, d) for rel, d in frames if d["imageSpriteId"] == number]
        held = [rel for rel, _ in holders if any(
            d.get("imageSpriteId") == number for d in walk_dicts(head_version(project, rel) or {}))]
        keep = next((h for h in holders if h[0] in held), holders[0])
        for rel, d in holders:
            if d is not keep[1]:
                d["imageSpriteId"] = free
                done.append(f"{rel}: imageSpriteId {number} -> {free}")
                changed.add(rel)
                free += 1

    for rel in changed & {*layouts, *objects}:
        path = project / rel
        like = path.read_text(encoding="utf-8")
        path.write_bytes(written({**layouts, **objects}[rel], like).encode("utf-8"))
    return done


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0], epilog=__doc__.split("\n\n", 2)[2],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", type=Path, default=Path("."), help="the project folder (default: this folder)")
    ap.add_argument("--dry-run", action="store_true", help="say what would be done, write nothing")
    args = ap.parse_args()
    project = args.project.resolve()
    listed = git(project, "ls-files", "-u", "-z")
    if listed.returncode != 0:
        print(f"{project} is not in a Git repository: {listed.stderr.strip()}", file=sys.stderr)
        return 2
    unmerged = sorted({row.split("\t", 1)[1] for row in listed.stdout.split("\0") if row})
    left, others, resolved, orders, texts = [], [], [], [], {}
    for rel in unmerged:
        if not is_project_file(rel):
            others.append(rel)
            continue
        ours, theirs, base = stage(project, 2, rel), stage(project, 3, rel), stage(project, 1, rel)
        if ours is None or theirs is None:
            left.append(f"{rel}: one side removed the file")
            continue
        SHARED_PLACES.clear()
        try:
            value = merge_values("", json.loads(base) if base is not None else ABSENT, json.loads(ours), json.loads(theirs))
        except Disagreement as d:
            left.append(f"{rel}: {d.path}: ours {shown(d.ours)}, theirs {shown(d.theirs)}")
            continue
        texts[rel] = written(value, ours)
        resolved.append(rel)
        orders += [f"order to check {rel}: {place}: both sides added here, the current branch's first"
                   for place in dict.fromkeys(SHARED_PLACES)]
    if args.dry_run:
        print("\n".join(f"would merge {rel}" for rel in resolved) or "no project file to merge")
    else:
        for rel, text in texts.items():
            (project / rel).write_bytes(text.encode("utf-8"))
        changed = set(resolved)
        for line in renumber(project, changed, {*unmerged} - changed):
            print(line)
        for rel in resolved:
            print(f"merged {rel}")
        for line in orders:
            print(line)
        if changed:
            git(project, "add", "--", *sorted(changed))
    for rel in others:
        print(f"left to you {rel}: not a project file that this script merges")
    for line in left:
        print(f"conflict {line}")
    if left:
        print(f"{len(left)} left: resolve each by hand, git add it, then run check_project.py", file=sys.stderr)
        return 1
    if others:
        print("next: resolve the files left to you and git add them, then run check_project.py")
    elif not args.dry_run:
        print("next: run check_project.py, then git cherry-pick --continue or git commit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
