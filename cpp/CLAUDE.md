# hanoi — C++ subproject (Dear ImGui, native + WebAssembly)

The **C++** implementation of hanoi (github.com/billsix/towersofhanoi): a **Dear ImGui** GUI over the
hanoi engine, building **both** a native desktop binary (`make gui`) and **WebAssembly** for a browser
(`make webassembly`). Self-contained: own `Dockerfile`, `Makefile`, `entrypoint/`, and emacs set. Kept
in sync with the Python canonical source (`../python`) — **never a replacement** (the Python package is
the behaviour oracle; if it changes, this port must be updated to match, not left to drift).

## Status

- **Engine (header-only, `src/`):** `model.hpp` (state + legal moves), `presenter.hpp` (the six peg
  **labellings** + label↔tower), `recipe.hpp` (recorder / registry / replay / rebinding) — ported from
  the canonical Python. The GUI drives these directly; the text-interface pieces (commands / engine
  dispatch / solvers) are only needed for a C++ CLI/TUI (not built — the GUI is at parity without them).
- **GUI:** `main.cpp` — one Dear ImGui app (native SDL2+OpenGL3; wasm OpenGL3→WebGL) at **feature
  parity with the wx GUI**: a menubar (Game → disk count 1–8 / Restart; Relabel → the 6 labellings;
  Recipe → save/reset/replay), the board coloured by label, moves in current labels, and the
  label→peg rebinding shown when relabelled. Target-specific code is only the main loop
  (`emscripten_set_main_loop_arg` vs native `while`), the no-ini/filesystem on web, and matching the SDL
  window to the browser canvas size.
- **Dear ImGui is vendored** at `imgui/` (pinned **v1.91.5**: core + `backends/imgui_impl_sdl2` +
  `imgui_impl_opengl3`). Re-vendor by copying those files from a pinned imgui tag.
- **doctest is vendored** at `doctest/doctest.h` (single header, pinned **v2.5.3**; `make
  update-doctest`). The engine's unit tests are `TEST_CASE`s inline in `src/*.hpp`, run by `make
  test` — see Conventions.

## Build / container workflow

Fedora-44 + podman template. Mounts at `/hanoi-cpp`. One `CMakeLists.txt` drives both targets (gated on
the `EMSCRIPTEN` variable).

- `make image` — build; `USE_EMACS` (default 1) installs emacs + clangd; `USE_WASM` (default 1) installs
  the pinned Emscripten SDK (`EMSDK_VERSION`, ~1-1.5 GB) needed for `make webassembly`. `MINIMAL_IMAGE=1`
  drops both → a lean native-only image.
- `make gui` — build + run the NATIVE app (cmake + system SDL2/OpenGL, on your X11/Wayland display).
- `make webassembly` — `emcmake cmake` → `web/index.{html,js,wasm}` (needs a `USE_WASM=1` image).
- `make serve` — serve `web/` over http at :8000 (wasm must be served over http, never `file://`).
- `make test` — build + run the engine unit tests (doctest) under `ctest`. The `TEST_CASE`s live
  **inline in the engine headers** (`src/*.hpp`), beside the code they test; the GUI/wasm binaries
  compile them out with `-DDOCTEST_CONFIG_DISABLE` (set per-target in `CMakeLists.txt`), and a
  separate native-only `hanoi-tests` executable (runner at `tests/run_tests.cpp`) builds them in.
- `make format` (clang-format, never the vendored `imgui/` or `doctest/`), `make shell`/`shell-exec`,
  `make image-export`/`image-import`, `make update-emacs-packages`.
- `make update-doctest DOCTEST_REF=<tag>` — re-vendor the doctest single header (`doctest/doctest.h`,
  pinned **v2.5.3**), like `make update-imgui`.

> **Fedora gotcha:** `SDL2-devel` on F44 is the `sdl2-compat` shim over SDL3 (`sdl2-config`/`sdl2.pc`
> still work). The wasm build's `-sUSE_SDL=2` is the genuine SDL2 port. Full build detail + flags:
> `../tasks/reference/imgui-cpp-native-and-wasm.md`.

## Emacs

`entrypoint/dotfiles/.emacs.d/` — `init.el` hooks `c/c++-mode` to **lsp-mode** + **clangd** (reads
`compile_commands.json` from the cmake `build/` dir), with `clang-format` (`C-c f`) and `company`.
Installed into the image, bind-mounted at runtime, and baked. `init.el` pins the LSP root to
`/hanoi-cpp`, ignores the build/cache dirs, and enables yasnippet — the hanoi per-language convention
(repo-root `CLAUDE.md` + `../tasks/reference/per-language-subproject-layout.md`).

## Conventions

C++17. Keep the GUI (`main.cpp`) thin — game logic lives in `src/` (the ported engine), mirroring the
Python layering. Never edit the vendored `imgui/` or `doctest/` trees (re-vendor from a pinned tag
instead). **Tests are doctests by default** — a test documenting an engine function/class is a
`TEST_CASE` placed **right after** that function (or after the class, for `Game`), inside
`namespace hanoi`; the GUI targets set `DOCTEST_CONFIG_DISABLE` so the cases vanish from the binaries.
This is the C++ analogue of the Python/Rust doctests-by-default rule
(`~/.claude/reference/doctests-by-default.md`). Reference:
`../tasks/reference/imgui-cpp-native-and-wasm.md` (the dual native/wasm build) and
`../tasks/reference/per-language-subproject-layout.md` (the subproject template).
