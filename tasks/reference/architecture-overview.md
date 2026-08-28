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

## Cross-links

- `tasks/record-recipe-bindings-and-show-rebinding.md` + `tasks/latex-workbook-solve-1-5.md` — both build
  on the recipe/relabelling model mapped here.
