.DEFAULT_GOAL := help

# Root of hanoi (github.com/billsix/towersofhanoi). After the per-language split this is
# the UMBRELLA + the book/workbook/bash layer: it builds the Sphinx book and holds the
# cross-language docs. Each LANGUAGE is a self-contained subproject with its own image and
# Makefile -- build/run those from their own dirs:
#
#     cd python && make        # hanoigame package: make cli | tui | wx | format | type-check
#     cd rust   && make        # Cargo workspace:   make cli | tui | wx | tauri | format
#
# BUILD_DOCS gates the heavy Sphinx + TeX Live docs toolchain (02-install-docs.sh). The
# book IS this layer, so it is on by default; MINIMAL_IMAGE=1 drops it for a lean image.
BUILD_DOCS ?= $(if $(filter 1,$(MINIMAL_IMAGE)),0,1)

TMUX_FILE := $(HOME)/.tmux.conf
TMUX_REAL_PATH := $(shell readlink -f $(TMUX_FILE))
TMUX_MOUNT := $(shell if [ -f $(TMUX_REAL_PATH) ]; then echo "-v $(TMUX_REAL_PATH):/root/.tmux.conf:Z" ; fi)

CONTAINER_CMD ?= $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)
CONTAINER_NAME = hanoi

# Extra flags for every container `run`. Auto-set when running nested (NESTED_PODMAN=1
# -> --cgroups=disabled); empty on a normal host. On `run` lines only, never `build`.
PODMAN_RUN_FLAGS ?= $(if $(filter 1,$(NESTED_PODMAN)),--cgroups=disabled)
FILES_TO_MOUNT = -v $(shell pwd):/$(CONTAINER_NAME):Z \
		 -v ./output/:/output/:Z \
		 $(TMUX_MOUNT)

REPO_MOUNT = /$(CONTAINER_NAME)

.PHONY: all
all: help ## Show the help (the book is `make docs`; languages live in python/ and rust/)

.PHONY: image
image: ## Build the book image (base + the Sphinx/TeX docs toolchain)
	$(CONTAINER_CMD) build --build-arg BUILD_DOCS=$(BUILD_DOCS) -t $(CONTAINER_NAME) .

# --- shell / shell-exec share ONE invocation so they can never drift (scoped to this pair).
SHELL_RUN_FLAGS = \
		--entrypoint /bin/bash \
		$(FILES_TO_MOUNT) \
		-v ./entrypoint/shell.sh:/shell.sh:Z \
		-v ./entrypoint/.bashrc:/root/.bashrc:Z

SHELL_EXEC_ARGS = -c 'cd $(REPO_MOUNT) && $(if $(CMD),$(CMD),exec bash $(SCRIPT))'

.PHONY: shell
shell: ## Get a shell in the book image (for working on docs/ and workbook/)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(SHELL_RUN_FLAGS) $(CONTAINER_NAME) shell.sh

.PHONY: shell-exec
shell-exec: image ## Run a script/command in the book env (no TTY): make shell-exec SCRIPT=path | CMD='...'
	@[ -n "$(SCRIPT)$(CMD)" ] || { echo 'usage: make shell-exec SCRIPT=<repo-relative path> | CMD="..."'; exit 2; }
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) --rm $(SHELL_RUN_FLAGS) $(CONTAINER_NAME) shell.sh $(SHELL_EXEC_ARGS)

.PHONY: docs
docs: image ## Build the Sphinx book (html/pdf/epub) into ./output/towersofhanoi/
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) --rm \
		$(FILES_TO_MOUNT) \
		$(CONTAINER_NAME)

# --- Umbrella delegation to the language subprojects (convenience; each also runs
# standalone from its own dir). These rebuild the subproject's own image as needed.
.PHONY: format
format: ## Format the Python source (delegates to python/; rust/ has its own `make format`)
	$(MAKE) -C python format

.PHONY: type-check
type-check: ## Type-check the Python (delegates to the python/ subproject)
	$(MAKE) -C python type-check

.PHONY: image-export
image-export: ## export the book OCI image to a timestamped tar in the repo root
	$(CONTAINER_CMD) save $(CONTAINER_NAME) -o $(CONTAINER_NAME)-$(shell date +%m-%d-%Y_%H-%M-%S).tar

.PHONY: image-import
image-import: ## import an OCI image tar: make image-import FILE=foo.tar
	$(CONTAINER_CMD) load -i $(FILE)

.PHONY: help
help:
	@grep --extended-regexp '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@printf '\nLanguage subprojects (own image + Makefile):\n  cd python && make   # cli | tui | wx | format | type-check\n  cd rust   && make   # cli | tui | wx | tauri | format\n'
