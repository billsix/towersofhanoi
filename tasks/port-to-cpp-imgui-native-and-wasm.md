# Port hanoi to C++ with a Dear ImGui GUI — runnable natively (in-container) AND as WebAssembly

**Status:** in progress — the `cpp/` subproject is scaffolded and the native build is verified; the
engine port and the wasm-build verification are the remaining work (see Progress).
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

- **Read first:** the repo-root `CLAUDE.md`; the canonical Python core at
  `python/src/hanoigame/` (`hanoimodel.py`, `commands.py`, `engine.py`, `presenter.py`,
  `recipe.py`, `board_renderers.py`); the Rust port at `rust/` (library crate
  `rust/hanoigame/src/{model,commands,engine,presenter,recipe,solvers}.rs` + binaries) as the
  structural template; and `tasks/archive/2026/10/23/port-to-rust-wxdragon.md` for how the Rust port was
  carried out (Python-as-oracle, module-for-module mirror, thin front-ends).
- **The port methodology to mirror (verified against the Rust port):** keep Python as the oracle and
  never remove it; reproduce the shared core **module-for-module** in a C++ library; each front-end
  reuses that library. The Tauri app (`rust/tauri/`, a webview `<canvas>` board over the Rust crate) is
  the closest existing precedent for a web/graphical board and worth reading for the view-model shape.
- **Current GUI landscape:** three existing renderings — wxPython (`hanoigui.py`), wxDragon (Rust
  `hanoi-gui`), Tauri webview `<canvas>`. **No Dear ImGui or Emscripten/WASM anywhere today** — this is
  greenfield, but the shared-core→thin-frontend split and the Tauri canvas precedent carry over.
- **Toolchain already present:** `entrypoint/04-install-rust.sh` already installs `gcc`, `gcc-c++`,
  `clang`/libclang, `cmake`, `ninja`, `make`. **Missing for this task:** SDL2 + mesa/OpenGL dev
  packages (deliberately absent today — `03-install-xwindows.sh` installs no OpenGL/mesa), and the
  **Emscripten SDK (emsdk)** for the WASM build. Both need adding to whichever image this port uses.
- **Interacts with the per-language split:** `tasks/archive/2026/10/24/split-into-per-language-containers.md` moves each
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

1. **Sequencing:** the **per-language split is now DONE** (`tasks/archive/2026/10/24/split-into-per-language-containers.md`,
   2026-10-24), so this is unblocked. The C++ port lands as a new `cpp/` subproject in that per-language
   shape — follow the recipe in `tasks/reference/per-language-subproject-layout.md` (own
   Dockerfile/Makefile/entrypoint + a `.emacs.d/` that pins the LSP root, ignores build/cache dirs, and
   enables yasnippet). This task creates `cpp/` itself.
2. **ImGui backend:** **SDL2 + OpenGL3** (`example_sdl2_opengl3`) — the best-documented dual native/WASM
   path, OpenGL3 → WebGL under Emscripten.
3. **Front-ends:** **ImGui GUI only** this round (native + WASM). A minimal headless mode may be added
   purely as a parity harness against the Python oracle; a full CLI/TUI is a later option if wanted.
4. **Dear ImGui:** **vendored at a pinned version** (self-contained, offline-rebuildable), not a git
   submodule.
5. **`make webassembly` output:** emit to **`cpp/web/` as gitignored build output**, with a `make serve`
   (python http.server) helper. No committed/publishable web build now; revisit (e.g. GitHub Pages)
   later if wanted.

## Progress (2026-10-24)

**Done + verified (nested podman):**
- **`cpp/` subproject scaffolded** in the per-language shape: `Dockerfile` (C++/SDL2/GL toolchain +
  optional pinned emsdk via `USE_WASM`/`EMSDK_VERSION` + optional emacs), `Makefile` (`gui`,
  `webassembly`, `serve`, `shell`/`shell-exec`, `format`, image-export/import, update-emacs-packages),
  `CMakeLists.txt` (one build, native vs. `EMSCRIPTEN`-gated), entrypoint scripts
  (`01-install-cpp-base.sh`, `02-install-emsdk.sh`, shell/format/entrypoint/.bashrc), a C++ emacs set
  (clangd + clang-format, root-pinned to `/hanoi-cpp`, build-dir ignores, yasnippet), `.dockerignore`,
  `.gitignore`, `CLAUDE.md`. Mounts at `/hanoi-cpp`.
- **Dear ImGui vendored** at `cpp/imgui/` (pinned **v1.91.5**: core + SDL2 + OpenGL3 backends).
- **Engine:** `cpp/src/model.hpp` — the C++ port of `hanoimodel.py` (state + legal-move enumeration),
  header-only.
- **GUI:** `cpp/main.cpp` — the dual-target Dear ImGui app (SDL2+OpenGL3; the only target-specific code
  is the `emscripten_set_main_loop_arg` vs native `while` loop + the no-filesystem/ini on web). Renders
  the board with draw-list primitives and a button per legal move from the model.
- **Native build VERIFIED:** lean image builds (~1.5 min); `cmake -G Ninja && cmake --build` compiles +
  links `hanoi-cpp` (SDL2 2.32.74 via sdl2-compat, model + vendored ImGui all compile).
- **WebAssembly build VERIFIED:** full image (emsdk 3.1.74 + emacs) builds; `emcmake cmake` + build
  compiles ImGui + the app and links `web/index.html` + `index.js` (~160 KB) + `index.wasm` (~685 KB).
  `make serve` serves them at :8000. Both targets build from the one `CMakeLists.txt`.

**Parity pass (2026-10-24, on maintainer feedback — disk count / recipes / menubar were missing):**
- Ported `src/presenter.hpp` (the six **labellings** + label↔tower) and `src/recipe.hpp` (Recorder,
  RecipeRegistry, replay `apply`, `rebinding`) from the canonical Python.
- Rewrote `main.cpp` to **feature parity with the wx GUI**: an ImGui **menubar** — **Game** (New game
  → disk counts 1–8, Restart), **Relabel** (the 6 labellings as radio items), **Recipe** (shows the
  recording length, Save-recording-as… via a modal, Reset recording, Replay ▸ saved names). The board
  is **coloured by label** (colour follows the peg's label after relabelling), legal-move buttons show
  the **current labels**, moves are recorded in default-label space, and the **label→peg rebinding** is
  shown under a non-default labelling. Both native and wasm **recompile + link** with all of this.
- **`make serve`:** now **depends on `webassembly`** (builds the wasm if needed, then serves) + prints
  the URL — so it can't fail on a missing `web/`. Verified end-to-end nested: the published port is
  reachable (HTTP 200 from outside the container), `.wasm` serves as `application/wasm`, and the emcc
  `index.html` loads `index.js`.
- **Fixed the BLANK web page (root cause):** the ImGui OpenGL3 backend does NOT auto-select GLES for
  Emscripten (its header: "You need to #define IMGUI_IMPL_OPENGL_ES2/ES3 to use WebGL") — the wasm build
  had compiled the **desktop** GL path (GLSL 130), whose shaders don't compile under WebGL, so
  everything loaded (the server log showed 200s) but nothing drew. Fix: the wasm target compiles with
  **`-DIMGUI_IMPL_OPENGL_ES3`** + links **`-sMIN/MAX_WEBGL_VERSION=2`**, and `main.cpp` uses an **ES 3.0
  context + "#version 300 es"** on web (desktop GL 3.0 + GLSL 130 natively). Also `shell.html` fills the
  viewport and `main.cpp` matches the SDL window to the canvas CSS size each frame (1:1 input). Testing
  note: browsers cache `index.js`/`index.wasm` (304s) — **hard-refresh** after a rebuild.
- **UX + build tweaks (2026-10-24, maintainer feedback):** default is now **3 disks**; all six moves are
  **always shown** (fixed layout, illegal ones `BeginDisabled`'d, matching wx — no more jumping buttons);
  and the Dockerfile **pre-warms the Emscripten cache** (SDL2 port + system libs) at image-build so a
  `--rm` `make serve`/`webassembly` doesn't re-download/rebuild them each run. Verified nested: a fresh
  wasm build is a cache hit (~7s, no "compiled N inputs"/"generating system asset"); `libSDL2.a` +
  `libc++*.a` are baked into the image's emsdk cache.

**Remaining:**
1. **On-display runs** (maintainer's host): `make gui` (native window) and loading `web/` in a browser
   after `make serve` — confirm the board/menus/recipes work interactively.
2. **Optional:** a C++ CLI/TUI would need the rest of the core (commands/engine-dispatch/solvers)
   ported; the **GUI** is at parity without them (it drives model/presenter/recipe directly). Decision 3
   kept this round to the ImGui GUI, so that port is a later option, not required for GUI parity.
3. **(superseded)** "port the rest of the shared core" to `cpp/src/` — commands, engine (dispatch), presenter (the six
   peg labellings), recipe (record/replay), solvers — mirroring the Python/Rust layout, and wire the
   full UI (relabelling, recipes) + a parity check against the Python oracle. The model is the start.

## Related

- Sibling task: `tasks/archive/2026/10/24/split-into-per-language-containers.md` (this port lands as the `cpp/` subproject).
- Reference: `tasks/reference/imgui-cpp-native-and-wasm.md` (the dual native/wasm build) +
  `tasks/reference/per-language-subproject-layout.md` (the subproject template).
- Structural template: `rust/` and `tasks/archive/2026/10/23/port-to-rust-wxdragon.md`.
- Canonical source of truth: `python/src/hanoigame/`.
- ImGui emscripten reference: https://github.com/ocornut/imgui/tree/master/examples/example_sdl2_opengl3
