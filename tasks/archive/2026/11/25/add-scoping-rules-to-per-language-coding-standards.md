# Add the Python scoping rules, reworded per language, to the coding standards of every language hanoi uses

**Done:** 2026-11-25 (William Emerison Six <billsix@gmail.com> asked for it the same day: "make a task for all of the languages in hanoi, to add similar rules regarding scoping per language in runClaudeInContainer and runCrushInContainer, and once that's done, to make a task in all of my repos for my projects in /mnt/sda1 to apply them, per language"). It touched three repositories: github.com/billsix/towersofhanoi (this task and its survey), github.com/billsix/runClaudeInContainer (the canonical standards) and github.com/billsix/runCrushInContainer (their mirrors).

## What this did

Five naming and scope rules (inline a binding used once, a binding used twice does not automatically earn a name, declare a name at the point of use, nest a helper with one caller, shadow deliberately when nesting) had been in the Python standard since 2026-11-06 and nowhere else. `hanoi` uses five code languages: Python, Rust, C++, bash and the Tauri frontend's JavaScript. Each of the other four now has the rules in its own standard, worded for that language, with the bindings that language must keep and a statement where a rule does not carry over.

| Language | Document (github.com/billsix/runClaudeInContainer `tasks/reference/`) | Section added |
|---|---|---|
| Rust | `rust-coding-standard.md` | "Locals and helpers — inline what is used once, declare at the point of use, nest a one-caller helper" |
| C++ | `cpp-coding-standard.md` | "Locals and helpers — inline what is used once; a one-caller helper stays a named function" |
| JavaScript | `javascript-coding-standard.md` | "(b) Judgment calls — locals and helpers: inline what is used once, nest a one-caller helper" |
| bash | `shell-and-gate-scripts.md` | "Names and scope in bash — inline what is used once, `local` at the point of use, no nested helpers" |

`code-style-conventions.md` ("Names: inline what is used once…") points at the four sections, and its nesting bullet no longer says a C++ helper nests as "a local `struct` or lambda"; it and the cross-project `CLAUDE.md` of both sandboxes say how nesting differs per language. C and Haskell were out of scope because `hanoi` has neither.

## Decisions (William Emerison Six <billsix@gmail.com>, 2026-11-25: "yes to all seven recommendations", five of them these)

1. **C++, rule 4:** a helper with one caller stays a named anonymous-namespace or `static` function and is not turned into a lambda; a lambda only when it captures local state.
2. **bash, rule 4:** the standard states that rule 4 does not apply (functions are global), and that rules 1, 2, 3 and 5 apply to variables.
3. **Rust, rule 4:** a one-caller helper that captures nothing becomes a nested `fn`, one that captures a local becomes a closure, and one a `#[cfg(test)]` function calls stays at module level.
4. **Where the bash section goes:** a section in `shell-and-gate-scripts.md`, not a new bash standard.
5. **Scope of languages:** hanoi's five; the application task adds C or Haskell sections when it meets a repository that needs one.

## What the survey found, and how it shaped the wording

`survey.py` (ctags for function spans, textual counts; removed with this archive, recoverable with `git show d1dd724:tasks/adhoc/add-scoping-rules-to-per-language-coding-standards/survey.py`) listed functions named exactly twice and locals named exactly twice inside their function: 408 lines of leads across 15 Rust, 6 C++, 43 bash and 1 JavaScript files. The leads that became rules or carve-outs:

- **Rust:** `let failed: bool = result.error.is_some(); results.push(result);` in `recipe::apply` (a read before a move); `let d: Dialog = dlg.clone();` before a `move` closure in the wx GUI; `let mut st: MutexGuard<…> = state.lock().unwrap();` in the Tauri backend (a guard); the `handle_move`, `handle_relabel`, `handle_show`, `handle_list` and `handle_history` methods of `GameSession`, each called once from the dispatch `match` (a method and a dispatch arm stay); the `two_minus_1_i_to_t`-style names in `solvers/recursive.rs`, each used once and each the name of a step of the relabelling method (a name that carries the lesson stays); `noun` in `presenter.rs`, used once in a `format!` capture (the named-argument form).
- **C++:** `detail::explain_illegal` in `recipe.hpp`, one caller, already an `inline` function in a `detail` namespace directly above it (the shape decision 1 asks for); `fp`, `tp` and `apply_name` copied in `main.cpp` before `app.clear_pending()` (a copy before its source changes); `wxDouble th`, `td`, `te` in `hanoiwx.cpp` (out-parameter targets); 47 one-caller leads, most of them toolkit event handlers and per-frame draw functions (they name a phase and stay).
- **JavaScript:** `const count = latest.review;` in `leaveReview`, read before an `await` on a dialog while `latest` is module state (the snapshot carve-out); the cast form `/** @type {Snapshot} */ (await invoke(…))` already used inline in `main.js`; `isActive` already nested in `renderRelabelMenu`.
- **bash:** only one function in 43 scripts (`ver_part` in `cpp/tools/update-doctest.sh`), so rule 4 has almost nothing to act on there; the single-use leads were `cpp_dir`, `pattern` and `web_files` in the `check-no-network.sh` scripts (a path that can be inlined, a regular expression and an array, which stay).

## Checked by running it (2026-11-25, in the sandbox)

- **Rust** (`rustc`, `rustdoc --test`): a borrow of a temporary across statements is E0716; a nested `fn` that names the enclosing generic parameter is E0401; a nested `fn` may recurse; `format!("{moves} {noun}", noun = if …)` compiles. A first draft said rustdoc does not collect a doctest from a nested item. That was wrong: rustdoc ran the example on `outer::inner`. The standard now gives the real reason a doctested helper stays at module level, which is that the example cannot name a nested item.
- **C++** (`g++` and `clang++ -std=c++20 -Wshadow`): a lambda parameter that repeats an explicit capture is an error in both; one that repeats a name taken by `[&]` is a `-Wshadow` warning in g++.
- **bash:** a function defined inside another is callable from outside once the outer has run, and sees its caller's `local`; `local v="$(false)"` has status 0 and the two-statement form has status 1; a `for` variable in a function leaks; a `( … )` body does not; under `set -e`, `echo "$(false)"` continues and `z="$(false)"` stops. shellcheck reported SC2155 and SC2034 on the test script.
- **JavaScript** (`node`): a closure that names a `const` declared below it throws `ReferenceError` when called before that line and works after it.
- **Not checked:** the sandbox has no `deno`, so the JavaScript section names lint rules generically (`no-var`, `prefer-const`) and makes no claim about Deno's recommended set.

## Mirrors

`rust-coding-standard.md`, `cpp-coding-standard.md` and `javascript-coding-standard.md` are byte-identical in three places (`cmp`): the canonical one, and github.com/billsix/runCrushInContainer `tasks/reference/` and `client/entrypoint/dotfiles/.config/crush/reference/`. `code-style-conventions.md` is byte-identical in the canonical and the baked Crush copy. The baked Crush `shell-and-gate-scripts.md` holds only the portable sections of the canonical; the new bash section was added to both from one source text.

## Commits

- This repository: `d1dd724` (the survey), then the work commit holding this record and the follow-on task, then the archive move.
- github.com/billsix/runClaudeInContainer: `d1e2fa1`. github.com/billsix/runCrushInContainer: `f788404`.

The SHAs are those on the `add-scoping-rules-to-per-language-coding-standards` branches before the maintainer's merge.

## Follow-on

`tasks/apply-naming-and-scope-rules-per-language-across-repositories.md` (proposed, three open questions): make a task per repository and language to apply these rules.
