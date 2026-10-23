# Abductractor: finish line and restart

## Answer

A tractor that reaches the finish line starts the game-over sequence. The restart happens at the end of that sequence, in event 108.

The project has one event sheet, `Events`, which the `Game` layout runs. All numbers below are the editor's margin numbers as `print_sheet.py` prints them.

1. **Trigger: event 103**, group "Finish Line" (event 102). `TractorBase: On collision with FinishLine` fires for every tractor. Its first action calls `prepareForGameOver()`.
2. **Branch: sub-events 104 and 105.**
   - Event 104: `TractorBase: Pick Own children Player` calls `showGameOver("success")`. This is the player's tractor.
   - Event 105: `System: Else` calls `showGameOver("fail")`. This is any AI tractor.
3. **Shut down the round: event 107**, function `prepareForGameOver()`. It stops all timers (`GameTimer: Stop all Timer timers`), sets `movementChecking` to False, stops the UFOs, sets the tractors' maximum speed to 0, sets the AI action to "none" and stops its timers, sets `pointerChallenge` to False, hides the stop lights and the gauge, and calls `stopAllAI()`.
4. **Show the result and restart: event 108**, function `showGameOver(type)`. It sets the FAIL or SUCCESS text, fades in `Fader` and `TextGameOver` over 1 second, and waits 4.0 seconds. It then hides the text and runs **System: Restart layout**, the only restart in the sheet. The next action is **System: Reset global variables to default (include static: True)**.
5. **What the restart re-runs:** the `Game` layout restarts, so its start-of-layout events run again. These are events 2 (Setup), 13 (Camera), 45 (AI setup) and 78 (Tractor Smoke). The reset in event 108 puts the globals back to their defaults, for example `tutorial` back to true.

Where the restart is decided, the sheet does not guard against a second call. Event 103 has no "Trigger once" condition. The UFO path in event 91 has one (`System: Trigger once while true`), and the finish path does not. Two tractors touching the line in the same tick, or another tractor touching it during the 4-second wait, would call `showGameOver` again and run **Restart layout** again. This is inferred from the sheet and was not run in the editor.
