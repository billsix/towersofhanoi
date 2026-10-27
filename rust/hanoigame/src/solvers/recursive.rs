// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later

//! Recursive Towers-of-Hanoi solvers, unrolled for teaching.
//!
//! Shows the recursion one level at a time: [`hanoi_1`] through [`hanoi_4`] are
//! the base case and three hand-unrolled levels, each written in terms of the
//! one below it, and [`hanoi_n`] is the general recursive form. Every solver
//! returns its moves as a newline-separated string of `"from -> to"` lines.
//! Each `hanoi_*` takes the same three peg arguments, `i` (initial), `t`
//! (temporary/spare) and `g` (goal). (Port of `hanoirecursive.py`; the Python's
//! `@snoop()` call-tracing is a teaching aid, not reproduced here.)

/// Solve a one-disc tower: the single move from the initial to the goal peg.
/// The recursion's base case; `_t` (the spare peg) is unused for one disc.
///
/// # Examples
/// ```
/// use hanoigame::solvers::recursive::hanoi_1;
/// let moves: String = hanoi_1(1, 2, 3);
/// assert_eq!(moves, "1 -> 3");
/// ```
pub fn hanoi_1(i: u32, _t: u32, g: u32) -> String {
    format!("{i} -> {g}")
}

/// Solve a two-disc tower by unrolling the recursion one level: top disc to the
/// spare, big disc to the goal, top disc onto the goal — each via [`hanoi_1`].
///
/// # Examples
/// ```
/// use hanoigame::solvers::recursive::hanoi_2;
/// let moves: String = hanoi_2(1, 2, 3);
/// assert_eq!(moves, "1 -> 2\n1 -> 3\n2 -> 3");
/// ```
pub fn hanoi_2(i: u32, t: u32, g: u32) -> String {
    let two_minus_1_i_to_t: String = hanoi_1(i, g, t);
    let big_peg_to_goal: String = hanoi_1(i, t, g);
    let two_minus_1_t_to_g: String = hanoi_1(t, i, g);
    format!("{two_minus_1_i_to_t}\n{big_peg_to_goal}\n{two_minus_1_t_to_g}")
}

/// Solve a three-disc tower by unrolling one more level: the top two discs to
/// the spare (via [`hanoi_2`]), the big disc to the goal, then the two onto it.
///
/// # Examples
/// ```
/// use hanoigame::solvers::recursive::hanoi_3;
/// let moves: String = hanoi_3(1, 2, 3);
/// assert_eq!(
///     moves,
///     "1 -> 3\n1 -> 2\n3 -> 2\n1 -> 3\n2 -> 1\n2 -> 3\n1 -> 3"
/// );
/// ```
pub fn hanoi_3(i: u32, t: u32, g: u32) -> String {
    let three_minus_1_i_to_t: String = hanoi_2(i, g, t);
    let big_peg_to_goal: String = hanoi_1(i, t, g);
    let three_minus_1_t_to_g: String = hanoi_2(t, i, g);
    format!("{three_minus_1_i_to_t}\n{big_peg_to_goal}\n{three_minus_1_t_to_g}")
}

/// Solve a four-disc tower, the last hand-unrolled level: the top three discs to
/// the spare (via [`hanoi_3`]), the big disc to the goal, then the three onto it.
pub fn hanoi_4(i: u32, t: u32, g: u32) -> String {
    let four_minus_1_i_to_t: String = hanoi_3(i, g, t);
    let big_peg_to_goal: String = hanoi_1(i, t, g);
    let four_minus_1_t_to_g: String = hanoi_3(t, i, g);
    format!("{four_minus_1_i_to_t}\n{big_peg_to_goal}\n{four_minus_1_t_to_g}")
}

/// Solve an `n`-disc tower with the general recursive algorithm — the pattern
/// the `hanoi_1`..`hanoi_4` unrollings make explicit: move `n-1` discs to the
/// spare, move the big disc to the goal, then move the `n-1` discs onto the
/// goal. `n` is assumed to be at least 1; returns the `2^n - 1` moves.
pub fn hanoi_n(n: u32, i: u32, t: u32, g: u32) -> String {
    if n == 1 {
        return format!("{i} -> {g}");
    }
    let n_minus_1_i_to_t: String = hanoi_n(n - 1, i, g, t);
    let big_peg_to_goal: String = hanoi_n(1, i, t, g);
    let n_minus_1_t_to_g: String = hanoi_n(n - 1, t, i, g);
    format!("{n_minus_1_i_to_t}\n{big_peg_to_goal}\n{n_minus_1_t_to_g}")
}

#[cfg(test)]
mod tests {
    use super::*;

    // The per-level examples (hanoi_1/2/3) are doctests on those functions now;
    // what stays here cross-checks the general form against them and against
    // the iterative solver.

    #[test]
    fn general_form_matches_the_unrolled_levels() {
        assert_eq!(hanoi_n(1, 1, 2, 3), hanoi_1(1, 2, 3));
        assert_eq!(hanoi_n(2, 1, 2, 3), hanoi_2(1, 2, 3));
        assert_eq!(hanoi_n(3, 1, 2, 3), hanoi_3(1, 2, 3));
        assert_eq!(hanoi_n(4, 1, 2, 3), hanoi_4(1, 2, 3));
    }

    #[test]
    fn general_form_matches_the_iterative_solver() {
        for n in 1..=8 {
            assert_eq!(hanoi_n(n, 1, 2, 3), super::super::iterative::solve(n));
        }
    }
}
