#!/usr/bin/env python3
"""Generate a Mermaid.js diagram of SQL table dependencies.

Scans SQL files under the tables directory, parses CREATE/INSERT/MERGE
statements to discover table dependencies, and renders a Mermaid diagram
as a Markdown file.

Usage:
    python generate.py [--sql-root PATH] [--output PATH]
"""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from implementations import (
    DependencyGraphBuilder,
    GlobSqlFileDiscoverer,
    RegexSqlParser,
)
from renderer import MermaidRenderer

DEFAULT_SQL_ROOT = SCRIPT_DIR.parent.parent / "src" / "databases" / "tables"
DEFAULT_OUTPUT = SCRIPT_DIR.parent / "diagram_tables.md"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Namespace with sql_root and output paths.
    """
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
    return parser.parse_args()


def run(sql_root: Path, output: Path, *, dry_run: bool = False) -> None:
    """Discover, parse, build graph, and render diagram.

    Args:
        sql_root: Root directory containing SQL files.
        output: Path to write the Markdown output.
        dry_run: If True, print to stdout instead of writing the file.
    """
    discoverer = GlobSqlFileDiscoverer()
    parser = RegexSqlParser()
    builder = DependencyGraphBuilder(sql_root=sql_root)
    renderer = MermaidRenderer()

    paths = discoverer.discover(sql_root)
    print(f"Discovered {len(paths)} SQL files under {sql_root}")

    all_statements = []
    for path in paths:
        content = path.read_text(encoding="utf-8")
        statements = parser.parse(content, path)
        all_statements.extend(statements)
    print(f"Parsed {len(all_statements)} actionable statements")

    graph = builder.build(all_statements)
    print(f"Graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges")

    markdown = renderer.render(graph)

    if dry_run:
        print(markdown)
        print(f"\n(dry-run) Would write to {output}")
    else:
        output.write_text(markdown, encoding="utf-8")
        print(f"Diagram written to {output}")


def main() -> None:
    """Entry point."""
    args = parse_args()
    run(args.sql_root, args.output, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
