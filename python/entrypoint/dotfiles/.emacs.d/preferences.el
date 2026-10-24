(show-paren-mode)
(tool-bar-mode -1)
(menu-bar-mode -1)
(setq inhibit-startup-message t)        ; Disable startup message
(setq-default indent-tabs-mode nil)

(add-hook 'before-save-hook 'delete-trailing-whitespace)

(visual-line-mode t)
(global-visual-line-mode t)
(global-display-line-numbers-mode t)
(set-buffer-file-coding-system 'unix)

(setq make-backup-files nil)

;; emacs-lisp is served by eglot; Python is served by lsp-mode + pyright (see
;; init.el), so the two clients don't both attach to a Python buffer.
(use-package eglot
  :ensure t
  :defer t
  :hook (emacs-lisp-mode . eglot-ensure))

(global-company-mode)
(setq company-idle-delay 0)
(setq company-minimum-prefix-length 1)
