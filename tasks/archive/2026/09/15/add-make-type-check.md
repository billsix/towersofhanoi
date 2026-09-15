# Add a `make type-check` target (ty)

**Status:** complete (2026-09-15) — `make type-check` runs `ty` over `src` + `tests`
in-container; exit 0 when clean, non-zero on any diagnostic. Implemented alongside the
`type-dataclass-docstring-all-python` task so that task's gate now exists.
**Priority:** 4
**Difficulty:** 2

## What this was

A dedicated `make type-check` gate that runs `ty` (Astral) over the Python, mirroring the
existing `make format` (ruff) gate. `ty` was already in the base image, so the work was a small
entrypoint script + a one-line Dockerfile `COPY` + a Makefile target. (The original guess that
no Dockerfile edit would be needed was wrong: `format.sh` is *baked* into the image, not mounted,
so the new script had to be `COPY`ed the same way.)

## What was done

- **`entrypoint/type-check.sh`** — portable + accumulating: `[ -d /hanoi/python ] && cd
  /hanoi/python` (no-ops on the host), then `status=0; ty check src || status=1; ty check tests ||
  status=1; exit $status`. No venv guard — hanoi installs `--system`, not into a venv, and `ty`
  resolves the package itself.
- **`Dockerfile`** — `COPY entrypoint/type-check.sh /`, mirroring `format.sh` (baked, run as
  `bash /type-check.sh`).
- **`Makefile`** — a `## `-documented `.PHONY: type-check` target (`type-check: image`) shaped
  like `format` but **without `-it`** (a gate must run headless / nested / in CI), threading
  `$(PODMAN_RUN_FLAGS)` on the `run` line only (never `build`) and mounting the source via
  `$(FILES_TO_MOUNT)`.
- **Decision the plan flagged:** kept `type-check` **separate** from `format` rather than folding
  `ty` into `format.sh` — keeps `make format` fast and matches "the agent doesn't over-wire
  gates." A combined `check` target could be added later.

## Verification

Nested, `BUILD_DOCS=0` image: on a clean tree both `ty check` steps run ("All checks passed!"
twice) and `make type-check` exits **0**; a planted `-> int` function returning a `str` in
`tests/` produced `ty`'s `invalid-return-type` and `make type-check` exited **2** — proving the
`tests` step runs and its failure propagates through the accumulate + `exit $status`. Probe
reverted.

## Related

- `Makefile` (`type-check`, `format`, `PODMAN_RUN_FLAGS`), `entrypoint/type-check.sh`,
  `entrypoint/format.sh`, `Dockerfile`.
- `tasks/archive/2026/09/15/type-dataclass-docstring-all-python.md` — the task whose gate this is.
- `tasks/reference/architecture-overview.md` — "Typing, docstrings & the type-check gate".
