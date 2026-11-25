# Make a task in every project repository to apply the naming and scope rules, per language

**Status:** proposed — needs go-ahead (and answers to the open questions below)
**Priority:** 6 (no deadline; many repositories, each a separate unit of work)
**Difficulty:** 5 (this task only writes task docs; each task it creates is its own difficulty, C++ and C the hardest)
**Created:** 2026-11-25 (William Emerison Six <billsix@gmail.com>): "once that's done, to make a task in all of my repos for my projects in /mnt/sda1 to apply them, per language".
**Depends on:** `tasks/archive/2026/11/25/add-scoping-rules-to-per-language-coding-standards.md` (done 2026-11-25; it wrote the per-language sections this task applies).

## BLUF

The five naming and scope rules now exist for Rust, C++, JavaScript and bash as well as Python, in the shared standards. This task creates one task doc per repository and language (status `proposed — needs go-ahead`) in every project repository the maintainer owns, each saying how to survey and apply the rules there. Done means every repository in the table below has its task docs, or a line here saying why it has none. This task changes no code.

## Context

**The rules, per language** (github.com/billsix/runClaudeInContainer `tasks/reference/`, mirrored in github.com/billsix/runCrushInContainer):

| Language | Section | What differs from Python |
|---|---|---|
| Python | `python-coding-standard.md`, "Inline a value used once…" and "What earns an extraction" | the baseline; `nest_one_caller.py` nests mechanically |
| Rust | `rust-coding-standard.md`, "Locals and helpers" | nested `fn` when the helper captures nothing, closure when it captures a local; a helper a `#[cfg(test)]` function calls stays at module level |
| C++ | `cpp-coding-standard.md`, "Locals and helpers" | a one-caller helper stays a named function above its caller, never a lambda; no shadowing |
| JavaScript | `javascript-coding-standard.md`, "(b) Judgment calls — locals and helpers" | as Python; a snapshot taken before an `await` keeps its binding |
| bash | `shell-and-gate-scripts.md`, "Names and scope in bash" | rule 4 does not apply; `local` at the point of use |

C and Haskell have standards but no such section yet. The standards task decided that this task adds a section when it first meets a repository that needs one.

**The pattern to copy.** The Python batch of 2026-11-25: `tasks/archive/2026/11/25/apply-2026-11-06-naming-and-scope-rules.md` in this repository and in `Programming3DComputerGraphics`, `methodfinder`, `mathnotebooks`, `multivariate-math`, `epix-mirror` and `geometricalgebra` (each on github.com/billsix/). Each of those surveyed first, applied by discretion, left GUI and GL construction blocks and tests alone, and recorded what it kept and why.

**A survey script for the four new languages** existed for hanoi and was removed when the standards task was archived; recover it with `git show d1dd724:tasks/adhoc/add-scoping-rules-to-per-language-coding-standards/survey.py`. It uses `ctags` and textual counts, lists functions named exactly twice and locals named exactly twice inside their function, and its output is a list of leads to read. On hanoi it gave 408 lines.

**Repositories and languages** (tracked files, vendored trees excluded by path pattern, counted 2026-11-25 with `git ls-files`; upstream-only checkouts `baldwin`, `galgebra` and `whitelistnetwork` are left out):

| Repository directory | Rust | C++ | C | bash | JavaScript | Haskell |
|---|---|---|---|---|---|---|
| `hanoi` | 15 | 6 | | 44 | 1 | |
| `spimulator` | 25 | | 166 | 28 | 2 | 26 |
| `smc` | | 77 | 88 | 23 | | |
| `duckgamevst` | | 133 | 220 | 4 | 112 | |
| `epix-mirror` | | 83 | 90 | 17 | | |
| `OpenGLSuperBibleV4Code` | | 123 | 213 | 9 | | |
| `sb7code` | | 90 | 85 | 4 | | |
| `openglredbook9examples` | | 43 | 17 | 4 | | |
| `openglredbook4.5` | | 43 | 99 | | 57 | |
| `hearnBakerCarithers4thEdition` | | 20 | 145 | 2 | | |
| `Craft` | | 21 | 1094 | 38 | | |
| `smalltalk` | | 13 | 223 | 11 | | |
| `gltron` | | 8 | 162 | 8 | | |
| `apue` | | | 2527 | 9 | | |
| `McNopperOpenGL` | | | 67 | 4 | | |
| `imps` | | | | 91 | | |
| `impo` | | | | 54 | 2 | |
| `billsEmacsConfigs` | 1 | 1 | 1 | 65 | | 1 |
| `geometricalgebra`, `Programming3DComputerGraphics`, `multivariate-math`, `methodfinder`, `CodeTheClassics`, `texExpToPng`, `runClaudeInContainer`, `runCrushInContainer`, `buildLineageOS`, `buildGZDoom`, `dotfiles`, `graphicalcontainer`, `whitakers-words` | | | | 1 to 21 each | | |

The counts are raw: the `.h` files of a C++ project count as C, and several of these repositories hold another author's book code or a game's source, most of it not the maintainer's own writing (see open question 1). `billsNotes`, `mathnotebooks`, `differentialEquationsTrench` and `essentialsOfProgrammingLanguages2ndEdition` have none of these languages.

## Plan

- [ ] Get answers to the open questions.
- [ ] For each repository in scope, read its `CLAUDE.md` and confirm which trees are the maintainer's code and which are vendored or generated.
- [ ] Write `tasks/apply-naming-and-scope-rules-<language>.md` in each (one per language present), `proposed — needs go-ahead`, citing the standard's section, the survey method, the repository's gate, and the carve-outs that the standard lists.
- [ ] Stage each by path; commit only where the maintainer has authorized it.

## Open questions

1. **Which repositories are in scope?** The global rule is to sweep only code the maintainer wrote and to leave someone else's code alone. (a) Only the repositories whose code is the maintainer's own (`hanoi`, `spimulator`'s Rust and Haskell, `smc`, and the bash of every repository), which is the agent's recommendation; or (b) every repository in the table, including the book-code and game-source ones (`apue`, `Craft`, `gltron`, `smalltalk`, the OpenGL book repositories).
2. **C section first?** `spimulator`, `smc` and others have C. Should this task write the C section of the rules in `c-coding-standard.md` (the agent's recommendation: yes, one short section, since C has no nested functions and the C++ decision carries over as "`static`, directly above the caller") before making C tasks?
3. **Shell scripts under `entrypoint/`:** every repository has the container template's `entrypoint/*.sh`, mostly near-identical. One task per repository (the agent's recommendation: no; one fleet task in github.com/billsix/runClaudeInContainer that surveys them all, since they are copies of one template), or per repository?
