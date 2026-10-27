// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later

//! Iterative Towers-of-Hanoi solver built by string rewriting.
//!
//! Teaching companion to [`super::recursive`]. Instead of recursion, it builds
//! the move list for `n` discs by taking the `n-1` solution and rewriting its
//! peg labels twice (via [`swap_temporary_and_goal`] and
//! [`swap_initial_and_temporary`]) to retarget the two sub-towers, then
//! splicing the big-disc move between them. (Port of `hanoiiterative.py`; the
//! Python prints the moves, this returns them — the clearer, testable form.)

/// Rewrite a move sequence with the temporary (`2`) and goal (`3`) pegs swapped.
///
/// Used to retarget the `n-1` sub-solution so it moves onto the temporary peg
/// instead of the goal peg.
///
/// # Examples
/// ```
/// use hanoigame::solvers::iterative::swap_temporary_and_goal;
/// assert_eq!(swap_temporary_and_goal("1 -> 2"), "1 -> 3");
/// ```
pub fn swap_temporary_and_goal(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            '2' => '3', // the temporary peg becomes the goal peg
            '3' => '2', // the goal peg becomes the temporary peg
            other => other,
        })
        .collect()
}

/// Rewrite a move sequence with the initial (`1`) and temporary (`2`) pegs
/// swapped.
///
/// Used to retarget the `n-1` sub-solution so it moves off the temporary peg
/// (where the smaller tower was parked) onto the goal.
///
/// # Examples
/// ```
/// use hanoigame::solvers::iterative::swap_initial_and_temporary;
/// assert_eq!(swap_initial_and_temporary("1 -> 2"), "2 -> 1");
/// ```
pub fn swap_initial_and_temporary(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            '1' => '2', // the initial peg becomes the temporary peg
            '2' => '1', // the temporary peg becomes the initial peg
            other => other,
        })
        .collect()
}

/// Build the newline-separated moves that solve an `n`-disc puzzle from peg 1
/// to peg 3, by string rewriting (no recursion).
///
/// Starts from the one-disc solution and, for each additional disc, rewrites
/// the current move list twice to place the two `n-1` sub-towers around the
/// big-disc move. `n` is assumed to be at least 1.
///
/// # Examples
/// ```
/// use hanoigame::solvers::iterative::solve;
/// assert_eq!(solve(1), "1 -> 3");
/// let three: String = solve(3);
/// assert_eq!(three, "1 -> 3\n1 -> 2\n3 -> 2\n1 -> 3\n2 -> 1\n2 -> 3\n1 -> 3");
/// assert_eq!(three.lines().count(), 7); // 2^3 - 1 moves
/// ```
pub fn solve(n: u32) -> String {
    let mut moves: String = String::from("1 -> 3");
    let mut x: u32 = 2;
    while x <= n {
        let x_minus_1_i_to_t: String = swap_temporary_and_goal(&moves);
        let big_peg_to_goal: &str = "1 -> 3";
        let x_minus_1_t_to_g: String = swap_initial_and_temporary(&moves);
        moves = format!("{x_minus_1_i_to_t}\n{big_peg_to_goal}\n{x_minus_1_t_to_g}");
        x += 1;
    }
    moves
}

#[cfg(test)]
mod tests {
    use super::*;

    // The one/two/three-disc examples are doctests on `solve` now; the loop
    // below keeps the 2^n - 1 move-count invariant as a property test.

    #[test]
    fn move_count_is_2n_minus_1() {
        for n in 1..=8 {
            assert_eq!(solve(n).lines().count(), (1usize << n) - 1);
        }
    }
}
