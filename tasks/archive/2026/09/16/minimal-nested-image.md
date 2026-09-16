# Lean image for nested-podman builds — what "minimal" means for hanoi

**Status:** complete
**Completed:** 2026-09-16 — nested lean 1.15 GB vs full 1.94 GB, pytest gate green in the lean image;
staged (maintainer commits). Research done 2026-09-10 (survey of the Dockerfile
+ Makefile from the runClaudeInContainer sandbox). One of the per-project children of
runClaudeInContainer `tasks/minimal-image-for-nested-podman-standard.md` (the convention: every optional-feature build flag defaults to its lean value when
`NESTED_PODMAN=1`); the fleet-wide findings table is runClaudeInContainer `tasks/reference/minimal-nested-images.md`. Created 2026-09-10 at the maintainer's
request (William Emerison Six <billsix@gmail.com>: "go through all of my projects with CLAUDE.md …
research what a minimal nested podman container would be for them").
**Priority:** 5
**Difficulty:** 1

## BLUF

Make `make image` inside a sandbox (which exports `NESTED_PODMAN=1`) build a lean image that fits
the nested RAM store and still runs this project's gate, while a host `make image` stays
byte-identical — via the idiom `FLAG ?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)` on each optional-feature flag (the `PODMAN_RUN_FLAGS`
pattern applied to build flags; reference implementation: runCrushInContainer `client/Makefile`,
`FULL_TOOLCHAIN`). Done = the flags below carry the nested-aware default, a nested `make image`
builds and passes the gate, both image sizes are measured and recorded here and in `CLAUDE.md`.

## Context — read first

- runClaudeInContainer `tasks/reference/minimal-nested-images.md` — the standard, the idiom, the rules (a project's *gates* and *product build deps* are never
  trimmed; only editors, docs toolchains, notebooks, GUI extras), and every project's row.
- This repo's `Dockerfile`, `Makefile` (flag block + `image` target), `entrypoint/*install*.sh`.
- The flag-coverage rule (cross-project `CLAUDE.md` › "Verification gates in nested containers"): a
  lean build verifies nothing about the layers it skips — when a change touches what a skipped layer
  consumes, build with that flag ON.

## Findings (2026-09-10)

**What the image installs today.** Flag `BUILD_DOCS` (1) gates `02-install-docs.sh` (aspell, latexmk, mathjax, sphinx + TeX — 13 pkgs). `01-install-base.sh` is 10 small packages (python3, ruff, pytest, wxpython…). The pip layer installs `requirements.txt` minus wxpython.

**What "minimal" is here.** `BUILD_DOCS` → 0 when nested; nothing else to cut.

**Notes.** The docs build is the only heavy path; `make docs` needs `BUILD_DOCS=1` nested (flag-coverage rule).

## Plan

- [x] Makefile: `BUILD_DOCS ?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)` (with an explaining comment).
      Verified `make -n image` emits `--build-arg BUILD_DOCS=0` nested; host build unchanged (1).
- [x] Measure both images; one line in `CLAUDE.md`.
- [x] Record both sizes (host full vs nested lean) here and in `CLAUDE.md`; added the one-line rule to
      `CLAUDE.md` ("nested = lean image automatically; `BUILD_DOCS=1` overrides").

## Result (2026-09-16)

Built both images nested (`/dev/fuse` present, `NESTED_PODMAN=1`):

| Build | Flag | Size |
|-------|------|------|
| Full (host default) | `BUILD_DOCS=1` | 1.94 GB |
| Lean (nested default) | `BUILD_DOCS=0` | 1.15 GB |

Saving ≈ 0.79 GB (~41%), all from dropping the Sphinx + TeX Live docs toolchain (`02-install-docs.sh`).
The base + pip layers (python3, ruff, pytest, wxpython, requirements) are shared, so nothing the code
gate needs was trimmed. **Gate verified in the lean image:** `pytest --exitfirst` → 128 passed
(flag-coverage rule satisfied — the change touches only the Makefile flag default, not anything the
docs toolchain consumes). The image `ENTRYPOINT` still runs docs unconditionally after pytest, so a
default `make docs`/entrypoint run on a lean image fails at `make html` by design — use
`make docs BUILD_DOCS=1` (or a host build) for the book.

Files: `Makefile` (flag default), `CLAUDE.md` (rule + sizes; also corrected stale test count 124→128).

## Open questions

None — the standard's decisions (dnf-only, gates never trimmed) were the maintainer's on 2026-09-10;
anything project-specific to decide is flagged inline above.
