# Add a `.dockerignore` to the top-level (docs) image context

**Status:** proposed — needs go-ahead. Created 2026-11-08 (William Emerison Six <billsix@gmail.com>).
**Priority:** 7
**Difficulty:** 1

## BLUF

The top-level `Dockerfile` is built with the repo root as context (`podman build … -t hanoi .`), and that
root holds about 36 GB: `rust/` build output (35 GB), `venv/` (442 MB), `cpp/build*/`. The `Dockerfile`
only copies a few named files (`entrypoint/*.sh`, `entrypoint/.bashrc`, `python/requirements.txt`).
`cpp/`, `python/`, `rust/` already have their own `.dockerignore`, but the root does not. Add an
allowlist ignore file (`*` then `!` exceptions for exactly those files). Done = `make image` succeeds and
the ignore file lists only what the `Dockerfile` copies.

## Context

- Dockerfile contract, `.dockerignore` bullet: the personal overlay (github.com/billsix/dotfiles
  `.ai-coding-conventions.personal.md`).
- Measured 2026-11-08 in the sandbox: under local podman, a 3 GB file in the context added ~1 s or less
  to a build that copies one small file (podman reads the context directory in place instead of
  uploading it). So the gain here is for Docker / `podman --remote` / CI builders that upload the whole
  context, plus protection against a future `COPY .`. That is why this is low priority. Step 1 measures
  the real effect for this repo.

## Plan

1. Time `make image` once before the change (warm cache) and once after. Record both here.
2. Add `.dockerignore`:
   ```
   *
   !entrypoint/
   !python/requirements.txt
   ```
   (Exact list from the `Dockerfile`'s `COPY` lines at the time of the change.)
3. `make image` succeeds; `make docs` (or the doc target) still builds.
