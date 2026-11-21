# Drag-only moves (no move buttons) and the macOS window jump (done 2026-11-21)

**Priority:** 3 **Difficulty:** 5
**Created / done:** 2026-11-21 (William Emerison Six <billsix@gmail.com>); branch `hanoi-gl-imgui-parity`.

## What was done

**The move buttons are gone from all seven graphical UIs** (Python wx, C++ wx, Rust wxDragon, C++ ImGui,
Rust egui, Rust Tauri, Python `hanoi-gl`). Moves are made by dragging a disc, or by the **keyboard
move**: type the from-peg number, then the to-peg number; Esc cancels; the same number twice cancels.
A hint line where the buttons were says how to move and shows a pending from-peg. A keyboard move goes
through the same checked dispatch path as a drop, so an illegal pair pops up its reason. Decisions
(William Emerison Six <billsix@gmail.com>, 2026-11-21, "go with your recommendations"): remove the
buttons in every GUI, keep a keyboard path for accessibility, and do it independently of part 1.

- Shared XRC (`ui/hanoi.xrc`): the Move box with six buttons became one `move_hint` static text
  (`wxST_NO_AUTORESIZE`). The three wx GUIs read it and bind a frame-level char hook
  (`EVT_CHAR_HOOK` / `wxEVT_CHAR_HOOK` / wxDragon `on_char_hook`), so the keys reach the frame before
  any child control. In C++ wx the keyboard move calls `on_board_drop` (physical pegs), because
  `on_move` there assumes a legal move.
- ImGui (C++ and `hanoi-gl`) read `ImGui::IsKeyPressed` / `imgui.is_key_pressed` (digits and keypad)
  when imgui does not want the keyboard and no popup is open; egui reads `ctx.input` unless a widget
  wants the keyboard; Tauri adds a `keydown` listener that ignores fields and dialogs.
- `tasks/reference/ui-design-principles.md` ruling 7 and its "dim, don't remove" note, and
  `tasks/reference/feature-spec.md` §6.2, §4.11 and the compliance notes describe the keyboard move.

**The macOS jump (part 1) could not be reproduced:** there is no Mac in the sandbox. The maintainer saw it
in the wx GUIs as a disc moved and the move buttons enabled/disabled; that per-move `Enable` loop (and the
re-layout after it) no longer exists, since the buttons are gone, and the hint that replaced them is a
fixed-size static text. Whether the jump is gone on a real Mac is tracked in
`tasks/verify-macos-board-jump-gone.md` (blocked on a Mac session), which also lists the remaining leads
(the history header and goal-line labels resizing on `SetLabel`).

## Verification

- Python: `format`, `type-check`, `test` (153 passed, 2 skipped); `python/tools/gui_smoke.py` drives the
  keyboard move (pending from-peg, Esc, a move through `_on_move`) and passes; `python/tools/gl_smoke.py`
  passes.
- C++: clang-format clean; native build (both GUIs) with no warnings; ctest green; the WebAssembly
  Release build compiles.
- Rust: `format`, `check --workspace --all-targets`, `test --workspace`, the egui and Tauri `cargo
  check`s and the Deno type-check gate green.
- Not checked: the keyboard move on a real display in each toolkit (focus quirks), and anything on macOS.
