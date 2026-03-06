# CLAUDE.md — tools monorepo

## Repository structure

This is a **monorepo** of standalone CLI tools. Each subfolder is an independent project with its own `README.md`, `Makefile`, `requirements.txt`, and virtual environment.

```
tools/
├── .claude/                            # Claude Code config (skills, CLAUDE.md)
├── rename-papers/                      # PDF renaming via LLM-generated slugs
├── extract-from-chrome-to-supabase/    # Chrome tab extraction & categorization
├── query-prolog/                       # Interactive Prolog REPL with NL fallback
├── generate_data_diagram/              # SQL dependency diagram generator
└── <future-tool>/                      # Same layout
```

## Architecture — Hexagonal (Ports & Adapters)

Every tool follows the **hexagonal architecture** pattern:

```
tool_name/
├── __main__.py           # CLI entry point (argparse + dotenv)
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

- **Composition root** — a `make_*()` factory in `service.py` (or `__main__.py`) wires adapters into the service.
- **Frozen dataclasses** for domain models (`@dataclass(frozen=True)`).
- **Protocols** (`typing.Protocol`) for all IO boundaries — enables testing via substitution. Port method signatures should use domain types for arguments and return values whenever possible.
- **Domain class methods** — static factories (`ClassName.from_path()`, `ClassName.skip()`) and serialization helpers (`to_dict()`, `to_row()`).
- **Lazy imports** — heavy third-party libs (openai, fitz, httpx) are imported inside adapter methods, not at module level.
- **Minimal dependencies** — each tool imports only what it needs; some are stdlib-only.

### Optional patterns (use when appropriate)

- **Service as port orchestration** — service methods read as high-level scripts that compose port calls; the ports form a domain-specific vocabulary that the service "narrates."
- **Plan-then-execute** — When **relevant** service exposes a read-only `plan()` and a side-effectful `execute()`; enables dry-run previews (see `rename-papers`).
- **Chained adapters** — compose multiple implementations behind a single port (e.g., keyword heuristic → AI fallback in `extract-from-chrome-to-supabase`).
- **Interactive ports** — a `UserInterface` / `UserPrompter` protocol abstracts CLI interaction for REPL or multi-step workflows (see `query-prolog`, `extract-from-chrome-to-supabase`).

### Environment configuration

- All tools use `.env` + `python-dotenv` (loaded in `__main__.py`).
- Common variables: `AI_PROVIDER`, `AI_MODEL`, `AI_API_KEY`, `AI_API_KEY`, `SUPABASE_*`.
- Each tool ships an `.env.example` with all required keys.

## Coding style

### Python conventions

- `from __future__ import annotations` at the top of every file.
- Type hints on all public signatures.
- Google-style docstrings (see `.claude/skills/docstring.md`).
- Module-level docstrings on every `.py` file.
- Snake_case for modules, functions, variables; PascalCase for classes.
- Private attributes use single underscore prefix (`_fs`, `_reader`).
- Explicit `__all__` in adapter `__init__.py`.

### Section markers in service code

```python
# -- planning (read-only) ------------------------------------------------
# -- execution (writes) --------------------------------------------------
```

### Naming conventions

- **Adapters**: named after the concrete tech (`PyMuPdfReader`, `SwiPrologEngine`, `ChromeAppleScriptSource`).
- **Ports**: named after the capability (`PdfReader`, `PrologEngine`, `TabSource`).
- **Domain models**: named after the business concept (`PaperFile`, `Tab`, `FactFile`).

## Project setup & automation

Each subfolder has a `Makefile` with standard targets:

| Target | Purpose |
|--------|---------|
| `make setup` | Create venv, install deps, copy `.env.example` → `.env` |
| `make run` | Execute the tool (env vars loaded from `.env`) |
| `make dry-run` | Preview without side effects (when plan-then-execute is used) |
| `make clean` | Remove venv and `__pycache__` |

## Documentation

Each tool and its code are documented at three levels:

| Level | What | Governed by |
|-------|------|-------------|
| **Tool README** | Purpose, usage, setup instructions per subfolder | [`subfolder_doc`](.claude/skills/subfolder_doc/SKILL.md) skill |
| **Docstrings** | Module, class, and function documentation (Google style) | [`docstring`](.claude/skills/docstring/SKILL.md) skill |
| **Commit messages** | Change history (Conventional Commits) | [`commit`](.claude/skills/commit/SKILL.md) skill |

### When to generate docs

- **New tool** → create `README.md` via `subfolder_doc` skill.
- **New / changed public API** → add or update docstrings via `docstring` skill.
- **Every commit** → use `commit` skill for message formatting.

## Skills

Custom skills are defined in `.claude/skills/`:

- [`commit`](.claude/skills/commit/SKILL.md) — Conventional commit messages (`type(scope): subject`).
- [`docstring`](.claude/skills/docstring/SKILL.md) — Google-style Python docstrings.
- [`subfolder_doc`](.claude/skills/subfolder_doc/SKILL.md) — README.md generation for subfolders.
- [`ux-flow`](.claude/skills/ux-flow/SKILL.md) — UX flow diagrams as Mermaid flowcharts.

## Commit conventions

Follow **Conventional Commits** (see `commit.md` skill for full spec):

```
<type>(<scope>): <subject>
```

- Types: `feat`, `fix`, `refactor`, `docs`, `style`, `test`, `chore`, `perf`, `build`
- Scope: tool name or module (e.g., `rename-papers`, `domain`)
- Subject: imperative mood, lowercase, no period, max 50 chars
