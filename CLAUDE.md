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

## Module map (teaching intent per file)

Every artifact models the same "solve small, relabel, replay" idea in a
different medium:

- `python/src/hanoigame/hanoimodel.py` — pure game state (`HanoiGame`, `Move`,
  `ValidMove`, `move_options()`). No I/O.
- `python/src/hanoigame/hanoirecursive.py` — pedagogical recursion: hand-written
  `hanoi_1..4` repeat the recursive shape four times before `hanoi_n`
  generalises. `@snoop()`-decorated so a student can watch the call/return
  trace; args named `i / t / g` (initial / temporary / goal) to match the RST
  tutorial.
- `python/src/hanoigame/hanoiiterative.py` — same algorithm, no recursion:
  grows a move-list string by applying two label swaps
  (`swap_temporary_and_goal` = 2↔3, `swap_initial_and_temporary` = 1↔2) to the
  previous solution. The relabelling trick made fully explicit.
- `python/src/hanoigame/` also holds `presenter` (render + 6 peg labellings),
  `commands` (typed parser), `engine` (shared dispatcher), `recipe`
  (record/replay in label-space), the three front-ends (`hanoicli`,
  `hanoigame`, `hanoigui`), `board_renderers` (text + `wx.GraphicsContext`),
  and `hanoi.xrc`.
- `bash/` — the same pedagogy as a Unix pipeline: `hanoi1.sh` prints the
  trivial move; `hanoi2/3/4.sh` compose smaller solutions piped through
  `tr`-based relabel filters (`1to2.sh`, `2to3.sh`, …); `hanoin.sh` is the
  recursive generalisation; `oneLineAtATime.sh` paginates output one move per
  Enter.
- `docs/source/` — Sphinx tutorial mirroring the game: `intro` states the
  rules, `byhand1` walks all six 1-disc moves, `byhand2` introduces the I/T/G
  substitution, `byhand3` extends to 3 discs, `byhand4` is a stub.
  `:ref:` cross-links each sub-problem back to the smaller solution it reuses.
- `workbook/` — four SVG worksheets (`hanoi1..4.svg`) + a Makefile that renders
  them to PDF via Inkscape; printable companions to the RST tutorial.

## Documentation model

- **`README.md`** — user-facing overview (running the front-ends, bash demos,
  the book). This file (`CLAUDE.md`) — agent/contributor reference (conventions,
  module map, teaching intent).
- **`tasks/`** — active, in-flight work, one file per task.
- **`tasks/archive/<YYYY>/<MM>/<DD>/`** — completed task docs, kept for history.
  The original step-by-step roadmap (`PLAN.md`, steps 1–8 done, step 9 OpenGL
  attempted and reverted) and the original design-notes doc (`NOTES.md`) were
  archived here once their content was folded into README/CLAUDE.

In-flight work (see `tasks/`):
- [`tasks/container-build-cleanup.md`](tasks/container-build-cleanup.md) — the
  Makefile `docs:` target is malformed (no command), and `entrypoint.sh` touches
  `/output/modelviewprojection/.nojekyll` (should be `towersofhanoi`).
- [`tasks/image-export-import-targets.md`](tasks/image-export-import-targets.md)
  — add the standard `image-export` / `image-import` Makefile pair.

Optional follow-ons (descoped from the completed roadmap): recipe persistence
to disk, a step-mode replay UI, a curses pass 2.
