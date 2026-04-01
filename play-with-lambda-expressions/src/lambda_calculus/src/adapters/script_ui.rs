//! Non-interactive UI for script file execution.

use crate::ports::UserInterface;

/// Reads from a list of statements, skipping comments and blanks.
pub struct ScriptUI {
    lines: Vec<String>,
    pos: usize,
}

impl ScriptUI {
    pub fn new(lines: Vec<String>) -> Self {
        Self { lines, pos: 0 }
    }
}

impl UserInterface for ScriptUI {
    fn read_input(&mut self) -> Option<String> {
        while self.pos < self.lines.len() {
            let line = self.lines[self.pos].trim().to_string();
            self.pos += 1;
            if line.is_empty() || line.starts_with('#') {
                continue;
            }
            return Some(line);
        }
        None
    }

    fn display(&mut self, text: &str) {
        println!("{}", text);
    }

    fn display_error(&mut self, text: &str) {
        println!("Error: {}", text);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_lines_in_order() {
        let mut ui = ScriptUI::new(vec!["first".into(), "second".into()]);
        assert_eq!(ui.read_input(), Some("first".into()));
        assert_eq!(ui.read_input(), Some("second".into()));
        assert_eq!(ui.read_input(), None);
    }

    #[test]
    fn skips_comments() {
        let mut ui = ScriptUI::new(vec!["# comment".into(), "actual".into()]);
        assert_eq!(ui.read_input(), Some("actual".into()));
    }

    #[test]
    fn skips_blank_lines() {
        let mut ui = ScriptUI::new(vec!["".into(), "  ".into(), "actual".into()]);
        assert_eq!(ui.read_input(), Some("actual".into()));
    }

    #[test]
    fn strips_whitespace() {
        let mut ui = ScriptUI::new(vec!["  padded  ".into()]);
        assert_eq!(ui.read_input(), Some("padded".into()));
    }
}
