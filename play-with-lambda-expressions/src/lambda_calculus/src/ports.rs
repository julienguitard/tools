//! Abstract traits for IO boundaries (ports).

use std::collections::HashMap;
use crate::domain::Term;

/// Generates lambda terms (e.g., randomly).
pub trait TermGenerator {
    fn generate(&mut self, max_depth: usize) -> Term;
}

/// Session-scoped named term storage.
pub trait NameRegistry {
    fn bind(&mut self, name: &str, term: Term);
    fn lookup(&self, name: &str) -> Option<&Term>;
    fn all_names(&self) -> HashMap<String, Term>;
}

/// REPL interaction abstraction.
pub trait UserInterface {
    fn read_input(&mut self) -> Option<String>;
    fn display(&mut self, text: &str);
    fn display_error(&mut self, text: &str);
}
