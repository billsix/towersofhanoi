# Format gate lint debt: 17 ruff errors + 2 files of format drift

**Status:** DONE 2026-07-30. All 13 UP035 + 1 UP007 fixed by hand (List/Tuple/
Type → builtins; the `Command` Union → a `|` chain); T201 suppressed via
`per-file-ignores` scoped to the two solver demos (Bill approved the
suppress-as-intentional-CLI-output recommendation), with the reason recorded in
`python/pyproject.toml`. Verified in-container: `ruff check` all-pass, format
gate exit 0 and idempotent (18 files unchanged on rerun), 112/112 tests pass,
and all 10 package modules import (the wx GUI ones aren't test-covered, so
imports were checked explicitly).

## Goal

Get `make format` green: triage the 17 `ruff check` errors (none auto-fixable
with safe fixes) and decide what to do with the 2 files `ruff format` rewrites.

## The findings, by class

### A. UP035 — deprecated `typing.List`/`Tuple`/`Type` imports (13 sites)

Mechanical modernization: `List[X]` → `list[X]`, `Tuple[...]` → `tuple[...]`,
`Type[X]` → `type[X]`, and drop the `typing` imports. Same change the other
repos already made in their modern-Python passes. Files:

- `python/src/hanoigame/board_renderers.py:35`
- `python/src/hanoigame/commands.py:25`
- `python/src/hanoigame/engine.py:31`
- `python/src/hanoigame/hanoigame.py:41`
- `python/src/hanoigame/hanoigui.py:30` (×2: `Tuple`, `Type`)
- `python/src/hanoigame/hanoimodel.py:20`
- `python/src/hanoigame/presenter.py:28` (×2: `List`, `Tuple`)
- `python/src/hanoigame/recipe.py:50` (×2: `List`, `Tuple`)
- `python/tests/test_hanoimodel.py:19`
- `python/tests/test_recipe.py:27`

### B. UP007 — `Optional`/`Union` → `X | Y` (1 site)

- `python/src/hanoigame/commands.py:93`

### C. T201 — `print` found (3 sites) — JUDGMENT CALL, not a bulk fix

- `python/src/hanoigame/hanoiiterative.py:64`, `:68`
- `python/src/hanoigame/hanoirecursive.py:110`

These are the standalone solver demos printing moves to the terminal — printing
is plausibly their entire point. If so, the linter can't see that context and
the right fix is a scoped suppression (`per-file-ignores` for the two solver
files, or inline `# noqa: T201` with a reason), NOT deleting the prints or
routing them through a logger. Needs Bill's call.

### D. `ruff format` drift (2 files)

`ruff format` rewrites `board_renderers.py` and `hanoigui.py` (cosmetic
reflow). Deterministic — reappears on every gate run until committed. As of
2026-07-29 the reflow sits unstaged in the working tree.

## Plan (after go-ahead)

1. Bulk-fix A and B (mechanical; `--unsafe-fixes` covers 3 of them, hand-edit
   the rest), run the test suite.
2. Decide C with Bill; apply the scoped suppression or the rework he prefers.
3. Commit the D reflow as part of the same pass.
4. Verify: in-container `make format` exits 0, `make image` (which runs the
   tests) stays green.

## Open questions

1. **T201 prints in the solver demos:** suppress as intentional CLI output
   (recommended), or restructure the demos to return strings?
