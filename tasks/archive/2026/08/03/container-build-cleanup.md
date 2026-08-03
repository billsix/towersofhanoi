# Fix container build: docs target + entrypoint output path

**Status:** done — 2026-08-03
**Priority:** 5
**Difficulty:** 2
**Created:** 2026-06-13

## Goal

Repair two defects in hanoi's container plumbing: the `Makefile` `docs:` target
is malformed (no command), and `entrypoint.sh` writes its GitHub-Pages marker to
the wrong project's output directory.

## Plan

- [x] **`docs:` target is a no-op/error.** It ended at `$(CONTAINER_NAME) \`
      with trailing backslashes running into blank lines — no command and no
      entrypoint passed. Its `##` help text was also copy-pasted ("Get Shell into
      a ephermeral container"). **Done:** rewrote the target to run the image's
      default `ENTRYPOINT` (`/entrypoint.sh`, which already builds the book) —
      dropped the shell.sh/.bashrc mounts (only the interactive shell needs
      them), removed `-it` (it is a non-interactive build), dropped the dangling
      `\`, and corrected the description to "Build the Sphinx book
      (html/pdf/epub) into ./output/towersofhanoi/". Confirms the open question:
      `docs` builds the book. `FILES_TO_MOUNT` supplies the source (`/hanoi`) and
      `./output/` mounts the entrypoint needs; `make -n docs` shows it wires to
      `image` then a bare `podman run --rm … hanoi` (default ENTRYPOINT).
- [x] **Wrong-project `.nojekyll`.** `entrypoint.sh:23` did
      `touch /output/modelviewprojection/.nojekyll` (a dir it never `mkdir`s, so
      the touch failed) amid otherwise-correct `/output/towersofhanoi/` paths, so
      hanoi's HTML output never got its `.nojekyll`. **Done:** now
      `touch /output/towersofhanoi/.nojekyll` (that dir is `mkdir -p`'d four lines
      above, so the touch succeeds).

## Notes / decisions

- `BUILD_DOCS` default mismatch (Makefile `1` / Dockerfile `0`) is benign — the
  Makefile always passes the arg explicitly, and it matches the family
  convention. Leave it.

## Open questions

- ~~Confirm `docs:` is meant to build the book (run the entrypoint) rather than
  open a shell~~ — resolved: `docs` builds the book. The copy-pasted help text
  was cloned from `shell:` and never finished; the target now runs the default
  ENTRYPOINT.

## Verification (2026-08-03)

- `make -n docs` — dry-run confirms wiring: `image` dep, then default-ENTRYPOINT
  `podman run`. No real image build run (shared 32G store, parallel agents).
- `make help` parses; the `docs` description renders correctly.
- shellcheck run on all three entrypoint scripts. Only **pre-existing** findings,
  none introduced by this change and all out of scope for this bounded task:
  SC2164 (`cd … || exit`) across entrypoint.sh/shell.sh, SC2035 (`cp -r *`),
  SC2148 (shell.sh has no shebang), SC2103. Left for a separate lint-hardening
  pass, not folded into this container-plumbing fix.
