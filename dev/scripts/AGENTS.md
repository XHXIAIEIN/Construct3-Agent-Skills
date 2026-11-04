# scripts/ Directory

## Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `build_plugin.py` | Set the plugin's version, and check `plugin/` against the limits of Claude's plugin directory and for a data folder, which belongs to the Construct3-RAG clone. `--check` also compares the version with the one the build would set (`docs/decisions/plugin-folder.md`, `docs/decisions/plugin-tracks-commits.md`, `docs/decisions/plugin-reads-the-clones.md`) | `python dev/scripts/build_plugin.py` |
| `../../scripts/bootstrap.py` | Clone the sibling repositories that are missing, create the game project from the empty project when its folder does not exist, and install the skill from `plugin/` in it; it stays at the root because the README prints its path | `python scripts/bootstrap.py --project <folder>` |
| `output_diff.py` | Run the skill's tools and generators with a git ref's scripts and with the working tree's, and list the cases whose output differs. The tools that read a project run over every official example and the game projects of `--projects`; `--help` names every case. Nothing is written to the repository. Before changing a skill script, read the `dev/AGENTS.md` Rules bullet "A change to a script is compared, old against new" | `python dev/scripts/output_diff.py [REF]`; `--only print_sheet`, `--limit 20` for a quick run |
| `measure_examples.py` | Measure the official examples for a number before the template or a check takes it: the player's height, the HUD's share of the screen, popup tweens, Sine idle motion (`docs/decisions/borrowed-numbers.md`), stagger steps, eases, layout transitions, HUD fades, emoji and symbols in texts, kept icons, even rows, near-miss edges | `python dev/scripts/measure_examples.py <actors\|hud\|popups\|sine\|stagger\|eases\|transitions\|fades\|glyphs\|icons\|rows\|edges> --examples <example-projects> [--out .local/docs/evidence/<record>/<measure>.json]` |
| `measure_timing.py` | Measure a recorded effect's rise, peak, fall and tail against the four parts of `guides/recipes/vfx-timing.md` of Construct3-Cookbook, and name the kind of effect from the ratio of the rise to the fall. The plugin's `/measure-timing` row runs it; it needs ffmpeg on PATH and exits 0 without it | `python scripts/measure_timing.py VIDEO [--from SECONDS] [--csv FILE]` |

## Rules

- The data is read, never written, here. The scripts that fetch and export
  it are in Construct3-RAG (`scripts/init.py` and `docs/dev/data-pipeline.md`
  there), and the skill's scripts read the clone directly.
- The locales of the data are the `languages` of the Construct3-RAG
  clone's `data/c3-schemas/_index.json`.

## Checks

```bash
python -m compileall -q scripts
python dev/scripts/build_plugin.py --check
```
