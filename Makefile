.DEFAULT_GOAL := help

# BUILD_DOCS gates the heavy Sphinx + TeX Live docs toolchain (02-install-docs.sh).
# Default is full (1). Pass MINIMAL_IMAGE=1 to build a lean image that drops it (a small
# export/airgap image); a nested `make image` builds FULL by default now that the sandbox's
# inner podman store is on disk (no RAM ceiling), so lean is a deliberate opt-in, not inferred.
# Override either way: make image BUILD_DOCS=1. (Build-CONTENT twin of the PODMAN_RUN_FLAGS
# RUN-capability idiom below — MINIMAL_IMAGE is image content, NESTED_PODMAN is run capability;
# the two are independent. Standard: runClaudeInContainer tasks/reference/minimal-nested-images.md.)
# The gate `make docs` needs BUILD_DOCS=1.
BUILD_DOCS ?= $(if $(filter 1,$(MINIMAL_IMAGE)),0,1)

# USE_X_WINDOWS installs the X11/Wayland client libs (03-install-xwindows.sh) so the
# wxPython GUI (hanoi-gui) can open a window. On by default, the same way
# modelviewprojection does it. Unlike BUILD_DOCS it stays ON when nested (plain 1, not
# the NESTED-aware form) so the GUI works from a nested shell too. Bare `podman build`
# stays lean (Dockerfile ARG default 0). Override: make image USE_X_WINDOWS=0.
USE_X_WINDOWS ?= 1

# USE_RUST installs the Rust toolchain + wx dev/link packages (04-install-rust.sh) so the
# Rust ports (rust/: hanoi, hanoi-cli, hanoi-gui) build/run in the container alongside the
# Python ports. On by default; a bare `podman build` stays lean (Dockerfile ARG 0).
# Override: make image USE_RUST=0.
USE_RUST ?= 1


TMUX_FILE := $(HOME)/.tmux.conf
TMUX_REAL_PATH := $(shell readlink -f $(TMUX_FILE))
TMUX_MOUNT := $(shell if [ -f $(TMUX_REAL_PATH) ]; then echo "-v $(TMUX_REAL_PATH):/root/.tmux.conf:Z" ; fi)

CONTAINER_CMD ?= $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)
CONTAINER_NAME = hanoi

# Extra flags for every container `run`. Auto-set when running nested inside a
# runClaudeInContainer/runCrushInContainer sandbox (which exports NESTED_PODMAN=1,
# making --cgroups=disabled apply so podman-in-podman works); empty — and
# byte-identical behavior — on a normal host. Overridable:
#   make shell PODMAN_RUN_FLAGS='--cgroups=disabled --network=host'
# On `run` lines only, never `build` (podman build rejects --cgroups). Convention:
# runClaudeInContainer tasks/reference/nested-podman-design.md.
PODMAN_RUN_FLAGS ?= $(if $(filter 1,$(NESTED_PODMAN)),--cgroups=disabled)
FILES_TO_MOUNT = -v $(shell pwd):/$(CONTAINER_NAME):Z \
		 -v ./output/:/output/:Z \
                 $(TMUX_MOUNT)
#                 -v ./bash:/$(CONTAINER_NAME)/bash:Z \
#		 -v ./python:/$(CONTAINER_NAME)/python:Z

# X11 display passthrough for the wxPython GUI (hanoi-gui): the host's DISPLAY + X
# socket. The security-opt label lets the container talk to the host X server under
# SELinux. Modelled on modelviewprojection.
X_FLAGS_FOR_CONTAINER = -e DISPLAY=$(DISPLAY) \
	-v /tmp/.X11-unix:/tmp/.X11-unix \
	--security-opt label=type:container_runtime_t
# GPU render node (harmless for wx's 2D Cairo renderer, kept for parity); skipped if
# /dev/dri is absent.
DRI_DEVICE := $(shell [ -d /dev/dri ] && echo "--device /dev/dri")
# Wayland display passthrough: the compositor socket + its env. No PYGLFW_LIBRARY line
# (that is glfw-specific in modelviewprojection; hanoi's GUI is wxPython/GTK, not glfw).
WAYLAND_FLAGS_FOR_CONTAINER = -e "XDG_SESSION_TYPE=wayland" \
			      -e "WAYLAND_DISPLAY=$(WAYLAND_DISPLAY)" \
			      -e "XDG_RUNTIME_DIR=$(XDG_RUNTIME_DIR)" \
			      -v "$(XDG_RUNTIME_DIR):$(XDG_RUNTIME_DIR)" \
			      $(DRI_DEVICE)




.PHONY: all
all: shell ## Build the image and get a shell in it

.PHONY: image
image: ## Build a $(CONTAINER_CMD)
	$(CONTAINER_CMD) build \
                         --build-arg BUILD_DOCS=$(BUILD_DOCS) \
                         --build-arg USE_X_WINDOWS=$(USE_X_WINDOWS) \
                         --build-arg USE_RUST=$(USE_RUST) \
                         -t $(CONTAINER_NAME) .

# --- shell / shell-exec share ONE container invocation, defined here so the two
# targets can never drift. Scoped to this pair ONLY. See runClaudeInContainer
# tasks/add-shell-exec-target.md for the design.
SHELL_RUN_FLAGS = \
		--entrypoint /bin/bash \
		$(FILES_TO_MOUNT) \
		$(X_FLAGS_FOR_CONTAINER) \
		$(WAYLAND_FLAGS_FOR_CONTAINER) \
		-v ./entrypoint/shell.sh:/shell.sh:Z \
		-v ./entrypoint/.bashrc:/root/.bashrc:Z

# In-container repo mount path (matches FILES_TO_MOUNT: -v $(pwd):/$(CONTAINER_NAME)).
REPO_MOUNT = /$(CONTAINER_NAME)

# shell-exec payload: cd to the repo root (independent of shell.sh's own cd), then
# run the inline CMD, else the repo-relative SCRIPT. Prefers CMD when both are set.
SHELL_EXEC_ARGS = -c 'cd $(REPO_MOUNT) && $(if $(CMD),$(CMD),exec bash $(SCRIPT))'

.PHONY: shell
shell:  ## Get Shell into a ephermeral container made from the image
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(SHELL_RUN_FLAGS) $(CONTAINER_NAME) shell.sh

.PHONY: shell-exec
shell-exec: ## Run a script/command in the container env (no TTY): make shell-exec SCRIPT=path | CMD='...'
	@[ -n "$(SCRIPT)$(CMD)" ] || { echo 'usage: make shell-exec SCRIPT=<repo-relative path> | CMD="..."'; exit 2; }
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) --rm $(SHELL_RUN_FLAGS) $(CONTAINER_NAME) shell.sh $(SHELL_EXEC_ARGS)

.PHONY: format
format: image ## Format the Python source with ruff (entrypoint/format.sh)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm \
		--entrypoint /bin/bash \
		$(FILES_TO_MOUNT) \
		$(CONTAINER_NAME) \
		/format.sh

.PHONY: type-check
type-check: image ## Type-check the Python (src + tests) with ty (entrypoint/type-check.sh)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) --rm \
		--entrypoint /bin/bash \
		$(FILES_TO_MOUNT) \
		$(CONTAINER_NAME) \
		/type-check.sh

.PHONY: docs
docs: image ## Build the Sphinx book (html/pdf/epub) into ./output/towersofhanoi/
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) --rm \
		$(FILES_TO_MOUNT) \
		$(CONTAINER_NAME)

.PHONY: image-export
image-export: ## export the OCI image to a timestamped tar in the repo root
	$(CONTAINER_CMD) save $(CONTAINER_NAME) -o $(CONTAINER_NAME)-$(shell date +%m-%d-%Y_%H-%M-%S).tar

.PHONY: image-import
image-import: ## import an OCI image tar: make image-import FILE=foo.tar
	$(CONTAINER_CMD) load -i $(FILE)

# --- Run a front-end (Python and Rust ports, kept in sync) ------------------
# Every target runs in the container, interactively, with X11 + Wayland passthrough
# (the TUI needs a terminal; the wx GUI needs a display). The Python targets install
# the package editable first; the Rust targets need an image built with USE_RUST=1 and use
# rust/.container-target (gitignored) so the heavy first build — wxDragon downloads and
# statically builds wxWidgets 3.3.4 — is cached across runs and never clashes with the host target.
PLAY_FLAGS = --entrypoint /bin/bash $(FILES_TO_MOUNT) \
	$(X_FLAGS_FOR_CONTAINER) $(WAYLAND_FLAGS_FOR_CONTAINER)
PYTHON_SETUP = cd /$(CONTAINER_NAME)/python && uv pip install --system -e . -q
RUST_SETUP = cd /$(CONTAINER_NAME)/rust && export CARGO_TARGET_DIR=/$(CONTAINER_NAME)/rust/.container-target

.PHONY: python-cli
python-cli: image ## Run the Python CLI front-end (hanoi-cli)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(PLAY_FLAGS) $(CONTAINER_NAME) \
		-c '$(PYTHON_SETUP) && exec hanoi-cli'

.PHONY: python-tui
python-tui: image ## Run the Python ncurses TUI front-end (hanoi)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(PLAY_FLAGS) $(CONTAINER_NAME) \
		-c '$(PYTHON_SETUP) && exec hanoi'

.PHONY: python-wx
python-wx: image ## Run the Python wxPython GUI front-end (hanoi-gui)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(PLAY_FLAGS) $(CONTAINER_NAME) \
		-c '$(PYTHON_SETUP) && exec hanoi-gui'

.PHONY: rust-cli
rust-cli: image ## Run the Rust CLI front-end (image needs USE_RUST=1)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(PLAY_FLAGS) $(CONTAINER_NAME) \
		-c '$(RUST_SETUP) && exec cargo run -q -p hanoi-cli'

.PHONY: rust-tui
rust-tui: image ## Run the Rust terminal-UI front-end (image needs USE_RUST=1)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(PLAY_FLAGS) $(CONTAINER_NAME) \
		-c '$(RUST_SETUP) && exec cargo run -q -p hanoi'

.PHONY: rust-wx
rust-wx: image ## Run the Rust wxDragon GUI front-end (image needs USE_RUST=1)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(PLAY_FLAGS) $(CONTAINER_NAME) \
		-c '$(RUST_SETUP) && exec cargo run -q -p hanoi-gui'

.PHONY: help
help:
	@grep --extended-regexp '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
