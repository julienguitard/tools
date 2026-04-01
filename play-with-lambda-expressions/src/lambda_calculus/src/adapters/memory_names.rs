//! In-memory named term registry with standard library preloaded.

use std::collections::HashMap;
use crate::domain::{Term, parse};
use crate::ports::NameRegistry;

const STANDARD_LIBRARY: &[(&str, &str)] = &[
    ("I", r"\x.x"),
    ("K", r"\x.\y.x"),
    ("S", r"\x.\y.\z.((x z) (y z))"),
    ("Y", r"\f.(\x.(f (x x)) \x.(f (x x)))"),
    ("OMEGA", r"(\x.(x x) \x.(x x))"),
    ("TRUE", r"\x.\y.x"),
    ("FALSE", r"\x.\y.y"),
    ("AND", r"\p.\q.((p q) p)"),
    ("OR", r"\p.\q.((p p) q)"),
    ("NOT", r"\p.((p \x.\y.y) \x.\y.x)"),
    ("ZERO", r"\f.\x.x"),
    ("SUCC", r"\n.\f.\x.(f ((n f) x))"),
    ("PLUS", r"\m.\n.\f.\x.((m f) ((n f) x))"),
    ("MULT", r"\m.\n.\f.(m (n f))"),
];

/// Dict-backed name registry, preloaded with standard combinators.
pub struct InMemoryNameRegistry {
    names: HashMap<String, Term>,
}

impl InMemoryNameRegistry {
    pub fn new() -> Self {
        let mut names = HashMap::new();
        for &(name, source) in STANDARD_LIBRARY {
            if let Ok(term) = parse(source, None) {
                names.insert(name.to_string(), term);
            }
        }
        Self { names }
    }
}

impl NameRegistry for InMemoryNameRegistry {
    fn bind(&mut self, name: &str, term: Term) {
        self.names.insert(name.to_string(), term);
    }

    fn lookup(&self, name: &str) -> Option<&Term> {
        self.names.get(name)
    }

    fn all_names(&self) -> HashMap<String, Term> {
        self.names.clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn standard_library_loaded() {
        let reg = InMemoryNameRegistry::new();
        assert_eq!(reg.all_names().len(), 14);
    }

    #[test]
    fn lookup_identity() {
        let reg = InMemoryNameRegistry::new();
        let i = reg.lookup("I").unwrap();
        assert_eq!(i.to_string(), "λx.x");
    }

    #[test]
    fn bind_and_lookup() {
        let mut reg = InMemoryNameRegistry::new();
        reg.bind("FOO", Term::var("bar"));
        assert_eq!(reg.lookup("FOO").unwrap(), &Term::var("bar"));
    }

    #[test]
    fn overwrite() {
        let mut reg = InMemoryNameRegistry::new();
        reg.bind("I", Term::var("overwritten"));
        assert_eq!(reg.lookup("I").unwrap(), &Term::var("overwritten"));
    }

    #[test]
    fn lookup_missing() {
        let reg = InMemoryNameRegistry::new();
        assert!(reg.lookup("NONEXISTENT").is_none());
    }

    #[test]
    fn all_names_is_copy() {
        let mut reg = InMemoryNameRegistry::new();
        let snapshot = reg.all_names();
        reg.bind("NEW", Term::var("x"));
        assert!(!snapshot.contains_key("NEW"));
    }
}
