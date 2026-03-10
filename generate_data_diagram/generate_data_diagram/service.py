"""Orchestration: depends only on ports, never on adapters."""

from __future__ import annotations

from pathlib import Path

from .data_types import DependencyGraph, ParsedStatement
from .protocols import DiagramRenderer, GraphBuilder, SqlFileDiscoverer, SqlParser


class DiagramGenerator:
    """Discover, parse, build graph, and render SQL dependency diagrams."""

    def __init__(
        self,
        discoverer: SqlFileDiscoverer,
        parser: SqlParser,
        builder: GraphBuilder,
        renderer: DiagramRenderer,
    ) -> None:
        self._discoverer = discoverer
        self._parser = parser
        self._builder = builder
        self._renderer = renderer

    # -- planning (read-only) ------------------------------------------------

    def plan(self, sql_root: Path) -> DependencyGraph:
        """Discover SQL files, parse statements, and build the graph.

        Args:
            sql_root: Root directory containing SQL files.

        Returns:
            The constructed dependency graph.
        """
        paths = self._discoverer.discover(sql_root)
        print(f"Discovered {len(paths)} SQL files under {sql_root}")

        all_statements: list[ParsedStatement] = []
        for path in paths:
            content = path.read_text(encoding="utf-8")
            statements = self._parser.parse(content, path)
            all_statements.extend(statements)
        print(f"Parsed {len(all_statements)} actionable statements")

        graph = self._builder.build(all_statements)
        print(f"Graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
        return graph

    # -- execution (writes) --------------------------------------------------

    def execute(
        self,
        graph: DependencyGraph,
        output: Path,
        *,
        dry_run: bool = False,
    ) -> None:
        """Render the graph and write the output file.

        Args:
            graph: The dependency graph to render.
            output: Path to write the Markdown output.
            dry_run: If True, print to stdout instead of writing the file.
        """
        markdown = self._renderer.render(graph)

        if dry_run:
            print(markdown)
            print(f"\n(dry-run) Would write to {output}")
        else:
            output.write_text(markdown, encoding="utf-8")
            print(f"Diagram written to {output}")


def make_diagram_generator(sql_root: Path) -> DiagramGenerator:
    """Wire concrete adapters into the service.

    Args:
        sql_root: Root of the SQL tables directory (passed to the builder).

    Returns:
        Configured DiagramGenerator instance.
    """
    from .adapters import (
        DependencyGraphBuilder,
        GlobSqlFileDiscoverer,
        MermaidRenderer,
        RegexSqlParser,
    )

    return DiagramGenerator(
        discoverer=GlobSqlFileDiscoverer(),
        parser=RegexSqlParser(),
        builder=DependencyGraphBuilder(sql_root=sql_root),
        renderer=MermaidRenderer(),
    )
