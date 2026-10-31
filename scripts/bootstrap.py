"""Set a machine up from this clone alone: the clones the skill reads, a game project, and the skill inside it.

    python scripts/bootstrap.py                     # clone what is missing into the home, ~/Construct3
    python scripts/bootstrap.py --project MyGame    # ... and install the skill in MyGame beside them;
                                                    # a folder that does not exist yet gets the empty project

Clones Construct3-RAG, Construct3-Cookbook and Construct3-Manual, each only when the scripts find no clone of
it, with the commands that the skill's setup.py prints: into the home, CONSTRUCT3_HOME or ~/Construct3, or
beside a Construct3-RAG clone that lies elsewhere. Construct3-RAG leaves out zh-CN unless --locales names it.
--all adds Construct-Example-Projects and Construct-Addon-SDK. A missing or empty project folder gets a copy of
the empty project of Construct3-RAG, then the skill's install.py runs on the project. Safe to run again: a
clone already present is left as it is, and install.py refreshes rather than overwrites.
"""
import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_SCRIPTS = ROOT / "plugin" / "skills" / "construct3-agent-plugin" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))
import c3project as c3  # noqa: E402
import setup  # noqa: E402
from new_project import new_project  # noqa: E402

INSTALL = SKILL_SCRIPTS / "install.py"
# The project the editor saves for Project > New, in the Construct3-RAG clone, so that a
# project can start without the editor. Copied, never used in place.
TEMPLATE = Path("data", "c3-new-project")


def clone(item: setup.Clone, target: Path, locales: list[str], dry_run: bool) -> tuple[str, bool]:
    """One clone, made with setup.py's commands, or the commands to run by hand; and whether it is in place or
    on its way."""
    commands = setup.clone_commands(item, target, locales)
    if dry_run:
        return "\n".join(f"{item.name}: would run {cmd}" for cmd in commands), True
    if not shutil.which("git"):
        return (f"{item.name}: git is not installed, so it was not cloned. Install Git (https://git-scm.com), "
                f"then run this again"), False
    for cmd in commands:
        p = subprocess.run(shlex.split(cmd), capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode != 0:
            return (f"{item.name}: {cmd.split(' --')[0]} failed; run by hand:\n"
                    + "\n".join(f"  {c}" for c in commands) + f"\n{p.stderr.strip()}"), False
    return f"{item.name}: cloned to {target}", True


def resolved(given: str) -> Path:
    """A path from a flag: `~` expanded, read from the current directory."""
    return Path(given).expanduser().resolve()


def game_folder(given: str, folder: Path) -> Path:
    """Where `--project` points. A bare name is a name, and a name goes beside
    the clones, whatever directory the command was run from; the README's
    `--project MyGame` means the same folder from a game project, from the
    desktop or from here. A path spelt out — a separator, a drive letter, `~`,
    `.` — is read from the current directory, as a path is anywhere else."""
    spelt_out = given.startswith(("~", ".")) or any(c in given for c in "/\\:")
    return resolved(given) if spelt_out else (folder / given).resolve()


def name_clones(project: Path, folder: Path, names: list[str]) -> str:
    """The scripts search the home and the folder that holds this repository, and the block expects the other
    clones beside Construct3-RAG. Cloned elsewhere, each gets its line under the Construct3-RAG line, once."""
    agents = project / "AGENTS.md"
    text = agents.read_text(encoding="utf-8") if agents.exists() else ""
    missing = [n for n in names if f"{n}:" not in text]
    key = "- Construct3-RAG:"
    if not missing or key not in text:
        return "AGENTS.md: the clones are already named"
    lines = "".join(f"- {n}: {(folder / n).as_posix()}\n" for n in missing)
    head, _, tail = text.partition(key)
    line, _, rest = tail.partition("\n")
    agents.write_text(head + key + line + "\n" + lines + rest, encoding="utf-8", newline="\n")
    return f"AGENTS.md: named {', '.join(missing)} under {folder.as_posix()}, where the scripts do not look"


def main() -> int:
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Clone the repositories the skill reads into the home, create a game project when the folder "
                    "does not exist yet, and install the construct3-agent-plugin skill in it. Safe to run again.",
        epilog="examples:\n"
               "  python scripts/bootstrap.py                          the required clones only\n"
               "  python scripts/bootstrap.py --all --locales zh-CN    every clone, with the Chinese data\n"
               "  python scripts/bootstrap.py --project MyGame         the clones, then the skill in MyGame,\n"
               "                                                       created beside them when it does not exist\n"
               "  python scripts/bootstrap.py --project ../MyGame --into .claude/skills\n\n"
               "exit codes: 0 done, 1 a clone or the project failed; the line says what to run by hand")
    ap.add_argument("--project", metavar="NAME|FOLDER",
                    help="the game project, created from the empty project when missing. A name goes beside the "
                         "clones; a path is read from the current directory")
    ap.add_argument("--into", metavar="DIR", help="skills directory inside the project, passed to install.py")
    ap.add_argument("--beside", metavar="FOLDER",
                    help="where the clones go and are looked for (default: where the scripts find each one, else "
                         "the home: CONSTRUCT3_HOME, or Construct3 in the user's home folder)")
    ap.add_argument("--all", action="store_true",
                    help="also clone the optional Construct-Example-Projects (about 864 MB) and Construct-Addon-SDK")
    ap.add_argument("--locales", nargs="+", default=[], metavar="LOCALE",
                    help="languages of the data besides en-US: zh-CN (default: en-US only)")
    ap.add_argument("--template", metavar="FOLDER",
                    help=f"the empty project to copy (default: {TEMPLATE.as_posix()} of the Construct3-RAG clone)")
    ap.add_argument("--dry-run", action="store_true", help="say what would be done, do nothing")
    args = ap.parse_args()
    c3.utf8_output()

    if args.beside:
        folder = resolved(args.beside)
        places = {c.name: (folder / c.name if (folder / c.name).is_dir() and any((folder / c.name).iterdir())
                           else None, folder / c.name) for c in setup.CLONES}
    else:
        places = {name: (at, into) for name, (at, into, _) in setup.found_clones(c3, None).items()}
    failed = False
    for item in setup.CLONES:
        at, into = places[item.name]
        if at:
            print(f"{item.name}: already at {at}")
        elif item.required or args.all:
            line, ok = clone(item, into, args.locales, args.dry_run)
            failed |= not ok
            print(line)
        else:
            print(f"{item.name} ({item.size}): not cloned, since it is optional; --all clones it")
    rag = places[setup.RAG][0] or places[setup.RAG][1]
    project = game_folder(args.project, rag.parent) if args.project else None
    template = resolved(args.template) if args.template else rag / TEMPLATE

    if project is None:
        print("dry run: nothing was done" if args.dry_run else
              f"ok: next, python {Path(__file__).as_posix()} --project <game folder>")
        return 1 if failed else 0

    if not (project / "project.c3proj").exists():
        # A dry run clones nothing, so the empty project of a Construct3-RAG still to clone is not there yet
        line = (f"{project.name}: would be created from {template} at {project}"
                if args.dry_run and not template.exists() else new_project(template, project, args.dry_run))
        print(line)
        if "not created" in line or "not empty" in line:
            return 1
    if args.dry_run:
        print("dry run: nothing was done")
        return 1 if failed else 0
    passed = ["--project", str(project), "--rag", str(rag)] + (["--into", args.into] if args.into else [])
    p = subprocess.run([sys.executable, str(INSTALL), *passed], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    lines = (p.stdout + p.stderr).rstrip("\n").splitlines()
    if not p.returncode and args.beside and folder not in (c3.clones_home(), c3.siblings_folder(ROOT)):
        # Before install.py's last line, "ok: read ...", which stays the last line of the run.
        lines.insert(-1, name_clones(project, folder, [n for n, (at, _) in places.items() if at or n == setup.RAG]))
    print("\n".join(lines))
    return 1 if failed or p.returncode else 0


if __name__ == "__main__":
    sys.exit(main())
