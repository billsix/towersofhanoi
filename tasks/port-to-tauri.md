# Port hanoi to a Tauri desktop app (reusing the Rust core)

**Status:** proposed — needs go-ahead (the prerequisite is now met; ready to start on your word).
**Depends on:** the `hanoigame` Rust library crate from
`tasks/archive/2026/10/23/port-to-rust-wxdragon.md` — **now DONE** (the Rust core + the CLI/TUI/GUI
front-ends are built and the wxDragon GUI is play-verified). Tauri reuses that crate as its backend
engine, so this no longer waits on anything within our control.
**Priority:** 7 **Difficulty:** 7
**Created:** 2026-10-23 (William Emerison Six <billsix@gmail.com>). Requested as the follow-up to the
Rust/wxDragon port: port it to Tauri as well. The maintainer is new to both Rust and Tauri.

## BLUF

Add a **Tauri** desktop front-end for hanoi: a Rust backend that exposes the shared `hanoigame`
library crate (from the completed `tasks/archive/2026/10/23/port-to-rust-wxdragon.md`) to a web UI through Tauri commands, and a
small web frontend (HTML/CSS/TypeScript) that renders the board and drives play — behaviourally
faithful to the existing front-ends, preserving the label-space recipe transparency and the six peg
labellings. "Done" = the Tauri app runs in the container (or on host), plays the game through the
same shared core, matches the other front-ends' behaviour, and builds clean (`cargo fmt`/`clippy`
for the Rust side, the frontend's own lint/format for the web side). Do **not** reimplement the
engine — Tauri is a **fourth front-end over the same Rust core**, exactly as the CLI/TUI/GUI are.

## Context (read first)

- **This reuses, not rewrites, the core.** The whole point of doing the Rust/wxDragon port first is
  that the model/engine/commands/presenter/recipe/solvers live in the `hanoigame` library crate; the
  Tauri backend depends on that crate and wraps its operations as `#[tauri::command]`s. If this task
  is picked up before the Rust core exists, that core is the prerequisite — build it first (don't
  duplicate the logic in the Tauri backend).
- **Tauri = Rust backend + webview frontend.** Rust owns the game state and logic (the `hanoigame`
  crate); the UI is web tech rendered in the OS webview, talking to Rust over Tauri's IPC. The board
  rendering that was `wx.GraphicsContext` in Python / wxDragon in the GUI port becomes a web canvas
  or DOM drawing in the frontend. **Use Tauri v2** (verify the current major/version and the project
  scaffold on tauri.app at implementation time — the maintainer has never used Tauri, so prefer the
  official `create-tauri-app` scaffold and the documented project structure).
- **The maintainer is new to Rust and Tauri** — keep the backend idiomatic to the shared Rust
  standard (runClaudeInContainer `tasks/reference/rust-coding-standard.md`), keep the frontend small
  and readable, and comment the IPC boundary (what each command does, what it returns).
- **Preserve the teaching invariants** (`tasks/reference/architecture-overview.md`): recipes stored
  in the user's labels and replayed through the current labelling; the six peg labellings; the
  relabelling method. These live in the Rust core already — the Tauri layer just surfaces them.

## Plan (sketch — refine after the Rust core lands)

1. **Scaffold** a Tauri v2 app whose `src-tauri` backend depends on the `hanoigame` crate (path
   dependency within the workspace). Decide the frontend stack (plain TS + Vite is the simplest for a
   newcomer; a framework is optional — see open questions).
2. **Expose the core via commands** — new game (size / same / relabel), parse+dispatch a move,
   current board state, record/replay a recipe, list the labellings. Return serializable
   (`serde`) view-models the frontend renders; keep the commands thin over `engine::dispatch`.
3. **Frontend** — render the board (canvas or DOM), the control surface (move buttons / input), the
   relabel menu (normal items, matching the wx gotcha semantics), and recipe record/replay. Mirror
   the Python GUI's affordances.
4. **Container/build** — add the Tauri build prerequisites to the image (the webview runtime —
   `webkit2gtk` on Linux — plus Node/TS tooling for the frontend), behind a feature/flag, keeping
   `MINIMAL_IMAGE` able to drop it; a Makefile target to build/run the Tauri app; self-contained
   offline build (vendor cargo + the npm deps into committed layers; rebuild only hanoi's own source
   from the mount). This is the heaviest image addition — flag it when adding it.

## Gates / verify

- Rust side: `cargo fmt --check`, `cargo clippy -D warnings`, warning-clean build.
- Frontend: its own formatter/linter (e.g. Prettier/ESLint or Biome) clean; TypeScript type-check.
- Behaviour fidelity: same moves / recipe record+replay / board states as the other front-ends
  (the shared core guarantees most of this; verify the IPC view-models don't distort it).
- Display verification (the webview window) is the maintainer's, on host.

## Decisions / open questions

1. **Frontend stack:** plain TypeScript + Vite (simplest, recommended for a first Tauri app) vs a
   framework (Svelte/React/Vue). Recommend **plain TS + Vite**. Preference?
2. **Board rendering:** HTML `<canvas>` (closest to the `GraphicsContext` 2D board) vs DOM/CSS
   elements (simpler, accessible). Recommend **canvas for the graphics board, with a DOM text board**
   mirroring the Python's two-renderer design. OK?
3. **Scope of parity:** does the Tauri app need the *text/screen-reader* mode and the *recipe*
   features from day one, or is a first cut the graphical board + play + relabel, with recipes
   second? (The CLI already serves the pipe/screen-reader case.)
4. **Where it lives:** a `tauri/` (or `src-tauri/` + frontend) subtree inside the same Cargo
   workspace as the Rust port, so it shares the `hanoigame` crate directly. Confirm.

## Pointers

- `tasks/archive/2026/10/23/port-to-rust-wxdragon.md` — the (completed) prerequisite; its `hanoigame`
  library crate is this app's engine.
- `tasks/reference/architecture-overview.md` — the dispatch flow and the recipe/labelling invariants
  to preserve.
- Shared Rust coding standard: runClaudeInContainer `tasks/reference/rust-coding-standard.md`.
- Tauri — tauri.app (verify v2 scaffold/APIs at implementation time); `tauri`, `serde` crates.
