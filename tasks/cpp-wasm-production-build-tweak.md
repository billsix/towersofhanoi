# Lean the C++ wasm build for production deployment

**Status:** proposed — needs go-ahead.
**Priority:** 7 **Difficulty:** 2
**Created:** 2026-11-02 (William Emerison Six <billsix@gmail.com>). Spun off a deploy Q&A:
the C++ Dear ImGui wasm app runs fine on any static host as-is (single-threaded → no
SharedArrayBuffer → no COOP/COEP headers needed); this is the optional polish for a *deployed*
build.

## BLUF

The wasm build (`cpp/`, `make webassembly` → `cpp/web/index.{html,js,wasm}`) hard-codes
`-sASSERTIONS=1` (`cpp/CMakeLists.txt:44`) in every configuration. Assertions are a dev aid
(extra runtime checks + code size); a deployed build doesn't want them. "Done" = assertions are
**on for a debug wasm build and off for the Release build** (`make webassembly` already configures
`-DCMAKE_BUILD_TYPE=Release`, `cpp/Makefile:130`), so the standard deploy artifact is lean with no
new target — plus a short deployment note (serve over http(s), optional host gzip/brotli, the
`application/wasm` MIME fallback). No behaviour change, no new dependency.

## Context (read first)

- **The flags today** (`cpp/CMakeLists.txt:29-46`, inside `if(EMSCRIPTEN)`): `-Os`,
  `-sALLOW_MEMORY_GROWTH=1`, `-sNO_FILESYSTEM=1`, `-sASSERTIONS=1`, WebGL2 forced
  (`-sMIN/MAX_WEBGL_VERSION=2`), SDL2 + GLES3, `--shell-file shell.html`. Already size-conscious
  (`-Os`); the one dev-only leftover in the deploy path is `-sASSERTIONS=1`.
- **The build type is already Release** for the deploy artifact: `make webassembly` runs `emcmake
  cmake ... -DCMAKE_BUILD_TYPE=Release` (`cpp/Makefile:130`). So a build-type gate needs no new
  target — the existing `make webassembly` picks up the lean setting automatically, and any future
  debug wasm invocation keeps assertions.
- **Flag rationale lives in** `tasks/reference/imgui-cpp-native-and-wasm.md` (the dual native/wasm
  build + why each `-s…` flag is set). Update it there when the ASSERTIONS flag becomes conditional.
- **Why only polish:** the app already deploys and runs on plain static hosting (verified by the
  flag audit 2026-11-02; no threads, no network at runtime — the latter enforced by
  `cpp/tools/check-no-network.sh`). This task buys a smaller `.wasm` and no production assertion
  overhead, nothing more.

## Plan

1. In `cpp/CMakeLists.txt` (the `if(EMSCRIPTEN)` block), make the assertion level follow the build
   type instead of a constant: `-sASSERTIONS=0` for a Release/MinSizeRel build, `-sASSERTIONS=1`
   otherwise (e.g. a CMake generator expression `-sASSERTIONS=$<IF:$<CONFIG:Release>,0,1>`, or an
   `if(CMAKE_BUILD_TYPE STREQUAL "Release")` branch — whichever reads cleaner for a newcomer).
2. (Optional, decide in Q2) consider `-sENVIRONMENT=web` to drop the unused Node/shell runtime glue
   from `index.js` — a further small trim, web-only. Confirm it doesn't break `make serve`.
3. Rebuild (`make webassembly`), confirm `cpp/web/` still loads and runs (`make serve`, open with
   the network cut — the no-network guarantee), and note the before/after `.wasm` size in this doc.
4. Add a brief **deployment** note where it belongs (README or `imgui-cpp-native-and-wasm.md`):
   upload `cpp/web/*` to any static host, serve over http(s) (not `file://`), no COOP/COEP needed;
   the host ideally serves `.wasm` as `application/wasm` (else Emscripten falls back with a console
   warning and still runs); enabling gzip/brotli on the host shrinks the transfer. Keep it
   commands-forward.
5. Update `tasks/reference/imgui-cpp-native-and-wasm.md` for the now-conditional ASSERTIONS flag.

## Open questions

1. **Gate on build type, or flip unconditionally?** Recommend **gate on build type** (Release →
   `ASSERTIONS=0`), so the deploy artifact is lean while a debug wasm build keeps the checks — no
   new target, and `make webassembly` is already Release. Flipping to a flat `=0` is simpler but
   loses the dev-time safety net. Your call.
2. **Also add `-sENVIRONMENT=web`** (drop Node/shell glue) while here, or keep scope to the
   assertion flag only? Recommend doing it in the same small change (it's web-only and the app is
   only ever served to a browser), but it's a separable trim. Your call.

## Related

- `tasks/reference/imgui-cpp-native-and-wasm.md` — the wasm build + flag rationale (the doc to update).
- `cpp/CLAUDE.md` — the `make webassembly` / `serve` targets and the `check-no-network` gate.
- `tasks/archive/2026/11/02/cpp-wasm-no-network-static-gate.md` — the sibling guarantee (no remote
  resources at runtime) that makes the deployed build safe to host anywhere.
