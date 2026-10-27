# hanoi

A Towers of Hanoi **teaching project**. The goal is *not* recursion for its own
sake — it teaches solving the puzzle by hand via **peg relabelling**: solve 1
disc, then reuse that as a black box for 2 discs by relabelling the pegs, and so
on. Every artifact (bash pipelines, the language implementations, the Sphinx book,
printable worksheets) reinforces that "solve small, relabel, replay" idea.

## Repository layout — per-language subprojects + a book/umbrella root

Each language is a **self-contained subproject** with its own `Dockerfile`, `Makefile`,
`entrypoint/`, and emacs set — build and run it from its own directory:

- **`python/`** — the **canonical** implementation (the behaviour oracle). `cd python`,
  then `make cli | tui | wx | format | type-check | test | shell`. See `python/CLAUDE.md`.
- **`rust/`** — a Cargo workspace mirroring Python feature-for-feature, **including the
  Tauri app** at `rust/tauri/` and the **egui app** at `rust/hanoi-egui/` (native + web; each its
  own workspace, like the wx one is just another UI). `cd rust`, then
  `make cli | tui | wx | tauri | egui | egui-web | format | check | type-check | test | shell`. See `rust/CLAUDE.md`.
- **`cpp/`** — **two GUIs** over the engine from one `CMakeLists.txt`: a **Dear ImGui** app building
  **native** (`make gui`) **and** **WebAssembly** (`make webassembly`/`make serve`), plus a **wxWidgets**
  app (`make wx`) built from the shared `ui/hanoi.xrc`. `cd cpp`, then
  `make gui | wx | webassembly | serve | format | shell`. See `cpp/CLAUDE.md`.
- **the root** (this dir) — the **book + workbook + bash + umbrella**: the Sphinx book
  (`docs/`), the printable worksheets (`workbook/`), the bash demos (`bash/`), and a thin
  umbrella Makefile. `make docs` builds the book; `make format`/`make type-check` delegate
  to the Python subproject.

**Why the root keeps its OWN `Dockerfile` + `Makefile`** (rather than being a bare directory): they
are the **book builder**, and the book is **cross-cutting** — it pulls code listings from `python/src`,
runs `tools/gen_byhand.py`, and aggregates `docs/`, so the root (which sees the whole repo) is its
natural home. The root is also where the cross-tree pytest / by-hand **drift guard** runs (it needs
`python/` + `tools/` + `docs/` together — the reason `test_byhand_drift.py` skips inside the isolated
Python image). So the root build files are deliberate, not leftover from the split: a language
subproject is self-contained, the book sits above them.

The C++ port (Dear ImGui, native + WebAssembly) is the `cpp/` subproject in that same shape — see
`cpp/CLAUDE.md`; the port record is `tasks/archive/2026/10/25/port-to-cpp-imgui-native-and-wasm.md`.
The split itself: `tasks/archive/2026/10/24/split-into-per-language-containers.md`.

## Status

- **Python** (`python/`, setuptools package `src/hanoigame/`) — one shared model + command
  grammar + dispatcher with three thin front-ends: `hanoi`/`hanoigame` (ncurses TUI),
  `hanoi-cli` (plain stdin/stdout + readline completion), `hanoi-gui` (wxPython; XRC UI;
  text or 2D-graphics board). pytest suite (the by-hand drift guard runs here when the
  full tree is present — it needs the root's `tools/` + `docs/`, so it is skipped in the
  isolated Python image).
- **Rust** (`rust/`, a Cargo workspace) — a parallel reimplementation kept **in sync with
  the Python, feature-for-feature** (the Python stays the behaviour oracle; never removed).
  A `hanoigame` library crate + five front-ends: `hanoi-cli`, `hanoi` (ratatui/crossterm
  TUI), `hanoi-gui` (wxDragon GUI, loads the shared `ui/hanoi.xrc`), **`rust/tauri/`** (Tauri v2
  desktop app, static webview UI over the same crate — NOT a workspace member; its own
  `[workspace]` root), and **`rust/hanoi-egui/`** (egui/eframe GUI, native + WebAssembly; its own
  workspace too).
  Build facts + wxDragon gotchas: runClaudeInContainer `tasks/reference/rust-gui-tui-and-ecosystem.md`; the port
  record: `tasks/archive/2026/10/23/port-to-rust-wxdragon.md`; Tauri:
  runClaudeInContainer `tasks/reference/tauri-desktop-apps.md` (follow-ups: the frontend lint is done —
  `tasks/archive/2026/10/26/tauri-frontend-lint.md`; `tasks/tauri-frontend-js-options.md` remains).
- **C++** (`cpp/`, header-only engine in `src/`) — **two GUIs** from one `CMakeLists.txt`: a Dear ImGui
  `main.cpp` (native SDL2+OpenGL3 and WebAssembly OpenGL3→WebGL-ES3; ImGui vendored at `cpp/imgui/`), and
  a **wxWidgets `hanoiwx.cpp`** (`make wx`) built from the shared `ui/hanoi.xrc`. Both at feature parity
  with the Python oracle (`tasks/reference/feature-spec.md`). Build + wasm gotchas:
  `tasks/reference/imgui-cpp-native-and-wasm.md`; the port + parity records:
  `tasks/archive/2026/10/25/port-to-cpp-imgui-native-and-wasm.md` and
  `tasks/archive/2026/10/25/cpp-add-wx-frontend-and-recipe-view-parity.md`.
- **Bash demos** (`bash/`), **Sphinx book** (`docs/`, `intro` + `byhand1..5`), and
  printable **worksheets** (`workbook/`) all reinforce the relabelling method.

## Layout (root)

- `python/` — the Python subproject (self-contained; see `python/CLAUDE.md`). Its package
  is `src/hanoigame/`: `hanoimodel`, `presenter` (render + 6 peg labellings), `commands`,
  `engine`, `recipe`, the three front-ends, `board_renderers`, `hanoi.xrc` (a symlink to `ui/hanoi.xrc`);
  `tests/`.
- `rust/` — the Rust subproject (self-contained; see `rust/CLAUDE.md`), incl. `rust/tauri/`.
- `cpp/` — the C++ subproject (self-contained; see `cpp/CLAUDE.md`): the ImGui `main.cpp` + wxWidgets
  `hanoiwx.cpp` GUIs over the header-only engine in `src/`, with vendored `imgui/`.
- `ui/` — the **one shared wx UI definition** (`ui/hanoi.xrc`). Each wx front-end
  (`python/src/hanoigame/hanoi.xrc`, `cpp/hanoi.xrc`, `rust/hanoi-gui/hanoi.xrc`) is a git-tracked
  symlink to it, and each subproject's Makefile mounts `ui/` at `/ui` so the symlink resolves
  in-container — one file, no drift. (Rust bakes it in via `include_str!`; Python/C++ load it at runtime.)
- `bash/` — 12 scripts (solves + relabel filters).
- `tools/` — repo dev scripts. `gen_byhand.py` generates `docs/source/byhand4/5.rst`
  (guarded by `python/tests/test_byhand_drift.py`; regenerate, don't hand-edit those pages).
- `docs/` — Sphinx source; `workbook/` — `hanoi1..4.svg` + `induction-workbook.tex`.
- `tasks/` — active work; `tasks/archive/<YYYY>/<MM>/<DD>/` — completed task docs.

## Build / container workflow

Fedora-44 + podman family template. **Each subproject builds and runs on its own**; the
root builds the book.

- **Root (book):** `make image` (book image: base + Sphinx/TeX under `BUILD_DOCS=1`, the
  default; `MINIMAL_IMAGE=1` for a lean image). `make docs` builds html/pdf/epub into
  `./output/towersofhanoi/`. `make format` / `make type-check` delegate to `python/`.
- **`cd python && make`** — `cli` / `tui` / `wx` run the front-ends (X11 + Wayland
  passthrough for the wx GUI); `format` (ruff) / `type-check` (ty) / `test` (pytest, which
  collects the library doctests via `--doctest-modules`) are the gates; `shell`.
  `USE_X_WINDOWS` (default 1) installs the GTK/X11 libs — no OpenGL/mesa (the board is 2D
  wx/Cairo). `USE_EMACS` (default 1) installs emacs + the Python dev set.
- **`cd rust && make`** — `cli` / `tui` / `wx` / `tauri` / `egui` run the front-ends (`egui-web` /
  `egui-serve` for the egui WebAssembly build, behind the `USE_WASM` toolchain); `format`
  (rustfmt + `deno fmt` of the Tauri frontend web files), `check` (`cargo check --workspace
  --all-targets`, which compiles the test modules bare `cargo check` skips), `type-check`
  (the Tauri frontend web files via Deno — `deno check` + `deno lint` + `deno fmt --check`, no
  `node_modules`), and `test` (`cargo test --workspace`, which runs the unit tests and the
  `hanoigame` crate's doctests) are the gates. The crates build at runtime (cached in `rust/.container-*`) because wxDragon
  builds wxWidgets from source over the network; Tauri needs webkit2gtk + the DMABUF flag.
- **`cd cpp && make`** — `gui` (native ImGui) / `wx` (wxWidgets, from the shared `ui/hanoi.xrc`) /
  `webassembly` (→ gitignored `web/`) / `serve` (http at :8000); `format` (clang-format, never the
  vendored `imgui/`). `USE_EMACS` installs emacs+clangd, `USE_WASM` the Emscripten SDK, `USE_WX` the wxGTK
  stack (all default 1; `MINIMAL_IMAGE=1` drops them). `update-imgui` re-vendors Dear ImGui.
- Every subproject has `shell` / `shell-exec` (sharing one invocation), `image-export` /
  `image-import`, `PODMAN_RUN_FLAGS` (nested-podman), and `update-emacs-packages`.

Without a container (Python): `cd python && python -m venv venv && . venv/bin/activate &&
pip install -e . && hanoi`.

## Conventions

- **Python** (in `python/`): ruff (line-length 80, from `[tool.ruff] line-length` in
  `python/pyproject.toml` — the single source of truth, so `format.sh` passes no flag).
  Fully typed + Google-docstringed; `make type-check` runs `ty` and must stay green.
- All front-ends (both languages) go through the shared `engine.dispatch` + `commands.parse`
  + `presenter.render` layer — keep them thin; logic belongs in the shared core.
- **Tests are doctests by default** (both languages): a unit test documenting an API lives in
  that item's docstring / doc comment and runs under `make test` (Python `--doctest-modules`,
  Rust `cargo test --doc`); typed bindings in the example, per house style. Parametrized /
  stateful / integration / loop tests stay plain `#[test]`/pytest. See
  `~/.claude/reference/doctests-by-default.md`.
- Recipes are stored in the user's *labels* and replayed through the *current* labelling —
  that label-space transparency is the teaching point. Preserve it.
- The Python package is the **behaviour oracle** for the Rust/C++ ports — never remove it to
  satisfy a port.
- **Emacs (per-language dev tooling).** Each subproject vendors its own
  `entrypoint/dotfiles/.emacs.d/` (lsp-mode + the language's server), installed into the image,
  bind-mounted at runtime, and baked so a mount-less image works too; refresh with the
  subproject's `make update-emacs-packages`. Every `init.el` must (1) **pin the LSP root** to the
  subproject's `REPO_MOUNT` (`/hanoi-<lang>`), (2) **ignore the build/cache dirs** under the mount
  in `lsp-file-watch-ignored-directories`, and (3) **enable yasnippet** (so the `${1:arg}$0`
  completion snippets expand). hanoi is a **reusable basis for other multi-language projects** — a
  new language folder gets the same shape. Full recipe + the exact elisp:
  `tasks/reference/per-language-subproject-layout.md`.

## Documentation model

- **`README.md`** — user-facing overview. This file (`CLAUDE.md`) — lean agent/contributor
  reference; each subproject has its own `CLAUDE.md`.
- **`tasks/`** — active work, one file per task. **`tasks/archive/<YYYY>/<MM>/<DD>/`** —
  completed task docs.

**Reference docs:** `tasks/reference/feature-spec.md` — the **UI-independent feature specification**
(rules, concepts, every feature + what each UI must show + why, then TUI/GUI advice + a compliance
checklist). It is the **parity authority**: read it before adding or changing any feature or building a
new UI/language, and keep it in step with the Python oracle (the spec leads, the code follows). Then
`tasks/reference/architecture-overview.md` (dispatch data-flow + the
default-label-space recipe invariant + the per-file teaching intent + wx/GTK gotchas) and
`tasks/reference/per-language-subproject-layout.md` (the per-language container/emacs template +
the recipe for adding a language); plus the shared `rust-gui-tui-and-ecosystem.md` and
`tauri-desktop-apps.md`. Read the relevant one before touching the engine/recipe subsystem, the
container layout, the wx GUI, or Tauri.
