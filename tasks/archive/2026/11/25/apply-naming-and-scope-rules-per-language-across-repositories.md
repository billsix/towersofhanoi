# Make a task in every project repository to apply the naming and scope rules, per language

**Done:** 2026-11-25. Asked for by William Emerison Six <billsix@gmail.com> the same day ("once that's done, to make a task in all of my repos for my projects in /mnt/sda1 to apply them, per language"), after `tasks/archive/2026/11/25/add-scoping-rules-to-per-language-coding-standards.md` wrote the rules for Rust, C++, JavaScript and bash.

## What this did

- **Wrote the rules for the two languages still missing them.** `c-coding-standard.md` and `haskell-coding-standard.md` (github.com/billsix/runClaudeInContainer `tasks/reference/`, mirrored byte-identically in github.com/billsix/runCrushInContainer) each gained a "Locals and helpers" section. C: a one-caller helper is `static`, directly above its caller, and nothing shadows (`-Wshadow` is in the gate). Haskell: a one-caller helper goes in its caller's `where` and reads the caller's arguments, and nothing shadows (`-Wall -Werror` rejects it).
- **Promoted the survey script to a shared tool.** `survey_names_and_scope.py` (same directory, mirrored the same way, run in place as `python3 ~/.claude/reference/survey_names_and_scope.py`) lists functions named exactly twice and locals named exactly twice inside their function, for Rust, C++, C, Haskell, bash and JavaScript.
- **Wrote `tasks/apply-naming-and-scope-rules-per-language.md` in 31 repositories**, one task per repository with a row per language it has. Each cites the standard's section per language, the survey tool, the whose-code rule and the Python batch as the pattern. The tasks in `hanoi` and `spimulator` are in progress; the other 29 are `proposed — needs go-ahead`.

## Decisions (William Emerison Six <billsix@gmail.com>, 2026-11-25)

- **Scope:** "make a task for all of them, but only start work on hanoi and spimulator". So every repository with code in a covered language got a task, including the ones that hold book examples or a game's source; each task's first step settles which trees are the maintainer's own code.
- **C and Haskell sections:** "the languages supported by spimulator should have similar advice added to runClaude and runCrush, I know at least for haskell", and "there should be a C section too, yes, absolutely, just like with haskell".
- **One task per repository, not per repository and language** (the agent's call): the Python batch used one task per repository, and a repository's languages share its gate and its scope decision.
- **Python is a row only where the Python batch has not run:** a repository with an archived `apply-2026-11-06-naming-and-scope-rules.md` has no Python row.
- **Not decided:** whether the container template's near-identical `entrypoint/*.sh` scripts should be surveyed once for the fleet instead of per repository. The maintainer did not answer; each repository's bash row covers its own scripts until he does.

## Repositories

- **Task written (31):** `CodeTheClassics`, `Craft`, `McNopperOpenGL`, `OpenGLSuperBibleV4Code`, `Programming3DComputerGraphics`, `apue`, `billsEmacsConfigs`, `buildGZDoom`, `buildLineageOS`, `dotfiles`, `duckgamevst`, `epix-mirror`, `geometricalgebra`, `gltron`, `graphicalcontainer`, `hanoi`, `hearnBakerCarithers4thEdition`, `impo`, `imps`, `methodfinder`, `multivariate-math`, `openglredbook4.5`, `openglredbook9examples`, `runClaudeInContainer`, `runCrushInContainer`, `sb7code`, `smalltalk`, `smc`, `spimulator`, `texExpToPng`, `whitakers-words` (directory names of the checkouts).
- **Skipped, upstream-only checkouts:** `baldwin`, `galgebra`, `whitelistnetwork`.
- **Skipped, no code in a covered language:** `billsNotes`, `differentialEquationsTrench`, `essentialsOfProgrammingLanguages2ndEdition`, `mathnotebooks`.

Committed on a branch in `hanoi`, `spimulator`, `runClaudeInContainer` and `runCrushInContainer`; staged, not committed, in the other 27.

## How

`make_tasks.py` (removed with this archive; it is in this repository's history under `tasks/adhoc/apply-naming-and-scope-rules-per-language-across-repositories/`) counted tracked files per language and top-level directory, left out vendored paths by pattern, skipped a checkout whose remotes are all third-party, and wrote the task unless it already existed. A second run wrote nothing (31 "left alone").
