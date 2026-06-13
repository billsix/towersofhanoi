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
- **Bash demos** (`bash/`) — `hanoi1..4.sh` / `hanoin.sh` compose solutions
  through `tr`-based relabel filters (`1to2.sh`, `2to3.sh`, …); `oneLineAtATime.sh`
  paginates a solution one move at a time.
- **Sphinx book** (`docs/`) — `intro` + `byhand1..4` walk the relabelling method.
- **Worksheets** (`workbook/`) — printable SVGs (→ PDF via Inkscape).
- 72 pytest tests pass (model, presenter, commands, CLI, recipes).

## Layout

- `python/src/hanoigame/` — `hanoimodel` (state), `presenter` (render + 6 peg
  labellings), `commands` (typed parser), `engine` (shared dispatcher), `recipe`
  (record/replay in label-space), the three front-ends (`hanoicli`, `hanoigame`,
  `hanoigui`), `board_renderers` (text + `wx.GraphicsContext`), `hanoi.xrc`.
- `python/tests/` — 72 tests across 5 files.
- `bash/` — 12 scripts (solves + relabel filters).
- `docs/` — Sphinx source; `workbook/` — SVG worksheets.
- `NOTES.md` (design philosophy + module map), `PLAN.md` (step-by-step roadmap:
  steps 1–8 done; an OpenGL renderer was tried in step 9 and reverted).

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

## Tasks (in-flight)

- [`tasks/container-build-cleanup.md`](tasks/container-build-cleanup.md) — the
  Makefile `docs:` target is malformed (no command), and `entrypoint.sh` touches
  `/output/modelviewprojection/.nojekyll` (should be `towersofhanoi`).
- `PLAN.md` lists optional follow-ons: recipe persistence to disk, a step-mode
  replay UI, a curses pass 2.
