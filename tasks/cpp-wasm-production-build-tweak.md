# Lean the C++ wasm build for production deployment (done 2026-11-21)

**Priority:** 7 **Difficulty:** 2
**Created:** 2026-11-02; **done:** 2026-11-21 (William Emerison Six <billsix@gmail.com>); branch
`gui-batch-2026-11-21`.

## What was done

- `cpp/CMakeLists.txt`: the WebAssembly link flags set `-sASSERTIONS=0` for a Release or MinSizeRel
  build (what `make webassembly` builds) and `1` otherwise, instead of a constant `1`, and add
  `-sENVIRONMENT=web`, which leaves out the Node.js/shell start-up code since the app only runs in a
  browser. Decisions (William Emerison Six <billsix@gmail.com>, 2026-11-21, "use your
  recommendations"): gate on build type rather than flip unconditionally; take the `ENVIRONMENT` trim
  in the same change.
- Deployment note, commands-forward: `tasks/reference/imgui-cpp-native-and-wasm.md` ("Deploying the
  web build", plus the flag paragraph), with a one-line pointer in `cpp/README.md`.

## Measured (Release build, before → after)

| file | bytes | gzipped |
|---|---|---|
| `index.js` | 187,486 → 152,712 | 41,546 → 32,952 |
| `index.wasm` | 753,999 → 742,879 | 265,931 → 271,769 |

The wasm's gzipped size went up slightly although its raw size went down; the javascript, which no
longer carries the Node.js paths, accounts for most of the saving.

## Verification

- The link line shows `-sASSERTIONS=0 -sENVIRONMENT=web` for the Release build; the native build (both
  GUIs) and the doctest suite were unchanged by the `EMSCRIPTEN`-only edit (built earlier in this batch).
- The Release build, served by `python3 -m http.server -d web`, loads and renders in headless Chromium
  with software WebGL (board, menus, first-run How-to-Play). Chromium was installed in the sandbox for
  this check (`dnf install chromium`).
- `cpp/tools/check-no-network.sh`: OK.
