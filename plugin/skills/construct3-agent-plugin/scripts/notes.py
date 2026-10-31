"""Keep the facts a check showed about the game, each on the events it rests on, and mark those whose events changed.

    python scripts/notes.py [--add FACT | --rewrite N FACT | --confirm N ... | --remove N ...]
                            [--sheet SHEET (--function NAME | --group TITLE | --event N)]
                            [--limit CHARS] [--project FOLDER] [--rag FOLDER]

A note is one short fact that a probe or a kept plan showed in the running
game: how to reach a scene, the parameters a function takes, the trigger that
starts a flow, the first-launch tutorial to skip. It names the function,
group or event of a sheet it rests on, and the day it was verified. The notes
are in tools/notes.json, which the editor ignores, committed with the project.

Without a flag the script prints every note. A note whose function, group or
event differs from what it was when the note was verified is marked changed,
and the events that changed print under it, as print_sheet.py --since prints
them, against the last commit that holds them as verified. A note whose
function, group or event the sheet no longer has is marked gone. A mark stays
until --confirm or --rewrite stamps the note again. The comparison leaves out
the sids, which a generator run gives anew, and a group covers every event in
it. A note on an event finds it by its sid, else by its content.
"""
import argparse
import datetime
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Iterator, NamedTuple

# python -I leaves this script's folder off sys.path, and the modules beside it are imported from there
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import c3project as c3
import print_sheet as ps
from c3project import NUMBERED

NOTES = Path("tools") / "notes.json"
FACT_LENGTH = 240       # characters of one fact: a longer one is several facts or a guess explained
HISTORY = 30            # commits of a sheet's history searched for the events a changed note was verified on
DIFF_LINES = 30         # lines of a changed note's events printed under it


class Place(NamedTuple):
    """Where a note's events are in a sheet now."""
    event: dict
    number: int         # the editor's number of the function, group or event
    top: bool           # every event above it is a group, so an event without conditions runs every tick


def bare(obj: object) -> object:
    """An event with everything under it, without the sids, which a generator run gives anew."""
    if isinstance(obj, dict):
        return {k: bare(v) for k, v in obj.items() if k != "sid"}
    return [bare(v) for v in obj] if isinstance(obj, list) else obj


def stamp_of(event: dict) -> str:
    return hashlib.sha256(json.dumps(bare(event), sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


def walk(events: list, counter: list[int], top: bool = True) -> Iterator[Place]:
    """Every numbered event of a sheet with its number, each before its sub-events."""
    for ev in events:
        if ev.get("eventType") in NUMBERED:
            counter[0] += 1
            yield Place(ev, counter[0], top)
        yield from walk(ev.get("children", []), counter, top and ev.get("eventType") == "group")


def name_of(ev: dict) -> str:
    """A function or custom action block by the name a note gives it."""
    if ev.get("eventType") == "function-block":
        return str(ev.get("functionName", ""))
    return f"{ev.get('objectClass')}.{ev.get('aceName')}"


def located(sheet: dict, note: dict) -> Place | None:
    """The function, group or event a note rests on, in the sheet as it is; None when the sheet has none."""
    places = list(walk(sheet.get("events", []), [0]))
    kind, name = note["kind"], str(note.get("name", "")).lower()
    if kind == "function":
        return next((p for p in places if p.event.get("eventType") in ps.FUNCTION_BLOCKS
                     and name_of(p.event).lower() == name), None)
    if kind == "group":
        return next((p for p in places if p.event.get("eventType") == "group"
                     and str(p.event.get("title", "")).lower() == name), None)
    return (next((p for p in places if p.event.get("sid") == note.get("sid")), None)
            or next((p for p in places if stamp_of(p.event) == note["stamp"]), None))


def names(sheet: dict, kind: str) -> list[str]:
    """The functions or groups of a sheet, for a miss."""
    places = walk(sheet.get("events", []), [0])
    if kind == "function":
        return [name_of(p.event) for p in places if p.event.get("eventType") in ps.FUNCTION_BLOCKS]
    return [str(p.event.get("title", "")) for p in places if p.event.get("eventType") == "group"]


def anchor(note: dict, place: Place | None = None) -> str:
    """What a note rests on, as the print names it: an event by its number now."""
    if note["kind"] == "event":
        return f"{note['sheet']} event {place.number if place else '?'}"
    return f"{note['sheet']} {note['kind']} {note['name']}"


# --- the file ---------------------------------------------------------------------------------------------------
def read(root: Path) -> list[dict]:
    path = root / NOTES
    if not path.is_file():
        return []
    notes = c3.load(path)
    if not isinstance(notes, list) or not all(isinstance(n, dict) and {"fact", "sheet", "kind", "stamp"} <= set(n)
                                              for n in notes):
        sys.exit(f"{path}: not a list of notes, each with fact, sheet, kind and stamp; fix it by hand or move it "
                 f"aside, then add the notes again with --add")
    return notes


def write(root: Path, notes: list[dict]) -> None:
    path = root / NOTES
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(notes, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def marks(project: c3.Project, notes: list[dict]) -> list[tuple[Place | None, str]]:
    """For each note, where its events are now and its mark: '' as verified, 'changed' or 'gone'."""
    sheets = project.load_listed("eventSheets")
    out = []
    for note in notes:
        place = located(sheets[note["sheet"]], note) if note["sheet"] in sheets else None
        out.append((place, "gone" if place is None else "" if stamp_of(place.event) == note["stamp"] else "changed"))
    return out


class Standing(NamedTuple):
    line: str           # how many notes, and the marked ones by number
    marked: int


def summary(project: c3.Project) -> Standing | None:
    """The notes in one line, for verify_change.py; None without notes."""
    notes = read(project.root)
    if not notes:
        return None
    marked = [str(k) for k, (_, mark) in enumerate(marks(project, notes), 1) if mark]
    return Standing(f"notes: {len(notes)} in {NOTES.as_posix()}"
                    + (f", {', '.join(marked)} rest{'s' if len(marked) == 1 else ''} on events that changed or went "
                       f"since {'it was' if len(marked) == 1 else 'they were'} verified" if marked
                       else ", each on its events as verified")
                    + f": {c3.script_command(project.root, 'notes.py')}", len(marked))


# --- what changed under a marked note ---------------------------------------------------------------------------
def history(root: Path, rel: str) -> list[str]:
    """The commits that changed the sheet's file, newest first; none outside a git repository."""
    if not shutil.which("git") or ps.git(root, "rev-parse", "--git-dir").returncode:
        return []
    return ps.git(root, "log", f"-n{HISTORY}", "--format=%H", "--", rel).stdout.split()


def changed_lines(project: c3.Project, note: dict, place: Place) -> list[str]:
    """The events of a changed note, as print_sheet.py --since prints them against the last commit that holds
    them as verified; as they are now when no commit does."""
    new = list(ps.sheet_rows(project, [place.event], [place.number - 1], (), place.top))
    path = project.listed_files("eventSheets")[note["sheet"]]
    rel = path.relative_to(project.root).as_posix()
    for commit in history(project.root, rel):
        shown = ps.git(project.root, "show", f"{commit}:./{rel}")
        try:
            then = located(json.loads(shown.stdout), note) if not shown.returncode else None
        except ValueError:      # the commit holds a sheet that is not valid JSON
            then = None
        if then is None or stamp_of(then.event) != note["stamp"]:
            continue
        short = ps.git(project.root, "rev-parse", "--short", commit).stdout.strip()
        with tempfile.TemporaryDirectory(prefix="notes-since-") as tmp:
            worded = ps.project_at(project, commit, Path(tmp)) or project
            old = list(ps.sheet_rows(worded, [then.event], [then.number - 1], (), then.top))
            chunks, _ = ps.changes(old, new, short)
        lines = [line for _, chunk in chunks for line in chunk]
        last = place.number + ps.numbered_below(place.event.get("children", []))
        more = (f"... {len(lines) - DIFF_LINES} more lines: "
                + c3.script_command(project.root, "print_sheet.py",
                                    f" {c3.quoted(note['sheet'])} --since {short} --events {place.number}-{last}"))
        return ([f"since {short}, the last commit that holds them as verified:"]
                + lines[:DIFF_LINES] + ([more] if len(lines) > DIFF_LINES else []))
    lines = [line for row in new for line in (*row.head, *row.body)]
    return (["no commit holds them as verified; as they are now:"] + lines[:DIFF_LINES]
            + ([f"... {len(lines) - DIFF_LINES} more lines"] if len(lines) > DIFF_LINES else []))


def print_notes(project: c3.Project, limit: int) -> int:
    notes = read(project.root)
    if not notes:
        print(f"no notes yet in {NOTES.as_posix()}. Once a probe or a kept plan has shown a fact a later check "
              f"needs, add it on the events it rests on: "
              + c3.script_command(project.root, "notes.py", ' --add "FACT" --sheet SHEET --function NAME'))
        return 0
    marked = marks(project, notes)
    head = (f"notes: {len(notes)} in {NOTES.as_posix()}; changed: the events a note rests on differ from what they "
            f"were when it was verified; gone: the sheet no longer has them")
    blocks = []
    for k, (note, (place, mark)) in enumerate(zip(notes, marked), 1):
        line = f"{k}. {anchor(note, place)}, verified {note.get('verified', '?')}" + (f" [{mark}]" if mark else "")
        first = [] if place is None or note["kind"] != "event" else \
            [f"   {ps.compared(next(ps.sheet_rows(project, [place.event], [place.number - 1], (), place.top)))[0].strip()}"]
        under = [f"   {line}" for line in changed_lines(project, note, place)] if mark == "changed" else []
        blocks.append([f"{line}: {note['fact']}", *first, *under])
    numbers = [str(k) for k, (_, mark) in enumerate(marked, 1) if mark]
    end = ("next: check each marked note in the game, with a probe or a kept plan; if it holds, "
           + c3.script_command(project.root, "notes.py", f" --confirm {' '.join(numbers)}")
           + '; if not, --rewrite N "FACT" with what holds now, or --remove N' if numbers else
           "ok: every note rests on events as they were when it was verified")
    print(head)
    used = len(head) + len(end) + 200
    for k, block in enumerate(blocks):
        size = ps.printed_length(block)
        if limit and used + size > limit and k:
            print(f"... notes {k + 1}-{len(blocks)} did not fit: "
                  + c3.script_command(project.root, "notes.py", " --limit 0"))
            break
        print("\n".join(block))
        used += size
    print(end)
    return 0


# --- the changes ------------------------------------------------------------------------------------------------
def anchored(project: c3.Project, args: argparse.Namespace) -> tuple[dict, Place]:
    """The anchor of --sheet and --function, --group or --event, as a note keeps it, and where it is."""
    sheets = project.load_listed("eventSheets")
    if args.sheet not in sheets:
        sys.exit(f"no event sheet named {args.sheet!r}{c3.closest(args.sheet, sheets)}; sheets: {', '.join(sheets)}")
    sheet = sheets[args.sheet]
    if args.event is not None:
        place = next((p for p in walk(sheet.get("events", []), [0]) if p.number == args.event), None)
        if place is None:
            sys.exit(f"sheet {args.sheet} has no event {args.event}; "
                     + c3.script_command(project.root, "print_sheet.py", f" {c3.quoted(args.sheet)}")
                     + " prints its numbers")
        return {"sheet": args.sheet, "kind": "event", "sid": place.event.get("sid")}, place
    kind, name = ("function", args.function) if args.function is not None else ("group", args.group)
    note = {"sheet": args.sheet, "kind": kind, "name": name}
    place = located(sheet, {**note, "stamp": ""})
    if place is None:
        known = names(sheet, kind)
        sys.exit(f"sheet {args.sheet} has no {kind} {name!r}{c3.closest(name, known)}"
                 + (f"; its {kind}s: {', '.join(known)}" if known else f"; it has no {kind}"))
    if kind == "function":
        note["name"] = name_of(place.event)
    else:
        note["name"] = str(place.event.get("title", name))
    return note, place


def fact_of(text: str) -> str:
    fact = " ".join(text.split())
    if not fact:
        sys.exit("a note needs its fact: what a probe or a kept plan showed, in a sentence")
    if len(fact) > FACT_LENGTH:
        sys.exit(f"a note is one short fact, at most {FACT_LENGTH} characters, and this one has {len(fact)}; "
                 f"split it into notes, each on the events it rests on")
    return fact


def picked(notes: list[dict], numbers: list[int]) -> list[int]:
    """The indexes of the notes numbered as the print numbers them."""
    wrong = [n for n in numbers if not 1 <= n <= len(notes)]
    if wrong:
        sys.exit(f"no note {', '.join(map(str, wrong))}: "
                 + (f"the notes are 1 to {len(notes)}" if notes else f"{NOTES.as_posix()} holds no note")
                 + "; print them with notes.py")
    return sorted({n - 1 for n in numbers})


def stamped(note: dict, place: Place) -> dict:
    """The note, stamped with its events as they are now and today's date."""
    note = {**note, "stamp": stamp_of(place.event), "verified": datetime.date.today().isoformat()}
    if note["kind"] == "event":
        note["sid"] = place.event.get("sid")
    return note


def change(project: c3.Project, args: argparse.Namespace) -> int:
    root = project.root
    notes = read(root)
    if args.add is not None or args.rewrite is not None:
        number, text = (None, args.add) if args.add is not None else (int(args.rewrite[0]), args.rewrite[1])
        fact = fact_of(text)
        if args.sheet is not None:
            base, place = anchored(project, args)
        else:
            k = picked(notes, [number])[0]
            base = {key: notes[k][key] for key in ("sheet", "kind", "name", "sid") if key in notes[k]}
            place = marks(project, [notes[k]])[0][0]
            if place is None:
                sys.exit(f"note {number} rests on {anchor(notes[k])}, which the sheet no longer has; give what it "
                         f"rests on now with --sheet and --function, --group or --event")
        note = stamped({"fact": fact, **base}, place)
        if number is None:
            notes.append(note)
            number = len(notes)
        else:
            notes[number - 1] = note
        write(root, notes)
        print(f"{'added' if args.add is not None else 'rewrote'} note {number} on {anchor(note, place)}: {fact}")
        return 0
    if args.confirm:
        indexes = picked(notes, args.confirm)
        found = marks(project, [notes[k] for k in indexes])
        gone = [str(k + 1) for k, (place, _) in zip(indexes, found) if place is None]
        if gone:
            sys.exit(f"note {', '.join(gone)} rests on events the sheet no longer has: "
                     f"--rewrite N \"FACT\" with --sheet and --function, --group or --event, or --remove N")
        for k, (place, _) in zip(indexes, found):
            notes[k] = stamped(notes[k], place)
        write(root, notes)
        print(f"confirmed note {', '.join(str(k + 1) for k in indexes)} on the events as they are now")
        return 0
    indexes = picked(notes, args.remove)
    write(root, [note for k, note in enumerate(notes) if k not in indexes])
    print(f"removed note {', '.join(str(k + 1) for k in indexes)}; the notes after "
          f"{'it' if len(indexes) == 1 else 'them'} moved up")
    return 0


def main() -> int:
    ap = c3.argument_parser(
        "Print the facts earlier checks verified about this game, each on the function, group or event it rests "
        "on, with the ones whose events changed since marked; or add, rewrite, confirm or remove one.",
        "examples:\n"
        "  python scripts/notes.py\n"
        '  python scripts/notes.py --add "createBase(col, row, kind, level) makes a piece; all four are needed"'
        " --sheet Game --function createBase\n"
        '  python scripts/notes.py --add "the tutorial ends when tutorialStep reaches 5" --sheet Game --group Tutorial\n'
        '  python scripts/notes.py --add "the idle hint timer starts on the first touch" --sheet Game --event 12\n'
        "  python scripts/notes.py --confirm 2 4        still true on the changed events: stamp them again\n"
        '  python scripts/notes.py --rewrite 2 "FACT"   what holds now, on the same events\n'
        "  python scripts/notes.py --remove 3\n\n"
        "exit codes: 0 printed or written; 1 no such note, sheet, function, group or event, a fact that is empty or\n"
        "too long, or a project or clone not found")
    what = ap.add_mutually_exclusive_group()
    what.add_argument("--add", metavar="FACT", help="add a note: one fact a probe or a kept plan showed")
    what.add_argument("--rewrite", nargs=2, metavar=("N", "FACT"),
                      help="replace note N with what holds now; with --sheet, on other events")
    what.add_argument("--confirm", nargs="+", type=int, metavar="N",
                      help="the notes still hold on their changed events: stamp them again")
    what.add_argument("--remove", nargs="+", type=int, metavar="N", help="remove notes")
    ap.add_argument("--sheet", metavar="SHEET", help="the event sheet the note rests on")
    on = ap.add_mutually_exclusive_group()
    on.add_argument("--function", metavar="NAME", help="the function or custom action (Object.Action) it rests on")
    on.add_argument("--group", metavar="TITLE", help="the group it rests on, with every event in it")
    on.add_argument("--event", type=int, metavar="N", help="the event it rests on, by the number print_sheet.py prints")
    args = ap.parse_args()
    has_anchor = args.function is not None or args.group is not None or args.event is not None
    if (args.sheet is not None or has_anchor) and args.add is None and args.rewrite is None:
        ap.error("--sheet with --function, --group or --event names what --add or --rewrite rests on")
    if (args.sheet is None) == has_anchor and (args.sheet is not None or has_anchor):
        ap.error("--sheet goes with one of --function, --group or --event")
    if args.add is not None and args.sheet is None:
        ap.error("--add needs what the fact rests on: --sheet SHEET with --function NAME, --group TITLE or --event N")
    if args.rewrite is not None and not args.rewrite[0].isdigit():
        ap.error(f"--rewrite takes the note's number, then the fact; got {args.rewrite[0]!r}")
    c3.utf8_output()
    findings = c3.Findings()
    c3.stop_with_a_sentence("notes.py", findings)
    project = c3.Project.open(args, findings)
    if args.add is None and args.rewrite is None and not args.confirm and not args.remove:
        return print_notes(project, args.limit)
    return change(project, args)


if __name__ == "__main__":
    sys.exit(main())
