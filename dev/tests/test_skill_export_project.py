"""export_project.py: the version an export carries, where its runtime starts, and what a run
that stops leaves in the editor."""
import io
import json
import re
import sys
import zipfile
from pathlib import Path

import pytest

from tests.skill_helpers import INSTALLED, SHEET, edit, events, game_rows, run, script_module

SCRIPT = f"{INSTALLED}/scripts/export_project.py"


def test_export_bumps_the_last_export_and_carries_a_hand_edit(project):
    """--bump adds one to the version in the export folder's data.json, a number past 99 carrying
    into the one before, and keeps the project's Version when a hand edit made it greater."""
    web = project / "export" / "web"
    web.mkdir(parents=True)
    (web / "data.json").write_text(json.dumps({"project": ["Coins", None, "0.1.0.99", 1]}), encoding="utf-8")
    script_module("export_project").take_over(web)
    code, out = run(project, SCRIPT, "--to", "export/web", "--bump", "--dry-run")
    assert code == 0 and "would export 1.0.0.0 " in out, out     # the project's 1.0.0.0 is greater than 0.1.1.0
    (web / "data.json").write_text(json.dumps({"project": ["Coins", "1.0.0.99"]}), encoding="utf-8")
    code, out = run(project, SCRIPT, "--to", "export/web", "--bump", "--dry-run")
    assert code == 0 and "would export 1.0.1.0 " in out and "project.c3proj version 1.0.0.0 -> 1.0.1.0" in out, out
    code, out = run(project, SCRIPT, "--version", "1.2", "--dry-run")
    assert code == 2 and "not 3 or 4 numbers" in out, out
    code, out = run(project, SCRIPT, "--dry-run")
    assert code == 0 and f"into {project.resolve() / '.build' / 'web'}" in out, out    # the products' folder
    assert not (project / ".build").exists()                                             # a dry run writes nothing


def test_export_refuses_a_folder_it_would_empty_of_other_files(project, tmp_path):
    """The export replaces everything in --to, so the project, a folder above it, a drive's root, a
    file and a folder of other files are refused before the browser starts, and stay as they were;
    a new or empty folder and an earlier export are taken (the audit of 2026-10-07 emptied a
    temporary project through --to .)."""
    other = tmp_path / "notes"
    other.mkdir()
    (other / "todo.txt").write_text("keep", encoding="utf-8")
    a_file = tmp_path / "a.txt"
    a_file.write_text("keep", encoding="utf-8")
    for to in (".", "..", str(other), str(a_file), str(Path(project.resolve().anchor))):
        code, out = run(project, SCRIPT, "--to", to, "--dry-run")
        assert code == 2 and "the export replaces everything in the folder" in out, (to, out)
    assert (other / "todo.txt").read_text(encoding="utf-8") == "keep" and (project / "project.c3proj").is_file()
    earlier, empty = project / "export" / "web", tmp_path / "empty"
    earlier.mkdir(parents=True)
    (earlier / "data.json").write_text(json.dumps({"project": ["Coins", "1.0.0.0"]}), encoding="utf-8")
    script_module("export_project").take_over(earlier)
    empty.mkdir()
    for to in ("export/web", str(empty), str(tmp_path / "new")):
        code, out = run(project, SCRIPT, "--to", to, "--dry-run")
        assert code == 0 and "would export" in out, (to, out)
    export = script_module("export_project")
    assert export.refused_folder(tmp_path / "game", Path(tmp_path.anchor)) == "it is the root of a drive"


def test_export_hands_the_editor_the_version_to_export(project):
    """The .c3p the editor opens carries the version to export with Auto-increment version off, so
    that the export carries it unchanged, and Use worker Auto; it holds only the
    files the editor reads: no export folder, .tmp or the worktrees under .claude (a game's .c3p was
    1.8 GB, 2026-10-03)."""
    export = script_module("export_project", project / INSTALLED / "scripts")
    path = project / "project.c3proj"
    path.write_text(path.read_text(encoding="utf-8").replace('"autoIncrementVersion": false',
                                                             '"autoIncrementVersion": true')
                    .replace('"useWorker": "auto"', '"useWorker": "dom"'), encoding="utf-8")
    web, worktree = project / "export" / "web", project / ".claude" / "worktrees" / "a"
    web.mkdir(parents=True)
    (web / "data.json").write_text("{}", encoding="utf-8")
    worktree.mkdir(parents=True)     # an agent's copies, 2.2 GB in a game
    (worktree / "project.c3proj").write_text("{}", encoding="utf-8")
    with zipfile.ZipFile(io.BytesIO(export.pack(project, "2.3.4.5", project / "export"))) as z:
        names = z.namelist()
        text = z.read("project.c3proj").decode("utf-8")
    assert '\t\t"version": "2.3.4.5",' in text and '"autoIncrementVersion": false' in text, text[:400]
    assert '"useWorker": "auto"' in text, text[:400]
    assert not any(n.startswith(("export/", ".tmp/", ".claude/")) for n in names), names
    assert any(n.startswith("layouts/") for n in names), names
    assert export.project_version(project) == "1.0.0.0"     # the project file itself is not touched
    assert '"useWorker": "dom"' in path.read_text(encoding="utf-8")


class Tab:
    """A tab of the user's browser as export_project drives it: what it was asked, in order."""

    def __init__(self, target: str = "tab-1") -> None:
        self.target, self.asked = target, []

    def call(self, method: str, wait: float = 10, **params) -> dict:
        self.asked.append(method)
        return {}

    def evaluate(self, expression: str, by_value: bool = True, wait: float = 10):
        self.asked.append(expression)
        return None


def stopped_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, opened: bool, stop_in: str) -> tuple:
    """export_project.run over --attach, stopped in open_project or in export; the module, the
    browser connection, the tab and the pages close_project was given, once run has raised."""
    export = script_module("export_project")
    browser, tab, closed = Tab("browser"), Tab(), []

    def stop(*args):
        raise export.Stop(f"stopped in {stop_in}")
    monkeypatch.setattr(export, "pack", lambda project, version, skip: b"zip")
    monkeypatch.setattr(export, "attach", lambda spec: browser)
    monkeypatch.setattr(export, "attached_page", lambda devtools, project: (tab, opened))
    monkeypatch.setattr(export, "wait_for_login", lambda page: "Someone")
    monkeypatch.setattr(export, "open_project", stop if stop_in == "open_project" else lambda *a: None)
    monkeypatch.setattr(export, "export", stop if stop_in == "export" else lambda page: b"")
    monkeypatch.setattr(export, "close_project", lambda page: closed.append(page))
    with pytest.raises(export.Stop):
        export.run(tmp_path, tmp_path / "web", "1.0.0.0", "9222", None)
    assert not (tmp_path / ".tmp" / "scripts" / "export-project" / f"{tmp_path.name}.c3p").exists()
    return export, browser, tab, closed


def test_a_stopped_export_closes_the_tab_it_opened(monkeypatch, tmp_path):
    """A run that stopped left its copy open in the user's browser, and the next run, which takes
    only a tab on the start page, opened another (2026-10-04, r495-2). A tab the run opened is
    closed when it stops, as after an export."""
    export, browser, tab, closed = stopped_run(monkeypatch, tmp_path, opened=True, stop_in="export")
    assert browser.asked == ["Target.closeTarget"] and closed == [], (browser.asked, closed)


@pytest.mark.parametrize("stop_in", ["open_project", "export"])
def test_a_stopped_export_leaves_the_users_own_tab_on_the_start_page(monkeypatch, tmp_path, stop_in):
    """In a tab of the user's the copy is closed without saving, and the dialogs, the file input
    and the interval open_in_editor's SETUP put there are taken away; the tab and its login stay."""
    export, browser, tab, closed = stopped_run(monkeypatch, tmp_path, opened=False, stop_in=stop_in)
    assert closed == [tab] and browser.asked == [], (closed, browser.asked)
    assert tab.asked[-2:] == [export.DISMISS_JS, export.UNSET_JS], tab.asked
    assert "window.__c3Keep = setInterval" in export.oe.SETUP_JS


@pytest.mark.parametrize("release, reused", [([506, 3], True), ([476, 4], True), ([475, 0], False)])
def test_the_own_window_reuses_an_editor_page_by_its_release(monkeypatch, tmp_path, release, reused):
    """The logged-in page of the script's window was at editor.construct.net/, release 506.3, after
    Update on the editor's update prompt; the next two runs matched pages by the URL of the project's
    release, r476-4/, opened a new page, showed Guest and stopped at the login (2026-10-31). A page
    whose release opens the project is reused wherever its URL points; an older one is not."""
    export = script_module("export_project")
    (tmp_path / "project.c3proj").write_text('{"savedWithRelease": 47604}', encoding="utf-8")
    pages = {"preview": "https://preview.construct.net/local.html", "editor": export.oe.EDITOR}
    opened = []

    class Page(Tab):
        def __init__(self, url: str) -> None:
            super().__init__(url.rsplit("/", 1)[-1])
            self.ws = self

        def close(self) -> None:
            pass

        def evaluate(self, expression: str, by_value: bool = True, wait: float = 10):
            super().evaluate(expression)
            return release if expression == export.oe.RELEASE_JS else None

    class Browser:
        port, devtools = 0, Tab("browser")

        def page(self, url: str) -> tuple:
            opened.append(url)
            return "new", Page(url)

    Browser.devtools.call = lambda method, **params: {"targetInfos": [
        {"type": "page", "url": url, "targetId": target} for target, url in pages.items()]}
    monkeypatch.setattr(export.oe, "DevTools", Page)
    monkeypatch.setattr(export.oe, "load", lambda page, url: None)
    target, page = export.own_page(Browser(), tmp_path)
    assert (target, opened) == (("editor", []) if reused else ("new", [export.oe.EDITOR + "r476-4/"])), (target, opened)


def test_a_crashed_editor_is_restarted_to_close_the_copy(capsys):
    """An export left the user's tab on the editor's crash report, which has no close button and
    came back each time the menu opened, so the copy could not be closed (2026-10-04, r495-2).
    Restart reloads the editor once the page's question about leaving is answered, which the
    DevTools protocol sees only after Page.enable; the editor was back on its start page in 3 s."""
    export = script_module("export_project")

    class Crashed(Tab):
        reloaded = pressed = False

        def call(self, method: str, wait: float = 10, **params) -> dict:
            super().call(method)
            if method == "Page.handleJavaScriptDialog":
                if not self.pressed:
                    raise export.oe.DevToolsError("Page.handleJavaScriptDialog: No dialog is showing")
                self.reloaded = True
            return {}

        def evaluate(self, expression: str, by_value: bool = True, wait: float = 10):
            super().evaluate(expression)
            if expression == "document.title":
                return "Game Making Software - Construct 3" if self.reloaded else "Coins - Construct 3"
            if expression == export.CRASH_JS:
                return not self.reloaded
            if "reloadButton" in expression:
                self.pressed = True
                return 1
            if expression.startswith("[performance.timeOrigin"):
                return [2 if self.reloaded else 1, self.reloaded]
            return 1 if expression == "performance.timeOrigin" else None

    tab = Crashed()
    export.close_project(tab)
    assert tab.reloaded and tab.asked.index("Page.enable") < tab.asked.index("Page.handleJavaScriptDialog")
    assert not any("mainMenuButton').getBoundingClientRect" in a for a in tab.asked), tab.asked   # no menu
    assert "pressing its Restart, which reloads the editor: log in there again if it asks" in capsys.readouterr().out


def test_export_reads_where_the_runtime_starts(tmp_path):
    """The end of an r504 export's scripts/main.js, worker off and on."""
    export = script_module("export_project")
    main = tmp_path / "scripts" / "main.js"
    main.parent.mkdir()
    for flag, expected in (("false", False), ("true", True)):
        main.write_text('// start-export.js\n"use strict";if(window["C3_IsSupported"]){const e=' + flag +
                        ';window["c3_runtimeInterface"]=new self.RuntimeInterface({useWorker:e,workerMainUrl:'
                        '"workermain.js",runtimeMainScript:"scripts/c3main.js"})}', encoding="utf-8")
        assert export.exported_worker(tmp_path) is expected
    main.write_text("", encoding="utf-8")
    assert export.exported_worker(tmp_path) is None


def zipped_export(version: str) -> bytes:
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as z:
        z.writestr("data.json", json.dumps({"project": ["Coins", version]}))
        z.writestr("index.html", version)
    return data.getvalue()


def test_a_failed_unpack_keeps_the_earlier_export(monkeypatch, tmp_path):
    """The new export is extracted beside the folder and checked before it takes the folder's place,
    so an extraction that fails, a version that differs and a swap that fails leave the earlier export
    as it was (the audit of 2026-10-07 lost it to a failed extraction)."""
    export = script_module("export_project")
    web = tmp_path / "web"
    export.unpack(zipped_export("1.0.0.0"), web, "1.0.0.0")
    before = {f.name: f.read_bytes() for f in web.iterdir()}

    def kept() -> bool:
        return {f.name: f.read_bytes() for f in web.iterdir()} == before and sorted(tmp_path.iterdir()) == [web]

    with pytest.raises(export.Stop, match="not 1.0.1.0"):
        export.unpack(zipped_export("1.0.2.0"), web, "1.0.1.0")
    assert kept()
    with monkeypatch.context() as m:
        def fail(*_):
            raise OSError("disk full")
        m.setattr(zipfile.ZipFile, "extractall", fail)
        with pytest.raises(export.Stop, match="disk full.*earlier export there is left as it was"):
            export.unpack(zipped_export("1.0.1.0"), web, "1.0.1.0")
    assert kept()
    with monkeypatch.context() as m:
        rename = Path.rename

        def fail_new(self, target):
            if self.name.startswith("web.new"):
                raise OSError("in use")
            return rename(self, target)
        m.setattr(Path, "rename", fail_new)
        with pytest.raises(export.Stop, match="in use"):
            export.unpack(zipped_export("1.0.1.0"), web, "1.0.1.0")
    assert kept()
    export.unpack(zipped_export("1.0.1.0"), web, "1.0.1.0")
    assert (web / "index.html").read_text(encoding="utf-8") == "1.0.1.0" and sorted(tmp_path.iterdir()) == [web]
    export.unpack(zipped_export("1.0.2.0"), tmp_path / "first", "1.0.2.0")     # no earlier export
    assert (tmp_path / "first" / "index.html").read_text(encoding="utf-8") == "1.0.2.0"
    mine = tmp_path / "first.old"     # a folder of the user's under the name the swap used before
    mine.mkdir()
    (mine / "notes.txt").write_text("keep", encoding="utf-8")
    export.unpack(zipped_export("1.0.3.0"), tmp_path / "first", "1.0.3.0")
    assert (mine / "notes.txt").is_file() and (tmp_path / "first" / "index.html").read_text(encoding="utf-8") == "1.0.3.0"


def tree(folder: Path) -> dict[str, bytes]:
    return {f.relative_to(folder).as_posix(): f.read_bytes() for f in folder.rglob("*") if f.is_file()}


def test_a_data_json_does_not_make_a_folder_the_exports(project, tmp_path):
    """A data.json proves nothing about who made a folder: a folder of notes beside one was taken as
    --to and emptied, and a project in web.new was deleted whole (the audit of 2026-10-07, S02). The
    export replaces only a folder it made itself, which holds no file it did not write; --take-over
    hands it another folder once, on the user's word."""
    export = script_module("export_project")
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "data.json").write_text(json.dumps({"project": ["Coins", "1.0.0.0"]}), encoding="utf-8")
    (notes / "measurements.txt").write_text("keep", encoding="utf-8")
    code, out = run(project, SCRIPT, "--to", str(notes), "--dry-run")
    assert code == 2 and "no record of" in out and "--take-over" in out, out
    code, out = run(project, SCRIPT, "--to", str(notes), "--take-over", "--dry-run")
    assert code == 0 and "would export" in out, out
    assert tree(notes)["measurements.txt"] == b"keep"

    web = tmp_path / "web"
    export.unpack(zipped_export("1.0.0.0"), web, "1.0.0.0")
    code, out = run(project, SCRIPT, "--to", str(web), "--dry-run")
    assert code == 0 and "would export" in out, out
    (web / "notes.txt").write_text("mine", encoding="utf-8")
    code, out = run(project, SCRIPT, "--to", str(web), "--dry-run")
    assert code == 2 and "did not write: notes.txt" in out, out
    with pytest.raises(export.Stop, match="did not write: notes.txt"):
        export.unpack(zipped_export("1.0.1.0"), web, "1.0.1.0")
    assert tree(web)["notes.txt"] == b"mine" and tree(web)["index.html"] == b"1.0.0.0"
    (web / "notes.txt").unlink()

    neighbours = {"web.new": {"project.c3proj": "{}", "data.json": "{}"},
                  "web.old": {"data.json": "{}", "notes.txt": "keep"}}
    for name, files in neighbours.items():
        (tmp_path / name).mkdir()
        for file, text in files.items():
            (tmp_path / name / file).write_text(text, encoding="utf-8")
    before = {name: tree(tmp_path / name) for name in neighbours}
    export.unpack(zipped_export("1.0.1.0"), web, "1.0.1.0")
    assert tree(web)["index.html"] == b"1.0.1.0"
    assert {name: tree(tmp_path / name) for name in neighbours} == before
    assert sorted(f.name for f in tmp_path.iterdir() if f != project) == ["notes", "web", "web.new", "web.old"]


def test_take_over_hands_the_export_a_folder_once(monkeypatch, project, tmp_path, capsys):
    """An export made by hand or by an earlier version of the script is replaced only with --take-over,
    and a run with it leaves a folder the next run replaces without it."""
    export = script_module("export_project")
    web = tmp_path / "web"
    web.mkdir()
    (web / "data.json").write_text(json.dumps({"project": ["Coins", "1.0.0.0"]}), encoding="utf-8")
    (web / "index.html").write_text("by hand", encoding="utf-8")
    before = tree(web)
    monkeypatch.setattr(export.oe, "browser_path", lambda: "browser")
    monkeypatch.setattr(export, "run", lambda project, folder, version, spec, exe:
                        export.unpack(zipped_export(version), folder, version))
    monkeypatch.setattr(export, "booted", lambda project, folder, exe: 0)
    argv = ["export_project.py", "--project", str(project), "--to", str(web), "--version", "1.2.0.0"]
    monkeypatch.setattr(sys, "argv", argv)
    assert export.main() == 2 and tree(web) == before
    monkeypatch.setattr(sys, "argv", argv + ["--take-over"])
    assert export.main() == 0 and tree(web)["index.html"] == b"1.2.0.0"
    monkeypatch.setattr(sys, "argv", argv[:-1] + ["1.3.0.0"])
    assert export.main() == 0 and tree(web)["index.html"] == b"1.3.0.0"
    assert [f.name for f in tmp_path.iterdir() if f != project] == ["web"]


class Killed(BaseException):
    """The process ending in the middle of a step, which no except clause of the script sees."""


@pytest.mark.parametrize("kill_in", ["extraction", "swap", "cleanup"])
def test_a_retry_after_a_killed_export_keeps_one_export(monkeypatch, tmp_path, kill_in):
    """A run killed between the steps of the swap leaves the earlier export beside the folder, at
    times as the only one; a retry restores it before it clears anything, so a retry that fails
    leaves an export in the folder (the audit of 2026-10-07, S01, lost both to a wrong version)."""
    export = script_module("export_project")
    web = tmp_path / "web"
    export.unpack(zipped_export("1.0.0.0"), web, "1.0.0.0")
    with monkeypatch.context() as m:
        def kill(*_):
            raise Killed
        if kill_in == "extraction":
            m.setattr(zipfile.ZipFile, "extractall", kill)
        elif kill_in == "swap":
            rename = Path.rename
            m.setattr(Path, "rename", lambda self, target: kill() if self.name.startswith("web.new")
                      else rename(self, target))
        else:
            m.setattr(export.shutil, "rmtree", kill)
        with pytest.raises(Killed):
            export.unpack(zipped_export("1.0.1.0"), web, "1.0.1.0")
    with pytest.raises(export.Stop, match="not 1.0.2.0"):
        export.unpack(zipped_export("1.0.1.0"), web, "1.0.2.0")
    expected = "1.0.1.0" if kill_in == "cleanup" else "1.0.0.0"
    assert (web / "index.html").read_text(encoding="utf-8") == expected
    assert [f.name for f in tmp_path.iterdir()] == ["web"]
    export.unpack(zipped_export("1.0.2.0"), web, "1.0.2.0")
    assert (web / "index.html").read_text(encoding="utf-8") == "1.0.2.0"
    assert [f.name for f in tmp_path.iterdir()] == ["web"]


def test_a_backup_that_cannot_be_restored_is_named(monkeypatch, tmp_path):
    """When the earlier export cannot go back in its place, the run stops and names where it is."""
    export = script_module("export_project")
    web = tmp_path / "web"
    export.unpack(zipped_export("1.0.0.0"), web, "1.0.0.0")
    rename = Path.rename
    with monkeypatch.context() as m:
        def kill(self, target):
            if self.name.startswith("web.new"):
                raise Killed
            return rename(self, target)
        m.setattr(Path, "rename", kill)
        with pytest.raises(Killed):
            export.unpack(zipped_export("1.0.1.0"), web, "1.0.1.0")
    (old,) = [f for f in tmp_path.iterdir() if f.name.startswith("web.old")]
    with monkeypatch.context() as m:
        def refuse(self, target):
            if self.name.startswith("web.old"):
                raise OSError("in use")
            return rename(self, target)
        m.setattr(Path, "rename", refuse)
        with pytest.raises(export.Stop, match=f"earlier export is in {re.escape(str(old))}"):
            export.unpack(zipped_export("1.0.1.0"), web, "1.0.1.0")
    assert (old / "index.html").read_text(encoding="utf-8") == "1.0.0.0" and not web.exists()


def test_export_stops_on_a_key_it_would_ship_and_names_the_hosts(project):
    """Every player of a web export can read its strings; the run stops before the browser starts."""
    key = "sk-" + "proj-" + "Ab1" * 12     # built from parts, so that no file of the repository holds one

    def put(sheet):
        events(sheet)["add_score"]["actions"][1]["parameters"]["text"] = f'"{key}" & "https://api.example.com/v1"'
    edit(project, SHEET, put)
    code, out = run(project, SCRIPT, "--dry-run")
    assert code == 1 and out.startswith("not exported: the export ships every string of the project"), out
    assert "  sheet Game event 8 action 2: an OpenAI API key (sk-pro…); to keep it, write allow-secret in the " \
           "comment above the event" in out and key not in out and "would export" not in out, out

    def mark(sheet):
        rows = game_rows(sheet)
        rows[rows.index(events(sheet)["add_score"]) - 1]["text"] += " allow-secret"
    edit(project, SHEET, mark)
    code, out = run(project, SCRIPT, "--dry-run")
    assert code == 0, out
    assert out.startswith("the game holds addresses of api.example.com (sheet Game event 8 action 2): tell the user "
                          "which hosts the game contacts\nwould export"), out


def test_an_export_whose_version_cannot_be_written_says_where_it_is_and_how_to_set_it(monkeypatch, project, capsys):
    """The export is put in place first and the version written after it, on purpose. When project.c3proj
    cannot be written, the run names the version of the export and that of the project, and how to set it,
    with exit code 4."""
    export = script_module("export_project")
    path = project / "project.c3proj"
    before = path.read_bytes()
    old = export.project_version(project)
    write_bytes = Path.write_bytes

    def refuse(self, data):
        if self.name == "project.c3proj":
            raise PermissionError(13, "Access is denied", str(self))
        return write_bytes(self, data)
    monkeypatch.setattr(Path, "write_bytes", refuse)
    monkeypatch.setattr(export.oe, "browser_path", lambda: "browser")
    monkeypatch.setattr(export, "run", lambda project, folder, version, spec, exe: True)
    monkeypatch.setattr(export, "booted", lambda project, folder, exe: 0)
    monkeypatch.setattr(sys, "argv", ["export_project.py", "--project", str(project), "--version", "1.2.0.0"])
    assert export.main() == 4
    out = next(line for line in capsys.readouterr().out.splitlines() if line.startswith("exported "))
    assert out.startswith(f"exported 1.2.0.0 into {project / '.build' / 'web'}, runtime in the worker; project.c3proj "
                          f"was not changed and still says version {old}: ")
    assert "Access is denied" in out and "set Version to 1.2.0.0" in out
    assert path.read_bytes() == before
    monkeypatch.setattr(Path, "write_bytes", write_bytes)
    assert export.main() == 0 and export.project_version(project) == "1.2.0.0"


@pytest.mark.parametrize("install", [False, True])
def test_export_stops_on_a_bundled_addon_unless_the_user_said_yes(monkeypatch, tmp_path, install):
    """The export opens the project in a profile of its own, so it answers the confirmation of a bundled
    addon as open_in_editor.py does: no, naming the addon, unless --install-bundled-addons is given."""
    export = script_module("export_project")
    asked = []

    class Page:
        def evaluate(self, expression, by_value=True, wait=None):
            if "install = false" in expression:
                asked.append(expression)
                return ({"opened": True, "title": "Game", "dialogs": [], "warnings": [], "errors": []} if install
                        else {"opened": False, "title": "", "dialogs": [], "warnings": [], "errors": [],
                              "addon": "Install addon? Name Mallory Tools Version 1.2.0.0 Type Plugin"})
            if expression == "document.title":
                return "Game - Construct 3"
            return "ready" if "async" in expression else {"objectId": "1"} if "aria-label" in expression else False

        def call(self, method, **params):
            return {}
    monkeypatch.setattr(export, "close_project", lambda page: None)
    monkeypatch.setattr(export, "project_title", lambda project: "Game")
    monkeypatch.setattr(export, "bundled", install)
    if install:
        export.open_project(Page(), tmp_path, tmp_path / "game.c3p")
        assert [e[-7:] for e in asked] == [")(true)"], asked
    else:
        with pytest.raises(export.Stop, match="Name Mallory Tools.*--install-bundled-addons"):
            export.open_project(Page(), tmp_path, tmp_path / "game.c3p")
        assert [e[-8:] for e in asked] == [")(false)"], asked


# A stand-in for the runtime of an export: the probe of open_in_editor finds C3.Runtime and waits for a Tick
RUNTIME = """globalThis.C3 = {Runtime: class {
  constructor() { this.n = 0; }
  Tick() { this.n++; }
  GetIRuntime() { const r = this; return {layout: {name: "Title"}, get tickCount() { return r.n; }, objects: {},
    globalVars: {}, addEventListener() {}}; }
}};
const runtime = new C3.Runtime();
setInterval(() => runtime.Tick(), 16);
"""


@pytest.mark.skipif(not script_module("export_project").oe.browser_path(), reason="no Edge, Chrome or Chromium")
@pytest.mark.parametrize("where", ["page", "worker"])
def test_the_boot_runs_the_export_and_names_its_errors_and_missing_files(tmp_path, where):
    """An export that packaged fine can still fail to start in the modes no preview played, so the
    script opens it as a player's browser would. The page and each worker are watched from their first
    line: an error a worker logs before its runtime ticks counts, once, and so does a file the export
    lacks, whichever context asked for it."""
    export = script_module("export_project")
    folder = tmp_path / "web"
    folder.mkdir()
    (folder / "runtime.js").write_text('console.error("no save slot"); fetch("data-missing.json");\n' + RUNTIME,
                                       encoding="utf-8")
    start = ('<script src="runtime.js"></script>' if where == "page"
             else '<script>new Worker("runtime.js", {type: "module"})</script>')
    (folder / "index.html").write_text(f"<!doctype html><body style='background:#235'><h1>Title</h1>{start}"
                                       f"<img src='images/gone.png'>", encoding="utf-8")
    shot = tmp_path / "boot.png"
    result = export.boot(folder, export.oe.browser_path(), tmp_path / "profile", shot)
    assert result["ticked"] is not None and result["layout"] == "Title", result
    assert result["runtime"] == f"the {where}" and result["errors"] == ["no save slot"], result
    assert sorted(result["failed"]) == ["404 data-missing.json", "404 images/gone.png"], result
    assert shot.read_bytes().startswith(b"\x89PNG") and not (tmp_path / "profile").exists()
    lines = export.boot_lines(result, folder, "msedge", shot)
    assert lines[:2] == ["  runtime: no save slot", "  request: " + result["failed"][0]], lines
    assert lines[-1].startswith(f"boot failed: the export in {folder}, served on 127.0.0.1 to a headless msedge: "
                                f"layout Title ticking in the {where} "), lines
    assert lines[-1].endswith(f"s after loading began, with 1 console error and 2 failed requests (above); "
                              f"screenshot {shot}"), lines


def test_the_boot_verdict_is_the_last_line():
    """booted only when the runtime ticked with nothing logged and nothing missing; a runtime that never
    ticked, or a first layout that drew nothing, is said in the same line."""
    export = script_module("export_project")
    shot, folder = Path("boot.png"), Path("web")
    clean = {"ticked": 1.25, "runtime": "the worker", "layout": "Game", "errors": [], "failed": [], "blank": None}
    assert export.boot_lines(clean, folder, "chrome", shot) == [
        f"booted: the export in {folder}, served on 127.0.0.1 to a headless chrome: layout Game ticking in the "
        f"worker 1.2 s after loading began, no console error and no failed request; screenshot {shot}"]
    stalled = {**clean, "ticked": None, "runtime": None, "layout": None, "blank": 0.9995,
               "failed": [f"404 images/{n}.png" for n in range(12)]}
    lines = export.boot_lines(stalled, folder, "chrome", shot)
    assert len(lines) == 12 and lines[-2] == "  and 2 more failed requests", lines
    assert lines[-1].startswith(f"boot failed: the export in {folder}, served on 127.0.0.1 to a headless chrome: no "
                                f"runtime ticked in {export.BOOT_WAIT} seconds, with 12 failed requests (above); "
                                f"99.9% or more of the screenshot is one colour"), lines


@pytest.mark.parametrize("boot, code", [("booted", 0), ("failed", 6), ("not run", 3)])
def test_the_exit_code_is_the_boots(monkeypatch, project, capsys, boot, code):
    """An export whose game did not boot is a finding, 6, and one whose boot could not run was not
    checked, 3, though the export is in place either way."""
    export = script_module("export_project")
    monkeypatch.setattr(export.oe, "browser_path", lambda: None if boot == "not run" else "browser")
    monkeypatch.setattr(export, "run", lambda project, folder, version, spec, exe:
                        export.unpack(zipped_export(version), folder, version))
    result = {"ticked": 2.0, "runtime": "the page", "layout": "Game", "errors": [] if boot == "booted" else ["x"],
              "failed": [], "blank": None}
    monkeypatch.setattr(export, "boot", lambda folder, exe, profile, shot: result)
    monkeypatch.setattr(sys, "argv", ["export_project.py", "--project", str(project), "--version", "1.2.0.0",
                                      *(["--attach", "9222"] if boot == "not run" else [])])
    assert export.main() == code
    out = capsys.readouterr().out.splitlines()
    assert out[-1].startswith({"booted": "booted: ", "failed": "boot failed: ", "not run": "boot not checked: "}[boot])
    assert (project / ".build" / "web" / "index.html").read_text(encoding="utf-8") == "1.2.0.0"


def test_release_warns_of_construct_icons_and_empty_properties(project):
    """A published game should not ship Construct's icons and loading logo or an empty Author, ID or
    Description; the dry run says so already, as a warning that keeps exit 0."""
    export = script_module("export_project")
    template = export.c3.locate_rag(project, None)[0] / "data" / "c3-new-project" / "icons"
    (project / "icons").mkdir(exist_ok=True)
    (project / "icons" / "loading-logo.png").write_bytes((template / "loading-logo.png").read_bytes())
    (project / "icons" / "icon-16.png").write_bytes(b"\x89PNG own")
    code, out = run(project, SCRIPT, "--dry-run")
    lines = [line for line in out.splitlines() if line.startswith("release: ")]
    assert code == 0 and "release: icons/ holds Construct's default loading-logo.png, " in lines[0], out
    assert "icon-16.png" not in lines[0], lines
    properties = export.c3.load(project / "project.c3proj")["properties"]
    empty = [label for key, label in (("author", "Author"), ("appId", "ID"), ("description", "Description"))
             if not properties.get(key)]
    if empty:
        assert lines[1].startswith(f"release: {empty[0]}"), lines

    def fill(data):
        data["properties"].update(author="Someone", appId="com.someone.coins", description="Coins to collect.")
    path = project / "project.c3proj"
    data = json.loads(path.read_text(encoding="utf-8"))
    fill(data)
    path.write_text(json.dumps(data, indent="\t"), encoding="utf-8")
    (project / "icons" / "loading-logo.png").write_bytes(b"\x89PNG own")
    code, out = run(project, SCRIPT, "--dry-run")
    assert code == 0 and "release: " not in out, out
