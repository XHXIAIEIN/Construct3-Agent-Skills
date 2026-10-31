# The Guide Search Prints the Symptom Rows First

Date: 2026-10-31

## Problem

`search_guides.py` searched only the entries of the Cookbook's pitfall
pages. An entry describes a mechanism, such as a trigger that runs only in
a sheet the layout includes, so it seldom holds the words of what an agent
sees on screen. Against the Cookbook of 2026-10-31, `trigger never fires`
found none of the three entries that cause it, `gone after save` found only
unrelated entries, and `click nothing` found one of five causes.
The Cookbook's `guides/symptoms.md`, added the same day, maps twelve
symptoms to their causes in the order to check them, each with the page
that holds its entry.

## Options

1. Leave the search as it was. An agent that searches with the words of a
   symptom gets entries that share a word, or none.
2. Search the symptom rows with the entries, ranked together. A row holds
   every word of its causes, so a common word ranks it beside an entry
   about one cause.
3. Search only the symptom column of each row, and print the matching rows
   before the entries, each cause with the full path of its page.

## Decision

Option 3. A symptom is a short phrase in the words an agent uses for what
it sees, so matching only that column keeps a row out of searches that name
a mechanism. A matching row comes first, because it orders the causes and
names every page that one search for the symptom would miss. `--pitfalls N`
prints at most N rows as well as N entries, so `--pitfalls 0` prints
neither. A Cookbook clone without `guides/symptoms.md` prints only the
entries.

## Re-evaluate when

- An eval shows an agent that searched with the words of a symptom in the
  table and did not get its row: search the causes too, or add the words to
  the symptom.
- The table grows past a size that one search prints whole: rank the causes
  within a row.
