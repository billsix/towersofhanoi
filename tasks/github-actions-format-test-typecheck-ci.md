# GitHub Actions CI: format-check + test + type-check on push (Python, Rust, C++)

**Status:** proposed — needs go-ahead.
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

**Depends on [[cpp-unit-tests-with-doctest]]** for the C++ `make test` stage (do that first).

## Context (cold start)

- Repo: github.com/billsix/towersofhanoi (mounted as `hanoi`), branch `cicd`. **No
  `.github/workflows/` exists yet.** Per-language subprojects, each its own container Makefile:
  `python/`, `rust/`, `cpp/`.
- **The CI pattern to copy** (from gacalc's `.github/workflows/checks.yml`): thin wrapper, one job per
  gate, `uses: actions/checkout@v5` then `run: make <target> <lean-flags>`. The jobs never modify the
  repo — `make check-format` runs the formatter in the disposable runner checkout then fails on
  `git diff --exit-code`; `test`/`type-check` are read-only. `CONTAINER_CMD` auto-detects
  podman→docker, so the identical `make` target runs on the `ubuntu-latest` Docker runner and on the
  maintainer's podman host. CI passes lean flags to skip heavy optional layers
  (gacalc: `BUILD_DOCS=0 USE_EMACS=0 USE_SPYDER=0`; mvp: `… USE_JUPYTER=0 USE_X_WINDOWS=0`).
- **Current gate targets per subproject** (what exists / what's missing):
  - `python/`: has `format` (ruff), `type-check` (ty + `check_local_annotations`), `test` (pytest +
    doctests). **Missing: `check-format`.**
  - `rust/`: has `format` (rustfmt + Deno fmt), `check` (`cargo check --workspace --all-targets`),
    `type-check` (the Tauri **JS** frontend via Deno), `test` (`cargo test --workspace`). Has
    `CONTAINER_CMD` auto-detect. **Missing: `check-format`.**
  - `cpp/`: has `format` (clang-format). **Missing: `check-format`, `test` (← the prerequisite task),
    and it uses no `CONTAINER_CMD` auto-detect yet** (confirm + add).

## Plan

1. **Add `check-format` to each subproject Makefile** — `check-format: format` then
   `git diff --exit-code` (the gacalc shape: run the formatter, fail if it changed a tracked file).
   Three small targets, each `## `-documented and `.PHONY`.
2. **Confirm/add `CONTAINER_CMD ?= $(shell command -v podman … || echo docker)` to `python/` and
   `cpp/` Makefiles** (rust already has it) so every `$(CONTAINER_CMD)` line runs under Docker on the
   runner. Required — a hardcoded `podman` fails on `ubuntu-latest`.
3. **Write `.github/workflows/checks.yml`** — `on: [push, pull_request]`, one job per
   (subproject × gate), each `checkout@v5` → `cd <sub> && make <target> <lean CI flags>`:
   - **python:** `check-format`, `type-check`, `test` (flags `USE_EMACS=0 USE_X_WINDOWS=0`).
   - **rust:** `check-format`, `type-check` (the JS/Tauri Deno gate), **`check`**
     (`cargo check --workspace --all-targets` — compiles every crate incl. the GUI), and **`test`
     scoped to `cargo test -p hanoigame`** (fast, offline — the engine + 25 doctests). This is the
     resolved answer to the wxWidgets-from-source problem: compilation of the GUI crate is still
     gated by `check`, but CI does not build wxWidgets from source to *run* GUI-crate tests. This
     needs a CI-scoped test entry — either a `make test-lib` target (`cargo test -p hanoigame`) or
     the CI step overriding the package; decide at implementation, prefer a named target.
   - **cpp:** `check-format` and `test` (from the prerequisite task), plus the plain app build. **No
     separate `type-check`** — the C++ compiler is the type check.
4. **Verify** by pushing the branch and reading the Actions run; fix any runner-only breakage (Docker
   vs podman, missing lean flag). Document the workflow in the root `CLAUDE.md`.

## Notes / design choices (using discretion unless a question below says otherwise)

- **One workflow, many jobs** (not a matrix) — the three subprojects have different gate sets and
  flags, so explicit jobs read more clearly than a matrix with exclusions.
- **Lean CI flags** keep each image build small (no emacs, no wasm toolchain, no X/GUI libs the CI
  doesn't exercise). The rust GUI crate is the one exception that forces a question.
- CI is **check-only**: it never pushes a reformat. `check-format` is the enforcement.

## Decisions (resolved with the maintainer, 2026-10-27)

1. **Rust CI = `check-format` + `type-check` (Deno/Tauri JS) + `check` + lib-only `test`.** The
   `test` job runs `cargo test -p hanoigame` (fast, offline: engine + 25 doctests); `make check`
   (`cargo check --workspace --all-targets`) still compiles every crate incl. the GUI, so the
   wxDragon crate is gated without CI building wxWidgets from source to run GUI tests.
2. **C++ gets no separate `type-check` job** — the compiler is the type check, so the C++ side is
   `check-format` + build + `test`. The "type-check incl. the JavaScript Tauri code" requirement is
   satisfied by the **rust** subproject's existing Deno `make type-check` over the Tauri JS.
3. **Trigger = every `push` + `pull_request` (all branches)**, matching gacalc/mvp — taken as the
   default; say so if you want `push` narrowed to `master`/`cicd` (PRs would still run everywhere).
