# Abductractor: finish line and restart

## Answer

The project has one event sheet, `Events`, run by layout `Game`. It has 108 events. The event numbers below are the ones `print_sheet.py` prints, which the skill says match the editor's margin. I did not open the editor, so the margin numbers are not checked there.

### When a tractor reaches the finish line

1. Event 103, `TractorBase: On collision with FinishLine` (group Finish Line, event 102), runs for each tractor that touches the line. Its action calls `prepareForGameOver()`.
2. Event 107, `function prepareForGameOver()`, stops the race. It stops the timers, sets `movementChecking` to False, stops the UFO tweens, sets every tractor's maximum speed to 0, sets the AI actions to "none", sets `pointerChallenge` to False, hides the stop lights and the gauge, and calls `stopAllAI()`.
3. The result depends on whose tractor it is:
   - Event 104, `TractorBase: Pick Own children Player`, calls `showGameOver("success")` when the tractor that arrived is the player's.
   - Event 105, `System: Else`, calls `showGameOver("fail")` for any other tractor.

### Where the game restarts

Event 108, `function showGameOver(type: string)`, does the restart:

1. It sets the text to FAIL or SUCCESS.
2. It fades in the Fader and the game-over text over 1 second.
3. It waits 4 seconds, then fades the text out over 1 second.
4. After the previous actions complete, it runs `System: Restart layout`, then `System: Reset global variables to default (include static: True)`.

After the restart, the layout's "On start of layout" events run again and build the race:

- Event 2 (sub-event 3) sets up the tutorial and fader, creates the player's `TractorBase` and adds `Player` as its child, and creates 400 `Corn`.
- Event 13 sets the camera.
- Event 45 (sub-event 46) creates a `TractorBase` for each `AIPlayer`.
- Event 78 starts the exhaust smoke timers.

### The other path into the restart

If the player's tractor is abducted, the same restart runs with "fail":

- Event 87, `function abductTractor()`, has its sub-event 88 (`TractorBase: Pick Own children Player`), which calls `prepareForGameOver()`.
- Event 91 (`System: Player.Count = 0`, `System: Trigger once`) calls `showGameOver("fail")`. It sits under event 90, `UFO: On Tween "UFOGoesToTractor" finished`.

A text search of the whole sheet found no other `Restart layout` and no `Go to layout`. The only layout actions are `On start of layout` (events 2, 13, 45, 78) and the restart in event 108.

### Caveat (inference, not run)

Event 103 has no guard. If a second tractor reaches the line during the 5-second game-over sequence, event 103 runs again and `showGameOver` runs a second time. The sheet does not show whether the second tractor can still reach the line after `prepareForGameOver` sets the speeds to 0. I did not play the game to check.
