# Technical Architecture — play-with-lambda-expressions

## 1. Project layout

Following the monorepo's hexagonal architecture conventions:

```
play-with-lambda-expressions/
├── Makefile
├── README.md
├── requirements.txt          # readline (if needed), nothing else for MVP
├── .env.example
├── play_with_lambda/
│   ├── __init__.py
│   ├── __main__.py           # CLI entry point (argparse + REPL bootstrap)
│   ├── domain.py             # Term ADT, substitution, reduction, variable analysis
│   ├── ports.py              # Protocols: TermGenerator, UserInterface, NameRegistry
│   ├── service.py            # REPL orchestration, command dispatch
│   └── adapters/
│       ├── __init__.py       # Re-exports with __all__
│       ├── random_gen.py     # RandomTermGenerator — random closed-term generation
│       ├── readline_ui.py    # ReadlineUI — REPL I/O with history and completion
│       └── memory_names.py   # InMemoryNameRegistry — session-scoped name bindings
```

## 2. Domain layer — `domain.py`

The domain is the heart of the tool. It models lambda terms as an algebraic data type and implements all pure computation: parsing, reduction, variable analysis, pretty-printing.

### 2.1 Term ADT

```python
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Var:
    """A variable reference."""
    name: str

@dataclass(frozen=True)
class Abs:
    """λ-abstraction: binds exactly one variable."""
    param: Var
    body: Term

@dataclass(frozen=True)
class App:
    """Application: explicit, no left-associativity sugar."""
    func: Term
    arg: Term

Term = Var | Abs | App
```

Python 3.10+ `match` statements provide exhaustive pattern matching on `Term`.

**Domain type discipline**: `str` appears only at the parse/stringify boundary (converting between external string representation and domain). All internal operations work with `Var`, `Abs`, `App`.

### 2.2 Core operations

| Function | Input | Output | Description |
|----------|-------|--------|-------------|
| `free_vars` | `term: Term` | `set[Var]` | Set of free variables as `Var` objects |
| `bound_vars` | `term: Term` | `set[Var]` | Set of variables that appear bound |
| `binding_vars` | `term: Term` | `set[Var]` | Set of variables that appear as λ-parameters (collects `Abs.param`) |
| `is_closed` | `term: Term` | `bool` | `not free_vars(term)` |
| `is_normal_form` | `term: Term` | `bool` | `beta_reduce_step(term) is None` |
| `_fresh_var` | `var: Var, avoid: set[Var]` | `Var` | Append `'` to `var.name` until `Var(name)` not in `avoid` |
| `substitute` | `term: Term, var: Var, replacement: Term` | `Term` | Capture-avoiding `M[x := N]`; comparisons use `Var` equality |
| `alpha_rename` | `abs_term: Abs, new_var: Var` | `Abs` | Returns `Abs(new_var, body[old_param := new_var])` |
| `beta_reduce_step` | `term: Term` | `Term \| None` | One normal-order β-step; `None` if already in normal form |
| `beta_reduce` | `term: Term, max_steps: int` | `tuple[Term, list[Term], bool]` | Full reduction returning `(final, trace, reached_normal_form)` |

### 2.3 Parser

A recursive-descent parser for the strict syntax:

```
<term>   ::= <abs> | <app_or_group> | <var>
<var>    ::= [a-zA-Z_][a-zA-Z0-9_]*
<abs>    ::= ('λ' | '\') <var> '.' <term>
<app_or_group> ::= '(' <term> <term> ')' | '(' <term> ')'
```

| Function / Class | Input | Output | Description |
|------------------|-------|--------|-------------|
| `ParseError` | `message: str, position: int` | — | Frozen dataclass for syntax errors |
| `parse` | `source: str, names: dict[str, Term] \| None` | `Term \| ParseError` | Boundary: str → domain. Constructs `Abs(Var(...), ...)`. Optional `names` dict resolves named terms |
| `stringify` | `term: Term` | `str` | Boundary: domain → str. Uses `λ` in output, reads `abs.param.name` |
| `_Parser.__init__` | `source: str, names: dict[str, Term] \| None` | `None` | Internal parser state with position tracking |
| `_Parser.parse_term` | — | `Term \| ParseError` | Top-level parse entry point |
| `_Parser._parse_abs` | — | `Term \| ParseError` | Parse `λ<var>.<body>` or `\<var>.<body>` |
| `_Parser._parse_paren` | — | `Term \| ParseError` | Parse `(<term>)` (grouping) or `(<term> <term>)` (application) |
| `_Parser._parse_var` | — | `Var` | Parse identifier, check against names dict |
| `_Parser._skip_whitespace` | — | `None` | Advance past whitespace |
| `_Parser._peek` | — | `str \| None` | Look at current character without consuming |
| `_Parser._advance` | — | `str` | Consume and return current character |

Round-trip property: `parse(stringify(t))` reconstructs an equivalent term for all valid `t`.

### 2.4 Term identity

Each term is structurally compared (`frozen=True` gives `__eq__` and `__hash__` for free). No UUID or sequence number at the domain level — named references are handled by the `NameRegistry` port. This keeps the domain pure and avoids the "deviation from purity" concern noted in the original idea.

## 3. Ports layer — `ports.py`

```python
from __future__ import annotations
from typing import Protocol
from play_with_lambda.domain import Term

class TermGenerator(Protocol):
    """Generates lambda terms (e.g., randomly)."""
    def generate(self, max_depth: int) -> Term: ...

class NameRegistry(Protocol):
    """Session-scoped named term storage."""
    def bind(self, name: str, term: Term) -> None: ...
    def lookup(self, name: str) -> Term | None: ...
    def all_names(self) -> dict[str, Term]: ...

class UserInterface(Protocol):
    """REPL interaction abstraction."""
    def read_input(self) -> str | None: ...
    def display(self, text: str) -> None: ...
    def display_error(self, text: str) -> None: ...
```

### Port method signatures

| Port | Method | Input | Output |
|------|--------|-------|--------|
| `TermGenerator` | `generate` | `max_depth: int` | `Term` |
| `NameRegistry` | `bind` | `name: str, term: Term` | `None` |
| `NameRegistry` | `lookup` | `name: str` | `Term \| None` |
| `NameRegistry` | `all_names` | — | `dict[str, Term]` |
| `UserInterface` | `read_input` | — | `str \| None` |
| `UserInterface` | `display` | `text: str` | `None` |
| `UserInterface` | `display_error` | `text: str` | `None` |

### Port rationale

| Port | Why it exists |
|------|--------------|
| `TermGenerator` | Decouples random generation strategy from service; allows deterministic generators for testing |
| `NameRegistry` | Abstracts storage so in-memory can be swapped for file-based persistence later |
| `UserInterface` | Enables testing the REPL logic without actual stdin/stdout |

## 4. Service layer — `service.py`

The service orchestrates REPL commands by composing port calls and domain functions. It contains no IO and no domain logic — it is the "narrator." Each handler reads as `port_call → domain_fn → ... → port_call`.

```python
from __future__ import annotations
from dataclasses import dataclass
from play_with_lambda.domain import (
    Term, parse, stringify, beta_reduce, beta_reduce_step,
    free_vars, bound_vars, binding_vars, is_normal_form, ParseError,
)
from play_with_lambda.ports import TermGenerator, NameRegistry, UserInterface

@dataclass
class ReplConfig:
    """Runtime configuration for the REPL."""
    max_steps: int = 100
    random_depth: int = 3
```

### ReplService method signatures

| Method | Input | Output | Composition |
|--------|-------|--------|-------------|
| `__init__` | `ui: UserInterface, generator: TermGenerator, registry: NameRegistry, config: ReplConfig` | `None` | Store injected ports |
| `run` | — | `None` | `ui.display` → loop `ui.read_input` → `_dispatch` → repeat |
| `_dispatch` | `raw: str` | `None` | Route: split on `:` prefix → delegate to handler |
| `_parse_with_names` | `source: str` | `Term \| ParseError` | `registry.all_names()` → `parse(source, names)` |
| `_handle_expression` | `raw: str` | `None` | `_parse_with_names` → `stringify` → `ui.display` |
| `_handle_reduce` | `arg: str` | `None` | `_parse_with_names` → `beta_reduce(term, config.max_steps)` → `stringify(final)` → `ui.display` |
| `_handle_step` | `arg: str` | `None` | `_parse_with_names` → `beta_reduce_step` → `stringify` or "NF" → `ui.display` |
| `_handle_trace` | `arg: str` | `None` | `_parse_with_names` → `beta_reduce` → `stringify` each step → `ui.display` |
| `_handle_free` | `arg: str` | `None` | `_parse_with_names` → `free_vars` → format `set[Var]` → `ui.display` |
| `_handle_bound` | `arg: str` | `None` | `_parse_with_names` → `bound_vars` → format `set[Var]` → `ui.display` |
| `_handle_binding` | `arg: str` | `None` | `_parse_with_names` → `binding_vars` → format `set[Var]` → `ui.display` |
| `_handle_random` | `arg: str` | `None` | parse depth (int) → `generator.generate(depth)` → `stringify` → `ui.display` |
| `_handle_let` | `arg: str` | `None` | split `=` → `_parse_with_names(expr)` → `registry.bind(name, term)` → `ui.display` confirm |
| `_handle_list` | — | `None` | `registry.all_names()` → `stringify` each → `ui.display` |
| `_handle_help` | — | `None` | `ui.display(HELP_TEXT)` |

The service resolves named references (from `NameRegistry`) before parsing via `_parse_with_names`, allowing `:reduce S` where `S` was previously bound via `:let`.

### Factory function

| Function | Input | Output | Description |
|----------|-------|--------|-------------|
| `make_repl` | `max_steps: int = 100, random_depth: int = 3` | `ReplService` | Composition root: imports adapters, wires dependencies |

## 5. Adapters layer

### 5.1 `RandomTermGenerator` — `adapters/random_gen.py`

Generates closed lambda terms using a stochastic recursive builder.

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `generate` | `max_depth: int` | `Term` | Public entry point |
| `_gen` | `depth: int, scope: list[Var]` | `Term` | Recursive builder; scope tracks `Var` objects |
| `_fresh_param` | `scope: list[Var]` | `Var` | `@staticmethod`; returns `Var("a")`, ..., `Var("z")`, `Var("a'")`, etc. |

- **Closure guarantee**: maintains a `list[Var]` of bound variables in scope; only generates `Var` nodes from in-scope bindings.
- **Depth control**: as depth approaches `max_depth`, bias shifts toward `Var` to terminate recursion.
- **Empty scope**: forces `Abs(fresh_var, ...)` to introduce a variable before any `Var` can be generated.

### 5.2 `ReadlineUI` — `adapters/readline_ui.py`

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `__init__` | — | `None` | Lazy-imports `readline`, sets up tab completer |
| `read_input` | — | `str \| None` | `input("λ> ")`, catches EOF/KeyboardInterrupt → `None` |
| `display` | `text: str` | `None` | `print(text)` to stdout |
| `display_error` | `text: str` | `None` | `print(f"Error: {text}")` to stdout |

- Prompt: `λ> `.
- Tab-completes `:` commands and named terms.

### 5.3 `InMemoryNameRegistry` — `adapters/memory_names.py`

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `__init__` | — | `None` | Parses 14 standard library entries into `dict[str, Term]` |
| `bind` | `name: str, term: Term` | `None` | Adds or overwrites entry |
| `lookup` | `name: str` | `Term \| None` | Returns `None` if not found |
| `all_names` | — | `dict[str, Term]` | Shallow copy of the internal dict |

- Simple `dict[str, Term]` wrapper.
- Preloaded with standard combinators at construction (all using `Abs(Var(...), ...)`):

```python
STANDARD_LIBRARY: dict[str, str] = {
    "I": r"\x.x",
    "K": r"\x.\y.x",
    "S": r"\x.\y.\z.((x z) (y z))",
    "Y": r"\f.(\x.(f (x x)) \x.(f (x x)))",
    "OMEGA": r"(\x.(x x) \x.(x x))",
    "TRUE": r"\x.\y.x",
    "FALSE": r"\x.\y.y",
    "AND": r"\p.\q.((p q) p)",
    "OR": r"\p.\q.((p p) q)",
    "NOT": r"\p.((p \x.\y.y) \x.\y.x)",
    "ZERO": r"\f.\x.x",
    "SUCC": r"\n.\f.\x.(f ((n f) x))",
    "PLUS": r"\m.\n.\f.\x.((m f) ((n f) x))",
    "MULT": r"\m.\n.\f.(m (n f))",
}
```

## 6. Composition root — `__main__.py`

| Function | Input | Output | Description |
|----------|-------|--------|-------------|
| `main` | — | `None` | Parse CLI args, call `make_repl().run()` |

```python
"""CLI entry point — python -m play_with_lambda."""
from __future__ import annotations
import argparse
from .service import make_repl


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactive untyped lambda calculus REPL.",
    )
    parser.add_argument("--max-steps", type=int, default=100)
    parser.add_argument("--random-depth", type=int, default=3)
    args = parser.parse_args()

    repl = make_repl(max_steps=args.max_steps, random_depth=args.random_depth)
    repl.run()


if __name__ == "__main__":
    main()
```

## 7. Key algorithms

### 7.1 Capture-avoiding substitution

`substitute(term: Term, var: Var, replacement: Term) -> Term` — the core operation behind β-reduction. All comparisons use `Var` equality (frozen dataclass `__eq__`):

```
Var(y)[x := N]       = N          if y == x        (Var equality)
                      = Var(y)    otherwise

App(M1, M2)[x := N]  = App(M1[x := N], M2[x := N])

Abs(p, M)[x := N]    = Abs(p, M)               if p == x  (shadowed, Var eq)
                      = Abs(p, M[x := N])       if p ∉ free_vars(N)  (set[Var] membership)
                      = Abs(z, M[p := z][x := N])
                                                 otherwise (α-rename p to fresh z)
```

Fresh variable generation via `_fresh_var(var: Var, avoid: set[Var]) -> Var`: append `'` (prime) to `var.name` until `Var(name)` is not in `free_vars(M) ∪ free_vars(N)`.

### 7.2 Normal-order reduction

`beta_reduce_step(term: Term) -> Term | None` — find the leftmost-outermost redex:

1. If `App(Abs(p, M), N)` → β-reduce: `substitute(M, p, N)` (p is `Var`).
2. If `App(M, N)` and `M` is not an `Abs` → reduce `M` first; if `M` in NF, reduce `N`.
3. If `Abs(p, M)` → reduce inside `M`.
4. `Var` → return `None` (no reduction possible).

This guarantees finding the normal form if one exists (unlike applicative order).

### 7.3 Random closed-term generation

`_gen(depth: int, scope: list[Var]) -> Term` — recursive procedure where `scope` tracks in-scope `Var` objects:

```
if depth == 0 or (scope is non-empty and random < var_bias):
    return random_choice(scope)              # return existing Var from scope
elif random < abs_threshold:
    fresh = _fresh_param(scope)              # returns Var
    return Abs(fresh, _gen(depth - 1, scope + [fresh]))
else:
    return App(_gen(depth - 1, scope), _gen(depth - 1, scope))
```

When `scope` is empty, the generator must produce an `Abs` to introduce a variable before any `Var` node can be generated. This guarantees closure.

## 8. Technical requirements

### 8.1 Language and runtime

| Requirement | Value |
|-------------|-------|
| Language | Python 3.10+ (for `match` statements and `X \| Y` union syntax) |
| Dependencies | stdlib only for MVP (no third-party packages) |
| Entry point | `python -m play_with_lambda` |

### 8.2 Testing strategy

| Layer | What to test | Approach |
|-------|-------------|----------|
| Domain — parser | Round-trip (`parse ∘ stringify == id`), error positions | Property-based with `hypothesis` generating random term trees |
| Domain — substitution | Capture avoidance, shadowing, identity cases | Unit tests with known-tricky cases (e.g., `(λx.λy.x)[x := y]`) |
| Domain — reduction | Known reductions (I, K, S applied), divergence detection | Unit tests comparing against hand-computed results |
| Domain — variables | Free/bound/binding for nested terms | Unit tests |
| Service — dispatch | Command routing, name resolution, error display | Inject mock `UserInterface` and `NameRegistry` |
| Adapters — random | Closure guarantee, depth bounds | Generate N terms, assert `is_closed` and depth ≤ max |

### 8.3 Non-functional requirements

| Property | Target |
|----------|--------|
| Startup time | < 200 ms (stdlib only, no heavy imports) |
| Reduction of Church 5+3 | < 1 s with default step limit |
| Memory | No concern for MVP (terms are small trees) |
| Portability | macOS + Linux; no OS-specific code |

## 9. Makefile

```makefile
.PHONY: setup run clean

# -- Setup ----------------------------------------------------------------

setup:
	@echo "No dependencies — stdlib only."
	@test -f ./.env || cp ./.env.example ./.env

# -- Run ------------------------------------------------------------------

run:
	python3 -m play_with_lambda

# -- Housekeeping ---------------------------------------------------------

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
```

## 10. Dependency graph

```
__main__.py
  ├── service.py
  │     ├── domain.py    (Term, parse, stringify, reduce, vars)
  │     └── ports.py     (TermGenerator, NameRegistry, UserInterface)
  ├── adapters/
  │     ├── random_gen.py   → implements TermGenerator   → imports domain
  │     ├── readline_ui.py  → implements UserInterface   → imports nothing from project
  │     └── memory_names.py → implements NameRegistry    → imports domain
  └── domain.py  (for parse of standard library in __main__)
```

No adapter imports another adapter. No adapter imports `service`. The hexagonal rules from `CLAUDE.md` are respected.

## 11. Future extensions (out of scope for MVP)

| Extension | Effort | Value |
|-----------|--------|-------|
| De Bruijn index representation | Medium | Eliminates α-conversion; cleaner equality |
| File-based name persistence | Low | Resume sessions with saved definitions |
| `:step N` — multi-step | Low | Convenience for exploring long reductions |
| η-reduction | Low | Completeness |
| Church encoding utilities | Medium | Auto-convert `3` → `SUCC(SUCC(SUCC(ZERO)))` and back |
| Rust rewrite | High | Performance for deep reductions; elegant `enum` ADT |
| WASM + web UI | High | Broader accessibility |

## 12. Open design decisions

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| D1 | Internal representation | Named variables vs. de Bruijn indices | Named for MVP (simpler to debug and display); de Bruijn as future refactor |
| D2 | Reduction strategy flag | Always normal-order vs. `--strategy` flag | Normal-order only for MVP; flag later |
| D3 | Standard library loading | Hardcoded in adapter vs. external `.lam` file | Hardcoded for MVP; file-based later for user extensibility |
| D4 | Parser error recovery | Fail on first error vs. collect multiple | Fail on first — simpler and sufficient for a REPL |
