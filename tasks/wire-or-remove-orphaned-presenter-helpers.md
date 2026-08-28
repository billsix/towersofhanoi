# Wire or remove the orphaned presenter helpers; label unwired teaching modules

**Status:** proposed — needs go-ahead. Created 2026-08-27 (William Emerison Six <billsix@gmail.com>).
**Priority:** 6
**Difficulty:** 2

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
