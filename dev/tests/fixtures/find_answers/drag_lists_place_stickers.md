# Drag and drop onto a bank box: official example and traps

## What changed

Nothing in the project. I only read files and ran read-only scripts. The project folder was not edited, and no commit was made.

## Answer

The official example that drags a piece onto a target is **Place stickers** (`place-stickers`, in the Construct-Example-Projects clone). Its drop logic is in the **Drag and Drop** group of its event sheet `Game`. The editor margin numbers that handle the drop are:

- **15**: `Sticker: On DragDrop drop`. This is the entry point for every drop.
- **16**: `Sticker: Is overlapping StickerSpot`. This is the test for a correct drop. Its sub-event **17** runs the completion check (`stickersPlaced = 15`) when the last piece lands.
- **18**: `System: Else`. This is the wrong-spot branch. It disables DragDrop and tweens the piece back to the inventory.

Supporting events in the same example:

- **14**: `Sticker: On DragDrop drag start`. It moves the piece to the top of its layer and shrinks it back to normal size.
- **12**: enables the DragDrop behaviour after the tutorial fades.
- **5-9**: set up the group and create the first stickers.

For a coin and a bank box, the same shape applies: on drop, test `Coin: Is overlapping Bank`. On true, add to the coin total and destroy the coin. On else, tween the coin back to its start position. Note that the example disables DragDrop on a placed piece (event 16). A banked coin is destroyed, so this step is not needed there.

## Traps to watch for

1. **Layer order.** A layout draws instances in the order they are listed, so a coin listed before the bank is drawn under it. The coin then vanishes when it snaps into the box. Put the coins on a higher layer, or raise the coin with *Move to top of layer* on drag start, as event 14 does. Seven of the ten official examples that test a dragged object against a target do this. `check_project.py` warns on this case. Source: `Construct3-Cookbook/guides/primitives/layers.md`, line 43.
2. **Which instance is dragged.** Drag & Drop starts on the front instance under the pointer. It ignores visibility, so a hidden coin can still be dragged. A popup without DragDrop does not block the drag. To stop drags during a popup, turn off the coins' layer with *Set layer interactive*, or disable the behaviour with *Set enabled*. Source: `Construct3-Cookbook/guides/behaviors/dragndrop.md`, line 28.
3. **Position is overwritten on every move.** Drag & Drop writes the position only when the pointer moves. A *Set position* on the dragged coin holds only until the next move. If the coin's look must lift above the finger, put the look on a child object and position that child with events. Source: `dragndrop.md`, line 17.
4. **Spawns into a slot that is landing.** While a dragged or tweening instance has collisions disabled, its target slot reads as empty. A bank event that spawns a coin there can put a new coin under the returning one. Make such an event wait while any coin is dragged or a landing tween plays. Source: `dragndrop.md`, line 6.
5. **Mouse and touch differ.** The Mouse object ignores a finger, except *On movement*. Drag & Drop accepts both. If a coin must lift higher under a finger, test `Mouse: Mouse button is down (left)` every tick during *Is dragging*. Source: `Construct3-Cookbook/guides/plugins/touch.md`, line 32.
6. **Always handle the miss.** *On DragDrop drop* fires for every drop, not only the good ones. Put the overlap test in it and an *Else* branch that returns the piece, as event 18 does.
