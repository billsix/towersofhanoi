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
    """A saved sequence of moves in default-label space (1-indexed).

    Attributes:
        name: The recipe's identifier, used as the registry key.
        disk_count: Disc count of the game when the recipe was captured.
        default_moves: The move sequence as ``(from, to)`` pairs of 1-indexed
            physical peg numbers (default-label space).
    """

    name: str
    disk_count: int
    default_moves: tuple[tuple[int, int], ...]


@dataclass
class Recorder:
    """Frontend-side log of moves, stored in default-label space.

    The frontend converts user-typed labels to default space before calling
    `record` — usually with `labels_to_towers(labelling, from, to)` plus a
    +1 to each physical index.

    Attributes:
        default_moves: Accumulated moves as ``(from, to)`` pairs of 1-indexed
            physical peg numbers.
    """

    default_moves: list[tuple[int, int]] = field(default_factory=list)

    def record(self, from_default: int, to_default: int) -> None:
        """Record a move expressed as 1-indexed physical pegs.

        The values are the labels that would have been visible under the
        default labelling.

        Args:
            from_default: Source peg, 1-indexed in default-label space.
            to_default: Destination peg, 1-indexed in default-label space.
        """
        self.default_moves.append((from_default, to_default))

    def reset(self) -> None:
        """Discard all recorded moves, resetting to an empty log."""
        self.default_moves.clear()

    def to_recipe(self, name: str, disk_count: int) -> Recipe:
        """Freeze the recorded moves into a named `Recipe`.

        Args:
            name: Identifier for the new recipe.
            disk_count: Disc count to record on the recipe.

        Returns:
            A `Recipe` holding a snapshot of the moves recorded so far.
        """
        return Recipe(
            name=name,
            disk_count=disk_count,
            default_moves=tuple(self.default_moves),
        )


@dataclass
class RecipeRegistry:
    """In-memory recipe store, scoped to a single CLI session.

    Attributes:
        _by_name: Saved recipes keyed by their name.
    """

    _by_name: dict[str, Recipe] = field(default_factory=dict)

    def save(self, recipe: Recipe) -> None:
        """Store `recipe`, replacing any existing recipe of the same name.

        Args:
            recipe: The recipe to save.
        """
        self._by_name[recipe.name] = recipe

    def get(self, name: str) -> Recipe | None:
        """Look up a recipe by name.

        Args:
            name: The recipe name to fetch.

        Returns:
            The matching `Recipe`, or None if no recipe has that name.
        """
        return self._by_name.get(name)

    def names(self) -> list[str]:
        """Return all saved recipe names.

        Returns:
            The recipe names, sorted alphabetically.
        """
        return sorted(self._by_name.keys())

    def __len__(self) -> int:
        """Return the number of saved recipes."""
        return len(self._by_name)

    def __contains__(self, name: str) -> bool:
        """Return whether a recipe with the given name is saved.

        Args:
            name: The recipe name to test for.

        Returns:
            True if a recipe of that name exists, otherwise False.
        """
        return name in self._by_name


@dataclass(frozen=True)
class StepResult:
    """One move's worth of `apply_iter` output.

    Attributes:
        from_label: The recipe's stored source value (default-label space).
        to_label: The recipe's stored destination value (default-label space).
        from_peg: 0-indexed physical peg the move actually hit, or None if the
            move could not be resolved to a peg.
        to_peg: 0-indexed physical destination peg, or None if unresolved.
        error: Failure message, or None if the move was applied successfully.
    """

    from_label: int
    to_label: int
    from_peg: int | None
    to_peg: int | None
    error: str | None

    @property
    def ok(self) -> bool:
        """Return whether the move succeeded (no error was recorded)."""
        return self.error is None


def apply_iter(
    recipe: Recipe, game: HanoiGame, labelling: Labelling
) -> Iterator[StepResult]:
    """Replay `recipe` against `game` under `labelling`.

    The recipe's stored default-space labels are interpreted as labels under
    `labelling`. Iteration stops after the first failure so the caller can
    surface the partial progress.

    No disk-count check: a recipe captured at one size may legitimately apply
    to a larger game (that's the whole point — using small solutions as
    sub-routines). Move legality is the gatekeeper, not size.

    Args:
        recipe: The saved move sequence to replay.
        game: The game to mutate as legal moves are applied.
        labelling: The labelling used to reinterpret the recipe's labels.

    Yields:
        One `StepResult` per move attempted, in order.
    """
    from_label: int
    to_label: int
    for from_label, to_label in recipe.default_moves:
        physical: tuple[int, int] | None = labels_to_towers(
            labelling, from_label, to_label
        )
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
    """Exhaust `apply_iter` and return all results.

    Args:
        recipe: The saved move sequence to replay.
        game: The game to mutate as legal moves are applied.
        labelling: The labelling used to reinterpret the recipe's labels.

    Returns:
        Every `StepResult` produced by replaying the recipe.
    """
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
    """Map each recipe label 1..3 to the 1-indexed physical peg it resolves to.

    Identity ((1,1),(2,2),(3,3)) under ONE_TWO_THREE.

    Args:
        labelling: The labelling to resolve the recipe labels through.

    Returns:
        One ``(label, peg)`` pair per label 1..3, with `peg` 1-indexed.
    """
    pairs: list[tuple[int, int]] = []
    label: int
    for label in (1, 2, 3):
        peg: Optional[int] = label_to_tower(labelling, label)
        assert peg is not None  # a label in 1..3 always resolves to a peg
        pairs.append((label, peg + 1))
    return tuple(pairs)


def format_rebinding(labelling: Labelling) -> list[str]:
    """Human-readable rebinding lines for the text (CLI/curses) frontends.

    Args:
        labelling: The active labelling.

    Returns:
        The rebinding explanation lines, or an empty list under the default
        labelling (there is no rebinding to show).
    """
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
    """Rewrite each move onto the 1-indexed physical pegs it lands on.

    Each move is a ``(from_label, to_label)`` pair. Pure (no game state);
    identity under ONE_TWO_THREE. Used for both a recipe's stored moves and a
    single just-typed move.

    Args:
        moves: The moves to rebind, as ``(from_label, to_label)`` pairs.
        labelling: The labelling to resolve the labels through.

    Returns:
        The moves rewritten as ``(from_peg, to_peg)`` pairs of 1-indexed
        physical pegs.
    """
    out: list[tuple[int, int]] = []
    from_label: int
    to_label: int
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
    """Render three aligned text columns.

    The text-frontend equivalent of the GUI's three-panel rebinding view::

        <left_header> | Rebinding (label -> peg) | Rebound (physical pegs)

    Left and right run one row per move and line up move-for-move; the middle is
    the 3-row label->peg key. Empty under the default labelling. `left_header`
    lets a single typed move say "Move (your labels)" while a recipe keeps the
    default -- the same table serves both `apply` and a plain move.

    Args:
        moves: The moves to display, as ``(from_label, to_label)`` pairs.
        labelling: The active labelling.
        left_header: Heading for the left column.

    Returns:
        The rendered table lines, or an empty list under the default labelling.
    """
    if labelling == Labelling.ONE_TWO_THREE:
        return []
    left: list[str] = [f"{i}: {a} -> {b}" for i, (a, b) in enumerate(moves, 1)]
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
        """Return `col[i]` left-justified to `width`, or blank padding.

        Args:
            col: The column of cell strings.
            i: Row index into `col`.
            width: Field width to pad to.

        Returns:
            The cell at row `i` padded to `width`, or `width` spaces if `i` is
            past the end of `col`.
        """
        return (col[i] if i < len(col) else "").ljust(width)

    lines: list[str] = [
        f"  {lhdr.ljust(lw)}   {mhdr.ljust(mw)}   {rhdr}",
        f"  {'-' * lw}   {'-' * mw}   {'-' * len(rhdr)}",
    ]
    i: int
    for i in range(rows):
        lines.append(
            f"  {cell(left, i, lw)}   {cell(mid, i, mw)}   {cell(right, i, 0)}"
        )
    return lines


def _explain_illegal(
    game: HanoiGame,
    from_peg: int,
    to_peg: int,
    from_label: int,
    to_label: int,
) -> str:
    """Build a human-readable reason a recipe move is illegal in this state.

    Args:
        game: The current game, inspected to diagnose the illegality.
        from_peg: 0-indexed source physical peg.
        to_peg: 0-indexed destination physical peg.
        from_label: The move's source value in default-label space.
        to_label: The move's destination value in default-label space.

    Returns:
        A sentence explaining why the move cannot be applied.
    """
    step: str = f"recipe move '{from_label} -> {to_label}'"
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
