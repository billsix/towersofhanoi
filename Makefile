.DEFAULT_GOAL := help

BUILD_DOCS ?= 1


CONTAINER_CMD = podman
CONTAINER_NAME = hanoi
FILES_TO_MOUNT = -v $(shell pwd):/$(CONTAINER_NAME):Z
#                 -v ./bash:/$(CONTAINER_NAME)/bash:Z \
#		 -v ./python:/$(CONTAINER_NAME)/python:Z


.PHONY: all
all: shell ## Build the image and get a shell in it

.PHONY: image
image: ## Build a $(CONTAINER_CMD)
	$(CONTAINER_CMD) build \
                         --build-arg BUILD_DOCS=$(BUILD_DOCS) \
                         -t $(CONTAINER_NAME) .

.PHONY: shell
shell:  image ## Get Shell into a ephermeral container made from the image
	$(CONTAINER_CMD) run -it --rm \
		--entrypoint /bin/bash \
		$(FILES_TO_MOUNT) \
		-v ./entrypoint/shell.sh:/shell.sh:Z \
		-v ./entrypoint/.bashrc:/root/.bashrc:Z \
		$(CONTAINER_NAME) \
		shell.sh


.PHONY: help
help:
	@grep --extended-regexp '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
