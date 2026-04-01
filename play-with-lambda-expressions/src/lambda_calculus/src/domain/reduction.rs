//! Substitution, alpha-renaming, and beta-reduction.

use std::collections::HashSet;
use super::term::Term;
use super::variables::free_vars;

/// Generate a fresh variable name by appending primes until not in `avoid`.
fn fresh_var(name: &str, avoid: &HashSet<String>) -> String {
    let mut candidate = name.to_string();
    while avoid.contains(&candidate) {
        candidate.push('\'');
    }
    candidate
}

/// Capture-avoiding substitution: `term[var := replacement]`.
pub fn substitute(term: &Term, var: &str, replacement: &Term) -> Term {
    match term {
        Term::Var(name) => {
            if name == var {
                replacement.clone()
            } else {
                term.clone()
            }
        }
        Term::App { func, arg } => Term::app(
            substitute(func, var, replacement),
            substitute(arg, var, replacement),
        ),
        Term::Abs { param, body } => {
            if param == var {
                // Shadowed — var is rebound, no substitution in body.
                term.clone()
            } else {
                let free_in_replacement = free_vars(replacement);
                if !free_in_replacement.contains(param) {
                    Term::abs(param, substitute(body, var, replacement))
                } else {
                    // Capture would occur — alpha-rename first.
                    let avoid: HashSet<String> = &free_vars(body) | &free_in_replacement;
                    let fresh = fresh_var(param, &avoid);
                    let renamed_body = substitute(body, param, &Term::var(&fresh));
                    Term::abs(&fresh, substitute(&renamed_body, var, replacement))
                }
            }
        }
    }
}

/// Rename the bound variable of an abstraction.
pub fn alpha_rename(abs_term: &Term, new_name: &str) -> Term {
    match abs_term {
        Term::Abs { param, body } => {
            let renamed_body = substitute(body, param, &Term::var(new_name));
            Term::abs(new_name, renamed_body)
        }
        _ => panic!("alpha_rename called on non-Abs term"),
    }
}

/// Perform one normal-order beta-reduction step.
///
/// Returns `Some(reduced)` or `None` if already in normal form.
pub fn beta_reduce_step(term: &Term) -> Option<Term> {
    match term {
        Term::App { func, arg } => {
            // Check for beta-redex: (λp.body arg)
            if let Term::Abs { param, body } = func.as_ref() {
                return Some(substitute(body, param, arg));
            }
            // Try reducing the function first.
            if let Some(f_reduced) = beta_reduce_step(func) {
                return Some(Term::app(f_reduced, *arg.clone()));
            }
            // Function is in NF — try the argument.
            if let Some(a_reduced) = beta_reduce_step(arg) {
                return Some(Term::app(*func.clone(), a_reduced));
            }
            None
        }
        Term::Abs { param, body } => {
            // Reduce under the lambda.
            beta_reduce_step(body).map(|b| Term::abs(param, b))
        }
        Term::Var(_) => None,
    }
}

/// Fully beta-reduce a term up to a step limit.
///
/// Returns `(final_term, trace, reached_normal_form)`.
/// The trace includes the original term as the first element.
pub fn beta_reduce(term: &Term, max_steps: usize) -> (Term, Vec<Term>, bool) {
    let mut trace = vec![term.clone()];
    let mut current = term.clone();
    for _ in 0..max_steps {
        match beta_reduce_step(&current) {
            None => return (current, trace, true),
            Some(next) => {
                trace.push(next.clone());
                current = next;
            }
        }
    }
    (current, trace, false)
}

/// Return true if no beta-redex exists in the term.
pub fn is_normal_form(term: &Term) -> bool {
    beta_reduce_step(term).is_none()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::parse;

    fn p(src: &str) -> Term {
        parse(src, None).unwrap()
    }

    // -- fresh_var -----------------------------------------------------------

    #[test]
    fn fresh_var_no_conflict() {
        let avoid = HashSet::new();
        assert_eq!(fresh_var("x", &avoid), "x");
    }

    #[test]
    fn fresh_var_one_prime() {
        let avoid = HashSet::from(["x".to_string()]);
        assert_eq!(fresh_var("x", &avoid), "x'");
    }

    #[test]
    fn fresh_var_two_primes() {
        let avoid = HashSet::from(["x".to_string(), "x'".to_string()]);
        assert_eq!(fresh_var("x", &avoid), "x''");
    }

    // -- substitute ----------------------------------------------------------

    #[test]
    fn substitute_var_match() {
        // x[x := a] = a
        let result = substitute(&Term::var("x"), "x", &Term::var("a"));
        assert_eq!(result, Term::var("a"));
    }

    #[test]
    fn substitute_var_no_match() {
        // y[x := a] = y
        let result = substitute(&Term::var("y"), "x", &Term::var("a"));
        assert_eq!(result, Term::var("y"));
    }

    #[test]
    fn substitute_app() {
        // (x y)[x := a] = (a y)
        let t = Term::app(Term::var("x"), Term::var("y"));
        let result = substitute(&t, "x", &Term::var("a"));
        assert_eq!(result, Term::app(Term::var("a"), Term::var("y")));
    }

    #[test]
    fn substitute_shadowed() {
        // (λx.x)[x := a] = λx.x (shadowed)
        let t = Term::abs("x", Term::var("x"));
        let result = substitute(&t, "x", &Term::var("a"));
        assert_eq!(result, Term::abs("x", Term::var("x")));
    }

    #[test]
    fn substitute_no_capture() {
        // (λy.x)[x := a] = λy.a
        let t = Term::abs("y", Term::var("x"));
        let result = substitute(&t, "x", &Term::var("a"));
        assert_eq!(result, Term::abs("y", Term::var("a")));
    }

    #[test]
    fn substitute_capture_avoidance() {
        // (λy.x)[x := y] -> must alpha-rename y to avoid capture
        let t = Term::abs("y", Term::var("x"));
        let result = substitute(&t, "x", &Term::var("y"));
        // Result should be λy'.y (y is substituted, param renamed)
        assert_eq!(result, Term::abs("y'", Term::var("y")));
    }

    // -- alpha_rename --------------------------------------------------------

    #[test]
    fn alpha_rename_basic() {
        // λx.x -> λy.y
        let t = Term::abs("x", Term::var("x"));
        let result = alpha_rename(&t, "y");
        assert_eq!(result, Term::abs("y", Term::var("y")));
    }

    // -- beta_reduce_step ----------------------------------------------------

    #[test]
    fn step_beta_redex() {
        // (λx.x a) -> a
        let t = Term::app(Term::abs("x", Term::var("x")), Term::var("a"));
        assert_eq!(beta_reduce_step(&t), Some(Term::var("a")));
    }

    #[test]
    fn step_normal_form_var() {
        assert_eq!(beta_reduce_step(&Term::var("x")), None);
    }

    #[test]
    fn step_normal_form_abs() {
        // λx.x is in NF
        assert_eq!(beta_reduce_step(&Term::abs("x", Term::var("x"))), None);
    }

    #[test]
    fn step_reduce_func_first() {
        // ((λx.x λy.y) a) -> (λy.y a)
        let inner = Term::app(Term::abs("x", Term::var("x")), Term::abs("y", Term::var("y")));
        let t = Term::app(inner, Term::var("a"));
        let result = beta_reduce_step(&t).unwrap();
        assert_eq!(result, Term::app(Term::abs("y", Term::var("y")), Term::var("a")));
    }

    #[test]
    fn step_reduce_under_abs() {
        // λx.(λy.y a) -> λx.a
        let t = Term::abs(
            "x",
            Term::app(Term::abs("y", Term::var("y")), Term::var("a")),
        );
        assert_eq!(
            beta_reduce_step(&t),
            Some(Term::abs("x", Term::var("a")))
        );
    }

    // -- beta_reduce ---------------------------------------------------------

    #[test]
    fn reduce_identity_application() {
        // (λx.x a) -> a
        let t = p(r"(\x.x a)");
        let (final_term, trace, reached_nf) = beta_reduce(&t, 100);
        assert_eq!(final_term, Term::var("a"));
        assert!(reached_nf);
        assert_eq!(trace.len(), 2); // original + result
    }

    #[test]
    fn reduce_k_combinator() {
        // ((λx.λy.x a) b) -> a
        let t = p(r"((\x.\y.x a) b)");
        let (final_term, _trace, reached_nf) = beta_reduce(&t, 100);
        assert_eq!(final_term, Term::var("a"));
        assert!(reached_nf);
    }

    #[test]
    fn reduce_skk_is_identity() {
        // ((S K) K) applied to a should give a
        // S = λx.λy.λz.((x z) (y z)), K = λx.λy.x
        let t = p(r"((((\x.\y.\z.((x z) (y z)) \x.\y.x) \x.\y.x) a))");
        let (final_term, _trace, reached_nf) = beta_reduce(&t, 100);
        assert_eq!(final_term, Term::var("a"));
        assert!(reached_nf);
    }

    #[test]
    fn reduce_already_nf() {
        let t = Term::var("x");
        let (final_term, trace, reached_nf) = beta_reduce(&t, 100);
        assert_eq!(final_term, Term::var("x"));
        assert!(reached_nf);
        assert_eq!(trace.len(), 1);
    }

    #[test]
    fn reduce_omega_diverges() {
        // (λx.(x x) λx.(x x)) — OMEGA, never reaches NF
        let t = p(r"(\x.(x x) \x.(x x))");
        let (_final_term, _trace, reached_nf) = beta_reduce(&t, 10);
        assert!(!reached_nf);
    }

    // -- is_normal_form ------------------------------------------------------

    #[test]
    fn is_nf_var() {
        assert!(is_normal_form(&Term::var("x")));
    }

    #[test]
    fn is_nf_abs() {
        assert!(is_normal_form(&Term::abs("x", Term::var("x"))));
    }

    #[test]
    fn is_not_nf_redex() {
        let t = Term::app(Term::abs("x", Term::var("x")), Term::var("a"));
        assert!(!is_normal_form(&t));
    }
}
