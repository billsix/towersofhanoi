# Bring hanoi's three Emacs configs onto the geometricalgebra / modelviewprojection setup (done 2026-11-07)

**Owed by the maintainer:** `make update-emacs-packages` in `python/`, `rust/`, and `cpp/` (needs
network). Then commit each `elpa/`, `make image`, and confirm the editor in one subproject's
`make shell`.

## Scope (William Emerison Six <billsix@gmail.com>, 2026-11-07)

"The configuration and the framework, and the make update-emacs-packages, but not the vendored emacs
packages themselves." So the `elpa/` trees were not regenerated. **Until they are, helm and the new
packages are missing from them, and Emacs in `make shell` reports `helm.el` failing to load.** The
theme question (keep `modus-vivendi` or switch) was settled by the same instruction to port the
setup over: `material` is active, and the other themes stay commented out on the lines around it.

## What was done

Done for every hanoi subproject that uses Emacs: `python/`, `rust/`, and `cpp/`. The root book image
has none.

- **`helm.el`** (new) and **`preferences.el`**: byte-identical copies of the shared files. They came
  from github.com/billsix/Craft, which matches modelviewprojection and the text in
  github.com/billsix/runClaudeInContainer `tasks/reference/emacs-container-contract.md`.
  - The shared `preferences.el` hooks eglot to emacs-lisp only, so the project language keeps a
    single client (lsp-mode).
  - Its comment says "C/C++" in every language's copy across the fleet, hanoi's included. That
    wording is a fleet-wide fix; it was not edited here, to keep the file byte-identical.
- **`init.el`**, in the contract's order: `package-initialize`, then `helm.el` and `preferences.el`,
  then the theme block, auto-revert, `yafolding`, `lsp-keymap-prefix "C-c l"`, and the language block.
  - hanoi's three rules are kept unchanged: the LSP root pinned to `/hanoi-<lang>`, the build/cache
    dirs in `lsp-file-watch-ignored-directories`, and yasnippet.
  - Added: `lsp-enable-dap-auto-configure nil`; for Python, pyright `basic` type checking and
    auto-import completions.
  - Not added: the references' global `(add-hook 'prog-mode-hook #'lsp-deferred)`. hanoi hooks lsp
    per language mode, so emacs-lisp buffers (eglot's) never get a second client.
  - `byte-recompile-directory` was left out. It is an open question in runClaudeInContainer
    `tasks/emacs-contract-conformance.md`, and `elpa/` is source-only.
  - **cpp fix:** the `clang-format` `C-c f` binding failed at startup on `master` (`c-mode-base-map`
    void: the map is defined by cc-mode, which had not loaded yet). It now waits with
    `:after cc-mode`, as Craft's does.
- **`install-melpa-packages.el`**: the contract's shared set plus each language's own packages.
  - Shared: lsp-mode, lsp-ui, lsp-treemacs, helm-lsp, helm-xref, yasnippet, projectile, hydra,
    flycheck, company, avy, which-key, the four themes, fold-this, yafolding, org-modern, discover,
    better-defaults, magit, markdown-mode, markdown-preview-mode.
  - Per language: lsp-pyright (Python); rust-mode and toml-mode (Rust); clang-format and cmake-mode
    (C++).
- **`make update-emacs-packages`** (Makefile, all three) now has the reference shape:
  - it mounts only `elpa/`, plus `install-melpa-packages.el` read-only, and runs under `set -e`;
  - before, it mounted the whole `.emacs.d` read-write, which is how `eln-cache/` came to be written
    into the checkout.
- **Dockerfiles** bake `helm.el` with `init.el`/`preferences.el`. The python and rust comments said
  `make shell` mounted the whole `.emacs.d`; they now say only `elpa/` is mounted.
- **Docs:** the root `CLAUDE.md` Emacs bullet, the three subproject `CLAUDE.md` "Emacs" sections, and
  `tasks/reference/per-language-subproject-layout.md` (the recipe, and step 3 of adding a language).

## Verification

Each subproject's new package list was installed from MELPA into a scratch `~/.emacs.d` outside the
repo, not into `elpa/`.

- **Loading `init.el` in batch, each language:**
  - no errors (after the cpp fix);
  - `material` active, `helm-mode` on, `helm-ff-guess-ffap-filenames` set, yasnippet on;
  - the LSP root resolves to `/hanoi-python`, `/hanoi-rust`, `/hanoi-cpp`;
  - each language mode hooks lsp-mode and not `eglot-ensure`;
  - cpp's `C-c f` is `clang-format-buffer` in a `c++-mode` buffer.
- **Helm check:** github.com/billsix/runClaudeInContainer `tools/check_helm_file_at_point.sh`
  passed 7/7 on each.
- **Image builds:**
  - python: the full `podman build` passed. The image bakes `helm.el`, `init.el`, and
    `preferences.el`, and its Emacs 31.1 loads the config cleanly with the scratch packages
    mounted. `pyright-langserver` is on PATH.
  - rust and cpp: recorded in the commit that archives this task.
