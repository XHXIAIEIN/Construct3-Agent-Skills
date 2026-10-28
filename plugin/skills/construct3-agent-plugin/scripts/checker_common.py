"""The names, tables and small helpers that check_project.py and its checker_*.py parts
share."""
import math
import re
import unicodedata
from collections.abc import Iterable, Iterator
from typing import NamedTuple

from c3project import LOWER, STRING_LITERAL


# Names. The editor passes every name through a filter when it opens the
# project and keeps the result, so a name the filter changes no longer matches
# the events that use it. After the open it also renames an object type or
# family whose name is reserved, Floor to Floor2. It refuses a name already
# taken in the object's namespace, where instance variables, behaviors, effects
# and the plugin's expressions live side by side, compared without case.
NAME_DROPS = set(".。,，\"“”(（)）?？:：\\/;*|'-`!¬£$%^&+=<>{}[]@#~­​")
VARIABLE_TYPES = ("number", "string", "boolean")
# Event keys the editor reads as text and stops on when missing, with its message.
EVENT_TEXT = (("comment", "text", "Cannot read properties of undefined (reading 'endsWith')"),
              ("group", "description", "expected string"),
              ("variable", "comment", "expected string"))
FUNCTION_RETURN_TYPES = ("none", "number", "string", "any")
# rootFileFolders kind -> the folder the editor saves its files in, as Scirra's guide
# "Construct's project format" lists them.
ROOT_FILE_FOLDERS = {"general": "files", "icon": "icons", "sound": "sounds", "music": "music",
                     "video": "videos", "font": "fonts", "script": "scripts"}
UNLISTED_ROOT_FILES = ("general", "icon", "sound", "music", "video", "font")
# Sound and music are WebM Opus; the editor converts what it imports.
AUDIO_TYPE = "audio/webm; codecs=opus"
# The "type" the editor wrote for a file of Files in the official examples, by extension, with every
# type it wrote (docs/decisions/file-types-in-project-c3proj.md). An extension the examples never saved
# has no entry, and nothing is said about it.
GENERAL_TYPES = {".css": ("text/css",), ".csv": ("text/csv",), ".glb": ("application/octet-stream",),
                 ".html": ("text/html",), ".js": ("application/javascript", "text/javascript"),
                 ".json": ("application/json",), ".png": ("image/png",), ".svg": ("image/svg+xml",),
                 ".ts": ("application/typescript",), ".txt": ("text/plain",), ".wasm": ("application/wasm",),
                 ".xml": ("text/xml",)}
# The fix loop stops after CAP changes that left one finding standing. The findings of the last run
# are c3.RECORD below the project (docs/decisions/fix-loop-cap.md).
# CONSTRUCT3_RAG_NO_RECORD=1 keeps no record, for the evals that run the checker over many projects at once.
CAP = 2
PLACES = {"sheet": "eventSheets", "layout": "layouts", "object type": "objectTypes", "family": "families"}
EVENT_PLACE = re.compile(r" event (\d+) \(sid ([^)]*)\)")
QUOTED = re.compile(r"(?<!\w)'(?:[^'\\]|\\.)*'(?!\w)|\"(?:[^\"\\]|\\.)*\"")
# how a layout instance writes the value of an instance variable of each type
JSON_TYPES = {"number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
              "string": lambda v: isinstance(v, str), "boolean": lambda v: isinstance(v, bool)}
JSON_EXAMPLES = {"number": "a number such as 1", "string": "text such as \"a\"", "boolean": "true or false"}
FULL_TURN = 2 * math.pi + 1e-6  # the largest world angle the official examples hold is 2π
# Names the editor reserves for an object besides the system expressions, compared without case.
# "system" is not among them: it is the System object's own name, and an object of that name
# stops the open.
RESERVED_WORDS = {"self", "true", "false"}
DEVICE_NAMES = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}

# project.c3proj. Opening a project reads the whole properties block before it
# reads a single file of the project, and each of these is asserted as it is
# read: a missing one throws "TypeError: expected string" and a wrong one names
# the property. The value sets are the editor's; the defaults are what it
# writes into a new project.
PROJECT_TEXT = {"description": "", "version": "1.0.0.0", "author": "", "authorEmail": "",
                "authorWebsite": "", "appId": ""}
PROJECT_OPTIONS = {"fullscreenMode": ("letterbox-scale", "letterbox-integer-scale", "scale-inner",
                                      "integer-scale-inner", "scale-outer", "integer-scale-outer", "off"),
                   "fullscreenQuality": ("high", "low"),
                   "orientations": ("any", "portrait", "landscape"),
                   "sampling": ("trilinear", "bilinear", "nearest"),
                   "downscaling": ("medium", "low", "high"),
                   "loaderStyle": ("splash", "progress-logo", "progress", "percent", "none")}
PROJECT_ALSO = {"sampling": ("linear", "point")}  # older ids the editor maps as it reads them
# Plugins whose object type carries an animations folder: the editor reads it as
# it opens the type and stops with "TypeError: expected object" when it is not
# there. The 2930 Sprite and 785 Shape3D types of the official examples all have
# one, and no other plugin there does.
ANIMATED_PLUGINS = ("Sprite", "Shape3D")
# Plugins whose object type carries one image instead: without the "image" block the
# editor stops the same way. The 872 TiledBg, 392 Spritefont2, 223 Particles, 153
# Tilemap and 106 NinePatch types of the official examples all have one, and no
# other plugin there does.
IMAGE_PLUGINS = ("TiledBg", "Spritefont2", "Particles", "Tilemap", "NinePatch")
# A layer's blend mode, read as it opens: the editor's own map, "xor" is not in it.
BLEND_MODES = ("normal", "additive", "copy", "destination-over", "source-in", "destination-in",
               "source-out", "destination-out", "source-atop", "destination-atop", "lighten",
               "darken", "multiply", "screen")
# The numbers the editor reads out of a layer and a world instance as it places it.
LAYER_NUMBERS = ("parallaxX", "parallaxY", "scaleRate")
WORLD_NUMBERS = ("x", "y", "width", "height", "originX", "originY")
# Below this release the editor reads an object type from objectTypes\<name in
# lower case>.json, the layout of a project from 2016, and finds nothing.
FOLDER_PROJECT_RELEASE = 30900

# Object and behavior names may start with a digit (3DCamera, 8Direction), so a
# token is any run of word characters and numeric literals are skipped by value.
# Word characters are Unicode ones: the editor takes names in any script, and an
# ASCII class skips them, or cuts a mixed name down to its ASCII part.
# Sprite(2).X picks an instance by IID; the index is checked as an expression.
IDENT = re.compile(r"\w+")
NUMBER = re.compile(r"\d+(\.\d+)?(e[+-]?\d+)?", re.I)
# The tokens of an expression whose text literals are blanked to "": a literal, a number, a name,
# an operator or a bracket. Anything else, a stray character, leaves the expression untyped.
TYPE_TOKEN = re.compile(r'""|\d+(?:\.\d+)?(?:e[+-]?\d+)?|\w+|<>|<=|>=|[-+*/%^&|=<>?:(),.]', re.I)
EMPTY_CALL = re.compile(r"\s*\(\s*\)")
MEMBER = re.compile(r"(\w+)(?:\([^()]*\))?\s*\.\s*(\w+)(?:\s*\.\s*(\w+))?")
# C-style operators the expression parser refuses, with the Construct operator for each; the power
# of JavaScript's ** is ^, which in C would be exclusive or. A lone ! has none: the editor calls it
# an unknown character, and the test is written as a comparison.
C_OPERATORS = {"==": "=", "!=": "<>", "&&": "&", "||": "|", "**": "^"}
C_OPERATOR = re.compile(r"==|!=|&&|\|\||\*\*|!")
# What a variable or parameter named like another one, compared without case, can be called instead.
SHADOW_SUFFIX = {"string": "Text", "number": "Value", "boolean": "Flag"}
# Text the player reads on the layout as it starts, warnings (checker-rules.md, the traps of the running game).
# A text whose aligned side lies less than TEXT_EDGE px from the screen's edge touches it; the template keeps
# its HUD a UNIT in. A text reads TEXT_CONTRAST:1 against the layer behind it, WCAG 2.2 1.4.3 for large text
# and the template's floor for a title. A layout has no background colour of its own (manual: Layouts), and
# behind layers that are all transparent the preview shows black (r495.2 preview, 2026-10-09).
TEXT_EDGE = 1
TEXT_CONTRAST = 3
SHORT_TEXT = 12  # characters: a number or a word, the thing a screen of one or two texts is about
# Instances created in a top-level event or trigger join the instance lists when it ends: until then only
# Pick by unique ID finds them outside the creating event
# (Construct3-Cookbook/guides/primitives/events/how-events-work.md). The
# actions that create an instance of a named type, with the parameter that names it; spawn-another-object
# is on every world object. Create object by name is left out: its type is an expression.
CREATING = {("System", "create-object"): "object-to-create", ("System", "recreate-initial-objects"): "object"}
# System conditions that pick among the instances of the type in their object parameter.
SYSTEM_PICKS = {"for-each", "for-each-ordered", "pick-nth-instance", "pick-random-instance", "pick-all",
                "pick-by-comparison", "pick-by-evaluate", "pick-by-highest-lowest-value",
                "pick-overlapping-point"}
# Conditions on an object that find a created instance anyway, or pick another object than their own.
NOT_PICKING = {"pick-by-unique-id", "pick-parent", "pick-children", "pick-nth-child", "on-created"}
# After one of these the rest of the actions run later, once the instances have joined.
WAITS = {"wait", "wait-for-signal", "wait-for-previous-actions"}


def editor_name(name: str, is_object: bool) -> str:
    """What the editor keeps of a name: the letter after a space is capitalised,
    spaces and punctuation go, leading underscores go. An object or behavior
    name may start with a digit but not be all digits; an instance variable
    name loses its leading digits too."""
    chars = list(unicodedata.normalize("NFC", name))
    for i in range(len(chars) - 1):
        if chars[i] == " ":
            chars[i + 1] = chars[i + 1].upper()
    chars = [c for c in chars if c not in NAME_DROPS and not c.isspace()]
    if is_object:
        while chars and chars[0] == "_":
            chars.pop(0)
        if all(c.isdigit() for c in chars):
            chars = []
    else:
        while chars and (chars[0].isdigit() or chars[0] == "_"):
            chars.pop(0)
    return "".join(chars)


def next_name(name: str) -> str:
    """The name the editor gives an object whose name it cannot keep: the number at its end plus
    one, or a 2 added when it has none."""
    stem = name.rstrip("0123456789")
    number = name[len(stem):]
    return stem + (str(int(number) + 1) if number else "2")


def free_name(name: str, taken: Iterable) -> str:
    """The name the editor gives a variable, parameter or function it renames: next_name,
    repeated until no name taken matches it without case (Amount3 when amount2 is taken)."""
    low = {LOWER(t) for t in taken if isinstance(t, str)}
    new = next_name(name)
    while LOWER(new) in low:
        new = next_name(new)
    return new


def variable_kind(var: dict) -> str:
    """What a finding calls a declaration; a function parameter carries no eventType."""
    if "eventType" not in var:
        return "parameter"
    return "constant" if var.get("isConstant") else "static variable" if var.get("isStatic") else "variable"


def case_aside(name: str, other: str) -> str:
    """' once case is ignored' when the two names differ, else ''."""
    return "" if name == other else " once case is ignored"


def params_of(ace: dict) -> dict:
    """An ACE's parameters by id; a function call keeps its arguments in a list, which names none."""
    params = ace.get("parameters")
    return params if isinstance(params, dict) else {}


def is_literal(v) -> bool:
    return isinstance(v, str) and STRING_LITERAL.fullmatch(v) is not None


def unquote(v: str) -> str:
    return v[1:-1].replace('""', '"')


# JavaScript text with its strings and comments blanked, for names in the code itself
JS_SKIPPED = re.compile(r"//[^\n]*|/\*.*?\*/|'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"|`(?:\\.|[^`\\])*`", re.S)
JS_SIGNAL = re.compile(r"runtime\s*\.\s*signal\s*\(\s*(?:(['\"])(.*?)\1\s*\))?")

# Actions the browser refuses unless the player has just touched, clicked or pressed a key: the manual asks
# for each in a user input trigger, on the plugin-reference page named here. Request MIDI access is not
# among them: its page says some browsers allow it on startup, and the MIDI examples ask there first.
GESTURE_ACTIONS = {
    ("browser", "request-fullscreen"): "browser", ("browser", "request-install"): "browser",
    ("touch", "request-permission"): "touch", ("platforminfo", "request-wake-lock"): "platform-info",
    ("mouse", "request-pointer-lock"): "mouse", ("share", "share-text"): "share",
    ("clipboard", "request-paste-text"): "clipboard", ("clipboard", "request-paste-binary"): "clipboard",
    ("filechooser", "click"): "file-chooser", ("filesystem", "show-open-file-picker"): "filesystem",
    ("filesystem", "show-save-file-picker"): "filesystem", ("filesystem", "show-folder-picker"): "filesystem",
    ("bluetooth", "request-device"): "bluetooth", ("bbcmicrobit", "request-device"): "bbc-micro-bit",
    ("gamerecorder", "start-screen-recording-2"): "video-recorder",
    ("speechrecognition", "request-speech-recognition"): "speech-recognition", ("googleplay", "sign-in"): "google-play",
}
INPUT_PLUGINS = {"touch", "mouse", "keyboard", "button", "textbox", "list", "sliderbar", "htmlelement"}

# Pathfinding (manual: behavior-reference/pathfinding.md). With Obstacles set to Solids the obstacle map is
# built once at startup, so creating, destroying, moving or resizing a Solid, switching its Solid off or
# changing a Solid tilemap's tiles leaves paths routed round the old map until a Regenerate action runs.
SOLID_CHANGES = {"destroy", "set-x", "set-y", "set-position", "set-position-to-another-object", "move-forward",
                 "move-at-angle", "set-width", "set-height", "set-size", "erase-tile", "set-tile", "erase-tile-range",
                 "set-tile-range", "set-tile-with-brush", "erase-tile-with-brush", "set-tile-with-brush-by-name",
                 "erase-tile-with-brush-by-name", "set-tile-with-patch-brush", "erase-tile-with-patch-brush",
                 "set-tile-with-patch-brush-by-name", "erase-tile-with-patch-brush-by-name"}
REGENERATE = {"regenerate-obstacle-map", "regenerate-region", "regenerate-region-around-object"}
# Is overlapping between a Platform object and a Solid
# (Construct3-Cookbook/guides/behaviors/platform.md): the
# Platform behavior pushes its object out of every enabled Solid each tick, so the two touch and do not overlap.
# On collision still fires, because the behavior registers the collision as it pushes out (exported c3runtime.js,
# Platform: PushOutSolidAxis, then RegisterCollision). An object that something else moves, or a Solid switched
# off by another event, can overlap, so neither is a finding.
MOVES = {"set-x", "set-y", "set-position", "set-position-to-another-object", "move-forward", "move-at-angle",
         "set-width", "set-height", "set-size"}
MOVERS = {"tween", "bullet", "moveto", "sin", "pin", "physics", "eightdir", "car", "tilemovement", "orbit",
          "follow", "dragndrop", "custom", "turret", "rotate"}
# A Bullet object the events fire that nothing removes once it misses flies on outside the layout forever, and
# the instances pile up (manual: behavior-reference/destroy-outside.md). It is removed by one of these behaviors,
# by a Destroy under a condition other than a hit, an input or a plain pick (a position, a timer, a Wait before
# it), or by hitting a Solid or a Tilemap, which in the official examples are the walls and ground that stop it.
HITS = {"on-collision-with-another-object", "is-overlapping-another-object", "is-overlapping-at-offset"}
INPUTS = {"keyboard", "mouse", "touch", "gamepad"}
PLAIN_PICKS = {"pick-nth-instance", "pick-random-instance", "pick-all", "for-each", "trigger-once", "every-tick"}
REMOVERS = {"destroy", "wrap", "bound", "fade", "tween"}
PLACINGS = {"set-x", "set-y", "set-position", "set-position-to-another-object"}
USED_DESTROY = '{"type": "behavior", "id": "destroy", "name": "Destroy outside layout", "author": "Scirra", "bundled": false}'
# A Drag & Drop object dropped on another, tested by overlap or collision or snapped onto it, is drawn under
# it when the layout puts it lower in the Z order: on a lower layer, or listed before it on the same layer
# (manual: project-primitives/objects/instances.md "Z index", 0 is the bottom; layers.md: a layer's own
# objects come above its sub-layers). The dropped piece then disappears behind its target. An action that
# changes the Z order of either, or a Z elevation, decides it at runtime instead.
DROP_TESTS = {"is-overlapping-another-object", "is-overlapping-at-offset", "on-collision-another-object"}
DROP_SNAPS = {"set-position-to-another-object"}
RESTACKS = {"move-to-top", "move-to-bottom", "move-to-layer", "move-to-object", "set-z-elevation",
            "set-position-3d", "sort-z-order"}
# A found path is there only after On path found: Move along path, and the node expressions, in the same
# actions as Find path read the previous path, unless Wait for previous actions to complete stands between.
PATH_NODES = re.compile(r"(\w+)\s*\.\s*(\w+)\s*\.\s*(?:nodecount|nodexat|nodeyat)\b", re.I)
TRIGGER_ONCE = "trigger-once-while-true"  # the id of System Trigger once
# Conditions that keep an event from running every tick, beside the triggers.
PACING = {("system", "every-x-seconds"), ("system", TRIGGER_ONCE)}
# Simulate control holds a control for the tick it runs in (manual: behavior-reference.md "Custom controls", the
# input events must be continually true), so under a trigger the object moves one tick and stops. Behavior id ->
# the controls held, None for all. A Platform jump starts on one tick, and Tile movement takes one tick as a move
# to the next tile: the official examples simulate both under On key pressed.
HELD_CONTROLS = {"platform": {"left", "right"}, "eightdir": None, "car": None}
# The trigger a held control was put under -> the condition that holds while the input is held, and the
# trigger's parameters it keeps.
HOLDING = {("keyboard", "on-key-pressed"): ("key-is-down", ("key",)),
           ("keyboard", "on-key-code-pressed"): ("key-code-is-down", ("keycode",)),
           ("gamepad", "on-button-pressed"): ("is-button-down", ("gamepad", "button")),
           ("touch", "on-touched-object"): ("is-touching-object", ("object",))}
# Conditions that test values, which hold until an event changes them; an overlap, a key held or a running timer
# change as the game plays. A Start timer under these alone, in an event that runs every tick, starts over each tick.
# Else is left out: it holds while the event before it fails, which may test anything.
VALUE_TESTS = {("System", "compare-two-values"), ("System", "compare-eventvar"), ("System", "compare-boolean-eventvar"),
               ("System", "evaluate-expression"), ("System", "is-between-values"), ("System", "every-tick"),
               ("System", "for-each"), ("System", "for-each-ordered"), ("System", "pick-by-evaluate"),
               ("System", "pick-by-comparison"), ("System", "pick-all")}
INSTANCE_VALUE_TESTS = {"compare-instance-variable", "is-boolean-instance-variable-set"}
# An object's expression in a value test, Player.X or Functions.canMove, reads what changes as the game plays;
# only Count and the variables wait for an event to change them.
OBJECT_EXPRESSION = re.compile(r"(?<![\w.])([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)")
# Actions that change what a value test reads: a variable set or toggled, keyed by the parameter that names it.
# Add and Subtract are left out: a count stepped each tick still starts the timer over on every tick until its
# test fails.
SETS = {"set-eventvar-value": "variable", "set-boolean-eventvar": "variable", "toggle-boolean-eventvar": "variable",
        "set-instvar-value": "instance-variable", "set-boolean-instvar": "instance-variable",
        "toggle-boolean-instvar": "instance-variable"}
# What an object action changes and a condition tests, as the words an expression reads it by: the state a
# switch is kept in (check_undone).
STATE_SETS = {"set-animation-frame": "animationframe", "set-animation": "animationname", "set-visible": "isvisible",
              "set-instvar-value": None, "add-to-instvar": None, "subtract-from-instvar": None,
              "set-boolean-instvar": None, "toggle-boolean-instvar": None}
STATE_TESTS = {"compare-animation-frame": "animationframe", "is-animation-playing": "animationname",
               "is-visible": "isvisible"}
# System actions after which the event does not run again in the next tick.
LEAVES = {"set-group-active", "go-to-layout", "go-to-layout-by-name", "restart-layout", "go-to-nextprevious-layout"}
# Actions that flip a variable between two values: Toggle, and a Set of the variable to N - x, -x, x * -1,
# x = a ? b : a or x <> a ? a : b, with literal values. An event that runs every tick flips it back on the
# next tick.
TOGGLES = {"toggle-boolean-eventvar": "variable", "toggle-boolean-instvar": "instance-variable"}
FLIPS = {"set-eventvar-value": "variable", "set-instvar-value": "instance-variable"}
LITERAL = r'-?\d+(?:\.\d+)?|"(?:[^"]|"")*"'
# The comparison ids of Compare two values: 0 =, 1 ≠, 2 <, 3 ≤, 4 >, 5 ≥.
COMPARISONS = {0: "=", 1: "<>", 2: "<", 3: "<=", 4: ">", 5: ">="}
# How a condition tests that none of a type is left: X.Count or X.PickedCount = 0, ≤ 0 or < 1, with the operands
# in either order.
NONE_LEFT = re.compile(r"(\w+)\.(count|pickedcount)(?:=0|<=0|<1)|(?:0=|0>=|1>)(\w+)\.(count|pickedcount)", re.I)
# Sprite Font (manual: plugin-reference/sprite-font.md) draws a character outside its Character set as an
# empty space; with Enable BBCode on, the tags are markup, not characters, and \[ is a bracket.
SPRITE_FONT_TEXT = ("set-text", "append-text", "typewriter-text")
BBCODE_TAG = re.compile(r"(?<!\\)\[/?[a-z]+(?:=[^\]]*)?\]", re.I)
# Set text to replace(Self.Text, "###", ProjectVersion): the object's own text is a template, and "###" is
# replaced before the font draws it.
OWN_TEXT_REPLACED = re.compile(r'replace\s*\(\s*(\w+)\s*\.\s*text\s*,\s*("(?:[^"]|"")*")', re.I)
# What the r495.2 editor reads for a Sprite Font instance that leaves these properties out, asked of the
# editor on 2026-10-03. They fit the editor's own font image; the Character set maps its cells from the
# top-left. Enable BBCode left out reads as off.
SPRITE_FONT_DEFAULTS = {
    "character-set": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,;:?!-_~#\"'&()[]|`\\/@"
                     "°+=*$£€<>",
    "character-width": 16,
    "character-height": 16,
}
# Actions that name an effect by its name on the object, the layer or the layout. A name the target lacks
# runs and changes nothing.
EFFECT_ACTIONS = {"set-effect-parameter", "set-effect-enabled", "set-layer-effect-parameter", "set-layer-effect-enabled",
                  "set-layout-effect-parameter", "set-layout-effect-enabled"}


def call_arguments(text: str, end: int) -> int:
    """How many arguments the call that follows text[:end] passes, counting the commas
    outside nested parentheses; 0 when no parenthesis follows. Text literals are
    blanked to "" first, so a comma inside one is not counted."""
    i = end
    while i < len(text) and text[i].isspace():
        i += 1
    if i >= len(text) or text[i] != "(":
        return 0
    depth, count, start = 0, 1, i + 1
    for j in range(i, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return count if text[start:j].strip() else 0
        elif text[j] == "," and depth == 1:
            count += 1
    return count  # not closed: the editor names that syntax error itself


def arguments_end(text: str, i: int) -> int:
    """The index just after the parenthesis that closes the one at text[i]; text literals
    are blanked to "" first, so a parenthesis inside one does not count."""
    depth = 0
    for j in range(i, len(text)):
        depth += {"(": 1, ")": -1}.get(text[j], 0)
        if depth == 0:
            return j + 1
    return len(text) + 1  # not closed


# find(text, find) and findcase take the text to search first. A one-character literal there
# with an expression after it is the other way round: find("^", LASTPOP) is -1 unless LASTPOP
# is "^" or empty. None of the 23 find calls of the 524 official examples has a literal first.
FIND_CALL = re.compile(r'(?<![\w.])(find|findcase)\s*\(\s*("(?:[^"]|"")*")\s*,', re.I)


def argument_at(expr: str, i: int) -> str:
    """The argument that starts at expr[i], up to the comma or parenthesis that ends it
    outside text literals and nested calls."""
    depth, j = 0, i
    while j < len(expr):
        c = expr[j]
        if c == '"':
            lit = STRING_LITERAL.match(expr, j)
            j = lit.end() if lit else len(expr)
            continue
        if c == "(":
            depth += 1
        elif c in "),":
            if depth == 0:
                break
            if c == ")":
                depth -= 1
        j += 1
    return expr[i:j].strip()


def arguments_from(expr: str, i: int) -> list[str]:
    """Every argument of the call whose opening parenthesis ends just before expr[i]."""
    args = []
    while True:
        arg = argument_at(expr, i)
        args.append(arg)
        j = expr.index(arg, i) + len(arg) if arg else i
        while j < len(expr) and expr[j] not in ",)":
            j += 1
        if j >= len(expr) or expr[j] == ")":
            return args
        i = j + 1


def outside_literals(expr: str, matches: Iterable[re.Match]) -> list[re.Match]:
    """The regex matches that do not start inside a text literal of expr."""
    literals = [m.span() for m in STRING_LITERAL.finditer(expr)]
    return [m for m in matches if not any(a < m.start() < b for a, b in literals)]


def top_level_operator(expr: str) -> bool:
    """Whether expr has a comparison or a logical operator outside literals and parentheses,
    after its outer parentheses are taken off: a value that is true or false."""
    text = STRING_LITERAL.sub('""', expr).strip()
    while text.startswith("(") and text.endswith(")") and argument_at(text, 1) == text[1:-1].strip():
        text = text[1:-1].strip()
    depth = 0
    for c in text:
        depth += (c == "(") - (c == ")")
        if depth == 0 and c in "=<>&|":
            return True
    return False


# Three habits of a generated card game, none in the 565 event sheets of the 524 official
# examples (event-sheet-design-guidance.md, 2026-10-04): chooseindex(condition, a, b) as an
# if-else, which the examples write condition ? b : a; sibling events dispatching on
# find(<same text>, "<code>"); and a value looked up through two text literals,
# mid("FEMAW", find("WFAEM", X), 1), where the examples step a number with %.
CHOOSEINDEX_CALL = re.compile(r'(?<![\w.])chooseindex\s*\(', re.I)
FIND_LITERAL_SECOND = re.compile(r'(?<![\w.])(find|findcase)\s*\(', re.I)
MID_OF_LITERAL = re.compile(r'(?<![\w.])mid\s*\(\s*("(?:[^"]|"")*")\s*,', re.I)


def script_text(script) -> str:
    return "\n".join(script) if isinstance(script, list) else script if isinstance(script, str) else ""


def bare_name_in(code: str, name: str) -> bool:
    """name read as a variable of the script: not a member, a key or the script's own declaration."""
    n = re.escape(name)
    declared = (rf"\b(?:let|const|var|function|class)\s+{n}\b|(?<![\w$.]){n}\s*=>"
                rf"|\((?:\s*[\w$]+\s*,)*\s*{n}\s*(?:,\s*[\w$]+\s*)*\)\s*=>"
                # destructured, as in const {{ Value }} = localVars
                rf"|\b(?:let|const|var)\s*(?:\{{[^}}]*|\[[^\]]*)(?<![\w$.]){n}(?![\w$])(?!\s*:(?!:))")
    if re.search(declared, code):
        return False
    return re.search(rf"(?<![\w$.]){re.escape(name)}(?![\w$])(?!\s*:(?!:))", code) is not None


def member_types(families: dict, obj: str) -> list[str]:
    """The object types a family stands for, or the object type itself."""
    return families[obj].get("members", []) if obj in families else [obj]


def replaced_in_own_text(sheets: dict, families: dict) -> dict[str, set[str]]:
    """Object type -> the parts of its own text that a Set text replaces, "###" for
    replace(Self.Text, "###", ProjectVersion): a layout text that holds them is a template the events fill in.
    An action of a family replaces them in each member."""
    found: dict[str, set[str]] = {}

    def walk(events: list) -> None:
        for ev in events:
            if not isinstance(ev, dict):
                continue
            for a in ev.get("actions") or []:
                obj = a.get("objectClass") if isinstance(a, dict) and a.get("id") == "set-text" else None
                text = (a.get("parameters") or {}).get("text") if obj else None
                if not isinstance(obj, str) or not isinstance(text, str):
                    continue
                for m in OWN_TEXT_REPLACED.finditer(text):
                    if m.group(1).lower() in ("self", obj.lower()):
                        for t in member_types(families, obj):
                            found.setdefault(t, set()).add(unquote(m.group(2)))
            if isinstance(ev.get("children"), list):
                walk(ev["children"])

    for sheet in sheets.values():
        if isinstance(sheet.get("events"), list):
            walk(sheet["events"])
    return found


def joined_literals(expr: str) -> list[str]:
    """The text literals an expression joins with & at its top level, unquoted: "Score: " & Score gives
    ["Score: "]; a literal that is an argument or a branch of a condition is left out."""
    parts, depth, start, quoted = [], 0, 0, False
    for i, ch in enumerate(expr):
        if ch == '"':
            quoted = not quoted  # a doubled quote inside a literal toggles twice
        elif not quoted and ch == "(":
            depth += 1
        elif not quoted and ch == ")":
            depth -= 1
        elif not quoted and depth == 0 and ch == "&":
            parts.append(expr[start:i])
            start = i + 1
    parts.append(expr[start:])
    return [unquote(p.strip()) for p in parts if is_literal(p.strip())]


def bare(value, options) -> str:
    """A combo item, a layout, an object and a variable are written bare; only an
    expression carries quotes. Says so when stripping the quotes gives a match."""
    if isinstance(value, str) and len(value) > 1 and value[0] == value[-1] == '"' and value[1:-1] in options:
        return f"; write it bare, \"{value[1:-1]}\": only an expression parameter carries inner quotes"
    return ""


def first_few(names: list[str], n: int) -> str:
    """The first n names, joined with commas, and how many more there are."""
    return ", ".join(names[:n]) + (f" and {len(names) - n} more" if len(names) > n else "")


def number_of(value) -> float | None:
    """A parameter written as a plain number, "1" or 1.0; None for any other expression."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def effect_names(holder: dict) -> set[str]:
    """The names of the effects an object type, family, layer or layout carries."""
    return {e["name"] for e in holder.get("effectTypes", []) if isinstance(e.get("name"), str)}


def contrast_ratio(a: list, b: list) -> float:
    """WCAG 2.2 contrast of two colours written as the editor writes them, 0 to 1 per channel."""
    def luminance(c: list) -> float:
        r, g, b_ = (v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in map(float, c[:3]))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b_
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def hex_colour(c: list) -> str:
    return "#" + "".join(f"{round(min(max(float(v), 0), 1) * 255):02x}" for v in c[:3])


def layer_instances(layers: list) -> Iterator[dict]:
    """Every instance on these layers and their sublayers, in the order the file lists them."""
    for layer in layers if isinstance(layers, list) else []:
        if isinstance(layer, dict):
            yield from (i for i in layer.get("instances") or [] if isinstance(i, dict))
            yield from layer_instances(layer.get("subLayers"))


def frames_of(folder: dict, prefix: str = "") -> Iterator[tuple[str, dict]]:
    """(file name without its extension, frame) for every frame of an animations folder."""
    for anim in folder.get("items", []):
        for i, fr in enumerate(anim["frames"]):
            yield f"{prefix}{anim['name'].lower()}-{i:03d}", fr
    for sub in folder.get("subfolders", []):
        yield from frames_of(sub, prefix)


STYLE_RUN = 8  # actions in a row without a comment action
STYLE_TREE = 3  # sub-event levels below an event, when every leaf calls the same function
STYLE_LADDER = 5  # sibling events of one shape, their conditions and actions the same, only the values differ
COUNTDOWN_ON_INSTANCE = ("subtract-from-instvar", "add-to-instvar", "set-instvar-value")


def declarations(events: list) -> Iterator[dict]:
    """Every variable and function parameter declared in a list of events and its sub-events."""
    for ev in events:
        if not isinstance(ev, dict):
            continue
        if ev.get("eventType") == "variable":
            yield ev
        yield from ev.get("functionParameters") or []
        if isinstance(ev.get("children"), list):
            yield from declarations(ev["children"])


class Holder(NamedTuple):
    """What holds the trigger of an event branch."""
    name: str  # "Touch:on-touched-object", or "the function AddScore"
    fires: bool  # a trigger condition, as opposed to a function standing in for one

    @property
    def text(self) -> str:
        return f"an event that already has the trigger {self.name}" if self.fires \
            else f"{self.name}, which counts as a trigger"
