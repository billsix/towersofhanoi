// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later

//! egui/eframe front-end for the Towers of Hanoi game — native AND web (WebAssembly)
//! from one codebase, over the same [`GameSession`] dispatcher as the CLI/TUI/wx ports.
//!
//! The board is painted with egui's `Painter` (solid fills, matching the wx DC board);
//! moves, relabelling, and recipes are plain egui widgets. Native runs via
//! `eframe::run_native` (glow/OpenGL); web runs the SAME `HanoiApp` on a `<canvas>` via
//! `eframe::WebRunner` (WebGL), gated on `target_arch = "wasm32"`. The Python package stays
//! the behaviour oracle; this must not drift from it. See
//! `tasks/rust-egui-native-and-web.md`.

use eframe::egui;

use hanoigame::commands::Command;
use hanoigame::engine::{DispatchResult, GameSession};
use hanoigame::model::HanoiGame;
use hanoigame::presenter::{
    change_labels_on_pegs, default_recipe_name, format_move_tally, format_win_celebration,
    Labelling,
};
use hanoigame::recipe::{format_rebinding_table, RecipeRegistry, Recorder};

const MAX_DISKS: u32 = 10;
const DEFAULT_DISKS: u32 = 3;

/// The six (from_label, to_label) move pairs, in display order.
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

fn colour((r, g, b): (u8, u8, u8)) -> egui::Color32 {
    egui::Color32::from_rgb(r, g, b)
}

fn darken((r, g, b): (u8, u8, u8), amount: f32) -> egui::Color32 {
    let f: f32 = 1.0 - amount;
    egui::Color32::from_rgb(
        (f32::from(r) * f) as u8,
        (f32::from(g) * f) as u8,
        (f32::from(b) * f) as u8,
    )
}

/// Width of a disc of `size` in an `n`-disc game, up to `max_w`.
fn disc_width(size: u32, n: u32, max_w: f32) -> f32 {
    if n <= 1 {
        return max_w;
    }
    let smallest: f32 = max_w / 3.0;
    smallest + (max_w - smallest) * (size - 1) as f32 / (n - 1) as f32
}

/// The whole GUI's mutable state.
struct HanoiApp {
    registry: RecipeRegistry,
    game: HanoiGame,
    labelling: Labelling,
    recorder: Recorder,
    status: String,
    /// Tier-2 latch: relabel + recipes stay dimmed until the first win, then unlock.
    won_once: bool,
    /// The win-celebration lines to show in a modal window (None = no dialog);
    /// set by `check_win`, cleared when the player dismisses or saves.
    win_dialog: Option<Vec<String>>,
    /// Save-on-discard (feature-spec §4.9; the win-celebration UX doc): whether
    /// the current won solution was reached by replaying a recipe and whether it
    /// was already saved (both reset per game), and a pending New Game (disc
    /// count) deferred behind the save-before-discard confirm window.
    won_via_apply: bool,
    saved_current: bool,
    pending_new_game: Option<u32>,
    /// Whether the New Game disc-picker window is open. egui 0.29 has no modal
    /// type, so it is an `egui::Window` like How-to-Play / Save-solution below.
    open_disc_picker: bool,
    /// Whether the How-to-Play window is open, and whether it has auto-opened once.
    open_help: bool,
    help_shown: bool,
    /// Scrollable detail (a recipe's moves, or a rebinding table), shown on demand.
    detail_title: String,
    detail: Vec<String>,
    /// Disc drag-drop (spike, mirrored across the GUIs): the physical peg (0,1,2)
    /// whose top disc is being dragged, its size, and the pointer position.
    drag_src: Option<usize>,
    drag_size: u32,
    drag_pos: egui::Pos2,
}

/// Board layout derived from the paint rect, shared by `paint_board` (drawing)
/// and the drag hit-test (so both agree on peg centres and disc sizes).
struct BoardGeom {
    relabelled: bool,
    margin: f32,
    base_h: f32,
    label_band_h: f32,
    peg_w: f32,
    peg_h: f32,
    peg_top_y: f32,
    base_y: f32,
    disc_h: f32,
    max_disc_w: f32,
    peg_centres: [f32; 3],
    n: u32,
}

impl HanoiApp {
    fn new() -> Self {
        HanoiApp {
            registry: RecipeRegistry::new(),
            game: HanoiGame::new(DEFAULT_DISKS),
            labelling: Labelling::OneTwoThree,
            recorder: Recorder::new(),
            status: String::new(),
            won_once: false,
            win_dialog: None,
            won_via_apply: false,
            saved_current: false,
            pending_new_game: None,
            open_disc_picker: false,
            open_help: false,
            help_shown: false,
            detail_title: String::new(),
            detail: Vec::new(),
            drag_src: None,
            drag_size: 0,
            drag_pos: egui::Pos2::ZERO,
        }
    }

    /// Run a command through a transient [`GameSession`] borrowing the shared registry.
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
        self.game = HanoiGame::new(n);
        self.labelling = Labelling::OneTwoThree;
        self.recorder = Recorder::new();
        self.status.clear();
        self.detail.clear();
        self.win_dialog = None;
        self.won_via_apply = false;
        self.saved_current = false;
        self.pending_new_game = None;
    }

    /// New Game / New Game (Same Size): if the finished game was won by hand and
    /// not yet saved, defer to the save-before-discard confirm window
    /// (`pending_new_game`); otherwise start the new game immediately.
    fn request_new_game(&mut self, n: u32) {
        if self.is_won() && !self.won_via_apply && !self.saved_current {
            self.pending_new_game = Some(n);
        } else {
            self.new_game(n);
        }
    }

    fn is_won(&self) -> bool {
        self.game.check_win_condition()
    }

    fn min_moves(&self) -> u64 {
        (1u64 << self.game.num_disks) - 1
    }

    /// The legal (from_label, to_label) moves in the current labelling.
    fn legal_moves(&self) -> Vec<(u32, u32)> {
        self.game
            .move_options()
            .iter()
            .map(|mv| {
                (
                    (change_labels_on_pegs(self.labelling, mv.from_peg) + 1) as u32,
                    (change_labels_on_pegs(self.labelling, mv.to_peg) + 1) as u32,
                )
            })
            .collect()
    }

    fn do_move(&mut self, from_label: u32, to_label: u32) {
        let relabelled: bool = self.labelling != Labelling::OneTwoThree;
        let result: DispatchResult = self.dispatch(&Command::Move {
            from_label,
            to_label,
        });
        if let Some(line) = result.lines.first() {
            self.status = line.clone();
        } else {
            self.status = format!("Moved {from_label} -> {to_label}.");
            if relabelled {
                self.show_rebinding("Rebinding for your move", &[(from_label, to_label)]);
            }
        }
        self.check_win();
    }

    fn do_relabel(&mut self, perm: [u32; 3]) {
        let result: DispatchResult = self.dispatch(&Command::Relabel(perm));
        if let Some(line) = result.lines.first() {
            self.status = line.clone();
        }
    }

    fn do_save(&mut self) {
        if !self.is_won() {
            return;
        }
        let name: String = default_recipe_name(self.game.num_disks as usize);
        let msg: String = self.save(&name);
        self.saved_current = true;
        self.status = msg;
    }

    /// Apply a recipe by name (a Tier-3 Recipe-menu action). When the pegs are
    /// relabelled, the per-step log is suppressed by the core, so the move count
    /// comes from the recipe itself and a rebinding table is shown.
    fn apply_recipe_named(&mut self, name: &str) {
        let relabelled: bool = self.labelling != Labelling::OneTwoThree;
        let moves: Option<Vec<(u32, u32)>> =
            self.registry.get(name).map(|r| r.default_moves.clone());
        let move_count: usize = moves.as_ref().map_or(0, Vec::len);
        let result: DispatchResult = self.dispatch(&Command::Apply(name.to_string()));
        if move_count > 0 {
            self.status = format!("Applied '{name}' -- {move_count} moves.");
        } else if let Some(last) = result.lines.last() {
            self.status = last.clone();
        }
        self.check_win();
        if self.is_won() {
            self.won_via_apply = true;
        }
        if relabelled {
            if let Some(moves) = moves {
                self.show_rebinding(&format!("Rebinding for '{name}'"), &moves);
            }
        }
    }

    /// Show a recipe's moves in the detail area (the Tier-3 Recipe-menu "View").
    fn view_recipe(&mut self, name: &str) {
        let lines: Vec<String> = self.dispatch(&Command::Show(name.to_string())).lines;
        self.detail_title = format!("Recipe '{name}'");
        self.detail = lines;
    }

    fn show_rebinding(&mut self, title: &str, moves: &[(u32, u32)]) {
        let table: Vec<String> =
            format_rebinding_table(moves, self.labelling, "Your move / recipe");
        if table.is_empty() {
            return;
        }
        self.detail_title = title.to_string();
        self.detail = table;
    }

    fn check_win(&mut self) {
        if !self.is_won() {
            return;
        }
        let first_win: bool = !self.won_once;
        let lines: Vec<String> = format_win_celebration(
            self.game.num_disks as usize,
            u64::from(self.game.current_moves),
            self.min_moves(),
            first_win,
        );
        if let Some(first) = lines.first() {
            self.status = first.clone();
        }
        // Later wins: status line only (a window would collide with the §4.8
        // rebinding detail). The teaching modal shows on the first win only.
        if first_win {
            self.win_dialog = Some(lines);
        }
    }

    /// Board layout from the paint rect (peg centres, disc sizes), shared by the
    /// drawing and the drag hit-test so they can't disagree.
    fn board_geometry(&self, rect: egui::Rect) -> BoardGeom {
        let n: u32 = self.game.num_disks.max(1);
        let relabelled: bool = self.labelling != Labelling::OneTwoThree;
        let w: f32 = rect.width();
        let h: f32 = rect.height();
        let margin: f32 = 20.0;
        let label_band_h: f32 = if relabelled { 60.0 } else { 36.0 };
        let base_h: f32 = 14.0;
        let avail_w: f32 = (w - 2.0 * margin).max(80.0);
        let avail_h: f32 = (h - 2.0 * margin - label_band_h - base_h).max(80.0);
        let peg_zone_w: f32 = avail_w / 3.0;
        let disc_h: f32 = (avail_h / (n.max(4) as f32) * 0.92).min(30.0);
        let max_disc_w: f32 = peg_zone_w * 0.92;
        let peg_w: f32 = (max_disc_w * 0.07).max(8.0);
        let peg_h: f32 = avail_h * 0.95;
        let base_y: f32 = rect.top() + h - margin - label_band_h - base_h;
        let peg_top_y: f32 = base_y - peg_h;
        let peg_centres: [f32; 3] =
            [0, 1, 2].map(|i| rect.left() + margin + peg_zone_w * (i as f32 + 0.5));
        BoardGeom {
            relabelled,
            margin,
            base_h,
            label_band_h,
            peg_w,
            peg_h,
            peg_top_y,
            base_y,
            disc_h,
            max_disc_w,
            peg_centres,
            n,
        }
    }

    /// Paint the board (solid fills) into `rect` with `painter`. The disc being
    /// dragged (if any) is omitted from its home peg and drawn at the pointer.
    fn paint_board(&self, painter: &egui::Painter, rect: egui::Rect, geom: &BoardGeom) {
        painter.rect_filled(rect, 0.0, egui::Color32::from_rgb(30, 36, 50));
        if self.game.num_disks == 0 {
            return;
        }
        let relabelled: bool = geom.relabelled;
        let w: f32 = rect.width();
        let n: u32 = geom.n;
        let base_h: f32 = geom.base_h;
        let label_band_h: f32 = geom.label_band_h;
        let peg_w: f32 = geom.peg_w;
        let peg_h: f32 = geom.peg_h;
        let peg_top_y: f32 = geom.peg_top_y;
        let base_y: f32 = geom.base_y;
        let disc_h: f32 = geom.disc_h;
        let max_disc_w: f32 = geom.max_disc_w;
        let peg_centres: [f32; 3] = geom.peg_centres;
        let font: egui::FontId = egui::FontId::proportional(13.0);

        // Base bar.
        painter.rect_filled(
            egui::Rect::from_min_size(
                egui::pos2(rect.left() + geom.margin, base_y),
                egui::vec2(w - 2.0 * geom.margin, base_h),
            ),
            4.0,
            egui::Color32::from_rgb(150, 110, 70),
        );

        // Pegs.
        for &cx in &peg_centres {
            painter.rect_filled(
                egui::Rect::from_min_size(
                    egui::pos2(cx - peg_w / 2.0, peg_top_y),
                    egui::vec2(peg_w, peg_h),
                ),
                peg_w / 2.0,
                egui::Color32::from_rgb(160, 120, 75),
            );
        }

        // Discs (bottom-up), coloured by size; omit the one being dragged.
        for (p, stack) in self.game.towers.iter().enumerate() {
            let cx: f32 = peg_centres[p];
            for (idx, &size) in stack.iter().enumerate() {
                if self.drag_src == Some(p) && idx + 1 == stack.len() {
                    continue;
                }
                let dw: f32 = disc_width(size, n, max_disc_w);
                let y: f32 = base_y - (idx as f32 + 1.0) * disc_h * 1.04;
                painter.rect_filled(
                    egui::Rect::from_min_size(egui::pos2(cx - dw / 2.0, y), egui::vec2(dw, disc_h)),
                    disc_h / 3.0,
                    colour(disc_rgb(size)),
                );
            }
        }

        // Active label badges.
        let active_label_y: f32 =
            base_y + base_h + if relabelled { 18.0 } else { label_band_h / 2.0 };
        for (p, &cx) in peg_centres.iter().enumerate() {
            let label: usize = change_labels_on_pegs(self.labelling, p);
            painter.circle_filled(
                egui::pos2(cx, active_label_y),
                14.0,
                colour(label_rgb(label)),
            );
            let _ = darken; // (kept for parity with the wx DC board's pen colours)
            painter.text(
                egui::pos2(cx, active_label_y),
                egui::Align2::CENTER_CENTER,
                (label + 1).to_string(),
                font.clone(),
                egui::Color32::WHITE,
            );
        }

        // Default 1-2-3 reference row when relabelled.
        if relabelled {
            let ref_y: f32 = active_label_y + 26.0;
            for (p, &cx) in peg_centres.iter().enumerate() {
                painter.text(
                    egui::pos2(cx, ref_y),
                    egui::Align2::CENTER_CENTER,
                    (p + 1).to_string(),
                    font.clone(),
                    egui::Color32::from_rgb(170, 178, 195),
                );
            }
        }

        // The dragged disc follows the pointer, drawn on top (gold tint).
        if self.drag_src.is_some() {
            let dw: f32 = disc_width(self.drag_size, n, max_disc_w);
            painter.rect_filled(
                egui::Rect::from_center_size(self.drag_pos, egui::vec2(dw, disc_h)),
                disc_h / 3.0,
                egui::Color32::from_rgb(235, 225, 150),
            );
        }
    }

    /// Handle the board drag gesture from the painter's `Response`: press picks
    /// up the top disc of the nearest peg, drag moves it, release drops on the
    /// nearest peg (forgiving) and dispatches through `do_move`. Off once won.
    /// Mirrors the wxPython GraphicsBoardRenderer spike + the ImGui port.
    fn handle_board_drag(&mut self, response: &egui::Response, geom: &BoardGeom) {
        if self.is_won() {
            self.drag_src = None;
            return;
        }
        let nearest = |x: f32| -> usize {
            let mut best: usize = 0;
            for i in 1..3 {
                if (x - geom.peg_centres[i]).abs() < (x - geom.peg_centres[best]).abs() {
                    best = i;
                }
            }
            best
        };
        if response.drag_started() {
            if let Some(pos) = response.interact_pointer_pos() {
                let peg: usize = nearest(pos.x);
                if let Some(&top) = self.game.towers[peg].last() {
                    self.drag_src = Some(peg);
                    self.drag_size = top;
                    self.drag_pos = pos;
                }
            }
        }
        if response.dragged() {
            if let Some(pos) = response.interact_pointer_pos() {
                self.drag_pos = pos;
            }
        }
        if response.drag_stopped() {
            if let Some(src) = self.drag_src.take() {
                let target: usize = nearest(self.drag_pos.x);
                if target != src {
                    let from_label: u32 = (change_labels_on_pegs(self.labelling, src) + 1) as u32;
                    let to_label: u32 = (change_labels_on_pegs(self.labelling, target) + 1) as u32;
                    self.do_move(from_label, to_label);
                }
            }
        }
    }
}

impl eframe::App for HanoiApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        let won: bool = self.is_won();
        self.won_once = self.won_once || won;
        // Tier-1: the How-to-Play window auto-opens once, on the first frame.
        if !self.help_shown {
            self.open_help = true;
            self.help_shown = true;
        }
        let legal: Vec<(u32, u32)> = self.legal_moves();
        let current: [u32; 3] =
            [0, 1, 2].map(|i| (change_labels_on_pegs(self.labelling, i) + 1) as u32);
        let n: u32 = self.game.num_disks;
        let moves: u32 = self.game.current_moves;
        let min: u64 = self.min_moves();

        // Tier-3: recipes live in a menu, dimmed until the first win; Help reopens
        // the How-to-Play window.
        egui::TopBottomPanel::top("menubar").show(ctx, |ui| {
            egui::menu::bar(ui, |ui| {
                // Game menu — pick a disc count for a New Game, or restart at the
                // current size, matching the wx front-ends' Game menu.
                ui.menu_button("Game", |ui| {
                    // New Game opens a disc-picker window (the wx oracle's modal
                    // "How many discs?"), rather than an inline control -- friendlier
                    // on touch/mobile web, where dragging a value is awkward.
                    if ui.button("New Game…").clicked() {
                        self.open_disc_picker = true;
                        ui.close_menu();
                    }
                    if ui.button("New Game (Same Size)").clicked() {
                        let n: u32 = self.game.num_disks.max(1);
                        self.request_new_game(n);
                        ui.close_menu();
                    }
                });
                ui.add_enabled_ui(self.won_once, |ui| {
                    ui.menu_button("Recipe", |ui| {
                        let can_save: bool = won && !self.recorder.default_moves.is_empty();
                        if ui
                            .add_enabled(can_save, egui::Button::new("Save current solution"))
                            .clicked()
                        {
                            self.do_save();
                            ui.close_menu();
                        }
                        if ui.button("Reset recording").clicked() {
                            self.recorder.reset();
                            self.status = "Recording reset.".to_string();
                            ui.close_menu();
                        }
                        ui.separator();
                        let names: Vec<String> = self.registry.names();
                        if names.is_empty() {
                            ui.add_enabled(false, egui::Button::new("(no saved recipes yet)"));
                        } else {
                            for name in names {
                                let label: String = match self.registry.get(&name) {
                                    Some(r) => format!(
                                        "{name}  ({} discs, {} moves)",
                                        r.disk_count,
                                        r.default_moves.len()
                                    ),
                                    None => name.clone(),
                                };
                                ui.menu_button(label, |ui| {
                                    if ui.button("View").clicked() {
                                        self.view_recipe(&name);
                                        ui.close_menu();
                                    }
                                    if ui.add_enabled(!won, egui::Button::new("Apply")).clicked() {
                                        self.apply_recipe_named(&name);
                                        ui.close_menu();
                                    }
                                });
                            }
                        }
                    });
                    // Tier-2: relabelling is a menu too (one item per permutation,
                    // the active labelling marked), dimmed until the first win and
                    // while the current game is already solved.
                    ui.menu_button("Relabel", |ui| {
                        ui.add_enabled_ui(!won, |ui| {
                            for perm in RELABEL_PERMS {
                                let active: bool = perm == current;
                                let text: String = format!("{} {} {}", perm[0], perm[1], perm[2]);
                                if ui.radio(active, text).clicked() {
                                    self.do_relabel(perm);
                                    ui.close_menu();
                                }
                            }
                        });
                    });
                });
                ui.menu_button("Help", |ui| {
                    if ui.button("How to Play").clicked() {
                        self.open_help = true;
                        ui.close_menu();
                    }
                });
            });
        });

        egui::TopBottomPanel::bottom("status").show(ctx, |ui| {
            ui.label(&self.status);
        });

        // Tier-1: the move history is always visible (the running count against the
        // optimal 2^N-1, then the numbered default-label tally).
        egui::SidePanel::right("history").show(ctx, |ui| {
            ui.heading("History");
            ui.label(format!(
                "{moves} moves (optimal {min}, default 1-2-3 labels)"
            ));
            ui.separator();
            egui::ScrollArea::vertical().show(ui, |ui| {
                let tally: Vec<String> = format_move_tally(&self.recorder.default_moves);
                if tally.is_empty() {
                    ui.weak("(no moves yet)");
                } else {
                    for line in &tally {
                        ui.monospace(line);
                    }
                }
            });
            if !self.detail.is_empty() {
                ui.separator();
                ui.label(&self.detail_title);
                egui::ScrollArea::vertical()
                    .id_salt("detail")
                    .max_height(200.0)
                    .show(ui, |ui| {
                        for line in &self.detail {
                            ui.monospace(line);
                        }
                    });
                if ui.button("Clear").clicked() {
                    self.detail.clear();
                }
            }
        });

        egui::CentralPanel::default().show(ctx, |ui| {
            // Tier-1 goal line. (New Game lives on the Game menu now.)
            ui.label(format!(
                "Goal: move all {n} discs to peg 3   (Moves: {moves} / optimal {min})"
            ));
            ui.separator();

            // Board.
            let desired: egui::Vec2 = egui::vec2(
                ui.available_width(),
                (ui.available_height() - 120.0).max(160.0),
            );
            let (response, painter): (egui::Response, egui::Painter) =
                ui.allocate_painter(desired, egui::Sense::click_and_drag());
            let geom: BoardGeom = self.board_geometry(response.rect);
            self.handle_board_drag(&response, &geom);
            self.paint_board(&painter, response.rect, &geom);

            ui.separator();

            // Move buttons (3 from-peg columns).
            ui.horizontal(|ui| {
                for from in 1..=3u32 {
                    ui.vertical(|ui| {
                        for &(f, t) in MOVE_PAIRS.iter().filter(|(f, _)| *f == from) {
                            let enabled: bool = !won && legal.contains(&(f, t));
                            if ui
                                .add_enabled(enabled, egui::Button::new(format!("{f} -> {t}")))
                                .clicked()
                            {
                                self.do_move(f, t);
                            }
                        }
                    });
                }
            });
        });

        // Tier-1: the dismissible How-to-Play window (first-run + Help).
        let mut open: bool = self.open_help;
        let mut dismiss: bool = false;
        egui::Window::new("How to Play")
            .open(&mut open)
            .collapsible(false)
            .resizable(false)
            .anchor(egui::Align2::CENTER_CENTER, egui::vec2(0.0, 0.0))
            .show(ctx, |ui| {
                ui.label("Goal: move the whole stack of discs to peg 3.");
                ui.label("Rule: never place a larger disc on a smaller one.");
                ui.separator();
                ui.label(
                    "Method: solve a smaller stack first, then relabel the pegs and \
                     replay your saved solution on the bigger one.",
                );
                ui.add_space(4.0);
                if ui.button("Got it").clicked() {
                    dismiss = true;
                }
            });
        self.open_help = open && !dismiss;

        // The win celebration (teaching hinge): shown only on the FIRST win
        // (teaching), so it never collides with the rebinding detail; later wins
        // are a status line. Save is offered at the New Game boundary below.
        if let Some(lines) = self.win_dialog.clone() {
            let mut keep_open: bool = true;
            let mut dismiss: bool = false;
            egui::Window::new("You solved it!")
                .open(&mut keep_open)
                .collapsible(false)
                .resizable(false)
                .anchor(egui::Align2::CENTER_CENTER, egui::vec2(0.0, 0.0))
                .show(ctx, |ui| {
                    for line in &lines {
                        ui.label(line);
                    }
                    ui.add_space(4.0);
                    if ui.button("Got it").clicked() {
                        dismiss = true;
                    }
                });
            if dismiss || !keep_open {
                self.win_dialog = None;
            }
        }

        // New Game disc picker (mirrors the wx oracle's modal "How many discs?"):
        // tap a count to start; the last-used count (current game size) is
        // highlighted. A Window, not egui::Modal (unavailable at the 0.29 pin) --
        // like How-to-Play above. It closes before `request_new_game` can raise the
        // save prompt, and the save block below is skipped on that closing frame
        // (`picker_was_open`), so the two windows never overlap (the two-modal
        // collision; the win-celebration UX doc).
        let picker_was_open: bool = self.open_disc_picker;
        if picker_was_open {
            let mut open: bool = true;
            let mut chosen: Option<u32> = None;
            let mut cancel: bool = false;
            egui::Window::new("New Game")
                .open(&mut open)
                .collapsible(false)
                .resizable(false)
                .anchor(egui::Align2::CENTER_CENTER, egui::vec2(0.0, 0.0))
                .show(ctx, |ui| {
                    ui.label("How many discs?");
                    ui.add_space(4.0);
                    egui::Grid::new("disc_picker_grid").show(ui, |ui| {
                        for d in 1..=MAX_DISKS {
                            let text: String = if d == 1 {
                                "1 disc".to_string()
                            } else {
                                format!("{d} discs")
                            };
                            if ui
                                .selectable_label(d == self.game.num_disks, text)
                                .clicked()
                            {
                                chosen = Some(d);
                            }
                            if d % 5 == 0 {
                                ui.end_row();
                            }
                        }
                    });
                    ui.add_space(6.0);
                    if ui.button("Cancel").clicked() {
                        cancel = true;
                    }
                });
            if let Some(d) = chosen {
                self.open_disc_picker = false;
                self.request_new_game(d);
            } else if cancel || !open {
                self.open_disc_picker = false;
            }
        }

        // Save-before-discard: a New Game requested while a hand-won, unsaved
        // solution is on the board defers here (the save-before-you-close
        // pattern; the win-celebration UX doc). Skipped on the frame the picker
        // just closed (`picker_was_open`), so it never overlaps the picker window.
        if let Some(n) = self.pending_new_game.filter(|_| !picker_was_open) {
            let mut decided: Option<bool> = None; // Some(true)=save, else discard
            egui::Window::new("Save solution?")
                .collapsible(false)
                .resizable(false)
                .anchor(egui::Align2::CENTER_CENTER, egui::vec2(0.0, 0.0))
                .show(ctx, |ui| {
                    ui.label("Save your solution as a recipe before starting over?");
                    ui.add_space(4.0);
                    ui.horizontal(|ui| {
                        if ui.button("Save").clicked() {
                            decided = Some(true);
                        }
                        if ui.button("Don't save").clicked() {
                            decided = Some(false);
                        }
                    });
                });
            if let Some(save) = decided {
                if save {
                    self.do_save();
                }
                self.pending_new_game = None;
                self.new_game(n);
            }
        }
    }
}

#[cfg(not(target_arch = "wasm32"))]
fn main() -> eframe::Result<()> {
    let options: eframe::NativeOptions = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default().with_inner_size([1000.0, 680.0]),
        ..Default::default()
    };
    eframe::run_native(
        "Towers of Hanoi",
        options,
        Box::new(|_cc| Ok(Box::new(HanoiApp::new()))),
    )
}

// Web entry: run the SAME HanoiApp on the page's <canvas> via eframe's WebRunner. Only
// compiled for the wasm32 target (built with trunk; see Trunk.toml / index.html). This
// branch is NOT exercised by a native `cargo check` and is verified by `make egui-web`.
#[cfg(target_arch = "wasm32")]
fn main() {
    let web_options: eframe::WebOptions = eframe::WebOptions::default();
    wasm_bindgen_futures::spawn_local(async {
        use eframe::wasm_bindgen::JsCast as _;
        let document: web_sys::Document = web_sys::window()
            .expect("no window")
            .document()
            .expect("no document");
        let canvas: web_sys::HtmlCanvasElement = document
            .get_element_by_id("hanoi_canvas")
            .expect("no #hanoi_canvas")
            .dyn_into::<web_sys::HtmlCanvasElement>()
            .expect("#hanoi_canvas is not a canvas");
        eframe::WebRunner::new()
            .start(
                canvas,
                web_options,
                Box::new(|_cc| Ok(Box::new(HanoiApp::new()))),
            )
            .await
            .expect("failed to start eframe");
    });
}
