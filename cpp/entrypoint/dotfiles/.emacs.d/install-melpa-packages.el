(require 'package)
(add-to-list 'package-archives '("melpa" . "https://melpa.org/packages/") t)
(package-initialize)

;; The C/C++ dev set for the hanoi C++ subproject: lsp-mode + clangd, clang-format,
;; company completion, flycheck, magit, and the usual navigation helpers.
(setq package-selected-packages
      '(lsp-mode
        clang-format
        lsp-ui
        company
        flycheck
        yasnippet
        projectile
        which-key
        magit
        markdown-mode
        cmake-mode
        material-theme
        dracula-theme))

(when (cl-find-if-not #'package-installed-p package-selected-packages)
  (package-refresh-contents)
  (mapc #'package-install package-selected-packages))
