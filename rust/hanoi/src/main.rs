// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later

//! Terminal-UI front-end for the Towers of Hanoi game.
//!
//! Same command grammar and dispatcher as the CLI — the user types `1 -> 3`,
//! `relabel 1 3 2`, `apply foo`, `help`, `quit`, … into a prompt at the bottom
//! of the screen. The coloured board is drawn above; the most recent
//! result/error sits just above the prompt. (Rust port of the ncurses
//! `python/src/hanoigame/hanoigame.py`, kept in sync — curses becomes
//! `ratatui` + `crossterm`, which redraw immediately rather than mutating a
//! window cell by cell.)
//!
//! The pure render functions ([`draw_play`] and its helpers) are exercised
//! headlessly by a `TestBackend`; the event loop needs a real terminal and is
//! verified interactively on the host.

use crossterm::event::{self, Event, KeyCode, KeyEventKind, KeyModifiers};
use ratatui::{
    layout::{Alignment, Constraint, Layout, Rect},
    style::{Color, Style},
    text::{Line, Span},
    widgets::Paragraph,
    DefaultTerminal, Frame,
};

use hanoigame::commands::parse;
use hanoigame::engine::GameSession;
use hanoigame::presenter::{self, change_labels_on_pegs, peg_color, Labelling};
use hanoigame::recipe::RecipeRegistry;

const MAX_DISKS: u32 = 10;
const MSG_AREA_LINES: usize = 6;
const HINT_AREA_LINES: usize = 2;

const DEFAULT_HINT: [&str; 2] = [
    "Move: type 'from -> to' (e.g. '1 -> 3')",
    "Other: relabel a b c | apply <name> | show <name> | list | help | quit",
];

// --- Colour ----------------------------------------------------------------

/// The foreground colour for the peg at `tower_index` under `labelling` — the
/// colour follows the peg's *label* (so "label 1 is the blue peg" survives a
/// relabelling), matching the curses `peg_color` pair numbers.
fn peg_fg(labelling: Labelling, tower_index: usize) -> Color {
    match peg_color(labelling, tower_index) {
        5 => Color::Blue,
        3 => Color::Yellow,
        4 => Color::Red,
        _ => Color::White,
    }
}

// --- Board -----------------------------------------------------------------

/// Coalesce a row of `(char, colour)` cells into a styled [`Line`], merging
/// adjacent cells that share a colour into one span.
fn row_to_line(cells: Vec<(char, Color)>) -> Line<'static> {
    let mut spans: Vec<Span<'static>> = Vec::new();
    let mut run: String = String::new();
    let mut run_color: Color = Color::White;
    for (ch, color) in cells {
        if !run.is_empty() && color != run_color {
            spans.push(Span::styled(
                std::mem::take(&mut run),
                Style::default().fg(run_color),
            ));
        }
        if run.is_empty() {
            run_color = color;
        }
        run.push(ch);
    }
    if !run.is_empty() {
        spans.push(Span::styled(run, Style::default().fg(run_color)));
    }
    Line::from(spans)
}

/// Build the coloured board as styled lines: cyan discs, white pegs/base, and
/// the active label row (plus a default-reference row when relabelled) coloured
/// per peg. Empty for a 0-disc game. Mirrors the curses `_draw_board`.
fn board_lines(session: &GameSession) -> Vec<Line<'static>> {
    let n: usize = session.num_disks() as usize;
    if n == 0 {
        return Vec::new();
    }
    let labelling: Labelling = session.labelling;
    let relabelled: bool = labelling != Labelling::OneTwoThree;
    let width: usize = presenter::total_width(n);
    let rows: usize = n + 3 + usize::from(relabelled);
    let mut grid: Vec<Vec<(char, Color)>> = vec![vec![(' ', Color::White); width]; rows];

    // Vertical pegs (rows 0..=n), white.
    for peg in 0..3 {
        let cx = presenter::peg_center_x(n, peg);
        for row in grid.iter_mut().take(n + 1) {
            row[cx] = ('|', Color::White);
        }
    }

    // Discs, cyan.
    let pvw = presenter::peg_visual_width(n);
    for (peg, stack) in session.game.towers.iter().enumerate() {
        let cx = presenter::peg_center_x(n, peg);
        for (i, &size) in stack.iter().enumerate() {
            let row = n - i;
            let start = cx - pvw / 2 + presenter::padding_left(n, size as usize);
            for col in start..start + presenter::disk_char_width(size as usize) {
                grid[row][col] = ('*', Color::Cyan);
            }
        }
    }

    // Base line, white.
    for cell in grid[n + 1].iter_mut() {
        *cell = ('=', Color::White);
    }

    // Active labels, coloured per peg.
    for peg in 0..3 {
        let cx = presenter::peg_center_x(n, peg);
        let digit = digit_char(change_labels_on_pegs(labelling, peg) + 1);
        grid[n + 2][cx] = (digit, peg_fg(labelling, peg));
    }

    // Default-reference row when relabelled.
    if relabelled {
        for peg in 0..3 {
            let cx = presenter::peg_center_x(n, peg);
            grid[n + 3][cx] = (digit_char(peg + 1), peg_fg(Labelling::OneTwoThree, peg));
        }
    }

    grid.into_iter().map(row_to_line).collect()
}

/// A single digit `d` (1..=9) as its character.
fn digit_char(d: usize) -> char {
    char::from_digit(d as u32, 10).expect("label digit is 1..=9")
}

/// The one-line status: disc count, active labelling, move count, recipe count.
fn status_line(session: &GameSession) -> String {
    let a = change_labels_on_pegs(session.labelling, 0) + 1;
    let b = change_labels_on_pegs(session.labelling, 1) + 1;
    let c = change_labels_on_pegs(session.labelling, 2) + 1;
    format!(
        " Discs: {}    Labelling: {a} {b} {c}    Moves: {}    Recipes: {} ",
        session.num_disks(),
        session.current_moves(),
        session.registry.len()
    )
}

// --- Rendering --------------------------------------------------------------

/// Render the whole play screen: status row, centred board, message area, hint
/// area, and the input prompt with the current buffer. Pure (no terminal), so
/// it renders to any backend — exercised headlessly in the tests.
fn draw_play(
    f: &mut Frame,
    session: &GameSession,
    msg_lines: &[String],
    hint: &[&str],
    input: &str,
) {
    let [status, board, messages, hints, prompt]: [Rect; 5] = Layout::vertical([
        Constraint::Length(1),
        Constraint::Min(1),
        Constraint::Length(MSG_AREA_LINES as u16),
        Constraint::Length(HINT_AREA_LINES as u16),
        Constraint::Length(1),
    ])
    .areas(f.area());

    f.render_widget(
        Paragraph::new(status_line(session)).style(Style::default().fg(Color::Yellow)),
        status,
    );
    f.render_widget(
        Paragraph::new(board_lines(session)).alignment(Alignment::Center),
        board,
    );

    let visible: Vec<Line> = msg_lines
        .iter()
        .rev()
        .take(MSG_AREA_LINES)
        .rev()
        .map(|s| Line::from(Span::styled(s.clone(), Style::default().fg(Color::Yellow))))
        .collect();
    f.render_widget(Paragraph::new(visible), messages);

    // Bottom-align the hint within its area (pad with blank lines on top).
    let shown: Vec<&str> = hint
        .iter()
        .rev()
        .take(HINT_AREA_LINES)
        .rev()
        .copied()
        .collect();
    let mut hint_lines: Vec<Line> = vec![Line::from(""); HINT_AREA_LINES - shown.len()];
    hint_lines.extend(shown.iter().map(|h| {
        Line::from(Span::styled(
            (*h).to_string(),
            Style::default().fg(Color::Gray),
        ))
    }));
    f.render_widget(Paragraph::new(hint_lines), hints);

    f.render_widget(Paragraph::new(format!("> {input}")), prompt);
}

/// Render the modal disc-count prompt on a clean screen.
fn draw_disc_prompt(f: &mut Frame, input: &str) {
    let lines = vec![
        Line::from(""),
        Line::from(Span::styled(
            " Towers of Hanoi — type 'help' for commands.",
            Style::default().fg(Color::Yellow),
        )),
        Line::from(""),
        Line::from(format!(" How many discs? (1-{MAX_DISKS}, or 'quit')")),
        Line::from(""),
        Line::from(format!("> {input}")),
    ];
    f.render_widget(Paragraph::new(lines), f.area());
}

/// Render the full-screen pager for output taller than the message area.
fn draw_pager(f: &mut Frame, lines: &[String], top: usize) {
    let area = f.area();
    let view_h = area.height.saturating_sub(1) as usize;
    let mut shown: Vec<Line> = lines
        .iter()
        .skip(top)
        .take(view_h)
        .map(|s| Line::from(s.clone()))
        .collect();
    while shown.len() < view_h {
        shown.push(Line::from(""));
    }
    shown.push(Line::from(Span::styled(
        "[Up/Down PgUp/PgDn Home/End scroll - q or Enter to close]",
        Style::default().fg(Color::Gray),
    )));
    f.render_widget(Paragraph::new(shown), area);
}

// --- Input ------------------------------------------------------------------

/// A key the UI cares about.
enum Key {
    Char(char),
    Enter,
    Backspace,
    Up,
    Down,
    PageUp,
    PageDown,
    Home,
    End,
    /// Ctrl-C or Esc — treated as cancel/EOF.
    Interrupt,
    Other,
}

/// Block until a key press, classified as a [`Key`].
fn read_key() -> std::io::Result<Key> {
    loop {
        if let Event::Key(k) = event::read()? {
            if k.kind != KeyEventKind::Press {
                continue;
            }
            let key = match k.code {
                KeyCode::Char('c' | 'C') if k.modifiers.contains(KeyModifiers::CONTROL) => {
                    Key::Interrupt
                }
                KeyCode::Esc => Key::Interrupt,
                KeyCode::Enter => Key::Enter,
                KeyCode::Backspace => Key::Backspace,
                KeyCode::Up => Key::Up,
                KeyCode::Down => Key::Down,
                KeyCode::PageUp => Key::PageUp,
                KeyCode::PageDown => Key::PageDown,
                KeyCode::Home => Key::Home,
                KeyCode::End => Key::End,
                KeyCode::Char(c) => Key::Char(c),
                _ => Key::Other,
            };
            return Ok(key);
        }
    }
}

/// Draw `draw(frame, input)` repeatedly while the user edits a line; return the
/// submitted line on Enter, or `None` on Ctrl-C/Esc.
fn read_line_on<F>(terminal: &mut DefaultTerminal, draw: F) -> std::io::Result<Option<String>>
where
    F: Fn(&mut Frame, &str),
{
    let mut input = String::new();
    loop {
        terminal.draw(|f| draw(f, &input))?;
        match read_key()? {
            Key::Char(c) => input.push(c),
            Key::Backspace => {
                input.pop();
            }
            Key::Enter => return Ok(Some(input)),
            Key::Interrupt => return Ok(None),
            _ => {}
        }
    }
}

/// Page through `lines` full-screen until the user closes it.
fn pager(terminal: &mut DefaultTerminal, lines: &[String]) -> std::io::Result<()> {
    let mut top: usize = 0;
    loop {
        terminal.draw(|f| draw_pager(f, lines, top))?;
        let view_h = terminal.size()?.height.saturating_sub(1) as usize;
        let maxtop = lines.len().saturating_sub(view_h);
        match read_key()? {
            Key::Char('q' | 'Q') | Key::Enter | Key::Interrupt => return Ok(()),
            Key::Down | Key::Char('j') => top = (top + 1).min(maxtop),
            Key::Up | Key::Char('k') => top = top.saturating_sub(1),
            Key::PageDown | Key::Char(' ') => top = (top + view_h).min(maxtop),
            Key::PageUp => top = top.saturating_sub(view_h),
            Key::Home => top = 0,
            Key::End => top = maxtop,
            _ => {}
        }
    }
}

// --- Top-level flow ---------------------------------------------------------

/// Modally ask for a disc count; `None` to quit.
fn prompt_disc_count(terminal: &mut DefaultTerminal) -> std::io::Result<Option<u32>> {
    loop {
        let Some(line) = read_line_on(terminal, draw_disc_prompt)? else {
            return Ok(None);
        };
        let s = line.trim().to_lowercase();
        if matches!(s.as_str(), "quit" | "q" | "exit") {
            return Ok(None);
        }
        if let Ok(n) = s.parse::<u32>() {
            if (1..=MAX_DISKS).contains(&n) {
                return Ok(Some(n));
            }
        }
    }
}

/// Play one game to a win or exit. Returns whether to play again.
fn play_game(
    terminal: &mut DefaultTerminal,
    n: u32,
    registry: &mut RecipeRegistry,
) -> std::io::Result<bool> {
    let mut session = GameSession::new(n, registry);
    let mut msg: Vec<String> = Vec::new();

    while !session.is_won() {
        let Some(line) = read_line_on(terminal, |f, input| {
            draw_play(f, &session, &msg, &DEFAULT_HINT, input)
        })?
        else {
            return Ok(false);
        };
        let cmd = parse(&line);
        let result = session.dispatch(&cmd);
        if result.quit {
            return Ok(false);
        }
        let mut show = result.lines.clone();
        show.extend(session.move_teaching_lines(&cmd, &result));
        if show.len() > MSG_AREA_LINES {
            pager(terminal, &show)?;
            msg = Vec::new();
        } else {
            msg = show;
        }
    }

    // Won.
    let min = session.min_moves();
    let moves = u64::from(session.current_moves());
    let mut banner = vec![format!("Solved! {moves} moves (minimum {min}).")];
    if moves == min {
        banner.push("Optimal solution!".to_string());
    } else {
        banner.push(format!("{} more than the minimum.", moves - min));
    }

    let save_hint = ["Save this solution? Type a name, or press Enter to skip."];
    let name = read_line_on(terminal, |f, input| {
        draw_play(f, &session, &banner, &save_hint, input)
    })?;
    if let Some(name) = name {
        let name = name.trim();
        if !name.is_empty() {
            let msg = session.save_recipe(name);
            banner.push(msg);
        }
    }

    let again_hint = ["Play again? (y/n)"];
    let again = read_line_on(terminal, |f, input| {
        draw_play(f, &session, &banner, &again_hint, input)
    })?;
    Ok(matches!(again, Some(a) if a.trim().to_lowercase().starts_with('y')))
}

/// The game loop: prompt for a disc count, play, repeat until the user quits.
fn app(terminal: &mut DefaultTerminal) -> std::io::Result<()> {
    let mut registry = RecipeRegistry::new();
    loop {
        let Some(n) = prompt_disc_count(terminal)? else {
            return Ok(());
        };
        if !play_game(terminal, n, &mut registry)? {
            return Ok(());
        }
    }
}

fn main() -> std::io::Result<()> {
    let mut terminal = ratatui::init();
    let result = app(&mut terminal);
    ratatui::restore();
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::{backend::TestBackend, Terminal};

    /// The whole rendered screen as one string (symbols only).
    fn screen(width: u16, height: u16, draw: impl FnOnce(&mut Frame)) -> String {
        let mut terminal = Terminal::new(TestBackend::new(width, height)).unwrap();
        terminal.draw(|f| draw(f)).unwrap();
        terminal
            .backend()
            .buffer()
            .content()
            .iter()
            .map(ratatui::buffer::Cell::symbol)
            .collect()
    }

    #[test]
    fn board_lines_match_presenter_width() {
        let mut reg = RecipeRegistry::new();
        let session = GameSession::new(3, &mut reg);
        let lines = board_lines(&session);
        // n + 3 rows under the default labelling (no reference row).
        assert_eq!(lines.len(), 3 + 3);
        for line in &lines {
            assert_eq!(line.width(), presenter::total_width(3));
        }
    }

    #[test]
    fn board_lines_empty_for_zero_discs() {
        let mut reg = RecipeRegistry::new();
        let session = GameSession::new(0, &mut reg);
        assert!(board_lines(&session).is_empty());
    }

    #[test]
    fn relabel_adds_reference_row() {
        let mut reg = RecipeRegistry::new();
        let mut session = GameSession::new(3, &mut reg);
        session.labelling = Labelling::ThreeTwoOne;
        assert_eq!(board_lines(&session).len(), 3 + 4);
    }

    #[test]
    fn play_screen_shows_status_board_and_prompt() {
        let mut reg = RecipeRegistry::new();
        let session = GameSession::new(3, &mut reg);
        let content = screen(60, 20, |f| {
            draw_play(f, &session, &["hello".to_string()], &DEFAULT_HINT, "1 -> 3");
        });
        assert!(content.contains("Discs: 3"), "status missing");
        assert!(content.contains("Moves: 0"), "move count missing");
        assert!(content.contains('*'), "a disc should be drawn");
        assert!(content.contains("hello"), "message missing");
        assert!(content.contains("> 1 -> 3"), "input prompt missing");
        assert!(content.contains("Move: type"), "default hint missing");
    }

    #[test]
    fn disc_prompt_renders() {
        let content = screen(60, 12, |f| draw_disc_prompt(f, "3"));
        assert!(content.contains("How many discs?"));
        assert!(content.contains("> 3"));
    }
}
