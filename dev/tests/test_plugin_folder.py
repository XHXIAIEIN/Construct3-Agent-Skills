"""plugin/, the Claude Code plugin: its data/ equal to a fresh build, the folder under the directory's limits,
and holding every data file the skill's text sends an agent to (docs/decisions/plugin-folder.md); the guides
live in Construct3-Cookbook, not here (docs/decisions/guides-in-cookbook.md)."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from scripts import build_plugin
from tests.skill_helpers import DATA, PLUGIN, REPO, SKILL

NAMED = re.compile(r"Construct3-(?:RAG|Agent-Skills/plugin)/(data/[A-Za-z0-9_./-]*[A-Za-z0-9_/])")


def test_the_plugin_holds_no_copy_of_the_guides():
    """The guides reach users by git pull of Construct3-Cookbook; a copy here would go stale between releases."""
    assert not (PLUGIN / "prompts").exists()
    assert not list(PLUGIN.rglob("event-sheet-pitfalls.md"))


def test_plugin_folder_is_a_fresh_build_under_the_limits():
    p = subprocess.run([sys.executable, str(REPO / "dev" / "scripts" / "build_plugin.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert p.returncode == 0, p.stdout + p.stderr


def test_the_build_copies_text_files_with_lf_and_an_image_byte_for_byte(tmp_path):
    # A checkout with core.autocrlf holds CRLF files (docs/decisions/plugin-folder.md)
    (tmp_path / "guide.md").write_bytes(b"# Construct 3\r\n\r\nA line.\r\n")
    icon = (PLUGIN / "icon.png").read_bytes()
    # The PNG signature holds CR LF, so a build that rewrote an image would change it
    assert b"\r\n" in icon
    (tmp_path / "icon.png").write_bytes(icon)
    build_plugin.copy(tmp_path / "guide.md", tmp_path / "out" / "guide.md")
    build_plugin.copy(tmp_path / "icon.png", tmp_path / "out" / "icon.png")
    assert (tmp_path / "out" / "guide.md").read_bytes() == b"# Construct 3\n\nA line.\n"
    assert (tmp_path / "out" / "icon.png").read_bytes() == icon


def test_a_crlf_checkout_of_plugin_equals_its_build(tmp_path):
    built, committed = tmp_path / "built.md", tmp_path / "committed.md"
    built.write_bytes(b"# Construct 3\n\nA line.\n")
    committed.write_bytes(b"# Construct 3\r\n\r\nA line.\r\n")
    assert build_plugin.same(built, committed)
    committed.write_bytes(b"# Construct 3\r\n\r\nAnother line.\r\n")
    assert not build_plugin.same(built, committed)


def test_the_repository_has_no_gitattributes():
    # The directory refuses to validate a repository whose attributes could rewrite files at checkout
    # (docs/decisions/plugin-folder.md)
    assert not (REPO / ".gitattributes").exists()


def test_the_schemas_are_the_source_json_with_an_indent_of_one():
    """An agent opens a schema in the plugin by the path it has in the clone and reads the same JSON;
    the one-space indent keeps the folder under the directory's size limit."""
    rel = "data/c3-schemas/en-US/plugins/sprite.json"
    source = (DATA.parent / rel).read_text(encoding="utf-8")
    built = (PLUGIN / rel).read_text(encoding="utf-8")
    assert json.loads(built) == json.loads(source)
    assert built.startswith('{\n "') and source.startswith('{\n  "')
    assert len(built) < len(source)


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


def test_every_data_file_the_skill_names_is_in_the_plugin():
    """SKILL.md tells a plugin user that such a path lies under the plugin's folder, so it names a file
    there, not one that only a bundle holds."""
    texts = [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md")), SKILL / "assets" / "game-project-block.md"]
    missing, names = set(), 0
    for path in texts:
        for rel in NAMED.findall(path.read_text(encoding="utf-8")):
            names += 1
            if not (PLUGIN / rel).exists():
                missing.add(f"{path.name}: {rel}")
    assert names > 5 and not missing, sorted(missing)


def test_the_language_packs_keep_what_check_project_and_a_preview_inspector_read():
    """check_project.py reads two subtrees of each language pack. The keys of a preview's inspector values
    are paths into the name, properties and debugger texts of a plugin or behavior, such as
    behaviors.platform.debugger.vector-x (references/reading-the-runtime.md, "Inspector values")."""
    for locale in ("en-US", "zh-CN"):
        full = json.loads((DATA / "c3-lang" / f"{locale}.json").read_text(encoding="utf-8-sig"))["text"]
        kept = json.loads((PLUGIN / "data" / "c3-lang" / f"{locale}.json").read_text(encoding="utf-8"))["text"]
        assert kept["ui"]["bars"]["properties"]["project"] == full["ui"]["bars"]["properties"]["project"]
        assert kept["ui"]["bars"]["timeline"]["eases"] == full["ui"]["bars"]["timeline"]["eases"]
        for kind in ("plugins", "behaviors"):
            for addon, texts in full[kind].items():
                for part in ("name", "properties", "debugger"):
                    if part in texts:
                        assert kept[kind][addon][part] == texts[part], f"{locale}: text.{kind}.{addon}.{part}"
        assert kept["behaviors"]["platform"]["debugger"]["vector-x"]


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


def test_scripts_in_the_plugin_read_the_bundled_data_and_print_what_opens(tmp_path):
    """A plugin user has no clone and often no Construct3-RAG line: a printed path opens as it is, and a
    declaration that only a bundle holds names the command that prints it. An example is its editor URL
    alone, since no example projects lie beside the plugin."""
    # A copy outside the repository, as Claude Code installs the plugin: no clone holds it or lies beside it
    plugin = tmp_path / "construct3"
    shutil.copytree(PLUGIN, plugin, ignore=shutil.ignore_patterns("__pycache__"))
    scripts = plugin / "skills" / "construct3-agent-plugin" / "scripts"
    # No CONSTRUCT3_RAG: the scripts find the plugin folder above them, as an installed plugin does;
    # no CONSTRUCT3_COOKBOOK either, so no Cookbook clone holds the pitfalls
    env = {k: v for k, v in os.environ.items() if k not in ("CONSTRUCT3_RAG", "CONSTRUCT3_COOKBOOK")}
    env.update(PYTHONIOENCODING="utf-8", CONSTRUCT3_RAG_OFFLINE="1")

    def run(script: str, *args: str) -> str:
        p = subprocess.run([sys.executable, str(scripts / script), *args], cwd=tmp_path, env=env,
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        assert p.returncode == 0, p.stdout + p.stderr
        return p.stdout

    out = run("lookup_script_api.py", "IRuntime.callFunction")
    assert out.startswith("IRuntime.callFunction   lookup_script_api.py IRuntime.callFunction\n"), out
    out = run("search_guides.py", "wait", "platformer")
    assert out.startswith("note: pitfalls not searched: no Construct3-Cookbook clone") and "git clone" in out, out
    assert not re.findall(r"^(.+\.md):\d+$", out, re.M), out
    assert "\n  https://editor.construct.net/#open=3d-platformer\n" in out and "beside Construct3-RAG" not in out, out
    # The pointers come from a Cookbook clone, which no copy of the plugin holds: an entry prints none
    out = run("lookup_ace.py", "Tween", "tween-one-property")
    assert "tween-one-property" in out and "  pitfalls: " not in out, out
    out = run("lookup_ace.py", "Fade", "start", "fade")
    assert "  prefer: " not in out, out


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
