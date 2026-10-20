# An Entry of the Lookup Ends With Its Pitfalls File and the Built-In Preferred to Its Addon

Date: 2026-10-16

## Problem

An entry of `lookup_ace.py` holds the parameters, the JSON to write and the
official examples that use the ACE. The traps of its addon are elsewhere, in
`prompts/pitfalls/<topic>.md`, which a model reaches through
`prompts/event-sheet-pitfalls.md`. A small model does not read that index
(`event-sheet-design-guidance.md`, "What small models read"), so the
entry is the only text it sees before it writes the ACE.

The repository also prefers some built-ins over addons the editor still
ships: a Tween on Opacity instead of Fade, a hierarchy instead of Pin
(`prompts/event-sheet-thinking.md`, "Native first"). The checker cannot
carry that preference. A check becomes an error only when a run over the
official examples adds no finding, and the examples use Fade
(`data/c3-example-usage/behaviors/fade.json`). So the lookup is the
place where the preference can reach a model.

## Options

1. One map in a JSON beside the topic files. It drifts: a topic renamed or
   split keeps its old row until someone notices.
2. An `addons:` line in each topic file's front matter. The map moves with
   the file; a test resolves every id against the schemas.
3. Tag the preferred-over addons in `_deprecated.json`. That list is the
   editor's, exported from its bundle; a repository preference inside it
   would read as a deprecation, and the next export would drop it.

## Decision

Option 2 for the pitfalls, a separate list for the preferences.

- Each topic file opens with `---`, `addons: <ids>`, `---`. An id is a
  plugin or behavior (`tween`), an ACE of one (`system/wait`,
  `_common/pick-children`), or `none` for a topic that holds for every sheet
  (Expressions). A topic lists an addon when it holds an entry about that
  addon's own behaviour, and an ACE when the entry is about that ACE and the
  rest of its plugin is not concerned: Wait, Create object and Restart layout
  are System's, and the other System entries print nothing.
- `prompts/native-first.json` lists the addons a row of the Native first
  table replaces, with the built-in to use and the row's Need text. The test
  checks that the row exists in the table and names the addon in its Not
  column, and that the editor has not deprecated the addon: a deprecated one
  belongs to `_deprecated.json` and prints as before.
- `lookup_ace.py` ends an entry printed in full with `pitfalls: <file>` for
  the topics that name its addon or the ACE, then `prefer: <built-in>; Native
  first, "<row>", in <file>`, after the example commands. Paths are printed
  as every command the scripts print is, relative to the current directory
  or absolute, so they open from the clone and from the plugin. Under
  `--limit` the example commands go first and the pointers stay while the
  entry fits with them. A list that prints no entry in full ends with the
  addons' own pointers once. An entry with neither prints nothing more.
- The `prefer:` line is a pointer, not a finding: `check_project.py` is
  unchanged, and `isDeprecated` keeps its marks.

The cost, measured on five lookups from the clone on 2026-10-16 as
characters of output:

| Lookup | Before | After |
|--------|--------|-------|
| `Tween tween one` | 3748 | 3826 |
| `Fade fade` | 1325 | 1476 |
| `Timer start timer` | 1439 | 1478 |
| `Sprite set animation` | 3316 | 3402 |
| `System wait` | 3119 | 3278 |

An entry of a mapped addon grows by one line, and a brief list by one line
at its end. The `addons:` lines reach the plugin with `prompts/`, which the
build copies whole.

## Re-evaluate when

- An eval shows a model writing a tween or a timer wrong with the pointer
  printed: the line is too little, and the conclusion lines of the topic
  may have to print in its place.
- A topic file collects entries about a second addon: add the id to its
  line, or split the topic.
- The Native first table gets a third superseded addon: add it to
  `native-first.json` and to the row's Not column in the same change.
