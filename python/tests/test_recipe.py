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

"""Tests for the recipe layer.

The marquee test is `test_apply_recipe_through_relabel_solves_subproblem`,
which encodes Bill's worked example: a 2-disc-from-1-to-3 recipe captured
under the default labelling, then applied to a 3-disc game after swapping
labels 2 and 3, lands the top two discs on physical peg 1 — the first
"recursive" step of solving 3 discs.
"""

from collections.abc import Iterator

from hanoigame.commands import MoveCmd, RelabelCmd
from hanoigame.engine import GameSession
from hanoigame.hanoimodel import HanoiGame, ValidMove
from hanoigame.presenter import Labelling, labels_to_towers
from hanoigame.recipe import (
    Recipe,
    RecipeRegistry,
    Recorder,
    StepResult,
    apply,
    apply_iter,
    format_rebinding,
    format_rebinding_table,
    rebinding,
    rebound_moves,
)


def _play_labeled(
    game: HanoiGame,
    labelling: Labelling,
    moves: list[tuple[int, int]],
    recorder: Recorder,
) -> None:
    """Apply a sequence of user-typed (label, label) moves to `game`,
    recording each into `recorder` in default-label space — the same
    translation the front-end does."""
    from_label: int
    to_label: int
    for from_label, to_label in moves:
        physical: tuple[int, int] | None = labels_to_towers(
            labelling, from_label, to_label
        )
        assert physical is not None, (from_label, to_label)
        fp: int
        tp: int
        fp, tp = physical
        vm: ValidMove
        for vm in game.move_options():
            if vm.move.from_peg == fp and vm.move.to_peg == tp:
                vm.action()
                break
        else:
            raise AssertionError(
                f"move {from_label}->{to_label} is illegal here"
            )
        recorder.record(fp + 1, tp + 1)


# --- The recipe -> physical-peg rebinding (the teaching step) -------------


def test_rebinding_identity_under_default() -> None:
    """Under the default labelling the rebinding is the identity."""
    assert rebinding(Labelling.ONE_TWO_THREE) == ((1, 1), (2, 2), (3, 3))


def test_rebinding_under_relabel() -> None:
    """A relabelling maps each recipe label to the peg now wearing it."""
    # ONE_THREE_TWO: physical pegs 0,1,2 carry labels 1,3,2, so recipe
    # label 1 -> peg 1, label 2 -> peg 3, label 3 -> peg 2.
    assert rebinding(Labelling.ONE_THREE_TWO) == ((1, 1), (2, 3), (3, 2))


def test_rebinding_covers_all_six_labellings() -> None:
    """Every labelling rebinds labels {1,2,3} onto a permutation of pegs."""
    # Every labelling yields a permutation of pegs {1,2,3}, one per label.
    lab: Labelling
    for lab in Labelling:
        pairs: tuple[tuple[int, int], ...] = rebinding(lab)
        assert [label for label, _ in pairs] == [1, 2, 3]
        assert sorted(peg for _, peg in pairs) == [1, 2, 3]


def test_format_rebinding_empty_under_default() -> None:
    """No rebinding lines are emitted under the default labelling."""
    # No relabelling -> nothing to teach, so no lines are emitted.
    assert format_rebinding(Labelling.ONE_TWO_THREE) == []


def test_format_rebinding_shows_the_mapping_when_relabelled() -> None:
    """A relabelling produces human-readable label -> peg mapping lines."""
    joined: str = "\n".join(format_rebinding(Labelling.ONE_THREE_TWO))
    assert "label 2 -> peg 3" in joined
    assert "label 3 -> peg 2" in joined


def test_rebound_moves_identity_under_default() -> None:
    """Rebinding moves under the default labelling leaves them unchanged."""
    moves: tuple[tuple[int, int], ...] = ((1, 2), (1, 3), (2, 3))
    assert rebound_moves(moves, Labelling.ONE_TWO_THREE) == (
        (1, 2),
        (1, 3),
        (2, 3),
    )


def test_rebound_moves_under_relabel() -> None:
    """Each move's labels are rewritten to the pegs those labels now sit on."""
    # ONE_THREE_TWO: label 1->peg 1, 2->peg 3, 3->peg 2. So each move's
    # labels are rewritten to the pegs those labels currently sit on.
    moves: tuple[tuple[int, int], ...] = ((1, 2), (1, 3), (2, 3))
    assert rebound_moves(moves, Labelling.ONE_THREE_TWO) == (
        (1, 3),
        (1, 2),
        (3, 2),
    )


def test_rebound_moves_single_typed_move() -> None:
    """The rebinding helper also rebinds a single just-typed move."""
    # The same helper serves a single just-typed move (current-label pair).
    assert rebound_moves([(2, 3)], Labelling.ONE_THREE_TWO) == ((3, 2),)


def test_format_rebinding_table_empty_under_default() -> None:
    """The rebinding table is empty under the default labelling."""
    moves: tuple[tuple[int, int], ...] = ((1, 2), (1, 3), (2, 3))
    assert format_rebinding_table(moves, Labelling.ONE_TWO_THREE) == []


def test_format_rebinding_table_has_all_three_panels() -> None:
    """The rebinding table shows recipe, key, and rebound-peg panels."""
    moves: tuple[tuple[int, int], ...] = ((1, 2), (1, 3), (2, 3))
    joined: str = "\n".join(
        format_rebinding_table(moves, Labelling.ONE_THREE_TWO)
    )
    # the three panel headers
    assert "Recipe (its labels)" in joined
    assert "Rebinding" in joined
    assert "Rebound (pegs)" in joined
    # recipe move 1 (left), a key row (middle), and its rebound move (right)
    assert "1: 1 -> 2" in joined
    assert "label 2 -> peg 3" in joined
    assert "1: 1 -> 3" in joined


def test_format_rebinding_table_custom_left_header_for_a_move() -> None:
    """A custom left header lets a single typed move reuse the table."""
    # A single typed move reuses the same table with its own header.
    joined: str = "\n".join(
        format_rebinding_table(
            [(2, 3)], Labelling.ONE_THREE_TWO, left_header="Move (your labels)"
        )
    )
    assert "Move (your labels)" in joined
    assert "1: 2 -> 3" in joined  # left: as typed
    assert "1: 3 -> 2" in joined  # right: rebound to pegs


def test_move_teaching_lines_only_for_a_relabelled_successful_move() -> None:
    """Teaching lines appear only for a legal move under a relabelling."""
    reg: RecipeRegistry = RecipeRegistry()
    # Default labelling: a move gets no teaching table.
    s: GameSession = GameSession(num_disks=3, registry=reg)
    cmd: MoveCmd = MoveCmd(1, 2)
    assert s.move_teaching_lines(cmd, s.dispatch(cmd)) == []

    # Relabelled + a legal move: the three-column table, headed "Move ...".
    s2: GameSession = GameSession(num_disks=3, registry=reg)
    s2.dispatch(RelabelCmd((1, 3, 2)))
    good: MoveCmd = MoveCmd(1, 2)
    lines: list[str] = s2.move_teaching_lines(good, s2.dispatch(good))
    assert any("Move (your labels)" in ln for ln in lines)

    # Relabelled but an illegal move (from an empty peg): no teaching, because
    # dispatch produced an error line.
    s3: GameSession = GameSession(num_disks=3, registry=reg)
    s3.dispatch(RelabelCmd((1, 3, 2)))
    bad: MoveCmd = MoveCmd(2, 3)  # label 2 is an empty peg on a fresh board
    assert s3.move_teaching_lines(bad, s3.dispatch(bad)) == []


# --- Recorder + Recipe basics --------------------------------------------


def test_recorder_to_recipe_round_trip() -> None:
    """A Recorder converts its logged moves into a matching Recipe."""
    rec: Recorder = Recorder()
    rec.record(1, 3)
    rec.record(1, 2)
    recipe: Recipe = rec.to_recipe("two-moves", disk_count=2)
    assert recipe.name == "two-moves"
    assert recipe.disk_count == 2
    assert recipe.default_moves == ((1, 3), (1, 2))


def test_recorder_reset_clears_moves() -> None:
    """Resetting a Recorder discards its recorded moves."""
    rec: Recorder = Recorder()
    rec.record(1, 3)
    rec.reset()
    assert rec.default_moves == []


# --- Registry ------------------------------------------------------------


def test_registry_save_and_get() -> None:
    """The registry stores recipes by name and reports membership and size."""
    reg: RecipeRegistry = RecipeRegistry()
    r: Recipe = Recipe(name="foo", disk_count=2, default_moves=((1, 3),))
    reg.save(r)
    assert reg.get("foo") is r
    assert reg.get("bar") is None
    assert reg.names() == ["foo"]
    assert "foo" in reg
    assert len(reg) == 1


def test_registry_save_overwrites_same_name() -> None:
    """Saving a recipe under an existing name replaces the earlier one."""
    reg: RecipeRegistry = RecipeRegistry()
    reg.save(Recipe("foo", 2, ((1, 3),)))
    reg.save(Recipe("foo", 3, ((1, 2),)))
    recipe: Recipe | None = reg.get("foo")
    assert recipe is not None
    assert recipe.default_moves == ((1, 2),)
    assert len(reg) == 1


def test_registry_names_sorted() -> None:
    """`names` returns saved recipe names in sorted order."""
    reg: RecipeRegistry = RecipeRegistry()
    reg.save(Recipe("zebra", 2, ()))
    reg.save(Recipe("alpha", 2, ()))
    assert reg.names() == ["alpha", "zebra"]


# --- apply_iter end-to-end -----------------------------------------------


def test_apply_recipe_same_labelling() -> None:
    """Sanity: solve 2 discs, save, replay on a fresh 2-disc game with the
    same labelling. End state is the won state."""
    g: HanoiGame = HanoiGame(num_disks=2)
    rec: Recorder = Recorder()
    L: Labelling = Labelling.ONE_TWO_THREE
    _play_labeled(g, L, [(1, 2), (1, 3), (2, 3)], rec)
    assert g.check_win_condition()
    recipe: Recipe = rec.to_recipe("solve2", disk_count=2)

    g2: HanoiGame = HanoiGame(num_disks=2)
    results: list[StepResult] = apply(recipe, g2, L)
    assert all(r.ok for r in results)
    assert g2.towers == [[], [], [2, 1]]
    assert g2.current_moves == 3


def test_recipe_normalises_to_default_label_space_at_save_time() -> None:
    """Bill's tightening: a recipe stored independently of save-time
    labelling. Capture a 2-disc-from-1-to-3 solve while a non-default
    labelling is active. The recipe should hold the *physical* moves
    expressed as default labels (= physical+1), NOT the labels the user
    typed under the active labelling."""
    g: HanoiGame = HanoiGame(num_disks=2)
    rec: Recorder = Recorder()

    # Under labelling (1,3,2) physical pegs 0,1,2 carry labels 1,3,2.
    # Optimal "1 -> 3" solve in label-space is 1->2, 1->3, 2->3 — that's
    # what the user types. Physically those map to (0,2),(0,1),(2,1).
    _play_labeled(
        g,
        Labelling.ONE_THREE_TWO,
        [(1, 2), (1, 3), (2, 3)],
        rec,
    )
    # Both discs ended up on physical peg 1 (which the user saw as label 3).
    assert g.towers == [[], [2, 1], []]

    recipe: Recipe = rec.to_recipe("solve-from-relabel", disk_count=2)
    # Stored as physical+1, NOT as what the user typed.
    # User typed (1,2),(1,3),(2,3); physically (0,2),(0,1),(2,1);
    # default-space = physical+1 = (1,3),(1,2),(3,2).
    assert recipe.default_moves == ((1, 3), (1, 2), (3, 2))

    # And replay under default labelling reproduces the same physical moves.
    g2: HanoiGame = HanoiGame(num_disks=2)
    results: list[StepResult] = apply(recipe, g2, Labelling.ONE_TWO_THREE)
    assert all(r.ok for r in results)
    assert [(r.from_peg, r.to_peg) for r in results] == [
        (0, 2),
        (0, 1),
        (2, 1),
    ]
    assert g2.towers == [[], [2, 1], []]


def test_apply_recipe_through_relabel_solves_subproblem() -> None:
    """Bill's worked example.

    Capture a 2-disc-from-1-to-3 solve under ONE_TWO_THREE. Then on a
    fresh 3-disc game, swap labels 2 and 3 (-> ONE_THREE_TWO) and apply
    the recipe. The recipe's "1 -> 3" steps now route to the physical
    pegs *currently* labelled 1 and 3, which means the top two discs of
    the 3-disc stack should land on physical peg 1 (originally the
    temporary peg). The bottom disc stays put on physical peg 0.
    """
    # 1) Capture the 2-disc solution under default labelling.
    g2: HanoiGame = HanoiGame(num_disks=2)
    rec: Recorder = Recorder()
    _play_labeled(
        g2,
        Labelling.ONE_TWO_THREE,
        [(1, 2), (1, 3), (2, 3)],
        rec,
    )
    assert g2.check_win_condition()
    recipe: Recipe = rec.to_recipe("solve-2-from-1-to-3", disk_count=2)

    # 2) On a 3-disc game, swap labels 2 and 3 and apply the recipe.
    g3: HanoiGame = HanoiGame(num_disks=3)
    assert g3.towers == [[3, 2, 1], [], []]
    relabelled: Labelling = Labelling.ONE_THREE_TWO  # physical 0,1,2 -> 1,3,2

    results: list[StepResult] = apply(recipe, g3, relabelled)
    assert all(r.ok for r in results), [r.error for r in results if r.error]

    # The size-3 disc has not moved; the top two discs are now stacked on
    # physical peg 1 (the original temporary peg). This is the state the
    # student wants to reach as the first step of solving 3 discs.
    assert g3.towers == [[3], [2, 1], []]
    assert g3.current_moves == 3


def test_apply_records_physical_pegs_per_step() -> None:
    """Each StepResult should report the physical pegs the move actually
    routed to under the active labelling, so the front-end can show the
    student what just happened."""
    g2: HanoiGame = HanoiGame(num_disks=2)
    rec: Recorder = Recorder()
    _play_labeled(
        g2,
        Labelling.ONE_TWO_THREE,
        [(1, 2), (1, 3), (2, 3)],
        rec,
    )
    recipe: Recipe = rec.to_recipe("r", disk_count=2)

    g3: HanoiGame = HanoiGame(num_disks=3)
    results: list[StepResult] = apply(recipe, g3, Labelling.ONE_THREE_TWO)
    # Under ONE_THREE_TWO, label 1 -> physical 0, label 2 -> physical 2,
    # label 3 -> physical 1. So the recipe's (1,2),(1,3),(2,3) physical
    # routes are (0,2),(0,1),(2,1).
    assert [(r.from_peg, r.to_peg) for r in results] == [
        (0, 2),
        (0, 1),
        (2, 1),
    ]


# --- apply stops on the first illegal step -------------------------------


def test_apply_stops_with_explanation_on_illegal_move() -> None:
    """A 2-disc recipe applied to a 1-disc game can't get past the second
    move (there's no disc 2 to move). apply_iter should yield the first
    successful step, then a StepResult carrying the error, and stop."""
    g2: HanoiGame = HanoiGame(num_disks=2)
    rec: Recorder = Recorder()
    _play_labeled(
        g2,
        Labelling.ONE_TWO_THREE,
        [(1, 2), (1, 3), (2, 3)],
        rec,
    )
    recipe: Recipe = rec.to_recipe("r", disk_count=2)

    g1: HanoiGame = HanoiGame(num_disks=1)
    results: list[StepResult] = list(
        apply_iter(recipe, g1, Labelling.ONE_TWO_THREE)
    )
    # First move (1->2) succeeds — the single disc moves to physical 1.
    assert len(results) == 2
    assert results[0].ok
    # Second move (1->3) fails — peg 1 (physical 0) is now empty.
    assert results[1].error is not None
    assert "is empty" in results[1].error


def test_apply_records_disc_size_in_larger_on_smaller_error() -> None:
    """A move that would put a larger disc on a smaller one mentions both
    sizes so the student can see what went wrong."""
    g3: HanoiGame = HanoiGame(num_disks=3)
    # Push disc 1 to peg 3 by hand.
    vm: ValidMove
    for vm in g3.move_options():
        if vm.move.from_peg == 0 and vm.move.to_peg == 2:
            vm.action()
            break

    # Recipe says move 1->3 again — that would put disc 2 on disc 1.
    recipe: Recipe = Recipe(name="bad", disk_count=3, default_moves=((1, 3),))
    results: list[StepResult] = apply(recipe, g3, Labelling.ONE_TWO_THREE)
    assert len(results) == 1
    assert results[0].error is not None
    assert "larger on smaller" in results[0].error


def test_apply_iter_is_lazy_step_mode() -> None:
    """The iter form yields one move at a time so the front-end can pause
    for confirmation between steps."""
    g2: HanoiGame = HanoiGame(num_disks=2)
    rec: Recorder = Recorder()
    _play_labeled(
        g2,
        Labelling.ONE_TWO_THREE,
        [(1, 2), (1, 3), (2, 3)],
        rec,
    )
    recipe: Recipe = rec.to_recipe("r", 2)

    g_target: HanoiGame = HanoiGame(num_disks=2)
    it: Iterator[StepResult] = apply_iter(
        recipe, g_target, Labelling.ONE_TWO_THREE
    )

    next(it)
    assert g_target.towers == [[2], [1], []]
    next(it)
    assert g_target.towers == [[], [1], [2]]
    next(it)
    assert g_target.towers == [[], [], [2, 1]]
