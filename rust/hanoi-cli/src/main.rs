// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later

//! Plain stdin/stdout front-end for the Towers of Hanoi game.
//!
//! A thin wrapper around [`hanoigame::GameSession`]: read a line, parse it, hand
//! the command to the session, print the lines that come back. The disc-count
//! prompt and the post-win save prompt are front-end-specific and live here.
//! (Rust port of `python/src/hanoigame/hanoicli.py`, kept in sync.)
//!
//! The game loop reads lines through the [`LineReader`] trait, so it serves both
//! modes from one body (as the Python's `_read_line` did): a [`StreamReader`]
//! over any `BufRead`/`Write` for pipes and tests (byte-for-byte scripted I/O),
//! and a [`RustylineReader`] at a real terminal for line editing + Tab
//! completion (command verbs at the start of a line; saved-recipe names after
//! `apply `/`show `). The completion logic itself ([`completions`]) is pure and
//! unit-tested.

use std::io::{BufRead, IsTerminal, Write};

use hanoigame::commands::{completions, parse};
use hanoigame::engine::GameSession;
use hanoigame::presenter::render_with_legend;
use hanoigame::recipe::RecipeRegistry;

const MAX_DISKS: u32 = 10;

/// Reads one line of input for the game loop, writing the `prompt` where the
/// mode requires it. `recipe_names` feeds tab-completion (ignored by the
/// non-interactive reader).
trait LineReader {
    fn read(
        &mut self,
        prompt: &str,
        out: &mut dyn Write,
        recipe_names: &[String],
    ) -> Option<String>;
}

/// The scripted / piped reader: write the prompt to `out`, read a line from the
/// stream, strip the trailing newline; `None` on EOF. No completion.
struct StreamReader<'a, R: BufRead> {
    input: &'a mut R,
}

impl<R: BufRead> LineReader for StreamReader<'_, R> {
    fn read(&mut self, prompt: &str, out: &mut dyn Write, _names: &[String]) -> Option<String> {
        let _ = write!(out, "{prompt}");
        let _ = out.flush();
        let mut line = String::new();
        match self.input.read_line(&mut line) {
            Ok(0) | Err(_) => None,
            Ok(_) => Some(line.trim_end_matches('\n').to_string()),
        }
    }
}

/// The interactive reader: rustyline line editing + history, with Tab
/// completion refreshed from the current recipe names each prompt. rustyline
/// prints the prompt itself, so `out` is unused here.
struct RustylineReader {
    editor: rustyline::Editor<HanoiHelper, rustyline::history::DefaultHistory>,
}

impl LineReader for RustylineReader {
    fn read(
        &mut self,
        prompt: &str,
        _out: &mut dyn Write,
        recipe_names: &[String],
    ) -> Option<String> {
        if let Some(helper) = self.editor.helper_mut() {
            helper.recipe_names = recipe_names.to_vec();
        }
        match self.editor.readline(prompt) {
            Ok(line) => {
                let _ = self.editor.add_history_entry(line.as_str());
                Some(line)
            }
            // Ctrl-D (Eof) and Ctrl-C (Interrupted) both end input, like the stream EOF.
            Err(_) => None,
        }
    }
}

/// rustyline helper providing Tab completion via [`completions`]; the other
/// helper traits are no-ops.
struct HanoiHelper {
    recipe_names: Vec<String>,
}

impl rustyline::completion::Completer for HanoiHelper {
    type Candidate = rustyline::completion::Pair;

    fn complete(
        &self,
        line: &str,
        pos: usize,
        _ctx: &rustyline::Context<'_>,
    ) -> rustyline::Result<(usize, Vec<Self::Candidate>)> {
        // The current word runs from the last space before the cursor to `pos`.
        let start = line[..pos].rfind(' ').map_or(0, |i| i + 1);
        let word = &line[start..pos];
        let pairs = completions(line, word, &self.recipe_names)
            .into_iter()
            .map(|s| rustyline::completion::Pair {
                display: s.clone(),
                replacement: s,
            })
            .collect();
        Ok((start, pairs))
    }
}

impl rustyline::hint::Hinter for HanoiHelper {
    type Hint = String;
}
impl rustyline::highlight::Highlighter for HanoiHelper {}
impl rustyline::validate::Validator for HanoiHelper {}
impl rustyline::Helper for HanoiHelper {}

/// Render the current board plus the running move count to `output`.
fn print_board<W: Write>(session: &GameSession, output: &mut W) {
    for line in render_with_legend(&session.game, session.labelling) {
        let _ = writeln!(output, "{line}");
    }
}

/// Prompt repeatedly for a disc count until a valid one is given; `None` on
/// EOF or quit.
fn prompt_disc_count<W: Write>(
    reader: &mut dyn LineReader,
    names: &[String],
    output: &mut W,
) -> Option<u32> {
    loop {
        let line = reader.read(
            &format!("How many discs? (1-{MAX_DISKS}, or 'quit'): "),
            output,
            names,
        )?;
        let s = line.trim().to_lowercase();
        if matches!(s.as_str(), "quit" | "q" | "exit") {
            return None;
        }
        if let Ok(n) = s.parse::<u32>() {
            if (1..=MAX_DISKS).contains(&n) {
                return Some(n);
            }
        }
        let _ = writeln!(output, "Please enter a number from 1 to {MAX_DISKS}.");
    }
}

/// After a win, offer to save the solution as a recipe.
fn prompt_save<W: Write>(reader: &mut dyn LineReader, session: &mut GameSession, output: &mut W) {
    let default = format!("solve-{}", session.num_disks());
    let names = session.registry.names();
    let prompt = format!(
        "\nSave this solution as a recipe? Enter to save as '{default}', a name \
         to rename, or '-' to skip: "
    );
    let Some(line) = reader.read(&prompt, output, &names) else {
        return;
    };
    let name = line.trim();
    if name == "-" {
        return;
    }
    let name = if name.is_empty() {
        default.as_str()
    } else {
        name
    };
    let _ = writeln!(output, "{}", session.save_recipe(name));
}

/// Play one game to a win, quit, or EOF. Returns whether to play again.
fn play_game<W: Write>(
    reader: &mut dyn LineReader,
    registry: &mut RecipeRegistry,
    n: u32,
    output: &mut W,
) -> bool {
    let mut session = GameSession::new(n, registry);

    while !session.is_won() {
        let _ = writeln!(output);
        print_board(&session, output);
        let _ = writeln!(output, "{}", session.valid_moves_str());
        let names = session.registry.names();
        let Some(line) = reader.read("> ", output, &names) else {
            return false;
        };
        let cmd = parse(&line);
        let result = session.dispatch(&cmd);
        for line in &result.lines {
            let _ = writeln!(output, "{line}");
        }
        for line in session.move_teaching_lines(&cmd, &result) {
            let _ = writeln!(output, "{line}");
        }
        if result.quit {
            return false;
        }
    }

    let _ = writeln!(output);
    print_board(&session, output);
    let min = session.min_moves();
    let moves = u64::from(session.current_moves());
    let _ = writeln!(output, "\nSolved! {moves} moves (minimum {min}).");
    if moves == min {
        let _ = writeln!(output, "Optimal solution!");
    } else {
        let _ = writeln!(output, "{} more than the minimum.", moves - min);
    }

    prompt_save(reader, &mut session, output);

    let names = session.registry.names();
    match reader.read("\nPlay again? (y/n): ", output, &names) {
        Some(again) => again.trim().to_lowercase().starts_with('y'),
        None => false,
    }
}

/// The game loop: greet, then prompt for a disc count and play until the user
/// quits or EOFs. Returns the process exit code (always `0`).
fn game_loop<W: Write>(reader: &mut dyn LineReader, output: &mut W) -> i32 {
    let _ = writeln!(output, "Towers of Hanoi — type 'help' for commands.");
    let mut registry = RecipeRegistry::new();
    loop {
        let names = registry.names();
        let Some(n) = prompt_disc_count(reader, &names, output) else {
            let _ = writeln!(output, "Bye.");
            return 0;
        };
        if !play_game(reader, &mut registry, n, output) {
            let _ = writeln!(output, "Bye.");
            return 0;
        }
    }
}

/// Run over any `BufRead`/`Write` pair (pipes, tests) — the scripted path, no
/// line editing or completion. Returns the process exit code.
pub fn run<R: BufRead, W: Write>(input: &mut R, output: &mut W) -> i32 {
    let mut reader = StreamReader { input };
    game_loop(&mut reader, output)
}

/// Run at a real terminal with rustyline line editing + Tab completion.
fn run_interactive() -> i32 {
    let mut editor =
        match rustyline::Editor::<HanoiHelper, rustyline::history::DefaultHistory>::new() {
            Ok(editor) => editor,
            Err(_) => {
                // readline init failed — fall back to the plain stream path.
                let stdin = std::io::stdin();
                let stdout = std::io::stdout();
                return run(&mut stdin.lock(), &mut stdout.lock());
            }
        };
    editor.set_helper(Some(HanoiHelper {
        recipe_names: Vec::new(),
    }));
    let mut reader = RustylineReader { editor };
    let stdout = std::io::stdout();
    game_loop(&mut reader, &mut stdout.lock())
}

fn main() {
    if std::io::stdin().is_terminal() {
        std::process::exit(run_interactive());
    }
    let stdin = std::io::stdin();
    let stdout = std::io::stdout();
    std::process::exit(run(&mut stdin.lock(), &mut stdout.lock()));
}

#[cfg(test)]
mod tests {
    use super::*;

    // Ported from python/tests/test_hanoicli.py.

    const WIN_3_OPTIMAL: [&str; 7] = ["1 3", "1 2", "3 2", "1 3", "2 1", "2 3", "1 3"];
    const WIN_2_OPTIMAL: [&str; 3] = ["1 2", "1 3", "2 3"];

    fn script(chunks: &[&str]) -> String {
        let mut s = chunks.join("\n");
        s.push('\n');
        s
    }

    fn drive(input_text: &str) -> String {
        let mut input = input_text.as_bytes();
        let mut output: Vec<u8> = Vec::new();
        run(&mut input, &mut output);
        String::from_utf8(output).expect("utf-8 output")
    }

    #[test]
    fn winning_3_disc_sequence_optimal() {
        let mut chunks = vec!["3"];
        chunks.extend(WIN_3_OPTIMAL);
        chunks.extend(["-", "n"]);
        let out = drive(&script(&chunks));
        assert!(out.contains("Solved! 7 moves (minimum 7)."));
        assert!(out.contains("Optimal solution!"));
    }

    #[test]
    fn winning_with_extra_moves_reports_diff() {
        let mut chunks = vec!["3", "1 2", "2 1"];
        chunks.extend(WIN_3_OPTIMAL);
        chunks.extend(["-", "n"]);
        let out = drive(&script(&chunks));
        assert!(out.contains("Solved! 9 moves (minimum 7)."));
        assert!(out.contains("2 more than the minimum."));
    }

    #[test]
    fn illegal_moves_are_explained() {
        assert!(drive(&script(&["3", "2 1", "quit"])).contains("Peg 2 is empty"));
        assert!(drive(&script(&["3", "1 3", "1 3", "quit"])).contains("larger on smaller"));
    }

    #[test]
    fn quit_and_eof_exit_cleanly() {
        assert!(drive("quit\n").contains("Bye."));
        assert!(drive("").contains("Bye."));
    }

    #[test]
    fn relabel_shows_both_label_rows() {
        let out = drive(&script(&["3", "relabel 3 2 1", "quit"]));
        assert!(out.contains("  3         2         1  "));
        assert!(out.contains("  1         2         3  "));
    }

    #[test]
    fn default_reference_row_absent_under_default() {
        let out = drive(&script(&["3", "quit"]));
        assert_eq!(out.matches("  1         2         3  ").count(), 1);
    }

    #[test]
    fn help_and_parse_error() {
        let help = drive(&script(&["3", "help", "quit"]));
        assert!(help.contains("Commands:") && help.contains("relabel"));
        assert!(drive(&script(&["3", "wat", "quit"])).contains("unrecognised command"));
    }

    #[test]
    fn invalid_disc_count_reprompts() {
        let out = drive("0\n11\nfoo\n3\nquit\n");
        assert_eq!(
            out.matches("Please enter a number from 1 to 10.").count(),
            3
        );
    }

    #[test]
    fn save_only_works_after_winning() {
        let out = drive(&script(&["3", "save mid-game", "quit"]));
        assert!(out.contains("Save only works after winning"));
    }

    #[test]
    fn post_win_save_named_default_and_skip() {
        let mut named = vec!["2"];
        named.extend(WIN_2_OPTIMAL);
        named.extend(["win-2", "n"]);
        assert!(drive(&script(&named)).contains("Saved recipe 'win-2'."));

        let mut dash = vec!["2"];
        dash.extend(WIN_2_OPTIMAL);
        dash.extend(["-", "n"]);
        let out = drive(&script(&dash));
        assert!(!out.contains("Saved recipe"));
        assert!(out.contains("Solved!"));

        let mut empty = vec!["2"];
        empty.extend(WIN_2_OPTIMAL);
        empty.extend(["", "n"]);
        assert!(drive(&script(&empty)).contains("Saved recipe 'solve-2'."));
    }

    #[test]
    fn list_and_apply_and_show() {
        let mut chunks = vec!["2"];
        chunks.extend(WIN_2_OPTIMAL);
        chunks.extend(["win-2", "y", "2", "list", "quit"]);
        let out = drive(&script(&chunks));
        assert!(out.contains("win-2"));
        assert!(out.contains("(2 discs, 3 moves)"));

        assert!(drive(&script(&["3", "list", "quit"])).contains("No recipes saved yet."));
        assert!(drive(&script(&["3", "apply ghost", "quit"])).contains("No recipe named 'ghost'"));
        assert!(drive(&script(&["3", "show ghost", "quit"])).contains("No recipe named 'ghost'"));
    }

    #[test]
    fn apply_replays_recipe_on_fresh_game() {
        let mut chunks = vec!["2"];
        chunks.extend(WIN_2_OPTIMAL);
        chunks.extend(["two", "y", "2", "apply two", "-", "n"]);
        let out = drive(&script(&chunks));
        assert!(out.contains("Applying recipe 'two' (3 moves):"));
        assert!(out.contains("  step 1: 1 -> 2"));
        assert!(out.contains("  step 2: 1 -> 3"));
        assert!(out.contains("  step 3: 2 -> 3"));
        assert_eq!(out.matches("Solved! 3 moves (minimum 3).").count(), 2);
    }

    #[test]
    fn show_prints_recipe_steps() {
        let mut chunks = vec!["2"];
        chunks.extend(WIN_2_OPTIMAL);
        chunks.extend(["two", "y", "2", "show two", "quit"]);
        let out = drive(&script(&chunks));
        assert!(out.contains("Recipe 'two' (2 discs, 3 moves):"));
        assert!(out.contains("  step 1: 1 -> 2"));
        assert!(out.contains("  step 3: 2 -> 3"));
    }

    #[test]
    fn overwriting_recipe_name_says_so() {
        let mut chunks = vec!["2"];
        chunks.extend(WIN_2_OPTIMAL);
        chunks.extend(["dup", "y", "2"]);
        chunks.extend(WIN_2_OPTIMAL);
        chunks.extend(["dup", "n"]);
        let out = drive(&script(&chunks));
        assert!(out.contains("Saved recipe 'dup'."));
        assert!(out.contains("Overwrote recipe 'dup'."));
    }

    #[test]
    fn bill_worked_example_via_cli() {
        let mut chunks = vec!["2"];
        chunks.extend(WIN_2_OPTIMAL);
        chunks.extend([
            "solve-2-from-1-to-3",
            "y",
            "3",
            "relabel 1 3 2",
            "apply solve-2-from-1-to-3",
            "quit",
        ]);
        let out = drive(&script(&chunks));
        assert!(out.contains("Applying recipe 'solve-2-from-1-to-3'"));
        assert!(out.contains("Done."));
        for line in [
            "  |         |         |  ",
            "  |         *         |  ",
            "*****      ***        |  ",
            "=========================",
            "  1         3         2  ",
        ] {
            assert!(out.contains(line), "missing board line: {line:?}");
        }
    }

    #[test]
    fn recipe_captured_under_relabel_replays_under_default() {
        let chunks = [
            "2",
            "relabel 3 2 1",
            "3 2",
            "3 1",
            "2 1",
            "captured-under-relabel",
            "y",
            "2",
            "apply captured-under-relabel",
            "-",
            "n",
        ];
        let out = drive(&script(&chunks));
        assert_eq!(out.matches("Solved! 3 moves (minimum 3).").count(), 2);
    }

    #[test]
    fn completions_verbs_at_line_start() {
        let names: Vec<String> = Vec::new();
        let all: std::collections::HashSet<String> =
            completions("", "", &names).into_iter().collect();
        let expected: std::collections::HashSet<String> =
            COMMAND_VERBS.iter().map(|v| v.to_string()).collect();
        assert_eq!(all, expected);
        assert_eq!(completions("ap", "ap", &names), vec!["apply".to_string()]);
        assert_eq!(
            completions("s", "s", &names),
            vec!["save".to_string(), "show".to_string()]
        );
    }

    #[test]
    fn completions_recipe_names_after_apply_and_show() {
        // The caller passes registry.names(), which is sorted.
        let names = vec!["other".to_string(), "solve-2".to_string()];
        assert_eq!(
            completions("apply ", "", &names),
            vec!["other".to_string(), "solve-2".to_string()]
        );
        assert_eq!(
            completions("apply so", "so", &names),
            vec!["solve-2".to_string()]
        );
        assert_eq!(
            completions("show ot", "ot", &names),
            vec!["other".to_string()]
        );
    }

    #[test]
    fn completions_none_after_save() {
        let names = vec!["solve-2".to_string()];
        assert_eq!(completions("save so", "so", &names), Vec::<String>::new());
        assert_eq!(completions("save ", "", &names), Vec::<String>::new());
    }
}
