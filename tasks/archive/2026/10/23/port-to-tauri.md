# Port hanoi to a Tauri desktop app (reusing the Rust core)

**Status:** done 2026-10-23 (William Emerison Six <billsix@gmail.com>) — the Tauri front-end is built,
runs, and was play-verified on the host; **archived** on the maintainer's say-so. The one remaining
item, a frontend lint/format (Biome/Prettier) for the three static web files, was deliberately left as
an **optional** judgment call (documented under "Remaining", not filed as its own task). Work committed
by the maintainer.
**Reuses:** the `hanoigame` Rust library crate from the completed
`tasks/archive/2026/10/23/port-to-rust-wxdragon.md` as its backend engine.
**Priority:** 7 **Difficulty:** 7
**Created:** 2026-10-23 (William Emerison Six <billsix@gmail.com>). Requested as the follow-up to the
Rust/wxDragon port: port it to Tauri as well. The maintainer was new to both Rust and Tauri.

## BLUF

A **fifth** hanoi front-end: a **Tauri v2** desktop app whose Rust backend reuses the shared
`hanoigame` library crate and whose UI is a static webview (HTML/CSS/vanilla JS) driven over Tauri's
IPC. It is behaviourally faithful to the other front-ends — same shared core, the six peg labellings,
and the label-space recipe transparency — with both a text board and a `<canvas>` graphics board. The
engine was **not** reimplemented: the Tauri layer is thin glue over `engine::dispatch`, exactly as the
CLI/TUI/wx front-ends are. Durable Tauri know-how from this work was harvested into
runClaudeInContainer `tasks/reference/tauri-desktop-apps.md` (see Pointers).

## What was built

A standalone **`tauri/` crate at the repo root** (deliberately NOT a member of the `rust/` workspace,
so the core's clean/offline 75-test build stays uncoupled from Tauri's heavy webview deps), with a
path-dep on `../rust/hanoigame`:

- **`src-tauri/`** — the Rust backend (`hanoi-tauri`), Tauri **v2** (2.12.x). A managed
  `Mutex<AppState>` holds the game + the cross-game recipe registry; each `#[tauri::command]` runs
  through a transient `GameSession` that borrows the registry (the GUI's `std::mem::replace`/`take`
  adaptation of the engine's `&mut`-registry design). Seven commands — `snapshot`, `new_game`,
  `do_move`, `relabel`, `save_recipe`, `apply_recipe`, `show_recipe` — each return **one `Snapshot`**
  view-model (text board + structured `towers: [Vec<u32>; 3]`, disc count, moves, min-moves, active
  labels, legal moves, won flag, the rebinding key, and the recipe list). `tauri.conf.json`
  (`frontendDist: ../frontend`, `withGlobalTauri`, `bundle.active: false`, valid PNG `bundle.icon`s) +
  `build.rs` (`tauri_build::build()`).
- **`frontend/`** — `index.html` + `main.js` + `style.css`, plain vanilla JS over
  `window.__TAURI__.core.invoke` (no bundler, no Node). All play/relabel/recipe affordances re-render
  from the returned `Snapshot`. A **`<canvas>` graphics board** (`drawBoard`) mirrors the wxDragon
  `draw_board_dc` 1:1 — same disc/label palettes, the `maxW/3→maxW` disc-width curve, base bar, pegs,
  size-coloured rounded discs, label-digit badges, and the physical 1-2-3 reference row when
  relabelled — with a **Text / Graphics toggle** (canvas is the default view, matching the wx GUI).
- **Container/build wiring** — a `make rust-tauri` target (`TAURI_SETUP`: own `CARGO_TARGET_DIR`,
  shared `CARGO_HOME` download cache, `WEBKIT_DISABLE_DMABUF_RENDERER=1`) under the existing
  X11/Wayland `PLAY_FLAGS`. The hanoi image's `entrypoint/04-install-rust.sh` gained
  **`webkit2gtk4.1-devel`** (`webkit2gtk-4.1.pc`) and **`libsoup3-devel`** (`libsoup-3.0.pc`) — the two
  WebKitGTK `-sys` deps the other Tauri crates resolve against, on top of the gtk3 headers
  `wxGTK-devel` already pulls in. `tauri/.gitignore` ignores `src-tauri/target/`, `src-tauri/gen/`, and
  `.container-target/`.

## Decisions (resolved 2026-10-23)

1. **Frontend stack:** plain HTML + vanilla JS, no bundler — `cargo run` embeds the static `frontend/`
   via `generate_context!`, and `withGlobalTauri` gives `window.__TAURI__.core.invoke`. (TS + Vite
   stays an option if the UI grows.)
2. **Board rendering:** text board first, then the `<canvas>` graphics board mirroring the wxDragon DC
   renderer — both shipped, toggle between them.
3. **Scope:** full parity from the first cut — play, relabel, and recipes (save/apply/show) plus the
   label→peg rebinding key, all driven by one `Snapshot`.
4. **Where it lives:** standalone `tauri/` crate at the repo root with a path-dep on
   `../rust/hanoigame`, NOT a `rust/` workspace member — for build isolation.

## Verify

- Backend `cargo check` + `cargo fmt --check` pass with the `Snapshot.towers` field; `main.js` parses
  clean. Package names verified to provide the exact `.pc` files on Fedora 44.
- **Play-verified on the host** by the maintainer (built via the rebuilt image, `make rust-tauri`).
- Not run: `cargo clippy` (not installed in the running sandbox — it is in the image/base-list gate)
  and a headless webview launch (avoided, to not leak WebKit processes; the visual check was the host
  play-test).

## Remaining (optional)

- A frontend lint/format for the web side (Biome or Prettier) — the one unmet item from the BLUF's
  original "done" bar, left as a judgment call since the UI is three small static files.

## Pointers

- `tasks/archive/2026/10/23/port-to-rust-wxdragon.md` — the (completed) prerequisite; its `hanoigame`
  library crate is this app's engine.
- runClaudeInContainer `tasks/reference/tauri-desktop-apps.md` — the harvested Tauri reference (project
  shape, IPC boundary, Fedora WebKitGTK build deps, gotchas, workspace isolation).
- `tasks/reference/architecture-overview.md` — the dispatch flow and the recipe/labelling invariants.
- Shared Rust coding standard: runClaudeInContainer `tasks/reference/rust-coding-standard.md`;
  practical ecosystem notes: `tasks/reference/rust-gui-tui-and-ecosystem.md`.
