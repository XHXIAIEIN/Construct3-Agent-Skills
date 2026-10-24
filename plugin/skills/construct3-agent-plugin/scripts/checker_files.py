"""The checks of project.c3proj, the names, the images, the layouts and the project's
files and addons. A part of check_project.Checker, which holds the state they read."""
import json
import math
import re
from collections import Counter
from pathlib import Path

import c3project as c3
from c3project import LOWER, RESOURCE_FOLDERS, closest, folder_items, script_command
from checker_common import (
    VARIABLE_TYPES, ROOT_FILE_FOLDERS, UNLISTED_ROOT_FILES, AUDIO_TYPE, GENERAL_TYPES, JSON_TYPES,
    JSON_EXAMPLES, FULL_TURN, RESERVED_WORDS, DEVICE_NAMES, PROJECT_TEXT, PROJECT_OPTIONS, PROJECT_ALSO,
    ANIMATED_PLUGINS, IMAGE_PLUGINS, BLEND_MODES, LAYER_NUMBERS, WORLD_NUMBERS, FOLDER_PROJECT_RELEASE,
    SHADOW_SUFFIX, TEXT_EDGE, TEXT_CONTRAST, SHORT_TEXT, editor_name, next_name, case_aside, BBCODE_TAG,
    SPRITE_FONT_DEFAULTS, member_types, replaced_in_own_text, first_few, effect_names, contrast_ratio,
    hex_colour, layer_instances, frames_of,
)


class FileChecks:
    # --- project.c3proj -----------------------------------------------------------------
    def check_project_file(self) -> None:
        """What the editor reads before it opens a single file of the project. A
        hand-written project.c3proj that keeps only the keys the tools read opens
        as `TypeError: expected string`, a message that names neither the key nor
        the file; the editor writes all of these into every project it saves."""
        data = self.p.data
        props = data.get("properties")
        if not isinstance(props, dict):
            self.err("project.c3proj: no \"properties\" block; copy the one from a project the editor saved, "
                     f"or from {(self.p.rag / 'data' / 'c3-new-project' / 'project.c3proj').as_posix()}")
            props = {}
        missing = [k for k in PROJECT_TEXT if not isinstance(props.get(k), str)]
        if missing:
            written = ", ".join(f'"{k}": {json.dumps(PROJECT_TEXT[k])}' for k in missing)
            self.err(f"project.c3proj properties: {', '.join(missing)} "
                     f"{'is' if len(missing) == 1 else 'are'} missing or not text; the editor reads every "
                     f"property as it opens the project and stops with \"TypeError: expected string\" before "
                     f"it names a file. Write {written}")
        for key, options in PROJECT_OPTIONS.items():
            value = props.get(key)
            if value is None:
                rest = ", ".join(options[1:])
                self.err(f"project.c3proj properties: no \"{key}\"; the editor reads it on open and stops. "
                         f"Write \"{key}\": \"{options[0]}\", or "
                         f"{rest if len(options) == 2 else 'one of ' + rest}")
            elif value not in options and value not in PROJECT_ALSO.get(key, ()):
                name, labels = self.project_property_wording(key)
                listed = ", ".join(f"{o} ({labels[o]})" if o in labels else o for o in options)
                self.err(f"project.c3proj properties: {key}{f' ({name})' if name else ''} {value!r} is not one of "
                         f"{listed}; the editor stops with \"invalid {key}\" before the project opens, so it "
                         f"cannot be changed there. Write \"{key}\": \"{options[0]}\" in project.c3proj, or "
                         f"another of these")
        for key in ("viewportWidth", "viewportHeight"):
            value = data.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 2:
                self.err(f"project.c3proj: {key} is {value!r}; the editor reads it as a number of at least 2 "
                         f"and stops with \"invalid {'viewport width' if key.endswith('Width') else 'viewport height'}\"")
        self.check_project_index()
        fmt = data.get("projectFormatVersion")
        if fmt is not None and (not isinstance(fmt, int) or fmt > 1):
            self.err(f"project.c3proj: projectFormatVersion is {fmt!r}; the editor refuses anything above 1 with "
                     f"\"project from a future version of C3\". Write \"projectFormatVersion\": 1")
        self.check_saved_with_release()

    def check_project_index(self) -> None:
        """The lists project.c3proj keeps of what the project holds. The editor
        walks each one's items and subfolders as it opens, and reads containers as
        an array before it has read a file, so a list that is missing rather than
        empty stops the open with a type and nothing else."""
        data = self.p.data
        for key in ("objectTypes", "families", "layouts", "eventSheets"):
            block = data.get(key)
            if not isinstance(block, dict):
                folder = self.p.root / key
                found = sorted(f.stem for f in folder.glob("*.json")) if folder.is_dir() else []
                self.err(f"project.c3proj: no \"{key}\"; the editor reads the list before it reads a file and "
                         f"stops with \"TypeError: expected object\". Write \"{key}\": "
                         f"{{\"items\": {json.dumps(found)}, \"subfolders\": []}}")
                continue
            for part in ("items", "subfolders"):
                if not isinstance(block.get(part), list):
                    self.err(f"project.c3proj {key}: {part} is {block.get(part)!r}; the editor walks both lists "
                             f"as it opens the project. Write \"{part}\": []")
        # The editor opens every listed timeline and flowchart; a list copied from a new
        # project without its folders stops it with "missing file path 'timelines\Timeline 1.json'".
        for key in ("timelines", "flowcharts"):
            if isinstance(data.get(key), dict):
                for name, folder in folder_items(data[key]):
                    if isinstance(name, str) and self.p.project_file(key, name, folder) is None:
                        shown = Path(key) / folder / f"{name}.json"
                        self.err(f"{key}: {name} is listed in project.c3proj but {shown.as_posix()} is missing; the "
                                 f"editor stops with \"missing file path '{shown}'\". Take \"{name}\" out of the "
                                 f"\"{key}\" items, or copy the file from the project the list came from")
        if not isinstance(data.get("containers"), list):
            self.err(f"project.c3proj: containers is {data.get('containers')!r}; the editor reads it as an array "
                     f"before it has read a file and stops with \"TypeError: expected array\". A project with no "
                     f"container writes \"containers\": []")

    def check_saved_with_release(self) -> None:
        """The release decides where the editor looks for an object type: under
        r309 it reads objectTypes\\<name in lower case>.json, the layout of a
        project from 2016, and a project without the key is read as r86."""
        release = self.p.data.get("savedWithRelease")
        if not isinstance(release, int) or isinstance(release, bool):
            self.err(f"project.c3proj: savedWithRelease is {release!r}; without the release the editor reads the "
                     f"project as r86 and looks for objectTypes\\{'coin' if 'Coin' in self.p.types else 'name'}"
                     f".json in lower case. Write \"savedWithRelease\": 49502, or the release the editor that "
                     f"saved the project shows; a release newer than the editor opening it asks the user first")
            return
        if release < FOLDER_PROJECT_RELEASE:
            # by the name the folder holds, not by Path.exists(): a Windows file
            # system answers for Coin.json when the editor asks for coin.json
            folder = self.p.root / "objectTypes"
            have = {f.name for f in folder.glob("*.json")} if folder.is_dir() else set()
            wrong = [n for n in self.p.types if f"{n.lower()}.json" not in have]
            if wrong:
                self.err(f"project.c3proj: savedWithRelease {release} is below r309, so the editor reads an object "
                         f"type from objectTypes/<name in lower case>.json; {', '.join(sorted(wrong)[:3])} "
                         f"{'has' if len(wrong) == 1 else 'have'} no such file. Write the release that saved the "
                         f"project, for example \"savedWithRelease\": 49502")

    # --- names, addon ids, families -----------------------------------------------------
    def check_name(self, where: str, what: str, name: str, is_object: bool) -> None:
        kept = editor_name(name, is_object)
        if kept != name:
            self.err(f"{where}: the editor does not keep the {what} name {name!r} as written"
                     + (f", it becomes {kept!r}" if kept else "")
                     + "; use letters, digits and underscores, starting with a letter")

    def check_addon_id(self, kind: str, addon_id: str, where: str) -> None:
        """The editor looks an addon up by its exact id, so 'sprite' or 'Tiledbg'
        fails to open even though the schema file is found case-insensitively."""
        exact = self.p.index.get(kind, {}).get(addon_id.lower(), {}).get("originalId")
        if exact and exact != addon_id:
            self.err(f"{where}: {kind[:-1]} id {addon_id!r} must be written {exact!r}; addon ids are case-sensitive")

    def reserved(self, name: str) -> str:
        """Why the editor reserves an object type's or family's name, or "" when it does not."""
        low = LOWER(name)
        if low in RESERVED_WORDS:
            return f"{low} is a reserved word"
        if low in DEVICE_NAMES:
            return f"{low} is a device name that Windows reserves"
        if low in self.p.system_expression_names:
            return f"{low} is a system expression"
        return ""

    def check_reserved(self, kind: str, name: str, used: set[str]) -> None:
        """A reserved name: the editor opens the project and renames the object, and an expression
        that names it by the old name fails."""
        if LOWER(name) == "system":
            what = "object type" if kind == "object type" else "object class"
            self.err(f"{kind} {name} has the name of the System object, compared without case; the editor stops "
                     f"with \"{what} name '{name}' already used\". Rename it, for example {name}Object")
            return
        why = self.reserved(name)
        if not why:
            return
        new = next_name(name)
        while LOWER(new) in used and not self.reserved(new):
            new = next_name(new)
        if self.reserved(new):
            self.err(f"{kind} {name}: {why}. The editor renames it to {new} when it opens the project, and {new} "
                     f"is reserved too, so the open stops with \"name is reserved\". Rename it, for example "
                     f"{name}Object")
            return
        if LOWER(name) == "self":  # in an expression the word is Self, whatever object has the name
            lost = (f"{name}.X in an expression reads as Self, and in a System action the editor stops with "
                    f"\"Invalid use of 'self'\"")
        else:
            lost = (f"an expression that names {name}, such as {name}.X, stops the open with \"Not an object: "
                    f"'{name}' is not an object name\"")
        self.err(f"{kind} {name}: {why}, so the editor renames it to {new} when it opens the project. Its "
                 f"conditions and actions follow the new name, but {lost}. A script finds no "
                 f"runtime.objects.{name}. Rename it, for example {name}Object")

    def check_names(self) -> None:
        p = self.p
        used = {LOWER(n) for n in (*p.types, *p.families, p.functions_object, "system")}
        for kind, listed in (("object type", p.types), ("family", p.families)):
            for name, t in listed.items():
                if t.get("name") != name:
                    self.err(f"{kind} {name}: the file says \"name\": {t.get('name')!r}; "
                             f"it must be the name listed in project.c3proj")
                self.check_name(f"{kind} {name}", kind, name, True)
                self.check_reserved(kind, name, used)
                self.check_addon_id("plugins", t["plugin-id"], f"{kind} {name}")
                for b in t.get("behaviorTypes", []):
                    self.check_addon_id("behaviors", b["behaviorId"], f"{kind} {name} behavior {b['name']}")
                    self.check_name(f"{kind} {name}", "behavior", b["name"], True)
                for v in t.get("instanceVariables", []):
                    self.check_name(f"{kind} {name}", "instance variable", v["name"], False)
                    if v.get("type") not in VARIABLE_TYPES:
                        self.err(f"{kind} {name}: instance variable {v['name']}: type {v.get('type')!r} is not "
                                 f"number, string or boolean; the editor's Text type is written \"string\"")
        for a in p.data.get("usedAddons", []):
            if a.get("type") in ("plugin", "behavior"):
                self.check_addon_id(a["type"] + "s", a["id"], "project.c3proj usedAddons")
                p.schema(a["type"] + "s", a["id"])  # an id by Scirra that no addon has is reported here
        for name in p.types:
            if LOWER(name) == LOWER(p.functions_object):
                self.err(f"object type {name} has the name of the built-in {p.functions_object} object, which "
                         f"project.c3proj names in \"functionsName\", compared without case. Functions are "
                         f"built in: delete "
                         f"objectTypes/{name}.json, its name in the objectTypes items and its usedAddons entry; "
                         f"an action of a function writes \"objectClass\": \"{p.functions_object}\"")
        # Object types, families and the Functions object share one namespace, without case.
        def listed(folder) -> list[str]:
            folder = folder if isinstance(folder, dict) else {}
            return [n for n in folder.get("items", []) if isinstance(n, str)] + [
                n for sub in folder.get("subfolders", []) for n in listed(sub)]
        seen: dict[str, str] = {}
        for name in listed(p.data.get("objectTypes")):
            if LOWER(name) in seen:
                self.err(f"project.c3proj lists object type {name} twice; the editor stops with \"object type "
                         f"name '{name}' already used\": list it once")
            seen[LOWER(name)] = f"object type {seen.get(LOWER(name), name)}"
        seen.setdefault(LOWER(p.functions_object), f"the {p.functions_object} object")
        for name in listed(p.data.get("families")):
            if LOWER(name) in seen:
                self.err(f"family {name} has the name of {seen[LOWER(name)]}, once case is ignored; the editor stops "
                         f"with \"object class name '{name}' already used\": rename the family")
            seen[LOWER(name)] = f"family {name}"

        for name, t in p.types.items():
            p.schema("plugins", t["plugin-id"])
            for b in t.get("behaviorTypes", []):
                p.schema("behaviors", b["behaviorId"])
        for fam, f in p.families.items():
            p.schema("plugins", f["plugin-id"])
            for b in f.get("behaviorTypes", []):
                p.schema("behaviors", b["behaviorId"])
            for m in f.get("members", []):
                if m not in p.types:
                    self.err(f"family {fam}: member {m} is not an object type")
                elif p.types[m]["plugin-id"] != f["plugin-id"]:
                    self.err(f"family {fam}: member {m} is a {p.types[m]['plugin-id']}, the family is {f['plugin-id']}")
        for c in p.data.get("containers", []):
            for m in c.get("members", []):
                if m not in p.types:
                    self.err(f"container {c.get('members')}: member {m} is not an object type")

    # --- images: {type}-{animation}-{frame:03d}.png per frame, {type}.png for single-image plugins ---
    def check_image(self, stem: str, entry: dict) -> None:
        """The image file of a frame or a single-image type. Its size is not compared with the
        entry's width and height: the editor takes the size from the file. An image imported in a
        lossy format and not edited since keeps that format, which the entry's fileType names."""
        folder = self.p.root / "images"
        file_type = entry.get("fileType") or "image/png"
        if (folder / f"{stem}.png").exists():
            return
        if file_type != "image/png" and folder.is_dir() and any(f.stem.lower() == stem for f in folder.iterdir()):
            return
        shown = f"images/{stem}.png" if file_type == "image/png" else f"images/{stem} as {file_type}"
        self.err(f"missing image {shown}: the editor reads a frame from images/<object type>-<animation>-<frame "
                 f"number, three digits>.png and a single image from images/<object type>.png, in lower case")

    def check_animations(self) -> None:
        for name, t in self.p.types.items():
            if t.get("plugin-id") in ANIMATED_PLUGINS and not isinstance(t.get("animations"), dict):
                self.err(f"object type {name}: a {t['plugin-id']} carries an animations folder and the editor "
                         f"reads it as it opens the type. Write \"animations\": {{\"items\": [{{\"name\": "
                         f"\"Default\", \"frames\": [...], \"sid\": <n>}}], \"subfolders\": []}}")
            if t.get("plugin-id") in IMAGE_PLUGINS and not isinstance(t.get("image"), dict):
                instead = " in place of its animations" if "animations" in t else ""
                self.err(f"object type {name}: a {t['plugin-id']} carries one image and the editor reads it as it "
                         f"opens the type. Write{instead} \"image\": {{\"width\": <w>, \"height\": <h>, "
                         f"\"originX\": 0.5, \"originY\": 0.5, \"originalSource\": \"\", \"exportFormat\": "
                         f"\"lossless\", \"exportQuality\": 0.8, \"imageSpriteId\": <n>, \"useCollisionPoly\": "
                         f"true}}, the size of images/{name.lower()}.png")
            if isinstance(t.get("animations"), dict):
                self.check_collision_polys(name, t["animations"])

    def check_collision_polys(self, name: str, folder: dict) -> None:
        """A frame's collision polygon is three or more x, y pairs; a frame without collisionPoly
        takes the whole image."""
        for anim in folder.get("items", []):
            for i, fr in enumerate(anim.get("frames", [])):
                poly = fr.get("collisionPoly") if isinstance(fr, dict) else None
                points = poly.get("points") if isinstance(poly, dict) else None
                if not isinstance(points, list) or (len(points) >= 6 and len(points) % 2 == 0):
                    continue
                pairs = len(points) % 2 == 0
                held = (f"{len(points) // 2} point{'' if len(points) == 2 else 's'}, {json.dumps(points)}" if pairs
                        else f"{len(points)} numbers, {json.dumps(points)}, which are not x, y pairs")
                said = ("must have at least three points in a collision poly" if pairs
                        else "must have an even number of elements in collision poly points array")
                self.err(f"object type {name} animation {anim.get('name')} frame {i}: collisionPoly holds {held}; "
                         f"the editor opens the project, then stops the preview with \"assertion "
                         f"failure: {said}\". Write three or more x, y pairs from 0 to 1 across the image, or leave "
                         f"collisionPoly out for the whole image")
        for sub in folder.get("subfolders", []):
            self.check_collision_polys(name, sub)

    def check_images(self) -> None:
        sprite_ids: dict[int, list[str]] = {}  # imageSpriteId -> each image or frame that has it
        files = self.p.listed_files("objectTypes")
        for name, t in self.p.types.items():
            shown = (f"{name} ({files[name].relative_to(self.p.root).as_posix()})" if files.get(name)
                     else name)
            if isinstance(t.get("image"), dict):
                self.check_image(name.lower(), t["image"])
                sprite_ids.setdefault(t["image"].get("imageSpriteId"), []).append(f"the image of {shown}")
            for stem, fr in frames_of(t.get("animations", {}), f"{name.lower()}-"):
                self.check_image(stem, fr)
                if isinstance(fr, dict):
                    sprite_ids.setdefault(fr.get("imageSpriteId"), []).append(f"the frame images/{stem}.png of {shown}")
        self.check_sprite_ids(sprite_ids)

    def check_sprite_ids(self, sprite_ids: dict) -> None:
        """Report an imageSpriteId that two images or frames share.
        The editor keeps one set of these ids for the project and stops on a repeated one.
        -1 is skipped, because the editor's loader gives it a new id."""
        taken = {s for s in sprite_ids if isinstance(s, int)}
        for s, owners in sprite_ids.items():
            if not isinstance(s, int) or s < 0 or len(owners) < 2:
                continue
            free = []
            n = s
            while len(free) < len(owners) - 1:
                # seven digits, as the editor and the generator write them
                n = n + 1 if n + 1 < 10**7 else 10**6
                if n not in taken:
                    free.append(n)
                    taken.add(n)
            self.err(f"{' and '.join(owners)} share the imageSpriteId {s}, and the editor stops with \"id already "
                     f"in use\" before the project opens. Keep {s} on one of them. Give "
                     + ("the other" if len(owners) == 2 else "each other one")
                     + " an imageSpriteId that no image or frame of the project has, for example "
                     + ", ".join(str(n) for n in free))

    # --- layouts ----------------------------------------------------------------------------
    def collect_sids(self, obj, in_ace: bool = False) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "sid" and isinstance(v, int):
                    (self.ace_sids if in_ace else self.sids).append(v)
                # instanceFolderItem and scene-graphs-folder-root are editor references that repeat an instance's sid
                if k not in ("instanceFolderItem", "scene-graphs-folder-root"):
                    self.collect_sids(v, in_ace or k in ("conditions", "actions"))
        elif isinstance(obj, list):
            for v in obj:
                self.collect_sids(v, in_ace)

    def check_properties(self, where: str, props: dict, schema_props: dict | None) -> None:
        """A property the schema does not list is a warning: older projects keep
        keys the editor has since renamed (z-height), and the editor drops them."""
        if schema_props is None:
            return
        for k, v in props.items():
            if k not in schema_props:
                self.warn(f"{where}: property {k} is not in the current schema")
                continue
            items = (schema_props[k] or {}).get("items")
            if items and v not in items:
                self.err(f"{where}: {k}={v!r} is not one of {list(items)}")

    def check_effects(self, effect_types: list) -> None:
        """Only whether the effect has a schema; an unknown one is warned about once."""
        for e in effect_types:
            self.p.schema("effects", e.get("effectId", e.get("id", "")))

    def check_instance(self, where: str, inst: dict) -> None:
        p = self.p
        t = inst.get("type")
        if not isinstance(inst.get("uid"), int):
            self.err(f"{where}: instance of {t} has no integer uid")
        else:
            self.uids.append(inst["uid"])
        self.templates.add(t)
        if t not in p.types:
            self.err(f"{where}: instance of unknown type {t}{closest(t or '', p.types)}")
            return
        ivars = p.ivars_of(t)
        ivar_types = p.ivar_types_of(t)
        for iv, value in inst.get("instanceVariables", {}).items():
            if iv not in ivars:
                self.err(f"{where}: {t} has no instance variable {iv}")
            elif ivar_types[iv] in JSON_TYPES and not JSON_TYPES[ivar_types[iv]](value):
                self.err(f"{where}: {t} instance variable {iv} = {value!r}; a {ivar_types[iv]} is written as "
                         f"{JSON_EXAMPLES[ivar_types[iv]]} here, a JSON value, not text")
        angle = inst.get("world", {}).get("angle", 0)
        if isinstance(angle, (int, float)) and abs(angle) > FULL_TURN:
            self.err(f"{where}: {t} world angle {angle} is more than a full turn; the file stores radians, "
                     f"{angle} degrees is {math.radians(angle):.4f}")
        for iv in ivars - set(inst.get("instanceVariables", {})):
            self.err(f"{where}: {t} instance has no value for instance variable {iv}")
        behs = p.behaviors_of(t)
        for b in inst.get("behaviors", {}):
            if b not in behs:
                self.err(f"{where}: {t} has no behavior {b}")
        for b in set(behs) - set(inst.get("behaviors", {})):
            self.err(f"{where}: {t} instance has no properties block for behavior {b}")
        plugin = p.schema("plugins", p.plugin_of[t])
        self.check_properties(f"{where}: {t}", inst.get("properties", {}), plugin.get("properties") if plugin else None)
        for b, block in inst.get("behaviors", {}).items():
            if b in behs and not (isinstance(block, dict) and isinstance(block.get("properties"), dict)):
                bs = p.schema("behaviors", behs[b])
                ids = list((bs or {}).get("properties") or {})
                values = ", ".join(f'"{k}": true' if k == "enabled" else f'"{k}": ...' for k in ids)
                self.err(f"{where}: {t} instance behavior {b} is {json.dumps(block)}, with no \"properties\" "
                         f"block; the editor reads it as it opens the layout. Write \"{b}\": {{\"properties\": "
                         f"{{{values}}}}}")
                continue
            if b in behs:
                bs = p.schema("behaviors", behs[b])
                self.check_properties(f"{where}: {t}.{b}", block.get("properties", {}),
                                      bs.get("properties") if bs else None)
                if behs[b].lower() == "pathfinding" and block.get("properties", {}).get("obstacles", "solids") == "solids":
                    self.solid_obstacles = True
        if p.plugin_of[t].lower() == "spritefont2":
            self.check_sprite_font_instance(where, t, inst.get("properties", {}))
        anims = p.animations_of(t)
        initial = inst.get("properties", {}).get("initial-animation")
        if anims is not None and initial is not None and LOWER(initial) not in anims:
            self.err(f"{where}: {t} has no animation {initial!r} for initial-animation")

    def check_sprite_font_instance(self, where: str, t: str, props: dict) -> None:
        """Records the characters this instance draws, for the type's Set text actions, and checks its own text
        without the parts a Set text replaces. A property the instance leaves out is read as the editor fills it."""
        missing = [k for k in SPRITE_FONT_DEFAULTS if k not in props]
        if missing:
            self.warn(f"{where}: {t} instance has no {', '.join(missing)}; the editor fills "
                      + ", ".join(f"{k} {json.dumps(SPRITE_FONT_DEFAULTS[k], ensure_ascii=False)}" for k in missing)
                      + ", which fit the font image the editor draws for a new Sprite Font. Write what this font "
                        "image has: character-set, the characters in the order its cells draw them, left to right "
                        "and top to bottom; character-width and character-height, one cell in pixels")
        charset = props.get("character-set", SPRITE_FONT_DEFAULTS["character-set"])
        if not isinstance(charset, str):
            return
        bbcode = props.get("enable-bbcode", False) is not False
        chars, any_bbcode = self.font_sets.get(t, (set(), False))
        self.font_sets[t] = (chars | set(charset), any_bbcode or bbcode)
        text = props.get("text")
        if isinstance(text, str):
            for part in self.font_templates.get(t, ()):
                text = text.replace(part, "")
            self.check_sprite_font_text(f"{where}: {t} text", t, text, set(charset), bbcode)

    def check_sprite_font_text(self, where: str, t: str, text: str, charset: set[str], bbcode: bool) -> None:
        shown = BBCODE_TAG.sub("", text).replace("\\[", "[") if bbcode else text
        missing = list(dict.fromkeys(c for c in shown if not c.isspace() and c not in charset))
        if missing:
            self.warn(f"{where}: {', '.join(map(repr, missing))} {'is' if len(missing) == 1 else 'are'} not in "
                      f"the Character set of "
                      f"the Sprite Font {t}, which draws {'it' if len(missing) == 1 else 'each'} as an empty space "
                      f"(manual: plugin-reference/sprite-font.md); add {'it' if len(missing) == 1 else 'them'} to "
                      f"the Character set and the font image, or show the text with a Text object")

    def check_number(self, where: str, what: str, value, least: float | None = None) -> bool:
        """A value the editor reads through its finite-number assertion. Text in
        place of a number stops the open with the assertion and nothing else."""
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            self.err(f"{where}: {what} is {value!r}; the editor reads it as a number and stops with "
                     f'"TypeError: expected finite number"')
            return False
        if least is not None and value < least:
            self.err(f"{where}: {what} is {value}; the editor refuses anything below {least}")
            return False
        return True

    def walk_layers(self, where: str, layer_list: list) -> None:
        for layer in layer_list:
            name = layer.get("name")
            here = f"{where} layer {name}"
            if not (isinstance(name, str) and name):
                self.err(f"{where}: a layer is named {name!r}; the editor reads a layer name as text and "
                         f'stops with "TypeError: expected string"')
            else:
                self.layers.add(name)
                self.layer_effects.setdefault(name, set()).update(effect_names(layer))
            for what in LAYER_NUMBERS:
                self.check_number(here, what, layer.get(what))
            if layer.get("blendMode") not in BLEND_MODES:
                self.err(f"{here}: blendMode is {layer.get('blendMode')!r}; the editor stops with "
                         f'"invalid blend mode". Write "blendMode": "normal", or one of '
                         f"{', '.join(BLEND_MODES[1:])}")
            if not isinstance(layer.get("instances"), list):
                self.err(f"{here}: instances is {layer.get('instances')!r}; the editor walks the list as it "
                         f'opens the layer. A layer with nothing on it writes "instances": []')
            self.check_effects(layer.get("effectTypes", []))
            for inst in layer.get("instances", []) if isinstance(layer.get("instances"), list) else []:
                self.world_types.add(inst.get("type"))
                self.check_world(here, inst)
                self.check_instance(here, inst)
            self.walk_layers(where, layer.get("subLayers", []))

    def check_world(self, where: str, inst: dict) -> None:
        """Where and how big an instance is on the layer. The editor reads the
        block before it reads the instance's own properties."""
        world = inst.get("world")
        if not isinstance(world, dict):
            self.err(f"{where}: {inst.get('type')} has no world block; an instance on a layer carries "
                     f'"world": {{"x": 0, "y": 0, "width": 32, "height": 32, "originX": 0.5, "originY": 0.5}}')
            return
        for what in WORLD_NUMBERS:
            self.check_number(f"{where}: {inst.get('type')}", f"world.{what}", world.get(what))

    def check_layouts(self) -> None:
        p = self.p
        self.layouts = p.load_listed("layouts")
        self.sheets = {**p.load_listed("eventSheets"), **self.unsaved}
        self.font_templates = replaced_in_own_text(self.sheets, p.families)
        for lname, lay in self.layouts.items():
            self.collect_sids(lay)
            if not (isinstance(lay.get("name"), str) and lay["name"]):
                self.err(f"layout {lname}: the file says \"name\": {lay.get('name')!r}; the editor reads it "
                         f"as text and stops with \"TypeError: expected string\"")
            for what in ("width", "height"):
                self.check_number(f"layout {lname}", what, lay.get(what), 2)
            if not isinstance(lay.get("layers"), list):
                self.err(f"layout {lname}: layers is {lay.get('layers')!r}; the editor walks the list as it "
                         f"opens the layout, before it reads anything on it")
                continue
            self.walk_layers(f"layout {lname}", lay["layers"])
            self.check_default_controls(lname, lay["layers"])
            self.check_screen_text(lname, lay)
            for inst in lay.get("nonworld-instances", []):
                self.check_instance(f"layout {lname}", inst)
            self.check_effects(lay.get("effectTypes", []))
            self.layout_effects |= effect_names(lay)
            if lay.get("eventSheet") and lay["eventSheet"] not in self.sheets:
                self.err(f"layout {lname}: event sheet {lay['eventSheet']} does not exist")

        single_globals: dict[str, list[str]] = {}  # plugin id -> its single-global object types
        for name, t in p.types.items():
            if "singleglobal-inst" in t:
                single_globals.setdefault(t.get("plugin-id"), []).append(name)
                self.uids.append(t["singleglobal-inst"]["uid"])
                plugin = p.schema("plugins", t["plugin-id"])
                self.check_properties(f"{name}", t["singleglobal-inst"].get("properties", {}),
                                      plugin.get("properties") if plugin else None)
            self.check_effects(t.get("effectTypes", []))
            self.collect_sids(t)
            self.class_sids.setdefault(t.get("sid"), []).append(name)
        # The editor's dialog refuses a second one: "can only be added to a project once"
        for plugin_id, names in single_globals.items():
            if len(names) > 1:
                tables = (". One Advanced Random holds every probability table by the name *Create probability "
                          "table* gives it, and *Set probability table* picks the one to draw from"
                          if plugin_id == "AdvancedRandom" else "")
                self.err(f"object types {', '.join(names)} are all {plugin_id}, and the editor lets a project add "
                         f"{plugin_id} once: keep one of them and point the events of the others at it{tables}")
        for fname, f in p.families.items():
            self.collect_sids(f)
            self.class_sids.setdefault(f.get("sid"), []).append(f"family {fname}")
        self.collect_sids(p.data.get("rootFileFolders", {}))

    def check_default_controls(self, lname: str, layers: list) -> None:
        """Default controls is a property of each instance of a movement behavior, and every instance with it
        on moves with the arrow keys. An instance without the property reads as on, as the editor fills it.
        Instances of two or more object types with it on in one layout walk together: a crate given Platform
        to be pushed walks with the player. One type steered on purpose, two knights that move as one, passes."""
        steered: dict[str, tuple[int, list[str]]] = {}  # type -> (instances, behavior names)
        for inst in layer_instances(layers):
            t = inst.get("type")
            behs = self.p.behaviors_of(t) if t in self.p.types else {}
            names = []
            for b, block in (inst.get("behaviors") or {}).items():
                schema = self.p.schema("behaviors", behs[b]) if b in behs else None
                props = block.get("properties") if isinstance(block, dict) else None
                if (schema and "default-controls" in (schema.get("properties") or {}) and isinstance(props, dict)
                        and props.get("default-controls", True) is not False):
                    names.append(b)
            if names:
                n, known = steered.get(t, (0, []))
                steered[t] = (n + 1, known + [b for b in names if b not in known])
        if len(steered) < 2:
            return
        listed = "; ".join(f"{t} ({n} instance{'s' if n > 1 else ''}, {', '.join(bs)})"
                           for t, (n, bs) in steered.items())
        self.warn(f"layout {lname}: {listed} have Default controls on, so all of them move with the arrow keys "
                  f"together. Keep it on for the object the player steers. In every layout, give each instance "
                  f"of the others \"default-controls\": false in its behavior's properties, and move it with "
                  f"Simulate control or the behavior's actions (manual: behavior-reference/platform.md "
                  f"\"Default controls\")")

    def check_screen_text(self, lname: str, lay: dict) -> None:
        """Warnings on the texts a layout shows as it starts: one whose aligned side touches the screen's edge,
        one that reads under TEXT_CONTRAST:1 against the layer colour behind it, and a short text that is all
        the screen shows drawn under the template's banner size. A text behind which another object, an effect
        or a global layer may lie is left out of the contrast, since what shows there is not known here."""
        data = self.p.data
        vw, vh = data.get("viewportWidth"), data.get("viewportHeight")
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 for v in (vw, vh)):
            return
        unit = 8 if vh <= 360 else 32  # the template's UNIT and MARGIN; its title is 2 UNIT pt
        if self.global_layers is None:
            self.global_layers = {layer.get("name") for other in self.layouts.values() if isinstance(other, dict)
                                  for layer, _ in c3.layers_of(other.get("layers") or []) if layer.get("global")}
        viewport_sized = (lay.get("width"), lay.get("height")) == (vw, vh)
        backdrop = None  # (layer name, colour) of the nearest opaque layer below
        unknown = False  # an effect or a global layer at or below: what shows behind is not known
        behind: list[tuple] = []  # boxes of the other objects drawn so far
        texts: list[tuple] = []  # (place, type, text, size, in the middle of the screen) of each text shown
        other_shown = False
        for layer, _ in c3.layers_of(lay["layers"]):
            if not isinstance(layer, dict):
                continue
            if layer.get("isTransparent") is False and isinstance(layer.get("backgroundColor"), list):
                backdrop, behind = (layer.get("name"), layer["backgroundColor"]), []
            unknown = unknown or bool(layer.get("effectTypes")) or layer.get("name") in self.global_layers
            hud = layer.get("parallaxX") == 0 and layer.get("parallaxY") == 0
            here = f"layout {lname} layer {layer.get('name')}"
            for inst in layer.get("instances") or []:
                world, props = inst.get("world"), inst.get("properties") or {}
                if not isinstance(world, dict) or not all(isinstance(world.get(k), (int, float))
                                                          for k in ("x", "y", "width", "height")):
                    continue
                t = self.p.types.get(inst.get("type")) or {}
                shown = props.get("initially-visible", True) is not False
                sprite_font = t.get("plugin-id") == "Spritefont2"
                if t.get("plugin-id") != "Text" and not sprite_font:
                    if shown:
                        other_shown = True
                        behind.append(c3.box(world))
                    continue
                if not shown or world.get("angle"):
                    continue
                text = props.get("text") if isinstance(props.get("text"), str) else ""
                box = c3.box(world)
                # A Text's size in pt; a Sprite Font's in px, its cell's height times its scale
                size = (props.get("character-height", 0) * props.get("scale", 1) if sprite_font
                        else props.get("size", 12))
                if text.strip() and isinstance(size, (int, float)):
                    # in the middle of the screen, not a HUD line held to an edge
                    middle = (hud or viewport_sized) and vh / 3 <= (box[1] + box[3]) / 2 <= 2 * vh / 3
                    texts.append((here, inst.get("type"), text, size, middle, sprite_font))
                name = f"{inst.get('type')} {text[:20]!r}" if text.strip() else str(inst.get("type"))
                if hud or viewport_sized:
                    self.text_at_edge(here, name, world, props, vw, vh, unit)
                # A Sprite Font's colour is its instance's tint, the text's own only over white glyphs
                colour = (world.get("color") if self.white_glyphs(inst.get("type")) else None) if sprite_font \
                    else props.get("color")
                covered = any(b[0] < box[2] and b[2] > box[0] and b[1] < box[3] and b[3] > box[1] for b in behind)
                if (text.strip() and not unknown and not covered and not inst.get("effects") and not t.get("effectTypes")
                        and not re.search(r"\[(outline|color)=", text) and isinstance(colour, list) and len(colour) >= 3):
                    self.text_on_backdrop(here, name, colour, backdrop)
        if other_shown or not 1 <= len(texts) <= 2 or any(len(t[2]) > SHORT_TEXT or "\n" in t[2] for t in texts):
            return
        here, otype, text, size, middle, sprite_font = max(texts, key=lambda t: t[3])
        if middle and size < 2 * unit:
            drawn = f"at {size:g} px" if sprite_font else f"at {size:g} pt it draws about {round(size * 4 / 3)} px high"
            fix = (f"Set its \"scale\" so that it draws {2 * unit} px high or more" if sprite_font
                   else f"Set its \"size\" to {2 * unit} or more")
            self.warn(f"{here}: {otype} {text!r} stands in the middle of a screen that shows nothing but "
                      f"{'two short texts' if len(texts) > 1 else 'this text'}, so it is what the screen is about, "
                      f"and {drawn} on a {vh:g} px high viewport. {fix}, the template's banner size "
                      f"(TEXT_SIZE[\"display\"]), and fit its box to it")

    def white_glyphs(self, otype: str) -> bool:
        """Whether the image of the Sprite Font type `otype` draws every glyph in white, as
        bake_font.py does, so that the instance's colour is the colour of its text."""
        if otype not in self.glyph_white:
            img = c3.png_rgba(path.read_bytes()) if (path := self.p.root / "images" / f"{otype.lower()}.png").is_file() \
                else None
            self.glyph_white[otype] = img is not None and all(px[:3] == (255, 255, 255)
                                                              for px in img[2] if px[3])
        return self.glyph_white[otype]

    def text_at_edge(self, here: str, name: str, world: dict, props: dict, vw: float, vh: float, unit: int) -> None:
        """A text on the screen whose aligned side lies at or past the screen's edge: its first or last letter
        touches the edge, and a phone's rounded corner cuts it."""
        left, top, right, bottom = c3.box(world)
        # edge -> (axis, distance from that edge, direction away from it), for the sides the text is aligned to
        edges = {"left": ("x", left, 1), "right": ("x", vw - right, -1),
                 "top": ("y", top, 1), "bottom": ("y", vh - bottom, -1)}
        for edge in (props.get("horizontal-alignment", "left"), props.get("vertical-alignment", "top")):
            if edge not in edges:
                continue
            axis, gap, sign = edges[edge]
            span = right - left if axis == "x" else bottom - top
            if -span < gap < TEXT_EDGE:
                self.warn(f"{here}: {name} is {edge}-aligned {gap:g} px from the {edge} edge of the screen, so its "
                          f"text touches the edge. Set world.{axis} to {world[axis] + sign * (unit - gap):g}, "
                          f"{unit} px in, the template's MARGIN")

    def text_on_backdrop(self, here: str, name: str, colour: list, backdrop: tuple | None) -> None:
        """A text that reads under TEXT_CONTRAST:1 against the colour of the opaque layer behind it, or against
        black when every layer at or below it is transparent."""
        under = backdrop[1] if backdrop else [0, 0, 0]
        if not all(isinstance(v, (int, float)) for v in [*colour[:3], *under[:3]]):
            return
        ratio = contrast_ratio(colour, under)
        if ratio >= TEXT_CONTRAST:
            return
        best = max(([0, 0, 0], [1, 1, 1]), key=lambda c: contrast_ratio(c, under))
        behind = (f"the background colour of layer {backdrop[0]}, {hex_colour(under)}" if backdrop else "black")
        why = ("" if backdrop else " Every layer at or below it is transparent, and a layout has no background "
                                   "colour of its own, so the screen behind it is black.")
        self.warn(f"{here}: {name} is {hex_colour(colour)} on {behind}, {ratio:.1f}:1, and text needs "
                  f"{TEXT_CONTRAST}:1 to read (WCAG 2.2, 1.4.3).{why} "
                  + ("Set its color to one that contrasts, such as " + json.dumps(best) if backdrop else
                     "Make the bottom layer opaque, \"isTransparent\": false, with a \"backgroundColor\" the text "
                     f"reads on, or set the text's color to one that reads on black, such as {json.dumps(best)}"))

    def check_namespace(self, obj: str) -> None:
        """`Enemy.Angle` has to mean one thing, so the editor refuses an instance
        variable, behavior or effect named like another one on the object or its
        families, or like an expression of the plugin. Names compare without case:
        instance variables hp and HP of Thing stopped the r495.2 and r504 editors with
        "name 'HP' already in object class 'Thing' namespace", and a family's hp beside
        a member's HP with the family named."""
        p = self.p
        declared: dict[str, tuple[str, str]] = {}  # lower name -> (label, name)
        for owner in [obj] + p.families_of(obj):
            d = p.types.get(owner) or p.families.get(owner) or {}
            entries = ([("instance variable", v["name"], v.get("type")) for v in d.get("instanceVariables", [])]
                       + [("behavior", b["name"], None) for b in d.get("behaviorTypes", [])]
                       + [("effect", e["name"], None) for e in d.get("effectTypes", []) if "name" in e])
            for what, name, vtype in entries:
                label = f"{what} {name}" + (f" of family {owner}" if owner != obj else "")
                if LOWER(name) in declared:
                    other, first = declared[LOWER(name)]
                    rename = f", for example {name}{SHADOW_SUFFIX.get(vtype, 'Value')}" if vtype else ""
                    self.err(f"{obj}: {label} has the same name as {other}{case_aside(name, first)}; the editor "
                             f"stops with \"name '{name}' already in object class '{owner}' namespace\" before the "
                             f"project opens. Rename {name}{rename}")
                declared[LOWER(name)] = (label, name)
        plugin = p.schema("plugins", p.plugin_of[obj])
        expressions = p.expressions_of(plugin)
        # commonAces give the shared ones, Z on a Sprite no layout holds, none on an Array
        if plugin is not None or any(m in self.world_types for m in member_types(p.families, obj)):
            expressions |= p.common_expressions_of(plugin)
        for key, (label, _) in declared.items():
            if key in expressions and " of family " not in label:
                self.err(f"{obj}: {label} collides with the expression {obj}.{key}; rename it")

    # --- uniqueness, project files, addons ----------------------------------------------------
    def check_uniqueness(self) -> None:
        def repeated(values: list[int]) -> set[int]:
            return {v for v, n in Counter(values).items() if n > 1}

        # Only an object class sid stops the editor
        shared = {s: names for s, names in self.class_sids.items() if len(names) > 1}
        for s, names in sorted(shared.items()):
            self.err(f"{' and '.join(names)} share the sid {s}; the editor stops with \"object class sid "
                     f"already in use\": give all but one a new 15-digit sid no other entry of the project has")
        dup_sids = sorted((repeated(self.sids) | (set(self.sids) & set(self.ace_sids))) - set(shared))
        if dup_sids:
            self.warn(f"duplicate sids: {dup_sids[:5]}{' ...' if len(dup_sids) > 5 else ''}; the editor opens the "
                      f"project; to make them unique, search the project's JSON for each sid and give all but one "
                      f"entry a new 15-digit sid")
        dup_ace_sids = sorted(repeated(self.ace_sids))
        if dup_ace_sids:
            self.warn(f"conditions or actions sharing a sid (pasted in the editor?): "
                      f"{dup_ace_sids[:5]}{' ...' if len(dup_ace_sids) > 5 else ''}")
        # The editor renumbers all but one of the instances that share a uid
        # list.count, not Counter: a single-global object's uid is not checked as an integer, so it may be unhashable
        dup_uids = sorted({u for u in self.uids if self.uids.count(u) > 1})
        if dup_uids:
            self.err(f"duplicate uids: {dup_uids[:5]}{' ...' if len(dup_uids) > 5 else ''}; the editor gives all "
                     f"but one of them another uid, so a hierarchy link or a Pick by UID written for one may reach "
                     f"the other: give the copies a uid no instance or single-global object type has")

    def check_secrets(self) -> None:
        """A string shaped like a key in what a web export ships, which every player can read."""
        for s, what, shown in c3.secrets_in(c3.shipped_strings(self.p.root, self.p.data, self.sheets)):
            self.warn(f"{s.place}: a string shaped like {what} ({shown}), and a web export ships every string to "
                      f"the players, who can read it. Move the key to a server that the game calls. If it is meant "
                      f"to be public, write {c3.ALLOW} in {s.mark}")

    def check_files_and_addons(self) -> None:
        p = self.p
        root_files = p.data.get("rootFileFolders", {})
        # The editor opens every listed file and stops with "missing file path 'icons\icon-16.png'".
        for kind, directory in ROOT_FILE_FOLDERS.items():
            for name, folder in folder_items(root_files.get(kind, {})):
                fname = name["name"] if isinstance(name, dict) else name
                if not (p.root / directory / folder / fname).exists():
                    shown = (Path(directory) / folder / fname).as_posix()
                    self.err(f"{kind} file {fname} is listed in project.c3proj but {shown} is missing; the editor "
                             f"stops with \"missing file path\". Add the file, or take it out of rootFileFolders")
                if kind in ("sound", "music") and not LOWER(fname).endswith(".webm"):
                    stem = Path(fname).stem
                    self.warn(f"{kind} file {fname} is not WebM Opus (.webm), the format a project's sound and music "
                              f"are in; the editor opens it, and whether it plays depends on the browser. Encode it, "
                              f"ffmpeg -i {fname} -c:a libopus {stem}.webm, and list {stem}.webm with \"type\": "
                              f"\"{AUDIO_TYPE}\", or import the file in the editor, which converts it")
        for item, _folder in folder_items(root_files.get("general", {})):
            known = GENERAL_TYPES.get(LOWER(Path(item["name"]).suffix)) if isinstance(item, dict) else None
            if known and item.get("type") not in known:
                self.warn(f"general file {item['name']} is listed with type \"{item.get('type')}\"; the editor "
                          f"wrote \"{known[0]}\" for {Path(item['name']).suffix} in the official examples. It opens "
                          f"the project; to match, set \"type\" to \"{known[0]}\"")
        self.check_scripts(root_files.get("script", {}))
        self.check_ts_defs()
        self.check_unlisted(root_files)

        addon_ids = {a["id"] for a in p.data.get("usedAddons", [])}

        def need_addon(addon_id: str, where: str) -> None:
            if addon_id not in addon_ids:
                self.err(f"{where}: {addon_id} is not listed in usedAddons")

        for name, t in p.types.items():
            need_addon(t["plugin-id"], f"object type {name}")
            for b in t.get("behaviorTypes", []):
                need_addon(b["behaviorId"], f"object type {name}")
            for e in t.get("effectTypes", []):
                need_addon(e.get("effectId", e.get("id", "")), f"object type {name}")
        for name, f in p.families.items():
            for b in f.get("behaviorTypes", []):
                need_addon(b["behaviorId"], f"family {name}")
            for e in f.get("effectTypes", []):
                need_addon(e.get("effectId", e.get("id", "")), f"family {name}")

    def check_scripts(self, scripts: dict) -> None:
        """A script listed as both .ts and .js: Construct runs the .js and ignores the .ts."""
        kinds: dict[str, set[str]] = {}
        shown: dict[str, str] = {}
        for name, folder in folder_items(scripts):
            fname = name["name"] if isinstance(name, dict) else name
            if not isinstance(fname, str):
                continue
            path = (folder / fname).with_suffix("").as_posix()
            kinds.setdefault(LOWER(path), set()).add(LOWER(Path(fname).suffix))
            shown.setdefault(LOWER(path), path)
        for key, suffixes in sorted(kinds.items()):
            if {".ts", ".js"} <= suffixes:
                self.warn(f"scripts/{shown[key]}.ts and scripts/{shown[key]}.js are both listed; Construct runs the "
                          f".js and ignores the .ts, so an edit to the .ts changes nothing. List the .ts alone when "
                          f"Construct compiles the TypeScript, the .js alone when an external editor does")

    def check_ts_defs(self) -> None:
        """scripts/ts-defs/instanceTypes.d.ts, which the editor writes when the user sets up or
        updates TypeScript definitions, without an object type or family the project has now:
        TypeScript checked against it does not know InstanceType.<name>."""
        p = self.p
        defs = p.root / "scripts" / "ts-defs" / "instanceTypes.d.ts"
        if not defs.is_file():
            return
        declared = set(re.findall(r"\w+", defs.read_text(encoding="utf-8", errors="replace")))
        missing = sorted(n for n in (*p.types, *p.families) if n not in declared)
        if missing:
            shown = first_few(missing, 5)
            self.warn(f"scripts/ts-defs/instanceTypes.d.ts does not declare {shown}, so TypeScript checked against "
                      f"it does not know InstanceType.{missing[0]}. Have the editor write them again: "
                      f"{script_command(p.root, 'open_in_editor.py', ' --typescript')}")

    def check_unlisted(self, root_files: dict) -> None:
        """A file in a folder of the project that project.c3proj does not list: the editor
        reads only what the project lists and ignores the rest."""
        p = self.p
        for kind in RESOURCE_FOLDERS:
            folder = p.root / kind
            if not folder.is_dir():
                continue
            listed = {LOWER(n) for n, _ in folder_items(p.data.get(kind) or {}) if isinstance(n, str)}
            for f in sorted(folder.rglob("*.json")):
                rel = f.relative_to(folder)
                if f.name.endswith(".uistate.json") or "uistate" in rel.parts[:-1] or LOWER(f.stem) in listed:
                    continue
                self.warn(f"{kind}/{rel.as_posix()} is not listed in project.c3proj, so the editor ignores it: if "
                          f"the project uses it, add \"{f.stem}\" to the \"{kind}\" items")
        for kind in UNLISTED_ROOT_FILES:
            directory = ROOT_FILE_FOLDERS[kind]
            folder = p.root / directory
            if not folder.is_dir():
                continue
            listed = {LOWER((sub / (n["name"] if isinstance(n, dict) else n)).as_posix())
                      for n, sub in folder_items(root_files.get(kind) or {})
                      if isinstance(n, str) or isinstance(n, dict) and isinstance(n.get("name"), str)}
            for f in sorted(folder.rglob("*")):
                rel = f.relative_to(folder)
                if f.is_file() and not f.name.endswith(".uistate.json") and LOWER(rel.as_posix()) not in listed:
                    self.warn(f"{directory}/{rel.as_posix()} is not listed in project.c3proj, so the editor ignores "
                              f"it: if the project uses it, import it in the editor, or add an entry for "
                              f"\"{f.name}\" to the rootFileFolders \"{kind}\" items, written like the entries the "
                              f"editor saved there")
