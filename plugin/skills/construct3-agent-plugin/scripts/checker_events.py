"""The checks of one event that walk() runs as it enters it: the names in scope and
the runtime traps. A part of check_project.Checker, which holds the state they read."""
import json
import re

import c3project as c3
from c3project import LOWER, STRING_LITERAL, describe
from checker_common import (
    IDENT, NUMBER, SHADOW_SUFFIX, free_name, variable_kind, case_aside, params_of, is_literal, unquote,
    JS_SKIPPED, JS_SIGNAL, GESTURE_ACTIONS, INPUT_PLUGINS, SOLID_CHANGES, REGENERATE, MOVES, MOVERS, HITS,
    INPUTS, PLAIN_PICKS, REMOVERS, PLACINGS, USED_DESTROY, DROP_TESTS, DROP_SNAPS, RESTACKS, PATH_NODES,
    TRIGGER_ONCE, PACING, HELD_CONTROLS, HOLDING, VALUE_TESTS, INSTANCE_VALUE_TESTS, OBJECT_EXPRESSION, SETS,
    LEAVES, TOGGLES, FLIPS, LITERAL, COMPARISONS, NONE_LEFT, script_text, bare_name_in, layer_instances,
)


class EventChecks:
    @staticmethod
    def variable_named(name, scope: dict) -> dict | None:
        """The variable a name refers to in scope, compared without case; enter keeps the
        scope as the editor binds the names."""
        if not isinstance(name, str):
            return None
        return next((v for k, v in scope.items() if LOWER(k) == LOWER(name)), None)

    def enter(self, scope: dict, var: dict, outer: dict, where: str, holder: str) -> None:
        """Bring a local or a function parameter into scope as the editor binds its name, and
        check the name against the variables in scope, compared without case. holder: the
        event that holds its list, "group Movement", "event 5" or "function launch"; outer:
        the scope as it was before this list.

        A local beside a global keeps its name and hides the global in its scope. As it opens
        the project, the editor renames a local or parameter whose name matches another of its
        list or of a scope that holds it: the one that comes later in the sheet gets a number
        (speed to speed2), and both names then refer to the other one wherever it is in scope.
        Probed in the r495.2 and r504 editors (docs/decisions/checker-editor-load-rules.md)."""
        name = var.get("name")
        if not isinstance(name, str):
            return
        visible = holder if variable_kind(var) == "parameter" or holder.startswith("group ") \
            else f"the sub-events of {holder}"
        self.declared[id(var)] = (where, f"the {variable_kind(var)} {name} of {holder}", visible)
        same = next((v for k, v in scope.items() if LOWER(k) == LOWER(name) and outer.get(k) is not v), None)
        if same is not None:
            self.renamed.add(id(var))
            self.check_declared_once(var, same, where, "declared above it in the same list of events",
                                     free_name(name, scope))
            return
        other = self.variable_named(name, outer)
        if other is not None and id(other) not in self.renamed and id(other) not in self.global_ids \
                and self.load_order.get(id(var), 0) > self.load_order.get(id(other), 0):
            self.renamed.add(id(var))
            self.check_renamed(var, other, where, free_name(name, scope))
            return
        for k in [k for k in scope if scope[k] is other]:
            del scope[k]
        scope[name] = var
        if other is None or id(other) in self.renamed:
            return
        if id(other) in self.global_ids:
            self.check_shadow(var, other, where, visible)
        else:
            self.renamed.add(id(other))
            self.check_outer_renamed(other, var, free_name(other["name"], scope))

    def check_renamed(self, var: dict, other: dict, where: str, new: str) -> None:
        """A local or parameter declared after a local or parameter of its name whose scope
        holds it: the editor renames it, and its uses refer to the other one."""
        name, desc = var["name"], self.declared[id(other)][1]
        kept = other["name"] if other["name"] != name else f"that {variable_kind(other)}"
        lost = ", and the value a call passes for it is lost" if variable_kind(var) == "parameter" else ""
        self.err(f"{where}: {name} has the name of {desc}{case_aside(name, other['name'])}, and {kept} is in "
                 f"scope where {name} is declared, before it. The editor renames {name} to {new} when it opens "
                 f"the project. Every use of {name} then refers to {kept}{lost}. Rename {name} and its uses, for "
                 f"example {name}{SHADOW_SUFFIX.get(var.get('type'), 'Value')}")

    def check_outer_renamed(self, var: dict, inner: dict, new: str) -> None:
        """An outer local declared after an inner local or parameter of its name: the editor
        renames the outer one, so its name refers to the inner one inside the inner one's
        scope and to nothing elsewhere."""
        where = self.declared[id(var)][0]
        name = var["name"]
        _, desc, visible = self.declared[id(inner)]
        kept = inner["name"] if inner["name"] != name else f"that {variable_kind(inner)}"
        self.err(f"{where}: {name} has the name of {desc}{case_aside(name, inner['name'])}, which is declared "
                 f"before it, inside the scope of {name}. The editor renames {name} to {new} when it opens the "
                 f"project. In {visible}, {name} then refers to {kept}, and elsewhere an expression that names "
                 f"{name} stops the open with \"Unknown expression '{name}': This is not a system expression or "
                 f"variable name in this scope\". Rename {name} and its uses, for example "
                 f"{name}{SHADOW_SUFFIX.get(var.get('type'), 'Value')}")

    def check_declared_once(self, var: dict, earlier: dict, where: str, first: str, new: str = "") -> None:
        """Two variables of one list whose names match without case, which the editor's own
        dialogs never allow. A file that has them opens, and every use of either name refers
        to the first. The editor renames the second local as it opens the project, to new:
        STEP to STEP2. A second global keeps its name, and only a script reads it. first:
        where the first one is, as a phrase."""
        name, other = var["name"], earlier["name"]
        if other == name:
            renames = f" The editor renames this one to {new} when it opens the project." if new else ""
            self.err(f"{where}: {name} is declared again; the first {name} is {first}.{renames} Every use of the "
                     f"name refers to the first, so this declaration is never read or written. Delete it"
                     + ("; a global is visible from every sheet" if id(var) in self.global_ids else ""))
            return
        renames = f" The editor renames {name} to {new} when it opens the project." if new else ""
        constant = (f"; an action that writes {name} stops the editor with \"event variable {name} is constant\""
                    if earlier.get("isConstant") else "")
        self.err(f"{where}: {name} has the name of {other}, {first}, once case is ignored.{renames} Every use of "
                 f"either name refers to {other}, so {name} is never read or written{constant}. Rename it and its "
                 f"uses, for example {name}{SHADOW_SUFFIX.get(var.get('type'), 'Value')}")

    def check_parameter_renamed(self, param: dict, last: dict, where: str, new: str) -> None:
        """Two parameters of one function whose names match without case. The editor renames
        every one but the last as it opens the project, amount to amount2 and Amount to
        Amount3 before a third AMOUNT, and every use of the name refers to the last."""
        name, kept = param["name"], last["name"]
        said = (f"{name} is declared again by a later parameter of the same function" if name == kept else
                f"{name} has the name of {kept}, a later parameter of the same function, once case is ignored")
        self.err(f"{where}: {said}. The editor renames {name} to {new} when it opens the project. Every use of "
                 f"the name refers to {'the later one' if name == kept else kept}, so {name} is never read or "
                 f"written, and the value a call passes for it is lost. Rename it and its uses, for example "
                 f"{name}{SHADOW_SUFFIX.get(param.get('type'), 'Value')}")

    def check_callable_name(self, ev: dict, kind: str, name: str, where: str) -> None:
        """Functions share one namespace, and the custom actions of an object another, compared
        without case. As it opens the project, the editor renames the one that comes later, a
        number added (Beep to Beep2), and a call by either name runs the first."""
        owner = "" if kind == "function" else str(ev.get("objectClass"))
        key = (owner, LOWER(name))
        first = self.callables.setdefault(key, (name, where))
        if first[0] == name:
            return
        of = f"{owner}." if owner else ""
        new = free_name(name, [n for (o, _), (n, _) in self.callables.items() if o == owner])
        self.err(f"{where}: {kind} {of}{name} has the name of the {kind} {of}{first[0]} at {first[1]} once case is "
                 f"ignored. The editor renames it to {new} when it opens the project, and a call to {name} runs "
                 f"{first[0]}, so this {kind} never runs. Rename it and its calls so that the two names differ by "
                 f"more than case")

    def note_signal(self, ace: dict, where: str) -> None:
        if ace.get("objectClass") != "System" or ace.get("id") not in ("signal", "wait-for-signal", "on-signal"):
            return
        tag = (ace.get("parameters") or {}).get("tag")
        if ace["id"] != "signal":
            if is_literal(tag):
                self.awaited.append((unquote(tag).lower(), ace["id"], where))
        elif self.signalled is not None:
            self.signalled = self.signalled | {unquote(tag).lower()} if is_literal(tag) else None

    def check_script(self, script, scope: dict, where: str) -> None:
        """A script reads an event's locals and parameters as localVars.name; a bare name
        is a ReferenceError when the event runs. Signals it raises count as Signal actions."""
        text = script_text(script)
        for m in JS_SIGNAL.finditer(text):
            if self.signalled is not None:
                self.signalled = self.signalled | {m.group(2).lower()} if m.group(1) else None
        code = JS_SKIPPED.sub('""', text)
        for name, var in scope.items():
            if id(var) not in self.global_ids and isinstance(name, str) and bare_name_in(code, name):
                self.warn(f"{where}: the script reads {name} as a bare name, which it does not know; an event's "
                          f"local or parameter is localVars.{name} in a script")

    def reads_input(self, ev: dict) -> bool:
        return any(self.p.plugin_of.get(c.get("objectClass"), "").lower() in INPUT_PLUGINS
                   for c in ev.get("conditions", []))

    def check_gesture(self, action: dict, by_input: bool | None, where: str) -> None:
        """by_input: whether the action's event or one above it tests touch, mouse, keyboard or a form
        control; None in a function or custom action, which an input trigger may call."""
        page = GESTURE_ACTIONS.get((self.p.plugin_of.get(action.get("objectClass"), "").lower(), action.get("id")))
        if page and by_input is False:
            self.warn(f"{where}: {describe(action)} runs with no touch, click or key in its event or above it, "
                      f"and the browser refuses it there; move it into an event with a trigger such as Touch On "
                      f"tap, Mouse On click or Keyboard On key pressed (manual: plugin-reference/{page}.md)")

    def pacing(self, ev: dict) -> set[str]:
        """What keeps the event from running every tick: "trigger", "every" for Every X seconds, "once" for
        Trigger once. A condition of an addon without a schema is a trigger when its id starts with on-."""
        kinds = set()
        for c in ev.get("conditions", []):
            entry = self.p.ace_entry("conditions", c)
            if entry.get("isTrigger") if entry else str(c.get("id", "")).startswith("on-"):
                kinds.add("trigger")
            elif (self.p.plugin_of.get(c.get("objectClass"), "").lower(), c.get("id")) in PACING:
                kinds.add("once" if c.get("id") == TRIGGER_ONCE else "every")
        return kinds

    def paces(self, ev: dict) -> bool:
        """Whether a condition of the event keeps it from running every tick."""
        return bool(self.pacing(ev))

    def is_solid(self, obj) -> bool:
        """A type with the Solid behavior, or a family that is one or has one among its members."""
        p = self.p
        names = [obj] + (p.families[obj].get("members", []) if obj in p.families else [])
        return any(b.lower() == "solid" for n in names if n in p.plugin_of for b in p.behaviors_of(n).values())

    def check_pathfinding(self, action: dict, where: str, found: dict[str, str], paced: bool | None) -> None:
        """found: object -> the name of the Pathfinding behavior a Find path earlier in the same actions
        started on it, cleared by Wait for previous actions to complete. paced: as check_block's."""
        p = self.p
        obj, ace_id, params = action.get("objectClass"), action.get("id"), action.get("parameters", {})
        if obj not in p.plugin_of or not isinstance(params, dict):
            return  # a comment, a script, a function call or a custom action
        behavior = p.behaviors_of(obj).get(action.get("behaviorType", ""), "").lower()
        if obj == "System" and ace_id == "wait-for-previous-actions":
            found.clear()
        made = params.get("object-to-create") if (obj, ace_id) == ("System", "create-object") \
            else params.get("object") if ace_id == "spawn-another-object" else None
        if (isinstance(made, str) and self.is_solid(made)) \
                or (ace_id in SOLID_CHANGES and not behavior and self.is_solid(obj)) \
                or (behavior == "solid" and ace_id == "set-enabled"):
            self.solid_changes.append(where)
        if behavior == "pathfinding" and ace_id in REGENERATE:
            self.regenerated = True
        if behavior == "pathfinding" and ace_id == "find-path":
            found[obj] = action["behaviorType"]
            if paced is False:
                # A kind of its own, so that edit_sheet.py refuses it in an event a plan creates.
                every = json.dumps({"id": "every-x-seconds", "objectClass": "System",
                                    "parameters": {"interval-seconds": "0.5"}})
                self.p.findings.style_finding(
                    "pathfinding", f"{where}: Find path runs every tick; move it into the trigger that sets the "
                                   f"target, such as Touch On tap or Mouse On click, or add System Every 0.5 seconds "
                                   f"to its event, {every}. With no trigger, Every X seconds or Trigger once in its "
                                   f"event or above it, the manual warns that pathfinding every tick takes extremely "
                                   f"high CPU and delays every other object's path "
                                   f"(manual: behavior-reference/pathfinding.md)")
            return
        early = obj in found and (behavior == "pathfinding" and ace_id == "move-along-path"
                                  or behavior == "moveto" and ace_id == "move-along-pathfinding-path")
        for m in PATH_NODES.finditer(" ".join(v for v in params.values() if isinstance(v, str))):
            owner = obj if LOWER(m.group(1)) == "self" else p.objects_lower.get(LOWER(m.group(1)))
            early |= owner in found and LOWER(m.group(2)) == LOWER(found[owner])
        if early:
            self.warn(f"{where}: {describe(action)} reads the path a Find path above it in the same actions has only "
                      f"started: the path is there after On path found, and until then this reads the previous "
                      f"one. Put System Wait for previous actions to complete between them, or move this into "
                      f"an On path found event (manual: behavior-reference/pathfinding.md)")

    def behavior_of(self, ace: dict) -> str:
        """The behavior id an ACE belongs to, lower case, or "" for the object's own."""
        obj = ace.get("objectClass")
        return self.p.behaviors_of(obj).get(ace.get("behaviorType", ""), "").lower() if obj in self.p.plugin_of else ""

    def check_held_control(self, action: dict, where: str, held: tuple, paced: bool | None) -> None:
        """Simulate control of a movement held down, under a trigger: the control holds for the one tick the
        trigger fires. held: the conditions of the event and of those above it."""
        controls = HELD_CONTROLS.get(self.behavior_of(action), ())
        control = params_of(action).get("control")
        if action.get("id") != "simulate-control" or paced is None or (controls is not None and control not in controls):
            return
        trigger = next((c for c in held if (self.p.ace_entry("conditions", c) or {}).get("isTrigger")), None)
        if trigger is None:
            return
        plugin = self.p.plugin_of.get(trigger.get("objectClass"), "").lower()
        hold = HOLDING.get((plugin, trigger.get("id")))
        if hold:
            kept = {k: v for k, v in params_of(trigger).items() if k in hold[1]}
            instead = {"id": hold[0], "objectClass": trigger["objectClass"], **({"parameters": kept} if kept else {})}
            fix = f"Put this action in an event whose condition is {trigger['objectClass']} {hold[0]} in place of the " \
                  f"trigger, {json.dumps(instead, ensure_ascii=False)}"
        else:
            example = json.dumps({"id": "key-is-down", "objectClass": "Keyboard", "parameters": {"key": 87}})
            fix = f"Put this action in an event whose condition holds while the input is held, such as {example} " \
                  f"with the key's code"
        self.p.findings.style_finding(
            "control", f"{where}: Simulate control {control} runs only in the tick that {describe(trigger)} fires, "
                       f"so {action.get('objectClass')} moves for one tick and stops. {fix} "
                       f"(manual: behavior-reference.md \"Custom controls\")")

    @staticmethod
    def words_of(aces: list) -> set[str]:
        """Every word in the parameters of these conditions or actions, lower case: the variables, objects and
        expressions they read."""
        words = set()
        for ace in aces:
            for value in params_of(ace).values():
                if isinstance(value, str):
                    words |= {w.lower() for w in IDENT.findall(value)}
        return words

    def check_timer_restart(self, action: dict, where: str, line: tuple, held: tuple, paced: bool | None) -> None:
        """Start timer in an event that runs every tick, whose conditions test values that the actions of its
        branch leave alone: each tick starts the timer over, and On timer never fires. A cooldown tests Is timer
        running, and an overlap, a key held or a position changes as the game plays, so those are left alone.
        line: the event and those above it, held: their conditions."""
        if paced is not False or action.get("id") != "start-timer" or self.behavior_of(action) != "timer":
            return
        for c in held:
            value_test = (c.get("objectClass"), c.get("id")) in VALUE_TESTS or c.get("id") in INSTANCE_VALUE_TESTS
            moving = any(m.group(2).lower() != "count" for value in params_of(c).values() if isinstance(value, str)
                         for m in OBJECT_EXPRESSION.finditer(value))
            if c.get("id") == "is-timer-running" or not value_test or moving:
                return
        actions = [a for ev in line for a in ev.get("actions", []) if isinstance(a, dict)]
        changed = {str(params_of(a).get(SETS[a["id"]], "")).lower() for a in actions if a.get("id") in SETS}
        changed |= {str(a.get("objectClass")).lower() for a in actions if a.get("id") == "destroy"}
        changed |= {made.lower() for made in map(self.made_by, actions) if made}
        if changed & self.words_of(list(held)) or any("callFunction" in a or "customAction" in a for a in actions) \
                or any(a.get("objectClass") == "System" and a.get("id") in LEAVES for a in actions):
            return
        tag = params_of(action).get("tag", '""')
        once = json.dumps({"id": TRIGGER_ONCE, "objectClass": "System"})
        self.p.findings.style_finding(
            "timer", f"{where}: Start timer {tag} runs every tick. No trigger, Every X seconds or Trigger once is in "
                     f"its event or above it, and its actions leave its conditions true. So the timer starts over each "
                     f"tick, and On timer {tag} never fires. Add System Trigger once as the last condition of its "
                     f"event, {once}, or start the timer in the event that begins the countdown")

    @staticmethod
    def flipped(a: dict) -> str | None:
        """The variable an action flips between two values, as TOGGLES and FLIPS name them; None for any other
        action. An instance variable is read as Self.x or through its object's name, an event variable bare."""
        params = params_of(a)
        if a.get("id") in TOGGLES:
            name = params.get(TOGGLES[a["id"]])
            return name if isinstance(name, str) else None
        name, value = params.get(FLIPS.get(a.get("id"), "")), params.get("value")
        if not isinstance(name, str) or not isinstance(value, str):
            return None
        x = re.escape(name) if a["id"] == "set-eventvar-value" else \
            rf"(?:self|{re.escape(str(a.get('objectClass')))})\.{re.escape(name)}"
        v = re.sub(r"\s+", "", value)
        forms = (rf"\(?-?\d+(?:\.\d+)?-{x}\)?", rf"-\(?{x}\)?", rf"\(?{x}\)?\*\(?-1\)?", rf"\(?-1\)?\*\(?{x}\)?")
        if any(re.fullmatch(f, v, re.I) for f in forms):
            return name
        m = re.fullmatch(rf"\(?{x}(=|<>)({LITERAL})\)?\?({LITERAL}):({LITERAL})", v, re.I)
        # x = a ? b : a and x <> a ? a : b go back to a on the next run
        if m and m.group(3) != m.group(4) and m.group(2) == (m.group(4) if m.group(1) == "=" else m.group(3)):
            return name
        return None

    @staticmethod
    def actions_below(ev: dict) -> list[dict]:
        """The actions of an event and of all its sub-events."""
        return [a for a in ev.get("actions") or [] if isinstance(a, dict)] + \
            [a for k in ev.get("children") or [] if isinstance(k, dict) for a in EventChecks.actions_below(k)]

    def writes(self, actions: list, seen: set[int]) -> set[str] | None:
        """What these actions change that a condition may test, lower case: the variables they set or toggle,
        and the types they create or destroy. The functions and custom actions they call count with their
        events. None when one leaves the group or the layout. seen: the blocks already read."""
        out: set[str] = set()
        for a in actions:
            if a.get("objectClass") == "System" and a.get("id") in LEAVES:
                return None
            if a.get("id") in SETS:
                out.add(str(params_of(a).get(SETS[a["id"]], "")).lower())
            made = self.made_by(a)
            if a.get("id") == "destroy" or made:
                out.add(str(made or a.get("objectClass")).lower())
            hit = self.called(a)
            if hit and id(hit[1]) not in seen:
                seen.add(id(hit[1]))
                below = self.writes(self.actions_below(hit[1]), seen)
                if below is None:
                    return None
                out |= below
        return out

    @staticmethod
    def tests_a_value(c: dict) -> bool:
        """Whether a condition tests a value that holds until an event changes it, a variable or Count, or is
        Else or Trigger once; an input, an overlap, a position or a function changes as the game plays."""
        if c.get("objectClass") == "System" and c.get("id") in ("else", TRIGGER_ONCE):
            return True
        moving = any(m.group(2).lower() != "count" for value in params_of(c).values() if isinstance(value, str)
                     for m in OBJECT_EXPRESSION.finditer(value))
        return ((c.get("objectClass"), c.get("id")) in VALUE_TESTS or c.get("id") in INSTANCE_VALUE_TESTS) \
            and not moving

    def check_flip(self, action: dict, where: str, line: tuple, paced: bool | None) -> None:
        """A variable flipped in an event that runs every tick: the event runs again on the next tick and flips
        it back. Under Trigger once alone, with conditions that test values, the flip happens once each time
        they turn true, not once per input. That is a warning edit_sheet.py does not refuse, since a flip once a
        round is sound. A branch passes when its actions change what its conditions test: they set a variable,
        create or destroy a type, or act on an object a condition is on or reads (Player.X, Grid.At). It also
        passes when they leave the group or layout. An event that starts with Else also tests the event it
        answers. line: the event and those above it."""
        name = self.flipped(action) if paced is not None else None
        if name is None:
            return
        kinds = set().union(*(self.pacing(ev) for ev in line))
        if kinds - {"once"}:
            return
        tested = []
        for ev in line:
            while ev is not None:
                tested += [c for c in ev.get("conditions", []) if isinstance(c, dict)]
                ev = self.answered.get(id(ev))
        if kinds and not all(self.tests_a_value(c) for c in tested):
            return
        read = self.words_of(tested) | {str(c.get("objectClass")).lower() for c in tested
                                        if c.get("objectClass") != "System"}
        actions = [a for ev in line for a in ev.get("actions", []) if isinstance(a, dict)]
        changed = self.writes(actions, set())
        if changed is None or changed & read \
                or any(a is not action and str(a.get("objectClass")).lower() in read for a in actions):
            return
        owner = "" if action.get("objectClass") == "System" else f"{action.get('objectClass')} "
        what = f"{owner}Toggle {name}" if action["id"] in TOGGLES else f"{owner}Set {name} to {params_of(action)['value']}"
        touch = next((n for n, plugin in self.p.plugin_of.items() if plugin.lower() == "touch"), "Touch")
        trigger = json.dumps({"id": "on-touched-object", "objectClass": touch,
                              "parameters": {"object": "<Object>", "type": "start"}})
        if kinds:
            self.p.findings.style_finding(
                "flip-once", f"{where}: {what} under Trigger once flips {name} once each time the conditions of "
                             f"its event turn true. They test values, not an input, so {name} changes when those "
                             f"values do, not once per tap or move. If it should follow each tap or move, move the "
                             f"flip into the event whose trigger causes the change, or into a sub-event of it, such "
                             f"as {trigger} with the tapped object for <Object>")
            return
        # A timeout has no trigger: the event that tests the time left resets it, and so runs once.
        timer = next((params_of(c).get("variable") for c in tested if c.get("id") == "compare-eventvar"
                      and params_of(c).get("variable") != name), None)
        reset = json.dumps({"id": "set-eventvar-value", "objectClass": "System",
                            "parameters": {"variable": timer or "<the time left>", "value": "<its start value>"}})
        self.p.findings.style_finding(
            "flip", f"{where}: {what} flips {name} on every tick, so an input can read either value: no trigger is "
                    f"in its event or above it. Move the flip into the event whose trigger causes the change, or "
                    f"into a sub-event of it. Trigger once does not fix it: it flips {name} once when the "
                    f"conditions turn true, not once per change. An event of its own for the flip starts with "
                    f"that trigger, such as {trigger}, with the tapped object for <Object>. If a value that runs "
                    f"out causes the change, such as the time left of a turn, keep the flip here and set that value "
                    f"back in the same actions, {reset}: the event then runs once each time it runs out")

    def none_left(self, c: dict) -> tuple[str, str] | None:
        """Return (the object type, "count" or "pickedcount") when a condition tests that none of the type is
        left, X.Count = 0 or X.PickedCount = 0, in Compare two values with the operands in either order or in
        Evaluate expression; None otherwise."""
        params = params_of(c)
        if c.get("objectClass") != "System" or c.get("isInverted"):
            return None
        if c.get("id") == "compare-two-values" and params.get("comparison") in COMPARISONS:
            text = f"{params.get('first-value')}{COMPARISONS[params['comparison']]}{params.get('second-value')}"
        elif c.get("id") == "evaluate-expression":
            text = str(params.get("value"))
        else:
            return None
        m = NONE_LEFT.fullmatch(re.sub(r"\s+", "", text))
        return None if m is None else (m.group(1), m.group(2).lower()) if m.group(1) else (m.group(3), m.group(4).lower())

    @staticmethod
    def picks(c: dict) -> set[str]:
        """The object types and families a condition narrows, lower case: its own, unless it is System's, and
        the one its object parameter names (Pick all, For each, On touched object, Is overlapping)."""
        own = c.get("objectClass") if c.get("objectClass") != "System" else None
        return {n.lower() for n in (own, params_of(c).get("object")) if isinstance(n, str)}

    def check_none_left(self, c: dict, where: str, gone: dict[str, str] | None, earlier: list[dict]) -> None:
        """X.Count = 0 after a Destroy of X earlier in the same top-level event: the destroyed instance counts
        until the top-level event ends (Construct3-Cookbook/guides/primitives/events/how-events-work.md), so the test fails for the last one.
        X.PickedCount = 0 below a condition that picks X: a pick of no X stops the event, Pick all included.
        gone: object type -> where an action destroyed it before this condition runs; earlier: the conditions
        that run before this one in its branch, those of OR blocks left out."""
        tested = self.none_left(c)
        if tested is None:
            return
        name, expression = tested
        if expression == "pickedcount":
            pick = next((e for e in earlier if name.lower() in self.picks(e)), None)
            if pick:
                count = json.dumps({"id": "compare-two-values", "objectClass": "System",
                                    "parameters": {"first-value": f"{name}.Count", "comparison": 0, "second-value": "0"}})
                self.p.findings.style_finding(
                    "picked", f"{where}: {name}.PickedCount = 0 never holds here. {describe(pick)} above it picks "
                              f"{name}, and a condition that picks no {name} stops its event, as System Pick all does "
                              f"when no {name} exists. Test none left in an event that does not pick {name}, {count}")
            return
        obj = next((o for o in gone or {} if o.lower() == name.lower()), None)
        if obj is None:
            return
        test = json.dumps([{"id": "compare-two-values", "objectClass": "System",
                            "parameters": {"first-value": f"{obj}.Count", "comparison": 0, "second-value": "0"}},
                           {"id": TRIGGER_ONCE, "objectClass": "System"}])
        self.p.findings.style_finding(
            "count", f"{where}: {obj}.Count = 0 is false here even when the last {obj} is gone. {gone[obj]} destroys "
                     f"it earlier in this top-level event, and a destroyed instance counts in Count until that event "
                     f"ends. Test it in a top-level event of its own, with the conditions {test}")

    @staticmethod
    def equals_constant(c: dict) -> tuple[str, str, str] | None:
        """(object, instance variable, value) of X: variable = a number or text literal, not inverted."""
        params = params_of(c)
        value = str(params.get("value", "")).strip()
        if (c.get("id") != "compare-instance-variable" or c.get("isInverted") or params.get("comparison") != 0
                or not (NUMBER.fullmatch(value) or STRING_LITERAL.fullmatch(value))):
            return None
        return c.get("objectClass", ""), str(params.get("instance-variable", "")).lower(), value

    def check_narrowed(self, c: dict, where: str, earlier: list[dict]) -> None:
        """X: v = 0 below X: v = 1 in the same branch: each condition keeps the instances the one above kept, so
        none passes both and the event never runs. A QQ bot wrote a tic-tac-toe row as nine Cell conditions
        (Row = 0, Column = 0, Value = 1, Row = 0, Column = 1, ...), 2026-10-06. A Pick all of X in between
        starts the narrowing again."""
        mine = self.equals_constant(c)
        if mine is None:
            return
        obj, var, value = mine
        for e in reversed(earlier):
            if e.get("id") == "pick-all" and str(params_of(e).get("object", "")).lower() == obj.lower():
                return
            other = self.equals_constant(e)
            if other and other[0] == obj and other[1] == var and other[2] != value:
                self.p.findings.style_finding(
                    "narrowed", f"{where}: {obj}.{params_of(c).get('instance-variable')} = {value} below "
                                f"{obj}.{params_of(e).get('instance-variable')} = {other[2]} in the same event never "
                                f"holds: each condition keeps only the {obj} the conditions above it kept, so no "
                                f"instance passes both. To test that several "
                                f"instances agree, narrow once and count: {obj}: Row = 0, {obj}: Value = 1, then "
                                f"System: {obj}.PickedCount = 3, or keep the values in an Array and compare its cells")
                return

    def note_solid_overlap(self, c: dict, where: str, ev: dict) -> None:
        """Is overlapping between an object with Platform and a Solid, kept for check_solid_overlaps once every
        action of the project is known."""
        if c.get("id") != "is-overlapping-another-object" or c.get("isInverted"):
            return
        a, b = c.get("objectClass"), params_of(c).get("object")
        for mover, solid in ((a, b), (b, a)):
            if (isinstance(mover, str) and isinstance(solid, str) and mover in self.p.plugin_of
                    and "platform" in {v.lower() for v in self.p.behaviors_of(mover).values()} and self.is_solid(solid)):
                lists = set()

                def own(e: dict) -> None:
                    if isinstance(e.get("actions"), list):
                        lists.add(id(self.running(e["actions"])))
                    for k in e.get("children") or []:
                        if isinstance(k, dict):
                            own(k)
                own(ev)
                self.solid_overlaps.append((where, c, mover, solid, lists))
                return

    def names_of(self, obj: str) -> set[str]:
        """The object, the families it is in and, for a family, its members: the names an action on it is under."""
        p = self.p
        return {obj, *(p.families_of(obj) if obj in p.types else []),
                *(p.families[obj].get("members", []) if obj in p.families else [])}

    def moved_otherwise(self, obj: str) -> bool:
        """Whether something besides its Platform moves the object: another movement behavior, an action, or its
        Platform switched off."""
        names = self.names_of(obj)
        if any(b.lower() in MOVERS for n in names if n in self.p.plugin_of for b in self.p.behaviors_of(n).values()):
            return True
        return any(isinstance(a, dict) and a.get("objectClass") in names
                   and (self.behavior_of(a) in MOVERS or (self.behavior_of(a) == "platform" and a.get("id") == "set-enabled")
                        or (not self.behavior_of(a) and a.get("id") in MOVES))
                   for actions, _ in self.action_lists for a in actions)

    def check_solid_overlaps(self) -> None:
        for where, c, mover, solid, lists in self.solid_overlaps:
            names = self.names_of(solid)
            off_elsewhere = any(isinstance(a, dict) and a.get("objectClass") in names and self.behavior_of(a) == "solid"
                                and a.get("id") == "set-enabled" for actions, _ in self.action_lists
                                if id(actions) not in lists for a in actions)
            off_at_start = any(inst.get("type") in names and isinstance(block, dict)
                               and (block.get("properties") or {}).get("enabled") is False
                               for lay in self.layouts.values() if isinstance(lay, dict)
                               for inst in layer_instances(lay.get("layers") or [])
                               for b, block in (inst.get("behaviors") or {}).items()
                               if self.p.behaviors_of(inst.get("type", "")).get(b, "").lower() == "solid")
            if off_elsewhere or off_at_start or self.moved_otherwise(mover) or self.moved_otherwise(solid):
                continue
            offset = json.dumps({"id": "is-overlapping-at-offset", "objectClass": mover,
                                 "parameters": {"object": solid, "offset-x": "1", "offset-y": "0"}})
            self.p.findings.style_finding(
                "solid-overlap",
                f"{where}: {describe(c)} never holds while {solid}'s Solid is enabled: the Platform behavior pushes "
                f"{mover} out of every Solid each tick, so the two touch and do not overlap, and the event "
                f"never runs. Test touching with Is overlapping at offset, 1 pixel towards {solid}: {offset} for a "
                f"{solid} on the right, \"offset-x\": \"-1\" on the left, \"offset-x\": \"0\", \"offset-y\": "
                f"\"1\" below; two events, or an OR block, for both sides. {mover} On collision with {solid} also "
                f"fires when they touch ({c3.guide_path(self.p.rag, 'behaviors/platform.md', self.p.root)})")

    def dragged(self, obj) -> bool:
        """An object type with Drag & Drop, or a family that has it or has a member with it."""
        return isinstance(obj, str) and any(b.lower() == "dragndrop" for n in self.names_of(obj)
                                            if n in self.p.plugin_of for b in self.p.behaviors_of(n).values())

    def note_drop(self, ace: dict, where: str) -> None:
        """A Drag & Drop object tested for overlap or collision with another, or set to another's position: the
        other is what it is dropped on. Kept for check_drops once every layout and action is known."""
        a, b = ace.get("objectClass"), params_of(ace).get("object")
        if ace.get("isInverted") or not isinstance(b, str) or a == b:
            return
        if ace.get("id") in DROP_TESTS:
            pairs = ((a, b), (b, a))
        elif ace.get("id") in DROP_SNAPS:
            pairs = ((a, b),)
        else:
            return
        for piece, target in pairs:
            if self.dragged(piece) and not self.dragged(target):
                self.drops.append((where, ace, piece, target))
                return

    def check_drops(self) -> None:
        """A dropped piece drawn under what it is dropped on: see DROP_TESTS."""
        p = self.p
        if not self.drops:
            return
        restacked = {a.get("objectClass") for actions, _ in self.action_lists for a in actions
                     if isinstance(a, dict) and a.get("id") in RESTACKS}
        restacked |= {params_of(a).get("object") for actions, _ in self.action_lists for a in actions
                      if isinstance(a, dict) and a.get("id") == "sort-z-order"}

        def types_of(obj: str) -> set[str]:
            return {obj} if obj in p.types else set(p.families.get(obj, {}).get("members", []))

        def drawn(layers, out: list) -> list:
            """(layer name, instance) bottom to top: a layer's sub-layers below its own instances."""
            for layer in layers if isinstance(layers, list) else []:
                if isinstance(layer, dict):
                    drawn(layer.get("subLayers"), out)
                    out += [(layer.get("name", ""), i) for i in layer.get("instances") or [] if isinstance(i, dict)]
            return out

        def shown(inst: dict) -> bool:
            color = (inst.get("world") or {}).get("color")
            alpha = color[3] if isinstance(color, list) and len(color) == 4 else 1
            return (inst.get("properties") or {}).get("initially-visible", True) is not False and alpha != 0

        said = set()
        for where, ace, piece, target in self.drops:
            if (piece, target) in said or self.names_of(piece) & restacked or self.names_of(target) & restacked:
                continue
            pieces, targets = types_of(piece), types_of(target)
            for lname, lay in self.layouts.items():
                order = drawn(lay.get("layers") if isinstance(lay, dict) else [], [])
                under = next(((i, j) for i, (_, pi) in enumerate(order) if pi.get("type") in pieces
                              for j, (_, ti) in enumerate(order) if ti.get("type") in targets and j > i and shown(ti)
                              and (pi.get("world") or {}).get("z", 0) == (ti.get("world") or {}).get("z", 0)), None)
                if under is None:
                    continue
                (pl, pi), (tl, ti) = order[under[0]], order[under[1]]
                how = (f"on layer {pl!r} {pi['type']} comes before {ti['type']} in the instances, and one listed later "
                       f"is drawn in front" if pl == tl else
                       f"{pi['type']} is on layer {pl!r}, below {ti['type']}'s layer {tl!r}")
                behavior = next((n for n, b in p.behaviors_of(pi["type"]).items() if b.lower() == "dragndrop"), "DragDrop")
                top = json.dumps({"eventType": "block", "conditions": [{"id": "on-drag-start", "objectClass": piece,
                                                                        "behaviorType": behavior}],
                                  "actions": [{"id": "move-to-top", "objectClass": piece}]})
                self.p.findings.style_finding(
                    "drop-under",
                    f"{where}: {describe(ace)} drops {piece} on {target}, and layout {lname} draws {piece} under "
                    f"{target}: {how}. Dropped there, {piece} disappears behind {target}. List {piece}'s instance "
                    f"after {target}'s on the same layer, or put it on a layer above; or raise it as it is picked "
                    f"up, {top} (manual: project-primitives/objects/instances.md \"Z index\")")
                said.add((piece, target))
                break

    def check_dead_timers(self) -> None:
        """A Once timer that only its own On timer starts again, under a condition, and otherwise only On start of
        layout: the first time the condition is false when the timer ends, nothing starts it, and On timer never
        fires again. A reset after N seconds without input was written this way: a 0.1 s tick restarted while
        combo > 0, never started by the tap, so it stopped at the first tick (a hosted model, 2026-10-09). Over
        the 524 official examples it adds no finding."""
        by_tag: dict[tuple[str, str], list[tuple[str, dict, tuple, bool | None]]] = {}
        for w, a, line, paced in self.timer_starts:
            tag = params_of(a).get("tag")
            if isinstance(tag, str):
                by_tag.setdefault((str(a.get("objectClass")), unquote(tag).lower()), []).append((w, a, line, paced))

        def fires(c: dict, obj: str, tag: str) -> bool:
            t = params_of(c).get("tag")
            return c.get("id") == "on-timer" and c.get("objectClass") == obj and self.behavior_of(c) == "timer" \
                and isinstance(t, str) and unquote(t).lower() == tag

        for (obj, tag), starts in by_tag.items():
            if any(str(params_of(a).get("type")).lower() != "once" for _, a, _, _ in starts):
                continue
            restarts = []
            for w, a, line, paced in starts:
                at = next((i for i, e in enumerate(line) if any(fires(c, obj, tag) for c in e.get("conditions", [])
                                                                if isinstance(c, dict))), None)
                if at is None:
                    if paced is None or not any(isinstance(c, dict) and c.get("objectClass") == "System" and
                                                c.get("id") == "on-start-of-layout"
                                                for e in line for c in e.get("conditions", [])):
                        break  # started by another trigger, a function or every tick
                    continue
                extra = [c for e in line[at:] for c in e.get("conditions", []) if isinstance(c, dict)
                         and not fires(c, obj, tag)]
                if not extra or any(c.get("objectClass") == "System" and c.get("id") == "else" for c in extra):
                    break  # On timer starts it again whatever the state
                restarts.append((w, a, extra))
            else:
                if not restarts:
                    continue
                w, a, extra = restarts[0]
                shown = params_of(a).get("tag")
                start = json.dumps({"id": "start-timer", "objectClass": obj, "behaviorType": a.get("behaviorType"),
                                    "parameters": {"duration": "<seconds>", "type": "once", "tag": shown}},
                                   ensure_ascii=False)
                self.p.findings.style_finding(
                    "dead-timer",
                    f"{w}: Start timer {shown} runs again only from its own On timer {shown}, under "
                    f"{' and '.join(describe(c) + ' ' + json.dumps(params_of(c), ensure_ascii=False) for c in extra)}, "
                    f"and otherwise only On start of layout starts it. "
                    f"The first time that condition is false when the timer ends, nothing starts it again, and On "
                    f"timer {shown} never fires after that. Start it in the trigger of what it times: for a reset N "
                    f"seconds after the last tap or key (a combo, an idle screen), start it in the input's trigger "
                    f"on every input, {start}, which restarts it, and reset in On timer {shown}; no variable "
                    f"needs to count the time ({c3.guide_path(self.p.rag, 'behaviors/timer.md', self.p.root)})")

    def not_leaving(self, c: dict) -> bool:
        """Whether a condition above a Destroy says nothing about an instance on its way out: a hit, an input or a
        plain pick. An inverted hit, a position, a timer or anything else may be."""
        if c.get("id") in HITS:
            return not c.get("isInverted")
        plugin = self.p.plugin_of.get(c.get("objectClass", ""), "")
        return plugin.lower() in INPUTS or (c.get("objectClass") == "System" and c.get("id") in PLAIN_PICKS)

    def is_wall(self, obj) -> bool:
        """A Solid or a Tilemap, or a family of them: what the official examples' bullets end on."""
        return isinstance(obj, str) and any(
            "solid" in {v.lower() for v in self.p.behaviors_of(n).values()} or self.p.plugin_of.get(n, "").lower() == "tilemap"
            for n in self.names_of(obj))

    def check_stray_bullets(self) -> None:
        p = self.p
        actions = [a for acts, _ in self.action_lists for a in acts if isinstance(a, dict)]
        for t in sorted(p.types):
            behaviors = {v.lower() for v in p.behaviors_of(t).values()}
            if "bullet" not in behaviors or behaviors & REMOVERS:
                continue
            names = self.names_of(t)
            if not any(self.made_by(a) in names for a in actions) \
                    or any(a.get("objectClass") in names and a.get("id") in PLACINGS for a in actions) \
                    or any(o in names and leaving for o, leaving in self.destroys):
                continue
            hit = sorted({b if a in names else a for a, b in self.hit_pairs if a in names or b in names} - {None},
                         key=str)
            if any(self.is_wall(o) for o in hit):
                continue
            behavior = '{"behaviorId": "destroy", "name": "DestroyOutsideLayout", "sid": <new sid>}'
            self.warn(f"{t} moves with the Bullet behavior and the events create it, but nothing removes one that misses: "
                      + (f"every Destroy of {t} is under a hit on {', '.join(map(str, hit))}, none of them a Solid, "
                         if any(o in names for o, _ in self.destroys) else "no event destroys it, ")
                      + f"so a {t} that hits nothing flies on outside the layout forever, and the instances pile up "
                        f"and slow the game. Add the Destroy outside behavior to {t}: {behavior} in its "
                        f"behaviorTypes, and \"DestroyOutsideLayout\": {{\"properties\": {{\"region\": \"layout\"}}}} "
                        f"in the behaviors of its layout instances, and {USED_DESTROY} in usedAddons of project.c3proj "
                        f"unless it is there; region \"viewport\" removes it at the screen's "
                        f"edge when the layout is larger. It has no conditions or actions "
                        f"(manual: behavior-reference/destroy-outside.md)")
