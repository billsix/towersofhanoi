# A static "no-network" gate for the C++ WebAssembly build

**Status:** DONE 2026-11-02 (William Emerison Six <billsix@gmail.com>) — implemented, committed, merged
(branch `checkNoNetwork`). The C++ member of the no-network gate change.
**Priority:** 6 **Difficulty:** 2
**Template / full record:** `tasks/archive/2026/11/02/tauri-frontend-no-network-static-gate.md` — the
shared rationale, pattern, and decisions. This doc records only the C++-specific parts.
**Created:** 2026-11-01.

## What this did (C++-specific)

The C++ Dear ImGui GUI also builds to WebAssembly (`cd cpp && make webassembly` / `make serve`), a web
target that must run offline. `cpp/tools/check-no-network.sh` greps **only `cpp/shell.html`** — the
Emscripten `--shell-file` template that becomes the generated `web/index.html`.

- **Scanned only `shell.html`, never a blanket `cpp/**/*.html`.** Two things are deliberately excluded:
  the generated `web/` tree (a gitignored build artifact — gate the source, not the output), and the
  vendored emacs `elpa/` tree (`cpp/entrypoint/dotfiles/.emacs.d/elpa/`), whose third-party package HTML
  carries its own CDN `<script>`/`<link>` tags that never ship in the hanoi app and must not trip the
  gate.
- **Wiring:** a standalone **`make check-no-network`** that runs the grep **host-side** (no `image`
  dependency) plus a new `cpp-check-no-network` CI job — because C++ has no `type-check` target to fold
  into, and a grep must not force CI to build the ~1.5 GB emsdk image.

## Verification

Green on the clean tree; an injected remote `<script>` in `shell.html` made it FAIL with the
`file:line`; restored. (Full method + the Rust side: the template task.)

## Related

- Template / full record: `tasks/archive/2026/11/02/tauri-frontend-no-network-static-gate.md`.
- `tasks/reference/imgui-cpp-native-and-wasm.md` — the wasm build (shell-file, offline emsdk, `web/`
  output) whose source this gate guards.
- `tasks/reference/ci-github-actions.md` — where the `cpp-check-no-network` job lives.
