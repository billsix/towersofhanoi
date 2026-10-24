# hanoi — the per-language subproject layout (a reusable template)

**Reference document** — what the repo's build/container structure IS, and the recipe for adding a
new language. Not a task; update in place. Created 2026-10-24 (William Emerison Six
<billsix@gmail.com>), harvested from `tasks/split-into-per-language-containers.md`. hanoi is meant to
serve as a **reusable basis for other multi-language projects**, so this doc states the template
precisely enough to copy.

## The shape

Each language is a **self-contained subproject** — its own image, driver, and dev tooling — and the
repo root is the book + umbrella:

- **`python/`** — the **canonical** implementation (the behaviour oracle). Mounts at `/hanoi-python`.
- **`rust/`** — a Cargo workspace mirroring Python feature-for-feature, **including `rust/tauri/`** (the
  Tauri desktop app — just another UI, not a workspace member). Mounts at `/hanoi-rust`.
- **the root** — the Sphinx book (`docs/`), worksheets (`workbook/`), bash demos (`bash/`), the
  by-hand generator (`tools/`), and a thin **umbrella** Makefile (`make docs`; `format`/`type-check`
  delegate to `python/`). Mounts the whole repo at `/hanoi`.

A new language (e.g. a future `cpp/`) is added as a sibling subproject in exactly this shape.

## Per-subproject contract (Fedora-44 + podman family template)

- **`Dockerfile`** — `FROM registry.fedoraproject.org/fedora:44`; `ARG` feature flags default **0** (a
  bare `podman build` is lean); package installs factored into host-runnable `entrypoint/0N-install-*.sh`
  group scripts dispatched by `ARG` `if` blocks; the dnf cache mount + `keepcache` stay in the
  Dockerfile. Third-party deps are installed into **committed layers** (offline-rebuildable); the
  subproject's **own source is COPY'd late** at the mount path and (re)built from the **bind-mount at
  runtime**, so host edits propagate.
- **`Makefile`** — `CONTAINER_NAME = hanoi-<lang>`, `REPO_MOUNT = /$(CONTAINER_NAME)`, feature flags
  default **1** (mirror of the Dockerfile's 0), optional-feature flags a lean image drops use the
  `MINIMAL_IMAGE` idiom (`?= $(if $(filter 1,$(MINIMAL_IMAGE)),0,1)`), and `PODMAN_RUN_FLAGS`
  (`?= $(if $(filter 1,$(NESTED_PODMAN)),--cgroups=disabled)`) is threaded into every `run` line, never
  `build`. Targets: `help` (default), `image`, `shell` + `shell-exec` (sharing **one** `SHELL_RUN_FLAGS`
  so they can't drift), `format`, the run targets (`cli`/`tui`/`wx`/…), `image-export`/`image-import`,
  and `update-emacs-packages`. Python subprojects also get `type-check` (`ty`).
- **`entrypoint/`** — `shell.sh` (`set -e` setup, then `exec bash "$@"` — the `"$@"` is what powers
  `shell-exec`), `entrypoint.sh` (the default gate: tests), `format.sh`, the `0N-install-*.sh` group
  scripts, `.bashrc`, and `dotfiles/.emacs.d/` (see Emacs below). **`.bashrc` is bind-mounted** by
  `make shell` so prompt/alias edits are live without a rebuild; it carries a real prompt, `alias
  ls='ls --color=auto'`, and the exit-runs-`/format.sh` hook. Committed scripts stay `+x` (a `Write`
  rewrite drops the bit — restore with `git add --chmod=+x`).

## Emacs + LSP recipe — do ALL of this for every language

Each subproject vendors its own `entrypoint/dotfiles/.emacs.d/` (`init.el`, `preferences.el`,
`install-melpa-packages.el`, and a vendored `elpa/` tree). The image installs emacs + the MELPA
packages at build (`USE_EMACS=1`, the Makefile default) and **bakes `init.el`+`preferences.el`** (COPY'd
after the dnf/MELPA layer so editing them doesn't bust the package cache); `make shell` bind-mounts the
live `.emacs.d` over the baked one (`ELPA_MOUNT`, `:U,z`) so a pulled image works standalone **and**
edits stay live. Refresh the vendored packages with `make update-emacs-packages` (network).

`init.el` must do three things, or the LSP experience is broken:

1. **Pin the LSP project root to `REPO_MOUNT`** — the subproject always mounts at a fixed path, so pin
   it rather than letting lsp prompt "Import project root?" or guess:
   ```elisp
   (setq lsp-auto-guess-root nil)
   (defun hanoi-<lang>-lsp-root (&rest _) "/hanoi-<lang>")
   (advice-add 'lsp--calculate-root :override #'hanoi-<lang>-lsp-root)
   ```
   The pinned path must equal `REPO_MOUNT` (where the project markers — `pyproject.toml`, `Cargo.toml`,
   … — live), so the server treats the real project as the root.
2. **Ignore the build + cache dirs under the mount** — the cargo `target`/`.container-*`, Python
   `__pycache__`/`.ruff_cache`/`.pytest_cache`, and the vendored `elpa`/`eln-cache` are tens of
   thousands of files; without this lsp prompts "watch N files?" on startup and then churns watching
   artifacts. Append them to `lsp-file-watch-ignored-directories` (the language server watches the real
   source itself).
3. **Enable yasnippet** (`(use-package yasnippet :config (yas-global-mode 1))`) — lsp only expands
   completion snippets (the `${1:arg}$0` tab-stops the server returns) into interactive placeholders
   when yasnippet is active; without it the raw template text is inserted. yasnippet ships in each
   `install-melpa-packages.el`.

The language server itself: Python → `lsp-pyright` (pyright via npm, installed under `USE_EMACS`);
Rust → `rust-mode` + `lsp-mode` with `rust-analyzer` (dnf, on PATH).

## Adding a new language — the recipe

1. Create `<lang>/` with `Dockerfile`, `Makefile`, `entrypoint/` (shell/entrypoint/format + the
   `0N-install-*.sh` group scripts), `.dockerignore`, `.gitignore`, `CLAUDE.md`, mounting at
   `/hanoi-<lang>`.
2. Reproduce the shared core from the Python canonical source and keep the front-ends thin.
3. Add `entrypoint/dotfiles/.emacs.d/` with the language's LSP set and the three must-dos above.
4. Verify nested: `make image` builds, the test gate passes, the GUI/build targets compile; then run
   `make update-emacs-packages` once to vendor `elpa/`.

## Cross-links

- `tasks/split-into-per-language-containers.md` — the work record of the split that produced this layout.
- `tasks/reference/architecture-overview.md` — the game-code architecture (dispatch, the recipe
  invariant, the module map), shared by all language ports.
- The container-per-project template + the "Self-contained images + live source" rule live in the
  maintainer's cross-project conventions.
