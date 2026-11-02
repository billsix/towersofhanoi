# Add a static "no-network" gate for the C++ WebAssembly build

**Status:** DONE 2026-11-02 (William Emerison Six <billsix@gmail.com>) — staged, not committed
(stage-only default). Ready to archive after the maintainer's work commit. Landed in the same change as
the template task; full work record + decisions there.
**Priority:** 6 **Difficulty:** 2
**Template:** `tasks/tauri-frontend-no-network-static-gate.md` (the proven pattern; read it first for the
rationale — this doc states only what differs for the C++ wasm target).
**Created:** 2026-11-01 (William Emerison Six <billsix@gmail.com>). Sibling of the Tauri gate, scaffolded
at the maintainer's go-ahead to cover every local web target.

## BLUF

The C++ Dear ImGui GUI also builds to **WebAssembly** (`cd cpp && make webassembly` / `make serve`), a
web target that must **run locally with no network** and be **statically verifiable**. Add the same
cheap static grep gate the Tauri frontend gets — fail if any committed C++ **web source** references a
remote resource — wired into the C++ subproject's static gate and CI. "Done" = the gate runs green on
the current tree, fails on an injected CDN reference, and is in CI.

## What differs from the Tauri template

- **What to scan (the app's committed web source):** `cpp/shell.html` — the Emscripten `--shell-file`
  template that becomes `web/index.html` — plus any committed `.css`/`.js` the app serves. **Do NOT scan
  the generated `web/` tree** (gitignored emscripten output: `index.html`/`.js`/`.wasm`) — it is a build
  artifact; gate the *source* that produces it.
- **Critical exclusion — the vendored emacs `elpa/` tree.** `cpp/entrypoint/dotfiles/.emacs.d/elpa/`
  contains third-party emacs packages whose own HTML carries CDN `<script>`/`<link>` tags (e.g.
  `lsp-ui-doc.html` → cdnjs). Those never ship in the hanoi app and must **not** fail the gate. Scope
  the grep to `shell.html` (+ explicit app web files), **never** a blanket `cpp/**/*.html`. (Verified
  2026-11-01: the only remote URLs under `cpp/` live in `elpa/`; `shell.html` is clean.)
- **Also check the Emscripten link flags** aren't pulling a remote shell/asset: the build is fully local
  (vendored ImGui, emsdk baked in the image per `tasks/reference/imgui-cpp-native-and-wasm.md`), so this
  is a quick confirm, not expected to find anything.
- **Wiring:** C++ has no `type-check` target (the compiler is the type check — `make build`). Put the
  gate in its own `## `-documented **`make check-no-network`**, or fold it into `make format`'s
  check-only sibling if one fits; add a `cpp-check-no-network` step to the C++ CI (the `cpp-build` or a
  new tiny job). Match `tasks/reference/ci-github-actions.md`'s thin-wrapper shape. (Open question 1.)

## Plan

1. Write `cpp/tools/check-no-network.sh` (or reuse a shared script if the Tauri task's open-question-3
   promotion happens): `grep -nE 'https?://|src="//'` over **`shell.html`** + any listed app web files,
   printing `file:line`, exit non-zero on a hit. Single-command → safe-by-shape on exit status.
2. Wire into a `make check-no-network` (C++ subproject) + a CI step.
3. Verify: green on the current tree; inject a `<script src="https://x">` into `shell.html` → fails with
   the right `file:line`; remove it.
4. Document the runtime proof: `make webassembly` then serve/open with the network cut — the page must
   render fully from local `web/` assets.

## Done (2026-11-02)

`cpp/tools/check-no-network.sh` scans **only** `cpp/shell.html` (never the generated `web/` nor the
vendored emacs `elpa/` tree, so the elpa CDN tags can't trip it). Wired into a standalone `make
check-no-network` that runs the grep **host-side** (no `image` dep — OQ1 resolved: standalone, not
`cpp-build`, and host-side so CI doesn't build the emsdk image) + a new `cpp-check-no-network` CI job.
OQ2 (shared vs per-copy): per-subproject copy, per the template's OQ3 resolution. Verified: green on the
clean tree; an injected remote `<script>` in `shell.html` made it FAIL with the `file:line`; restored.
Full details + the Rust side: `tasks/tauri-frontend-no-network-static-gate.md` "Done — what was built".

## Open questions

*(Both resolved 2026-11-02 — see Done above.)*

1. ~~Wiring on the C++ side~~ — **standalone `make check-no-network`, host-side** (no image), + its own
   `cpp-check-no-network` CI job.
2. ~~Shared script vs per-subproject copy~~ — **per-subproject copy** (template OQ3).

## Related

- Template + rationale: `tasks/tauri-frontend-no-network-static-gate.md`.
- `tasks/reference/imgui-cpp-native-and-wasm.md` — the wasm build (shell-file, offline emsdk, `web/`
  output) this gate guards the source of.
- `tasks/reference/ci-github-actions.md` — the C++ CI jobs a step is added to.
