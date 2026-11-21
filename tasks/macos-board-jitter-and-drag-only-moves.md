# macOS: the window seems to resize on a move — find why; then consider drag-only moves (drop the buttons)

**Status:** proposed — needs go-ahead (decisions recorded 2026-11-21; no open questions)
**Priority:** 3
**Difficulty:** 5 (part 1 is an investigation on a real Mac; part 2 is a fan-out across five GUIs)
**Created:** 2026-11-21 (William Emerison Six <billsix@gmail.com>)

## BLUF

On macOS, moving a disc makes the window look like it **resizes or jumps**. The maintainer suspects
it is tied to the **move buttons**, and is not sure whether a drag or a button click causes it.
Part 1 finds the cause and fixes it. Part 2 **removes the move buttons** and keeps drag-and-drop as
the only way to move, if that is feasible, in every graphical UI. Done = no visible jump on a move on
macOS, and the button decision has been made and applied to every GUI.

## Context

- Read first: `CLAUDE.md`, `tasks/reference/ui-design-principles.md` ruling #7 ("Direct
  manipulation: drag a disc, and **keep the buttons**"), `tasks/reference/feature-spec.md` §6.2
  ("show all move buttons and **disable** the illegal ones rather than hiding them, so controls
  don't jump") and compliance row 17-ish (drag-drop), the drag spike
  `tasks/archive/2026/10/31/wxpython-drag-drop-disks-spike.md`, and its fan-out
  `tasks/archive/2026/11/01/port-drag-drop-to-graphical-uis.md`.
- **Part 2 reverses a recorded decision.** Ruling #7 keeps the buttons as the keyboard /
  accessible path. Dropping them needs a replacement for keyboard-only players (see Open
  question 2), and the ruling, feature spec and compliance checklist must be updated with it.
- The graphical UIs: Python wx (`python/src/hanoigame/hanoigui.py` + `board_renderers.py`, the
  oracle), C++ ImGui (`cpp/main.cpp`), C++ wx (`cpp/hanoiwx.cpp`), Rust wxDragon
  (`rust/hanoi-gui/src/main.rs`), Rust egui (`rust/hanoi-egui/src/main.rs`), Rust Tauri
  (`rust/tauri/frontend/main.js`). The three wx GUIs share `ui/hanoi.xrc` (byte-identical copy at
  `python/src/hanoigame/hanoi.xrc`).

## Part 1 — leads for the macOS jump (unverified; reproduce first)

The maintainer saw it in the wx GUIs (Decisions); it happens as a disc is moved and the move buttons enable/disable (see Decisions). Leads in the wx oracle, read
2026-11-21:

- `HanoiFrame._refresh` (`hanoigui.py`) runs after **every** command and ends with
  `self.panel.Layout()` and `self.Layout()`. Anything in it whose best size changes on a move makes
  the sizers re-place everything, and the board moves.
- Candidates whose size changes per move: the history header (`self._history_header.SetLabel(...)`
  in `_update_history`, whose text grows with the move count), the goal line (`_update_goal`), and
  the history `wx.ListBox` gaining a row. A `wx.StaticText` without `wx.ST_NO_AUTORESIZE` resizes
  itself on `SetLabel`, and on macOS (Cocoa) the native control's best size follows its text
  closely, so a sizer slot that is fixed on GTK can change width there.
- The move buttons: `btn.Enable(...)` per move. On Cocoa, a disabled `NSButton` is not expected to
  change size, but check it, since the maintainer suspects the buttons.

Method: reproduce on the Mac (`cd python && make wx`, or the UI the maintainer names), then remove
one candidate at a time (fix a label's width, drop the `Layout()` calls) until the jump stops.
Compare with the same build on Linux to confirm it is macOS-only. Apply the same fix to the other
UIs that show the same symptom.

## Part 2 — drag-only moves (if approved)

1. Remove the move-button row from every GUI (in the shared XRC for the three wx ones).
2. Add the keyboard move (Decisions).
3. Update ruling #7, feature-spec §6.2, and the compliance checklist; run each subproject's gate
   (`make format` / `type-check` / `test`), and `python/tools/gui_smoke.py` for the oracle.

## Decisions (William Emerison Six <billsix@gmail.com>, 2026-11-21: "go with your recommendations")

- **The jump was seen in the wx GUIs** (Python wx, C++ wx, Rust wxDragon, which share `ui/hanoi.xrc`). Part 1 starts in the Python wx oracle and the fix goes to all three; the shared layout makes a common cause likely.
- **Keyboard path after the buttons go:** a keyboard move: press the from-peg number, then the to-peg number (Esc cancels). It keeps the accessibility reason behind ruling #7; update the ruling to say so.
- **Part 2 is independent of part 1:** remove the buttons even if they turn out to cause the jump.

- **When it happens** (William Emerison Six <billsix@gmail.com>, 2026-11-21): "when the disk got moved and the buttons got highlighted or turned off, I think." So start with the move buttons: the `btn.Enable(...)` loop in `_refresh` and the `self.panel.Layout()` / `self.Layout()` right after it. On Cocoa, check whether a button's best size or focus ring changes when it is disabled or re-enabled (a focused button that gets disabled moves focus, and the default/highlighted button style can change its size), and whether that re-layout shifts the board. The label-width leads are second.
