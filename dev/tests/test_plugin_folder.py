"""plugin/, the Claude Code plugin: its sources under the directory's limits and no data, which the scripts read
from the Construct3-RAG clone and print the clone command for when there is none
(docs/decisions/plugin-reads-the-clones.md, docs/decisions/plugin-folder.md); the guides live in
Construct3-Cookbook, not here (docs/decisions/guides-in-cookbook.md)."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from scripts import build_plugin
from tests.skill_helpers import DATA, PLUGIN, REPO, SKILL

NAMED = re.compile(r"Construct3-RAG/(data/[A-Za-z0-9_./-]*[A-Za-z0-9_/])")
RAG_CLONE = 'git clone --depth 1 https://github.com/XHXIAIEIN/Construct3-RAG "{}"'


def test_the_plugin_holds_no_copy_of_the_guides():
    """The guides reach users by git pull of Construct3-Cookbook; a copy here would go stale between releases."""
    assert not (PLUGIN / "prompts").exists()
    assert not list(PLUGIN.rglob("event-sheet-pitfalls.md"))


def test_the_plugin_holds_no_data():
    """The scripts read the data from the Construct3-RAG clone, which a data refresh moves every day."""
    assert not (PLUGIN / "data").exists()
    assert not list(PLUGIN.rglob("*.bundle-*.json"))


def test_plugin_folder_is_under_the_limits_with_its_version():
    p = subprocess.run([sys.executable, str(REPO / "dev" / "scripts" / "build_plugin.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert p.returncode == 0, p.stdout + p.stderr


def test_the_check_refuses_a_data_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(build_plugin, "PLUGIN", tmp_path)
    assert build_plugin.held_data() == []
    (tmp_path / "data").mkdir()
    assert build_plugin.held_data() and "Construct3-RAG" in build_plugin.held_data()[0]


def test_the_repository_has_no_gitattributes():
    # The directory refuses to validate a repository whose attributes could rewrite files at checkout
    # (docs/decisions/plugin-folder.md)
    assert not (REPO / ".gitattributes").exists()


def test_the_limits_hold_the_folder_size(tmp_path, monkeypatch):
    folder = tmp_path / "plugin"
    folder.mkdir()
    (folder / "a.json").write_bytes(b"{}\n" * 10)
    assert build_plugin.limits(build_plugin.files(folder)) == []
    monkeypatch.setattr(build_plugin, "MAX_TOTAL", 29)
    assert build_plugin.limits(build_plugin.files(folder)) == ["30 bytes in all, more than 29"]
    # A checkout with core.autocrlf holds the same file with CRLF: the directory reads the stored LF bytes
    (folder / "a.json").write_bytes(b"{}\r\n" * 10)
    assert build_plugin.limits(build_plugin.files(folder)) == ["30 bytes in all, more than 29"]


def test_every_data_file_the_skill_names_is_in_the_construct3_rag_clone():
    """The skill names a file of the data as Construct3-RAG/<path>, a path in the clone the scripts read."""
    texts = [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md")), SKILL / "assets" / "game-project-block.md"]
    missing, names = set(), 0
    for path in texts:
        for rel in NAMED.findall(path.read_text(encoding="utf-8")):
            names += 1
            if not (DATA.parent / rel).exists():
                missing.add(f"{path.name}: {rel}")
    assert names > 5 and not missing, sorted(missing)


def test_the_marketplace_installs_the_plugin_folder():
    market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert [p["source"] for p in market["plugins"]] == ["./plugin"]
    assert not (REPO / ".claude-plugin" / "plugin.json").exists()
    assert json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["name"] == "construct3"


def test_the_listing_icon_is_a_file_of_the_plugin():
    """The directory reads the listing icon from plugin.json's "icon", a path inside the plugin, outside
    .claude-plugin/ (Claude Code docs, "Plugin manifest reference", "Directory listing fields")."""
    icon = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["icon"]
    path = (PLUGIN / icon).resolve()
    assert icon.startswith("./") and path.is_file(), icon
    assert path.is_relative_to(PLUGIN.resolve()) and ".claude-plugin" not in path.relative_to(PLUGIN.resolve()).parts


def installed_plugin(tmp_path: Path, version: str = "1.0.0") -> Path:
    """A copy of the plugin outside the repository, where Claude Code installs it: a version folder of the
    plugin's cache folder, with no clone holding it."""
    plugin = tmp_path / "cache" / "construct3" / version
    shutil.copytree(PLUGIN, plugin, ignore=shutil.ignore_patterns("__pycache__"))
    return plugin


def plugin_runner(tmp_path: Path, plugin: Path):
    """A script of the plugin run from tmp_path, with no CONSTRUCT3_RAG and no CONSTRUCT3_COOKBOOK: the scripts
    find the clones beside the plugin's cache folder, as an installed plugin does."""
    scripts = plugin / "skills" / "construct3-agent-plugin" / "scripts"
    env = {k: v for k, v in os.environ.items() if k not in ("CONSTRUCT3_RAG", "CONSTRUCT3_COOKBOOK")}
    env.update(PYTHONIOENCODING="utf-8", CONSTRUCT3_RAG_OFFLINE="1")

    def run(script: str, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(scripts / script), *args], cwd=tmp_path, env=env,
                              capture_output=True, text=True, encoding="utf-8", timeout=60)
    return run


def test_the_installed_plugin_reads_the_construct3_rag_clone_beside_it(tmp_path):
    """With a Construct3-RAG clone beside the plugin's cache folder every script finds the data, and a printed
    path opens as it is. An example is its editor URL alone, since no example projects lie beside the plugin."""
    plugin = installed_plugin(tmp_path)
    shutil.copytree(DATA, plugin.parent / "Construct3-RAG" / "data")
    run = plugin_runner(tmp_path, plugin)

    def out(script: str, *args: str) -> str:
        p = run(script, *args)
        assert p.returncode == 0, p.stdout + p.stderr
        return p.stdout

    assert out("lookup_ace.py", "System", "wait").startswith("action wait - Wait [system]\n")
    text = out("lookup_script_api.py", "IRuntime.callFunction")
    path = re.match(r"IRuntime\.callFunction   (.+\.d\.ts):\d+\n", text)
    assert path and Path(path[1]).is_file() and Path(path[1]).is_relative_to(plugin.parent / "Construct3-RAG"), text
    text = out("search_guides.py", "wait", "platformer")
    assert text.startswith("note: pitfalls not searched: no Construct3-Cookbook clone") and "git clone" in text, text
    assert "\n  https://editor.construct.net/#open=3d-platformer\n" in text, text
    # The pointers come from a Cookbook clone, which no copy of the plugin holds: an entry prints none
    text = out("lookup_ace.py", "Tween", "tween-one-property")
    assert "tween-one-property" in text and "  pitfalls: " not in text, text
    assert out("new_project.py", "MyGame").rstrip().splitlines()[-1].startswith("ok: next, python ")
    p = run("check_project.py", "--project", str(tmp_path / "MyGame"))
    assert p.returncode == 0 and p.stdout.rstrip().splitlines()[-1].startswith("ok:"), p.stdout + p.stderr


def test_the_installed_plugin_without_construct3_rag_prints_the_clone_command(tmp_path):
    """The plugin never clones or downloads anything itself: each script that reads the data stops with the
    git clone that puts Construct3-RAG beside the plugin's cache folder, where it looks first."""
    plugin = installed_plugin(tmp_path)
    run = plugin_runner(tmp_path, plugin)
    clone = RAG_CLONE.format((plugin.parent / "Construct3-RAG").as_posix())
    (tmp_path / "game").mkdir()
    (tmp_path / "game" / "project.c3proj").write_text("{}", encoding="utf-8")
    for script, *args in (("lookup_ace.py", "System", "wait"), ("lookup_script_api.py", "IRuntime"),
                          ("search_guides.py", "wait"), ("new_project.py", "MyGame"),
                          ("check_project.py", "--project", str(tmp_path / "game")),
                          ("print_sheet.py", "--project", str(tmp_path / "game"), "Game")):
        p = run(script, *args)
        assert p.returncode != 0 and clone in p.stderr and "Traceback" not in p.stderr, (script, p.stdout + p.stderr)
    assert not (tmp_path / "MyGame").exists() and not (plugin.parent / "Construct3-RAG").exists()


def test_the_plugin_agent_carries_only_the_tools_the_scripts_need():
    """A general-purpose sub-agent starts with every tool and server of the session; the plugin's agent
    type names only the tools the skill's scripts are run and read with, and Agent, which starts the look
    judge on the brief of review_look.py (docs/decisions/project-worker-agent.md, which measures the cost).
    A plain frontmatter parser reads it, so no value holds ': '."""
    agent = PLUGIN / "agents" / "project-worker.md"
    text = agent.read_text(encoding="utf-8")
    head, body = text.split("\n---\n", 1)
    fields = dict(line.split(": ", 1) for line in head.removeprefix("---\n").splitlines())
    assert fields["name"] == "project-worker" and len(fields["description"]) < 1024
    assert [t.strip() for t in fields["tools"].split(",")] == ["Bash", "PowerShell", "Read", "Edit", "Write", "Grep",
                                                               "Glob", "Skill", "Agent"]
    assert "construct3:construct3-agent-plugin" in body and "SKILL.md" in body
    assert "`brief:`" in body and "construct3:look-judge" in body and "construct3:design-judge" in body
    assert "construct3:recording-describer" in body and "preview_project.py" in body
    # A judge started in the background outlives a worker that ends first, and its reply reaches no one.
    assert "`run_in_background: false`" in body


def test_the_design_judge_only_reads_and_runs_the_measured_model():
    """The design judge answers review_design.py's brief apart from the agent that wrote the events: it can only
    read, it starts without the project's instruction files, and it names the model whose answers were measured
    by its full ID (docs/decisions/design-judge-agent.md)."""
    text = (PLUGIN / "agents" / "design-judge.md").read_text(encoding="utf-8")
    head, body = text.split("\n---\n", 1)
    fields = dict(line.split(": ", 1) for line in head.removeprefix("---\n").splitlines())
    assert fields["name"] == "design-judge" and len(fields["description"]) < 1024
    assert fields["tools"] == "Read" and fields["omitClaudeMd"] == "true"
    assert fields["model"].startswith("claude-"), fields["model"]
    assert "brief.md" in body and "offset" in body


def test_the_recording_describer_only_reads_and_never_judges():
    """The recording describer answers the brief of a recording apart from the agent that wrote the events: it can
    only read, it starts without the project's instruction files, it runs a fixed model, and it describes what the
    frames show without judging it (docs/decisions/recording-describer.md)."""
    text = (PLUGIN / "agents" / "recording-describer.md").read_text(encoding="utf-8")
    head, body = text.split("\n---\n", 1)
    fields = dict(line.split(": ", 1) for line in head.removeprefix("---\n").splitlines())
    assert fields["name"] == "recording-describer" and len(fields["description"]) < 1024
    assert fields["tools"] == "Read" and fields["omitClaudeMd"] == "true"
    assert fields["model"].startswith("claude-"), fields["model"]
    assert "brief.md" in body and "unreadable" in body and "cannot make out" in body and "400 words" in body
    assert "Never say whether anything is correct" in body


def test_the_art_drawer_draws_on_a_fixed_model_from_its_brief():
    """The art drawer draws a game's pictures from the brief of art.py on a fixed strong model, since the main
    agent may be a small one, and starts without the project's instruction files
    (docs/decisions/art-drawer-agent.md)."""
    text = (PLUGIN / "agents" / "art-drawer.md").read_text(encoding="utf-8")
    head, body = text.split("\n---\n", 1)
    fields = dict(line.split(": ", 1) for line in head.removeprefix("---\n").splitlines())
    assert fields["name"] == "art-drawer" and len(fields["description"]) < 1024
    assert [t.strip() for t in fields["tools"].split(",")] == ["Read", "Write", "Edit", "Bash"]
    assert fields["omitClaudeMd"] == "true" and fields["model"].startswith("claude-"), fields["model"]
    assert "brief.md" in body and "three rounds" in body and "tools/drawings.py" in body


def test_the_look_judge_only_reads_and_runs_the_measured_model():
    """The look judge answers review_look.py's brief apart from the agent that built the game: it can only read,
    it starts without the project's instruction files, and it names the model whose answers were measured by its
    full ID, which a client's alias table cannot move (docs/decisions/look-judge-agent.md)."""
    text = (PLUGIN / "agents" / "look-judge.md").read_text(encoding="utf-8")
    head, body = text.split("\n---\n", 1)
    fields = dict(line.split(": ", 1) for line in head.removeprefix("---\n").splitlines())
    assert fields["name"] == "look-judge" and len(fields["description"]) < 1024
    assert fields["tools"] == "Read" and fields["omitClaudeMd"] == "true"
    assert fields["model"].startswith("claude-haiku-"), fields["model"]
    assert "brief.md" in body


def test_every_installed_version_reads_one_construct3_rag_clone(tmp_path):
    """Claude Code gives each plugin version a folder of its own. The clone lies beside those folders, so the
    next version finds the clone the last one used, and no version asks for a copy inside its own folder."""
    old, new = installed_plugin(tmp_path, "1.0.0"), installed_plugin(tmp_path, "1.0.1")
    clone = RAG_CLONE.format((tmp_path / "cache" / "construct3" / "Construct3-RAG").as_posix())
    for plugin in (old, new):
        p = plugin_runner(tmp_path, plugin)("lookup_ace.py", "System", "wait")
        assert p.returncode != 0 and clone in p.stderr, p.stdout + p.stderr
    shutil.copytree(DATA, tmp_path / "cache" / "construct3" / "Construct3-RAG" / "data")
    for plugin in (old, new):
        p = plugin_runner(tmp_path, plugin)("lookup_ace.py", "System", "wait")
        assert p.returncode == 0 and p.stdout.startswith("action wait - Wait [system]\n"), p.stdout + p.stderr
