//! Variable analysis: free, bound, binding variables.

use std::collections::HashSet;
use super::term::{Term, fold};

/// Return the set of free variables in a term.
pub fn free_vars(term: &Term) -> HashSet<String> {
    fold(
        term,
        &|name| {
            let mut s = HashSet::new();
            s.insert(name.to_string());
            s
        },
        &|param, mut body| {
            body.remove(param);
            body
        },
        &|f, a| &f | &a,
    )
}

/// Return the set of variables that appear bound in a term.
pub fn bound_vars(term: &Term) -> HashSet<String> {
    bound_vars_inner(term, &HashSet::new())
}

fn bound_vars_inner(term: &Term, scope: &HashSet<String>) -> HashSet<String> {
    match term {
        Term::Var(name) => {
            if scope.contains(name) {
                let mut s = HashSet::new();
                s.insert(name.clone());
                s
            } else {
                HashSet::new()
            }
        }
        Term::Abs { param, body } => {
            let mut new_scope = scope.clone();
            new_scope.insert(param.clone());
            bound_vars_inner(body, &new_scope)
        }
        Term::App { func, arg } => {
            &bound_vars_inner(func, scope) | &bound_vars_inner(arg, scope)
        }
    }
}

/// Return the set of binding variables (lambda parameters) in a term.
pub fn binding_vars(term: &Term) -> HashSet<String> {
    fold(
        term,
        &|_| HashSet::new(),
        &|param, mut body| {
            body.insert(param.to_string());
            body
        },
        &|f, a| &f | &a,
    )
}

/// Return true if the term has no free variables.
pub fn is_closed(term: &Term) -> bool {
    free_vars(term).is_empty()
}

#[cfg(test)]
mod tests {
    use super::*;

    // -- free_vars -----------------------------------------------------------

    #[test]
    fn free_vars_single_var() {
        let t = Term::var("x");
        assert_eq!(free_vars(&t), HashSet::from(["x".to_string()]));
    }

    #[test]
    fn free_vars_bound_only() {
        // λx.x -> no free vars
        let t = Term::abs("x", Term::var("x"));
        assert!(free_vars(&t).is_empty());
    }

    #[test]
    fn free_vars_mixed() {
        // λx.(x y) -> {y}
        let t = Term::abs("x", Term::app(Term::var("x"), Term::var("y")));
        assert_eq!(free_vars(&t), HashSet::from(["y".to_string()]));
    }

    #[test]
    fn free_vars_app() {
        // (x y) -> {x, y}
        let t = Term::app(Term::var("x"), Term::var("y"));
        assert_eq!(
            free_vars(&t),
            HashSet::from(["x".to_string(), "y".to_string()])
        );
    }

    #[test]
    fn free_vars_nested_abs() {
        // λx.λy.z -> {z}
        let t = Term::abs("x", Term::abs("y", Term::var("z")));
        assert_eq!(free_vars(&t), HashSet::from(["z".to_string()]));
    }

    // -- bound_vars ----------------------------------------------------------

    #[test]
    fn bound_vars_single_var() {
        let t = Term::var("x");
        assert!(bound_vars(&t).is_empty());
    }

    #[test]
    fn bound_vars_identity() {
        // λx.x -> {x}
        let t = Term::abs("x", Term::var("x"));
        assert_eq!(bound_vars(&t), HashSet::from(["x".to_string()]));
    }

    #[test]
    fn bound_vars_unused_param() {
        // λx.y -> {} (x is binding but not bound)
        let t = Term::abs("x", Term::var("y"));
        assert!(bound_vars(&t).is_empty());
    }

    #[test]
    fn bound_vars_mixed() {
        // λx.(x y) -> {x}
        let t = Term::abs("x", Term::app(Term::var("x"), Term::var("y")));
        assert_eq!(bound_vars(&t), HashSet::from(["x".to_string()]));
    }

    // -- binding_vars --------------------------------------------------------

    #[test]
    fn binding_vars_no_abs() {
        let t = Term::app(Term::var("x"), Term::var("y"));
        assert!(binding_vars(&t).is_empty());
    }

    #[test]
    fn binding_vars_single() {
        let t = Term::abs("x", Term::var("x"));
        assert_eq!(binding_vars(&t), HashSet::from(["x".to_string()]));
    }

    #[test]
    fn binding_vars_nested() {
        // λx.λy.(x y) -> {x, y}
        let t = Term::abs("x", Term::abs("y", Term::app(Term::var("x"), Term::var("y"))));
        assert_eq!(
            binding_vars(&t),
            HashSet::from(["x".to_string(), "y".to_string()])
        );
    }

    // -- is_closed -----------------------------------------------------------

    #[test]
    fn is_closed_true() {
        // λx.x
        let t = Term::abs("x", Term::var("x"));
        assert!(is_closed(&t));
    }

    #[test]
    fn is_closed_false() {
        // λx.y
        let t = Term::abs("x", Term::var("y"));
        assert!(!is_closed(&t));
    }

    #[test]
    fn is_closed_free_var() {
        let t = Term::var("x");
        assert!(!is_closed(&t));
    }
}
