# docs/ Directory

Each folder holds the documents of one reader. Put a new document in the
folder of its reader.

| Folder | Reader | Contents |
|--------|--------|----------|
| `decisions/` | Anyone asking why something is the way it is | one record per decision |

When a document here is added or moves, update the tables of
`AGENTS.md` at the repository root, the agent entry point, to match. The
docs of the data and the lookup service are in Construct3-RAG.

## Decision records

A record answers why the current design is what it is. It carries `Date`
and, where the data matters, `Schema` lines, then `Problem`, `Evidence` when
it is not in the problem, `Options`, `Decision`, and `Re-evaluate when`.

- A record states what holds now. When a decision changes, rewrite the
  record; do not append a dated update. A record whose subject is gone is
  deleted, and the commit that deletes it says why. Git keeps the history.
- Evidence is the finding that settles the choice, in a sentence or a small
  table, not the log of the runs behind it. Eval iterations, sweeps, raw
  counts and hashes stay in `.local/docs/evidence/`, which `.gitignore`
  excludes; a record may name that folder, and nothing needed to use the
  data or the service lives there.
- A finding from someone's game project is stated generically: no project,
  object or variable names.
- State behavior and cite the manual; a tally over the examples or a
  minified editor name goes stale with the next release.

## The index

`decisions/README.md` lists every record by its own title and date, newest
first, one line each; `tests/test_decision_index.py` fails when a record
lacks its line and prints the line to paste. A new record gets its line in
the same change that adds it.

The records of the event sheet guides' layout, naming and index live with
the guides in
[Construct3-Cookbook](https://github.com/XHXIAIEIN/Construct3-Cookbook/tree/main/docs/decisions).
