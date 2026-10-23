# Port the whole hanoi program to Rust (wxDragon for the GUI)

**Status:** in progress — **all four front-ends built, tested, and staged 2026-10-23** (see Work
record). Remaining: a `make image` rebuild to activate the new run targets, and the maintainer's
host display-verification of the TUI/GUI. Large
initiative; the maintainer is new to Rust, so clarity and idiomatic code matter as much as the port.

> **CONSTRAINT (maintainer, 2026-10-23): the Python version is kept FOREVER. This is NOT a
> replacement — it is a parallel copy kept in sync, feature for feature.** The Rust lives in its own
> `rust/` subtree beside `python/`; both front-end sets stay runnable; a feature added to one is
> added to the other. The Python package is also the behaviour oracle the Rust is verified against.
> Never remove or deprecate the Python.
**Priority:** 5 **Difficulty:** 8
**Created:** 2026-10-23 (William Emerison Six <billsix@gmail.com>). Requested: port everything done
in Python — the wxWidgets GUI, the engine, the command line, *everything* — to Rust, using
**wxDragon** for the GUI. A Tauri port is the follow-up (`tasks/port-to-tauri.md`).

## Work record (2026-10-23)

**Built + staged** in `rust/` (a Cargo workspace; the Python stays, per the CONSTRAINT):

- **`hanoigame` library crate** — the shared core: `model`, `commands` (parser), `engine`
  (`GameSession` dispatcher), `presenter` (6 labellings + layout + text render), `recipe`
  (Recorder/Registry/Replay + rebinding tables), `solvers` (iterative + recursive). **51 unit tests**
  reproducing the Python core suite, incl. Bill's `apply_through_relabel_solves_subproblem`.
- **`hanoi-cli`** — stdin/stdout front-end over any `BufRead`/`Write`; **19 tests** = every Python CLI
  test (the worked example's exact board, capture-under-relabel). Interactive **`rustyline`
  tab-completion** (command verbs + recipe names) is wired via a `LineReader` abstraction that keeps
  the scripted/piped path byte-identical; the pure `completions` logic stays unit-tested.
- **`hanoi` TUI** — ratatui 0.30 / crossterm 0.29 port of the ncurses UI (coloured board, status,
  message pager, input line, disc prompt, win/save/play-again); **5 `TestBackend` headless tests**.
- **`hanoi-gui`** — wxDragon 0.9.23 programmatic GUI: menu (New/Same/Exit/About), relabel menu (6
  items + active bullet), two board renderers (monospace text + a solid-fill DC graphics board) with
  a View toggle, 6 move buttons, recipes (list + Save/Apply/Show + double-click), rebinding dialog.
  Compiles warning-free; the Xvfb smoke launches it without crashing (display-verify is the
  maintainer's, on host wxGTK).

**Gates:** `cargo fmt --check` + warning-clean `cargo build` + `cargo test` (**75 tests**) all green,
offline for the core/CLI. `cargo clippy` NOT run — `clippy` isn't installed in the sandbox yet (a
base-list add was offered).

**Deviations from the plan, recorded:**
- **Error strategy (decision #4):** `thiserror`/`anyhow` were NOT pulled — the core has no fallible
  I/O surface needing them; `model::MoveError` is a plain std enum (`Display` + `std::error::Error`).
  Revisit if a future fallible API warrants `thiserror`.
- **GUI graphics renderer:** solid fills (the wxDC model), not the wxPython `GraphicsContext`
  gradients/shadows — wxDragon exposes only wxDC (the capability-section caveat, now also in the
  shared `rust-gui-tui-and-ecosystem.md`).
- **Recipe `apply_iter` (lazy generator) → a `Replay::step(&mut game)` stepper** (a Rust `Iterator`
  can't let the caller observe the game between steps); the shared registry → `&mut RecipeRegistry`
  on the session (the GUI adapts it via a transient session inside `Rc<RefCell<GuiState>>`).
- **Recipe-show / rebinding** are message dialogs, not the Python's scrollable 3-panel dialog (same
  teaching content).
- **Corrected (build deps):** wxDragon does NOT use the system wxGTK — `wxdragon-sys` **downloads
  wxWidgets 3.3.4 and statically builds it** (a `reqwest`/native-tls build-dep). The real build deps:
  `openssl-devel` (for that download — the error the maintainer hit on `make rust-wx`), `gtk3-devel`
  (pulled by `wxGTK-devel`, to compile wx), and `libSM-devel`/`libICE-devel` (the `-lSM`/`-lICE`
  static-link fix). The build needs network + a cached target dir (`rust/.container-target`); it is
  not offline-reproducible as-is. Recorded in the shared `rust-gui-tui-and-ecosystem.md`.

**Container / Makefile (staged):** a gated `USE_RUST` Dockerfile ARG + `entrypoint/04-install-rust.sh`
(rust/cargo/rustfmt + `wxGTK-devel` + `libSM/libICE-devel`), `python3-wxpython4` added to
`03-install-xwindows.sh` (the Python wx GUI couldn't run in-container before), and six Makefile run
targets: `python-cli`/`tui`/`wx` and `rust-cli`/`tui`/`wx`. **The rust-\* and python-wx targets need a
`make image` rebuild** to pick up the new packages (not done here — the full image is heavy). Both
sandboxes' base lists gained `wxGTK-devel`/`libSM-devel`/`libICE-devel`; learnings harvested to the
shared reference doc runClaudeInContainer `tasks/reference/rust-gui-tui-and-ecosystem.md`.

**Remaining:** the maintainer's host display-verify of the TUI + GUI; the `make image` rebuild to
activate the `rust-*`/`python-wx` run targets; optionally add `clippy` to the sandbox base list for
the lint gate. When the display-verify passes, this archives.

## BLUF

Reimplement the entire `python/src/hanoigame/` package and its three front-ends in **Rust**: a
shared library crate for the teaching core (model, command grammar, engine/dispatcher, presenter +
the six peg labellings, label-space recipes, iterative/recursive solvers, board renderers) plus
three binaries — the plain CLI, the ncurses-style TUI, and the **wxDragon** GUI — behaviourally
faithful to the Python, with the 130 Python tests reproduced as Rust tests. "Done" = all three Rust
front-ends run in the container and match the Python ones' behaviour, the ported test suite is
green, `cargo fmt --check` + `cargo clippy -D warnings` + the build are clean, and the GUI
display-verifies on the maintainer's host. Follow the shared **Rust coding standard**
(runClaudeInContainer `tasks/reference/rust-coding-standard.md`, github.com/billsix/runClaudeInContainer;
mounted at `~/.claude/reference/rust-coding-standard.md`) throughout — read it before writing Rust.

## Context (read first)

- **Read `tasks/reference/architecture-overview.md` first** — it holds the dispatch data-flow across
  the three front-ends, the **default-label-space recipe invariant** (recipes are stored in the
  user's *labels* and replayed through the *current* labelling — the teaching point; preserve it),
  the per-file teaching intent (module map), and the **wx/GTK frontend gotchas** (sizer alignment
  flags; the relabel menu uses normal, not radio, items). Those gotchas carry straight into wxDragon.
- **What "everything" is — the Python package** (`python/src/hanoigame/`, entry points in
  `python/pyproject.toml` `[project.scripts]`):
  - **Shared core (port to a library crate):** `hanoimodel.py` (peg/disc state), `commands.py`
    (typed command parser), `engine.py` (the dispatcher all front-ends share), `presenter.py`
    (render + the six peg labellings), `recipe.py` (record/replay in label-space),
    `board_renderers.py` (a text renderer + a `wx.GraphicsContext` 2D renderer),
    `hanoiiterative.py` / `hanoirecursive.py` (the two solvers).
  - **Front-ends (port to binaries):** `hanoigame.py` → `hanoi` (ncurses TUI); `hanoicli.py` →
    `hanoi-cli` (plain stdin/stdout for pipes/screen readers; readline verb/recipe tab-completion at
    a TTY); `hanoigui.py` → `hanoi-gui` (wxPython: loads `hanoi.xrc`, a `wx.TextCtrl` text board or a
    `wx.GraphicsContext` 2D board, a menubar bound by `XRCID`).
  - **Tests:** `python/tests/` — 130 tests across `test_hanoimodel`, `test_presenter`,
    `test_commands`, `test_hanoicli`, `test_recipe`, `test_byhand_drift`.
- **Out of scope for this task** (language-independent teaching artifacts, leave in place): the
  Sphinx book (`docs/`), the bash demos (`bash/`), the printable worksheets (`workbook/`), and
  `tools/gen_byhand.py` (which generates `docs/source/byhand4/5.rst`, guarded by
  `test_byhand_drift.py`). Those stay Python/TeX. Decide (open question) whether the Rust test suite
  needs a byhand-drift equivalent or whether that check stays in the Python side.
- **The maintainer has never used Rust.** Write idiomatic, well-commented Rust to the shared
  standard — this port doubles as their introduction to the language. Favour the clear form; explain
  the *why* in comments where Rust's ownership/borrowing choices are non-obvious.

## wxDragon capability check — VERIFIED 2026-10-23 (it has everything needed)

Researched online and by reading the cloned source (github.com/AllenDang/wxDragon, crate
**`wxdragon` 0.9.21**, wrapping **wxWidgets 3.3.1** via a `wxdragon-sys` C wrapper; Apache-2.0/MIT).
Every wx feature the Python GUI uses is present:

1. **2D custom drawing — YES, via the wxDC model** (`rust/wxdragon/src/dc/`). A `DeviceContext`
   trait with the full primitive set — `set_pen`, `set_brush`, `set_font`, `draw_line`,
   `draw_rectangle`, **`draw_rounded_rectangle`** (exactly right for discs), `draw_circle`,
   `draw_ellipse`, `draw_polygon`, `draw_text`, `draw_bitmap`, clipping + scale/origin transforms —
   on `PaintDC` / **`AutoBufferedPaintDC`** (flicker-free, for frequent redraws) / `ClientDC` /
   `MemoryDC`. The paint idiom is `panel.on_paint(move |_| { let dc = AutoBufferedPaintDC::new(&panel);
   /* draw */ });` with `panel.set_background_style(BackgroundStyle::Paint)` at init.
   **Caveat (minor, cosmetic):** wxDragon exposes the DC model, **not** `wxGraphicsContext`, so there
   is no built-in anti-aliasing / alpha-compositing path. The Hanoi board (pegs as rectangles, discs
   as rounded rectangles) renders fine on the DC; if the Python's `wx.GraphicsContext` was used for
   smooth edges, that is a small visual downgrade, not a functional gap. (`wxdragon-sys` could bind
   `wxGraphicsContext` later if AA is wanted — out of scope.)
2. **Menus — YES** (`rust/wxdragon/src/menus/`): `Menu`/`MenuBar`/`MenuItem`, `MenuBuilder` with
   `append_item` (`ItemKind::Normal`), `append_check_item`, `append_radio_item`, `append_separator`;
   `Frame::set_menu_bar`. **Normal items are the default** — the arch-doc gotcha (the relabel menu
   must use *normal*, not radio, items) is just `append_item` / `ItemKind::Normal`.
3. **XRC — present** (`xrc` feature: an `xrc` module with `XmlResource`/`get_xrc_id` and an
   `include_xrc!` macro that generates a *typed* UI struct at compile time). But the idiom differs
   from Python's runtime `XmlResource.Load` + `LoadMenuBar` + `XRCID`. **Recommendation: build the UI
   programmatically in Rust** — the hanoi window is small (a menubar, a text/graphics panel, move
   buttons, a new-game dialog), every piece has a builder, and programmatic construction is the more
   idiomatic, type-safe path; retire `hanoi.xrc` for the Rust GUI (keep it only if the Python
   front-end lives on). `include_xrc!` stays available if the maintainer prefers to keep the XRC.
4. **TextCtrl multiline — YES** (`TextCtrlStyle::MultiLine`, `is_multiline()`); set a fixed-width
   font for the monospace text board. Frame, Panel, Button, dialogs, and sizers are all present.

**Verdict: no GUI blocker — proceed with programmatic wxDragon + the DC drawing model.** wxDragon
wraps the C++ wxWidgets 3.3.1 library, so the Dockerfile must install the wxGTK dev packages (and
wxDragon can build wxWidgets from source if absent — confirm which the image should do). The
core/CLI/TUI don't depend on any of this, so build them first regardless.

## Plan (phased — core first, GUI last; each phase its own commit)

This is 3+ sizeable sequential chunks; if the maintainer wants per-front-end review/commit
boundaries, promote it to an umbrella + step-tasks. Kept as one doc for now (don't over-scaffold).

1. **Workspace + core library crate.** A Cargo workspace: a `hanoigame` library crate for the
   shared core, binary crates (or `src/bin/`) for the three front-ends. Port `hanoimodel`,
   `commands`, `engine`, `presenter` (+ the six labellings), `recipe`, the two solvers, and the
   **text** board renderer. Port the core tests (`test_hanoimodel`/`presenter`/`commands`/`recipe`)
   as Rust `#[test]`s. This is the bulk of the teaching logic and has no GUI dependency.
2. **`hanoi-cli`** (plain stdin/stdout + a readline-equivalent — `rustyline` — for verb/recipe
   tab-completion at a TTY; keep pipe/screen-reader mode clean). Port `test_hanoicli` as an
   integration test.
3. **`hanoi` TUI** (the ncurses front-end → a Rust terminal UI; `crossterm`/`ratatui` or a curses
   binding — decide). Behaviour-faithful to the Python TUI.
4. **`hanoi-gui`** via wxDragon, per the capability check above: the text board first, then the 2D
   graphics board; the relabel menu as normal (not radio) items (the arch-doc gotcha).

Keep the front-ends **thin** — all logic in the shared crate, exactly as the Python keeps them thin
over `engine.dispatch` + `commands.parse` + `presenter.render`.

## Container / build (conformance to the template)

hanoi follows the Fedora-44 + podman template. The port adds a Rust toolchain and wxWidgets:

- Install Rust (rustup or the Fedora `rust`/`cargo` packages) via an `entrypoint/0N-install-rust.sh`
  group script the Dockerfile dispatches (per "Host-agnostic setup belongs in a script"), and the
  **wxGTK development packages** wxDragon links against. Gate both behind the existing
  `USE_X_WINDOWS` (GUI) / a new build flag as appropriate; keep `MINIMAL_IMAGE` able to drop the GUI.
- Self-contained-image rule: vendor the crates at image-build (`cargo fetch` into a committed layer)
  so an exported image builds offline, and rebuild only hanoi's own source from the bind-mount at
  runtime (`cargo build --offline`). Keep the build tree **outside** the repo mount (a fixed
  `/opt/hanoi-build` target dir) so a host `target/` doesn't collide. See the personal overlay's
  "Self-contained images + live source".
- Makefile targets mirroring the Python ones: build, run each front-end, `cargo fmt`/`clippy` as the
  format/lint gate, `cargo test` as the test gate; thread `PODMAN_RUN_FLAGS` into every `run` line.

## Gates / verify

- `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, warning-clean `cargo build`.
- `cargo test` — the ported 130-test equivalent green (core logic, CLI integration).
- **Behaviour fidelity:** compare each Rust front-end against the Python one on the same inputs
  (same move sequences, same recipe record/replay in label space, same rendered boards). The
  label-space recipe transparency is the invariant that must survive the port.
- **GUI display** verification is the maintainer's (host wxGTK).

## Decisions (resolved 2026-10-23 — maintainer: "go with your recommendation")

1. **Crate layout:** a **Cargo workspace** in a new `rust/` subtree — a `hanoigame` library crate
   (the shared core) + binary crates `hanoi` (TUI), `hanoi-cli`, `hanoi-gui`. Clean lib/bin split;
   each front-end thin over the lib.
2. **TUI:** **`ratatui` + `crossterm`** (modern, pure-Rust, portable), behaviour-faithful to the
   Python ncurses TUI.
3. **GUI:** **programmatic wxDragon** + the **DC drawing model** (`AutoBufferedPaintDC` + `on_paint`),
   relabel menu as normal items (see the verified capability section). `hanoi.xrc` stays with the
   Python front-end; the Rust GUI builds its UI in code.
4. **Error strategy:** **`thiserror` in the `hanoigame` lib, `anyhow` in the binaries** (per the
   shared Rust standard).
5. **byhand-drift:** **stays in Python** (`tools/gen_byhand.py` + `test_byhand_drift.py` guard
   Python/TeX book pages — out of the Rust scope).
6. **Keep the Python:** **kept forever, in sync** — see the CONSTRAINT banner at the top. Not a
   decision to revisit; the Python is permanent and the Rust tracks it feature-for-feature.

## Pointers

- `python/src/hanoigame/` — the source of truth being ported; `python/tests/` — the 130-test oracle.
- `tasks/reference/architecture-overview.md` — dispatch flow, recipe invariant, module map, wx gotchas.
- Shared Rust coding standard: runClaudeInContainer `tasks/reference/rust-coding-standard.md`
  (github.com/billsix/runClaudeInContainer).
- `tasks/port-to-tauri.md` — the follow-up front-end (reuses this task's `hanoigame` Rust lib).
- wxDragon — crates.io / docs.rs (verify name, version, XRC + graphics-context support before use).
