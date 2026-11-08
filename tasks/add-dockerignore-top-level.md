# Add a `.dockerignore` to the top-level (docs) image context

Done 2026-11-08 (William Emerison Six <billsix@gmail.com> asked for it), on branch `add-dockerignore`.

## What changed

The top-level `Dockerfile` is built with the repo root as context, which held ~36 GB in ~107,000 files
(`rust/` build output 35 GB, `venv/` 442 MB, `cpp/build*/`). The `Dockerfile` copies only seven small
files. The new root `.dockerignore` is an allowlist: `*`, then `!` for exactly those seven
(`entrypoint/01-install-base.sh`, `02-install-docs.sh`, `.bashrc`, `entrypoint.sh`, `format.sh`,
`type-check.sh`, `python/requirements.txt`). It must be kept in step with the `COPY` lines. The `cpp/`,
`python/` and `rust/` images keep their own contexts and ignore files.

## Verification (2026-11-08, nested podman, a spimulator build running alongside both times)

| fully cached `make image` | run 1 | run 2 |
|---|---|---|
| before (no `.dockerignore`) | 99.7 s | 99.0 s |
| after (allowlist) | 2.6 s | 2.5 s |

After the change all 11 steps after `FROM` were cache hits (the copied files are unchanged), and the
build succeeded. The time went on buildah walking the context's ~107,000 files, not on file size: an
earlier test with one 3 GB file in a context showed no measurable cost. This corrected the Dockerfile
contract's `.dockerignore` bullet (personal overlay, github.com/billsix/dotfiles
`.ai-coding-conventions.personal.md`), which had said context size doesn't matter for local podman.
`make docs` was not re-run: the ignore file affects only `podman build`, not the run targets' bind
mounts.
