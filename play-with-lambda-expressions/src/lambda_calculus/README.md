# lambda_calculus (Rust)

Rust port of the Python `play_with_lambda` REPL.  Same features, same hexagonal
architecture, same test expectations — different type-system trade-offs.

This document focuses on what Rust forces you to spell out that Python leaves
implicit.  Each section pairs a Python snippet with its Rust equivalent and
explains the annotations.

## 1. Recursive data: `Box<Term>`

**Python** — recursive types "just work" because everything is a heap-allocated
reference:

```python
@dataclass(frozen=True)
class Abs:
    param: Var
    body: Term          # Term can be Abs, so recursion is fine
```

**Rust** — an `enum` must have a known size at compile time.  A `Term` that
contains another `Term` would be infinite, so we wrap the recursive field in
`Box`, a heap pointer with a fixed size of 8 bytes:

```rust
pub enum Term {
    Var(String),
    Abs { param: String, body: Box<Term> },   // Box = heap pointer
    App { func: Box<Term>, arg: Box<Term> },
}
```

`Box<Term>` is Rust's equivalent of Python's implicit pointer — it says "this
value lives on the heap and I own it exclusively."

## 2. References: `&` and `&mut`

Python passes objects by reference automatically.  Rust makes you choose:

| Rust | Meaning | Python equivalent |
|------|---------|-------------------|
| `&Term` | Shared, read-only borrow | Just passing the object |
| `&mut Term` | Exclusive, mutable borrow | Passing + mutating in place |
| `Term` | Ownership transfer (moved) | No direct equivalent |

Most domain functions take `&Term` because they only read:

```rust
// Read-only — just inspects the term
pub fn free_vars(term: &Term) -> HashSet<String>

// Read-only — builds a new term from parts of the old one
pub fn substitute(term: &Term, var: &str, replacement: &Term) -> Term
```

Port methods take `&mut self` because they change internal state:

```rust
pub trait NameRegistry {
    fn bind(&mut self, name: &str, term: Term);  // mutates the registry
    fn lookup(&self, name: &str) -> Option<&Term>;  // read-only
}
```

The `&` / `&mut` split is the core of Rust's borrowing model: you can have many
`&` or one `&mut`, but never both at the same time.

## 3. Ownership and `.clone()`

In Python, frozen dataclasses are freely shared — every assignment is a cheap
reference copy.  In Rust, each value has exactly one owner:

```rust
// Python: return replacement if v == var else v
//   (both `replacement` and `v` can be reused freely)

// Rust: we must .clone() because `replacement` is borrowed, not owned
Term::Var(name) => {
    if name == var {
        replacement.clone()   // create a new owned copy
    } else {
        term.clone()
    }
}
```

Every substitution/reduction step builds a **new tree**, cloning unchanged
subtrees.  This is the simplest correct approach — `Rc<Term>` (reference
counting) could share subtrees, but adds complexity for a learning project.

## 4. `Option<T>` and `Result<T, E>` instead of union types

Python uses `X | None` and `X | Error` as return types, distinguished at
runtime with `isinstance`:

```python
def beta_reduce_step(term: Term) -> Term | None: ...
def parse(source: str) -> Term | ParseError: ...

# Caller:
result = parse(source)
if isinstance(result, ParseError):
    ...
```

Rust uses dedicated types that the compiler enforces:

```rust
pub fn beta_reduce_step(term: &Term) -> Option<Term>
pub fn parse(source: &str, ...) -> Result<Term, ParseError>

// Caller — the ? operator propagates errors automatically:
let term = parse(source, names)?;   // returns Err early if parse fails
```

`Option<T>` is either `Some(value)` or `None`.  `Result<T, E>` is either
`Ok(value)` or `Err(error)`.  You cannot access the inner value without
handling both cases — the compiler rejects code that ignores errors.

## 5. Trait objects: `Box<dyn Trait>`

Python protocols are duck-typed — any object with the right methods satisfies
a `Protocol`:

```python
class ReplService:
    def __init__(self, ui: UserInterface, generator: TermGenerator, ...):
        self._ui = ui   # any object with read_input, display, display_error
```

Rust traits must be explicit, and storing a trait object requires two things:

1. `dyn Trait` — "I don't know the concrete type, only that it implements this
   trait" (dynamic dispatch via vtable, like Python's method resolution)
2. `Box<dyn Trait>` — "...and it lives on the heap, with a known pointer size"

```rust
pub struct ReplService {
    ui: Box<dyn UserInterface>,        // any type implementing UserInterface
    generator: Box<dyn TermGenerator>,
    registry: Box<dyn NameRegistry>,
    config: ReplConfig,
}
```

Without `dyn`, Rust would use **generics** (static dispatch, monomorphized at
compile time) — making `ReplService<U, G, R>` generic over three types.
`Box<dyn Trait>` trades a tiny runtime cost (~1 pointer indirection) for simpler
code and mirrors the Python approach.

## 6. `&dyn Fn` for closures

The `fold` catamorphism takes function arguments.  In Python, any `Callable`
works:

```python
def fold(term, on_var, on_abs, on_app): ...

# Called with lambdas:
fold(term, on_var=lambda v: {v}, on_abs=lambda p, body: body - {p}, ...)
```

In Rust, each closure has a **unique anonymous type**, so we use trait objects
to accept any closure with the right signature:

```rust
pub fn fold<R>(
    term: &Term,
    on_var: &dyn Fn(&str) -> R,      // reference to any closure: &str -> R
    on_abs: &dyn Fn(&str, R) -> R,
    on_app: &dyn Fn(R, R) -> R,
) -> R

// Called with closures prefixed by &:
fold(term, &|name| ..., &|param, body| ..., &|f, a| ...)
```

`&dyn Fn(A) -> R` means "a reference to any callable thing that takes `A` and
returns `R`."  The `&` is needed because trait objects are unsized — you can't
hold them on the stack directly.

## 7. Lifetimes: `'a`

Python objects live as long as something references them (garbage collection).
Rust has no GC — references must not outlive the data they point to:

```rust
struct Parser<'a> {
    chars: Vec<char>,
    pos: usize,
    names: &'a HashMap<String, Term>,  // borrowed from caller
    ...
}
```

`'a` is a **lifetime parameter** — it says "this `Parser` borrows `names` and
must not outlive the `HashMap` it points to."  The compiler enforces this at
every call site.  Most of the codebase avoids lifetimes by using owned data
(`String`, `Vec`, `HashMap`).  The parser is the one place where borrowing
(avoiding a clone of the entire names map) was worth the annotation.

## 8. `PhantomData<T>` for phantom types

Python uses `Generic[T]` where `T` is a type variable that's never stored:

```python
@dataclass(frozen=True)
class Meter(Generic[T]):
    value: int
# Meter[Size] vs Meter[Depth] — only the type checker distinguishes them
```

Rust generics require the type parameter to actually appear in the struct.
`PhantomData<T>` is a zero-sized marker that satisfies this requirement without
using any memory:

```rust
pub struct Meter<T> {
    pub value: usize,
    _marker: PhantomData<T>,   // 0 bytes, exists only for the type system
}

pub struct Size;   // zero-sized tag type, never instantiated
```

`Meter<Size>` and `Meter<Depth>` are now different types — you can't pass one
where the other is expected, and the compiler enforces this at zero cost.

## 9. `#[derive(...)]` — auto-generated trait implementations

Python's `@dataclass(frozen=True)` gives you `__eq__`, `__hash__`, and
`__repr__` for free.  Rust's equivalent is `#[derive]`:

```rust
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Term { ... }
```

| Derive | Python equivalent | What it does |
|--------|-------------------|--------------|
| `Debug` | `__repr__` | `{:?}` formatting for debugging |
| `Clone` | (implicit copy) | `.clone()` to create a deep copy |
| `PartialEq` + `Eq` | `__eq__` | `==` structural comparison |
| `Hash` | `__hash__` | usable as `HashSet`/`HashMap` key |

Without `Clone`, you can't duplicate a `Term`.  Without `PartialEq`, you can't
compare two terms with `==`.  Rust makes you opt in to each capability.

## 10. `Display` instead of `stringify`

Python uses a standalone function:

```python
def stringify(term: Term) -> str:
    return fold(term, on_var=lambda v: v.name, ...)
```

Rust uses the `Display` trait, making `format!("{}", term)` and
`term.to_string()` work everywhere:

```rust
impl fmt::Display for Term {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Term::Var(name) => write!(f, "{}", name),
            Term::Abs { param, body } => write!(f, "λ{}.{}", param, body),
            Term::App { func, arg } => write!(f, "({} {})", func, arg),
        }
    }
}
```

`&self` = read-only borrow of the term.  `&mut fmt::Formatter<'_>` = mutable
borrow of the output buffer being written to.  `'_` = "the compiler can figure
out this lifetime, I don't need to name it."

## Summary table

| Concept | Python | Rust | Why |
|---------|--------|------|-----|
| Recursive type | Implicit (heap refs) | `Box<Term>` | Fixed-size requirement |
| Read-only access | Default | `&Term` | Borrowing model |
| Mutation | Default | `&mut self` | Exclusive access guarantee |
| Copy/share | Implicit | `.clone()` | Single ownership |
| Nullable return | `X \| None` | `Option<X>` | Compiler-checked exhaustive handling |
| Error return | `X \| Error` | `Result<X, E>` | Compiler-checked, `?` propagation |
| Runtime polymorphism | `Protocol` (duck typing) | `Box<dyn Trait>` | Vtable dispatch, explicit |
| Higher-order functions | `Callable` | `&dyn Fn(A) -> R` | Closures have unique types |
| Borrowed data | GC keeps it alive | `'a` lifetime | No GC, compiler-checked |
| Phantom generics | `Generic[T]` | `PhantomData<T>` | Type param must appear in struct |
| Auto-generated methods | `@dataclass` | `#[derive(...)]` | Opt-in per capability |
| String conversion | `stringify()` function | `impl Display` | Integrates with `format!`, `println!` |
