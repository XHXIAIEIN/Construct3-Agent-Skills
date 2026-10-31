"""Check what the skill needs before its first use, and print every clone that is missing at once.

    python scripts/setup.py                    # English data: the Construct3-RAG clone without zh-CN
    python scripts/setup.py --locales zh-CN    # ... and the Chinese data as well

Checks Python 3.10 or later, git, and the clones the scripts and the agent read: Construct3-RAG,
Construct3-Cookbook and Construct3-Manual are required; Construct-Example-Projects and
Construct-Addon-SDK are optional. Each missing clone gets its size and the command that clones it into
the home, ~/Construct3 unless CONSTRUCT3_HOME names another folder. It downloads nothing itself: the agent
gives the user the list, and runs the commands once the user agrees (docs/decisions/clones-home.md).
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PYTHON = (3, 10)
SPARSE_GIT = (2, 35)        # git sparse-checkout set --no-cone
RAG = "Construct3-RAG"
ENGLISH = "en-US"           # always checked out: every script reads --locale en-US by default


class Clone:
    """A repository the skill reads: its folder name, its origin, whether the skill needs it, its size checked
    out, what it holds, the file that marks a clone of it, and the variable that names one elsewhere."""

    def __init__(self, name, url, required, size, holds, marker, variable=""):
        self.name, self.url, self.required, self.size = name, url, required, size
        self.holds, self.marker, self.variable = holds, marker, variable


CLONES = [
    Clone(RAG, "https://github.com/XHXIAIEIN/Construct3-RAG", True, "about 6 MB, 10 MB with zh-CN",
          "the schemas, editor texts, example index and empty project the scripts read",
          "data/c3-schemas/_index.json", "CONSTRUCT3_RAG"),
    Clone("Construct3-Cookbook", "https://github.com/XHXIAIEIN/Construct3-Cookbook", True, "about 1 MB",
          "the event sheet design guides and pitfalls", "guides/pitfalls.md", "CONSTRUCT3_COOKBOOK"),
    Clone("Construct3-Manual", "https://github.com/XHXIAIEIN/Construct3-Manual", True, "about 5 MB",
          "the Construct 3 manual, which every [manual: ...] source of the guides names", "Construct3-Manual"),
    Clone("Construct-Example-Projects", "https://github.com/Scirra/Construct-Example-Projects", False,
          "about 864 MB", "the official example projects, which print_sheet.py prints as events",
          "example-projects"),
    Clone("Construct-Addon-SDK", "https://github.com/Scirra/Construct-Addon-SDK", False, "about 1 MB",
          "the samples for writing a plugin, behavior or effect", "plugin-sdk"),
]
BY_NAME = {c.name: c for c in CLONES}


def quoted(path: Path) -> str:
    return f'"{path.as_posix()}"'


def clone_commands(clone: Clone, into: Path, locales: list[str]) -> list[str]:
    """The commands that clone one repository into the folder into. Construct3-RAG leaves out every language
    but en-US and those in locales, so that an English user's clone has no Chinese data: a partial clone that
    fetches the files it checks out, then a sparse checkout without them. Without a language to leave out it
    is a plain shallow clone, like the others."""
    left_out = [] if clone.name != RAG or "zh-CN" in locales else ["zh-CN"]
    if not left_out:
        return [f"git clone --depth 1 {clone.url} {quoted(into)}"]
    patterns = " ".join(["'/*'", *(f"'!*{lang}*'" for lang in left_out)])
    return [f"git clone --depth 1 --filter=blob:none --no-checkout {clone.url} {quoted(into)}",
            f"git -C {quoted(into)} sparse-checkout set --no-cone {patterns}",
            f"git -C {quoted(into)} checkout"]


def git_version() -> tuple[int, ...] | None:
    if not shutil.which("git"):
        return None
    try:
        out = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    numbers = out.split()[2].split(".") if len(out.split()) > 2 else []
    return tuple(int(n) for n in numbers[:3] if n.isdigit()) or None


def found_clones(c3, root: Path | None) -> dict[str, tuple[Path | None, Path, str]]:
    """Each clone as (the folder where it is or None, where it goes when missing, a note), found as the scripts
    find it. Construct3-Manual and the optional clones lie where a line of the project's instruction file names
    them, beside Construct3-RAG, or in the home. A missing clone goes into the home, or beside a Construct3-RAG
    that lies elsewhere. A clone in Claude Code's plugin cache, where installs made before the home put them,
    gets a note to move it out."""
    rag = c3.locate_rag(root, None)[0]
    home = c3.clones_home()
    cache = [p.parent for source, p in c3.clone_places(RAG, root) if source == "beside the plugin cache"]
    beside = c3.siblings_folder(rag) if rag and [c3.siblings_folder(rag)] != cache else home
    found = {RAG: (rag, home), "Construct3-Cookbook": (c3.locate_cookbook(rag, root)[0], home)}
    for clone in CLONES[2:]:
        places = [Path(c) for _, c in c3.instruction_lines(root, clone.name) if c]
        places += [c3.siblings_folder(rag) / clone.name] if rag else []
        found[clone.name] = (next((p for p in [*places, home / clone.name] if (p / clone.marker).exists()), None),
                             beside)
    out = {}
    for name, (at, into) in found.items():
        note = (f"; it lies in Claude Code's plugin cache, which Claude Code may clean, so move the folder to "
                f"{(home / name).as_posix()}" if at and [at.parent] == cache else "")
        out[name] = (at, into / name, note)
    return out


def report(c3, root: Path | None, locales: list[str], git: tuple[int, ...] | None) -> tuple[list[str], bool]:
    """The lines setup.py prints, and whether every required clone is in place."""
    lines = []
    home = c3.clones_home()
    found = found_clones(c3, root)
    missing = [c for c in CLONES if found[c.name][0] is None]
    for clone in CLONES:
        at, _, note = found[clone.name]
        kind = "required" if clone.required else "optional"
        if at is None:
            lines.append(f"missing: {clone.name} ({kind}, {clone.size}): {clone.holds}")
            continue
        langs = ""
        if clone.name == RAG:
            langs = f" ({', '.join(c3.checked_out_locales(at))})"
        lines.append(f"ok: {clone.name} at {at.as_posix()}{langs}{note}")

    rag = found[RAG][0]
    adds = []
    for lang in locales if rag else []:
        gap = c3.locale_missing(rag, lang)
        if gap:
            lines.append(f"missing: {lang} data: {gap}")
            adds.append(lang)
    if not missing and not adds:
        lines.append("ok: everything the skill reads is in place")
        return lines, True
    required = [c for c in missing if c.required]
    if git is None:
        lines.append("missing: git, which clones the repositories and keeps them current; install it from "
                     "https://git-scm.com, then run this again")
    elif git < SPARSE_GIT and rag is None and "zh-CN" not in locales:
        lines.append(f"note: git {'.'.join(map(str, git))} is older than {'.'.join(map(str, SPARSE_GIT))}, which "
                     f"the clone without zh-CN needs; update git, or run this with --locales zh-CN for a full clone")
    if missing:
        lines += ["", "Before you clone, ask the user whether they already have any of these clones elsewhere, so "
                      "that no second copy is made. A clone elsewhere is named, not cloned again:"]
        lines += [f"  {clone.name}: set {clone.variable} to its folder" for clone in missing if clone.variable]
        beside = [clone.name for clone in missing if not clone.variable]
        if beside:
            lines.append(f"  {', '.join(beside)}: beside Construct3-RAG, or on a '- <name>: <folder>' line of the "
                         f"project's AGENTS.md")
        lines.append(f"  or set CONSTRUCT3_HOME to the folder that holds them all, instead of {home.as_posix()}")
    for title, group in (("These commands clone the required ones", required),
                         ("These clone the optional ones, only if the user wants them",
                          [c for c in missing if not c.required])):
        if group:
            lines += ["", f"{title}:"]
            for clone in group:
                lines += [f"  {cmd}" for cmd in clone_commands(clone, found[clone.name][1], locales)]
    if required:
        lines += ["", f"missing: {len(required)} required clone{'s' if len(required) > 1 else ''}; give the user "
                      f"every line above in one message, run the commands once the user agrees, then run this again"]
    elif adds:
        lines += ["", f"missing: the {', '.join(adds)} data; run the command above once the user agrees"]
    else:
        lines += ["", "ok: everything required is in place; the optional clones above are the user's choice"]
    return lines, not required and not adds


def main() -> int:
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Check Python, git and the clones the skill reads, and print every missing clone at once with "
                    "its size and the command that clones it into the home (~/Construct3, or CONSTRUCT3_HOME). "
                    "Downloads nothing.",
        epilog="examples:\n"
               "  python scripts/setup.py                   English only\n"
               "  python scripts/setup.py --locales zh-CN   English and Chinese\n\n"
               "exit codes: 0 everything required is in place, 1 something required is missing")
    ap.add_argument("--locales", nargs="+", default=[], metavar="LOCALE",
                    help=f"languages of the data besides {ENGLISH}, which is always kept: zh-CN")
    ap.add_argument("--project", metavar="FOLDER",
                    help="a game project whose AGENTS.md or CLAUDE.md names clones on their lines")
    args = ap.parse_args()
    if sys.version_info < PYTHON:
        print(f"missing: Python {'.'.join(map(str, PYTHON))} or later; this is Python "
              f"{'.'.join(map(str, sys.version_info[:3]))}. Install a newer one from https://www.python.org, "
              f"then run this again with it")
        return 1
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import c3project as c3
    c3.utf8_output()
    unknown = [lang for lang in args.locales if lang != "zh-CN"]
    if unknown:
        print(f"--locales takes zh-CN, and {ENGLISH} is always kept; not {', '.join(unknown)}")
        return 2
    git = git_version()
    print(f"ok: Python {'.'.join(map(str, sys.version_info[:3]))}")
    if git:
        print(f"ok: git {'.'.join(map(str, git))}")
    root = c3.find_project(args.project)
    lines, ready = report(c3, root if root and (root / "project.c3proj").is_file() else None, args.locales, git)
    print("\n".join(lines))
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
