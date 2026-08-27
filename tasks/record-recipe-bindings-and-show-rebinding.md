# Record recipe bindings + played state, and show the rebinding on save

**Status:** blocked
**Priority:** 6
**Difficulty:** 4
**Started:** 2026-08-27
**Blocked on:** maintainer answers the Open questions below (the bullet is partially thought through —
the binding semantics and persistence model must be pinned before implementing).
**Recheck:** the Open questions below are answered (maintainer-gated; no automated signal —
`/recheck-blocked` surfaces this for the maintainer to confirm, then set a real Status/Priority).

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

1. **What is a "binding" to hold onto** — the active labelling *permutation* at replay time, or the
   per-subproblem I/T/G variable→peg map? And in default-label space or current-label space?
   (Affects the data-model shape at recipe.py:57-62.)
2. **"Save that it was played"** — a boolean on the `Recipe`, a counter, or a flag stored **per
   move**? And should it **persist beyond the session** (the registry is RAM-only, recipe.py:92) —
   i.e. do you want on-disk recipe persistence as part of this?
3. **"Save onto individual moves"** — extend each `default_moves` entry to carry its own binding
   (changing the `Recipe` shape)? This touches the apply/relabel invariant (recipe.py:37-39) — OK to
   change that shape?
4. **"Show the rebinding" on recipe save** — a textual before/after label mapping printed in the
   terminal? Which frontend(s) should show it — CLI, curses, and/or the wx GUI?
