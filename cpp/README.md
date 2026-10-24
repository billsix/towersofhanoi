# hanoi — C++ (Dear ImGui, native + WebAssembly)

A **Dear ImGui** front-end for Towers of Hanoi, over the C++ port of the hanoi engine. One codebase
builds both a native desktop app and a browser (WebAssembly) app. Kept in sync with the canonical
Python implementation (`../python`).

## Dear ImGui version

Dear ImGui is **vendored** in `imgui/` at a pinned version: **v1.91.5** (core + the SDL2 and OpenGL3
backends). Update it to another branch, tag, or commit with:

```sh
make update-imgui IMGUI_REF=v1.92.0      # a tag
make update-imgui IMGUI_REF=master       # a branch
make update-imgui IMGUI_REF=<commit-SHA> # a specific commit
```

That overwrites the files in `imgui/` from `github.com/ocornut/imgui`, prints the new version, and
reminds you to update the pin noted here + in `CLAUDE.md` and to rebuild/re-verify.

## Build & run

Fedora + podman. The native build needs the C++/SDL2/OpenGL toolchain; the web build also needs the
Emscripten SDK (installed into the image when `USE_WASM=1`, the default).

```sh
make gui           # build + run the NATIVE app (SDL2 + OpenGL, on your X11/Wayland display)
make webassembly   # build the browser app → web/index.{html,js,wasm}
make serve         # serve web/ over http at http://localhost:8000  (wasm needs http, not file://)
make shell         # a dev shell in the image
make format        # clang-format (never touches the vendored imgui/)
```

`make image MINIMAL_IMAGE=1` builds a lean, native-only image (drops the Emscripten SDK and emacs).

## Layout

- `main.cpp` — the Dear ImGui app; the only target-specific code is the main loop
  (`emscripten_set_main_loop_arg` on web vs a native `while`) and disabling the filesystem/ini on web.
- `src/` — the ported engine (`model.hpp` so far; the rest of the shared core is in progress — see
  `../tasks/port-to-cpp-imgui-native-and-wasm.md`).
- `imgui/` — vendored Dear ImGui (see above).
- `CMakeLists.txt` — one build description driving both targets (gated on the `EMSCRIPTEN` variable).

Build mechanics + the dual native/wasm rationale: `../tasks/reference/imgui-cpp-native-and-wasm.md`.
