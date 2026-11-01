// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later

//! wxDragon GUI front-end for the Towers of Hanoi game.
//!
//! The three-tier learning flow (feature-spec.md §3.5), mirroring the wxPython
//! oracle `python/src/hanoigame/hanoigui.py`: Tier 1 is always visible (the
//! board, a goal line in the status bar, an always-visible move-history panel,
//! and move feedback); Tier 2 (relabelling + recipes) unlocks at the first win
//! and stays unlocked; Tier 3 keeps recipes and relabelling on the menu bar,
//! out of the workspace. A first-run "How to Play" panel teaches the one rule
//! and the method (solve small, relabel, replay), reopenable from Help.
//!
//! Port notes: the board panel + move buttons are loaded from the **shared
//! `ui/hanoi.xrc`** (the one UI definition the Python and C++ wx front-ends also
//! use) via wxDragon's `XmlResource`; the XRC stays shared and structural, so
//! each front-end carries the tier wiring in its own code (the oracle does the
//! same). Two wxDragon-specific departures from the oracle, both keeping the XRC
//! untouched: (1) the **menu bar is built in code** rather than loaded from the
//! XRC, because wxDragon exposes no way to insert a menu into an XRC-loaded
//! menu bar (`MenuBar` has only a builder `append` and `replace`); (2) the XRC
//! recipe sidebar is **destroyed** rather than hidden, because wxDragon has no
//! sizer hide/detach to collapse the freed slot. The graphics board is drawn in
//! code with the wxDC model (solid fills; no `wxGraphicsContext` in wxDragon).
//! GUI state is shared across wxDragon's `'static` event closures via
//! `Rc<RefCell<GuiState>>`. The recipe-show and rebinding views are monospace
//! dialogs (the same teaching content as the Python's scrollable 3-panel one).

use std::cell::RefCell;
use std::rc::Rc;

use wxdragon::dc::{GradientDirection, Rect as DcRect};
use wxdragon::prelude::*;

use hanoigame::commands::Command;
use hanoigame::engine::{DispatchResult, GameSession};
use hanoigame::model::HanoiGame;
use hanoigame::presenter::{self, change_labels_on_pegs, format_move_tally, Labelling};
use hanoigame::recipe::{format_rebinding_table, RecipeRegistry, Recorder};

/// The shared wx UI definition (repo-root `ui/hanoi.xrc`, reached via the
/// git-tracked `hanoi.xrc` symlink in this crate). `include_str!` bakes the
/// bytes into the binary at compile time, so no XRC file is needed at run time.
/// Only the board panel + move buttons are taken from it; the menu bar is built
/// in code (see the module docs).
const XRC_DATA: &str = include_str!("../hanoi.xrc");

const MAX_DISKS: u32 = 10;
const DEFAULT_DISKS: u32 = 3;

/// The six (from_label, to_label) move-button pairs, in display order; each maps
/// to the XRC button named `move_<from>_<to>`.
const MOVE_PAIRS: [(u32, u32); 6] = [(1, 2), (1, 3), (2, 1), (2, 3), (3, 1), (3, 2)];

/// The six peg-label permutations; each is a Relabel-menu item.
const RELABEL_PERMS: [[u32; 3]; 6] = [
    [1, 2, 3],
    [1, 3, 2],
    [2, 1, 3],
    [2, 3, 1],
    [3, 1, 2],
    [3, 2, 1],
];

/// Tier-1 onboarding text (How to Play), mirroring `hanoigui.py` HOWTO_TEXT. The
/// goal itself lives in the status bar; this teaches the one rule and the method.
const HOWTO_TEXT: &str = "Move the whole stack of discs from peg 1 to peg 3.\n\
     - Move one disc at a time -- always the top disc of a peg.\n\
     - Never place a larger disc on a smaller one.\n\
     \n\
     The method this teaches: solve a SMALL stack, then RELABEL the pegs to\n\
     reuse that solution for a bigger stack -- \"solve small, relabel, replay.\"\n\
     Relabelling and saved recipes unlock after your first win.";

/// `Config` key: show the How-to-Play panel on launch. Cleared by the panel's
/// "Don't show this again" checkbox; re-shown any time from Help / View.
const CONFIG_SHOW_HOWTO: &str = "show_howto_on_start";

// Menu command ids. The menu bar is built in code and dispatched through
// `frame.on_menu_selected` by id -- `MenuItem::on_click` does NOT fire for a
// menu-bar item (it binds on the item's parent *window*, which is null for a
// code-built menu). Custom ids sit above `wxID_HIGHEST` (5999) so they never
// collide with the stock ids (ID_EXIT / ID_ABOUT, used for Quit / About).
const ID_NEW: i32 = 6001;
const ID_NEW_SAME: i32 = 6002;
const ID_STYLE_TEXT: i32 = 6003;
const ID_STYLE_GRAPHICS: i32 = 6004;
const ID_HISTORY_TOGGLE: i32 = 6005;
const ID_HELP_HOWTO: i32 = 6007;
const ID_SAVE: i32 = 6008;
/// First of the six Relabel items (one per permutation): `ID_RELABEL_BASE + i`.
const ID_RELABEL_BASE: i32 = 6010;
/// Per-recipe submenu items: `ID_RECIPE_BASE + 2*i` = View, `+ 2*i + 1` = Apply,
/// where `i` indexes `registry.names()` (sorted, so stable between rebuild and
/// click). Must stay clear of the Relabel block above.
const ID_RECIPE_BASE: i32 = 6100;

// --- Colour palettes (from board_renderers.py) ------------------------------

/// Disc colour by size (1-indexed); cycles past 10 discs.
fn disc_rgb(size: u32) -> (u8, u8, u8) {
    const DISCS: [(u8, u8, u8); 10] = [
        (232, 80, 80),
        (232, 145, 70),
        (235, 200, 75),
        (170, 210, 80),
        (85, 195, 130),
        (75, 170, 220),
        (100, 130, 220),
        (160, 110, 220),
        (220, 110, 200),
        (185, 145, 110),
    ];
    DISCS[((size as usize).saturating_sub(1)) % DISCS.len()]
}

/// Label-badge colour by 0-indexed label (blue / yellow / red).
fn label_rgb(label: usize) -> (u8, u8, u8) {
    const LABELS: [(u8, u8, u8); 3] = [(70, 130, 200), (230, 195, 70), (220, 90, 80)];
    LABELS[label % 3]
}

fn colour((r, g, b): (u8, u8, u8)) -> Colour {
    Colour::rgb(r, g, b)
}

fn darken((r, g, b): (u8, u8, u8), amount: f64) -> Colour {
    let f: f64 = 1.0 - amount;
    Colour::rgb(
        (f64::from(r) * f) as u8,
        (f64::from(g) * f) as u8,
        (f64::from(b) * f) as u8,
    )
}

/// Width of a disc of `size` in an `n`-disc game, up to `max_w` (smallest is
/// 1/3 the largest — a visible difference without being tiny).
fn disc_width(size: u32, n: u32, max_w: f64) -> f64 {
    if n <= 1 {
        return max_w;
    }
    let smallest: f64 = max_w / 3.0;
    smallest + (max_w - smallest) * f64::from(size - 1) / f64::from(n - 1)
}

/// Draw the board onto a device context (solid fills; no gradients/shadows).
/// The three peg-centre x-coordinates for a board `w` pixels wide. Shared by the
/// board drawing and the drag hit-test so they agree on where the pegs are.
fn board_peg_centres(w: i32) -> [f64; 3] {
    let margin: i32 = 20;
    let avail_w: i32 = (w - 2 * margin).max(80);
    let peg_zone_w: f64 = f64::from(avail_w) / 3.0;
    [0, 1, 2].map(|i| f64::from(margin) + peg_zone_w * (f64::from(i) + 0.5))
}

/// The physical peg (0,1,2) whose centre is nearest `x` on a board `w` wide --
/// forgiving drop targeting (the decided spike behaviour).
fn nearest_board_peg(x: i32, w: i32) -> usize {
    let centres: [f64; 3] = board_peg_centres(w);
    let xf: f64 = f64::from(x);
    let mut best: usize = 0;
    for i in 1..3 {
        if (xf - centres[i]).abs() < (xf - centres[best]).abs() {
            best = i;
        }
    }
    best
}

/// Draw the board. `drag_src`/`drag_size`/`drag_x`/`drag_y` describe the disc
/// currently being dragged (if any): it is omitted from its home peg and drawn
/// following the cursor.
#[allow(clippy::too_many_arguments)]
fn draw_board_dc(
    dc: &AutoBufferedPaintDC,
    w: i32,
    h: i32,
    game: &HanoiGame,
    labelling: Labelling,
    drag_src: Option<usize>,
    drag_size: u32,
    drag_x: i32,
    drag_y: i32,
) {
    // Vertical background gradient (top lighter), matching the wxPython renderer's
    // GraphicsContext gradient; the DC can't gradient-fill the rounded pegs/discs, so
    // those stay flat. Transparent text background so the label digits have no box.
    dc.gradient_fill_linear(
        DcRect::new(0, 0, w, h),
        Colour::rgb(45, 52, 68),
        Colour::rgb(20, 26, 38),
        GradientDirection::South,
    );
    dc.set_background_mode(BackgroundMode::Transparent);

    let n: u32 = game.num_disks;
    if n == 0 {
        return;
    }
    let relabelled: bool = labelling != Labelling::OneTwoThree;

    let margin: i32 = 20;
    let label_band_h: i32 = if relabelled { 60 } else { 36 };
    let base_h: i32 = 14;
    let avail_w: i32 = (w - 2 * margin).max(80);
    let avail_h: i32 = (h - 2 * margin - label_band_h - base_h).max(80);
    let peg_zone_w: f64 = f64::from(avail_w) / 3.0;
    let disc_h: f64 = (f64::from(avail_h) / f64::from(n.max(4)) * 0.92).min(30.0);
    let max_disc_w: f64 = peg_zone_w * 0.92;
    let peg_w: f64 = (max_disc_w * 0.07).max(8.0);
    let peg_h: f64 = f64::from(avail_h) * 0.95;
    let base_y: f64 = f64::from(h - margin - label_band_h - base_h);
    let peg_top_y: f64 = base_y - peg_h;
    let peg_centres: [f64; 3] = board_peg_centres(w);

    // Base bar.
    dc.set_pen(Colour::rgb(90, 64, 38), 1, PenStyle::Solid);
    dc.set_brush(Colour::rgb(150, 110, 70), BrushStyle::Solid);
    dc.draw_rounded_rectangle(margin, base_y as i32, w - 2 * margin, base_h, 4.0);

    // Pegs.
    for &cx in &peg_centres {
        dc.set_pen(Colour::rgb(120, 86, 50), 1, PenStyle::Solid);
        dc.set_brush(Colour::rgb(160, 120, 75), BrushStyle::Solid);
        dc.draw_rounded_rectangle(
            (cx - peg_w / 2.0) as i32,
            peg_top_y as i32,
            peg_w as i32,
            peg_h as i32,
            peg_w / 2.0,
        );
    }

    // Discs (bottom-up), coloured by size.
    for (p, stack) in game.towers.iter().enumerate() {
        let cx: f64 = peg_centres[p];
        for (idx, &size) in stack.iter().enumerate() {
            // Omit the disc currently being dragged from its home peg.
            if drag_src == Some(p) && idx + 1 == stack.len() {
                continue;
            }
            let dw: f64 = disc_width(size, n, max_disc_w);
            let y: f64 = base_y - (idx as f64 + 1.0) * disc_h * 1.04;
            let rgb: (u8, u8, u8) = disc_rgb(size);
            dc.set_pen(darken(rgb, 0.45), 1, PenStyle::Solid);
            dc.set_brush(colour(rgb), BrushStyle::Solid);
            dc.draw_rounded_rectangle(
                (cx - dw / 2.0) as i32,
                y as i32,
                dw as i32,
                disc_h as i32,
                disc_h / 3.0,
            );
        }
    }

    // Active label badges (coloured circles with the label digit, bold + centred).
    let active_label_y: f64 = base_y
        + f64::from(base_h)
        + if relabelled {
            18.0
        } else {
            f64::from(label_band_h) / 2.0
        };
    if let Some(badge_font) = Font::builder()
        .with_point_size(13)
        .with_weight(FontWeight::Bold)
        .build()
    {
        dc.set_font(&badge_font);
    }
    dc.set_text_foreground(Colour::rgb(255, 255, 255));
    for (p, &cx) in peg_centres.iter().enumerate() {
        let label: usize = change_labels_on_pegs(labelling, p);
        let rgb: (u8, u8, u8) = label_rgb(label);
        dc.set_pen(darken(rgb, 0.40), 1, PenStyle::Solid);
        dc.set_brush(colour(rgb), BrushStyle::Solid);
        dc.draw_circle(cx as i32, active_label_y as i32, 14);
        let text: String = (label + 1).to_string();
        let (tw, th): (i32, i32) = dc.get_text_extent(&text);
        dc.draw_text(&text, cx as i32 - tw / 2, active_label_y as i32 - th / 2);
    }

    // Default 1-2-3 reference row when relabelled (smaller, neutral, centred).
    if relabelled {
        let ref_y: f64 = active_label_y + 26.0;
        if let Some(ref_font) = Font::builder().with_point_size(10).build() {
            dc.set_font(&ref_font);
        }
        dc.set_text_foreground(Colour::rgb(170, 178, 195));
        for (p, &cx) in peg_centres.iter().enumerate() {
            let text: String = (p + 1).to_string();
            let (tw, th): (i32, i32) = dc.get_text_extent(&text);
            dc.draw_text(&text, cx as i32 - tw / 2, ref_y as i32 - th / 2);
        }
    }

    // The dragged disc follows the cursor, drawn on top in its size colour (as
    // if lifted off its peg).
    if drag_src.is_some() {
        let dw: f64 = disc_width(drag_size, n, max_disc_w);
        let rgb: (u8, u8, u8) = disc_rgb(drag_size);
        dc.set_pen(darken(rgb, 0.45), 1, PenStyle::Solid);
        dc.set_brush(colour(rgb), BrushStyle::Solid);
        dc.draw_rounded_rectangle(
            (f64::from(drag_x) - dw / 2.0) as i32,
            (f64::from(drag_y) - disc_h / 2.0) as i32,
            dw as i32,
            disc_h as i32,
            disc_h / 3.0,
        );
    }
}

/// Draw the legal/illegal-move teaching figure onto a DC: a smaller disc may
/// rest on a larger one (left, allowed); a larger disc may never rest on a
/// smaller one (right, forbidden). Mirrors `hanoigui.py` _LegalMoveDiagram
/// (flat wxDC fills — wxDragon has no `wxGraphicsContext`).
fn draw_legal_diagram(dc: &AutoBufferedPaintDC, w: i32, h: i32) {
    // Fill the panel background (AutoBufferedPaintDC must be painted fully).
    let bg: Colour = Colour::rgb(238, 238, 242);
    dc.gradient_fill_linear(DcRect::new(0, 0, w, h), bg, bg, GradientDirection::South);
    dc.set_background_mode(BackgroundMode::Transparent);
    let half: i32 = w / 2;
    draw_diagram_example(dc, 0, half, true);
    draw_diagram_example(dc, half, half, false);
}

/// One two-disc stack centred in `[x0, x0+width]`: wide-under-narrow when
/// `legal`, else narrow-under-wide struck through, with a caption.
fn draw_diagram_example(dc: &AutoBufferedPaintDC, x0: i32, width: i32, legal: bool) {
    let cx: i32 = x0 + width / 2;
    let disc_h: i32 = 16;
    let top_y: i32 = 42;
    let big_w: i32 = 78;
    let small_w: i32 = 42;
    let bottom_w: i32 = if legal { big_w } else { small_w };
    let upper_w: i32 = if legal { small_w } else { big_w };
    let accent: (u8, u8, u8) = if legal { (40, 150, 60) } else { (200, 55, 55) };

    dc.set_pen(Colour::rgb(30, 30, 40), 1, PenStyle::Solid);
    dc.set_brush(Colour::rgb(210, 210, 215), BrushStyle::Solid);
    dc.draw_rounded_rectangle(cx - bottom_w / 2, top_y + disc_h, bottom_w, disc_h, 4.0);
    dc.draw_rounded_rectangle(cx - upper_w / 2, top_y, upper_w, disc_h, 4.0);

    if !legal {
        dc.set_pen(colour(accent), 3, PenStyle::Solid);
        dc.draw_line(
            cx - big_w / 2,
            top_y - 4,
            cx + big_w / 2,
            top_y + disc_h + 4,
        );
    }

    dc.set_text_foreground(colour(accent));
    let caption: &str = if legal {
        "\u{2713}  smaller on larger"
    } else {
        "\u{2717}  larger on smaller"
    };
    let (tw, _th): (i32, i32) = dc.get_text_extent(caption);
    dc.draw_text(caption, cx - tw / 2, 84);
}

/// The whole GUI's mutable state.
struct GuiState {
    registry: RecipeRegistry,
    game: HanoiGame,
    labelling: Labelling,
    recorder: Recorder,
    disc_count: u32,
    graphics_mode: bool,
    /// Tier-2 gating (feature-spec §3.5): relabel + recipes unlock at the first
    /// win and stay unlocked for the rest of the session.
    won_once: bool,
    frame: Frame,
    board_text: TextCtrl,
    board_graphics: Panel,
    move_buttons: Vec<Button>,
    // Menu handles `refresh` touches (the menu is built in code, not from XRC).
    relabel_items: Vec<MenuItem>,
    recipe_menu: Menu,
    recipe_save_item: MenuItem,
    // Tier-1 onboarding + always-visible history, built in code.
    config: Config,
    history_panel: Panel,
    history_header: StaticText,
    history_list: ListBox,
    history_toggle: MenuItem,
    // Disc drag-drop (spike): the physical peg (0,1,2) whose top disc is being
    // dragged, its size, and the cursor position on the board panel.
    drag_src: Option<usize>,
    drag_size: u32,
    drag_x: i32,
    drag_y: i32,
}

impl GuiState {
    /// Run a command through a transient [`GameSession`] borrowing the shared
    /// registry (moving the game/labelling/recorder in and back out).
    fn dispatch(&mut self, cmd: &Command) -> DispatchResult {
        let game: HanoiGame = std::mem::replace(&mut self.game, HanoiGame::new(0));
        let recorder: Recorder = std::mem::take(&mut self.recorder);
        let mut session: GameSession<'_> = GameSession {
            game,
            labelling: self.labelling,
            recorder,
            registry: &mut self.registry,
        };
        let result: DispatchResult = session.dispatch(cmd);
        self.labelling = session.labelling;
        self.game = std::mem::replace(&mut session.game, HanoiGame::new(0));
        self.recorder = std::mem::take(&mut session.recorder);
        result
    }

    /// Save the current (won) solution under `name`; returns the confirmation.
    fn save(&mut self, name: &str) -> String {
        let game: HanoiGame = std::mem::replace(&mut self.game, HanoiGame::new(0));
        let recorder: Recorder = std::mem::take(&mut self.recorder);
        let mut session: GameSession<'_> = GameSession {
            game,
            labelling: self.labelling,
            recorder,
            registry: &mut self.registry,
        };
        let msg: String = session.save_recipe(name);
        self.game = std::mem::replace(&mut session.game, HanoiGame::new(0));
        self.recorder = std::mem::take(&mut session.recorder);
        msg
    }

    /// Start a fresh `n`-disc game. The `won_once` latch is NOT reset — Tier 2
    /// stays unlocked for the rest of the session once earned (feature-spec §3.5).
    fn new_game(&mut self, n: u32) {
        self.disc_count = n;
        self.game = HanoiGame::new(n);
        self.labelling = Labelling::OneTwoThree;
        self.recorder = Recorder::new();
    }

    fn is_won(&self) -> bool {
        self.game.check_win_condition()
    }

    fn min_moves(&self) -> u64 {
        (1u64 << self.game.num_disks) - 1
    }

    /// The text board, horizontally centred and pushed to the bottom of the text
    /// control — matching the wxPython TextBoardRenderer (which the maintainer
    /// prefers), rather than sitting top-left. Recomputed on every refresh from
    /// the control's current size (wxDragon exposes no resize hook, so a bare
    /// window-resize reflows only on the next state change — close enough).
    fn centred_board_text(&self) -> String {
        let lines: Vec<String> = presenter::render(&self.game, self.labelling);
        let Some(first) = lines.first() else {
            return String::new();
        };
        let size: Size = self.board_text.get_size();
        let char_w: i32 = self.board_text.get_char_width().max(1);
        let line_h: i32 = self.board_text.get_char_height().max(1);
        let visible_cols: i32 = (size.width / char_w).max(1);
        let visible_rows: i32 = (size.height / line_h).max(1);
        let line_width: i32 = first.chars().count() as i32;
        let h_pad: usize = ((visible_cols - line_width) / 2).max(0) as usize;
        let pad: String = " ".repeat(h_pad);
        let centred: Vec<String> = lines.iter().map(|l| format!("{pad}{l}")).collect();
        // -1 of slack so the bottom line isn't under a horizontal scrollbar.
        let v_pad: usize = (visible_rows - centred.len() as i32 - 1).max(0) as usize;
        format!("{}{}", "\n".repeat(v_pad), centred.join("\n"))
    }

    /// Redraw the board and re-sync every control to the session.
    fn refresh(&self) {
        // Board.
        self.board_text.set_value(&self.centred_board_text());
        if self.graphics_mode {
            self.board_graphics.refresh(true, None);
        }

        let won: bool = self.is_won();
        let legal: Vec<(u32, u32)> = self
            .game
            .move_options()
            .iter()
            .map(|mv| {
                (
                    (change_labels_on_pegs(self.labelling, mv.from_peg) + 1) as u32,
                    (change_labels_on_pegs(self.labelling, mv.to_peg) + 1) as u32,
                )
            })
            .collect();
        for (btn, &(f, t)) in self.move_buttons.iter().zip(MOVE_PAIRS.iter()) {
            btn.set_label(&format!("{f} \u{2192} {t}"));
            btn.enable(!won && legal.contains(&(f, t)));
        }

        // Relabel-menu bullets (active permutation marked; display-only). The
        // items are NORMAL (not radio) — a radio's checked state is unreliable on
        // wxGTK — so the active one is marked by rewriting its label. Tier-2
        // gating: each item is enabled only once `won_once`.
        let current: [u32; 3] =
            [0, 1, 2].map(|i| (change_labels_on_pegs(self.labelling, i) + 1) as u32);
        for (item, perm) in self.relabel_items.iter().zip(RELABEL_PERMS.iter()) {
            let marker: &str = if *perm == current {
                "\u{25CF}  "
            } else {
                "    "
            };
            item.set_label(&format!("{marker}{} {} {}", perm[0], perm[1], perm[2]));
            item.enable(self.won_once);
        }

        // Tier-2 gating (dim, don't remove): the Relabel and Recipe top menus are
        // disabled until the first win, then stay enabled for the session. Save
        // is enabled only on a won game.
        if let Some(mb) = self.frame.get_menu_bar() {
            mb.enable_top(1, self.won_once); // Relabel pegs
            mb.enable_top(2, self.won_once); // Recipe
        }
        self.recipe_save_item.enable(won);

        self.update_history();
        self.update_goal();
        self.frame
            .set_status_text(&format!("Moves: {}", self.game.current_moves), 2);
    }

    /// Repopulate the always-visible move-history panel from the recorder: every
    /// move this game in the default 1-2-3 labels, with a live count vs 2^N-1.
    fn update_history(&self) {
        let tally: Vec<String> = format_move_tally(&self.recorder.default_moves);
        self.history_list.clear();
        for line in &tally {
            self.history_list.append(line);
        }
        let count: usize = self.recorder.default_moves.len();
        let noun: &str = if count == 1 { "move" } else { "moves" };
        self.history_header.set_label(&format!(
            "{count} {noun}  optimal {} (default 1-2-3 labels)",
            self.min_moves()
        ));
    }

    /// The persistent goal line in the status bar (field 0) for the current disc
    /// count; the full rules live in the How-to-Play panel, so this stays terse.
    fn update_goal(&self) {
        self.frame.set_status_text(
            &format!("Goal: move all {} discs to peg 3", self.game.num_disks),
            0,
        );
    }

    /// The win message for the feedback field: the move count vs the optimum and
    /// the Tier-2-unlocked handoff.
    fn win_message(&self) -> String {
        let min: u64 = self.min_moves();
        let moves: u64 = u64::from(self.game.current_moves);
        let verdict: String = if moves == min {
            "Optimal!".to_string()
        } else {
            format!("{} more than the minimum ({min}).", moves - min)
        };
        format!(
            "Solved in {moves} moves \u{2014} {verdict}  Relabel pegs and Recipe are now \
             unlocked: save this solve, start a bigger stack, and reuse it."
        )
    }
}

// --- Handlers ---------------------------------------------------------------

fn on_move(state: &Rc<RefCell<GuiState>>, from_label: u32, to_label: u32) {
    let moves_for_dialog: Option<Vec<(u32, u32)>> = {
        let mut st: std::cell::RefMut<'_, GuiState> = state.borrow_mut();
        let relabelled: bool = st.labelling != Labelling::OneTwoThree;
        let result: DispatchResult = st.dispatch(&Command::Move {
            from_label,
            to_label,
        });
        let (status, moves): (String, Option<Vec<(u32, u32)>>) =
            if let Some(line) = result.lines.first() {
                (line.clone(), None)
            } else {
                (
                    format!("Moved {from_label} \u{2192} {to_label}."),
                    if relabelled {
                        Some(vec![(from_label, to_label)])
                    } else {
                        None
                    },
                )
            };
        st.frame.set_status_text(&status, 1);
        if st.is_won() {
            st.won_once = true;
        }
        st.refresh();
        if st.is_won() {
            let msg: String = st.win_message();
            st.frame.set_status_text(&msg, 1);
        }
        moves
    };
    if let Some(moves) = moves_for_dialog {
        let (frame, labelling): (Frame, Labelling) = {
            let st: std::cell::Ref<'_, GuiState> = state.borrow();
            (st.frame.clone(), st.labelling)
        };
        show_rebinding(&frame, "Rebinding for your move", &moves, labelling);
    }
}

/// Show `lines` in a MONOSPACE dialog. The rebinding / recipe-show text is laid out as
/// aligned columns assuming a fixed-width font (like the CLI/TUI); a `MessageDialog` uses
/// a proportional font, which collapses the columns. A read-only teletype `TextCtrl`
/// keeps the columns aligned, matching the Python wx.
fn show_monospace_dialog(parent: &Frame, title: &str, lines: &[String]) {
    let dlg: Dialog = Dialog::builder(parent, title).with_size(640, 460).build();
    let text: TextCtrl = TextCtrl::builder(&dlg)
        .with_style(TextCtrlStyle::MultiLine | TextCtrlStyle::ReadOnly)
        .build();
    if let Some(mono) = Font::builder()
        .with_point_size(11)
        .with_family(FontFamily::Teletype)
        .build()
    {
        text.set_font(&mono);
    }
    text.set_value(&lines.join("\n"));
    let close: Button = Button::builder(&dlg).with_label("Close").build();
    let sizer: BoxSizer = BoxSizer::builder(Orientation::Vertical).build();
    sizer.add(&text, 1, SizerFlag::Expand | SizerFlag::All, 8);
    sizer.add(&close, 0, SizerFlag::All, 8);
    dlg.set_sizer(sizer, true);
    let dlg_for_close: Dialog = dlg.clone();
    close.on_click(move |_| dlg_for_close.end_modal(ID_OK));
    dlg.show_modal();
}

fn show_rebinding(frame: &Frame, title: &str, moves: &[(u32, u32)], labelling: Labelling) {
    let table: Vec<String> = format_rebinding_table(moves, labelling, "Recipe (its labels)");
    if table.is_empty() {
        return;
    }
    show_monospace_dialog(frame, title, &table);
}

fn on_relabel(state: &Rc<RefCell<GuiState>>, perm: [u32; 3]) {
    let mut st: std::cell::RefMut<'_, GuiState> = state.borrow_mut();
    let result: DispatchResult = st.dispatch(&Command::Relabel(perm));
    if let Some(line) = result.lines.first() {
        st.frame.set_status_text(line, 1);
    }
    st.refresh();
}

fn on_new_game(state: &Rc<RefCell<GuiState>>) {
    let (frame, current): (Frame, u32) = {
        let st: std::cell::Ref<'_, GuiState> = state.borrow();
        (st.frame.clone(), st.disc_count)
    };
    let dlg: TextEntryDialog =
        TextEntryDialog::builder(&frame, "How many discs? (1-10)", "New Game")
            .with_default_value(&current.to_string())
            .build();
    if dlg.show_modal() != ID_OK {
        return;
    }
    let Some(value) = dlg.get_value() else { return };
    let Ok(n) = value.trim().parse::<u32>() else {
        return;
    };
    if !(1..=MAX_DISKS).contains(&n) {
        return;
    }
    let mut st: std::cell::RefMut<'_, GuiState> = state.borrow_mut();
    st.new_game(n);
    st.frame.set_status_text("", 1);
    st.refresh();
}

fn on_new_game_same(state: &Rc<RefCell<GuiState>>) {
    let mut st: std::cell::RefMut<'_, GuiState> = state.borrow_mut();
    let n: u32 = st.disc_count;
    st.new_game(n);
    st.frame.set_status_text("", 1);
    st.refresh();
}

fn on_save(state: &Rc<RefCell<GuiState>>) {
    let (frame, default, won): (Frame, String, bool) = {
        let st: std::cell::Ref<'_, GuiState> = state.borrow();
        (
            st.frame.clone(),
            format!("solve-{}", st.game.num_disks),
            st.is_won(),
        )
    };
    if !won {
        return;
    }
    let dlg: TextEntryDialog = TextEntryDialog::builder(&frame, "Recipe name:", "Save Recipe")
        .with_default_value(&default)
        .build();
    if dlg.show_modal() != ID_OK {
        return;
    }
    let Some(name) = dlg.get_value() else { return };
    let name: String = name.trim().to_string();
    if name.is_empty() {
        return;
    }
    {
        let mut st: std::cell::RefMut<'_, GuiState> = state.borrow_mut();
        let msg: String = st.save(&name);
        st.frame.set_status_text(&msg, 1);
        st.refresh();
    }
    // Recipes changed, so rebuild the Recipe menu's per-recipe submenus.
    rebuild_recipe_menu(state);
}

/// Recipe menu → <name> → Apply: replay the recipe under the current labelling;
/// under a relabelling, pop the three-panel rebinding teaching view.
fn apply_recipe_by_name(state: &Rc<RefCell<GuiState>>, name: &str) {
    let (frame, relabelled, moves): (Frame, bool, Option<Vec<(u32, u32)>>) = {
        let st: std::cell::Ref<'_, GuiState> = state.borrow();
        let moves: Option<Vec<(u32, u32)>> = st.registry.get(name).map(|r| r.default_moves.clone());
        (
            st.frame.clone(),
            st.labelling != Labelling::OneTwoThree,
            moves,
        )
    };
    let labelling: Labelling = {
        let mut st: std::cell::RefMut<'_, GuiState> = state.borrow_mut();
        let result: DispatchResult = st.dispatch(&Command::Apply(name.to_string()));
        // The move count comes from the recipe, not the apply log (which omits
        // the per-step log under a relabelling, feature-spec §4.8).
        if let Some(count) = moves.as_ref().map(Vec::len) {
            st.frame
                .set_status_text(&format!("Applied '{name}' \u{2014} {count} moves."), 1);
        } else if let Some(last) = result.lines.last() {
            st.frame.set_status_text(last, 1);
        }
        if st.is_won() {
            st.won_once = true;
        }
        st.refresh();
        if st.is_won() {
            let msg: String = st.win_message();
            st.frame.set_status_text(&msg, 1);
        }
        st.labelling
    };
    if relabelled {
        if let Some(moves) = moves {
            show_rebinding(
                &frame,
                &format!("Rebinding for '{name}'"),
                &moves,
                labelling,
            );
        }
    }
}

/// Recipe menu → <name> → View: show a saved recipe's steps; under a
/// relabelling, the three-panel rebinding view instead.
fn view_recipe(state: &Rc<RefCell<GuiState>>, name: &str) {
    let (frame, relabelled, moves): (Frame, bool, Option<Vec<(u32, u32)>>) = {
        let st: std::cell::Ref<'_, GuiState> = state.borrow();
        let moves: Option<Vec<(u32, u32)>> = st.registry.get(name).map(|r| r.default_moves.clone());
        (
            st.frame.clone(),
            st.labelling != Labelling::OneTwoThree,
            moves,
        )
    };
    if relabelled {
        if let Some(moves) = moves {
            let labelling: Labelling = state.borrow().labelling;
            show_rebinding(
                &frame,
                &format!("Recipe '{name}' - rebinding"),
                &moves,
                labelling,
            );
        }
        return;
    }
    let lines: Vec<String> = {
        let mut st: std::cell::RefMut<'_, GuiState> = state.borrow_mut();
        st.dispatch(&Command::Show(name.to_string())).lines
    };
    show_monospace_dialog(&frame, &format!("Recipe '{name}'"), &lines);
}

/// Rebuild the Recipe menu's tail: one submenu per saved recipe (View / Apply),
/// or a disabled placeholder when none are saved. The head (Save + separator,
/// items 0-1) is kept; everything after is deleted and re-appended. Mirrors
/// `hanoigui.py` _rebuild_recipe_menu — point at the recipe, not a chooser verb.
fn rebuild_recipe_menu(state: &Rc<RefCell<GuiState>>) {
    let st: std::cell::Ref<'_, GuiState> = state.borrow();
    // Delete the stale tail (everything after Save + separator).
    let items: Vec<MenuItem> = st.recipe_menu.get_menu_items();
    for item in items.iter().skip(2) {
        st.recipe_menu.delete_item(item);
    }
    let names: Vec<String> = st.registry.names();
    if names.is_empty() {
        if let Some(empty) = st.recipe_menu.append(
            ID_ANY as i32,
            "(no saved recipes yet)",
            "",
            ItemKind::Normal,
        ) {
            empty.enable(false);
        }
        return;
    }
    // Each saved recipe (in registry.names() sorted order) gets a submenu with
    // stable ids: View = ID_RECIPE_BASE + 2i, Apply = +2i+1. Dispatch is via
    // frame.on_menu_selected by id -- MenuItem::on_click is a no-op for menu-bar
    // items (its parent-window handle is null), so the handler decodes the id
    // back to this same sorted index.
    for (i, name) in names.iter().enumerate() {
        let Some(recipe) = st.registry.get(name) else {
            continue;
        };
        let label: String = format!(
            "{name}  ({} discs, {} moves)",
            recipe.disk_count,
            recipe.default_moves.len()
        );
        let base: i32 = ID_RECIPE_BASE + 2 * i as i32;
        let submenu: Menu = Menu::builder().build();
        submenu.append(base, "&View", "Show this recipe's steps", ItemKind::Normal);
        submenu.append(
            base + 1,
            "&Apply",
            "Replay under the current labelling",
            ItemKind::Normal,
        );
        st.recipe_menu.append_submenu(submenu, &label, "");
    }
}

/// Swap the visible board renderer (graphics ↔ text) and re-sync the radios.
fn set_board_mode(state: &Rc<RefCell<GuiState>>, graphics: bool) {
    let mut st: std::cell::RefMut<'_, GuiState> = state.borrow_mut();
    st.graphics_mode = graphics;
    st.board_graphics.show(graphics);
    st.board_text.show(!graphics);
    st.frame.layout();
    st.refresh();
}

/// Show or hide the always-visible move-history panel (View → Move history).
fn toggle_history(state: &Rc<RefCell<GuiState>>) {
    let st: std::cell::Ref<'_, GuiState> = state.borrow();
    st.history_panel.show(st.history_toggle.is_checked());
    st.frame.layout();
}

/// Show the "How to Play" onboarding as a centered modal dialog: a heading, the
/// rules text, a flat-DC legal/illegal diagram, a "Don't show this again"
/// checkbox, and a "Got it" button. Shown once on first run (via `call_after`
/// from `main`) and reopenable from Help; the goal itself lives in the status
/// bar (ui-design-principles ruling 4 — a centered dialog, not an inline panel).
fn show_howto_dialog(state: &Rc<RefCell<GuiState>>) {
    let (frame, initial): (Frame, bool) = {
        let st: std::cell::Ref<'_, GuiState> = state.borrow();
        (
            st.frame.clone(),
            st.config.read_bool(CONFIG_SHOW_HOWTO, true),
        )
    };
    let dlg: Dialog = Dialog::builder(&frame, "How to Play").build();
    let heading: StaticText = StaticText::builder(&dlg).with_label("How to Play").build();
    if let Some(head_font) = Font::builder()
        .with_point_size(13)
        .with_weight(FontWeight::Bold)
        .build()
    {
        heading.set_font(&head_font);
    }
    let body: StaticText = StaticText::builder(&dlg).with_label(HOWTO_TEXT).build();
    let diagram: Panel = Panel::builder(&dlg).build();
    diagram.set_background_style(BackgroundStyle::Paint);
    diagram.set_min_size(Size::new(300, 108));
    {
        let d: Panel = diagram.clone();
        diagram.on_paint(move |_| {
            let dc: AutoBufferedPaintDC = AutoBufferedPaintDC::new(&d);
            let (w, h): (i32, i32) = dc.get_size();
            draw_legal_diagram(&dc, w, h);
        });
    }
    let dont_show: CheckBox = CheckBox::builder(&dlg)
        .with_label("Don't show this again")
        .build();
    dont_show.set_value(!initial);
    let got_it: Button = Button::builder(&dlg).with_label("Got it").build();

    let text_col: BoxSizer = BoxSizer::builder(Orientation::Vertical).build();
    text_col.add(&heading, 0, SizerFlag::Bottom, 6);
    text_col.add(&body, 0, SizerFlag::AlignLeft, 0);
    let top_row: BoxSizer = BoxSizer::builder(Orientation::Horizontal).build();
    top_row.add_sizer(&text_col, 1, SizerFlag::Expand | SizerFlag::Right, 12);
    top_row.add(&diagram, 0, SizerFlag::AlignCenterVertical, 0);
    let foot_row: BoxSizer = BoxSizer::builder(Orientation::Horizontal).build();
    foot_row.add(&dont_show, 0, SizerFlag::AlignCenterVertical, 0);
    foot_row.add_stretch_spacer(1);
    foot_row.add(&got_it, 0, SizerFlag::AlignCenterVertical, 0);
    let sizer: BoxSizer = BoxSizer::builder(Orientation::Vertical).build();
    sizer.add_sizer(&top_row, 0, SizerFlag::Expand | SizerFlag::All, 12);
    sizer.add_sizer(
        &foot_row,
        0,
        SizerFlag::Expand | SizerFlag::Left | SizerFlag::Right | SizerFlag::Bottom,
        12,
    );
    dlg.set_sizer(sizer, true);
    dlg.fit();
    dlg.centre();
    {
        let d: Dialog = dlg.clone();
        got_it.on_click(move |_| d.end_modal(ID_OK));
    }
    dlg.show_modal();
    // Persist the "don't show again" choice after the dialog closes.
    let st: std::cell::Ref<'_, GuiState> = state.borrow();
    st.config
        .write_bool(CONFIG_SHOW_HOWTO, !dont_show.get_value());
    st.config.flush(false);
}

fn main() {
    let _ = wxdragon::main(|_| {
        // Load the shared UI definition (the board panel + move buttons) from the
        // baked XRC. The menu bar is built in code below (see the module docs).
        let res: XmlResource = XmlResource::get();
        res.init_all_handlers();
        if let Err(e) = res.load_from_string(XRC_DATA) {
            eprintln!("failed to load hanoi.xrc: {e}");
            return;
        }

        // Per-user preference store (the "show How-to-Play on launch" flag), named
        // so it is stable across runs.
        let config: Config =
            Config::new("hanoi-wx", Some("hanoi"), None, None, ConfigStyle::empty());
        let show_howto_on_start: bool = config.read_bool(CONFIG_SHOW_HOWTO, true);

        let frame: Frame = Frame::builder()
            .with_title("Towers of Hanoi")
            .with_size(Size::new(1040, 660))
            .build();

        // --- Menu bar, built in code (the shared XRC stays untouched) ---
        // The menu bar is built in code and dispatched by id through
        // frame.on_menu_selected (below) -- MenuItem::on_click is a no-op for
        // menu-bar items. Only the handles refresh() needs are kept: the six
        // Relabel items (active-bullet + Tier-2 enable), the Save item (enable),
        // and the two View check items (checked state); everything else is
        // dispatched purely by its id.
        let game_menu: Menu = Menu::builder().build();
        game_menu.append(
            ID_NEW,
            "&New Game…\tCtrl+N",
            "Start a new game",
            ItemKind::Normal,
        );
        game_menu.append(
            ID_NEW_SAME,
            "New Game (Same &Size)\tCtrl+Shift+N",
            "Start a new game with the same disc count",
            ItemKind::Normal,
        );
        game_menu.append_separator();
        game_menu.append(ID_EXIT, "&Quit\tCtrl+Q", "Quit", ItemKind::Normal);

        let relabel_menu: Menu = Menu::builder().build();
        let relabel_items: Vec<MenuItem> = RELABEL_PERMS
            .iter()
            .enumerate()
            .map(|(i, perm)| {
                relabel_menu
                    .append(
                        ID_RELABEL_BASE + i as i32,
                        &format!("{} {} {}", perm[0], perm[1], perm[2]),
                        "Relabel the pegs to this order",
                        ItemKind::Normal,
                    )
                    .expect("relabel item")
            })
            .collect();

        let recipe_menu_build: Menu = Menu::builder().build();
        let recipe_save_item: MenuItem = recipe_menu_build
            .append(
                ID_SAVE,
                "&Save Current Solution\tCtrl+S",
                "Save the just-won solution as a reusable recipe",
                ItemKind::Normal,
            )
            .expect("Save");
        recipe_menu_build.append_separator();
        // The per-recipe submenus are filled by rebuild_recipe_menu once the
        // state exists.

        let view_menu: Menu = Menu::builder().build();
        let style_menu: Menu = Menu::builder().build();
        style_menu.append(
            ID_STYLE_TEXT,
            "&Text",
            "Show the board as monospace text",
            ItemKind::Radio,
        );
        style_menu.append(
            ID_STYLE_GRAPHICS,
            "&Graphics",
            "Show the graphical board",
            ItemKind::Radio,
        );
        view_menu.append_submenu(style_menu, "Board &Style", "");
        view_menu.append_separator();
        let history_toggle: MenuItem = view_menu
            .append(
                ID_HISTORY_TOGGLE,
                "Move &history\tCtrl+H",
                "Show the running list of moves in default 1-2-3 labels",
                ItemKind::Check,
            )
            .expect("history toggle");
        // How-to-Play is a dialog now (Help menu), not a toggled View item.

        let help_menu: Menu = Menu::builder().build();
        help_menu.append(
            ID_HELP_HOWTO,
            "How to &Play",
            "Show the goal and the rules",
            ItemKind::Normal,
        );
        help_menu.append_separator();
        help_menu.append(ID_ABOUT, "&About", "About this program", ItemKind::Normal);

        let menu_bar: MenuBar = MenuBar::builder()
            .append(game_menu, "&Game")
            .append(relabel_menu, "&Relabel pegs")
            .append(recipe_menu_build, "&Recipe")
            .append(view_menu, "&View")
            .append(help_menu, "&Help")
            .build();
        frame.set_menu_bar(menu_bar);
        // Re-fetch the Recipe menu as a borrowed handle for later rebuilds.
        let recipe_menu: Menu = frame
            .get_menu_bar()
            .and_then(|mb| mb.get_menu(2))
            .expect("Recipe menu");
        if let Some(mb) = frame.get_menu_bar() {
            mb.check_item(ID_STYLE_GRAPHICS, true); // graphics is the default board
        }
        history_toggle.check(true);

        let status_bar: StatusBar = frame.create_status_bar(3, 0, ID_ANY as i32, "");
        // Field 0 = goal line; field 1 = action feedback; field 2 = moves counter.
        status_bar.set_status_widths(&[-1, -2, 140]);

        // --- Board panel + move buttons from the shared XRC ---
        let panel: Panel = res
            .load_panel(Some(&frame), "HanoiPanel")
            .expect("HanoiPanel in hanoi.xrc");

        // The board_slot is an empty placeholder panel in the XRC; put the two
        // board widgets (one shown at a time) inside it.
        let board_slot: Panel = panel
            .find_child_by_xrc_name("board_slot")
            .expect("board_slot in hanoi.xrc");
        let board_graphics: Panel = Panel::builder(&board_slot).build();
        board_graphics.set_background_style(BackgroundStyle::Paint);
        let board_text: TextCtrl = TextCtrl::builder(&board_slot)
            .with_style(TextCtrlStyle::MultiLine | TextCtrlStyle::ReadOnly)
            .build();
        board_text.show(false); // graphics is the default view
        let slot_sizer: BoxSizer = BoxSizer::builder(Orientation::Vertical).build();
        slot_sizer.add(&board_graphics, 1, SizerFlag::Expand, 0);
        slot_sizer.add(&board_text, 1, SizerFlag::Expand, 0);
        board_slot.set_sizer(slot_sizer, true);

        let move_buttons: Vec<Button> = MOVE_PAIRS
            .iter()
            .map(|(f, t)| {
                panel
                    .find_child_by_xrc_name(&format!("move_{f}_{t}"))
                    .unwrap_or_else(|| panic!("move_{f}_{t} in hanoi.xrc"))
            })
            .collect();

        // Tier 3: HIDE the XRC recipe sidebar (list + Save/Apply/Show + its static
        // box) -- recipes move to the Recipe menu. wxDragon has no sizer
        // hide/detach, but wxWidgets reclaims a hidden window's sizer space on the
        // next Layout (no wxRESERVE_SPACE_EVEN_IF_HIDDEN on these XRC items), so
        // hiding every window in the Recipes box collapses the slot. We hide
        // rather than destroy: destroying left the StaticBoxSizer holding freed
        // pointers, which GTK then dereferenced in its idle size-allocate -> a
        // segfault at launch. The shared XRC still defines these controls for the
        // other wx front-ends.
        {
            let recipe_list: ListBox = panel
                .find_child_by_xrc_name("recipe_list")
                .expect("recipe_list in hanoi.xrc");
            // The wxStaticBox is the items' parent on modern wxWidgets; hiding it
            // removes the box frame/label. Guard against ever hiding the panel.
            if let Some(bp) = recipe_list.get_parent() {
                if bp.handle_ptr() != panel.handle_ptr() {
                    bp.hide();
                }
            }
            recipe_list.hide();
            for name in ["recipe_save", "recipe_apply", "recipe_show"] {
                if let Some(b) = panel.find_child_by_xrc_name::<Button>(name) {
                    b.hide();
                }
            }
            panel.layout();
        }

        // --- Tier-1 always-visible move-history panel (frame child) ---
        let history_panel: Panel = Panel::builder(&frame).build();
        let history_title: StaticText = StaticText::builder(&history_panel)
            .with_label("Move history")
            .build();
        if let Some(bold) = Font::builder().with_weight(FontWeight::Bold).build() {
            history_title.set_font(&bold);
        }
        let history_header: StaticText = StaticText::builder(&history_panel).with_label("").build();
        let history_list: ListBox = ListBox::builder(&history_panel).build();
        if let Some(mono) = Font::builder()
            .with_point_size(11)
            .with_family(FontFamily::Teletype)
            .build()
        {
            history_list.set_font(&mono);
        }
        history_list.set_min_size(Size::new(240, 220));
        let history_sizer: BoxSizer = BoxSizer::builder(Orientation::Vertical).build();
        history_sizer.add(&history_title, 0, SizerFlag::All, 6);
        history_sizer.add(
            &history_header,
            0,
            SizerFlag::Left | SizerFlag::Right | SizerFlag::Bottom,
            6,
        );
        history_sizer.add(
            &history_list,
            1,
            SizerFlag::Expand | SizerFlag::Left | SizerFlag::Right | SizerFlag::Bottom,
            6,
        );
        history_panel.set_sizer(history_sizer, true);

        // --- Frame layout: [board panel | history]. (How-to-Play is a centered
        // modal dialog now, shown on first run via call_after below and
        // reopenable from Help -- not an inline panel above the board.) ---
        let row: BoxSizer = BoxSizer::builder(Orientation::Horizontal).build();
        row.add(&panel, 1, SizerFlag::Expand, 0);
        row.add(
            &history_panel,
            0,
            SizerFlag::Expand | SizerFlag::Top | SizerFlag::Bottom | SizerFlag::Right,
            6,
        );
        let frame_sizer: BoxSizer = BoxSizer::builder(Orientation::Vertical).build();
        frame_sizer.add_sizer(&row, 1, SizerFlag::Expand, 0);
        frame.set_sizer(frame_sizer, true);

        let state: Rc<RefCell<GuiState>> = Rc::new(RefCell::new(GuiState {
            registry: RecipeRegistry::new(),
            game: HanoiGame::new(DEFAULT_DISKS),
            labelling: Labelling::OneTwoThree,
            recorder: Recorder::new(),
            disc_count: DEFAULT_DISKS,
            graphics_mode: true,
            won_once: false,
            frame: frame.clone(),
            board_text: board_text.clone(),
            board_graphics: board_graphics.clone(),
            move_buttons: move_buttons.clone(),
            relabel_items: relabel_items.clone(),
            recipe_menu,
            recipe_save_item,
            config,
            history_panel: history_panel.clone(),
            history_header: history_header.clone(),
            history_list: history_list.clone(),
            history_toggle,
            drag_src: None,
            drag_size: 0,
            drag_x: 0,
            drag_y: 0,
        }));

        // Graphics board paint handler.
        {
            let st: Rc<RefCell<GuiState>> = state.clone();
            let panel_clone: Panel = board_graphics.clone();
            board_graphics.on_paint(move |_| {
                let dc: AutoBufferedPaintDC = AutoBufferedPaintDC::new(&panel_clone);
                let (w, h): (i32, i32) = dc.get_size();
                let s: std::cell::Ref<'_, GuiState> = st.borrow();
                draw_board_dc(
                    &dc,
                    w,
                    h,
                    &s.game,
                    s.labelling,
                    s.drag_src,
                    s.drag_size,
                    s.drag_x,
                    s.drag_y,
                );
            });
        }

        // Disc drag-drop (spike): press picks up the top disc of the nearest peg,
        // motion moves it, release drops on the nearest peg and dispatches through
        // the engine (on_move, which validates + reports an illegal drop). No
        // mouse capture -- wxDragon exposes no capture-lost handler, and the board
        // panel fills the drag area. The move buttons stay as the accessible path.
        {
            let st: Rc<RefCell<GuiState>> = state.clone();
            board_graphics.on_mouse_left_down(move |ev: WindowEventData| {
                let WindowEventData::MouseButton(e) = ev else {
                    return;
                };
                let Some(pos) = e.get_position() else { return };
                let mut s: std::cell::RefMut<'_, GuiState> = st.borrow_mut();
                if s.is_won() {
                    return;
                }
                let w: i32 = s.board_graphics.get_size().width;
                let peg: usize = nearest_board_peg(pos.x, w);
                if let Some(&top) = s.game.towers[peg].last() {
                    s.drag_src = Some(peg);
                    s.drag_size = top;
                    s.drag_x = pos.x;
                    s.drag_y = pos.y;
                    s.board_graphics.refresh(true, None);
                }
            });
        }
        {
            let st: Rc<RefCell<GuiState>> = state.clone();
            board_graphics.on_mouse_motion(move |ev: WindowEventData| {
                let WindowEventData::MouseMotion(e) = ev else {
                    return;
                };
                let mut s: std::cell::RefMut<'_, GuiState> = st.borrow_mut();
                if s.drag_src.is_none() {
                    return;
                }
                if let Some(pos) = e.get_position() {
                    s.drag_x = pos.x;
                    s.drag_y = pos.y;
                    s.board_graphics.refresh(true, None);
                }
            });
        }
        {
            let st: Rc<RefCell<GuiState>> = state.clone();
            board_graphics.on_mouse_left_up(move |ev: WindowEventData| {
                let WindowEventData::MouseButton(e) = ev else {
                    return;
                };
                let (src, target): (usize, usize) = {
                    let mut s: std::cell::RefMut<'_, GuiState> = st.borrow_mut();
                    let Some(src) = s.drag_src.take() else { return };
                    let Some(pos) = e.get_position() else { return };
                    let w: i32 = s.board_graphics.get_size().width;
                    let target: usize = nearest_board_peg(pos.x, w);
                    s.board_graphics.refresh(true, None); // snap back to true state
                    (src, target)
                };
                if target != src {
                    let labelling: Labelling = st.borrow().labelling;
                    let from_label: u32 = (change_labels_on_pegs(labelling, src) + 1) as u32;
                    let to_label: u32 = (change_labels_on_pegs(labelling, target) + 1) as u32;
                    on_move(&st, from_label, to_label);
                }
            });
        }

        // Move buttons.
        for (btn, (f, t)) in move_buttons.iter().zip(MOVE_PAIRS.iter()) {
            let st: Rc<RefCell<GuiState>> = state.clone();
            let (f, t): (u32, u32) = (*f, *t);
            btn.on_click(move |_| on_move(&st, f, t));
        }

        // Menu dispatch: ONE handler on the frame catches every menu command by
        // id. MenuItem::on_click is a no-op for menu-bar items (it binds on the
        // item's parent *window*, which is null for a code-built menu), so all
        // menu actions -- static and the dynamic per-recipe items -- route here.
        {
            let st: Rc<RefCell<GuiState>> = state.clone();
            let frame_for_menu: Frame = frame.clone();
            frame.on_menu_selected(move |ev: MenuEventData| {
                let id: i32 = ev.get_id();
                match id {
                    ID_NEW => on_new_game(&st),
                    ID_NEW_SAME => on_new_game_same(&st),
                    ID_EXIT => frame_for_menu.close(true),
                    ID_ABOUT => {
                        MessageDialog::builder(
                            &frame_for_menu,
                            "Towers of Hanoi\n\nA teaching tool: solve small, relabel pegs, \
                             replay. Shares its model and dispatcher with the CLI and TUI \
                             front-ends.",
                            "About Towers of Hanoi",
                        )
                        .build()
                        .show_modal();
                    }
                    ID_STYLE_TEXT => set_board_mode(&st, false),
                    ID_STYLE_GRAPHICS => set_board_mode(&st, true),
                    ID_HISTORY_TOGGLE => toggle_history(&st),
                    ID_HELP_HOWTO => show_howto_dialog(&st),
                    ID_SAVE => on_save(&st),
                    _ if (ID_RELABEL_BASE..ID_RELABEL_BASE + RELABEL_PERMS.len() as i32)
                        .contains(&id) =>
                    {
                        on_relabel(&st, RELABEL_PERMS[(id - ID_RELABEL_BASE) as usize]);
                    }
                    _ if id >= ID_RECIPE_BASE => {
                        // ID_RECIPE_BASE + 2i = View, +2i+1 = Apply, i indexing
                        // registry.names() (sorted, same order as rebuild).
                        let offset: i32 = id - ID_RECIPE_BASE;
                        let i: usize = (offset / 2) as usize;
                        let is_apply: bool = offset % 2 == 1;
                        let name: Option<String> = st.borrow().registry.names().into_iter().nth(i);
                        if let Some(name) = name {
                            if is_apply {
                                apply_recipe_by_name(&st, &name);
                            } else {
                                view_recipe(&st, &name);
                            }
                        }
                    }
                    _ => {}
                }
            });
        }

        // How-to-Play is a dialog now (built in show_howto_dialog), so there are
        // no inline-panel controls to wire here.

        rebuild_recipe_menu(&state);
        state.borrow().refresh();
        frame.show(true);
        frame.centre();
        // First-run How-to-Play: the frame is up, so show the centered modal now
        // (show_modal runs a nested loop, then the main loop starts). Reopen from
        // Help. (wxDragon's call_after requires Send, which the Rc state is not,
        // so this is shown directly rather than deferred like the C++/Python wx.)
        if show_howto_on_start {
            show_howto_dialog(&state);
        }
    });
}
