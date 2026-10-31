"""notes.py: the facts a check showed about a game, each on the function, group or event it rests on, marked when
those events change, until a later session confirms or rewrites the note."""
import json
import re
import sys
from pathlib import Path

from tests.skill_helpers import PLUGIN, SHEET, SKILL, edit, events, game_rows, git, tool

sys.path.insert(0, str(SKILL / "scripts"))
import verify_change  # noqa: E402

NOTES = "tools/notes.json"


def committed(root: Path) -> None:
    """The project's files in a commit of a repository of its own, as a game project keeps them."""
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "notes")


def noted(project: Path) -> None:
    """Three notes: on a function, named in another case; on a group; on an event, by its number."""
    for args in (("--add", "AddScore(points) adds points to score and shows it", "--sheet", "Game",
                  "--function", "addscore"),
                 ("--add", "the keys dim on the first touch and stay dim after a restart", "--sheet", "Game",
                  "--group", "Hints"),
                 ("--add", "the first touch anywhere starts the hint", "--sheet", "Game", "--event", "13")):
        code, out = tool(project, "notes", *args)
        assert code == 0, out


def renumbered(sheet: dict) -> None:
    """Every sid given anew, as a generator run gives them."""
    fresh = iter(range(10 ** 14, 10 ** 15, 7919))

    def walk(node):
        if isinstance(node, dict):
            node.update({"sid": next(fresh)} if "sid" in node else {})
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(sheet)


def test_no_notes_says_when_to_add_one(project):
    code, out = tool(project, "notes")
    assert code == 0 and out.startswith("no notes yet in tools/notes.json") and "--add" in out, out
    assert not (project / NOTES).exists()


def test_a_note_names_its_events_and_stays_unmarked_while_they_hold(project):
    noted(project)
    kept = json.loads((project / NOTES).read_text(encoding="utf-8"))
    assert [(n["kind"], n.get("name")) for n in kept] == [("function", "AddScore"), ("group", "Hints"), ("event", None)]
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", n["verified"]) for n in kept), kept
    code, out = tool(project, "notes")
    lines = out.splitlines()
    assert code == 0 and re.fullmatch(r"1\. Game function AddScore, verified [\d-]+: AddScore\(points\) adds .*", lines[1]), out
    assert lines[3].startswith("3. Game event 13, verified ") and lines[4] == "   Touch: On any touch start", out
    assert lines[-1] == "ok: every note rests on events as they were when it was verified", out

    # A generator run gives every sid anew: the same content is the same events
    edit(project, SHEET, renumbered)
    code, out = tool(project, "notes")
    assert out.splitlines()[-1].startswith("ok: "), out


def test_a_changed_note_shows_what_changed_until_it_is_confirmed(project):
    noted(project)
    committed(project)
    edit(project, SHEET, lambda sheet: events(sheet)["add_score"]["actions"][1]["parameters"].update(
        text='"Score: " & score'))
    code, out = tool(project, "notes")
    lines = out.splitlines()
    assert code == 0 and lines[1].startswith("1. Game function AddScore, verified ") and " [changed]: " in lines[1], out
    assert re.fullmatch(r"   since \w+, the last commit that holds them as verified:", lines[2]), out
    assert "   -         -> ScoreText: Set text to score" in lines, out
    assert '   +         -> ScoreText: Set text to "Score: " & score' in lines, out
    assert "[changed]" not in out.split("2. ")[1], out
    assert lines[-1].startswith("next: check each marked note in the game") and " --confirm 1;" in lines[-1], out

    # The mark stays run after run, and verify_change.py names it once the checker passes
    code, out = tool(project, "verify_change", "--upto", "checked")
    assert "notes: 3 in tools/notes.json, 1 rests on events that changed or went since it was verified: " in out, out
    code, out = tool(project, "notes", "--confirm", "1")
    assert code == 0 and out.strip() == "confirmed note 1 on the events as they are now", out
    code, out = tool(project, "notes")
    assert out.splitlines()[-1].startswith("ok: "), out
    code, out = tool(project, "verify_change", "--upto", "checked")
    assert "notes:" not in out, out


def test_a_note_without_a_commit_prints_its_events_as_they_are(project):
    noted(project)
    edit(project, SHEET, lambda sheet: next(e for e in game_rows(sheet) if e.get("title") == "Hints")["children"].pop())
    code, out = tool(project, "notes")
    lines = out.splitlines()
    at = next(k for k, line in enumerate(lines) if line.startswith("2. Game group Hints"))
    assert " [changed]: " in lines[at] and lines[at + 1] == "   no commit holds them as verified; as they are now:", out
    assert lines[at + 2] == "     11 group Hints", out


def test_a_rewritten_note_is_stamped_again_and_a_gone_one_cannot_be_confirmed(project):
    noted(project)
    edit(project, SHEET, lambda sheet: game_rows(sheet).remove(events(sheet)["restart"]))
    edit(project, SHEET, lambda sheet: game_rows(sheet).remove(
        next(e for e in game_rows(sheet) if e.get("functionName") == "AddScore")))
    code, out = tool(project, "notes")
    assert "1. Game function AddScore, verified " in out and " [gone]: " in out, out
    # The event note's number follows its event, which moved up with the three events above it gone
    assert re.search(r"^3\. Game event (\d+),", out, re.M).group(1) == "10", out
    code, out = tool(project, "notes", "--confirm", "1")
    assert code == 1 and "note 1 rests on events the sheet no longer has" in out, out
    code, out = tool(project, "notes", "--rewrite", "1", "Coin.Collect scores the coin", "--sheet", "Game",
                     "--function", "Coin.Collect")
    assert code == 0 and out.strip() == "rewrote note 1 on Game function Coin.Collect: Coin.Collect scores the coin", out
    code, out = tool(project, "notes", "--remove", "2")
    assert code == 0, out
    kept = json.loads((project / NOTES).read_text(encoding="utf-8"))
    assert [n["fact"] for n in kept] == ["Coin.Collect scores the coin", "the first touch anywhere starts the hint"]


def test_a_miss_names_what_comes_near(project):
    for args, said in ((("--add", "x", "--sheet", "Gmae", "--group", "Hints"), "no event sheet named 'Gmae'; closest: Game"),
                       (("--add", "x", "--sheet", "Game", "--function", "AddScor"),
                        "sheet Game has no function 'AddScor'; closest: AddScore"),
                       (("--add", "x", "--sheet", "Game", "--event", "99"), "sheet Game has no event 99"),
                       (("--add", "x " * 200, "--sheet", "Game", "--event", "1"), "a note is one short fact"),
                       (("--confirm", "4"), "no note 4: tools/notes.json holds no note")):
        code, out = tool(project, "notes", *args)
        assert code == 1 and said in out, (args, out)
    code, out = tool(project, "notes", "--add", "x")
    assert code == 2 and "--add needs what the fact rests on" in out, out
    code, out = tool(project, "notes", "--confirm", "1", "--sheet", "Game", "--group", "Hints")
    assert code == 2 and "names what --add or --rewrite rests on" in out, out


def test_a_note_changes_none_of_the_files_the_checks_ran_on(project):
    before = verify_change.files_digest(project)
    noted(project)
    assert verify_change.files_digest(project) == before
