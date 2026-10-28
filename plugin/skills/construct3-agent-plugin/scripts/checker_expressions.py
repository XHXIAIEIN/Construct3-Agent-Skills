"""The checks of the expressions, parameters, conditions and actions of an event
sheet. A part of check_project.Checker, which holds the state they read."""
import difflib
import json
import math
import re
from pathlib import Path

import c3project as c3
from c3project import LOWER, STRING_LITERAL, closest, describe, folder_items, squash
from checker_common import (
    VARIABLE_TYPES, IDENT, NUMBER, EMPTY_CALL, MEMBER, C_OPERATORS, C_OPERATOR, SHADOW_SUFFIX, is_literal,
    unquote, SPRITE_FONT_TEXT, EFFECT_ACTIONS, call_arguments, FIND_CALL, argument_at, arguments_from,
    outside_literals, top_level_operator, CHOOSEINDEX_CALL, MID_OF_LITERAL, member_types, joined_literals,
    bare, first_few, effect_names, Holder,
)


class ExpressionChecks:
    # --- event sheets: expressions and parameters -------------------------------------------
    def check_expr(self, where: str, expr, scope: dict, owner: str | None = None,
                   stand_in: str | None = None) -> None:
        """owner: the object of the condition or action the expression belongs to;
        Self names it, so Self in a System parameter names nothing, and the editor
        stops with 'Invalid use of self'. stand_in: the object a System parameter
        of the same ACE names, the one to write instead of Self."""
        p = self.p
        if not isinstance(expr, str):
            return
        if not expr.strip():
            self.err(f"{where}: the expression is empty; the editor stops with \"Empty expression: You must enter an "
                     f"expression\". Empty text is the literal \"\" (\"\\\"\\\"\" in the JSON), a number 0")
            return
        if expr.count('"') % 2:  # a quote inside a literal is doubled, so an odd count leaves one open
            self.err(f"{where}: a text literal is not closed; the editor stops with \"Syntax error: String missing "
                     f"finishing \\\"\". A quote inside text is doubled: \"say \"\"hi\"\"\"")
            return
        text = STRING_LITERAL.sub('""', expr)
        if "\\" in text:
            self.err(f"{where}: a backslash stands outside a text literal; the editor stops with \"Syntax error: "
                     f"Unknown character\". Inside text it is a plain character: Construct has no escapes")
        # A list literal [a, b] of JavaScript: the editor stopped a QQ bot's sheet with it (2026-10-06).
        if "[" in text or "]" in text:
            self.err(f"{where}: a square bracket stands outside a text literal; the editor stops with \"Syntax "
                     f"error: Unknown character\". Expressions have no lists: compare each value on its own, "
                     f"a = 1 & b = 2, or keep the values in an Array object")
        scope_lower = {LOWER(k) for k in scope}
        self.check_find(where, expr)
        if self.style:
            self.check_chooseindex(where, expr, scope)
            self.check_letter_table(where, expr)
        found = [m.group(0) for m in C_OPERATOR.finditer(text)]
        if found:
            # Rewrite outside the string literals only: "a == b" as text is valid.
            def construct_operators(code: str) -> str:
                return C_OPERATOR.sub(lambda m: C_OPERATORS.get(m.group(0), m.group(0)), code)
            parts, last = [], 0
            for lit in STRING_LITERAL.finditer(expr):
                parts += [construct_operators(expr[last:lit.start()]), lit.group(0)]
                last = lit.end()
            parts.append(construct_operators(expr[last:]))
            fixed = "".join(parts)
            ops = list(dict.fromkeys(found))
            hint = (f"; write {fixed!r}" if "!" not in found
                    else "; = compares, <> is not equal, & is and, | is or, and a negation is a comparison with 0")
            self.err(f"{where}: {', '.join(ops)} {'is not an operator' if len(ops) == 1 else 'are not operators'} "
                     f"of Construct expressions; the editor stops with "
                     f"\"Syntax error\"{hint}")
        # With a variable or parameter named self in scope, a bare self reads as it; self. is still Self.
        variable_self = "self" in scope_lower
        if owner == "System" and any(LOWER(m.group(0)) == "self" and not (
                variable_self and not text[m.end():].lstrip().startswith(".")) for m in IDENT.finditer(text)):
            pattern = r"\bself\b(?=\s*\.)" if variable_self else r"\bself\b"
            fixed = re.sub(pattern, stand_in, expr, flags=re.I) if stand_in else None
            hint = f"; write {fixed!r}" if fixed else "; name the object instead"
            self.err(f"{where}: Self names the object of the condition or action, and here that is System; "
                     f"the editor stops with \"Invalid use of 'self'\"{hint}")
        for m in MEMBER.finditer(text):
            obj, member, sub = m.group(1), m.group(2), m.group(3)
            if LOWER(obj) == "self" or NUMBER.fullmatch(obj):  # a decimal such as 0.5 is not a member access
                continue
            if LOWER(obj) == LOWER(p.functions_object):
                names = p.expression_names(p.system)
                mapped = [e for e in p.system.get("expressions", [])
                          if c3.is_functions_ace(e) and LOWER(names.get(e["id"], "")) == LOWER(member)]
                defined = LOWER(member) in {LOWER(f) for f in self.functions}
                if mapped and not defined:
                    # Functions.CallMapped is an expression of the Functions object, not a function of the project
                    self.check_arguments(where, f"{obj}.{member}", [(p.system, {"expressions": mapped})], member,
                                         text, m.end(2), scope)
                elif not defined:
                    self.err(f"{where}: {obj}.{member} is not a defined function")
                elif self.returns.get(LOWER(member)) == "none":
                    self.err(f"{where}: {obj}.{member} has no return type, and the editor stops with \"The function "
                             f"'{member}' has a return type of 'None' so cannot be used as an expression\": give it a "
                             f"return type and a Set return value, or call it as an action")
                elif EMPTY_CALL.match(text, m.end(2)):
                    # No official example writes an empty pair; the editor stops at it (r504, 2026-10-02).
                    self.err(f"{where}: {obj}.{member}() has an empty pair of parentheses; the editor stops with "
                             f"\"Syntax error: ')' can't go here\". A function without parameters is called "
                             f"without them: {obj}.{member}")
                continue
            obj = p.objects_lower.get(LOWER(obj))
            if obj is None or obj == "System":
                # JSON.Get names the plugin; an expression is reached through the project's object of it.
                users = [n for n, pl in p.plugin_of.items() if squash(pl) == squash(m.group(1)) and pl != "system"]
                hint = f"; {m.group(1)} is the plugin, the object of it here is {', '.join(users)}" if users \
                    else closest(m.group(1), p.plugin_of)
                self.err(f"{where}: unknown object {m.group(1)} in expression{hint}")
                continue
            behs = {LOWER(k): v for k, v in p.behaviors_of(obj).items()}
            if LOWER(member) in behs:
                bs = p.schema("behaviors", behs[LOWER(member)])
                if bs is None:
                    continue
                retired = p.deprecated_expressions("behaviors", behs[LOWER(member)]).get(LOWER(sub or ""))
                if retired:
                    self.deprecated_use(where, self.deprecated_expression(f"{obj}.{member}.{sub}", behs[LOWER(member)], retired))
                elif sub is None or LOWER(sub) not in p.expressions_of(bs):
                    self.err(f"{where}: {obj}.{member}.{sub or ''} is not an expression of behavior "
                             f"{behs[LOWER(member)]}")
                else:
                    self.check_arguments(where, f"{m.group(1)}.{member}.{sub}", [(bs, None)], sub, text, m.end(3), scope)
                continue
            plugin = p.schema("plugins", p.plugin_of[obj])
            if plugin is None:
                continue
            ivars = {LOWER(v) for v in p.ivars_of(obj)}
            retired = p.deprecated_expressions("plugins", p.plugin_of[obj]).get(LOWER(member))
            if retired is None and LOWER(member) in p.common_expressions_of(plugin):
                retired = p.deprecated_expressions("plugins", "_common").get(LOWER(member))
            if retired and LOWER(member) not in ivars:
                self.deprecated_use(where, self.deprecated_expression(f"{obj}.{member}", p.plugin_of[obj], retired))
                continue
            known = p.expressions_of(plugin) | p.common_expressions_of(plugin) | ivars
            if LOWER(member) not in known:
                # Platform.Speed is reached as Player.Platform.Speed, through the behavior's name on the object.
                owner = next((name for name, b in p.behaviors_of(obj).items()
                              if LOWER(member) in p.expressions_of(p.schema("behaviors", b))), None)
                hint = f"; it is an expression of a behavior: {obj}.{owner}.{member}" if owner \
                    else closest(member, known)
                self.err(f"{where}: {obj}.{member} is neither an expression nor an instance variable of {obj}{hint}")
            elif LOWER(member) not in ivars and sub is None:
                self.check_arguments(where, f"{m.group(1)}.{member}", [(plugin, None), (p.common, p.common_of(plugin))],
                                     member, text, m.end(2), scope)
        for m in IDENT.finditer(text):
            name = m.group(0)
            if NUMBER.fullmatch(name):
                continue
            if text[:m.start()].rstrip().endswith(".") or text[m.end():].lstrip().startswith("."):
                continue
            if LOWER(name) in scope_lower:
                continue
            retired = p.deprecated_expressions("plugins", "system").get(LOWER(name))
            if retired:
                self.deprecated_use(where, self.deprecated_expression(name, "System", retired))
                continue
            if LOWER(name) in p.system_expressions:
                self.check_arguments(where, name, [(p.system, None)], name, text, m.end(), scope)
                continue
            if LOWER(name) in p.objects_lower and text[m.end():].lstrip().startswith("("):
                continue
            hint = closest(name, list(scope) + list(p.plugin_of))
            if LOWER(name) in p.objects_lower:
                hint = f"; {p.objects_lower[LOWER(name)]} is an object, write {p.objects_lower[LOWER(name)]}.<expression>"
            elif LOWER(name) in ("true", "false"):
                hint = ("; an expression has no true or false, a comparison gives 1 or 0. Test a boolean "
                        "variable with System compare-boolean-eventvar, inverted for false, and set it with System "
                        "set-boolean-eventvar; a boolean instance variable with is-boolean-instance-variable-set "
                        "and set-boolean-instvar")
            elif LOWER(name) in ("if", "then", "else"):
                hint = "; an expression chooses with condition ? a : b"
            elif text.strip() == name:
                hint += f"; a text value carries inner quotes: \"\\\"{name}\\\"\""
            self.err(f"{where}: identifier {name!r} is not a variable, parameter or system expression{hint}")

    def check_find(self, where: str, expr: str) -> None:
        """find or findcase with a one-character literal first and an expression second:
        a one-character text holds nothing longer, so the literal is the text searched for."""
        for m in outside_literals(expr, FIND_CALL.finditer(expr)):
            if len(unquote(m.group(2))) != 1:
                continue
            second = argument_at(expr, m.end())
            if not second or STRING_LITERAL.fullmatch(second):
                continue
            name, first = m.group(1), m.group(2)
            self.warn(f"{where}: {name}({first}, {second}) searches the one-character text {first} for {second}, "
                      f"so it is -1 unless {second} is {first} or empty; {name}(text, find) takes the text to search "
                      f"first: write {name}({second}, {first})")

    def is_boolean(self, expr: str, scope: dict) -> bool:
        """A comparison or logical expression, or a boolean variable: local, global or instance."""
        if top_level_operator(expr):
            return True
        m = re.fullmatch(r"\s*(?:(\w+)\s*\.\s*)?(\w+)\s*", expr)
        if not m:
            return False
        if m.group(1) is None:
            return (self.variable_named(m.group(2), scope) or {}).get("type") == "boolean"
        types = {LOWER(k): v for k, v in self.p.ivar_types_of(m.group(1)).items()}
        return types.get(LOWER(m.group(2))) == "boolean"

    def check_chooseindex(self, where: str, expr: str, scope: dict) -> None:
        """chooseindex(condition, a, b) as an if-else: it returns b when the condition is
        true, the reverse of the order it is read in. The examples write condition ? b : a."""
        for m in outside_literals(expr, CHOOSEINDEX_CALL.finditer(expr)):
            args = arguments_from(expr, m.end())
            if len(args) != 3 or not self.is_boolean(args[0], scope):
                continue
            test, if_false, if_true = args
            self.p.findings.style_finding(
                "choice", f"{where}: chooseindex({test}, {if_false}, {if_true}) is a two-way choice on a condition, "
                          f"which returns its last value when the condition is true; Construct's conditional "
                          f"operator reads in that order: write {test} ? {if_true} : {if_false}")

    def check_letter_table(self, where: str, expr: str) -> None:
        """mid("<letters>", find("<letters>", X) ..., 1): a value mapped through two text
        literals, a table or a cycle of letters."""
        for m in outside_literals(expr, MID_OF_LITERAL.finditer(expr)):
            position = argument_at(expr, m.end())
            for f in outside_literals(position, FIND_CALL.finditer(position)):
                looked_up = argument_at(position, f.end())
                letters = unquote(f.group(2))
                self.p.findings.style_finding(
                    "table", f"{where}: mid({m.group(1)}, {position}, ...) looks {looked_up} up through the letters "
                             f"{f.group(2)}, a table written as text; keep {looked_up} as a number 0 to "
                             f"{len(letters) - 1}: the next one in a cycle is ({looked_up} + 1) % {len(letters)}, "
                             f"as alien-battle steps (AnimationState + 1) % 3, and a value that maps to another "
                             f"is a Dictionary key or an Array index loaded from a project file")
                break

    def check_find_dispatch(self, tests: dict[str, list[tuple[int, str, str]]]) -> None:
        """Sibling events that test one text with find for different codes: a mini-language
        dispatched by substring. find matches any part of the text and ignores case, so the
        branch of "B" fires for "BU" too."""
        for subject, hits in tests.items():
            events = sorted({(n, w) for n, w, _ in hits})
            if len(events) < 2:
                continue
            codes = sorted({lit for _, _, lit in hits}, key=lambda s: (len(s), s))
            plain = [unquote(c).lower() for c in codes]
            overlap = next(((a, b) for i, a in enumerate(plain) for b in plain[i + 1:] if a and a in b), None)
            because = (f"\"{overlap[0]}\" also matches \"{overlap[1]}\", so a wrong branch runs" if overlap else
                       "a code that contains another runs that one's branch too")
            others = ", ".join(str(n) for n, _ in events[1:])
            self.p.findings.style_finding(
                "dispatch", f"{events[0][1]}: with events {others}, picks a branch by testing {subject} for the codes "
                            f"{', '.join(codes)} with find, which matches any part of the text and ignores case: "
                            f"{because}. Keep each fact in a field of its own, a text field such as kind compared "
                            f"with = (an instance variable, or a field of a JSON or Array project file) and numbers "
                            f"such as amount and times in number fields")

    def check_arguments(self, where: str, written: str, sources: list[tuple[dict, dict | None]], name: str,
                        text: str, end: int, scope: dict) -> None:
        """The arguments of an expression call against the parameters its schema lists.
        sources: (schema, the part of it that applies) in order; the first that has an
        expression of this name decides. The editor stops with "Incorrect parameters:
        'LocalStorage.ItemValue' does not accept 1 parameters"; LocalStorage.ItemValue
        reads the item the last Get item fetched and takes none."""
        for schema, part in sources:
            names = self.p.expression_names(schema)
            entry = next((e for e in (part or schema or {}).get("expressions", [])
                          if LOWER(names.get(e["id"], "")) == LOWER(name)), None)
            if entry is None:
                continue
            params = list(entry.get("params") or {})
            given = call_arguments(text, end)
            # isVariadicParameters: more may follow the listed ones, Mouse.X("HUD"), Array.At(x, y), max(a, b, c)
            more = entry.get("isVariadicParameters")
            if given < len(params) or given > len(params) and not more:
                usage = f"{written}({', '.join(params)}{', ...' if more else ''})" if params or more else written
                # The message is the one r495.2 gave for one argument too many; too few was not probed.
                self.err(f"{where}: {written} takes {'at least ' if more else ''}{len(params)} "
                         f"parameter{'' if len(params) == 1 else 's'} and is given {given}; the editor stops with "
                         f"\"Incorrect parameters: '{written}' does not accept {given} parameters\". Write {usage}")
                return
            if given:
                self.check_argument_types(where, written, entry.get("params") or {}, text,
                                          text.index("(", end) + 1, scope)
            return

    def check_argument_types(self, where: str, written: str, params: dict, text: str, start: int,
                             scope: dict) -> None:
        """A number where the parameter takes text, or text where it takes a number: the editor
        types each argument and stops with "parameter 0 does not take 'number'". Only a literal
        or a variable has a type known here. The official examples convert first, even a
        literal: DictRewards.Get(str(9)), DictProfile.Get(str(Self.slotID))."""
        for i, (arg, (key, param)) in enumerate(zip(arguments_from(text, start), params.items())):
            wanted = param.get("type")
            if wanted not in ("string", "number"):
                continue
            given = self.argument_type(arg, scope)
            if given is None or given == wanted:
                continue
            if wanted == "string":
                takes, what, fix = "text", f"the number {arg}", f"Write str({arg}) there"
            elif arg == '""':
                takes, what, fix = "a number", "a text literal", "Write the number without quotes"
            else:
                takes, what, fix = "a number", f"the text {arg}", f"Write int({arg}) there"
            self.err(f"{where}: {written} takes {takes} as its parameter {key} and is given {what}; the editor "
                     f"stops with \"parameter {i} does not take '{given}'\". {fix}")

    def argument_type(self, arg: str, scope: dict) -> str | None:
        """string or number for a literal, a variable or an object's instance variable; None
        for anything else. Text literals are blanked to "" in the text checked."""
        if arg == '""':
            return "string"
        if NUMBER.fullmatch(arg.lstrip("-").strip()):
            return "number"
        m = re.fullmatch(r"(?:(\w+)\s*\.\s*)?(\w+)", arg)
        if not m:
            return None
        if m.group(1) is None:
            vtype = (self.variable_named(m.group(2), scope) or {}).get("type")
        else:
            obj = self.p.objects_lower.get(LOWER(m.group(1)))
            if obj is None or obj == "System":
                return None
            vtype = {LOWER(k): v for k, v in self.p.ivar_types_of(obj).items()}.get(LOWER(m.group(2)))
        return vtype if vtype in ("string", "number") else None

    @staticmethod
    def deprecated_expression(written: str, owner: str, retired: tuple[str, dict]) -> str:
        """The warning for an expression the editor has deprecated: it still opens the project."""
        _, entry = retired
        return (f"{written} is a deprecated expression of {owner}: {c3.DEPRECATED}"
                + (f"; the current expression of the same name is {entry['current']}" if entry.get("current") else ""))

    def project_property_wording(self, key: str) -> tuple[str, dict[str, str]]:
        """The Properties bar's name of a project property and of its options in the locale,
        so a finding names them as the user's editor shows them: fullscreenMode is 缩放模式 in zh-CN."""
        pack = self.p.rag / "data" / "c3-lang" / f"{self.p.locale}.json"
        if not pack.exists():
            return "", {}
        bar = c3.load(pack)["text"]["ui"]["bars"]["properties"]["project"]
        entry = bar.get(re.sub(r"(?<!^)(?=[A-Z])", "-", key).lower(), {})
        return entry.get("name", ""), entry.get("options", {})

    def builtin_eases(self) -> set[str]:
        """Ids of the built-in eases, the keys the editor's language pack labels."""
        if not self._eases:
            pack = self.p.rag / "data" / "c3-lang" / "en-US.json"
            if pack.exists():
                self._eases.update(c3.load(pack)["text"]["ui"]["bars"]["timeline"]["eases"])
        return self._eases

    def project_eases(self) -> set[str]:
        """Names of the project's custom eases: the timelines items whose file holds
        transitionKeyframes, which the editor saves under timelines/transitions/."""
        out = set()
        for name, folder in folder_items(self.p.data.get("timelines", {})):
            path = self.p.project_file("timelines", name, folder)
            if path and "transitionKeyframes" in c3.load(path):
                out.add(name)
        return out

    def check_param(self, where: str, key: str, value, ptype: str, items: dict | None, obj: str, scope: dict,
                    writes: bool = False, stand_in: str | None = None) -> None:
        """writes: the parameter belongs to an action, which assigns the variable it names.
        stand_in: the object an "object" parameter of the same ACE names."""
        p = self.p
        if ptype == "cmp":
            if value not in (0, 1, 2, 3, 4, 5) or isinstance(value, bool):
                self.err(f"{where}: comparison {value!r} is not an integer 0-5 (=, ≠, <, ≤, >, ≥)")
        elif ptype == "boolean":
            if not isinstance(value, bool):
                self.err(f"{where}: {key} should be a JSON boolean, not {value!r}")
        elif ptype in ("combo", "combo-grouped"):
            if items and value not in items:
                self.err(f"{where}: {key}={value!r} is not one of {list(items)}{bare(value, items)}; the editor "
                         f"opens the project and silently keeps the default item instead")
        elif ptype == "keyb":
            if not isinstance(value, int) or isinstance(value, bool):
                self.err(f"{where}: {key}={value!r} should be a key code, a JSON number such as 32 for Space or "
                         f"37-40 for the arrows; the editor stops with 'expected finite number'")
        elif ptype == "ease":
            eases = self.builtin_eases()
            if isinstance(value, str) and eases and value not in eases and not p.data.get("eases"):
                custom = self.project_eases()
                if value not in custom:
                    self.err(f"{where}: {key}={value!r} is neither a built-in ease nor a custom ease of the "
                             f"project{closest(value, eases | custom)}")
        elif ptype == "audiofile":
            # The editor looks the name up among the sound and music files, without the extension and
            # in any case, and refuses the project on any other value: "missing file '0'". The official
            # examples write the name as a string; a project saved by r495 writes {"path": "Name"}.
            stems = [Path(n["name"] if isinstance(n, dict) else n).stem
                     for kind in ("sound", "music")
                     for n, _ in folder_items(p.data.get("rootFileFolders", {}).get(kind, {}))]
            name = value["path"] if isinstance(value, dict) else value
            name = unquote(name) if is_literal(name) else name
            if not isinstance(name, str) or LOWER(name) not in {LOWER(s) for s in stems}:
                near = closest(Path(name).stem, stems) if isinstance(name, str) else ""
                shown = first_few(stems, 8)
                listed = f"; the project has {shown}" if stems else "; the project has none"
                self.err(f"{where}: {key}={value!r} is not a sound or music file of the project; the editor stops "
                         f"with \"missing file {name!r}\". Write the file's name without its extension"
                         + (near or listed))
        elif ptype == "function":
            # Map function and Map default function name a function block, without case; for any
            # other name the editor stops with "cannot find function 'FnRed'" (r495.2, 2026-10-09).
            # declared_functions() has read every sheet before the walk, so a later block counts.
            if not isinstance(value, str) or LOWER(value) not in {LOWER(f) for f in self.functions}:
                shown = first_few(list(self.functions), 8)
                listed = f"; the project has {shown}" if self.functions else "; the project has none"
                self.err(f"{where}: {key}={value!r} is not a function of the project; the editor stops with "
                         f"\"cannot find function {value!r}\". Add a function block named {value} or name one "
                         f"the project has"
                         + (bare(value, self.functions) or closest(value, self.functions) or listed))
        elif ptype in ("tilemapbrush", "model3d", "objecteffect"):
            return
        elif ptype == "template":
            # a name in an expression, "\"\"" for none; written "" the editor does not open the project
            self.check_expr(f"{where} {key}", value, scope, obj, stand_in)
        elif ptype == "object":
            if value not in p.plugin_of or value == "System":
                self.err(f"{where}: {key}={value!r} is not an object type or family"
                         + (bare(value, p.plugin_of) or closest(value, p.plugin_of)))
        elif ptype in ("instancevar", "instancevarbool"):
            # shared ACEs name one of the object's own variables
            ivars = p.ivar_types_of(obj)
            if value not in ivars:
                self.err(f"{where}: {obj} has no instance variable {value!r}{bare(value, ivars) or closest(value, ivars)}")
            elif ptype == "instancevarbool" and ivars[value] != "boolean":
                self.err(f"{where}: instance variable {value!r} is not a boolean")
        elif ptype == "objinstancevar":
            target, ivar = (value.get("objectClass", obj), value.get("name")) if isinstance(value, dict) else (obj, value)
            if ivar not in p.ivars_of(target):
                self.err(f"{where}: {target} has no instance variable {ivar!r}{closest(ivar or '', p.ivars_of(target))}")
        elif ptype in ("eventvar", "eventvarbool", "eventvarany"):
            var = self.variable_named(value, scope)
            if var is None:
                self.err(f"{where}: variable {value!r} is not in scope{bare(value, scope) or closest(value, scope)}")
            elif ptype == "eventvarbool" and var["type"] != "boolean":
                self.err(f"{where}: variable {value!r} is not a boolean")
            elif writes and var.get("isConstant") and var["name"] != value and value in self.variable_names:
                kind = "global" if id(var) in self.global_ids else "local"
                self.err(f"{where}: {value} is read as the {kind} constant {var['name']}: the editor finds a "
                         f"variable by its name without case, so the action writes {var['name']} and the editor "
                         f"stops with 'event variable {value} is constant'. Rename the variable {value}, here and "
                         f"wherever it is declared and used, so that it differs from {var['name']} by more than "
                         f"case, for example {value}{SHADOW_SUFFIX.get(var.get('type'), 'Value')}")
            elif writes and var.get("isConstant"):
                self.err(f"{where}: {value} is a constant and an action cannot change it; "
                         f"the editor stops with 'event variable {value} is constant'")
        elif ptype == "layer":
            if is_literal(value):
                if unquote(value) not in self.layers and not self.off:
                    self.err(f"{where}: no layer named {unquote(value)!r} in any layout")
            else:
                self.check_expr(f"{where} {key}", value, scope, obj, stand_in)
        elif ptype == "layout":
            if value not in self.layouts:
                self.err(f"{where}: no layout named {value!r}{bare(value, self.layouts) or closest(value, self.layouts)}")
        elif ptype == "groupname":
            if is_literal(value) and unquote(value) not in self.group_titles and not self.off:
                self.err(f"{where}: no group titled {unquote(value)!r}")
        elif ptype == "animation":
            anims = p.animations_of(obj)
            if is_literal(value):
                if anims is not None and LOWER(unquote(value)) not in anims and not self.off:
                    self.err(f"{where}: {obj} has no animation {unquote(value)!r}")
            else:
                self.check_expr(f"{where} {key}", value, scope, obj, stand_in)
        elif ptype == "projectfile":
            name = value["path"] if isinstance(value, dict) else value
            if not (p.root / "files" / name).exists() and not list((p.root / "files").rglob(Path(name).name)):
                self.err(f"{where}: project file {name!r} is not in files/")
        elif ptype == "timeline":
            if value not in [n for n, _ in folder_items(p.data.get("timelines", {}))]:
                self.err(f"{where}: no timeline named {value!r}")
        elif ptype == "flowchart":
            if value not in [n for n, _ in folder_items(p.data.get("flowcharts", {}))]:
                self.err(f"{where}: no flowchart named {value!r}")
        else:
            if not isinstance(value, str):
                self.err(f"{where}: {key} should be an expression string, not {value!r}")
            else:
                self.check_expr(f"{where} {key}", value, scope, obj, stand_in)

    # --- event sheets: conditions and actions -------------------------------------------------
    def ace_hint(self, kind: str, ace: dict) -> str:
        """Where an id the schema does not have under this object does exist: on one
        of its behaviors, on the object itself, as the other kind, or under a near
        spelling (the script name and the list name are tried as well as the id)."""
        p = self.p
        obj, ace_id = ace["objectClass"], ace["id"]
        if "behaviorType" not in ace:
            for name, behavior_id in p.behaviors_of(obj).items():
                s = p.schema("behaviors", behavior_id)
                if s and any(it["id"] == ace_id for it in s.get(kind, [])):
                    return f"; it belongs to the behavior {name}: add \"behaviorType\": \"{name}\""
        elif any(it["id"] == ace_id for s in p.ace_sources({"objectClass": obj}) for it in s.get(kind, [])):
            return "; it belongs to the object itself: remove \"behaviorType\""
        sources = p.ace_sources(ace)
        other = "actions" if kind == "conditions" else "conditions"
        found = next((it for s in sources for it in s.get(other, []) if it["id"] == ace_id), None)
        if found:
            # where to move it: told only "not its actions", a small model rewrote the loop away (2026-10-04)
            where = (f": move it into the \"conditions\" of this event" + (
                     ", or of a sub-event whose actions are the ones to repeat; a loop is a condition, and the actions "
                     "of its event run once per pass" if found.get("isLooping") else "")
                     if kind == "actions" else ": move it into the \"actions\" of this event")
            return f"; {ace_id} is one of its {other}, not its {kind}{where}"
        spellings = {}
        for s in sources:
            for it in s.get(kind, []):
                for text in (it["id"], it.get("scriptName", ""), it.get("list-name", "")):
                    spellings.setdefault(squash(text), it["id"])
        if squash(ace_id) in spellings:
            return f"; the id is {spellings[squash(ace_id)]!r}"
        near = difflib.get_close_matches(squash(ace_id), list(spellings), n=4, cutoff=0.6)
        ids = list(dict.fromkeys(spellings[n] for n in near))[:3]
        return "; closest: " + ", ".join(ids) if ids else ""

    def check_ace(self, kind: str, ace: dict, scope: dict, where: str) -> None:
        p = self.p
        obj = ace.get("objectClass")
        ace_id = ace.get("id")
        params = ace.get("parameters", {})
        where = f"{where} {obj}:{ace_id}"
        if obj is None or ace_id is None:
            self.err(f"{where}: a {kind[:-1]} needs \"objectClass\" and \"id\"")
            return
        if obj not in p.plugin_of:
            self.err(f"{where}: unknown object {obj}{closest(obj, p.plugin_of)}")
            return
        if "behaviorType" in ace and ace["behaviorType"] not in p.behaviors_of(obj):
            self.err(f"{where}: {obj} has no behavior {ace['behaviorType']}"
                     f"{closest(ace['behaviorType'], p.behaviors_of(obj))}; "
                     f"\"behaviorType\" is the name the behavior has on the object, not its id")
            return
        if not p.ace_sources(ace):
            return  # no schema for this addon: warned about once, nothing to check against
        entry = p.ace_entry(kind, ace)
        retired = p.deprecated_entry(kind, ace)
        if retired:
            # The editor opens a project that uses it, so this is no error, but a new event should not.
            owner, dep = retired
            owner = "System" if owner == "system" else owner
            self.deprecated_use(where, f"{kind[:-1]} {ace_id} of {owner} is deprecated: {c3.DEPRECATED}"
                                + ("" if entry else ", and its parameters are not checked")
                                + (f"; the current {kind[:-1]} of the same name is {dep['current']}"
                                   if dep.get("current") else ""))
            if entry is None:
                return
        if entry is None:
            owner = p.behaviors_of(obj)[ace["behaviorType"]] if "behaviorType" in ace else p.plugin_of[obj]
            shared = "behaviorType" not in ace and obj != "System" and \
                any(it["id"] == ace_id for it in (p.common or {}).get(kind, []))
            self.err(f"{where}: {owner} has no {kind[:-1]} {ace_id}"
                     + (f": it is in plugins/_common.json, but the editor gives it only to plugins that ask for "
                        f"it, not to {owner}, and does not open the project" if shared
                        else "" if "behaviorType" in ace or obj == "System" else " (not in _common either)")
                     + self.ace_hint(kind, ace))
            return
        schema_params = entry.get("params") or {}
        if not isinstance(params, dict):
            self.err(f"{where}: \"parameters\" should be an object keyed by parameter id: "
                     f"{', '.join(schema_params) or 'none here'}")
            return
        for k in params:
            if k not in schema_params:
                self.err(f"{where}: unknown parameter {k}; the parameters are: {', '.join(schema_params) or 'none'}")
        for k in schema_params:
            if k not in params:
                if not self.review:  # the editor saves an ACE so and fills it on open
                    self.warn(f"{where}: parameter {k} is omitted; the editor fills its default")
        named = [v for k, v in params.items() if schema_params.get(k, {}).get("type") == "object"]
        stand_in = named[0] if len(named) == 1 and named[0] in p.plugin_of else None
        for k, v in params.items():
            if k not in schema_params:
                continue
            self.check_param(where, k, v, schema_params[k]["type"], schema_params[k].get("items"), obj, scope,
                             writes=kind == "actions", stand_in=stand_in)
        if self.off:
            return  # what follows is about what the action does when it runs
        if kind == "actions" and ace_id in EFFECT_ACTIONS:
            self.check_effect_name(where, obj, ace_id, params)
        if kind == "actions" and ace_id in SPRITE_FONT_TEXT and isinstance(params.get("text"), str) \
                and p.plugin_of[obj].lower() == "spritefont2":
            members = member_types(p.families, obj)
            sets = [self.font_sets[m] for m in members if m in self.font_sets]
            if sets:
                charset, bbcode = set().union(*(s for s, _ in sets)), any(b for _, b in sets)
                for literal in joined_literals(params["text"]):
                    self.check_sprite_font_text(f"{where} text", obj, literal, charset, bbcode)
        if ace_id == "create-object" and obj == "System":
            self.created.add(params.get("object-to-create"))
        if ace_id == "set-eventvar-value" and \
                (self.variable_named(params.get("variable"), scope) or {}).get("type") == "boolean":
            self.err(f"{where}: Set value on boolean {params['variable']}; use Set boolean")

    def check_effect_name(self, where: str, obj: str, ace_id: str, params: dict) -> None:
        """An effect named in a literal that the object, the layer or the layouts do not carry: the action runs
        and changes nothing. An object reaches its families' effects. A family's action accepts its members'
        effects, and a layer's the effects of that layer in any layout: whether the runtime resolves those
        was not probed."""
        p = self.p
        name = params.get("effect")
        if not is_literal(name):
            return
        name = unquote(name)
        if ace_id.startswith("set-layer-"):
            layer = params.get("layer")
            if not is_literal(layer) or unquote(layer) not in self.layer_effects:
                return  # a layer by number or expression, or one check_param already says is missing
            names, add = self.layer_effects[unquote(layer)], "the layer's Effects"
            missing, held = f"the layer {unquote(layer)} has no effect named {name!r}", "it has"
        elif ace_id.startswith("set-layout-"):
            names, add = self.layout_effects, "the layout's Effects"
            missing, held = f"no layout has an effect named {name!r}", "the layouts have"
        else:
            holders = [obj] + p.families_of(obj) + (p.families[obj].get("members", []) if obj in p.families else [])
            names = set().union(*(effect_names(p.types.get(h) or p.families.get(h) or {}) for h in holders))
            missing, held, add = f"{obj} has no effect named {name!r}", "it has", f"{obj}'s Effects"
        if LOWER(name) not in {LOWER(n) for n in names}:
            has = f"{held} {', '.join(sorted(names))}" if names else f"{held} none"
            self.warn(f"{where}: {missing} ({has}), so the action runs and changes nothing; add the effect in "
                      f"{add}, or name one it has")

    def check_structure(self, ev: dict, where: str, above: Holder | None, previous: dict | None) -> Holder | None:
        """Where a condition may stand. These are the editor's own rules, the first
        three applied as it opens the project and the fourth before every preview:
        an event branch, from the top-level event down to a leaf, holds one trigger,
        and a function or a custom action counts as one (only an OR block lists
        several); a trigger, a loop and a condition the schema marks
        isInvertible: false cannot be inverted; a function cannot be an OR block;
        Else is the first condition of an event that directly follows a plain event.

        above is the holder of the branch's trigger so far, previous the sibling
        before this event with comments skipped. Returns the holder for the
        sub-events: above, or this event if it brings the trigger."""
        p = self.p
        conds = [c for c in ev.get("conditions", []) if "id" in c]
        entries = [p.ace_entry("conditions", c) or {} for c in conds]
        is_function = ev.get("eventType") != "block"
        triggers = [c for c, e in zip(conds, entries) if e.get("isTrigger")]
        if is_function and ev.get("isOrBlock"):
            self.err(f"{where}: a function or custom action cannot be an OR block")
        if triggers and (above or is_function):
            holder = above.text if above else "a function or custom action, which counts as a trigger"
            self.err(f"{where}: {describe(triggers[0])} is a trigger inside {holder}; the editor stops with 'cannot "
                     f"add another trigger to event branch'. Move it to an event of its own, outside, and test the "
                     f"rest in sub-events")
        elif len(triggers) > 1 and not ev.get("isOrBlock"):
            self.err(f"{where}: {' and '.join(describe(c) for c in triggers)} are two triggers in one event; the "
                     f"editor stops with 'cannot add another trigger to event branch'. One event per trigger, or an "
                     f"OR block")
        for c, e in zip(conds, entries):
            # Both findings are fixed in the condition itself, so they name it, as check_ace does.
            its = f"{where} condition {next(i for i, x in enumerate(ev['conditions'], 1) if x is c)}"
            if c.get("isInverted") and (e.get("isTrigger") or e.get("isLooping") or e.get("isInvertible") is False):
                kind = "a trigger" if e.get("isTrigger") else "a loop" if e.get("isLooping") else "this condition"
                self.err(f"{its}: {describe(c)} is inverted, and {kind} cannot be; "
                         f"the editor stops with 'condition not invertible'")
            # Trigger once, Every X seconds: the editor keeps them out of a triggered branch, where they
            # are tested only in the tick the trigger fires. Else has its own rule below.
            if e.get("isCompatibleWithTriggers") is False and c["id"] != "else" and not self.off \
                    and (triggers or (above and above.fires)):
                self.warn(f"{its}: {describe(c)} is in a branch run by the trigger "
                          f"{describe(triggers[0]) if triggers else above.name}; the editor does not offer it there, "
                          f"since it is only tested when the trigger fires")
        for i, c in enumerate(conds):
            if c.get("objectClass") != "System" or c["id"] != "else":
                continue
            problem = None
            before = [b for b in (previous or {}).get("conditions", []) if "id" in b]
            flags = [p.ace_entry("conditions", b) or {} for b in before]
            if ev.get("isOrBlock") or is_function:
                problem = "its event is " + ("an OR block" if ev.get("isOrBlock") else "a function")
            elif triggers:
                problem = f"its event has the trigger {describe(triggers[0])}"
            elif i != 0:
                problem = "it is not the first condition of its event"
            elif previous is None or previous.get("eventType") != "block":
                problem = "it is the first event of its list" if previous is None else \
                    f"it follows a {previous.get('eventType')}, and only comments may stand between it and the " \
                    f"event it answers"
            elif len(before) == 1 and describe(before[0]) == "System:else":
                problem = "it follows an event whose only condition is Else"
            elif any(f.get("isTrigger") for f in flags):
                problem = "it follows a triggered event"
            elif any(f.get("isLooping") for f in flags):
                problem = "it follows a loop"
            if problem:
                self.err(f"{where}: Else cannot stand here, {problem}; the editor refuses to preview ('An Else "
                         f"condition cannot be placed here'). Use a second event with the inverted condition")
        if above:
            return above
        if is_function:
            kind = "function" if ev.get("eventType") == "function-block" else "custom action"
            return Holder(f"the {kind} {ev.get('functionName') or ev.get('aceName')}", False)
        return Holder(describe(triggers[0]), True) if triggers else None

    def check_variable(self, var: dict, where: str, what: str) -> None:
        """An event variable or a function parameter: its type is one of three and its
        initialValue is text, as the editor writes it. The editor reads a boolean by
        comparing the text to "true", in the editor and again on export, so a JSON
        true or a "True" reads as false; a function parameter may also carry a
        number, anything else stops the load with 'invalid type of initialValue'."""
        name, vtype, value = var.get("name"), var.get("type"), var.get("initialValue")
        w = f"{where}: {what} {name}"
        if isinstance(name, str) and LOWER(name) in self.p.system_expression_names:
            # A local mid passed as Functions.measure(mid) is read as the text function mid(), and
            # a parameter round in "第 " & round & " 轮" as round() with no argument; the editor
            # refuses the project either way (r504, 2026-10-02). None of the 2697 variables and
            # 1028 function parameters of the official examples shares a system expression's name.
            said = ("\"Invalid expressions ... parameter 0 does not take 'string'\" for a local mid"
                    if what == "variable" else "\"'round' does not accept 0 parameters\" for a parameter round")
            self.err(f"{w}: the name is that of the system expression {LOWER(name)}, which wins inside an "
                     f"expression: {name} there is read as {LOWER(name)}(), not as the {what}, and the editor "
                     f"refuses the project ({said}); rename it, for example {name}Value, where it is declared "
                     f"and where it is used")
        if vtype not in VARIABLE_TYPES:
            self.err(f"{w}: type {vtype!r} is not number, string or boolean")
            return
        if what == "parameter" and isinstance(value, (int, float)) and not isinstance(value, bool):
            value = str(value)
        if not isinstance(value, str):
            if vtype == "boolean":
                self.err(f"{w}: initialValue should be the text \"true\" or \"false\", not {value!r}; "
                         f"the editor compares the text to \"true\", so a JSON boolean reads as false")
            else:
                self.err(f"{w}: initialValue should be text, {json.dumps(str(value if value is not None else ''))}, "
                         f"not {value!r}; the editor stores every initial value as text")
        elif vtype == "boolean" and value not in ("true", "false"):
            self.err(f"{w}: initialValue {value!r} should be \"true\" or \"false\", lowercase; "
                     f"the editor compares the text to \"true\" and reads anything else as false")
        elif vtype == "number":
            try:
                finite = math.isfinite(float(value))
            except ValueError:
                finite = False
            if not finite:
                self.err(f"{w}: initialValue {value!r} is not a number; the editor reads it as 0")

    def check_shadow(self, var: dict, other: dict, where: str, visible: str) -> None:
        """A local or parameter named like a global, compared without case. The editor keeps
        both names, and in the local's scope the global's name refers to the local. A text
        count beside a number COUNT makes COUNT - 1 there "Type mismatch: - does not work with
        'string' and 'number'", which stops the open. With a local of the same type under
        another case the project opens, and the global's spelling there reads the local. No
        official example declares a local named like a variable in scope. visible: where the
        local is visible."""
        name, outer = var["name"], other["name"]
        if other.get("type") != var.get("type"):
            self.err(f"{where}: {var.get('type')} {name} has the name of the {other.get('type')} variable {outer} "
                     f"once case is ignored, and it hides it here and in the sub-events; an expression that means "
                     f"{outer} reads {name}, and the editor refuses the project with \"Type mismatch\" "
                     f"(\"- does not work with 'string' and 'number'\" for a text local beside a number); rename it, "
                     f"for example {name}{SHADOW_SUFFIX.get(var.get('type'), 'Local')}")
        elif name != outer:
            self.warn(f"{where}: {name} has the name of the global {outer} once case is ignored, and hides it in "
                      f"{visible}. There, an expression or action that names {outer} refers to {name}, which the "
                      f"editor accepts. If they are two values, rename {name} and its uses, for example "
                      f"{name}{SHADOW_SUFFIX.get(var.get('type'), 'Value')}")
