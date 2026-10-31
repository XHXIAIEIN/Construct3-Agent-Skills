# An Export Passes Only When Its Game Boots

Date: 2026-10-31

## Problem

`export_project.py` ended once the Web export was unpacked: it printed
`exported` and exited 0, and nothing ever loaded the exported game. An export
runs in modes that no preview played: Use worker Auto, Offline support,
deduplicated and optimized images, and the other options the editor
remembers. So a project that previews fine can export a game that does not
start, and an agent would hand it over as done.

Evidence: a Web export of an official example, with one spritesheet removed
from its folder, logged three runtime errors for the missing file and never
ticked; the packaging step cannot see that. Agent tools for other engines
state the same rule, that a successful build proves packaging only.

## Options

- Keep the export step as it is, and tell the agent to open the export by
  hand: the agent skips a step that no script asks for.
- Open the export in the browser that exported it: that window is headed
  and logged in to the editor, and the service worker of Offline support
  would stay in its profile.
- Serve the export folder on `127.0.0.1` and open it in a headless, muted
  browser on a fresh profile, deleted after the run, as a player's browser
  would load it from a web host.

## Decision

The third. After the export the script waits up to 30 seconds for the
runtime to tick, with the probe that `open_in_editor.py` uses for a preview,
lets it run 2 seconds, and keeps a screenshot of the first layout in
`.tmp/scripts/export-project/boot.png`. The page and each worker are watched
from their first line: a worker waits for the debugger until its console and
its requests are enabled. The local server also keeps the status of every
request, so a file the export lacks shows whichever context asked for it.

The last line is the verdict. `booted:` with exit 0 needs a tick with no
console error and no failed request. `boot failed:` exits 6, a code of its
own, because the export is in place and the fix is in the project, which
exit 1, "not exported", does not say. A boot that could not run exits 3,
the code of a check that did not run (`not-checked-is-not-a-pass.md`).

The browser's own request for `favicon.ico` is not counted, because the game
does not make it. A worker's errors reach the page's log as well, so only
the worker's own console counts them.

`release:` lines warn, before and after the export, of the icons and loading
logo of a new project, which are Construct's, and of an empty Author, ID or
Description, which the export writes into its `appmanifest.json`. They keep
the exit code, because a game in testing ships with them.

## Re-evaluate when

A game needs a request that fails on `127.0.0.1` but not on its host, such
as a call to a server that allows only its own origin, often enough that the
boot needs a list of the requests that may fail.
