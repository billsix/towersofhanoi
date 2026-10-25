# hanoi — Rust subproject

The **Rust** implementation of hanoi (github.com/billsix/towersofhanoi): a Cargo workspace
that reimplements the Python canonical source (`../python`) **feature-for-feature**, kept in
sync, never a replacement (the Python stays the behaviour oracle). Self-contained: own
`Dockerfile`, `Makefile`, `entrypoint/`, and emacs set.

## Status

- `hanoigame/` — the shared library crate (model / commands / engine / presenter / recipe /
  solvers), mirroring the Python package module-for-module.
- Four front-ends over that crate:
  - `hanoi-cli/` — plain CLI (`make cli`)
  - `hanoi/` — ratatui/crossterm TUI (`make tui`)
  - `hanoi-gui/` — wxDragon GUI; programmatic UI, solid-fill DC board (`make wx`)
  - `tauri/` — Tauri v2 desktop app (static webview UI over the same crate; `make tauri`).
    Just another UI, like the wx one. NOT a workspace member (Tauri needs its own build);
    it depends on `../hanoigame` by path.

## Build / container workflow

Fedora-44 + podman template. Mounts at `/hanoi-rust`. The image installs the Rust toolchain
+ the full native build stack wxDragon needs (see `entrypoint/01-install-rust-base.sh`); the
crates are built at **runtime** (not image-build), cached in `.container-target` /
`.container-cargo` on the mount — because wxDragon downloads + builds wxWidgets 3.3.4 from
source at cargo-build time (needs network; the first `make wx` is minutes-long, then cached).

- `make image` — build; `MINIMAL_IMAGE=1` drops emacs. `USE_EMACS` (default 1) installs emacs
  + the Rust dev set.
- `make shell` / `make shell-exec` — dev shell (cargo caches preset).
- `make cli` / `make tui` / `make wx` / `make tauri` — run a front-end (X11 + Wayland
  passthrough; Tauri also sets `WEBKIT_DISABLE_DMABUF_RENDERER=1`).
- `make format` — rustfmt (workspace + the Tauri crate).
- `make check` — `cargo check --workspace --all-targets`: the compile gate. `--all-targets`
  is load-bearing — bare `cargo check` and `make format` both skip the test modules, so a
  test that stopped compiling slips through without it (caught one here 2026-10-25).
- `make type-check` — the **Tauri frontend JS** gate (`tauri/frontend/main.js`), via **Deno**:
  `deno check --check-js` (JSDoc + `checkJs`/strict from `tauri/frontend/deno.json`) + `deno lint`.
  Deno is a pinned binary baked by `entrypoint/02-install-deno.sh` — no `node_modules`, no npm. The
  JS house style + the Deno-first rationale: `~/.claude/reference/javascript-coding-standard.md`.
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
The wxDragon GUI build gotchas (libclang/bindgen, from-source wxWidgets, system image libs, X11
session libs) are documented in `entrypoint/01-install-rust-base.sh` and
`~/.claude/reference/rust-gui-tui-and-ecosystem.md`; Tauri specifics in
`~/.claude/reference/tauri-desktop-apps.md`.
