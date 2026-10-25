# Rust: close the front-end spec-parity gaps (Tauri rebinding view, TUI valid-moves, help, autocomplete)

**Status:** COMPLETE (2026-10-25) — the Rust front-ends were brought to feature-spec parity and the
maintainer **confirmed them on-display** ("they look good"). Compile-verified nested throughout
(`cargo check --workspace` + the separate Tauri crate + `rustfmt`). One item was deferred as an
oracle/spec decision, not a Rust fix: the redundant apply per-step `1 -> 3` log →
`tasks/apply-output-trim-redundant-move-log.md`.
**Priority:** 6 **Difficulty:** 3
**Created:** 2026-10-25 (William Emerison Six <billsix@gmail.com>). Filed from the feature-spec compliance
audit (`tasks/archive/2026/10/25/program-feature-spec-and-compliance.md`), after the maintainer set full
spec parity as the standard for every implementation (Rust included).

## BLUF

The Rust shared `hanoigame` crate was already spec-complete (all recipe/rebinding/three-panel logic,
unit-tested), so the parity gaps were **presentation-layer only, in the front-ends**. This task closed
them — the Tauri apply view, the TUI valid-moves line, wx/Tauri help, the §4.5 save prefill, and TUI
Tab-completion — against `tasks/reference/feature-spec.md`. The crate's behaviour was not changed.

## Context

- **Authority + audit:** `tasks/reference/feature-spec.md` (§4.4 valid moves, §4.5 save prefill, §4.8 the
  three-panel apply view, §6.1 completion, §7 checklist) and the per-row audit in
  `tasks/archive/2026/10/25/program-feature-spec-and-compliance.md`.
- **Backend primitives were already present** in the crate: `recipe::format_rebinding_table`,
  `recipe::rebound_moves`, `engine::valid_moves_str` — the work was wiring/rendering, not new game logic.
- Independent of `tasks/rust-gui-use-shared-xrc.md` (the wx XRC-loading rewrite).

## What was done & verified

- **Tauri — three-panel rebinding view on apply (§4.8, the biggest gap).** `apply_recipe`
  (`tauri/src-tauri/src/main.rs`) was extended to return a view-model carrying the recipe's own moves, the
  rebound physical moves, and the per-step results; `tauri/frontend/{main.js,index.html,style.css}` render
  **three side-by-side columns** (recipe moves | rebinding label→peg | rebound physical moves) at apply
  time, shown only under a non-default labelling (open question resolved: three columns, not aligned text).
- **Tauri — per-step replay log (§4.8).** The dropped per-step log is returned and shown, matching the
  CLI/TUI.
- **TUI — valid-moves line (§4.4).** `rust/hanoi/src/main.rs` `draw_play` gained the
  `session.valid_moves_str()` line the CLI/wx/Tauri already showed.
- **wx + Tauri — help (§4.10/§6.2).** A help dialog/control listing the features/commands.
- **§4.5 save prefill.** Each Rust front-end's save flow prepopulates `solve-<N>` (folded in beyond the
  original gaps, since §4.5 now requires it of every UI).
- **TUI Tab-completion (§6.1).** Added to the ratatui prompt: the CLI's `completions()` was **moved into
  the shared `hanoigame::commands` crate** (so the CLI and TUI use one copy, no drift), the TUI's
  `read_line_on` line editor gained a completer parameter + a `complete_line` helper (single candidate
  fills in; several fill to the longest common prefix), wired at all four prompt call sites. Spec §6.1 was
  sharpened to require completion of TUIs, not just the readline CLI; the Python ncurses TUI's matching
  gap was filed as `tasks/python-tui-autocomplete.md`.

**Verification:** `cargo check --workspace` (hanoigame / CLI / TUI / wx) clean, `cargo check` on the
separate Tauri crate clean, `rustfmt` clean + post-format re-check clean — all nested. The maintainer ran
`make tui`/`wx`/`tauri` on-display and confirmed look/behaviour (the Tauri three-column view, the TUI
line + completion, help). No display in-sandbox, so on-display was the maintainer's step throughout.

**Deferred (not a Rust bug):** invoking a recipe also prints a per-step `1 -> 3` log that now duplicates
the three-panel's columns — but that is the **Python oracle's** `_handle_apply` output, which the Rust CLI
faithfully mirrors, so it is an oracle/spec decision for every UI → `tasks/apply-output-trim-redundant-move-log.md`.

## Related

- Authority + audit: `tasks/reference/feature-spec.md`, `tasks/archive/2026/10/25/program-feature-spec-and-compliance.md`.
- Sibling parity task: `tasks/archive/2026/10/25/cpp-add-wx-frontend-and-recipe-view-parity.md` (C++).
- Follow-ons surfaced here: `tasks/python-tui-autocomplete.md`, `tasks/apply-output-trim-redundant-move-log.md`.
- Rust ecosystem/build facts: the shared `rust-gui-tui-and-ecosystem.md` (runClaudeInContainer
  `tasks/reference/`) and `tauri-desktop-apps.md`; the Rust port record
  `tasks/archive/2026/10/23/port-to-rust-wxdragon.md`.
