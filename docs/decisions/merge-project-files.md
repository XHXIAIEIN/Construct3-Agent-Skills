# A Stopped Git Merge Is Finished by sid and uid, Not by Line

Date: 2026-11-05

## Problem

Git merges the JSON files of a folder project by line. Two branches that each
add an instance, an event or an object type at the end of one list stop on the
same few lines, though nothing in them disagrees. An agent then reads the
conflict markers and writes the file by hand. Two branches can also give one
uid to two instances, or one `imageSpriteId` to two images. Git sees no conflict
there, and the editor refuses to open the project.

## Evidence

A replay over one game project's history: 989 files of commits that were
cherry-picked, merged from the same three versions as the original pick. Git's
line merge stopped on 52 of them.

| What the script did with the 52 | Files |
|---------------------------------|-------|
| Left in conflict, a value both sides changed | 23 |
| Merged, the same as the commit a person or agent made | 16 |
| Merged, the same but for the order of two additions | 5 |
| Merged, and the commit also holds what was written during the resolution, or a uid renumbered by hand | 8 |

On the other 937 files it stopped on none. One of them differs from Git's result
in the order of two events, because an edited comment has no sid and so counts as
an addition; the output names that list. Three of the stopped picks, run for real
in a worktree, then passed `check_project.py`.

## Options

1. **A merge driver in `.gitattributes`.** Git would call it by itself, but this
   repository cannot ship the file, because Claude's directory refuses to validate
   a plugin that has one, and each game project would have to install it.
2. **A script an agent runs when Git stops.** Chosen. It needs no setup, and
   `SKILL.md` says when to run it.
3. **Rules in a guide for resolving by hand.** The files are thousands of lines,
   and the uids and image numbers are not visible in the conflict.

## Decision

Option 2, `scripts/merge_project.py`.

- A list whose elements have a sid, uid, `imageSpriteId`, name or id, or are text,
  merges element by element. Any other list, such as a position or a polygon, is
  one value, because merging its elements makes a value neither side chose.
- A value both sides changed stays in conflict with Git's markers, and is printed
  with both sides. The script never picks a side.
- Where both sides added at one place, the current branch's comes first and the
  output names the list, because the order of events and of instances changes
  what the game does.
- A uid or image number that two things share stays on what the last commit holds.
  The other gets a free number, with the references to a uid in the hierarchy. A
  uid written as a number in an event or a script is not followed.
- Only project files are merged. Documents and tuning data stay for the agent.

## Re-evaluate when

The editor writes a project format that holds no sid on some list, or a replay
shows the script losing an element that either side had.
