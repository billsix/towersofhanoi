# Spike: drag-and-drop disks in the wxPython GUI (replace move buttons)

**Status:** spike IMPLEMENTED 2026-10-31 (branch `ui-learning-flow-and-fixes`) — awaiting the
maintainer's on-display evaluation ("do I like it?"). NOT archived until that call; the
port-to-other-UIs follow-ups are filed only if approved.
**Priority:** 3
**Difficulty:** 6

## Work record (spike implemented 2026-10-31)

- **What was built:** in `python/src/hanoigame/board_renderers.py`, `GraphicsBoardRenderer` now
  supports mouse pick-up/drag/drop of a peg's top disc — mouse capture + hit-testing (nearest peg,
  the decided forgiving targeting), geometry captured each paint, the dragged disc follows the cursor
  and is omitted from its stack, and a `set_move_callback` / `set_interactive` API. `hanoigui.py`
  wires the drop callback (`_on_board_drop`: physical pegs → current labels → the existing `_on_move`,
  so an illegal drop snaps back with the usual reason and a drop under a relabelling shows the
  single-move rebinding) and disables dragging once the game is won. **Both** the move buttons and
  dragging are active (the decided spike choice; whether to drop the buttons is the post-eval call).
- **Verification:** `cd python && make format` / `type-check` / `test` green (130 passed / 2 skipped);
  a headless Xvfb smoke (`tasks/adhoc/drag-drop-spike/gui_smoke.py`) drives a board drop → engine
  dispatch and a drop-to-win. The *feel* of dragging can only be judged on a real display.
- **How to evaluate (maintainer):** `cd python && make wx`, then drag a top disc from one peg onto
  another (graphics board; the default). Compare against the move buttons. Decide: keep drag + buttons,
  drag-only, or revert. The headless smoke is at `tasks/adhoc/drag-drop-spike/gui_smoke.py`.
- **Recommendation:** keep drag **and** buttons. Dragging is the stronger direct-manipulation teaching
  gesture (Apple-HIG), but the buttons are the accessible/keyboard path and feature-spec §6.2's
  "disable illegal ones" affordance; dropping them is a separate accessibility decision.
- **If approved → follow-ups to file:** port drag-drop to C++ ImGui, C++ wx, Rust wx, Rust egui, Rust
  Tauri (one per graphical UI), cross-linked with `tasks/fan-out-ui-learning-flow.md`.

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
