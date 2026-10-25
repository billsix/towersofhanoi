# Rust: close the front-end spec-parity gaps (Tauri rebinding view, TUI valid-moves, help)

**Status:** proposed — needs go-ahead.
**Priority:** 6 **Difficulty:** 3
**Created:** 2026-10-25 (William Emerison Six <billsix@gmail.com>). Filed from the feature-spec compliance
audit (`tasks/archive/2026/10/25/program-feature-spec-and-compliance.md` § Audit results, 2026-10-25), after the maintainer
set full spec parity as the standard for every implementation (Rust included).

## BLUF

The Rust **shared `hanoigame` crate is already at full parity** with the feature spec
(`tasks/reference/feature-spec.md`) — all recipe/rebinding/three-panel logic is present and unit-tested.
The only gaps are **presentation-layer, in two front-ends**, and all the backend primitives they need
already exist:

1. **Tauri — the three-panel rebinding view on apply (spec §4.8, checklist row 13; biggest).** `apply_recipe`
   returns a one-line "Applied — N moves" message, and the frontend shows only a standing "Rebinding:
   label → peg" line (the middle column). Missing: the recipe's own moves (left) and the rebound physical
   moves (right), shown on invoke and only under a non-default labelling. The Rust backend already has
   `format_rebinding_table` + `rebound_moves` — wire `apply_recipe` to return those columns (or the table
   lines) and render three panels/columns in `tauri/frontend/main.js` at apply time.
2. **Tauri — apply richness (row 12).** The per-step replay log is dropped (collapsed to one line); return
   the per-step results so the frontend can show the step-by-step replay the CLI/TUI already give.
3. **ratatui TUI — valid-moves line (spec §4.4, row 8).** The CLI, wx, and Tauri surface the legal moves
   in current labels; the TUI shows none. Add a `session.valid_moves_str()` line to `draw_play` (hint
   area or above the prompt).
4. **wx + Tauri — real help (row 14).** wx's Help is an About blurb (not the command/feature reference);
   Tauri has no help control. Add a help dialog listing the features/commands (minor).

"Done" = the Tauri app shows the three-panel rebinding view on apply (matching the spec and the
CLI/TUI/wx output), the TUI shows the valid-moves line, and wx/Tauri have a real help dialog — verified
against `tasks/reference/feature-spec.md` §7 rows 8, 12, 13, 14.

## Context (read first)

- **Spec + audit:** `tasks/reference/feature-spec.md` (§4.8 the three-panel view; §7 checklist) and the
  per-row audit in `tasks/archive/2026/10/25/program-feature-spec-and-compliance.md`.
- **The crate is the oracle-parity layer, don't change its behavior** — these are rendering/IPC changes in
  `rust/hanoi-gui/` (wx), `rust/hanoi/` (TUI), and `rust/tauri/` (both `src-tauri/src/main.rs` and
  `frontend/main.js`). Backend primitives already present: `recipe::format_rebinding_table`,
  `recipe::rebound_moves`, `engine::valid_moves_str`.
- **Independent of** `tasks/rust-gui-use-shared-xrc.md` (that's the wx XRC-loading rewrite); this is about
  feature parity in the Tauri/TUI front-ends. They can be done in either order.

## Plan

1. **Tauri apply view** — extend the `apply_recipe` command's return (serde view-model) with the recipe's
   own moves + the rebound physical moves (or the `format_rebinding_table` lines + a shown-only-when-
   relabelled flag); render three columns/panels in `main.js` at apply time; keep the per-step results so
   the replay log can be shown.
2. **TUI valid-moves** — add the `valid_moves_str()` line to `draw_play`.
3. **wx + Tauri help** — a help dialog/control listing the features/commands.
4. **Verify** — against spec §7 rows 8/12/13/14; the Tauri view matches the CLI/TUI/wx three-panel output
   for a sample recipe under a non-default labelling; `make format` (rustfmt) clean; nested build/run.

## Open questions

1. **Tauri three-panel layout** — three side-by-side `<div>` columns (matches the GUI §6.2 advice), or a
   single aligned-text block reusing `format_rebinding_table` (simplest, matches wx's dialog)? Recommend
   three columns for Tauri since it's HTML/CSS and the spec prefers panels.

## Related

- Authority + audit: `tasks/reference/feature-spec.md`, `tasks/archive/2026/10/25/program-feature-spec-and-compliance.md`.
- Sibling parity task: `tasks/archive/2026/10/25/cpp-add-wx-frontend-and-recipe-view-parity.md` (C++).
- Rust ecosystem/build facts: the shared `rust-gui-tui-and-ecosystem.md` (runClaudeInContainer
  `tasks/reference/`) and `tauri-desktop-apps.md`; the Rust port record
  `tasks/archive/2026/10/23/port-to-rust-wxdragon.md`.
