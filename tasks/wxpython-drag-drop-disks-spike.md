# Spike: drag-and-drop disks in the wxPython GUI (replace move buttons)

**Status:** proposed — investigation/spike; needs go-ahead to start.
**Priority:** 3
**Difficulty:** 6

## BLUF

Investigate whether the wxPython GUI can let the user **drag a peg's top disk and drop it onto another
peg** — direct manipulation — in place of the move buttons. Build a working spike in wxPython only. If
it works and the maintainer likes it, **then** file follow-up tasks to port the interaction to the
other graphical UIs (C++ ImGui, C++ wx, Rust wx/egui/tauri). Done (for this task) = a runnable
wxPython spike + a recommendation (keep / drop / keep-both-with-buttons), not a fleet change.

## Context (cold-start orientation)

- **Why this is appealing:** drag-and-drop is the purest form of Apple-HIG **direct manipulation** —
  the learner acts on the real object (the disk) rather than on an abstract control. It fits the
  learner-journey redesign in `tasks/ui-learning-flow-spec-and-wxpython.md` (move interaction is
  Tier 1). Decide the two together: if drag-drop wins, the Tier-1 "make a move" affordance becomes the
  board itself, not a button row.
- **Where it lives:** `python/src/hanoigame/hanoigui.py` + `board_renderers.py` (the 2D-graphics board
  uses `wx.GraphicsContext`; the wx GUI also has a text board). Drag-drop requires the **2D-graphics
  board** with hit-testing — a text board can't be dragged, so the spike targets the graphics board.
- **The move still goes through the shared core:** a drop resolves to a `<from-peg> -> <to-peg>` move
  dispatched via `engine.dispatch` / `commands.parse` exactly as a button does (keep front-ends thin,
  per the repo CLAUDE.md). Moves are in the current labelling; the drop must map the physical pegs the
  user dragged between back to labelled pegs for dispatch.

## Plan (the spike)

1. **Hit-testing:** on mouse-down, identify whether the cursor is over the **top disk** of a peg
   (only the top disk is movable); on drag, render the disk following the cursor; on mouse-up,
   identify the **target peg** under the cursor.
2. **Dispatch + feedback:** resolve drop → move, dispatch through the engine. **Legal:** the board
   updates and the move is recorded (feeds the always-visible move history). **Illegal:** the disk
   **snaps back** and the usual distinct rejection reason is shown (range / same peg / empty /
   larger-on-smaller — §4.2) — snap-back + reason is the *forgiveness* principle made visible.
3. **Compare** against the move-button interaction and write the recommendation.

## Decisions (maintainer, 2026-10-31)

- **Keep both during the spike:** drag-and-drop **plus** the existing move buttons, so the two
  interactions can be compared fairly; whether to drop the buttons is decided after. (The feature-spec
  §6.2 "show all move buttons and disable the illegal ones" guidance stays until that decision.)

## Open questions (answer by number)

1. **Drop precision:** must the disk be dropped within a peg's column, or is "nearest peg to the drop
   point" close enough? (Rec: nearest-peg — more forgiving.)

## Related

- `tasks/ui-learning-flow-spec-and-wxpython.md` — the Tier-1 move interaction this would replace;
  decide jointly.
- `tasks/reference/ui-design-principles.md` (direct manipulation, forgiveness),
  `tasks/reference/feature-spec.md` §4.2 (move + rejection reasons), §6.2 (GUI button guidance).
- **Follow-ups to file only if the maintainer likes the spike:** port drag-drop to C++ ImGui, C++ wx,
  Rust wx, Rust egui, Rust tauri (one per graphical UI).
