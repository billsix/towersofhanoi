# Record recipe bindings + played state, and show the rebinding on save

**Status:** Done — shipped, iterated to a **three-panel view**, and brought to CLI/TUI/GUI parity
(2026-09-14). 124 tests pass; touched files ty/ruff-clean. Archived 2026-09-14 (maintainer declined a
final GUI/curses human-verify; the wx dialog and curses pager remain agent-unverified — noted below).
Durable design harvested to `tasks/reference/architecture-overview.md`.
**Priority:** 5
**Difficulty:** 4
**Started:** 2026-08-27

## What shipped (2026-09-14)

The rebinding is shown as an **in-session teaching step** in all three frontends, no persistence,
driven by shared pure helpers so the logic is written and tested once.

**First cut** — a rebinding block + per-move `(pegs a -> b)` on each step.

**Then iterated (maintainer's request) to a three-panel view** — modelled on the GUI's numbered
recipe-steps list: **left** = the recipe's moves in its own labels, **middle** = the label→peg
rebinding key, **right** = the same moves rebound onto physical pegs. Left and right line up
move-for-move.

- **`recipe.py`** (pure, shared, tested):
  - `rebinding(labelling)` — each recipe label 1..3 → the 1-indexed physical peg it resolves to (the
    full labelling permutation; identity under `ONE_TWO_THREE`). The **middle** panel.
  - `rebound_moves(recipe, labelling)` — each recipe move rewritten onto physical pegs. The **right**
    panel. Pure (no game state).
  - `format_rebinding_table(recipe, labelling)` — the three columns as aligned text (the text-frontend
    equivalent of the GUI panels); empty under the default labelling. (`format_rebinding` — the
    middle-only text — is retained.)
- **`engine.py` `_handle_apply`** (shared by CLI + curses) — under a relabelling, inserts the
  three-column `format_rebinding_table` above the live step log; default-labelling output unchanged.
- **`hanoigui.py` `_show_rebinding_dialog`** (wx) — a non-modal three-panel dialog: two monospace
  scroll `ListBox`es (recipe moves | rebound-to-pegs) flanking the rebinding key, with **synced
  selection** (clicking a move on one side highlights the matching move on the other). Replaced the
  earlier `MessageBox`. (Also fixed `_on_apply`'s pre-existing step-count filter — it matched
  `"step "` but the lines are indented `"  step "`.)
- **Tests** — `test_recipe.py` covers `rebinding`/`format_rebinding` (identity, a relabel case, all
  six labellings, empty-under-default) and the new `rebound_moves`/`format_rebinding_table`
  (identity, relabel, empty-under-default, all-three-panels-present, single-move). Existing CLI apply
  assertions still pass (substring `in output` checks, robust to the added table lines).

### GUI refinements (2026-09-14, later)

- **wx sizer-flag crash fixed:** `wx.ALIGN_CENTER_VERTICAL` was used in a *vertical* sizer (illegal —
  only horizontal alignment is valid there); the middle key now uses `ALIGN_CENTER_HORIZONTAL` with
  the stretch spacers doing the vertical centering.
- **Scroll alignment:** selecting a move now selects *and scrolls* both lists so the matched rows
  line up (both have the same row count, so pinning the same first item aligns them; `SetFirstItem`
  with an `EnsureVisible` fallback, guarded).
- **Dialog on every relabelled move:** `_show_rebinding_dialog` was generalized to take any move list
  (`rebound_moves` now takes a move Sequence, not a `Recipe`), and `_on_move` fires it for the single
  just-made move whenever a relabelling is active — so the student is forced to see typed-label →
  physical-peg on each move, not only on `apply`. One dialog is reused (previous closed first) so
  repeated moves don't stack windows.
- **Still unverified by the agent:** the wx rendering — wxPython isn't importable in the agent's
  sandbox, so the dialog layout/scroll/close behaviour needs a human run to confirm.

### CLI + TUI parity (2026-09-14, later)

Brought the text frontends up to the GUI's "teach on every move, not just apply":

- **Shared helper** — `format_rebinding_table` now takes a move `Sequence` + a `left_header` (so one
  table serves both a recipe and a single move), and `GameSession.move_teaching_lines(cmd, result)`
  returns that table for a plain move **only when it's a `MoveCmd` that succeeded (no error lines)
  under a relabelling**. It lives beside `dispatch` (not inside `_handle_move`) on purpose: the GUI
  treats a move's non-empty `result.lines` as an *error*, so folding teaching text into the move's
  lines would misfire there — the GUI keeps its dialog; the text frontends call this helper.
- **CLI** (`hanoicli._play_game`) prints the table after a relabelled move — verified: typing
  `1 -> 2` under labelling (1,3,2) shows the same three-column table headed "Move (your labels)".
- **TUI** (`hanoigame`) does the same, and — since the message area is only `MSG_AREA_LINES` (6) tall
  and the `apply` table is ~11 lines — long output now opens a **scrollable full-screen pager**
  (`_show_pager`: Up/Down·PgUp/PgDn·Home/End·q, wired in `_play_game`) instead of truncating. The
  single-move table (5 lines) still fits the message area. **Curses pager is agent-unverified** (no
  tty here) — needs a human run.

No `Recipe`/registry shape change and no disk persistence — the binding is captured for *display*
only, so the apply/relabel invariant at recipe.py:37-39 is untouched.

## Decisions (maintainer, 2026-09-14)

1. **A "binding" is the whole labelling permutation** (the full relabelling in effect), not the
   per-subproblem I/T/G map alone.
2. **No persistence.** This is a purely **in-session, visible teaching step** — nothing is written to
   disk (the recipe registry stays RAM-only). The value is what the *student learns* from seeing it.
3. **Show the rebinding in all three frontends** — CLI, curses, and the wx GUI.

**The teaching point (what this must make visible):** a student already knows how to replay a recipe in
a relabelled context. What they don't yet grasp is that **a recipe thinks in its own local labels**
(the I/T/G abstraction — see `docs/source/byhand2.rst`), but when the *n−1* recipe is replayed to
build the *n* solution, the moves recorded into the new recipe are in **global (concrete-peg) labels**.
So when solving for *n*, replaying the *n−1* recipe must surface the **local→global rebinding as an
explicit step** ("here is the n−1 recipe in I/T/G → here it is rebound to concrete pegs to slot into
the n solution"), so the student sees *why* the sub-solution's labels change.

## Goal

Maintainer's idea, verbatim: *"When replaying recipe, hold onto bindings and save that it was
played. Save onto individual moves. Then, on recipe save, show the rebinding."*

Extend the recipe system so that replaying a recipe under a relabelling **captures the binding**
(the label mapping in effect) and records that the recipe **was played**, storing this **per move**,
and so that **saving a recipe shows the rebinding** (a before/after label mapping). This is a
follow-on to the existing recipe record/replay-through-relabel feature — not a redo of it.

## Context (what already exists — from investigation 2026-08-27)

- Recipes live in `python/src/hanoigame/recipe.py`. `Recipe` (recipe.py:57-62) stores only `name`,
  `disk_count`, `default_moves` — moves in **default-label space**, with **no per-move binding
  metadata and no "played" flag**. `Recorder` (recipe.py:66-91) logs moves; `apply_iter`/`apply`
  (recipe.py:129, :184) replay under the *current* labelling. The relabel-and-replay teaching moment
  is documented at recipe.py:37-39.
- The recipe registry is **RAM-only** (recipe.py:92) — there is no on-disk persistence today, which
  bears on "save that it was played".
- Relabelling is a separate command: `RelabelCmd` (commands.py:37); presenter peg-relabelling maths
  at presenter.py:20/:95/:148. All three frontends (CLI, curses, wx GUI) share `engine.dispatch`.
- This feature was scoped but **not** built in the archived recipe work:
  `tasks/archive/2026/05/11/PLAN.md` (Step 3) and `tasks/archive/2026/04/28/NOTES.md` §3.2.

## Plan (draft — refine after questions answered)

- [ ] Decide the `Recipe`/move data-model change (per-move binding + played flag) — see Q1–Q3.
- [ ] Capture the active binding at replay time into each replayed move (`apply_iter`/`apply`,
      recipe.py:129/:184), without breaking the apply/relabel invariant at recipe.py:37-39.
- [ ] Set the "played" state (per Q2) when a recipe is replayed.
- [ ] On recipe save, render the rebinding (before/after label mapping) in the chosen frontend(s) —
      see Q4. If persistence is wanted (Q2), design a save format (registry is RAM-only today).
- [ ] Tests mirroring the existing apply-through-relabel test.

## Notes / decisions

Recommendation from triage: NEW task (there were no active tasks and no `tasks/reference/`). If the
recipe/relabel semantics deserve a durable write-up, a `tasks/reference/` doc harvested from
`NOTES.md`/`PLAN.md` would be the natural home — separate call.

## Open questions

All resolved 2026-09-14 — see "Decisions" above. (Binding = full permutation; in-session only, no
persistence; shown in all three frontends; per-move binding capture is fine since it's transient
display state, not persisted — so the apply/relabel invariant at recipe.py:37-39 is respected by
capturing the binding for *display* without changing the stored `default_moves` shape.)
