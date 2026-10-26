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
use hanoigame::presenter::{change_labels_on_pegs, Labelling};
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
    disc_count: u32,
    status: String,
    selected_recipe: Option<String>,
    /// Scrollable detail (a recipe's moves, or a rebinding table), shown on demand.
    detail_title: String,
    detail: Vec<String>,
}

impl HanoiApp {
    fn new() -> Self {
        HanoiApp {
            registry: RecipeRegistry::new(),
            game: HanoiGame::new(DEFAULT_DISKS),
            labelling: Labelling::OneTwoThree,
            recorder: Recorder::new(),
            disc_count: DEFAULT_DISKS,
            status: String::new(),
            selected_recipe: None,
            detail_title: String::new(),
            detail: Vec::new(),
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
        self.disc_count = n;
        self.game = HanoiGame::new(n);
        self.labelling = Labelling::OneTwoThree;
        self.recorder = Recorder::new();
        self.status.clear();
        self.detail.clear();
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
            self.status = format!("Moved {from_label} \u{2192} {to_label}.");
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
        let name: String = format!("solve-{}", self.game.num_disks);
        let msg: String = self.save(&name);
        self.status = msg;
    }

    fn do_apply(&mut self) {
        let Some(name) = self.selected_recipe.clone() else {
            self.status = "Select a recipe first.".to_string();
            return;
        };
        let relabelled: bool = self.labelling != Labelling::OneTwoThree;
        let moves: Option<Vec<(u32, u32)>> =
            self.registry.get(&name).map(|r| r.default_moves.clone());
        let result: DispatchResult = self.dispatch(&Command::Apply(name.clone()));
        let steps: usize = result
            .lines
            .iter()
            .filter(|l| l.trim_start().starts_with("step "))
            .count();
        if steps > 0 {
            self.status = format!("Applied '{name}' \u{2014} {steps} moves.");
        } else if let Some(last) = result.lines.last() {
            self.status = last.clone();
        }
        self.check_win();
        if relabelled {
            if let Some(moves) = moves {
                self.show_rebinding(&format!("Rebinding for '{name}'"), &moves);
            }
        }
    }

    fn do_show(&mut self) {
        let Some(name) = self.selected_recipe.clone() else {
            self.status = "Select a recipe first.".to_string();
            return;
        };
        let lines: Vec<String> = self.dispatch(&Command::Show(name.clone())).lines;
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
        let min: u64 = self.min_moves();
        let moves: u64 = u64::from(self.game.current_moves);
        let verdict: String = if moves == min {
            "Optimal!".to_string()
        } else {
            format!("{} more than the minimum ({min}).", moves - min)
        };
        self.status = format!("Solved in {moves} moves \u{2014} {verdict}  Save to keep it.");
    }

    /// Paint the board (solid fills) into `rect` with `painter`.
    fn paint_board(&self, painter: &egui::Painter, rect: egui::Rect) {
        painter.rect_filled(rect, 0.0, egui::Color32::from_rgb(30, 36, 50));
        let n: u32 = self.game.num_disks;
        if n == 0 {
            return;
        }
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
        let font: egui::FontId = egui::FontId::proportional(13.0);

        // Base bar.
        painter.rect_filled(
            egui::Rect::from_min_size(
                egui::pos2(rect.left() + margin, base_y),
                egui::vec2(w - 2.0 * margin, base_h),
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

        // Discs (bottom-up), coloured by size.
        for (p, stack) in self.game.towers.iter().enumerate() {
            let cx: f32 = peg_centres[p];
            for (idx, &size) in stack.iter().enumerate() {
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
    }
}

impl eframe::App for HanoiApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        let won: bool = self.is_won();
        let legal: Vec<(u32, u32)> = self.legal_moves();
        let current: [u32; 3] =
            [0, 1, 2].map(|i| (change_labels_on_pegs(self.labelling, i) + 1) as u32);

        egui::TopBottomPanel::bottom("status").show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.label(format!("Moves: {}", self.game.current_moves));
                ui.separator();
                ui.label(&self.status);
            });
        });

        egui::SidePanel::right("recipes").show(ctx, |ui| {
            ui.heading("Recipes");
            egui::ScrollArea::vertical()
                .max_height(220.0)
                .show(ui, |ui| {
                    for name in self.registry.names() {
                        let label: String = match self.registry.get(&name) {
                            Some(r) => {
                                format!(
                                    "{name}  ({} discs, {} moves)",
                                    r.disk_count,
                                    r.default_moves.len()
                                )
                            }
                            None => name.clone(),
                        };
                        let selected: bool = self.selected_recipe.as_deref() == Some(name.as_str());
                        if ui.selectable_label(selected, label).clicked() {
                            self.selected_recipe = Some(name.clone());
                        }
                    }
                });
            ui.separator();
            ui.add_enabled_ui(won, |ui| {
                if ui.button("Save (solve-N)").clicked() {
                    self.do_save();
                }
            });
            if ui.add_enabled(!won, egui::Button::new("Apply")).clicked() {
                self.do_apply();
            }
            if ui.button("Show").clicked() {
                self.do_show();
            }
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
            // New game controls.
            ui.horizontal(|ui| {
                ui.label("Discs:");
                ui.add(egui::DragValue::new(&mut self.disc_count).range(1..=MAX_DISKS));
                if ui.button("New game").clicked() {
                    let n: u32 = self.disc_count.clamp(1, MAX_DISKS);
                    self.new_game(n);
                }
            });
            ui.separator();

            // Board.
            let desired: egui::Vec2 = egui::vec2(
                ui.available_width(),
                (ui.available_height() - 120.0).max(160.0),
            );
            let (response, painter): (egui::Response, egui::Painter) =
                ui.allocate_painter(desired, egui::Sense::hover());
            self.paint_board(&painter, response.rect);

            ui.separator();

            // Move buttons (3 from-peg columns).
            ui.horizontal(|ui| {
                for from in 1..=3u32 {
                    ui.vertical(|ui| {
                        for &(f, t) in MOVE_PAIRS.iter().filter(|(f, _)| *f == from) {
                            let enabled: bool = !won && legal.contains(&(f, t));
                            if ui
                                .add_enabled(
                                    enabled,
                                    egui::Button::new(format!("{f} \u{2192} {t}")),
                                )
                                .clicked()
                            {
                                self.do_move(f, t);
                            }
                        }
                    });
                }
            });

            ui.separator();

            // Relabel buttons (the active one highlighted).
            ui.label("Relabel pegs (physical 1 2 3 \u{2192}):");
            ui.horizontal_wrapped(|ui| {
                for perm in RELABEL_PERMS {
                    let active: bool = perm == current;
                    let text: String = format!("{} {} {}", perm[0], perm[1], perm[2]);
                    if ui
                        .add_enabled(!won, egui::SelectableLabel::new(active, text))
                        .clicked()
                    {
                        self.do_relabel(perm);
                    }
                }
            });
        });
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
