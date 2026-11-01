# Port drag-and-drop discs to the other graphical front-ends

**Status:** IN PROGRESS (branch `drag-drop-fanout`; gpg off → restored). All five graphical
front-ends now carry the drag gesture. **C++ ImGui on-display-verified by the maintainer**; the other
four (egui, C++ wx, Rust wxDragon, Tauri) are compile- and headless-smoke-verified (Tauri via the deno
type-check) and **await the maintainer's on-display sign-off** per UI.
**Priority:** 3
**Difficulty:** 6

## BLUF

Replicate the approved wxPython drag-and-drop interaction — **drag a peg's top disc and drop it onto
another peg**, nearest-peg targeting, illegal drop snaps back with the usual reason, dragging off once
won, **move buttons kept** — in every other graphical front-end, each dispatched through that UI's own
shared core. Done = each graphical UI supports disc drag-drop + keeps its buttons, with its
subproject gates green and an on-display check. One umbrella because the interaction design is
identical across all five; only the toolkit's hit-testing/drawing differs (each target is its own
commit boundary and can spin into its own task if it turns out large).

## Context (cold-start orientation)

- **The reference implementation (approved):** `python/src/hanoigame/board_renderers.py`
  `GraphicsBoardRenderer` (mouse capture + geometry captured each paint + nearest-peg hit-test + the
  dragged disc follows the cursor and is omitted from its stack; `set_move_callback`/`set_interactive`)
  and `python/src/hanoigame/hanoigui.py` `_on_board_drop` (physical pegs → current labels → the shared
  `_on_move`). Archived spike: `tasks/archive/2026/10/31/wxpython-drag-drop-disks-spike.md`.
- **Dispatch stays in the core.** A drop resolves to a `<from-peg> → <to-peg>` move dispatched through
  the same engine every front-end already uses; the UI only adds the gesture. Moves are in the current
  labelling, so each UI maps the physical pegs dragged-between back to labelled pegs, exactly as the
  oracle does.
- **Decisions carried from the spike (don't re-litigate):** nearest-peg drop (forgiving); keep drag
  **and** buttons (buttons are the accessible/keyboard path); disable dragging once the game is won.

## Targets (each its own commit; check off as done)

- [x] **C++ Dear ImGui** — `cpp/main.cpp` `draw_board`. An invisible button over the board owns the
  gesture (`IsItemActivated`/`IsItemActive`/`IsItemDeactivated` + `GetMousePos`); press picks up the
  top disc of the nearest peg, the disc follows the cursor (omitted from its stack), release drops on
  the nearest peg. Drop + buttons share a new `do_board_move`. Native + wasm compile; on-display-verified.
- [x] **C++ wxWidgets** — `cpp/hanoiwx.cpp`. `BoardView` captures the mouse (EVT_LEFT_DOWN/MOTION/
  LEFT_UP/CAPTURE_LOST), caches peg centres each paint for hit-testing, draws the dragged disc via
  `wxGraphicsContext`; `on_board_drop` validates (a drop can be illegal, unlike a button) then calls
  `on_move`. Shares `ui/hanoi.xrc`. Compile + headless smoke; **on-display pending**.
- [x] **Rust wxDragon** — `rust/hanoi-gui/src/main.rs`. Plain-DC drag: `on_mouse_left_down/motion/
  left_up` matched on `WindowEventData`, a shared `board_peg_centres`/`nearest_board_peg` hit-test,
  the dragged disc drawn with the DC; drop → `on_move` (validating). **No mouse capture** — wxDragon
  exposes no capture-lost handler, and the board panel fills the drag area. Compile + smoke; **on-display pending**.
- [x] **Rust egui** — `rust/hanoi-egui/src/main.rs`. `Sense::click_and_drag()` on the board painter;
  `drag_started/dragged/drag_stopped` + `interact_pointer_pos`; a shared `board_geometry` for drawing
  and hit-test. Compile + smoke; **on-display pending**.
- [x] **Rust Tauri** — `rust/tauri/frontend/main.js`. Canvas pointer events (`pointerdown/move/up/
  cancel`) with `setPointerCapture`; nearest-peg hit-test; the resolved move crosses the existing
  `do_move` IPC command (which validates), so the rule stays in Rust. deno type-check; **on-display pending**.

## Plan (per target, refine on go-ahead)

1. Add the gesture in that UI's board drawing/input, mapping press→top-disc and release→nearest peg.
2. Resolve the drop to a labelled move and dispatch through the existing core; **legal** → board
   updates + history records; **illegal** → snap back + the distinct rejection reason (forgiveness).
3. Keep the move buttons; disable dragging when won.
4. Verify that subproject's gates (`make format`/`check`/`type-check`/`test` as applicable) + an
   on-display run; tick the box.

## Related

- `tasks/archive/2026/10/31/wxpython-drag-drop-disks-spike.md` — the approved oracle this mirrors;
  `python/tools/gui_smoke.py` — the headless GUI smoke harness (pattern for a per-UI smoke).
- `tasks/fan-out-ui-learning-flow.md` — do each UI's drag-drop with its tier redesign (shared files).
- `tasks/reference/ui-design-principles.md` (direct manipulation, forgiveness),
  `tasks/reference/feature-spec.md` §4.2 (move + rejection reasons), §6.2 (GUI button guidance),
  `tasks/reference/imgui-cpp-native-and-wasm.md` (C++ build/run + wasm).
