#!/usr/bin/env python3
"""Set the plugin's version and hold plugin/ to the limits of Claude's plugin directory.

    python dev/scripts/build_plugin.py            write the version
    python dev/scripts/build_plugin.py --check    fail when the version differs or plugin/ breaks a limit

plugin/ is the Claude Code plugin and holds its sources only: the skill under
skills/construct3-agent-plugin/, the manifest, the README, the icon and the
agents. It holds no data. The scripts read the data from the Construct3-RAG
clone, and print the git clone command when there is none. Why:
docs/decisions/plugin-reads-the-clones.md.

The folder stays under the limits of Claude's plugin directory: 512 files or
fewer, every file other than an image under 256 KiB, and the folder under
7 MB in all. --check also fails when plugin/data/ exists. Why:
docs/decisions/plugin-folder.md.

The build sets the version in .claude-plugin/plugin.json. The published
plugin is the one at the commit that HEAD shares with origin/main, or at HEAD
without that ref. During a merge, it is the one at the commit that the merge
commit will share with origin/main. If the plugin's files other than
plugin.json equal the published ones, the build keeps the published version;
otherwise it writes the published version with its patch raised by one. The
version committed in plugin.json is the floor, raised by hand for a minor or
major release. The build reads Git locally and never fetches. Why:
docs/decisions/plugin-tracks-commits.md.

exit codes: 0 written or equal, 1 the version differs or plugin/ breaks a limit
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugin"
MANIFEST = ".claude-plugin/plugin.json"

MAX_FILES = 512
MAX_SIZE = 256 * 1024
# The directory's limit on the folder, read off its scans: 6,908,884 bytes passed, 7,107,992 did not
MAX_TOTAL = 7_000_000
BINARIES = (".png",)     # images, compared byte for byte


def stored(p: Path) -> bytes:
    """A file's bytes as Git stores them: a text file with LF, whatever a checkout with core.autocrlf wrote."""
    data = p.read_bytes()
    return data if p.name.endswith(BINARIES) else data.replace(b"\r\n", b"\n")


def blob_id(data: bytes) -> str:
    """The id Git gives a file holding data."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def git(*args: str) -> str | None:
    """What git prints, or None when it fails."""
    p = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, encoding="utf-8")
    return p.stdout if p.returncode == 0 else None


def published() -> tuple[str | None, dict[str, str]]:
    """The version and the blob ids, by path, of the plugin at the commit that HEAD shares with
    origin/main. Without origin/main or a merge base, as in a shallow CI checkout, the commit is HEAD."""
    # During a merge, the commit the merge commit will share: git takes the merge base of the first
    # commit and a merge of the others
    merging = ["MERGE_HEAD"] if git("rev-parse", "-q", "--verify", "MERGE_HEAD") else []
    base = (git("merge-base", "origin/main", "HEAD", *merging) or "HEAD").strip()
    version = None
    for path in (f"plugin/{MANIFEST}", MANIFEST):      # the second path: the manifest in commits that predate plugin/
        text = git("show", f"{base}:{path}")
        if text and (version := json.loads(text).get("version")):
            break
    blobs: dict[str, str] = {}
    for entry in (git("ls-tree", "-r", "-z", f"{base}:plugin") or "").split("\0"):
        if entry:
            meta, path = entry.split("\t", 1)
            kind, blob = meta.split()[1:]
            if kind == "blob" and path != MANIFEST:
                blobs[path] = blob
    return version, blobs


def release_version(published_version: str | None, published_blobs: dict[str, str],
                    fresh_blobs: dict[str, str], floor: str) -> str:
    """The version of a build. It is the published version while the plugin's files equal the published
    files, and that version with its patch raised by one once they differ. It is never below the floor."""
    def numbers(version: str) -> tuple[int, ...]:
        return tuple(int(n) for n in version.split("."))

    if published_version is None:
        return floor
    version = numbers(published_version)
    if fresh_blobs != published_blobs:
        version = (*version[:-1], version[-1] + 1)
    return ".".join(map(str, max(version, numbers(floor))))


def files(folder: Path) -> dict[str, Path]:
    """The files of a folder, without the bytecode Python writes beside a script it ran."""
    return {p.relative_to(folder).as_posix(): p for p in sorted(folder.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts}


def manifest() -> dict:
    return json.loads((PLUGIN / MANIFEST).read_text(encoding="utf-8"))


def version_for() -> str:
    """The release version of the plugin's files as they stand."""
    fresh = {rel: blob_id(stored(p)) for rel, p in files(PLUGIN).items() if rel != MANIFEST}
    return release_version(*published(), fresh, manifest()["version"])


def set_version(version: str) -> None:
    """Write version into the plugin's manifest, keeping its other fields."""
    data = manifest()
    data["version"] = version
    (PLUGIN / MANIFEST).write_bytes((json.dumps(data, ensure_ascii=False, indent="\t") + "\n").encode("utf-8"))


def limits(found: dict[str, Path]) -> list[str]:
    """What breaks the directory's limits on the plugin folder, over its files by path. The sizes are
    those of the bytes Git stores, because the directory reads the repository, not a checkout that
    core.autocrlf wrote with CRLF."""
    problems = [f"{len(found)} files, more than {MAX_FILES}"] if len(found) > MAX_FILES else []
    sizes = {rel: len(stored(p)) for rel, p in found.items()}
    total = sum(sizes.values())
    if total > MAX_TOTAL:
        problems.append(f"{total:,} bytes in all, more than {MAX_TOTAL:,}")
    for rel, p in found.items():
        if rel.endswith(BINARIES):
            continue
        if sizes[rel] > MAX_SIZE:
            problems.append(f"{rel}: {sizes[rel] // 1024} KiB, more than {MAX_SIZE // 1024}")
        try:
            p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            problems.append(f"{rel}: not UTF-8 text")
    return problems


def held_data() -> list[str]:
    """plugin/data/ as a problem: the scripts read the data from the Construct3-RAG clone."""
    return ["plugin/data/: the plugin holds no data; the scripts read it from the Construct3-RAG clone, so remove "
            "the folder"] if (PLUGIN / "data").exists() else []


def main() -> int:
    ap = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description="Set the plugin's version and hold plugin/ to the limits of Claude's "
                                             "plugin directory.",
                                 epilog="exit codes: 0 written or equal, 1 the version differs or plugin/ breaks a limit")
    ap.add_argument("--check", action="store_true", help="compare the version with the plugin's files, write nothing")
    args = ap.parse_args()
    version = version_for()
    problems = held_data() + limits(files(PLUGIN))
    if args.check:
        committed = manifest()["version"]
        if committed != version:
            problems.append(f"version: {committed} in plugin.json, {version} for the plugin's files")
    else:
        set_version(version)
    for line in problems:
        print(line)
    if args.check:
        print(f"plugin/: {'differs or breaks a limit; run python dev/scripts/build_plugin.py' if problems else 'within the limits, version current'}")
    else:
        print(f"plugin/: version {manifest()['version']}, {len(files(PLUGIN))} files"
              f"{'; breaks the limits above' if problems else ''}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
