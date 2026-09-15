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

### Making the rebinding visible (the teaching *display*, 2026-09-14)

That relabel-and-replay is now *shown* to the student, not just performed, as an in-session step
(no persistence). The pure logic is shared, in `recipe.py`:
- `rebinding(labelling)` — each recipe label 1..3 → the physical peg it resolves to (the full
  labelling permutation; identity under `ONE_TWO_THREE`).
- `rebound_moves(moves, labelling)` — a move list rewritten onto physical pegs (works for a recipe's
  moves *or* a single typed move).
- `format_rebinding_table(moves, labelling, left_header=…)` — the three aligned text columns
  (moves-in-their-labels │ label→peg key │ rebound-to-pegs); empty under the default labelling.

Wiring, one behaviour across all three frontends: **CLI/curses** get it from the shared engine —
`_handle_apply` prepends the table, and `GameSession.move_teaching_lines(cmd, result)` supplies it
after a plain move. **Key architecture note:** `move_teaching_lines` lives beside `dispatch`, *not*
inside `_handle_move`, because the **GUI treats a move's non-empty `result.lines` as an error**
(illegal-move popup) — so teaching text must not ride a move's lines. The **wx GUI** instead shows a
non-modal three-panel dialog (two synced scroll lists flanking the key) from `_show_rebinding_dialog`.
The **curses** message area is only `MSG_AREA_LINES` tall, so output taller than it (the ~11-line
apply table) opens a scrollable pager (`_show_pager`). Work record:
`tasks/archive/2026/09/14/record-recipe-bindings-and-show-rebinding.md`.

### wx/GTK gotchas (both cost real debugging time — 2026-09-14/15)

- **Sizer alignment flags are orientation-specific.** A *vertical* alignment flag
  (`wx.ALIGN_CENTER_VERTICAL`) inside a **vertical** `BoxSizer` raises a `wxAssertionError` on GTK
  ("only horizontal alignment flags can be used in vertical sizers") — use `ALIGN_CENTER_HORIZONTAL`
  and let stretch spacers do vertical centering. (Mirror for horizontal sizers.)
- **Don't use radio menu items for an action that can be re-selected on wxGTK — use normal items.**
  wxGTK emits **no** `wx.EVT_MENU` when the user clicks the radio item GTK already considers active: the
  click is swallowed *before Python sees it*, so the handler never runs. GTK's active radio also
  persists across state resets (`_new_game`) and drifts from the model, so "the item GTK thinks is
  active" is frequently not the model's state — and clicking the item you actually want then does
  nothing. This caused a stubborn relabel bug (`hanoigui`, 2026-09): the relabel to the peg order left
  active by the *previous* game silently failed (repro: solve n=3 + save, n=4 ending on `2 1 3` + save,
  then n=5 → relabel to `2 1 3` did nothing). **Two fixes that operated in `_refresh`/`_on_relabel_menu`
  failed**, because the failing click produces no event at all — nothing handler-side can rescue it. The
  fix that worked: make the relabel items **normal (non-radio) `wxMenuItem`s** (which always emit on
  every click) and show the active one with a leading `●` bullet via `SetItemLabel` in `_refresh`
  (display-only; `SetItemLabel` emits nothing). The maintainer confirmed the exact repro relabels to
  `2 1 3` first-click after the change. Rule of thumb on wxGTK: a radio menu item is safe only when
  re-selecting the active choice is genuinely a no-op you never need an event for (e.g. board-style
  Text/Graphics, whose handler early-returns anyway); anything you might click again to re-fire must be
  a normal item. Never treat a wxGTK radio's checked state as source of truth — keep state in the model
  and reflect it into the menu's *labels*.

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

## Typing, docstrings & the type-check gate (2026-09-15)

The whole Python tree (`src` **and** `tests`) is **fully typed, dataclass-ified, and
Google-docstringed**, and stays that way via a gate:

- **`make type-check`** runs `ty` (Astral) over `src` then `tests` in-container
  (`entrypoint/type-check.sh` — portable host/container, *accumulating* so both steps always
  run and any diagnostic fails the gate). Kept **separate** from `make format` (ruff) so
  formatting stays fast; `ty` is installed in the base image, so no Dockerfile dep was needed
  beyond `COPY`ing the script.
- **Maximal local annotations are a deliberate hanoi-specific choice** (2026-09-15): *every*
  binding is annotated — every signature (params + returns), and every local, module constant,
  and loop/unpack/`with`-as target — not just the ones that "add information". This is stricter
  than the shared `~/.claude/reference/python-coding-standard.md` default, which was left
  unchanged. The only bindings left bare are the ones that **can't** be: comprehension /
  generator-expression variables (separate scope, no syntax), and the `xrcctrl =
  wx.xrc.XRCCTRL` function alias (annotating its return narrows XRCCTRL's dynamic result and
  breaks the specific-control method calls downstream).
- **Line width is one source of truth:** `[tool.ruff] line-length = 80` in
  `python/pyproject.toml` governs *both* `ruff format` and the E501 lint; `entrypoint/format.sh`
  passes **no** `--line-length` flag. (They used to disagree — config defaulted to 88, the
  script forced 80.)

**Typing patterns worth knowing before editing the GUI/model** (each cleared a real `ty`
diagnostic): `hanoigui.HanoiFrame.session` is declared **non-Optional** (`_new_game`, called in
`__init__`, always sets it before any handler runs); `board_renderers` passes the narrowed
`game`/`labelling` into `_paint_game` rather than reading the Optional attributes; a
`registry.get(name)` whose `name` came from `registry.names()` is narrowed with `assert … is
not None`; `HELP_TEXT: str` so `.splitlines()` is `list[str]` (not the invariant
`list[LiteralString]`); and `BoardRenderer.__init__(self, parent)` exists only to declare the
constructor contract so `type[BoardRenderer]` is constructible with a parent. Also fixed a
latent bug on the way: `ValidMove.action`'s `default_factory=noop` had set the default to
`None` (the *result* of `noop()`); it is now `default_factory=lambda: noop`.

## Cross-links

- `tasks/record-recipe-bindings-and-show-rebinding.md` + `tasks/latex-workbook-solve-1-5.md` — both build
  on the recipe/relabelling model mapped here.
