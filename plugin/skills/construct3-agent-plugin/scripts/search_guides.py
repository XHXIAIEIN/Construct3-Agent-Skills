"""Search the event sheet pitfalls and the official examples by words.

    python scripts/search_guides.py WORD [WORD ...] [--pitfalls N] [--examples N] [--locale en-US]
                                    [--limit CHARS] [--project FOLDER] [--rag FOLDER] [--cookbook FOLDER]

Prints the pitfall entries of `Construct3-Cookbook/guides/` that hold the
words, each in full with its file and line, and those of the user's own
folder laid out the same way, which come first among entries that hold as
many of the words (`--cookbook-extra`). Then it prints the official
examples whose id, name, description, tags or addons hold them, each with the
command that prints its events. Entries with more of the words come first. A
word matches inside longer words too: `tap` finds "taps". The pitfalls are
English whatever the --locale.

Search before writing events for an interaction, a timing, a pick or a
movement, and when events do not behave as expected. The pitfalls record
runtime behaviour that differs from what a programmer expects. This prints
only the entries that hold the words.
"""
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path

# python -I leaves this script's folder off sys.path, and the modules beside it are imported from there
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import c3project as c3

ENTRY = re.compile(r"^- ", re.M)


def without_source(text: str) -> str:
    """The entry without the bracket of sources it ends with, "[manual: ...; runtime: ...]"; the file and line
    printed lead to them."""
    if not text.endswith("]"):
        return text
    depth = 0
    for n in range(len(text) - 1, -1, -1):
        depth += {"]": 1, "[": -1}.get(text[n], 0)
        if depth == 0:
            return text[:n].rstrip() if n and text[n - 1] == " " else text
    return text


def pitfalls(guides: Path | None) -> list[tuple[str, int, str]]:
    """Every bullet of the pitfall pages as (file, line, text), the text on one line without its source."""
    out = []
    for path in c3.pitfall_pages(guides):
        text = path.read_text(encoding="utf-8")
        starts = [m.start() for m in ENTRY.finditer(text)]
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(text)
            block = re.split(r"\n(?!  )", text[start:end].rstrip())[0]     # the bullet ends at an unindented line
            out.append((path.as_posix(), text.count("\n", 0, start) + 1,
                        without_source(" ".join(block[2:].split()))))
    return out


def examples(rag: Path, locale: str) -> list[dict]:
    """The entries of data/c3-examples/{locale}/, one per official example."""
    return [json.loads(text) for text in c3.data_texts(rag, f"data/c3-examples/{locale}", "*.json").values()]


def example_text(e: dict) -> str:
    addons = e.get("used-addons", {})
    parts = [e.get("id", ""), e.get("name", ""), e.get("description", ""), *e.get("tags", [])]
    for kind in ("plugins", "behaviors", "effects"):
        parts += addons.get(kind, [])
    return " ".join(parts)


def ranked(items: list, text_of: Callable[[object], str], words: list[str], first: int = 0) -> list:
    """The items that hold at least one word: the ones with the most of the words first, then the first
    `first` items, the user's own, then the ones that repeat the words most, so the entry about the words
    outranks one that names them in passing."""
    lowered = [w.lower() for w in words]
    scored = []     # (words held, times they occur, position, item)
    for n, item in enumerate(items):
        text = text_of(item).lower()
        held = sum(w in text for w in lowered)
        if held:
            scored.append((held, sum(text.count(w) for w in lowered), n, item))
    scored.sort(key=lambda s: (-s[0], s[2] >= first, -s[1], s[2]))
    best = scored[0][0] if scored else 0
    return [item for held, _, _, item in scored if held == best or held >= 2]


def main() -> int:
    ap = c3.argument_parser(
        "Search the event sheet pitfalls and the official example projects by words, and print the matching "
        "pitfall entries in full and the examples with the command that prints their events.",
        "examples:\n"
        "  python scripts/search_guides.py tap button stacked     which button a tap on two stacked buttons hits\n"
        "  python scripts/search_guides.py wait pick              what a Wait keeps of the event's picks\n"
        "  python scripts/search_guides.py chase enemy --examples 0\n"
        "  python scripts/search_guides.py match-3 --pitfalls 0   official examples only\n\n"
        "exit codes: 0 something matched, 1 nothing matched, or the clone was not found")
    ap.add_argument("words", nargs="+", metavar="WORD", help="English words; an entry holding more of them ranks higher")
    ap.add_argument("--pitfalls", type=int, default=5, metavar="N", help="pitfall entries to print (default: 5)")
    ap.add_argument("--examples", type=int, default=8, metavar="N", help="example projects to print (default: 8)")
    ap.add_argument("--cookbook", metavar="FOLDER",
                    help="the Construct3-Cookbook clone that holds the pitfalls (default: CONSTRUCT3_COOKBOOK, else the "
                         "'Construct3-Cookbook:' line of the project's AGENTS.md or CLAUDE.md, else a Construct3-Cookbook "
                         "folder beside the clones)")
    ap.add_argument("--cookbook-extra", metavar="FOLDER",
                    help="your own pitfall pages, laid out as the Cookbook's guides/ (default: CONSTRUCT3_COOKBOOK_EXTRA, "
                         "else the 'Construct3-Cookbook-extra:' line of the project's AGENTS.md or CLAUDE.md)")
    args = ap.parse_args()
    c3.utf8_output()
    root = c3.find_project(args.project)
    rag = c3.find_rag(root if root and (root / "project.c3proj").exists() else None, args.rag)
    c3.note_drift(rag)

    lines: list[str] = []
    guides = c3.guides_folder(rag, root, args.cookbook) if args.pitfalls else None
    own, note = c3.own_pitfalls(root, args.cookbook_extra) if args.pitfalls else (None, None)
    if note:
        print(f"note: {note}")
    if args.pitfalls and not guides:
        print(f"note: {'the Cookbook ' if own else ''}pitfalls not searched: {c3.missing_cookbook(rag)}")
    mine = pitfalls(own)
    found_pitfalls = ranked(mine + pitfalls(guides), lambda p: p[2], args.words, len(mine))[: args.pitfalls]
    if found_pitfalls:
        lines.append("pitfalls:")
        for file, line, text in found_pitfalls:
            lines += [f"{file}:{line}", f"  {text}", ""]
    found_examples = ranked(examples(rag, args.locale), example_text, args.words)[: args.examples]
    if found_examples:
        clone = c3.siblings_folder(rag) / c3.EXAMPLES_CLONE / "example-projects"
        lines.append("examples:")
        if not clone.parent.is_dir():
            lines.append(f"(no {c3.EXAMPLES_CLONE} clone at {clone.parent}; {c3.examples_clone_command(rag)} "
                         f"clones it, and each example then gets the command that reads its events)")
        for e in found_examples:
            lines.append(f"{e['id']}: {e.get('name', '')}. {e.get('description', '')}")
            # An example written in both languages is two folders, <id>-js and <id>-ts
            folders = [f for f in (clone / f"{e['id']}{end}" for end in ("", "-js", "-ts")) if f.is_dir()]
            lines += [f"  {c3.script_command(f, 'print_sheet.py')}" for f in folders] or [f"  {e.get('open', '')}"]
    if not lines:
        print(f"nothing holds {' or '.join(args.words)}; try fewer words, another English word for the same "
              f"thing, or the name of the condition or behavior (`overlapping`, `tween`, `wait`)")
        return 1
    shown = c3.fitting(lines, args.limit)
    print("\n".join(lines[:shown]).rstrip())
    if shown < len(lines):
        print(f"-- {len(lines) - shown} more lines; add a word, or pass --limit 0 for all")
    return 0


if __name__ == "__main__":
    sys.exit(main())
