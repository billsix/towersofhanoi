// Copyright (c) 2025-2026 William Emerison Six
// SPDX-License-Identifier: GPL-2.0-or-later

//! Shared input grammar for the Hanoi game front-ends.
//!
//! [`parse`] turns one line of user input into a [`Command`] (a sum type that
//! includes the empty-input and parse-error cases) so the CLI, TUI, and GUI
//! front-ends dispatch identically. Pure: no I/O, no state. (Rust port of
//! `python/src/hanoigame/commands.py`, kept in sync. The Python `MoveCmd`,
//! `ParseError`, … dataclasses become variants of one enum here.)

/// One parsed line of user input.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Command {
    /// Move the top disc from `from_label` to `to_label` (1-indexed labels
    /// under the current `Labelling`).
    Move { from_label: u32, to_label: u32 },
    /// Set the labelling so physical pegs 0, 1, 2 carry these 1-indexed labels
    /// (a permutation of 1, 2, 3).
    Relabel([u32; 3]),
    /// Save the most recently won game's moves as a named recipe.
    Save(String),
    /// Replay a named recipe, translated through the current labelling.
    Apply(String),
    /// Print the contents of a named recipe.
    Show(String),
    /// List all saved recipes.
    List,
    /// Show help text.
    Help,
    /// Quit the game.
    Quit,
    /// Blank input — a front-end may redraw and re-prompt.
    Empty,
    /// Input couldn't be parsed; the string explains why (the Python
    /// `ParseError`).
    Error(String),
}

/// The keyword commands [`parse`] recognises at the start of a line, in the
/// order they appear in [`HELP_TEXT`] — the single source of truth for
/// tab-completion. Moves use the `<from> -> <to>` syntax, not a keyword, so
/// there is no "move" verb here.
pub const COMMAND_VERBS: [&str; 7] = ["relabel", "save", "apply", "show", "list", "help", "quit"];

/// Tab-completion candidates for `text` (the token under the cursor) given the whole input
/// `buffer` and the saved-recipe `recipe_names`: command verbs while still on the first token,
/// recipe names after `apply `/`show ` (never after `save `, so completion never invites
/// overwriting a recipe). Pure and unit-testable; `recipe_names` is a slice (sorted by the
/// caller) so this doesn't depend on the registry type. Shared by every front-end that offers
/// completion (the CLI's readline helper and the TUI prompt).
pub fn completions(buffer: &str, text: &str, recipe_names: &[String]) -> Vec<String> {
    let stripped: &str = buffer.trim_start();
    if stripped.starts_with("apply ") || stripped.starts_with("show ") {
        return recipe_names
            .iter()
            .filter(|name| name.starts_with(text))
            .cloned()
            .collect();
    }
    if stripped.contains(' ') {
        return Vec::new();
    }
    COMMAND_VERBS
        .iter()
        .filter(|verb| verb.starts_with(text))
        .map(|verb| verb.to_string())
        .collect()
}

/// The help text listing every command.
pub const HELP_TEXT: &str = "\
Commands:
  <from> -> <to>   move a disc, e.g. '1 -> 3' (also accepts '1 3' or '13')
  relabel a b c    rename pegs so physical pegs 1,2,3 show as a,b,c
                   (a,b,c must be a permutation of 1,2,3)
  save <name>      save the just-won solution as a recipe
  apply <name>     replay a saved recipe under the current labelling
  show <name>      print the moves in a saved recipe
  list             list saved recipes
  help             show this help
  quit             quit the game";

/// Non-empty and every byte an ASCII digit (the Rust equivalent of Python's
/// `str.isdigit()` for the ASCII inputs the grammar accepts).
fn is_digits(s: &str) -> bool {
    !s.is_empty() && s.bytes().all(|b| b.is_ascii_digit())
}

/// A `Move` for labels `a` -> `b`, or an `Error` when they are out of 1..=3 or
/// equal.
fn move_or_error(a: u32, b: u32) -> Command {
    if !(1..=3).contains(&a) || !(1..=3).contains(&b) {
        return Command::Error(format!("move labels must be 1, 2, or 3 — got {a} and {b}"));
    }
    if a == b {
        return Command::Error(format!("can't move from peg {a} to itself"));
    }
    Command::Move {
        from_label: a,
        to_label: b,
    }
}

/// A recipe command (`save`/`apply`/`show`) carrying the joined name, or an
/// `Error` when no name was given.
fn name_cmd(parts: &[&str], verb: &str, make: fn(String) -> Command) -> Command {
    if parts.len() < 2 {
        return Command::Error(format!(
            "{verb} needs a recipe name, e.g. '{verb} my-3-disc-solve'"
        ));
    }
    make(parts[1..].join(" "))
}

/// Parse one line of user input into a [`Command`]. Never fails (the failure
/// cases are the `Empty` and `Error` variants).
pub fn parse(line: &str) -> Command {
    let s: &str = line.trim();
    if s.is_empty() {
        return Command::Empty;
    }

    match s.to_lowercase().as_str() {
        "quit" | "q" | "exit" => return Command::Quit,
        "help" | "h" | "?" => return Command::Help,
        "list" => return Command::List,
        _ => {}
    }

    // Move with an explicit arrow: "1 -> 3", "1->3", any internal spacing.
    if let Some(idx) = s.find("->") {
        let a: &str = s[..idx].trim();
        let b: &str = s[idx + 2..].trim();
        if is_digits(a) && is_digits(b) {
            return move_or_error(a.parse().unwrap(), b.parse().unwrap());
        }
        return Command::Error(format!(
            "couldn't parse move {s:?} — expected '<from> -> <to>', e.g. '1 -> 3'"
        ));
    }

    // Bare two-digit shorthand: "13" -> 1 to 3.
    if is_digits(s) && s.len() == 2 {
        let digits: &[u8] = s.as_bytes();
        let a: u32 = u32::from(digits[0] - b'0');
        let b: u32 = u32::from(digits[1] - b'0');
        return move_or_error(a, b);
    }

    let parts: Vec<&str> = s.split_whitespace().collect();

    // Spaced two-token move: "1 3".
    if parts.len() == 2 && is_digits(parts[0]) && is_digits(parts[1]) {
        return move_or_error(parts[0].parse().unwrap(), parts[1].parse().unwrap());
    }

    match parts[0].to_lowercase().as_str() {
        "relabel" => {
            if parts.len() != 4 || !parts[1..].iter().all(|p| is_digits(p)) {
                return Command::Error(
                    "relabel takes three labels, e.g. 'relabel 2 1 3'".to_string(),
                );
            }
            let labels: [u32; 3] = [
                parts[1].parse().unwrap(),
                parts[2].parse().unwrap(),
                parts[3].parse().unwrap(),
            ];
            let mut sorted: [u32; 3] = labels;
            sorted.sort_unstable();
            if sorted != [1, 2, 3] {
                return Command::Error(format!(
                    "relabel needs a permutation of 1,2,3 — got {labels:?}"
                ));
            }
            Command::Relabel(labels)
        }
        "save" => name_cmd(&parts, "save", Command::Save),
        "apply" => name_cmd(&parts, "apply", Command::Apply),
        "show" => name_cmd(&parts, "show", Command::Show),
        _ => Command::Error(format!(
            "unrecognised command: {s:?}. Type 'help' for the command list."
        )),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Ported from python/tests/test_commands.py.

    fn mv(a: u32, b: u32) -> Command {
        Command::Move {
            from_label: a,
            to_label: b,
        }
    }

    #[test]
    fn parse_move_accepts_every_syntax() {
        let cases: [(&str, Command); 11] = [
            ("1 3", mv(1, 3)),
            ("2 1", mv(2, 1)),
            ("  1   3  ", mv(1, 3)),
            ("13", mv(1, 3)),
            ("31", mv(3, 1)),
            ("1 -> 3", mv(1, 3)),
            ("1->3", mv(1, 3)),
            ("  1->3  ", mv(1, 3)),
            ("1 ->3", mv(1, 3)),
            ("1-> 3", mv(1, 3)),
            ("3 -> 1", mv(3, 1)),
        ];
        for (line, expected) in cases {
            assert_eq!(parse(line), expected, "line {line:?}");
        }
    }

    #[test]
    fn parse_arrow_move_invalid() {
        for line in ["1 -> 1", "4 -> 1", "1 -> wat", "-> 3"] {
            assert!(matches!(parse(line), Command::Error(_)), "line {line:?}");
        }
    }

    #[test]
    fn parse_move_invalid() {
        for line in ["1 1", "11", "4 1", "1 4", "0 3", "44"] {
            assert!(matches!(parse(line), Command::Error(_)), "line {line:?}");
        }
    }

    #[test]
    fn parse_relabel_valid() {
        let cases: [(&str, [u32; 3]); 4] = [
            ("relabel 1 2 3", [1, 2, 3]),
            ("relabel 2 1 3", [2, 1, 3]),
            ("relabel 3 2 1", [3, 2, 1]),
            ("RELABEL 1 3 2", [1, 3, 2]),
        ];
        for (line, labels) in cases {
            assert_eq!(parse(line), Command::Relabel(labels), "line {line:?}");
        }
    }

    #[test]
    fn parse_relabel_invalid() {
        for line in [
            "relabel",
            "relabel 1 2",
            "relabel 1 2 3 4",
            "relabel 1 1 1",
            "relabel 1 2 4",
            "relabel a b c",
        ] {
            assert!(matches!(parse(line), Command::Error(_)), "line {line:?}");
        }
    }

    #[test]
    fn parse_recipes() {
        assert_eq!(parse("save foo"), Command::Save("foo".to_string()));
        assert_eq!(
            parse("save my 3-disc solve"),
            Command::Save("my 3-disc solve".to_string())
        );
        assert!(matches!(parse("save"), Command::Error(_)));
        assert_eq!(parse("apply foo"), Command::Apply("foo".to_string()));
        assert!(matches!(parse("apply"), Command::Error(_)));
        assert_eq!(parse("show foo"), Command::Show("foo".to_string()));
        assert!(matches!(parse("show"), Command::Error(_)));
    }

    #[test]
    fn parse_list_help_quit_empty() {
        assert_eq!(parse("list"), Command::List);
        assert_eq!(parse("LIST"), Command::List);
        for l in ["help", "h", "?", "HELP"] {
            assert_eq!(parse(l), Command::Help, "{l:?}");
        }
        for l in ["quit", "q", "exit", "QUIT", "Q"] {
            assert_eq!(parse(l), Command::Quit, "{l:?}");
        }
        for l in ["", "   ", "\t", "\n"] {
            assert_eq!(parse(l), Command::Empty, "{l:?}");
        }
    }

    #[test]
    fn parse_garbage() {
        for l in [
            "wat",
            "move 1 3",
            "1 2 3",
            "relabel-now 1 2 3",
            "saveapply foo",
        ] {
            assert!(matches!(parse(l), Command::Error(_)), "{l:?}");
        }
    }
}
