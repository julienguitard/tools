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
    param: str
    body: Term

@dataclass(frozen=True)
class App:
    """Application: explicit, no left-associativity sugar."""
    func: Term
    arg: Term

Term = Var | Abs | App
```

Python 3.10+ `match` statements provide exhaustive pattern matching on `Term`.

### 2.2 Core operations

| Function | Signature | Description |
|----------|-----------|-------------|
| `free_vars` | `(Term) -> set[str]` | Set of free variable names |
| `bound_vars` | `(Term) -> set[str]` | Set of variables that appear bound |
| `binding_vars` | `(Term) -> set[str]` | Set of variables that appear as λ-parameters |
| `substitute` | `(Term, str, Term) -> Term` | Capture-avoiding substitution `M[x := N]` |
| `alpha_rename` | `(Abs, str) -> Abs` | Rename the bound variable to avoid capture |
| `beta_reduce_step` | `(Term) -> Term \| None` | One normal-order β-step; `None` if already in normal form |
| `beta_reduce` | `(Term, max_steps: int) -> tuple[Term, list[Term], bool]` | Full reduction returning `(final, trace, reached_normal_form)` |
| `is_normal_form` | `(Term) -> bool` | True if no β-redex exists |
| `is_closed` | `(Term) -> bool` | True if `free_vars(t) == {}` |

### 2.3 Parser

A recursive-descent parser for the strict syntax:

```
<term>   ::= <var> | <abs> | <app> | '(' <term> ')'
<var>    ::= [a-zA-Z_][a-zA-Z0-9_]*
<abs>    ::= ('λ' | '\') <var> '.' <term>
<app>    ::= '(' <term> ' ' <term> ')'
```

```python
@dataclass(frozen=True)
class ParseError:
    """Syntax error with position for display."""
    message: str
    position: int

def parse(source: str) -> Term | ParseError: ...
def stringify(term: Term) -> str: ...
```

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

### Port rationale

| Port | Why it exists |
|------|--------------|
| `TermGenerator` | Decouples random generation strategy from service; allows deterministic generators for testing |
| `NameRegistry` | Abstracts storage so in-memory can be swapped for file-based persistence later |
| `UserInterface` | Enables testing the REPL logic without actual stdin/stdout |

## 4. Service layer — `service.py`

The service orchestrates REPL commands by composing port calls. It contains no IO and no domain logic — it is the "narrator."

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
    max_steps: int = 100
    random_depth: int = 3

class ReplService:
    def __init__(
        self,
        ui: UserInterface,
        generator: TermGenerator,
        registry: NameRegistry,
        config: ReplConfig,
    ) -> None: ...

    def run(self) -> None:
        """Main REPL loop: read → dispatch → display → repeat."""
        ...
```

### Command dispatch

```python
# -- command dispatch -----------------------------------------------------

def _dispatch(self, raw: str) -> None:
    """Route input to the appropriate handler."""
    ...

def _handle_expression(self, raw: str) -> None: ...
def _handle_reduce(self, arg: str) -> None: ...
def _handle_step(self, arg: str) -> None: ...
def _handle_trace(self, arg: str) -> None: ...
def _handle_free(self, arg: str) -> None: ...
def _handle_bound(self, arg: str) -> None: ...
def _handle_binding(self, arg: str) -> None: ...
def _handle_random(self, arg: str) -> None: ...
def _handle_let(self, arg: str) -> None: ...
def _handle_list(self) -> None: ...
def _handle_help(self) -> None: ...
```

The service resolves named references (from `NameRegistry`) before parsing, allowing `:reduce S` where `S` was previously bound via `:let`.

## 5. Adapters layer

### 5.1 `RandomTermGenerator` — `adapters/random_gen.py`

Generates closed lambda terms using a stochastic recursive builder.

- **Parameters**: `max_depth`, `var_prob`, `abs_prob`, `app_prob` (weights for node type selection).
- **Closure guarantee**: maintains a list of bound variables in scope; only generates `Var` nodes from in-scope bindings.
- **Depth control**: as depth approaches `max_depth`, bias shifts toward `Var` to terminate recursion.

### 5.2 `ReadlineUI` — `adapters/readline_ui.py`

- Uses Python `readline` for line editing, history, and tab completion.
- Prompt: `λ> `.
- Returns `None` on `EOF` (`Ctrl-D`).
- Completes `:` commands and named terms on `Tab`.

### 5.3 `InMemoryNameRegistry` — `adapters/memory_names.py`

- Simple `dict[str, Term]` wrapper.
- Preloaded with standard combinators at construction:

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

```python
"""CLI entry point for the lambda calculus REPL."""
from __future__ import annotations
import argparse
from play_with_lambda.service import ReplService, ReplConfig
from play_with_lambda.adapters import (
    RandomTermGenerator,
    ReadlineUI,
    InMemoryNameRegistry,
)

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactive untyped lambda calculus REPL.",
    )
    parser.add_argument("--max-steps", type=int, default=100)
    parser.add_argument("--random-depth", type=int, default=3)
    args = parser.parse_args()

    config = ReplConfig(max_steps=args.max_steps, random_depth=args.random_depth)
    ui = ReadlineUI()
    generator = RandomTermGenerator()
    registry = InMemoryNameRegistry()

    service = ReplService(ui=ui, generator=generator, registry=registry, config=config)
    service.run()

if __name__ == "__main__":
    main()
```

## 7. Key algorithms

### 7.1 Capture-avoiding substitution

`M[x := N]` — the core operation behind β-reduction:

```
Var(y)[x := N]       = N          if y == x
                      = Var(y)    otherwise

App(M1, M2)[x := N]  = App(M1[x := N], M2[x := N])

Abs(y, M)[x := N]    = Abs(y, M)               if y == x  (x is shadowed)
                      = Abs(y, M[x := N])       if y ∉ free_vars(N)
                      = Abs(z, M[y := Var(z)][x := N])
                                                 otherwise (α-rename to fresh z)
```

Fresh variable generation: append `'` (prime) to the variable name until it is not in `free_vars(M) ∪ free_vars(N)`.

### 7.2 Normal-order reduction

Find the leftmost-outermost redex:

1. If `App(Abs(x, M), N)` → β-reduce: `M[x := N]`.
2. If `App(M, N)` and `M` is not an `Abs` → reduce `M` first.
3. If `App(Abs(x, M), N)` is not directly reducible (shouldn't happen) → reduce inside `M`, then `N`.
4. If `Abs(x, M)` → reduce inside `M`.
5. `Var` → no reduction.

This guarantees finding the normal form if one exists (unlike applicative order).

### 7.3 Random closed-term generation

Recursive procedure `gen(depth, scope)` where `scope` is the list of bound variables:

```
if depth == 0 or (scope is non-empty and random < var_bias):
    return Var(random_choice(scope))       # only from in-scope vars
elif random < abs_threshold:
    fresh = new_var_name()
    return Abs(fresh, gen(depth - 1, scope + [fresh]))
else:
    return App(gen(depth - 1, scope), gen(depth - 1, scope))
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
VENV     := .venv
PYTHON   := $(VENV)/bin/python
PIP      := $(VENV)/bin/pip

.PHONY: setup run clean test

setup:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	test -f .env || cp .env.example .env

run:
	$(PYTHON) -m play_with_lambda

test:
	$(PYTHON) -m pytest tests/ -v

clean:
	rm -rf $(VENV) __pycache__ play_with_lambda/__pycache__
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
