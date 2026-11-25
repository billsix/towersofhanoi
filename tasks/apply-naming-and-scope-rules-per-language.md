# Apply the naming and scope rules, per language (Rust, C++, bash, JavaScript)

**Done:** 2026-11-25 (William Emerison Six <billsix@gmail.com>, the same day: "make a task for all of them, but only start work on hanoi and spimulator"). Written by the fleet task `tasks/archive/2026/11/25/apply-naming-and-scope-rules-per-language-across-repositories.md`. Python had its own pass earlier that day (`tasks/archive/2026/11/25/apply-2026-11-06-naming-and-scope-rules.md`).

## What this did

Applied the five naming and scope rules (inline a binding used once; two uses do not earn a name; declare at the point of use; nest a one-caller helper; shadow deliberately) to hanoi's Rust, C++, bash and JavaScript, each as its standard words them: the "Locals and helpers" sections of `rust-coding-standard.md`, `cpp-coding-standard.md` and `javascript-coding-standard.md`, and "Names and scope in bash" in `shell-and-gate-scripts.md` (github.com/billsix/runClaudeInContainer `tasks/reference/`). Behaviour is unchanged. Ten files changed.

**Survey.** `survey_names_and_scope.py` (same directory as the standards) gave 408 lines of leads: functions named exactly twice and locals named exactly twice inside their function. Every lead in the shared engine and the text front-ends was read; the GUI files were read for one-caller helpers only.

## Rust

- **Nested (rule 4), nine helpers, each a nested `fn` at the top of its one caller** (none reads a caller's local): `default_label_row` into `render` (`hanoigame/src/presenter.rs`; it lost its `pub`, which nothing outside the crate used, and the Python oracle nests it the same way); `explain_illegal` into `Replay::step` (`recipe.rs`); in the TUI (`hanoi/src/main.rs`) `row_to_line` into `board_lines`, `status_line` into `draw_play`, `draw_pager` into `pager`, `complete_line` into `play_game`, `app` into `main`; in the CLI (`hanoi-cli/src/main.rs`) `prompt_save` into `play_game` and `run_interactive` into `main`. Done with `nest_rust_fn.py` (below), then `rustfmt`.
- **Inlined (rule 1), in `hanoigame`:** `width` in `default_label_row`; `target` in `label_to_tower`; `fp` and `tp` in `labels_to_towers`, in `rebound_moves` and in `handle_apply`'s recorder call; `peg` in `rebinding`; `f` and `t` in `valid_moves_str`; `recipe` in `save_recipe` (`overwrote` is still read first). Four names that existed only to be a `format!` capture became named arguments with no binding: `noun` (twice), `plural`, `extra`.
- **Left alone, with the reason:**
  - the `GameSession::handle_*` methods and `truncate_to` (methods; the five handlers are the arms of the dispatch);
  - `swap_initial_and_temporary`, `swap_temporary_and_goal` and the `two_minus_1_i_to_t`-style locals in `solvers/` (each names a step of the relabelling method, which is what the code teaches; the Python oracle keeps them too);
  - `failed` in `recipe::apply` (read before `result` is moved), `overwrote` (read before the save), `replay`, `registry`, `terminal` and the readers (`let mut`, borrowed mutably), `result` in the TUI's `main` (read before `ratatui::restore()`);
  - `width` in `handle_list`, `pvw` in `render` and `rows` in `format_rebinding_table` (computed once, read inside a loop); `results` in `handle_apply` (the standard keeps a chain out of a `for` header);
  - everything in `#[cfg(test)]` modules (inputs, expected values, case tables);
  - the single-use locals of the TUI and CLI front-ends (names of layout areas, hint texts and prompt strings that label what is drawn);
  - the three GUI crates (`hanoi-gui`, `hanoi-egui`, `tauri/src-tauri`): widget construction, event handlers and `#[tauri::command]` functions, whose callers are the toolkit; changes there need a display to see. This follows the Python pass, which left its GUI and GL modules alone.

## C++

- **Rule 4 changed nothing.** A one-caller helper stays a named function above its caller, and that is how the code already stood (`detail::explain_illegal` in `src/recipe.hpp`; the anonymous-namespace helpers and per-frame `draw_*` functions in `main.cpp` and `hanoiwx.cpp`).
- **Inlined (rule 1), in the engine headers:** `peg` in `rebinding` and `fp`, `tp` in `rebound_moves` (`src/recipe.hpp`); `target` in `label_to_tower` and `noun` in `format_win_celebration` (`src/presenter.hpp`).
- **Left alone:** `disk` in `Game::apply` (read before `pop_back`); `order` and `rows` (computed once, read in a loop); `fp`, `tp`, `apply_name` in `main.cpp` (copied before `clear_pending()`); `th`, `td`, `te` in `hanoiwx.cpp` (out-parameter targets); the rest of the two GUI files, for the reason given under Rust.

## JavaScript (`rust/tauri/frontend/main.js`)

- **Nested (rule 4), six functions:** `renderRelabelMenu`, `renderRecipeMenu`, `renderApplyView` and `showWinTeaching` into `render`; `initMenuBar` and `initBoardDrag` into `init`. Each reads only its parameters and module state. `renderRelabelMenu(s)` and `renderRecipeMenu(s)` take the snapshot under the name `render` uses for it, a deliberate shadow. Done with `nest_js_fn.py`, then `deno fmt`.
- **Inlined (rule 1):** `radius` in `roundRect`, `labels` in the relabel handler, `steps` in the recipe-view handler (the cast form carries its type).
- **Left alone:** `init` (called once from the module's top level, so there is nothing to nest it into); `count` and `num` (snapshots of `latest` taken before an `await`); `willOpen` and `firstWin` (read before the next statement changes their source); `rgb` (a palette helper beside `darken`, called from the per-frame board drawing); the geometry names in `drawBoard` and `boardPegCentres`; the row templates in `renderApplyView`.

## bash

- **Inlined (rule 1):** `here` in `cpp/tools/check-no-network.sh` and `rust/tools/check-no-network.sh` (it fed one `cd`).
- **Left alone:** `cpp_dir`, `scan_dir`, `web_files`, `egui_files` and `pattern` in those scripts (the settings a reader edits: what is scanned and for what); `VER` in `cpp/tools/update-imgui.sh` (a command substitution whose failure should not hide inside an `echo`). Rule 4 does not apply to bash, and the 44 scripts hold one function. The `entrypoint/` install scripts had no leads.

## Verification (2026-11-25)

- **Rust**, in the `hanoi-rust` image (the gate's own commands, run against the existing image): `cargo fmt --check` exit 0; `cargo check --workspace --all-targets` exit 0; `cargo test --workspace` exit 0 (5, 21, 30 and 32 tests in the four suites that have any).
- **JavaScript**, same image: `tools/check-no-network.sh` OK; `deno check --check-js --no-lock main.js`, `deno lint main.js` and `deno fmt --check` all exit 0.
- **C++**, in the `hanoi-cpp` image: `cmake --build build` built `hanoi-tests`, the ImGui app and `hanoi-wx`; `ctest` 100% passed (20 doctest cases, 86 assertions when run directly); `clang-format` left the two headers as committed.
- **bash:** both `check-no-network.sh` scripts print OK, one of them also from another working directory; `shellcheck` is quiet on both; both keep mode 100755.
- **Not exercised:** no front-end was run. The TUI, the CLI and the Tauri frontend changed only by moving functions and by the inlines listed; the compiler and Deno's checker cover the moves, and the CLI's tests cover its game loop.

## Owed to the maintainer

On a display: `make tauri` once (menus open and close, relabel, recipe view, the first-win dialog, dragging a disc), and `make tui` once (the pager on a long output, tab completion of a recipe name).

## How

`nest_rust_fn.py` and `nest_js_fn.py` (removed with this archive; in this repository's history under `tasks/adhoc/apply-naming-and-scope-rules-per-language/`) cut a top-level function with its doc comment and paste it at the top of its caller's body. Each refuses to act unless it finds one definition of each function, and a second run reports the helper already nested and changes nothing.
