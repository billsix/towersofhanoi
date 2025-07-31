.DEFAULT_GOAL := help

PODMAN_CMD = podman
CONTAINER_NAME = hanoi

.PHONY: all
all: clean image html ## Build the HTML and PDF from scratch in Debian Bulleye

.PHONY: image
image: ## Build a $(PODMAN_CMD) image in which to build the book
	$(PODMAN_CMD) build -t $(CONTAINER_NAME) .

.PHONY: shell
shell: image ## Get Shell into a ephermeral container made from the image
	$(PODMAN_CMD) run -it --rm \
		--entrypoint /bin/bash \
		-v ./game:/$(CONTAINER_NAME)/game:Z \
		-v ./bash:/$(CONTAINER_NAME)/bash:Z \
		-v ./entrypoint/shell.sh:/shell.sh:Z \
		-v ./python:/$(CONTAINER_NAME)/python:Z \
		$(CONTAINER_NAME) \
		shell.sh


.PHONY: help
help:
	@grep --extended-regexp '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
