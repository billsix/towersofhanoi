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

import io

from hanoigame.hanoicli import run


def _drive(input_text: str) -> str:
    """Run the CLI against the given canned input. Return all stdout."""
    out = io.StringIO()
    run(io.StringIO(input_text), out)
    return out.getvalue()


# Optimal 3-disc moves from peg 1 to peg 3 under the default labelling.
WIN_3_OPTIMAL = ["1 3", "1 2", "3 2", "1 3", "2 1", "2 3", "1 3"]

# Optimal 2-disc moves from peg 1 to peg 3 under the default labelling.
WIN_2_OPTIMAL = ["1 2", "1 3", "2 3"]


def _script(*chunks: str) -> str:
    """Join input lines with newlines (and a trailing newline)."""
    return "\n".join(chunks) + "\n"


# --- Basic gameplay (preserved from step 2) ------------------------------


def test_winning_3_disc_sequence_optimal():
    # Skip save prompt with empty line; decline play-again.
    output = _drive(_script("3", *WIN_3_OPTIMAL, "", "n"))
    assert "Solved! 7 moves (minimum 7)." in output
    assert "Optimal solution!" in output


def test_winning_with_extra_moves_reports_diff():
    # Same solution but with two wasted moves at the start.
    moves = ["1 2", "2 1", *WIN_3_OPTIMAL]
    output = _drive(_script("3", *moves, "", "n"))
    assert "Solved! 9 moves (minimum 7)." in output
    assert "2 more than the minimum." in output


def test_illegal_move_empty_source():
    output = _drive(_script("3", "2 1", "quit"))
    assert "Peg 2 is empty" in output


def test_illegal_move_larger_on_smaller():
    output = _drive(_script("3", "1 3", "1 3", "quit"))
    assert "larger on smaller" in output


def test_quit_at_disc_prompt_exits_cleanly():
    assert "Bye." in _drive("quit\n")


def test_eof_at_disc_prompt_exits_cleanly():
    assert "Bye." in _drive("")


def test_relabel_changes_label_digits_in_render():
    output = _drive(_script("3", "relabel 3 2 1", "quit"))
    assert "  3         2         1  " in output


def test_relabel_appends_default_reference_row():
    """When the user relabels, every subsequent board redraw should show
    two label rows: the active labels on top, and the default '1 2 3'
    reference underneath so the user can see which physical peg is which."""
    output = _drive(_script("3", "relabel 3 2 1", "quit"))
    # Both rows present in the post-relabel render.
    assert "  3         2         1  " in output
    assert "  1         2         3  " in output


def test_default_reference_row_absent_under_default_labelling():
    """No reference row when the active labelling is already default."""
    output = _drive(_script("3", "quit"))
    # The default label row appears once (the active labels). Counting all
    # occurrences in the printed board renders for the single 3-disc
    # prompt should give exactly 1.
    assert output.count("  1         2         3  ") == 1


def test_help_lists_commands():
    output = _drive(_script("3", "help", "quit"))
    assert "Commands:" in output
    assert "relabel" in output


def test_parse_error_is_surfaced():
    output = _drive(_script("3", "wat", "quit"))
    assert "unrecognised command" in output


def test_invalid_disc_count_reprompts():
    output = _drive("0\n11\nfoo\n3\nquit\n")
    assert output.count("Please enter a number from 1 to 10.") == 3


# --- Recipes -------------------------------------------------------------


def test_save_only_works_after_winning():
    output = _drive(_script("3", "save mid-game", "quit"))
    assert "Save only works after winning" in output


def test_post_win_prompt_saves_named_recipe():
    output = _drive(_script("2", *WIN_2_OPTIMAL, "win-2", "n"))
    assert "Saved recipe 'win-2'." in output


def test_post_win_empty_name_skips_save():
    output = _drive(_script("2", *WIN_2_OPTIMAL, "", "n"))
    assert "Saved recipe" not in output
    assert "Solved!" in output


def test_list_shows_saved_recipe_with_disc_count_and_moves():
    output = _drive(
        _script("2", *WIN_2_OPTIMAL, "win-2", "y", "2", "list", "quit")
    )
    assert "win-2" in output
    assert "(2 discs, 3 moves)" in output


def test_list_when_empty_says_so():
    output = _drive(_script("3", "list", "quit"))
    assert "No recipes saved yet." in output


def test_apply_unknown_recipe_errors():
    output = _drive(_script("3", "apply ghost", "quit"))
    assert "No recipe named 'ghost'" in output


def test_apply_replays_recipe_on_fresh_game():
    """Save a 2-disc solution, then start another 2-disc game and apply it
    instead of typing the moves. The game should win without any manual
    moves."""
    output = _drive(
        _script(
            "2",
            *WIN_2_OPTIMAL,
            "two",
            "y",
            "2",
            "apply two",
            "",
            "n",
        )
    )
    # Apply step lines, then the win banner from the second game.
    assert "Applying recipe 'two' (3 moves):" in output
    assert "  step 1: 1 -> 2" in output
    assert "  step 2: 1 -> 3" in output
    assert "  step 3: 2 -> 3" in output
    # Two wins reported (one from manual play, one from the apply).
    assert output.count("Solved! 3 moves (minimum 3).") == 2


def test_bill_worked_example_via_cli():
    """The pedagogical moment: a 2-disc-from-1-to-3 recipe, applied to a
    3-disc game after swapping labels 2 and 3, reproduces the first
    'recursive' step — top two discs land on physical peg 1 (which is now
    labelled 3 under the swap, so the board shows the small two stacked on
    the peg labelled 3)."""
    script = _script(
        # Game 1: solve 2 discs and save under the default labelling.
        "2",
        *WIN_2_OPTIMAL,
        "solve-2-from-1-to-3",
        "y",
        # Game 2: 3 discs, swap labels 2 and 3, apply the recipe.
        "3",
        "relabel 1 3 2",
        "apply solve-2-from-1-to-3",
        "quit",
    )
    output = _drive(script)
    assert "Applying recipe 'solve-2-from-1-to-3'" in output
    assert "Done." in output
    # After the apply: physical peg 0 holds disc 3 (alone), physical peg 1
    # holds discs 2 and 1 (stacked correctly). Under labelling ONE_THREE_TWO
    # the label row reads "1 3 2".
    expected_board = [
        "  |         |         |  ",
        "  |         |         |  ",
        "  |         *         |  ",
        "*****      ***        |  ",
        "=========================",
        "  1         3         2  ",
    ]
    for line in expected_board:
        assert line in output, f"missing board line: {line!r}"


def test_show_prints_recipe_steps():
    output = _drive(
        _script(
            "2",
            *WIN_2_OPTIMAL,
            "two",
            "y",
            "2",
            "show two",
            "quit",
        )
    )
    assert "Recipe 'two' (2 discs, 3 moves):" in output
    assert "  step 1: 1 -> 2" in output
    assert "  step 2: 1 -> 3" in output
    assert "  step 3: 2 -> 3" in output


def test_show_unknown_recipe_errors():
    output = _drive(_script("3", "show ghost", "quit"))
    assert "No recipe named 'ghost'" in output


def test_recipe_captured_under_relabel_replays_under_default():
    """A recipe captured while a non-default labelling is active should
    represent the *physical* moves, not the labels the user typed. So a
    recipe that looks like '3 -> 2, 3 -> 1, 2 -> 1' to the user under
    labelling (3,2,1) — which physically is the standard left-to-right
    solve — should replay successfully on a fresh default-labelling game.

    Without normalisation, the recipe would store '(3,2),(3,1),(2,1)' and
    replay under default would route to the wrong physical pegs and fail.
    """
    script = _script(
        # Game 1: relabel so physical pegs 1,2,3 show as 3,2,1. Then play
        # the symmetric "3 -> 1" solve which physically is the standard
        # left-to-right sweep, landing on physical peg 2 (= the win state).
        "2",
        "relabel 3 2 1",
        "3 2",
        "3 1",
        "2 1",
        "captured-under-relabel",
        "y",
        # Game 2: default labelling. Apply the recipe. The save step
        # normalised it to physical-space, so the same physical moves run
        # and the game wins.
        "2",
        "apply captured-under-relabel",
        "",
        "n",
    )
    output = _drive(script)
    # Two solves for 2 discs: one manual under the relabel, one via apply.
    assert output.count("Solved! 3 moves (minimum 3).") == 2


def test_overwriting_recipe_name_says_so():
    output = _drive(
        _script(
            "2",
            *WIN_2_OPTIMAL,
            "dup",
            "y",
            "2",
            *WIN_2_OPTIMAL,
            "dup",
            "n",
        )
    )
    assert "Saved recipe 'dup'." in output
    assert "Overwrote recipe 'dup'." in output
