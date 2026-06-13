# Fix container build: docs target + entrypoint output path

**Status:** proposed — not started
**Created:** 2026-06-13

## Goal

Repair two defects in hanoi's container plumbing: the `Makefile` `docs:` target
is malformed (no command), and `entrypoint.sh` writes its GitHub-Pages marker to
the wrong project's output directory.

## Plan

- [ ] **`docs:` target is a no-op/error.** It ends at `$(CONTAINER_NAME) \`
      with trailing backslashes running into blank lines — no command and no
      entrypoint passed. Its `##` help text is also copy-pasted ("Get Shell into
      a ephermeral container"). **Fix:** decide what `docs` should do — almost
      certainly just run the image's default `ENTRYPOINT` (`/entrypoint.sh`,
      which already builds the docs) — drop the dangling `\`, and correct the
      `## …` description.
- [ ] **Wrong-project `.nojekyll`.** `entrypoint.sh:23` does
      `touch /output/modelviewprojection/.nojekyll` (a dir it never `mkdir`s, so
      the touch fails) amid otherwise-correct `/output/towersofhanoi/` paths, so
      hanoi's HTML output never gets its `.nojekyll`. **Fix:**
      `touch /output/towersofhanoi/.nojekyll`.

## Notes / decisions

- `BUILD_DOCS` default mismatch (Makefile `1` / Dockerfile `0`) is benign — the
  Makefile always passes the arg explicitly, and it matches the family
  convention. Leave it.

## Open questions

- Confirm `docs:` is meant to build the book (run the entrypoint) rather than
  open a shell — the current copy-pasted help text suggests it was cloned from
  `shell:` and never finished.
