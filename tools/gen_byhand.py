#!/usr/bin/env python3
"""Generate docs/source/byhand4.rst and byhand5.rst, mirroring byhand3.rst exactly.

For tasks/complete-byhand-book-n4-n5.md. Each byhandN page has four sections in order:
1to3 (the concrete solve), ItoG (the I/T/G generalization of 1to3), then 1to2 and 2to3
(substitutions of ItoG). This is correct-by-construction: the move sequences come from the
standard optimal-Hanoi recursion, and the three derived orientations are digit remaps of the
base solve -- the same substitution byhand3 documents in prose. Idempotent: rerunning writes
byte-identical files. Paths are resolved relative to the repo root, so it runs from anywhere.

Run (from anywhere):  python3 tools/gen_byhand.py

When to run: only if byhand4/5's format must change (or to add byhand6, byhand7, ...) -- these
pages are generated, not hand-edited. Regenerate and rebuild the book to confirm.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs" / "source"

LICENSE = """\
..
   Copyright (c) 2026 William Emerison Six

   Permission is granted to copy, distribute and/or modify this document
   under the terms of the GNU Free Documentation License, Version 1.3
   or any later version published by the Free Software Foundation;
   with no Invariant Sections, no Front-Cover Texts, and no Back-Cover Texts.

   A copy of the license is available at
   https://www.gnu.org/licenses/fdl-1.3.html.
"""

Move = tuple[int, int]


def solve(n: int, src: int, dst: int) -> list[Move]:
    """Optimal moves to shift n discs from peg src to peg dst (pegs are 1,2,3)."""
    if n == 0:
        return []
    spare = 6 - src - dst
    return solve(n - 1, src, spare) + [(src, dst)] + solve(n - 1, spare, dst)


def remap(moves: list[Move], m: dict[int, object]) -> list[tuple[object, object]]:
    """Apply a per-peg substitution to every move."""
    return [(m[a], m[b]) for a, b in moves]


def move_table(rows: list[tuple[object, object]]) -> str:
    """A From/To grid table in byhand3's format (single-character cell values)."""
    out = ["+------+------+", "| From | To   |", "+======+======+"]
    for a, b in rows:
        out.append(f"|{a}     | {b}    |")
        out.append("+------+------+")
    return "\n".join(out)


def ref_table(n: int) -> str:
    """The sub-problem :ref: link table for the 1->3 section (reuses the n-1 solves)."""
    texts = [
        f":ref:`{n - 1} discs, from peg 1 to peg 2 <{n - 1}-1to2>`",
        ":ref:`1 discs, from peg 1 to peg 3 <1-1to3>`",
        f":ref:`{n - 1} discs, from peg 2 to peg 3 <{n - 1}-2to3>`",
    ]
    inner = max(len(t) for t in texts) + 3  # leading space + text + >=2 trailing
    border = "+" + "-" * inner + "+"
    lines = [border]
    for t in texts:
        lines.append("| " + t + " " * (inner - 1 - len(t)) + "|")
        lines.append(border)
    return "\n".join(lines)


def diagram(n: int, left: int, right: int, labels: tuple[str, str, str]) -> str:
    """byhand3-style start->goal picture: the full n-disc stack on peg `left` moving to
    peg `right` (0-based peg indices); `labels` names the three pegs (1/2/3 or I/T/G)."""
    base_w = (
        2 * n + 3
    )  # widest disc is (2n-1)+2 chars; +2 padding, and odd like byhand3

    def centre(s: str) -> str:
        pad = base_w - len(s)
        lead = pad // 2
        return " " * lead + s + " " * (pad - lead)

    def cell(has_stack: bool, row: int) -> str:
        # row 0 is the pole tip; rows 1..n hold discs 1..n (smallest at top).
        if has_stack and row >= 1:
            return centre("[" + "*" * (2 * row - 1) + "]")
        return centre("|")

    indent = " " * 3
    gap = "  "

    def block(stack_peg: int, row: int) -> str:
        return gap.join(cell(p == stack_peg, row) for p in range(3))

    lines = []
    for row in range(n + 1):  # pole tip + n disc rows
        sep = " " * 7
        lines.append(indent + block(left, row) + sep + block(right, row))
    base_block = gap.join("=" * base_w for _ in range(3))
    lines.append(indent + base_block + "  ->   " + base_block)
    label_block = gap.join(centre("Peg " + lbl) for lbl in labels)
    lines.append(indent + label_block + " " * 7 + label_block)
    return "\n".join(lines)


def section(
    anchor: str,
    blank_after_anchor: int,
    heading: str,
    prose: str,
    rows: list[tuple[object, object]],
    diag: str,
    ref_tbl: str | None = None,
) -> str:
    parts = [f".. _{anchor}:"]
    parts.append("\n" * blank_after_anchor + heading)
    parts.append("~" * len(heading))
    parts.append("")
    parts.append(prose)
    if ref_tbl is not None:
        parts.append("")
        parts.append(ref_tbl)
        parts.append("")
        parts.append("The results are the following")
    parts.append("")
    parts.append("")
    parts.append(move_table(rows))
    parts.append("")
    parts.append("")
    parts.append("")
    parts.append("::")
    parts.append("")
    parts.append(diag)
    return "\n".join(parts)


def page(n: int) -> str:
    base = solve(n, 1, 3)
    itog = remap(base, {1: "I", 2: "T", 3: "G"})
    to12 = remap(base, {1: 1, 2: 3, 3: 2})  # ItoG with I->1,T->3,G->2
    to23 = remap(base, {1: 2, 2: 1, 3: 3})  # ItoG with I->2,T->1,G->3

    title = f"Solve For {n}"
    stars = "*" * len(title)

    body = [
        LICENSE,
        f"{stars}\n{title}\n{stars}",
        section(
            f"{n}-1to3",
            1,
            "From 1 to 3",
            "Follow the links below, and write down their steps",
            base,
            diagram(n, 0, 2, ("1", "2", "3")),
            ref_tbl=ref_table(n),
        ),
        section(
            f"{n}-ItoG",
            2,
            "From I to G",
            "Take :ref:`solution above <" + f"{n}-1to3" + ">` - substitute variable "
            '"I" for 1, "T" for 2, "G" for 3.\n"I" means initial peg, "T" means '
            'temporary peg, and "G" means goal peg.',
            itog,
            diagram(n, 0, 2, ("I", "T", "G")),
        ),
        section(
            f"{n}-1to2",
            1,
            "From 1 to 2",
            'Take :ref:`solution from "I" to "G" <' + f"{n}-ItoG" + ">` .  "
            'Substitute 1 for "I", 3 for "T", 2 for "G".',
            to12,
            diagram(n, 0, 1, ("1", "2", "3")),
        ),
        section(
            f"{n}-2to3",
            1,
            "From 2 to 3",
            'Take :ref:`solution from "I" to "G" <' + f"{n}-ItoG" + ">`.  "
            'Substitute 2 for "I", 1 for "T", 3 for "G".',
            to23,
            diagram(n, 1, 2, ("1", "2", "3")),
        ),
    ]
    return "\n\n".join(body) + "\n"


def selfcheck() -> None:
    """The n=3 solves must match byhand3.rst's known-correct tables."""
    assert solve(3, 1, 3) == [(1, 3), (1, 2), (3, 2), (1, 3), (2, 1), (2, 3), (1, 3)]
    assert remap(solve(3, 1, 3), {1: 1, 2: 3, 3: 2}) == [
        (1, 2),
        (1, 3),
        (2, 3),
        (1, 2),
        (3, 1),
        (3, 2),
        (1, 2),
    ]
    assert remap(solve(3, 1, 3), {1: 2, 2: 1, 3: 3}) == [
        (2, 3),
        (2, 1),
        (3, 1),
        (2, 3),
        (1, 2),
        (1, 3),
        (2, 3),
    ]
    # move counts
    assert len(solve(4, 1, 3)) == 15
    assert len(solve(5, 1, 3)) == 31


def main() -> None:
    selfcheck()
    for n in (4, 5):
        path = DOCS / f"byhand{n}.rst"
        path.write_text(page(n))
        print(f"wrote {path.relative_to(REPO_ROOT)} ({len(solve(n, 1, 3))} moves)")


if __name__ == "__main__":
    main()
