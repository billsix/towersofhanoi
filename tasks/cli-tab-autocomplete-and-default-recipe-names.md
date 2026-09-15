# CLI: tab autocomplete + GUI-default recipe names (no name-picking)

**Status:** implemented (2026-09-15) — code + tests done, `ty`/ruff/format/128 tests green
in-container. **Awaiting a human TTY verify** of the interactive completion (pytest/StringIO
can't exercise the `input()`/readline path — only the pure completer + the non-interactive
reads + the save semantics are unit-tested). See "Outcome".
**Priority:** 4
**Difficulty:** 3

## Outcome (2026-09-15)

Implemented per option (a) and both decisions.

- **Single-source verb list:** `commands.COMMAND_VERBS` (`relabel`/`save`/`apply`/`show`/`list`/
  `help`/`quit` — no "move"; moves use `<from> -> <to>`, not a keyword). Both `parse` and the
  completer draw from it in spirit; the tuple is the completion source of truth.
- **Interactive-only reads:** `hanoicli._read_line(prompt, in_, out)` uses `input()` (so readline
  editing + Tab completion fire) **only** when `in_ is sys.stdin and sys.stdin.isatty()`
  (`_is_interactive`); otherwise it does the old `out.write(prompt); out.flush(); in_.readline()`,
  so the scripted/piped path is byte-identical. All three prompts (disc-count, game `> `, save,
  play-again) route through it. EOF is now `None` (vs the old empty-string check).
- **Completer:** `_install_completion(registry, in_)` (called once in `run()`, no-op unless
  interactive + `readline` importable) binds Tab (GNU `tab: complete`, else libedit
  `bind ^I rl_complete`) to a hook over the **pure** `_completions(buffer, text, registry)`:
  verbs on the first token; `registry.names()` after `apply `/`show `; **nothing after `save `**
  (no overwrite invitation) or any other post-verb position. The registry is shared, so names
  saved mid-session complete on later lines.
- **Save default:** `_prompt_save` now offers `solve-<n>` (matching the GUI) — **Enter saves the
  default**, a typed name renames, **`-` skips** (EOF also skips).
- **Tests:** the scripted CLI tests that used a blank line to *skip* the save now use `-`; added
  `test_post_win_empty_saves_default_name` (Enter → `solve-2`) and `test_post_win_dash_skips_save`;
  added three direct `_completions` unit tests (verbs; names after `apply`/`show`; empty after
  `save`). 128 tests pass.
- **Cannot auto-test (needs a human `make shell` → `hanoi-cli` at a real terminal):** that Tab
  actually completes verbs and recipe names, and that Enter at the save prompt saves `solve-<n>`.
  Per the plan, no `pty`/`pexpect` dependency was added just for this.

## BLUF

Make the command-line front-end (`hanoi-cli`) feel like a real shell:

1. **Tab autocomplete for actions** — pressing Tab at the prompt completes the command verbs
   (`move`/`relabel`/`save`/`apply`/`show`/`list`/`help`/`quit`).
2. **Recipe-name completion for `apply`/`show`** — after typing `apply ` or `show `, Tab completes
   the names of saved recipes (the CLI's "load" path).
3. **Default recipe names matching the GUI, so the user needn't pick one** — the GUI pre-fills the
   save name as **`solve-{num_disks}`** (`hanoigui.py:499`); the CLI's post-win save prompt should
   offer that same default so pressing Enter saves under `solve-{n}` instead of *skipping*.

"Done" = at an interactive terminal, Tab completes verbs at the start of a line and recipe names
after `apply `/`show `; the save prompt defaults to `solve-{n}`; and the scripted/piped test path
(injected streams) is byte-for-byte unchanged.

## Context — read first

- **The CLI is stream-injected, not `input()`-based** (`python/src/hanoigame/hanoicli.py`). Every
  read is `in_.readline()` on a `TextIO` passed into `run(in_, out)` / `_play_game(...)` — this is
  what makes it testable with `io.StringIO`. **`readline` autocomplete does NOT hook `stream.readline()`
  — it only hooks the built-in `input()` when stdin is an interactive TTY.** So the core design
  problem is: add completion *without* breaking the injected-stream contract the tests rely on.
- **Command grammar:** `commands.parse(line)` (`commands.py`) recognises the verbs listed in
  `HELP_TEXT` (`commands.py:106`): `move` (as `<from> -> <to>` / `<from> <to>` / two-digit),
  `relabel`, `save <name>`, `apply <name>`, `show <name>`, `list`, `help`, `quit`. The verb list for
  the completer should be **derived from / kept in sync with** this grammar, not hand-duplicated in a
  way that silently drifts (a single module-level tuple both use, or a small accessor).
- **Recipe store:** `RecipeRegistry` (`recipe.py:92`) — `registry.names()` (`recipe.py:104`) already
  returns the sorted saved-recipe names. That is exactly the completion source for `apply`/`show`.
  The registry is created in `run()` and threaded through `_play_game`; the completer needs a
  reference to it (see design note on closures below).
- **Save prompt today** (`_prompt_save`, `hanoicli.py:61`): prints "Type a name, or press Enter to
  skip", and an empty line *skips the save*. The GUI instead pre-fills `solve-{n}` in a
  `wx.TextEntryDialog` (`hanoigui.py:494`) — the user can edit it but usually just accepts it. Align
  the CLI: prompt should show the default and **Enter = accept `solve-{n}`** (offer an explicit way
  to skip, e.g. typing `-` or `no`, so the skip path isn't lost — decide and document).
- **Backend:** `readline` is present and is **GNU readline** in the sandbox (verified 2026-09-15:
  `readline.__doc__` says "GNU"). On **macOS** Python's `readline` is often backed by **libedit**,
  where `parse_and_bind("tab: complete")` does nothing and you need
  `parse_and_bind("bind ^I rl_complete")`. Detect via `"libedit" in (readline.__doc__ or "")` and
  bind accordingly — the maintainer runs on both Fedora (container) and possibly Mac.
- **Entry point:** `hanoi-cli = hanoigame.hanoicli:main` (`pyproject.toml:45`); `main()` passes the
  real `sys.stdin`/`sys.stdout`.

## Design (the shape to implement)

- **Gate completion on an interactive TTY.** Only install the readline completer when
  `in_ is sys.stdin and sys.stdin.isatty()` (and `readline` imports). Otherwise leave the current
  `in_.readline()` path completely untouched — this preserves the scripted-test contract and avoids
  emitting completion escapes into piped output.
- **How to actually get completion to fire:** `readline` completes the line being edited by
  `input()`, so the interactive read must go through `input(prompt)` rather than `out.write(prompt);
  in_.readline()`. Two options — surface the choice:
  - **(a)** Add a thin `_read_line(prompt, in_, out)` that uses `input()` when interactive and falls
    back to `out.write(prompt); in_.readline()` otherwise. Route the game prompt (`> `), the
    disc-count prompt, and the save prompt through it. Cleanest; keeps one code path per prompt.
  - **(b)** Keep `readline()` and rely on readline's auto-hooking — **rejected**: readline does not
    hook a bare `stream.readline()`, so this won't complete. (Recorded so it isn't re-tried.)
  Recommend **(a)**.
- **Context-sensitive completer.** One completer function inspects `readline.get_line_buffer()`:
  - if the buffer has no space yet (still typing the first token) → complete **verbs**;
  - if it starts with `apply `/`show ` → complete **`registry.names()`** (the load side);
    **not** after `save ` — no existing-name completion there (decision 2 below);
  - the completer needs the live `registry` — install it as a closure over the registry (set up in
    `run()`), or a small completer object holding a registry reference, re-pointed per game if needed.
- **Bind once, restore politely.** `readline.set_completer(fn)` +
  `readline.parse_and_bind(<tab binding per backend>)`; consider saving/restoring any prior completer
  so importing the CLI programmatically doesn't clobber a host readline setup.

## Plan

- [ ] Extract the verb list from `commands.py` (single source of truth) for the completer to consume.
- [ ] Add the interactive-only `_read_line` helper (option a); route the three prompts through it,
      leaving the injected-stream path identical when not a TTY.
- [ ] Add the context-sensitive readline completer (verbs at line start; `registry.names()` after
      `apply `/`show ` only — not `save `), backend-aware Tab binding (GNU vs libedit).
- [ ] Change `_prompt_save` to default to `solve-{n}` (Enter accepts; document the explicit skip).
- [ ] Tests: the scripted-stream path (StringIO) stays byte-identical — assert existing CLI tests
      still pass unchanged; add a unit test for the completer function directly (it's pure given a
      line buffer + registry, so it's testable without a PTY). A full interactive PTY test is optional
      (`pty`/`pexpect` not currently a dep — don't add one just for this; test the completer function).
- [ ] Verify in-container at an actual TTY (`make shell` → `hanoi-cli`): Tab completes verbs and
      recipe names; Enter at the save prompt saves `solve-{n}`.

## Decisions (answered by the maintainer 2026-09-15)

1. **Save-prompt skip:** with Enter accepting `solve-{n}`, the user skips saving by typing **`-`**.
   Show this in the prompt text (e.g. "Enter to save as 'solve-5', or '-' to skip").
2. **`save ` completion:** **no** completion of existing recipe names after `save ` (don't invite
   overwriting). Tab after `save ` may still offer the `solve-{n}` default, but must not list existing
   names. Recipe-name completion applies to **`apply `/`show `** only (the load side).

## Related

- `python/src/hanoigame/hanoicli.py` (the front-end), `commands.py` (verb grammar),
  `recipe.py` (`RecipeRegistry.names()`), `hanoigui.py:494` (the GUI default name).
- Python `readline` docs: `set_completer`, `parse_and_bind`, `get_line_buffer`.
