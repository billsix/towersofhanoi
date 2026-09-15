# Add a `make type-check` target (ty)

**Status:** complete (2026-09-15) — `make type-check` runs `ty` over `src` + `tests`
in-container; exit 0 when clean, non-zero on any diagnostic. Implemented alongside the
`type-dataclass-docstring-all-python` task so that task's gate now exists. See "Outcome".
**Priority:** 4
**Difficulty:** 2

## Outcome (2026-09-15)

- **`entrypoint/type-check.sh`** — portable + accumulating: `[ -d /hanoi/python ] && cd
  /hanoi/python` (no-ops on host), then `status=0; ty check src || status=1; ty check tests ||
  status=1; exit $status`. No `ty` install was needed (already in `01-install-base.sh`) and no
  venv guard (hanoi installs `--system`, not into a venv; `ty` resolves the package itself).
- **`Dockerfile`** — one line, `COPY entrypoint/type-check.sh /`, mirroring `format.sh` (baked,
  run as `bash /type-check.sh`).
- **`Makefile`** — a `.PHONY: type-check` target (`## `-documented, `type-check: image`) shaped
  like `format` but **without `-it`** (a gate must run in a non-TTY / nested / CI context),
  threading `$(PODMAN_RUN_FLAGS)` on the `run` line (never `build`) and mounting the source via
  `$(FILES_TO_MOUNT)`.
- **Decision (the one the plan flagged):** kept `type-check` **separate** from `format` rather
  than folding `ty` into `format.sh` — keeps `make format` fast, and matches the standard's "the
  agent doesn't over-wire gates." A combined `check` target can be added later if wanted.
- **Verified** (nested, `BUILD_DOCS=0` image): clean tree → both `ty check` steps run
  ("All checks passed!" twice), `make type-check` exit **0**; a planted `-> int` returning a
  `str` in `tests/` → `ty` `invalid-return-type`, `make type-check` exit **2** (proving the
  tests step runs and its failure propagates). Probe reverted.

## BLUF

Add a `make type-check` target that runs **ty** over the Python (`src`, and `tests`) inside the
container, mirroring the existing `make format` gate. `ty` is **already installed** in the image
(`entrypoint/01-install-base.sh:35`), so this is very likely a Makefile + small entrypoint-script
change with **no Dockerfile edit needed** — confirm that first (the maintainer flagged it "may
require adding things to the dockerfile"). "Done" = `make type-check` builds/uses the image and runs
`ty`, failing the build on any diagnostic.

## Context — read first

- **Current gate:** `make format` (`Makefile:64`) → `entrypoint/format.sh` runs `ruff check --fix`
  + `ruff format` in-container (source bind-mounted). There is **no** type-check target, and
  `format.sh` does **not** run `ty` today (ty is installed but unused by the gate).
- **ty is present:** `entrypoint/01-install-base.sh` installs it (~line 35). Verify in the image:
  `make shell` then `command -v ty` (or `make shell-exec CMD='command -v ty'`). Only touch the
  Dockerfile/install script if it's somehow absent.
- **Shell-script conventions** (`~/.claude/reference/` shell-and-gate docs, and the cross-project
  standard): a gate script must (1) run **every** step and accumulate failure
  (`status=0; ty … || status=1; … exit $status`), not fail-fast; (2) be **portable** — guard any
  `source /venv/bin/activate`, use **relative** paths (`ty check src`, `ty check tests`) and let the
  caller `cd` to the repo root, so it runs in-container *and* on the host from `python/`.
- **Where the code lives:** the package is under `python/` (`python/src/hanoigame`, `python/tests`),
  so the check runs from `python/` — mirror how `format` handles the working dir.

## Plan

- [ ] Add `entrypoint/type-check.sh` (portable, accumulating): `ty check src || status=1; ty check
      tests || status=1; exit $status`, run from the repo's `python/` dir.
- [ ] Add a `.PHONY: type-check` Makefile target with a `## ` help line, shaped like `format:` —
      `type-check: image` then `$(CONTAINER_CMD) run … $(PODMAN_RUN_FLAGS) … $(CONTAINER_NAME)
      <type-check.sh>` with the source bind-mounted. Thread `PODMAN_RUN_FLAGS` (never on `build`).
- [ ] **Decision to surface:** keep `type-check` separate, OR also fold `ty` into `format.sh` so one
      gate does both? Propose; don't silently rewire (the standard: the agent doesn't over-wire gates).
      Recommend a separate `type-check` target now (keeps `format` fast), addable to a combined
      `check` later.
- [ ] Verify: `make type-check` runs ty in-container and its exit status reflects ty's result (green
      when clean, non-zero on a planted error).

## Notes

- Pairs with `tasks/type-dataclass-docstring-all-python.md`: that task's "done" is *this* gate green.
  Land this target first so that task has something to check against.

## Related

- `Makefile` (`format`, `shell`, `PODMAN_RUN_FLAGS`), `entrypoint/format.sh`,
  `entrypoint/01-install-base.sh` (ty install).
- `tasks/type-dataclass-docstring-all-python.md`.
