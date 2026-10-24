# Dear ImGui in C++: one source, native desktop + WebAssembly

**Reference document** — how to build a Dear ImGui C++ app that compiles BOTH to a native desktop
binary (run in the Fedora-44 container via X11/Wayland) AND to WebAssembly for a browser, from one
codebase. Durable knowledge, reusable beyond hanoi. Created 2026-10-24 (William Emerison Six
<billsix@gmail.com>) from web research verified against ocornut/imgui `master`, emscripten.org, and live
Fedora-44 dnf metadata. Drives the hanoi `cpp/` subproject (`tasks/port-to-cpp-imgui-native-and-wasm.md`).

## The approach: SDL2 + OpenGL3, shared source

Dear ImGui's `examples/example_sdl2_opengl3/` is the canonical dual-target example: the **same**
`main.cpp` builds native (SDL2 + the OpenGL3 backend) and, under Emscripten, with the OpenGL3 backend's
calls mapped onto **WebGL** and SDL2 provided by Emscripten's bundled SDL2 port (`-sUSE_SDL=2`). Upstream:
"The SDL+GL, GLFW+GL and SDL+WebGPU examples are all ready to build and run with Emscripten."

**What differs between targets is tiny** — only the main loop and the filesystem/ini handling:

- **Main loop (the crux).** A browser tab cannot block in a `while(1)`; Emscripten must own the loop via
  `emscripten_set_main_loop[_arg]`. ImGui ships a stub, `examples/libs/emscripten/emscripten_mainloop_stub.h`,
  with `EMSCRIPTEN_MAINLOOP_BEGIN`/`EMSCRIPTEN_MAINLOOP_END` so the *same* loop-body text works both ways:
  native → `while (!done) {…}`; web → the body becomes a callback passed to
  `emscripten_set_main_loop_arg(..., fps=0, simulate_infinite_loop=true)`. Shape:
  ```cpp
  #ifdef __EMSCRIPTEN__
      io.IniFilename = nullptr;            // no fopen of imgui.ini on web
      EMSCRIPTEN_MAINLOOP_BEGIN
  #else
      while (!done)
  #endif
      { /* poll SDL events → ImGui frame → render → SDL_GL_SwapWindow */ }
  #ifdef __EMSCRIPTEN__
      EMSCRIPTEN_MAINLOOP_END;
  #endif
  ```
- Everything else — SDL init, window + GL context, `ImGui::CreateContext()`,
  `ImGui_ImplSDL2_InitForOpenGL`, `ImGui_ImplOpenGL3_Init(glsl_version)`, the per-frame UI, shutdown — is
  identical. The GL/GLSL version is chosen at compile time (default desktop "GL 3.0 + GLSL 130" path;
  emcc maps it onto WebGL — you do NOT define `IMGUI_IMPL_OPENGL_ES2/3` unless you need an explicit GLES
  path, see Gotchas).

## ImGui is vendored source (no package, no library)

Compile these `.cpp` into your binary (same list for native and web); include `-I<imgui> -I<imgui>/backends`:
`imgui.cpp`, `imgui_draw.cpp`, `imgui_tables.cpp`, `imgui_widgets.cpp`, `backends/imgui_impl_sdl2.cpp`,
`backends/imgui_impl_opengl3.cpp`, plus your `main.cpp`. (`imgui_demo.cpp` only while developing.) **Pin a
version** (vendor a tagged release) for a reproducible, offline build.

## Native build on Fedora 44

dnf packages (verified on F44): `gcc-c++`, `SDL2-devel`, `mesa-libGL-devel`, and `cmake`/`ninja-build`/
`make`; for the emacs clangd set add `clang`, `clang-tools-extra`. Link flags on Linux: `-lGL -ldl`
+ `sdl2-config --libs`; compile with `sdl2-config --cflags` (pkg-config `sdl2` works too). C++ ≥ 11.

> **Fedora 42+ gotcha:** there is no classic SDL2 — `SDL2-devel` is a virtual provide satisfied by
> **`sdl2-compat-devel`**, a shim implementing the SDL2 API/ABI on top of **SDL3**. `sdl2-config`/
> `sdl2.pc` still work (so Makefiles are unchanged), but native SDL2 is really SDL3 underneath. The web
> build's `-sUSE_SDL=2` is the genuine SDL2 C port, so if SDL behaves differently native vs. web, the
> shim is a suspect. (`mesa-libGLES-devel` isn't a real F44 name — it's `libglvnd-devel`; only needed for
> an explicit GLES build.)

## Emscripten in a Fedora container (the Dockerfile crux)

**There is no official Fedora `emscripten` dnf package** (only an unofficial Copr — avoid). The canonical,
reproducible path is the **emsdk**, cloned into the image at a **pinned version** (not `latest`, which
drifts):
```sh
dnf install -y git python3            # emsdk's only prereqs (it ships its own clang/node/binaryen)
git clone https://github.com/emscripten-core/emsdk.git /opt/emsdk
cd /opt/emsdk && ./emsdk install <X.Y.Z> && ./emsdk activate <X.Y.Z>
```
`./emsdk install` downloads **prebuilt** LLVM/clang (wasm backend) + Node.js + Binaryen (`wasm-opt`) —
**~1–1.5 GB** on disk (LLVM is the bulk; prune `emsdk/downloads` after activation to shrink). emsdk
installs nothing system-wide — everything stays under `/opt/emsdk`. **In a container, `source
emsdk_env.sh` only affects the current shell**, so either source it inside each build `RUN`, or bake the
three tool dirs onto `PATH` with `ENV` so `emcc`/`em++`/`emcmake` resolve non-interactively. (The official
`emscripten/emsdk` Docker image is an alternative but is Debian-based — it conflicts with this project's
Fedora-44 base + native-run story; clone-into-Fedora keeps one image for both `make gui` and `make
webassembly`. The old `trzeci/emscripten` image is deprecated.)

## The build flags (from the current ImGui `Makefile.emscripten`)

Compile+link both: `-sUSE_SDL=2` (bundled SDL2 port), `-sDISABLE_EXCEPTION_CATCHING=1`. Link only:
`-sWASM=1`, `-sALLOW_MEMORY_GROWTH=1`, `-sNO_EXIT_RUNTIME=0`, `-sASSERTIONS=1` (drop to 0 for a size
release), `--shell-file <shell.html>`. Filesystem off (default): `-sNO_FILESYSTEM=1` (link) **and**
`-DIMGUI_DISABLE_FILE_FUNCTIONS` (compile) + `io.IniFilename=nullptr` (runtime) — no imgui.ini on web.
Compile with `-Os` for size. The example does NOT set `MIN/MAX_WEBGL_VERSION`, `FULL_ES3`, or `GL_*` —
it relies on emcc defaulting the desktop OpenGL3 backend onto WebGL (see Gotchas for when to override).

## One CMakeLists drives both targets (recommended for this repo)

`emcmake` passes Emscripten's CMake toolchain file automatically, so a single `CMakeLists.txt` with
`CMAKE_EXPORT_COMPILE_COMMANDS=ON` builds both; gate web-only bits on the predefined `EMSCRIPTEN` variable:
- **Native:** `cmake -B build && cmake --build build` → a native binary.
- **Web:** `emcmake cmake -B build-web && cmake --build build-web`. Set the target's output suffix to
  `.html` (`set_target_properties(<tgt> PROPERTIES SUFFIX ".html")`) so emcc emits `index.html` +
  `index.js` + `index.wasm` (**all three required**); put the `-s…`/`--shell-file` flags in
  `target_link_options(... $<$<BOOL:${EMSCRIPTEN}>:...>)`. The output extension drives the artifact type
  (`.html` → launcher+js+wasm; `.js` → js+wasm; `.wasm` → standalone; `-sSINGLE_FILE` inlines all).
- **Serve:** `python3 -m http.server -d web` (then http://localhost:8000) or `emrun web/index.html`.
  **Must be served over http** — browsers refuse to instantiate `.wasm` over `file://` (the #1 "blank
  page" cause).

## Gotchas

- **Serve over http, never `file://`.** (Above — the most common failure.)
- **Emscripten owns the loop** — a blocking `while(1)` freezes the tab; use the mainloop stub.
- **WebGL version:** emcc defaults to WebGL1. ImGui's OpenGL3 backend usually works, but for shader/context
  trouble be explicit: `-sMIN_WEBGL_VERSION=2 -sMAX_WEBGL_VERSION=2` (WebGL2 ≈ GLES3) and/or compile the
  ES3 path. `USE_WEBGL2=1` is deprecated → use `MAX_WEBGL_VERSION=2`.
- **No filesystem on web:** do all three — `-sNO_FILESYSTEM=1`, `-DIMGUI_DISABLE_FILE_FUNCTIONS`,
  `io.IniFilename=nullptr`. For persisted settings on web, use IDBFS.
- **Fonts:** ImGui's built-in font is an embedded C array (no file I/O) — fine with `NO_FILESYSTEM`, and
  enough for a board drawn with draw-list primitives. A custom `.ttf` needs either `AddFontFromMemoryTTF`
  (embed as a C array, keeps `NO_FILESYSTEM`) or `--preload-file fonts@/fonts` + `USE_FILE_SYSTEM=1`.
- **`-sGL_ENABLE_GET_PROC_ADDRESS=1`** only if you add a GL loader (glad/glew) — ImGui's
  `imgui_impl_opengl3` has its own loader and needs none under Emscripten.

## Sources (verified 2026-10-24)

- Example + its build files: https://github.com/ocornut/imgui/tree/master/examples/example_sdl2_opengl3
  (`main.cpp`, `Makefile`, `Makefile.emscripten`), mainloop stub
  `examples/libs/emscripten/emscripten_mainloop_stub.h`.
- emsdk install: https://emscripten.org/docs/getting_started/downloads.html
- Building projects (emcmake/emmake, output extensions): https://emscripten.org/docs/compiling/Building-Projects.html
- Settings reference: https://emscripten.org/docs/tools_reference/settings_reference.html
- Fedora SDL2→sdl2-compat note: https://github.com/oznogon/EmptyEpsilon/wiki/Build-on-Fedora-Linux
