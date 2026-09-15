# Wire or remove the orphaned presenter helpers; label unwired teaching modules

**Status:** complete (2026-09-15). Created 2026-08-27 (William Emerison Six <billsix@gmail.com>).
`ty`/ruff/format green in-container, 128 tests pass.
**Priority:** 6
**Difficulty:** 2

## What this was

Cleanup of the dead/orphaned code the architecture overview had surfaced: the presenter's sizing
helpers (`min_cols`/`min_rows`) were unused because the curses frontend had its own size check,
`render_with_legend` had no production caller, `recipe.apply` was test-only, and the two teaching
modules had no importers. The one open question: route the curses size check through
`presenter.min_cols`/`min_rows` (DRY) or delete them and keep the curses-local check?

## Outcome

The open question needed a **split** answer — route where the presenter helper genuinely matched,
delete where it didn't:

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
removed an unused, incorrect helper).

## Related

- `tasks/reference/architecture-overview.md` — "Orphan cleanup" (the durable record).
- `python/src/hanoigame/`: `presenter.py`, `hanoigame.py`, `hanoicli.py`, `recipe.py`,
  `hanoirecursive.py`, `hanoiiterative.py`; `python/tests/test_presenter.py`.
