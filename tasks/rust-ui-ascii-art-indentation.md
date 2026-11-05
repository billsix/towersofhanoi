# Investigate the ASCII-art indentation problems in the Rust UIs

**Status:** proposed — needs go-ahead
**Priority:** 5
**Difficulty:** 3
**Created:** 2026-11-05 (William Emerison Six <billsix@gmail.com>)

## BLUF

The maintainer sees indentation problems in the ASCII art (the text board, and possibly the recipe and
rebinding tables) in the Rust wx GUI, and maybe the other Rust UIs. Find each place where it breaks, find
the cause, and fix it so every Rust UI lines up the same way the Python wx GUI (the oracle) does. Done
means a screenshot of each Rust UI's text views lines up column-for-column with the Python wx GUI.

## Context (read first)

- `tasks/reference/feature-spec.md` §4.3 (board label rows) and §4.8 (the three-panel rebinding table)
  say what the text views show. `python/src/hanoigame/presenter.py` `render` and
  `recipe.format_rebinding_table` produce the lines; the Rust `hanoigame` crate mirrors them.
- Rust UIs: `rust/hanoi-gui/` (wxDragon), `rust/hanoi-egui/` (egui, native + web), `rust/tauri/`
  (webview), plus the ratatui TUI and the CLI.
- How to see a GUI headless: Xvfb + screenshot, per the nested-run-and-gates.md reference doc in
  github.com/billsix/runClaudeInContainer.

## Lead found while writing this task (2026-11-05, not yet verified on screen)

**The Rust wx text board never gets a monospace font.** In `rust/hanoi-gui/src/main.rs`, the
`board_text` `TextCtrl` built in the frame setup (`TextCtrl::builder(&board_slot)` with
`MultiLine | ReadOnly`) has no `set_font` call. The Python oracle sets a teletype font on its text board
(`python/src/hanoigame/board_renderers.py`, the text renderer's control, `wx.FONTFAMILY_TELETYPE`), and
the Rust GUI already does this for its other text views (`show_monospace_dialog`, and the history
`ListBox`). In a proportional font, spaces are narrower than `*` and `|`, so the board's columns drift.
It has a second effect: `centred_board_text` pads using `get_char_width()`, which is an *average* width
in a proportional font, so the centring is off too.

Already checked, less likely to be the cause:

- The C++ wx GUI (`cpp/hanoiwx.cpp`) sets `wxFONTFAMILY_TELETYPE` on its text views.
- Tauri renders the board in a `<pre id="board">` with a monospace font stack (`--font-mono` in
  `rust/tauri/frontend/style.css`).
- egui uses `ui.monospace(line)` for the rebinding and recipe lines. Its win dialog uses `ui.label`,
  but that text isn't ASCII art.

## Plan

1. Reproduce: run each Rust UI under Xvfb, switch to the text board, make a few moves, relabel, and
   apply a recipe. Screenshot the board, the recipe view, the rebinding table, and the move history next
   to the Python wx GUI's.
2. For each misaligned view, find the cause. Candidates: a proportional font; leading whitespace
   trimmed by a widget or a `trim()`; tabs; centring maths that assumes fixed-width characters;
   non-ASCII characters (`—`, `→`) that render wider than one column in some fonts.
3. Fix it in the UI layer (front-ends stay thin; the shared `presenter` lines are correct as long as the
   CLI/TUI line up). Prefer one shared helper per front-end for "make a monospace text control".
4. Check that the egui web build and the Tauri app still render the same.
5. Add the "text views use a monospace font" rule to the feature spec's GUI guidance (§6.2) and its
   compliance checklist (§7), if it isn't already there.

## Open questions

None yet. Step 1 may show the problem is somewhere else than the lead suggests.
