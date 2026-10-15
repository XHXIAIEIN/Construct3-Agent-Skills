# scripts/ Directory

## Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `build_plugin.py` | Build `plugin/`, the Claude Code plugin, from the skill, the prompts and the data of the Construct3-RAG clone beside this repository, under the limits of Claude's plugin directory. `--check` compares `plugin/` with a fresh build (`docs/decisions/plugin-folder.md`, `docs/decisions/plugin-tracks-commits.md`, `docs/decisions/plugin-repository.md`) | `python scripts/build_plugin.py`; `--rag <clone>` for a Construct3-RAG clone elsewhere |
| `bootstrap.py` | Clone the sibling repositories that are missing, create the game project from the empty project when its folder does not exist, and install the skill from `plugin/` in it | `python scripts/bootstrap.py --project <folder>` |
| `output_diff.py` | Run the skill's tools and generators with a git ref's scripts and with the working tree's, and list the cases whose output differs. The tools that read a project run over every official example and the game projects of `--projects`; `--help` names every case. Nothing is written to the repository. Before changing a skill script, read the `skills/AGENTS.md` Rules bullet "A change to a script is compared, old against new" | `python scripts/output_diff.py [REF]`; `--only print_sheet`, `--limit 20` for a quick run |
| `measure_examples.py` | Measure the official examples for a number before the template or a check takes it: the player's height, the HUD's share of the screen, popup tweens, Sine idle motion (`docs/decisions/borrowed-numbers.md`) | `python scripts/measure_examples.py <actors\|hud\|popups\|sine> --examples <example-projects> [--out .local/docs/evidence/borrowed-numbers/<measure>.json]` |
| `plugin/` | The plugin's manifest, README, icon and `agents/`, its sub-agent types, that `build_plugin.py` copies into `plugin/`; `version` in `plugin.json` is the floor the build never goes below, raised by hand for a minor or major release (`docs/decisions/plugin-tracks-commits.md`) | edit, then `python scripts/build_plugin.py` |

## Rules

- The data is read, never written, here. The scripts that fetch and export
  it are in Construct3-RAG (`scripts/init.py` and `docs/dev/data-pipeline.md`
  there), and a data change reaches `plugin/` through the build.
- The locales of the data are the `languages` of the Construct3-RAG
  clone's `data/c3-schemas/_index.json`; the build reads them from there.

## Checks

```bash
python -m compileall -q scripts
python scripts/build_plugin.py --check
```
