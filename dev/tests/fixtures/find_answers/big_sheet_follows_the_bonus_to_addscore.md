# Wave 17 bonus: answer and run log

## Answer

The wave 17 bonus is paid by **event 284** of the sheet **Waves**. It calls `GiveBonus(454)`, so the bonus is **454 points**.

Event 284 reads:

- Conditions: `wave = 17`, `spawnLeft = 0`, `Coin.Count = 0`, `Trigger once`
- Actions: `Functions: Call GiveBonus(454)`, then `System: Add 1 to wave`

`GiveBonus(points)` is defined at event 410 of the same sheet. It calls `AddScore(points)`, and `AddScore` on the Game sheet (event 7) adds `points` to `score` with no multiplier. So the 454 points reach the score unchanged.

No other event calls `GiveBonus` for wave 17. The 25 `GiveBonus` calls in Waves are one per wave, 1 to 24.

Evidence level: the event number and the amount come from reading the sheet with `print_sheet.py`, which the skill says prints the editor's numbers. I did not open the sheet in the Construct 3 editor, so the margin number is confirmed by the skill's numbering, not by a screenshot of the editor.
