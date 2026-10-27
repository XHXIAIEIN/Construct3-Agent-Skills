"""Static checks for a Construct 3 folder project, run without the editor.

    python scripts/check_project.py [--project FOLDER] [--rag FOLDER] [--locale en-US]

Reads project.c3proj and every object type, family, layout and event sheet it
lists, and checks them against the schemas in Construct3-RAG and against the
rules the editor applies when it opens or previews a project. What is
checked, and where each rule comes from: references/checker-rules.md.

Picking, timing and the meaning of an expression run in the preview:
open_in_editor.py --preview and preview_project.py.

Findings in event sheets are placed as `sheet Game event 15 action 2`, the
number the editor prints in the margin; print_sheet.py prints that numbering.
Under --limit the findings that fit are printed and the rest counted; the
last line, `ok:` or the number of problems, always prints.

Each run keeps its findings in .tmp/check-project.json, with a digest of the
files it checked and the number of problems, so that the next run counts the
changes to each finding: a change to the event, layer or file that a finding
names, after which the finding is still there. After two changes, the last
line starts with `stop:`. The agent does not change that place a third time,
and the finding goes to the user. A run with nothing changed counts no change
and says so. pack_project.py packs a folder project only when the record holds
the digest of the files now and 0 problems. --review keeps no record.

Exit 0: no errors; warnings do not fail the run. Exit 1: findings, or the
project or the clone was not found. Exit 2: the run stopped, because a
project file lacks a key the editor always writes or because the script
failed; its line says which.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

# python -I leaves this script's folder off sys.path, and the modules beside it are imported from there
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import c3project as c3
import pack_project as pp
from c3project import RECORD, project_digest, script_command
from checker_common import (
    GENERAL_TYPES, CAP, PLACES, EVENT_PLACE, QUOTED, JSON_TYPES, STYLE_RUN, STYLE_TREE, STYLE_LADDER,
)
from checker_events import EventChecks
from checker_expressions import ExpressionChecks
from checker_files import FileChecks
from checker_sheets import SheetChecks


class Checker(FileChecks, ExpressionChecks, EventChecks, SheetChecks):
    """The checks in the order check() calls them, each from the checker_*.py
    part of its kind. A later one reads what an earlier one collected: the
    layers and template instances of the layouts, the functions and groups of
    every sheet."""

    def __init__(self, p: c3.Project, limit: int = 0, sheets: dict[str, dict] | None = None,
                 style: bool = False, review: bool = False, record: bool = False) -> None:
        self.p = p
        self.review = review  # someone else's project: no omitted parameters, no next steps
        self.record = record  # keep the findings in .tmp/ and stop the fix loop at CAP
        self.limit = limit
        self.unsaved = sheets or {}  # edit_sheet.py checks a sheet before it writes it
        self.style = style  # the warnings of check_style, off unless asked
        self.ran: dict[int, list] = {}  # id of an event's actions -> those not disabled (running)
        self.off = False  # inside a disabled event or group, or in a disabled condition or action: it never runs
        self.err, self.warn = p.err, p.warn
        self.layouts: dict[str, dict] = {}
        self.global_layers: set[str] | None = None  # layer names some layout marks global
        self.sheets: dict[str, dict] = {}
        self.layers: set[str] = set()
        self.templates: set[str] = set()  # types with an instance in some layout
        self.world_types: set[str] = set()  # types with an instance on a layer: they have X, Width, Angle ...
        self.uids: list[int] = []
        self.sids: list[int] = []  # sids of events, variables, object types, instances, files
        self.ace_sids: list[int] = []  # sids of condition and action entries
        self.class_sids: dict[int, list[str]] = {}  # sid -> the object types and families that have it
        self.group_titles: set[str] = set()
        self.functions: dict[str, int] = {}  # name -> parameter count
        self.returns: dict[str, str] = {}  # lowercase name -> functionReturnType
        self.custom_actions: dict[tuple[str, str], int] = {}  # (owner, name) -> parameter count
        self.pending_calls: list[tuple] = []
        self.created: set[str] = set()
        self._eases: set[str] = set()
        self.deprecated_uses: dict[str, list[str]] = {}  # warning -> where each use is
        self.global_ids: set[int] = set()  # the top-level variables of every sheet
        self.variable_names: set[str] = set()  # every variable and parameter name, as written
        self.load_order: dict[int, int] = {}  # id of a local or parameter -> its place in the sheets' order
        self.declared: dict[int, tuple[str, str, str]] = {}  # id -> (where, what a finding calls it, its scope)
        self.renamed: set[int] = set()  # ids of the locals and parameters the editor renames
        self.callables: dict[tuple[str, str], tuple[str, str]] = {}  # (owner or "", lower name) -> (name, where)
        self.numbers_on_disk = True  # whether the sheet being walked is the file, whose numbers a plan can name
        self.signalled: set[str] | None = set()  # literal tags a Signal raises; None once one is not literal
        self.awaited: list[tuple[str, str, str]] = []  # (tag, ACE id, where) of each Wait for signal and On signal
        self.layer_effects: dict[str, set[str]] = {}  # layer name -> its effects' names, in any layout
        self.glyph_white: dict[str, bool] = {}  # Sprite Font type -> its image draws every glyph white
        self.layout_effects: set[str] = set()  # the effects of every layout
        # Sprite Font type -> the characters its instances draw, whether any has BBCode on
        self.font_sets: dict[str, tuple[set[str], bool]] = {}
        self.font_templates: dict[str, set[str]] = {}  # type -> the parts of its text a Set text replaces
        self.solid_obstacles = False  # a Pathfinding instance takes its obstacles from Solids
        self.solid_changes: list[str] = []  # where an action changes a Solid
        self.regenerated = False  # some action regenerates the obstacle map or a region of it
        self.function_blocks: dict[str, dict] = {}  # name -> function block
        self.custom_blocks: dict[tuple[str, str], dict] = {}  # (owner, name) -> custom action block
        self.event_where: dict[int, str] = {}  # id(event) -> where it is, for a finding about another event
        self.answered: dict[int, dict] = {}  # id(event that starts with Else) -> the event before it
        self.action_lists: list[tuple[list, str]] = []  # (actions, where) of every block
        self.solid_overlaps: list[tuple[str, dict, str, str, set[int]]] = []  # (where, condition, Platform object, Solid, ids of its event's action lists)
        self.drops: list[tuple[str, dict, str, str]] = []  # (where, condition or action, Drag & Drop object, what it is dropped on)
        self.timer_starts: list[tuple[str, dict, tuple, bool | None]] = []  # (where, Start timer, line, paced)
        self.hit_pairs: list[tuple] = []  # (object, the object it hits) of each collision or overlap test
        self.destroys: list[tuple] = []  # (object, whether it can be a bullet that missed) of each Destroy
        self._summaries: dict[int, tuple | None] = {}

    def check(self) -> None:
        self.check_project_file()
        self.check_names()
        self.check_animations()
        self.check_images()
        self.check_layouts()
        for obj in list(self.p.types) + list(self.p.families):
            self.check_namespace(obj)
        self.check_sheets()
        self.check_calls()
        self.check_uniqueness()
        self.check_files_and_addons()
        self.check_secrets()
        self.warn_deprecated()

    def deprecated_use(self, where: str, what: str) -> None:
        self.deprecated_uses.setdefault(what, []).append(where)

    def warn_deprecated(self) -> None:
        """One warning per deprecated ACE or expression, at its first use: a model
        writing from memory repeats `rgb` a dozen times, and a line for each would
        push the project's errors out of the report."""
        for what, wheres in self.deprecated_uses.items():
            more = len(wheres) - 1
            self.warn(f"{wheres[0]}: {what}" + (f"; used {more} more time{'s' if more > 1 else ''} after this" if more else ""))

    def run(self) -> int:
        self.check()
        return self.report()

    def report(self) -> int:
        """Warnings, then problems, then the line that says how it went. A report
        longer than --limit prints what fits of each, warnings in at most a third
        of it when there are problems too, the problems in the rest, and says how
        many it left out."""
        p = self.p
        warnings, errors = [f"warning: {w}" for w in p.findings.warnings], p.findings.errors
        # The room kept for the cut notes and the last line.
        closing = 300 + (0 if errors else len(self.ok_line())) + (len(c3.REVIEW) if self.review else 0)
        room = max(self.limit - closing, 3)
        cut = self.limit and c3.fitting(warnings + errors, room) < len(warnings + errors)
        shares = (0, 0)  # 0 is no limit
        if cut:
            of_warnings = room // 3 if errors else room
            used = sum(len(w) + 1 for w in warnings[:max(c3.fitting(warnings, of_warnings), 1)])
            shares = (of_warnings, max(room - used, 1))
        for lines, share, rest in ((warnings, shares[0], "warnings"),
                                   (errors, shares[1], "problems; fix these and run again")):
            fit = max(c3.fitting(lines, share), 1)
            if lines:
                print("\n".join(lines[:fit]))
            if fit < len(lines):
                print(f"... and {len(lines) - fit} more {rest} (--limit 0 prints all)")
        if self.review:
            print(c3.REVIEW)
        notes, stops = fix_loop(p, errors) if self.record else ([], [])
        if notes:
            print("\n".join(notes))
        if errors:
            print(f"{len(errors)} problem(s)")
            if stops:
                print("\n".join(stops))
            return 1
        print(self.ok_line(then_open=not self.review))
        return 0

    def ok_line(self, then_open: bool = True) -> str:
        """An agent takes the last line of a passing check for the end of the
        work, so the line names the step after it. edit_sheet.py prints it without:
        a plan is one step of the work, not its end."""
        p = self.p
        line = (f"ok: {len(p.types)} object types, {len(p.families)} families, {len(self.layouts)} layouts, "
                f"{len(self.sheets)} sheets, {len(self.sids) + len(self.ace_sids)} sids, {len(self.uids)} uids, "
                f"{len(self.functions)} functions, {len(self.custom_actions)} custom actions")
        scripts = p.scripts_summary()
        if scripts:
            line += f"; scripts, which this check does not run or type-check: {scripts}"
        if not then_open:
            return line
        if scripts:
            line += "".join(f"; {clause}" for clause in copied_sizes(p, self.layouts))
            line += (f"; when you write or change a script, look up each API it calls: "
                     f"{script_command(p.root, 'lookup_script_api.py')} NAME")
        if os.environ.get(c3.IN_VERIFY) == "1":  # verify_change.py says the next step itself
            return line
        return (f"{line}; next, run {script_command(p.root, 'verify_change.py')}, which goes on with the design "
                f"review, the editor and its preview, the kept plays and the look, and says what to do at each")


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def own_part(node):
    """An event without its sub-events, a layer without its sublayers: a change below it is not a
    change to it."""
    return {k: v for k, v in node.items() if k not in ("children", "subLayers")} if isinstance(node, dict) else node


def event_in(events: list, sid: str, number: int) -> dict | None:
    """The event of a sheet with this sid, else its numbered event of this number."""
    def every(rows):
        for ev in rows if isinstance(rows, list) else []:
            if isinstance(ev, dict):
                yield ev
                yield from every(ev.get("children"))
    found = next((ev for ev in every(events) if str(ev.get("sid")) == sid), None)
    if found is None and isinstance(events, list):
        found = next((ev for n, ev in enumerate(c3.numbered_events([e for e in events if isinstance(e, dict)]), 1)
                      if n == number), None)
    return found


def layer_in(layers: list, name: str) -> dict | None:
    for layer in layers if isinstance(layers, list) else []:
        if isinstance(layer, dict):
            if layer.get("name") == name:
                return layer
            found = layer_in(layer.get("subLayers"), name)
            if found is not None:
                return found
    return None


def plain(text: str, numbers: bool = False) -> str:
    """The words of a finding in lowercase letters only, and with `numbers` the numbers too (action
    2): what stays when a change alters a name, an id or a value that the finding names."""
    return " ".join(w for w in QUOTED.sub(" ", text).replace(";", " ").replace(",", " ").split()
                    if (numbers and w.isdigit()) or (w.isascii() and w.isalpha() and w.islower()))


def finding_place(p: c3.Project, finding: str) -> dict | None:
    """Where a finding is, as the fix loop counts it, or None for a finding that names no project
    file, such as a clone that is behind. The place is the file, the event (by sid and number) or
    layer that the finding names in it, and the rest of its place (action 2). The plain words of
    the message tell two findings at one place apart, and a digest holds what the place holds now."""
    where, _, message = finding.partition(": ")
    if not message:
        return None
    if where == "project.c3proj" or where.startswith("project.c3proj "):
        path, rest = p.root / "project.c3proj", where[len("project.c3proj"):]
    else:
        prefix = next((pre for pre in PLACES if where.startswith(pre + " ")), None)
        if prefix is None:
            return None
        files = p.listed_files(PLACES[prefix])
        names = [n for n in files if where == f"{prefix} {n}" or where.startswith(f"{prefix} {n} ")]
        if not names or files[max(names, key=len)] is None:
            return None
        name = max(names, key=len)
        path, rest = files[name], where[len(prefix) + 1 + len(name):]
    try:
        node = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        node = path.read_bytes().hex() if path.is_file() else None
    event = sid = None
    part = plain(rest, numbers=True)
    m = EVENT_PLACE.match(rest)
    if m and isinstance(node, dict):
        event, sid, part = int(m.group(1)), m.group(2), plain(rest[m.end():], numbers=True)
        node = event_in(node.get("events"), sid, event) or node
    elif rest.startswith(" layer ") and isinstance(node, dict):
        part = rest.strip()
        node = layer_in(node.get("layers"), rest[len(" layer "):]) or node
    return {"file": path.resolve().relative_to(p.root.resolve()).as_posix(), "event": event, "sid": sid,
            "part": part, "words": plain(message), "digest": digest(own_part(node))}


def fix_loop(p: c3.Project, errors: list[str]) -> tuple[list[str], list[str]]:
    """Count the changes to each finding's place against the record of the last run, and keep the
    new record: the digest of the files, the number of problems and the findings with a place. A
    change counts when the place differs from the last run and the finding is still there. A rerun
    with nothing changed counts none and says so; a finding fixed, or a new one, starts from none.
    Returns the notes, and a stop line for each finding that CAP changes left standing. Nothing in
    the project is undone: which change to keep is the user's call."""
    record = p.root / pp.SCRATCH / RECORD
    try:
        last = json.loads(record.read_text(encoding="utf-8"))
        before = last["findings"] if isinstance(last.get("findings"), list) else []
    except (OSError, ValueError, AttributeError, KeyError):
        last, before = {}, []

    def key(e: dict, by: str) -> tuple:
        return e.get("file"), by, e.get(by), e.get("part"), e.get("words")
    earlier = {key(e, by): e for e in before if isinstance(e, dict) for by in ("sid", "event")}
    now, entries, seen = project_digest(p.root), [], set()
    for finding in errors:
        place = finding_place(p, finding)
        if place is None or key(place, "sid") in seen:
            continue
        seen.add(key(place, "sid"))
        was = earlier.get(key(place, "sid")) if place["sid"] is not None else None
        was = was or earlier.get(key(place, "event"))
        changes = was.get("changes", 0) + (was.get("digest") != place["digest"]) if was else 0
        entries.append({**place, "finding": finding, "changes": changes})
    pp.ignored_folder(record.parent)
    record.write_text(json.dumps({"project": now, "problems": len(errors), "findings": entries},
                                 ensure_ascii=False, indent=1), encoding="utf-8")
    generated = (p.root / c3.GENERATOR).is_file()
    notes = []
    if errors and last.get("project") == now:
        notes.append(f"nothing changed in project.c3proj or the editor's JSON files since the last run, so no "
                     f"finding counts as changed: change the project where each finding says, then run this again."
                     + (f" {c3.GENERATOR} writes the files: run python {c3.GENERATOR} after a change to it."
                        if generated else ""))
    stops = []
    for e in entries:
        if e["changes"] < CAP:
            continue
        where = f"event {e['event']}" if e["event"] else e["part"] if e["part"].startswith("layer ") else ""
        at = f"{where} of {e['file']}" if where else e["file"]
        diff = f"git diff {e['file']}" + (f" {c3.GENERATOR}" if generated else "")
        stops.append(f"stop: do not change {at} again. {e['changes']} changes left this finding standing, so the "
                     f"fix it names was misread or does not fit there: {e['finding']}. {diff} shows the changes "
                     f"(git log -p after they are committed). Tell the user the finding and what each change "
                     f"tried, and let them decide; the changes stay in the project. Fix the other findings as "
                     f"they say.")
    return notes, stops


def copied_sizes(p: c3.Project, layouts: dict[str, dict]) -> list[str]:
    """A clause for each script whose code writes both the width and the height of a layout as
    numbers, for the first such layout: the numbers, and what to read at run time in their place.
    A size copied into a script is wrong when the layout is resized. An instance's size is named
    only beside its layout's, because scripts also write such numbers as offsets and counts.
    Evidence: docs/decisions/project-tools-skill.md."""
    def size(holder: dict) -> tuple[float, float] | None:
        w, h = holder.get("width"), holder.get("height")
        return (float(w), float(h)) if JSON_TYPES["number"](w) and JSON_TYPES["number"](h) and w > 0 and h > 0 \
            else None

    def written(numbers: dict[float, int], wh: tuple[float, float]) -> bool:
        # A square is written when its side appears twice
        return numbers.get(wh[0], 0) >= 2 if wh[0] == wh[1] else wh[0] in numbers and wh[1] in numbers

    def shown(wh: tuple[float, float]) -> str:
        return f"width {wh[0]:.10g}, height {wh[1]:.10g}"

    out = []
    for path in p.script_files():
        numbers = p.script_numbers(path)
        for name, layout in layouts.items():
            wh = size(layout) if isinstance(layout, dict) else None
            if not wh or not written(numbers, wh):
                continue
            objects: dict[str, tuple[float, float]] = {}
            for layer, _ in c3.layers_of(layout.get("layers", [])):
                for inst in layer.get("instances", []):
                    of = size(inst.get("world") or {}) if isinstance(inst, dict) else None
                    if of and written(numbers, of):
                        objects.setdefault(str(inst.get("type")), of)
            named = list(objects.items())[:3]
            held = f"{path.as_posix()} writes these sizes as numbers: layout {name!r} ({shown(wh)})"
            held += "".join(f", {obj} in it ({shown(of)})" for obj, of in named)
            read = ("Replace the layout's numbers with runtime.layout.width and runtime.layout.height, and each "
                    "object's numbers with the width and height of its instance") if named \
                else "Replace them with runtime.layout.width and runtime.layout.height"
            out.append(f"{held}. {read}. A number copied from the layout is wrong when the layout"
                       f"{' or an instance' if named else ''} is resized")
            break
    return out


def helpers_behind(root: Path, rag: Path) -> str | None:
    """A sentence when the helpers of the project's generator are an older version than the
    skill's, with the command that refreshes them; a generator whose markers are broken is
    named too, since nothing can refresh it. Edits there, with nothing newer to take, and a
    generator from before the markers say nothing. The helpers edited there are named when the
    clone's history holds the template they were copied from, as install.py names them."""
    h = c3.generator_helpers(root)
    command = script_command(root, "install.py", " --helpers-only")
    if h.state == "broken":
        return f"{c3.GENERATOR}: {h.detail}; until then the skill cannot refresh its helpers"
    if h.state == "older":
        have, want = c3.versions(h.have, h.want)
        return (f"{c3.GENERATOR}: its helpers, between the markers, are the skill's of {have}, and the skill's are "
                f"now of {want}; refresh them, which leaves the lines outside the markers as they are: {command}, "
                f"then run python {c3.GENERATOR}")
    if h.state == "edited" and h.have.stamp != h.want.stamp and h.have.version <= h.want.version:
        have, want = c3.versions(h.have, h.want)
        copied = c3.copied_template(rag, h.have.stamp)
        lost = c3.unkept_helpers(root, copied=copied) if copied else None
        changed = f" ({', '.join(n for n, _, _ in lost)})" if isinstance(lost, list) and lost else ""
        return (f"{c3.GENERATOR}: its helpers, between the markers, are the skill's of {have} with edits made "
                f"there, and the skill's are now of {want}. Copy each helper changed there{changed} below "
                f"the end marker, where a def of the same name replaces the one between the markers, then run "
                f"{command} --replace-edited-helpers and python {c3.GENERATOR}")
    return None


def block_behind(root: Path) -> str | None:
    """A sentence when the Construct 3 block of the project's instruction file is an older version
    than the skill's, with the command that refreshes it, as helpers_behind says it of the generator.
    An edited block with a newer version to take gets the command that lists the edits, and a block
    whose markers are broken is named, since nothing can refresh it. Edits with nothing newer to
    take, and an instruction file without a block that install.py wrote, say nothing."""
    b = c3.instruction_block(root)
    command = script_command(root, "install.py", " --block-only")
    if b.state == "broken":
        return f"{b.file}: {b.detail}; until then the skill cannot refresh its Construct 3 block"
    if b.state == "older":
        have, want = c3.versions(b.have, b.want)
        before = "" if b.have.marked else ", written before the block had markers,"
        return (f"{b.file}: its Construct 3 block is the skill's of {have}{before} and the skill's is now of {want}; "
                f"refresh it, which keeps the lines that name a clone's folder and every line outside the block: "
                f"{command}")
    if b.state == "edited" and b.have.stamp != b.want.stamp and b.have.version <= b.want.version:
        have, want = c3.versions(b.have, b.want)
        return (f"{b.file}: its Construct 3 block is the skill's of {have} with edits made between its markers, and "
                f"the skill's is now of {want}. {command} lists the lines that differ; move the project's own below "
                f"the end marker, then run it with --replace-edited-block")
    return None


def main() -> int:
    ap = c3.argument_parser(
        "Check a Construct 3 folder project against the Construct3-RAG schemas and the rules the editor applies "
        "when it opens or previews a project. Every finding names its place, as 'sheet Game event 15 action 2' "
        "with the editor's event number, and says what to write where it can.",
        "examples:\n"
        "  python scripts/check_project.py\n"
        "  python scripts/check_project.py --project ../OtherGame\n\n"
        "  python scripts/check_project.py --style        # a project the agent wrote\n"
        "  python scripts/check_project.py --review       # a project someone asked about\n\n"
        "the last line: ok: and the next step, the number of problems, or stop: and a finding that two\n"
        "changes left standing, which goes to the user\n\n"
        "exit codes: 0 no errors (warnings do not fail the run), 1 findings or project/clone not found,\n"
        "2 the run stopped: a project file lacks a key the editor always writes, or the script failed,\n"
        "as its line says")
    ap.add_argument("--style", action="store_true",
                    help="also warn where a sheet departs from the authoring style of the official examples: "
                         f"{STYLE_RUN} or more actions in a row without a comment action, a top-level event with "
                         f"no comment above it, an event none of whose case sub-events has a comment above it, "
                         f"Every tick beside another condition, "
                         f"sub-events {STYLE_TREE} levels deep whose leaves all call one function, "
                         f"{STYLE_LADDER} or more sibling events of the same conditions and actions with other "
                         "values, Every N seconds taking N off a variable, a countdown the Timer "
                         "behavior keeps, chooseindex on a condition, sibling events dispatching on find of one "
                         "text, and mid through two text literals. For a project the agent wrote; edit_sheet.py "
                         "refuses a plan whose new events raise the first four and warns on the other six")
    ap.add_argument("--review", action="store_true",
                    help="for a project someone else wrote and asked about: leave out the parameters the editor "
                         "fills, end without the next steps of writing a project, and say above the last line "
                         "what a review reports")
    args = ap.parse_args()
    c3.utf8_output()
    findings = c3.Findings()
    c3.stop_with_a_sentence("check_project.py", findings)
    project = c3.Project.open(args, findings)
    cookbook = c3.locate_cookbook(project.rag, project.root)[0]
    if c3.offline():
        print(f"note: CONSTRUCT3_RAG_OFFLINE is 1, so the clone at {project.rag} was not compared with its upstream"
              f"{f', nor the {c3.COOKBOOK_CLONE} clone at {cookbook} with its' if cookbook else ''}")
    # The checks run without the guides; only the pitfalls their findings cite are missing
    if not cookbook:
        print(f"note: {c3.missing_cookbook(project.rag)}")
    # Stale tools and guides are a problem to fix first: a warning above a passing check's last line goes unread
    behind = c3.clone_behind(project.rag)
    for lag in (behind, c3.cookbook_behind(cookbook)):
        if lag:
            line, error = lag
            (findings.err if error else findings.warn)(line)
    drift = None if behind and behind[1] else c3.skill_drift(project.rag)  # the update above refreshes the copy too
    if drift:
        findings.err(drift)
    helpers = helpers_behind(project.root, project.rag)
    if helpers:
        findings.warn(helpers)
    block = block_behind(project.root)
    if block:
        findings.warn(block)
    record = not args.review and os.environ.get("CONSTRUCT3_RAG_NO_RECORD") != "1"
    return Checker(project, args.limit, style=args.style, review=args.review, record=record).run()


if __name__ == "__main__":
    sys.exit(main())
