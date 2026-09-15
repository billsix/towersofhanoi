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
  - `hanoi-cli` — plain stdin/stdout (pipes, screen readers)
  - `hanoi-gui` — wxPython (XRC UI; text or 2D-graphics board renderer)
- **Bash demos** (`bash/`), **Sphinx book** (`docs/`, `intro` + `byhand1..4`), and
  printable **SVG worksheets** (`workbook/`) all reinforce the relabelling method
  (see Layout for the file breakdown).
- 124 pytest tests pass (model, presenter, commands, CLI, recipes).

## Layout

- `python/src/hanoigame/` — `hanoimodel` (state), `presenter` (render + 6 peg
  labellings), `commands` (typed parser), `engine` (shared dispatcher), `recipe`
  (record/replay in label-space), the three front-ends (`hanoicli`, `hanoigame`,
  `hanoigui`), `board_renderers` (text + `wx.GraphicsContext`), `hanoi.xrc`.
- `python/tests/` — 124 tests across 5 files.
- `bash/` — 12 scripts (solves + relabel filters).
- `docs/` — Sphinx source; `workbook/` — SVG worksheets.
- `tasks/` — active work; `tasks/archive/<YYYY>/<MM>/<DD>/` — completed task
  docs. See "Documentation model" and "Module map" below.

## Build / container workflow

Fedora-44 + podman family template.

- `make image` — build the image (`BUILD_DOCS=1` adds Sphinx/TeX Live).
- `make shell` — dev shell; inside, run `hanoi` / `hanoi-cli` / `hanoi-gui`
  (the GUI needs X forwarding).
- The image `ENTRYPOINT` installs the package, runs `pytest --exitfirst`, then
  builds the book (html/latexpdf/epub) into `/output/towersofhanoi/`.

Without the container: `cd python && python -m venv venv && . venv/bin/activate &&
pip install -e . && hanoi`.

## Conventions

- Python, formatted with **ruff** (`ruff check --fix` + `ruff format
  --line-length=80`); runs on shell exit.
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
