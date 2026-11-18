# Dockerfiles: drop the unpinned setuptools install; silence uv's hardlink warning (done)

**Done:** 2026-11-18 (William Emerison Six <billsix@gmail.com>)

The root `Dockerfile` (book image) and `python/Dockerfile` each ran
`uv pip install --system setuptools` (unpinned) before
`uv pip install --system -r requirements-nowx.txt`, which pins `setuptools==82.0.1`, so any newer
setuptools was installed and then swapped for the pin. The separate install was removed from both,
and each got `ENV UV_LINK_MODE=copy` before its pip `RUN`. The uv cache mount is a different
filesystem from the image layer, so uv has to copy instead of hardlinking, and it printed "Failed to
hardlink files" until the setting said so. The rule is in the `python-coding-standard.md` reference
doc in github.com/billsix/runClaudeInContainer ("Pin direct dependencies").

Verified nested on 2026-11-18:
- `python/`: `make image` installed each pin once (setuptools 82.0.1 among them) with no hardlink
  warning, and the build-time `--no-build-isolation -e` install of hanoigame still found setuptools.
  `make test` gave 136 passed, 2 skipped, and `make type-check` was clean.
- Root: `make image` (same result) and `make docs` (HTML/PDF/EPUB built). Its 3 warnings, the missing
  `_static` and an empty EPUB `version`, are about the book's config, not this change.

Out of scope and not changed: hanoi installs with `--system` rather than into a `/venv`, and has no
`constraints.txt`, so transitive deps aren't locked (all eight direct requirements are pinned exact).
