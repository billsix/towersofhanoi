"""Find function locals that break the 2026-11-06 naming and scope rules.

Walks the in-scope Python files with ``ast`` and reports, per function:

* ``ONCE``   -- a local assigned once and loaded once (rule 1: inline it),
  with the line distance from assignment to the load (rule 3).
* ``TWICE``  -- a local assigned once and loaded exactly twice (rule 2: look).
* ``FAR``    -- a local whose first load is more than ``FAR_LINES`` lines
  below its assignment (rule 3: declare at the point of use).
* ``ONE_CALLER`` -- a module-level function called from exactly one other
  function in its module and imported by no test (rule 4: nest it).

Module-level names are never reported: procedural programs use module globals
on purpose.  Writes ``data/candidates.txt`` next to this script.

Run from anywhere: ``python3 tasks/adhoc/<slug>/discover.py PATH [PATH ...]``,
each PATH a repository-relative directory or ``.py`` file; the script's own
directory is skipped.
"""

import ast
import collections
import pathlib
import sys
import typing

FAR_LINES: int = 10
REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parents[3]
SCOPE_PATHS: list[str] = sys.argv[1:]

FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


def in_scope_files() -> list[pathlib.Path]:
    """Return every in-scope ``.py`` file, sorted."""
    found: list[pathlib.Path] = sorted(
        path
        for scope_path in SCOPE_PATHS
        for path in (
            [REPO_ROOT / scope_path]
            if (REPO_ROOT / scope_path).is_file()
            else (REPO_ROOT / scope_path).rglob("*.py")
        )
        if pathlib.Path(__file__).parent not in path.parents
    )
    return found


def own_nodes(function: FunctionNode) -> typing.Iterator[ast.AST]:
    """Yield the nodes of ``function`` without entering nested functions."""
    pending: list[ast.AST] = list(function.body)
    while pending:
        node: ast.AST = pending.pop()
        yield node
        for child in ast.iter_child_nodes(node):
            match child:
                case ast.FunctionDef() | ast.AsyncFunctionDef() | ast.Lambda():
                    # a nested scope: its loads count as loads of ours
                    yield from ast.walk(child)
                case _:
                    pending.append(child)


def local_report(path: pathlib.Path, function: FunctionNode) -> list[str]:
    """Return the ONCE / TWICE / FAR lines for one function's locals."""
    stores: dict[str, list[int]] = collections.defaultdict(list)
    loads: dict[str, list[int]] = collections.defaultdict(list)
    declared_outer: set[str] = set()
    for node in own_nodes(function):
        match node:
            case ast.Global(names=names) | ast.Nonlocal(names=names):
                declared_outer.update(names)
            case ast.Name(id=name, ctx=ast.Store()):
                stores[name].append(node.lineno)
            case ast.Name(id=name, ctx=ast.Load()):
                loads[name].append(node.lineno)
            case _:
                pass
    rel: str = path.relative_to(REPO_ROOT).as_posix()
    lines: list[str] = []
    for name, store_lines in sorted(stores.items()):
        if name in declared_outer or len(store_lines) != 1:
            continue
        load_lines: list[int] = sorted(loads.get(name, []))
        where: str = f"{rel}:{store_lines[0]} {function.name}() {name}"
        match len(load_lines):
            case 1:
                gap: int = load_lines[0] - store_lines[0]
                lines.append(f"ONCE  {where} (load {gap} lines below)")
            case 2:
                lines.append(f"TWICE {where} (loads at {load_lines})")
            case 0:
                pass
            case _:
                if load_lines[0] - store_lines[0] > FAR_LINES:
                    gap = load_lines[0] - store_lines[0]
                    lines.append(f"FAR   {where} (first load {gap} lines below)")
    return lines


def one_caller_report(path: pathlib.Path, tree: ast.Module, tests: str) -> list[str]:
    """Return ONE_CALLER lines for module-level helpers in ``tree``."""
    functions: dict[str, FunctionNode] = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    callers: dict[str, set[str]] = collections.defaultdict(set)
    for caller in functions.values():
        for node in ast.walk(caller):
            match node:
                case ast.Name(id=name, ctx=ast.Load()) if (
                    name in functions and name != caller.name
                ):
                    callers[name].add(caller.name)
                case _:
                    pass
    module_loads: collections.Counter[str] = collections.Counter(
        node.id
        for top in tree.body
        if not isinstance(top, ast.FunctionDef | ast.AsyncFunctionDef)
        for node in ast.walk(top)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    )
    rel: str = path.relative_to(REPO_ROOT).as_posix()
    lines: list[str] = []
    for name, callers_of in sorted(callers.items()):
        if len(callers_of) != 1 or module_loads[name] or name in tests:
            continue
        (only,) = callers_of
        lines.append(
            f"ONE_CALLER {rel}:{functions[name].lineno} {name}() "
            f"is called only from {only}()"
        )
    return lines


def main() -> None:
    """Write the candidate worklog."""
    # a helper another test file names counts as having a second caller
    tests_text: str = "\n".join(
        path.read_text() for path in in_scope_files() if "test" in path.name
    )
    report: list[str] = []
    for path in in_scope_files():
        tree: ast.Module = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                report.extend(local_report(path, node))
        report.extend(one_caller_report(path, tree, tests_text))
    out: pathlib.Path = pathlib.Path(__file__).parent / "data" / "candidates.txt"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(report) + "\n")
    counts: collections.Counter[str] = collections.Counter(
        line.split()[0] for line in report
    )
    sys.stdout.write(f"{dict(counts)} -> {out.relative_to(REPO_ROOT)}\n")


if __name__ == "__main__":
    main()
