// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later

//! Tauri desktop front-end for the Towers of Hanoi game.
//!
//! A fourth front-end, reusing the same [`hanoigame`] library crate as the CLI,
//! TUI, and wxDragon GUI — not a reimplementation. The Rust backend owns the
//! game state and exposes it through `#[tauri::command]`s; a small static web
//! UI (../frontend) renders the board and drives play over Tauri's IPC. (New in
//! the Rust port; the teaching invariants — the six peg labellings and the
//! label-space recipe rebinding — live in the shared crate and are preserved.)
//!
//! Port note: GUI state is shared across command invocations via Tauri's managed
//! `Mutex<AppState>`; each command moves the game/labelling/recorder into a
//! transient `GameSession` that borrows the registry (the same adaptation the
//! wxDragon GUI uses for the engine's `&mut`-registry design).

// Hide the extra console window on Windows release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;

use serde::Serialize;
use tauri::State;

use hanoigame::commands::Command;
use hanoigame::engine::{DispatchResult, GameSession};
use hanoigame::model::HanoiGame;
use hanoigame::presenter::{self, change_labels_on_pegs, Labelling};
use hanoigame::recipe::{apply, rebinding, rebound_moves, RecipeRegistry, Recorder};

const MAX_DISKS: u32 = 10;
const DEFAULT_DISKS: u32 = 3;

/// The backend's game state (one game + the cross-game recipe registry),
/// behind Tauri's managed `Mutex`.
struct AppState {
    registry: RecipeRegistry,
    game: HanoiGame,
    labelling: Labelling,
    recorder: Recorder,
}

impl AppState {
    fn new(num_disks: u32) -> Self {
        Self {
            registry: RecipeRegistry::new(),
            game: HanoiGame::new(num_disks),
            labelling: Labelling::OneTwoThree,
            recorder: Recorder::new(),
        }
    }

    fn new_game(&mut self, num_disks: u32) {
        self.game = HanoiGame::new(num_disks);
        self.labelling = Labelling::OneTwoThree;
        self.recorder = Recorder::new();
    }

    /// Run a command through a transient [`GameSession`] borrowing the registry
    /// (moving the game/labelling/recorder in and back out).
    fn dispatch(&mut self, cmd: &Command) -> DispatchResult {
        let game = std::mem::replace(&mut self.game, HanoiGame::new(0));
        let recorder = std::mem::take(&mut self.recorder);
        let mut session = GameSession {
            game,
            labelling: self.labelling,
            recorder,
            registry: &mut self.registry,
        };
        let result = session.dispatch(cmd);
        self.labelling = session.labelling;
        self.game = std::mem::replace(&mut session.game, HanoiGame::new(0));
        self.recorder = std::mem::take(&mut session.recorder);
        result
    }

    fn save(&mut self, name: &str) -> String {
        let game = std::mem::replace(&mut self.game, HanoiGame::new(0));
        let recorder = std::mem::take(&mut self.recorder);
        let mut session = GameSession {
            game,
            labelling: self.labelling,
            recorder,
            registry: &mut self.registry,
        };
        let msg = session.save_recipe(name);
        self.game = std::mem::replace(&mut session.game, HanoiGame::new(0));
        self.recorder = std::mem::take(&mut session.recorder);
        msg
    }

    /// Build the serializable view the frontend renders.
    fn snapshot(&self, message: String) -> Snapshot {
        let num_disks = self.game.num_disks;
        let labels: [u32; 3] =
            [0, 1, 2].map(|i| (change_labels_on_pegs(self.labelling, i) + 1) as u32);
        let legal: Vec<[u32; 2]> = self
            .game
            .move_options()
            .iter()
            .map(|mv| {
                [
                    (change_labels_on_pegs(self.labelling, mv.from_peg) + 1) as u32,
                    (change_labels_on_pegs(self.labelling, mv.to_peg) + 1) as u32,
                ]
            })
            .collect();
        let relabelled = self.labelling != Labelling::OneTwoThree;
        let rebinding = if relabelled {
            rebinding(self.labelling)
                .iter()
                .map(|&(label, peg)| [label, peg])
                .collect()
        } else {
            Vec::new()
        };
        let recipes = self
            .registry
            .names()
            .into_iter()
            .filter_map(|name| {
                self.registry.get(&name).map(|r| RecipeInfo {
                    name: name.clone(),
                    disks: r.disk_count,
                    moves: r.default_moves.len(),
                })
            })
            .collect();
        Snapshot {
            board: presenter::render(&self.game, self.labelling),
            towers: self.game.towers.clone(),
            num_disks,
            moves: self.game.current_moves,
            min_moves: (1u64 << num_disks) - 1,
            labels,
            legal,
            won: self.game.check_win_condition(),
            rebinding,
            recipes,
            message,
            apply: None,
        }
    }

    /// Apply `name` to the game, mirroring `GameSession::handle_apply` (apply +
    /// record the successful steps) but capturing the structured result for the
    /// three-panel view. The crate's `apply` does the same game mutation the
    /// dispatch path would; we just keep the `StepResult`s instead of only lines.
    fn apply_structured(&mut self, name: &str) -> ApplyOutcome {
        let Some(recipe) = self.registry.get(name).cloned() else {
            return ApplyOutcome {
                message: format!("No recipe named '{name}'. Use the list to pick one."),
                view: None,
            };
        };
        let labelling = self.labelling;
        let relabelled = labelling != Labelling::OneTwoThree;
        let recipe_moves: Vec<[u32; 2]> =
            recipe.default_moves.iter().map(|&(a, b)| [a, b]).collect();
        let rebound: Vec<[u32; 2]> = rebound_moves(&recipe.default_moves, labelling)
            .iter()
            .map(|&(a, b)| [a, b])
            .collect();
        let rebind: Vec<[u32; 2]> = if relabelled {
            rebinding(labelling).iter().map(|&(l, p)| [l, p]).collect()
        } else {
            Vec::new()
        };

        let results = apply(&recipe, &mut self.game, labelling);
        let mut steps: Vec<ApplyStep> = Vec::new();
        let mut applied = 0usize;
        let mut stopped: Option<String> = None;
        for r in &results {
            steps.push(ApplyStep {
                from_label: r.from_label,
                to_label: r.to_label,
                from_peg: r.from_peg.map(|p| (p + 1) as u32),
                to_peg: r.to_peg.map(|p| (p + 1) as u32),
                error: r.error.clone(),
            });
            if r.ok() {
                let fp = r.from_peg.expect("a successful step carries pegs");
                let tp = r.to_peg.expect("a successful step carries pegs");
                self.recorder.record((fp + 1) as u32, (tp + 1) as u32);
                applied += 1;
            } else {
                stopped = r.error.clone();
            }
        }
        let message = match &stopped {
            Some(e) => format!("Applied '{name}' \u{2014} stopped: {e}"),
            None => format!("Applied '{name}' \u{2014} {applied} moves."),
        };
        ApplyOutcome {
            message,
            view: Some(ApplyView {
                name: name.to_string(),
                relabelled,
                recipe_moves,
                rebinding: rebind,
                rebound_moves: rebound,
                steps,
            }),
        }
    }
}

/// The view-model the frontend renders (one shape returned by every command).
#[derive(Serialize)]
struct Snapshot {
    board: Vec<String>,
    /// The three physical pegs (0, 1, 2), each bottom-to-top disc sizes — the
    /// structured state the `<canvas>` graphics board draws (the text `board`
    /// above is the same state rendered as monospace lines).
    towers: [Vec<u32>; 3],
    num_disks: u32,
    moves: u32,
    min_moves: u64,
    /// The active peg labels (1-indexed) at physical pegs 0, 1, 2.
    labels: [u32; 3],
    /// Currently legal `[from_label, to_label]` moves.
    legal: Vec<[u32; 2]>,
    won: bool,
    /// `[label, physical_peg]` pairs when relabelled (empty under the default) —
    /// the recipe-rebinding teaching key.
    rebinding: Vec<[u32; 2]>,
    recipes: Vec<RecipeInfo>,
    message: String,
    /// Populated only by `apply_recipe`: the three-panel rebinding view + the
    /// per-step replay log (feature-spec.md §4.8). `None` for every other command.
    apply: Option<ApplyView>,
}

#[derive(Serialize)]
struct RecipeInfo {
    name: String,
    disks: u32,
    moves: usize,
}

/// The on-invoke three-panel rebinding view (feature-spec.md §4.8), returned by
/// `apply_recipe`. `recipe_moves | rebinding | rebound_moves` are the three
/// columns; `steps` is the per-step replay log; `relabelled` gates the panel
/// (the three columns are the teaching payoff only under a non-default labelling).
#[derive(Serialize)]
struct ApplyView {
    name: String,
    relabelled: bool,
    recipe_moves: Vec<[u32; 2]>,
    rebinding: Vec<[u32; 2]>,
    rebound_moves: Vec<[u32; 2]>,
    steps: Vec<ApplyStep>,
}

#[derive(Serialize)]
struct ApplyStep {
    from_label: u32,
    to_label: u32,
    /// 1-indexed physical pegs the move resolved to (None if unresolved).
    from_peg: Option<u32>,
    to_peg: Option<u32>,
    /// Failure reason, or None if the step applied.
    error: Option<String>,
}

/// `apply_structured`'s result: the status message + the view (None if no recipe).
struct ApplyOutcome {
    message: String,
    view: Option<ApplyView>,
}

#[tauri::command]
fn snapshot(state: State<'_, Mutex<AppState>>) -> Snapshot {
    state.lock().unwrap().snapshot(String::new())
}

#[tauri::command]
fn new_game(state: State<'_, Mutex<AppState>>, discs: u32) -> Snapshot {
    let mut st = state.lock().unwrap();
    st.new_game(discs.clamp(1, MAX_DISKS));
    st.snapshot(String::new())
}

#[tauri::command]
fn do_move(state: State<'_, Mutex<AppState>>, from: u32, to: u32) -> Snapshot {
    let mut st = state.lock().unwrap();
    let result = st.dispatch(&Command::Move {
        from_label: from,
        to_label: to,
    });
    let message = result
        .lines
        .first()
        .cloned()
        .unwrap_or_else(|| format!("Moved {from} \u{2192} {to}."));
    st.snapshot(message)
}

#[tauri::command]
fn relabel(state: State<'_, Mutex<AppState>>, labels: [u32; 3]) -> Snapshot {
    let mut st = state.lock().unwrap();
    let result = st.dispatch(&Command::Relabel(labels));
    let message = result.lines.first().cloned().unwrap_or_default();
    st.snapshot(message)
}

#[tauri::command]
fn save_recipe(state: State<'_, Mutex<AppState>>, name: String) -> Snapshot {
    let mut st = state.lock().unwrap();
    let message = if st.game.check_win_condition() && !name.trim().is_empty() {
        st.save(name.trim())
    } else if !st.game.check_win_condition() {
        "Save only works after winning a game.".to_string()
    } else {
        "Enter a recipe name.".to_string()
    };
    st.snapshot(message)
}

#[tauri::command]
fn apply_recipe(state: State<'_, Mutex<AppState>>, name: String) -> Snapshot {
    let mut st = state.lock().unwrap();
    let outcome = st.apply_structured(&name);
    let mut snap = st.snapshot(outcome.message);
    snap.apply = outcome.view;
    snap
}

#[tauri::command]
fn show_recipe(state: State<'_, Mutex<AppState>>, name: String) -> Vec<String> {
    let mut st = state.lock().unwrap();
    st.dispatch(&Command::Show(name)).lines
}

fn main() {
    tauri::Builder::default()
        .manage(Mutex::new(AppState::new(DEFAULT_DISKS)))
        .invoke_handler(tauri::generate_handler![
            snapshot,
            new_game,
            do_move,
            relabel,
            save_recipe,
            apply_recipe,
            show_recipe
        ])
        .run(tauri::generate_context!())
        .expect("error while running the Towers of Hanoi Tauri application");
}
