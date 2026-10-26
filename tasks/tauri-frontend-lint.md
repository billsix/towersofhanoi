# Lint/format the Tauri frontend web files

**Status:** DONE 2026-10-26 (William Emerison Six <billsix@gmail.com>). Gate green in-container.
**Priority:** 5 **Difficulty:** 2
**Created:** 2026-10-23. Requested as the deferred-optional item from the completed Tauri port
(`tasks/archive/2026/10/23/port-to-tauri.md`): wire a lint/format for the web side.
**Next:** `tasks/tauri-frontend-js-options.md` (investigate the JS code's future).

## BLUF

The Tauri front-end's three static web files — `rust/tauri/frontend/{index.html,main.js,style.css}` —
now pass a formatter + linter, wired into the project's gate the way `cargo fmt`/`clippy` holds the
Rust side. **Deno** (already baked into the rust image for the JS type-check) does it — one binary, no
Node, honouring the port's no-Node-toolchain decision. `deno fmt` was folded into `make format`
(writes) and `deno fmt --check` into `make type-check` (verifies), with no new target.

## What was done (2026-10-26)

- **`rust/tauri/frontend/deno.json`** — `fmt.include` extended from `["main.js"]` to all three files
  (`index.html`, `main.js`, `style.css`). `lint.include` stays `["main.js"]` — `deno lint` is JS/TS
  only; `deno fmt` is what covers HTML + CSS. Note string updated.
- **`rust/entrypoint/format.sh`** — after `cargo fmt`, `make format` now also runs
  `( cd tauri/frontend && deno fmt )`, guarded on `command -v deno` so the portable host caller (no
  deno) still works; the container always has it.
- **`rust/Makefile` `type-check`** — the gate now runs `deno fmt --check` in addition to the existing
  `deno check --check-js main.js` + `deno lint main.js`, so the three files must stay formatted.
- **`rust/tauri/frontend/main.js`** — applied `deno fmt` once (it had never been run through fmt; the
  gate only had check + lint). 185-line reflow of the long `addEventListener` chains; no behaviour
  change. `index.html`/`style.css` were already deno-fmt-clean.

## Decisions (resolved the Open questions)

1. **Which tool → Deno.** The task recommended evaluating Biome first, but Deno was *already installed*
   (`entrypoint/02-install-deno.sh`) and wired for the JS type-check, and it formats HTML/CSS/JS from
   one baked binary with no Node — it already satisfies the no-Node-toolchain constraint, so adding
   Biome would have been redundant. Chose Deno.
2. **Where it runs → folded into the existing `format` + `type-check` targets, no new `tauri-lint`
   target.** `deno fmt` (writing) belongs with the other formatters in `make format`; `deno fmt
   --check` (read-only) belongs with the other gates in `make type-check`. This is "the same place
   `format` lives" that the task preferred, and avoids a one-off target.

## Gate / verify (passed)

In-container (`localhost/hanoi-rust`), from `tauri/frontend`:
`deno check --check-js --no-lock main.js` → OK; `deno lint main.js` → OK; `deno fmt --check` →
clean across 3 files. `make format` re-run is idempotent (second `--check` clean).

## Pointers

- `tasks/archive/2026/10/23/port-to-tauri.md` — the completed port; this was its deferred-optional item.
- The JS house style + Deno-first rationale: `~/.claude/reference/javascript-coding-standard.md`
  (shared, from runClaudeInContainer). The rust gate wiring is summarized in `rust/CLAUDE.md`.
- The multi-step-check-script shape (`status=0; cmd || status=1; … exit $status`):
  `~/.claude/reference/shell-and-gate-scripts.md`.
