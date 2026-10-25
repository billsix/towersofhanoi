# Port hanoi to C++ with a Dear ImGui GUI — runnable natively (in-container) AND as WebAssembly

**Status:** COMPLETE (2026-10-25) — the `cpp/` subproject was built, both `make gui` (native) and `make
webassembly`/`make serve` (browser) verified, and the GUI + emacs C++ LSP (clangd) confirmed working on
the maintainer's display. Durable build knowledge lives in `tasks/reference/imgui-cpp-native-and-wasm.md`
and the subproject recipe in `tasks/reference/per-language-subproject-layout.md`; the optional full-core
CLI/TUI port was not pursued (the GUI was at parity without it). Archived to `tasks/archive/2026/10/25/`.
**Priority:** 6 **Difficulty:** 7
**Created:** 2026-10-24 (William Emerison Six <billsix@gmail.com>). Requested: "just like you ported the
python source (canonical source) to rust, do the same for C++, using IMGUI as the GUI, look online for
how to use IMGUI using webassembly. But it should also be able to be run locally, so a `make gui` should
run it in container, but a `make webassembly` should make as output that can be run in a webbrowser."

## BLUF

Added a **C++ port** of hanoi mirroring the Python→Rust port methodology — a shared engine reused by a
thin front-end — with the GUI built on **Dear ImGui**. The C++ app builds two ways from one codebase:
**`make gui`** → a native binary run inside the container (ImGui on SDL2 + the OpenGL3 backend, via the
existing X11/Wayland passthrough), and **`make webassembly`** → an Emscripten build emitting
`web/index.{html,js,wasm}` runnable in a browser. Python stayed the **behaviour oracle** (never removed);
the C++ port was checked against it, as Rust is. "Done" was: the C++ engine reproduces the shared core,
an ImGui front-end renders the board + legal moves + relabelling + recipes, both `make gui` and `make
webassembly` work, and GUI parity with the Python oracle holds — all met and maintainer-verified.

## Context

- **Canonical source of truth:** the Python core at `python/src/hanoigame/` (`hanoimodel.py`,
  `commands.py`, `engine.py`, `presenter.py`, `recipe.py`, `board_renderers.py`). The Rust port at
  `rust/` was the structural template, and `tasks/archive/2026/10/23/port-to-rust-wxdragon.md` recorded
  how it was carried out (Python-as-oracle, module-for-module mirror, thin front-ends).
- **Methodology mirrored (from the Rust port):** keep Python as the oracle and never remove it;
  reproduce the shared core in C++; the front-end reuses that library. The Tauri app (`rust/tauri/`) was
  the closest existing precedent for a web/graphical board.
- **Greenfield for the GUI:** the three prior renderings were wxPython, wxDragon, and Tauri webview
  `<canvas>` — no Dear ImGui or Emscripten/WASM existed. The shared-core→thin-frontend split and the
  Tauri canvas precedent carried over.
- **Landed inside the per-language split:** `tasks/archive/2026/10/24/split-into-per-language-containers.md`
  moved each language to its own subproject (own Dockerfile/Makefile/emacs). This port landed directly in
  that shape as a new **`cpp/`** subproject, following `tasks/reference/per-language-subproject-layout.md`.

## External research — Dear ImGui: one source, native + WebAssembly (2026-10-24)

- **Canonical approach:** ImGui's `examples/example_sdl2_opengl3/` compiles to **both** a native binary
  and WebAssembly from one source — native uses SDL2 + the OpenGL3 backend (`imgui_impl_sdl2.cpp` +
  `imgui_impl_opengl3.cpp`); the web build reuses the same backend with the OpenGL3 path mapped onto
  **WebGL**, SDL2 supplied by Emscripten's SDL2 port.
  (https://github.com/ocornut/imgui/tree/master/examples/example_sdl2_opengl3)
- **Native build:** host toolchain (`g++`/cmake + system SDL2 + OpenGL via `sdl2-config`/pkg-config),
  run under the existing X11/Wayland passthrough. Needed SDL2 + mesa/GL dev packages added to the image.
- **WASM build:** `CC=emcc`/`CXX=em++`, `-sUSE_SDL=2` (compile + link), `-sWASM=1
  -sALLOW_MEMORY_GROWTH=1`, a shell HTML, no filesystem/ini on web, Emscripten owning the loop
  (`emscripten_set_main_loop`), `io.IniFilename = NULL`. Needed the **emsdk** in the image.
- A later finding corrected the naive reading of "reuses the same backend": the OpenGL3 backend does NOT
  auto-select GLES for Emscripten (see "The blank-page bug" below).

## Decisions (maintainer, 2026-10-24 — "after the split, yes, and what you recommend")

1. **Sequencing:** gated on the per-language split, which completed 2026-10-24, so this was unblocked and
   landed as a new `cpp/` subproject per the per-language recipe.
2. **ImGui backend: SDL2 + OpenGL3** (`example_sdl2_opengl3`) — the best-documented dual native/WASM
   path, OpenGL3 → WebGL under Emscripten.
3. **Front-ends: the ImGui GUI only** this round (native + WASM). A full CLI/TUI was deferred as a later
   option; the GUI reaches parity without the text pieces.
4. **Dear ImGui: vendored at a pinned version** (self-contained, offline-rebuildable), not a submodule.
5. **`make webassembly` output: `cpp/web/` as gitignored build output**, with a `make serve`
   (python http.server) helper — no committed/publishable web build (revisit GitHub Pages later if wanted).

## What was built and verified (2026-10-24 → 2026-10-25)

**The `cpp/` subproject**, in the per-language shape: `Dockerfile` (C++/SDL2/GL toolchain + optional
pinned emsdk via `USE_WASM`/`EMSDK_VERSION` + optional emacs), `Makefile` (`gui`, `webassembly`, `serve`,
`shell`/`shell-exec`, `format`, `image-export`/`import`, `update-emacs-packages`), one `CMakeLists.txt`
driving both targets (native vs. `EMSCRIPTEN`-gated), entrypoint scripts (`01-install-cpp-base.sh`,
`02-install-emsdk.sh`, shell/format/entrypoint/.bashrc), a C++ emacs set, `.dockerignore`, `.gitignore`,
`CLAUDE.md`. Mounts at `/hanoi-cpp`.

- **Engine (header-only `src/`):** `model.hpp` (state + legal moves), `presenter.hpp` (the six peg
  **labellings** + label↔tower), `recipe.hpp` (Recorder / RecipeRegistry / replay `apply` / `rebinding`)
  — ported from the canonical Python. The GUI drives these directly; the text pieces (commands / engine
  dispatch / solvers) were left unported since the GUI reaches parity without them.
- **Dear ImGui vendored** at `cpp/imgui/` (pinned **v1.91.5**: core + `imgui_impl_sdl2` +
  `imgui_impl_opengl3`). Re-vendor via `cpp/tools/update-imgui.sh` (host-run; the single-dep standalone
  form of the `update-<dep>` pattern).
- **GUI (`main.cpp`):** one Dear ImGui app at **feature parity with the wx GUI** — a menubar (Game →
  disk count 1–8 / Restart; Relabel → the 6 labellings as radio items; Recipe → save/reset/replay), the
  board **coloured by label**, legal-move buttons in the **current labels**, moves recorded in
  default-label space, and the label→peg rebinding shown under a non-default labelling. The only
  target-specific code is the main loop (`emscripten_set_main_loop_arg` vs native `while`), the
  no-ini/filesystem on web, and matching the SDL window to the browser canvas size.
- **Native build verified** (nested podman): lean image builds (~1.5 min); `cmake -G Ninja && cmake
  --build` compiles + links `hanoi-cpp` (SDL2 2.32.74 via sdl2-compat; model + vendored ImGui compile).
- **WebAssembly build verified:** the full image (emsdk 3.1.74 + emacs) builds; `emcmake cmake` + build
  links `web/index.html` + `index.js` (~160 KB) + `index.wasm` (~685 KB). `make serve` (now depending on
  `webassembly`) serves them at :8000 — verified end-to-end nested: HTTP 200 from outside the container,
  `.wasm` served as `application/wasm`.

**The blank-page bug (root cause + fix).** The wasm build first loaded (server log showed 200s) but drew
nothing. Cause: the ImGui OpenGL3 backend does NOT auto-select GLES for Emscripten (its header: "You need
to #define IMGUI_IMPL_OPENGL_ES2/ES3 to use WebGL") — the wasm build had compiled the **desktop** GL path
(GLSL 130), whose shaders don't compile under WebGL. Fix: the wasm target compiles with
**`-DIMGUI_IMPL_OPENGL_ES3`** + links **`-sMIN/MAX_WEBGL_VERSION=2`**, and `main.cpp` uses an **ES 3.0
context + "#version 300 es"** on web (desktop GL 3.0 + GLSL 130 natively); `shell.html` fills the
viewport and the SDL window tracks the canvas CSS size each frame. Testing note: browsers cache
`index.js`/`index.wasm` (304s) — hard-refresh after a rebuild.

**UX + build tweaks (maintainer feedback).** Default is **3 disks**; all six moves are **always shown**
(fixed layout, illegal ones `BeginDisabled`'d, matching wx — no jumping buttons); and the Dockerfile
**pre-warms the Emscripten cache** (SDL2 port + system libs) at image-build, so a `--rm`
`make serve`/`webassembly` doesn't re-download/rebuild them each run (verified: a fresh wasm build is a
~7s cache hit; `libSDL2.a` + `libc++*.a` baked into the image's emsdk cache).

**Emacs C++ LSP.** `init.el` hooks `c/c++-mode` → lsp-mode + clangd (the clangd + clang-format binaries
come from `clang-tools-extra` in `01-install-cpp-base.sh`, always-on), with the per-language LSP-root pin
to `/hanoi-cpp`, build/cache `lsp-file-watch-ignored-directories`, and yasnippet (so clangd's `${1:arg}$0`
completion snippets expand) — the hanoi per-language convention. `make update-emacs-packages` vendors the
`elpa/` set (maintainer-run).

**Maintainer verification (2026-10-25, on-display):** the native `make gui` window, the wasm GUI in the
browser after `make serve`, and the board/menus/recipes all work interactively ("the imgui gui works well
now"); the emacs setup confirmed working ("the emacs stuff works well").

## Not pursued (a future option, not required)

A C++ CLI/TUI would need the rest of the core (commands / engine-dispatch / solvers) ported. The GUI is
at parity without them (it drives model/presenter/recipe directly), and Decision 3 kept this round to the
ImGui GUI. If wanted later, it's a fresh task mirroring the Python/Rust layout + a parity check against
the oracle.

## Related

- Sibling: `tasks/archive/2026/10/24/split-into-per-language-containers.md` (this port landed as `cpp/`).
- Reference: `tasks/reference/imgui-cpp-native-and-wasm.md` (the dual native/wasm build) +
  `tasks/reference/per-language-subproject-layout.md` (the subproject + emacs template).
- Structural template: `rust/` and `tasks/archive/2026/10/23/port-to-rust-wxdragon.md`.
- Canonical source of truth: `python/src/hanoigame/`.
- ImGui emscripten reference: https://github.com/ocornut/imgui/tree/master/examples/example_sdl2_opengl3
