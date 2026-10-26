# Rust egui front-end for hanoi — native standalone AND web-delivered

**Status:** IMPLEMENTED 2026-10-26 (William Emerison Six <billsix@gmail.com>) — native **confirmed
working on-display by the maintainer**; web build **compiles to wasm + produces a `dist/`** (browser
render is the maintainer's check after `make image` rebuilds with the `USE_WASM` toolchain).
**Priority:** 7 **Difficulty:** 5

## What was done (2026-10-26)

- **`rust/hanoi-egui/`** — a new eframe/egui crate over the shared `hanoigame` engine, its **own
  workspace** (like Tauri), egui/eframe pinned `=0.29.1` (glow renderer). One `HanoiApp: eframe::App`
  renders the board (egui `Painter`, solid fills), move/relabel buttons, a recipe list + Save/Apply/
  Show, and a status line; native and web share it (`cfg(target_arch = "wasm32")` entry).
- **Native** — `make egui` (`cargo run`, X11/Wayland passthrough). Maintainer confirmed it runs.
- **Web** — `cfg(wasm32)` entry starts `eframe::WebRunner` on the `#hanoi_canvas`; `index.html` +
  `Trunk.toml` drive trunk. `make egui-web` (→ gitignored `dist/`) + `make egui-serve` (`:8080`).
- **Toolchain baked** — `entrypoint/03-install-wasm.sh` (`dnf`: wasm32 std + trunk) under a `USE_WASM`
  build-arg (Makefile default 1; `MINIMAL_IMAGE` drops it), like the other image deps.
- **Verified** — `cargo check`/`fmt --check` clean (native); `trunk build` compiles the crate to wasm
  and emits `dist/` (the `.wasm` + `.js`), so the web entry is correct, not just native.

## Decisions (resolved the Open questions)

1. **Native renderer → glow** (OpenGL; the recommended option — lighter, WebGL on web). The image's
   libGL/libEGL (from the wxGTK stack) satisfy it.
2. **Web toolchain → baked behind `USE_WASM`** (wasm32 std + trunk, both Fedora rpms — no `cargo
   install`, offline after). Mirrors the C++ `USE_WASM` idea.
3. **Publishable web build → local for now** (gitignored `dist/` + `make egui-serve`); GitHub Pages
   deferred (same call as the C++ web build).
4. **Relationship to the other Rust GUIs → keep all** (parallel teaching demos of the one engine).

## Residual / follow-up

- trunk fetches its matching **wasm-bindgen** CLI on first `egui-web` (then caches) — the one runtime
  download; bake it too if a fully-offline web build is wanted.
- The egui layout/visual is first-cut; on-display polish (sizing, board proportions) may follow, like
  the wx GUI got.
**Created:** 2026-10-24 (William Emerison Six <billsix@gmail.com>). Requested as a follow-up to the C++
ImGui/WebAssembly task: "make one for rust to use egui, both as standalone and as web delivered."

## BLUF

Add an **egui** front-end to the hanoi Rust subproject — another UI over the shared `hanoigame` crate
(like the wxDragon `hanoi-gui` and the Tauri app) — that builds **both** as a native desktop binary and
as a **browser (WebAssembly)** app, from one codebase. This is the Rust parallel to the C++
ImGui-native+wasm port (`tasks/port-to-cpp-imgui-native-and-wasm.md`): both are immediate-mode GUIs
delivered native + web. The key difference: egui/eframe is **pure Rust** — native via `eframe` (winit +
glow/wgpu), web via the `wasm32-unknown-unknown` target + `trunk`, with **no Emscripten/SDL/OpenGL
system stack** (it stays inside cargo). "Done" = `cd rust && make egui` runs the native app and `make
egui-web` produces a servable web build, both reusing the `hanoigame` engine, with the board rendered
by egui and the move/relabel/recipe interactions wired.

## Context (read first)

- **Where it lives:** the `rust/` subproject (`tasks/reference/per-language-subproject-layout.md`). It's
  a new front-end over the existing `hanoigame` library crate — do **not** reimplement game logic; reuse
  the crate exactly as `hanoi-cli`/`hanoi`/`hanoi-gui` do. The Python package stays the behaviour oracle;
  this must not drift from it.
- **egui / eframe (web research, 2026-10-24):**
  - egui is an immediate-mode GUI in pure Rust; an app is an `impl eframe::App` with an
    `update(&mut self, ctx, frame)` method called each frame.
  - **eframe runs the SAME app native and on web.** Native: `eframe::run_native(...)` gated on
    `cfg(not(target_arch = "wasm32"))`. Web: `eframe::WebRunner` started on a `<canvas>`, gated on
    `cfg(target_arch = "wasm32")`.
  - **Native build:** `cargo run --release` (eframe pulls winit + a renderer — glow/OpenGL by default,
    or wgpu). Runs under the subproject's existing X11/Wayland passthrough.
  - **Web build (toolchain additions):** `rustup target add wasm32-unknown-unknown` + `cargo install
    --locked trunk`; then `trunk serve` (dev, :8080) or `trunk build --release` → a static `dist/`
    (index.html + .wasm + .js). A `Trunk.toml` + an `index.html` with the canvas drive it.
  - Reference: the official **`github.com/emilk/eframe_template`** builds both targets from one crate
    (cfg-gated) and ships a GitHub Pages deploy workflow; `github.com/emilk/egui` is upstream.
  - **egui releases frequently with breaking changes** (0.36-era at research time) — **pin egui +
    eframe** and check their changelogs rather than copying old examples.
- **Contrast with the C++ ImGui port** (`tasks/port-to-cpp-imgui-native-and-wasm.md` +
  `tasks/reference/imgui-cpp-native-and-wasm.md`): same dual native/web, immediate-mode idea, but C++
  needs emsdk + SDL2 + OpenGL/WebGL; egui needs only the `wasm32` target + trunk. So the toolchain story
  is much lighter here — no new system packages, just a rustup target + the trunk binary.

## Plan (sketch — refine after open questions)

1. **Add the crate** (e.g. `rust/hanoi-egui/`) depending on `hanoigame` + `eframe`/`egui` (pinned). Not
   necessarily a workspace member if the web build wants its own profile — decide like the Tauri crate.
2. **One `App`** implementing the board + towers + legal moves + relabelling table + recipe
   record/replay, drawing the board with egui's painter (or widgets). Gate the native vs web entry
   points with `cfg(target_arch = "wasm32")`.
3. **Native:** a `make egui` target (`cargo run -p hanoi-egui`, under X11/Wayland passthrough, cargo
   caches on the mount).
4. **Web:** add `wasm32-unknown-unknown` + `trunk` to the rust image (gated so a lean image can skip
   them, like the C++ `USE_WASM` idiom); a `make egui-web` target (`trunk build --release` → a gitignored
   `dist/`) + a `make egui-serve` (`trunk serve`). An `index.html` + `Trunk.toml`.
5. **Parity:** reuse the engine; feed the same command/recipe sequences as the oracle where testable.
6. **Verify nested:** `make egui` builds + runs (maintainer confirms on the host); `make egui-web`
   produces a servable `dist/` that loads in a browser.

## Open questions

1. **Native renderer:** eframe defaults to **glow (OpenGL)**; **wgpu** is the alternative (Vulkan/Metal/
   WebGPU). Recommend glow (simpler, lighter, matches the "2D board" need; WebGL on web). Switch to wgpu
   only if WebGPU is wanted. OK with glow?
2. **Web toolchain in the image:** add `wasm32-unknown-unknown` + `trunk` to the rust image behind a flag
   (so a lean image skips them)? Recommend yes (mirrors the C++ `USE_WASM` gating). The trunk binary is a
   `cargo install` (build-time, baked).
3. **Publishable web build?** Just a local `make egui-serve`/gitignored `dist/` for now, or also a
   committed/publishable build (e.g. GitHub Pages, like the eframe_template)? Recommend: local now;
   revisit Pages later (same call as the C++ web build).
4. **Relationship to the other Rust GUIs:** this is a 4th/5th Rust UI (alongside wx + tauri). Keep all of
   them, or is egui meant to eventually replace one? Recommend: keep all — they're parallel teaching
   demos of the same engine.

## Related

- Sibling (the C++ analog): `tasks/port-to-cpp-imgui-native-and-wasm.md` +
  `tasks/reference/imgui-cpp-native-and-wasm.md`.
- `tasks/reference/per-language-subproject-layout.md` (the subproject model) and
  runClaudeInContainer `tasks/reference/rust-gui-tui-and-ecosystem.md`.
- Upstream: github.com/emilk/egui, github.com/emilk/eframe_template.
