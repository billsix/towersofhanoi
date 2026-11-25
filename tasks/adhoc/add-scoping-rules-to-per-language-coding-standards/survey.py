"""List where the naming and scope rules fire in hanoi's Rust, C++, bash and JavaScript.

Read-only. For each language it prints two lead lists: functions whose name occurs
exactly twice in that language's files (a definition and one call, so a candidate for
"nest a helper with one caller"), and local bindings whose name occurs exactly twice
inside the function that declares them (a candidate for "inline a binding used once").
The counts are textual, so every line is a lead to read, not a finding.

Run from anywhere: ``python3 tasks/adhoc/<this-task>/survey.py > data/survey.txt``.
"""

import collections
import dataclasses
import enum
import json
import pathlib
import re
import subprocess

REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parents[3]

VENDORED: re.Pattern[str] = re.compile(r"elpa|/imgui/|doctest")


class Language(enum.Enum):
    """The four languages surveyed, valued by the label printed in the report."""

    RUST = "rust"
    CPP = "c++"
    BASH = "bash"
    JAVASCRIPT = "javascript"


def suffixes(language: Language) -> tuple[str, ...]:
    """Return the file suffixes that belong to a language.

    Args:
        language: The language to look up.

    Returns:
        The suffixes, each with its leading dot.

    Raises:
        ValueError: If the language has no suffixes recorded.
    """
    match language:
        case Language.RUST:
            return (".rs",)
        case Language.CPP:
            return (".cpp", ".hpp")
        case Language.BASH:
            return (".sh",)
        case Language.JAVASCRIPT:
            return (".js",)
        case _:
            raise ValueError(language)


def binding_pattern(language: Language) -> re.Pattern[str]:
    """Return the pattern that finds a local binding's name on a line.

    Args:
        language: The language whose declaration syntax to match.

    Returns:
        A pattern whose first group is the bound name.

    Raises:
        ValueError: If the language has no pattern recorded.
    """
    match language:
        case Language.RUST:
            return re.compile(r"^\s*let (?:mut )?(\w+)\s*[:=]")
        case Language.CPP:
            return re.compile(r"^\s*(?:const )?[\w:<>,\*& ]+?[ \*&](\w+)\s*(?:=|\{).*;\s*$")
        case Language.BASH:
            return re.compile(r"^\s*(?:local |declare |readonly )?(?:-\w+ )?(\w+)=")
        case Language.JAVASCRIPT:
            return re.compile(r"^\s*(?:const|let) (\w+)\s*=")
        case _:
            raise ValueError(language)


@dataclasses.dataclass(frozen=True)
class Function:
    """A function definition found by ctags."""

    name: str
    path: str
    line: int
    end: int
    scope: str


def functions_in(paths: list[str]) -> list[Function]:
    """Ask ctags for every function definition in the given files.

    Args:
        paths: Repository-relative paths of one language's files.

    Returns:
        The definitions, in ctags' order.
    """
    ctags: subprocess.CompletedProcess[str] = subprocess.run(
        ["ctags", "--output-format=json", "--fields=+neK", "-o", "-", *paths],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    tags: list[dict[str, object]] = [json.loads(line) for line in ctags.stdout.splitlines()]
    return [
        Function(
            name=str(tag["name"]),
            path=str(tag["path"]),
            line=int(str(tag["line"])),
            end=int(str(tag.get("end", tag["line"]))),
            scope=str(tag.get("scope", "")),
        )
        for tag in tags
        if tag.get("kind") in ("function", "method")
    ]


def with_ends(functions: list[Function], lines_of: dict[str, list[str]]) -> list[Function]:
    """Give every function an end line, and every function-free file one whole-file scope.

    ctags reports no end line for Rust or JavaScript, so a function without one is taken
    to run to the line before the next function in its file (or to the end of the file).
    A file with no functions at all (most shell scripts) is surveyed as a single scope.

    Args:
        functions: The definitions ctags found.
        lines_of: Each surveyed file's lines, by path.

    Returns:
        The definitions with usable end lines, followed by the whole-file scopes.
    """
    starts_of: dict[str, list[int]] = {
        path: sorted(function.line for function in functions if function.path == path)
        for path in lines_of
    }
    ended: list[Function] = [
        function
        if function.end > function.line
        else dataclasses.replace(
            function,
            end=min(
                (start - 1 for start in starts_of[function.path] if start > function.line),
                default=len(lines_of[function.path]),
            ),
        )
        for function in functions
    ]
    whole_files: list[Function] = [
        Function(name="", path=path, line=1, end=len(lines), scope="whole file")
        for path, lines in lines_of.items()
        if not starts_of[path]
    ]
    return ended + whole_files


def survey(language: Language, tracked: list[str]) -> None:
    """Print the two lead lists for one language.

    Args:
        language: The language to survey.
        tracked: Every tracked path in the repository.
    """
    paths: list[str] = [
        path for path in tracked if path.endswith(suffixes(language)) and not VENDORED.search(path)
    ]
    lines_of: dict[str, list[str]] = {
        path: (REPO_ROOT / path).read_text().splitlines() for path in paths
    }
    # word_counts: how often each identifier occurs across the language's files.
    word_counts: collections.Counter[str] = collections.Counter(
        word for lines in lines_of.values() for line in lines for word in re.findall(r"\w+", line)
    )
    functions: list[Function] = with_ends(functions_in(paths), lines_of)
    print(f"== {language.value}: {len(paths)} files, {len(functions)} functions")
    print("-- functions named exactly twice (definition and one call)")
    for function in functions:
        if function.name and word_counts[function.name] == 2:
            print(f"{function.path}:{function.line}: {function.name} [{function.scope}]")
    print("-- locals named exactly twice inside their function")
    pattern: re.Pattern[str] = binding_pattern(language)
    for function in functions:
        body: list[str] = lines_of[function.path][function.line - 1 : function.end]
        for offset, line in enumerate(body):
            found: re.Match[str] | None = pattern.match(line)
            if found is None:
                continue
            uses: int = sum(len(re.findall(rf"\b{found.group(1)}\b", row)) for row in body)
            if uses == 2:
                print(f"{function.path}:{function.line + offset}: {line.strip()}")


def main() -> None:
    """Survey each language in turn."""
    tracked: list[str] = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    for language in Language:
        survey(language, tracked)


if __name__ == "__main__":
    main()
