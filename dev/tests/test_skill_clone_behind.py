"""The checker's lines about a clone whose plugin version is older than its upstream's and about a
data clone, the Cookbook here, that lacks its upstream's newest commit and is pulled, against a bare
repository on disk as the upstream. Construct3-RAG and the examples go through the same commits_behind. The read of the upstream's version or commit, an HTTPS request to GitHub in use, reads the
bare repository here."""
import subprocess
from pathlib import Path

import pytest

from tests.skill_helpers import NEEDS_GIT, git, script_module

c3 = script_module("c3project")

pytestmark = NEEDS_GIT

MANIFEST = "plugin/.claude-plugin/plugin.json"
READS: list[str] = []      # the upstream reads of the current test
SENT: list[str] = []       # the ETag each of them sent, "" for a plain read


def answer(value: str | None, etag: str) -> tuple[str | None, str] | None:
    """What a read of the stand-in upstream gives: its ETag is the value's, and a read that sends
    the ETag of the value now gets 304, no value."""
    SENT.append(etag)
    if not value:
        return None
    return (None if etag == f'"{value}"' else value), f'"{value}"'


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

    def read_version(url, etag=""):
        READS.append(url)
        remote, branch, rel = url.split("|")
        p = subprocess.run(["git", "-C", remote, "show", f"{branch}:{rel}"], capture_output=True, text=True)
        return answer(c3.json.loads(p.stdout).get("version") if p.returncode == 0 else None, etag)
    monkeypatch.setattr(c3, "read_version", read_version)
    READS.clear()
    SENT.clear()
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


def test_a_later_read_asks_only_whether_the_upstream_changed(clones, tmp_path):
    """The read after a period sends the ETag of the last one. A 304 keeps the last version, and
    the line is an error again, since the upstream was asked in this run."""
    mine, other = clones
    release(other)
    line, error = c3.clone_behind(mine / "plugin")
    expire(tmp_path)
    assert c3.clone_behind(mine / "plugin") == (line, True)
    assert SENT == ["", '"1.0.1"']
    release(other, "1.0.2")
    expire(tmp_path)
    assert "holds 1.0.2" in c3.clone_behind(mine / "plugin")[0]
    assert SENT[-1] == '"1.0.1"'


def test_a_stamp_without_an_etag_is_read_plainly(clones, tmp_path):
    """A stamp written before the ETag was kept holds the value alone; its next read is a plain one."""
    mine, other = clones
    release(other)
    (tmp_path / "stamps").mkdir()
    (tmp_path / "stamps" / c3.path_key(mine)).write_text("1.0.1", encoding="utf-8")
    assert c3.clone_behind(mine / "plugin")[1] is False
    expire(tmp_path)
    assert c3.clone_behind(mine / "plugin")[1] is True
    assert SENT == [""]


def test_a_failed_read_says_nothing_and_waits_a_period(clones, monkeypatch):
    mine, other = clones
    release(other)
    reads = []
    monkeypatch.setattr(c3, "read_version", lambda url, etag="": reads.append(url))
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


PITFALLS = "guides/pitfalls.md"


@pytest.fixture
def cookbooks(tmp_path, monkeypatch) -> tuple[Path, Path, Path]:
    """A Cookbook clone the checker reads, another one that pushes pitfalls to their upstream, and the upstream."""
    monkeypatch.delenv("CONSTRUCT3_RAG_OFFLINE", raising=False)
    monkeypatch.setattr(c3, "VERSION_STAMPS", tmp_path / "stamps")
    upstream, mine, other = tmp_path / "upstream.git", tmp_path / "Construct3-Cookbook", tmp_path / "other"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(upstream))
    git(tmp_path, "clone", "-q", str(upstream), str(mine))
    (mine / PITFALLS).parent.mkdir(parents=True)
    (mine / PITFALLS).write_text("# Pitfalls\n", encoding="utf-8")
    git(mine, "add", PITFALLS)
    git(mine, "commit", "-q", "-m", "first")
    git(mine, "push", "-q", "-u", "origin", "main")
    git(tmp_path, "clone", "-q", str(upstream), str(other))
    monkeypatch.setattr(c3, "commit_url", lambda remote_url, branch: f"{upstream}|{branch}")  # any spelling of the remote

    def read_commit(url, etag=""):
        READS.append(url)
        remote, branch = url.split("|")
        p = subprocess.run(["git", "-C", remote, "rev-parse", branch], capture_output=True, text=True)
        return answer(p.stdout.strip() if p.returncode == 0 else None, etag)
    monkeypatch.setattr(c3, "read_commit", read_commit)
    READS.clear()
    SENT.clear()
    return mine, other, upstream


def add_pitfall(other: Path) -> None:
    git(other, "pull", "-q")
    with (other / PITFALLS).open("a", encoding="utf-8") as f:
        f.write("- a new pitfall\n")
    git(other, "commit", "-q", "-am", "pitfall")
    git(other, "push", "-q")


def test_a_current_cookbook_says_nothing(cookbooks):
    mine, _, _ = cookbooks
    assert c3.cookbook_behind(mine) is None
    assert len(READS) == 1


def test_a_cookbook_behind_is_pulled(cookbooks):
    """A data clone with no work of its own is pulled by the check, so one clone stays current."""
    mine, other, _ = cookbooks
    before = c3.git_out(mine, "rev-parse", "--short", "HEAD")
    add_pitfall(other)
    line, level = c3.cookbook_behind(mine)
    after = c3.git_out(mine, "rev-parse", "--short", "HEAD")
    assert level == "note" and after != before, line
    assert line == (f"Construct3-Cookbook at {mine} lacks the newer guides of origin/main, so it was pulled "
                    f"from {before} to {after}")
    assert "a new pitfall" in (mine / PITFALLS).read_text(encoding="utf-8")
    assert c3.cookbook_behind(mine) is None


def unreachable(clone: Path, tmp_path: Path) -> None:
    """The clone's remote gone, so that its pull fails while the read of the upstream still answers."""
    git(clone, "remote", "set-url", "origin", str(tmp_path / "gone.git"))


def test_a_cookbook_whose_pull_fails_gives_the_pull_for_the_agent(cookbooks, tmp_path):
    mine, other, _ = cookbooks
    add_pitfall(other)
    unreachable(mine, tmp_path)
    line, level = c3.cookbook_behind(mine)
    assert level == "error" and f"Construct3-Cookbook at {mine} lacks the newer guides of origin/main" in line
    assert line.endswith(f'Run git -C "{mine}" pull --ff-only, then run this check again')


def test_a_shallow_cookbook_behind_and_current(cookbooks, tmp_path):
    """A --depth 1 clone, as the printed clone command makes, lacks the history; the new commit is still not in it."""
    _, other, upstream = cookbooks
    shallow = tmp_path / "shallow"
    git(tmp_path, "clone", "-q", "--depth", "1", upstream.as_uri(), str(shallow))
    assert c3.cookbook_behind(shallow) is None
    add_pitfall(other)
    expire(tmp_path)
    line, level = c3.cookbook_behind(shallow)
    assert level == "note" and "lacks the newer guides" in line and "was pulled" in line, line
    assert c3.cookbook_behind(shallow) is None


@pytest.mark.parametrize("own", ["commit", "change"])
def test_a_cookbook_behind_with_the_users_own_work_is_the_users(cookbooks, own):
    mine, other, _ = cookbooks
    add_pitfall(other)
    if own == "commit":
        git(mine, "commit", "-q", "--allow-empty", "-m", "mine")
    else:
        (mine / PITFALLS).write_text("# Mine\n", encoding="utf-8")
    head = c3.git_out(mine, "rev-parse", "HEAD")
    line, level = c3.cookbook_behind(mine)
    assert level == "warning" and "lacks the newer guides" in line and "pull" not in line
    assert c3.git_out(mine, "rev-parse", "HEAD") == head
    assert ("1 commit of its own" if own == "commit" else "uncommitted changes of its own") in line
    assert "tell the user" in line


def test_a_cookbook_read_once_a_period_and_a_later_check_warns(cookbooks, tmp_path):
    """A pull that failed after a read of this run is an error; from the period's earlier read, a warning."""
    mine, other, _ = cookbooks
    assert c3.cookbook_behind(mine) is None
    add_pitfall(other)
    unreachable(mine, tmp_path)
    assert c3.cookbook_behind(mine) is None
    assert len(READS) == 1
    expire(tmp_path)
    line, level = c3.cookbook_behind(mine)
    assert level == "error" and len(READS) == 2
    assert c3.cookbook_behind(mine) == (line, "warning")
    assert len(READS) == 2


def test_a_failed_cookbook_read_says_nothing_and_waits_a_period(cookbooks, monkeypatch):
    mine, other, _ = cookbooks
    add_pitfall(other)
    reads = []
    monkeypatch.setattr(c3, "read_commit", lambda url, etag="": reads.append(url))
    assert c3.cookbook_behind(mine) is None
    assert c3.cookbook_behind(mine) is None
    assert len(reads) == 1


def test_no_cookbook_offline_or_untracked_says_nothing(cookbooks, monkeypatch):
    mine, other, _ = cookbooks
    add_pitfall(other)
    assert c3.cookbook_behind(None) is None
    monkeypatch.setenv("CONSTRUCT3_RAG_OFFLINE", "1")
    assert c3.cookbook_behind(mine) is None
    assert not READS
    monkeypatch.delenv("CONSTRUCT3_RAG_OFFLINE")
    git(mine, "switch", "-q", "--detach")
    assert c3.cookbook_behind(mine) is None
    assert c3.cookbook_behind(mine.parent) is None
    assert not READS


def test_the_examples_beside_construct3_rag_are_pulled(cookbooks, tmp_path):
    """The examples clone is compared and pulled as the other data clones, when it lies beside Construct3-RAG."""
    mine, other, _ = cookbooks
    examples = tmp_path / c3.EXAMPLES_CLONE
    mine.rename(examples)
    rag = tmp_path / c3.RAG_CLONE
    rag.mkdir()
    assert c3.examples_behind(rag) is None
    add_pitfall(other)
    expire(tmp_path)
    line, level = c3.examples_behind(rag)
    assert level == "note" and line.startswith(f"{c3.EXAMPLES_CLONE} at {examples} lacks the newer examples"), line
    assert c3.examples_behind(tmp_path / "elsewhere" / c3.RAG_CLONE) is None


def data_clone(tmp_path: Path, version: str | None) -> Path:
    rag = tmp_path / c3.RAG_CLONE
    (rag / "data" / "c3-schemas").mkdir(parents=True)
    (rag / "data" / "c3-schemas" / "_index.json").write_text(
        "{}" if version is None else f'{{"version": "{version}"}}', encoding="utf-8")
    return rag


@pytest.mark.parametrize("version, old", [("r400", True), ("r506.2", True), (c3.RAG_DATA_FLOOR, False),
                                          ("r507", False), ("r1000.1", False), (None, False)])
def test_data_older_than_the_floor_fails(tmp_path, version, old):
    rag = data_clone(tmp_path, version)
    line = c3.data_too_old(rag)
    assert bool(line) == old, line
    if old:
        assert line == (f"Construct3-RAG at {rag} holds the data of Construct {version}, and the scripts expect "
                        f"{c3.RAG_DATA_FLOOR} or later, so some ACEs and checks are missing. Run git -C \"{rag}\" "
                        f"pull --ff-only, then run this check again")


def test_the_construct3_rag_clone_beside_this_one_meets_the_floor():
    """The floor is the data the tests run on, or older: raise it only with a refresh that holds it."""
    from tests.skill_helpers import RAG
    assert c3.release_key(c3.data_version(RAG)) >= c3.release_key(c3.RAG_DATA_FLOOR)
    assert c3.data_too_old(RAG) is None


def test_the_commit_url_is_the_public_api():
    assert c3.commit_url("git@github.com:XHXIAIEIN/Construct3-Cookbook.git", "main") ==         "https://api.github.com/repos/XHXIAIEIN/Construct3-Cookbook/commits/main"
    assert c3.commit_url("https://gitlab.com/someone/repo.git", "main") is None


@pytest.fixture
def server():
    """A local HTTP server that answers like GitHub: the body with its ETag, or 304 when the request
    sends that ETag. Its body is set per test."""
    import http.server
    import threading

    class Handler(http.server.BaseHTTPRequestHandler):
        body = b""
        accepts: list[str] = []

        def do_GET(self):
            etag = f'W/"{len(self.body)}-{hash(self.body) & 0xffff:x}"'
            Handler.accepts.append(self.headers.get("Accept", ""))
            if self.headers.get("If-None-Match") == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("ETag", etag)
            self.send_header("Content-Length", str(len(self.body)))
            self.end_headers()
            self.wfile.write(self.body)

        def log_message(self, *args):
            pass

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield Handler, f"http://127.0.0.1:{httpd.server_address[1]}/x"
    httpd.shutdown()


def test_the_version_read_is_conditional_over_http(server):
    handler, url = server
    handler.body = b'{\n\t"name": "construct3",\n\t"version": "1.0.1"\n}\n'
    version, etag = c3.read_version(url)
    assert version == "1.0.1" and etag
    assert c3.read_version(url, etag) == (None, etag)
    handler.body = b'{"version": "1.0.2"}'
    assert c3.read_version(url, etag)[0] == "1.0.2"


def test_the_commit_read_is_conditional_over_http(server):
    handler, url = server
    handler.body = b"a" * 40
    sha, etag = c3.read_commit(url)
    assert sha == "a" * 40 and handler.accepts[-1] == "application/vnd.github.sha"
    assert c3.read_commit(url, etag) == (None, etag)
    handler.body = b"not a commit"
    assert c3.read_commit(url) is None


def test_a_refused_read_fails():
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    assert c3.read_upstream(f"http://127.0.0.1:{port}/x") is None
