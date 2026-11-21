# Link side-by-side lists in the GUIs: scrolling or selecting in one moves the other

**Status:** proposed — needs go-ahead (open questions below)
**Priority:** 3
**Difficulty:** 4 (per-toolkit mechanics differ; five GUIs)
**Created:** 2026-11-21 (William Emerison Six <billsix@gmail.com>)

## BLUF

Where a GUI shows lists side by side, most of all the **three-panel rebinding view** (recipe moves |
rebinding label→peg | rebound physical moves, feature-spec §4.8), the rows of one list correspond
row-for-row to the rows of another. Scrolling one list should scroll the others to the same rows, and
selecting a row in one should select the matching row in the others, so the student can read across
"move 3 in the recipe's labels → move 3 on the physical pegs". Done = every paired list in every
graphical UI is linked, and the behaviour is written into the feature spec.

## Context

- Read first: `tasks/reference/feature-spec.md` §4.8 (the three-panel view) and §7 (compliance
  checklist), `tasks/reference/ui-design-principles.md`.
- The view is built from the shared core's `recipe.format_rebinding_table` /
  `rebound_moves` (`python/src/hanoigame/recipe.py`; Rust `rust/hanoigame/src/recipe.rs`). The left
  and right lists have one row per move, so row *i* ↔ row *i*. The middle panel is the label→peg key
  (three rows), not a per-move list. Whether it should highlight the row the selected move uses is
  Open question 2.
- Per UI, where the three-panel view lives:
  - Python wx (oracle): `RebindingDialog` in `ui/hanoi.xrc` (`rebind_left`, `rebind_key` (a
    `wx.StaticText`), `rebind_right`), filled in `hanoigui.py` (look for `rebind_left`). wx has no
    built-in scroll sync: bind `EVT_LISTBOX` for selection and mirror `SetSelection`; for scrolling,
    poll or bind `EVT_SCROLLWIN` and mirror `SetFirstItem` (a plain `wx.ListBox` does not always
    send scroll events on every platform; try a `wx.ListCtrl`/`wx.VListBox` if needed).
  - C++ wx: the `RebindingDialog` code in `cpp/hanoiwx.cpp` (search "Three-panel rebinding dialog").
  - C++ ImGui: the three-panel view in `cpp/main.cpp` (search "three-panel rebinding view"). In
    immediate mode, simplest is one `ImGui::BeginTable` with three columns and a shared scroll, or
    copy `GetScrollY` to the others with `SetScrollY`.
  - Rust wxDragon: `rust/hanoi-gui/src/main.rs` (search "three-panel").
  - Rust egui: `rust/hanoi-egui/src/main.rs`. One `egui_extras::TableBuilder`, or shared
    `ScrollArea` offsets.
  - Rust Tauri: `rust/tauri/frontend/main.js` (the `ApplyView` rendering). Mirror `scrollTop` and the
    selected class between the panels.
- Other paired lists found so far: none besides the rebinding view. The move-history panel is a single
  list (its click-to-review behaviour is `tasks/gui-move-history-review-mode.md`). Check the recipe
  "show" view while doing this.

## Plan

1. Python oracle first; on-display check by the maintainer (`cd python && make wx`, play to a win,
   save a recipe, relabel, apply it).
2. Write the behaviour into feature-spec §4.8 and a new compliance row.
3. Fan out to the other four GUIs, one checklist item each; run each subproject's gate.

## Open questions

1. **Single table instead of linked lists?** Replacing the three lists with one three-column table
   gives linked scroll and selection for free in every toolkit. Is that acceptable, or must they
   stay three separate panels? *Recommend a single table where the toolkit has one (ImGui, egui,
   Tauri), and linked `ListBox`es in the wx UIs, keeping the visual three-panel look.*
2. **Middle panel:** when a move is selected, should the label→peg key highlight the two bindings
   that move uses? *Recommend yes; it is the point of the view.*
