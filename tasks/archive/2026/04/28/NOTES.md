# Towers of Hanoi — Working Notes

This file captures (a) my understanding of the existing code and the teaching
idea behind it, and (b) the next round of work Bill has scoped. Version
controlled so changes to either side stay visible.

---

## 1. Teaching philosophy (what the project is actually for)

The project is **not** a Hanoi solver and the goal is **not** to teach recursion
as such. The goal is to teach a human to solve Towers of Hanoi by hand, by
building up:

1. Solve for **1 disc**, from any peg to any peg (six trivial cases).
2. Solve for **2 discs**, from any peg to any peg, by *re-labelling the pegs*
   so the problem matches a 1-disc solution you already know, applying that
   solution as a black box, then putting the labels back.
3. Same trick for 3, then 4, then `n`.

The "peg relabelling" mechanic in the curses UI is the load-bearing part. It
lets the student treat their previous `n-1` solution as a recipe and replay it
under whatever orientation the current sub-problem needs (e.g. swap 2↔3 to run
an `n-1` solve, then swap back). This is the same idea recursion expresses,
but the student is doing the substitution themselves with their hands and eyes
instead of trusting a stack frame.

Every artifact in the repo reinforces this same idea in a different medium —
the bash pipeline, the iterative Python version, the by-hand RST tutorial, and
the curses game all model "solve small, relabel, replay."

---

## 2. What's in the repo

### `python/src/hanoigame/`

- **`hanoimodel.py`** — pure game state. `HanoiGame` holds three towers (lists
  used as stacks), the disk count, and the move counter. `move_options()`
  enumerates the at-most-six peg pairs and returns `ValidMove` objects, each of
  which bundles a `Move(from_peg, to_peg)` description with a zero-arg
  `action()` closure that actually performs the move. Also exposes layout
  helpers (`peg_visual_width`, `peg_gap`, `min_cols`, `min_rows`,
  `padding_left`, `disk_char_width`) used by the curses front-end. No I/O.

- **`hanoirecursive.py`** — pedagogical recursion. Hand-written `hanoi_1`,
  `hanoi_2`, `hanoi_3`, `hanoi_4` show the same recursive shape four times
  before generalising to `hanoi_n`. Each function is `@snoop()`-decorated so a
  student can watch the call/return trace. Args are named `i / t / g` (initial
  / temporary / goal) — the same I/T/G abstraction used in the RST tutorial.

- **`hanoiiterative.py`** — same algorithm, no recursion. Maintains the move
  list as a string of "1 -> 3" lines and grows it in a `while x <= n` loop by
  applying two label swaps to the previous solution: `swap_temporary_and_goal`
  (2↔3) and `swap_initial_and_temporary` (1↔2). This is the relabelling trick
  made fully explicit — exactly what the curses UI is asking the student to do
  in their head.

- **`hanoigame.py`** — curses front-end. `_main` wraps a three-phase loop:
  pick disk count → play → win/lose screen. `Labelling` is a 6-value `Enum`
  for the six peg permutations; `change_labels_on_pegs` and `peg_color`
  re-route both the displayed digit and its colour through that permutation.
  The move menu is built each tick from `game.move_options()`. Hotkeys: arrows
  + Enter to pick a move, `M` to toggle disc visibility, `1`–`6` to switch
  labelling, `Q` to quit.

  Two small things I noticed while reading (not blockers, just flagging):
  - `display_message(stdstr=…)` on line ~448 is a typo of `stdscr` — only
    reachable in the "no valid moves" safeguard, so it never fires in practice.
  - The `1`–`6` keys only cover three of the six `Labelling` cases mapped to
    the permutations a student would actually need; `4`/`5`/`6` are wired but
    not advertised in the on-screen hint ("Press 1 2 or 3 to change labels").

### `python/tests/test_hanoimodel.py`

Pytest coverage of `HanoiGame.__post_init__` and a four-move walk through
`move_options()` / `action()`, asserting both tower contents and the next
move list at each step. UI helpers from the model are not yet covered (see
`TODO.org`).

### `bash/`

Same pedagogy expressed as a Unix pipeline. `hanoi1.sh` prints the trivial
move; `hanoi2.sh`/`3`/`4` compose smaller solutions and pipe them through
relabel filters (`1to2.sh`, `2to3.sh`, …) which are each a one-liner
`exec tr '123' '…'`. `hanoin.sh` is the recursive generalisation.
`oneLineAtATime.sh` paginates the output one move per Enter press, intended
for stepping through the solution at the prompt.

### `docs/source/`

Sphinx tutorial that mirrors the curses game: `intro.rst` states the rules,
then `byhand1.rst` walks through all six 1-disc moves, `byhand2.rst`
introduces the I/T/G substitution, `byhand3.rst` extends it to 3 discs, and
`byhand4.rst` is currently a stub. Cross-references (`:ref:`) link each
sub-problem back to the smaller solution being reused — the "use my earlier
work as a black box" idea, on paper.

### `workbook/`

Four SVG worksheets (`hanoi1.svg` … `hanoi4.svg`) plus a Makefile that
renders them to PDF via Inkscape — printable companions to the RST tutorial.

### Build / dev environment

Containerised: `Dockerfile` builds on Fedora 44, `Makefile` provides `make
image` / `make shell` / `make docs` via podman. `entrypoint/entrypoint.sh`
installs the package, runs pytest, then builds Sphinx HTML/LaTeX/EPUB into
`/output/towersofhanoi/`. `entrypoint/format.sh` runs `ruff check --fix` and
`ruff format --line-length=80`; the bashrc override invokes it on shell exit.

---

## 3. Outstanding work

These extend the existing `TODO.org` entries (unit-test the UI helpers, build
a CLI, scriptable moves with save/replay) with more design intent.

### 3.1 Plain-text CLI front-end (no curses)

Same model (`HanoiGame`), pure stdin/stdout so it works under `oneLineAtATime`
style stepping, in pipes, in CI, and in a screen reader.

- Prompt for the number of discs at start.
- After every move, redraw the position as ASCII art using the same layout
  primitives the curses version uses (`peg_visual_width`, `padding_left`,
  `disk_char_width`, `total_game_content_width`) — keep the visual identical
  so a student moving between front-ends sees the same picture.
- Prompt for the next move as a free-form `from to` (e.g. `1 3`), reject
  illegal moves with an explanation rather than just refusing.
- On win, show move count vs. `2^n - 1` minimum, same as curses does.

Bill has given UI discretion here — match functionality, pick whatever
input shape works. Working assumption: typed commands (`1 3` for a move,
`relabel 1 3 2`, `apply <recipe>`) so the CLI grammar can be reused as the
curses command bar and as the wxWidgets button payloads.

### 3.2 Recipes — record, name, replay

When a game is won, the system should be able to capture the sequence of
moves as a **recipe** held in memory for the rest of the session, and let the
user replay that recipe later as a single step. This is the in-product
realisation of the teaching idea: "your past solution becomes a black box you
can drop into a bigger problem."

Sketch:

- A `Recipe` is an ordered list of `Move`s (re-use `hanoimodel.Move`),
  optionally annotated with the disc count it was solved for and a name the
  user gives it ("solve-3-from-1-to-3").
- After each win, prompt: *Save this solution as a recipe? Name?* Stored in a
  session-local registry; no disk persistence needed for v1.
- A new player command — `apply <recipe-name>` — replays the moves under
  the **current** peg labelling, not the labelling that was active when the
  recipe was captured. This is the load-bearing pedagogical moment: the
  student is partway through a bigger problem, swaps two labels on a hunch,
  realises *this is something I already solved*, and applies the saved recipe
  to watch it work. Concretely, a 2-disc recipe captured under `1 2 3` and
  replayed after the user swaps 2↔3 (so labels read `1 3 2`) executes the
  *same physical moves* the user would now type — the from/to indices in the
  recipe are interpreted through the current label permutation, exactly as
  `hanoiiterative.py` rewrites its move string with `swap_temporary_and_goal`.
- Step mode: replay one move at a time so the student can watch the recipe
  work and confirm it really is the same solution they would have typed.

Persistence (file save / load) is the `TODO.org` "scriptable moves" item and
can come after the in-memory version is working.

### 3.3 Curses UX rework

The current overlay-menu approach (move menu drawn on top of the board, plus
the message rows competing for the top of the screen) is what's bothering
Bill. Want suggestions for slicker patterns.

Things to consider:
- Function-key driven action bar pinned to the bottom row (mc / nano
  convention): `F1 Help  F2 Move  F3 Relabel  F4 Recipe  F10 Quit`.
- Or a single-keystroke command bar: type `13` to mean "1 → 3" and have it
  validated against `move_options()` before committing — this maps onto the
  CLI command grammar so both front-ends share the same input language.
- A dedicated, always-visible status panel for current labelling and saved
  recipes, instead of message rows that flash and scroll.
- Lose the per-move arrow-key picker entirely; show valid move pairs as a
  static list with their hotkeys and let the student type one.

This is open — the right answer probably depends on whether we keep the
"highlight the legal moves for me" affordance (good for first-time players)
or drop it (it does some of the puzzle's work for the student).

### 3.4 wxWidgets front-end

Same `HanoiGame` model. Display panel shows the board as monospace text
(reuse the same layout helpers — keep it visually identical to CLI/curses),
and the controls are real GUI widgets:

- Disc count chooser (spinner or dropdown).
- Six "From → To" buttons, enabled/disabled live from `move_options()`.
- Six relabelling buttons for the peg permutations.
- A recipe panel: list of saved recipes with **Save current**, **Replay**,
  **Step**, **Delete** buttons.
- Move counter and minimum-moves display.

Plain text rendering for the board keeps parity with the other two front-ends
and avoids dragging in image assets — the GUI value is in the controls, not
the visuals.

---

## 4. Small cleanup items spotted while reading

Recording these so they don't get lost; not asking to do them now.

- `hanoigame.py` line ~448: `stdstr=` typo for `stdscr=`.
- The on-screen "Press 1 2 or 3 to change labels" hint undersells the six
  available labellings (`1`–`6` are all wired).
- `hanoigame.py` has six near-identical `elif key == ord('N')` blocks that
  each define a one-line closure to set `labelling`. A small lookup table
  keyed by character would collapse these to one branch — only worth doing
  when the menu rework lands, since the whole keymap is changing anyway.
- `pyproject.toml` has `[tools.ruff]` (extra `s`) alongside the correct
  `[tool.ruff.lint]`; the typo'd table is silently ignored.
