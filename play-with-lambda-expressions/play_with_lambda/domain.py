"""Pure domain models — no IO, no side effects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar


# -- Term ADT ----------------------------------------------------------------


@dataclass(frozen=True)
class Var:
    """A variable reference.

    Attributes:
        name: The variable identifier.
    """

    name: str


@dataclass(frozen=True)
class Abs:
    """Lambda abstraction: binds exactly one variable.

    Attributes:
        param: The binding variable (a Var, not a raw string).
        body: The body of the abstraction.
    """

    param: Var
    body: Term


@dataclass(frozen=True)
class App:
    """Application: explicit parentheses, no left-associativity sugar.

    Attributes:
        func: The function term.
        arg: The argument term.
    """

    func: Term
    arg: Term


Term = Var | Abs | App

R = TypeVar("R")


def fold(
    term: Term,
    on_var: Callable[[Var], R],
    on_abs: Callable[[Var, R], R],
    on_app: Callable[[R, R], R],
) -> R:
    """Catamorphism over the Term ADT.

    Recursively collapses a term by replacing each constructor with
    a function:
      - Var(v)      → on_var(v)
      - Abs(p, body) → on_abs(p, fold(body))
      - App(f, a)   → on_app(fold(f), fold(a))

    Args:
        term: The term to fold over.
        on_var: Handles variable leaves.
        on_abs: Combines a binder with its folded body.
        on_app: Combines folded function and argument.

    Returns:
        The result of collapsing the entire term.
    """
    match term:
        case Var() as v:
            return on_var(v)
        case Abs(param=p, body=b):
            return on_abs(p, fold(b, on_var, on_abs, on_app))
        case App(func=f, arg=a):
            return on_app(
                fold(f, on_var, on_abs, on_app),
                fold(a, on_var, on_abs, on_app),
            )


@dataclass(frozen=True)
class ParseError:
    """Syntax error with position for display.

    Attributes:
        message: Human-readable error description.
        position: Character offset in the source string.
    """

    message: str
    position: int


@dataclass(frozen=True)
class ParseResult:
    """Successful parse with optional shadowing metadata.

    Attributes:
        term: The parsed term (with shadowed variables renamed).
        renames: Pairs of (original_name, fresh_name) for each rename.
    """

    term: Term
    renames: tuple[tuple[str, str], ...]


# -- Variable analysis --------------------------------------------------------


def free_vars(term: Term) -> set[Var]:
    """Return the set of free variables in a term."""
    return fold(
        term,
        on_var=lambda v: {v},
        on_abs=lambda p, body: body - {p},
        on_app=lambda f, a: f | a,
    )


def bound_vars(term: Term) -> set[Var]:
    """Return the set of variables that appear bound in a term."""
    return _bound_vars(term, set())


def _bound_vars(term: Term, scope: set[Var]) -> set[Var]:
    """Recursive helper tracking in-scope binders."""
    match term:
        case Var() as v:
            return {v} if v in scope else set()
        case Abs(param=p, body=b):
            return _bound_vars(b, scope | {p})
        case App(func=f, arg=a):
            return _bound_vars(f, scope) | _bound_vars(a, scope)


def binding_vars(term: Term) -> set[Var]:
    """Return the set of binding variables (lambda parameters) in a term."""
    return fold(
        term,
        on_var=lambda _: set(),
        on_abs=lambda p, body: {p} | body,
        on_app=lambda f, a: f | a,
    )


def is_closed(term: Term) -> bool:
    """Return True if the term has no free variables."""
    return not free_vars(term)


def is_normal_form(term: Term) -> bool:
    """Return True if no beta-redex exists in the term."""
    return beta_reduce_step(term) is None


# -- Complexity metrics -------------------------------------------------------

T = TypeVar("T")


@dataclass(frozen=True)
class Meter(Generic[T]):
    """A tagged complexity measurement. T is a phantom type tag.

    Attributes:
        value: The measured integer quantity.
    """

    value: int


@dataclass(frozen=True)
class Ratio(Generic[T]):
    """A tagged ratio measurement. T is a phantom type tag.

    Attributes:
        numerator: Count of matching occurrences.
        denominator: Count of total occurrences.
    """

    numerator: int
    denominator: int


# Phantom type tags — never instantiated, used only as type parameters.
class Size:
    """Total AST node count."""

class Depth:
    """AST tree height."""

class AbsDepth:
    """Maximum lambda-binder nesting."""

class SubtermCount:
    """Number of distinct subterms."""

class DeBruijnHeight:
    """Maximum distance from a variable to its binder."""

class BindingDensity:
    """Ratio of bound to total variable occurrences."""


def term_size(term: Term) -> Meter[Size]:
    """Total number of AST nodes (Var + Abs + App)."""
    return Meter(fold(
        term,
        on_var=lambda _: 1,
        on_abs=lambda _p, body: 1 + body,
        on_app=lambda f, a: 1 + f + a,
    ))


def term_depth(term: Term) -> Meter[Depth]:
    """Height of the AST tree."""
    return Meter(fold(
        term,
        on_var=lambda _: 0,
        on_abs=lambda _p, body: 1 + body,
        on_app=lambda f, a: 1 + max(f, a),
    ))


def abs_depth(term: Term) -> Meter[AbsDepth]:
    """Maximum nesting depth of lambda binders."""
    return Meter(fold(
        term,
        on_var=lambda _: 0,
        on_abs=lambda _p, body: 1 + body,
        on_app=lambda f, a: max(f, a),
    ))


def subterms(term: Term) -> set[Term]:
    """Set of all distinct subterms (including the term itself).

    Note: cannot be expressed as a pure fold because each node must
    include *itself* (the original Term, not just the folded result).
    """
    match term:
        case Var():
            return {term}
        case Abs(body=b):
            return {term} | subterms(b)
        case App(func=f, arg=a):
            return {term} | subterms(f) | subterms(a)


def subterm_count(term: Term) -> Meter[SubtermCount]:
    """Number of distinct subterms."""
    return Meter(len(subterms(term)))


def de_bruijn_height(term: Term) -> Meter[DeBruijnHeight]:
    """Maximum distance from a variable occurrence to its binder."""
    return Meter(_de_bruijn_height(term, {}, 0))


def _de_bruijn_height(
    term: Term, binder_depth: dict[str, int], depth: int,
) -> int:
    match term:
        case Var(name=n):
            if n in binder_depth:
                return depth - binder_depth[n]
            return 0
        case Abs(param=p, body=b):
            return _de_bruijn_height(
                b, {**binder_depth, p.name: depth + 1}, depth + 1,
            )
        case App(func=f, arg=a):
            return max(
                _de_bruijn_height(f, binder_depth, depth),
                _de_bruijn_height(a, binder_depth, depth),
            )


def binding_density(term: Term) -> Ratio[BindingDensity]:
    """Ratio of bound variable occurrences to total variable occurrences."""
    total, bound = _var_counts(term, set())
    return Ratio(numerator=bound, denominator=total)


def _var_counts(term: Term, scope: set[Var]) -> tuple[int, int]:
    """Count (total_var_occurrences, bound_var_occurrences)."""
    match term:
        case Var() as v:
            return (1, 1) if v in scope else (1, 0)
        case Abs(param=p, body=b):
            return _var_counts(b, scope | {p})
        case App(func=f, arg=a):
            ft, fb = _var_counts(f, scope)
            at, ab = _var_counts(a, scope)
            return (ft + at, fb + ab)


# -- Substitution and reduction -----------------------------------------------


def _fresh_var(var: Var, avoid: set[Var]) -> Var:
    """Generate a fresh variable by appending primes until not in avoid."""
    name = var.name
    while Var(name) in avoid:
        name += "'"
    return Var(name)


def substitute(term: Term, var: Var, replacement: Term) -> Term:
    """Capture-avoiding substitution: term[var := replacement]."""
    match term:
        case Var() as v:
            return replacement if v == var else v
        case App(func=f, arg=a):
            return App(substitute(f, var, replacement),
                       substitute(a, var, replacement))
        case Abs(param=p, body=b):
            if p == var:
                # Shadowed — var is rebound, no substitution in body.
                return term
            if p not in free_vars(replacement):
                return Abs(p, substitute(b, var, replacement))
            # Capture would occur — alpha-rename first.
            fresh = _fresh_var(p, free_vars(b) | free_vars(replacement))
            renamed_body = substitute(b, p, fresh)
            return Abs(fresh, substitute(renamed_body, var, replacement))


def alpha_rename(abs_term: Abs, new_var: Var) -> Abs:
    """Rename the bound variable of an abstraction."""
    renamed_body = substitute(abs_term.body, abs_term.param, new_var)
    return Abs(new_var, renamed_body)


def beta_reduce_step(term: Term) -> Term | None:
    """Perform one normal-order beta-reduction step.

    Returns:
        The reduced term, or None if already in normal form.
    """
    match term:
        case App(func=Abs(param=p, body=b), arg=n):
            # Beta-redex found.
            return substitute(b, p, n)
        case App(func=f, arg=a):
            # Try reducing the function first.
            f_reduced = beta_reduce_step(f)
            if f_reduced is not None:
                return App(f_reduced, a)
            # Function is in NF — try the argument.
            a_reduced = beta_reduce_step(a)
            if a_reduced is not None:
                return App(f, a_reduced)
            return None
        case Abs(param=p, body=b):
            # Reduce under the lambda.
            b_reduced = beta_reduce_step(b)
            if b_reduced is not None:
                return Abs(p, b_reduced)
            return None
        case Var():
            return None


def beta_reduce(
    term: Term, max_steps: int = 100,
) -> tuple[Term, list[Term], bool]:
    """Fully beta-reduce a term up to a step limit.

    Returns:
        A tuple of (final_term, trace, reached_normal_form).
        The trace includes the original term as the first element.
    """
    trace: list[Term] = [term]
    current = term
    for _ in range(max_steps):
        next_term = beta_reduce_step(current)
        if next_term is None:
            return current, trace, True
        trace.append(next_term)
        current = next_term
    return current, trace, False


# -- Parser -------------------------------------------------------------------


class _Parser:
    """Recursive-descent parser for strict lambda calculus syntax.

    Maintains a scope stack to detect and rename shadowed binding
    variables, producing unambiguous terms.
    """

    def __init__(
        self, source: str, names: dict[str, Term] | None = None,
    ) -> None:
        self._src = source
        self._pos = 0
        self._names = names or {}
        self._scope: dict[str, Var] = {}
        self.renames: list[tuple[str, str]] = []

    def parse_term(self) -> Term | ParseError:
        """Parse a single term from the current position."""
        self._skip_whitespace()
        ch = self._peek()
        if ch is None:
            return ParseError("unexpected end of input", self._pos)
        if ch in ("\\", "λ"):
            return self._parse_abs()
        if ch == "(":
            return self._parse_paren()
        if ch.isalpha() or ch == "_":
            return self._parse_var_or_name()
        return ParseError(f"unexpected character: '{ch}'", self._pos)

    def _parse_abs(self) -> Term | ParseError:
        """Parse λ<var>.<body> or \\<var>.<body>."""
        self._advance()  # consume λ or \
        self._skip_whitespace()

        # Parse parameter name.
        if self._peek() is None or not (self._peek().isalpha() or self._peek() == "_"):
            return ParseError("expected parameter name after λ", self._pos)
        param_name = self._parse_identifier()

        # Detect shadowing and rename if needed.
        if param_name in self._scope:
            fresh = _fresh_var(Var(param_name), set(self._scope.values()))
            if fresh.name != param_name:
                self.renames.append((param_name, fresh.name))
            param_var = fresh
        else:
            param_var = Var(param_name)

        self._skip_whitespace()
        if self._peek() != ".":
            return ParseError("expected '.' after parameter", self._pos)
        self._advance()  # consume .

        # Push scope, parse body, pop scope.
        old_binding = self._scope.get(param_name)
        self._scope[param_name] = param_var
        body = self.parse_term()
        if old_binding is None:
            del self._scope[param_name]
        else:
            self._scope[param_name] = old_binding

        if isinstance(body, ParseError):
            return body
        return Abs(param_var, body)

    def _parse_paren(self) -> Term | ParseError:
        """Parse (term) for grouping or (term term) for application."""
        self._advance()  # consume (
        first = self.parse_term()
        if isinstance(first, ParseError):
            return first

        self._skip_whitespace()
        if self._peek() == ")":
            # Grouping parentheses.
            self._advance()
            return first

        # Application: parse second term.
        second = self.parse_term()
        if isinstance(second, ParseError):
            return second

        self._skip_whitespace()
        if self._peek() != ")":
            return ParseError("expected ')' to close application", self._pos)
        self._advance()  # consume )
        return App(first, second)

    def _parse_var_or_name(self) -> Term:
        """Parse an identifier — resolve via scope, names dict, or raw Var."""
        name = self._parse_identifier()
        if name in self._scope:
            return self._scope[name]
        if name in self._names:
            return self._names[name]
        return Var(name)

    def _parse_identifier(self) -> str:
        """Consume and return an identifier [a-zA-Z_][a-zA-Z0-9_']*."""
        start = self._pos
        while self._peek() is not None and (
            self._peek().isalnum() or self._peek() in ("_", "'")
        ):
            self._advance()
        return self._src[start : self._pos]

    def _skip_whitespace(self) -> None:
        """Advance past whitespace characters."""
        while self._peek() is not None and self._peek().isspace():
            self._advance()

    def _peek(self) -> str | None:
        """Look at current character without consuming."""
        if self._pos >= len(self._src):
            return None
        return self._src[self._pos]

    def _advance(self) -> str:
        """Consume and return the current character."""
        ch = self._src[self._pos]
        self._pos += 1
        return ch


def _run_parser(
    source: str, names: dict[str, Term] | None = None,
) -> tuple[Term, list[tuple[str, str]]] | ParseError:
    """Run the parser, returning the term and any renames, or a ParseError."""
    source = source.strip()
    if not source:
        return ParseError("empty input", 0)
    parser = _Parser(source, names)
    result = parser.parse_term()
    if isinstance(result, ParseError):
        return result
    parser._skip_whitespace()
    if parser._pos < len(source):
        return ParseError(
            f"unexpected trailing content: '{source[parser._pos:]}'",
            parser._pos,
        )
    return result, parser.renames


def parse(source: str, names: dict[str, Term] | None = None) -> Term | ParseError:
    """Parse a lambda calculus expression from a string.

    Shadowed binding variables are silently renamed. Use parse_with_info
    to get rename details.

    Args:
        source: The source string to parse.
        names: Optional mapping of identifiers to pre-defined terms.

    Returns:
        A Term on success, or a ParseError on failure.
    """
    result = _run_parser(source, names)
    if isinstance(result, ParseError):
        return result
    return result[0]


def parse_with_info(
    source: str, names: dict[str, Term] | None = None,
) -> ParseResult | ParseError:
    """Parse a lambda expression, returning rename metadata.

    Args:
        source: The source string to parse.
        names: Optional mapping of identifiers to pre-defined terms.

    Returns:
        A ParseResult with the term and any shadowing renames,
        or a ParseError on failure.
    """
    result = _run_parser(source, names)
    if isinstance(result, ParseError):
        return result
    term, renames = result
    return ParseResult(term=term, renames=tuple(renames))


# -- Pretty-printer -----------------------------------------------------------


def stringify(term: Term) -> str:
    """Convert a term to its string representation using λ notation.

    Uses the strict syntax: explicit parentheses for application,
    single-variable λ-abstraction.
    """
    return fold(
        term,
        on_var=lambda v: v.name,
        on_abs=lambda p, body: f"λ{p.name}.{body}",
        on_app=lambda f, a: f"({f} {a})",
    )
