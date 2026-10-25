# Inspectable running move tally (default 1-2-3 labels) — build in wxPython first, then spec it, then fan out

**Status:** proposed — needs go-ahead.
**Priority:** 4 **Difficulty:** 4 (the wx phase; the fan-out is larger but follows the spec)
**Created:** 2026-10-25 (William Emerison Six <billsix@gmail.com>). Requested: "there should be a running
tally that shows all moves done, relative to the original labelling 1 2 3. that should be inspectable. add
a task for the wxpython one, to do it, and then from that, extract out what the markdown file that
describes the product should say, and when we do that, then fan out to implement that across all UIs."

## BLUF

Add an **inspectable running move tally** to hanoi: a view of **every move made this game, in order, in
the default 1-2-3 (physical) labelling** — the ground truth beneath any relabelling — that the user can
inspect at any time. Per the maintainer's sequence, build it **first in the wxPython GUI** (the behaviour
oracle), **then finalize the product spec** (`tasks/reference/feature-spec.md` §4.11) *from* that
implementation, **then fan out** to every other UI/implementation. "Done" (this task) = the wx tally
works, §4.11 is finalized into a real spec + §7 checklist row, and the fan-out is scoped (its own
task(s)).

## Context (read first)

- **Feature-spec entry:** `tasks/reference/feature-spec.md` §4.11 is the PLANNED placeholder for this; it
  says the exact presentation will be finalized from the wx implementation. Finalizing it is Phase 2.
- **The data already exists.** Moves are already recorded in **default-label space** by
  `recipe.Recorder` (`python/src/hanoigame/recipe.py` — `recorder.default_moves`, a list of
  `(from_default, to_default)` physical pairs); every legal move, typed or applied, is recorded there
  (`engine.GameSession._handle_move` / `_handle_apply` call `recorder.record(fp+1, tp+1)`). So the tally
  is a **view of existing state**, not new bookkeeping — this is why it's low-difficulty in wx.
- **wx GUI:** `python/src/hanoigame/hanoigui.py` (+ `board_renderers.py`) is where the view goes. It is
  the Part-A oracle for the C++/Rust wx GUIs and the behaviour authority for all.
- **Default-label invariant:** the tally is in default 1-2-3 (physical) labels regardless of the active
  labelling — same invariant recipes use. "Relative to the original labelling 1 2 3" = default space.

## Plan (phases)

**Phase 1 — wxPython (the oracle), this task's deliverable.** Add an inspectable running tally to
`hanoigui.py`: a view listing each move of the current game in order, in default 1-2-3 labels (e.g.
`1 -> 3`, `1 -> 2`, …), with a live count, sourced from `recorder.default_moves`. Decide the presentation
(open question 1). Resets with a new game; updates on every move (typed or applied). Verify in-container
(wx GUI builds + the tally updates; `make format`/`type-check` green).

**Phase 2 — finalize the spec from the wx impl.** Rewrite `feature-spec.md` §4.11 from PLANNED to the
real contract (what's shown, how it's inspected, where it lives, reset behaviour), and promote the §7
checklist row 15 to a real pass/fail. This is the "extract what the markdown should say" step.

**Phase 3 — fan out.** Implement the finalized tally across every UI/implementation — Python CLI/TUI,
C++ ImGui + wx, Rust CLI/TUI/wx/Tauri, and any future one — each checked against §4.11/§7. Scope this as
its own task/umbrella when Phase 2 lands (a good fan-out candidate; mind the token cost — brief tightly,
don't over-fork).

## Open questions

1. **wx presentation** — an always-visible side panel/list, an on-demand dialog (like the recipe Show /
   Rebinding dialogs), or a View-menu toggle? Recommend an **on-demand dialog** (consistent with the
   existing Show/Rebinding dialogs, no permanent layout cost), unless you want it always visible.
2. **Scope of "all moves"** — strictly the default-space move list, or also annotate wins/relabels? The
   request is "all moves … relative to 1 2 3", so **moves only, default space** (recommend); relabels
   aren't moves.
3. **Reset** — the tally is per-game and resets on New Game (recommend; it mirrors the recorder's
   lifetime).

## Related

- `tasks/reference/feature-spec.md` §4.11 (the placeholder this finalizes) + §7 row 15.
- Oracle + data source: `python/src/hanoigame/{recipe.py (Recorder/default_moves),engine.py,hanoigui.py}`.
- Fan-out precedent (how a spec drove multi-implementation work):
  `tasks/archive/2026/10/25/program-feature-spec-and-compliance.md`.
