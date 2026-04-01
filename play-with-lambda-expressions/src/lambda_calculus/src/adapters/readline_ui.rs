//! Terminal-based REPL interface with rustyline support.

use rustyline::error::ReadlineError;
use rustyline::DefaultEditor;
use crate::ports::UserInterface;

/// Interactive terminal UI with history and tab completion.
pub struct ReadlineUI {
    editor: DefaultEditor,
}

impl ReadlineUI {
    pub fn new() -> Self {
        let editor = DefaultEditor::new().expect("failed to create readline editor");
        Self { editor }
    }
}

impl UserInterface for ReadlineUI {
    fn read_input(&mut self) -> Option<String> {
        match self.editor.readline("λ> ") {
            Ok(line) => {
                let _ = self.editor.add_history_entry(&line);
                Some(line)
            }
            Err(ReadlineError::Interrupted | ReadlineError::Eof) => {
                println!();
                None
            }
            Err(_) => None,
        }
    }

    fn display(&mut self, text: &str) {
        println!("{}", text);
    }

    fn display_error(&mut self, text: &str) {
        println!("Error: {}", text);
    }
}
