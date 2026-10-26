.DEFAULT_GOAL := help

# The Rust subproject of hanoi: a Cargo workspace (hanoigame lib + hanoi-cli / hanoi /
# hanoi-gui) plus the Tauri front-end under tauri/. Self-contained -- own image, own
# emacs set. Kept in sync with the Python canonical source in ../python (never a
# replacement).

# USE_EMACS installs emacs + the vendored Rust dev set (rust-mode + rust-analyzer).
# On by default; a lean MINIMAL_IMAGE build (make image MINIMAL_IMAGE=1) drops it, for a
# small export/airgap image. To refresh the vendored elpa: make update-emacs-packages.
USE_EMACS ?= $(if $(filter 1,$(MINIMAL_IMAGE)),0,1)

# USE_WASM bakes the WebAssembly toolchain (wasm32 Rust std + trunk) for the egui web
# build (make egui-web/egui-serve). On by default; a lean MINIMAL_IMAGE build drops it.
USE_WASM ?= $(if $(filter 1,$(MINIMAL_IMAGE)),0,1)

CONTAINER_CMD ?= $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)
CONTAINER_NAME = hanoi-rust

# Extra flags for every container `run`. Auto-set when running nested (NESTED_PODMAN=1
# -> --cgroups=disabled); empty on a normal host. On `run` lines only, never `build`.
PODMAN_RUN_FLAGS ?= $(if $(filter 1,$(NESTED_PODMAN)),--cgroups=disabled)

TMUX_FILE := $(HOME)/.tmux.conf
TMUX_REAL_PATH := $(shell readlink -f $(TMUX_FILE))
TMUX_MOUNT := $(shell if [ -f $(TMUX_REAL_PATH) ]; then echo "-v $(TMUX_REAL_PATH):/root/.tmux.conf:Z" ; fi)

REPO_MOUNT = /$(CONTAINER_NAME)
# The shared wx UI definition lives at the repo-root ui/ (one file). hanoi-gui's
# hanoi.xrc is a git-tracked symlink to ../../ui/hanoi.xrc; mounting ui/ at /ui makes
# that symlink resolve in-container (/hanoi-rust/hanoi-gui/../../ui = /ui) at
# cargo-build time, when the GUI's include_str! reads it. Read-only -- the UI file is
# never written from here.
UI_MOUNT := -v $(CURDIR)/../ui:/ui:ro,Z
FILES_TO_MOUNT = -v $(shell pwd):$(REPO_MOUNT):Z $(UI_MOUNT) $(TMUX_MOUNT)

# X11 display passthrough for the wxDragon GUI and the Tauri webview.
X_FLAGS_FOR_CONTAINER = -e DISPLAY=$(DISPLAY) \
	-v /tmp/.X11-unix:/tmp/.X11-unix \
	--security-opt label=type:container_runtime_t
DRI_DEVICE := $(shell [ -d /dev/dri ] && echo "--device /dev/dri")
WAYLAND_FLAGS_FOR_CONTAINER = -e "XDG_SESSION_TYPE=wayland" \
			      -e "WAYLAND_DISPLAY=$(WAYLAND_DISPLAY)" \
			      -e "XDG_RUNTIME_DIR=$(XDG_RUNTIME_DIR)" \
			      -v "$(XDG_RUNTIME_DIR):$(XDG_RUNTIME_DIR)" \
			      $(DRI_DEVICE)

ifeq ($(USE_EMACS), 1)
  ELPA_MOUNT = -v $(CURDIR)/entrypoint/dotfiles/.emacs.d/:/root/.emacs.d/:U,z
else
  ELPA_MOUNT =
endif

.PHONY: all
all: shell ## Build the image and get a shell in it

.PHONY: image
image: ## Build the podman image (Rust toolchain + native build stack)
	$(CONTAINER_CMD) build --build-arg USE_EMACS=$(USE_EMACS) --build-arg USE_WASM=$(USE_WASM) -t $(CONTAINER_NAME) .

# --- shell / shell-exec share ONE invocation so they can never drift (scoped to this
# pair only). shell.sh sets the cargo caches on the mount.
SHELL_RUN_FLAGS = \
		--entrypoint /bin/bash \
		$(FILES_TO_MOUNT) \
		$(X_FLAGS_FOR_CONTAINER) \
		$(WAYLAND_FLAGS_FOR_CONTAINER) \
		$(ELPA_MOUNT) \
		-v $(CURDIR)/entrypoint/.bashrc:/root/.bashrc:Z

SHELL_EXEC_ARGS = -c 'cd $(REPO_MOUNT) && $(if $(CMD),$(CMD),exec bash $(SCRIPT))'

.PHONY: shell
shell: ## Get a shell in an ephemeral container made from the image
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(SHELL_RUN_FLAGS) $(CONTAINER_NAME) /usr/local/bin/shell.sh

.PHONY: shell-exec
# Depends on image (NOT format) so a batch run never reformats the source as a side effect.
shell-exec: image ## Run a script/command in the container env (no TTY): make shell-exec SCRIPT=path | CMD='...'
	@[ -n "$(SCRIPT)$(CMD)" ] || { echo 'usage: make shell-exec SCRIPT=<repo-relative path> | CMD="..."'; exit 2; }
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) --rm $(SHELL_RUN_FLAGS) $(CONTAINER_NAME) /usr/local/bin/shell.sh $(SHELL_EXEC_ARGS)

.PHONY: format
format: image ## Format the Rust code with rustfmt (entrypoint/format.sh)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm \
		--entrypoint /bin/bash $(FILES_TO_MOUNT) $(CONTAINER_NAME) /format.sh

.PHONY: check
check: image ## Compile-check the workspace INCLUDING tests/examples (cargo check --all-targets) -- catches a test module that stopped compiling, which bare `cargo check` and `make format` both skip
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) --rm \
		--entrypoint /bin/bash $(FILES_TO_MOUNT) $(CONTAINER_NAME) \
		-c '$(RUST_SETUP) && cargo check --workspace --all-targets'

.PHONY: type-check
type-check: image ## Type-check + lint + fmt-check the Tauri frontend web files via Deno (deno check/lint/fmt; JSDoc + checkJs, no node_modules)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) --rm \
		--entrypoint /bin/bash $(FILES_TO_MOUNT) $(CONTAINER_NAME) \
		-c 'cd $(REPO_MOUNT)/tauri/frontend && s=0; \
		    deno check --check-js --no-lock main.js || s=1; \
		    deno lint main.js || s=1; \
		    deno fmt --check || s=1; \
		    exit $$s'

# --- Run a front-end. Two cargo caches on the bind-mount (both gitignored) make repeat
# runs fast and avoid re-doing the heavy wxDragon wxWidgets build every run.
PLAY_FLAGS = --entrypoint /bin/bash $(FILES_TO_MOUNT) \
	$(X_FLAGS_FOR_CONTAINER) $(WAYLAND_FLAGS_FOR_CONTAINER)
RUST_SETUP = cd $(REPO_MOUNT) && export CARGO_TARGET_DIR=$(REPO_MOUNT)/.container-target && export CARGO_HOME=$(REPO_MOUNT)/.container-cargo
# Tauri is not a workspace member and keeps its own target dir; it shares the crate cache.
TAURI_SETUP = cd $(REPO_MOUNT)/tauri/src-tauri && export CARGO_TARGET_DIR=$(REPO_MOUNT)/tauri/.container-target && export CARGO_HOME=$(REPO_MOUNT)/.container-cargo && export WEBKIT_DISABLE_DMABUF_RENDERER=1
# egui (eframe) is its own workspace too (own target dir, shared crate cache).
EGUI_SETUP = cd $(REPO_MOUNT)/hanoi-egui && export CARGO_TARGET_DIR=$(REPO_MOUNT)/hanoi-egui/.container-target && export CARGO_HOME=$(REPO_MOUNT)/.container-cargo

.PHONY: cli
cli: image ## Run the CLI front-end (hanoi-cli)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(PLAY_FLAGS) $(CONTAINER_NAME) \
		-c '$(RUST_SETUP) && exec cargo run -q -p hanoi-cli'

.PHONY: tui
tui: image ## Run the terminal-UI front-end (ratatui)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(PLAY_FLAGS) $(CONTAINER_NAME) \
		-c '$(RUST_SETUP) && exec cargo run -q -p hanoi'

.PHONY: wx
wx: image ## Run the wxDragon GUI front-end (first run builds wxWidgets from source)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(PLAY_FLAGS) $(CONTAINER_NAME) \
		-c '$(RUST_SETUP) && exec cargo run -q -p hanoi-gui'

.PHONY: tauri
tauri: image ## Run the Tauri desktop front-end (webkit2gtk; another UI like wx)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(PLAY_FLAGS) $(CONTAINER_NAME) \
		-c '$(TAURI_SETUP) && exec cargo run'

.PHONY: egui
egui: image ## Run the egui native GUI front-end (eframe/glow)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(PLAY_FLAGS) $(CONTAINER_NAME) \
		-c '$(EGUI_SETUP) && exec cargo run'

.PHONY: egui-web
egui-web: image ## Build the egui WebAssembly app with trunk (-> hanoi-egui/dist; needs a USE_WASM image)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) --rm $(PLAY_FLAGS) $(CONTAINER_NAME) \
		-c '$(EGUI_SETUP) && exec trunk build --release'

.PHONY: egui-serve
egui-serve: image ## Serve the egui web app with trunk at http://localhost:8080 (needs a USE_WASM image)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm -p 8080:8080 $(PLAY_FLAGS) $(CONTAINER_NAME) \
		-c '$(EGUI_SETUP) && exec trunk serve --address 0.0.0.0'

.PHONY: image-export
image-export: ## export the OCI image to a timestamped tar in this dir
	$(CONTAINER_CMD) save $(CONTAINER_NAME) -o $(CONTAINER_NAME)-$(shell date +%m-%d-%Y_%H-%M-%S).tar

.PHONY: image-import
image-import: ## import an OCI image tar: make image-import FILE=foo.tar
	$(CONTAINER_CMD) load -i $(FILE)

# Refresh the vendored Emacs packages (see the Python subproject for the pattern). Network.
.PHONY: update-emacs-packages
update-emacs-packages: ## USE_EMACS=1: rebuild, wipe+reinstall vendored elpa, strip *.elc/*.eln, git add -f
	$(MAKE) image USE_EMACS=1
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) --rm \
		-v $(CURDIR)/entrypoint/dotfiles/.emacs.d/:/root/.emacs.d/:U,z \
		--entrypoint /bin/bash $(CONTAINER_NAME) \
		-c 'mkdir -p /root/.emacs.d/elpa; find /root/.emacs.d/elpa -mindepth 1 -delete; \
		    emacs --batch --load /root/.emacs.d/install-melpa-packages.el'
	mkdir -p $(CURDIR)/entrypoint/dotfiles/.emacs.d/elpa && cd $(CURDIR)/entrypoint/dotfiles/.emacs.d/elpa && \
		find . \( -iname '*.elc' -o -iname '*.eln' \) -delete && git add -A -f .
	@echo "Done: reinstalled packages, stripped *.elc/*.eln, staged elpa -- review and commit."

.PHONY: help
help:
	@grep --extended-regexp '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
