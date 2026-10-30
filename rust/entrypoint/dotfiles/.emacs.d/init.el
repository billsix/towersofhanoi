;; Emacs config for the hanoi Rust subproject: Rust editing with lsp-mode +
;; rust-analyzer (installed via dnf, on PATH). lsp-mode uses the Cargo.toml directory
;; as the project root.
(package-initialize)

(load-file "~/.emacs.d/preferences.el")

;; theme
(load-theme 'modus-vivendi t)

(global-auto-revert-mode)
(setq auto-revert-avoid-polling t)

(require 'lsp-mode)

;; Pin the lsp project root. The Rust subproject is ALWAYS mounted at /hanoi-rust in the
;; container (REPO_MOUNT in the Makefile), and the Cargo workspace lives there -- so pin
;; the root explicitly instead of letting lsp prompt "Import project root?" or guess.
;; rust-analyzer then roots at the workspace. SAME convention as every language subproject
;; -- see "Emacs: pin the LSP project root per subproject" in the repo-root CLAUDE.md.
(setq lsp-auto-guess-root nil)
(defun hanoi-rust-lsp-root (&rest _)
  "The fixed in-container project root for the hanoi Rust subproject."
  "/hanoi-rust")
(advice-add 'lsp--calculate-root :override #'hanoi-rust-lsp-root)

;; Keep lsp's generic file-watcher off the build + cache dirs that live UNDER the mount
;; (the cargo target + registry caches are tens of thousands of files). Without this, lsp
;; prompts "watch N files?" on startup and then churns watching build artifacts;
;; rust-analyzer watches the real source itself. Match any such dir anywhere in the tree.
(with-eval-after-load 'lsp-mode
  (dolist (re '("[/\\\\]\\.container-target\\'"
                "[/\\\\]\\.container-cargo\\'"
                "[/\\\\]target\\'"
                "[/\\\\]elpa\\'"
                "[/\\\\]eln-cache\\'"))
    (add-to-list 'lsp-file-watch-ignored-directories re)))

;; yasnippet must be ACTIVE for lsp to expand completion snippets: rust-analyzer returns
;; items like `chunk_by(${1:pred})$0` (${N:..} tab-stops, $0 final point), and lsp only
;; turns those into interactive placeholders when yasnippet is on -- without it the raw
;; template text is inserted. (yasnippet is in install-melpa-packages.el.)
(use-package yasnippet
  :config (yas-global-mode 1))

(use-package rust-mode
  :hook (rust-mode . lsp-deferred)
  :init
  (setq rust-mode-treesitter-derive nil))

(setq lsp-rust-analyzer-server-command '("rust-analyzer"))

(use-package lsp-ui :commands lsp-ui-mode)

(use-package company
  :hook (after-init . global-company-mode)
  :config
  (setq company-minimum-prefix-length 1
        company-idle-delay 0.0))

;; Enable hideshow (hs-minor-mode) in all programming modes so code regions
;; (functions, blocks) can be folded/collapsed.  Toggle a block with
;; `C-c @ C-c`; hide-all / show-all with `C-c @ C-M-h` / `C-c @ C-M-s`.
(add-hook 'prog-mode-hook #'hs-minor-mode)
