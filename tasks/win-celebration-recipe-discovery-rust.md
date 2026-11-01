# Win celebration + recipe discovery — Rust

**Status:** proposed — needs go-ahead.
**Priority:** 5 **Difficulty:** 5 (five front-ends)
**Part of:** `tasks/win-celebration-recipe-discovery.md` (umbrella — the cross-cutting design + the four
open questions that **block implementation**).
**Depends on:** `tasks/win-celebration-recipe-discovery-python.md` (the Python oracle fixes the wording
and updates the spec; mirror that here — don't invent wording).
**Created:** 2026-11-01 (William Emerison Six <billsix@gmail.com>).

## BLUF

Mirror the Python win-celebration wording into the Rust **`hanoigame` crate** (one presenter helper), then
wire all **five** front-ends to surface it at the win: `hanoi-cli` (CLI), `hanoi` (ratatui TUI),
`hanoi-gui` (wxDragon), `tauri`, `hanoi-egui`. "Done" = every Rust UI shows the first-win teaching moment
+ lighter later wins, wording matches the oracle (asserted in a test), `make check`/`make test`/
`make type-check` green, and the maintainer display-verifies each GUI.

## Context (read first)

- Umbrella design + open questions: `tasks/win-celebration-recipe-discovery.md`. The **wording is the
  Python task's output** — this task reproduces it, it does not redesign it.
- The crate mirrors the Python package module-for-module (`rust/CLAUDE.md`): put the helper in the
  `hanoigame` presenter module next to the move-tally formatter; **annotate every binding** (house style).
- **Tauri already has a partial inline hint** — `rust/tauri/frontend/main.js` `render()` builds "Solved in
  M moves — … Save it from the Recipe menu." **Upgrade** it to the first-win teaching popup (an HTML
  `<dialog>` `showModal`, like the How-to-Play dialog already in `index.html`/`main.js`), keeping the
  lighter inline line for later wins; stays typed (`@ts-check`, strict `checkJs`). The celebration text
  should come from the backend snapshot (one serde view), not be hand-written in JS, so it matches the
  crate helper and the oracle.

## Plan

1. **Crate helper** in `hanoigame` presenter: the mirror of the Python `format_win_celebration`, with a
   **doctest/unit test asserting the exact oracle strings** (the parity bar).
2. **Expose it on the snapshot** the UIs already consume (so Tauri/egui/wx/tui/cli all read one field),
   or a command — decide with the existing IPC/view-model shape (`rust/tauri/src/main.rs` Snapshot).
3. **Wire each front-end** to its idiom: `hanoi-gui` (wxDragon modal on first win, Save prefilled
   `solve-<N>`); `tauri` (upgrade the inline hint → `<dialog>` first-win, inline after); `hanoi-egui`
   (a centered egui window); `hanoi` (ratatui — a one-time region/overlay); `hanoi-cli` (printed block +
   `save` hint). Keep the Tier-2 menu enable and drag-off-on-win.
4. **Verify:** `make check` (`cargo check --workspace --all-targets`) + `make test` (incl. doctests) +
   `make type-check` (Deno, for the Tauri frontend) + `make format`; maintainer runs `make wx`/`make
   tauri`/`make egui`/`make tui` to confirm each on display.

## Open questions — resolved

- The umbrella's four are **resolved** (2026-11-01; see umbrella): teaching first-win-only; congrats +
  Save offer every win; shared crate helper; spec updated (by the Python task). **Rust-local:** whether
  the celebration text rides the existing `Snapshot` as a new field or a dedicated command —
  implementation discretion, resolve against the current view-model (note it in the work record).

## Related

- Umbrella + Python oracle: `tasks/win-celebration-recipe-discovery.md`,
  `tasks/win-celebration-recipe-discovery-python.md`.
- `rust/CLAUDE.md` (the crate/front-end map), `tasks/reference/tauri-frontend-native-look.md` (the Tauri
  `<dialog>` pattern used by How-to-Play), `tasks/reference/feature-spec.md`.
