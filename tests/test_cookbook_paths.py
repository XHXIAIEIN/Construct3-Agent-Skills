"""Every Construct3-Cookbook path this repository names exists in the Cookbook clone.

The event sheet guides live in Construct3-Cookbook (docs/decisions/guides-in-cookbook.md). The skill, its
scripts and the instruction files name them as Construct3-Cookbook/guides/<path>, and a guide
renamed there breaks those names with nothing else to report it. The records under docs/decisions/ keep the
paths of their day and are left out.
"""
import re

from tests.skill_helpers import COOKBOOK, NEEDS_COOKBOOK, PLUGIN, REPO

NAMED = re.compile(r"Construct3-Cookbook/(guides/[A-Za-z0-9_./-]*[A-Za-z0-9_/])")
TEXTS = sorted({
    REPO / "AGENTS.md", REPO / "README.md", REPO / "README_CN.md",
    *REPO.glob("*/AGENTS.md"), *REPO.glob(".claude/agents/*.md"),
    *(p for p in PLUGIN.rglob("*") if p.suffix in (".md", ".py") and "data" not in p.relative_to(PLUGIN).parts[:1]),
} - {p for p in REPO.glob("docs/decisions/*.md")})


def named() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for path in TEXTS:
        for rel in NAMED.findall(path.read_text(encoding="utf-8")):
            found.setdefault(rel, set()).add(path.relative_to(REPO).as_posix())
    return found


def test_the_skill_names_the_guides_by_their_cookbook_paths():
    assert "guides/design/thinking.md" in named()
    assert "guides/pitfalls.md" in named()


@NEEDS_COOKBOOK
def test_every_cookbook_path_named_here_exists_in_the_clone():
    missing = [f"{rel} (named in {', '.join(sorted(files))})" for rel, files in sorted(named().items())
               if not (COOKBOOK / rel).exists()]
    assert not missing, "\n".join(missing)
