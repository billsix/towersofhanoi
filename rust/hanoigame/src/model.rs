// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later

//! Core Towers of Hanoi game state and legal-move enumeration.
//!
//! The shared model the three front-ends build on: [`HanoiGame`] holds the three
//! pegs as stacks of disc sizes, and [`HanoiGame::move_options`] yields the
//! currently legal moves. Pegs are 0-indexed here; the 1-indexed labels the
//! player sees are applied by the presenter. (Rust port of
//! `python/src/hanoigame/hanoimodel.py`, kept in sync.)

use std::fmt;

/// A single disc move between two physical pegs (both 0-indexed).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Move {
    /// 0-indexed peg the top disc is taken from.
    pub from_peg: usize,
    /// 0-indexed peg the disc is placed on.
    pub to_peg: usize,
}

impl Move {
    /// Construct a move between two 0-indexed pegs.
    pub fn new(from_peg: usize, to_peg: usize) -> Self {
        Self { from_peg, to_peg }
    }
}

/// Why a requested move is not legal.
///
/// The Python model never raises — it builds the performing closure only for
/// already-legal moves (`move_options`). The Rust port keeps that enumeration
/// but also makes [`HanoiGame::apply_move`] total and checked, so a front-end
/// cannot silently corrupt the towers.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MoveError {
    /// The source peg has no disc to move.
    SourceEmpty,
    /// The moved disc is larger than the disc it would land on.
    LargerOntoSmaller,
    /// A peg index was outside `0..=2`.
    PegOutOfRange(usize),
}

impl fmt::Display for MoveError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            MoveError::SourceEmpty => write!(f, "source peg is empty"),
            MoveError::LargerOntoSmaller => {
                write!(f, "cannot place a larger disc on a smaller one")
            }
            MoveError::PegOutOfRange(peg) => {
                write!(f, "peg index {peg} is out of range (expected 0, 1 or 2)")
            }
        }
    }
}

impl std::error::Error for MoveError {}

/// The six ordered `(from, to)` peg pairs, in the Python model's enumeration
/// order — so [`HanoiGame::move_options`] yields moves in exactly the order the
/// front-ends and recipes already depend on.
const PEG_PAIRS: [(usize, usize); 6] = [(0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1)];

/// A Towers of Hanoi game: three pegs holding stacks of disc sizes.
///
/// Each peg is a `Vec<u32>` used as a stack of disc sizes (larger numbers are
/// larger discs; the top of the stack is the last element). The all-on-peg-0
/// start, the win condition, and the legal-move set match the Python model.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HanoiGame {
    /// The three pegs, bottom-to-top (index 0 of a peg's `Vec` is its bottom).
    pub towers: [Vec<u32>; 3],
    /// The number of discs the game started with.
    pub num_disks: u32,
    /// How many moves have been made so far.
    pub current_moves: u32,
}

impl HanoiGame {
    /// Start a game with `num_disks` discs stacked on peg 0, largest at the
    /// bottom and smallest on top.
    ///
    /// # Examples
    /// ```
    /// use hanoigame::HanoiGame;
    /// let game: HanoiGame = HanoiGame::new(3);
    /// assert_eq!(game.towers, [vec![3, 2, 1], vec![], vec![]]);
    /// assert_eq!((game.num_disks, game.current_moves), (3, 0));
    /// assert!(!game.check_win_condition()); // nothing on peg 2 yet
    /// ```
    pub fn new(num_disks: u32) -> Self {
        let mut towers: [Vec<u32>; 3] = [Vec::new(), Vec::new(), Vec::new()];
        // Largest (num_disks) pushed first so it lands at the bottom, down to 1.
        for size in (1..=num_disks).rev() {
            towers[0].push(size);
        }
        Self {
            towers,
            num_disks,
            current_moves: 0,
        }
    }

    /// Whether every disc has been moved onto peg 2 (a win).
    ///
    /// # Examples
    /// ```
    /// use hanoigame::{HanoiGame, Move};
    /// let mut game: HanoiGame = HanoiGame::new(1);
    /// assert!(!game.check_win_condition());
    /// game.apply_move(Move::new(0, 2)).unwrap();
    /// assert!(game.check_win_condition()); // the only disc reached peg 2
    /// ```
    pub fn check_win_condition(&self) -> bool {
        self.towers[2].len() as u32 == self.num_disks
    }

    /// Whether the top disc of `from_peg` may legally move onto `to_peg`.
    pub fn is_valid_move(&self, from_peg: usize, to_peg: usize) -> bool {
        match (self.towers.get(from_peg), self.towers.get(to_peg)) {
            (Some(source), Some(dest)) => match (source.last(), dest.last()) {
                (None, _) => false,                       // source peg empty
                (Some(top), Some(under)) => top <= under, // no larger-on-smaller
                (Some(_), None) => true,                  // onto an empty peg
            },
            _ => false, // a peg index out of range is never a legal move
        }
    }

    /// Enumerate the currently legal moves, in the fixed peg-pair order.
    pub fn move_options(&self) -> Vec<Move> {
        PEG_PAIRS
            .iter()
            .filter(|&&(from, to)| self.is_valid_move(from, to))
            .map(|&(from, to)| Move::new(from, to))
            .collect()
    }

    /// Apply `mv`: pop the source peg's top disc onto the destination peg and
    /// count the move. Returns a [`MoveError`] (leaving the game unchanged) if
    /// the move is not legal.
    ///
    /// # Examples
    /// ```
    /// use hanoigame::{HanoiGame, Move, MoveError};
    /// let mut game: HanoiGame = HanoiGame::new(3);
    /// assert_eq!(game.apply_move(Move::new(1, 0)), Err(MoveError::SourceEmpty));
    /// game.apply_move(Move::new(0, 1)).unwrap(); // smallest disc to peg 1
    /// assert_eq!(game.towers, [vec![3, 2], vec![1], vec![]]);
    /// assert_eq!(
    ///     game.apply_move(Move::new(0, 1)), // disc 2 onto disc 1
    ///     Err(MoveError::LargerOntoSmaller),
    /// );
    /// assert_eq!(game.apply_move(Move::new(0, 9)), Err(MoveError::PegOutOfRange(9)));
    /// ```
    pub fn apply_move(&mut self, mv: Move) -> Result<(), MoveError> {
        if mv.from_peg > 2 {
            return Err(MoveError::PegOutOfRange(mv.from_peg));
        }
        if mv.to_peg > 2 {
            return Err(MoveError::PegOutOfRange(mv.to_peg));
        }
        let Some(&top) = self.towers[mv.from_peg].last() else {
            return Err(MoveError::SourceEmpty);
        };
        if let Some(&under) = self.towers[mv.to_peg].last() {
            if top > under {
                return Err(MoveError::LargerOntoSmaller);
            }
        }
        self.towers[mv.from_peg].pop();
        self.towers[mv.to_peg].push(top);
        self.current_moves += 1;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // new / check_win_condition / apply_move's single moves and error cases are
    // doctests on those methods now; makemove keeps the full multi-step walk.

    #[test]
    fn makemove() {
        let mut game: HanoiGame = HanoiGame::new(3);

        assert_eq!(game.move_options(), vec![Move::new(0, 1), Move::new(0, 2)]);

        // make_move(0)
        let mv: Move = game.move_options()[0];
        game.apply_move(mv).unwrap();
        assert_eq!(game.towers, [vec![3, 2], vec![1], vec![]]);
        assert_eq!(
            game.move_options(),
            vec![Move::new(0, 2), Move::new(1, 0), Move::new(1, 2)]
        );

        // make_move(2)
        let mv: Move = game.move_options()[2];
        game.apply_move(mv).unwrap();
        assert_eq!(game.towers, [vec![3, 2], vec![], vec![1]]);
        assert_eq!(
            game.move_options(),
            vec![Move::new(0, 1), Move::new(2, 0), Move::new(2, 1)]
        );

        // make_move(0)
        let mv: Move = game.move_options()[0];
        game.apply_move(mv).unwrap();
        assert_eq!(game.towers, [vec![3], vec![2], vec![1]]);
        assert_eq!(
            game.move_options(),
            vec![Move::new(1, 0), Move::new(2, 0), Move::new(2, 1)]
        );

        // make_move(2)
        let mv: Move = game.move_options()[2];
        game.apply_move(mv).unwrap();
        assert_eq!(game.towers, [vec![3], vec![2, 1], vec![]]);
        assert_eq!(
            game.move_options(),
            vec![Move::new(0, 2), Move::new(1, 0), Move::new(1, 2)]
        );
    }
}
