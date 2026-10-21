# An Export Replaces Only the Folders It Recorded

Date: 2026-10-22

## Problem

`export_project.py` empties `--to` and deletes the folders beside it that a
killed run left. It took a folder for an earlier export when the folder held
a `data.json`, and the folders beside it had the fixed names `<folder>.new`
and `<folder>.old`. The audit of 2026-10-07 (S02) lost a folder of notes
that also held a `data.json`, passed as `--to`, and a project with a
`data.json` that sat in `web.new`. Checking more files of the Web format does
not help: a copy of an export, or a folder of the user's under a fixed name,
passes any check of the format.

## Options

- Check the format harder: the cases above still pass.
- Never delete: every export leaves its predecessor behind, and a `.c3p`
  packed later carries it.
- A record that the script writes into each folder it makes, listing the
  files it wrote; the script replaces or deletes only a folder that holds
  the record and no other file, and the folders beside `--to` get names of
  their own.

## Decision

The third. Every export folder holds `.export_project.json`, the list of the
files the export wrote, and ships with it: it holds file names only. A
folder without the record, or with a file the record does not name, stops
the export with exit 2 and the names of those files. `--take-over` records
what such a folder holds, as the user asked, and the export then replaces
it; it still refuses a folder without a `data.json`. The folders the swap
uses are `<folder>.new-<8 hex digits>` and `<folder>.old-<8 hex digits>`,
and the `.new` one holds the record before the zip is extracted into it, so
that a run killed at any step leaves only folders the next run knows. A
folder beside `--to` without the record is left alone.

The cost: an export that an earlier version of the script made has no
record, so its next export stops once and asks for `--take-over`.

## Re-evaluate when

A host refuses or serves the record in a way that matters, or the editor's
export starts writing a file of the same name.
