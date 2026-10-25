# Tauri frontend JS: JSDoc-type every binding + a safe `make type-check` (apply the JS standard)

**Status:** proposed — needs go-ahead.
**Priority:** 5 **Difficulty:** 4
**Created:** 2026-10-25 (William Emerison Six <billsix@gmail.com>). Requested: once the JavaScript coding
standard was written for the sandboxes, apply it to hanoi's Tauri frontend JS.

## BLUF

Apply the new JavaScript standard (`~/.claude/reference/javascript-coding-standard.md`) to hanoi's only
JavaScript — the **Tauri frontend** (`rust/tauri/frontend/main.js`, the static no-bundler webview UI).
JSDoc-type **every binding** (params, returns, locals via `/** @type {} */`, `@typedef`s for the IPC
view-models), turn on **`// @ts-check`** + a **`jsconfig.json`** (`checkJs`, strict) scoping the frontend,
and add a safe **`make type-check`** that installs the dev tooling with **`npm ci --ignore-scripts`** and
runs **`tsc --noEmit`** + **`eslint`** (`eslint-plugin-jsdoc`). hanoi is the maintainer's repo, so this is
a **full sweep** of the frontend JS. "Done" = the frontend JS is fully JSDoc-typed, `make type-check` is
green (type + lint), and the devDeps are baked into the Tauri image so it runs offline. The `.js` ships
unchanged (no transpile; the webview loads it directly).

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

## Plan

1. **Dev tooling, safely:** add `rust/tauri/frontend/package.json` + committed `package-lock.json` pinning
   `typescript`, `eslint`, `eslint-plugin-jsdoc` (devDependencies); install at image-build with
   **`npm ci --ignore-scripts`** (baked → offline); add Node/npm to the image if absent.
2. **`jsconfig.json`** in `rust/tauri/frontend/` — `checkJs`, `strict`, `noImplicitAny`, `noEmit`,
   `include` the frontend `.js`; add `// @ts-check` atop `main.js` (belt-and-suspenders).
3. **ESLint flat config** (`eslint.config.js`): `jsdoc.configs['flat/recommended']` +
   `require-param-type` / `require-returns-type` / `check-types` / `no-undefined-types`.
4. **JSDoc-type every binding** in `main.js` (full sweep): `@param`/`@returns` on each function,
   `/** @type {} */` on opaque locals (DOM lookups, `invoke()` IPC results, empty arrays), `@typedef`s for
   the IPC view-models + Move/Recipe shapes; parameterize all element types.
5. **`make type-check`** (open question 1): `npm ci --ignore-scripts` (or baked deps) → `npx tsc --noEmit`
   + `npx eslint .`, both exit statuses accumulated, run in-container. Verify green.

## Open questions

1. **Where the target lives** — a `tauri`-scoped `make type-check` in `rust/Makefile`, or a small Makefile
   under `rust/tauri/`? (The Tauri crate is already separate from the Rust workspace.)
2. **Node in the image** — add Node/npm to the existing Tauri image build (recommended), or a separate
   tool image?

## Related

- The standard: `~/.claude/reference/javascript-coding-standard.md`; the overlay Makefile `type-check`
  contract. Tauri setup: `~/.claude/reference/tauri-desktop-apps.md`. Target: `rust/tauri/frontend/main.js`.
