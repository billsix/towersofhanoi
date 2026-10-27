# Python: push unit tests into doctests and wire them into `make test`

**Status:** proposed — needs go-ahead.
**Priority:** 5
**Difficulty:** 4
**Created:** 2026-10-27 (William Emerison Six <billsix@gmail.com>)
**Updated:** 2026-10-27 (William Emerison Six <billsix@gmail.com>)

## BLUF

For the **Python** subproject (`python/`), push as many unit tests as reasonable **into doctests**
in the library source, and **wire doctests into `make test`** so docstring examples run as part of
the suite. "Done" = `python/Makefile` has a `test` target that runs pytest with `--doctest-modules`
(or `python -m doctest`), the cases that read well as doctests have been migrated, the ones that
stay pytest are listed with a reason each, and `make test` is green.

This repo has a **Rust** subproject too (`rust/`); its doctest work is the sibling task
[[rust-doctests-into-make-test]].

## Context (cold start)

- Repo: github.com/billsix/towersofhanoi (mounted as `hanoi`). Per-language subprojects, each with
  its own container Makefile: `python/`, `rust/`, `cpp/`, plus `docs/`, `workbook/`.
- Python subproject: `python/` holds the `hanoigame` package + ~7 `test_*.py` files.
- **No `test` target exists yet.** `python/Makefile` has `all`/`image`/`shell`/`shell-exec` but no
  `test` — so nothing runs the tests (or any doctests) as a gate today. Wiring is step one here,
  unlike gacalc/mvp where `--doctest-modules` is already configured.

## Plan

1. **Wire the gate.** Add a `test` target to `python/Makefile` following the container-template
   shape (`test: image`, `podman run … pytest`, mirroring `shell`'s env). Configure pytest to
   collect doctests (`addopts = --doctest-modules`, `testpaths = src tests` in a `pytest.ini`/
   `pyproject.toml`), watching for modules that execute at import (guard any runnable script with
   `if __name__ == "__main__":` before letting `--doctest-modules` import it — same trap mvp hit).
2. **Migrate.** Inventory the ~7 test files; move the short deterministic `input → output` cases
   into the library docstrings; delete the redundant pytest case.
3. **Keep as pytest** (list each with a reason): anything needing a debugger to understand the
   code, fixtures/parametrization/`pytest.raises`, slow/randomized cases, or internal invariants.
4. `make test` green; doctests actually collected (count went up).

## Notes

Part of a cross-repo "doctests by default" initiative; the convention write-up is tracked in
**runClaudeInContainer** (`tasks/document-doctests-by-default.md`), to be done after the migrations.
