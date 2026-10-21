"""The checker's line about a clone whose plugin version is older than its upstream's,
against a bare repository on disk as the upstream. The read of the upstream's version,
an HTTPS request to GitHub in use, reads the bare repository here."""
import subprocess
from pathlib import Path

import pytest

from tests.skill_helpers import NEEDS_GIT, git, script_module

c3 = script_module("c3project")

pytestmark = NEEDS_GIT

MANIFEST = "plugin/.claude-plugin/plugin.json"
READS: list[str] = []      # the upstream reads of the current test


def set_version(clone: Path, version: str) -> None:
    (clone / MANIFEST).write_text(f'{{\n\t"name": "construct3",\n\t"version": "{version}"\n}}\n', encoding="utf-8")


@pytest.fixture
def clones(tmp_path, monkeypatch) -> tuple[Path, Path]:
    """A clone the checker reads and another one that pushes to their upstream."""
    monkeypatch.delenv("CONSTRUCT3_RAG_OFFLINE", raising=False)
    monkeypatch.setattr(c3, "VERSION_STAMPS", tmp_path / "stamps")
    upstream, mine, other = tmp_path / "upstream.git", tmp_path / "mine", tmp_path / "other"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(upstream))
    git(tmp_path, "clone", "-q", str(upstream), str(mine))
    (mine / MANIFEST).parent.mkdir(parents=True)
    set_version(mine, "1.0.0")
    (mine / "notes.txt").write_text("first\n", encoding="utf-8")
    git(mine, "add", MANIFEST, "notes.txt")
    git(mine, "commit", "-q", "-m", "first")
    git(mine, "push", "-q", "-u", "origin", "main")
    git(tmp_path, "clone", "-q", str(upstream), str(other))
    monkeypatch.setattr(c3, "manifest_url", lambda remote_url, branch, rel: f"{remote_url}|{branch}|{rel}")

    def read_version(url):
        READS.append(url)
        remote, branch, rel = url.split("|")
        p = subprocess.run(["git", "-C", remote, "show", f"{branch}:{rel}"], capture_output=True, text=True)
        return c3.json.loads(p.stdout).get("version") if p.returncode == 0 else None
    monkeypatch.setattr(c3, "read_version", read_version)
    READS.clear()
    return mine, other


def release(other: Path, version: str = "1.0.1") -> None:
    git(other, "pull", "-q")
    set_version(other, version)
    git(other, "commit", "-q", "-am", version)
    git(other, "push", "-q")


def expire(tmp_path: Path) -> None:
    for stamp in (tmp_path / "stamps").iterdir():
        stamp.touch()
        old = stamp.stat().st_mtime - c3.VERSION_EVERY - 1
        c3.os.utime(stamp, (old, old))


def test_up_to_date_says_nothing(clones):
    mine, _ = clones
    assert c3.clone_behind(mine / "plugin") is None


def test_behind_gives_the_pull_for_the_agent(clones):
    mine, other = clones
    release(other)
    line, error = c3.clone_behind(mine / "plugin")
    assert error and "holds version 1.0.0 of the plugin, and origin/main holds 1.0.1" in line
    assert f'git -C "{mine}" pull --ff-only, then run this check again' in line


def test_the_printed_pull_brings_the_clone_level(clones):
    mine, other = clones
    release(other)
    line, _ = c3.clone_behind(mine / "plugin")
    command = line.split("Run ", 1)[1].split(", then")[0]
    assert subprocess.run(command, shell=True, capture_output=True, timeout=60).returncode == 0, command
    assert c3.clone_behind(mine / "plugin") is None


def test_behind_with_a_copy_of_the_skill_gives_its_refresh_too(clones, monkeypatch):
    """One line takes the agent through both steps, instead of a second check finding the copy stale."""
    mine, other = clones
    release(other)
    monkeypatch.setattr(c3, "refresh_command", lambda rag: "python install.py --into skills")
    line, error = c3.clone_behind(mine / "plugin")
    assert error and "pull --ff-only, then python install.py --into skills, then run this check again" in line


@pytest.mark.parametrize("own", ["commit", "change"])
def test_behind_with_the_users_own_work_is_the_users(clones, own):
    """A pull could merge into or refuse over the user's work: the line asks for the user, not the pull."""
    mine, other = clones
    release(other)
    if own == "commit":
        git(mine, "commit", "-q", "--allow-empty", "-m", "mine")
    else:
        (mine / "notes.txt").write_text("edited\n", encoding="utf-8")
    line, error = c3.clone_behind(mine / "plugin")
    assert not error and "holds version 1.0.0" in line and "pull" not in line
    assert ("1 commit of its own" if own == "commit" else "uncommitted changes of its own") in line
    assert "tell the user" in line


def test_read_once_a_period_and_a_later_check_warns(clones, tmp_path):
    """A read in the period is not repeated. The line from an earlier read is a warning, so a
    pull that failed offline does not hold every check of the period."""
    mine, other = clones
    assert c3.clone_behind(mine / "plugin") is None
    release(other)
    assert c3.clone_behind(mine / "plugin") is None
    assert len(READS) == 1
    expire(tmp_path)
    line, error = c3.clone_behind(mine / "plugin")
    assert error and len(READS) == 2
    assert c3.clone_behind(mine / "plugin") == (line, False)
    assert len(READS) == 2


def test_a_failed_read_says_nothing_and_waits_a_period(clones, monkeypatch):
    mine, other = clones
    release(other)
    reads = []
    monkeypatch.setattr(c3, "read_version", lambda url: reads.append(url))
    assert c3.clone_behind(mine / "plugin") is None
    assert c3.clone_behind(mine / "plugin") is None
    assert len(reads) == 1


def test_offline_or_untracked_says_nothing(clones, monkeypatch):
    mine, other = clones
    release(other)
    monkeypatch.setenv("CONSTRUCT3_RAG_OFFLINE", "1")
    assert c3.clone_behind(mine / "plugin") is None
    assert not READS
    for value in ("0", "", "true"):         # only 1 turns the check off
        monkeypatch.setenv("CONSTRUCT3_RAG_OFFLINE", value)
        assert c3.clone_behind(mine / "plugin") is not None, value
    monkeypatch.delenv("CONSTRUCT3_RAG_OFFLINE")
    git(mine, "switch", "-q", "--detach")  # no upstream
    assert c3.clone_behind(mine / "plugin") is None
    assert c3.clone_behind(mine.parent) is None  # not a clone


@pytest.mark.parametrize("remote", [
    "git@github.com:XHXIAIEIN/Construct3-Agent-Skills.git",
    "https://github.com/XHXIAIEIN/Construct3-Agent-Skills.git",
    "https://github.com/XHXIAIEIN/Construct3-Agent-Skills",
    "ssh://git@github.com/XHXIAIEIN/Construct3-Agent-Skills.git/",
])
def test_the_manifest_url_is_the_public_raw_file(remote):
    assert c3.manifest_url(remote, "main", MANIFEST) == \
        "https://raw.githubusercontent.com/XHXIAIEIN/Construct3-Agent-Skills/main/plugin/.claude-plugin/plugin.json"


def test_a_remote_off_github_has_no_manifest_url():
    assert c3.manifest_url("https://gitlab.com/someone/repo.git", "main", MANIFEST) is None
    assert c3.manifest_url("D:/clones/upstream.git", "main", MANIFEST) is None
