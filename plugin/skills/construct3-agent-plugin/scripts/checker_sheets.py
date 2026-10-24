"""The walk through the event sheets, the --style warnings, the checks over a whole
sheet and the calls and created instances that the walk collected. A part of
check_project.Checker, which holds the state they read."""
import json
import re

import c3project as c3
from c3project import LOWER, NUMBERED, STRING_LITERAL, closest, describe
from checker_common import (
    EVENT_TEXT, FUNCTION_RETURN_TYPES, IDENT, CREATING, SYSTEM_PICKS, NOT_PICKING, WAITS, free_name,
    params_of, HITS, INSTANCE_VALUE_TESTS, SETS, STATE_SETS, STATE_TESTS, arguments_from, outside_literals,
    FIND_LITERAL_SECOND, script_text, number_of, STYLE_RUN, STYLE_TREE, STYLE_LADDER, COUNTDOWN_ON_INSTANCE,
    declarations, Holder,
)


class SheetChecks:
    def check_block(self, ev: dict, scope: dict, where: str, by_input: bool | None = False,
                    paced: bool | None = False, line: tuple = (), gone: dict[str, str] | None = None) -> None:
        """by_input as check_gesture's; paced: whether the event or one above it is triggered, on a timer
        or Trigger once, None in a function or custom action; line: the event and those above it; gone: as
        check_none_left's, filled by the event's Destroy actions, None for the sub-events of an event whose
        actions wait."""
        held = tuple(c for e in line for c in e.get("conditions", []) if isinstance(c, dict))
        earlier = [c for e in line[:-1] if not e.get("isOrBlock") for c in e.get("conditions", []) if isinstance(c, dict)]
        self.event_where[id(ev)] = where
        if isinstance(ev.get("actions"), list):
            self.action_lists.append((ev["actions"], where))
        for i, c in enumerate(ev.get("conditions", []), 1):
            self.check_ace("conditions", c, scope, f"{where} condition {i}")
            self.note_signal(c, f"{where} condition {i}")
            if isinstance(c, dict):
                self.check_none_left(c, f"{where} condition {i}", gone, earlier)
                self.note_solid_overlap(c, f"{where} condition {i}", ev)
                self.note_drop(c, f"{where} condition {i}")
                if c.get("id") in HITS:
                    self.hit_pairs.append((c.get("objectClass"), params_of(c).get("object")))
                if not ev.get("isOrBlock"):
                    self.check_narrowed(c, f"{where} condition {i}", earlier)
                    earlier.append(c)
        found: dict[str, str] = {}
        for i, a in enumerate(ev.get("actions", []), 1):
            w = f"{where} action {i}"
            self.note_signal(a, w)
            self.check_gesture(a, by_input, w)
            self.check_pathfinding(a, w, found, paced)
            self.check_held_control(a, w, held, paced)
            self.check_timer_restart(a, w, line, held, paced)
            if a.get("id") == "start-timer" and self.behavior_of(a) == "timer":
                self.timer_starts.append((w, a, line, paced))
            self.check_flip(a, w, line, paced)
            if isinstance(a, dict):
                self.note_drop(a, w)
            if gone is not None and a.get("id") == "destroy" and a.get("objectClass") in self.p.plugin_of:
                gone.setdefault(a["objectClass"], w)
            if a.get("id") == "destroy":
                waited = any(self.waits(b) for b in ev["actions"][:i - 1] if isinstance(b, dict))
                self.destroys.append((a.get("objectClass"), waited or not held
                                      or not all(self.not_leaving(c) for c in held)))
            if a.get("type") == "script":
                self.check_script(a.get("script"), scope, w)
            if a.get("type") in ("comment", "script"):
                continue
            if "callFunction" in a or "customAction" in a:
                params = a.get("parameters", [])
                if not isinstance(params, list):
                    self.err(f"{w}: the call writes \"parameters\": {json.dumps(params, ensure_ascii=False)}, and the "
                             f"editor stops with \"TypeError: expected array\" before the project opens. Write the "
                             f"arguments as a list in order, \"parameters\": [\"1\"], or leave the key out when the "
                             f"call passes none")
                    params = []
                if "callFunction" in a:
                    self.pending_calls.append(("function", a["callFunction"], None, len(params), w))
                else:
                    owner = a.get("customActionObjectClass", a["objectClass"])
                    self.pending_calls.append(("custom", a["customAction"], owner, len(params), w))
                callee = self.called(a)
                kinds = [q.get("type") for q in callee[1]["functionParameters"]] if callee else []
                for i, param in enumerate(params, 1):
                    if kinds[i - 1:i] != ["boolean"]:
                        self.check_expr(w, param, scope)
                    elif not isinstance(param, bool):
                        self.err(f"{w}: parameter {i} of {callee[0]} is a boolean and gets {json.dumps(param)}, "
                                 f"which reads as true, \"0\" and \"false\" too; write the JSON true or false")
                continue
            self.check_ace("actions", a, scope, w)

    def check_event_lists(self, ev: dict, et, where: str) -> None:
        """What the editor walks as it reads an event. A block and its two
        relatives loop over conditions and actions without looking first, so a
        block that carries neither stops the open where the sheet is named and
        the event is not."""
        if et in ("block", "function-block", "custom-ace-block"):
            for what in ("conditions", "actions"):
                if not isinstance(ev.get(what), list):
                    self.err(f"{where}: {what} is {ev.get(what)!r}; the editor walks both lists as it reads the "
                             f'event. An event with none writes "{what}": []')
        if et == "script" and not isinstance(ev.get("script"), (str, list)):
            self.err(f"{where}: script is {ev.get('script')!r}; the editor stops with \"invalid script data\". "
                     f"Write the code as text, or as a list with a line per item")
        if "children" in ev and not isinstance(ev["children"], list):
            self.err(f"{where}: children is {ev['children']!r}; sub-events are a list, and an event with none "
                     f"leaves the key out")
        # Text the editor reads without a default; an empty one is written "".
        for kind, key, message in EVENT_TEXT:
            if et == kind and not isinstance(ev.get(key), str):
                self.err(f"{where}: the {kind} has {key} {ev.get(key)!r}; write \"{key}\": \"\" when it has none, "
                         f"the editor reads it as text and stops with \"{message}\"")
        if et == "function-block" and ev.get("functionReturnType") not in FUNCTION_RETURN_TYPES:
            self.err(f"{where}: functionReturnType {ev.get('functionReturnType')!r} is not one of "
                     f"{', '.join(FUNCTION_RETURN_TYPES)}; the editor stops with \"function has wrong return type\"")
        if et == "custom-ace-block" and ev.get("aceType") != "action":
            self.err(f"{where}: aceType {ev.get('aceType')!r} should be \"action\", the one kind of custom ACE; "
                     f"the editor stops with \"invalid ACE type\"")

    def walk(self, events: list, scope: dict, where: str, counter: list[int], above: Holder | None = None,
             depth: int = 0, group: dict | None = None, by_input: bool | None = False,
             paced: bool | None = False, line: tuple = (), gone: dict[str, str] | None = None,
             holder: str = "") -> None:
        """A local declared in a list of sibling events is visible to every event of
        that list, whatever the order, and to their sub-events; not to the parent's
        own actions. So the list's variables enter the scope first, and a block is
        checked before its children are walked. scope maps a name to the variable
        event or function parameter that declares it, in the order enter keeps; a
        sheet's own top-level variables are there before its walk. counter holds the sheet's
        running event number, above what holds the trigger of this branch, depth
        how many sub-event levels down this list is (a group's children are 0),
        group the group whose children the list is, by_input whether an event above
        tests input (check_gesture), paced whether one above is triggered or on a
        timer (check_pathfinding), line the events above in this branch, gone
        what the top-level event destroyed before the list runs (check_none_left),
        shared by the list's events in the order they run, holder the event that
        holds the list, "group Movement", "event 5" or "function launch"."""
        scope = dict(scope)
        bad = [ev for ev in events if not isinstance(ev, dict)]
        if bad:
            self.err(f"{where}: an event is {bad[0]!r}; every event is an object with an eventType")
            events = [ev for ev in events if isinstance(ev, dict)]
        outer = dict(scope)
        for ev in events:
            if ev.get("eventType") == "variable" and id(ev) not in self.global_ids:
                self.enter(scope, ev, outer, f"{where} variable {ev['name']}", holder)
        ladders = self.ladders(events) if self.style else {}
        numbered: dict[int, list[tuple[int, str]]] = {}
        find_tests: dict[str, list[tuple[int, str, str]]] = {}
        previous = None
        for i, ev in enumerate(events):
            et = ev.get("eventType")
            if et in NUMBERED:
                counter[0] += 1
            w = f"{where} event {counter[0] + (et not in NUMBERED)} (sid {ev.get('sid', '?')})"
            self.check_event_lists(ev, et, w)
            if self.style and et in ("block", "function-block", "custom-ace-block"):
                self.check_style(ev, w, events, i, depth, group, counter[0])
            if et == "block":
                self.check_undone(events[:i], ev, w)
            if self.style and et == "block":
                for subject, code in self.find_tests(ev):
                    find_tests.setdefault(subject, []).append((counter[0], w, code))
            if id(ev) in ladders:
                rungs = numbered.setdefault(ladders[id(ev)][0], [])
                rungs.append((counter[0], w))
                if len(rungs) == ladders[id(ev)][1]:
                    self.check_ladder(rungs)
            if et == "variable":
                self.check_variable(ev, w, "variable")
            elif et in ("comment", "include"):
                if et == "include" and ev["includeSheet"] not in self.sheets:
                    self.err(f"{w}: included sheet {ev['includeSheet']} does not exist"
                             f"{closest(ev['includeSheet'], self.sheets)}")
                elif et == "include" and where == f"sheet {ev['includeSheet']}":
                    self.err(f"{w}: a sheet cannot include itself")
            elif et == "group":
                self.walk(ev.get("children") or [], scope, where, counter, above, group=ev, by_input=by_input,
                          paced=paced, holder=f"group {ev.get('title')}")
            elif et in ("function-block", "custom-ace-block"):
                kind = "function" if et == "function-block" else "custom action"
                name = ev.get("functionName") if et == "function-block" else ev.get("aceName")
                label = ev.get("functionName") or f"{ev['objectClass']}.{ev['aceName']}"
                if isinstance(name, str):
                    self.check_callable_name(ev, kind, name, w)
                fscope = dict(scope)
                outer = dict(fscope)
                params = ev["functionParameters"]
                # Of the parameters whose names match without case, the editor keeps the last.
                last = {LOWER(p["name"]): p for p in params if isinstance(p.get("name"), str)}
                taken = set(fscope) | {p.get("name") for p in params}
                for param in params:
                    kept = last[LOWER(param["name"])] if isinstance(param.get("name"), str) else param
                    if kept is param:
                        self.enter(fscope, param, outer, f"{w} parameter {param['name']}", f"{kind} {label}")
                    else:
                        new = free_name(param["name"], taken)
                        taken.add(new)
                        self.check_parameter_renamed(param, kept, f"{w} parameter {param['name']}", new)
                    self.check_variable(param, w, "parameter")
                if et == "custom-ace-block" and ev["objectClass"] not in self.p.plugin_of:
                    self.err(f"{w}: custom action {label} belongs to unknown object {ev['objectClass']}")
                body: dict[str, str] = {}
                self.check_block(ev, fscope, f"{w} {label}", None, None, gone=body)
                self.walk(ev.get("children", []), fscope, where, counter,
                          self.check_structure(ev, f"{w} {label}", above, previous), depth + 1, by_input=None,
                          paced=None, gone=None if any(self.waits(a) for a in ev.get("actions", [])) else body,
                          holder=f"{kind} {label}")
            elif et == "block":
                here = None if by_input is None else by_input or self.reads_input(ev)
                timed = None if paced is None else paced or self.paces(ev)
                first = next(iter(ev.get("conditions") or []), None)
                if isinstance(first, dict) and (first.get("objectClass"), first.get("id")) == ("System", "else") \
                        and previous is not None and previous.get("eventType") == "block":
                    self.answered[id(ev)] = previous
                # A top-level event starts with nothing destroyed; after a Wait its sub-events run later.
                mine = {} if depth == 0 else gone
                self.check_block(ev, scope, w, here, timed, line + (ev,), mine)
                self.walk(ev.get("children", []), scope, where, counter, self.check_structure(ev, w, above, previous),
                          depth + 1, by_input=here, paced=timed, line=line + (ev,),
                          gone=None if any(self.waits(a) for a in ev.get("actions", [])) else mine,
                          holder=f"event {counter[0]}")
            elif et == "script":
                self.check_script(ev.get("script"), scope, w)
            else:
                self.err(f"{w}: unknown eventType {et!r}; the editor knows block, group, variable, comment, include, "
                         f"function-block, custom-ace-block and script")
            if et != "comment":
                previous = ev
        self.check_find_dispatch(find_tests)

    @staticmethod
    def find_tests(ev: dict) -> list[tuple[str, str]]:
        """(text searched, code) for each find or findcase in the event's conditions whose
        second argument is a text literal: find(TMP, "BU")."""
        tests = []
        for c in ev.get("conditions", []):
            params = c.get("parameters")
            for value in (params.values() if isinstance(params, dict) else []):
                if not isinstance(value, str):
                    continue
                for m in outside_literals(value, FIND_LITERAL_SECOND.finditer(value)):
                    args = arguments_from(value, m.end())
                    if len(args) == 2 and STRING_LITERAL.fullmatch(args[1]) and \
                            not STRING_LITERAL.fullmatch(args[0]):
                        tests.append((re.sub(r"\s+", "", args[0]), args[1]))
        return tests

    # --- style, with --style ------------------------------------------------------------
    def check_style(self, ev: dict, where: str, siblings: list, i: int, depth: int, group: dict | None,
                    n: int) -> None:
        """Habits of sheets written by small models, each with the shape the
        official examples give it instead. Warnings, never errors: the editor
        accepts them all. The thresholds sit past the 90th percentile of the
        studio examples, where a run of actions without a comment is 3 at the
        median and 6 at the 90th percentile, branches go two sub-events deep in
        93% of events, 93% of top-level events have a comment above them, and
        of the events with two or more case sub-events 84% have a comment above
        at least one case (docs/decisions/event-sheet-design-guidance.md,
        2026-09-22). edit_sheet.py refuses a plan whose new events raise the
        warnings whose fix is one comment or one deleted condition, and prints
        the others; check_project.py reports them all over the whole project
        when asked, which suits a project the agent wrote. Every tick beside
        another condition adds nothing: an event without a trigger is tested
        every tick. A ladder of sibling events is check_ladder."""
        actions = ev.get("actions", [])
        run = longest = 0
        for a in actions:
            run = 0 if a.get("type") == "comment" else run + 1
            longest = max(longest, run)
        style = self.p.findings.style_finding
        if longest >= STYLE_RUN:
            style("run", f"{where}: {longest} actions in a row without a comment action; the official examples step a "
                         f"long block with a comment action every three to five actions, "
                         '{"type": "comment", "text": "What the next actions do."}')
        conditions = ev.get("conditions", [])
        others = [c for c in conditions if (c.get("objectClass"), c.get("id")) != ("System", "every-tick")]
        if not ev.get("isOrBlock") and others and len(others) < len(conditions):
            style("tick", f"{where}: Every tick beside {len(others)} other condition(s) changes nothing, an event "
                          f"without a trigger is tested every tick already; the official examples write Every tick "
                          f"only as an event's one condition. Remove it")
        self.check_countdown(ev, where, conditions, actions)
        if depth == 0 and (actions or ev.get("children")):
            j = i - 1
            while j >= 0 and siblings[j].get("eventType") == "variable":  # locals declared above the event
                j -= 1
            commented = j >= 0 and siblings[j].get("eventType") == "comment"
            comment = '{"eventType": "comment", "text": "..."}'
            if not commented and group is None:
                style("comment", f"{where}: no comment above it; the official examples put a one-sentence comment "
                                 f"above every top-level event, saying what it does or which case it is, "
                                 f"{comment} as the event before it")
            elif not commented:
                # Small models took "top-level" for the sheet's own list and put the comment
                # above the group, plan after plan (event-sheet-design-guidance.md): name the list it goes into.
                on_disk = f'; edit_sheet.py puts it there with {{"before": {n}, "events": [{comment}]}}'
                style("comment", f"{where}: no comment above it; the official examples put a one-sentence comment "
                                 f"above every top-level event, the events directly in a group included, saying "
                                 f"what it does or which case it is. This one is entry {i + 1} in the \"children\" "
                                 f"of group {json.dumps(group.get('title'), ensure_ascii=False)}: {comment} goes "
                                 f"into that list before it" + (on_disk if self.numbers_on_disk else ""))
        cases = [j for j, k in enumerate(ev.get("children", []))
                 if k.get("eventType") == "block" and (k.get("actions") or k.get("children"))]
        if len(cases) >= 2 and not any(j > 0 and ev["children"][j - 1].get("eventType") == "comment" for j in cases):
            style("cases", f"{where}: none of its {len(cases)} case sub-events has a comment above it; the official "
                           f"examples put a one-sentence comment above each case, saying which case it is, "
                           '{"eventType": "comment", "text": "..."} as the event before each')
        if depth == 0 and self.tree_depth(ev) >= STYLE_TREE:
            leaves = self.leaves(ev)
            called = {a["callFunction"] for leaf in leaves for a in leaf.get("actions", []) if "callFunction" in a}
            if len(leaves) >= 3 and len(called) == 1 and \
                    all(any("callFunction" in a for a in leaf.get("actions", [])) for leaf in leaves):
                style("tree", f"{where}: sub-events {self.tree_depth(ev)} levels deep, every leaf calling "
                              f"{called.pop()}; the official examples write the cases as sibling sub-events with a "
                              f"comment each, or compute the value in one expression")

    @staticmethod
    def seconds_taken(a: dict, interval: float) -> str | None:
        """The variable an action takes `interval` off, in any of the three spellings small
        models write: Subtract N, Add -N, Set v to v - N; None for any other action."""
        params = a.get("parameters")
        if not isinstance(params, dict):
            return None
        aid, value = a.get("id"), params.get("value")
        name = params.get("instance-variable" if aid in COUNTDOWN_ON_INSTANCE else "variable")
        if aid in ("subtract-from-eventvar", "subtract-from-instvar"):
            return name if number_of(value) == interval else None
        if aid in ("add-to-eventvar", "add-to-instvar"):
            return name if number_of(value) == -interval else None
        if aid in ("set-eventvar-value", "set-instvar-value") and isinstance(value, str):
            m = re.fullmatch(r"\s*(?:\w+\s*\.\s*)?(\w+)\s*-\s*([\d.]+)\s*", value)
            if m and m.group(1).lower() == str(name).lower() and number_of(m.group(2)) == interval:
                return name
        return None

    def check_countdown(self, ev: dict, where: str, conditions: list, actions: list) -> None:
        """Every N seconds taking N off a variable: the variable counts seconds, a timer
        kept by hand. Of the 155 eval and small-model projects, 73 wrote it, as Subtract 1
        (60), Add -1 (12) or Set v to v - 1 (1); none of the 524 official examples does,
        and the one that subtracts every N seconds counts coins, not time. A global
        counted this way keeps its value across Restart layout, so the next round starts
        at 0 (event-sheet-design-guidance.md, 2026-09-28). Subtracting dt is left alone:
        the examples count cooldowns that way."""
        every = [c for c in conditions if (c.get("objectClass"), c.get("id")) == ("System", "every-x-seconds")]
        if not every or ev.get("isOrBlock"):
            return
        interval = (every[0].get("parameters") or {}).get("interval-seconds")
        if number_of(interval) is None:
            return
        for a in actions:
            name = self.seconds_taken(a, number_of(interval))
            if name is None:
                continue
            on_instance = a["id"] in COUNTDOWN_ON_INSTANCE
            owner = a.get("objectClass", "<Object>") if on_instance else "<Object>"
            start = json.dumps({"id": "start-timer", "objectClass": owner, "behaviorType": "Timer",
                                "parameters": {"duration": "<seconds>", "type": "once", "tag": '"countdown"'}})
            self.p.findings.style_finding(
                "countdown", f"{where}: {name} counts seconds by hand, {number_of(interval):g} off every {interval} seconds"
                             + ("" if on_instance else "; a global keeps its value across Restart layout, so the next "
                                                       "round starts where this one ended") +
                             f". The Timer behavior counts time: add it to "
                             f"{owner if on_instance else 'the object that shows the time (<Object> below)'}, start it where "
                             f"the count starts, {start}, end the count in Timer On timer \"countdown\", and show "
                             f"ceil({owner}.Timer.Duration(\"countdown\") - {owner}.Timer.CurrentTime(\"countdown\"))")
            return

    @staticmethod
    def shape(ev: dict) -> tuple:
        """An event's conditions and actions by their ACE, without their values."""
        return (ev.get("isOrBlock", False),
                tuple((c.get("objectClass"), c.get("id"), c.get("isInverted", False)) for c in ev.get("conditions", [])),
                tuple((a.get("objectClass"), a.get("id")) for a in ev.get("actions", [])),
                len([k for k in ev.get("children", []) if k.get("eventType") == "block"]))

    def ladders(self, events: list) -> dict[int, tuple[int, int]]:
        """The sibling blocks that share their shape with STYLE_LADDER or more others, by
        id, each mapped to its ladder's number and size. One event per option,
        building or state, only the numbers changed, is a table transcribed into
        events; the studio examples reach five such siblings in 32 places of 20 of their 219
        projects, input ladders (a key per action) and else-if chains among them."""
        of_shape: dict[tuple, list[dict]] = {}
        for ev in events:
            if ev.get("eventType") == "block" and (ev.get("actions") or ev.get("children")):
                of_shape.setdefault(self.shape(ev), []).append(ev)
        return {id(ev): (n, len(evs)) for n, evs in enumerate(of_shape.values()) if len(evs) >= STYLE_LADDER
                for ev in evs}

    def trigger_of(self, ev: dict) -> dict | None:
        """The event's first condition when it is a trigger, else None."""
        conds = [c for c in ev.get("conditions") or [] if isinstance(c, dict)]
        if not conds:
            return None
        entry = self.p.ace_entry("conditions", conds[0])
        return conds[0] if (entry.get("isTrigger") if entry else str(conds[0].get("id", "")).startswith("on-")) \
            else None

    def state_set(self, actions: list) -> set[str]:
        """The variables these actions set, and Obj.animationframe and the like for the state of an object, up to
        the first wait: what a wait leaves for later, the next event of the same input does not see. Object state
        is keyed by names_of(), never bare."""
        out = set()
        for a in actions:
            if self.waits(a):
                break
            params = params_of(a)
            obj = str(a.get("objectClass"))
            if obj == "System" and a.get("id") in {*SETS, "add-to-eventvar", "subtract-from-eventvar"}:
                out.add(str(params.get(SETS.get(a["id"], "variable"), "")).lower())
            if a.get("id") in STATE_SETS and obj != "System":
                prop = STATE_SETS[a["id"]] or str(params.get("instance-variable", "")).lower()
                out |= {f"{name.lower()}.{prop}" for name in self.names_of(obj)}
        return out

    def state_read(self, conditions: list) -> set[str]:
        """What these conditions test, in the form state_set() writes: variables, Obj.var, Obj.animationframe."""
        out = set()
        for c in conditions:
            obj = str(c.get("objectClass")).lower()
            if c.get("id") in STATE_TESTS:
                out.add(f"{obj}.{STATE_TESTS[c['id']]}")
            if c.get("id") in INSTANCE_VALUE_TESTS:
                out.add(f"{obj}.{str(params_of(c).get('instance-variable', '')).lower()}")
            for key, value in params_of(c).items():
                if isinstance(value, str) and key != "instance-variable":
                    out |= {m.lower() for m in re.findall(r"\w+\.\w+", value)} | {w.lower() for w in IDENT.findall(value)}
        return out

    def check_undone(self, before: list, ev: dict, where: str) -> None:
        """A block with the same trigger as an earlier block in its list that tests what that block changed.
        Both run on the one input, the later one after the earlier one's actions, so it sees the new value: a
        switch written as "frame 0: set 1" and "frame 1: set 0" sets it back on every tap. Else does not reach
        across two events with their own trigger; one event with the trigger and two case sub-events, the
        second starting with Else, does."""
        trigger = self.trigger_of(ev)
        tests = [c for c in (ev.get("conditions") or [])[1:] if isinstance(c, dict)]
        if trigger is None or not tests:
            return
        same = ("objectClass", "id", "parameters", "isInverted")
        key = json.dumps({k: trigger.get(k) for k in same}, sort_keys=True)
        read = self.state_read(tests)
        for earlier in reversed(before):
            if not isinstance(earlier, dict) or earlier.get("eventType") != "block":
                continue
            first = self.trigger_of(earlier)
            if first is None or json.dumps({k: first.get(k) for k in same}, sort_keys=True) != key:
                continue
            actions = self.actions_below(earlier)
            hit = sorted(self.state_set(actions) & read)
            if not hit:
                continue
            case = json.dumps({"eventType": "block", "conditions": [{"id": "else", "objectClass": "System"}],
                               "actions": ["..."]})
            self.p.findings.style_finding(
                "undone", f"{where}: it has the same trigger as an earlier event in its list and tests {', '.join(hit)}, "
                          f"which that event's actions change. Both run on the same input, this one after the other, "
                          f"so it sees the value just set and can set it back: a switch never stays switched. Write "
                          f"one event with the trigger, and the cases as its sub-events: the first with the test, the "
                          f"second {case}")
            return

    def check_ladder(self, rungs: list[tuple[int, str]]) -> None:
        others = ", ".join(str(n) for n, _ in rungs[1:])
        self.p.findings.style_finding(
            "ladder", f"{rungs[0][1]}: with events {others}, the same conditions and actions {len(rungs)} times over, "
                      f"differing only in their values; the official examples write such cases once, over what "
                      f"differs: an instance variable of the object touched, a family, a Dictionary loaded from a "
                      f"project file, or the value in one expression")

    @staticmethod
    def tree_depth(ev: dict) -> int:
        kids = [k for k in ev.get("children", []) if k.get("eventType") == "block"]
        return 1 + max((SheetChecks.tree_depth(k) for k in kids), default=0) if kids else 0

    @staticmethod
    def leaves(ev: dict) -> list[dict]:
        kids = [k for k in ev.get("children", []) if k.get("eventType") == "block"]
        return [leaf for k in kids for leaf in SheetChecks.leaves(k)] if kids else [ev]

    def declared_functions(self, events: list) -> None:
        """Functions and custom actions are visible from every sheet, so collect them
        first. An event that is not an object is reported by walk(), which numbers it."""
        for ev in events:
            if not isinstance(ev, dict):
                continue
            et = ev.get("eventType")
            if et == "function-block":
                self.functions[ev["functionName"]] = len(ev["functionParameters"])
                self.returns[LOWER(ev["functionName"])] = ev.get("functionReturnType")
                self.function_blocks[ev["functionName"]] = ev
            elif et == "custom-ace-block":
                self.custom_actions[(ev["objectClass"], ev["aceName"])] = len(ev["functionParameters"])
                self.custom_blocks[(ev["objectClass"], ev["aceName"])] = ev
            self.declared_functions(ev.get("children") or [])

    def declared_groups(self, events: list) -> None:
        for ev in events:
            if not isinstance(ev, dict):
                continue
            if ev.get("eventType") == "group":
                self.group_titles.add(ev["title"])
            self.declared_groups(ev.get("children") or [])

    def check_sheets(self) -> None:
        for sname, sheet in self.sheets.items():
            if not (isinstance(sheet.get("name"), str) and sheet["name"]):
                self.err(f"sheet {sname}: the file says \"name\": {sheet.get('name')!r}; the editor reads it "
                         f"as text and stops with \"invalid event sheet name\"")
            if not isinstance(sheet.get("events"), list):
                self.err(f"sheet {sname}: events is {sheet.get('events')!r}; an empty sheet writes "
                         f"\"events\": []")
        self.sheets = {n: s for n, s in self.sheets.items() if isinstance(s.get("events"), list)}
        for sheet in self.sheets.values():
            self.collect_sids(sheet)
        for sheet in self.sheets.values():
            self.declared_functions(sheet["events"])
            self.declared_groups(sheet["events"])
        # A global declared at the top level of any sheet is visible from every sheet.
        tops = [(sname, ev) for sname, s in self.sheets.items() for ev in s["events"]
                if isinstance(ev, dict) and ev.get("eventType") == "variable"]
        self.global_ids = {id(ev) for _, ev in tops}
        sheet_of = {id(ev): sname for sname, ev in tops}
        globals_: dict = {}
        for sname, ev in tops:
            earlier = self.variable_named(ev.get("name"), globals_)
            if earlier is not None:
                self.check_declared_once(ev, earlier, f"sheet {sname} variable {ev['name']}",
                                         f"declared at the top level of sheet {sheet_of[id(earlier)]}")
            elif isinstance(ev.get("name"), str):
                globals_[ev["name"]] = ev
        # The order the editor reads variables and parameters in: sheet by sheet, each event before its sub-events.
        variables = [v for s in self.sheets.values() for v in declarations(s["events"])]
        self.load_order = {id(v): i for i, v in enumerate(variables)}
        self.variable_names = {v.get("name") for v in variables}
        for sname, sheet in self.sheets.items():
            # A plan's sheet has numbers the file does not have yet: no operation can address them.
            self.numbers_on_disk = sname not in self.unsaved
            self.walk(sheet["events"], globals_, f"sheet {sname}", [0])

    def check_calls(self) -> None:
        p = self.p
        for kind, name, owner, nparams, where in self.pending_calls:
            if kind == "function":
                if name not in self.functions:
                    self.err(f"{where}: call to undefined function {name}{closest(name, self.functions)}")
                elif self.functions[name] != nparams:
                    self.err(f"{where}: {name} called with {nparams} parameters, defined with {self.functions[name]}")
                elif self.returns.get(LOWER(name), "none") != "none":
                    self.err(f"{where}: {name} returns a {self.returns[LOWER(name)]} and is called as an action; the "
                             f"editor stops with \"function '{name}' has wrong return type\". Read it in an expression, "
                             f"{p.functions_object}.{name}{'(...)' if nparams else ''}, or set its return type to none")
            else:
                owners = [owner] + p.families_of(owner)
                hit = next(((o, name) for o in owners if (o, name) in self.custom_actions), None)
                if hit is None:
                    self.err(f"{where}: {owner} has no custom action {name!r}"
                             + closest(name, [n for o, n in self.custom_actions if o in owners]))
                elif self.custom_actions[hit] != nparams:
                    self.err(f"{where}: {owner}.{name} called with {nparams} parameters, "
                             f"defined with {self.custom_actions[hit]}")
        # Signals are not kept: a Wait for signal or On signal that no Signal raises never ends or runs.
        for tag, ace, where in self.awaited if self.signalled is not None else []:
            if tag not in self.signalled:
                self.warn(f"{where}: no Signal action or runtime.signal() raises \"{tag}\", so this "
                          + ("Wait for signal never ends" if ace == "wait-for-signal" else "On signal never runs")
                          + f"; add Signal \"{tag}\" where it should")
        if self.solid_obstacles and self.solid_changes and not self.regenerated:
            places, more = self.solid_changes[:3], len(self.solid_changes) - 3
            self.warn("; ".join(places) + (f" and {more} more" if more > 0 else "")
                      + f": {'this changes' if len(places) == 1 else 'these change'} a Solid while Pathfinding "
                        "takes its obstacles from Solids, and nothing regenerates the obstacle map, which is built "
                        "once at startup: paths keep going round the old obstacles. After a change add Pathfinding "
                        "Regenerate region around object on the Solid, or for many changes Regenerate obstacle map; "
                        "it takes effect the next tick, so a Find path right after it waits first "
                        "(manual: behavior-reference/pathfinding.md)")
        self.check_solid_overlaps()
        self.check_drops()
        self.check_dead_timers()
        self.check_stray_bullets()
        self.check_pending_instances()
        for t in self.created:
            if t in p.types and t not in self.templates:
                self.warn(f"{t} is created at runtime but has no instance in any layout: "
                          f"it is created, but its behavior properties read 0 (a Bullet does not "
                          f"move); place one in a layout that never runs")

    # --- created instances read by a later function in the same actions ------------------------
    def is_object(self, name) -> bool:
        return isinstance(name, str) and (name in self.p.types or name in self.p.families)

    def related(self, a: str, b: str) -> bool:
        return a == b or a in self.p.families_of(b) or b in self.p.families_of(a)

    @staticmethod
    def waits(a: dict) -> bool:
        """Whether the actions after this one run later: a System wait, or a script that awaits."""
        if a.get("type") == "script":
            return "await" in script_text(a.get("script"))
        return a.get("objectClass") == "System" and a.get("id") in WAITS

    def made_by(self, a: dict) -> str | None:
        """The object type or family an action creates instances of, when a literal parameter names it."""
        obj, ace_id = a.get("objectClass"), a.get("id")
        key = CREATING.get((obj, ace_id)) or ("object" if ace_id == "spawn-another-object" else None)
        made = (a.get("parameters") or {}).get(key) if key else None
        return made if self.is_object(made) else None

    def picked_by(self, c: dict) -> str | None:
        """The object type or family a condition picks among the instances that have joined."""
        obj, cid = c.get("objectClass"), c.get("id")
        if obj == "System":
            made = (c.get("parameters") or {}).get("object") if cid in SYSTEM_PICKS else None
            return made if self.is_object(made) else None
        return obj if self.is_object(obj) and cid not in NOT_PICKING else None

    @staticmethod
    def picked_by_link(c: dict) -> str | None:
        """The type a condition picks through a link to an instance rather than among the type's
        instances: Pick by unique ID, Pick last created, or the child or parent of picked instances.
        A condition on that type after it narrows what the link found."""
        cid, params = c.get("id"), c.get("parameters") or {}
        if cid == "pick-by-unique-id":
            return c.get("objectClass")
        if cid == "pick-last-created" and c.get("objectClass") == "System":
            return params.get("object")
        if cid in ("pick-children", "pick-nth-child"):
            return params.get("child")
        return params.get("parent") if cid == "pick-parent" else None

    def called(self, a: dict) -> tuple[str, dict] | None:
        """(the name to print, the block) of the function or custom action an action calls."""
        if "callFunction" in a:
            name = a["callFunction"]
            return (name, self.function_blocks[name]) if name in self.function_blocks else None
        if "customAction" in a:
            owner = a.get("customActionObjectClass", a.get("objectClass"))
            for o in [owner] + self.p.families_of(owner):
                if (o, a["customAction"]) in self.custom_blocks:
                    return f"{owner}.{a['customAction']}", self.custom_blocks[(o, a["customAction"])]
        return None

    def summary(self, block: dict) -> tuple[dict, dict] | None:
        """What a function or custom action does when called, in its own events and the functions they
        call: ({type it creates: [the functions it calls to create it]},
        {type it picks: (where, condition, [the functions it calls to pick it])}).
        None when it waits anywhere, since what follows a wait runs after the instances have joined. A
        condition after a pick through a link on the same type (picked_by_link), or the picks of a custom
        action or a function that copies the caller's picked instances, are not counted: those start from
        instances the caller picked. A cycle of calls counts what is known when it closes."""
        key = id(block)
        if key in self._summaries:
            return self._summaries[key]
        self._summaries[key] = ({}, {})
        made: dict[str, list[str]] = {}
        picked: dict[str, tuple[str, str, list[str]]] = {}

        def visit(ev: dict, uids: set[str]) -> bool:
            if ev.get("eventType") == "script":
                return "await" not in script_text(ev.get("script"))
            uids = set(uids)
            for c in ev.get("conditions") or []:
                if not isinstance(c, dict):
                    continue
                linked = self.picked_by_link(c)
                if linked:
                    uids.add(linked)
                    continue
                t = self.picked_by(c)
                if t and not any(self.related(t, u) for u in uids if isinstance(u, str)):
                    picked.setdefault(t, (self.event_where.get(id(ev), "an event"), describe(c), []))
            for a in ev.get("actions") or []:
                if not isinstance(a, dict):
                    continue
                if self.waits(a):
                    return False
                t = self.made_by(a)
                if t:
                    made.setdefault(t, [])
                hit = self.called(a)
                sub = self.summary(hit[1]) if hit else None
                if sub:
                    for t, chain in sub[0].items():
                        made.setdefault(t, [hit[0]] + chain)
                    if hit[1].get("eventType") == "function-block" and not hit[1].get("functionCopyPicked"):
                        for t, (w, c, path) in sub[1].items():
                            picked.setdefault(t, (w, c, [hit[0]] + path))
            return all(visit(child, uids) for child in ev.get("children") or [] if isinstance(child, dict))

        self._summaries[key] = (made, picked) if visit(block, set()) else None
        return self._summaries[key]

    def check_pending_instances(self) -> None:
        """In one list of actions, a function that creates instances and then a function that picks them
        by a condition: the second runs before the instances join, and misses them."""
        for actions, where in self.action_lists:
            made: dict[str, tuple[int, list[str]]] = {}
            warned: set[tuple[str, str]] = set()
            for i, a in enumerate(actions, 1):
                if not isinstance(a, dict):
                    continue
                if self.waits(a):
                    break  # the rest runs later, where when the instances join is not read here
                t = self.made_by(a)
                if t:
                    made.setdefault(t, (i, []))
                    continue
                hit = self.called(a)
                sub = self.summary(hit[1]) if hit else None
                if not sub:
                    continue
                name, block = hit
                if block.get("eventType") == "function-block":
                    for p, (pwhere, cond, path) in sub[1].items():
                        for t, (j, chain) in made.items():
                            # a function that copies picked instances gets the one the caller created
                            if not self.related(p, t) or (not chain and block.get("functionCopyPicked")) \
                                    or (name, t) in warned:
                                continue
                            warned.add((name, t))
                            by = f"action {j} creates {t}" if not chain else \
                                f"action {j} calls {chain[0]}, which creates {t}" \
                                + (f" through {', '.join(chain[1:])}" if len(chain) > 1 else "")
                            through = f" through {', '.join(path)}" if path else ""
                            self.warn(f"{where} action {i}: {name} picks {p}{through} ({cond} in {pwhere}), but {by} "
                                      f"earlier in the same actions, and that new {t} is not among the "
                                      f"instances {name} picks from: until the top-level event or trigger that "
                                      f"runs these actions ends, only Pick by unique ID finds it outside the "
                                      f"event that created it. Set the new {t} up in the event that creates "
                                      f"it, pass its UID to {name} and pick it there by unique ID, or call "
                                      f"{name} from a later top-level event or trigger "
                                      f"({c3.guide_path(self.p.rag, 'primitives/events/how-events-work.md', self.p.root)})")
                for t, chain in sub[0].items():
                    made.setdefault(t, (i, [name] + chain))
