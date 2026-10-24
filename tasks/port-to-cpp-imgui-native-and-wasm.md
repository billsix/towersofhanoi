# Port hanoi to C++ with a Dear ImGui GUI — runnable natively (in-container) AND as WebAssembly

**Status:** proposed — needs go-ahead
**Priority:** 6 **Difficulty:** 7
**Created:** 2026-10-24 (William Emerison Six <billsix@gmail.com>). Requested: "just like you ported the
python source (canonical source) to rust, do the same for C++, using IMGUI as the GUI, look online for
how to use IMGUI using webassembly. But it should also be able to be run locally, so a `make gui`
should run it in container, but a `make webassembly` should make as output that can be run in a
webbrowser."

## BLUF

Add a **C++ port** of hanoi that mirrors the existing Python→Rust port methodology — a shared library
("the engine") reused by thin front-ends — with the GUI built on **Dear ImGui**. The C++ app must build
two ways from one codebase: **`make gui`** → a native binary that runs inside the container (ImGui on
SDL2 + the OpenGL3 backend, shown via the existing X11/Wayland passthrough), and **`make webassembly`**
→ an Emscripten build producing `web/index.{html,js,wasm}` runnable in a browser. Python stays the
**behaviour oracle** (never removed); the C++ port is checked against it, exactly as Rust is. "Done" =
the C++ engine reproduces the shared core, at least one ImGui front-end renders the board + legal moves
+ relabelling, both `make gui` and `make webassembly` work (native verified headless/on-display; WASM
verified by serving `web/` and loading it), and parity with the Python oracle is demonstrated.

## Context (read first)

- **Read first:** `/foo/opt/hanoi/CLAUDE.md`; the canonical Python core at
  `/foo/opt/hanoi/python/src/hanoigame/` (`hanoimodel.py`, `commands.py`, `engine.py`, `presenter.py`,
  `recipe.py`, `board_renderers.py`); the Rust port at `/foo/opt/hanoi/rust/` (library crate
  `rust/hanoigame/src/{model,commands,engine,presenter,recipe,solvers}.rs` + binaries) as the
  structural template; and `tasks/archive/2026/10/23/port-to-rust-wxdragon.md` for how the Rust port was
  carried out (Python-as-oracle, module-for-module mirror, thin front-ends).
- **The port methodology to mirror (verified against the Rust port):** keep Python as the oracle and
  never remove it; reproduce the shared core **module-for-module** in a C++ library; each front-end
  reuses that library. The Tauri app (`tauri/`, a webview `<canvas>` board over the Rust crate) is the
  closest existing precedent for a web/graphical board and worth reading for the view-model shape.
- **Current GUI landscape:** three existing renderings — wxPython (`hanoigui.py`), wxDragon (Rust
  `hanoi-gui`), Tauri webview `<canvas>`. **No Dear ImGui or Emscripten/WASM anywhere today** — this is
  greenfield, but the shared-core→thin-frontend split and the Tauri canvas precedent carry over.
- **Toolchain already present:** `entrypoint/04-install-rust.sh` already installs `gcc`, `gcc-c++`,
  `clang`/libclang, `cmake`, `ninja`, `make`. **Missing for this task:** SDL2 + mesa/OpenGL dev
  packages (deliberately absent today — `03-install-xwindows.sh` installs no OpenGL/mesa), and the
  **Emscripten SDK (emsdk)** for the WASM build. Both need adding to whichever image this port uses.
- **Interacts with the per-language split:** `tasks/split-into-per-language-containers.md` moves each
  language to its own subproject (own Dockerfile/Makefile/emacs). This C++ port should land directly in
  that shape as a new **`cpp/`** subproject (own `cpp/Dockerfile`, `cpp/Makefile`, `cpp/entrypoint/`,
  C++-tailored emacs set: cc-mode/c++-mode + clangd via eglot/lsp-mode, cmake-mode, magit). Sequence the
  two tasks per open question Q1.

## External research — Dear ImGui: one source, native + WebAssembly (verified 2026-10-24)

- **Canonical approach:** Dear ImGui's `examples/example_sdl2_opengl3/` compiles to **both** a native
  desktop binary and to WebAssembly from the same source. Native uses SDL2 + the OpenGL3 backend
  (`imgui_impl_sdl2.cpp` + `imgui_impl_opengl3.cpp`); the web build reuses the same backend with the
  OpenGL3 path mapped onto **WebGL**, with SDL2 provided by Emscripten's SDL2 port. Upstream: "The
  SDL+GL, GLFW+GL and SDL+WebGPU examples are all ready to build and run with Emscripten."
  (https://github.com/ocornut/imgui/tree/master/examples/example_sdl2_opengl3)
- **Native build (`make gui`):** host toolchain (`g++`/cmake + system SDL2 + OpenGL via
  `sdl2-config`/pkg-config) → a native binary, run under the existing `PLAY_FLAGS` X11/Wayland
  passthrough (analogous to `rust-wx`). Needs SDL2 + mesa/GL dev packages added to the image.
- **WASM build (`make webassembly`):** uses the example's `Makefile.emscripten` — `CC=emcc`,
  `CXX=em++`, `-s USE_SDL=2` (on both compile and link), link flags `-s WASM=1 -s
  ALLOW_MEMORY_GROWTH=1 -s NO_EXIT_RUNTIME=0 -s ASSERTIONS=1`, `--shell-file .../shell_minimal.html`,
  `USE_FILE_SYSTEM=0` → `-s NO_FILESYSTEM=1 -DIMGUI_DISABLE_FILE_FUNCTIONS`, `-Os`. Emscripten owns the
  loop (`emscripten_set_main_loop`); set `io.IniFilename = NULL`. **Output:** `web/index.html`,
  `web/index.js`, `web/index.wasm`. Serve with `python3 -m http.server -d web` (or `emrun`). Needs the
  **emsdk** added to the image.
- Implementation note: keep the ImGui layer thin — it calls into the C++ hanoi engine (model/commands/
  engine/presenter/recipe) exactly as the Rust/Python front-ends call theirs; the board can be drawn
  with ImGui draw-list primitives or as text, reusing the presenter's labellings.

## Plan (sketch — refine after open questions)

1. **`cpp/hanoigame` engine library** — port the Python core module-for-module (model, commands,
   engine, presenter, recipe, solvers). Pick a C++ standard and build system (CMake, matching the
   family's C/C++ projects). No GUI dependency in the engine.
2. **ImGui front-end** — vendor Dear ImGui (pin a version) + the SDL2/OpenGL3 backend; a single
   `main.cpp` that builds both native and WASM (guard the loop with `#ifdef __EMSCRIPTEN__`). Render
   board + towers + legal moves + the relabelling table + recipe record/replay.
3. **`cpp/Makefile`** — `make gui` (native, in-container, under X11/Wayland passthrough) and `make
   webassembly` (emsdk → `web/index.{html,js,wasm}`, plus a `serve` helper), alongside the standard
   contract targets (`help`/`image`/`shell`/`shell-exec`/`format`). `make format` = clang-format.
4. **`cpp/Dockerfile` + install scripts** — add SDL2 + mesa/GL dev packages and the emsdk (as
   `0N-install-*.sh` group scripts, host-runnable, baked into committed layers per the self-contained-
   images rule so the WASM build is offline-reproducible).
5. **Parity with the oracle** — reuse/extend the cross-language parity approach from the Rust port (feed
   the same command/recipe sequences, compare presenter output). A CLI or headless mode makes this
   testable without a display.
6. **Verify** — native `make gui` (headless or on-display), `make webassembly` serves and loads in a
   browser, parity demonstrated, `make format` green, offline export/import test per the self-contained
   images rule.

## Decisions (maintainer, 2026-10-24 — "after the split, yes, and what you recommend")

1. **Sequencing:** do the **per-language split first** (`tasks/split-into-per-language-containers.md`),
   then this; the C++ port lands as a `cpp/` subproject already in that per-language shape (so this task
   creates `cpp/`, the split task only converts python/rust).
2. **ImGui backend:** **SDL2 + OpenGL3** (`example_sdl2_opengl3`) — the best-documented dual native/WASM
   path, OpenGL3 → WebGL under Emscripten.
3. **Front-ends:** **ImGui GUI only** this round (native + WASM). A minimal headless mode may be added
   purely as a parity harness against the Python oracle; a full CLI/TUI is a later option if wanted.
4. **Dear ImGui:** **vendored at a pinned version** (self-contained, offline-rebuildable), not a git
   submodule.
5. **`make webassembly` output:** emit to **`cpp/web/` as gitignored build output**, with a `make serve`
   (python http.server) helper. No committed/publishable web build now; revisit (e.g. GitHub Pages)
   later if wanted.

## Related

- Sibling task: `tasks/split-into-per-language-containers.md` (this port lands as the `cpp/` subproject).
- Structural template: `/foo/opt/hanoi/rust/` and `tasks/archive/2026/10/23/port-to-rust-wxdragon.md`.
- Canonical source of truth: `/foo/opt/hanoi/python/src/hanoigame/`.
- ImGui emscripten reference: https://github.com/ocornut/imgui/tree/master/examples/example_sdl2_opengl3
