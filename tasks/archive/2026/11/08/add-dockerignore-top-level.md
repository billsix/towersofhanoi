# Add a `.dockerignore` to the top-level (docs) image context

Done 2026-11-08 (William Emerison Six <billsix@gmail.com> asked for it), on branch `add-dockerignore`.

## What changed

The top-level `Dockerfile` is built with the repo root as context, which held ~36 GB in ~107,000 files
(`rust/` build output 35 GB, `venv/` 442 MB, `cpp/build*/`). The `Dockerfile` copies only seven small
files. The new root `.dockerignore` is an allowlist: `*`, then `!` for exactly those seven
(`entrypoint/01-install-base.sh`, `02-install-docs.sh`, `.bashrc`, `entrypoint.sh`, `format.sh`,
`type-check.sh`, `python/requirements.txt`). It must be kept in step with the `COPY` lines. The `cpp/`,
`python/` and `rust/` images keep their own contexts and ignore files.

## Verification (2026-11-08, nested podman)

`make image` succeeded with the allowlist, all 11 steps after `FROM` cache hits.

The change has **no measurable effect on local podman build time**. Fully cached builds, with nothing
else running: 2.0 s with the allowlist, 2.0 s with `--ignorefile /dev/null`, 2.1 s with the file
removed. Local `podman build` reads the context in place and only checksums the paths a `COPY` names.
The benefit is for builders that upload the whole context (Docker/BuildKit, `podman --remote`, CI), and
it protects against a future `COPY .` of the 36 GB root.

An earlier measurement (99 s before, 2.6 s after) was wrong. During the "before" runs a spimulator
image build was committing layers and holding podman's storage lock; during the "after" runs it was
compiling. Timing builds while another build runs measures the lock, not the change.
