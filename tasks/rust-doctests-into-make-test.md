# Rust: push tests into doctests and wire `cargo test` into a make target

**Status:** done — committed on branch `doctests`; pending the maintainer's squash, then archive.
**Priority:** 5
**Difficulty:** 4
**Created:** 2026-10-27 (William Emerison Six <billsix@gmail.com>)
**Updated:** 2026-10-27 (William Emerison Six <billsix@gmail.com>)

## BLUF

For the **Rust** subproject (`rust/`), as many unit tests as read well were pushed **into doctests**
(runnable ` ```rust ` examples in `///` / `//!` doc comments) and wired to run under a `make test`
target. Done: `rust/Makefile` has a `test` target running `cargo test --workspace` (which includes
`cargo test --doc`); the API-documenting single-case tests moved into the `hanoigame` crate's doc
comments; the loop / property / multi-step tests stayed `#[test]` (listed below with reasons); and
`make test` is green (30 lib tests + 25 doctests, 0 failed — doctests up from 6).

The sibling Python subproject task is [[python-doctests-into-make-test]].

## Context (cold start)

- Repo: github.com/billsix/towersofhanoi (mounted as `hanoi`). The Rust subproject is a Cargo
  workspace under `rust/`: a `hanoigame` library crate + front-ends (`hanoi-cli`, `hanoi` TUI,
  `hanoi-gui`), plus the separate `rust/tauri/` and `rust/hanoi-egui/` workspaces.
- **Rust runs doctests for free.** `cargo test` compiles and runs every ` ```rust ` block in a
  `///`/`//!` doc comment as a doctest automatically — no extra config, unlike Python's
  `--doctest-modules`. So "wiring" was just making a make target invoke `cargo test`.
- Before this task, `rust/Makefile` had `check` (`cargo check --workspace --all-targets` — compiles
  the test modules but does **not run** them) and `type-check` (the Tauri frontend via Deno), but
  **no `test` target that runs the suite** — so `#[test]` cases and doctests were never executed by
  a gate. All migration was confined to the `hanoigame` library crate; the front-ends carry no unit
  tests of their own (logic lives in the crate), so they could not be affected.

## What was done

1. **Wired the gate.** Added `test: image` to `rust/Makefile`, running `cargo test --workspace`
   inside the container and mirroring `shell`'s env / `PODMAN_RUN_FLAGS`. `check` stayed the
   compile-only gate; `test` is the run gate — both standalone, with nothing interactive depending
   on them (the same reasoning that keeps `check: image`).
2. **Migrated the single-case, API-documenting tests into doctests** on the item each documents, in
   the `hanoigame` crate:
   - `solvers/recursive.rs` — `hanoi_1`, `hanoi_2`, `hanoi_3`.
   - `solvers/iterative.rs` — `solve`, `swap_temporary_and_goal`, `swap_initial_and_temporary`.
   - `model.rs` — `HanoiGame::new`, `check_win_condition`, `apply_move` (the last showing all three
     `MoveError` cases).
   - `presenter.rs` — the seven layout fns (`peg_visual_width`, `peg_gap`, `total_width`,
     `disk_char_width`, `padding_left`, `peg_center_x`, `min_cols`), the labelling/colour fns
     (`change_labels_on_pegs`, `labelling_for`, `label_to_tower`, `peg_color`, `labels_to_towers`),
     and `render` (the 3-disc fresh board + the 0-disc empty case).
   - `recipe.rs` — `rebinding`, `rebound_moves`, and a `Recorder` round-trip (record → `to_recipe`
     → `reset`) on the struct doc.

   The matching single-case `#[test]`s were **deleted** (consolidation, not duplication): each was
   removed only after the doctest asserted the same thing, and a short comment left in the `tests`
   module says the per-case checks are doctests now.

### Decisions and their rationale (chronological)

- **Every doctest binding is typed** (`let x: T = …`), not left to Rust's inference. The house
  "annotate every binding" rule was taken to extend into doctests, because a doctest is example code
  the reader copies — it should model house style. (This was applied after the maintainer pointed
  out the first batch had shipped bare bindings; the rule was then also written into the shared
  reference doc.)
- **Consolidation boundary = "is there a single doctest home?"** A test migrated only when one
  function/item owned the behaviour it asserted. Anything spanning several items, or asserting a
  sequence, stayed a plain test (below).
- **`cargo test --workspace`, not `-p hanoigame`,** so the gate also compiles the front-end crates
  (and would run their tests if any existed) — matching the Python side's "collect everything".

## Kept as `#[test]` (the doctest exception, spelled in Rust)

- **Exhaustive loops:** `labelling_for_round_trip` (all six labellings).
- **Property / invariant loops:** `move_count_is_2n_minus_1`, `general_form_matches_the_unrolled_levels`,
  `general_form_matches_the_iterative_solver`, `render_dimensions` (width/height over several `n`).
- **Multi-step sequences** a doc example would turn into noise: `makemove` (the full move walk),
  `render_after_one_move`, `render_label_row_changes_with_labelling`,
  `render_omits_reference_row_under_default`, `render_appends_reference_row_when_relabelled`,
  `render_with_legend_appends_move_count`, and every `recipe` `apply`/`replay`/`registry`/`format_*`
  test (they build a game, play labelled moves, record, relabel and replay — stateful and long).

## Verification

`make test` (`cargo test --workspace`), run nested, exited 0: `hanoigame` reported 30 lib tests +
25 doctests passing (0 failed); the front-end crates compiled with no test targets of their own.
Doctest count rose from 6 (solvers only) to 25.

## Lessons fed back

Appended to `~/.claude/reference/doctests-by-default.md` (canonical in runClaudeInContainer;
byte-identical runCrush mirror re-synced): the typed-doctest-bindings rule, and a hanoi contributor
entry noting the cross-language shape of the consolidation — in Rust it is "delete the `#[test]`
once a ` ```rust ` doctest covers it", keeping the same loop / exhaustive / multi-step exception
list as Python, spelled in Rust.

## Notes

- `use` lines a doc example needs are shown (teaching) rather than hidden with a leading `#`, since
  this is a teaching repo.
- Part of the cross-repo "doctests by default" initiative; the shared convention lives in
  `~/.claude/reference/doctests-by-default.md` (its `## Rust` section). The sibling
  [[python-doctests-into-make-test]] did the same for the `## Python` section.
