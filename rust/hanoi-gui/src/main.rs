// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later

//! wxDragon GUI front-end for the Towers of Hanoi game.
//!
//! A board (a solid-fill 2D graphics view by default, or a monospace text view)
//! plus six move buttons, a relabel menu, and a recipe list with Save / Apply /
//! Show — all driven by the same [`GameSession`] dispatcher as the CLI and TUI.
//! (Rust port of the wxPython `python/src/hanoigame/hanoigui.py` +
//! `board_renderers.py`, kept in sync.)
//!
//! Port notes: the window (menu bar + panel layout + move/recipe controls) is
//! loaded from the **shared `ui/hanoi.xrc`** — the one UI definition the Python
//! and C++ wx front-ends also use — via wxDragon's `XmlResource`
//! (`load_from_string` on the `include_str!`'d XRC, then `load_panel` /
//! `MenuBar::from_xrc_name`, with children fetched by `find_child_by_xrc_name`).
//! The graphics board is still drawn in code with the wxDC model (solid fills,
//! rounded rectangles, circles) into a sub-panel of the XRC `board_slot`.
//! GUI state is shared across wxDragon's `'static` event closures via
//! `Rc<RefCell<GuiState>>`. The recipe-show and rebinding views are message
//! dialogs rather than the Python's scrollable 3-panel dialog (the teaching
//! content is the same). See `tasks/rust-gui-use-shared-xrc.md`.

use std::cell::RefCell;
use std::rc::Rc;

use wxdragon::dc::{GradientDirection, Rect as DcRect};
use wxdragon::prelude::*;

use hanoigame::commands::Command;
use hanoigame::engine::{DispatchResult, GameSession};
use hanoigame::model::HanoiGame;
use hanoigame::presenter::{self, change_labels_on_pegs, Labelling};
use hanoigame::recipe::{format_rebinding_table, RecipeRegistry, Recorder};

/// The shared wx UI definition (repo-root `ui/hanoi.xrc`, reached via the
/// git-tracked `hanoi.xrc` symlink in this crate). `include_str!` bakes the
/// bytes into the binary at compile time, so no XRC file is needed at run time.
const XRC_DATA: &str = include_str!("../hanoi.xrc");

const MAX_DISKS: u32 = 10;
const DEFAULT_DISKS: u32 = 3;

/// The six (from_label, to_label) move-button pairs, in display order; each maps
/// to the XRC button named `move_<from>_<to>`.
const MOVE_PAIRS: [(u32, u32); 6] = [(1, 2), (1, 3), (2, 1), (2, 3), (3, 1), (3, 2)];

/// The six peg-label permutations; each maps to the XRC menu item
/// `relabel_<a>_<b>_<c>`.
const RELABEL_PERMS: [[u32; 3]; 6] = [
    [1, 2, 3],
    [1, 3, 2],
    [2, 1, 3],
    [2, 3, 1],
    [3, 1, 2],
    [3, 2, 1],
];

/// The XRC name of the relabel menu item for a permutation.
fn relabel_item_name(perm: [u32; 3]) -> String {
    format!("relabel_{}_{}_{}", perm[0], perm[1], perm[2])
}

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
fn draw_board_dc(dc: &AutoBufferedPaintDC, w: i32, h: i32, game: &HanoiGame, labelling: Labelling) {
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
    let peg_centres: [f64; 3] =
        [0, 1, 2].map(|i| f64::from(margin) + peg_zone_w * (f64::from(i) + 0.5));

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
}

/// The whole GUI's mutable state.
struct GuiState {
    registry: RecipeRegistry,
    game: HanoiGame,
    labelling: Labelling,
    recorder: Recorder,
    disc_count: u32,
    graphics_mode: bool,
    frame: Frame,
    board_slot: Panel,
    board_text: TextCtrl,
    board_graphics: Panel,
    move_buttons: Vec<Button>,
    recipe_list: ListBox,
    save_btn: Button,
    apply_btn: Button,
    show_btn: Button,
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

    fn selected_recipe(&self) -> Option<String> {
        let i: u32 = self.recipe_list.get_selection()?;
        self.registry.names().get(i as usize).cloned()
    }

    /// Redraw the board and re-sync every control to the session.
    /// The text board, horizontally centred and pushed to the bottom of the text
    /// control — matching the wxPython TextBoardRenderer (which the maintainer prefers),
    /// rather than sitting top-left. Recomputed on every refresh from the control's
    /// current size (wxDragon exposes no resize hook, so a bare window-resize reflows
    /// only on the next state change — close enough for a teaching board).
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
        // items are NORMAL (not radio) in the XRC — a radio's checked state is
        // unreliable on wxGTK — so the active one is marked by rewriting its
        // label, which never emits an event.
        let current: [u32; 3] =
            [0, 1, 2].map(|i| (change_labels_on_pegs(self.labelling, i) + 1) as u32);
        if let Some(mb) = self.frame.get_menu_bar() {
            for perm in RELABEL_PERMS.iter() {
                let id: i32 = XmlResource::get_xrc_id(&relabel_item_name(*perm));
                if let Some(item) = mb.find_item(id) {
                    let marker: &str = if *perm == current {
                        "\u{25CF}  "
                    } else {
                        "    "
                    };
                    item.set_label(&format!("{marker}{} {} {}", perm[0], perm[1], perm[2]));
                    item.enable(!won);
                }
            }
        }

        // Recipe list (repopulate, preserve selection by name).
        let previously: Option<String> = self.selected_recipe();
        self.recipe_list.clear();
        let names: Vec<String> = self.registry.names();
        for name in &names {
            if let Some(recipe) = self.registry.get(name) {
                self.recipe_list.append(&format!(
                    "{name}  ({} discs, {} moves)",
                    recipe.disk_count,
                    recipe.default_moves.len()
                ));
            }
        }
        if let Some(prev) = previously {
            if let Some(i) = names.iter().position(|n| *n == prev) {
                self.recipe_list.set_selection(i as u32, true);
            }
        }

        self.apply_btn.enable(!won);
        self.show_btn.enable(true);
        self.save_btn.enable(won);
        self.frame
            .set_status_text(&format!("Moves: {}", self.game.current_moves), 1);
    }

    fn check_win(&self) {
        if !self.is_won() {
            return;
        }
        let min: u64 = self.min_moves();
        let moves: u64 = u64::from(self.game.current_moves);
        let verdict: String = if moves == min {
            "Optimal!".to_string()
        } else {
            format!("{} more than the minimum ({min}).", moves - min)
        };
        self.frame.set_status_text(
            &format!("Solved in {moves} moves — {verdict}  Click 'Save' to keep it."),
            0,
        );
    }
}

// --- Handlers ---------------------------------------------------------------

fn on_move(state: &Rc<RefCell<GuiState>>, from_label: u32, to_label: u32) {
    let (relabelled, status, moves_for_dialog): (bool, String, Option<Vec<(u32, u32)>>) = {
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
        st.frame.set_status_text(&status, 0);
        st.refresh();
        st.check_win();
        (relabelled, status, moves)
    };
    let _ = (relabelled, status);
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
/// a proportional font, which collapses the columns (hence the misalignment the maintainer
/// saw). A read-only teletype `TextCtrl` keeps the columns aligned, matching the Python wx.
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
    let table: Vec<String> = format_rebinding_table(moves, labelling, "Your move / recipe");
    if table.is_empty() {
        return;
    }
    show_monospace_dialog(frame, title, &table);
}

fn on_relabel(state: &Rc<RefCell<GuiState>>, perm: [u32; 3]) {
    let mut st: std::cell::RefMut<'_, GuiState> = state.borrow_mut();
    let result: DispatchResult = st.dispatch(&Command::Relabel(perm));
    if let Some(line) = result.lines.first() {
        st.frame.set_status_text(line, 0);
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
    st.frame.set_status_text("", 0);
    st.refresh();
}

fn on_new_game_same(state: &Rc<RefCell<GuiState>>) {
    let mut st: std::cell::RefMut<'_, GuiState> = state.borrow_mut();
    let n: u32 = st.disc_count;
    st.new_game(n);
    st.frame.set_status_text("", 0);
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
    let mut st: std::cell::RefMut<'_, GuiState> = state.borrow_mut();
    let msg: String = st.save(&name);
    st.frame.set_status_text(&msg, 0);
    st.refresh();
}

fn on_apply(state: &Rc<RefCell<GuiState>>) {
    let (name, frame, relabelled, moves): (String, Frame, bool, Option<Vec<(u32, u32)>>) = {
        let st: std::cell::Ref<'_, GuiState> = state.borrow();
        let Some(name) = st.selected_recipe() else {
            st.frame.set_status_text("Select a recipe first.", 0);
            return;
        };
        let moves: Option<Vec<(u32, u32)>> =
            st.registry.get(&name).map(|r| r.default_moves.clone());
        (
            name,
            st.frame.clone(),
            st.labelling != Labelling::OneTwoThree,
            moves,
        )
    };
    let labelling: Labelling = {
        let mut st: std::cell::RefMut<'_, GuiState> = state.borrow_mut();
        let result: DispatchResult = st.dispatch(&Command::Apply(name.clone()));
        let steps: usize = result
            .lines
            .iter()
            .filter(|l| l.trim_start().starts_with("step "))
            .count();
        if steps > 0 {
            st.frame
                .set_status_text(&format!("Applied '{name}' — {steps} moves."), 0);
        } else if let Some(last) = result.lines.last() {
            st.frame.set_status_text(last, 0);
        }
        st.refresh();
        st.check_win();
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

fn on_show(state: &Rc<RefCell<GuiState>>) {
    let (name, frame): (Option<String>, Frame) = {
        let st: std::cell::Ref<'_, GuiState> = state.borrow();
        (st.selected_recipe(), st.frame.clone())
    };
    let Some(name) = name else {
        state
            .borrow()
            .frame
            .set_status_text("Select a recipe first.", 0);
        return;
    };
    let lines: Vec<String> = {
        let mut st: std::cell::RefMut<'_, GuiState> = state.borrow_mut();
        st.dispatch(&Command::Show(name.clone())).lines
    };
    show_monospace_dialog(&frame, &format!("Recipe '{name}'"), &lines);
}

fn main() {
    let _ = wxdragon::main(|_| {
        // Load the shared UI definition (menu bar + panel) from the baked XRC.
        let res: XmlResource = XmlResource::get();
        res.init_all_handlers();
        if let Err(e) = res.load_from_string(XRC_DATA) {
            eprintln!("failed to load hanoi.xrc: {e}");
            return;
        }

        let frame: Frame = Frame::builder()
            .with_title("Towers of Hanoi")
            .with_size(Size::new(1000, 640))
            .build();
        if let Some(menu_bar) = MenuBar::from_xrc_name("main_menubar") {
            frame.set_menu_bar(menu_bar);
        }
        frame.create_status_bar(2, 0, ID_ANY as i32, "");

        let panel: Panel = res
            .load_panel(Some(&frame), "HanoiPanel")
            .expect("HanoiPanel in hanoi.xrc");

        // The board_slot is an empty placeholder panel in the XRC; put the two
        // board widgets (one shown at a time) inside it, as the Python renderer
        // slot does.
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
        let recipe_list: ListBox = panel
            .find_child_by_xrc_name("recipe_list")
            .expect("recipe_list in hanoi.xrc");
        let save_btn: Button = panel
            .find_child_by_xrc_name("recipe_save")
            .expect("recipe_save in hanoi.xrc");
        let apply_btn: Button = panel
            .find_child_by_xrc_name("recipe_apply")
            .expect("recipe_apply in hanoi.xrc");
        let show_btn: Button = panel
            .find_child_by_xrc_name("recipe_show")
            .expect("recipe_show in hanoi.xrc");

        // The XRC panel carries its own sizer; drop it into the frame to fill it.
        let frame_sizer: BoxSizer = BoxSizer::builder(Orientation::Vertical).build();
        frame_sizer.add(&panel, 1, SizerFlag::Expand, 0);
        frame.set_sizer(frame_sizer, true);

        // XRC menu-item ids (resolved by name once; the match below compares to
        // these, since they aren't compile-time constants).
        let id_new: i32 = XmlResource::get_xrc_id("wxID_NEW");
        let id_new_same: i32 = XmlResource::get_xrc_id("game_new_same");
        let id_exit: i32 = XmlResource::get_xrc_id("wxID_EXIT");
        let id_about: i32 = XmlResource::get_xrc_id("wxID_ABOUT");
        let id_style_text: i32 = XmlResource::get_xrc_id("style_text");
        let id_style_graphics: i32 = XmlResource::get_xrc_id("style_graphics");
        let relabel_ids: [i32; 6] =
            RELABEL_PERMS.map(|p| XmlResource::get_xrc_id(&relabel_item_name(p)));

        // Graphics is the default board; mark its (radio) menu item.
        if let Some(mb) = frame.get_menu_bar() {
            mb.check_item(id_style_graphics, true);
        }

        let state: Rc<RefCell<GuiState>> = Rc::new(RefCell::new(GuiState {
            registry: RecipeRegistry::new(),
            game: HanoiGame::new(DEFAULT_DISKS),
            labelling: Labelling::OneTwoThree,
            recorder: Recorder::new(),
            disc_count: DEFAULT_DISKS,
            graphics_mode: true,
            frame: frame.clone(),
            board_slot: board_slot.clone(),
            board_text: board_text.clone(),
            board_graphics: board_graphics.clone(),
            move_buttons: move_buttons.clone(),
            recipe_list: recipe_list.clone(),
            save_btn: save_btn.clone(),
            apply_btn: apply_btn.clone(),
            show_btn: show_btn.clone(),
        }));

        // Graphics board paint handler.
        {
            let st: Rc<RefCell<GuiState>> = state.clone();
            let panel_clone: Panel = board_graphics.clone();
            board_graphics.on_paint(move |_| {
                let dc: AutoBufferedPaintDC = AutoBufferedPaintDC::new(&panel_clone);
                let (w, h): (i32, i32) = dc.get_size();
                let s: std::cell::Ref<'_, GuiState> = st.borrow();
                draw_board_dc(&dc, w, h, &s.game, s.labelling);
            });
        }

        // Move buttons.
        for (btn, (f, t)) in move_buttons.iter().zip(MOVE_PAIRS.iter()) {
            let st: Rc<RefCell<GuiState>> = state.clone();
            let (f, t): (u32, u32) = (*f, *t);
            btn.on_click(move |_| on_move(&st, f, t));
        }

        // Recipe buttons + double-click.
        {
            let st: Rc<RefCell<GuiState>> = state.clone();
            save_btn.on_click(move |_| on_save(&st));
        }
        {
            let st: Rc<RefCell<GuiState>> = state.clone();
            apply_btn.on_click(move |_| on_apply(&st));
        }
        {
            let st: Rc<RefCell<GuiState>> = state.clone();
            show_btn.on_click(move |_| on_show(&st));
        }
        {
            let st: Rc<RefCell<GuiState>> = state.clone();
            recipe_list.on_item_double_clicked(move |_| on_show(&st));
        }

        // Menu. The item ids come from the XRC (resolved above), so this is an
        // if/else chain rather than a match on constants.
        {
            let st: Rc<RefCell<GuiState>> = state.clone();
            let frame_for_menu: Frame = frame.clone();
            frame.on_menu_selected(move |ev: MenuEventData| {
                let id: i32 = ev.get_id();
                if id == id_new {
                    on_new_game(&st);
                } else if id == id_new_same {
                    on_new_game_same(&st);
                } else if id == id_exit {
                    frame_for_menu.close(true);
                } else if id == id_about {
                    MessageDialog::builder(
                        &frame_for_menu,
                        "Towers of Hanoi\n\nA teaching tool: solve small, relabel pegs, \
                         replay. Shares its model and dispatcher with the CLI and TUI \
                         front-ends.",
                        "About Towers of Hanoi",
                    )
                    .build()
                    .show_modal();
                } else if id == id_style_graphics || id == id_style_text {
                    let graphics: bool = id == id_style_graphics;
                    let mut s: std::cell::RefMut<'_, GuiState> = st.borrow_mut();
                    s.graphics_mode = graphics;
                    s.board_graphics.show(graphics);
                    s.board_text.show(!graphics);
                    if let Some(mb) = s.frame.get_menu_bar() {
                        mb.check_item(id_style_graphics, graphics);
                        mb.check_item(id_style_text, !graphics);
                    }
                    s.board_slot.layout();
                    s.frame.layout();
                    s.refresh();
                } else if let Some(pos) = relabel_ids.iter().position(|&x| x == id) {
                    on_relabel(&st, RELABEL_PERMS[pos]);
                }
            });
        }

        state.borrow().refresh();
        frame.show(true);
        frame.centre();
    });
}
