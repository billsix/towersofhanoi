# Verify on a Mac that the wx window no longer jumps when a disc moves

**Status:** blocked
**Priority:** 8 (blocked)
**Difficulty:** 2
**Created:** 2026-11-21 (William Emerison Six <billsix@gmail.com>), from
`tasks/archive/2026/11/21/macos-board-jitter-and-drag-only-moves.md`.
**Blocked on:** a macOS session with the wx GUIs (no Mac in the sandbox).
**Recheck:** on the Mac, `cd python && make wx`, make several moves (drag and keyboard); "cleared" = the
board stays put. Repeat for `cd cpp && make wx` and `cd rust && make wx`.

## BLUF

The maintainer saw the window jump on macOS as a disc moved and the move buttons enabled/disabled. The
buttons were removed in every GUI (the archived task above), which removes the suspected cause. Check on
a Mac that the jump is gone; if not, chase the remaining leads below. Done = no jump in the three wx GUIs
on macOS, or a fix for what still causes it.

## Remaining leads (if it still jumps)

- `HanoiFrame._refresh` (`python/src/hanoigame/hanoigui.py`) ends with `self.panel.Layout()` and
  `self.Layout()` after every command; anything whose best size changes then moves the board.
- The history header (`_update_history`, `self._history_header.SetLabel(...)`, text grows with the move
  count) and the status-bar goal line: a `wx.StaticText` without `wx.ST_NO_AUTORESIZE` resizes on
  `SetLabel`, and Cocoa's native control follows its text closely. Fix: `ST_NO_AUTORESIZE` plus a fixed
  minimum width, in all three wx GUIs (`cpp/hanoiwx.cpp`, `rust/hanoi-gui/src/main.rs` build the same
  history panel in code).
