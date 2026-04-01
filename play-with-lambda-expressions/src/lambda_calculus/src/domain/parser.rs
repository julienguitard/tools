//! Recursive-descent parser for strict lambda calculus syntax.

use std::collections::HashMap;
use super::term::Term;

/// Syntax error with position for display.
#[derive(Debug, Clone)]
pub struct ParseError {
    pub message: String,
    pub position: usize,
}

/// Successful parse with optional shadowing metadata.
#[derive(Debug, Clone)]
pub struct ParseResult {
    pub term: Term,
    pub renames: Vec<(String, String)>,
}

/// Parse a lambda calculus expression from a string.
pub fn parse(source: &str, names: Option<&HashMap<String, Term>>) -> Result<Term, ParseError> {
    let (term, _) = run_parser(source, names)?;
    Ok(term)
}

/// Parse a lambda expression, returning rename metadata.
pub fn parse_with_info(
    source: &str,
    names: Option<&HashMap<String, Term>>,
) -> Result<ParseResult, ParseError> {
    let (term, renames) = run_parser(source, names)?;
    Ok(ParseResult { term, renames })
}

fn run_parser(
    source: &str,
    names: Option<&HashMap<String, Term>>,
) -> Result<(Term, Vec<(String, String)>), ParseError> {
    let source = source.trim();
    if source.is_empty() {
        return Err(ParseError {
            message: "empty input".to_string(),
            position: 0,
        });
    }
    let empty = HashMap::new();
    let names = names.unwrap_or(&empty);
    let mut parser = Parser::new(source, names);
    let term = parser.parse_term()?;
    parser.skip_whitespace();
    if parser.pos < parser.chars.len() {
        let trailing: String = parser.chars[parser.pos..].iter().collect();
        return Err(ParseError {
            message: format!("unexpected trailing content: '{}'", trailing),
            position: parser.pos,
        });
    }
    Ok((term, parser.renames))
}

// -- Internal parser ---------------------------------------------------------

struct Parser<'a> {
    chars: Vec<char>,
    pos: usize,
    names: &'a HashMap<String, Term>,
    scope: HashMap<String, String>,
    renames: Vec<(String, String)>,
}

impl<'a> Parser<'a> {
    fn new(source: &str, names: &'a HashMap<String, Term>) -> Self {
        Self {
            chars: source.chars().collect(),
            pos: 0,
            names,
            scope: HashMap::new(),
            renames: Vec::new(),
        }
    }

    fn parse_term(&mut self) -> Result<Term, ParseError> {
        self.skip_whitespace();
        match self.peek() {
            None => Err(ParseError {
                message: "unexpected end of input".to_string(),
                position: self.pos,
            }),
            Some('\\') | Some('λ') => self.parse_abs(),
            Some('(') => self.parse_paren(),
            Some(ch) if ch.is_alphabetic() || ch == '_' => Ok(self.parse_var_or_name()),
            Some(ch) => Err(ParseError {
                message: format!("unexpected character: '{}'", ch),
                position: self.pos,
            }),
        }
    }

    fn parse_abs(&mut self) -> Result<Term, ParseError> {
        self.advance(); // consume λ or \
        self.skip_whitespace();

        // Parse parameter name.
        match self.peek() {
            Some(ch) if ch.is_alphabetic() || ch == '_' => {}
            _ => {
                return Err(ParseError {
                    message: "expected parameter name after λ".to_string(),
                    position: self.pos,
                });
            }
        }
        let param_name = self.parse_identifier();

        // Detect shadowing and rename if needed.
        let actual_param = if self.scope.contains_key(&param_name) {
            let in_scope: std::collections::HashSet<String> =
                self.scope.values().cloned().collect();
            let fresh = fresh_var(&param_name, &in_scope);
            if fresh != param_name {
                self.renames.push((param_name.clone(), fresh.clone()));
            }
            fresh
        } else {
            param_name.clone()
        };

        self.skip_whitespace();
        if self.peek() != Some('.') {
            return Err(ParseError {
                message: "expected '.' after parameter".to_string(),
                position: self.pos,
            });
        }
        self.advance(); // consume .

        // Push scope, parse body, pop scope.
        let old_binding = self.scope.get(&param_name).cloned();
        self.scope.insert(param_name.clone(), actual_param.clone());
        let body = self.parse_term();
        if let Some(old) = old_binding {
            self.scope.insert(param_name, old);
        } else {
            self.scope.remove(&param_name);
        }

        Ok(Term::abs(&actual_param, body?))
    }

    fn parse_paren(&mut self) -> Result<Term, ParseError> {
        self.advance(); // consume (
        let first = self.parse_term()?;

        self.skip_whitespace();
        if self.peek() == Some(')') {
            // Grouping parentheses.
            self.advance();
            return Ok(first);
        }

        // Application: parse second term.
        let second = self.parse_term()?;

        self.skip_whitespace();
        if self.peek() != Some(')') {
            return Err(ParseError {
                message: "expected ')' to close application".to_string(),
                position: self.pos,
            });
        }
        self.advance(); // consume )
        Ok(Term::app(first, second))
    }

    fn parse_var_or_name(&mut self) -> Term {
        let name = self.parse_identifier();
        if let Some(actual) = self.scope.get(&name) {
            return Term::var(actual);
        }
        if let Some(term) = self.names.get(&name) {
            return term.clone();
        }
        Term::var(&name)
    }

    fn parse_identifier(&mut self) -> String {
        let start = self.pos;
        while let Some(ch) = self.peek() {
            if ch.is_alphanumeric() || ch == '_' || ch == '\'' {
                self.advance();
            } else {
                break;
            }
        }
        self.chars[start..self.pos].iter().collect()
    }

    fn skip_whitespace(&mut self) {
        while let Some(ch) = self.peek() {
            if ch.is_whitespace() {
                self.advance();
            } else {
                break;
            }
        }
    }

    fn peek(&self) -> Option<char> {
        self.chars.get(self.pos).copied()
    }

    fn advance(&mut self) -> char {
        let ch = self.chars[self.pos];
        self.pos += 1;
        ch
    }
}

/// Generate a fresh variable name by appending primes until not in `avoid`.
fn fresh_var(name: &str, avoid: &std::collections::HashSet<String>) -> String {
    let mut candidate = name.to_string();
    while avoid.contains(&candidate) {
        candidate.push('\'');
    }
    candidate
}

#[cfg(test)]
mod tests {
    use super::*;

    // -- Basic parsing -------------------------------------------------------

    #[test]
    fn parse_var() {
        let t = parse("x", None).unwrap();
        assert_eq!(t, Term::var("x"));
    }

    #[test]
    fn parse_abs_backslash() {
        let t = parse(r"\x.x", None).unwrap();
        assert_eq!(t, Term::abs("x", Term::var("x")));
    }

    #[test]
    fn parse_abs_lambda() {
        let t = parse("λx.x", None).unwrap();
        assert_eq!(t, Term::abs("x", Term::var("x")));
    }

    #[test]
    fn parse_app() {
        let t = parse("(f x)", None).unwrap();
        assert_eq!(t, Term::app(Term::var("f"), Term::var("x")));
    }

    #[test]
    fn parse_grouping() {
        let t = parse("(x)", None).unwrap();
        assert_eq!(t, Term::var("x"));
    }

    #[test]
    fn parse_nested_abs() {
        let t = parse(r"\x.\y.(x y)", None).unwrap();
        assert_eq!(
            t,
            Term::abs("x", Term::abs("y", Term::app(Term::var("x"), Term::var("y"))))
        );
    }

    #[test]
    fn parse_complex_application() {
        // ((λx.x a) b)
        let t = parse(r"((\x.x a) b)", None).unwrap();
        assert_eq!(
            t,
            Term::app(
                Term::app(Term::abs("x", Term::var("x")), Term::var("a")),
                Term::var("b"),
            )
        );
    }

    #[test]
    fn parse_with_whitespace() {
        let t = parse("  \\x . x  ", None).unwrap();
        assert_eq!(t, Term::abs("x", Term::var("x")));
    }

    #[test]
    fn parse_multichar_var() {
        let t = parse("foo", None).unwrap();
        assert_eq!(t, Term::var("foo"));
    }

    #[test]
    fn parse_underscore_var() {
        let t = parse("_x", None).unwrap();
        assert_eq!(t, Term::var("_x"));
    }

    // -- Name resolution -----------------------------------------------------

    #[test]
    fn parse_with_names() {
        let mut names = HashMap::new();
        names.insert("I".to_string(), Term::abs("x", Term::var("x")));
        let t = parse("(I a)", Some(&names)).unwrap();
        assert_eq!(
            t,
            Term::app(Term::abs("x", Term::var("x")), Term::var("a"))
        );
    }

    // -- Shadowing -----------------------------------------------------------

    #[test]
    fn shadowing_renames_inner() {
        // \c.\c.c -> inner c renamed to c'
        let result = parse_with_info(r"\c.\c.c", None).unwrap();
        assert_eq!(
            result.term,
            Term::abs("c", Term::abs("c'", Term::var("c'")))
        );
        assert_eq!(result.renames, vec![("c".to_string(), "c'".to_string())]);
    }

    #[test]
    fn shadowing_triple() {
        // \a.\a.\a.a -> middle a renamed to a', third a takes back "a"
        // (a' is in scope, not a, so a is fresh again)
        let result = parse_with_info(r"\a.\a.\a.a", None).unwrap();
        assert_eq!(
            result.term,
            Term::abs("a", Term::abs("a'", Term::abs("a", Term::var("a"))))
        );
        assert_eq!(result.renames, vec![("a".to_string(), "a'".to_string())]);
    }

    // -- Parse errors --------------------------------------------------------

    #[test]
    fn error_empty_input() {
        let err = parse("", None).unwrap_err();
        assert_eq!(err.message, "empty input");
    }

    #[test]
    fn error_unexpected_char() {
        let err = parse("123", None).unwrap_err();
        assert!(err.message.contains("unexpected character"));
    }

    #[test]
    fn error_missing_dot() {
        let err = parse(r"\x x", None).unwrap_err();
        assert!(err.message.contains("expected '.'"));
    }

    #[test]
    fn error_unclosed_paren() {
        let err = parse("(x y", None).unwrap_err();
        assert!(err.message.contains("expected ')'"));
    }

    #[test]
    fn error_trailing_content() {
        let err = parse("x y", None).unwrap_err();
        assert!(err.message.contains("trailing content"));
    }

    // -- Round trips ---------------------------------------------------------

    #[test]
    fn round_trip_var() {
        let t = Term::var("x");
        assert_eq!(parse(&t.to_string(), None).unwrap(), t);
    }

    #[test]
    fn round_trip_abs() {
        let t = Term::abs("x", Term::abs("y", Term::app(Term::var("x"), Term::var("y"))));
        assert_eq!(parse(&t.to_string(), None).unwrap(), t);
    }

    #[test]
    fn round_trip_app() {
        let t = Term::app(
            Term::abs("x", Term::var("x")),
            Term::app(Term::var("a"), Term::var("b")),
        );
        assert_eq!(parse(&t.to_string(), None).unwrap(), t);
    }
}
