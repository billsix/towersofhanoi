.DEFAULT_GOAL := help

# The C++ subproject of hanoi: a Dear ImGui GUI over the hanoigame engine, built native
# (`make gui`) and as WebAssembly (`make webassembly`). Self-contained -- own image, own
# emacs set. Kept in sync with the Python canonical source (never a replacement).

# USE_EMACS installs emacs + the C/C++ dev set (clangd). USE_WASM installs the Emscripten
# SDK (for `make webassembly`; heavy). Both on by default; a lean MINIMAL_IMAGE build drops
# them (a small native-only image). EMSDK_VERSION pins the toolchain.
USE_EMACS ?= $(if $(filter 1,$(MINIMAL_IMAGE)),0,1)
USE_WASM ?= $(if $(filter 1,$(MINIMAL_IMAGE)),0,1)
EMSDK_VERSION ?= 3.1.74

CONTAINER_CMD ?= $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)
CONTAINER_NAME = hanoi-cpp

PODMAN_RUN_FLAGS ?= $(if $(filter 1,$(NESTED_PODMAN)),--cgroups=disabled)

TMUX_FILE := $(HOME)/.tmux.conf
TMUX_REAL_PATH := $(shell readlink -f $(TMUX_FILE))
TMUX_MOUNT := $(shell if [ -f $(TMUX_REAL_PATH) ]; then echo "-v $(TMUX_REAL_PATH):/root/.tmux.conf:Z" ; fi)

REPO_MOUNT = /$(CONTAINER_NAME)
FILES_TO_MOUNT = -v $(shell pwd):$(REPO_MOUNT):Z $(TMUX_MOUNT)

# X11 + Wayland passthrough for the native ImGui window (SDL2/OpenGL).
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
image: ## Build the podman image (C++ toolchain + SDL2/GL; emsdk when USE_WASM=1)
	$(CONTAINER_CMD) build \
	                 --build-arg USE_EMACS=$(USE_EMACS) \
	                 --build-arg USE_WASM=$(USE_WASM) \
	                 --build-arg EMSDK_VERSION=$(EMSDK_VERSION) \
	                 -t $(CONTAINER_NAME) .

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
shell-exec: image ## Run a script/command in the container env (no TTY): make shell-exec SCRIPT=path | CMD='...'
	@[ -n "$(SCRIPT)$(CMD)" ] || { echo 'usage: make shell-exec SCRIPT=<repo-relative path> | CMD="..."'; exit 2; }
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) --rm $(SHELL_RUN_FLAGS) $(CONTAINER_NAME) /usr/local/bin/shell.sh $(SHELL_EXEC_ARGS)

.PHONY: format
format: image ## Format the C++ with clang-format (entrypoint/format.sh; never the vendored imgui/)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm \
		--entrypoint /bin/bash $(FILES_TO_MOUNT) $(CONTAINER_NAME) /format.sh

PLAY_FLAGS = --entrypoint /bin/bash $(FILES_TO_MOUNT) \
	$(X_FLAGS_FOR_CONTAINER) $(WAYLAND_FLAGS_FOR_CONTAINER)

.PHONY: gui
gui: image ## Build + run the NATIVE Dear ImGui app (cmake + SDL2/OpenGL, on your display)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm $(PLAY_FLAGS) $(CONTAINER_NAME) \
		-c 'cd $(REPO_MOUNT) && cmake -S . -B build -G Ninja -DCMAKE_EXPORT_COMPILE_COMMANDS=ON && cmake --build build && exec ./build/hanoi-cpp'

.PHONY: webassembly
webassembly: image ## Build the WebAssembly app into ./web/ (needs a USE_WASM=1 image)
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) --rm $(FILES_TO_MOUNT) --entrypoint /bin/bash $(CONTAINER_NAME) \
		-c '. /opt/emsdk/emsdk_env.sh >/dev/null 2>&1 && cd $(REPO_MOUNT) && emcmake cmake -S . -B build-web -DCMAKE_BUILD_TYPE=Release && cmake --build build-web'

.PHONY: serve
serve: webassembly ## Build the wasm (if needed) + serve ./web/ over http at http://localhost:8000
	@echo
	@echo "  Open http://localhost:8000/ in a browser (Ctrl-C to stop the server)."
	@echo
	$(CONTAINER_CMD) run $(PODMAN_RUN_FLAGS) -it --rm -p 8000:8000 $(FILES_TO_MOUNT) --entrypoint /bin/bash $(CONTAINER_NAME) \
		-c 'cd $(REPO_MOUNT) && python3 -m http.server -d web -b 0.0.0.0 8000'

.PHONY: update-imgui
update-imgui: ## Re-vendor Dear ImGui at a ref (overwrites imgui/): make update-imgui IMGUI_REF=v1.92.0
	@[ -n "$(IMGUI_REF)" ] || { echo 'usage: make update-imgui IMGUI_REF=<branch|tag|SHA>'; exit 2; }
	bash tools/update-imgui.sh "$(IMGUI_REF)"

.PHONY: image-export
image-export: ## export the OCI image to a timestamped tar in this dir
	$(CONTAINER_CMD) save $(CONTAINER_NAME) -o $(CONTAINER_NAME)-$(shell date +%m-%d-%Y_%H-%M-%S).tar

.PHONY: image-import
image-import: ## import an OCI image tar: make image-import FILE=foo.tar
	$(CONTAINER_CMD) load -i $(FILE)

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
