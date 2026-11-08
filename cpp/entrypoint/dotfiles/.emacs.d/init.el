;; Emacs config for the hanoi C++ subproject: helm, C/C++ editing with lsp-mode + clangd.
;; clangd reads compile_commands.json from the cmake build dir (generated with
;; CMAKE_EXPORT_COMPILE_COMMANDS=ON).
;; Layout: github.com/billsix/runClaudeInContainer tasks/reference/emacs-container-contract.md.
(package-initialize)
;; Byte-compile each vendored package that has no .elc yet, through package.el's own
;; compile (package-recompile), the same path package-install uses. The .elc land in
;; the bind-mounted elpa/ and persist, so later starts find them and compile nothing;
;; a package whose files cannot all compile (compat's compat-2x.el backports on a
;; newer Emacs) still gets its other .elc and is not retried on every start.
(dolist (entry package-alist)
  (let ((desc (cadr entry)))
    (unless (directory-files-recursively (package-desc-dir desc) "\\.elc\\'")
      (with-demoted-errors "Error while compiling: %S"
        (package-recompile desc)))))

(load-file "~/.emacs.d/helm.el")
(load-file "~/.emacs.d/preferences.el")

;; theme
;(load-theme 'modus-vivendi t)
(load-theme 'material t)
;(load-theme 'dracula t)
;(load-theme 'monokai t)
;(load-theme 'zenburn t)

(global-auto-revert-mode)
(setq auto-revert-avoid-polling t)

(use-package yafolding
  :hook (prog-mode . yafolding-mode))

(setq lsp-keymap-prefix "C-c l")
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

;; Never load dap-mode.
(setq lsp-enable-dap-auto-configure nil)

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
  :after cc-mode               ; c-mode-base-map is defined by cc-mode; wait for it
  :bind (:map c-mode-base-map
              ("C-c f" . clang-format-buffer)))

;; Enable hideshow (hs-minor-mode) in all programming modes so code regions
;; (functions, blocks) can be folded/collapsed.  Toggle a block with
;; `C-c @ C-c`; hide-all / show-all with `C-c @ C-M-h` / `C-c @ C-M-s`.
(add-hook 'prog-mode-hook #'hs-minor-mode)
