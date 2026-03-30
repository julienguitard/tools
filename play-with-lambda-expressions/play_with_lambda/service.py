"""Orchestration: depends only on ports, never on adapters."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass

from .domain import (
    ParseError,
    Term,
    abs_depth,
    beta_reduce_step,
    binding_density,
    binding_vars,
    bound_vars,
    de_bruijn_height,
    free_vars,
    parse,
    stringify,
    subterm_count,
    term_depth,
    term_size,
)
from .ports import NameRegistry, TermGenerator, UserInterface


@dataclass
class ReplConfig:
    """Runtime configuration for the REPL.

    Attributes:
        max_steps: Maximum beta-reduction steps before stopping.
        random_depth: Default AST depth for :random.
    """

    max_steps: int = 100
    random_depth: int = 3


class ReplService:
    """Interactive REPL for untyped lambda calculus.

    Each handler is a composition of port calls and domain functions.
    The service contains no domain logic itself.
    """

    def __init__(
        self,
        ui: UserInterface,
        generator: TermGenerator,
        registry: NameRegistry,
        config: ReplConfig,
    ) -> None:
        self._ui = ui
        self._generator = generator
        self._registry = registry
        self._config = config

    def run(self) -> None:
        """Main REPL loop: read -> dispatch -> display -> repeat."""
        self._ui.display(
            "Lambda calculus REPL. Type :help for commands, :quit to exit."
        )

        while True:
            raw = self._ui.read_input()
            if raw is None:
                break

            text = raw.strip()
            if not text:
                continue

            self._dispatch(text)

    # -- command dispatch -----------------------------------------------------

    def _dispatch(self, raw: str) -> None:
        """Route input to the appropriate handler."""
        # :let must be checked before pipe detection because the RHS may
        # contain |> which _handle_let evaluates itself.
        if raw.startswith(":"):
            parts = raw.split(None, 1)
            cmd = parts[0].lower()
            if cmd == ":let":
                self._handle_let(parts[1] if len(parts) > 1 else "")
                return

        if "|>" in raw:
            result = self._eval_pipe(raw)
            if result is not None:
                self._ui.display(stringify(result))
            return

        if not raw.startswith(":"):
            self._handle_expression(raw)
            return

        parts = raw.split(None, 1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        match cmd:
            case ":quit" | ":q":
                raise SystemExit(0)
            case ":help" | ":h":
                self._handle_help()
            case ":reduce":
                self._handle_reduce(arg)
            case ":step":
                self._handle_step(arg)
            case ":trace":
                self._handle_trace(arg)
            case ":free":
                self._handle_free(arg)
            case ":bound":
                self._handle_bound(arg)
            case ":binding":
                self._handle_binding(arg)
            case ":random":
                self._handle_random(arg)
            case ":size":
                self._handle_metric(arg, "size")
            case ":depth":
                self._handle_metric(arg, "depth")
            case ":abs_depth":
                self._handle_metric(arg, "abs_depth")
            case ":subterms":
                self._handle_metric(arg, "subterms")
            case ":debruijn":
                self._handle_metric(arg, "debruijn")
            case ":density":
                self._handle_metric(arg, "density")
            case ":list":
                self._handle_list()
            case _:
                self._ui.display_error(f"unknown command: {parts[0]}")

    def _parse_with_names(self, source: str) -> Term | ParseError:
        """Parse source with named-term resolution from registry."""
        return parse(source, self._registry.all_names())

    # -- handlers (each is a port/domain composition) -------------------------

    def _handle_expression(self, raw: str) -> None:
        """Parse and display a term."""
        result = self._parse_with_names(raw)
        if isinstance(result, ParseError):
            self._show_parse_error(raw, result)
            return
        self._ui.display(stringify(result))

    def _handle_reduce(self, arg: str) -> None:
        """Fully beta-reduce a term."""
        if not arg:
            self._ui.display_error(":reduce requires an expression")
            return
        result = self._parse_with_names(arg)
        if isinstance(result, ParseError):
            self._show_parse_error(arg, result)
            return
        current, steps, reached_nf = self._reduce_interruptible(result)
        self._ui.display(stringify(current))
        if not reached_nf:
            self._ui.display(
                f"  (stopped after {steps} steps"
                " — may not be in normal form)"
            )

    def _handle_step(self, arg: str) -> None:
        """Perform one beta-reduction step."""
        if not arg:
            self._ui.display_error(":step requires an expression")
            return
        result = self._parse_with_names(arg)
        if isinstance(result, ParseError):
            self._show_parse_error(arg, result)
            return
        stepped = beta_reduce_step(result)
        if stepped is None:
            self._ui.display("Already in normal form.")
        else:
            self._ui.display(stringify(stepped))

    def _handle_trace(self, arg: str) -> None:
        """Show a numbered reduction trace."""
        if not arg:
            self._ui.display_error(":trace requires an expression")
            return
        result = self._parse_with_names(arg)
        if isinstance(result, ParseError):
            self._show_parse_error(arg, result)
            return
        current, trace, reached_nf = self._trace_interruptible(result)
        for i, term in enumerate(trace):
            self._ui.display(f"  {i}: {stringify(term)}")
        if not reached_nf:
            steps = len(trace) - 1
            self._ui.display(f"  (stopped after {steps} steps)")

    def _handle_free(self, arg: str) -> None:
        """Display the free variables of a term."""
        if not arg:
            self._ui.display_error(":free requires an expression")
            return
        result = self._parse_with_names(arg)
        if isinstance(result, ParseError):
            self._show_parse_error(arg, result)
            return
        fv = free_vars(result)
        self._ui.display(
            "{" + ", ".join(sorted(v.name for v in fv)) + "}"
        )

    def _handle_bound(self, arg: str) -> None:
        """Display the bound variables of a term."""
        if not arg:
            self._ui.display_error(":bound requires an expression")
            return
        result = self._parse_with_names(arg)
        if isinstance(result, ParseError):
            self._show_parse_error(arg, result)
            return
        bv = bound_vars(result)
        self._ui.display(
            "{" + ", ".join(sorted(v.name for v in bv)) + "}"
        )

    def _handle_binding(self, arg: str) -> None:
        """Display the binding variables (lambda parameters) of a term."""
        if not arg:
            self._ui.display_error(":binding requires an expression")
            return
        result = self._parse_with_names(arg)
        if isinstance(result, ParseError):
            self._show_parse_error(arg, result)
            return
        biv = binding_vars(result)
        self._ui.display(
            "{" + ", ".join(sorted(v.name for v in biv)) + "}"
        )

    def _handle_metric(self, arg: str, metric: str) -> None:
        """Compute and display a complexity metric for a term."""
        if not arg:
            self._ui.display_error(f":{metric} requires an expression")
            return
        result = self._parse_with_names(arg)
        if isinstance(result, ParseError):
            self._show_parse_error(arg, result)
            return
        self._ui.display(self._format_metric(result, metric))

    def _handle_random(self, arg: str) -> None:
        """Generate and display a random closed term."""
        depth = self._config.random_depth
        if arg.strip():
            try:
                depth = int(arg.strip())
            except ValueError:
                self._ui.display_error(f"invalid depth: '{arg.strip()}'")
                return
        term = self._generator.generate(depth)
        self._ui.display(stringify(term))

    def _handle_let(self, arg: str) -> None:
        """Bind a name to an expression (supports pipes on RHS)."""
        if "=" not in arg:
            self._ui.display_error(":let requires 'name = expression'")
            return
        name, rhs = arg.split("=", 1)
        name = name.strip()
        rhs = rhs.strip()
        if not name:
            self._ui.display_error("missing name in :let")
            return
        result = self._eval_pipe(rhs)
        if result is None:
            return
        self._registry.bind(name, result)
        self._ui.display(f"  {name} = {stringify(result)}")

    def _handle_list(self) -> None:
        """Display all named terms."""
        names = self._registry.all_names()
        if not names:
            self._ui.display("(no named terms)")
            return
        for name in sorted(names):
            self._ui.display(f"  {name:8s} = {stringify(names[name])}")

    def _handle_help(self) -> None:
        """Display the command reference."""
        self._ui.display(textwrap.dedent("""\
            Commands:
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
              \\x.body  or  λx.body     Abstraction (one variable)
              (func arg)                Application (explicit parens)
              x, foo                    Variable"""))

    # -- pipe evaluation ------------------------------------------------------

    def _eval_pipe(self, raw: str) -> Term | None:
        """Evaluate a pipe expression, returning the final Term or None.

        Splits on |>, evaluates left-to-right, threading Term values.
        Returns None if a terminal command displayed output or on error.
        """
        segments = [s.strip() for s in raw.split("|>")]

        # First segment: expression or :random.
        first = segments[0]
        current = self._eval_pipe_source(first)
        if current is None:
            return None

        # Remaining segments: commands applied to the current Term.
        for segment in segments[1:]:
            if not segment.startswith(":"):
                self._ui.display_error(
                    f"expected :command in pipe, got '{segment}'"
                )
                return None
            parts = segment.split(None, 1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""
            result = self._eval_pipe_segment(cmd, arg, current)
            if result is None:
                return None
            current = result

        return current

    def _eval_pipe_source(self, segment: str) -> Term | None:
        """Evaluate the first segment of a pipe (a term source)."""
        if segment.startswith(":"):
            parts = segment.split(None, 1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""
            if cmd == ":random":
                depth = self._config.random_depth
                if arg:
                    try:
                        depth = int(arg)
                    except ValueError:
                        self._ui.display_error(f"invalid depth: '{arg}'")
                        return None
                return self._generator.generate(depth)
            self._ui.display_error(f"cannot start pipe with {cmd}")
            return None
        result = self._parse_with_names(segment)
        if isinstance(result, ParseError):
            self._show_parse_error(segment, result)
            return None
        return result

    def _eval_pipe_segment(
        self, cmd: str, arg: str, term: Term,
    ) -> Term | None:
        """Apply one pipe command to a Term.

        Returns Term to continue the pipe, or None for terminals/errors.
        """
        match cmd:
            case ":reduce":
                current, _, _ = self._reduce_interruptible(term)
                return current
            case ":step":
                stepped = beta_reduce_step(term)
                return stepped if stepped is not None else term
            case ":trace":
                _, trace, reached_nf = self._trace_interruptible(term)
                for i, t in enumerate(trace):
                    self._ui.display(f"  {i}: {stringify(t)}")
                if not reached_nf:
                    self._ui.display(
                        f"  (stopped after {len(trace) - 1} steps)"
                    )
                return trace[-1]
            case ":free":
                fv = free_vars(term)
                self._ui.display(
                    "{" + ", ".join(sorted(v.name for v in fv)) + "}"
                )
                return None
            case ":bound":
                bv = bound_vars(term)
                self._ui.display(
                    "{" + ", ".join(sorted(v.name for v in bv)) + "}"
                )
                return None
            case ":binding":
                biv = binding_vars(term)
                self._ui.display(
                    "{" + ", ".join(sorted(v.name for v in biv)) + "}"
                )
                return None
            case (":size" | ":depth" | ":abs_depth"
                  | ":subterms" | ":debruijn" | ":density"):
                metric = cmd.removeprefix(":")
                self._ui.display(self._format_metric(term, metric))
                return None
            case ":assert_eq":
                if not arg:
                    self._ui.display_error(
                        ":assert_eq requires an expected expression"
                    )
                    return None
                expected = self._parse_with_names(arg)
                if isinstance(expected, ParseError):
                    self._show_parse_error(arg, expected)
                    return None
                if term == expected:
                    self._ui.display("  ok")
                else:
                    self._ui.display_error(
                        "assertion failed\n"
                        f"  got:      {stringify(term)}\n"
                        f"  expected: {stringify(expected)}"
                    )
                return None
            case _:
                self._ui.display_error(f"cannot pipe into {cmd}")
                return None

    # -- interruptible reduction (Ctrl+C safe) --------------------------------

    def _reduce_interruptible(
        self, term: Term,
    ) -> tuple[Term, int, bool]:
        """Step-by-step reduction loop that catches Ctrl+C.

        Returns:
            (final_term, step_count, reached_normal_form).
        """
        current = term
        steps = 0
        try:
            for _ in range(self._config.max_steps):
                next_term = beta_reduce_step(current)
                if next_term is None:
                    return current, steps, True
                current = next_term
                steps += 1
        except KeyboardInterrupt:
            pass
        return current, steps, False

    def _trace_interruptible(
        self, term: Term,
    ) -> tuple[Term, list[Term], bool]:
        """Step-by-step trace loop that catches Ctrl+C.

        Returns:
            (final_term, trace, reached_normal_form).
        """
        trace: list[Term] = [term]
        current = term
        try:
            for _ in range(self._config.max_steps):
                next_term = beta_reduce_step(current)
                if next_term is None:
                    return current, trace, True
                trace.append(next_term)
                current = next_term
        except KeyboardInterrupt:
            pass
        return current, trace, False

    # -- presentation helpers -------------------------------------------------

    @staticmethod
    def _format_metric(term: Term, metric: str) -> str:
        """Format a complexity metric for display."""
        match metric:
            case "size":
                return str(term_size(term).value)
            case "depth":
                return str(term_depth(term).value)
            case "abs_depth":
                return str(abs_depth(term).value)
            case "subterms":
                return str(subterm_count(term).value)
            case "debruijn":
                return str(de_bruijn_height(term).value)
            case "density":
                r = binding_density(term)
                return f"{r.numerator}/{r.denominator}"

    def _show_parse_error(self, source: str, error: ParseError) -> None:
        """Display a parse error with position marker."""
        self._ui.display_error(error.message)
        self._ui.display(f"  {source}")
        self._ui.display(f"  {' ' * error.position}^")


def make_repl(
    max_steps: int = 100, random_depth: int = 3,
) -> ReplService:
    """Wire concrete adapters into the service for interactive use.

    Args:
        max_steps: Maximum beta-reduction steps.
        random_depth: Default AST depth for :random.

    Returns:
        A fully wired ReplService ready to run.
    """
    from .adapters import InMemoryNameRegistry, RandomTermGenerator, ReadlineUI

    config = ReplConfig(max_steps=max_steps, random_depth=random_depth)
    return ReplService(
        ui=ReadlineUI(),
        generator=RandomTermGenerator(),
        registry=InMemoryNameRegistry(),
        config=config,
    )


def make_script_repl(
    lines: list[str],
    max_steps: int = 100,
    random_depth: int = 3,
) -> ReplService:
    """Wire concrete adapters for non-interactive script execution.

    Args:
        lines: Script lines to execute.
        max_steps: Maximum beta-reduction steps.
        random_depth: Default AST depth for :random.

    Returns:
        A fully wired ReplService ready to run.
    """
    from .adapters import InMemoryNameRegistry, RandomTermGenerator, ScriptUI

    config = ReplConfig(max_steps=max_steps, random_depth=random_depth)
    return ReplService(
        ui=ScriptUI(lines),
        generator=RandomTermGenerator(),
        registry=InMemoryNameRegistry(),
        config=config,
    )
