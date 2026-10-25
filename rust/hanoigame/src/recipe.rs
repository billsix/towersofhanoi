// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later

//! Recipes — saved sequences of moves the user can replay.
//!
//! Recipes are stored in **default-label space** (1-indexed physical peg
//! numbers — the labels visible under the default `OneTwoThree` labelling), so
//! a recipe is independent of whatever labelling was active when it was
//! captured. At apply time the stored values are reinterpreted as labels under
//! the *current* labelling — the relabel-and-replay teaching moment. (Rust port
//! of `python/src/hanoigame/recipe.py`, kept in sync.)
//!
//! Port note: Python's lazy `apply_iter` generator becomes [`Replay`], a
//! stepper whose [`Replay::step`] takes `&mut HanoiGame` per move — a Rust
//! `Iterator` can't both drive and let the caller observe the game between
//! steps. [`apply`] is the eager form the engine uses.

use std::collections::HashMap;

use crate::model::{HanoiGame, Move};
use crate::presenter::{label_to_tower, labels_to_towers, Labelling};

/// A saved sequence of moves in default-label space (1-indexed).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Recipe {
    /// The recipe's identifier, used as the registry key.
    pub name: String,
    /// Disc count of the game when the recipe was captured.
    pub disk_count: u32,
    /// The move sequence as `(from, to)` pairs of 1-indexed physical pegs.
    pub default_moves: Vec<(u32, u32)>,
}

impl Recipe {
    /// Construct a recipe directly (mostly for tests and the registry).
    pub fn new(name: &str, disk_count: u32, default_moves: Vec<(u32, u32)>) -> Self {
        Self {
            name: name.to_string(),
            disk_count,
            default_moves,
        }
    }
}

/// Front-end-side log of moves, stored in default-label space. The front-end
/// converts user-typed labels to default space (via
/// [`labels_to_towers`](crate::presenter::labels_to_towers) plus 1) before
/// calling [`Recorder::record`].
#[derive(Debug, Default, Clone)]
pub struct Recorder {
    /// Accumulated moves as `(from, to)` pairs of 1-indexed physical pegs.
    pub default_moves: Vec<(u32, u32)>,
}

impl Recorder {
    /// A fresh, empty recorder.
    pub fn new() -> Self {
        Self::default()
    }

    /// Record a move expressed as 1-indexed physical pegs (default-label space).
    pub fn record(&mut self, from_default: u32, to_default: u32) {
        self.default_moves.push((from_default, to_default));
    }

    /// Discard all recorded moves.
    pub fn reset(&mut self) {
        self.default_moves.clear();
    }

    /// Freeze the recorded moves into a named [`Recipe`].
    pub fn to_recipe(&self, name: &str, disk_count: u32) -> Recipe {
        Recipe::new(name, disk_count, self.default_moves.clone())
    }
}

/// In-memory recipe store, scoped to a single session.
#[derive(Debug, Default)]
pub struct RecipeRegistry {
    by_name: HashMap<String, Recipe>,
}

impl RecipeRegistry {
    /// A fresh, empty registry.
    pub fn new() -> Self {
        Self::default()
    }

    /// Store `recipe`, replacing any existing recipe of the same name.
    pub fn save(&mut self, recipe: Recipe) {
        self.by_name.insert(recipe.name.clone(), recipe);
    }

    /// Look up a recipe by name.
    pub fn get(&self, name: &str) -> Option<&Recipe> {
        self.by_name.get(name)
    }

    /// All saved recipe names, sorted alphabetically.
    pub fn names(&self) -> Vec<String> {
        let mut names: Vec<String> = self.by_name.keys().cloned().collect();
        names.sort();
        names
    }

    /// The number of saved recipes.
    pub fn len(&self) -> usize {
        self.by_name.len()
    }

    /// Whether no recipes are saved.
    pub fn is_empty(&self) -> bool {
        self.by_name.is_empty()
    }

    /// Whether a recipe with the given name is saved.
    pub fn contains(&self, name: &str) -> bool {
        self.by_name.contains_key(name)
    }
}

/// One move's worth of [`apply`] / [`Replay::step`] output.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StepResult {
    /// The recipe's stored source value (default-label space).
    pub from_label: u32,
    /// The recipe's stored destination value (default-label space).
    pub to_label: u32,
    /// 0-indexed physical source peg the move hit, or `None` if unresolved.
    pub from_peg: Option<usize>,
    /// 0-indexed physical destination peg, or `None` if unresolved.
    pub to_peg: Option<usize>,
    /// Failure message, or `None` if the move was applied successfully.
    pub error: Option<String>,
}

impl StepResult {
    /// Whether the move succeeded (no error recorded).
    pub fn ok(&self) -> bool {
        self.error.is_none()
    }
}

/// A recipe replay in progress: steps through the recipe's moves, applying each
/// legal one to a game passed to [`Replay::step`] and stopping after the first
/// failure. The eager [`apply`] drives this to completion.
#[derive(Debug)]
pub struct Replay {
    moves: Vec<(u32, u32)>,
    idx: usize,
    labelling: Labelling,
    stopped: bool,
}

impl Replay {
    /// Begin replaying `recipe` under `labelling`.
    pub fn new(recipe: &Recipe, labelling: Labelling) -> Self {
        Self {
            moves: recipe.default_moves.clone(),
            idx: 0,
            labelling,
            stopped: false,
        }
    }

    /// Apply the next recipe move to `game`, returning its [`StepResult`], or
    /// `None` once the recipe is exhausted or a prior step failed.
    pub fn step(&mut self, game: &mut HanoiGame) -> Option<StepResult> {
        if self.stopped || self.idx >= self.moves.len() {
            return None;
        }
        let (from_label, to_label): (u32, u32) = self.moves[self.idx];
        self.idx += 1;

        let Some((fp, tp)) = labels_to_towers(self.labelling, from_label, to_label) else {
            self.stopped = true;
            return Some(StepResult {
                from_label,
                to_label,
                from_peg: None,
                to_peg: None,
                error: Some(format!(
                    "Recipe move '{from_label} -> {to_label}' uses a label that \
                     doesn't exist under the current labelling."
                )),
            });
        };

        if game.is_valid_move(fp, tp) {
            game.apply_move(Move::new(fp, tp))
                .expect("move validated by is_valid_move just above");
            Some(StepResult {
                from_label,
                to_label,
                from_peg: Some(fp),
                to_peg: Some(tp),
                error: None,
            })
        } else {
            self.stopped = true;
            Some(StepResult {
                from_label,
                to_label,
                from_peg: Some(fp),
                to_peg: Some(tp),
                error: Some(explain_illegal(game, fp, tp, from_label, to_label)),
            })
        }
    }
}

/// Replay `recipe` against `game` under `labelling`, returning every
/// [`StepResult`] in order and stopping after the first failure. No disc-count
/// check: a small recipe may legitimately apply to a larger game (the whole
/// point — small solutions as sub-routines); move legality is the gatekeeper.
pub fn apply(recipe: &Recipe, game: &mut HanoiGame, labelling: Labelling) -> Vec<StepResult> {
    let mut replay: Replay = Replay::new(recipe, labelling);
    let mut results: Vec<StepResult> = Vec::new();
    while let Some(result) = replay.step(game) {
        let failed: bool = result.error.is_some();
        results.push(result);
        if failed {
            break;
        }
    }
    results
}

/// A human-readable reason a recipe move is illegal in the current state.
fn explain_illegal(
    game: &HanoiGame,
    from_peg: usize,
    to_peg: usize,
    from_label: u32,
    to_label: u32,
) -> String {
    let step: String = format!("recipe move '{from_label} -> {to_label}'");
    let Some(&from_top) = game.towers[from_peg].last() else {
        return format!(
            "{step}: peg {from_label} (physical {}) is empty.",
            from_peg + 1
        );
    };
    if let Some(&to_top) = game.towers[to_peg].last() {
        if from_top > to_top {
            return format!(
                "{step}: would put disc {from_top} on disc {to_top} — larger on smaller."
            );
        }
    }
    format!("{step}: illegal in current state.")
}

// --- The rebinding: recipe's local labels -> physical pegs ------------------

/// Map each recipe label 1..=3 to the 1-indexed physical peg it resolves to
/// under `labelling` (the identity `[(1,1),(2,2),(3,3)]` under the default).
pub fn rebinding(labelling: Labelling) -> [(u32, u32); 3] {
    let mut pairs: [(u32, u32); 3] = [(0, 0); 3];
    for (i, label) in [1u32, 2, 3].into_iter().enumerate() {
        let peg: usize =
            label_to_tower(labelling, label).expect("a label in 1..=3 always resolves");
        pairs[i] = (label, (peg + 1) as u32);
    }
    pairs
}

/// Human-readable rebinding lines for the text front-ends; empty under the
/// default labelling (nothing to show).
pub fn format_rebinding(labelling: Labelling) -> Vec<String> {
    if labelling == Labelling::OneTwoThree {
        return Vec::new();
    }
    let body: String = rebinding(labelling)
        .iter()
        .map(|(label, peg)| format!("label {label} -> peg {peg}"))
        .collect::<Vec<String>>()
        .join(",  ");
    vec![
        "  Rebinding (this recipe's labels -> physical pegs, because you relabelled):".to_string(),
        format!("    {body}"),
        "    Each move below is the recorded label, rebound to the peg after '->'.".to_string(),
    ]
}

/// Rewrite each `(from_label, to_label)` move onto the 1-indexed physical pegs
/// those labels currently sit on (identity under the default labelling).
pub fn rebound_moves(moves: &[(u32, u32)], labelling: Labelling) -> Vec<(u32, u32)> {
    moves
        .iter()
        .map(|&(from_label, to_label)| {
            let fp: usize = label_to_tower(labelling, from_label).expect("labels are 1..=3");
            let tp: usize = label_to_tower(labelling, to_label).expect("labels are 1..=3");
            ((fp + 1) as u32, (tp + 1) as u32)
        })
        .collect()
}

/// Render three aligned text columns — the text front-end's equivalent of the
/// GUI's three-panel rebinding view (recipe labels | label->peg key | rebound
/// pegs). Empty under the default labelling.
pub fn format_rebinding_table(
    moves: &[(u32, u32)],
    labelling: Labelling,
    left_header: &str,
) -> Vec<String> {
    if labelling == Labelling::OneTwoThree {
        return Vec::new();
    }
    let left: Vec<String> = moves
        .iter()
        .enumerate()
        .map(|(i, &(a, b))| format!("{}: {a} -> {b}", i + 1))
        .collect();
    let mid: Vec<String> = rebinding(labelling)
        .iter()
        .map(|(label, peg)| format!("label {label} -> peg {peg}"))
        .collect();
    let right: Vec<String> = rebound_moves(moves, labelling)
        .iter()
        .enumerate()
        .map(|(i, &(fp, tp))| format!("{}: {fp} -> {tp}", i + 1))
        .collect();

    let mhdr: &str = "Rebinding";
    let rhdr: &str = "Rebound (pegs)";
    let lw: usize = left
        .iter()
        .map(String::len)
        .chain(std::iter::once(left_header.len()))
        .max()
        .unwrap_or(0);
    let mw: usize = mid
        .iter()
        .map(String::len)
        .chain(std::iter::once(mhdr.len()))
        .max()
        .unwrap_or(0);
    let rows: usize = left.len().max(mid.len()).max(right.len());

    let cell = |col: &[String], i: usize, width: usize| -> String {
        let s: &str = col.get(i).map(String::as_str).unwrap_or("");
        format!("{s:<width$}")
    };

    let mut lines: Vec<String> = vec![
        format!("  {left_header:<lw$}   {mhdr:<mw$}   {rhdr}"),
        format!(
            "  {}   {}   {}",
            "-".repeat(lw),
            "-".repeat(mw),
            "-".repeat(rhdr.len())
        ),
    ];
    for i in 0..rows {
        lines.push(format!(
            "  {}   {}   {}",
            cell(&left, i, lw),
            cell(&mid, i, mw),
            cell(&right, i, 0)
        ));
    }
    lines
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::HanoiGame;

    // Ported from python/tests/test_recipe.py (the GameSession-dependent
    // teaching-lines test lives in engine.rs).

    /// Apply user-typed (label, label) moves, recording each in default space —
    /// the translation the front-end does (the Python test's `_play_labeled`).
    fn play_labeled(
        game: &mut HanoiGame,
        labelling: Labelling,
        moves: &[(u32, u32)],
        rec: &mut Recorder,
    ) {
        for &(from_label, to_label) in moves {
            let (fp, tp) = labels_to_towers(labelling, from_label, to_label).expect("legal label");
            game.apply_move(Move::new(fp, tp)).expect("legal move");
            rec.record((fp + 1) as u32, (tp + 1) as u32);
        }
    }

    #[test]
    fn rebinding_identity_and_relabel() {
        assert_eq!(rebinding(Labelling::OneTwoThree), [(1, 1), (2, 2), (3, 3)]);
        assert_eq!(rebinding(Labelling::OneThreeTwo), [(1, 1), (2, 3), (3, 2)]);
    }

    #[test]
    fn format_rebinding_default_vs_relabelled() {
        assert!(format_rebinding(Labelling::OneTwoThree).is_empty());
        let joined = format_rebinding(Labelling::OneThreeTwo).join("\n");
        assert!(joined.contains("label 2 -> peg 3"));
        assert!(joined.contains("label 3 -> peg 2"));
    }

    #[test]
    fn rebound_moves_identity_and_relabel() {
        let moves = [(1, 2), (1, 3), (2, 3)];
        assert_eq!(
            rebound_moves(&moves, Labelling::OneTwoThree),
            vec![(1, 2), (1, 3), (2, 3)]
        );
        assert_eq!(
            rebound_moves(&moves, Labelling::OneThreeTwo),
            vec![(1, 3), (1, 2), (3, 2)]
        );
        assert_eq!(
            rebound_moves(&[(2, 3)], Labelling::OneThreeTwo),
            vec![(3, 2)]
        );
    }

    #[test]
    fn format_rebinding_table_panels() {
        let moves = [(1, 2), (1, 3), (2, 3)];
        assert!(
            format_rebinding_table(&moves, Labelling::OneTwoThree, "Recipe (its labels)")
                .is_empty()
        );
        let joined = format_rebinding_table(&moves, Labelling::OneThreeTwo, "Recipe (its labels)")
            .join("\n");
        assert!(joined.contains("Recipe (its labels)"));
        assert!(joined.contains("Rebinding"));
        assert!(joined.contains("Rebound (pegs)"));
        assert!(joined.contains("1: 1 -> 2"));
        assert!(joined.contains("label 2 -> peg 3"));
        assert!(joined.contains("1: 1 -> 3"));

        let joined2 =
            format_rebinding_table(&[(2, 3)], Labelling::OneThreeTwo, "Move (your labels)")
                .join("\n");
        assert!(joined2.contains("Move (your labels)"));
        assert!(joined2.contains("1: 2 -> 3"));
        assert!(joined2.contains("1: 3 -> 2"));
    }

    #[test]
    fn recorder_round_trip_and_reset() {
        let mut rec = Recorder::new();
        rec.record(1, 3);
        rec.record(1, 2);
        let recipe = rec.to_recipe("two-moves", 2);
        assert_eq!(recipe.name, "two-moves");
        assert_eq!(recipe.disk_count, 2);
        assert_eq!(recipe.default_moves, vec![(1, 3), (1, 2)]);
        rec.reset();
        assert_eq!(rec.default_moves, Vec::<(u32, u32)>::new());
    }

    #[test]
    fn registry_save_get_names() {
        let mut reg = RecipeRegistry::new();
        reg.save(Recipe::new("foo", 2, vec![(1, 3)]));
        assert!(reg.get("foo").is_some());
        assert!(reg.get("bar").is_none());
        assert_eq!(reg.names(), vec!["foo".to_string()]);
        assert!(reg.contains("foo"));
        assert_eq!(reg.len(), 1);

        reg.save(Recipe::new("foo", 3, vec![(1, 2)]));
        assert_eq!(reg.get("foo").unwrap().default_moves, vec![(1, 2)]);
        assert_eq!(reg.len(), 1);

        reg.save(Recipe::new("zebra", 2, vec![]));
        reg.save(Recipe::new("alpha", 2, vec![]));
        assert_eq!(
            reg.names(),
            vec!["alpha".to_string(), "foo".to_string(), "zebra".to_string()]
        );
    }

    #[test]
    fn apply_same_labelling_wins() {
        let mut g = HanoiGame::new(2);
        let mut rec = Recorder::new();
        play_labeled(
            &mut g,
            Labelling::OneTwoThree,
            &[(1, 2), (1, 3), (2, 3)],
            &mut rec,
        );
        assert!(g.check_win_condition());
        let recipe = rec.to_recipe("solve2", 2);

        let mut g2 = HanoiGame::new(2);
        let results = apply(&recipe, &mut g2, Labelling::OneTwoThree);
        assert!(results.iter().all(StepResult::ok));
        assert_eq!(g2.towers, [vec![], vec![], vec![2, 1]]);
        assert_eq!(g2.current_moves, 3);
    }

    #[test]
    fn recipe_normalises_to_default_space_at_save_time() {
        let mut g = HanoiGame::new(2);
        let mut rec = Recorder::new();
        play_labeled(
            &mut g,
            Labelling::OneThreeTwo,
            &[(1, 2), (1, 3), (2, 3)],
            &mut rec,
        );
        assert_eq!(g.towers, [vec![], vec![2, 1], vec![]]);

        let recipe = rec.to_recipe("solve-from-relabel", 2);
        assert_eq!(recipe.default_moves, vec![(1, 3), (1, 2), (3, 2)]);

        let mut g2 = HanoiGame::new(2);
        let results = apply(&recipe, &mut g2, Labelling::OneTwoThree);
        assert!(results.iter().all(StepResult::ok));
        let pegs: Vec<(Option<usize>, Option<usize>)> =
            results.iter().map(|r| (r.from_peg, r.to_peg)).collect();
        assert_eq!(
            pegs,
            vec![(Some(0), Some(2)), (Some(0), Some(1)), (Some(2), Some(1))]
        );
        assert_eq!(g2.towers, [vec![], vec![2, 1], vec![]]);
    }

    #[test]
    fn apply_through_relabel_solves_subproblem() {
        // Bill's worked example.
        let mut g2 = HanoiGame::new(2);
        let mut rec = Recorder::new();
        play_labeled(
            &mut g2,
            Labelling::OneTwoThree,
            &[(1, 2), (1, 3), (2, 3)],
            &mut rec,
        );
        assert!(g2.check_win_condition());
        let recipe = rec.to_recipe("solve-2-from-1-to-3", 2);

        let mut g3 = HanoiGame::new(3);
        assert_eq!(g3.towers, [vec![3, 2, 1], vec![], vec![]]);
        let results = apply(&recipe, &mut g3, Labelling::OneThreeTwo);
        assert!(results.iter().all(StepResult::ok));
        assert_eq!(g3.towers, [vec![3], vec![2, 1], vec![]]);
        assert_eq!(g3.current_moves, 3);
    }

    #[test]
    fn apply_stops_with_explanation_on_illegal_move() {
        let mut g2 = HanoiGame::new(2);
        let mut rec = Recorder::new();
        play_labeled(
            &mut g2,
            Labelling::OneTwoThree,
            &[(1, 2), (1, 3), (2, 3)],
            &mut rec,
        );
        let recipe = rec.to_recipe("r", 2);

        let mut g1 = HanoiGame::new(1);
        let results = apply(&recipe, &mut g1, Labelling::OneTwoThree);
        assert_eq!(results.len(), 2);
        assert!(results[0].ok());
        let err = results[1].error.as_ref().unwrap();
        assert!(err.contains("is empty"), "got {err:?}");
    }

    #[test]
    fn apply_reports_larger_on_smaller() {
        let mut g3 = HanoiGame::new(3);
        g3.apply_move(Move::new(0, 2)).unwrap(); // disc 1 to peg 3
        let recipe = Recipe::new("bad", 3, vec![(1, 3)]);
        let results = apply(&recipe, &mut g3, Labelling::OneTwoThree);
        assert_eq!(results.len(), 1);
        let err = results[0].error.as_ref().unwrap();
        assert!(err.contains("larger on smaller"), "got {err:?}");
    }

    #[test]
    fn replay_is_lazy_step_mode() {
        let mut g2 = HanoiGame::new(2);
        let mut rec = Recorder::new();
        play_labeled(
            &mut g2,
            Labelling::OneTwoThree,
            &[(1, 2), (1, 3), (2, 3)],
            &mut rec,
        );
        let recipe = rec.to_recipe("r", 2);

        let mut target = HanoiGame::new(2);
        let mut replay = Replay::new(&recipe, Labelling::OneTwoThree);
        replay.step(&mut target);
        assert_eq!(target.towers, [vec![2], vec![1], vec![]]);
        replay.step(&mut target);
        assert_eq!(target.towers, [vec![], vec![1], vec![2]]);
        replay.step(&mut target);
        assert_eq!(target.towers, [vec![], vec![], vec![2, 1]]);
    }
}
