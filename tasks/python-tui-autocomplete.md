# Python ncurses TUI: add Tab-completion to the prompt (the CLI has it, the TUI doesn't)

**Status:** proposed — needs go-ahead.
**Priority:** 5 **Difficulty:** 3
**Created:** 2026-10-25 (William Emerison Six <billsix@gmail.com>). Filed from on-screen feedback that the
Rust TUI lacked autocomplete; checking the oracle showed the **Python ncurses TUI lacks it too**, so this
closes the oracle's gap (and feature-spec §6.1 now requires completion of TUIs, not just the readline CLI).

## BLUF

The Python CLI (`hanoicli.py`) has readline tab-completion of command verbs + saved-recipe names; the
Python **ncurses TUI** (`hanoigame.py`) has a hand-rolled `getch` input loop with **no completion**. Add
Tab-completion to that input loop — command verbs on the first token, recipe names after `apply `/`show `
— matching the CLI and feature-spec §6.1. "Done" = pressing Tab at the TUI prompt completes the verb /
recipe name (single candidate fills in, several fill to the longest common prefix); gates green.

## Context

- **Oracle + gap:** `python/src/hanoigame/hanoigame.py` — the input echo loop (around the `getch`
  handling, "Echoes printable characters, handles backspace…") never handles Tab. `hanoicli.py` has the
  completion logic (command verbs on the first token; recipe names after `apply `/`show `, never `save `).
- **Share the candidate logic, don't duplicate.** The Rust side just did this cleanly: a pure
  `completions(buffer, text, names)` helper, used by both the CLI and the TUI (see
  `tasks/rust-feature-parity-tauri-tui-gaps.md` + `rust/hanoigame/src/commands.rs::completions`). Do the same in
  Python — a pure helper (verbs + recipe-name logic) that both `hanoicli.py` and `hanoigame.py` call, so
  they can't drift. `commands.COMMAND_VERBS` is the single source of verbs.
- **Spec:** feature-spec.md §6.1 requires Tab-completion "in both a readline CLI and a full-screen/curses
  TUI … share the candidate logic across front-ends."

## Plan

1. Extract/confirm a pure `completions(buffer, text, names)` helper in the Python package (if the CLI's
   logic isn't already shared), so both front-ends use one copy.
2. In `hanoigame.py`'s input loop, handle Tab: compute candidates for the token under the cursor, fill in
   the single candidate or the longest common prefix (no candidate → no-op). ncurses supports this on its
   own input line.
3. Verify: `make tui` in-container, Tab completes verbs + recipe names; `make format`/`type-check` green.

## Related

- Oracle: `python/src/hanoigame/{hanoigame.py,hanoicli.py,commands.py}`.
- The spec: `tasks/reference/feature-spec.md` §6.1. The Rust precedent: `rust/hanoigame/src/commands.rs`
  (`completions`) + `rust/hanoi/src/main.rs` (`complete_line` on the TUI prompt).
