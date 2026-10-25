# Tauri frontend JS: JSDoc-type every binding + a safe `make type-check` (apply the JS standard)

**Status:** done — 2026-10-25 (William Emerison Six <billsix@gmail.com>).
**Priority:** 5 **Difficulty:** 4
**Created:** 2026-10-25 (William Emerison Six <billsix@gmail.com>). Requested once the JavaScript coding
standard was written for the sandboxes: apply it to hanoi's Tauri frontend JS.

## BLUF

Applied the JavaScript standard (`~/.claude/reference/javascript-coding-standard.md`) to hanoi's only
JavaScript — the **Tauri frontend** (`rust/tauri/frontend/main.js`, the static no-bundler webview UI).
Every binding is JSDoc-typed (params, returns, locals via `/** @type {} */`, and `@typedef`s for the IPC
view-models); a `deno.json` (`checkJs`, `strict`, DOM libs) + `// @ts-check` turn on checking; and a
`tauri`-scoped `make type-check` runs **`deno check --check-js` + `deno lint`**. The gate is **one pinned
Deno binary — no `node_modules`, no lockfile, npm lifecycle scripts off** (the supply-chain vector), the
maintainer's reputation call over npm/tsc/eslint. hanoi is the maintainer's repo, so this was a **full
sweep** of the frontend JS. The `.js` ships unchanged (no transpile; the webview loads it directly).

## Context

- **The standard** (`~/.claude/reference/javascript-coding-standard.md`) is Deno-first: JSDoc on every
  binding, the `checkJs`/strict type-gate, `deno check` + `deno lint`/`deno fmt` from one binary, with
  npm + `tsc` + `eslint-plugin-jsdoc` (`npm ci --ignore-scripts`) kept only as the fallback for an
  already-npm repo. The Makefile `type-check` contract (JS sibling): the personal overlay
  (`ai-coding-conventions.personal.md`).
- **The target** was `rust/tauri/frontend/main.js` — a no-bundler, `withGlobalTauri` static frontend
  (`~/.claude/reference/tauri-desktop-apps.md`), so type-checking is dev-only tooling: no build step, the
  webview keeps loading the raw `.js`. `main.js` is the only JavaScript in hanoi.
- **IPC view-models:** every `#[tauri::command]` return (`src-tauri/src/main.rs`) is the shape captured as
  a JSDoc `@typedef` on the JS side — the one-serde-view boundary.

## What was done (Deno, not npm)

1. **Deno baked into the image** — `rust/entrypoint/02-install-deno.sh` downloads a **pinned,
   checksum-verified** Deno (`DENO_VERSION=v2.9.8`, `deno-x86_64-unknown-linux-gnu.zip` + its
   `.sha256sum`) to `/usr/local/bin`; `rust/Dockerfile` added the `ARG DENO_VERSION` + a source-independent
   `RUN`. One binary, no `node_modules`, no lockfile, npm lifecycle scripts off by default.
2. **`rust/tauri/frontend/deno.json`** — `compilerOptions` `checkJs` + `strict` + `noImplicitAny`,
   `lib: ["dom","dom.iterable","esnext"]` (the webview, not Deno's own globals); `lint`/`fmt` scoped to
   `main.js`. `// @ts-check` atop `main.js`.
3. **JSDoc-typed every binding** in `main.js` — `@typedef`s for the four IPC view-models (`Snapshot` /
   `RecipeInfo` / `ApplyView` / `ApplyStep`, transcribed from the Rust `#[derive(Serialize)]` structs:
   serde snake_case fields, `Option<T>` → `T|null`), `@param`/`@returns` on every function, element types
   on the colour-tuple arrays, and a cast at each `invoke()` / `getElementById()` opaque source. `window`
   → `globalThis` (webview-equivalent) to satisfy `deno lint`'s `no-window` without suppressing the rule.
4. **`make type-check`** — a `tauri`-scoped target in `rust/Makefile` running
   `deno check --check-js --no-lock main.js` + `deno lint main.js`, statuses accumulated. `deno fmt` was
   left out of the gate so it would not reflow the hand-laid JSDoc casts; formatting was not part of "done."
5. **Verified** — `deno check` exit 0 + `deno lint` exit 0 against the real `main.js` with the pinned Deno
   2.9.8 (run directly in-session), and the maintainer then ran `make type-check` on the host, in-image:
   it passed.

## Decisions

1. **Gate = `rust/Makefile`, `tauri`-scoped** (not a new `rust/tauri/` Makefile): the Tauri app already
   uses the `rust/` image, so a second Makefile would be drift.
2. **Deno, not Node/npm** — the maintainer's reputation call. Deno is one pinned binary with zero package
   tree and lifecycle scripts off, so the npm supply-chain surface the standard warns about is simply
   absent. The one trade-off — `deno lint` lacks `eslint-plugin-jsdoc`'s "a tag must be present" nags — is
   covered by the house style + review; the enforcement that matters (strict `checkJs`, no implicit-`any`
   on an opaque binding) is fully in `deno check`. This decision was generalised into the shared JS
   standard (Deno-first, npm fallback).

## Related

- The standard (now Deno-first): `~/.claude/reference/javascript-coding-standard.md`; the overlay Makefile
  `type-check` contract. Tauri setup: `~/.claude/reference/tauri-desktop-apps.md`. Target:
  `rust/tauri/frontend/main.js`. When a future JS widget (e.g. a menubar) would otherwise pull a runtime
  dependency, write it vanilla instead per `~/.claude/reference/reimplementing-third-party-libraries.md`.
