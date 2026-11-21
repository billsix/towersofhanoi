# Linked rows in the GUIs' three-panel rebinding view (done 2026-11-21)

**Priority:** 3 **Difficulty:** 4
**Created / done:** 2026-11-21 (William Emerison Six <billsix@gmail.com>); branch `gui-batch-2026-11-21`.

## What was done

In the three-panel rebinding view (feature-spec §4.8: recipe moves | label→peg key | rebound physical
moves), the rows of the two move columns now behave as one in every graphical UI: scrolling one scrolls
the other, selecting a move selects the same row on the other side, and the key marks the two bindings
the selected move uses (its from- and to-label). The behaviour is written into
`tasks/reference/feature-spec.md` §4.8 ("Linked rows") and compliance row 13.

Per UI, following the decision "one table where the toolkit has one; the wx UIs keep linked list boxes"
(William Emerison Six <billsix@gmail.com>, 2026-11-21):

- **Python wx** (`python/src/hanoigame/hanoigui.py`, `_show_rebinding_dialog`): selection mirroring
  already existed; added the key marker (▶) and scroll following. A native list box does not report every
  scroll as a wx event, so a 100 ms `wx.Timer` polls `GetTopItem()` on both lists and copies whichever
  moved onto the other with `SetFirstItem`. The timer stops on `EVT_WINDOW_DESTROY`, which covers both
  Close and the dialog being replaced by the next one.
- **C++ wx** (`cpp/hanoiwx.cpp`, `show_rebinding`): had no linking; got the same three behaviours as the
  Python dialog (selection mirror, polled scroll follow, ▶ marker).
- **C++ ImGui** (`cpp/main.cpp`, `draw_recipe_view`): already one table (shared scroll); the move cell is
  now an `ImGui::Selectable` spanning all columns, and the key marks with `>` because the default ImGui
  font has no ▶ glyph. `RecipeView.selected` holds the row.
- **Rust egui** (`rust/hanoi-egui/src/main.rs`): the view was monospace text lines; it is now a
  `RebindView` drawn as one `egui::Grid` in one `ScrollArea`, with selectable move cells and the ▶ marker.
- **Rust wxDragon** (`rust/hanoi-gui/src/main.rs`): the view was a read-only text dialog. wxDragon 0.9.23's
  `ListBox` cannot read or set its scroll position (no `GetTopItem`/`SetFirstItem`), so two linked list
  boxes were not possible; the view is one monospace list box with one row per move (all three columns
  in the row), which scrolls and selects as one. Selecting a row rewrites the rows with the `>` marker
  (`rebinding_rows`).
- **Rust Tauri** (`rust/tauri/frontend/main.js` `renderApplyView`, `style.css`): the three `div` columns
  became one `<table>` in a scrolling box with a sticky header; clicking a move row selects it and marks
  the key cells.

## Also fixed

`python/tools/gui_smoke.py` hung forever on master: the first-win teaching dialog and How-to-Play became
modal after the smoke was written, and the harness runs no event loop. It now stubs `ShowModal` to return
OK and also exercises the rebinding dialog's selection mirror and key marker. It prints `SMOKE OK 1`.

## Verification

- Python: `format`, `type-check`, `test` (136 passed, 2 skipped) green; the Xvfb smoke passes.
- C++: clang-format clean, full native build (both GUIs) with no warnings, ctest green.
- Rust: `format`, `check --workspace --all-targets`, `test --workspace`, the egui and Tauri `cargo check`s,
  and the Deno type-check gate green.
- Not checked: how it feels on a real display (scroll following in the wx dialogs, the egui/Tauri row
  highlight). That is the maintainer's on-display check.
