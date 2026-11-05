# Verifying a change by playing it

How to plan a check of what a change does in the running game: which cases
to play, how to reach each one, and how to read whether the events did what
they were written for. `scripts/preview_project.py --help` says how a plan is
written, [editor-and-preview.md](editor-and-preview.md) what the preview and
the input sent into it do, and
[reading-the-runtime.md](reading-the-runtime.md) how to read a value the
`state` step does not print. Read this before writing the plan for a change
the player triggers or sees: a drag, a merge, a jump, a hint, a sound.

A lesson about planning such a check goes into the step or row it
sharpens: rewrite that rule so it covers the lesson, and keep one source
per step, the one that shows the rule most plainly. A lesson no step covers
becomes a step with its source. The file is read for every kind of game, so
a source from one game shows the rule and does not narrow it; a list of one
game's cases under a step would be copied into games it does not fit. A fact
about the editor or the preview goes to `editor-and-preview.md`.

## Steps

1. **Name the cases before the plan.** A change that adds or moves a
   condition has a case it is written for, a neighbouring case where it
   must not fire, the case the game falls back to there, and a
   follow-through: the player does what the game asked and the state that
   asked for it clears. Play every one; a plan that plays only the first
   passes a condition that fires everywhere. If the game restarts the
   layout or goes to it again (a new round, a retry, a return from a
   menu), play the cases a second time. *Restart layout* and *Go to
   layout* bring the instances back as placed but keep every global
   variable and static local at its end value, so a case that passes the
   first time can fail the second
   (`Construct3-Cookbook/guides/plugins/system.md`). A change
   with no condition of its own, a colour, a size, a duration, a volume,
   has one case: reach the scene where it shows and read it as step 5
   says. A change that shows something for a moment, a notice, a hint, a
   banner, has one more case when the flow can show another such thing at
   that time: play to both at once and take a `shot`, which prints the `text`,
   `stacked`, `overlap` and `edge` findings of that frame. A finding on a
   frame in motion may be the motion, so let it rest and shoot again.
   [observed in a game project, r504 preview, 2026-10-02: an
   idle hint to deploy a piece was played with the slot's column holding an
   enemy, without one, where it had to fall back to a merge hint, and
   followed through by dragging as the hand showed]
2. **For a bug, see the plan fail before the fix.** Write the report in
   four parts:
   - given: the scene and the state the game is in
   - doing: the input, or the time that passes
   - produces: what the game does
   - instead of: what it should do

   The plan reaches the given, does the doing and reads the produces where
   the player sees it. Play it on the project before any event changes,
   and see it fail at that read for the reason the report gives. A plan
   that passes there, or fails at an earlier step, has not reached the
   bug. A fix played against it shows nothing, so change the plan until it
   fails as reported. Then change the events and play the same plan until
   it passes. [design: `Construct3-Agent-Skills/docs/decisions/preview-player.md`,
   the bullet on a bug's plan]
3. **Reach each scene the way the game does.** Start from what earlier
   checks showed: the notes of the game, each on the function, group or
   event it rests on. `print_sheet.py` ends a whole print with the notes on
   its sheets, and `scripts/notes.py` prints them all. A note marked
   changed rests on events that changed since it was verified, so check it
   in the game before you rely on it. Play to the scene when that is short; otherwise call
   the game's own functions with
   `runtime.callFunction`, which run the events that keep related values in
   step. Write a value directly only when no event reaches it, and then
   write every value the events tie to it as well: a value written alone
   lets the game's own expressions compute what play never produces, and
   the runtime errors that follow are the plan's. Rerun the same steps
   without the write before blaming the events. [observed in a game
   project, r504 preview, 2026-10-02: pieces made by calling the game's own
   creation function behaved as bought ones; an enemy's hp set to 10^6
   through a JSON instance's `setJsonDataCopy`, above the stage total the
   events add up as enemies spawn, drove a progress ratio near -20000 and a
   low-pass frequency computed from it to 0, logging a RangeError per call
   that the same steps without the write did not]
   `runtime.callFunction(name, ...params)` takes every parameter the
   function declares, in the sheet's order. Fewer throw `not enough
   function parameters passed for 'X' (1 passed, 4 expected)`, and a name
   no function has throws `cannot find function name 'X'`. Either stops
   the step. Read the declaration with `print_sheet.py` first. [observed in
   a game project, r504 preview, 2026-10-05:
   `runtime.callFunction('createBase', 8)` threw the first error, and the
   same call with all four parameters made three pieces; observed in a game
   project, preview, 2026-10-03: a call of `checkStageClear`, which the
   sheet did not define, threw the second]
4. **Meet the conditions that start the flow.** Read the trigger chain of
   the event under test back to its first trigger: a countdown that a touch
   starts, an audio clock that stands still until the first input, a
   tutorial or a save flag. Each run starts from a first launch, so a game
   with a first-launch tutorial needs it finished or skipped before the
   scene. [observed in a game project, r504 preview, 2026-10-02: the idle
   timer of a hint starts in *On any touch start*, and a plan that set the
   scene up through `runtime` alone waited 15 seconds for a hint that never
   came, until a tap on an empty spot came first]
5. **Read the result where the player sees it.** A variable that says the
   flow ran is not the flow: read what is on screen, positions, opacity,
   the layer shown, and for anything that moves, read it over time. A
   tween caught in one screenshot shows a point on its way. Put a `record`
   step around the motion with the values to follow in `watch`: they are
   read with every frame, the run prints their changes, and
   `NN-NAME/timeline.json` puts frames, steps and values on one clock, so
   where a motion starts, rests and ends is read from them. A `js` step
   that samples one value in a loop does the same for a value read once.
   Wait with `until` on the result, not a fixed
   `wait`, so a slow run does not fail and a fast one does not hide a
   second firing. A text or a mark that claims a state (Saved, Ready, Locked,
   a full bar, a key prompt) claims more than a change on screen, so read the
   value it claims while it shows. Local Storage answers a write later with
   *On item set* or *On error*, so a Saved set beside the write says what the
   game does not know yet (`Construct3-Cookbook/guides/plugins/localstorage.md`).
   [observed in a game project, r504 preview, 2026-10-02:
   a guide hand that fades in, presses and drags was read as a drag
   between two slots from the first two samples less than 0.5 px apart and
   the last sample after 1.5 s]
6. **Turn a word of feel into a number.** Floaty, slow, sluggish or heavy
   names no value to change. Name the variable behind the word: a jump's
   gravity and strength, a tween's duration and ease, a speed, a delay.
   Read its current value in the project. Then measure what the player
   feels in a `record` step with that value in `watch`: the time from the
   press to the top of a jump, how long a tween takes to rest, how far a
   dragged piece lags. Write the target in the same measure, from the row
   for the effect in `Construct3-Cookbook/guides/recipes/feel.md` where
   there is one, otherwise from the user. The change is done when the
   recording measures the target, not when the motion looks better.
   [design: `Construct3-Agent-Skills/docs/decisions/preview-player.md`, the bullet
   on a word of feel]
7. **Judge the change by the cases the run reached.** A run counts for the
   events it reached: a run that ends before the event fires has checked
   nothing yet, so extend the plan until it fires, and an error that
   follows a direct write comes from the write until the same steps without
   it show it too (step 3). Judge a motion's feel and timing from the
   watched values first: where it starts, overshoots and rests, and how
   long each part takes, against the row for the same effect in
   `Construct3-Cookbook/guides/recipes/feel.md` where there is one.
   Have a reviewer that has not seen the change describe the frames, and
   judge what they show from that description, because the agent that
   wrote the events reads its own frames by what it meant them to show.
   Before the run, write `expect` on the `record` step: what a frame would
   show if the change works and if it does not, as visible features. Write
   `ask` too: open questions about the frames, such as what moves and which
   way, what is at a place, what a text says. Leave out what you hope to
   see and any question a yes answers, because both tell the reviewer what
   to look for. The run writes a brief of the frames and the questions
   alone. Have it answered as its `brief:` line says, and check the reply
   with `--reply`. Then hold the description against `expect`. A
   description in which the thing is not seen (too small, covered, off the
   frame, too fast) is no verdict: record that part closer or slower and
   play it again. Name the three worst defects the description shows, each
   with its time and frame and the event to change. Fix only those and
   record that part again, until the values and the description show no
   defect. If a run did something once (the player reached the ledge, the
   door opened), state the claim that it can happen as shown. If the plan
   did not reach it or do it, the claim is open, not false, because the
   plan is as likely at fault as the game: improve the plan. Say it cannot
   happen only when the game's own values show it, such as a jump's
   strength and gravity against a platform's height or a speed against a
   timer, and name those values. The hand-over names the cases played, what each read, any
   value the plan forced and each claim left open, one line each, with the
   recording's review page, `NN-NAME.html`, where the user plays it frame
   by frame, selects a part that looks wrong and copies it back as a task.
   [design: `Construct3-Agent-Skills/docs/decisions/recording-describer.md`;
   `Construct3-Agent-Skills/docs/decisions/preview-player.md`, the bullets
   on `record` and the review page]
8. **Keep the plan, and replay every kept plan after each change.** Once a
   plan passes, run it again with `--keep NAME`. Only an `until` step after
   an input or a wait fails when the game does not do what the change
   should make it do, so a plan without one is refused: an `until` before
   the first input reads the start, and a `js` or `state` step prints a
   value and checks nothing. The plan is copied to
   `tools/plans/NAME.json` in the project, beside the generator and the
   design, and is committed with the change it checks; the editor ignores
   the folder. After every later change, `preview_project.py --all` plays
   each kept plan from a first launch in one editor session and names each
   one that fails. Fix the events the failing step reads, not the plan,
   because the plan passed when its change was made. Change a kept plan
   only when the game was meant to change what it checks.

   If a plan passes in some replays and fails in others on the same game,
   the plan races the game, so fix the plan. Confirm it by playing the plan
   alone several times, then look for one of these readings:
   - It starts after the input. A motion of 0.3 s can end before the first
     read, so start the `record` with its `watch`, or the loop that reads
     every frame, before the input.
   - It samples a motion at fixed intervals. A wobble crosses its rest
     position twice in each swing, so a read every 0.12 s can land on the
     rest position. Read every frame and test the largest value.
   - It tests a threshold that only an overshoot reaches. Test the size at
     rest, because an overshoot lasts a few frames.
   - It sends a gesture on a timer. A game reads a finger's speed per tick,
     so a dropped frame changes the speed. Send one move per tick, by
     awaiting `tick` on `runtime`.
   - It starts at any phase of a repeating timer while a later step tells
     two causes apart by that phase. Wait until the timer reaches a known
     phase, then start.
   - It calls a game function before the player could. A function that a
     button calls can run during a transition that keeps the button off, and
     then the game enters a state that play never reaches. Wait with `until`
     for the state that the button needs, then call the function.

   [observed in a game project, r506.3 preview, 2026-11-05: six kept plans
   that failed at intervals, each traced to one of these readings]
   [design: `Construct3-Agent-Skills/docs/decisions/preview-player.md`, the bullet
   on kept plans]
9. **Keep the facts a later check needs.** Once a probe or a passing plan
   has shown a fact that a later check of this game would search for
   again, keep it as a note: how a scene is reached, the parameters a
   function takes, the trigger that starts a flow, the tutorial to skip,
   the variable behind a feel. Run `scripts/notes.py --add "FACT" --sheet
   SHEET --function NAME`, or `--group TITLE` or `--event N` in place of
   `--function`. The note goes into `tools/notes.json`, which is committed
   with the change. One note holds one fact. A fact read from the events
   alone goes in only after the game showed it, because the events are what
   the check tests. If a note is marked changed, check it in the game, then
   run `--confirm N`, or `--rewrite N "FACT"` with what holds now. If a note
   is marked gone, rewrite it on the events it rests on now, or remove it
   with `--remove N`. [design:
   `Construct3-Agent-Skills/docs/decisions/project-notes.md`]

## What each layout shows

`scripts/check_screens.py` checks what every layout shows, once the preview
passes. It goes to each layout with the runtime's `goToLayout`, takes a
screenshot into `.tmp/scripts/check-screens/shots/`, and reads the layout's
instances from the runtime. Each finding line names the layout, the object
type and the UID: a text its box cuts (`text`), instances of one type on one
box (`stacked`), overlaps on the HUD and texts over texts (`overlap`), a HUD
instance the screen's edge cuts (`edge`), a type whose kinds show one frame
(`frame`), a text still "Text" or Lorem ipsum after the start (`placeholder`),
a text whose letters read under 4.5:1, or 3:1 when large, on what lies behind
them on screen (`faint`), and Texts that events set with no declared longest
text (`unlimited`).

A finding fails the run. A warning does not, and the hand-over names it:
`unlimited` warns, and so does a finding that only a guessed longest text
causes.

Each layout is also shown in three more data states and on two more shapes of
screen: the Texts that events set show their longest text, nothing, and a
count of one, and the screen takes the shapes the project's orientations
allow, such as 4:3 and a phone's. A finding that arises only there carries `@`
and where, as `@phone worst`, and its screenshot is
`<layout>@phone-worst.png`. The longest text of a Text comes from
`tools/texts.json`, which the generator writes from each helper's `longest=`.
`--viewport` shows one screen and `--data demo` the layout as it starts.

A layout reached by `goToLayout` starts without what the game's flow sets up
before it, and one whose start events leave at once is printed as left for
the layout they went to. Play to such a scene with a plan of
`scripts/preview_project.py` and a `shot` step, which prints the findings
that hold on any frame. [observed in a generated card game, r495.2
preview, 2026-10-04: the combat layout, reached directly, went to the ending
at once; played to by a plan, the same checks over its instances found the
names, descriptions and costs of five cards stacked on one card, in a
screenshot the agent had reported as rendering normally]

## The design of the sheets

`scripts/review_design.py` reads the event sheets once `check_project.py`
passes, before the editor opens them. It starts no browser. Each finding
line names the event as `print_sheet.py` numbers it and says what to write
instead; fix every one. A rule is a finding only where it finds next to
nothing in the 524 official examples, every example hit read; what the
examples also write becomes a question that names its events. Measured on
2026-10-04 with `evals/measure_design.py`, over the examples, a generated
card game, an editor-made game project and a tic-tac-toe sheet:

| Rule | Finding at | Examples | Card | Editor-made | Tic-tac-toe |
|------|------------|----------|------|-------|-------------|
| `conditions` | 12 or more conditions besides the trigger; the examples' most is 11 | 0 | 0 | 1 | 0 |
| `guard` | the same 3 or more conditions of objects in 3 or more events of a sheet | 5 in 5 projects | 0 | 5 | 0 |
| `trigger` | 2 or more sibling events with one trigger, told apart by globals | 2 in 2 projects | 0 | 0 | 1 |
| `twice` | one action list writes a value into an Array cell indexed by an object's expressions and into that object's instance variable | 0 | 0 | 0 | 2 |
| `global` | a scratch global (`TMP`, `TMPN2`); a layout's sheet declaring 10 or more globals only other sheets use | 0 | 6 | 0 | 0 |
| `uid` | an instance variable set to the UID of an instance created in the same actions, then picked back by it: a container | 0 | 3 | 0 | 0 |
| `data` | 20 or more actions of one kind with literal values: a project file | 0 | 1 | 0 | 0 |
| `restart` | On start of layout setting instances after *Pick all*, on a layout that *Restart layout* or *Go to layout* enters again | 0 | 0 | 0 | 1 |
| `expression` | 5 or more parentheses deep, with a call of 30 or more characters written twice: a function | 0 | 6 | 1 | 0 |
| `follow` | a part in the object's container or created beside it, set from the object's position once, while another event moves the object alone: a hierarchy | 2 in 1 project | 3 | 0 | 0 |

The five `guard` hits in the examples repeat 3 or 4 conditions, inverted
*Is playing* or *Is touching* tests and a pick, across sibling events of one
group; a parent event would hold them once there too. The two `trigger`
hits press Space in sibling events told apart by booleans, the shape of the
tic-tac-toe sheet. The card game's `uid` hits were replaced by a container
while it was measured.

The `follow` rule was measured the same way. Its two example hits are in
ceiling-trap: the rail path is placed at the trap once and stays while the
trap stomps down it, which is the design there. The card game's three hits
move the cards in the hand layout, the aim and the play while their name,
cost and text labels stay where the cards were drawn. Spawned parts that
start at an object and then move on their own, such as projectiles, are not
made with the object, and the rule leaves them.

The questions name the events of what the examples write as well: 4 to 11
conditions (231 events in 76 example projects, 71 in the editor-made game),
sibling events of one trigger that test more than it (5 in 4), sibling
events that differ only in their numbers and texts (53 in 27; the style
ladder of `check_project.py --style` takes 5 or more), 3 or more inverted
conditions (34 in 21), a global one function or one group reads and writes
(262 in 92), and a UID kept in an instance variable (19 in 16). A question
is answered from the printed events it names, never from memory of the
plan. So the review writes the questions and the sheets as `print_sheet.py`
prints them into `brief.md`, for a reviewer that has not seen the project or
the request; `construct3:design-judge` is such a reviewer. Without a
sub-agent, answer them from `print_sheet.py`. Two candidates were dropped: a global that several
functions write and others read (20 in 6 examples, 15 in the editor-made game,
all of them game state), and 10 or more globals on a layout's sheet (45
examples; the examples keep shared globals on a sheet with no layout,
samuroof `Globals`). An event of 6 or more conditions stays a question and
is not a `--style` warning of `check_project.py`: 44 events in 24 example
projects have one.

## By kind of game

What the plan drives, what it reads and what has to be held still differ
with the input and the timing the game is built on. A game mixing several
kinds takes the rows of each.

| Kind | Drive | Read | Hold still |
|------|-------|------|------------|
| Board, merge, puzzle, cards: input on instances | `tap` and `drag` with an instance or `{js}` as the target | instance variables, which cell an instance sits in, counts; a recording for the motion of a drop or a merge | random placement: read where an instance landed instead of assuming it |
| Platformer, top-down, action: input held over time | `key` with `seconds`, `hold` | positions and behavior state against a range, `until` a position is passed; a recording watching the position for a jump's arc | the frame rate, which sets `dt` |
| Physics | as above | positions and velocities against a range | the Physics time step |
| Rhythm, music, sound | input on the beat, timed from `Audio.CurrentTime` | the sound itself, recorded in the page | the audio clock's start |
| Spawners, random levels, loot | play or `callFunction` | what spawned and where | the random seed |
| Menus, several layouts | `tap` on buttons; `move` for a menu that opens on hover, with `seconds` and `rest` for its delays | the current layout and layer visibility | the layout the preview starts on |

- Frame rate: a preview ticks at the display's rate, so a move that
  integrates `dt` lands at a slightly different place each run. Compare
  positions against a range, and use `until` instead of a fixed wait.
  `runtime.timeScale` slows the game for a closer look; the audio clock is
  not scaled. To count an effect's frames, as `scripts/measure_timing.py`
  does, slow the game and give the `record` step `"fps": 60`, because a
  recording on the clock holds about half of a 60 fps effect's frames.
  [editor-and-preview.md, the bullet on the display's rate and "Recording
  an effect's frames"; manual: scripting/scripting-reference/iruntime.md
  `timeScale`]
- Physics time step: with the default *Framerate independent* stepping the
  simulation can differ between runs; *Set stepping mode* to *Fixed* makes
  it deterministic for the check. [manual:
  behavior-reference/physics.md "Set stepping mode"]
- Random seed: an Advanced Random object with *Replace system random* and a
  fixed *Seed* makes `random()` and the randomness of behaviors repeat from
  run to run; *Update seed* changes it from an event, such as a debug
  key or a function the plan calls. Fix the seed before recording a motion
  twice to compare the two contact sheets, so the frames differ only by
  the change.
  [manual: plugin-reference/advanced-random.md "Seed", "Replace system
  random", "Update seed"]
- Sound: the preview runs muted, and a sound is checked by recording it in
  the page, as [editor-and-preview.md](editor-and-preview.md) describes. The
  audio clock does not run until the first release, click or key, so a plan
  that checks music sends one first.
  [`Construct3-Cookbook/guides/plugins/audio.md`, the bullet on the audio
  clock]
- Layouts: the preview starts on the layout open in the editor, not the
  project's first layout. [editor-and-preview.md, the first bullet]
