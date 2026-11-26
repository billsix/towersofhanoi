# Apply the naming and scope rules, per language (Rust, C++, bash, JavaScript)

**Done:** 2026-11-25 (William Emerison Six <billsix@gmail.com>, the same day: "make a task for all of them, but only start work on hanoi and spimulator"). Written by the fleet task `tasks/archive/2026/11/25/apply-naming-and-scope-rules-per-language-across-repositories.md`. Python had its own pass earlier that day (`tasks/archive/2026/11/25/apply-2026-11-06-naming-and-scope-rules.md`).

## What this did

Applied the five naming and scope rules (inline a binding used once; two uses do not earn a name; declare at the point of use; nest a one-caller helper; shadow deliberately) to hanoi's Rust, C++, bash and JavaScript, each as its standard words them: the "Locals and helpers" sections of `rust-coding-standard.md`, `cpp-coding-standard.md` and `javascript-coding-standard.md`, and "Names and scope in bash" in `shell-and-gate-scripts.md` (github.com/billsix/runClaudeInContainer `tasks/reference/`). Behaviour is unchanged. Ten files changed in the first pass and six more in the second (the GUI code; see "Second pass").

**Survey.** `survey_names_and_scope.py` (same directory as the standards) gave 408 lines of leads: functions named exactly twice and locals named exactly twice inside their function. Every lead was read: the shared engine and the text front-ends in the first pass, the GUI crates and files in the second.

## Rust

- **Nested (rule 4), nine helpers, each a nested `fn` at the top of its one caller** (none reads a caller's local): `default_label_row` into `render` (`hanoigame/src/presenter.rs`; it lost its `pub`, which nothing outside the crate used, and the Python oracle nests it the same way); `explain_illegal` into `Replay::step` (`recipe.rs`); in the TUI (`hanoi/src/main.rs`) `row_to_line` into `board_lines`, `status_line` into `draw_play`, `draw_pager` into `pager`, `complete_line` into `play_game`, `app` into `main`; in the CLI (`hanoi-cli/src/main.rs`) `prompt_save` into `play_game` and `run_interactive` into `main`. Done with `nest_rust_fn.py` (below), then `rustfmt`.
- **Inlined (rule 1), in `hanoigame`:** `width` in `default_label_row`; `target` in `label_to_tower`; `fp` and `tp` in `labels_to_towers`, in `rebound_moves` and in `handle_apply`'s recorder call; `peg` in `rebinding`; `f` and `t` in `valid_moves_str`; `recipe` in `save_recipe` (`overwrote` is still read first). Four names that existed only to be a `format!` capture became named arguments with no binding: `noun` (twice), `plural`, `extra`.
- **Left alone, with the reason:**
  - the `GameSession::handle_*` methods and `truncate_to` (methods; the five handlers are the arms of the dispatch);
  - `swap_initial_and_temporary`, `swap_temporary_and_goal` and the `two_minus_1_i_to_t`-style locals in `solvers/` (each names a step of the relabelling method, which is what the code teaches; the Python oracle keeps them too);
  - `failed` in `recipe::apply` (read before `result` is moved), `overwrote` (read before the save), `replay`, `registry`, `terminal` and the readers (`let mut`, borrowed mutably), `result` in the TUI's `main` (read before `ratatui::restore()`);
  - `width` in `handle_list`, `pvw` in `render` and `rows` in `format_rebinding_table` (computed once, read inside a loop); `results` in `handle_apply` (the standard keeps a chain out of a `for` header);
  - everything in `#[cfg(test)]` modules (inputs, expected values, case tables);
  - the GUI crates and the remaining front-end locals were left in the first pass and done in the second (below).

## C++

- **Rule 4 changed nothing.** A one-caller helper stays a named function above its caller, and that is how the code already stood (`detail::explain_illegal` in `src/recipe.hpp`; the anonymous-namespace helpers and per-frame `draw_*` functions in `main.cpp` and `hanoiwx.cpp`).
- **Inlined (rule 1), in the engine headers:** `peg` in `rebinding` and `fp`, `tp` in `rebound_moves` (`src/recipe.hpp`); `target` in `label_to_tower` and `noun` in `format_win_celebration` (`src/presenter.hpp`).
- **Left alone:** `disk` in `Game::apply` (read before `pop_back`); `order` and `rows` (computed once, read in a loop); `fp`, `tp`, `apply_name` in `main.cpp` (copied before `clear_pending()`); `th`, `td`, `te` in `hanoiwx.cpp` (out-parameter targets). The rest of the two GUI files was done in the second pass (below).

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
## Second pass: the GUI code and the front-end locals (2026-11-25)

The first pass left the GUI crates and files alone, as the Python pass had. The maintainer asked the same day whether every language was fully done ("if not, do it"), so the rest was read lead by lead and the bindings that qualify were inlined by hand.

- **Rust wx GUI (`rust/hanoi-gui/src/main.rs`), nested (rule 4):** four more one-caller helpers that read none of their caller's locals became nested `fn`s: `draw_board_dc` and `apply_recipe_by_name` into `main`, `draw_legal_diagram` into `show_howto_dialog`, `show_monospace_dialog` into `view_recipe`. **Inlined:** `avail_w` in `board_peg_centres` and in `draw_board_dc`; `w` in the two drag handlers; `status_bar` (now one call chain); `noun` in `update_history` (a named `format!` argument).
- **Rust egui (`rust/hanoi-egui/src/main.rs`):** `avail_w` in `board_geometry`; `marker` in the rebinding grid (a named `format!` argument); `n` in the "New Game (Same Size)" item.
- **Rust TUI (`rust/hanoi/src/main.rs`):** `width` in `board_lines`; `default_name` and `msg` in `play_game`.
- **Tauri backend (`rust/tauri/src-tauri/src/main.rs`):** `fp` and `tp` in `apply_structured`'s recorder call; `message` in `relabel`.
- **C++ wx (`cpp/hanoiwx.cpp`):** `avail_w` in `paint_graphics`; `width` in the diagram's `on_paint`; `item_id` and `view_pos` in `build_menu_bar`; `row_h` in `build_history_panel`; `w` in the refresh.
- **C++ ImGui (`cpp/main.cpp`):** `avail_w` in the board; `relabelled` in `draw_recipe_view`; `has_name` in the save modal; `name` and `n` in the discard-or-save modal; the two `io` references.
- **Kept, by group, in all of the above:**
  - widget and dialog handles that later lines configure (`body`, `diagram`, `got_it`, `label`, the menu items);
  - clones made to move into a closure (`d`, `dlg_for_close`, `panel_clone`, `list_for_select`) and `RefMut` and `MutexGuard` guards (`st`);
  - a dispatch result read before the session's state is swapped back (`result` in each front-end's `dispatch`, `msg` in each `save`), and `relabelled` read before the move or the apply;
  - the layout quantities that later lines draw with (`peg_top_y`, `ref_y`, `y`, `disc_h`, `peg_w`, `char_w`, `line_h`, `visible_cols`, `visible_rows`, `h_pad`, `v_pad`, `bottom_w` and `upper_w`): each is the name of a coordinate or a size, and the chain they form is the layout;
  - pairs and triples bound together (`from_label` with `to_label`; `a`, `b`, `c` in the status line; `left`, `mid`, `right` in the rebinding rows);
  - values that take several lines to compute (`later`, `text`, `rest`, `fill`, `key`, `moves_for_dialog`, `options`): substituted into the next statement they would bury it;
  - `item` in the ImGui menu (its `c_str()` is what the call takes), `fp`, `tp`, `apply_name` (copied before `clear_pending()`), the out-parameter targets, the `overwrote` flags;
  - event handlers and `#[tauri::command]` functions with one textual caller (`on_key`, `on_history_select`, `review_back`, `show_recipe` and the rest): the toolkit is their caller.

**Checked for the second pass:**
- `hanoi-rust` image: `cargo fmt --check` exit 0, `cargo check --workspace --all-targets` exit 0, `cargo test --workspace` exit 0 (5, 21, 30, 32 tests); `cargo check --all-targets` exit 0 in `tauri/src-tauri` and in `hanoi-egui`, each its own workspace.
- `hanoi-cpp` image: `cmake --build build` built all three programs; `ctest` 100% passed.
- **Run on a virtual display** (Xvfb in the sandbox, its socket mounted into the containers, `GDK_BACKEND=x11`), with a screenshot of each read: the C++ wx GUI, the C++ ImGui GUI, the Rust wx GUI (again after its four helpers were nested) and the Tauri app each start and draw the board with its three pegs, the discs, the labels, the menus, the history panel and the How to Play dialog. The Tauri window confirms that `main.js` loads and renders after the first pass nested its `render*` and `init*` functions.
- **Not run:** the egui app. Under X11 it stops at start with "Library libxkbcommon-x11.so could not be loaded"; the `hanoi-rust` image does not ship that library (the app is run on Wayland on the host). It compiles. Nothing was clicked or dragged in any GUI.

## Owed to the maintainer

On a real display: one move by drag and one by keyboard in each GUI, a relabel, a recipe view, and `make egui` once (it was not run here). `make tui` once for the pager and tab completion of a recipe name.

## How

`nest_rust_fn.py` and `nest_js_fn.py` (removed with this archive; in this repository's history under `tasks/adhoc/apply-naming-and-scope-rules-per-language/`) cut a top-level function with its doc comment and paste it at the top of its caller's body. Each refuses to act unless it finds one definition of each function, and a second run reports the helper already nested and changes nothing.
