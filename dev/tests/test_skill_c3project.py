"""c3project.py, what the skill's scripts share: the one form of every command a script prints for the agent
to run next, from the current directory."""
from pathlib import Path

from tests.skill_helpers import REPO, SKILL, new_project, script_module

c3 = script_module("c3project")
PRINT_SHEET = c3.quoted((SKILL / "scripts" / "print_sheet.py").as_posix())


def test_quoted_quotes_a_word_a_shell_would_split_or_read():
    assert c3.quoted("a b") == '"a b"'
    assert c3.quoted("D:/x/y.py") == "D:/x/y.py"
    assert c3.quoted("D:\\x\\y.py") == "D:\\x\\y.py"
    assert c3.quoted("Game") == "Game" and c3.quoted("eventSheets/Game.json") == "eventSheets/Game.json"
    assert c3.quoted("Game & HUD") == '"Game & HUD"'
    assert c3.quoted(7) == "7"


def test_script_command_names_the_script_and_the_project_from_the_current_directory(project, tmp_path, monkeypatch):
    """From inside the project, the script alone. From the repository root, the script relative to it and
    --project. From a folder in no project, the script absolute and --project, quoted when the root holds
    a space."""
    monkeypatch.chdir(project)
    assert c3.script_command(project, "print_sheet.py") == f"python {PRINT_SHEET}"
    assert c3.script_command(None, "print_sheet.py", " --outline") == f"python {PRINT_SHEET} --outline"
    monkeypatch.chdir(REPO)
    assert c3.script_command(project, "print_sheet.py") == (
        f"python plugin/skills/construct3-agent-plugin/scripts/print_sheet.py --project {project.resolve().as_posix()}")
    spaced = new_project(tmp_path / "New folder" / "game")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert c3.script_command(spaced, "print_sheet.py") == (
        f'python {PRINT_SHEET} --project "{spaced.resolve().as_posix()}"')
    assert c3.open_command(spaced).endswith(f' --project "{spaced.resolve().as_posix()}" --preview')


def test_missing_examples_bootstrap_names_the_tool_repository():
    assert c3.examples_clone_command(None) == "python <Construct3-Agent-Skills>/scripts/bootstrap.py"


def cookbook(folder: Path) -> Path:
    """A folder that counts as a Construct3-Cookbook clone."""
    index = folder / "guides" / "pitfalls.md"
    index.parent.mkdir(parents=True)
    index.write_text("# Pitfalls", encoding="utf-8")
    return folder


def test_the_cookbook_is_found_by_flag_variable_line_then_beside_the_clones(tmp_path, monkeypatch):
    rag = tmp_path / "Construct3-RAG"
    rag.mkdir()
    game = tmp_path / "game"
    game.mkdir()
    monkeypatch.setattr(c3, "SKILL_DIR", game / ".agents" / "skills" / "construct3-agent-plugin")
    monkeypatch.delenv("CONSTRUCT3_COOKBOOK", raising=False)
    monkeypatch.chdir(game)
    assert c3.guides_folder(rag, game) is None
    assert f'"{(tmp_path / "Construct3-Cookbook").as_posix()}"' in c3.missing_cookbook(rag)

    # A folder of that name without the guides, such as a private workspace, is not a clone
    (tmp_path / "Construct3-Cookbook").mkdir()
    assert c3.guides_folder(rag, game) is None
    cookbook(tmp_path / "Construct3-Cookbook")
    assert c3.guides_folder(rag, game) == tmp_path / "Construct3-Cookbook" / "guides"

    line = cookbook(tmp_path / "named")
    (game / "AGENTS.md").write_text(f"- Construct3-Cookbook: {line.as_posix()}\n", encoding="utf-8")
    assert c3.locate_cookbook(rag, game)[0] == line
    variable = cookbook(tmp_path / "variable")
    monkeypatch.setenv("CONSTRUCT3_COOKBOOK", str(variable))
    assert c3.locate_cookbook(rag, game)[0] == variable
    flag = cookbook(tmp_path / "flag")
    assert c3.locate_cookbook(rag, game, str(flag))[0] == flag


def test_a_guide_is_cited_by_its_cookbook_path_without_a_clone(tmp_path, monkeypatch):
    monkeypatch.setattr(c3, "SKILL_DIR", tmp_path / "game" / ".agents" / "skills" / "construct3-agent-plugin")
    monkeypatch.delenv("CONSTRUCT3_COOKBOOK", raising=False)
    monkeypatch.chdir(tmp_path)
    rag = tmp_path / "Construct3-RAG"
    rag.mkdir()
    assert c3.guide_path(rag, "behaviors/timer.md") == "Construct3-Cookbook/guides/behaviors/timer.md"
