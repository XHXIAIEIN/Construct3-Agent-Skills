"""The shape of the event sheet pitfalls: an index and its topic files.

The index gives every group one conclusion line per pitfall, pointing at
the topic file under prompts/pitfalls/ that holds the pitfall with its
cases and its source.
"""
import json
import re
from pathlib import Path

from tests.skill_helpers import script_module

REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "plugin"
PROMPTS = PLUGIN / "prompts"
INDEX = PROMPTS / "event-sheet-pitfalls.md"
TOPICS = PROMPTS / "pitfalls"
SCHEMAS = PLUGIN / "data" / "c3-schemas"

# The .md file a Markdown link points at, without its anchor
LINK = re.compile(r"\]\(([^)#\s]+\.md)(?:#[^)]*)?\)")
# A source is a bracketed span that is not a Markdown link's text.
SOURCE = re.compile(r"\[[^\]]+\](?!\()")


def bullets(text: str) -> list[str]:
    """Top-level list entries, each with its continuation lines."""
    entries: list[str] = []
    for line in text.splitlines():
        if line.startswith("- "):
            entries.append(line)
        elif line.startswith("#"):
            entries.append("")
        elif entries and entries[-1]:
            entries[-1] += "\n" + line
    return [entry for entry in entries if entry]


def index_groups() -> dict[str, tuple[str, int]]:
    """Each topic group of the index: its linked topic file and how many conclusion lines it has."""
    text = INDEX.read_text(encoding="utf-8")
    topics = text.split("\n## Topics\n", 1)[1].split("\n## ", 1)[0]
    groups: dict[str, tuple[str, int]] = {}
    for block in topics.split("\n### ")[1:]:
        title, body = block.split("\n", 1)
        links = [link for link in LINK.findall(body) if link.startswith("pitfalls/")]
        assert len(links) == 1, f"group {title!r} links {links}, not one topic file"
        groups[title] = (links[0], len(bullets(body)))
    return groups


def test_every_topic_file_is_linked_from_the_index_and_exists() -> None:
    linked = {path for path, _ in index_groups().values()}
    on_disk = {f"pitfalls/{path.name}" for path in TOPICS.glob("*.md")}
    assert linked - on_disk == set(), "the index links topic files that do not exist"
    assert on_disk - linked == set(), "topic files the index does not link"


def test_each_group_has_one_conclusion_line_per_topic_entry() -> None:
    for title, (path, lines) in index_groups().items():
        entries = len(bullets((PROMPTS / path).read_text(encoding="utf-8")))
        assert lines == entries, (
            f"group {title!r}: {lines} conclusion lines in the index, "
            f"{entries} entries in {path}"
        )


def test_every_entry_names_its_source() -> None:
    inline = INDEX.read_text(encoding="utf-8").split("\n## Topics\n", 1)[0]
    files = {INDEX.name: inline}
    files.update({f"pitfalls/{p.name}": p.read_text(encoding="utf-8") for p in TOPICS.glob("*.md")})
    for name, text in files.items():
        for entry in bullets(text):
            assert SOURCE.search(entry), f"{name}: no source in {entry.splitlines()[0]!r}"


def addon_ids() -> dict[str, dict]:
    index = json.loads((SCHEMAS / "en-US" / "_index.json").read_text(encoding="utf-8"))
    return {**index["plugins"], **index["behaviors"]}


def ace_ids(addon: str) -> set[str]:
    file = "plugins/_common.json" if addon == "_common" else addon_ids()[addon]["file"]
    schema = json.loads((SCHEMAS / "en-US" / file).read_text(encoding="utf-8"))
    return {it["id"] for kind in ("conditions", "actions", "expressions") for it in schema.get(kind, [])}


def test_every_topic_file_names_the_addons_whose_entries_point_at_it() -> None:
    """The `addons:` line is what lookup_ace.py reads, so a topic without one is reached from no entry,
    and an id that no schema holds never matches an entry. `none` marks a topic that holds for every sheet."""
    lookup = script_module("lookup_ace")
    addons = addon_ids()
    for path in sorted(TOPICS.glob("*.md")):
        line = lookup.front_matter(path).get("addons")
        assert line, f"{path.name}: no addons: line in its front matter"
        for key in line.split(","):
            key = key.strip()
            if key == "none":
                assert line.strip() == "none", f"{path.name}: none beside an id"
                continue
            addon, _, ace = key.partition("/")
            assert addon in addons or addon == "_common", f"{path.name}: no addon {addon!r}"
            if ace:
                assert ace in ace_ids(addon), f"{path.name}: no ACE {ace!r} of {addon}"


def test_native_first_lists_the_addons_a_row_of_the_table_replaces() -> None:
    """The list is the repository's preference, apart from the editor's deprecation list: each addon is
    one the editor still offers, and its row of the Native first table names it as the one not to use."""
    data = json.loads((PROMPTS / "native-first.json").read_text(encoding="utf-8"))
    text = (PLUGIN / data["file"]).read_text(encoding="utf-8")
    table = text.split(f"\n## {data['table']}\n", 1)[1].split("\n## ", 1)[0]
    deprecated = json.loads((SCHEMAS / "en-US" / "_deprecated.json").read_text(encoding="utf-8"))["addons"]
    for addon, row in data["addons"].items():
        name = addon_ids()[addon]["name"]
        assert addon not in deprecated["plugins"] and addon not in deprecated["behaviors"], addon
        lines = [line for line in table.splitlines() if line.startswith(f"| {row['row']} |")]
        assert len(lines) == 1, f"{addon}: no row {row['row']!r} in {data['file']}"
        assert f"{name} behavior" in lines[0].rsplit("|", 2)[-2], f"{addon}: the row's Not column does not name {name}"
        assert row["use"] and row["use"][0].islower(), (addon, "use")
