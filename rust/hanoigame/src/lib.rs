// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later

//! `hanoigame` — the shared Towers of Hanoi teaching core, in Rust.
//!
//! This is the Rust port of the Python `hanoigame` package
//! (`python/src/hanoigame/`), kept **in sync** with it feature for feature —
//! the Python version is the behaviour oracle and is never replaced.
//!
//! The crate holds the representation-independent logic every front-end builds
//! on, so the `hanoi` / `hanoi-cli` / `hanoi-gui` binaries stay thin:
//!
//! - [`model`] — the game state ([`HanoiGame`]) and legal-move enumeration.
//! - [`commands`] — the shared input grammar ([`Command`] + `parse`).
//! - [`presenter`] — UI-agnostic rendering and the six peg [`Labelling`]s.
//! - [`recipe`] — record/replay of move sequences in default-label space.
//! - [`engine`] — the [`GameSession`] dispatcher the front-ends share.
//! - [`solvers`] — the standalone teaching solvers (iterative string-rewriting
//!   and recursive), which nothing else in the crate depends on.
//!
//! Still to port (tracked in `tasks/port-to-rust-wxdragon.md`): the board
//! renderers; then the three front-end binaries (`hanoi-cli`, `hanoi` TUI,
//! `hanoi-gui`).

pub mod commands;
pub mod engine;
pub mod model;
pub mod presenter;
pub mod recipe;
pub mod solvers;

pub use commands::Command;
pub use engine::{DispatchResult, GameSession};
pub use model::{HanoiGame, Move, MoveError};
pub use presenter::Labelling;
pub use recipe::{Recipe, RecipeRegistry, Recorder};
