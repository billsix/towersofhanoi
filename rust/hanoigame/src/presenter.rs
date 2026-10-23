// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later

//! UI-agnostic rendering and labelling for [`HanoiGame`].
//!
//! Owns the board-layout maths, the peg-relabelling enum, and the pure-text
//! [`render`] that turns a game state into ASCII lines. The TUI uses the layout
//! helpers and the labelling table directly so it can colour cells itself; the
//! CLI consumes [`render`] output unchanged. (Rust port of
//! `python/src/hanoigame/presenter.py`, kept in sync.)
//!
//! The layout functions assume `num_disks >= 1` and `1 <= size <= num_disks`;
//! [`render`] returns no lines for a 0-disc game before any layout maths runs.

use crate::model::HanoiGame;

// --- Labelling --------------------------------------------------------------

/// The six ways the three pegs can be labelled 1, 2, 3.
///
/// Each variant names the 1-indexed labels worn by physical pegs 0, 1, 2 in
/// order — e.g. `OneThreeTwo` labels peg 0 as 1, peg 1 as 3, peg 2 as 2.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Labelling {
    OneTwoThree,
    OneThreeTwo,
    TwoOneThree,
    TwoThreeOne,
    ThreeOneTwo,
    ThreeTwoOne,
}

impl Labelling {
    /// The 0-indexed labels worn by physical pegs 0, 1, 2, in order.
    pub fn label_order(self) -> [usize; 3] {
        match self {
            Labelling::OneTwoThree => [0, 1, 2],
            Labelling::OneThreeTwo => [0, 2, 1],
            Labelling::TwoOneThree => [1, 0, 2],
            Labelling::TwoThreeOne => [1, 2, 0],
            Labelling::ThreeOneTwo => [2, 0, 1],
            Labelling::ThreeTwoOne => [2, 1, 0],
        }
    }
}

/// The 0-indexed label currently attached to the peg at `tower_index`.
pub fn change_labels_on_pegs(labelling: Labelling, tower_index: usize) -> usize {
    labelling.label_order()[tower_index]
}

/// The labelling under which pegs 0, 1, 2 carry `labels` (1-indexed), or `None`
/// if `labels` is not a permutation of (1, 2, 3).
pub fn labelling_for(labels: &[u32]) -> Option<Labelling> {
    match labels {
        [1, 2, 3] => Some(Labelling::OneTwoThree),
        [1, 3, 2] => Some(Labelling::OneThreeTwo),
        [2, 1, 3] => Some(Labelling::TwoOneThree),
        [2, 3, 1] => Some(Labelling::TwoThreeOne),
        [3, 1, 2] => Some(Labelling::ThreeOneTwo),
        [3, 2, 1] => Some(Labelling::ThreeTwoOne),
        _ => None,
    }
}

/// Which physical peg carries the 1-indexed `label` under `labelling` (the
/// inverse of [`change_labels_on_pegs`]); `None` if `label` is out of 1..=3.
pub fn label_to_tower(labelling: Labelling, label: u32) -> Option<usize> {
    if !(1..=3).contains(&label) {
        return None;
    }
    let target: usize = (label - 1) as usize;
    labelling.label_order().iter().position(|&l| l == target)
}

// --- Colours (referenced by the TUI; harmless to ignore from the CLI) -------

/// TUI colour-pair number for label 1.
pub const COLOR_BLUE: i32 = 5;
/// TUI colour-pair number for label 2.
pub const COLOR_YELLOW: i32 = 3;
/// TUI colour-pair number for label 3.
pub const COLOR_RED: i32 = 4;

// Colour follows the *label*, not the physical peg, so the student can keep
// tracking "label 1 is the blue peg" after relabelling.
const PEG_COLOR_BY_LABEL: [i32; 3] = [COLOR_BLUE, COLOR_YELLOW, COLOR_RED];

/// The TUI colour-pair number for the peg at `tower_index` under `labelling`;
/// the colour tracks that peg's label, not its position.
pub fn peg_color(labelling: Labelling, tower_index: usize) -> i32 {
    PEG_COLOR_BY_LABEL[change_labels_on_pegs(labelling, tower_index)]
}

// --- Layout maths -----------------------------------------------------------

/// The fixed gap, in characters, between adjacent pegs.
pub const PEG_GAP: usize = 5;

/// The character width of a peg sized for `num_disks` discs.
pub fn peg_visual_width(num_disks: usize) -> usize {
    num_disks * 2 - 1
}

/// The fixed gap, in characters, between adjacent pegs.
pub fn peg_gap() -> usize {
    PEG_GAP
}

/// The full board width in characters for `num_disks` discs (all three pegs and
/// the gaps between them).
pub fn total_width(num_disks: usize) -> usize {
    (peg_visual_width(num_disks) + peg_gap()) * 3 - peg_gap()
}

/// The character width of a disc of the given `size`.
pub fn disk_char_width(size: usize) -> usize {
    size * 2 - 1
}

/// The left padding that centres a disc of `size` within a peg column.
pub fn padding_left(num_disks: usize, size: usize) -> usize {
    (peg_visual_width(num_disks) - disk_char_width(size)) / 2
}

/// The 0-indexed column of the centre of `tower_index`.
pub fn peg_center_x(num_disks: usize, tower_index: usize) -> usize {
    tower_index * (peg_visual_width(num_disks) + peg_gap()) + peg_visual_width(num_disks) / 2
}

/// The minimum terminal width the TUI needs to draw the board with padding.
pub fn min_cols(num_disks: usize) -> usize {
    total_width(num_disks) + 4
}

// --- Pure text rendering ----------------------------------------------------

/// A single digit `d` (1..=9) as its character.
fn digit_char(d: usize) -> char {
    char::from_digit(d as u32, 10).expect("label digit is 1..=9")
}

/// A line showing the default "1 2 3" labelling at the peg-centre columns, used
/// as a reference row under a non-default labelling.
pub fn default_label_row(num_disks: usize) -> String {
    let width: usize = total_width(num_disks);
    let mut row: Vec<char> = vec![' '; width];
    for peg in 0..3 {
        row[peg_center_x(num_disks, peg)] = digit_char(peg + 1);
    }
    row.into_iter().collect()
}

/// Render the board top-to-bottom as plain ASCII lines.
///
/// Rows 0..=num_disks are the peg verticals with discs overlaid, then the base
/// line, then the active-labelling peg-label row, then — only when `labelling`
/// is not the default — a default "1 2 3" reference row. Each line is
/// [`total_width`] characters wide; a 0-disc game renders to no lines.
pub fn render(game: &HanoiGame, labelling: Labelling) -> Vec<String> {
    let n: usize = game.num_disks as usize;
    if n == 0 {
        return Vec::new();
    }
    let width: usize = total_width(n);
    let mut grid: Vec<Vec<char>> = vec![vec![' '; width]; n + 3];

    // Vertical pegs (rows 0..=n).
    for peg in 0..3 {
        let cx: usize = peg_center_x(n, peg);
        for row in grid.iter_mut().take(n + 1) {
            row[cx] = '|';
        }
    }

    // Discs — bottom of each stack sits on row n; each next disc one row up.
    let pvw: usize = peg_visual_width(n);
    for (peg, stack) in game.towers.iter().enumerate() {
        let cx: usize = peg_center_x(n, peg);
        for (i, &size) in stack.iter().enumerate() {
            let row: usize = n - i;
            let start: usize = cx - pvw / 2 + padding_left(n, size as usize);
            for col in start..start + disk_char_width(size as usize) {
                grid[row][col] = '*';
            }
        }
    }

    // Base line.
    grid[n + 1] = vec!['='; width];

    // Peg labels under the active labelling.
    for peg in 0..3 {
        let cx: usize = peg_center_x(n, peg);
        grid[n + 2][cx] = digit_char(change_labels_on_pegs(labelling, peg) + 1);
    }

    let mut lines: Vec<String> = grid
        .into_iter()
        .map(|row| row.into_iter().collect())
        .collect();
    // Append the default reference row when the user has relabelled.
    if labelling != Labelling::OneTwoThree {
        lines.push(default_label_row(n));
    }
    lines
}

/// Same as [`render`], but with a trailing `Moves: <count>` status line.
pub fn render_with_legend(game: &HanoiGame, labelling: Labelling) -> Vec<String> {
    let mut lines: Vec<String> = render(game, labelling);
    lines.push(format!("Moves: {}", game.current_moves));
    lines
}

// --- Move translation through the current labelling -------------------------

/// Translate a typed `(from_label, to_label)` pair (1-indexed under
/// `labelling`) into physical `(from_peg, to_peg)` indices, or `None` if either
/// label is out of range.
pub fn labels_to_towers(
    labelling: Labelling,
    from_label: u32,
    to_label: u32,
) -> Option<(usize, usize)> {
    let fp: usize = label_to_tower(labelling, from_label)?;
    let tp: usize = label_to_tower(labelling, to_label)?;
    Some((fp, tp))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{HanoiGame, Move};

    // Ported from python/tests/test_presenter.py.

    #[test]
    fn layout_maths_3_discs() {
        assert_eq!(peg_visual_width(3), 5);
        assert_eq!(peg_gap(), 5);
        assert_eq!(total_width(3), 25);
        assert_eq!(peg_center_x(3, 0), 2);
        assert_eq!(peg_center_x(3, 1), 12);
        assert_eq!(peg_center_x(3, 2), 22);
        assert_eq!(disk_char_width(1), 1);
        assert_eq!(disk_char_width(2), 3);
        assert_eq!(disk_char_width(3), 5);
        assert_eq!(padding_left(3, 1), 2);
        assert_eq!(padding_left(3, 2), 1);
        assert_eq!(padding_left(3, 3), 0);
        assert_eq!(min_cols(3), 29);
    }

    #[test]
    fn layout_maths_5_discs() {
        assert_eq!(peg_visual_width(5), 9);
        assert_eq!(total_width(5), 37);
        assert_eq!(peg_center_x(5, 0), 4);
        assert_eq!(peg_center_x(5, 1), 18);
        assert_eq!(peg_center_x(5, 2), 32);
    }

    #[test]
    fn change_labels_default_and_swapped() {
        let d = Labelling::OneTwoThree;
        assert_eq!(change_labels_on_pegs(d, 0), 0);
        assert_eq!(change_labels_on_pegs(d, 1), 1);
        assert_eq!(change_labels_on_pegs(d, 2), 2);
        let s = Labelling::OneThreeTwo;
        assert_eq!(change_labels_on_pegs(s, 0), 0);
        assert_eq!(change_labels_on_pegs(s, 1), 2);
        assert_eq!(change_labels_on_pegs(s, 2), 1);
    }

    #[test]
    fn labelling_for_round_trip() {
        let cases: [(&[u32], Labelling); 6] = [
            (&[1, 2, 3], Labelling::OneTwoThree),
            (&[1, 3, 2], Labelling::OneThreeTwo),
            (&[2, 1, 3], Labelling::TwoOneThree),
            (&[2, 3, 1], Labelling::TwoThreeOne),
            (&[3, 1, 2], Labelling::ThreeOneTwo),
            (&[3, 2, 1], Labelling::ThreeTwoOne),
        ];
        for (labels, expected) in cases {
            assert_eq!(labelling_for(labels), Some(expected));
        }
    }

    #[test]
    fn labelling_for_invalid() {
        assert_eq!(labelling_for(&[1, 1, 1]), None);
        assert_eq!(labelling_for(&[1, 2]), None);
        assert_eq!(labelling_for(&[4, 1, 2]), None);
    }

    #[test]
    fn label_to_tower_inverse() {
        let l = Labelling::OneThreeTwo; // towers carry labels 1, 3, 2
        assert_eq!(label_to_tower(l, 1), Some(0));
        assert_eq!(label_to_tower(l, 3), Some(1));
        assert_eq!(label_to_tower(l, 2), Some(2));
        assert_eq!(label_to_tower(l, 4), None);
        assert_eq!(label_to_tower(l, 0), None);
    }

    #[test]
    fn labels_to_towers_maps_pairs() {
        let l = Labelling::OneThreeTwo; // towers carry labels 1, 3, 2
        assert_eq!(labels_to_towers(l, 1, 3), Some((0, 1)));
        assert_eq!(labels_to_towers(l, 2, 1), Some((2, 0)));
        assert_eq!(labels_to_towers(l, 1, 9), None);
    }

    #[test]
    fn peg_color_follows_label_not_tower() {
        let blue = peg_color(Labelling::OneTwoThree, 0); // tower 0 carries label 1
        assert_eq!(peg_color(Labelling::TwoOneThree, 1), blue);
        assert_eq!(peg_color(Labelling::ThreeTwoOne, 2), blue);
    }

    #[test]
    fn render_3_disc_fresh_game() {
        let game = HanoiGame::new(3);
        let lines = render(&game, Labelling::OneTwoThree);
        assert_eq!(
            lines,
            vec![
                "  |         |         |  ",
                "  *         |         |  ",
                " ***        |         |  ",
                "*****       |         |  ",
                "=========================",
                "  1         2         3  ",
            ]
        );
    }

    #[test]
    fn render_after_one_move() {
        let mut game = HanoiGame::new(3);
        game.apply_move(Move::new(0, 2)).unwrap();
        let lines = render(&game, Labelling::OneTwoThree);
        assert_eq!(
            lines,
            vec![
                "  |         |         |  ",
                "  |         |         |  ",
                " ***        |         |  ",
                "*****       |         *  ",
                "=========================",
                "  1         2         3  ",
            ]
        );
    }

    #[test]
    fn render_label_row_changes_with_labelling() {
        let game = HanoiGame::new(3);
        let lines = render(&game, Labelling::ThreeTwoOne);
        assert_eq!(lines[lines.len() - 2], "  3         2         1  ");
        assert_eq!(lines[lines.len() - 1], "  1         2         3  ");
    }

    #[test]
    fn render_omits_reference_row_under_default() {
        let game = HanoiGame::new(3);
        let lines = render(&game, Labelling::OneTwoThree);
        assert_eq!(lines.len(), 3 + 3);
        assert_eq!(lines[lines.len() - 1], "  1         2         3  ");
    }

    #[test]
    fn render_appends_reference_row_when_relabelled() {
        let game = HanoiGame::new(3);
        let lines = render(&game, Labelling::OneThreeTwo);
        assert_eq!(lines.len(), 3 + 4);
        assert_eq!(lines[lines.len() - 2], "  1         3         2  ");
        assert_eq!(lines[lines.len() - 1], "  1         2         3  ");
    }

    #[test]
    fn render_dimensions() {
        for n in [1u32, 2, 3, 5, 8] {
            let game = HanoiGame::new(n);
            let lines = render(&game, Labelling::OneTwoThree);
            assert_eq!(lines.len(), n as usize + 3);
            for line in &lines {
                assert_eq!(line.chars().count(), total_width(n as usize));
            }
        }
    }

    #[test]
    fn render_zero_discs_is_empty() {
        let game = HanoiGame::new(0);
        assert_eq!(render(&game, Labelling::OneTwoThree), Vec::<String>::new());
    }

    #[test]
    fn render_with_legend_appends_move_count() {
        let mut game = HanoiGame::new(2);
        let lines = render_with_legend(&game, Labelling::OneTwoThree);
        assert_eq!(lines[lines.len() - 1], "Moves: 0");
        let mv = game.move_options()[0];
        game.apply_move(mv).unwrap();
        let lines = render_with_legend(&game, Labelling::OneTwoThree);
        assert_eq!(lines[lines.len() - 1], "Moves: 1");
    }
}
