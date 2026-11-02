# A static "no-network" gate for the egui WebAssembly build

**Status:** DONE 2026-11-02 (William Emerison Six <billsix@gmail.com>) — implemented, committed, merged
(branch `checkNoNetwork`). The egui-web member of the no-network gate change.
**Priority:** 6 **Difficulty:** 2
**Template / full record:** `tasks/archive/2026/11/02/tauri-frontend-no-network-static-gate.md` — the
shared rationale, pattern, and decisions. This doc records only the egui-web-specific parts.
**Created:** 2026-11-01.

## What this did (egui-web-specific)

The Rust egui/eframe GUI also builds to WebAssembly (`cd rust && make egui-web` / `make egui-serve`,
Trunk + wasm-bindgen), a web target that must run offline. It is covered by the **same**
`rust/tools/check-no-network.sh` as the Tauri frontend (one Rust-side script for both Rust web targets):
it greps `hanoi-egui/index.html` + `Trunk.toml` alongside `tauri/frontend/`.

- **Trunk's `data-trunk rel="rust"` build directive is correctly allowed** (it carries no scheme or
  `//host`), so the trunk entry page passes.
- **Folded into the Rust `make type-check`** (rides `rust-type-check`, no new CI job). The grep is
  workspace-agnostic (plain file paths), so it reaches the separate `hanoi-egui` workspace without
  needing the `rust-check-egui` job.
- Scanned the committed source only — not the gitignored `dist/` Trunk output. (Whether the *build*
  itself is offline — Trunk/wasm-bindgen fetching a toolchain — is a separate concern, covered by the
  baked image / the offline-export test, not by this runtime-asset grep.)

## Verification

Green on the clean tree; an injected protocol-relative `<link href="//…">` in `index.html` made it FAIL
with the `file:line`; restored. (Full method + the Tauri side: the template task.)

## Related

- Template / full record: `tasks/archive/2026/11/02/tauri-frontend-no-network-static-gate.md`.
- `tasks/reference/ci-github-actions.md` — the Rust CI jobs (`rust-type-check`) the step rides in.
- Root `CLAUDE.md` — the egui-web build targets (`make egui-web` / `egui-serve`, behind `USE_WASM`).
