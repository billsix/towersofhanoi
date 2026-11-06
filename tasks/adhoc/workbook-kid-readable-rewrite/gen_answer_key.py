"""Print the workbook's answer-key rows and check every sheet's solve.

Sheet n is built the way the booklet teaches: Step A copies Sheet n-1 with
the key 1->1, 2->3, 3->2; Step B is 1 -> 3; Step C copies Sheet n-1 with the
key 1->2, 2->1, 3->3.  Each sheet is replayed on a simulated board to prove
every move is legal and the sheet ends with all discs on peg 3.

Output is one LaTeX macro call per line, pasted into the answer-key section of
``workbook/induction-workbook.tex``:

    \\keyhead{n}                          heading for Sheet n
    \\keystep{A|B|C}                      step label
    \\keycopy{src}{k}{a}{b}{dst}{m}{c}{d} copied row: Sheet src move k = a->b,
                                         swapped to Sheet dst move m = c->d
    \\keyone{n}{m}{a}{b}                  a move with nothing copied

Usage: python3 gen_answer_key.py [max_sheet]   (default 5)
"""

import sys

Move = tuple[int, int]

KEY_A: dict[int, int] = {1: 1, 2: 3, 3: 2}
KEY_C: dict[int, int] = {1: 2, 2: 1, 3: 3}


def swap(move: Move, key: dict[int, int]) -> Move:
    """Return ``move`` with both peg numbers looked up in ``key``.

    >>> swap((3, 2), KEY_A)
    (2, 3)
    """
    source, target = move
    return (key[source], key[target])


def sheet(n: int) -> list[Move]:
    """Return Sheet ``n``'s moves, built from Sheet ``n - 1``.

    >>> sheet(3)
    [(1, 3), (1, 2), (3, 2), (1, 3), (2, 1), (2, 3), (1, 3)]
    """
    if n == 1:
        return [(1, 3)]
    previous: list[Move] = sheet(n - 1)
    step_a: list[Move] = [swap(m, KEY_A) for m in previous]
    step_c: list[Move] = [swap(m, KEY_C) for m in previous]
    return [*step_a, (1, 3), *step_c]


def check(n: int, moves: list[Move]) -> None:
    """Replay ``moves`` on an ``n``-disc board; raise if any move is illegal.

    >>> check(2, [(1, 2), (1, 3), (2, 3)])
    """
    pegs: dict[int, list[int]] = {1: list(range(n, 0, -1)), 2: [], 3: []}
    for source, target in moves:
        if not pegs[source]:
            raise ValueError(f"sheet {n}: peg {source} is empty")
        disc: int = pegs[source][-1]
        if pegs[target] and pegs[target][-1] < disc:
            raise ValueError(f"sheet {n}: disc {disc} onto a smaller disc")
        pegs[target].append(pegs[source].pop())
    if pegs[3] != list(range(n, 0, -1)) or len(moves) != 2**n - 1:
        raise ValueError(f"sheet {n}: not solved in 2^n - 1 moves")


def rows(n: int) -> list[str]:
    """Return the LaTeX answer-key lines for Sheet ``n``.

    >>> rows(2)[2]
    '\\\\keycopy{1}{1}{1}{3}{2}{1}{1}{2}'
    """
    moves: list[Move] = sheet(n)
    head: list[str] = [rf"\keyhead{{{n}}}"]
    if n == 1:
        return [*head, rf"\keyone{{1}}{{1}}{{1}}{{3}}"]
    previous: list[Move] = sheet(n - 1)
    half: int = len(previous)

    def copied(first: int) -> list[str]:
        return [
            rf"\keycopy{{{n - 1}}}{{{k + 1}}}{{{a}}}{{{b}}}"
            rf"{{{n}}}{{{first + k}}}{{{c}}}{{{d}}}"
            for k, ((a, b), (c, d)) in enumerate(
                zip(previous, moves[first - 1 : first - 1 + half])
            )
        ]

    return [
        *head,
        r"\keystep{A}",
        *copied(1),
        r"\keystep{B}",
        rf"\keyone{{{n}}}{{{half + 1}}}{{1}}{{3}}",
        r"\keystep{C}",
        *copied(half + 2),
    ]


def main() -> None:
    """Check sheets 1..max and print their answer-key lines."""
    last: int = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    for n in range(1, last + 1):
        check(n, sheet(n))
    print("\n".join(line for n in range(1, last + 1) for line in rows(n)))


if __name__ == "__main__":
    main()
