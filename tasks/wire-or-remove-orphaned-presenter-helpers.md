# Wire or remove the orphaned presenter helpers; label unwired teaching modules

**Status:** complete (2026-09-15). Created 2026-08-27 (William Emerison Six <billsix@gmail.com>).
`ty`/ruff/format green in-container, 128 tests pass. See "Outcome".
**Priority:** 6
**Difficulty:** 2

## Outcome (2026-09-15)

The open question turned out to need a **split** answer — route where the presenter helper genuinely
matched, delete where it didn't:

- **`presenter.min_cols`** — WIRED. `hanoigame._required_cols` now returns `presenter.min_cols(n)`
  (they were byte-identical, `total_width(n) + 4`), so the helper has a real consumer.
- **`presenter.min_rows`** — DELETED (and its test). It was `n + 7`, but the real curses requirement
  is `_required_rows` = `n + 14` (it accounts for `MSG_AREA_LINES`/`HINT_AREA_LINES`). Routing
  through `min_rows` would have *under-reported* the height by 7 rows and let the UI draw
  off-screen; and `min_rows` couldn't correctly become the curses value without importing
  curses-frontend layout constants into the presenter (wrong layering). So the curses rows check
  stays authoritative and local (with a comment saying why).
- **`presenter.render_with_legend`** — WIRED into `hanoicli._print_board`; it returns
  `render(...) + ["Moves: N"]`, byte-identical to what the CLI printed by hand.
- **`recipe.apply`** — kept, with a docstring note that it's the eager convenience over `apply_iter`
  (the engine streams via `apply_iter`; `apply` is exercised by the tests). Not dead — a public API.
- **`hanoirecursive.py` / `hanoiiterative.py`** — module docstrings now state they are standalone
  teaching scripts with no importers.

All changes are behaviour-preserving (the two wirings are byte-identical substitutions; the deletion
was of an unused, incorrect helper). Reference doc updated:
`tasks/reference/architecture-overview.md` ("Orphan cleanup").

## Goal

Clean up the dead/orphaned code surfaced in `tasks/reference/architecture-overview.md`: the presenter's
sizing helpers are unused because the curses frontend reimplements the check locally, and two teaching
modules have no importers.

## Plan

- [ ] **Presenter sizing helpers** — `presenter.min_cols` (`presenter.py:138`), `min_rows` (`:143`)
      (and `render_with_legend`, `:222`): either **route the curses size check through them**
      (`hanoigame.py` currently reimplements it) — the DRY fix — or **delete** them if the curses version
      should stay authoritative. Prefer routing through the presenter (single source of truth).
- [ ] **`recipe.apply` (`recipe.py:184`)** — test-only; either leave with a `# test-only` note or fold
      its callers onto `apply_iter`.
- [ ] **Teaching modules** — mark `hanoirecursive.py` / `hanoiiterative.py` as standalone/non-wired
      (a module docstring line) so a reader doesn't hunt for their importers.
- [ ] Tests green.

## Open questions

1. Route curses sizing through `presenter.min_cols`/`min_rows` (recommended — DRY), or delete the
   presenter helpers and keep the curses-local check?
