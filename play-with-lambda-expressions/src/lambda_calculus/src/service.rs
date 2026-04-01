//! Orchestration: depends only on ports, never on adapters.

use crate::domain::{
    Term, parse_with_info, ParseError,
    free_vars, bound_vars, binding_vars,
    beta_reduce_step,
    term_size, term_depth, abs_depth, subterm_count, de_bruijn_height, binding_density,
};
use crate::ports::{TermGenerator, NameRegistry, UserInterface};

/// Runtime configuration for the REPL.
pub struct ReplConfig {
    pub max_steps: usize,
    pub random_depth: usize,
}

impl Default for ReplConfig {
    fn default() -> Self {
        Self {
            max_steps: 100,
            random_depth: 3,
        }
    }
}

/// Interactive REPL for untyped lambda calculus.
///
/// Each handler is a composition of port calls and domain functions.
/// The service contains no domain logic itself.
pub struct ReplService {
    ui: Box<dyn UserInterface>,
    generator: Box<dyn TermGenerator>,
    registry: Box<dyn NameRegistry>,
    config: ReplConfig,
}

impl ReplService {
    pub fn new(
        ui: Box<dyn UserInterface>,
        generator: Box<dyn TermGenerator>,
        registry: Box<dyn NameRegistry>,
        config: ReplConfig,
    ) -> Self {
        Self { ui, generator, registry, config }
    }

    /// Main REPL loop: read -> dispatch -> display -> repeat.
    pub fn run(&mut self) {
        self.ui.display("Lambda calculus REPL. Type :help for commands, :quit to exit.");

        loop {
            let raw = match self.ui.read_input() {
                Some(r) => r,
                None => break,
            };
            let text = raw.trim().to_string();
            if text.is_empty() {
                continue;
            }
            if self.dispatch(&text) {
                break;
            }
        }
    }

    // -- command dispatch -----------------------------------------------------

    /// Route input to the appropriate handler. Returns true if should quit.
    fn dispatch(&mut self, raw: &str) -> bool {
        // :let must be checked before pipe detection because the RHS may
        // contain |> which handle_let evaluates itself.
        if raw.starts_with(':') {
            let parts: Vec<&str> = raw.splitn(2, char::is_whitespace).collect();
            let cmd = parts[0].to_lowercase();
            if cmd == ":let" {
                let arg = if parts.len() > 1 { parts[1] } else { "" };
                self.handle_let(arg);
                return false;
            }
        }

        if raw.contains("|>") {
            if let Some(result) = self.eval_pipe(raw) {
                self.ui.display(&result.to_string());
            }
            return false;
        }

        if !raw.starts_with(':') {
            self.handle_expression(raw);
            return false;
        }

        let parts: Vec<&str> = raw.splitn(2, char::is_whitespace).collect();
        let cmd = parts[0].to_lowercase();
        let arg = if parts.len() > 1 { parts[1] } else { "" };

        match cmd.as_str() {
            ":quit" | ":q" => return true,
            ":help" | ":h" => self.handle_help(),
            ":reduce" => self.handle_reduce(arg),
            ":step" => self.handle_step(arg),
            ":trace" => self.handle_trace(arg),
            ":free" => self.handle_free(arg),
            ":bound" => self.handle_bound(arg),
            ":binding" => self.handle_binding(arg),
            ":random" => self.handle_random(arg),
            ":size" => self.handle_metric(arg, "size"),
            ":depth" => self.handle_metric(arg, "depth"),
            ":abs_depth" => self.handle_metric(arg, "abs_depth"),
            ":subterms" => self.handle_metric(arg, "subterms"),
            ":debruijn" => self.handle_metric(arg, "debruijn"),
            ":density" => self.handle_metric(arg, "density"),
            ":list" => self.handle_list(),
            _ => self.ui.display_error(&format!("unknown command: {}", parts[0])),
        }
        false
    }

    fn parse_with_names(&mut self, source: &str) -> Result<Term, ParseError> {
        let names = self.registry.all_names();
        let result = parse_with_info(source, Some(&names))?;
        for (original, renamed) in &result.renames {
            self.ui.display(&format!("  (shadowed {} \u{2192} {})", original, renamed));
        }
        Ok(result.term)
    }

    // -- handlers (each is a port/domain composition) -------------------------

    fn handle_expression(&mut self, raw: &str) {
        match self.parse_with_names(raw) {
            Ok(term) => self.ui.display(&term.to_string()),
            Err(e) => self.show_parse_error(raw, &e),
        }
    }

    fn handle_reduce(&mut self, arg: &str) {
        if arg.is_empty() {
            self.ui.display_error(":reduce requires an expression");
            return;
        }
        let term = match self.parse_with_names(arg) {
            Ok(t) => t,
            Err(e) => { self.show_parse_error(arg, &e); return; }
        };
        let (current, steps, reached_nf) = self.reduce_interruptible(&term);
        self.ui.display(&current.to_string());
        if !reached_nf {
            self.ui.display(&format!(
                "  (stopped after {} steps — may not be in normal form)", steps
            ));
        }
    }

    fn handle_step(&mut self, arg: &str) {
        if arg.is_empty() {
            self.ui.display_error(":step requires an expression");
            return;
        }
        let term = match self.parse_with_names(arg) {
            Ok(t) => t,
            Err(e) => { self.show_parse_error(arg, &e); return; }
        };
        match beta_reduce_step(&term) {
            None => self.ui.display("Already in normal form."),
            Some(stepped) => self.ui.display(&stepped.to_string()),
        }
    }

    fn handle_trace(&mut self, arg: &str) {
        if arg.is_empty() {
            self.ui.display_error(":trace requires an expression");
            return;
        }
        let term = match self.parse_with_names(arg) {
            Ok(t) => t,
            Err(e) => { self.show_parse_error(arg, &e); return; }
        };
        let (_current, trace, reached_nf) = self.trace_interruptible(&term);
        for (i, t) in trace.iter().enumerate() {
            self.ui.display(&format!("  {}: {}", i, t));
        }
        if !reached_nf {
            self.ui.display(&format!("  (stopped after {} steps)", trace.len() - 1));
        }
    }

    fn handle_free(&mut self, arg: &str) {
        if arg.is_empty() {
            self.ui.display_error(":free requires an expression");
            return;
        }
        let term = match self.parse_with_names(arg) {
            Ok(t) => t,
            Err(e) => { self.show_parse_error(arg, &e); return; }
        };
        let fv = free_vars(&term);
        let mut names: Vec<&str> = fv.iter().map(|s| s.as_str()).collect();
        names.sort();
        self.ui.display(&format!("{{{}}}", names.join(", ")));
    }

    fn handle_bound(&mut self, arg: &str) {
        if arg.is_empty() {
            self.ui.display_error(":bound requires an expression");
            return;
        }
        let term = match self.parse_with_names(arg) {
            Ok(t) => t,
            Err(e) => { self.show_parse_error(arg, &e); return; }
        };
        let bv = bound_vars(&term);
        let mut names: Vec<&str> = bv.iter().map(|s| s.as_str()).collect();
        names.sort();
        self.ui.display(&format!("{{{}}}", names.join(", ")));
    }

    fn handle_binding(&mut self, arg: &str) {
        if arg.is_empty() {
            self.ui.display_error(":binding requires an expression");
            return;
        }
        let term = match self.parse_with_names(arg) {
            Ok(t) => t,
            Err(e) => { self.show_parse_error(arg, &e); return; }
        };
        let biv = binding_vars(&term);
        let mut names: Vec<&str> = biv.iter().map(|s| s.as_str()).collect();
        names.sort();
        self.ui.display(&format!("{{{}}}", names.join(", ")));
    }

    fn handle_metric(&mut self, arg: &str, metric: &str) {
        if arg.is_empty() {
            self.ui.display_error(&format!(":{} requires an expression", metric));
            return;
        }
        let term = match self.parse_with_names(arg) {
            Ok(t) => t,
            Err(e) => { self.show_parse_error(arg, &e); return; }
        };
        self.ui.display(&format_metric(&term, metric));
    }

    fn handle_random(&mut self, arg: &str) {
        let depth = if arg.trim().is_empty() {
            self.config.random_depth
        } else {
            match arg.trim().parse::<usize>() {
                Ok(d) => d,
                Err(_) => {
                    self.ui.display_error(&format!("invalid depth: '{}'", arg.trim()));
                    return;
                }
            }
        };
        let term = self.generator.generate(depth);
        self.ui.display(&term.to_string());
    }

    fn handle_let(&mut self, arg: &str) {
        if !arg.contains('=') {
            self.ui.display_error(":let requires 'name = expression'");
            return;
        }
        let (name, rhs) = arg.split_once('=').unwrap();
        let name = name.trim();
        let rhs = rhs.trim();
        if name.is_empty() {
            self.ui.display_error("missing name in :let");
            return;
        }
        let result = match self.eval_pipe(rhs) {
            Some(t) => t,
            None => return,
        };
        self.registry.bind(name, result.clone());
        self.ui.display(&format!("  {} = {}", name, result));
    }

    fn handle_list(&mut self) {
        let names = self.registry.all_names();
        if names.is_empty() {
            self.ui.display("(no named terms)");
            return;
        }
        let mut keys: Vec<&String> = names.keys().collect();
        keys.sort();
        for name in keys {
            self.ui.display(&format!("  {:8} = {}", name, names[name]));
        }
    }

    fn handle_help(&mut self) {
        self.ui.display(
"Commands:
  <expr>              Parse and display a lambda expression
  :reduce <expr>      Fully beta-reduce (up to step limit)
  :step <expr>        One beta-reduction step
  :trace <expr>       Show full reduction trace
  :free <expr>        List free variables
  :bound <expr>       List bound variables
  :binding <expr>     List binding variables (lambda params)
  :size <expr>        Total AST node count
  :depth <expr>       AST tree height
  :abs_depth <expr>   Maximum lambda-binder nesting
  :subterms <expr>    Number of distinct subterms
  :debruijn <expr>    Maximum de Bruijn index
  :density <expr>     Bound/total variable occurrence ratio
  :random [depth]     Generate a random closed term
  :let name = <expr>  Bind a name to an expression
  :assert_eq <expr>   Assert piped term equals <expr> (pipe only)
  :list               Show all named terms
  :help               Show this help
  :quit               Exit

Pipes:
  <expr> |> :cmd      Chain commands: (I a) |> :reduce |> :free
  :let X = <expr> |> :reduce   Pipes work in :let RHS

Syntax:
  \\x.body  or  \u{03BB}x.body     Abstraction (one variable)
  (func arg)                Application (explicit parens)
  x, foo                    Variable");
    }

    // -- pipe evaluation ------------------------------------------------------

    fn eval_pipe(&mut self, raw: &str) -> Option<Term> {
        let segments: Vec<&str> = raw.split("|>").map(|s| s.trim()).collect();

        // First segment: expression or :random.
        let mut current = self.eval_pipe_source(segments[0])?;

        // Remaining segments: commands applied to the current Term.
        for &segment in &segments[1..] {
            if !segment.starts_with(':') {
                self.ui.display_error(&format!(
                    "expected :command in pipe, got '{}'", segment
                ));
                return None;
            }
            let parts: Vec<&str> = segment.splitn(2, char::is_whitespace).collect();
            let cmd = parts[0].to_lowercase();
            let arg = if parts.len() > 1 { parts[1].trim() } else { "" };
            current = self.eval_pipe_segment(&cmd, arg, &current)?;
        }

        Some(current)
    }

    fn eval_pipe_source(&mut self, segment: &str) -> Option<Term> {
        if segment.starts_with(':') {
            let parts: Vec<&str> = segment.splitn(2, char::is_whitespace).collect();
            let cmd = parts[0].to_lowercase();
            let arg = if parts.len() > 1 { parts[1].trim() } else { "" };
            if cmd == ":random" {
                let depth = if arg.is_empty() {
                    self.config.random_depth
                } else {
                    match arg.parse::<usize>() {
                        Ok(d) => d,
                        Err(_) => {
                            self.ui.display_error(&format!("invalid depth: '{}'", arg));
                            return None;
                        }
                    }
                };
                return Some(self.generator.generate(depth));
            }
            self.ui.display_error(&format!("cannot start pipe with {}", cmd));
            return None;
        }
        match self.parse_with_names(segment) {
            Ok(t) => Some(t),
            Err(e) => {
                self.show_parse_error(segment, &e);
                None
            }
        }
    }

    fn eval_pipe_segment(&mut self, cmd: &str, arg: &str, term: &Term) -> Option<Term> {
        match cmd {
            ":reduce" => {
                let (current, _, _) = self.reduce_interruptible(term);
                Some(current)
            }
            ":step" => {
                Some(beta_reduce_step(term).unwrap_or_else(|| term.clone()))
            }
            ":trace" => {
                let (_, trace, reached_nf) = self.trace_interruptible(term);
                for (i, t) in trace.iter().enumerate() {
                    self.ui.display(&format!("  {}: {}", i, t));
                }
                if !reached_nf {
                    self.ui.display(&format!(
                        "  (stopped after {} steps)", trace.len() - 1
                    ));
                }
                Some(trace.last().unwrap().clone())
            }
            ":free" => {
                let fv = free_vars(term);
                let mut names: Vec<&str> = fv.iter().map(|s| s.as_str()).collect();
                names.sort();
                self.ui.display(&format!("{{{}}}", names.join(", ")));
                None
            }
            ":bound" => {
                let bv = bound_vars(term);
                let mut names: Vec<&str> = bv.iter().map(|s| s.as_str()).collect();
                names.sort();
                self.ui.display(&format!("{{{}}}", names.join(", ")));
                None
            }
            ":binding" => {
                let biv = binding_vars(term);
                let mut names: Vec<&str> = biv.iter().map(|s| s.as_str()).collect();
                names.sort();
                self.ui.display(&format!("{{{}}}", names.join(", ")));
                None
            }
            ":size" | ":depth" | ":abs_depth" | ":subterms" | ":debruijn" | ":density" => {
                let metric = &cmd[1..]; // strip leading ':'
                self.ui.display(&format_metric(term, metric));
                None
            }
            ":assert_eq" => {
                if arg.is_empty() {
                    self.ui.display_error(":assert_eq requires an expected expression");
                    return None;
                }
                let expected = match self.parse_with_names(arg) {
                    Ok(t) => t,
                    Err(e) => {
                        self.show_parse_error(arg, &e);
                        return None;
                    }
                };
                if *term == expected {
                    self.ui.display("  ok");
                } else {
                    self.ui.display_error(&format!(
                        "assertion failed\n  got:      {}\n  expected: {}",
                        term, expected
                    ));
                }
                None
            }
            _ => {
                self.ui.display_error(&format!("cannot pipe into {}", cmd));
                None
            }
        }
    }

    // -- interruptible reduction (no Ctrl+C in v1, just max-steps) -----------

    fn reduce_interruptible(&self, term: &Term) -> (Term, usize, bool) {
        let mut current = term.clone();
        let mut steps = 0;
        for _ in 0..self.config.max_steps {
            match beta_reduce_step(&current) {
                None => return (current, steps, true),
                Some(next) => {
                    current = next;
                    steps += 1;
                }
            }
        }
        (current, steps, false)
    }

    fn trace_interruptible(&self, term: &Term) -> (Term, Vec<Term>, bool) {
        let mut trace = vec![term.clone()];
        let mut current = term.clone();
        for _ in 0..self.config.max_steps {
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

    // -- presentation helpers ------------------------------------------------

    fn show_parse_error(&mut self, source: &str, error: &ParseError) {
        self.ui.display_error(&error.message);
        self.ui.display(&format!("  {}", source));
        self.ui.display(&format!("  {}^", " ".repeat(error.position)));
    }
}

fn format_metric(term: &Term, metric: &str) -> String {
    match metric {
        "size" => term_size(term).value.to_string(),
        "depth" => term_depth(term).value.to_string(),
        "abs_depth" => abs_depth(term).value.to_string(),
        "subterms" => subterm_count(term).value.to_string(),
        "debruijn" => de_bruijn_height(term).value.to_string(),
        "density" => {
            let r = binding_density(term);
            format!("{}/{}", r.numerator, r.denominator)
        }
        _ => "unknown metric".to_string(),
    }
}

// -- Factory functions -------------------------------------------------------

/// Wire concrete adapters into the service for interactive use.
pub fn make_repl(max_steps: usize, random_depth: usize) -> ReplService {
    use crate::adapters::{InMemoryNameRegistry, RandomTermGenerator, ReadlineUI};

    ReplService::new(
        Box::new(ReadlineUI::new()),
        Box::new(RandomTermGenerator::new()),
        Box::new(InMemoryNameRegistry::new()),
        ReplConfig { max_steps, random_depth },
    )
}

/// Wire concrete adapters for non-interactive script execution.
pub fn make_script_repl(
    lines: Vec<String>,
    max_steps: usize,
    random_depth: usize,
) -> ReplService {
    use crate::adapters::{InMemoryNameRegistry, RandomTermGenerator, ScriptUI};

    ReplService::new(
        Box::new(ScriptUI::new(lines)),
        Box::new(RandomTermGenerator::new()),
        Box::new(InMemoryNameRegistry::new()),
        ReplConfig { max_steps, random_depth },
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;
    use std::collections::HashMap;

    // -- Fake ports for testing -----------------------------------------------

    struct FakeUI {
        inputs: RefCell<Vec<String>>,
        outputs: RefCell<Vec<String>>,
    }

    impl FakeUI {
        fn new(inputs: Vec<&str>) -> Self {
            Self {
                inputs: RefCell::new(inputs.into_iter().rev().map(String::from).collect()),
                outputs: RefCell::new(Vec::new()),
            }
        }

        fn outputs(&self) -> Vec<String> {
            self.outputs.borrow().clone()
        }
    }

    impl UserInterface for FakeUI {
        fn read_input(&mut self) -> Option<String> {
            self.inputs.borrow_mut().pop()
        }

        fn display(&mut self, text: &str) {
            self.outputs.borrow_mut().push(text.to_string());
        }

        fn display_error(&mut self, text: &str) {
            self.outputs.borrow_mut().push(format!("Error: {}", text));
        }
    }

    struct FakeGenerator {
        term: Term,
    }

    impl TermGenerator for FakeGenerator {
        fn generate(&mut self, _max_depth: usize) -> Term {
            self.term.clone()
        }
    }

    struct FakeRegistry {
        names: HashMap<String, Term>,
    }

    impl FakeRegistry {
        fn empty() -> Self {
            Self { names: HashMap::new() }
        }
    }

    impl NameRegistry for FakeRegistry {
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

    // Test via dispatch with accessible UI through raw pointer.

    struct TestHarness {
        service: ReplService,
    }

    impl TestHarness {
        fn new() -> Self {
            Self::with_registry(FakeRegistry::empty())
        }

        fn with_registry(registry: FakeRegistry) -> Self {
            Self {
                service: ReplService::new(
                    Box::new(FakeUI::new(vec![])),
                    Box::new(FakeGenerator { term: Term::var("rnd") }),
                    Box::new(registry),
                    ReplConfig { max_steps: 100, random_depth: 3 },
                ),
            }
        }

        fn dispatch(&mut self, input: &str) {
            self.service.dispatch(input);
        }

        fn outputs(&self) -> Vec<String> {
            // Safety: we know ui is a FakeUI because we created it.
            // We use the RefCell inside FakeUI to get outputs.
            let ui_ptr = &*self.service.ui as *const dyn UserInterface as *const FakeUI;
            unsafe { &*ui_ptr }.outputs()
        }

        fn last_output(&self) -> String {
            self.outputs().last().cloned().unwrap_or_default()
        }
    }

    // -- Expression tests ----------------------------------------------------

    #[test]
    fn dispatch_expression() {
        let mut h = TestHarness::new();
        h.dispatch(r"\x.x");
        assert_eq!(h.last_output(), "λx.x");
    }

    #[test]
    fn dispatch_application() {
        let mut h = TestHarness::new();
        h.dispatch("(f x)");
        assert_eq!(h.last_output(), "(f x)");
    }

    // -- :reduce tests -------------------------------------------------------

    #[test]
    fn dispatch_reduce() {
        let mut h = TestHarness::new();
        h.dispatch(r":reduce (\x.x a)");
        assert_eq!(h.last_output(), "a");
    }

    #[test]
    fn dispatch_reduce_no_arg() {
        let mut h = TestHarness::new();
        h.dispatch(":reduce");
        assert!(h.last_output().contains("Error"));
    }

    // -- :step tests ---------------------------------------------------------

    #[test]
    fn dispatch_step() {
        let mut h = TestHarness::new();
        h.dispatch(r":step (\x.x a)");
        assert_eq!(h.last_output(), "a");
    }

    #[test]
    fn dispatch_step_nf() {
        let mut h = TestHarness::new();
        h.dispatch(":step x");
        assert_eq!(h.last_output(), "Already in normal form.");
    }

    // -- :trace tests --------------------------------------------------------

    #[test]
    fn dispatch_trace() {
        let mut h = TestHarness::new();
        h.dispatch(r":trace (\x.x a)");
        let outputs = h.outputs();
        assert!(outputs.iter().any(|o| o.contains("0:")));
        assert!(outputs.iter().any(|o| o.contains("1:")));
    }

    // -- :free, :bound, :binding tests ---------------------------------------

    #[test]
    fn dispatch_free() {
        let mut h = TestHarness::new();
        h.dispatch(r":free \x.(x y)");
        assert_eq!(h.last_output(), "{y}");
    }

    #[test]
    fn dispatch_bound() {
        let mut h = TestHarness::new();
        h.dispatch(r":bound \x.(x y)");
        assert_eq!(h.last_output(), "{x}");
    }

    #[test]
    fn dispatch_binding() {
        let mut h = TestHarness::new();
        h.dispatch(r":binding \x.\y.(x y)");
        assert_eq!(h.last_output(), "{x, y}");
    }

    // -- :let and :list tests ------------------------------------------------

    #[test]
    fn dispatch_let_and_list() {
        let mut h = TestHarness::new();
        h.dispatch(r":let ID = \x.x");
        assert!(h.last_output().contains("ID = λx.x"));
    }

    // -- :random test --------------------------------------------------------

    #[test]
    fn dispatch_random() {
        let mut h = TestHarness::new();
        h.dispatch(":random");
        // FakeGenerator returns Term::var("rnd")
        assert_eq!(h.last_output(), "rnd");
    }

    // -- Metric tests --------------------------------------------------------

    #[test]
    fn dispatch_size() {
        let mut h = TestHarness::new();
        h.dispatch(r":size \x.x");
        assert_eq!(h.last_output(), "2");
    }

    #[test]
    fn dispatch_depth() {
        let mut h = TestHarness::new();
        h.dispatch(r":depth \x.x");
        assert_eq!(h.last_output(), "1");
    }

    #[test]
    fn dispatch_density() {
        let mut h = TestHarness::new();
        h.dispatch(r":density \x.x");
        assert_eq!(h.last_output(), "1/1");
    }

    // -- Pipe tests ----------------------------------------------------------

    #[test]
    fn pipe_reduce_then_free() {
        let mut h = TestHarness::new();
        h.dispatch(r"(\x.x a) |> :reduce |> :free");
        // :free is terminal — after reducing (λx.x a) -> a, free vars = {a}
        assert!(h.outputs().iter().any(|o| o == "{a}"));
    }

    #[test]
    fn pipe_reduce() {
        let mut h = TestHarness::new();
        h.dispatch(r"(\x.x a) |> :reduce");
        assert_eq!(h.last_output(), "a");
    }

    #[test]
    fn pipe_assert_eq_ok() {
        let mut h = TestHarness::new();
        h.dispatch(r"(\x.x a) |> :reduce |> :assert_eq a");
        assert!(h.outputs().iter().any(|o| o.contains("ok")));
    }

    #[test]
    fn pipe_assert_eq_fail() {
        let mut h = TestHarness::new();
        h.dispatch(r"(\x.x a) |> :reduce |> :assert_eq b");
        assert!(h.outputs().iter().any(|o| o.contains("assertion failed")));
    }

    // -- Error tests ---------------------------------------------------------

    #[test]
    fn dispatch_unknown_command() {
        let mut h = TestHarness::new();
        h.dispatch(":foobar");
        assert!(h.last_output().contains("unknown command"));
    }

    #[test]
    fn dispatch_parse_error() {
        let mut h = TestHarness::new();
        h.dispatch("123");
        assert!(h.outputs().iter().any(|o| o.contains("Error")));
    }

    // -- :let with pipes -----------------------------------------------------

    #[test]
    fn let_with_pipe() {
        let mut h = TestHarness::new();
        h.dispatch(r":let RESULT = (\x.x a) |> :reduce");
        assert!(h.last_output().contains("RESULT = a"));
    }
}
