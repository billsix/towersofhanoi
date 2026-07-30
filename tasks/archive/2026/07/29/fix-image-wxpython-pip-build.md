# `make image` is broken: pip tries to source-build wxPython

**Status:** DONE 2026-07-29 — Bill approved; the Dockerfile now filters wxPython
out of the pip install (dnf's `python3-wxpython4` owns it). Verified: `make image`
completes and the format gate runs (found 17 pre-existing ruff errors — separate
issue, not tracked by this task).

## The failure

`make image` fails at the requirements step:

```
RUN uv pip install --system -r /requirements.txt
...
configure: error: no acceptable C compiler found in $PATH
buildtools.builder.BuildError: Error running configure   (wxPython build)
```

`python/requirements.txt` pins `wxPython==4.2.5`, so pip attempts a from-source
build of wxPython inside an image that (correctly) ships no C toolchain — while
`python3-wxpython4` is **already installed via dnf** (Dockerfile line ~20). This
is the exact copy-paste drift the container-template conventions warn about;
modelviewprojection's Dockerfile solves it with the `grep -v wxpython` idiom
(dnf owns the heavy native dep; pip installs the rest).

## The fix (one line in the Dockerfile)

```dockerfile
RUN  uv pip install --system setuptools && \
     grep -v -i wxpython /requirements.txt > /requirements-nopwx.txt && \
     uv pip install --system -r /requirements-nopwx.txt && \
     rm /requirements.txt /requirements-nopwx.txt
```

(Or drop the `wxPython==4.2.5` line from `python/requirements.txt` if pip
installs outside the container aren't a use case — decide which file is the
source of truth; mvp chose to keep the requirement listed and filter it in the
Dockerfile only.)

## Verification

`make image` completes; then `make format` runs (its `format.sh` gained
fail-propagation on 2026-07-29 and has NOT yet been exercised in this repo's
own container — this task unblocks that).
