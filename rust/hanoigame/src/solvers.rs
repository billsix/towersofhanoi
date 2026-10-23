// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later

//! Standalone teaching solvers — nothing else in the crate depends on them.
//!
//! Two ways to generate the moves that solve an `n`-disc puzzle, kept side by
//! side for teaching (ports of `hanoiiterative.py` / `hanoirecursive.py`):
//! [`iterative`] builds the list by rewriting peg labels, [`recursive`] by
//! recursion (with the first four levels hand-unrolled). Both return the moves
//! as a newline-separated string of `"from -> to"` lines using the 1-indexed
//! peg labels `1`, `2`, `3`.

pub mod iterative;
pub mod recursive;
