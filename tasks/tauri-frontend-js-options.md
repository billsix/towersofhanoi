# Investigate options for the Tauri frontend's JavaScript (TypeScript rewrite vs. alternatives)

**Status:** proposed — needs go-ahead (an **investigation/survey**; read-only until a direction is
chosen). The deliverable is a recommendation, not code.
**Priority:** 7 **Difficulty:** 4
**Depends on:** the lint task — DONE 2026-10-26, `tasks/archive/2026/10/26/tauri-frontend-lint.md`
(Deno fmt/lint/check wired into `make format` + `make type-check`; whatever this task recommends may
reshape that setup).
**Created:** 2026-10-23 (William Emerison Six <billsix@gmail.com>). Requested: "investigate what other
options there are to do with the JavaScript code; my first inclination is to rewrite the JavaScript in
TypeScript, but I want to hear if there are other options."

## BLUF

The Tauri front-end is plain vanilla JavaScript (`rust/tauri/frontend/main.js` ~130 lines + `index.html` +
`style.css`), with **no bundler and no Node toolchain** by deliberate choice. The maintainer's first
inclination is to **rewrite it in TypeScript** for type-safety; this task is to **survey and compare
the realistic options** — including TS, but also lighter and heavier alternatives — against this
project's constraints, and come back with a **recommendation** (and, if it recommends a change,
scaffold the follow-on task). Do **not** change the frontend as part of this task — it is an
investigation; implementation waits on the maintainer picking a direction.

## Context (read first)

- **Current state:** vanilla ES modules-free JS loaded by `<script src="main.js">`, calling
  `window.__TAURI__.core.invoke` (the `withGlobalTauri` global — no `import`), plus a `<canvas>` board
  renderer. `tauri.conf.json` embeds the static `frontend/` via `generate_context!` at compile time —
  there is **no dev server and no build step** for the web side today.
- **The binding constraints any option must respect:**
  - **No Node/npm toolchain in the image** (`tasks/archive/2026/10/23/port-to-tauri.md` decision 1;
    runClaudeInContainer `tasks/reference/tauri-desktop-apps.md`). Anything needing a `node_modules`
    install at build time fights this.
  - **Self-contained-image + offline rebuild** (personal overlay "Self-contained images + live
    source"): a build step's deps must bake into a committed layer, not be fetched at build/run.
  - **Keep it small and readable for a newcomer** (the maintainer is new to Rust/Tauri) — the UI is
    tiny; a heavy framework would be out of proportion.
  - It must still produce static assets Tauri can embed (`frontendDist`), or change that story
    deliberately.

## Options to evaluate (seed list — the investigation should confirm, cost, and add to these)

1. **Status quo + JSDoc types, type-checked by `tsc --checkJs --noEmit`** — keep the JS, add JSDoc
   annotations, run the TypeScript *checker* over it with no emit and no bundler. Type-safety without a
   rewrite or a build step; the checker is one tool (could be Deno/Biome-adjacent). Cheapest path to
   the maintainer's actual goal (type-safety).
2. **Rewrite in TypeScript (the maintainer's inclination)** — real `.ts`, compiled to JS. Needs a
   compiler/bundler (tsc, esbuild, Vite, or a Rust-based bundler) → a build step and a toolchain. Weigh
   which toolchain fits the no-Node constraint (e.g. `esbuild`/`deno` single binaries vs. Vite's Node
   project), and how the emitted JS feeds `frontendDist`.
3. **TypeScript via a single-binary toolchain (Deno or Bun, or esbuild)** — get TS without a full
   Node/npm project: Deno (one binary, native TS) or esbuild (one binary) compiles TS→JS as a build
   step. A middle path between (1) and a Vite project.
4. **Rust → WASM frontend (Leptos / Dioxus / Yew / Sycamore)** — no JavaScript at all; the whole app,
   UI included, in Rust. Keeps one language and the type system end-to-end, but it is the heaviest
   option (a WASM build step, a bigger bundle, a rewrite of the canvas/DOM code) and changes the
   architecture. Note whether it even pairs well with Tauri's webview vs. being its own thing.
5. **A minimal reactive framework (Svelte/SolidJS compiled, or lit)** — likely overkill for a
   ~130-line UI; include only to rule out explicitly.

For each: the type-safety gain, the build-step/toolchain cost, whether it keeps the image lean + the
offline-rebuild guarantee, bundle size, and the newcomer-readability cost. **Verify claims** (does
Biome/Deno/esbuild ship for Fedora 44 as a single binary? does Tauri v2 document a recommended TS/WASM
setup?) rather than asserting from memory — the ecosystem moves.

## Deliverable

A short comparison (a `tasks/reference/` doc if it earns one, else written up in this task) with a
**recommendation**, and — per the convention for a survey whose deliverable recommends an action —
**scaffold the follow-on implementation task** (`proposed — needs go-ahead`, cross-linked) rather than
stranding the recommendation. Explicitly test the maintainer's TypeScript hypothesis against the
cheaper type-check-the-JS option (1), since that may meet the real goal at a fraction of the cost.

## Open questions

1. **What is the actual goal** — type-safety (then option 1 or 3 may suffice), a nicer authoring
   experience, future UI growth headroom, or single-language purity (then option 4)? The recommendation
   hinges on this; recommend the maintainer name it, else the survey will weigh all axes.

## Pointers

- `tasks/archive/2026/10/26/tauri-frontend-lint.md` — the predecessor (lint, done 2026-10-26).
- `tasks/archive/2026/10/23/port-to-tauri.md` — the port; the no-bundler/no-Node decision lives here.
- runClaudeInContainer `tasks/reference/tauri-desktop-apps.md` — the Tauri frontend setup + constraints.
- Personal overlay "Self-contained images + live source" — the offline-rebuild constraint any build
  step must satisfy.
