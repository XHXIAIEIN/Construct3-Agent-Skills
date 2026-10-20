#!/usr/bin/env python3
"""Refresh plugin/data/ from the data of Construct3-RAG and set the plugin's version.

    python scripts/build_plugin.py            write plugin/data/ and the version
    python scripts/build_plugin.py --check    fail when plugin/data/ or the version differs from a fresh build
    python scripts/build_plugin.py --rag F    read data/ from the Construct3-RAG clone F

plugin/ is the Claude Code plugin and holds its sources: the skill under
skills/construct3-agent-plugin/, the rows of the / menu under skills/<name>/,
the prompts, the manifest, the README, the icon and the agents. Only its
data/ is built, from the Construct3-RAG clone beside this repository, or from
--rag or CONSTRUCT3_RAG_DATA, which must be a Git clone, because the build
takes the tracked files. Why: docs/decisions/plugin-repository.md.

The folder stays under the limits of Claude's plugin directory: 512 files or
fewer, every file other than an image or a font under 256 KiB, and the folder
under 7 MB in all. The schemas, the guides and the empty project are copied
to the same paths under data/; a schema is written with an indent of one
space, which keeps the folder under its size limit. The TypeScript
definitions, the examples and the index of their ACEs are written as bundles,
which skills/construct3-agent-plugin/scripts/c3project.py reads with
data_texts; the language packs keep the parts check_project.py reads. They
also keep the name, properties and debugger texts of every plugin and
behavior, because the keys of a preview's inspector values point into them.
Why: docs/decisions/plugin-folder.md.

skills/<name>/SKILL.md is one thin skill per user-facing script, so that the
plugin's / menu lists the scripts; each runs its script and is never loaded
into the model's context on its own. The build fails when a script and the
menu disagree. Why: docs/decisions/plugin-script-menu.md.

The build also sets the version in .claude-plugin/plugin.json. The published
plugin is the one at the commit that HEAD shares with origin/main, or at HEAD
without that ref. During a merge, it is the one at the commit that the merge
commit will share with origin/main. If the plugin's files other than
plugin.json equal the published ones, the build keeps the published version;
otherwise it writes the published version with its patch raised by one. The
version committed in plugin.json is the floor, raised by hand for a minor or
major release. The build reads Git locally and never fetches. Why:
docs/decisions/plugin-tracks-commits.md.

exit codes: 0 built or equal, 1 plugin/ differs, breaks a limit or disagrees with the menu, 2 no Construct3-RAG clone
"""
import argparse
import contextlib
import filecmp
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin"
SKILL = "plugin/skills/construct3-agent-plugin"
sys.path.insert(0, str(ROOT / SKILL / "scripts"))

from c3project import siblings_folder  # noqa: E402

# The Construct3-RAG clone whose data/ the build takes: beside this repository, as the other clones are
RAG = Path(os.environ.get("CONSTRUCT3_RAG_DATA") or siblings_folder(ROOT) / "Construct3-RAG")
RAG_URL = "https://github.com/XHXIAIEIN/Construct3-RAG"
DATA = "data"
MANIFEST = ".claude-plugin/plugin.json"
# The scripts with no menu skill: modules the scripts import, and install.py, which copies the skill into a
# game project, a copy a plugin user does not need (docs/decisions/plugin-tracks-commits.md)
NOT_IN_MENU = frozenset({"c3project", "design_review", "game_model", "install"})

# Copied to the same path under plugin/
COPIED = ("data/c3-schemas", "data/c3-guides", "data/c3-new-project", "data/c3-ts-defs/autocomplete-data.json")
# Written as bundles: folder, the files of it to take
BUNDLED = (("data/c3-ts-defs", "*.d.ts"), ("data/c3-examples/en-US", "*.json"), ("data/c3-examples/zh-CN", "*.json"),
           ("data/c3-example-usage", "*.json"))
# The language pack keys check_project.py reads
LANG_KEYS = (("text", "ui", "bars", "properties", "project"), ("text", "ui", "bars", "timeline", "eases"))
# The texts kept for every plugin and behavior, at text.<kind>.<id>.<part>
# A preview's inspector keys point into them (references/reading-the-runtime.md, "Inspector values")
ADDON_TEXTS = ("name", "properties", "debugger")

MAX_FILES = 512
MAX_SIZE = 256 * 1024
# The directory's limit on the folder, read off its scans: 6,908,884 bytes passed, 7,107,992 did not
MAX_TOTAL = 7_000_000
BUNDLE_SIZE = 240 * 1024     # below MAX_SIZE, so that a bundle stays under it as its files grow a little
BINARIES = (".png",)     # images, copied byte for byte
SCHEMAS = "data/c3-schemas"     # copied with an indent of one space, 400 KiB less than the two of the source


def source(rel: str) -> Path:
    """The clone a repository path is read from: data/ from the Construct3-RAG clone, the rest from here."""
    return (RAG if rel.split("/", 1)[0] == DATA else ROOT) / rel


def tracked(path: str) -> list[str]:
    """The files under path that Git tracks or would track in the clone that holds it, sorted."""
    root = source(path).parents[len(PurePosixPath(path).parts) - 1]
    p = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "--", path],
                       capture_output=True, text=True, encoding="utf-8", check=True)
    return sorted({line for line in p.stdout.splitlines() if (root / line).is_file() and "__pycache__" not in line})


def locales() -> list[str]:
    """The locales of the data, from its index."""
    return json.loads(source("data/c3-schemas/_index.json").read_text(encoding="utf-8-sig"))["languages"]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def copy(src: Path, dst: Path) -> None:
    """src at dst: an image byte for byte, any other file with LF line endings, as Git stores it.
    A checkout with core.autocrlf holds CRLF files; LF keeps its build equal to plugin/."""
    data = src.read_bytes()
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data if src.name.endswith(BINARIES) else data.replace(b"\r\n", b"\n"))


def reindent(src: Path, dst: Path) -> None:
    """src at dst as the same JSON with an indent of one space, which an agent reads as it reads the source."""
    text = src.read_text(encoding="utf-8-sig")
    write(dst, json.dumps(json.loads(text), ensure_ascii=False, indent=1) + "\n")


def dump(bundle: dict[str, str]) -> str:
    """A bundle as the text of its file."""
    return json.dumps(bundle, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def bundles(folder: str, pattern: str) -> list[tuple[str, str]]:
    """The bundles of a folder, <folder>.bundle-<n>.json, each under BUNDLE_SIZE."""
    out: list[str] = []
    part: dict[str, str] = {}
    for rel in tracked(folder):
        inner = rel[len(folder) + 1:]
        if not PurePosixPath(inner).match(pattern) or "sdk" in inner.split("/"):
            continue
        text = source(rel).read_text(encoding="utf-8-sig")
        if inner.endswith(".json"):
            # The scripts parse a bundled JSON file and no agent reads it by line: without its indent it
            # takes 200 KiB less of the folder's limit
            text = json.dumps(json.loads(text), ensure_ascii=False, separators=(",", ":"))
        if part and len(dump({**part, inner: text}).encode("utf-8")) > BUNDLE_SIZE:
            out.append(dump(part))
            part = {}
        part[inner] = text
    if part:
        out.append(dump(part))
    return [(f"{folder}.bundle-{n}.json", text) for n, text in enumerate(out, 1)]


def lang_subset(locale: str) -> str:
    """The plugin's copy of a language pack, as text: the parts at LANG_KEYS, and ADDON_TEXTS of every
    plugin and behavior."""
    pack = json.loads(source(f"data/c3-lang/{locale}.json").read_text(encoding="utf-8-sig"))
    out: dict[str, dict] = {}
    for keys in LANG_KEYS:
        src, dst = pack, out
        for k in keys[:-1]:
            src, dst = src[k], dst.setdefault(k, {})
        dst[keys[-1]] = src[keys[-1]]
    for kind in ("plugins", "behaviors"):
        for addon, texts in pack["text"][kind].items():
            kept = {part: texts[part] for part in ADDON_TEXTS if part in texts} if isinstance(texts, dict) else {}
            if kept:
                out["text"].setdefault(kind, {})[addon] = kept
    return json.dumps(out, ensure_ascii=False, indent="\t", sort_keys=True) + "\n"


def menu_skills() -> dict[str, str]:
    """The thin skills of the / menu: the script's stem for each skill name, from the folders beside the skill."""
    folders = sorted({PurePosixPath(rel).parts[2] for rel in tracked("plugin/skills")
                      if rel.endswith("/SKILL.md") and PurePosixPath(rel).parts[2] != "construct3-agent-plugin"})
    return {name: name.replace("-", "_") for name in folders}


def menu_problems() -> list[str]:
    """Where the scripts and the / menu disagree: a user-facing script without a menu skill, a menu skill whose
    script does not exist, or a menu skill for a script NOT_IN_MENU leaves out."""
    scripts = {PurePosixPath(rel).stem for rel in tracked(f"{SKILL}/scripts") if rel.endswith(".py")}
    menu = menu_skills()
    out = [f"{SKILL}/scripts/{stem}.py has no plugin/skills/{stem.replace('_', '-')}/SKILL.md"
           for stem in sorted(scripts - NOT_IN_MENU - set(menu.values()))]
    out += [f"plugin/skills/{name}/SKILL.md names no script: {SKILL}/scripts/{stem}.py" for name, stem in menu.items()
            if stem not in scripts]
    out += [f"plugin/skills/{name}/SKILL.md: {stem}.py is NOT_IN_MENU" for name, stem in menu.items()
            if stem in NOT_IN_MENU]
    return out


def build(out: Path) -> None:
    """The plugin's data folder, written fresh at out."""
    for part in COPIED:
        for rel in tracked(part):
            inner = rel[len(DATA) + 1:]
            if part == SCHEMAS and rel.endswith(".json"):
                reindent(source(rel), out / inner)
            else:
                copy(source(rel), out / inner)
    for folder, pattern in BUNDLED:
        for rel, text in bundles(folder, pattern):
            write(out / rel[len(DATA) + 1:], text)
    for locale in locales():
        write(out / "c3-lang" / f"{locale}.json", lang_subset(locale))


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


def plugin_files(data: Path) -> dict[str, Path]:
    """The plugin's files with the data folder at data in place of plugin/data/, by their path in the plugin."""
    out = {rel: p for rel, p in files(PLUGIN).items() if rel.split("/", 1)[0] != DATA}
    out.update({f"{DATA}/{rel}": p for rel, p in files(data).items()})
    return out


def manifest() -> dict:
    return json.loads((PLUGIN / MANIFEST).read_text(encoding="utf-8"))


def version_for(data: Path) -> str:
    """The release version of the plugin with the data folder at data."""
    fresh = {rel: blob_id(stored(p)) for rel, p in plugin_files(data).items() if rel != MANIFEST}
    return release_version(*published(), fresh, manifest()["version"])


def set_version(version: str) -> None:
    """Write version into the plugin's manifest, keeping its other fields."""
    data = manifest()
    data["version"] = version
    write(PLUGIN / MANIFEST, json.dumps(data, ensure_ascii=False, indent="\t") + "\n")


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


def differences(built: Path, committed: Path) -> list[str]:
    a, b = files(built), files(committed) if committed.is_dir() else {}
    out = [f"missing from plugin/data/: {rel}" for rel in a if rel not in b]
    out += [f"not in a fresh build: {rel}" for rel in b if rel not in a]
    out += [f"differs: {rel}" for rel in a if rel in b and not same(a[rel], b[rel])]
    return out


def same(built: Path, committed: Path) -> bool:
    """Whether a committed file equals its build. A checkout with core.autocrlf holds
    plugin/ with CRLF text files, which Git stores as the LF the build writes."""
    if built.name.endswith(BINARIES):
        return filecmp.cmp(built, committed, shallow=False)
    return built.read_bytes() == committed.read_bytes().replace(b"\r\n", b"\n")


@contextlib.contextmanager
def fresh_build() -> Iterator[tuple[Path, str]]:
    """A fresh data folder in a temporary place, with the plugin's version; the folder goes at the end."""
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / DATA
        build(fresh)
        yield fresh, version_for(fresh)


def rebuild() -> list[str]:
    """plugin/data/ replaced by a fresh build and the version written, and what breaks the limits or the menu."""
    with fresh_build() as (fresh, version):
        if (PLUGIN / DATA).exists():
            shutil.rmtree(PLUGIN / DATA)
        shutil.copytree(fresh, PLUGIN / DATA)
        set_version(version)
    return limits(files(PLUGIN)) + menu_problems()


def check() -> list[str]:
    """How plugin/data/ and the version differ from a fresh build, and what breaks the limits or the menu."""
    with fresh_build() as (fresh, version):
        problems = limits(plugin_files(fresh)) + menu_problems() + differences(fresh, PLUGIN / DATA)
    committed = manifest()["version"]
    if committed != version:
        problems.append(f"version: {committed} in plugin.json, {version} for the plugin's files")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description="Refresh plugin/data/ from the data of Construct3-RAG and set the plugin's version.",
                                 epilog="exit codes: 0 built or equal, 1 plugin/ differs, breaks a limit or disagrees with the menu, 2 no Construct3-RAG clone")
    ap.add_argument("--check", action="store_true", help="compare plugin/data/ and the version with a fresh build, write nothing")
    ap.add_argument("--rag", metavar="FOLDER", help=f"the Construct3-RAG clone whose data/ is built in (default: {RAG})")
    args = ap.parse_args()
    if args.rag:
        globals()["RAG"] = Path(args.rag).resolve()
    if not (RAG / "data" / "c3-schemas" / "_index.json").is_file():
        print(f"no Construct3-RAG clone at {RAG}; git clone {RAG_URL} \"{RAG.as_posix()}\" puts it there, "
              "or pass --rag <clone>")
        return 2
    problems = check() if args.check else rebuild()
    for line in problems:
        print(line)
    if args.check:
        print(f"plugin/: {'differs or breaks a limit; run python scripts/build_plugin.py' if problems else 'equal to a fresh build'}")
    else:
        print(f"plugin/: built, version {manifest()['version']}, {len(files(PLUGIN))} files"
              f"{'; breaks the limits above' if problems else ''}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
