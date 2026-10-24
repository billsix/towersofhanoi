;; Emacs config for the hanoi Python subproject: Python editing with lsp-mode +
;; pyright (lsp-pyright). pyright-langserver is installed globally (npm) in the image.
(package-initialize)

(load-file "~/.emacs.d/preferences.el")

;; theme
(load-theme 'modus-vivendi t)

(global-auto-revert-mode)
(setq auto-revert-avoid-polling t)

(require 'lsp-mode)

;; Pin the lsp project root. The Python subproject is ALWAYS mounted at /hanoi-python in
;; the container (REPO_MOUNT in the Makefile), and pyproject.toml / setup.py / src/ live
;; there -- so pin the root explicitly instead of letting lsp prompt "Import project
;; root?" or guess. pyright then reads pyproject.toml and treats src/ as the project.
;; (Mirrors the maintainer's per-language template, which pins the root the same way, with
;; this subproject's mount path.)
(setq lsp-auto-guess-root nil)
(defun hanoi-python-lsp-root (&rest _)
  "The fixed in-container project root for the hanoi Python subproject."
  "/hanoi-python")
(advice-add 'lsp--calculate-root :override #'hanoi-python-lsp-root)

;; Keep lsp's generic file-watcher off the cache dirs and the vendored emacs packages
;; that live UNDER the mount, so it doesn't prompt "watch N files?" on startup or churn
;; watching artifacts. Match any such dir anywhere in the tree.
(with-eval-after-load 'lsp-mode
  (dolist (re '("[/\\\\]\\.ruff_cache\\'"
                "[/\\\\]\\.pytest_cache\\'"
                "[/\\\\]__pycache__\\'"
                "[/\\\\]elpa\\'"
                "[/\\\\]eln-cache\\'"))
    (add-to-list 'lsp-file-watch-ignored-directories re)))

;; Python via pyright (lsp-pyright). pyright is installed globally (npm) in the image;
;; the package is installed into the system site-packages, so imports resolve.
;; yasnippet must be ACTIVE for lsp to expand completion snippets: the server returns
;; items with `${N:arg}` tab-stops and a `$0` final point, and lsp only turns those into
;; interactive placeholders when yasnippet is on -- without it the raw template text is
;; inserted. (yasnippet is in install-melpa-packages.el.)
(use-package yasnippet
  :config (yas-global-mode 1))

(use-package lsp-pyright
  :hook (python-mode . (lambda ()
                         (require 'lsp-pyright)
                         (lsp-deferred))))

(use-package lsp-ui :commands lsp-ui-mode)

(use-package company
  :hook (after-init . global-company-mode)
  :config
  (setq company-minimum-prefix-length 1
        company-idle-delay 0.0))
