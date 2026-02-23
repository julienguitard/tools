# CLAUDE.md — tools monorepo

## Repository structure

This is a **monorepo** of standalone CLI tools. Each subfolder is an independent project with its own `README.md`, `Makefile`, `requirements.txt`, and virtual environment.

```
tools/
├── .claude/              # Claude Code config (skills, CLAUDE.md)
├── rename-papers/        # PDF renaming tool (reference implementation)
└── <future-tool>/        # Same layout as rename-papers
```

## Architecture — Hexagonal (Ports & Adapters)

Every tool follows the **hexagonal architecture** pattern established by `rename-papers/`:

```
tool_name/
├── __main__.py           # CLI entry point (argparse)
├── domain.py             # Pure domain models — no IO, no side effects
├── ports.py              # Abstract protocols (typing.Protocol)
├── service.py            # Orchestration — depends ONLY on ports
└── adapters/             # Concrete implementations of ports
    ├── __init__.py       # Re-exports with __all__
    └── *.py              # One file per adapter
```

### Layer rules

| Layer | May import | Must NOT import |
|-------|-----------|-----------------|
| `domain.py` | stdlib only | ports, adapters, service |
| `ports.py` | stdlib, domain | adapters, service |
| `service.py` | stdlib, domain, ports | adapters (injected via constructor) |
| `adapters/` | stdlib, domain, ports, third-party libs | service |
| `__main__.py` | everything | — (composition root) |

### Key patterns

- **Composition root** in `service.py` (`make_*()` factory) or `__main__.py` — wires adapters into the service.
- **Plan-then-execute** — services expose a read-only `plan()` and a side-effectful `execute()`.
- **Frozen dataclasses** for domain models (`@dataclass(frozen=True)`).
- **Protocols** for IO boundaries — enables testing via substitution.
- **Static factory methods** on domain classes (`ClassName.from_path()`, `ClassName.skip()`).

## Coding style

### Python conventions

- `from __future__ import annotations` at the top of every file.
- Type hints on all public signatures.
- Google-style docstrings (see `.claude/skills/docstring.md`).
- Module-level docstrings on every `.py` file.
- Snake_case for modules, functions, variables; PascalCase for classes.
- Private attributes use single underscore prefix (`_fs`, `_reader`).
- Lazy imports for heavy third-party libs inside adapter methods.
- Explicit `__all__` in adapter `__init__.py`.

### Section markers in service code

```python
# -- planning (read-only) ------------------------------------------------
# -- execution (writes) --------------------------------------------------
```

### Naming conventions

- Adapters: named after the concrete tech (`PyMuPdfReader`, `OpenAiSlugGenerator`).
- Ports: named after the capability (`PdfReader`, `SlugGenerator`).
- Domain models: named after the business concept (`PaperFile`, `RenameAction`).

## Project setup & automation

Each subfolder has a `Makefile` with standard targets:

| Target | Purpose |
|--------|---------|
| `make setup` | Create venv, install deps, copy `env.example` → `.env` |
| `make run` | Execute the tool |
| `make dry-run` | Preview without side effects |
| `make clean` | Remove venv and `__pycache__` |

## Skills

Custom skills are defined in `.claude/skills/`:

- [`commit.md`](.claude/skills/commit.md) — Conventional commit messages (`type(scope): subject`).
- [`docstring.md`](.claude/skills/docstring.md) — Google-style Python docstrings.
- [`subfolder_doc.md`](.claude/skills/subfolder_doc.md) — README.md generation for subfolders.

## Commit conventions

Follow **Conventional Commits** (see `commit.md` skill for full spec):

```
<type>(<scope>): <subject>
```

- Types: `feat`, `fix`, `refactor`, `docs`, `style`, `test`, `chore`, `perf`, `build`
- Scope: tool name or module (e.g., `rename-papers`, `domain`)
- Subject: imperative mood, lowercase, no period, max 50 chars
