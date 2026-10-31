"""setup.py, the first-use check: Python, git and every clone the skill reads, each missing one printed at once
with its size and the command that clones it into the home, and nothing downloaded
(docs/decisions/clones-home.md). Also the clone without zh-CN that its command makes, which the checker's pull
keeps without zh-CN."""
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from tests.skill_helpers import NEEDS_GIT, PLUGIN, git, script_module

c3 = script_module("c3project")
setup = script_module("setup")
RAG_URL = "https://github.com/XHXIAIEIN/Construct3-RAG"


def installed(tmp_path: Path) -> Path:
    """The scripts of a copy of the plugin in a version folder of Claude Code's plugin cache, with no clone above it."""
    plugin = tmp_path / "cache" / "construct3" / "1.2.0"
    if not plugin.is_dir():
        shutil.copytree(PLUGIN, plugin, ignore=shutil.ignore_patterns("__pycache__"))
    return plugin / "skills" / "construct3-agent-plugin" / "scripts"


def run_setup(tmp_path: Path, *args: str) -> tuple[int, str]:
    """setup.py of an installed copy run from tmp_path, with tmp_path/home as the home and no clone named."""
    env = {k: v for k, v in os.environ.items() if k not in ("CONSTRUCT3_RAG", "CONSTRUCT3_COOKBOOK")}
    env.update(PYTHONIOENCODING="utf-8", CONSTRUCT3_HOME=str(tmp_path / "home"))
    p = subprocess.run([sys.executable, str(installed(tmp_path) / "setup.py"), *args], cwd=tmp_path, env=env,
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    return p.returncode, p.stdout + p.stderr


def make(folder: Path, marker: str) -> None:
    """A folder that counts as a clone: it holds the clone's marker file or folder."""
    (folder / marker).parent.mkdir(parents=True, exist_ok=True)
    if marker.endswith(".json"):
        (folder / marker).write_text('{"languages": ["en-US", "zh-CN"]}', encoding="utf-8")
    elif marker.endswith(".md"):
        (folder / marker).write_text("# Pitfalls\n", encoding="utf-8")
    else:
        (folder / marker).mkdir()


def test_an_empty_home_lists_every_clone_at_once_with_its_size_and_command(tmp_path):
    """Nothing is cloned: every missing clone is listed, the required ones first, each with its size; the agent
    asks first whether the user has one elsewhere, and the commands clone into the home. Without --locales
    Construct3-RAG is the clone without zh-CN."""
    home = (tmp_path / "home").as_posix()
    code, out = run_setup(tmp_path)
    assert code == 1, out
    lines = out.splitlines()
    assert lines[0].startswith("ok: Python 3.") and lines[1].startswith("ok: git "), out
    assert [line.split(" (")[0] for line in lines[2:7]] == [
        "missing: Construct3-RAG", "missing: Construct3-Cookbook", "missing: Construct3-Manual",
        "missing: Construct-Example-Projects", "missing: Construct-Addon-SDK"], out
    assert "(required, about 1 MB)" in lines[3] and "(optional, about 864 MB)" in lines[5], out
    assert "ask the user whether they already have any of these clones elsewhere" in out, out
    assert "  Construct3-RAG: set CONSTRUCT3_RAG to its folder\n" in out, out
    assert "  Construct3-Cookbook: set CONSTRUCT3_COOKBOOK to its folder\n" in out, out
    assert f"set CONSTRUCT3_HOME to the folder that holds them all, instead of {home}\n" in out, out
    assert (f'  git clone --depth 1 --filter=blob:none --no-checkout {RAG_URL} "{home}/Construct3-RAG"\n'
            f'  git -C "{home}/Construct3-RAG" sparse-checkout set --no-cone \'/*\' \'!*zh-CN*\'\n'
            f'  git -C "{home}/Construct3-RAG" checkout\n') in out, out
    assert f'  git clone --depth 1 https://github.com/XHXIAIEIN/Construct3-Manual "{home}/Construct3-Manual"\n' in out
    required, optional = out.split("These commands clone the required ones:")[1].split("These clone the optional")
    assert "Construct-Example-Projects" not in required and "Construct-Example-Projects" in optional, out
    assert lines[-1] == ("missing: 3 required clones; give the user every line above in one message, run the "
                         "commands once the user agrees, then run this again"), out
    assert not (tmp_path / "home").exists()


def test_locales_zh_cn_makes_construct3_rag_a_full_clone(tmp_path):
    code, out = run_setup(tmp_path, "--locales", "zh-CN")
    assert code == 1 and f'  git clone --depth 1 {RAG_URL} "{(tmp_path / "home").as_posix()}/Construct3-RAG"\n' in out
    assert "sparse-checkout" not in out, out
    code, out = run_setup(tmp_path, "--locales", "ja-JP")
    assert code == 2 and out.strip() == "--locales takes zh-CN, and en-US is always kept; not ja-JP", out


def test_the_required_clones_in_the_home_pass_and_a_left_out_locale_gives_its_command(tmp_path):
    home = tmp_path / "home"
    for clone in setup.CLONES[:3]:
        make(home / clone.name, clone.marker)
    (home / "Construct3-RAG" / "data" / "c3-schemas" / "en-US").mkdir()
    code, out = run_setup(tmp_path)
    assert code == 0, out
    assert f"ok: Construct3-RAG at {(home / 'Construct3-RAG').as_posix()} (en-US)\n" in out, out
    assert "These commands clone the required ones" not in out and "Construct-Addon-SDK" in out, out
    assert out.splitlines()[-1] == "ok: everything required is in place; the optional clones above are the user's choice"
    code, out = run_setup(tmp_path, "--locales", "zh-CN")
    assert code == 1 and f'git -C "{(home / "Construct3-RAG").as_posix()}" sparse-checkout disable' in out, out
    assert out.splitlines()[-1] == "missing: the zh-CN data; run the command above once the user agrees", out
    for clone in setup.CLONES[3:]:
        make(home / clone.name, clone.marker)
    code, out = run_setup(tmp_path)
    assert code == 0 and out.splitlines()[-1] == "ok: everything the skill reads is in place", out


def test_a_clone_in_the_plugin_cache_is_found_and_moved_out(tmp_path):
    """An install made before the home put Construct3-RAG beside the plugin's version folders: the scripts still
    read it, and setup.py says to move it, since Claude Code cleans its cache."""
    cache = tmp_path / "cache" / "construct3"
    make(cache / "Construct3-RAG", "data/c3-schemas/_index.json")
    make(cache / "Construct3-RAG", "data/c3-schemas/en-US")
    code, out = run_setup(tmp_path)
    assert (f"ok: Construct3-RAG at {(cache / 'Construct3-RAG').as_posix()} (en-US); it lies in Claude Code's plugin "
            f"cache, which Claude Code may clean, so move the folder to "
            f"{(tmp_path / 'home' / 'Construct3-RAG').as_posix()}\n") in out, out
    assert f'"{(tmp_path / "home").as_posix()}/Construct3-Manual"' in out, out


def upstream(folder: Path) -> Path:
    """A repository laid out like Construct3-RAG, with en-US and zh-CN data, that serves a partial clone."""
    for locale in ("en-US", "zh-CN"):
        (folder / "data" / "c3-schemas" / locale).mkdir(parents=True)
        (folder / "data" / "c3-schemas" / locale / "system.json").write_text("1", encoding="utf-8")
    (folder / "data" / "c3-lang").mkdir()
    (folder / "data" / "c3-lang" / "zh-CN.json").write_text("{}", encoding="utf-8")
    (folder / "data" / "c3-schemas" / "_index.json").write_text('{"languages": ["en-US", "zh-CN"]}', encoding="utf-8")
    git(folder, "init", "-q", "-b", "main")
    git(folder, "config", "uploadpack.allowFilter", "true")
    git(folder, "add", ".")
    git(folder, "commit", "-q", "-m", "data")
    return folder


@NEEDS_GIT
def test_the_clone_without_zh_cn_keeps_it_out_through_the_checkers_pull(tmp_path, monkeypatch):
    """setup.py's commands make a clone with no zh-CN file. When the upstream adds a commit, the checker pulls
    it, fast-forward only, and the sparse checkout keeps zh-CN out while the English data moves on."""
    source = upstream(tmp_path / "upstream")
    clone = tmp_path / "home" / "Construct3-RAG"
    rag = next(c for c in setup.CLONES if c.name == "Construct3-RAG")
    monkeypatch.setattr(rag, "url", source.as_uri())
    for command in setup.clone_commands(rag, clone, []):
        p = subprocess.run(shlex.split(command), capture_output=True, text=True, timeout=60)
        assert p.returncode == 0, (command, p.stderr)
    assert c3.checked_out_locales(clone) == ["en-US"] and not (clone / "data" / "c3-lang" / "zh-CN.json").exists()

    (source / "data" / "c3-schemas" / "en-US" / "system.json").write_text("2", encoding="utf-8")
    (source / "data" / "c3-schemas" / "zh-CN" / "system.json").write_text("2", encoding="utf-8")
    (source / "data" / "c3-schemas" / "zh-CN" / "sprite.json").write_text("2", encoding="utf-8")
    git(source, "commit", "-q", "-am", "refresh")
    git(source, "add", ".")
    git(source, "commit", "-q", "-m", "sprite")
    newest = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    monkeypatch.delenv("CONSTRUCT3_RAG_OFFLINE", raising=False)
    monkeypatch.setattr(c3, "commit_url", lambda remote, branch: "https://api.github.com/repos/x/y/commits/main")
    monkeypatch.setattr(c3, "upstream_value", lambda folder, url, read: (newest, True))
    note, level = c3.rag_behind(clone)
    assert level == "note" and "so it was pulled from" in note, note
    assert (clone / "data" / "c3-schemas" / "en-US" / "system.json").read_text(encoding="utf-8") == "2"
    zh = [f for f in clone.rglob("*zh-CN*") if ".git" not in f.parts]
    assert c3.checked_out_locales(clone) == ["en-US"] and not zh, zh
