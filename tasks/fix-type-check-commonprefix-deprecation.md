# Fix `make type-check`: `os.path.commonprefix` is deprecated on Python 3.15

**Status:** proposed — needs go-ahead
**Priority:** 2
**Difficulty:** 1
**Started:** 2026-11-06

## BLUF

`make type-check` (the CI job `python-type-check`) fails. `ty` reports one diagnostic:
`os.path.commonprefix` is deprecated since Python 3.15, which the Fedora 45 image now ships. The fix
is to replace that one call in `python/src/hanoigame/hanoigame.py` with a plain string common prefix.
Done means `make type-check` exits 0 and `make test` stays green.

## Context

- **Reproduced 2026-11-06:** in a freshly built `hanoi-python` image (ty 0.0.91, Python 3.15.0),
  `/type-check.sh` exited 1 with the output below. `ty check tests` passed; `ty check src` failed on
  this one warning. ty exits nonzero on a warning by default, and `python/pyproject.toml` has no
  `[tool.ty]` section that changes that.

  ```
  warning[deprecated]: The overload of `commonprefix` is deprecated
     --> src/hanoigame/hanoigame.py:401:52
      |
  401 |         candidates[0] if len(candidates) == 1 else commonprefix(candidates)
      |                                                    ^^^^^^^^^^^^ Deprecated since Python 3.15; use os.path.commonpath() for path prefixes.
  ```

- **Why it appeared now:** `ty` and Python come from Fedora `dnf` packages
  (`python/entrypoint/01-install-base.sh`), not a pin. The Fedora 45 upgrade
  (`tasks/archive/2026/11/05/upgrade-to-fedora-45.md`) brought Python 3.15.
- **The call site:** `_complete` in `python/src/hanoigame/hanoigame.py` (the TUI's Tab completion)
  fills in the longest common prefix of the matching command / recipe names. It is imported at the
  top of that file: `from os.path import commonprefix`.
- **Don't follow ty's hint.** `os.path.commonpath()` compares path components split on `/`, not
  characters. For command names like `["apply", "about"]` it would return `""` or the whole name,
  never `"a"`, so Tab completion would stop extending partial words. This needs a character-wise
  string prefix.
- This is the only use: `rg -n "commonprefix" python/src` finds just the import and line 401.
  The readline CLI (`hanoicli.py`) shares the candidate list via `commands.completions`, but readline
  does its own prefix filling.
- Rust and C++ ports have their own completion code and are unaffected.

## Plan

1. Replace `commonprefix` with a small typed helper, e.g.
   `common_prefix(words: list[str]) -> str`, that compares characters. One way is
   `min`/`max` of the list and the shared leading run of those two strings. Give it a doctest
   (house rule: doctests by default), including the `["apply", "about"] -> "a"` case.
   Put it beside `_complete`, its only caller.
2. Drop the `os.path` import.
3. Gates: `make type-check` exits 0, `make test` green (it collects the new doctest),
   `make format` clean.

## Notes

- Verifying in this nested sandbox: `make type-check` depends on `image`, and a nested
  `podman build` without `--network=host` fails at network setup (`pasta ... Couldn't open network
  namespace ... Permission denied`). That is a sandbox limit, not this bug. On 2026-11-06 the image
  was built with `podman build --network=host ...` and the gate's own `podman run` line was run
  against it.
