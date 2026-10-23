# hanoi

A Towers of Hanoi **teaching project**. The goal is *not* recursion for its own
sake — it teaches solving the puzzle by hand via **peg relabelling**: solve 1
disc, then reuse that as a black box for 2 discs by relabelling the pegs, and so
on. Every artifact (bash pipelines, Python front-ends, the Sphinx book, printable
worksheets) reinforces that "solve small, relabel, replay" idea.

## Status

- **Python package** (`python/src/hanoigame/`, setuptools) with three front-ends
  over one shared model + command grammar + dispatcher:
  - `hanoi` / `hanoigame` — ncurses TUI
  - `hanoi-cli` — plain stdin/stdout (pipes, screen readers); readline
    tab-completion (verbs, recipe names) at an interactive TTY
  - `hanoi-gui` — wxPython (XRC UI; text or 2D-graphics board renderer)
- **Rust port** (`rust/`, a Cargo workspace) — a parallel reimplementation kept **in sync with the
  Python, feature-for-feature** (the Python stays the behaviour oracle; never removed). A `hanoigame`
  library crate (model/commands/engine/presenter/recipe/solvers) + three binaries: `hanoi-cli`,
  `hanoi` (ratatui/crossterm TUI), `hanoi-gui` (wxDragon GUI; programmatic UI, solid-fill DC board);
  75 `cargo test`s. Run via `make rust-cli`/`rust-tui`/`rust-wx` (needs an image built with
  `USE_RUST=1`, the Makefile default — `entrypoint/04-install-rust.sh` installs the full native
  toolchain wxDragon's from-source wxWidgets build needs; the `make rust-*` targets persist cargo's
  build + download caches in gitignored `rust/.container-*` dirs). Build facts + the wxDragon gotchas:
  runClaudeInContainer `tasks/reference/rust-gui-tui-and-ecosystem.md`; the port record:
  `tasks/archive/2026/10/23/port-to-rust-wxdragon.md`. A **Tauri v2** desktop app (`tauri/`, a separate
  crate — a static webview UI over the same `hanoigame` crate; text or `<canvas>` board; `make
  rust-tauri`) rounds out the set — done and play-verified. Records:
  `tasks/archive/2026/10/23/port-to-tauri.md` and runClaudeInContainer
  `tasks/reference/tauri-desktop-apps.md` (follow-ups: `tasks/tauri-frontend-lint.md`,
  `tasks/tauri-frontend-js-options.md`).
- **Bash demos** (`bash/`), **Sphinx book** (`docs/`, `intro` + `byhand1..5`), and
  printable **worksheets** (`workbook/`: the `hanoi1..4.svg` solution diagrams plus
  `induction-workbook.tex`, a blank fill-in induction booklet) all reinforce the
  relabelling method (see Layout for the file breakdown).
- 130 pytest tests pass (model, presenter, commands, CLI, recipes, byhand-drift).

## Layout

- `python/src/hanoigame/` — `hanoimodel` (state), `presenter` (render + 6 peg
  labellings), `commands` (typed parser), `engine` (shared dispatcher), `recipe`
  (record/replay in label-space), the three front-ends (`hanoicli`, `hanoigame`,
  `hanoigui`), `board_renderers` (text + `wx.GraphicsContext`), `hanoi.xrc`.
- `python/tests/` — 130 tests across 6 files (incl. `test_byhand_drift.py`, which
  fails if `docs/source/byhand4/5.rst` drift from `tools/gen_byhand.py`).
- `bash/` — 12 scripts (solves + relabel filters).
- `tools/` — repo dev scripts. `gen_byhand.py` generates `docs/source/byhand4/5.rst`
  (guarded by `test_byhand_drift.py`; regenerate, don't hand-edit those pages).
- `docs/` — Sphinx source; `workbook/` — `hanoi1..4.svg` solution diagrams (→ PDF via
  Inkscape) + `induction-workbook.tex` blank induction booklet (→ PDF via pdflatex/TikZ).
- `tasks/` — active work; `tasks/archive/<YYYY>/<MM>/<DD>/` — completed task
  docs. See "Documentation model" and "Module map" below.

## Build / container workflow

Fedora-44 + podman family template.

- `make image` — build the image; full by default (`BUILD_DOCS=1`, Sphinx/TeX Live, ~1.94 GB),
  host **or** nested. Pass `MINIMAL_IMAGE=1` for a lean image (`BUILD_DOCS=0`, ~1.15 GB) — a small
  export/airgap build; it still runs the pytest gate. `MINIMAL_IMAGE` is build content, independent
  of `NESTED_PODMAN` (run capability); the sandbox does not set it, so a nested `make image` builds
  full (renamed 2026-09-27 from the old nested-inferred `NESTED_PODMAN`; the disk-backed inner store
  makes full fit nested). Override a single flag with `make image BUILD_DOCS=1`; `make docs` needs
  `BUILD_DOCS=1`.
- `make shell` — dev shell; inside, run `hanoi` / `hanoi-cli` / `hanoi-gui`. Display
  passthrough for the wxPython GUI is on by default: `USE_X_WINDOWS=1` installs the
  X11/Wayland client libs (`entrypoint/03-install-xwindows.sh`) and `make shell` forwards
  the host's X11 (`DISPLAY` + `/tmp/.X11-unix`) and Wayland (`WAYLAND_DISPLAY` +
  `XDG_RUNTIME_DIR`) sockets, so `hanoi-gui` opens on the host display. Unlike `BUILD_DOCS`
  this stays on when nested (modelled on modelviewprojection); disable with
  `make image USE_X_WINDOWS=0`. hanoi's GUI is 2D (wx/Cairo), so no OpenGL/mesa is installed.
- `make format` — ruff check+format the Python (line width from pyproject config).
- `make type-check` — run `ty` over the Python (`src` + `tests`); fails on any diagnostic.
- The image `ENTRYPOINT` installs the package, runs `pytest --exitfirst`, then
  builds the book (html/latexpdf/epub) into `/output/towersofhanoi/`.

Without the container: `cd python && python -m venv venv && . venv/bin/activate &&
pip install -e . && hanoi`.

## Conventions

- Python, formatted with **ruff** (`ruff check --fix` + `ruff format`); the line
  width (80) is set once in `[tool.ruff] line-length` in `python/pyproject.toml` — it
  governs the formatter *and* E501, so `format.sh` passes no `--line-length` flag.
  `make format` runs it; it also runs on shell exit.
- **Fully typed, dataclass-ified, and Google-docstringed.** *Every* binding is annotated
  — a hanoi-specific **maximal** choice (signatures, locals, constants, loop/`with`
  targets), stricter than the shared standard's default. `make type-check` runs `ty` over
  `src` + `tests`; keep it green. Rationale + the typing patterns:
  `tasks/reference/architecture-overview.md` ("Typing, docstrings & the type-check gate").
- All three front-ends go through the same `engine.dispatch` + `commands.parse` +
  `presenter.render` — keep them thin; logic belongs in the shared layers.
- Recipes are stored in the user's *labels* and replayed through the *current*
  labelling — that label-space transparency is the teaching point. Preserve it.

## Documentation model

- **`README.md`** — user-facing overview (running the front-ends, bash demos,
  the book). This file (`CLAUDE.md`) — lean agent/contributor reference.
- **`tasks/`** — active, in-flight work, one file per task (surfaced by the
  session-start scan). **`tasks/archive/<YYYY>/<MM>/<DD>/`** — completed task
  docs, kept for history.

**Reference docs:** `tasks/reference/architecture-overview.md` — the dispatch data-flow
across the three frontends + the default-label-space recipe invariant, the **per-file
teaching intent (module map)**, the **wx/GTK frontend gotchas** (sizer alignment flags;
why the relabel menu uses normal — not radio — items), and the doc/roadmap history (archived
`PLAN.md`/`NOTES.md`, the reverted OpenGL step, descoped follow-ons). Read it before touching
the engine/recipe subsystem, the wx GUI, or for the per-file "why".
