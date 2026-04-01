//! Complexity metrics with phantom type tags.

use std::collections::HashSet;
use std::marker::PhantomData;
use super::term::{Term, fold};

// -- Tagged measurement types ------------------------------------------------

/// A tagged complexity measurement. `T` is a phantom type tag.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Meter<T> {
    pub value: usize,
    _marker: PhantomData<T>,
}

impl<T> Meter<T> {
    pub fn new(value: usize) -> Self {
        Self { value, _marker: PhantomData }
    }
}

/// A tagged ratio measurement. `T` is a phantom type tag.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Ratio<T> {
    pub numerator: usize,
    pub denominator: usize,
    _marker: PhantomData<T>,
}

impl<T> Ratio<T> {
    pub fn new(numerator: usize, denominator: usize) -> Self {
        Self { numerator, denominator, _marker: PhantomData }
    }
}

// -- Phantom type tags (zero-sized, never instantiated) ----------------------

/// Total AST node count.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Size;
/// AST tree height.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Depth;
/// Maximum lambda-binder nesting.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AbsDepth;
/// Number of distinct subterms.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SubtermCount;
/// Maximum distance from a variable to its binder.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DeBruijnHeight;
/// Ratio of bound to total variable occurrences.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BindingDensity;

// -- Metric functions --------------------------------------------------------

/// Total number of AST nodes (Var + Abs + App).
pub fn term_size(term: &Term) -> Meter<Size> {
    Meter::new(fold(
        term,
        &|_| 1usize,
        &|_, body| 1 + body,
        &|f, a| 1 + f + a,
    ))
}

/// Height of the AST tree.
pub fn term_depth(term: &Term) -> Meter<Depth> {
    Meter::new(fold(
        term,
        &|_| 0usize,
        &|_, body| 1 + body,
        &|f, a| 1 + f.max(a),
    ))
}

/// Maximum nesting depth of lambda binders.
pub fn abs_depth(term: &Term) -> Meter<AbsDepth> {
    Meter::new(fold(
        term,
        &|_| 0usize,
        &|_, body| 1 + body,
        &|f, a| f.max(a),
    ))
}

/// Set of all distinct subterms (including the term itself).
fn subterms(term: &Term) -> HashSet<Term> {
    match term {
        Term::Var(_) => {
            let mut s = HashSet::new();
            s.insert(term.clone());
            s
        }
        Term::Abs { body, .. } => {
            let mut s = subterms(body);
            s.insert(term.clone());
            s
        }
        Term::App { func, arg } => {
            let mut s = subterms(func);
            s.extend(subterms(arg));
            s.insert(term.clone());
            s
        }
    }
}

/// Number of distinct subterms.
pub fn subterm_count(term: &Term) -> Meter<SubtermCount> {
    Meter::new(subterms(term).len())
}

/// Maximum distance from a variable occurrence to its binder.
pub fn de_bruijn_height(term: &Term) -> Meter<DeBruijnHeight> {
    Meter::new(de_bruijn_inner(term, &std::collections::HashMap::new(), 0))
}

fn de_bruijn_inner(
    term: &Term,
    binder_depth: &std::collections::HashMap<String, usize>,
    depth: usize,
) -> usize {
    match term {
        Term::Var(name) => {
            if let Some(&bd) = binder_depth.get(name) {
                depth - bd
            } else {
                0
            }
        }
        Term::Abs { param, body } => {
            let mut new_depth = binder_depth.clone();
            new_depth.insert(param.clone(), depth + 1);
            de_bruijn_inner(body, &new_depth, depth + 1)
        }
        Term::App { func, arg } => {
            de_bruijn_inner(func, binder_depth, depth)
                .max(de_bruijn_inner(arg, binder_depth, depth))
        }
    }
}

/// Ratio of bound variable occurrences to total variable occurrences.
pub fn binding_density(term: &Term) -> Ratio<BindingDensity> {
    let (total, bound) = var_counts(term, &HashSet::new());
    Ratio::new(bound, total)
}

fn var_counts(term: &Term, scope: &HashSet<String>) -> (usize, usize) {
    match term {
        Term::Var(name) => {
            if scope.contains(name) {
                (1, 1)
            } else {
                (1, 0)
            }
        }
        Term::Abs { param, body } => {
            let mut new_scope = scope.clone();
            new_scope.insert(param.clone());
            var_counts(body, &new_scope)
        }
        Term::App { func, arg } => {
            let (ft, fb) = var_counts(func, scope);
            let (at, ab) = var_counts(arg, scope);
            (ft + at, fb + ab)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::parse;

    fn p(src: &str) -> Term {
        parse(src, None).unwrap()
    }

    // -- term_size -----------------------------------------------------------

    #[test]
    fn size_var() {
        assert_eq!(term_size(&Term::var("x")), Meter::new(1));
    }

    #[test]
    fn size_abs() {
        // λx.x -> 2 nodes
        assert_eq!(term_size(&p(r"\x.x")), Meter::new(2));
    }

    #[test]
    fn size_app() {
        // (f x) -> 3 nodes
        assert_eq!(term_size(&p("(f x)")), Meter::new(3));
    }

    #[test]
    fn size_complex() {
        // λx.λy.(x y) -> 5 nodes
        assert_eq!(term_size(&p(r"\x.\y.(x y)")), Meter::new(5));
    }

    // -- term_depth ----------------------------------------------------------

    #[test]
    fn depth_var() {
        assert_eq!(term_depth(&Term::var("x")), Meter::new(0));
    }

    #[test]
    fn depth_abs() {
        assert_eq!(term_depth(&p(r"\x.x")), Meter::new(1));
    }

    #[test]
    fn depth_nested() {
        // λx.λy.(x y) -> depth 3
        assert_eq!(term_depth(&p(r"\x.\y.(x y)")), Meter::new(3));
    }

    // -- abs_depth -----------------------------------------------------------

    #[test]
    fn abs_depth_no_abs() {
        assert_eq!(abs_depth(&p("(x y)")), Meter::new(0));
    }

    #[test]
    fn abs_depth_single() {
        assert_eq!(abs_depth(&p(r"\x.x")), Meter::new(1));
    }

    #[test]
    fn abs_depth_nested() {
        assert_eq!(abs_depth(&p(r"\x.\y.x")), Meter::new(2));
    }

    // -- subterm_count -------------------------------------------------------

    #[test]
    fn subterm_count_var() {
        assert_eq!(subterm_count(&Term::var("x")), Meter::new(1));
    }

    #[test]
    fn subterm_count_app_same() {
        // (x x) -> {x, (x x)} = 2
        assert_eq!(subterm_count(&p("(x x)")), Meter::new(2));
    }

    #[test]
    fn subterm_count_app_diff() {
        // (x y) -> {x, y, (x y)} = 3
        assert_eq!(subterm_count(&p("(x y)")), Meter::new(3));
    }

    // -- de_bruijn_height ----------------------------------------------------

    #[test]
    fn debruijn_free_var() {
        assert_eq!(de_bruijn_height(&Term::var("x")), Meter::new(0));
    }

    #[test]
    fn debruijn_identity() {
        // λx.x -> distance 0 (immediately bound)
        assert_eq!(de_bruijn_height(&p(r"\x.x")), Meter::new(0));
    }

    #[test]
    fn debruijn_nested() {
        // λx.λy.x -> distance 1 (one lambda between x and its binder)
        assert_eq!(de_bruijn_height(&p(r"\x.\y.x")), Meter::new(1));
    }

    // -- binding_density -----------------------------------------------------

    #[test]
    fn density_all_free() {
        // (x y) -> 0 bound / 2 total
        assert_eq!(binding_density(&p("(x y)")), Ratio::new(0, 2));
    }

    #[test]
    fn density_all_bound() {
        // λx.x -> 1 bound / 1 total
        assert_eq!(binding_density(&p(r"\x.x")), Ratio::new(1, 1));
    }

    #[test]
    fn density_mixed() {
        // λx.(x y) -> 1 bound / 2 total
        assert_eq!(binding_density(&p(r"\x.(x y)")), Ratio::new(1, 2));
    }
}
