# Apply output: reconcile the redundant per-step `1 -> 3` move log vs. the three-panel view

**Status:** proposed — needs go-ahead (a design decision, then an oracle-first fan-out).
**Priority:** 5 **Difficulty:** 3
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

## Open questions

1. **What should `apply` print under a relabelling** — three-panel only + "Done" (recommended), or keep
   the per-step log in some form? See Context options (a)/(b)/(c).

## Related

- Oracle: `python/src/hanoigame/engine.py` (`_handle_apply`), `recipe.py` (`format_rebinding_table`).
- Spec: `tasks/reference/feature-spec.md` §4.8. Surfaced during the Rust parity work
  (`tasks/rust-feature-parity-tauri-tui-gaps.md`).
