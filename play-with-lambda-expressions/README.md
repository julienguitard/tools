# play-with-lambda-expressions

Interactive CLI REPL for learning untyped lambda calculus through practice.

## Purpose

A hands-on study tool for exploring lambda calculus mechanics: write expressions, watch them reduce step-by-step, inspect variable properties, and generate random terms to discover the space beyond standard combinators.

## Quick start

```bash
make run
# or directly:
python3 -m play_with_lambda
```

No dependencies required — stdlib only.

## Usage

```
λ> \x.x
λx.x

λ> :reduce (\x.x y)
y

λ> :trace ((\x.\y.x a) b)
  0: ((λx.λy.x a) b)
  1: (λy.a b)
  2: a

λ> :let ID = \x.x
  ID = λx.x

λ> :reduce (ID a)
a

λ> :free \x.(x y)
{y}

λ> :random 3
λa.(a λb.b)

λ> :list
  AND      = λp.λq.((p q) p)
  FALSE    = λx.λy.y
  I        = λx.x
  K        = λx.λy.x
  ...
```

## Commands

| Command | Description |
|---------|-------------|
| `<expr>` | Parse and display a lambda expression |
| `:reduce <expr>` | Fully beta-reduce (up to step limit) |
| `:step <expr>` | One beta-reduction step |
| `:trace <expr>` | Show full reduction trace |
| `:free <expr>` | List free variables |
| `:bound <expr>` | List bound variables |
| `:binding <expr>` | List binding variables (lambda params) |
| `:random [depth]` | Generate a random closed term |
| `:let name = <expr>` | Bind a name to an expression |
| `:list` | Show all named terms |
| `:help` | Show command reference |
| `:quit` | Exit |

## Syntax

| Construct | Syntax | Example |
|-----------|--------|---------|
| Variable | identifier | `x`, `foo` |
| Abstraction | `\x.body` or `λx.body` | `\x.x` |
| Application | `(func arg)` | `(\x.x y)` |

Strict syntax — each `λ` binds one variable, application requires explicit parentheses.

## CLI options

```
python3 -m play_with_lambda [--max-steps N] [--random-depth D]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--max-steps` | 100 | Maximum beta-reduction steps before stopping |
| `--random-depth` | 3 | Default AST depth for `:random` |

## Standard library

14 combinators are preloaded and available by name:

| Name | Definition |
|------|------------|
| `I` | `λx.x` |
| `K` | `λx.λy.x` |
| `S` | `λx.λy.λz.((x z) (y z))` |
| `Y` | `λf.(λx.(f (x x)) λx.(f (x x)))` |
| `OMEGA` | `(λx.(x x) λx.(x x))` |
| `TRUE` | `λx.λy.x` |
| `FALSE` | `λx.λy.y` |
| `AND`, `OR`, `NOT` | Church boolean operations |
| `ZERO` | `λf.λx.x` |
| `SUCC`, `PLUS`, `MULT` | Church numeral operations |

## Architecture

Hexagonal (ports & adapters), following the monorepo conventions:

```
play_with_lambda/
├── __main__.py       CLI entry point (argparse)
├── domain.py         Term ADT, parser, reduction, variable analysis
├── ports.py          Protocols: TermGenerator, NameRegistry, UserInterface
├── service.py        ReplService orchestration + make_repl() factory
└── adapters/
    ├── random_gen.py   RandomTermGenerator
    ├── readline_ui.py  ReadlineUI (prompt, history, tab completion)
    └── memory_names.py InMemoryNameRegistry (standard library preloaded)
```

## Files

| File | Purpose |
|------|---------|
| `domain.py` | `Var`, `Abs`, `App` frozen dataclasses; `parse`, `stringify`, `substitute`, `beta_reduce`, `free_vars` |
| `ports.py` | `TermGenerator`, `NameRegistry`, `UserInterface` protocols |
| `service.py` | REPL loop, command dispatch, `make_repl()` composition root |
| `adapters/random_gen.py` | Generates random closed terms with depth control |
| `adapters/readline_ui.py` | Terminal I/O with readline history and `:` command completion |
| `adapters/memory_names.py` | `dict[str, Term]` registry preloaded with 14 standard combinators |

## Key domain concepts

- **Normal-order reduction**: leftmost-outermost redex first — guarantees finding normal form if one exists
- **Capture-avoiding substitution**: automatic alpha-renaming when variable capture would occur
- **Domain type discipline**: all internal operations use `Var`, `Abs`, `App` types; `str` only at parse/stringify boundaries
- **`Abs.param` is `Var`** (not `str`) — the binding variable is a proper domain object

## Tests

```bash
python3 -m pytest tests/ -v
```

92 tests covering:
- Parser round-trips and error cases
- Capture-avoiding substitution (including tricky cases like `(λy.x)[x:=y]`)
- Known reductions (I, K, SKK=I, OMEGA divergence)
- Service command dispatch with mock ports
- Random generator closure guarantee
