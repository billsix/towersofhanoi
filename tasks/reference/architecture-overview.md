# hanoi — architecture overview

**Reference document** — the command-dispatch data flow shared by all three frontends, and the one
genuinely subtle invariant (recipes stored in default-label space, reinterpreted under the current
labelling). This repo's first reference doc. Not a task; update in place. Created 2026-08-27
(William Emerison Six <billsix@gmail.com>) from a direct read (load-bearing anchors verified).

## Data flow: model → dispatch → commands → presenter → frontends

Input (from any frontend) → `commands.parse` produces a `Command` (a union of command types,
`commands.py`) → `GameSession.dispatch` (`engine.py`) runs an isinstance chain and returns a
`DispatchResult` (`lines` to show + a `quit` flag) → the frontend renders `lines` and honours `quit`.
The **three frontends share `engine.dispatch`**:

- **CLI** — `hanoicli.py` (stdin loop; the sole printer of the valid-moves string).
- **curses** — `hanoigame.py` (reimplements the terminal-size check locally — see the orphaned helpers
  below).
- **wx GUI** — `hanoigui.py` (XRC-driven; recipe apply/save wired to buttons, e.g. `recipe_apply` at
  `hanoigui.py:164,199`).

## The subtle invariant (the durable insight): recipes live in default-label space

Recipes (`recipe.py`) store their moves in **default-label space** and are **reinterpreted under the
current labelling at apply time** — that relabel-and-replay is the teaching point.
- `apply_iter` (`recipe.py:129`) is the production replay path (no disk-count check, so a small recipe
  can act as a **sub-routine** inside a larger solve).
- `apply` (`recipe.py:184`) is a **test-only** convenience (production uses `apply_iter`).
- Relabelling maths live in the presenter (`presenter.py` — the `Labelling` enum + tuple maps;
  `peg_color` follows the *label*, not the physical peg).
- The recipe registry is **RAM-only** (`recipe.py:92`) — no persistence.

## Dead / orphaned / unwired code (grounds the follow-on)

- **Orphaned presenter helpers:** `presenter.min_cols` (`presenter.py:138`), `min_rows` (`:143`), and
  `render_with_legend` (`:222`) are not used by production — the **curses** frontend reimplements its own
  size check (`hanoigame.py`) instead of calling `min_cols`/`min_rows`.
- **Test-only:** `recipe.apply` (`recipe.py:184`) — engine uses `apply_iter`.
- **Unwired teaching modules:** `hanoirecursive.py` / `hanoiiterative.py` are standalone teaching scripts
  with no importers (run directly, not part of the game).

## Follow-on

`tasks/wire-or-remove-orphaned-presenter-helpers.md` — route the curses size check through
`presenter.min_cols`/`min_rows` (or delete those helpers), and mark the teaching modules as non-wired.

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

## Documentation & roadmap history

- The original step-by-step roadmap (`PLAN.md`, steps 1–8 done, step 9 OpenGL
  attempted and reverted) and the original design-notes doc (`NOTES.md`) were
  archived under `tasks/archive/<YYYY>/<MM>/<DD>/` once their content was folded
  into README/CLAUDE.
- Optional follow-ons (descoped from the completed roadmap): recipe persistence
  to disk, a step-mode replay UI, a curses pass 2.

## Cross-links

- `tasks/record-recipe-bindings-and-show-rebinding.md` + `tasks/latex-workbook-solve-1-5.md` — both build
  on the recipe/relabelling model mapped here.
