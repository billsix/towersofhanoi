"""Move a top-level JavaScript function inside the one function that calls it.

Usage: ``python3 nest_js_fn.py FILE HELPER CALLER``.

The helper's declaration (its ``/** ... */`` JSDoc block, the signature and the body)
is cut from where it stands and pasted at the top of the caller's body, indented one
level.  Braces are matched textually, which is right
as long as every string in the helper holds balanced braces (template literals do).  The
script refuses to act unless it finds exactly one definition of each function, and it
does nothing when the helper is already inside the caller, so a second run changes
nothing.  Run ``deno fmt`` afterwards; it does not reflow comments, so check those.
"""

import pathlib
import re
import sys


def item_span(lines: list[str], name: str) -> tuple[int, int, int]:
    """Find one function item by name.

    Args:
        lines: The file's lines, without line endings.
        name: The function's name.

    Returns:
        The index of the item's first line (JSDoc block included), the
        index of the line that opens its body, and the index of its closing-brace line.

    Raises:
        SystemExit: If the function is not defined exactly once.
    """
    signature: re.Pattern[str] = re.compile(rf"^\s*(?:async )?function {name}\(")
    found: list[int] = [index for index, line in enumerate(lines) if signature.match(line)]
    if len(found) != 1:
        raise SystemExit(f"{name}: expected one definition, found {len(found)}")
    opening: int = next(
        index for index in range(found[0], len(lines)) if lines[index].rstrip().endswith("{")
    )
    depth: int = 0
    closing: int = opening
    for index in range(opening, len(lines)):
        depth += lines[index].count("{") - lines[index].count("}")
        if depth == 0:
            closing = index
            break
    first: int = found[0]
    if first > 0 and lines[first - 1].strip() == "*/":
        while not lines[first].lstrip().startswith("/**"):
            first -= 1
    return first, opening, closing


def main() -> None:
    """Nest the helper named on the command line inside the caller named after it."""
    path: pathlib.Path = pathlib.Path(sys.argv[1])
    helper: str = sys.argv[2]
    caller: str = sys.argv[3]
    lines: list[str] = path.read_text().splitlines()
    helper_first, _, helper_closing = item_span(lines, helper)
    caller_first, _, caller_closing = item_span(lines, caller)
    if caller_first <= helper_first <= caller_closing:
        print(f"{helper}: already inside {caller}, nothing to do")
        return
    item: list[str] = lines[helper_first : helper_closing + 1]
    # Drop the helper, and the blank line that followed it, from its old place.
    rest: list[str] = lines[:helper_first] + lines[helper_closing + 1 :]
    if helper_first < len(rest) and not rest[helper_first].strip():
        del rest[helper_first]
    _, caller_opening, _ = item_span(rest, caller)
    indent: str = re.match(r"\s*", rest[caller_opening + 1]).group(0)
    nested: list[str] = [(indent + line) if line.strip() else "" for line in item]
    rest[caller_opening + 1 : caller_opening + 1] = [*nested, ""]
    path.write_text("\n".join(rest) + "\n")
    print(f"{helper}: nested inside {caller}")


if __name__ == "__main__":
    main()
