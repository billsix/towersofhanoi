# Click a move in the history to review the board as it was then (done 2026-11-21)

**Priority:** 4 **Difficulty:** 6
**Created / done:** 2026-11-21 (William Emerison Six <billsix@gmail.com>); branch `gui-batch-2026-11-21`.

## What was done

In every graphical UI, clicking (or arrowing to) move *k* in the always-visible move history shows the
board as it stood after move *k*, so a student can step back through a solve. While reviewing, the move
buttons and dragging follow the reviewed board; "Back to current" (or selecting the last move) returns
to the live game. A move or recipe apply made while reviewing asks "Continue from move *k*? This deletes
moves *k+1*…*n*.": yes truncates the game to *k* moves and makes the move, no stays in review. The
behaviour is in `tasks/reference/feature-spec.md` §4.11 ("Review a past move") and compliance row 21.

Decisions (William Emerison Six <billsix@gmail.com>, 2026-11-21, "go with your recommendations"): ask
rather than block; truncating a won game is allowed (it un-wins it and disables Save until the next win;
the saved/replayed-win flags reset); past states are shown under the current labelling, so the history
model is unchanged; no text-UI command in this task.

### Shared core (one rule, every UI)

- Python: `recipe.replay_default_moves(num_disks, moves)` (replays default-space moves on a fresh game,
  raising `ValueError` on an illegal one), `Recorder.truncate(count)`, and
  `GameSession.state_after(count)` / `GameSession.truncate_to(count)` in `engine.py`, each with doctests.
- Rust (`rust/hanoigame/`): `recipe::replay_default_moves` (returns the `MoveError`), `Recorder::truncate`,
  `GameSession::state_after` / `truncate_to`, with doctests.
- C++ (`cpp/src/recipe.hpp`): `replay_default_moves` (an empty `std::optional` on an illegal move) and
  `Recorder::truncate`, with doctest cases.

### Per UI

- **Python wx** (`hanoigui.py`): `_review_count`, `_on_history_select`, `_on_history_back`,
  `_confirm_leave_review` (a Yes/No `wx.MessageDialog`, so the board takes nothing else until answered),
  `_shown_game`; `_refresh` draws and enables from the shown game; `_update_history` keeps the reviewed row
  selected and enables "Back to current".
- **C++ wx** (`hanoiwx.cpp`): the same shape (`on_history_select`, `confirm_leave_review`, `shown_game`).
- **Rust wxDragon** (`hanoi-gui`): the same shape with `MessageDialog` Yes/No.
- **C++ ImGui** and **Rust egui**: no blocking dialog in an immediate-mode loop, so the move or apply is
  held (`pending_*` / `PendingAction`) and a "Continue from here?" modal/window asks; dragging and the
  move buttons are off while it is open. History rows are `Selectable`/`selectable_label`.
- **Rust Tauri**: the backend holds `review` and adds `review_move`, `review_back` and
  `continue_from_review` commands; the snapshot's `board`/`towers`/`legal` describe the shown board, with
  `won` (live) and `board_won` (shown) kept apart so the win celebration doesn't refire. The frontend's
  history items are clickable and the question is an HTML `<dialog>`.

## Verification

- Python: `format`, `type-check`, `test` (140 passed, 2 skipped) green; `python/tools/gui_smoke.py` now
  also drives review → "no" (game unchanged) → "yes" (truncated, new move made); prints `SMOKE OK 2`.
- C++: format clean; full native build with no warnings; doctest 20/20 cases.
- Rust: `format`, `check --workspace --all-targets`, `test --workspace`, the egui and Tauri `cargo check`s,
  and the Deno type-check gate green.
- Not checked: the feel on a real display (all six UIs). That is the maintainer's on-display check.

## Follow-up (not filed)

A text-UI `history <k>` command (print the board after move *k*) was left out by decision; file it if
wanted.
