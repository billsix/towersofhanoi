# Inspectable running move tally (default 1-2-3 labels) — build in wxPython first, then spec it, then fan out

**Status:** implemented 2026-10-26 (William Emerison Six <billsix@gmail.com>) — Phase 1 (wx) + Phase 2
(spec) DONE; **awaiting the maintainer's on-display confirmation** of the wx dialog before archiving
(the code + logic are tested + gate-green; only the on-screen rendering needs a human look). Phase 3
(fan-out) split to its own task.
**Priority:** 4 **Difficulty:** 4
**Created:** 2026-10-25. Requested: "there should be a running tally that shows all moves done, relative
to the original labelling 1 2 3 … inspectable. add a task for the wxpython one … then extract out what
the markdown file that describes the product should say … then fan out to implement that across all UIs."

## BLUF

An inspectable running move tally — every move this game, in the default 1-2-3 (physical) labelling —
is implemented in the wxPython GUI (the oracle) and finalized into the product spec. Phase 1 (wx) and
Phase 2 (spec) are done; Phase 3 (fan-out to the other UIs) is now `tasks/fan-out-move-tally.md`.

## What was done (2026-10-26)

**Phase 1 — wxPython (the oracle).**
- `presenter.format_move_tally(moves)` — shared pure helper turning the recorded default-space move
  pairs into numbered ``"<n>. <from> -> <to>"`` lines (so the fan-out UIs render identically).
- `hanoigui.py` — a **View → Move history…** menu item (`Ctrl+H`) opens a **non-modal** dialog listing
  every move this game in default 1-2-3 labels with a **live count** header. Sourced from
  `recipe.Recorder.default_moves`; `_refresh` live-updates it; it **resets on New Game**.
- Tests: `test_presenter.py::test_format_move_tally_*`. Gate green (137 passed / 2 skipped; ruff + ty
  clean). The dialog's on-screen rendering is the maintainer's review item.

**Phase 2 — spec finalized from the impl.** `feature-spec.md` §4.11 rewritten PLANNED → the real
contract (numbered default-space list, live count, moves-only, on-demand-or-panel, reset-per-game, via
`format_move_tally`); §7 row 15 promoted to a real pass/fail.

**Phase 3 — fan-out** scoped as `tasks/fan-out-move-tally.md` (Python CLI/TUI, C++ ImGui/wx, Rust
CLI/TUI/wx/Tauri), proposed.

## Decisions / judgment calls (logged)

1. **Presentation (was open Q1) → on-demand non-modal dialog**, the maintainer's recommended option
   (consistent with the Show/Rebinding dialogs; no permanent layout cost). Made it live-updating while
   open, satisfying "inspectable at any time" + "live count".
2. **Built programmatically, NOT in the shared `ui/hanoi.xrc`** — the menu bar and the other dialogs
   come from that one XRC, which C++ and Rust also load; adding a tally menu item/dialog there would
   surface a dead control in those UIs during this oracle phase. Keeping it Python-only isolates the
   oracle change; the fan-out task finalizes the XRC form. (My call — the task didn't prescribe this.)
3. **Scope (was open Q2) → moves only, default space** (the maintainer's recommendation); relabels are
   not moves and are excluded (spec §4.11 says so).
4. **Reset (was open Q3) → per-game, resets on New Game** (recommended), which falls out for free: a new
   game builds a fresh `GameSession` with a fresh `Recorder`.

## Remaining to close this task

- **The maintainer's on-display check** that the wx dialog renders/updates correctly (`cd python &&
  make wx`, then View → Move history / Ctrl+H, make moves + New Game). Then archive.

## Related

- `tasks/fan-out-move-tally.md` — Phase 3 (the fan-out).
- `tasks/reference/feature-spec.md` §4.11 + §7 row 15 (the finalized contract).
- Oracle + data source: `python/src/hanoigame/{recipe.py (Recorder/default_moves),engine.py,hanoigui.py,
  presenter.py}`.
