# Fix `make type-check`: `os.path.commonprefix` is deprecated on Python 3.15

**Started:** 2026-11-06
**Finished:** 2026-11-06

## Summary

`make type-check` (the CI job `python-type-check`) failed with exit 1 on one `ty` diagnostic:
`os.path.commonprefix` is deprecated since Python 3.15, which the Fedora 45 image ships. The one
call, in the TUI's Tab completion (`_complete_buffer` in `python/src/hanoigame/hanoigame.py`), was
replaced with a small typed helper `_common_prefix`. It sits beside its caller and has a doctest.
The `os.path` import was dropped. `make type-check`, `make test` and `make format` all pass.

## What was found

- Reproduced in a freshly built `hanoi-python` image (ty 0.0.91, Python 3.15.0). `ty check src`
  failed on this one warning; `ty check tests` passed. ty exits nonzero on a warning by default,
  and `python/pyproject.toml` has no `[tool.ty]` section that changes that:

  ```
  warning[deprecated]: The overload of `commonprefix` is deprecated
     --> src/hanoigame/hanoigame.py:401:52
  ... Deprecated since Python 3.15; use os.path.commonpath() for path prefixes.
  ```

- Why it appeared now: `ty` and Python come from unpinned Fedora `dnf` packages
  (`python/entrypoint/01-install-base.sh`), and the Fedora 45 upgrade
  (`tasks/archive/2026/11/05/upgrade-to-fedora-45.md`) brought Python 3.15.
- ty's suggested replacement was not used. `os.path.commonpath()` compares path components, not
  characters. For `["apply", "about"]` it would never return `"a"`, so Tab would stop extending
  partial command words.
- That was the only use in `python/src`. The readline CLI does its own prefix filling, and the
  Rust and C++ ports have their own completion code.

## What changed

- `_common_prefix(words: Sequence[str]) -> str` compares the lexicographically smallest and largest
  words character by character. If any two words differ at some position, those two differ there
  first, so that comparison gives the common prefix of the whole list. A single word returns itself,
  so `_complete_buffer` no longer special-cases one candidate. Its doctest covers `["apply",
  "about"] -> "a"`, a word that is a prefix of another, one word, no shared prefix, and an empty
  list.
- Gates (run 2026-11-06):
  - format: exit 0, no changes.
  - type-check: exit 0, "All checks passed!" for both `src` and `tests`.
  - test: exit 0, 136 passed, 2 skipped. That includes the new doctest
    `hanoigame.py::..._common_prefix` and the four existing `test_complete_buffer_*` tests.

## Notes

- Verifying in a nested sandbox: `make type-check` depends on `image`, and a nested
  `podman build` without `--network=host` fails at network setup (`pasta ... Couldn't open network
  namespace ... Permission denied`). That is a sandbox limit, not a project bug. The image was
  built with `podman build --network=host ...`, and each gate's own `podman run` line was then run
  against it.
