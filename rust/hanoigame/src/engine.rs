// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later

//! Front-end-agnostic game session and command dispatcher.
//!
//! [`GameSession`] owns one in-progress game (board state, current labelling,
//! move recorder) plus a reference to the cross-game [`RecipeRegistry`].
//! [`GameSession::dispatch`] turns any parsed [`Command`] into a
//! [`DispatchResult`] with display lines and a quit flag, so the CLI, TUI, and
//! GUI front-ends behave identically. (Rust port of
//! `python/src/hanoigame/engine.py`, kept in sync.)
//!
//! Port note: the registry is shared, mutable, cross-game state. Python stores
//! it on the session; Rust models that as a `&mut RecipeRegistry` borrowed for
//! the life of the session (only one game is active at a time — a new game
//! takes a fresh session over the same registry once the old one is dropped).

use crate::commands::{Command, HELP_TEXT};
use crate::model::{HanoiGame, Move};
use crate::presenter::{change_labels_on_pegs, labelling_for, labels_to_towers, Labelling};
use crate::recipe::{apply, format_rebinding_table, RecipeRegistry, Recorder};

/// The fallout from [`GameSession::dispatch`]: the front-end renders `lines` and
/// breaks its loop if `quit` is true.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct DispatchResult {
    /// Lines for the front-end to display.
    pub lines: Vec<String>,
    /// Whether the front-end should quit.
    pub quit: bool,
}

impl DispatchResult {
    /// A result carrying only display lines (not a quit).
    fn from_lines(lines: Vec<String>) -> Self {
        Self { lines, quit: false }
    }
}

/// One in-progress game plus the cross-game recipe registry.
pub struct GameSession<'r> {
    /// The current board state.
    pub game: HanoiGame,
    /// The active peg labelling.
    pub labelling: Labelling,
    /// The move recorder (default-label space), fed on every successful move.
    pub recorder: Recorder,
    /// The shared recipe store (borrowed, not owned).
    pub registry: &'r mut RecipeRegistry,
}

impl<'r> GameSession<'r> {
    /// Start a fresh game under the default labelling over `registry`.
    pub fn new(num_disks: u32, registry: &'r mut RecipeRegistry) -> Self {
        Self {
            game: HanoiGame::new(num_disks),
            labelling: Labelling::OneTwoThree,
            recorder: Recorder::new(),
            registry,
        }
    }

    // --- Read-only helpers --------------------------------------------------

    /// The number of discs the current game started with.
    pub fn num_disks(&self) -> u32 {
        self.game.num_disks
    }

    /// How many moves have been made in the current game.
    pub fn current_moves(&self) -> u32 {
        self.game.current_moves
    }

    /// Whether the current game has been solved.
    pub fn is_won(&self) -> bool {
        self.game.check_win_condition()
    }

    /// The optimal move count for this game (`2^n - 1`).
    pub fn min_moves(&self) -> u64 {
        (1u64 << self.num_disks()) - 1
    }

    /// A sorted `Valid moves: a -> b, ...` line in the current labels.
    pub fn valid_moves_str(&self) -> String {
        let mut pairs: Vec<String> = self
            .game
            .move_options()
            .iter()
            .map(|mv| {
                let f = change_labels_on_pegs(self.labelling, mv.from_peg) + 1;
                let t = change_labels_on_pegs(self.labelling, mv.to_peg) + 1;
                format!("{f} -> {t}")
            })
            .collect();
        pairs.sort();
        if pairs.is_empty() {
            "No valid moves.".to_string()
        } else {
            format!("Valid moves: {}", pairs.join(", "))
        }
    }

    /// Extra teaching lines a text front-end prints after a plain move: the
    /// three-column rebinding table, but only for a `Move` that actually
    /// happened (dispatch produced no lines) and only under a non-default
    /// labelling. Empty otherwise.
    pub fn move_teaching_lines(&self, cmd: &Command, result: &DispatchResult) -> Vec<String> {
        match cmd {
            Command::Move {
                from_label,
                to_label,
            } if result.lines.is_empty() => format_rebinding_table(
                &[(*from_label, *to_label)],
                self.labelling,
                "Move (your labels)",
            ),
            _ => Vec::new(),
        }
    }

    /// Save the current move sequence under `name`; returns a one-line
    /// confirmation. The caller must not call this mid-game.
    pub fn save_recipe(&mut self, name: &str) -> String {
        let recipe = self.recorder.to_recipe(name, self.num_disks());
        let overwrote = self.registry.contains(name);
        self.registry.save(recipe);
        if overwrote {
            format!("Overwrote recipe '{name}'.")
        } else {
            format!("Saved recipe '{name}'.")
        }
    }

    // --- Dispatch -----------------------------------------------------------

    /// Route a parsed command to its handler.
    pub fn dispatch(&mut self, cmd: &Command) -> DispatchResult {
        match cmd {
            Command::Move {
                from_label,
                to_label,
            } => DispatchResult::from_lines(self.handle_move(*from_label, *to_label)),
            Command::Relabel(labels) => DispatchResult::from_lines(self.handle_relabel(*labels)),
            Command::Apply(name) => DispatchResult::from_lines(self.handle_apply(name)),
            Command::Show(name) => DispatchResult::from_lines(self.handle_show(name)),
            Command::List => DispatchResult::from_lines(self.handle_list()),
            Command::Save(_) => DispatchResult::from_lines(vec![
                "Save only works after winning a game. Keep playing — you'll be \
                 prompted to name the recipe when you finish."
                    .to_string(),
            ]),
            Command::Help => {
                DispatchResult::from_lines(HELP_TEXT.lines().map(str::to_string).collect())
            }
            Command::Quit => DispatchResult {
                lines: Vec::new(),
                quit: true,
            },
            Command::Empty => DispatchResult::default(),
            Command::Error(message) => DispatchResult::from_lines(vec![message.clone()]),
        }
    }

    // --- Per-command handlers -----------------------------------------------

    fn handle_move(&mut self, from_label: u32, to_label: u32) -> Vec<String> {
        let Some((fp, tp)) = labels_to_towers(self.labelling, from_label, to_label) else {
            return vec![format!("Label out of range: {from_label}, {to_label}.")];
        };
        if self.game.is_valid_move(fp, tp) {
            self.game
                .apply_move(Move::new(fp, tp))
                .expect("move validated by is_valid_move just above");
            // Recipes store moves in default-label space (= physical + 1).
            self.recorder.record((fp + 1) as u32, (tp + 1) as u32);
            return Vec::new();
        }
        if self.game.towers[fp].is_empty() {
            return vec![format!("Peg {from_label} is empty — nothing to move.")];
        }
        if let Some(&to_top) = self.game.towers[tp].last() {
            let from_top = *self.game.towers[fp].last().expect("non-empty checked");
            if from_top > to_top {
                return vec![format!(
                    "Can't put disc {from_top} on disc {to_top} — larger on smaller."
                )];
            }
        }
        vec!["Invalid move.".to_string()]
    }

    fn handle_relabel(&mut self, labels: [u32; 3]) -> Vec<String> {
        let Some(new_labelling) = labelling_for(&labels) else {
            return vec![format!("No labelling matches {labels:?}.")];
        };
        self.labelling = new_labelling;
        let [a, b, c] = labels;
        vec![format!(
            "Relabelled: physical pegs 1,2,3 now show as {a},{b},{c}."
        )]
    }

    fn handle_apply(&mut self, name: &str) -> Vec<String> {
        let Some(recipe) = self.registry.get(name).cloned() else {
            return vec![format!(
                "No recipe named '{name}'. Try 'list' to see saved recipes."
            )];
        };
        let mut lines: Vec<String> = vec![format!(
            "Applying recipe '{}' ({} moves):",
            recipe.name,
            recipe.default_moves.len()
        )];
        let table =
            format_rebinding_table(&recipe.default_moves, self.labelling, "Recipe (its labels)");
        if !table.is_empty() {
            lines.push(String::new());
            lines.extend(table);
            lines.push(String::new());
        }
        let results = apply(&recipe, &mut self.game, self.labelling);
        for (i, result) in results.iter().enumerate() {
            let step = i + 1;
            if result.ok() {
                lines.push(format!(
                    "  step {step}: {} -> {}",
                    result.from_label, result.to_label
                ));
                let fp = result.from_peg.expect("a successful step carries pegs");
                let tp = result.to_peg.expect("a successful step carries pegs");
                self.recorder.record((fp + 1) as u32, (tp + 1) as u32);
            } else {
                lines.push(format!(
                    "  step {step}: stopped — {}",
                    result.error.as_deref().unwrap_or("")
                ));
                return lines;
            }
        }
        lines.push("Done.".to_string());
        lines
    }

    fn handle_show(&self, name: &str) -> Vec<String> {
        let Some(recipe) = self.registry.get(name) else {
            return vec![format!(
                "No recipe named '{name}'. Try 'list' to see saved recipes."
            )];
        };
        let n = recipe.default_moves.len();
        let plural = if n == 1 { "" } else { "s" };
        let mut lines: Vec<String> = vec![format!(
            "Recipe '{}' ({} discs, {n} move{plural}):",
            recipe.name, recipe.disk_count
        )];
        for (i, &(a, b)) in recipe.default_moves.iter().enumerate() {
            lines.push(format!("  step {}: {a} -> {b}", i + 1));
        }
        lines
    }

    fn handle_list(&self) -> Vec<String> {
        if self.registry.is_empty() {
            return vec!["No recipes saved yet.".to_string()];
        }
        let names = self.registry.names();
        let width = names.iter().map(String::len).max().unwrap_or(0);
        let mut lines: Vec<String> = vec!["Saved recipes:".to_string()];
        for name in &names {
            let recipe = self.registry.get(name).expect("name came from names()");
            lines.push(format!(
                "  {name:<width$}  ({} discs, {} moves)",
                recipe.disk_count,
                recipe.default_moves.len()
            ));
        }
        lines
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Ported from python/tests/test_recipe.py's GameSession-dependent test.

    #[test]
    fn move_teaching_lines_only_for_a_relabelled_successful_move() {
        let mut reg = RecipeRegistry::new();

        // Default labelling: a move gets no teaching table.
        {
            let mut s = GameSession::new(3, &mut reg);
            let cmd = Command::Move {
                from_label: 1,
                to_label: 2,
            };
            let r = s.dispatch(&cmd);
            assert_eq!(s.move_teaching_lines(&cmd, &r), Vec::<String>::new());
        }

        // Relabelled + a legal move: the three-column table, headed "Move ...".
        {
            let mut s = GameSession::new(3, &mut reg);
            s.dispatch(&Command::Relabel([1, 3, 2]));
            let good = Command::Move {
                from_label: 1,
                to_label: 2,
            };
            let r = s.dispatch(&good);
            let lines = s.move_teaching_lines(&good, &r);
            assert!(lines.iter().any(|ln| ln.contains("Move (your labels)")));
        }

        // Relabelled but an illegal move (empty peg): no teaching, because
        // dispatch produced an error line.
        {
            let mut s = GameSession::new(3, &mut reg);
            s.dispatch(&Command::Relabel([1, 3, 2]));
            let bad = Command::Move {
                from_label: 2,
                to_label: 3,
            };
            let r = s.dispatch(&bad);
            assert_eq!(s.move_teaching_lines(&bad, &r), Vec::<String>::new());
        }
    }

    #[test]
    fn dispatch_basics() {
        let mut reg = RecipeRegistry::new();
        let mut s = GameSession::new(3, &mut reg);
        assert!(s.dispatch(&Command::Quit).quit);
        assert!(s.dispatch(&Command::Empty).lines.is_empty());
        assert_eq!(s.min_moves(), 7);
        // A legal move leaves no message; an illegal one explains.
        assert!(s
            .dispatch(&Command::Move {
                from_label: 1,
                to_label: 3
            })
            .lines
            .is_empty());
        let err = s.dispatch(&Command::Move {
            from_label: 2,
            to_label: 3,
        });
        assert_eq!(err.lines.len(), 1);
        // list is empty initially.
        assert_eq!(
            s.dispatch(&Command::List).lines,
            vec!["No recipes saved yet.".to_string()]
        );
    }
}
