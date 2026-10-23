# Lint/format the Tauri frontend web files

**Status:** proposed — go-ahead given (the maintainer asked for this task; not yet started).
**Priority:** 5 **Difficulty:** 2
**Next:** `tasks/tauri-frontend-js-options.md` (investigate the JS code's future — do this lint first).
**Created:** 2026-10-23 (William Emerison Six <billsix@gmail.com>). Requested as the deferred-optional
item from the completed Tauri port (`tasks/archive/2026/10/23/port-to-tauri.md`): wire a lint/format
for the web side.

## BLUF

The Tauri front-end's three static web files — `tauri/frontend/{index.html,main.js,style.css}` — have
no linter/formatter, the one unmet item from the Tauri port's original "done" bar. Add one and wire it
into the project's gate so the web side is held to a consistent style the way `cargo fmt`/`clippy`
holds the Rust side. "Done" = the three files pass a formatter + linter, the check is runnable from a
`make` target (and ideally the same place `format` lives), and the choice honours the port's
**no-Node-toolchain** decision (keep the image lean). Small, mechanical; no behaviour change.

## Context (read first)

- **The frontend is deliberately plain vanilla JS, no bundler, no Node** (`port-to-tauri.md` decision 1;
  runClaudeInContainer `tasks/reference/tauri-desktop-apps.md` "Frontend without a bundler"). So adding
  a JS linter must NOT quietly drag a full Node/npm toolchain into the hanoi image — that would undo
  that decision and bloat a Python+Rust image.
- **`main.js` is ~130 lines** of vanilla JS over `window.__TAURI__.core.invoke` + a `<canvas>` renderer;
  `index.html` and `style.css` are small. This is a style/consistency gate, not a type system (the
  type-safety question is the follow-up task, below — keep that out of scope here).
- The Rust side's gate is `cargo fmt --check` + `cargo clippy -D warnings`; this task gives the web
  side a parallel, so a future contributor's frontend edits stay tidy.

## Options for the tool (decide in Open questions)

1. **Biome** (recommended to evaluate first) — a single self-contained binary (Rust-based) that does
   **both** format and lint for JS/TS/CSS/JSON, with **no Node project required**. Fits the
   no-Node-toolchain constraint best: install the one binary in the Rust install group
   (`entrypoint/04-install-rust.sh`) or fetch it, run `biome check`/`biome format`. Verify it is
   packaged/fetchable for Fedora 44 without npm.
2. **Prettier + ESLint** — the conventional pair, but both are npm packages → needs Node in the image
   (against the decision) or a one-off `npx` with network (against offline/self-contained). Only if
   Biome doesn't fit.
3. **Deno fmt/lint** — Deno is a single binary that formats+lints JS/TS; another no-npm option if
   Biome is unavailable.

## Plan (sketch — refine after the tool decision)

1. Pick the tool (Open question 1) and get it into the image's Rust/web install group (or document a
   host-run path), keeping the image lean.
2. Add an `entrypoint/<name>.sh` (or extend the existing format path) that runs the formatter + linter
   over `tauri/frontend/`, with the accumulate-`status` shape (every step runs, nonzero if any failed)
   — the cross-project multi-step-check-script rule.
3. Add a `make` target (e.g. `tauri-lint`, or fold into `format`) that runs it in the container, source
   bind-mounted so fixes land on the host. `## `-document it for `make help`.
4. Apply the formatter once (commit the reformat), fix any lint findings, and confirm the gate is green
   and idempotent (`--check` clean on a second run).

## Gates / verify

- The three files pass the chosen formatter (`--check` clean) and linter (no findings) in-container.
- `make <target>` runs it and the image stays lean (no Node/npm pulled in unless explicitly chosen).

## Open questions

1. **Which tool** — Biome (single binary, no Node; recommended), Deno, or Prettier+ESLint (needs Node)?
   Recommend confirming Biome is Fedora-44-installable without npm, else Deno.
2. **Where it runs** — a new `make tauri-lint`, or folded into the existing `make format`? (The Rust
   ports aren't in `format` either, so a dedicated target may be cleaner.)

## Pointers

- `tasks/archive/2026/10/23/port-to-tauri.md` — the completed port; this is its deferred-optional item.
- runClaudeInContainer `tasks/reference/tauri-desktop-apps.md` — the frontend-without-a-bundler setup.
- The multi-step-check-script shape (`status=0; cmd || status=1; … exit $status`): runClaudeInContainer
  `tasks/reference/shell-and-gate-scripts.md`.
