# CLI: tab autocomplete + GUI-default recipe names (no name-picking)

**Status:** complete (2026-09-15) — implemented, `ty`/ruff/format green in-container, 128 tests
pass, and the maintainer confirmed the interactive Tab-completion and `solve-<n>` save default at
a real terminal.
**Priority:** 4
**Difficulty:** 3

## What this was

Three shell-like conveniences for `hanoi-cli`: (1) Tab-completes command verbs at the start of a
line; (2) Tab-completes saved-recipe names after `apply `/`show ` (the load side); (3) the post-win
save prompt defaults to `solve-<n>` (matching the GUI's pre-filled name) so the user needn't invent
one. The design constraint that shaped everything: the CLI is **stream-injected** (`run(in_, out)`
reads `in_.readline()`, which is what makes it testable with `io.StringIO`), and `readline`
completion only hooks the built-in `input()` at an interactive TTY — so the interactive behaviour
had to be added *without* changing the scripted-stream path the tests depend on.

## What was done

- **Single-source verb list** — `commands.COMMAND_VERBS` (`relabel`/`save`/`apply`/`show`/`list`/
  `help`/`quit`; no "move" — moves use the `<from> -> <to>` syntax, not a keyword).
- **Interactive-only reads** — `hanoicli._read_line(prompt, in_, out)` goes through `input()` (so
  readline editing + Tab completion fire) **only** when `_is_interactive(in_)` (`in_ is sys.stdin
  and sys.stdin.isatty()`); otherwise it does the old `out.write(prompt); out.flush();
  in_.readline()`, keeping scripted output byte-identical. All prompts (disc-count, game `> `, save,
  play-again) route through it; EOF is now signalled by `None` rather than an empty string.
- **The completer** — `_install_completion(registry, in_)` (called once in `run()`, a no-op unless
  interactive and `readline` importable) binds Tab (GNU `tab: complete`, else libedit
  `bind ^I rl_complete`) to a hook over the **pure** `_completions(buffer, text, registry)`: verbs
  on the first token; `registry.names()` after `apply `/`show `; **nothing after `save `** (decision
  below) or any other post-verb position. The registry is shared across games, so names saved
  mid-session complete on later lines. Extracting `_completions` as a pure function is what makes
  the completion logic unit-testable without a PTY.
- **Save default** — `_prompt_save` offers `solve-<n>`: **Enter saves the default**, a typed name
  renames, and **`-` skips** (EOF also skips).

## Decisions (maintainer, 2026-09-15)

1. Skip the save with **`-`** (Enter now means "accept the default", so a distinct skip token was
   needed).
2. **No** recipe-name completion after `save ` — completing existing names there would invite
   overwriting; recipe-name completion is the load side (`apply `/`show `) only.

## Verification

`ty` 0, `ruff` clean at 80, `ruff format --check` idempotent, **128 tests** pass in-container. The
scripted CLI tests that used a blank line to *skip* the save were switched to `-`; added
`test_post_win_empty_saves_default_name` (Enter → `solve-2`), `test_post_win_dash_skips_save`, and
three direct `_completions` unit tests (verbs; names after `apply`/`show`; empty after `save`). The
interactive Tab-completion and `input()`-based reads can't be exercised by pytest/StringIO (they
only fire at a real TTY, and no `pty`/`pexpect` dependency was added), so the maintainer verified
them by hand at `make shell` → `hanoi-cli`.

## Related

- `python/src/hanoigame/hanoicli.py`, `commands.py` (`COMMAND_VERBS`), `recipe.py`
  (`RecipeRegistry.names()`), `hanoigui.py` (the GUI `solve-<n>` default it mirrors).
- `tasks/reference/architecture-overview.md` — the frontends + the interactive-vs-injected-stream
  pattern.
