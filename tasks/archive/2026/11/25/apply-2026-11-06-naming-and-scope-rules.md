# Apply the 2026-11-06 naming and scope rules across hanoi (the Python package under `python/`)

**Done:** 2026-11-25 (work commit; the archive move follows). Source: the maintainer (William Emerison Six <billsix@gmail.com>, 2026-11-06), who asked for the survey in geometricalgebra and then "add a similar task to every other python project in opt"; run on 2026-11-25 as the sixth repository of the seven (after mvp, methodfinder, mathnotebooks, multivariate-math and epix-mirror).

## What this did

Five rules entered the shared Python standard on 2026-11-06 (github.com/billsix/runClaudeInContainer, `tasks/reference/python-coding-standard.md`: "Inline a value used once, and name it in a comment instead of a binding" and "What earns an extraction"): inline a binding used once; a binding used twice does not automatically earn a name; declare a name at the point of use; nest a helper with one caller inside that caller; shadow deliberately when nesting. The task surveyed `python/src/hanoigame/`, `python/tests/`, `python/tools/` and the repository-root `tools/`, and refactored the package without changing behaviour. The Rust and C++ ports and the vendored Emacs trees are out of scope.

## Decisions

- **Survey first, then discretion; a helper a test imports stays at module level** (William Emerison Six <billsix@gmail.com>, 2026-11-24, for the mvp task; applied to all repositories in this batch).
- **Survey:** `tasks/adhoc/apply-2026-11-06-naming-and-scope-rules/discover.py` wrote 524 leads: 256 `ONCE`, 220 `TWICE`, 16 `FAR`, 32 `ONE_CALLER`. Most `ONCE` leads in the library modules were comprehension and `for` targets, not bindings.
- **Nested (rule 4), by `nest_one_caller.py` (19 helpers):** `_move_or_error` into `parse` (`commands.py`); `_print_board`, `_prompt_save`, `_play_game`, `_prompt_disc_count` and `_read_line` into `run`, and `_play_game`'s helpers (`hanoicli.py`); `_check_size`, `_show_too_small`, `_required_rows`, `_required_cols`, `_show_pager`, `_draw_board`, `_draw_top_status`, `_draw_messages`, `_draw_hint`, `_setup_colours` and `_prompt_disc_count` (`hanoigame.py`, the curses TUI); `default_label_row` into `render` (`presenter.py`); `_explain_illegal` into `apply_iter` (`recipe.py`). A second run found nothing.
  - **Kept at module level on purpose:** `swap_initial_and_temporary` and `swap_temporary_and_goal` in `hanoiiterative.py` (`--keep`: they are the named steps of the teaching solution, and the Rust and C++ ports mirror them); the helpers the tool skipped for a doctest (`_common_prefix`, `collides_with_peg`, `hanoi_2`, `label_to_tower`, `padding_left`, `peg_center_x`, `rebound_moves`) and for being named in another file (`_completions`, `_redraw`, `apply_iter`).
  - **The ports:** the nested names are private helpers of the Python front-ends and of `presenter.render`; none appears in `rust/` or `cpp/` (`git grep` of `default_label_row` there found nothing), so the ports read the same as before.
- **Inlined or moved (rules 1 and 3), three places:** `recipe` in `engine.save_recipe` (the call moved into `registry.save(...)`; `overwrote` is still computed first); `width` in `presenter.default_label_row`; and in `recipe.format_rebinding_table`, `rows` into the `for` header, with `lw` and `mw` moved down to the `lines` list that first reads them.
- **Left alone, with the reason:** the GL and GUI modules (`hanoigl.py`, `hanoigui.py`, `board_renderers.py`: GL handles, widgets, picked-disc state and uniform values, 44 and 47 `ONCE` leads, a display is needed to see them, and the mvp and multivariate-math precedent leaves such blocks alone); `test_*.py` (named inputs, expected values and case tables); `tools/gen_byhand.py` at the repository root (outside every format gate; it already has 21 ruff findings against the project's configuration, and nesting its helpers into `main` added four more `E501`; it was nested and reverted; the generator itself reproduces `docs/source/byhand4.rst` and `byhand5.rst` byte-identically either way); `engine.py`'s message words (`plural`, `noun`, `top_from`, `top_to`: they sit inside f-strings that read worse with the conditional inline); `overwrote` in `save_recipe` (it must be read before `registry.save` changes the registry); comprehension and `for` targets, which the survey also lists.
- **17 comment and docstring lines** that the deeper indent pushed past 80 columns were reflowed as whole paragraphs (the longer `Args:` entries were reworded to fit, not wrapped), and one long f-string was split into two adjacent literals.

## Result

- Applied: the 19 nestings, the three inlines and moves, and the reflow; 6 files changed in `python/src/hanoigame/`. Behaviour is unchanged.

## Verification (containerized, 2026-11-25)

- `make type-check` exit 0 and `make test` 155 passed, 2 skipped (the two skips are the by-hand drift guard, which the isolated Python image skips by design).
- `ruff format` and `ruff check` on the six changed files: no findings, nothing left to reformat. The repository's `make format` was not run because its `ruff check --fix` rewrites files tree-wide.
- `tools/gen_byhand.py` rewrote `byhand4.rst` and `byhand5.rst` with no change to `docs/`: the generator is unchanged and the book pages are in step.
- **The curses TUI** (`hanoigame.py`, where eleven helpers moved) ran under a pseudo-terminal through `tasks/adhoc/apply-2026-11-06-naming-and-scope-rules/tui_smoke.py`: it drew the board, took 3 discs and two moves, showed the history and quit with exit status 0 and no traceback.
- Not exercised: the wx and OpenGL front-ends were not touched; the CLI is covered by `test_hanoicli.py`.

## Owed

The maintainer runs `make tui` once for the pager (`PgUp`/`PgDn` on a long output such as an applied recipe) and the terminal-too-small screen, the two nested helpers the pty smoke did not reach.
