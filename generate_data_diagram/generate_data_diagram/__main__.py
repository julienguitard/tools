"""CLI entry point — python -m generate_data_diagram."""

from __future__ import annotations

import argparse
from pathlib import Path

from .service import make_diagram_generator

_SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SQL_ROOT = _SCRIPT_DIR.parent.parent / "src" / "databases" / "tables"
DEFAULT_OUTPUT = _SCRIPT_DIR.parent / "diagram_tables.md"


def main() -> None:
    """Parse CLI arguments and run the diagram generator."""
    parser = argparse.ArgumentParser(
        description="Generate Mermaid.js SQL dependency diagram.",
    )
    parser.add_argument(
        "--sql-root",
        type=Path,
        default=DEFAULT_SQL_ROOT,
        help=f"Root of SQL tables directory (default: {DEFAULT_SQL_ROOT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output Markdown file path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print diagram to stdout without writing the output file.",
    )
    args = parser.parse_args()

    generator = make_diagram_generator(sql_root=args.sql_root)
    graph = generator.plan(args.sql_root)
    generator.execute(graph, args.output, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
