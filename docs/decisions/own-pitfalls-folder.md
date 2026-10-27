# A User's Own Pitfalls Sit Beside the Cookbook's

Date: 2026-10-27

## Problem

A user who learns a pitfall in their own project has nowhere for the skill
to read it but a fork of Construct3-Cookbook. The scripts read one Cookbook
clone (`guides-in-cookbook.md`), so a fork replaces the official guides, and
the user then merges every upstream change by hand to keep getting new
pitfalls.

## Evidence

- `locate_cookbook` returns the first folder that holds
  `guides/pitfalls.md`; nothing else is read.
- Two scripts read pitfall pages by folder and page name, not through the
  index: `search_guides.py` searches every bullet of the pages under
  `PITFALL_FOLDERS`, and `lookup_ace.py` maps an addon to the page its id
  names and to the pages whose `addons:` line names it. A second folder
  laid out the same way needs no index to be read by both.
- The design and style guides, Native first and the pages the checker cites
  are one text each, read whole or hashed by the design review. Two
  versions of them would have to be merged, not listed.

## Options

1. Fork the Cookbook. Works today; costs a merge per upstream change, and
   the user's pages mix with the official ones.
2. A folder of the user's own pitfall pages beside the official clone, read
   by the two scripts that search pitfalls. No merge; the official guides
   stay as they are.
3. A second folder that may also override the design guides. The design
   review and the checker would need rules for which text wins.

## Decision

Option 2. The folder has the layout of the Cookbook's `guides/`, without
`pitfalls.md`. It is named by `--cookbook-extra`, `CONSTRUCT3_COOKBOOK_EXTRA`
or a `Construct3-Cookbook-extra:` line of the project's instruction file,
whose relative path starts at that file's folder so a folder kept in the
game project travels with it. A named place that is not a folder is a note,
not an error. `search_guides.py` puts the user's entries first among entries
that hold as many of the words, since they are about the user's own game;
`lookup_ace.py` lists the user's page first. The design guides, Native
first and the checker's citations stay the Cookbook's. The block that
`install.py` writes is unchanged: the line is optional, and a user adds it.

## Re-evaluate when

Users ask for their own design or style guidance, or for the checker to
cite their pages.
