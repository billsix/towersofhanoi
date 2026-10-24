# hanoi — Python subproject

The **Python** implementation of hanoi (github.com/billsix/towersofhanoi) and the
**canonical source** the Rust and C++ ports mirror. Self-contained: own `Dockerfile`,
`Makefile`, `entrypoint/`, and emacs set — no dependency on the sibling language folders.
The Sphinx book (`../docs/`) and workbook (`../workbook/`) stay at the repo root.

## Status

- `src/hanoigame/` (setuptools package) — one shared model + command grammar + dispatcher
  with three thin front-ends over it:
  - `hanoi` / `hanoigame` — ncurses TUI (`make tui`)
  - `hanoi-cli` — plain stdin/stdout, readline completion (`make cli`)
  - `hanoi-gui` — wxPython (XRC UI; text or 2D-graphics board) (`make wx`)
- `tests/` — pytest suite. All front-ends route through `engine.dispatch` +
  `commands.parse` + `presenter.render`; keep them thin.

## Build / container workflow

Fedora-44 + podman template. Third-party deps are baked into the image at build time and
the package is rebuilt editable from the bind-mount at runtime (host edits propagate;
offline-rebuildable). Mounts at `/hanoi-python`.

- `make image` — build; full by default. `MINIMAL_IMAGE=1` drops emacs + X11 for a lean
  export image. `USE_X_WINDOWS` (default 1) installs the GTK/X11/Wayland libs the wxPython
  GUI needs — no OpenGL/mesa (the board is 2D wx/Cairo). `USE_EMACS` (default 1) installs
  emacs + the vendored Python dev set.
- `make shell` / `make shell-exec SCRIPT=… | CMD='…'` — dev shell (share one invocation).
- `make cli` / `make tui` / `make wx` — run a front-end (X11 + Wayland passthrough).
- `make format` (ruff) / `make type-check` (ty over src + tests) — the gates.
- `make image-export` / `make image-import FILE=…` — OCI tar save/load.
- `make update-emacs-packages` — refresh the vendored `entrypoint/dotfiles/.emacs.d/elpa`
  (needs network).

## Emacs

`entrypoint/dotfiles/.emacs.d/` — `init.el` hooks `python-mode` to **lsp-mode** +
**pyright** (lsp-pyright; pyright installed via npm in the image under `USE_EMACS`),
`company` completion, `preferences.el` for editor defaults. Installed into the image and
bind-mounted at runtime so `make shell` uses the committed packages. Package list:
`install-melpa-packages.el`. `init.el` **pins the lsp project root to `/hanoi-python`**
(this subproject's `REPO_MOUNT`) so pyright roots there without prompting — the
per-language root-pin convention in the repo-root `CLAUDE.md`.

## Conventions

Python, ruff (line-length 80, from `[tool.ruff] line-length` in `pyproject.toml` — the
single source of truth, so `format.sh` passes no flag). Fully typed + Google docstrings;
`make type-check` runs `ty` and must stay green. This package is the behaviour oracle for
the Rust/C++ ports — never remove it to satisfy a port.
