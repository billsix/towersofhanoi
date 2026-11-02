# A static "no-network" gate for the web front-ends

**Status:** DONE 2026-11-02 (William Emerison Six <billsix@gmail.com>) — implemented, committed, merged
(branch `checkNoNetwork`). This was the template; the two sibling gates (C++ wasm, egui-web) landed in
the same change — see them for their per-target specifics.
**Priority:** 6 **Difficulty:** 2
**Parent:** `tasks/archive/2026/11/01/tauri-frontend-js-options.md` (investigation; this was the one
concrete change it recommended — everything else was "already done, stay the course").
**Created:** 2026-11-01.

## What this did

The web front-ends must run entirely from local/embedded assets with no network — a hard maintainer
constraint — and the maintainer wanted that enforced mechanically rather than re-audited by eye. All
three web targets were in fact clean already, but nothing stopped a future edit from adding a CDN
`<script>`, a web-font `@import`, a remote `<img>`, or a `fetch()`/WebSocket. This added a cheap static
grep gate per web target that fails if any committed web source references a remote resource, wired into
each subproject's static gate and CI, with no new dependency, no network, and no Node.

## What was built

- **Two per-subproject scripts** (both portable — run in-container or host-side — and committed
  executable):
  - `rust/tools/check-no-network.sh` covers **both** Rust web targets: the Tauri frontend
    (`tauri/frontend/*.{html,js,css}`) and the egui-web source (`hanoi-egui/index.html`, `Trunk.toml`).
  - `cpp/tools/check-no-network.sh` covers the C++ wasm source (`cpp/shell.html` only).
- **The pattern:** fail on `http(s)://` / `ws(s)://` anywhere, and protocol-relative `//host` in
  `src=`/`href=`/`url(…)`. Allowed: relative paths, `data:` URIs, Tauri `invoke()`/`window.__TAURI__`,
  and Trunk's `data-trunk` directive (no scheme). A URL in a *comment* trips it too (conservative; the
  script says to allow-list a genuine exception in-place with a reason). Single-pattern grep, so it is
  safe-by-shape on exit status.
- **Wiring:** the Rust check is folded into `make type-check` (accumulating exit status with the Deno
  steps, in-container; rides the existing `rust-type-check` CI job — no new job). The C++ check is a
  standalone `make check-no-network` that runs the grep **host-side** (no `image` dependency) plus a new
  `cpp-check-no-network` CI job — deliberately not behind `: image`, so CI needn't build the ~1.5 GB
  emsdk image to grep one file.
- **Docs:** `rust/CLAUDE.md`, `cpp/CLAUDE.md`, and the root `CLAUDE.md` target/CI lists updated; the
  offline runtime-proof noted in each subproject `CLAUDE.md`.

## Decisions

- **Per-subproject copies, not one shared vendored script** (the logic is ~8 lines of grep and hanoi
  prizes subproject self-containment; only two subprojects need it). Promote to a shared vendored script
  (à la `check_local_annotations.py`) only if a 3rd subproject appears.
- **Rust wiring folded into `make type-check`** (no new target/job) per the recorded 2026-11-01
  maintainer decision; **C++ wiring standalone + host-side** because C++ has no type-check target and a
  grep must not pull in the emsdk image.
- **Scope covered all three web targets at once** (the sibling tasks), this one being the template.

## Verification

Ran host-side 2026-11-02: green on the clean tree; injecting a remote `<script src="https://…">` into
`tauri/frontend/index.html`, a protocol-relative `<link href="//…">` into `hanoi-egui/index.html`, and a
remote `<script>` into `cpp/shell.html` each made the right gate FAIL with the offending `file:line`;
`git checkout` restored all three and the gates went green again. The Make/CI wiring was verified by
inspection (running it would build the subproject images).

## Related

- Siblings (same change, per-target specifics): `tasks/archive/2026/11/02/cpp-wasm-no-network-static-gate.md`,
  `tasks/archive/2026/11/02/egui-web-no-network-static-gate.md`.
- Parent investigation: `tasks/archive/2026/11/01/tauri-frontend-js-options.md`.
- `tasks/reference/ci-github-actions.md` — the CI jobs the steps ride in.
- The JS static gate it rides alongside (Deno `check`/`lint`/`fmt`, no `node_modules`):
  <https://github.com/billsix/runClaudeInContainer/blob/master/tasks/reference/javascript-coding-standard.md>.
- Personal overlay "Self-contained images + live source" — the offline guarantee this statically
  enforces for the web assets.
