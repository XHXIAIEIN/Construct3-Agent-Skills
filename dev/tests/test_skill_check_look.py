"""check_look.py: the look's rules, read off the images, layouts and sheets of a project."""
import re

from tests.skill_helpers import tool, edit, template_module, cond, block, png


def test_check_look_passes_the_stand_in_and_names_each_fault(project):
    code, out = tool(project, "check_look")
    assert code == 0 and out.splitlines()[-1].startswith("ok: 4 images, 2 world instances on a 32 px grid, "
                                                          "1 runtime creations"), out
    t = template_module()
    t.ROOT = project
    t.write_png("smudge.png", 2, 1, lambda x, y: [(9, 9, 9, 0), (*t.PALETTE["danger"], 128)][x])
    t.write_png("glow.png", 1, 1, lambda x, y: (*t.PALETTE["danger"], 37), painted=True)
    (project / "images" / "dirty.png").write_bytes(png(1, 1, lambda x, y: (9, 9, 9, 0)))    # a clear pixel with a colour under it
    edit(project, "layouts/Objects.json", lambda d: d["layers"][0]["instances"][0]["world"].update(x=150))
    sheet = project / "eventSheets" / "Game.json"
    sheet.write_text(re.sub(r'"x": "(?:[^"\\]|\\.)*loopindex(?:[^"\\]|\\.)*"', '"x": "random(96, 1728)"',
                            sheet.read_text(encoding="utf-8"), count=1), encoding="utf-8")
    code, out = tool(project, "check_look")
    assert code == 1, out
    assert "alpha.pure: images/dirty.png has 1 clear pixels that hold a colour, the first at (0,0)" in out
    assert "glow.png" not in out                    # above pixel art an edge keeps its antialiasing
    assert re.search(r"grid.world-placement: layout Objects layer Objects: Coin at \(\d+,\d+\) \d+x\d+ is off the 32 px grid", out)
    assert "grid.runtime-spawn: sheet Game: create Coin at x = random(96, 1728), a raw random()" in out
    assert out.splitlines()[-1].startswith("3 findings:")
    # On the grid of pixel art an image is clear, opaque or the shadow, unless it is named as a painting
    _, out = tool(project, "check_look", "--unit", "8")
    assert re.search(r"alpha.pure: images/glow.png has alpha 37 at \(0,0\); the project's shadow is \d+.*--painted glow.png", out)
    _, out = tool(project, "check_look", "--unit", "8", "--painted", "glow.png")
    assert "glow.png" not in out
    edit(project, "objectTypes/Coin.json", lambda d: d["behaviorTypes"].append(
        {"behaviorId": "Flash", "name": "Flash", "sid": 633333333333333}))
    _, out = tool(project, "check_look", "--painted", "glow.png")
    assert "motion.hit: Coin has the Flash behavior Flash; a hit shows as a colour for an instant" in out
    edit(project, "objectTypes/Coin.json", lambda d: d["behaviorTypes"].append(
        {"behaviorId": "solid", "name": "Solid", "sid": 644444444444444}))
    _, out = tool(project, "check_look", "--painted", "glow.png")
    assert ("motion.squash-art: sheet Game: Coin is squashed but has solid, so its collision box grows into the "
            "floor; squash its art") in out


def test_check_look_leaves_paper_and_inks_rules_to_its_fallback(project):
    """A game whose generator names the user's look in USER_LOOK may show a hit with the Flash
    behavior, a rule of paper and ink's taste; the grid holds in every look."""
    edit(project, "objectTypes/Coin.json", lambda d: d["behaviorTypes"].append(
        {"behaviorId": "Flash", "name": "Flash", "sid": 633333333333333}))
    edit(project, "layouts/Objects.json", lambda d: d["layers"][0]["instances"][0]["world"].update(x=150))
    generator = project / "tools" / "build_project.py"
    source = generator.read_text(encoding="utf-8")
    assert source.count('\nUSER_LOOK = ""') == 1
    generator.write_text(source.replace('\nUSER_LOOK = ""', '\nUSER_LOOK = "the user\'s: a blinking arcade look"'),
                         encoding="utf-8")
    code, out = tool(project, "check_look")
    assert code == 1 and "motion.hit" not in out.replace("motion.hit, a rule of paper and ink, is not checked", ""), out
    assert ("look: the user's, from USER_LOOK (the user's: a blinking arcade look); motion.hit, a rule of paper and "
            "ink, is not checked") in out
    assert "grid.world-placement: layout Objects layer Objects: Coin" in out and out.splitlines()[-1].startswith("1 findings")
    generator.write_text(source, encoding="utf-8")
    assert "motion.hit: Coin has the Flash behavior" in tool(project, "check_look")[1]


def test_check_look_warns_of_a_letterbox_mode(project):
    """The template fills the screen; a project in a Letterbox mode passes with a warning that
    names the mode to write, since the editor accepts it and the bars are the user's call."""
    edit(project, "project.c3proj", lambda p: p["properties"].update(fullscreenMode="letterbox-integer-scale"))
    code, out = tool(project, "check_look")
    assert code == 0 and out.splitlines()[-1].startswith("ok:"), out
    assert ("warning: screen.fill: project.c3proj has fullscreenMode letterbox-integer-scale, which shows bars "
            "where the screen's shape differs from the viewport's; the template's build_project() writes "
            "integer-scale-outer") in out
    edit(project, "project.c3proj", lambda p: p["properties"].update(fullscreenMode="scale-outer"))
    assert "screen.fill" not in tool(project, "check_look")[1]


def test_check_look_warns_of_a_viewport_under_the_notch(project):
    """Viewport fit Cover draws under a notch, where the anchored HUD then lies: a warning until an
    event reads the safe area's insets, since the editor accepts the setting."""
    edit(project, "project.c3proj", lambda p: p["properties"].update(viewportFit="cover"))
    code, out = tool(project, "check_look")
    assert code == 0 and out.splitlines()[-1].startswith("ok:"), out
    assert ("warning: screen.safe-area: project.c3proj has viewportFit cover, which draws the game under a "
            "phone's notch") in out
    edit(project, "eventSheets/Game.json", lambda s: s["events"].append(
        {"eventType": "comment", "text": "PlatformInfo.SafeAreaInsetTop is read nowhere yet"}))
    assert "screen.safe-area" in tool(project, "check_look")[1]
    edit(project, "eventSheets/Game.json", lambda s: s["events"].append(block(
        [cond("on-start-of-layout")], [cond("set-y", "ScoreLabel", {"y": "MARGIN + PlatformInfo.SafeAreaInsetTop"})])))
    assert "screen.safe-area" not in tool(project, "check_look")[1]
    edit(project, "project.c3proj", lambda p: p["properties"].update(viewportFit="auto"))
    assert "screen.safe-area" not in tool(project, "check_look")[1]


def test_check_look_names_the_motion_that_breaks_the_hud_or_a_tween(project):
    """A HUD object that grows from 0, and a count restarted without Stop, are findings; an
    overshoot or an ease-in fade on the HUD and a squash of an object a size tween destroys are
    warnings, since the subject of a moment and a guarded squash are not in the files. The stand-in
    game's own tweens, a coin's hit and its shrink in one action list among them, raise none."""
    code, out = tool(project, "check_look")
    assert code == 0 and "motion." not in out and out.splitlines()[-1].endswith(", 3 tweens"), out
    t = template_module()
    stop = t.stop_tweens("ScoreText", "count")
    count = t.tween_value("ScoreText", "count", "int(ScoreText.Text)", "score", "0.5", "easeoutquad")
    rows = [
        block([cond("on-any-touch-start", "Touch")], [
            t.tween1("KeyBox", "pop", "offsetY", "0", "0.5", "easeoutback"),
            t.tween1("KeyBox", "show", "offsetOpacity", "100", "0.5", "easeinsine"),
            t.tween1("KeyBox", "hide", "offsetOpacity", "0", "0.5", "easeinsine"),
            t.act("set-size", "KeyBox", {"width": "0", "height": "0"}),
            t.tween2("KeyBox", "open", "size", "320", "64", style="popup"),
            count,
            t.tween2("Coin", "land", "size", "Self.ImageWidth", "Self.ImageHeight", "0.5", "easeoutelastic")]),
        block([cond("on-any-touch-end", "Touch")], [stop, count]),
        block([cond("on-any-touch-end", "Touch")], [t.tween2("Coin", "die", "size", "0", "0", destroy=True)]),
    ]
    edit(project, "eventSheets/Game.json", lambda s: s["events"].extend(rows))
    code, out = tool(project, "check_look")
    assert code == 1, out
    assert ("warning: motion.hud-overshoot: sheet Game: KeyBox, on the HUD, tweens offsetY with easeoutback. An "
            "overshoot ease is for world objects and the subject of a moment") in out
    assert "warning: motion.hud-ease-in: sheet Game: KeyBox, on the HUD, fades in with easeinsine" in out
    assert out.count("motion.hud-ease-in") == 1                     # a fade out with an ease-in passes
    assert "motion.panel-from-zero: sheet Game: KeyBox, on the HUD, grows its size from 0" in out
    assert ("motion.value-restart: sheet Game: ScoreText starts the value tween 'count' from int(ScoreText.Text), "
            "the number it shows, without Stop 'count' first") in out
    assert out.count("motion.value-restart") == 1                   # the count after its Stop passes
    assert ("warning: motion.size-on-dying: sheet Game: Coin is destroyed by a size tween, and another event "
            "tweens its size back to its rest size") in out
    assert out.splitlines()[-1].startswith("2 findings:"), out
