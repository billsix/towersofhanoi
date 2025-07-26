.DEFAULT_GOAL := help

.PHONY: all
all: clean image html ## Build the HTML and PDF from scratch in Debian Bulleye

.PHONY: image
image: ## Build a Podman image in which to build the book
	podman build -t hanoi .

.PHONY: shell
shell: image ## Get Shell into a ephermeral container made from the image
	podman run -it --rm \
		--entrypoint /bin/bash \
		-v ./game:/hanoi/game:Z \
		-v ./bash:/hanoi/bash:Z \
		-v ./python:/hanoi/python:Z \
		hanoi \
		-c "cd /hanoi/game;  python3 -m pip install -e .  --root-user-action=ignore ; exec bash"


.PHONY: help
help:
	@grep --extended-regexp '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
