(require 'package)
(add-to-list 'package-archives '("melpa" . "https://melpa.org/packages/") t)
(package-initialize)

;; The C/C++ dev set for the hanoi C/C++ subproject: helm, lsp-mode + clangd, clang-format,
;; company, flycheck, magit, folding, and the themes init.el chooses between. The shared
;; part matches the cross-project list (github.com/billsix/runClaudeInContainer
;; tasks/reference/emacs-container-contract.md). The vendored elpa/ is regenerated from
;; this list by `make update-emacs-packages`.
(setq package-selected-packages
      '(lsp-mode
        lsp-ui
        lsp-treemacs
        helm-lsp
        helm-xref
        yasnippet
        projectile
        hydra
        flycheck
        company
        avy
        which-key

        material-theme
        dracula-theme
        monokai-theme
        zenburn-theme

        fold-this
        yafolding

        org-modern

        discover
        better-defaults
        magit
        markdown-mode
        markdown-preview-mode

        clang-format
        cmake-mode
        ))

(when (cl-find-if-not #'package-installed-p package-selected-packages)
  (package-refresh-contents)
  (mapc #'package-install package-selected-packages))
