//! Term ADT, Display (stringify), and fold catamorphism.

use std::fmt;

/// Untyped lambda calculus term.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Term {
    /// A variable reference.
    Var(String),
    /// Lambda abstraction: binds exactly one variable.
    Abs { param: String, body: Box<Term> },
    /// Application: explicit parentheses, no left-associativity sugar.
    App { func: Box<Term>, arg: Box<Term> },
}

impl Term {
    /// Convenience constructor for `Var`.
    pub fn var(name: &str) -> Self {
        Term::Var(name.to_string())
    }

    /// Convenience constructor for `Abs`.
    pub fn abs(param: &str, body: Term) -> Self {
        Term::Abs {
            param: param.to_string(),
            body: Box::new(body),
        }
    }

    /// Convenience constructor for `App`.
    pub fn app(func: Term, arg: Term) -> Self {
        Term::App {
            func: Box::new(func),
            arg: Box::new(arg),
        }
    }
}

/// Catamorphism over the Term ADT.
///
/// Recursively collapses a term by replacing each constructor with a function:
///   - `Var(v)`        -> `on_var(v)`
///   - `Abs(p, body)`  -> `on_abs(p, fold(body))`
///   - `App(f, a)`     -> `on_app(fold(f), fold(a))`
pub fn fold<R>(
    term: &Term,
    on_var: &dyn Fn(&str) -> R,
    on_abs: &dyn Fn(&str, R) -> R,
    on_app: &dyn Fn(R, R) -> R,
) -> R {
    match term {
        Term::Var(name) => on_var(name),
        Term::Abs { param, body } => {
            let body_r = fold(body, on_var, on_abs, on_app);
            on_abs(param, body_r)
        }
        Term::App { func, arg } => {
            let func_r = fold(func, on_var, on_abs, on_app);
            let arg_r = fold(arg, on_var, on_abs, on_app);
            on_app(func_r, arg_r)
        }
    }
}

/// Display a term using lambda notation: `λx.body`, `(f a)`, `x`.
impl fmt::Display for Term {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Term::Var(name) => write!(f, "{}", name),
            Term::Abs { param, body } => write!(f, "λ{}.{}", param, body),
            Term::App { func, arg } => write!(f, "({} {})", func, arg),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // -- Construction and equality -------------------------------------------

    #[test]
    fn var_equality() {
        assert_eq!(Term::var("x"), Term::var("x"));
        assert_ne!(Term::var("x"), Term::var("y"));
    }

    #[test]
    fn abs_equality() {
        let t1 = Term::abs("x", Term::var("x"));
        let t2 = Term::abs("x", Term::var("x"));
        let t3 = Term::abs("y", Term::var("y"));
        assert_eq!(t1, t2);
        assert_ne!(t1, t3);
    }

    #[test]
    fn app_equality() {
        let t1 = Term::app(Term::var("f"), Term::var("x"));
        let t2 = Term::app(Term::var("f"), Term::var("x"));
        let t3 = Term::app(Term::var("f"), Term::var("y"));
        assert_eq!(t1, t2);
        assert_ne!(t1, t3);
    }

    #[test]
    fn nested_term_equality() {
        // λx.(x y) == λx.(x y)
        let t1 = Term::abs("x", Term::app(Term::var("x"), Term::var("y")));
        let t2 = Term::abs("x", Term::app(Term::var("x"), Term::var("y")));
        assert_eq!(t1, t2);
    }

    // -- Display (stringify) -------------------------------------------------

    #[test]
    fn display_var() {
        assert_eq!(Term::var("x").to_string(), "x");
    }

    #[test]
    fn display_abs() {
        let t = Term::abs("x", Term::var("x"));
        assert_eq!(t.to_string(), "λx.x");
    }

    #[test]
    fn display_app() {
        let t = Term::app(Term::var("f"), Term::var("x"));
        assert_eq!(t.to_string(), "(f x)");
    }

    #[test]
    fn display_nested() {
        // λx.λy.(x y)
        let t = Term::abs("x", Term::abs("y", Term::app(Term::var("x"), Term::var("y"))));
        assert_eq!(t.to_string(), "λx.λy.(x y)");
    }

    #[test]
    fn display_complex() {
        // (λx.x a)
        let t = Term::app(Term::abs("x", Term::var("x")), Term::var("a"));
        assert_eq!(t.to_string(), "(λx.x a)");
    }

    // -- Fold ----------------------------------------------------------------

    #[test]
    fn fold_counts_nodes() {
        // λx.(x y) -> 4 nodes: Abs + App + Var(x) + Var(y)
        let t = Term::abs("x", Term::app(Term::var("x"), Term::var("y")));
        let count = fold(
            &t,
            &|_| 1usize,
            &|_, body| 1 + body,
            &|f, a| 1 + f + a,
        );
        assert_eq!(count, 4);
    }

    #[test]
    fn fold_collects_var_names() {
        // (x y) -> {"x", "y"}
        let t = Term::app(Term::var("x"), Term::var("y"));
        let names: Vec<String> = fold(
            &t,
            &|name| vec![name.to_string()],
            &|_, body| body,
            &|mut f, a| {
                f.extend(a);
                f
            },
        );
        assert_eq!(names, vec!["x".to_string(), "y".to_string()]);
    }

    #[test]
    fn fold_stringify_matches_display() {
        let t = Term::abs("x", Term::app(Term::var("x"), Term::var("y")));
        let s = fold(
            &t,
            &|name| name.to_string(),
            &|param, body| format!("λ{}.{}", param, body),
            &|f, a| format!("({} {})", f, a),
        );
        assert_eq!(s, t.to_string());
    }
}
