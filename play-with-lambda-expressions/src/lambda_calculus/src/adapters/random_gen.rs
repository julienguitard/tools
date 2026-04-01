//! Random closed-term generator.

use rand::Rng;
use crate::domain::Term;
use crate::ports::TermGenerator;

/// Generates random closed lambda terms via recursive construction.
///
/// Guarantees that every generated term is closed (no free variables)
/// by tracking in-scope bindings and forcing abstractions when the
/// scope is empty.
pub struct RandomTermGenerator {
    rng: rand::rngs::ThreadRng,
}

impl RandomTermGenerator {
    pub fn new() -> Self {
        Self { rng: rand::rng() }
    }

    fn build(&mut self, depth: usize, scope: &[String]) -> Term {
        if scope.is_empty() {
            // No variables in scope — must introduce one via Abs.
            let fresh = Self::fresh_param(scope);
            let mut new_scope = scope.to_vec();
            new_scope.push(fresh.clone());
            let body = self.build(depth.saturating_sub(1), &new_scope);
            return Term::abs(&fresh, body);
        }

        if depth == 0 {
            // Depth exhausted — return a variable from scope.
            let idx = self.rng.random_range(0..scope.len());
            return Term::var(&scope[idx]);
        }

        // Weighted choice: Var(1), Abs(2), App(3)
        let roll: f64 = self.rng.random::<f64>() * 6.0;
        if roll < 1.0 {
            // Var
            let idx = self.rng.random_range(0..scope.len());
            Term::var(&scope[idx])
        } else if roll < 3.0 {
            // Abs
            let fresh = Self::fresh_param(scope);
            let mut new_scope = scope.to_vec();
            new_scope.push(fresh.clone());
            let body = self.build(depth - 1, &new_scope);
            Term::abs(&fresh, body)
        } else {
            // App
            let func = self.build(depth - 1, scope);
            let arg = self.build(depth - 1, scope);
            Term::app(func, arg)
        }
    }

    fn fresh_param(scope: &[String]) -> String {
        let used: std::collections::HashSet<&str> =
            scope.iter().map(|s| s.as_str()).collect();
        for suffix_count in 0..10 {
            let suffix: String = std::iter::repeat('\'').take(suffix_count).collect();
            for ch in 'a'..='z' {
                let name = format!("{}{}", ch, suffix);
                if !used.contains(name.as_str()) {
                    return name;
                }
            }
        }
        format!("v{}", scope.len())
    }
}

impl TermGenerator for RandomTermGenerator {
    fn generate(&mut self, max_depth: usize) -> Term {
        self.build(max_depth, &[])
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::is_closed;

    #[test]
    fn generated_terms_are_closed() {
        let mut generator = RandomTermGenerator::new();
        for depth in 1..=5 {
            for _ in 0..20 {
                let term = generator.generate(depth);
                assert!(is_closed(&term), "generated term is not closed: {}", term);
            }
        }
    }

    #[test]
    fn fresh_param_avoids_used() {
        let scope = vec!["a".to_string(), "b".to_string()];
        let fresh = RandomTermGenerator::fresh_param(&scope);
        assert!(!scope.contains(&fresh));
    }

    #[test]
    fn fresh_param_empty_scope() {
        let fresh = RandomTermGenerator::fresh_param(&[]);
        assert_eq!(fresh, "a");
    }
}
