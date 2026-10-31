"""c3project.py, what the skill's scripts share: the one form of every command a script prints for the agent
to run next, from the current directory."""
from pathlib import Path

from tests.skill_helpers import REPO, SKILL, new_project, png, script_module

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


def rag_clone(folder: Path, locales: tuple[str, ...] = ("en-US",)) -> Path:
    """A folder that counts as a Construct3-RAG clone, whose index lists en-US and zh-CN and which holds the
    schemas of locales only, as a clone made without zh-CN does."""
    schemas = folder / "data" / "c3-schemas"
    schemas.mkdir(parents=True)
    (schemas / "_index.json").write_text('{"languages": ["en-US", "zh-CN"]}', encoding="utf-8")
    for locale in locales:
        (schemas / locale).mkdir()
    return folder


def running_plugin(folder: Path, monkeypatch) -> Path:
    """A plugin folder at folder that the scripts run from."""
    (folder / ".claude-plugin").mkdir(parents=True)
    (folder / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
    (folder / "skills" / "construct3-agent-plugin").mkdir(parents=True)
    monkeypatch.setattr(c3, "SKILL_DIR", (folder / "skills" / "construct3-agent-plugin").resolve())
    return folder


def test_construct3_rag_is_found_by_flag_variable_line_home_then_beside_the_clones(tmp_path, monkeypatch):
    """Run from plugin/ of a Construct3-Agent-Skills clone, a developer's checkout: a clone in the home comes
    before one beside the checkout, and a flag, the variable and a line come before both."""
    plugin = running_plugin(tmp_path / "GitHub" / "Construct3-Agent-Skills" / "plugin", monkeypatch)
    (plugin.parent / ".git").mkdir()
    home = tmp_path / "home"
    monkeypatch.setenv("CONSTRUCT3_HOME", str(home))
    monkeypatch.delenv("CONSTRUCT3_RAG", raising=False)
    game = tmp_path / "game"
    game.mkdir()
    monkeypatch.chdir(game)
    assert c3.clone_places("Construct3-RAG", game) == [("CONSTRUCT3_HOME", home / "Construct3-RAG"),
                                                       ("beside the clones", tmp_path / "GitHub" / "Construct3-RAG")]
    assert c3.locate_rag(game, None) == (None, [f"CONSTRUCT3_HOME: {home / 'Construct3-RAG'}",
                                               f"beside the clones: {tmp_path / 'GitHub' / 'Construct3-RAG'}"])
    beside = rag_clone(tmp_path / "GitHub" / "Construct3-RAG")
    assert c3.locate_rag(game, None)[0] == beside
    in_home = rag_clone(home / "Construct3-RAG")
    assert c3.locate_rag(game, None)[0] == in_home
    line = rag_clone(tmp_path / "line")
    (game / "AGENTS.md").write_text(f"- Construct3-RAG: {line.as_posix()}\n", encoding="utf-8")
    assert c3.locate_rag(game, None)[0] == line
    variable = rag_clone(tmp_path / "variable")
    monkeypatch.setenv("CONSTRUCT3_RAG", str(variable))
    assert c3.locate_rag(game, None)[0] == variable
    flag = rag_clone(tmp_path / "flag")
    assert c3.locate_rag(game, str(flag))[0] == flag


def test_an_installed_plugin_looks_in_the_home_then_beside_its_cache_folder(tmp_path, monkeypatch):
    """Claude Code's plugin cache holds no clone of Construct3-Agent-Skills: the home, ~/Construct3 without
    CONSTRUCT3_HOME, comes first, and the folder beside the version folders, where installs made before the
    home put the clones, comes last."""
    plugin = running_plugin(tmp_path / "cache" / "marketplace" / "construct3" / "1.2.0", monkeypatch)
    monkeypatch.delenv("CONSTRUCT3_HOME", raising=False)
    monkeypatch.delenv("CONSTRUCT3_RAG", raising=False)
    monkeypatch.delenv("CONSTRUCT3_COOKBOOK", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "user"))
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "user" / "Construct3"
    assert c3.clone_places("Construct3-RAG", None) == [("the home", home / "Construct3-RAG"),
                                                       ("beside the plugin cache", plugin.parent / "Construct3-RAG")]
    old = rag_clone(plugin.parent / "Construct3-RAG")
    assert c3.locate_rag(None, None)[0] == old
    assert c3.locate_cookbook(old)[1] == [f"the home: {home / 'Construct3-Cookbook'}",
                                          f"beside the clones: {plugin.parent / 'Construct3-Cookbook'}"]
    new = rag_clone(home / "Construct3-RAG")
    assert c3.locate_rag(None, None)[0] == new
    assert c3.locate_cookbook(new)[0] is None
    assert cookbook(home / "Construct3-Cookbook") == c3.locate_cookbook(new)[0]


def test_a_locale_the_clone_left_out_gives_the_command_that_adds_it(tmp_path):
    """setup.py clones Construct3-RAG without zh-CN unless asked, and the index still lists it: the message
    names the sparse checkout to disable, not the languages of the index. A locale the index does not list
    gives the ones the clone holds."""
    rag = rag_clone(tmp_path / "Construct3-RAG")
    assert c3.checked_out_locales(rag) == ["en-US"]
    assert c3.locale_missing(rag, "en-US") is None
    assert c3.locale_missing(rag, "zh-CN") == (
        f"the Construct3-RAG clone at {rag.as_posix()} was cloned without the zh-CN files; run "
        f'git -C "{rag.as_posix()}" sparse-checkout disable to add every language (about 4 MB), then run this again')
    assert c3.locale_missing(rag, "xx-XX") == "no schemas for --locale xx-XX; the clone has: en-US"


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
    assert "scripts/setup.py prints the clone to make; for a clone elsewhere, set CONSTRUCT3_COOKBOOK" in         c3.missing_cookbook(rag)

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


def test_your_own_pitfalls_are_found_by_flag_variable_then_line(tmp_path, monkeypatch):
    """A line's relative path starts at its file's folder, so a folder kept in the game project travels with it."""
    game = tmp_path / "game"
    (game / "notes" / "plugins").mkdir(parents=True)
    monkeypatch.setattr(c3, "SKILL_DIR", game / ".agents" / "skills" / "construct3-agent-plugin")
    monkeypatch.delenv("CONSTRUCT3_COOKBOOK_EXTRA", raising=False)
    monkeypatch.chdir(tmp_path)
    assert c3.own_pitfalls(game) == (None, None)
    (game / "AGENTS.md").write_text("- Construct3-Cookbook: ../Construct3-Cookbook\n"
                                    "- Construct3-Cookbook-extra: notes\n", encoding="utf-8")
    assert c3.own_pitfalls(game) == (game / "notes", None)
    variable = tmp_path / "variable"
    variable.mkdir()
    monkeypatch.setenv("CONSTRUCT3_COOKBOOK_EXTRA", str(variable))
    assert c3.own_pitfalls(game) == (variable, None)
    folder, note = c3.own_pitfalls(game, "missing")
    assert folder is None and "--cookbook-extra names missing, which is not a folder" in note


def test_a_guide_is_cited_by_its_cookbook_path_without_a_clone(tmp_path, monkeypatch):
    monkeypatch.setattr(c3, "SKILL_DIR", tmp_path / "game" / ".agents" / "skills" / "construct3-agent-plugin")
    monkeypatch.delenv("CONSTRUCT3_COOKBOOK", raising=False)
    monkeypatch.chdir(tmp_path)
    rag = tmp_path / "Construct3-RAG"
    rag.mkdir()
    assert c3.guide_path(rag, "behaviors/timer.md") == "Construct3-Cookbook/guides/behaviors/timer.md"


def test_a_screenshot_is_blank_only_when_its_share_of_one_colour_and_its_luminance_both_say_so():
    """At an eighth of a 430 x 932 window: an empty screen is one colour and flat. A small sprite alone leaves
    99.9% of it one colour, which the share alone took for nothing drawn, but its luminance deviates; a faint
    speck does not, and stays blank."""
    def screen(drawn, ink=(0, 0, 0, 255)):
        return png(54, 116, lambda x, y: ink if drawn(x, y) else (209, 209, 209, 255))
    assert c3.fill(screen(lambda x, y: False)) == (1.0, 0.0)
    assert c3.blank_share(screen(lambda x, y: False)) == 1.0
    sprite = screen(lambda x, y: 26 <= x < 28 and 58 <= y < 61)
    share, spread = c3.fill(sprite)
    assert share > c3.BLANK and spread > c3.SPREAD and c3.blank_share(sprite) is None, (share, spread)
    speck = screen(lambda x, y: (x, y) == (26, 58), (180, 180, 180, 255))
    assert c3.is_blank(*c3.fill(speck)) and c3.blank_share(speck) is not None
