# Add a static "no-network" gate for the egui WebAssembly build

**Status:** proposed — needs go-ahead.
**Priority:** 6 **Difficulty:** 2
**Template:** `tasks/tauri-frontend-no-network-static-gate.md` (the proven pattern; read it first for the
rationale — this doc states only what differs for the egui-web target).
**Created:** 2026-11-01 (William Emerison Six <billsix@gmail.com>). Sibling of the Tauri gate, scaffolded
at the maintainer's go-ahead to cover every local web target.

## BLUF

The Rust egui/eframe GUI also builds to **WebAssembly** (`cd rust && make egui-web` / `make egui-serve`,
Trunk + wasm-bindgen), a web target that must **run locally with no network** and be **statically
verifiable**. Add the same cheap static grep gate — fail if the committed egui-web source references a
remote resource — wired into the Rust subproject's static gate and CI. "Done" = green on the current
tree, fails on an injected CDN reference, in CI.

## What differs from the Tauri template

- **What to scan:** `rust/hanoi-egui/index.html` (Trunk's source HTML, with its `<link data-trunk>`
  directives) + any committed `.css`/`.js` assets it references. `Trunk.toml` too — confirm no
  `<link data-trunk rel="...">` or asset pulls a remote URL. (Verified 2026-11-01: `index.html` is
  clean — no remote URLs; committed web files are `index.html`, `Trunk.toml`, `Cargo.toml`.)
- **Don't scan the generated `dist/` / Trunk output** (gitignored build artifact) — gate the source.
- **Build-vs-runtime note (not this gate's job, but say it):** Trunk/wasm-bindgen is a *build* tool that
  can fetch the `wasm-bindgen` CLI / the wasm target toolchain. Per "Self-contained images + live
  source" those must be baked into the image (offline). This gate only checks the **web assets for
  remote runtime references**; whether the *build* is offline is a separate check (the offline-export
  test), noted here so the two aren't conflated.
- **Wiring:** fold into the Rust subproject's **`make type-check`** (the static-gate bucket that already
  runs Deno over the Tauri frontend and would now also carry the egui-web grep) **or** a standalone
  `make check-no-network` — decide alongside how the Tauri gate lands in `rust-type-check`. The Rust CI
  already has a `rust-type-check` job to extend. (Open question 1.)

## Plan

1. Write `rust/hanoi-egui/tools/check-no-network.sh` (or reuse a shared script per the Tauri task's
   open-question-3): `grep -nE 'https?://|src="//'` over `index.html` + `Trunk.toml` + any app web
   assets, printing `file:line`, exit non-zero on a hit.
2. Wire into the Rust static gate + CI (`rust-type-check`).
3. Verify: green now; inject a remote `<link>`/`<script>` into `index.html` → fails with `file:line`;
   remove it.
4. Document the runtime proof: `make egui-web` then serve/open with the network cut — the page renders
   fully from local `dist/` assets.

## Open questions

1. **Wiring on the Rust side** — fold into `make type-check` (recommended, mirrors the Tauri decision
   and the egui-web assets are a natural member of the same static gate), or a standalone target? Note
   the egui-web assets live in the `hanoi-egui` *separate workspace*, so confirm the Rust `make
   type-check`/CI reaches them (the `rust-check-egui` job is egui's compile gate — the no-network grep
   is cheap and workspace-agnostic, so either job can host it). Your call.
2. **Shared script vs per-subproject copy** — same as the Tauri task's open question 3.

## Related

- Template + rationale: `tasks/tauri-frontend-no-network-static-gate.md`.
- `tasks/reference/ci-github-actions.md` — the Rust CI jobs (`rust-type-check`, `rust-check-egui`) a step
  is added to.
- Root `CLAUDE.md` — the egui-web build targets (`make egui-web` / `egui-serve`, behind `USE_WASM`).
