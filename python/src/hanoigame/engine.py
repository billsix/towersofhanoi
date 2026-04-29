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

"""Front-end-agnostic game session and command dispatcher.

`GameSession` owns one in-progress game (board state, current labelling,
move recorder) plus a pointer to the cross-game `RecipeRegistry`.
`dispatch(cmd)` turns any parsed `Command` into a `DispatchResult` with
display lines and a quit flag — frontends just have to render the lines
and respect quit.

This is what the CLI, curses, and (eventually) wxWidgets front-ends share,
so behaviour stays consistent across them.
"""

from dataclasses import dataclass, field
from typing import List

from .commands import (
    HELP_TEXT,
    ApplyCmd,
    Command,
    EmptyCmd,
    HelpCmd,
    ListCmd,
    MoveCmd,
    ParseError,
    QuitCmd,
    RelabelCmd,
    SaveCmd,
    ShowCmd,
)
from .hanoimodel import HanoiGame
from .presenter import (
    Labelling,
    change_labels_on_pegs,
    labelling_for,
    labels_to_towers,
)
from .recipe import RecipeRegistry, Recorder, apply_iter


@dataclass
class DispatchResult:
    """The fallout from `GameSession.dispatch`. The frontend renders `lines`
    in its message area and breaks its loop if `quit` is True."""

    lines: List[str] = field(default_factory=list)
    quit: bool = False


class GameSession:
    """One in-progress game plus the cross-game recipe registry.

    Mutates `self.labelling` on `RelabelCmd`, mutates `self.game` on
    successful moves and applies, mutates `self.recorder` on every
    successful move (typed or applied).
    """

    def __init__(self, num_disks: int, registry: RecipeRegistry) -> None:
        self.game = HanoiGame(num_disks=num_disks)
        self.labelling: Labelling = Labelling.ONE_TWO_THREE
        self.recorder = Recorder()
        self.registry = registry

    # --- Read-only helpers ------------------------------------------------

    @property
    def num_disks(self) -> int:
        return self.game.num_disks

    @property
    def current_moves(self) -> int:
        return self.game.current_moves

    def is_won(self) -> bool:
        return self.game.check_win_condition()

    def min_moves(self) -> int:
        return (2**self.num_disks) - 1

    def valid_moves_str(self) -> str:
        pairs = []
        for vm in self.game.move_options():
            f = change_labels_on_pegs(self.labelling, vm.move.from_peg) + 1
            t = change_labels_on_pegs(self.labelling, vm.move.to_peg) + 1
            pairs.append(f"{f} -> {t}")
        pairs.sort()
        return (
            "Valid moves: " + ", ".join(pairs) if pairs else "No valid moves."
        )

    # --- Recipe save (post-win, frontend triggers explicitly) -------------

    def save_recipe(self, name: str) -> str:
        """Save the current move sequence under `name`. Returns a one-line
        confirmation. Caller is responsible for not calling this mid-game."""
        recipe = self.recorder.to_recipe(name, disk_count=self.num_disks)
        overwrote = name in self.registry
        self.registry.save(recipe)
        if overwrote:
            return f"Overwrote recipe {name!r}."
        return f"Saved recipe {name!r}."

    # --- Dispatch ---------------------------------------------------------

    def dispatch(self, cmd: Command) -> DispatchResult:
        if isinstance(cmd, MoveCmd):
            return DispatchResult(lines=self._handle_move(cmd))
        if isinstance(cmd, RelabelCmd):
            return DispatchResult(lines=self._handle_relabel(cmd))
        if isinstance(cmd, ApplyCmd):
            return DispatchResult(lines=self._handle_apply(cmd))
        if isinstance(cmd, ShowCmd):
            return DispatchResult(lines=self._handle_show(cmd))
        if isinstance(cmd, ListCmd):
            return DispatchResult(lines=self._handle_list())
        if isinstance(cmd, SaveCmd):
            return DispatchResult(
                lines=[
                    "Save only works after winning a game. "
                    "Keep playing — you'll be prompted to name the recipe "
                    "when you finish."
                ]
            )
        if isinstance(cmd, HelpCmd):
            return DispatchResult(lines=HELP_TEXT.splitlines())
        if isinstance(cmd, QuitCmd):
            return DispatchResult(quit=True)
        if isinstance(cmd, EmptyCmd):
            return DispatchResult()
        if isinstance(cmd, ParseError):
            return DispatchResult(lines=[cmd.message])
        return DispatchResult(lines=[f"Unhandled command: {cmd!r}"])

    # --- Per-command handlers --------------------------------------------

    def _handle_move(self, cmd: MoveCmd) -> List[str]:
        physical = labels_to_towers(
            self.labelling, cmd.from_label, cmd.to_label
        )
        if physical is None:
            return [f"Label out of range: {cmd.from_label}, {cmd.to_label}."]
        fp, tp = physical

        for vm in self.game.move_options():
            if vm.move.from_peg == fp and vm.move.to_peg == tp:
                vm.action()
                # Recipe stores moves in default-label space (= physical+1).
                self.recorder.record(fp + 1, tp + 1)
                return []

        if not self.game.towers[fp]:
            return [f"Peg {cmd.from_label} is empty — nothing to move."]
        if (
            self.game.towers[tp]
            and self.game.towers[fp][-1] > self.game.towers[tp][-1]
        ):
            top_from = self.game.towers[fp][-1]
            top_to = self.game.towers[tp][-1]
            return [
                f"Can't put disc {top_from} on disc {top_to} "
                "— larger on smaller."
            ]
        return ["Invalid move."]

    def _handle_relabel(self, cmd: RelabelCmd) -> List[str]:
        new_labelling = labelling_for(cmd.labels)
        if new_labelling is None:
            return [f"No labelling matches {cmd.labels}."]
        self.labelling = new_labelling
        a, b, c = cmd.labels
        return [f"Relabelled: physical pegs 1,2,3 now show as {a},{b},{c}."]

    def _handle_apply(self, cmd: ApplyCmd) -> List[str]:
        recipe = self.registry.get(cmd.name)
        if recipe is None:
            return [
                f"No recipe named {cmd.name!r}. "
                "Try 'list' to see saved recipes."
            ]
        lines = [
            f"Applying recipe {recipe.name!r} "
            f"({len(recipe.default_moves)} moves):"
        ]
        for step, result in enumerate(
            apply_iter(recipe, self.game, self.labelling), start=1
        ):
            if result.ok:
                lines.append(
                    f"  step {step}: {result.from_label} -> {result.to_label}"
                )
                self.recorder.record(result.from_peg + 1, result.to_peg + 1)
            else:
                lines.append(f"  step {step}: stopped — {result.error}")
                return lines
        lines.append("Done.")
        return lines

    def _handle_show(self, cmd: ShowCmd) -> List[str]:
        recipe = self.registry.get(cmd.name)
        if recipe is None:
            return [
                f"No recipe named {cmd.name!r}. "
                "Try 'list' to see saved recipes."
            ]
        n_moves = len(recipe.default_moves)
        plural = "" if n_moves == 1 else "s"
        lines = [
            f"Recipe {recipe.name!r} "
            f"({recipe.disk_count} discs, {n_moves} move{plural}):"
        ]
        for i, (a, b) in enumerate(recipe.default_moves, 1):
            lines.append(f"  step {i}: {a} -> {b}")
        return lines

    def _handle_list(self) -> List[str]:
        if len(self.registry) == 0:
            return ["No recipes saved yet."]
        lines = ["Saved recipes:"]
        width = max(len(n) for n in self.registry.names())
        for name in self.registry.names():
            recipe = self.registry.get(name)
            lines.append(
                f"  {name:<{width}}  "
                f"({recipe.disk_count} discs, "
                f"{len(recipe.default_moves)} moves)"
            )
        return lines
