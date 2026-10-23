# Drag and drop onto a bank box: the official example and its traps

## What changed

Nothing in the project. No project file was edited, no `git init`, no commit. The only files written are in the outputs folder: `answer.md` and `checker_stdout.txt` (the checker's full output).

## The example

**Persistent inventory** (`persistent-inventory`), at <path>

Its trash bin (`TrashBin`, layer Store, x 158..182, y 143..167 of a 320 x 180 layout) sits at the bottom of the screen. Dropping an item onto it destroys the item. That is the nearest official match to "drop a coin onto a box at the bottom to bank it": keep the same shape and replace *Destroy* with a score add.

Runner-up: **Place stickers** (`place-stickers`). Its drop tests a matching target slot and returns the sticker when the slot is wrong (events 14 to 18).

### How persistent-inventory handles the drop

Numbers are the editor's margin numbers, from `print_sheet.py`:

- **11** `InventoryItem: On DragDrop drag start`: stores the start X and Y, sets Dragging to True, and runs *Move to top of layer*.
- **12** `InventoryItem: On DragDrop drop` with sub-events **13 to 19**. This is the drop trigger.
  - **13** `Is overlapping Slot`: snaps the item to the slot. Sub-events 14 to 16 swap out an item that already sits there.
  - **17** `Else`, `Is overlapping TrashBin`: *Destroy*. This is the bank branch to copy.
  - **18** `Else`, not overlapping a slot and not overlapping the bin: moves the item back to its start position with a bounce.
  - **19** (runs with its parent): Dragging to False, then save the data.

The label reads "DragDrop" because the behavior instance in that project is named DragDrop. The ACE is *On drop* of the Drag & Drop behavior.

## Traps for the coin game

Each trap is checked against the Cookbook pages named in brackets. Items 1 and 2 concern your current sheet.

1. **Your current tap event fights the drag.** Event **5** in your Game sheet, `Touch: On touched Coin (start)` then `Coin: Collect()`, fires on the press. A press meant to drag a coin therefore scores it before it moves. The official examples collect on *Touch: On tap gesture* instead (place-stickers, event 11). Change event 5 to a tap gesture, or remove it, before you add the drag. [plugins/touch.md]
2. **Layer order hides a coin dropped on the bank.** The Game layout draws Background, then Game, then UI, from bottom to top. Your coins are created on Game. If the bank sits on UI, a coin dragged over it is drawn under it. *Move to top of layer* reorders only inside one layer, so it does not fix this. Put the coins on a layer above the bank, or put the bank on a layer below the coins. [primitives/layers.md; pitfalls.md, Layers]
3. **Drag & Drop picks the front instance, not the visible one.** It picks the highest layer first, then the highest Z. It ignores visibility, so a hidden coin can still be dragged. A popup without the behavior does not block drags beneath it. To stop drags while a popup shows, turn the coins' layer off with *Set layer interactive*, or the behavior off with *Set enabled*. [behaviors/dragndrop.md]
4. **A position set on the dragged coin is overwritten by the next pointer move.** Drag & Drop moves the instance only when the pointer moves. If the coin must lift or trail the finger, put that look on a child that the events position. [behaviors/dragndrop.md]
5. **The slot a coin came from reads as empty while the coin is out of it.** A coin with collisions disabled fails every overlap test in both directions. If you return a coin with a tween, an event that spawns coins into empty spots can land on it. Make such an event wait while any coin is dragged or any landing tween plays. [behaviors/dragndrop.md; plugins/sprite.md]
6. **A drop on empty space needs an Else branch.** *On drop* fires on every release. Without an Else that returns the coin, a coin released in the open stays where the finger let go. Persistent-inventory uses events 17 and 18 for this. [behaviors/dragndrop.md; project example]
7. **Use the trigger's pick.** Inside *On drop*, the dropped coin is the trigger's pick. Test `Is overlapping Bank` on that pick, not on *Pick all Coin*, which tests every coin on the layout. [design/thinking.md, item 3]
8. **Pick children finds nothing if the child type sits in the parent's container.** This applies only if coins have child sprites (for example a face). Give the child type a family of its own and pick children of the family. [plugins/_common.md]
9. **Mouse and finger differ.** Drag & Drop takes a mouse and a finger alike. The Mouse object ignores fingers. A *Touch: On touched* event fires for both, so it collides with the drag in trap 1. [plugins/touch.md]
