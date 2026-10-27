# Rust: push tests into doctests and wire `cargo test` into a make target

**Status:** proposed — needs go-ahead.
**Priority:** 5
**Difficulty:** 4
**Created:** 2026-10-27 (William Emerison Six <billsix@gmail.com>)
**Updated:** 2026-10-27 (William Emerison Six <billsix@gmail.com>)

## BLUF

For the **Rust** subproject (`rust/`), push as many unit tests as reasonable **into doctests**
(runnable ` ```rust ` examples in `///` / `//!` doc comments) and ensure they run as part of a
`make test` target. "Done" = a `test` target in `rust/Makefile` runs `cargo test` (which includes
`cargo test --doc`), the cases that read well as doc examples have been moved into the library
crate's doc comments, the ones that stay `#[test]` are listed with a reason each, and it is green.

The sibling Python subproject task is [[python-doctests-into-make-test]].

## Context (cold start)

- Repo: github.com/billsix/towersofhanoi (mounted as `hanoi`). The Rust subproject is a Cargo
  workspace under `rust/`: a `hanoigame` library crate + front-ends (`hanoi-cli`, `hanoi` TUI,
  `hanoi-gui`), plus the separate `rust/tauri/` and `rust/hanoi-egui/` workspaces.
- **Rust runs doctests for free.** `cargo test` compiles and runs every ` ```rust ` block in a
  `///`/`//!` doc comment as a doctest automatically — no extra config, unlike Python's
  `--doctest-modules`. So "wiring" here is just making sure a make target invokes `cargo test`.
- **Current gate:** `rust/Makefile` has `check` (`cargo check --workspace --all-targets` — compiles
  test modules but does **not run** them) and `type-check` (the Tauri frontend via Deno). There is
  **no `test` target that runs the suite**, so `#[test]` cases and any doctests are not executed by
  a gate today. Adding one is step one.

## Plan

1. **Wire the gate.** Add `test: image` to `rust/Makefile` running `cargo test --workspace`
   (runs unit, integration, and `--doc` doctests) inside the container, mirroring `shell`'s env /
   `PODMAN_RUN_FLAGS`. Keep `check` as the compile-only gate; `test` is the run gate (both
   standalone, nothing interactive depends on them — same reasoning as `check: image`).
2. **Migrate.** For the `hanoigame` library crate, move the short deterministic `#[test]` cases
   that document an API into ` ```rust ` doc examples on the relevant item (they then appear in
   `cargo doc` and run under `cargo test --doc`). Keep the `assert_eq!`-heavy or multi-step tests
   as `#[test]` where a doc example would be noise.
3. **Keep as `#[test]`** (list each with a reason): tests needing a debugger to follow the code,
   anything with heavy setup/fixtures, property/randomized tests, panics via `#[should_panic]`,
   and internal (`#[cfg(test)]` private) invariants not meant for the public docs.
4. `make test` green; `cargo test --doc` actually runs the new doc examples.

## Notes

- `use std::X;` lines a doc example needs are either shown (teaching) or hidden with a leading `#`.
- Part of a cross-repo "doctests by default" initiative. The shared convention + lessons now live in
  **`~/.claude/reference/doctests-by-default.md`** (canonical: github.com/billsix/runClaudeInContainer;
  read its `## Rust` section first — `cargo test` runs `--doc` doctests for free, so wiring is just a
  `make test` that runs `cargo test`; plus the consolidation hazards and keep-as-`#[test]` exceptions).
- **Required on completion:** append anything new this (Rust) migration taught to
  `doctests-by-default.md` (its `## Rust` section, or the language-agnostic core if general) and
  re-sync the byte-identical runCrush mirror (`runCrushInContainer tasks/reference/doctests-by-default.md`).
  The sibling [[python-doctests-into-make-test]] does the same for the `## Python` section.
