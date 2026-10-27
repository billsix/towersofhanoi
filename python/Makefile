.DEFAULT_GOAL := help

# The Python subproject of hanoi: the hanoigame package + its three front-ends
# (hanoi-cli / hanoi / hanoi-gui). Self-contained -- own image, own emacs set.

# USE_X_WINDOWS installs the X11/Wayland client libs (03-install-xwindows.sh) so the
# wxPython GUI (hanoi-gui) can open a window. On by default; a lean MINIMAL_IMAGE build
# (make image MINIMAL_IMAGE=1) drops it, for a small export/airgap image. Override:
# make image USE_X_WINDOWS=0. (MINIMAL_IMAGE is image CONTENT, independent of
# NESTED_PODMAN run capability -- the sandbox does not set it, so a nested build is full.)
USE_X_WINDOWS ?= $(if $(filter 1,$(MINIMAL_IMAGE)),0,1)
# USE_EMACS installs emacs + the vendored Python dev set (lsp-pyright over pyright).
# On by default; MINIMAL_IMAGE=1 drops it. To refresh the vendored elpa packages:
# make update-emacs-packages.
USE_EMACS ?= $(if $(filter 1,$(MINIMAL_IMAGE)),0,1)

CONTAINER_CMD ?= $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)
CONTAINER_NAME = hanoi-python

# Extra flags for every container `run`. Auto-set when running nested inside a
# runClaudeInContainer/runCrushInContainer sandbox (NESTED_PODMAN=1 -> --cgroups=disabled
# so podman-in-podman works); empty on a normal host. On `run` lines only, never `build`.
PODMAN_RUN_FLAGS ?= $(if $(filter 1,$(NESTED_PODMAN)),--cgroups=disabled)

TMUX_FILE := $(HOME)/.tmux.conf
TMUX_REAL_PATH := $(shell readlink -f $(TMUX_FILE))
TMUX_MOUNT := $(shell if [ -f $(TMUX_REAL_PATH) ]; then echo "-v $(TMUX_REAL_PATH):/root/.tmux.conf:Z" ; fi)

# In-container mount path for this subproject (shell.sh cds here).
REPO_MOUNT = /$(CONTAINER_NAME)
# hanoi.xrc is now a git-tracked symlink -> ../../../ui/hanoi.xrc (the one true file lives at
# the repo-root ui/, shared with the C++ wx front-end). Mount ui/ at /ui so the symlink
# resolves inside the container: /hanoi-python/src/hanoigame/hanoi.xrc -> ../../../ui/hanoi.xrc
# lands on /ui/hanoi.xrc. Without this the wxPython GUI can't load its layout.
# See hanoi tasks/cpp-add-wx-frontend-and-recipe-view-parity.md Decision 1.
UI_MOUNT = -v $(shell pwd)/../ui:/ui:Z
FILES_TO_MOUNT = -v $(shell pwd):$(REPO_MOUNT):Z $(UI_MOUNT) $(TMUX_MOUNT)

# X11 display passthrough for the wxPython GUI (hanoi-gui). The security-opt label lets
# the container talk to the host X server under SELinux.
X_FLAGS_FOR_CONTAINER = -e DISPLAY=$(DISPLAY) \
	-v /tmp/.X11-unix:/tmp/.X11-unix \
	--security-opt label=type:container_runtime_t
DRI_DEVICE := $(shell [ -d /dev/dri ] && echo "--device /dev/dri")
WAYLAND_FLAGS_FOR_CONTAINER = -e "XDG_SESSION_TYPE=wayland" \
			      -e "WAYLAND_DISPLAY=$(WAYLAND_DISPLAY)" \
			      -e "XDG_RUNTIME_DIR=$(XDG_RUNTIME_DIR)" \
			      -v "$(XDG_RUNTIME_DIR):$(XDG_RUNTIME_DIR)" \
			      $(DRI_DEVICE)

# USE_EMACS=1 (default) bind-mounts the vendored .emacs.d/ so an interactive `make shell`
# uses the committed packages (:U chowns to the container user, :z relabels for SELinux).
# Refresh the elpa tree with `make update-emacs-packages`.
ifeq ($(USE_EMACS), 1)
  ELPA_MOUNT = -v $(CURDIR)/entrypoint/dotfiles/.emacs.d/:/root/.emacs.d/:U,z
else
  ELPA_MOUNT =
endif

.PHONY: all
all: shell ## Build the image and get a shell in it

.PHONY: image
image: ## Build the podman image (hanoigame package + deps baked in)
	$(CONTAINER_CMD) build \
	                 --build-arg USE_X_WINDOWS=$(USE_X_WINDOWS) \
	                 --build-arg USE_EMACS=$(USE_EMACS) \
	                 -t $(CONTAINER_NAME) .

# --- shell / shell-exec share ONE invocation so they can never drift (scoped to this
# pair only). shell.sh re-installs the package editable from the mount, so host edits win.
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
format: image ## Format the Python source with ruff (entrypoint/format.sh)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm \
		--entrypoint /bin/bash $(FILES_TO_MOUNT) $(CONTAINER_NAME) /format.sh

.PHONY: test
test: image ## Run the test suite (pytest, incl. doctests via --doctest-modules) in the container
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) --rm \
		--entrypoint /bin/bash $(FILES_TO_MOUNT) $(CONTAINER_NAME) \
		-c 'cd $(REPO_MOUNT) && python -m pytest'

.PHONY: type-check
type-check: image ## Type-check the Python (src + tests) with ty (entrypoint/type-check.sh)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) --rm \
		--entrypoint /bin/bash $(FILES_TO_MOUNT) $(CONTAINER_NAME) /type-check.sh

# --- Run a front-end. Interactive, with X11 + Wayland passthrough (the TUI needs a
# terminal; the wx GUI needs a display). The package is baked in and re-installed from
# the mount so host edits propagate.
PLAY_FLAGS = --entrypoint /bin/bash $(FILES_TO_MOUNT) \
	$(X_FLAGS_FOR_CONTAINER) $(WAYLAND_FLAGS_FOR_CONTAINER)
PYTHON_SETUP = cd $(REPO_MOUNT) && uv pip install --no-deps --no-index --no-build-isolation --system -e . -q

.PHONY: cli
cli: image ## Run the CLI front-end (hanoi-cli)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(PLAY_FLAGS) $(CONTAINER_NAME) \
		-c '$(PYTHON_SETUP) && exec hanoi-cli'

.PHONY: tui
tui: image ## Run the ncurses TUI front-end (hanoi)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(PLAY_FLAGS) $(CONTAINER_NAME) \
		-c '$(PYTHON_SETUP) && exec hanoi'

.PHONY: wx
wx: image ## Run the wxPython GUI front-end (hanoi-gui)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(PLAY_FLAGS) $(CONTAINER_NAME) \
		-c '$(PYTHON_SETUP) && exec hanoi-gui'

.PHONY: image-export
image-export: ## export the OCI image to a timestamped tar in this dir
	$(CONTAINER_CMD) save $(CONTAINER_NAME) -o $(CONTAINER_NAME)-$(shell date +%m-%d-%Y_%H-%M-%S).tar

.PHONY: image-import
image-import: ## import an OCI image tar: make image-import FILE=foo.tar
	$(CONTAINER_CMD) load -i $(FILE)

# Refresh the vendored Emacs packages: force USE_EMACS=1, rebuild, wipe + reinstall ONLY
# the elpa/ subtree into the host-mounted .emacs.d/elpa, strip compiled *.elc/*.eln, and
# force-stage the tree. Needs network.
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
