.DEFAULT_GOAL := help

BUILD_DOCS ?= 1


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




.PHONY: all
all: shell ## Build the image and get a shell in it

.PHONY: image
image: ## Build a $(CONTAINER_CMD)
	$(CONTAINER_CMD) build \
                         --build-arg BUILD_DOCS=$(BUILD_DOCS) \
                         -t $(CONTAINER_NAME) .

# --- shell / shell-exec share ONE container invocation, defined here so the two
# targets can never drift. Scoped to this pair ONLY. See runClaudeInContainer
# tasks/add-shell-exec-target.md for the design.
SHELL_RUN_FLAGS = \
		--entrypoint /bin/bash \
		$(FILES_TO_MOUNT) \
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

.PHONY: help
help:
	@grep --extended-regexp '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
