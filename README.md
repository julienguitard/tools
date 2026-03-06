# tools

A monorepo of standalone Python CLI tools, each following **hexagonal architecture** (ports & adapters).

## Tools

| Tool | Description |
|------|-------------|
| [rename-papers](rename-papers/) | Rename research paper PDFs with AI-generated semantic slugs |
| [extract-from-chrome-to-supabase](extract-from-chrome-to-supabase/) | Interactive Chrome tab curation with keyword + AI categorization, saved to Supabase |
| [query-prolog](query-prolog/) | REPL for Prolog fact files with natural language query support |
| [generate_data_diagram](generate_data_diagram/) | SQL dependency scanner that renders Mermaid data pipeline diagrams |

## Quick start

```bash
# Set up all tools at once
make setup

# Or set up a single tool
cd rename-papers && make setup
```

All tools share a single `.env` at the repo root (see [.env.example](.env.example)).

## Architecture

Every tool follows the same package layout:

```
tool_name/
├── __main__.py       # CLI entry point (argparse + dotenv)
├── domain.py         # Pure domain models (frozen dataclasses)
├── ports.py          # Abstract protocols (typing.Protocol)
├── service.py        # Orchestration (depends only on ports)
└── adapters/         # Concrete implementations
```

**Layer rules:** domain has no dependencies, ports depend on domain, service depends on ports (adapters injected), adapters implement ports using third-party libs.

See each tool's README for protocols, types, UX flow diagrams, and usage details.

## Makefile targets

Each tool provides a consistent set of targets:

| Target | Description |
|--------|-------------|
| `make setup` | Create venv and install dependencies |
| `make run` | Run the tool |
| `make dry-run` | Preview without side effects (where applicable) |
| `make clean` | Remove venv and caches |

## License

MIT
