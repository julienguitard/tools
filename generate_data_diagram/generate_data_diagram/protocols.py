"""Protocol definitions for the SQL dependency diagram generator."""

from pathlib import Path
from typing import Protocol

from data_types import DependencyGraph, ParsedStatement


class SqlFileDiscoverer(Protocol):
    """Discovers SQL files in a directory tree."""

    def discover(self, root: Path) -> list[Path]:
        """Return all SQL file paths under *root*.

        Args:
            root: Directory to scan recursively.

        Returns:
            Sorted list of .sql file paths.
        """
        ...


class SqlParser(Protocol):
    """Parses SQL content into structured statements."""

    def parse(self, content: str, file_path: Path) -> list[ParsedStatement]:
        """Parse SQL content into a list of statements.

        Args:
            content: Raw SQL file content.
            file_path: Path of the SQL file (for provenance).

        Returns:
            List of parsed statements with targets and sources.
        """
        ...


class GraphBuilder(Protocol):
    """Builds a dependency graph from parsed statements."""

    def build(self, statements: list[ParsedStatement]) -> DependencyGraph:
        """Aggregate statements into a dependency graph.

        Args:
            statements: All parsed statements from all SQL files.

        Returns:
            Graph with nodes (tables) and edges (dependencies).
        """
        ...


class DiagramRenderer(Protocol):
    """Renders a dependency graph as a Mermaid diagram."""

    def render(self, graph: DependencyGraph) -> str:
        """Produce a complete Markdown document with Mermaid diagram.

        Args:
            graph: The dependency graph to render.

        Returns:
            Markdown string with embedded Mermaid code block.
        """
        ...
