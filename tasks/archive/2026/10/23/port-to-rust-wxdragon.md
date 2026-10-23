# Port the whole hanoi program to Rust (wxDragon for the GUI) — DONE

**Status:** DONE 2026-10-23 — the Python `hanoigame` package and all three front-ends were
reimplemented in Rust; the wxDragon GUI was **play-tested by the maintainer on the host and works**.
Archived.
**Priority:** 5 **Difficulty:** 8
**Created & completed:** 2026-10-23 (William Emerison Six <billsix@gmail.com>). The maintainer
requested a full Rust port — the wxWidgets GUI, the engine, the command line, everything — using
**wxDragon** for the GUI; they were new to Rust, so idiomatic, well-commented code mattered as much
as the port. The Tauri port is the filed follow-up (`tasks/port-to-tauri.md`).

> **CONSTRAINT (maintainer): the Python version is kept FOREVER — this is NOT a replacement, but a
> parallel copy kept in sync, feature for feature.** The Rust lives in `rust/` beside `python/`; both
> front-end sets stay runnable; the Python stays the behaviour oracle. Never remove the Python.

## What was built (`rust/`, a Cargo workspace)

- **`hanoigame` library crate** — the shared teaching core: `model`, `commands` (parser), `engine`
  (`GameSession` dispatcher), `presenter` (the six peg labellings + layout + text render), `recipe`
  (Recorder / Registry / Replay + the label-space rebinding tables), `solvers` (iterative +
  recursive). **51 unit tests** reproducing the Python core suite, including Bill's worked example
  `apply_through_relabel_solves_subproblem`.
- **`hanoi-cli`** — a stdin/stdout front-end over any `BufRead`/`Write`; **19 tests** reproducing
  every Python CLI test (the worked example's exact board, capture-under-relabel). Interactive
  `rustyline` tab-completion (command verbs + recipe names) is wired through a `LineReader`
  abstraction that keeps the scripted/piped path byte-identical.
- **`hanoi` TUI** — a ratatui 0.30 / crossterm 0.29 port of the ncurses UI: coloured board, status
  line, scrolling message pager, input line, disc prompt, win/save/play-again. **5 `TestBackend`
  headless render tests.**
- **`hanoi-gui`** — a wxDragon 0.9.23 **programmatically-built** GUI: menu (New / New-same / Exit /
  About), relabel menu (six permutations, the active one bulleted), two board renderers (monospace
  text + a solid-fill DC graphics board) with a View-menu toggle, six move buttons, recipes (list +
  Save/Apply/Show + double-click), and a rebinding dialog.

**Gates:** `cargo fmt --check`, a warning-clean `cargo build`, and `cargo test` (**75 tests**) all
green — offline for the core and CLI. `clippy` was added to both sandbox base lists so
`cargo clippy -- -D warnings` becomes available after those images rebuild.

## Decisions (maintainer: "go with your recommendation")

1. **Crate layout:** a Cargo workspace in `rust/` — one `hanoigame` library crate + four thin binary
   crates over it.
2. **TUI:** `ratatui` + `crossterm`.
3. **GUI:** programmatic wxDragon + the wxDC drawing model; `hanoi.xrc` stays with the Python GUI.
4. **Error strategy:** planned `thiserror`/`anyhow`, but **neither was pulled** — the core has no
   fallible-I/O surface that needs them, so `model::MoveError` is a plain std enum (`Display` +
   `std::error::Error`). Revisit only if a future fallible public API warrants `thiserror`.
5. **byhand-drift stays Python** (`tools/gen_byhand.py` + `test_byhand_drift.py` guard Python/TeX
   book pages — outside the Rust scope).
6. **Python kept forever, in sync** — the CONSTRAINT above.

## Where the plan was wrong (corrections worth remembering)

- **wxDragon does NOT wrap or link the system wxGTK.** `wxdragon-sys` **downloads the wxWidgets 3.3.4
  source over HTTPS and statically builds it**, and `bindgen`-generates its FFI. The pre-port
  "capability check" that said it wraps wx 3.3.1 / links system wx via `wx-config` was wrong. The
  real build deps are the full native toolchain — `gcc`/`gcc-c++`, `make`, `cmake`, `ninja-build`,
  `clang-devel` (libclang for bindgen), `openssl-devel` (the HTTPS download via `reqwest`/native-tls),
  `gtk3-devel` (via `wxGTK-devel`, to compile wx), `libSM-devel`/`libICE-devel`, and the system image
  libs `libjpeg-turbo-devel`/`libtiff-devel`/`expat-devel`.
- **Graphics renderer:** solid fills (wxDC), not the wxPython `GraphicsContext` gradients/shadows —
  wxDragon exposes only the DC model (functional parity, minor cosmetic downgrade).
- **Recipe `apply_iter`** (a lazy Python generator) became a **`Replay::step(&mut game)` stepper** — a
  Rust `Iterator` can't let the caller observe the game between steps. The shared registry is a
  `&mut RecipeRegistry` on the session; the GUI adapts that via a transient session inside
  `Rc<RefCell<GuiState>>` (event closures are `'static`).
- **Recipe-show / rebinding** are message dialogs, not the Python's scrollable 3-panel dialog.

## The build-deps saga (hard-won)

Getting the GUI to build on hanoi's deliberately lean, Python-only image took **four `make rust-wx`
rounds** — `openssl-devel`, then the C/C++ toolchain + `libclang`, then the system image libs — each
surfaced by the next build error. The complete toolchain now lives in `entrypoint/04-install-rust.sh`.
**Lesson:** for a `-sys` crate that builds a big C/C++ library from source, read its `build.rs` and
the final link line up front to see the whole dependency set in one pass. Captured durably in the
shared reference doc.

## Container / Makefile (how to run it)

- A gated **`USE_RUST`** Dockerfile ARG (Makefile default 1) dispatches `entrypoint/04-install-rust.sh`
  (the full Rust + wxDragon build stack). `python3-wxpython4` was added to
  `03-install-xwindows.sh` so the **Python** wx GUI also runs in-container (it couldn't before).
- Six run targets: **`make python-cli`/`python-tui`/`python-wx`** and
  **`make rust-cli`/`rust-tui`/`rust-wx`** — all run in the container with X11 + Wayland passthrough.
  The Rust targets use `rust/.container-target` (gitignored) so the heavy from-source wxWidgets build
  is cached across runs.
- **Offline caveat:** because wxDragon fetches wxWidgets at build time, a Rust-GUI build needs
  network and is not offline-reproducible as-is (`WXDRAGON_SYS_BUILD_DIR` could pre-vendor the source).

## Durable knowledge harvested to

- runClaudeInContainer `tasks/reference/rust-gui-tui-and-ecosystem.md` — wxDragon (build deps, the
  DC-not-GraphicsContext limit, the programmatic API), ratatui/crossterm, rustyline, the
  `Rc<RefCell>` event-state pattern, the sandbox toolchain + headless-Xvfb verify.
- hanoi `CLAUDE.md` — the `rust/` port exists, how to run and build it.

## Pointers

- `python/src/hanoigame/` — the oracle that was ported; `rust/` — the port.
- `tasks/reference/architecture-overview.md` — the dispatch data-flow + the label-space recipe
  invariant the port preserves.
- Shared Rust coding standard: runClaudeInContainer `tasks/reference/rust-coding-standard.md`.
- `tasks/port-to-tauri.md` — the filed follow-up; its prerequisite (the `hanoigame` Rust lib) is now
  met.
