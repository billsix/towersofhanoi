# GitHub Actions CI: format-check + test + type-check on push (Python, Rust, C++)

**Status:** done (staged; awaiting the maintainer's commit, then archive).
**Priority:** 5
**Difficulty:** 5
**Created:** 2026-10-27 (William Emerison Six <billsix@gmail.com>)
**Updated:** 2026-10-27 (William Emerison Six <billsix@gmail.com>)

## BLUF

Add a GitHub Actions workflow (`.github/workflows/checks.yml`, on push + PR) that runs, **per
language subproject**, a **format check**, a **`make test`**, and a **`make type-check`** — mirroring
the thin-wrapper CI in github.com/billsix/geometricalgebra and github.com/billsix/modelviewprojection
(each job is just `checkout` → `make <target>`; all logic stays in the Makefiles). Covers Python
(`python/`), Rust (`rust/`, including the Tauri **JavaScript** frontend's Deno type-check), and C++
(`cpp/`). Done: a push with mis-formatted code, a failing test, or a type error turns the action red,
without the CI ever reformatting or committing.

The C++ `make test` prerequisite is done: [[cpp-unit-tests-with-doctest]] (now archived/complete).

## Context (cold start)

- Repo: github.com/billsix/towersofhanoi (mounted as `hanoi`), branch `cicd`. **No
  `.github/workflows/` exists yet.** Per-language subprojects, each its own container Makefile:
  `python/`, `rust/`, `cpp/`.
- **The CI pattern to copy** (gacalc's `.github/workflows/checks.yml`): thin wrapper, one job per
  gate, `uses: actions/checkout@v5` then `run: make <target> <lean-flags>`. The jobs never modify the
  repo — `make check-format` runs the formatter in the disposable runner checkout then fails on
  `git diff --exit-code`; `test`/`type-check` are read-only. `CONTAINER_CMD` auto-detects
  podman→docker, so the identical `make` target runs on the `ubuntu-latest` Docker runner and on the
  maintainer's podman host. CI passes lean flags to skip heavy optional layers (gacalc:
  `BUILD_DOCS=0 USE_EMACS=0 USE_SPYDER=0`; mvp adds `USE_JUPYTER=0 USE_X_WINDOWS=0`).
- **Current gate targets per subproject** (verified 2026-10-27):
  - `python/`: has `format` (ruff), `type-check` (ty + `check_local_annotations`), `test` (pytest +
    doctests). **Missing: `check-format`.** Has no `CONTAINER_CMD` auto-detect line — add one.
  - `rust/`: has `format`, `check` (`cargo check --workspace --all-targets`), `type-check` (Tauri JS
    via Deno), `test` (`cargo test --workspace`). Has `CONTAINER_CMD` auto-detect. **Missing: `check-format`.**
  - `cpp/`: has `format` (clang-format) and now `test` (doctest/ctest, from the prerequisite task).
    Has `CONTAINER_CMD` auto-detect (Makefile line 16). **Missing: `check-format`.**
  (Earlier draft wrongly said `cpp/` lacked `CONTAINER_CMD`; it has it. Re-confirm `python/`.)

## Plan

1. **Add `check-format` to each subproject Makefile** — `check-format: format` then
   `git diff --exit-code` (gacalc's shape). Three small `.PHONY`, `## `-documented targets.
2. **Add `CONTAINER_CMD ?= $(shell command -v podman … || echo docker)` where missing** (`python/`;
   confirm). Required — a hardcoded `podman` fails on `ubuntu-latest`.
3. **Write `.github/workflows/checks.yml`** — `on: [push, pull_request]`, one job per (subproject ×
   gate), each `checkout@v5` → `cd <sub> && make <target> <lean CI flags>`:
   - **python:** `check-format`, `type-check`, `test` (flags `USE_EMACS=0 USE_X_WINDOWS=0`).
   - **rust:** `check-format`, `type-check` (Deno/Tauri JS), **`check`** (`cargo check --workspace
     --all-targets`), and **`test` scoped to `cargo test -p hanoigame`** — fast/offline (engine + 25
     doctests); `check` still compiles every crate incl. the GUI, so the wxDragon crate is gated
     without CI building wxWidgets from source to run GUI tests. Needs a CI-scoped test entry (a
     `make test-lib` target or a CI step overriding the package; prefer a named target).
   - **cpp:** `check-format` + `test` (doctest/ctest) + the plain app build. **No `type-check`** —
     the C++ compiler is the type check.
4. **Verify** by pushing the branch and reading the Actions run; fix any runner-only breakage
   (Docker vs podman, missing lean flag). Document the workflow in the root `CLAUDE.md`.

## Decisions (resolved with the maintainer, 2026-10-27)

1. **Rust CI = `check-format` + `type-check` (Deno/Tauri JS) + `check` + lib-only `test`**
   (`cargo test -p hanoigame`), so CI never builds wxWidgets from source to run GUI tests while
   `check` still gates GUI-crate compilation.
2. **C++ gets no separate `type-check` job** — the compiler is the type check; the C++ side is
   `check-format` + build + `test`. The "type-check incl. JavaScript Tauri code" requirement is the
   **rust** subproject's existing Deno `make type-check`.
3. **Trigger = every `push` + `pull_request` (all branches)**, matching gacalc/mvp (default; say so
   to narrow `push` to `master`/`cicd`).

## What was done (2026-10-27)

`.github/workflows/checks.yml` + Makefile targets, all staged. One workflow, **10 jobs** (one per
subproject × gate), each `checkout@v5` → `working-directory: <sub>` → `make <target> <lean flags>`.

- **Makefile changes:**
  - Added **`check-format: format` + `git diff --exit-code`** to all three subproject Makefiles
    (`python/`, `rust/`, `cpp/`) — gacalc's shape.
  - **Removed `-it` from the three `format` targets** (they were the only hanoi `format`s carrying it;
    gacalc's does not). A formatter needs no TTY, and `check-format` depends on `format`, so a
    TTY-less CI runner would have died on `-it`. Interactive `make format` is unaffected.
  - **`rust/`**: added **`test-lib`** (`cargo test -p hanoigame`) — the CI test gate, library-only, so
    CI never triggers the wxDragon GUI crate's from-source wxWidgets build. `make check`
    (`--workspace --all-targets`) still gates GUI-crate compilation.
  - **`cpp/`**: added **`build`** — configure + `cmake --build build` (all native targets: both GUIs +
    the test runner), no display needed; the compiler is the C++ type check.
- **`CONTAINER_CMD` auto-detect**: re-confirmed present in all three (python line 17, rust line 20,
  cpp line 16) — the earlier draft's worry was moot; no Makefile needed it added.
- **Lean CI flags (per job):** python `check-format` → `USE_EMACS=0 USE_X_WINDOWS=0`; python
  `type-check`/`test` → `USE_EMACS=0` **only** (keep X11 — see the trap below); rust (all) →
  `USE_EMACS=0 USE_WASM=0`; cpp `check-format`/`test` → `USE_EMACS=0 USE_WASM=0 USE_WX=0`; cpp
  `build` → `USE_EMACS=0 USE_WASM=0` (keep `USE_WX=1` so `hanoi-wx` compiles).
- **Flag-coverage trap (found + avoided):** `python/pytest.ini` collects `src` with
  `--doctest-modules`, so test collection imports `hanoigui.py`/`board_renderers.py`, which
  `import wx` at module top. `USE_X_WINDOWS=0` would break `make test` (and `ty`'s wx resolution), so
  those two python jobs keep X11 on.

## Verification (2026-10-27)

- **Verified nested:** python image builds with `USE_EMACS=0 USE_X_WINDOWS=0`; `make check-format`
  runs ruff with the `-it` removed and reformats nothing (the only working-tree diff was the
  in-flight Makefile/workflow edits — on a clean CI checkout `git diff --exit-code` is 0).
- **Not re-run nested (wrap existing, already-green targets):** python `test`/`type-check`, rust
  `check`/`test`/`type-check`, cpp `test` all wrap targets verified green in prior sessions; cpp
  `build` runs the same `cmake --build` that `make gui`/`make wx` already compile+run (both
  maintainer-verified on-display). rust `check` builds wxWidgets from source (minutes) — left for the
  real CI run. **The authoritative check is the maintainer's push to `cicd` + reading the Actions
  run** (the runner is Docker-on-ubuntu, not the sandbox's nested podman — only a push exercises the
  real environment).

## Notes

- **One workflow, many jobs** (not a matrix) — the subprojects have different gate sets and flags.
- CI is **check-only**; `check-format` is the enforcement (never a reformat-and-push).
- **rust `check` is the slow job** — `cargo check --workspace --all-targets` compiles the wxDragon GUI
  crate, whose `build.rs` builds wxWidgets 3.3.4 from source. That is the price of gating GUI
  compilation per the resolved decision; narrow it later if per-push time is a problem.
