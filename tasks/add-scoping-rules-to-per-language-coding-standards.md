# Add the Python scoping rules, reworded per language, to the coding standards of every language hanoi uses

**Status:** proposed — needs go-ahead
**Priority:** 6 (a standards edit with no deadline; it gates the follow-on task that applies the rules across the other repositories)
**Difficulty:** 4 (five short sections plus mirrored copies; the judgment is in what each rule means in a language without lexical nesting)
**Created:** 2026-11-25 (William Emerison Six <billsix@gmail.com>, from `git config`): "make a task for all of the languages in hanoi, to add similar rules regarding scoping per language in runClaudeInContainer and runCrushInContainer, and once that's done, to make a task in all of my repos for my projects in /mnt/sda1 to apply them, per language".

## BLUF

Five naming and scope rules (inline a binding used once, a binding used twice does not automatically earn a name, declare a name at the point of use, nest a helper with one caller, shadow deliberately when nesting) were added to the Python standard on 2026-11-06 and applied to seven Python repositories on 2026-11-25. They exist only for Python. `hanoi` uses five code languages (Python, Rust, C++, bash, and the Tauri frontend's JavaScript); this task writes each rule into that language's standard in github.com/billsix/runClaudeInContainer and its mirrors in github.com/billsix/runCrushInContainer, or says in the standard why a rule does not carry over. Done means every one of those standards has the section (or the stated exception), the mirrored copies are byte-identical, and the follow-on task, "apply the rules in every repository under `/mnt/sda1`, per language", is scaffolded.

## Context

**The rules and their source.** `python-coding-standard.md` in github.com/billsix/runClaudeInContainer (`tasks/reference/`): "Inline a value used once, and name it in a comment instead of a binding", "What earns an extraction: duplication, or naming a phase — not reshaping control flow" (rule 4, with the pointer to `nest_one_caller.py`), and the carve-out "A name that documents what it holds keeps its binding" (test inputs and case tables, tables of rows and named corners, slices of a packed array named for their layout, side-effecting calls, a value computed before a later statement changes its inputs). The language-agnostic summary is `code-style-conventions.md` ("Names: inline what is used once, declare at the point of use, nest and shadow") and the global `CLAUDE.md` section "What earns pulling code into its own function". Read the archived records of the Python batch for what went wrong and what each carve-out is for: `tasks/archive/2026/11/25/apply-2026-11-06-naming-and-scope-rules.md` in the `Programming3DComputerGraphics`, `methodfinder`, `mathnotebooks`, `multivariate-math`, `epix-mirror`, `hanoi` and `geometricalgebra` repositories (each on github.com/billsix/).

**Languages in `hanoi`** (counted from `git ls-files`, vendored trees excluded, 2026-11-25) and the standard each one has:

| Language | Where in `hanoi` | Standard (github.com/billsix/runClaudeInContainer `tasks/reference/`) | What it says today |
|---|---|---|---|
| Python | `python/src/hanoigame/`, `python/tests/`, `tools/` (24 files) | `python-coding-standard.md` | has all five rules |
| Rust | `rust/` (15 files; the Tauri backend in `rust/tauri/src-tauri/`) | `rust-coding-standard.md` | no section on locals or nested helpers |
| C++ | `cpp/hanoiwx.cpp`, `cpp/main.cpp`, `cpp/src/*.hpp` (header-only engine with inline doctest tests) | `cpp-coding-standard.md` | "Lambdas" (Meyers EMC++ 31–34, `F.50`–`F.54`), initialize-and-`const`; nothing on single-use locals or one-caller helpers |
| bash | `bash/*.sh` (12 demos), `entrypoint/*.sh`, `tools/*.sh` (44 files in all) | `shell-and-gate-scripts.md` (gate and format scripts; there is no bash coding standard) | exit-status and portability rules only |
| JavaScript | `rust/tauri/frontend/main.js` (vanilla, JSDoc-typed, Deno gate) | `javascript-coding-standard.md` | JSDoc types on every binding; no scoping section |

Not code, so out of scope: reStructuredText (`docs/`), LaTeX (`workbook/`), XRC (`ui/hanoi.xrc`), TOML, HTML and CSS. The Crush client carries baked copies of these documents under `client/entrypoint/dotfiles/.config/crush/reference/`; `shell-and-gate-scripts.md` has no copy in runCrushInContainer's `tasks/reference/`, only the baked one.

**What does not carry over unchanged** (the agent's analysis, to be settled by the open questions below):
- **Rust:** `let` shadowing is idiomatic (`let x = x.trim();`), so rule 5's "shadow deliberately" is already the norm; a nested `fn` item cannot capture locals (a closure can), so "nest a one-caller helper" means a nested `fn` when it captures nothing and a closure when it does; unit tests in a `#[cfg(test)]` module call private functions in the same file, which counts as a second caller under the Python batch's rule for a helper a test imports.
- **C++:** a nested helper is a lambda, which loses the name for overloading and recursion and can obscure a stack trace; an anonymous-namespace or `static` function is the conventional private helper. The doctest cases sit in the header beside the code, so a helper they call has a second caller.
- **bash:** functions are global, and `local` is dynamically scoped, so a function defined inside a function becomes global when the outer one runs. Rule 4 has no lexical meaning; rules 1, 2, 3 and 5 apply to variables (`local` at the point of use, no single-use variable that only names an expression).
- **JavaScript:** nested function declarations and closures work as in Python; `const` at the point of use.

**What the tooling is.** `nest_one_caller.py` (github.com/billsix/runClaudeInContainer `tasks/reference/`, mirrored in runCrushInContainer) nests Python helpers only. There is no equivalent for the other languages and this task does not write one; it records, per language, whether a tool is warranted.

## Goal

Make each of hanoi's code languages say, in its own standard, how to inline a binding used once, how to treat a binding used twice, where to declare a name, whether and how to nest a helper that has one caller, and how to shadow. Each rule is worded in that language's terms and checked against `hanoi`'s own code (the Rust and C++ ports mirror the Python's structure, so they are the natural test), and a rule that does not apply says so and why.

## Plan

- [ ] Settle the open questions below; each one changes what is written.
- [ ] Read the Python sections and the seven archived records named above; list the carve-outs that are language-independent (a name that documents what it holds, order of evaluation, a test as a second caller) and quote them rather than rewriting them.
- [ ] For each language, survey `hanoi`'s code for places the rule fires (a one-off script under `tasks/adhoc/add-scoping-rules-to-per-language-coding-standards/`, read-only), so each new section is written from real cases and compared to a baseline the reader knows (the Python section).
- [ ] Write the sections in the canonical documents in github.com/billsix/runClaudeInContainer: `rust-coding-standard.md`, `cpp-coding-standard.md`, `javascript-coding-standard.md`, and the bash location the open questions choose.
- [ ] Copy each changed document, byte-identical, to its mirrors in github.com/billsix/runCrushInContainer (`tasks/reference/` and `client/entrypoint/dotfiles/.config/crush/reference/`); check with `cmp`.
- [ ] Update the language-agnostic summary (`code-style-conventions.md`) and the global `CLAUDE.md` section only where a rule's wording changes for all languages.
- [ ] Scaffold the follow-on task, proposed and cross-linked: in every project repository under `/mnt/sda1` (not the upstream-only checkouts), apply these rules per language, one task per repository and language.
- [ ] Stage by path and stop; the archive move waits for the work commit.

## Notes / decisions

- The ordering is the maintainer's: this task first, then the application task (2026-11-25).
- C and Haskell standards exist but `hanoi` has neither, so they are outside this task.

## Open questions

Each blocks implementation until addressed. The recommendation is first.

1. **C++, rule 4:** state that a helper with one caller stays an anonymous-namespace or `static` function and is **not** turned into a lambda (a lambda only when it captures local state, as the existing "Lambdas" section already says), or translate rule 4 as "nest it as a lambda"? Recommended: stays a named function.
2. **bash, rule 4:** state that rule 4 does not apply (functions are global, so there is nothing to nest into), and that rules 1, 2, 3 and 5 apply to variables? Recommended: yes.
3. **Rust, rule 4:** a one-caller helper that captures nothing becomes a nested `fn` inside its caller, one that captures a local becomes a closure, and a helper a `#[cfg(test)]` function calls stays at module level? Recommended: yes.
4. **Where the bash section goes:** a section in `shell-and-gate-scripts.md`, or a new `bash-coding-standard.md`? Recommended: a section in `shell-and-gate-scripts.md` (one document, no new mirror set beyond the existing copies).
5. **Scope of languages:** only hanoi's five, or also C and Haskell now, since other repositories under `/mnt/sda1` use them? Recommended: only hanoi's five; the application task adds C or Haskell sections when it meets a repository that needs one.
