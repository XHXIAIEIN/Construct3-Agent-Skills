# A Preview Run Names What Went Wrong in the Runtime

Date: 2026-10-31
Schema: Construct 3 r506.3

## Problem

A preview run printed the runtime's exceptions and console errors, the
layout at the end and the screenshots. A plan of 14 steps on a phone-sized
window passed every step, while it fetched a missing file, emptied the
screen, put one small sprite on it, held the game's thread for 2 seconds
and changed the layout:

- A file the game asked for and did not get. A `fetch` of a missing file
  answers 404 and logs nothing.
- A screen with nothing drawn. The blank test counted only the share of one
  colour, at or above 99.9%. A sprite alone leaves that much of a phone
  screen one colour, so it counts as not drawn yet. On a 430 x 932 window
  the test read an empty screen as drawn, through a black row the scaled
  capture adds.
- A tap that went to another layout. The run printed the layout once, at
  the end, so a failed `until` did not say where the game was.
- A game that stopped ticking. A stall that ends left nothing. A While that
  never ends holds the runtime's thread for good: the run waited for a
  reload, and after 37 seconds failed the step with "the page reloaded, and
  no runtime ran in it in 30 seconds".
- An editor the browser could not reach. Every cause printed one sentence,
  "check the network connection", while the browser's own error code, on
  its error page, said which: DNS, a proxy, a certificate, a refused
  connection or a timeout.

## Evidence

Measured in previews in Edge headless on a 143 Hz display, of 12 official
examples and a game converted to Construct 3, with the runtime probe's
tick listener:

| Where | Longest gap between two ticks |
|-------|-------------------------------|
| A running layout | 0.05 s |
| Screenshots taken one after another, as a `record` step takes them | 0.014 s |
| The start of a layout, over 78 changes of layout | 0.27 s |

Over the screenshots the scripts took of games, at an eighth of their size,
every one at 99% one colour or more that showed something had a luminance
deviation of 7.9 or more; a layout that drew only a 4 px bar had 0.3, an
empty one 0. A 20 x 20 ship sprite alone on a 430 x 932 screen read 99.98%
one colour with a deviation of 2.6.

A request of the runtime's worker reaches only the worker's own DevTools
session, once `Network.enable` was sent there. The layout's first requests
come while the worker starts.

## Options

- Read failed requests from the console's "Failed to load resource" lines.
  The Log domain replays them, but a worker's requests are not among them.
- Read failed requests from the Network domain of the page and of each
  worker. The worker's first requests come before a session that attaches
  late turns it on, unless the worker is held at its start.
- Judge stalls from the time a step's own call took. A `wait` step makes no
  call, and a stall that ends inside it leaves nothing.

## Decision

- Requests: `open_in_editor.py --preview` and `preview_project.py` turn on
  the Network domain of the preview window as it opens, and attach each new
  worker held at its start (`waitForDebuggerOnStart`), turn its requests
  on, then let it run. A response of HTTP 400 or more and a request that got
  no response print a `network:` line at the step it came in, with the URL,
  and count as errors: the run fails, as it does on a runtime error. A
  request the page cancelled, as a reload does, is not one. A worker's
  startup request for a missing file came in each of 12 runs, 5 held and 7
  not held; the hold keeps that order on a machine where the worker starts
  faster than the run turns its requests on.
- Blank: a frame is blank when 99.9% or more of it is one colour and the
  standard deviation of its luminance is under 2. Every screenshot prints
  both numbers. The window is read at an eighth of its size, each side cut
  to its multiple of 8, because a height of 932 adds a black last row: an
  empty screen read 99.15% and a deviation of 19.
- Layout: after each step the run reads the layout and the ticks in one
  call. A step that leaves the game on another layout says `layout 'A' ->
  'B'`, and a failed step prints the trail from the start.
- Ticks: the probe's `ticks()` gives the ticks, the seconds and the longest
  gap since its last call. A step fails when the gap passed 1 second, about
  four times the longest one measured, or when the game's page or worker
  did not answer in 5 seconds. A `record` line gives the ticks a second and
  the longest gap over the steps it covered.
- Editor: on the browser's error page the run reads the error code and
  names it with the advice for its kind: a name that does not resolve, a
  proxy, a certificate, a refused connection, a timeout, no connection. An
  HTTP 404 from the editor names `--release`.

## Re-evaluate when

- A machine slower than the one measured fails a step on a layout that
  starts slowly: measure the gap there before raising the limit.
- A game reports a request as failed that it meant to fail, such as a
  probe for an optional file.
- A Construct release moves the runtime's requests out of the page and its
  workers, as into a service worker.
