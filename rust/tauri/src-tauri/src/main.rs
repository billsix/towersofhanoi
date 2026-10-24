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
use hanoigame::recipe::{rebinding, RecipeRegistry, Recorder};

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
}

#[derive(Serialize)]
struct RecipeInfo {
    name: String,
    disks: u32,
    moves: usize,
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
    let result = st.dispatch(&Command::Apply(name.clone()));
    let steps = result
        .lines
        .iter()
        .filter(|l| l.trim_start().starts_with("step "))
        .count();
    let message = if steps > 0 {
        format!("Applied '{name}' \u{2014} {steps} moves.")
    } else {
        result.lines.last().cloned().unwrap_or_default()
    };
    st.snapshot(message)
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
