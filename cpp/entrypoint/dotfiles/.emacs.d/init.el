;; Emacs config for the hanoi C++ subproject: C/C++ editing with lsp-mode + clangd.
;; clangd reads compile_commands.json from the cmake build dir (generated with
;; CMAKE_EXPORT_COMPILE_COMMANDS=ON).
(package-initialize)

(load-file "~/.emacs.d/preferences.el")

;; theme
(load-theme 'modus-vivendi t)

(global-auto-revert-mode)
(setq auto-revert-avoid-polling t)

(require 'lsp-mode)

;; Pin the lsp project root to the subproject's fixed container mount (REPO_MOUNT =
;; /hanoi-cpp). hanoi per-language convention -- see the repo-root CLAUDE.md and
;; tasks/reference/per-language-subproject-layout.md.
(setq lsp-auto-guess-root nil)
(defun hanoi-cpp-lsp-root (&rest _)
  "The fixed in-container project root for the hanoi C++ subproject."
  "/hanoi-cpp")
(advice-add 'lsp--calculate-root :override #'hanoi-cpp-lsp-root)

;; Keep lsp's file-watcher off the build + cache dirs under the mount (the cmake build
;; tree, the emscripten web output, the vendored emacs trees).
(with-eval-after-load 'lsp-mode
  (dolist (re '("[/\\\\]build\\'"
                "[/\\\\]web\\'"
                "[/\\\\]elpa\\'"
                "[/\\\\]eln-cache\\'"))
    (add-to-list 'lsp-file-watch-ignored-directories re)))

;; C/C++ via clangd.
(use-package lsp-mode
  :hook ((c-mode c++-mode) . lsp-deferred)
  :init
  (setq lsp-clients-clangd-executable "clangd"))

;; yasnippet active so lsp expands clangd's completion snippets (the `${1:arg}$0`
;; tab-stops) into interactive placeholders instead of inserting raw text.
(use-package yasnippet
  :config (yas-global-mode 1))

(use-package lsp-ui :commands lsp-ui-mode)

(use-package company
  :hook (after-init . global-company-mode)
  :config
  (setq company-minimum-prefix-length 1
        company-idle-delay 0.0))

(use-package clang-format
  :bind (:map c-mode-base-map
              ("C-c f" . clang-format-buffer)))
