"""Orchestration: depends only on ports, never on adapters."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass

from .domain import (
    ParseError,
    Term,
    beta_reduce,
    beta_reduce_step,
    binding_vars,
    bound_vars,
    free_vars,
    is_normal_form,
    parse,
    stringify,
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
            case ":let":
                self._handle_let(arg)
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
        final, _trace, reached_nf = beta_reduce(
            result, self._config.max_steps,
        )
        self._ui.display(stringify(final))
        if not reached_nf:
            self._ui.display(
                f"  (stopped after {self._config.max_steps} steps"
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
        _final, trace, reached_nf = beta_reduce(
            result, self._config.max_steps,
        )
        for i, term in enumerate(trace):
            self._ui.display(f"  {i}: {stringify(term)}")
        if not reached_nf:
            self._ui.display(
                f"  (stopped after {self._config.max_steps} steps)"
            )

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
        """Bind a name to an expression."""
        if "=" not in arg:
            self._ui.display_error(":let requires 'name = expression'")
            return
        name, expr = arg.split("=", 1)
        name = name.strip()
        expr = expr.strip()
        if not name:
            self._ui.display_error("missing name in :let")
            return
        result = self._parse_with_names(expr)
        if isinstance(result, ParseError):
            self._show_parse_error(expr, result)
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
              :random [depth]     Generate a random closed term
              :let name = <expr>  Bind a name to an expression
              :list               Show all named terms
              :help               Show this help
              :quit               Exit

            Syntax:
              \\x.body  or  λx.body     Abstraction (one variable)
              (func arg)                Application (explicit parens)
              x, foo                    Variable"""))

    # -- presentation helpers -------------------------------------------------

    def _show_parse_error(self, source: str, error: ParseError) -> None:
        """Display a parse error with position marker."""
        self._ui.display_error(error.message)
        self._ui.display(f"  {source}")
        self._ui.display(f"  {' ' * error.position}^")


def make_repl(
    max_steps: int = 100, random_depth: int = 3,
) -> ReplService:
    """Wire concrete adapters into the service.

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
