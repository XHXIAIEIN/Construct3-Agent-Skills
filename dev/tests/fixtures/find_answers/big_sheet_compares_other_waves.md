# Wave 17 bonus: answer

**Event 284** of the event sheet `Waves` (sheet file `eventSheets/Waves.json`) pays the wave 17 bonus. It calls `GiveBonus` with **454** points, and `GiveBonus` passes that value to `AddScore`, which adds it to `score` without a multiplier.

Caveat: no layout runs `Waves`, and no sheet includes it. The sheet's triggers therefore do not fire in the game as the project stands, so event 284 does not pay out in play until `Waves` is run by a layout or included by `Game`.

## Evidence

- Observation: `print_sheet.py Waves --find GiveBonus` lists event 284 under `group Wave 17` with the action `Functions: Call GiveBonus(454)`, after the conditions `wave = 17`, `spawnLeft = 0`, `Coin.Count = 0` and `Trigger once`.
- Observation: `eventSheets/Waves.json` holds the same call as `"callFunction": "GiveBonus"` with the parameter `"454"`.
- Observation: `GiveBonus(points)` in event 410 calls `AddScore(points)`. `AddScore` in the `Game` sheet (event 7) runs `Add points to score`. No multiplier appears on this path.
- Observation: `--map` reports `Waves: no layout runs it` and lists no sheet that includes it. `Game` has no include entry, and no layout file refers to `Waves`.
- Derivation: the margin number is the number `print_sheet.py` prints, which the skill names as the editor's numbering.
- Unknown: whether the project is meant to run `Waves` in a future layout. The file alone does not show that.

Other wave bonuses for comparison: every wave's bonus sits at event 12 + 17 * (wave - 1), so wave 16 is event 267 (427 points) and wave 18 is event 301 (460 points).
