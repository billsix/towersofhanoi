# Apply output: reconcile the redundant per-step `1 -> 3` move log vs. the three-panel view

**Status:** DONE 2026-10-31 (autonomous batch, branch `ui-fanout-and-apply-output`, gpg off). Decision
below taken at the maintainer's discretion. Archived same day.
**Priority:** 5 **Difficulty:** 3

## Decision + work record (2026-10-31)

- **Decision = option (a), scoped to the relabelled case:** under a **relabelling** the three-panel
  rebinding table already lists every recipe move (left) and its rebound physical move (right), so the
  per-step `step N: <from> -> <to>` log just repeated the Rebound column — **drop it there**. Under the
  **default labelling** (no table) **keep** the per-step log: it is then the only move output. Failures
  (`step N: stopped — <reason>`) stay visible in both cases. Moves are still **recorded** regardless
  (the running tally depends on it).
- **Implemented:** Python oracle `engine._handle_apply` (`show_table` guard); feature-spec §4.8
  finalized (new "Per-step log — only under the default labelling" bullet); wxPython `_apply_recipe_by_name`
  now takes its "Applied 'x' — N moves" count from the recipe, not by parsing the (now-absent) step log.
  Rust `handle_apply` (engine.rs) mirrors it; the ratatui TUI renders engine lines so inherits it.
  **C++ needs no change** — its GUIs show the three-panel dialog, never a text step log.
- **Tests:** a lock-in assertion (`"step 1:"` absent under a relabelling) added to both the Python
  (`test_bill_worked_example_via_cli`) and Rust (`bill_worked_example_via_cli`) CLI tests; default-labelling
  apply tests keep asserting the step log. Python gates green (130 passed/2 skipped); Rust test gate green.
**Created:** 2026-10-25 (William Emerison Six <billsix@gmail.com>). On-screen feedback (Rust CLI): invoking
a recipe shows the three-panel rebinding (good), "but then it shows the implementation from 1 to 3 again,
which makes no sense — the stuff on the right [the rebound physical moves] is the relabelled one."

## BLUF

When a recipe is applied under a non-default labelling, the **text front-ends** (CLI/TUI) print the
**three-panel rebinding table** (recipe moves | rebinding label→peg | rebound physical moves) **and then**
a per-step `step N: <from> -> <to>` log — and the per-step log now duplicates/confuses what the table's
columns already show. This is the **Python oracle's** behaviour (`engine._handle_apply` emits the table
then the per-step lines), which the Rust CLI faithfully mirrors — so it's **not a Rust bug** but a
spec/oracle design decision. Decide what `apply` should print, fix it **first in the Python oracle**,
finalize feature-spec.md §4.8, then **fan out** to every implementation. "Done" = the apply output is
decided + consistent across all UIs, per §4.8.

## Context

- **Where it lives:** `python/src/hanoigame/engine.py` `_handle_apply` appends `format_rebinding_table(...)`
  (the three-panel, only when relabelled) then one `  step N: from -> to` line per step; the CLI/TUI
  print those lines verbatim. The GUIs show their own three-panel dialog, not this text log — so this is
  a **text-frontend** output question.
- **The decision (open question 1):** with the three-panel already showing recipe moves (left) and rebound
  physical moves (right), is the per-step log redundant? Options: (a) **drop the per-step log when the
  three-panel is shown** (recommended — the table covers it), (b) keep only a terse "Done (N moves)."
  summary, or (c) keep the log but in physical/default space labelled clearly as the applied moves.
- **Oracle-first, then fan out** (the maintainer's standard flow): change `_handle_apply` (+ the wxPython
  GUI if it shows any equivalent), finalize §4.8, then update the Rust CLI/TUI (which mirror the oracle),
  the C++, and any other UI.

## Plan

1. Decide the apply output (open question 1) — the maintainer picks; recommend (a).
2. Implement in the Python oracle (`engine._handle_apply`); keep the three-panel, trim/replace the
   per-step log per the decision. Gates green.
3. Finalize feature-spec.md §4.8 to state exactly what `apply` shows.
4. Fan out to every implementation (Rust CLI/TUI, C++, …), each checked against §4.8.

## Open questions — resolved (2026-10-31)

1. **What should `apply` print under a relabelling** → **(a)**: the three-panel table + "Done.", with the
   per-step log dropped under a relabelling (kept under the default labelling). See the decision above.

## Related

- Oracle: `python/src/hanoigame/engine.py` (`_handle_apply`), `recipe.py` (`format_rebinding_table`).
- Spec: `tasks/reference/feature-spec.md` §4.8. Surfaced during the Rust parity work
  (`tasks/archive/2026/10/25/rust-feature-parity-tauri-tui-gaps.md`).
