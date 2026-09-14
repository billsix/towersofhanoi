# Copyright (c) 2025 William Emerison Six
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""Recipes — saved sequences of moves the user can replay.

Recipes are stored in **default-label space** — i.e., 1-indexed physical
peg numbers (the labels that would have been visible under the default
ONE_TWO_THREE labelling). This makes a recipe independent of whatever
labelling was active when it was captured: the same physical sequence
gets the same recipe regardless of how the user had relabelled at the
time.

    1. Solve 2 discs from 1 to 3 under default labelling, save the recipe.
       Stored as ((1,2),(1,3),(2,3)) — same as what was typed.

    2. Or: relabel to (1,3,2) first, then solve 2 discs by typing
       '1 -> 3', '1 -> 2', '3 -> 2' (which under that labelling is the
       physical sequence (0,1),(0,2),(1,2)). Saved recipe is still
       ((1,2),(1,3),(2,3)) — the *physical* moves, normalised back to
       default labels.

At apply time, the recipe's default-space values are interpreted as labels
under the *current* labelling. So a recipe captured "1 -> 3" replayed under
labelling (1,3,2) finds the physical pegs that are *currently* labelled 1
and 3 — that's the relabel-and-replay teaching moment.

The model (HanoiGame) stays oblivious to recipes; the Recorder lives beside
it and is fed by the front-end after each successful move. The front-end
is responsible for translating user-typed labels into default space before
calling `record` — the helper `labels_to_towers` from `presenter` does the
work.
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Optional

from .hanoimodel import HanoiGame
from .presenter import Labelling, label_to_tower, labels_to_towers


@dataclass(frozen=True)
class Recipe:
    """A saved sequence of moves in default-label space (1-indexed)."""

    name: str
    disk_count: int
    default_moves: tuple[tuple[int, int], ...]


@dataclass
class Recorder:
    """Frontend-side log of moves, stored in default-label space.

    The frontend converts user-typed labels to default space before calling
    `record` — usually with `labels_to_towers(labelling, from, to)` plus a
    +1 to each physical index.
    """

    default_moves: list[tuple[int, int]] = field(default_factory=list)

    def record(self, from_default: int, to_default: int) -> None:
        """Record a move expressed as 1-indexed physical pegs (= the labels
        that would have been visible under the default labelling)."""
        self.default_moves.append((from_default, to_default))

    def reset(self) -> None:
        self.default_moves.clear()

    def to_recipe(self, name: str, disk_count: int) -> Recipe:
        return Recipe(
            name=name,
            disk_count=disk_count,
            default_moves=tuple(self.default_moves),
        )


class RecipeRegistry:
    """In-memory recipe store, scoped to a single CLI session."""

    def __init__(self) -> None:
        self._by_name: dict[str, Recipe] = {}

    def save(self, recipe: Recipe) -> None:
        self._by_name[recipe.name] = recipe

    def get(self, name: str) -> Optional[Recipe]:
        return self._by_name.get(name)

    def names(self) -> list[str]:
        return sorted(self._by_name.keys())

    def __len__(self) -> int:
        return len(self._by_name)

    def __contains__(self, name: str) -> bool:
        return name in self._by_name


@dataclass(frozen=True)
class StepResult:
    """One move's worth of `apply_iter` output."""

    from_label: int  # the recipe's stored value (default-label space)
    to_label: int
    from_peg: Optional[int]  # 0-indexed physical peg the move actually hit
    to_peg: Optional[int]
    error: Optional[str]  # None if the move was applied successfully

    @property
    def ok(self) -> bool:
        return self.error is None


def apply_iter(
    recipe: Recipe, game: HanoiGame, labelling: Labelling
) -> Iterator[StepResult]:
    """Replay `recipe` against `game`, interpreting the recipe's stored
    default-space labels as labels under `labelling`.

    Yields one StepResult per move attempted. Stops after the first failure
    so the caller can surface the partial progress.

    No disk-count check: a recipe captured at one size may legitimately apply
    to a larger game (that's the whole point — using small solutions as
    sub-routines). Move legality is the gatekeeper, not size.
    """
    for from_label, to_label in recipe.default_moves:
        physical = labels_to_towers(labelling, from_label, to_label)
        if physical is None:
            yield StepResult(
                from_label=from_label,
                to_label=to_label,
                from_peg=None,
                to_peg=None,
                error=(
                    f"Recipe move '{from_label} -> {to_label}' uses a label "
                    "that doesn't exist under the current labelling."
                ),
            )
            return
        fp, tp = physical

        action = None
        for vm in game.move_options():
            if vm.move.from_peg == fp and vm.move.to_peg == tp:
                action = vm.action
                break

        if action is None:
            yield StepResult(
                from_label=from_label,
                to_label=to_label,
                from_peg=fp,
                to_peg=tp,
                error=_explain_illegal(game, fp, tp, from_label, to_label),
            )
            return

        action()
        yield StepResult(
            from_label=from_label,
            to_label=to_label,
            from_peg=fp,
            to_peg=tp,
            error=None,
        )


def apply(
    recipe: Recipe, game: HanoiGame, labelling: Labelling
) -> list[StepResult]:
    """Convenience wrapper: exhaust `apply_iter` and return all results."""
    return list(apply_iter(recipe, game, labelling))


# --- The rebinding: recipe's local labels -> global (physical) pegs ---------
#
# The teaching moment (see tasks/record-recipe-bindings-and-show-rebinding.md):
# a recipe's moves are written in its own labels 1,2,3. Replaying under a
# relabelling reinterprets each label as "the peg currently wearing it", so
# label l lands on physical peg label_to_tower(labelling, l) + 1. A student
# must SEE that local->global rebinding when a recipe is replayed in a
# relabelled context -- it is why the sub-solution's labels change.


def rebinding(labelling: Labelling) -> tuple[tuple[int, int], ...]:
    """For each recipe label in 1..3, the 1-indexed physical peg it resolves
    to under `labelling`. Identity ((1,1),(2,2),(3,3)) under ONE_TWO_THREE."""
    pairs: list[tuple[int, int]] = []
    for label in (1, 2, 3):
        peg: Optional[int] = label_to_tower(labelling, label)
        assert peg is not None  # a label in 1..3 always resolves to a peg
        pairs.append((label, peg + 1))
    return tuple(pairs)


def format_rebinding(labelling: Labelling) -> list[str]:
    """Human-readable rebinding lines for the text (CLI/curses) frontends.
    Empty under the default labelling -- there is no rebinding to show."""
    if labelling == Labelling.ONE_TWO_THREE:
        return []
    body: str = ",  ".join(
        f"label {label} -> peg {peg}" for label, peg in rebinding(labelling)
    )
    return [
        "  Rebinding (this recipe's labels -> physical pegs, because you "
        "relabelled):",
        f"    {body}",
        "    Each move below is the recorded label, rebound to the peg after "
        "'->'.",
    ]


def rebound_moves(
    moves: Sequence[tuple[int, int]], labelling: Labelling
) -> tuple[tuple[int, int], ...]:
    """Each move (a ``(from_label, to_label)`` pair) rewritten onto 1-indexed
    physical pegs under `labelling` -- the move rebound to where it actually
    happens. Pure (no game state); identity under ONE_TWO_THREE. Used for both
    a recipe's stored moves and a single just-typed move."""
    out: list[tuple[int, int]] = []
    for from_label, to_label in moves:
        fp: Optional[int] = label_to_tower(labelling, from_label)
        tp: Optional[int] = label_to_tower(labelling, to_label)
        assert fp is not None and tp is not None  # labels are 1..3
        out.append((fp + 1, tp + 1))
    return tuple(out)


def format_rebinding_table(
    moves: Sequence[tuple[int, int]],
    labelling: Labelling,
    left_header: str = "Recipe (its labels)",
) -> list[str]:
    """Three aligned text columns -- the text-frontend equivalent of the GUI's
    three-panel rebinding view:

        <left_header> | Rebinding (label -> peg) | Rebound (physical pegs)

    Left and right run one row per move and line up move-for-move; the middle is
    the 3-row label->peg key. Empty under the default labelling. `left_header`
    lets a single typed move say "Move (your labels)" while a recipe keeps the
    default -- the same table serves both `apply` and a plain move.
    """
    if labelling == Labelling.ONE_TWO_THREE:
        return []
    left: list[str] = [
        f"{i}: {a} -> {b}" for i, (a, b) in enumerate(moves, 1)
    ]
    mid: list[str] = [
        f"label {label} -> peg {peg}" for label, peg in rebinding(labelling)
    ]
    right: list[str] = [
        f"{i}: {fp} -> {tp}"
        for i, (fp, tp) in enumerate(rebound_moves(moves, labelling), 1)
    ]
    lhdr, mhdr, rhdr = left_header, "Rebinding", "Rebound (pegs)"
    lw: int = max([len(lhdr), *(len(s) for s in left)])
    mw: int = max([len(mhdr), *(len(s) for s in mid)])
    rows: int = max(len(left), len(mid), len(right))

    def cell(col: list[str], i: int, width: int) -> str:
        return (col[i] if i < len(col) else "").ljust(width)

    lines: list[str] = [
        f"  {lhdr.ljust(lw)}   {mhdr.ljust(mw)}   {rhdr}",
        f"  {'-' * lw}   {'-' * mw}   {'-' * len(rhdr)}",
    ]
    for i in range(rows):
        lines.append(
            f"  {cell(left, i, lw)}   {cell(mid, i, mw)}   "
            f"{cell(right, i, 0)}"
        )
    return lines


def _explain_illegal(
    game: HanoiGame,
    from_peg: int,
    to_peg: int,
    from_label: int,
    to_label: int,
) -> str:
    step = f"recipe move '{from_label} -> {to_label}'"
    if not game.towers[from_peg]:
        return f"{step}: peg {from_label} (physical {from_peg + 1}) is empty."
    if (
        game.towers[to_peg]
        and game.towers[from_peg][-1] > game.towers[to_peg][-1]
    ):
        return (
            f"{step}: would put disc {game.towers[from_peg][-1]} on disc "
            f"{game.towers[to_peg][-1]} — larger on smaller."
        )
    return f"{step}: illegal in current state."
