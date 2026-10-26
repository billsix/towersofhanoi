# Python ncurses TUI: add Tab-completion to the prompt (the CLI has it, the TUI doesn't)

**Status:** DONE 2026-10-26 (William Emerison Six <billsix@gmail.com>). Gate green in-container.
**Priority:** 5 **Difficulty:** 3
**Created:** 2026-10-25. Filed from on-screen feedback that the Rust TUI lacked autocomplete; checking
the oracle showed the Python ncurses TUI lacked it too (feature-spec §6.1 requires completion of TUIs,
not just the readline CLI).

## BLUF

The Python ncurses TUI's hand-rolled `getch` input loop now has Tab-completion, matching the readline
CLI and feature-spec §6.1: command verbs on the first token, saved-recipe names after `apply `/`show `.
The candidate logic is shared with the CLI (one pure helper) so the two front-ends can't drift.

## What was done (2026-10-26)

- **`commands.completions(buffer, text, names)`** — new pure helper holding the candidate logic
  (verbs on the first token; recipe `names` after `apply `/`show `; nothing after `save ` or once
  past the first token). Lifted out of `hanoicli._completions`; it is exactly the signature
  feature-spec §6.1 prescribes.
- **`hanoicli._completions`** — now a thin readline-side adapter that supplies `registry.names()` to
  `commands.completions`. The CLI's behaviour and its existing tests are unchanged.
- **`hanoigame.py`** — `_read_line` gained an optional `registry`; the command prompt passes it, so
  Tab there completes the current token via the new pure `_complete_buffer(buffer, names)` helper
  (single candidate fills fully; several fill the longest common prefix via `os.path.commonprefix`;
  none is a no-op). The disc-count / save-name / play-again prompts pass no registry, so Tab stays
  inert there. Tab is key `9`, handled before the printable-char branch.
- **Tests** — `test_commands.py::test_completions_*` (the shared helper) and new
  `test_hanoigame.py::test_complete_buffer_*` (the TUI fill rule: full / common-prefix / no-op).

## Decisions / judgment calls

- **Shared helper lives in `commands.py`, takes `names` (not a registry)** — matches the Rust
  precedent (`commands.rs::completions`) and keeps `commands.py` pure (no recipe-store dependency).
  The CLI keeps its `_completions(…, registry)` adapter so its tests/interface don't churn.
- **`_complete_buffer` is a separate pure helper in `hanoigame.py`** so the Tab behaviour is
  unit-testable without a curses window (the `getch` loop itself can't be driven headlessly).
- **Fixed a pre-existing ty-deprecation in the same file** (not part of the feature): `stdscr_attr`'s
  `@contextmanager` return annotation `Iterator[None]` → `Generator[None, None, None]`. `ty check src`
  (image Python 3.14 / current ty) flags the `Iterator` form, so `make type-check` was **already red
  on master** before this work; the one-line change restores a green gate. Flagged to the maintainer.

## Gate / verify (passed, hanoi-python nested)

135 passed / 2 skipped; `ruff check` + `ruff format --check` clean; `ty check src` + `ty check tests`
clean. The wx/TUI on-screen behaviour (pressing Tab) is the maintainer's on-display confirmation, but
the completion + fill logic is covered by the pure-helper tests.

## Related

- Oracle: `python/src/hanoigame/{hanoigame.py,hanoicli.py,commands.py}`.
- Spec: `tasks/reference/feature-spec.md` §6.1 (already prescribes the `completions(buffer, text,
  names)` helper this implements). Rust precedent: `rust/hanoigame/src/commands.rs` (`completions`) +
  `rust/hanoi/src/main.rs` (`complete_line`).
