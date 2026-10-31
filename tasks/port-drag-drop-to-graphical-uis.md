# Port drag-and-drop discs to the other graphical front-ends

**Status:** proposed — needs go-ahead (the wxPython spike is approved; this carries it to the rest).
Do each UI **together with** its learning-flow fan-out (`tasks/fan-out-ui-learning-flow.md`) — same
files, same "Tier-1 move affordance" decision.
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

- [ ] **C++ Dear ImGui** — `cpp/main.cpp` `draw_board`. Immediate-mode: track the drag across frames
  (mouse down/pos/released), hit-test the top disc on press, draw the dragged disc at the cursor, and
  on release pick the nearest peg reusing the existing peg-centre math. **Native + wasm share the code**
  — verify wasm pointer coords line up (the canvas-size sync in `main_loop`). Read
  `tasks/reference/imgui-cpp-native-and-wasm.md` first.
- [ ] **C++ wxWidgets** — `cpp/hanoiwx.cpp`. Retained-mode wx like the Python oracle: mouse capture on
  the board panel + `wxGraphicsContext` hit-test/draw. Shares `ui/hanoi.xrc`.
- [ ] **Rust wxDragon** — `rust/hanoi-gui/src/main.rs` (the Rust port of the wxPython GUI). **Constraint:
  wxDragon draws with a plain DC, not `wxGraphicsContext`** — render the dragged disc with the DC; wire
  mouse events through the wxDragon bindings. Shares `ui/hanoi.xrc`.
- [ ] **Rust egui** — `rust/hanoi-egui/src/main.rs`. Immediate-mode like ImGui: use the board
  `Response` drag state + pointer position (`interact`/`dragged`/`hover_pos`). Native + web.
- [ ] **Rust Tauri** — `rust/tauri` (web frontend over the Rust core). Pointer events / HTML5 drag on
  the board canvas/DOM in the frontend; the resolved move crosses the `#[tauri::command]` IPC boundary
  to the core. The thinnest layer — the gesture is JS/DOM, the rule stays in Rust.

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
