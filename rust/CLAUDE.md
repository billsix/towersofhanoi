# hanoi — Rust subproject

The **Rust** implementation of hanoi (github.com/billsix/towersofhanoi): a Cargo workspace
that reimplements the Python canonical source (`../python`) **feature-for-feature**, kept in
sync, never a replacement (the Python stays the behaviour oracle). Self-contained: own
`Dockerfile`, `Makefile`, `entrypoint/`, and emacs set.

## Status

- `hanoigame/` — the shared library crate (model / commands / engine / presenter / recipe /
  solvers), mirroring the Python package module-for-module.
- Five front-ends over that crate:
  - `hanoi-cli/` — plain CLI (`make cli`)
  - `hanoi/` — ratatui/crossterm TUI (`make tui`)
  - `hanoi-gui/` — wxDragon GUI; loads the shared `ui/hanoi.xrc` (menu bar + panel +
    move/recipe controls) via `XmlResource` (wxdragon `xrc` feature), with a solid-fill DC
    board drawn into the XRC `board_slot` (`make wx`). `hanoi.xrc` is a git-tracked symlink to
    `../../ui/hanoi.xrc`, baked into the binary by `include_str!`; the Makefile mounts `ui/` at
    `/ui` so it resolves in-container.
  - `tauri/` — Tauri v2 desktop app (static webview UI over the same crate; `make tauri`).
    Just another UI, like the wx one. NOT a workspace member (Tauri needs its own build);
    it depends on `../hanoigame` by path.
  - `hanoi-egui/` — egui/eframe GUI, **native and web (WebAssembly)** from one crate
    (`make egui` native; `make egui-web` → gitignored `dist/`; `make egui-serve` at
    `:8080`). Its own workspace (like Tauri); egui/eframe pinned (glow renderer). The web
    build uses the baked wasm toolchain (`USE_WASM`: wasm32 std + trunk — `make egui-web`
    needs a `USE_WASM` image). The board is painted with egui's `Painter`.

## Build / container workflow

Fedora-44 + podman template. Mounts at `/hanoi-rust`. The image installs the Rust toolchain
+ the full native build stack wxDragon needs (see `entrypoint/01-install-rust-base.sh`); the
crates are built at **runtime** (not image-build), cached in `.container-target` /
`.container-cargo` on the mount — because wxDragon downloads + builds wxWidgets 3.3.4 from
source at cargo-build time (needs network; the first `make wx` is minutes-long, then cached).

- `make image` — build; `MINIMAL_IMAGE=1` drops emacs + the wasm toolchain. `USE_EMACS`
  (default 1) installs emacs + the Rust dev set; `USE_WASM` (default 1) bakes the wasm32
  Rust std + trunk (Fedora rpms) for the egui web build — `make egui-web`/`egui-serve`
  need a `USE_WASM` image.
- `make shell` / `make shell-exec` — dev shell (cargo caches preset).
- `make cli` / `make tui` / `make wx` / `make tauri` / `make egui` — run a front-end (X11 +
  Wayland passthrough; Tauri also sets `WEBKIT_DISABLE_DMABUF_RENDERER=1`).
- `make egui-web` — build the egui WebAssembly app with trunk (→ gitignored `dist/`);
  `make egui-serve` — serve it at `http://localhost:8080`. The wasm-bindgen CLI trunk needs
  is **baked** into the image under `USE_WASM` (pinned to `hanoi-egui/Cargo.lock`, pre-placed
  in trunk's cache so fresh `--rm` containers don't re-download it); the egui crate deps
  cache on `.container-cargo` like the other Rust crates.
- `make format` — rustfmt (workspace + the Tauri crate), plus `deno fmt` over the Tauri frontend's
  three static web files (`tauri/frontend/{index.html,main.js,style.css}`, scoped by
  `tauri/frontend/deno.json`'s `fmt.include`).
- `make check` — `cargo check --workspace --all-targets`: the compile gate. `--all-targets`
  is load-bearing — bare `cargo check` and `make format` both skip the test modules, so a
  test that stopped compiling slips through without it (caught one here 2026-10-25).
- `make test` — `cargo test --workspace`: the run gate. Runs the unit tests and the
  `hanoigame` crate's **doctests** (`cargo test --doc`, which `check` compiles but never runs).
  Standalone, like `check`/`type-check` — nothing interactive depends on it.
- `make type-check` — the **Tauri frontend web** gate, via **Deno**: `deno check --check-js`
  (JSDoc + `checkJs`/strict from `tauri/frontend/deno.json`) + `deno lint` (JS only) + `deno fmt
  --check` (all three files). Deno is a pinned binary baked by `entrypoint/02-install-deno.sh` —
  no `node_modules`, no npm. The JS house style + the Deno-first rationale:
  `~/.claude/reference/javascript-coding-standard.md`.
- `make image-export` / `make image-import FILE=…`, `make update-emacs-packages`.

## Emacs

`entrypoint/dotfiles/.emacs.d/` — `init.el` hooks `rust-mode` to **lsp-mode** +
**rust-analyzer** (installed via dnf, on PATH), `company` completion. Installed into the image
and bind-mounted at runtime. Package list: `install-melpa-packages.el`. `init.el` **pins the
lsp project root to `/hanoi-rust`** (this subproject's `REPO_MOUNT`) so rust-analyzer roots at
the Cargo workspace without prompting — the per-language root-pin convention in the repo-root
`CLAUDE.md`.

## Conventions

Keep each front-end thin — logic lives in the `hanoigame` crate, mirroring the Python layering.
**Type annotations — annotate every binding** (house style, over Rust's inference): every `let`
carries an explicit `let x: T =`, preferring the annotation to a turbofish; pattern bindings stay
inferred. This is a deliberate deviation from idiomatic Rust, mirroring the Python
annotate-every-binding rule; there is no checker, it is review discipline. The full rule and its
rationale: `runClaudeInContainer tasks/reference/rust-coding-standard.md` ("Type annotations").
**Tests are doctests by default** — a test documenting an item's API is a ` ```rust ` example in
its doc comment (run by `make test`), with typed bindings like the code; loop / property /
multi-step tests stay `#[test]`. See `~/.claude/reference/doctests-by-default.md`.
The wxDragon GUI build gotchas (libclang/bindgen, from-source wxWidgets, system image libs, X11
session libs) are documented in `entrypoint/01-install-rust-base.sh` and
`~/.claude/reference/rust-gui-tui-and-ecosystem.md`; Tauri specifics in
`~/.claude/reference/tauri-desktop-apps.md`.
