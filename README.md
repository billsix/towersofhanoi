# Towers of Hanoi

Example implementations of the Towers of Hanoi, in **bash**, **Python**, **Rust**, and **C++**.
It's a teaching project: the focus is learning to solve the puzzle *by hand* via
**peg relabelling** — solve a small stack, then reuse that solution as a black box
for a bigger one by relabelling the pegs.

Runs on Linux, macOS, and Windows (WSL2, or mingw/cygwin).

## Layout

Each language is a **self-contained subproject** with its own container image and `make`
targets — build and run it from its own directory:

- **`python/`** — the canonical implementation (three front-ends).
- **`rust/`** — a Rust reimplementation kept in sync feature-for-feature, including the
  Tauri desktop app at `rust/tauri/`.
- **`cpp/`** — a C++ port with a Dear ImGui GUI, building a native binary **and** WebAssembly.
- the repo **root** builds the Sphinx **book** (`docs/`) and the printable worksheets
  (`workbook/`), and holds the **bash** demos. (The root keeps its own `Dockerfile`/`Makefile`
  — unlike a plain directory — because the book is cross-cutting: it pulls code listings from
  `python/` and aggregates `docs/`, so `make docs` lives at the root, which sees the whole repo.)

(Containers use Fedora + podman; install podman and GNU make.)

## Python

Three front-ends share the same game model and commands:

- `hanoi` (a.k.a. `hanoigame`) — ncurses, in the terminal
- `hanoi-cli` — plain stdin/stdout (good for pipes and screen readers); at a terminal,
  Tab completes commands and saved-recipe names
- `hanoi-gui` — wxPython window with a text or 2D-graphics board (needs a display)

```sh
cd python
make cli      # hanoi-cli
make tui      # hanoi (ncurses)
make wx       # hanoi-gui (opens on your desktop; X11 + Wayland forwarded automatically)
make shell    # a dev shell; inside, run hanoi / hanoi-cli / hanoi-gui
```

Plain Python, no container:

```sh
cd python
python -m venv venv && source venv/bin/activate
python -m pip install -e .
hanoi
```

## Rust

The same game in **Rust** — a `hanoigame` library crate with four front-ends:

```sh
cd rust
make cli      # stdin/stdout CLI
make tui      # ratatui terminal UI
make wx       # wxDragon desktop GUI
make tauri    # Tauri desktop app (webview UI; text or canvas board)
```

The GUI/desktop targets forward your display automatically. (The first `make wx` is slow —
it builds wxWidgets from source; later runs reuse the cached build.)

## C++

A **Dear ImGui** GUI over the same game engine, built two ways from one codebase:

```sh
cd cpp
make gui          # native desktop window (X11 + Wayland forwarded automatically)
make webassembly  # build web/index.{html,js,wasm}
make serve        # build the wasm if needed, then serve it at http://localhost:8000
```

## Bash demos

The bash scripts build solutions by piping smaller solutions through `tr`-based
relabelling filters (`1to2.sh`, `1to3.sh`, `2to3.sh`, …):

```sh
cd bash
./hanoi1.sh                        # the 1-disc solve:  1 -> 3
./hanoi2.sh                        # 2-disc, composed from 1-disc solves via relabelling
./hanoin.sh 4                      # generic n-disc
./hanoi3.sh | ./oneLineAtATime.sh  # step through a solution one move at a time
```

## The book & worksheets

`docs/` is a Sphinx book (`intro`, `byhand1..5`) that teaches the by-hand relabelling
method; `workbook/` has printable worksheets — the `hanoi1..4.svg` solution diagrams and
`induction-workbook.tex`, a blank fill-in induction booklet (cover + one sheet per n=1..5).
From the repo root, `make docs` builds the book (HTML/PDF/EPUB) into `output/towersofhanoi/`.
Build the worksheet PDFs with `make -C workbook` (needs Inkscape + pdflatex/TikZ).

## License

GNU GPL v2. See `LICENSE`.
