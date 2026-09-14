# Record recipe bindings + played state, and show the rebinding on save

**Status:** actionable — design decided 2026-09-14 (see "Decisions" below); ready to implement.
**Priority:** 5
**Difficulty:** 4
**Started:** 2026-08-27

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
