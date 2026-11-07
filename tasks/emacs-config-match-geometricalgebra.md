# Bring hanoi's three Emacs configs onto the geometricalgebra / modelviewprojection setup

**Status:** proposed — needs go-ahead (requested by William Emerison Six <billsix@gmail.com>, 2026-11-07)
**Priority:** 5
**Difficulty:** 4

## BLUF

hanoi's subprojects (`cpp/`, `python/`, `rust/`) each vendor a minimal, hand-written Emacs config: plain
lsp-mode with company and flycheck, the `modus-vivendi` theme, and **no helm**, so `C-x C-f` prefills
nothing and doc paths can't be opened from the cursor. Make each one use Emacs the way
github.com/billsix/geometricalgebra and github.com/billsix/modelviewprojection do: helm (`helm.el`
loaded from `init.el`, `helm-find-files`/`helm-M-x`/`helm-mini`, helm-xref, helm-lsp), the same
preferences and theme set, and `helm-ff-guess-ffap-filenames` so `C-x C-f` on a repo-root-relative doc
path opens the file. Keep each subproject's own language server (pyright via lsp-pyright for Python,
rust-analyzer, clangd). Done = the three configs match the reference layout, their `elpa/` trees are
regenerated, `tools/check_helm_file_at_point.sh` (github.com/billsix/runClaudeInContainer) passes 7/7
on each, and the maintainer confirms the editor in one subproject's `make shell`.

## Context

- **Reference configs:** geometricalgebra `entrypoint/dotfiles/.emacs.d/{init,helm,preferences,install-melpa-packages}.el`
  and modelviewprojection's (the two differ slightly in `init.el` and `helm.el`; diff them first and
  pick the shared shape). Their `helm.el` sets `helm-ff-guess-ffap-filenames` (added 2026-11-07, see
  runClaudeInContainer `tasks/archive/2026/11/07/doc-file-references-openable-in-editor.md`).
- **hanoi today** (2026-11-07 diff, `python/` against geometricalgebra): `init.el` has no
  `(load-file "~/.emacs.d/helm.el")`, no `byte-recompile-directory`, theme `modus-vivendi` instead of
  `material`, plain `(require 'lsp-mode)` instead of the `use-package lsp-mode` block, no
  `yafolding`. `preferences.el` lacks the colour, face-height, `region-generate-sha1`, and terminal
  transparency settings, and serves emacs-lisp with eglot. `install-melpa-packages.el` lacks helm,
  helm-lsp, helm-xref, lsp-treemacs, hydra, avy, the theme packages, fold-this/yafolding, org-modern
  (and, for Python, blacken/elpy). `cpp/` and `rust/` follow the same minimal shape (check each).
- Each subproject is standalone, with its own Makefile `ELPA_MOUNT` (only `elpa/` is bind-mounted; the
  rest of `.emacs.d` reaches the image by `COPY`), its own `install-emacs` group script, and its own
  `make update-emacs-packages`. The emacs-vendoring rules are in the personal overlay (dotfiles
  `.ai-coding-conventions.personal.md`, "emacs … installed BINARY-ONLY"), including **npm pyright,
  never the pip `pyright`**, for Python.
- **hanoi's own Emacs rules must survive the change** (`CLAUDE.md` › Conventions › "Emacs (per-language
  dev tooling)"; full elisp in `tasks/reference/per-language-subproject-layout.md`): every `init.el`
  (1) pins the LSP root to the subproject's `REPO_MOUNT` (`/hanoi-<lang>`), (2) ignores the build/cache
  dirs under the mount in `lsp-file-watch-ignored-directories`, and (3) enables yasnippet. The
  reference configs don't carry these; add helm *on top of* them, and update the layout reference doc's
  recipe so a new language folder gets helm too.
- Decision to keep: hanoi chose lsp-mode for Python and eglot only for emacs-lisp so two clients never
  attach to one Python buffer (comment in `python/.../preferences.el`). Preserve that split, or adopt
  the reference configs' arrangement only after checking they avoid the double attach too.

## Plan

1. Diff geometricalgebra against modelviewprojection's `.emacs.d/*.el`; write down the common shape and
   which differences are project-specific (language server, mode hooks).
2. For each of `python/`, `rust/`, `cpp/`: copy in `helm.el` (with the ffap setting), align `init.el` and
   `preferences.el` to the reference while keeping that language's LSP block, and extend
   `install-melpa-packages.el` with the helm/theme/folding set.
3. `make update-emacs-packages` in each subproject (needs network) to regenerate its vendored `elpa/`
   (source-only, `.elc`/`.eln` stripped, `git add -f`), then `make image`.
4. Run `tools/check_helm_file_at_point.sh <subproject>/entrypoint/dotfiles/.emacs.d` (runClaudeInContainer)
   for each: 7/7.
5. Maintainer: `make shell` in one subproject, open a Python/Rust/C++ file (LSP attaches once, helm
   completion works) and a task doc (`C-x C-f` on `tasks/reference/…` opens it).
6. Update `CLAUDE.md` / each subproject's notes where they describe the Emacs set.

## Open questions

1. **Theme:** switch to the references' `material` theme, or keep hanoi's `modus-vivendi`? *Recommend
   matching the references (that's the point of the task), unless you prefer modus here.*
