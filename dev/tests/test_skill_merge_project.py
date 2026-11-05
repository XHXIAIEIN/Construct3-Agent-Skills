"""merge_project.py: a Git merge or cherry-pick that stopped on project files, finished field by field."""
import copy
import json
import subprocess
from pathlib import Path

import pytest

from tests.skill_helpers import INSTALLED, NEEDS_GIT, SKILL, edit, git, run, script_module, tool

pytestmark = NEEDS_GIT
LAYOUT = "layouts/Game.json"


def merge(root: Path, *args: str) -> tuple[int, str]:
    return run(root, f"{INSTALLED}/scripts/merge_project.py", *args)


def unmerged(root: Path) -> str:
    return subprocess.run(["git", "ls-files", "-u"], cwd=root, capture_output=True, text=True, check=True).stdout


def add_instance(root: Path, uid: int, sid: int, **fields) -> None:
    """A copy of the layout's first instance at the end of its layer."""
    def change(layout):
        layer = next(layer for layer in layout["layers"] if layer["instances"])
        inst = copy.deepcopy(layer["instances"][0])
        inst.pop("sceneGraphData", None)
        layer["instances"].append({**inst, "uid": uid, "sid": sid, **fields})
    edit(root, LAYOUT, change)


def instance(root: Path, sid: int) -> dict:
    layout = json.loads((root / LAYOUT).read_text(encoding="utf-8"))
    return next(inst for layer in layout["layers"] for inst in layer["instances"] if inst["sid"] == sid)


@pytest.fixture
def repo(project) -> Path:
    """The project in a repository with a branch `side`, both at one commit."""
    git(project, "init", "-b", "main")
    git(project, "add", "-A")
    git(project, "commit", "-m", "base")
    git(project, "branch", "side")
    return project


def stop_on(repo: Path, ours, theirs) -> None:
    """Make the change `theirs` on the branch side and `ours` on main, then cherry-pick the first, which stops."""
    for branch, change in (("side", theirs), ("main", ours)):
        git(repo, "switch", branch)
        change(repo)
        git(repo, "add", "-A")
        git(repo, "commit", "-m", branch)
    git(repo, "cherry-pick", "side", check=False)
    assert unmerged(repo)


def test_two_additions_at_one_place_are_both_kept_and_the_file_is_staged(repo):
    """Git stops on the last lines of the layer, where each branch added an instance. The current branch's
    comes first, and a line says that the order was a choice, because order is Z order and event order."""
    stop_on(repo, lambda root: add_instance(root, 900001, 800000000000001),
            lambda root: add_instance(root, 900002, 800000000000002))
    code, out = merge(repo)
    assert code == 0 and f"merged {LAYOUT}" in out, out
    assert not unmerged(repo)
    assert instance(repo, 800000000000001)["uid"] == 900001 and instance(repo, 800000000000002)["uid"] == 900002
    layout = json.loads((repo / LAYOUT).read_text(encoding="utf-8"))
    sids = [inst["sid"] for layer in layout["layers"] for inst in layer["instances"]]
    assert sids.index(800000000000001) < sids.index(800000000000002)
    assert f"order to check {LAYOUT}: layers[" in out, out
    code, out = tool(repo, "check_project")
    assert code == 0, out


def test_changes_to_different_fields_of_one_instance_are_both_kept(repo):
    def move(field, value):
        def change(root):
            def on(layout):
                next(layer for layer in layout["layers"] if layer["instances"])["instances"][0]["world"][field] = value
            edit(root, LAYOUT, on)
        return change
    stop_on(repo, move("x", 11), move("y", 22))
    code, out = merge(repo)
    assert code == 0, out
    layout = json.loads((repo / LAYOUT).read_text(encoding="utf-8"))
    world = next(layer for layer in layout["layers"] if layer["instances"])["instances"][0]["world"]
    assert (world["x"], world["y"]) == (11, 22)


def test_one_value_changed_on_both_sides_stays_in_conflict_and_names_both(repo):
    """The file keeps Git's markers, so that it cannot pass for merged, and the other file is still merged."""
    def rename(value):
        def change(root):
            edit(root, "project.c3proj", lambda data: data.update(name=value))
            add_instance(root, 900000 + len(value), 800000000000000 + len(value))
        return change
    stop_on(repo, rename("ours"), rename("theirs!"))
    code, out = merge(repo)
    assert code == 1, out
    assert 'conflict project.c3proj: name: ours "ours", theirs "theirs!"' in out, out
    assert f"merged {LAYOUT}" in out, out
    assert "project.c3proj" in unmerged(repo) and LAYOUT not in unmerged(repo)
    assert "<<<<<<<" in (repo / "project.c3proj").read_text(encoding="utf-8")


def test_a_value_removed_on_one_side_and_changed_on_the_other_stays_in_conflict():
    mp = script_module("merge_project")
    with pytest.raises(mp.Disagreement) as caught:
        mp.merge_values("", {"a": 1}, {}, {"a": 2})
    assert caught.value.path == "a" and mp.shown(caught.value.ours) == "(removed)"


def test_a_value_only_one_side_added_is_kept():
    mp = script_module("merge_project")
    assert mp.merge_values("", {}, {}, {"a": 1}) == {"a": 1}
    assert mp.merge_values("", [{"sid": 1}], [{"sid": 1}], [{"sid": 1}, {"sid": 2}]) == [{"sid": 1}, {"sid": 2}]


def test_a_list_of_numbers_is_one_value():
    """Merging the elements of a position would make a place neither side chose."""
    mp = script_module("merge_project")
    assert mp.merge_values("", {"p": [0, 0]}, {"p": [1, 0]}, {"p": [0, 0]}) == {"p": [1, 0]}
    with pytest.raises(mp.Disagreement):
        mp.merge_values("", {"p": [0, 0]}, {"p": [1, 0]}, {"p": [0, 2]})


def test_elements_are_matched_by_name_whatever_their_place():
    mp = script_module("merge_project")
    base = {"items": [{"sid": 1, "v": 0}, {"sid": 2, "v": 0}]}
    ours = {"items": [{"sid": 2, "v": 0}, {"sid": 1, "v": 5}]}      # moved one and changed the other
    theirs = {"items": [{"sid": 1, "v": 0}, {"sid": 2, "v": 7}, {"sid": 3, "v": 0}]}
    assert mp.merge_values("", base, ours, theirs) == {
        "items": [{"sid": 2, "v": 7}, {"sid": 3, "v": 0}, {"sid": 1, "v": 5}]}


def test_folder_items_named_by_their_text_merge():
    mp = script_module("merge_project")
    assert mp.merge_values("", {"items": ["a"]}, {"items": ["a", "b"]}, {"items": ["c", "a"]}) == {"items": ["c", "a", "b"]}


def test_a_list_moved_on_both_sides_stays_in_conflict():
    mp = script_module("merge_project")
    one, two, three = {"sid": 1}, {"sid": 2}, {"sid": 3}
    with pytest.raises(mp.Disagreement) as caught:
        mp.merge_values("", [one, two, three], [two, one, three], [one, three, two])
    assert "(order)" in caught.value.path


def test_a_uid_both_branches_gave_stays_on_the_current_branchs_instance(repo):
    """Nothing conflicts on that field, since the instances differ, and the editor stops on the two uids.
    Children keep their parent through the new number."""
    def theirs(root):
        add_instance(root, 900001, 800000000000002, sceneGraphData={"parent-uid": None, "uid": 900001, "flags": 0,
                                                                     "children": [{"uid": 900003, "flags": 0}]})
        add_instance(root, 900003, 800000000000003, sceneGraphData={"parent-uid": 900001, "uid": 900003, "flags": 0})
    stop_on(repo, lambda root: add_instance(root, 900001, 800000000000001), theirs)
    code, out = merge(repo)
    assert code == 0, out
    new = instance(repo, 800000000000002)
    assert instance(repo, 800000000000001)["uid"] == 900001 and new["uid"] != 900001
    assert new["sceneGraphData"]["uid"] == new["uid"]
    assert instance(repo, 800000000000003)["sceneGraphData"]["parent-uid"] == new["uid"]
    assert f"uid 900001 -> {new['uid']}" in out, out
    code, out = tool(repo, "check_project")
    assert code == 0, out


def test_an_image_number_two_objects_share_gets_a_free_one(repo):
    """Two objects in two files share no line, so Git merges them, and the editor refuses the project."""
    mp = script_module("merge_project")
    first, second = [p for p in sorted((repo / "objectTypes").rglob("*.json"))
                     if "imageSpriteId" in p.read_text(encoding="utf-8")][:2]
    held = next(d for d in mp.walk_dicts(json.loads(first.read_text(encoding="utf-8"))) if "imageSpriteId" in d)["imageSpriteId"]

    def share(data):
        next(d for d in mp.walk_dicts(data) if "imageSpriteId" in d)["imageSpriteId"] = held
    edit(repo, second.relative_to(repo).as_posix(), share)
    code, out = merge(repo)
    assert code == 0 and f"imageSpriteId {held} -> " in out, out
    code, out = tool(repo, "check_project")
    assert code == 0, out


def test_dry_run_writes_nothing(repo):
    stop_on(repo, lambda root: add_instance(root, 900001, 800000000000001),
            lambda root: add_instance(root, 900002, 800000000000002))
    before = (repo / LAYOUT).read_bytes()
    code, out = merge(repo, "--dry-run")
    assert code == 0 and f"would merge {LAYOUT}" in out, out
    assert (repo / LAYOUT).read_bytes() == before and LAYOUT in unmerged(repo)


def test_a_file_it_does_not_merge_is_named_and_left_as_git_left_it(repo):
    def note(text):
        def change(root):
            (root / "files").mkdir(exist_ok=True)
            (root / "files" / "data.json").write_text(text, encoding="utf-8")
        return change
    stop_on(repo, note('{"a": 1}'), note('{"a": 2}'))
    code, out = merge(repo)
    assert code == 0 and "left to you files/data.json" in out, out
    assert "files/data.json" in unmerged(repo)
    assert "next: resolve the files left to you" in out, out


def test_a_folder_outside_a_repository_stops(tmp_path):
    code, out = run(tmp_path, SKILL / "scripts" / "merge_project.py")
    assert code == 2 and "not in a Git repository" in out, out


def test_a_sheet_keeps_its_line_ends_and_its_end_of_file():
    mp = script_module("merge_project")
    assert mp.written({"a": 1}, '{\r\n}\r\n') == '{\r\n\t"a": 1\r\n}\r\n'
    assert mp.written({"a": 1}, '{\n}') == '{\n\t"a": 1\n}'
