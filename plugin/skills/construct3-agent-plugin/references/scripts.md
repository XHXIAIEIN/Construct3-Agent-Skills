# The other scripts and assets

`SKILL.md` lists the scripts every change uses. These are the ones a task
needs only now and then. Each prints its options and examples with `--help`.

| Script | Use |
|--------|-----|
| `scripts/check_design.py DESIGN.json` | A new game's design before any project file: refuses a gap by its path, then plays its acceptance tests on the rules as a prototype, without the editor |
| `scripts/play_design.py DESIGN.json` | The same tests played in the editor on the game built from the design, then the first screen against the prototype; each failure names the test, the step and the rules to compare |
| `scripts/review_look.py` | Preview the project, visit every layout and print a screenshot of each, the faults the runtime shows on it, and fixed yes/no questions to answer from the screenshots |
| `scripts/bake_font.py [--add TEXT] [--replace] [--check]` | The characters a pixel-art game shows, baked from the pixel font of the user's font cache into the images of its Sprite Fonts: appended by default, `--add` for words that events build at runtime, `--replace` to drop what is no longer in use, `--check` to list what is in use and not baked |
| `scripts/check_look.py` | The strict rules of `assets/look-manifest.json` on a project built from `assets/build_project.py`, after the generator's check ends with `ok:` |
| `scripts/check_sounds.py` | Sounds measured against `tools/sounds.json` |
| `scripts/make_sounds.py` | Placeholder sounds for `tools/sounds.json` |
| `scripts/screenshot_sheet.py [SHEET] [--group TITLE]` | A picture of an event sheet or one group of it as the editor shows it, for a forum post, a bug report or a doc |
| `scripts/measure_timing.py VIDEO [--from SECONDS] [--csv FILE]` | The rise, peak, fall and tail of an effect in a recording at 60 fps of game time ([editor-and-preview.md](editor-and-preview.md), "Recording an effect's frames"), in frames, and the kind its rise to fall ratio names, beside the counts of `guides/recipes/vfx-timing.md` in Construct3-Cookbook; needs ffmpeg |
| `scripts/advanced_random.py SEED` | The numbers an Advanced Random object gives after *Update seed* SEED, computed offline as the plugin does |
| `scripts/export_project.py` | Export the project to Web (HTML5) in the editor into `--to`; a string shaped like a key stops it first. The editor exports for a subscribed account the user logs in to: read `references/export-project.md` before the first export, when the script stops, or before `--attach` |
| `scripts/pack_project.py` | Save the project as a .c3p or .zip, or a .c3p or .zip as a project folder, with project.c3proj at the archive's root as the editor needs it; a project handed over as a file is packed with it, only after the checker passed its files as they are, and `--open` opens the result once in the editor |
| `scripts/prepare_art.py` | The art from the image tool of this session: `--list` prints the next step toward the pictures the generator's `art()` asks for; without it, each picture saved in `art/raw/` is cut out and fitted to its box. Needs Pillow |
| `scripts/new_project.py FOLDER` | A new game project in an empty FOLDER, copied from the empty project the editor saves for Project > New; for a game that has no project yet |
| `scripts/install.py` | Install this skill in a game project, or refresh a copy, the Construct 3 block of the project's `AGENTS.md` and the helpers of its `tools/build_project.py` from the clone |
| `assets/build_project.py` | Template of a generator, copied to the project's `tools/` and rewritten for the game above and below its helpers, which stay the skill's between two markers |
| `assets/runtime-probe.js` | Evaluated in a running preview by a script of the agent's, reads the game's state. Read `references/reading-the-runtime.md` before checking what an event did in the preview |
