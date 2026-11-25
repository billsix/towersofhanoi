"""Write one "apply the naming and scope rules" task doc into every project repository.

The repositories are the git checkouts that sit beside this one.  A checkout whose
remotes all point at a third party is skipped (it is read-only for the maintainer).
For each of the others the script counts tracked files per language, leaves out
languages the repository does not have, and writes
``tasks/apply-naming-and-scope-rules-per-language.md`` unless that file already exists,
so a second run changes nothing.  It prints one line per repository saying what it did.

Run: ``python3 tasks/adhoc/<this-task>/make_tasks.py``.
"""

import collections
import dataclasses
import pathlib
import re
import subprocess

CHECKOUTS: pathlib.Path = pathlib.Path(__file__).resolve().parents[4]

TASK_PATH: str = "tasks/apply-naming-and-scope-rules-per-language.md"

VENDORED: re.Pattern[str] = re.compile(
    r"elpa/|/imgui/|doctest/|vendor|third_party|node_modules|^builddir/"
)

MINE: re.Pattern[str] = re.compile(
    r"192\.168\.|[@/]10\.\d+\.|172\.(?:1[6-9]|2\d|3[01])\.|github\.com[:/]billsix/"
)

IN_PROGRESS: tuple[str, ...] = ("hanoi", "spimulator")

STANDARDS: str = "github.com/billsix/runClaudeInContainer `tasks/reference/`"


@dataclasses.dataclass(frozen=True)
class Language:
    """A language the rules exist for, and where its rules are written."""

    name: str
    suffixes: tuple[str, ...]
    section: str
    difference: str


LANGUAGES: tuple[Language, ...] = (
    Language(
        "Python",
        (".py",),
        '`python-coding-standard.md`, "Inline a value used once…" and "What earns an extraction"',
        "the baseline; `nest_one_caller.py --dry-run` lists and then nests the one-caller helpers",
    ),
    Language(
        "Rust",
        (".rs",),
        '`rust-coding-standard.md`, "Locals and helpers"',
        "a nested `fn` when the helper captures nothing, a closure when it captures a local; "
        "a helper a `#[cfg(test)]` function calls stays at module level",
    ),
    Language(
        "C++",
        (".cpp", ".cc", ".cxx", ".hpp", ".hh"),
        '`cpp-coding-standard.md`, "Locals and helpers"',
        "a one-caller helper stays a named function directly above its caller, never a lambda; "
        "no shadowing",
    ),
    Language(
        "C",
        (".c", ".h"),
        '`c-coding-standard.md`, "Locals and helpers"',
        "a one-caller helper is `static`, directly above its caller; no shadowing (`-Wshadow`)",
    ),
    Language(
        "Haskell",
        (".hs",),
        '`haskell-coding-standard.md`, "Locals and helpers"',
        "a one-caller helper goes in its caller's `where` and reads the caller's arguments; "
        "no shadowing (`-Wall -Werror`)",
    ),
    Language(
        "bash",
        (".sh",),
        '`shell-and-gate-scripts.md`, "Names and scope in bash"',
        "rule 4 does not apply (functions are global); `local` at the point of use",
    ),
    Language(
        "JavaScript",
        (".js", ".mjs"),
        '`javascript-coding-standard.md`, "(b) Judgment calls — locals and helpers"',
        "as Python; a snapshot taken before an `await` keeps its binding",
    ),
)


def git(repository: pathlib.Path, *arguments: str) -> str:
    """Run a git command in a repository and return what it printed.

    Args:
        repository: The checkout to run in.
        *arguments: The git subcommand and its arguments.

    Returns:
        Standard output, or the empty string when git failed.
    """
    return subprocess.run(
        ["git", "-C", str(repository), *arguments], capture_output=True, text=True, check=False
    ).stdout


def task_text(repository: pathlib.Path, counts: dict[str, collections.Counter[str]]) -> str:
    """Compose the task doc for one repository.

    Args:
        repository: The checkout the task is for.
        counts: For each language name present, tracked files per top-level directory.

    Returns:
        The Markdown text of the task.
    """
    github: str = re.sub(
        r"^.*github\.com[:/]|\.git$", "", git(repository, "remote", "get-url", "github").strip()
    )
    where: str = f"github.com/{github}" if github else "this repository"
    total: int = sum(sum(per_directory.values()) for per_directory in counts.values())
    difficulty: int = 3 if total <= 20 else 5 if total <= 150 else 7
    status: str = (
        "in progress (started 2026-11-25, on the maintainer's go-ahead for this repository)"
        if repository.name in IN_PROGRESS
        else "proposed — needs go-ahead"
    )
    rows: list[str] = []
    for language in LANGUAGES:
        if language.name not in counts:
            continue
        per_directory: collections.Counter[str] = counts[language.name]
        places: str = ", ".join(
            f"`{directory}` {count}" for directory, count in per_directory.most_common(6)
        )
        rows.append(
            f"| {language.name} | {sum(per_directory.values())} | {places} | {language.section} "
            f"| {language.difference} |"
        )
    table: str = "\n".join(rows)
    names: str = ", ".join(language.name for language in LANGUAGES if language.name in counts)
    return f"""# Apply the naming and scope rules, per language ({names})

**Status:** {status}
**Priority:** 7 (a readability sweep with no deadline)
**Difficulty:** {difficulty} ({total} tracked files in the languages below; the judgment is in which leads to leave alone)
**Created:** 2026-11-25 (William Emerison Six <billsix@gmail.com>: "make a task in all of my repos for my projects in /mnt/sda1 to apply them, per language", and the same day "make a task for all of them, but only start work on hanoi and spimulator").
**Source:** github.com/billsix/towersofhanoi `tasks/apply-naming-and-scope-rules-per-language-across-repositories.md` (the fleet task that wrote this one).

## BLUF

Five naming and scope rules are written for every language in the shared coding standards. This task applies them to the code in {where} that the maintainer wrote: survey for leads, apply by discretion, record what was left alone and why, and pass the repository's own gate. Done means each language in the table has been surveyed and either changed or recorded as left alone, with the gate green.

## Context

**The five rules:** inline a binding used once (a comment above the expression names it); a binding used twice does not automatically earn a name; declare a name at the point of use; nest a helper with one caller inside that caller, where the language has a nested function; shadow deliberately when nesting, where the language allows it. Each language's standard says how the rule reads there and which bindings must stay.

**Languages here** (tracked files, counted 2026-11-25 with `git ls-files`; paths matching `{VENDORED.pattern}` left out; a `.h` file counts as C even in a C++ tree):

| Language | Files | Where (top-level directory, files) | Section in {STANDARDS} | What differs from Python |
|---|---|---|---|---|
{table}

**Read first:** this repository's `CLAUDE.md` if it has one (its gate, its vendored and generated trees, whose code each tree is), then the standard's section for each language above.

**Whose code.** The cross-project rule is to sweep code the maintainer wrote and to leave another author's code alone: book examples, a game's original source, a vendored library and generated files are out of scope even when tracked. The first plan step settles this per tree.

**The pattern to copy** is the Python batch of 2026-11-25, github.com/billsix/towersofhanoi `tasks/archive/2026/11/25/apply-2026-11-06-naming-and-scope-rules.md`: it surveyed first, applied by discretion, left GUI and GL construction blocks and tests alone, kept helpers that a test imports or that name a step of a teaching method, and recorded each group it left with the reason.

**The survey tool.** `python3 ~/.claude/reference/survey_names_and_scope.py [--language rust] [--exclude REGEX]` (canonical in {STANDARDS}; Crush: `~/.config/crush/reference/`) lists functions named exactly twice and locals named exactly twice inside their function, for Rust, C++, C, Haskell, bash and JavaScript. Its counts are textual: a callback passed by name, a trait method and a name repeated in a comment are miscounted, so read every lead. For Python, `python3 ~/.claude/reference/nest_one_caller.py --dry-run FILE ...` lists the one-caller helpers and why it would skip each.

## Plan

- [ ] Settle scope: list the trees that are the maintainer's own code, and write the excluded ones here with the reason.
- [ ] Per language: run the survey, save its output under `tasks/adhoc/apply-naming-and-scope-rules-per-language/data/`, and read the leads.
- [ ] Per language: apply the rules by discretion, one commit-sized unit per language, keeping the bindings the standard lists (guards and RAII objects, out-parameter targets, values read before their source changes, calls made for a side effect, test inputs and case tables, names that carry the lesson in teaching code).
- [ ] Run the formatter on the changed files only, then the repository's gate (format, type-check or build, tests), and record the result.
- [ ] Write the done-record: what changed, what was left alone and why, per language.

## Open questions

None recorded. Scope (the first plan step) is the executor's call under the whose-code rule; ask only if a tree's authorship is unclear.
"""


def main() -> None:
    """Write the task doc into every project checkout that has code in a covered language."""
    for repository in sorted(path for path in CHECKOUTS.iterdir() if (path / ".git").exists()):
        if not MINE.search(git(repository, "remote", "-v")):
            print(f"{repository.name}: skipped, upstream-only")
            continue
        python_done: bool = any(
            (repository / "tasks" / "archive").glob("**/apply-2026-11-06-naming-and-scope-rules.md")
        )
        counts: dict[str, collections.Counter[str]] = {}
        for path in git(repository, "ls-files").splitlines():
            if VENDORED.search(path):
                continue
            for language in LANGUAGES:
                if path.endswith(language.suffixes) and not (
                    language.name == "Python" and python_done
                ):
                    directory: str = path.split("/")[0] if "/" in path else "(root)"
                    counts.setdefault(language.name, collections.Counter())[directory] += 1
        target: pathlib.Path = repository / TASK_PATH
        if not counts:
            print(f"{repository.name}: skipped, no code in a covered language")
        elif target.exists():
            print(f"{repository.name}: left alone, task already exists")
        else:
            target.parent.mkdir(exist_ok=True)
            target.write_text(task_text(repository, counts))
            print(f"{repository.name}: wrote {TASK_PATH} ({', '.join(counts)})")


if __name__ == "__main__":
    main()
