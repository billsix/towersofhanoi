# Dockerfiles: drop the unpinned setuptools install; silence uv's hardlink warning

**Status:** proposed — needs go-ahead
**Priority:** 8
**Difficulty:** 2
**Started:** 2026-11-18 (William Emerison Six <billsix@gmail.com>)

## BLUF

The root `Dockerfile` and `python/Dockerfile` share one pip layer that runs
`uv pip install --system setuptools` (unpinned) and then
`uv pip install --system -r requirements-nowx.txt`. The requirements file pins
`setuptools==82.0.1`, so whenever PyPI's newest setuptools is different, uv installs it and
then swaps it for the pin. The layer runs under a uv cache mount, so uv also warns
"Failed to hardlink files". Neither affects the final image. Done = the separate setuptools
install is gone, `ENV UV_LINK_MODE=copy` is set, and both images build without the warning.

## Context

- This is the same cleanup as github.com/billsix/geometricalgebra
  `tasks/dockerfile-pin-every-venv-install.md`, and the rule is in the Python standard: the
  `python-coding-standard.md` reference doc in github.com/billsix/runClaudeInContainer, under
  "Pin direct dependencies".
- **The hardlink warning:** uv's cache (`RUN --mount=type=cache,target=/root/.cache/uv`) is a
  different filesystem from the image layer, so uv has to copy instead of hardlinking. Copying is
  required anyway (the cache mount is discarded), so `UV_LINK_MODE=copy` just states it.
- **The setuptools install:** `python/requirements.txt` already pins setuptools, and that is the
  version that wins, so the extra unpinned install only adds a download that gets rolled back.
  The other packages are pure-Python wheels, so nothing in the second install needs setuptools
  already present. Confirm that during the build.
- Both Dockerfiles have the same layer: root `Dockerfile` (the book image, which `COPY`s
  `python/requirements.txt`) and `python/Dockerfile`.

## Plan

1. In both Dockerfiles: delete `uv pip install --system setuptools &&` and add
   `ENV UV_LINK_MODE=copy` (with a one-line why) before the pip `RUN`.
2. `make image` at the root and in `python/`. The pip layer shows no hardlink warning and no
   `-`/`+` setuptools pair. Then run each image's test gate.

## Out of scope (noted, not fixed here)

These are differences from the container-template Python rules (the personal overlay's
"Python deps"), not part of this cleanup: hanoi installs with `--system` rather than into a
`/venv`, and has no `constraints.txt`, so transitive deps aren't locked. All eight direct
requirements are pinned exact, so the drift is small. File a separate task if you want those changed.
