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
//! Port notes: the UI is built programmatically (the Python used `hanoi.xrc`);
//! GUI state is shared across wxDragon's `'static` event closures via
//! `Rc<RefCell<GuiState>>`. The graphics renderer draws with the wxDC model
//! (solid fills, rounded rectangles, circles) — **not** the wxPython
//! `GraphicsContext` gradients/shadows, which wxDragon does not expose. The
//! recipe-show and rebinding views are message dialogs rather than the Python's
//! scrollable 3-panel dialog (the teaching content is the same). See
//! `tasks/port-to-rust-wxdragon.md`.

use std::cell::RefCell;
use std::rc::Rc;

use wxdragon::prelude::*;

use hanoigame::commands::Command;
use hanoigame::engine::{DispatchResult, GameSession};
use hanoigame::model::HanoiGame;
use hanoigame::presenter::{self, change_labels_on_pegs, Labelling};
use hanoigame::recipe::{format_rebinding_table, RecipeRegistry, Recorder};

const MAX_DISKS: u32 = 10;
const DEFAULT_DISKS: u32 = 3;

const ID_NEW: i32 = 1001;
const ID_NEW_SAME: i32 = 1002;
const ID_EXIT: i32 = 1003;
const ID_ABOUT: i32 = 1004;
const ID_HELP: i32 = 1005;
const ID_STYLE_TEXT: i32 = 1010;
const ID_STYLE_GRAPHICS: i32 = 1011;
const ID_RELABEL_BASE: i32 = 1020;

/// The six (from_label, to_label) move-button pairs, in display order.
const MOVE_PAIRS: [(u32, u32); 6] = [(1, 2), (1, 3), (2, 1), (2, 3), (3, 1), (3, 2)];

/// The six peg-label permutations, in menu order.
const RELABEL_PERMS: [[u32; 3]; 6] = [
    [1, 2, 3],
    [1, 3, 2],
    [2, 1, 3],
    [2, 3, 1],
    [3, 1, 2],
    [3, 2, 1],
];

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
    dc.set_background(Colour::rgb(30, 36, 50));
    dc.set_background_mode(BackgroundMode::Solid);
    dc.clear();

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

    // Active label badges (coloured circles with the label digit).
    let active_label_y: f64 = base_y
        + f64::from(base_h)
        + if relabelled {
            18.0
        } else {
            f64::from(label_band_h) / 2.0
        };
    for (p, &cx) in peg_centres.iter().enumerate() {
        let label: usize = change_labels_on_pegs(labelling, p);
        let rgb: (u8, u8, u8) = label_rgb(label);
        dc.set_pen(darken(rgb, 0.40), 1, PenStyle::Solid);
        dc.set_brush(colour(rgb), BrushStyle::Solid);
        dc.draw_circle(cx as i32, active_label_y as i32, 14);
        dc.set_text_foreground(Colour::rgb(255, 255, 255));
        dc.draw_text(
            &(label + 1).to_string(),
            cx as i32 - 4,
            active_label_y as i32 - 8,
        );
    }

    // Default 1-2-3 reference row when relabelled.
    if relabelled {
        let ref_y: f64 = active_label_y + 26.0;
        dc.set_text_foreground(Colour::rgb(170, 178, 195));
        for (p, &cx) in peg_centres.iter().enumerate() {
            dc.draw_text(&(p + 1).to_string(), cx as i32 - 4, ref_y as i32 - 8);
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
    fn refresh(&self) {
        // Board.
        self.board_text
            .set_value(&presenter::render(&self.game, self.labelling).join("\n"));
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

        // Relabel-menu bullets (active permutation marked; display-only).
        let current: [u32; 3] =
            [0, 1, 2].map(|i| (change_labels_on_pegs(self.labelling, i) + 1) as u32);
        if let Some(mb) = self.frame.get_menu_bar() {
            for (i, perm) in RELABEL_PERMS.iter().enumerate() {
                if let Some(item) = mb.find_item(ID_RELABEL_BASE + i as i32) {
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

fn show_rebinding(frame: &Frame, title: &str, moves: &[(u32, u32)], labelling: Labelling) {
    let table: Vec<String> = format_rebinding_table(moves, labelling, "Your move / recipe");
    if table.is_empty() {
        return;
    }
    MessageDialog::builder(frame, &table.join("\n"), title)
        .build()
        .show_modal();
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
    MessageDialog::builder(&frame, &lines.join("\n"), &format!("Recipe '{name}'"))
        .build()
        .show_modal();
}

fn build_menu_bar(frame: &Frame) {
    let game_menu: Menu = Menu::builder()
        .append_item(ID_NEW, "&New Game…\tCtrl+N", "Start a new game")
        .append_item(
            ID_NEW_SAME,
            "New Game (&same discs)",
            "Restart with the same disc count",
        )
        .append_separator()
        .append_item(ID_EXIT, "E&xit\tCtrl+Q", "Exit")
        .build();

    let mut relabel_menu = Menu::builder();
    for (i, perm) in RELABEL_PERMS.iter().enumerate() {
        relabel_menu = relabel_menu.append_item(
            ID_RELABEL_BASE + i as i32,
            &format!("    {} {} {}", perm[0], perm[1], perm[2]),
            "Relabel the pegs",
        );
    }
    let relabel_menu: Menu = relabel_menu.build();

    let view_menu: Menu = Menu::builder()
        .append_check_item(ID_STYLE_GRAPHICS, "Board: &Graphics", "2D graphics board")
        .append_check_item(ID_STYLE_TEXT, "Board: &Text", "Monospace text board")
        .build();

    let help_menu: Menu = Menu::builder()
        .append_item(ID_HELP, "&How to play…", "Features and controls")
        .append_item(ID_ABOUT, "&About", "About Towers of Hanoi")
        .build();

    let menu_bar: MenuBar = MenuBar::builder()
        .append(game_menu, "&Game")
        .append(relabel_menu, "&Relabel")
        .append(view_menu, "&View")
        .append(help_menu, "&Help")
        .build();
    frame.set_menu_bar(menu_bar);
}

fn main() {
    let _ = wxdragon::main(|_| {
        let frame: Frame = Frame::builder()
            .with_title("Towers of Hanoi")
            .with_size(Size::new(1000, 640))
            .build();
        build_menu_bar(&frame);
        frame.create_status_bar(2, 0, ID_ANY as i32, "");

        let panel: Panel = Panel::builder(&frame).build();

        // Two board widgets stacked in the board area; one is shown at a time.
        let board_graphics: Panel = Panel::builder(&panel).build();
        board_graphics.set_background_style(BackgroundStyle::Paint);
        let board_text: TextCtrl = TextCtrl::builder(&panel)
            .with_style(TextCtrlStyle::MultiLine | TextCtrlStyle::ReadOnly)
            .build();
        board_text.show(false); // graphics is the default view

        let button_sizer: BoxSizer = BoxSizer::builder(Orientation::Horizontal).build();
        let mut move_buttons: Vec<Button> = Vec::new();
        for (f, t) in MOVE_PAIRS {
            let btn: Button = Button::builder(&panel)
                .with_label(&format!("{f} \u{2192} {t}"))
                .build();
            button_sizer.add(&btn, 1, SizerFlag::Expand | SizerFlag::All, 4);
            move_buttons.push(btn);
        }

        // Recipe row: a list plus Save / Apply / Show buttons.
        let recipe_list: ListBox = ListBox::builder(&panel).build();
        let save_btn: Button = Button::builder(&panel).with_label("Save").build();
        let apply_btn: Button = Button::builder(&panel).with_label("Apply").build();
        let show_btn: Button = Button::builder(&panel).with_label("Show").build();
        let recipe_btns: BoxSizer = BoxSizer::builder(Orientation::Vertical).build();
        recipe_btns.add(&save_btn, 0, SizerFlag::Expand | SizerFlag::All, 2);
        recipe_btns.add(&apply_btn, 0, SizerFlag::Expand | SizerFlag::All, 2);
        recipe_btns.add(&show_btn, 0, SizerFlag::Expand | SizerFlag::All, 2);
        let recipe_row: BoxSizer = BoxSizer::builder(Orientation::Horizontal).build();
        recipe_row.add(&recipe_list, 1, SizerFlag::Expand | SizerFlag::All, 4);
        recipe_row.add_sizer(&recipe_btns, 0, SizerFlag::Expand | SizerFlag::All, 2);

        let panel_sizer: BoxSizer = BoxSizer::builder(Orientation::Vertical).build();
        panel_sizer.add(&board_graphics, 3, SizerFlag::Expand | SizerFlag::All, 6);
        panel_sizer.add(&board_text, 3, SizerFlag::Expand | SizerFlag::All, 6);
        panel_sizer.add_sizer(&button_sizer, 0, SizerFlag::Expand | SizerFlag::All, 4);
        panel_sizer.add_sizer(&recipe_row, 1, SizerFlag::Expand | SizerFlag::All, 4);
        panel.set_sizer(panel_sizer, true);

        let frame_sizer: BoxSizer = BoxSizer::builder(Orientation::Vertical).build();
        frame_sizer.add(&panel, 1, SizerFlag::Expand, 0);
        frame.set_sizer(frame_sizer, true);

        if let Some(mb) = frame.get_menu_bar() {
            mb.check_item(ID_STYLE_GRAPHICS, true);
        }

        let state: Rc<RefCell<GuiState>> = Rc::new(RefCell::new(GuiState {
            registry: RecipeRegistry::new(),
            game: HanoiGame::new(DEFAULT_DISKS),
            labelling: Labelling::OneTwoThree,
            recorder: Recorder::new(),
            disc_count: DEFAULT_DISKS,
            graphics_mode: true,
            frame: frame.clone(),
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

        // Menu.
        {
            let st: Rc<RefCell<GuiState>> = state.clone();
            let frame_for_menu: Frame = frame.clone();
            frame.on_menu_selected(move |ev: MenuEventData| {
                let id: i32 = ev.get_id();
                match id {
                    ID_NEW => on_new_game(&st),
                    ID_NEW_SAME => on_new_game_same(&st),
                    ID_EXIT => frame_for_menu.close(true),
                    ID_HELP => {
                        MessageDialog::builder(
                            &frame_for_menu,
                            "Move: click a legal 'from \u{2192} to' button (in the current labels); \
                             illegal moves are disabled.\n\n\
                             Relabel: rename the physical pegs (Relabel menu). Discs don't move, and \
                             the colours track the label \u{2014} so a solved sub-problem can be \
                             replayed under a new name.\n\n\
                             Recipes: after you win, Save the solution (default name solve-N). Apply \
                             replays a saved recipe under the current labelling and, when relabelled, \
                             shows the three-panel rebinding (the recipe's labels, the label \u{2192} \
                             peg key, and the rebound moves on the physical pegs). Show lists a \
                             recipe's moves.\n\n\
                             New Game: pick a disc count (1–10).",
                            "How to play",
                        )
                        .build()
                        .show_modal();
                    }
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
                    ID_STYLE_GRAPHICS | ID_STYLE_TEXT => {
                        let graphics: bool = id == ID_STYLE_GRAPHICS;
                        let mut s: std::cell::RefMut<'_, GuiState> = st.borrow_mut();
                        s.graphics_mode = graphics;
                        s.board_graphics.show(graphics);
                        s.board_text.show(!graphics);
                        if let Some(mb) = s.frame.get_menu_bar() {
                            mb.check_item(ID_STYLE_GRAPHICS, graphics);
                            mb.check_item(ID_STYLE_TEXT, !graphics);
                        }
                        s.frame.layout();
                        s.refresh();
                    }
                    _ if (ID_RELABEL_BASE..ID_RELABEL_BASE + 6).contains(&id) => {
                        let perm: [u32; 3] = RELABEL_PERMS[(id - ID_RELABEL_BASE) as usize];
                        on_relabel(&st, perm);
                    }
                    _ => {}
                }
            });
        }

        state.borrow().refresh();
        frame.show(true);
        frame.centre();
    });
}
