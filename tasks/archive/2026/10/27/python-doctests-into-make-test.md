# Python: push unit tests into doctests and wire them into `make test`

**Status:** done — committed on branch `doctests`; pending the maintainer's squash, then archive.
**Priority:** 5
**Difficulty:** 4
**Created:** 2026-10-27 (William Emerison Six <billsix@gmail.com>)
**Updated:** 2026-10-27 (William Emerison Six <billsix@gmail.com>)

## BLUF

For the **Python** subproject (`python/`), as many unit tests as read well were pushed **into
doctests** in the library source, and doctests were **wired into a `make test`** gate. Done:
`python/pytest.ini` collects doctests (`--doctest-modules --import-mode=importlib`, `testpaths =
tests src`); `python/Makefile` has a `test` target; the single-case tests moved into docstrings;
the parametrized / stateful / integration tests stayed pytest (listed below); and `make test` is
green (130 passed, 2 skipped, ruff clean).

This repo has a **Rust** subproject too (`rust/`); its doctest work is the sibling task
[[rust-doctests-into-make-test]].

## Context (cold start)

- Repo: github.com/billsix/towersofhanoi (mounted as `hanoi`). Per-language subprojects, each with
  its own container Makefile: `python/`, `rust/`, `cpp/`, plus `docs/`, `workbook/`.
- Python subproject: `python/` holds the `hanoigame` package (src layout, relative imports) + its
  `test_*.py` files.
- Before this task, `python/Makefile` had `all`/`image`/`shell`/`shell-exec` but **no `test`
  target** — nothing ran the tests (or any doctests) as a gate, unlike gacalc/mvp where
  `--doctest-modules` was already configured. Wiring was step one.

## What was done

1. **Wired the gate.** Added `python/pytest.ini` with `addopts = --doctest-modules
   --import-mode=importlib`, `pythonpath = src`, and `testpaths = tests src`; added a `test` target
   to `python/Makefile` that runs pytest in-container, mirroring `shell`'s setup. The committed
   `pytest.ini` carries a comment explaining both the no-allowlist decision and the import-mode.
2. **Migrated the single-case, behaviour-documenting tests into doctests** on the item each
   documents: `hanoimodel.py` (`HanoiGame`), `presenter.py` (the layout, labelling and render
   functions — `render` examples print `repr(line)` so trailing-space-significant board rows stay
   `repr`-stable), `recipe.py` (`rebinding`, `rebound_moves`, `Recorder`, `RecipeRegistry`), and
   `commands.py` (`parse`, `completions`). The redundant pytest cases were deleted (consolidation),
   and the imports they left dangling were trimmed.

### Decisions and their rationale (chronological)

- **`--import-mode=importlib` was required, discovered by failure.** Plain `--doctest-modules`
  imports each `src` file as a top-level module, so the package's relative imports
  (`from .hanoimodel import …`) failed collection with "attempted relative import with no known
  parent package". `importlib` mode imports each as `hanoigame.<mod>`, respecting the package.
- **No `testpaths` allowlist — guard instead of exclude.** `--doctest-modules` imports every module
  it collects, so a module that runs code at import would crash collection. All of the package's
  modules were already import-safe (their executable entry code sits behind
  `if __name__ == "__main__":`), so the whole package is collected with no exclusion list. The
  maintainer then asked to make that guard **standard practice** (separate functional from
  application code), which was written into `python-coding-standard.md`.
- **Every doctest binding is typed** (`name: T = …`), per the house "annotate every binding" rule —
  taken to extend into doctests, since a doctest is example code the reader copies.

## Kept as pytest (the doctest exception)

- **Parametrized** (`@pytest.mark.parametrize` — machinery a doctest can't express): the
  `commands.py` parse tests (`test_parse_move`, `…_arrow_move_invalid`, `…_relabel`, `…_help`,
  `…_quit`, `…_empty`, `…_garbage`), and the by-hand drift guard `test_byhand_drift.py`.
- **Exhaustive loops:** `test_labelling_for_round_trip`, `test_rebinding_covers_all_six_labellings`.
- **Multi-step / stateful sequences:** `test_makemove`; the `render_*` label/reference-row/legend/
  dimensions tests; and the `recipe` `apply`/`apply_iter`/`format_rebinding*`/teaching-lines tests
  (they play labelled moves, record, relabel and replay — stateful and long).
- **Integration / IO** (full CLI sessions driven through captured stdin/stdout): all of
  `test_hanoicli.py` and the completion-buffer tests in `test_hanoigame.py`.

## Verification

`make test`, run nested, was green: **130 passed, 2 skipped**, ruff clean. The doctests are
collected (the count rose) and the kept pytest cases still run.

## Lessons fed back

Appended to `~/.claude/reference/doctests-by-default.md` (canonical in runClaudeInContainer;
byte-identical runCrush mirror re-synced): the `--import-mode=importlib` need for a src-layout
package, the `__main__`-guard-as-import-safety-fix (and applying it project-wide first so the gate
config stays "collect everything"), and the typed-doctest-bindings rule. A new standard-practice
section on `if __name__ == "__main__":` was added to `python-coding-standard.md` (both sandboxes).

## Notes

Part of the cross-repo "doctests by default" initiative; the shared convention lives in
`~/.claude/reference/doctests-by-default.md` (its `## Python` section). The sibling
[[rust-doctests-into-make-test]] did the same for the `## Rust` section.
