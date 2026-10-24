(require 'package)
(add-to-list 'package-archives '("melpa" . "https://melpa.org/packages/") t)
(package-initialize)

;; The Rust dev set for the hanoi Rust subproject: lsp-mode + rust-mode (rust-analyzer),
;; company completion, flycheck, magit, and the usual navigation helpers.
(setq package-selected-packages
      '(lsp-mode
        rust-mode
        lsp-ui
        company
        flycheck
        yasnippet
        projectile
        which-key
        magit
        markdown-mode
        toml-mode
        material-theme
        dracula-theme))

(when (cl-find-if-not #'package-installed-p package-selected-packages)
  (package-refresh-contents)
  (mapc #'package-install package-selected-packages))
