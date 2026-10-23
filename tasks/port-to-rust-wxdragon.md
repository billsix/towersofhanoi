# Port the whole hanoi program to Rust (wxDragon for the GUI)

**Status:** proposed — needs go-ahead (large new initiative; the maintainer is new to Rust, so
clarity and idiomatic code matter as much as the port itself).
**Priority:** 5 **Difficulty:** 8
**Created:** 2026-10-23 (William Emerison Six <billsix@gmail.com>). Requested: port everything done
in Python — the wxWidgets GUI, the engine, the command line, *everything* — to Rust, using
**wxDragon** for the GUI. A Tauri port is the follow-up (`tasks/port-to-tauri.md`).

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

## Decisions / open questions

1. **Crate layout:** one workspace with a `hanoigame` lib + three bin crates, vs one crate with
   `src/bin/{hanoi,hanoi-cli,hanoi-gui}.rs`. Recommend the **workspace** (clean lib/bin separation,
   each front-end thin). OK?
2. **TUI crate:** `ratatui` + `crossterm` (modern, pure-Rust, portable) vs an ncurses binding
   (closest to the Python). Recommend **ratatui/crossterm**. Preference?
3. **GUI UI construction:** ~~programmatic vs XRC~~ **RESOLVED (see the capability section):**
   build the UI programmatically with wxDragon (recommended), draw the board with the DC model
   (`AutoBufferedPaintDC` + `on_paint`), relabel menu as normal items. `include_xrc!` is available if
   you'd rather keep `hanoi.xrc`. Confirm the programmatic choice, or say to keep the XRC.
4. **Error strategy** (per the Rust standard): `thiserror` in the `hanoigame` lib, `anyhow` in the
   binaries. OK?
5. **byhand-drift:** leave `tools/gen_byhand.py` + `test_byhand_drift.py` in Python (docs stay
   Python/TeX), or also port the drift check into the Rust suite? Recommend **leave it in Python**
   (it guards Python-generated book pages). OK?
6. **Keep or retire the Python package?** Recommend keeping both side by side initially (the Python
   is the behaviour oracle for the port); decide removal only once the Rust is verified.

## Pointers

- `python/src/hanoigame/` — the source of truth being ported; `python/tests/` — the 130-test oracle.
- `tasks/reference/architecture-overview.md` — dispatch flow, recipe invariant, module map, wx gotchas.
- Shared Rust coding standard: runClaudeInContainer `tasks/reference/rust-coding-standard.md`
  (github.com/billsix/runClaudeInContainer).
- `tasks/port-to-tauri.md` — the follow-up front-end (reuses this task's `hanoigame` Rust lib).
- wxDragon — crates.io / docs.rs (verify name, version, XRC + graphics-context support before use).
