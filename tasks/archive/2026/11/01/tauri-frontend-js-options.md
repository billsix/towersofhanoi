# Investigate options for the Tauri frontend's JavaScript (TypeScript rewrite vs. alternatives)

**Status:** investigation COMPLETE 2026-11-01 (William Emerison Six <billsix@gmail.com>) — findings +
recommendation below. **The headline: the maintainer's goal (type-safety) is already met by the live
setup, so no rewrite is warranted.** The one genuine change worth making is a static *no-network* gate;
its follow-on is scaffolded (`tasks/archive/2026/11/02/tauri-frontend-no-network-static-gate.md`, proposed — needs
go-ahead). This doc is otherwise read-only history now.
**Priority:** 7 **Difficulty:** 4
**Depends on:** the lint task — DONE 2026-10-26, `tasks/archive/2026/10/26/tauri-frontend-lint.md`
(Deno fmt/lint/check wired into `make format` + `make type-check`; whatever this task recommends may
reshape that setup).
**Created:** 2026-10-23 (William Emerison Six <billsix@gmail.com>). Requested: "investigate what other
options there are to do with the JavaScript code; my first inclination is to rewrite the JavaScript in
TypeScript, but I want to hear if there are other options."

## BLUF

The Tauri front-end is plain vanilla JavaScript (`rust/tauri/frontend/main.js` + `index.html` +
`style.css`), with **no bundler and no Node toolchain** by deliberate choice. The maintainer's first
inclination is to **rewrite it in TypeScript** for type-safety; this task was to **survey and compare
the realistic options** — including TS, but also lighter and heavier alternatives — against this
project's constraints, and come back with a **recommendation**.

**Outcome (see "Findings & recommendation"):** the premise is now **stale**. When this task was written
(2026-10-23, `main.js` ~130 lines) the frontend had no type-checking; since then the lint task
(2026-10-26) and the learning-flow/drag-drop fan-out (2026-11-01) left it at **607 lines that are
already `// @ts-check`'d under strict Deno `checkJs`** (75 JSDoc annotations), with the board + disc
drag-drop already in **plain Canvas 2D + Pointer Events, no library**, and **no remote URL anywhere**.
That is exactly option 1's end state, reached incidentally. So the recommendation is **stay the course —
no rewrite, no framework** — plus one concrete gap worth closing (a static no-network gate).

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
6. **Reimplement/adapt only the piece you want from a framework, in vanilla JS under the upstream's
   licence** — the deliberate "don't take the dependency" path
   (<https://github.com/billsix/runClaudeInContainer/blob/master/tasks/reference/reimplementing-third-party-libraries.md>).
   Rather than *adopt* a framework (option 5)
   or hand-roll from nothing, study a framework/widget's source online, lift **only** the part this
   ~130-line UI needs, and ship it as **one tailored, trimmed, framework-free file** in the house
   vanilla-JSDoc style
   (<https://github.com/billsix/runClaudeInContainer/blob/master/tasks/reference/javascript-coding-standard.md> — Deno
   `check --check-js` strict, no `node_modules`). **Licence is an obligation, not a flourish:** if any
   upstream source is copied in, the file is a **derivative work** and MUST carry the upstream licence
   (real SPDX id, a vendored `LICENSE`, upstream links, changes stated); a genuine *clean-room*
   reimplementation written from behaviour/docs may be relicensed but should still match upstream as a
   courtesy — the `pgzero_gl` precedent in <https://github.com/billsix/modelviewprojection>. The fetched source is
   a **transient reference, never a dependency**: it never enters the image, lockfile, or runtime, so
   this preserves the no-Node / offline-rebuild / lean-image guarantees intact. Best when a *specific*
   framework has one widget worth borrowing; if the UI needs nothing a framework offers, this collapses
   back to option 1 (plain vanilla JS + JSDoc).

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

## Findings & recommendation (2026-11-01, William Emerison Six <billsix@gmail.com>)

The maintainer added a scope to this survey: *study the UI design docs + the wx XRC, research JS
libraries worth using or pulling from, with the hard constraint that **everything runs locally with no
network**, ideally **statically verifiable**.* This section is that write-up.

### Verified current state of the frontend (the premise was stale)

Read `rust/tauri/frontend/` on 2026-11-01:
- `main.js` is **607 lines**, headed `// @ts-check`; `frontend/deno.json` sets `compilerOptions`
  `checkJs: true`, `strict: true`, `noImplicitAny: true` (DOM libs). So the JS is **already
  type-checked strictly** — `make type-check` runs `deno check --check-js` + `deno lint` + `deno fmt
  --check`, no `node_modules`, and CI gates it (`rust-type-check`). **75 JSDoc annotations** present.
- The **board + disc drag-drop is already implemented in plain Canvas 2D + Pointer Events, no library**
  (`pegCenters` / nearest-peg hit-test, `dragSrc`/`dragSize`/`dragX`/`dragY`), per
  `ui-design-principles.md` ruling 7 (nearest-peg targeting, snap-back, off-when-solved, one shared
  dispatch).
- **No remote URL anywhere** in `frontend/` (grepped `https?://`, `src="//"` — none). Tauri embeds the
  static `frontend/` via `generate_context!`, so the webview already loads only local assets. The file
  is **GPL-2.0-or-later** (matters for option 6: adapting MIT/BSD source *into* it is fine and the
  permissive notice is retained for that portion; you cannot pull GPL-incompatible source in).

### The two constraints are independent — only one is about libraries

- **"Runs locally, no network" is NOT a library property — it is vendor-vs-CDN.** Any library is fine
  *if vendored* (its `dist` file committed in `frontend/`, referenced by a relative path) and fatal *if
  CDN-linked*. Vendoring a single file adds no build step and no Node, so it respects every binding
  constraint in Context. The rule: **vendor, never `<script src="https://…">`.**
- **"Verify statically" IS the library discriminator.** The gate is `deno check --check-js` strict. A
  library helps static checking only if it **ships TypeScript declarations** that resolve at your call
  sites. This rules *out* a whole class: **declarative-HTML libraries (Alpine.js, htmx) and
  HTML-template libraries (Lit)** put logic in attributes / string templates the checker cannot see —
  adopting one forfeits exactly the guarantee the maintainer wants.

### Per-option verdict

1. **Status quo + JSDoc, strict `checkJs`** — **this is already the live state** (`@ts-check` + strict
   Deno). Meets the type-safety goal at zero further cost. **← recommended (and already in place).**
2. **Rewrite in TypeScript** — would add a transpile/build step and a toolchain for no behavioural gain
   over (1); `.ts`→`.js` emit is the only thing it buys, and JSDoc already gives the same checker.
   **Not worth it** for a 607-line, type-checked, no-build frontend. (The maintainer's original
   inclination — tested against (1) as the brief required, and (1) wins.)
3. **TS via a single-binary toolchain (Deno/esbuild/Bun)** — only relevant if (2) were chosen; moot.
4. **Rust→WASM (Leptos/Dioxus/Yew)** — the heaviest option; rewrites the working canvas/DOM code, adds
   a WASM build + bundle. Justified only for "single-language purity," not type-safety. **Not
   recommended** unless the maintainer explicitly wants the whole UI in Rust.
5. **A minimal reactive framework (Svelte/Solid/lit)** — overkill for this UI; and lit's templates are
   not statically checkable (see above). **Ruled out.**
6. **Pull one piece from a framework under its licence** — the right escape hatch *if* a specific widget
   is ever wanted (see board note below); not needed today.

### The library research (what to use, or pull from)

The wx XRC layout maps cleanly to **plain structural HTML + CSS** (two-column split → grid/flex; the
3×2 Move grid → a button grid; recipe sidebar → `<ul>` + buttons; menu bar → buttons/`<menu>`; the
Recipe + 3-panel Rebinding dialogs and How-to-Play → `<dialog>`+`showModal`; goal line → a status
`<div>`). None of that needs a framework, and the app shell is best left vanilla (most teachable, most
checkable). Libraries researched (all MIT, all vendorable offline, all ship TS types — sources at end):

- **Board + disc drag-drop** — the only non-trivial interactive piece, and **it is already done the
  recommended way (vanilla Canvas 2D + Pointer Events, no dependency).** Keep it. If it ever became
  painful to maintain by hand:
  - **Konva.js** — canvas scene-graph, `draggable` + `dragBoundFunc` (ideal for snap-back/nearest-peg),
    written in TS (statically checkable). Cost: a few hundred KB minified — heavy and out of proportion
    here; a real dependency to vendor + licence-track.
  - **interact.js** — DOM drag with built-in snapping/inertia, one `dist/interact.min.js`; smaller, but
    only if discs become DOM elements (changes the canvas board).
  - Prefer **option 6** over adopting either: lift just the snapping/`dragBoundFunc` logic into one
    vanilla file under the upstream MIT licence.
- **Reactivity** — if ever wanted, **VanJS** (~1 KB, MIT, no build, TS types) is the only one worth a
  mention; a ~20-line `render(state)` is clearer here. Skip for now.
- **Avoid:** CDN `<script>` (breaks no-network); npm/bundler frameworks (React/Vue/Svelte/Solid — Node +
  build); Alpine/htmx/Lit (not statically checkable); desktop-look web-component kits (**Shoelace is
  MIT; Web Awesome v3's licence is unconfirmed** — flag — and either way a large component tree whose
  "native look" job Tauri's webview + your CSS already do).

### The one change worth making: a static no-network gate

The frontend currently has no remote references, but **nothing enforces that it stays that way.** The
maintainer's stated priority ("verify this statically") is best served by a cheap static gate that fails
if any remote resource creeps in. Scaffolded as the follow-on:
`tasks/archive/2026/11/02/tauri-frontend-no-network-static-gate.md`.

### Caveat for any *future* library adoption (verify in a spike first)

I confirmed Konva/interact.js/VanJS ship TS types + MIT, but did **not** confirm `deno check` resolves a
**UMD-global** library's types (e.g. `window.Konva`) without an ESM import — you may need a small local
`.d.ts` declaring the global, or the lib's ESM build. 10-minute spike before committing to any lib. (The
current no-library board sidesteps this entirely.)

### Sources (verified 2026-11-01)

- Konva.js — MIT, built-in TS types, `draggable`: <https://konvajs.org/docs/about.html>,
  <https://konvajs.org/docs/faq.html>
- VanJS — ~1 KB, MIT, no build, TS: <https://bestofjs.org/projects/vanjs>,
  <https://github.com/vanjs-org/van>
- interact.js — MIT, snapping, ships types, `dist/interact.min.js`:
  <https://bestofjs.org/projects/interactjs>, <https://npmjs.com/package/interactjs>
- Deno `check --check-js` (strict `checkJs`, local-only, offline on warm cache):
  <https://docs.deno.com/runtime/reference/cli/check/>,
  <https://docs.deno.com/runtime/manual/getting_started/typescript>
- Shoelace MIT / Web Awesome successor (v3 licence unconfirmed):
  <https://awesome.ecosyste.ms/projects/github.com%2Fshoelace-style%2Fshoelace>

## Open questions

1. **What is the actual goal** — type-safety (then option 1 or 3 may suffice), a nicer authoring
   experience, future UI growth headroom, or single-language purity (then option 4)? The recommendation
   hinges on this; recommend the maintainer name it, else the survey will weigh all axes.
   **Findings assume type-safety** (the stated inclination), and on that goal the answer is "already met
   — no change." **If the real goal is single-language purity**, option 4 (Rust→WASM) is the only one
   that delivers it, at the cost of rewriting the working frontend — say so and this re-opens as a
   much larger task. Otherwise this question is resolved.

## Pointers

- `tasks/archive/2026/10/26/tauri-frontend-lint.md` — the predecessor (lint, done 2026-10-26).
- `tasks/archive/2026/10/23/port-to-tauri.md` — the port; the no-bundler/no-Node decision lives here.
- runClaudeInContainer `tasks/reference/tauri-desktop-apps.md` — the Tauri frontend setup + constraints.
- Personal overlay "Self-contained images + live source" — the offline-rebuild constraint any build
  step must satisfy.
- <https://github.com/billsix/runClaudeInContainer/blob/master/tasks/reference/reimplementing-third-party-libraries.md>
  — option 6's method (clean-room-vs-derivative licence distinction, the `pgzero_gl` header/licence
  mechanics, fetch-to-learn is transient); its JS sibling
  <https://github.com/billsix/runClaudeInContainer/blob/master/tasks/reference/javascript-coding-standard.md>
  — the vanilla-JSDoc style (and the "write a vanilla JS widget instead of a dependency" cross-link that
  seeds this option).
