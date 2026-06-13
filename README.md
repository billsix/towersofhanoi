# Towers of Hanoi

Example implementations of the Towers of Hanoi, in both **bash** and **Python**.
It's a teaching project: the focus is learning to solve the puzzle *by hand* via
**peg relabelling** — solve a small stack, then reuse that solution as a black box
for a bigger one by relabelling the pegs.

Runs on Linux, macOS, and Windows (WSL2, or mingw/cygwin).

## Python front-ends

Three front-ends share the same game model and commands:

- `hanoi` (a.k.a. `hanoigame`) — ncurses, in the terminal
- `hanoi-cli` — plain stdin/stdout (good for pipes and screen readers)
- `hanoi-gui` — wxPython window with a text or 2D-graphics board (needs an X display)

### Docker / Podman

Install podman and GNU make:

```sh
make image
make shell
```

Then run one of `hanoi`, `hanoi-cli`, or `hanoi-gui`. To run the GUI from inside
the container, forward your X socket when starting the shell — typically
`-e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix:Z` on Linux hosts.

### Plain Python

```sh
cd python
python -m venv venv
source venv/bin/activate
python -m pip install -e .
hanoi
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

`docs/` is a Sphinx book (`intro`, `byhand1..4`) that teaches the by-hand
relabelling method; `workbook/` has printable SVG worksheets. The container's
default build produces HTML/PDF/EPUB under `output/towersofhanoi/`.

## License

GNU GPL v2. See `LICENSE`.
