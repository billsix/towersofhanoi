# Tauri frontend JS: JSDoc-type every binding + a safe `make type-check` (apply the JS standard)

**Status:** done — staged; archive after the work commit.
**Priority:** 5 **Difficulty:** 4
**Created:** 2026-10-25 (William Emerison Six <billsix@gmail.com>). Requested: once the JavaScript coding
standard was written for the sandboxes, apply it to hanoi's Tauri frontend JS.
**Done:** 2026-10-25 (William Emerison Six <billsix@gmail.com>). Implemented with **Deno** as the gate
(not npm) — the maintainer's call, to drop the npm supply-chain surface to zero.

## BLUF

Apply the JavaScript standard (`~/.claude/reference/javascript-coding-standard.md`) to hanoi's only
JavaScript — the **Tauri frontend** (`rust/tauri/frontend/main.js`, the static no-bundler webview UI).
JSDoc-type **every binding** (params, returns, locals via `/** @type {} */`, `@typedef`s for the IPC
view-models), add a **`deno.json`** (`checkJs`, `strict`, DOM libs) + **`// @ts-check`**, and a safe
**`make type-check`** that runs **`deno check --check-js` + `deno lint`** — **one pinned Deno binary, no
`node_modules`, no lockfile, npm lifecycle scripts off** (the supply-chain vector). hanoi is the
maintainer's repo, so this was a **full sweep** of the frontend JS. "Done" = the frontend JS is fully
JSDoc-typed and `deno check` + `deno lint` are green (verified locally with the pinned Deno 2.9.8; the
in-container `make type-check` is the maintainer's host/rebuild confirmation). The `.js` ships unchanged
(no transpile; the webview loads it directly).

## Context (read first)

- **The standard:** `~/.claude/reference/javascript-coding-standard.md` — JSDoc on every binding, the
  `@ts-check`/`jsconfig.json` `checkJs` gate, `eslint-plugin-jsdoc`, the `npm ci --ignore-scripts` +
  `tsc --noEmit` type-check. The Makefile `type-check` contract (now covering JS too): the personal
  overlay (`ai-coding-conventions.personal.md`).
- **The target:** `rust/tauri/frontend/` — `main.js` (UI logic, incl. the `apply_recipe` three-panel view
  added in the Rust parity work), `index.html`, `style.css`. It's a **no-bundler, `withGlobalTauri` static
  frontend** (`~/.claude/reference/tauri-desktop-apps.md`), so type-checking is **dev-only tooling** — no
  build step is added; the frontend keeps loading the raw `.js`.
- **IPC view-models:** the `#[tauri::command]` returns (e.g. `apply_recipe`'s view-model) are the shapes
  to capture as JSDoc `@typedef`s on the JS side (the one-serde-view boundary).

## What was done (Deno, not npm)

1. **Deno baked into the image** — `rust/entrypoint/02-install-deno.sh` downloads a **pinned,
   checksum-verified** Deno (`DENO_VERSION=v2.9.8`, `deno-x86_64-unknown-linux-gnu.zip` + its
   `.sha256sum`) to `/usr/local/bin`; `rust/Dockerfile` adds the `ARG DENO_VERSION` + a source-independent
   `RUN`. One binary, no `node_modules`, no lockfile, npm lifecycle scripts off by default.
2. **`rust/tauri/frontend/deno.json`** — `compilerOptions` `checkJs` + `strict` + `noImplicitAny`,
   `lib: ["dom","dom.iterable","esnext"]` (webview, not Deno globals); `lint`/`fmt` scope `main.js`.
   `// @ts-check` atop `main.js`.
3. **JSDoc-typed every binding** in `main.js` (full sweep): `@typedef`s for the four IPC view-models
   (`Snapshot` / `RecipeInfo` / `ApplyView` / `ApplyStep`, transcribed from the Rust `#[derive(Serialize)]`
   structs — snake_case fields, `Option<T>` → `T|null`), `@param`/`@returns` on every function, element
   types on the colour-tuple arrays, and a cast at each `invoke()` / `getElementById()` opaque source.
   `window` → `globalThis` (webview-equivalent; satisfies `deno lint`'s `no-window`).
4. **`make type-check`** (Q1): a `tauri`-scoped target in `rust/Makefile` running
   `deno check --check-js --no-lock main.js` + `deno lint main.js`, statuses accumulated. (`deno fmt` left
   out of the gate so it doesn't reflow the hand-laid JSDoc casts; formatting isn't part of "done" here.)
5. **Verified:** `deno check` exit 0 + `deno lint` exit 0 against the real `main.js` with the pinned Deno
   2.9.8 (run directly; the in-container `make type-check` is the same invocation — maintainer confirms on
   a host rebuild).

## Open questions — resolved

1. **Where the target lives** → `rust/Makefile`, `tauri`-scoped. No second Makefile: the Tauri app uses
   the `rust/` image already, so a `rust/tauri/` Makefile would be drift.
2. **Node in the image** → neither Node nor npm. **Deno** instead (the maintainer's reputation call): one
   pinned binary, zero package tree, lifecycle scripts off — the npm supply-chain surface the standard
   warns about is simply absent.

## Related

- The standard: `~/.claude/reference/javascript-coding-standard.md`; the overlay Makefile `type-check`
  contract. Tauri setup: `~/.claude/reference/tauri-desktop-apps.md`. Target: `rust/tauri/frontend/main.js`.
