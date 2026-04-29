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

from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Tuple

from .hanoimodel import HanoiGame
from .presenter import Labelling, labels_to_towers


@dataclass(frozen=True)
class Recipe:
    """A saved sequence of moves in default-label space (1-indexed)."""

    name: str
    disk_count: int
    default_moves: Tuple[Tuple[int, int], ...]


@dataclass
class Recorder:
    """Frontend-side log of moves, stored in default-label space.

    The frontend converts user-typed labels to default space before calling
    `record` — usually with `labels_to_towers(labelling, from, to)` plus a
    +1 to each physical index.
    """

    default_moves: List[Tuple[int, int]] = field(default_factory=list)

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

    def names(self) -> List[str]:
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
) -> List[StepResult]:
    """Convenience wrapper: exhaust `apply_iter` and return all results."""
    return list(apply_iter(recipe, game, labelling))


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
