# Drag and drop onto a bank box: official example, drop events, traps

## Answer

The closest official example is **Persistent inventory** (`persistent-inventory`, by Viridino Studios). Its `TrashBin` is a box at the bottom of the layout, and dropping an item on it destroys the item. That is the shape of "drop a coin on the bank". The other fit is **Place stickers** (`place-stickers`), which shows the snap-to-target half: a correct drop snaps the piece into its spot, and a wrong drop returns it.

Drop events in Persistent inventory, as the editor's margin numbers them (`print_sheet.py` output, group `DragAndDrop`):

- 11: `InventoryItem: On DragDrop drag start`. Stores the start position, sets Dragging, and calls *Move to top of layer*.
- 12: `InventoryItem: On DragDrop drop`. The parent of the drop branches, sub-events 13 to 19.
- 13: `InventoryItem: Is overlapping Slot`. Snaps the item to the slot and bounces it.
- 14 to 16: the item overlaps another item, so the one not being dragged goes back to the start position.
- 17: `System: Else`, then `InventoryItem: Is overlapping TrashBin`, then `InventoryItem: Destroy`. This is the bank branch to copy.
- 18: `System: Else`, then not overlapping a slot and not overlapping the TrashBin. The item returns to its start position.
- 19: sets Dragging to False and calls `UpdateStoredData`.

Drop events in Place stickers (`place-stickers`):

- 14: `Sticker: On DragDrop drag start`. Move to top of layer, then shrink the scale.
- 15: `Sticker: On DragDrop drop`. Picks the matching sticker inventory slot; the sub-events are 16 to 18.
- 16: `Sticker: Is overlapping StickerSpot`. Sets the position to the spot, disables DragDrop, and moves the sticker and background to the bottom.
- 17: the completion branch under 16, which runs when the count reaches 15.
- 18: `System: Else`. Disables DragDrop and tweens the sticker back to the inventory.

Evidence:

- Observed: the event numbers and structure above come from `print_sheet.py` on each example, which the skill says uses the editor's numbering.
- Observed: in `persistent-inventory`'s layout, `TrashBin` sits at y 143 to 167 on a 180-pixel-high layer `Store`, the lowest layer. Items are on layer `Inventory`, above it.
- Not verified: I did not open or preview either example in the editor, and I did not run the events. The numbers are from reading the sheets.

Why Persistent inventory: the drop target is a box at the bottom, the drop consumes the dragged instance, and the off-target case returns it. The bank needs the same three branches, with "add the coin value to the bank" before the destroy. Use Place stickers only if the coin should stay on the target.

## Traps to watch for in Construct drag and drop

Sources are the Cookbook pages named in brackets. Each is a runtime behavior; the list is not exhaustive.

1. **Layer and Z order hide the target.** A layout draws the instances on one layer in the order the layout lists them. A coin listed before the bank is drawn under the bank and vanishes when it snaps or drops. Put the coins on a layer above the bank, list them after it, or run *Move to top of layer* in *On drag start*. Seven of the ten official examples that test a drag against a target raise the piece at runtime. [primitives/layers.md:43]
2. **Drag & Drop grabs the front instance, ignoring visibility.** It picks the highest layer, then the highest Z order, among instances whose behavior is enabled and whose layer is interactive. A hidden coin can still be dragged, and a popup without the behavior does not block drags underneath it. To stop drags while a popup shows, turn the coins' layer non-interactive or disable the behavior. [behaviors/dragndrop.md:28]
3. **The drop test uses the dragged coin's box, not the pointer.** Overlap tests use the dragged instance, and the drop position is the pointer minus the grab offset. A coin that is partly over the bank can miss the test if its own box does not cover the bank. [behaviors/dragndrop.md:17]
4. **Drag moves only when the pointer moves.** A *Set position* on the dragged coin lasts only until the next pointer move. If the coin should lift above the finger, put that visual on a child instance and position the child from events. [behaviors/dragndrop.md:17]
5. **A slot reads empty while its instance is dragged or flying back.** A dragged or tweening instance with collisions disabled counts as absent to overlap tests. An event that fills empty slots, such as a spawn, then creates an instance under a returning coin. Make such an event wait while a drag or a landing tween runs. [behaviors/dragndrop.md:6]
6. **Drop onto another coin needs its own branch.** Persistent inventory's events 14 to 16 move the non-dragged item back when two items overlap. For the bank, decide what happens when a coin lands on a coin that is already placed. [observed in `persistent-inventory`, event 14 to 16]
7. **Touch and mouse differ.** The Mouse object ignores fingers. If touch matters, test *Mouse button is down* every tick under *Is dragging*, not in *On drag start*. The order of the two triggers is not documented. [plugins/touch.md:32]
8. **Keep the bank on screen at the bottom.** A bank at the bottom edge moves off screen on other aspect ratios unless it is pinned with Anchor. A bank off screen cannot receive a drop. [pitfalls index, layout and scaling entry]
9. **Look up the Pick children behavior before you use child objects.** If a coin's art is a child in the coin's container, *Pick children* can find nothing in a drop event. Give the child its own family. [plugins/_common.md:6]
