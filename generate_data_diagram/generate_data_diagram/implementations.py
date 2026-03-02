"""Concrete implementations for SQL discovery, parsing, and graph building."""

import re
from pathlib import Path

from data_types import (
    DependencyEdge,
    DependencyGraph,
    ParsedStatement,
    TableNode,
)

# ─── Constants ───────────────────────────────────────────────────────────────

TABLE_RE = re.compile(
    r"`(insight-factory-478617\.(\w+)\.(\w+))`"
)
"""Matches fully qualified BigQuery table references in backticks.
Groups: (1) full_name, (2) dataset, (3) table_name.
"""

EXCLUDED_DIRS = {"shared", "mockup", "_moved_or_deprecated"}
"""Subdirectories to skip during SQL file discovery."""

LAYER_DIRS = ("bronze", "silver", "gold", "platinum", "raw", "operations")
"""Known layer directory names in the tables/ tree."""

LAYER_PREFIXES = (
    "bronze_", "silver_", "gold_", "platinum_", "raw_",
)
"""Table name prefixes used to infer layer when no source file exists."""


# ═════════════════════════════════════════════════════════════════════════════
# 1. File Discovery
# ═════════════════════════════════════════════════════════════════════════════


class GlobSqlFileDiscoverer:
    """Discovers .sql files recursively, excluding non-table directories."""

    def discover(self, root: Path) -> list[Path]:
        """Return all .sql file paths under *root*, sorted.

        Args:
            root: Directory to scan recursively.

        Returns:
            Sorted list of .sql file paths.
        """
        return sorted(
            p for p in root.rglob("*.sql")
            if not self._is_excluded(p)
        )

    @staticmethod
    def _is_excluded(path: Path) -> bool:
        """Check if a path falls inside an excluded directory.

        Args:
            path: File path to check.

        Returns:
            True if any parent directory is in EXCLUDED_DIRS.
        """
        return any(part in EXCLUDED_DIRS for part in path.parts)


# ═════════════════════════════════════════════════════════════════════════════
# 2. SQL Parsing
# ═════════════════════════════════════════════════════════════════════════════


class RegexSqlParser:
    """Parses SQL files using regex to extract table dependencies."""

    def parse(self, content: str, file_path: Path) -> list[ParsedStatement]:
        """Parse SQL content into structured statements.

        Args:
            content: Raw SQL file content.
            file_path: Path of the SQL file (for provenance).

        Returns:
            List of ParsedStatement, one per actionable statement.
        """
        cleaned = strip_comments(content)
        raw_stmts = split_statements(cleaned)
        results: list[ParsedStatement] = []
        for stmt in raw_stmts:
            stype = classify_statement(stmt)
            if stype in ("drop", "declare", "other"):
                continue
            target = extract_target(stmt, stype)
            if target is None:
                continue
            all_tables = extract_all_tables(stmt)
            sources = compute_sources(all_tables, target)
            results.append(ParsedStatement(
                statement_type=stype,
                target_table=target,
                source_tables=sources,
                source_file=file_path,
            ))
        return results


# ─── Atomic parsing functions ────────────────────────────────────────────────


def strip_comments(sql: str) -> str:
    """Remove SQL comments from content.

    Handles both single-line (--) and multi-line (/* ... */) comments.

    Args:
        sql: Raw SQL string.

    Returns:
        SQL with all comments removed.
    """
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql


def split_statements(sql: str) -> list[str]:
    """Split SQL content into individual statements on semicolons.

    Args:
        sql: Comment-free SQL string.

    Returns:
        List of non-empty statement strings.
    """
    return [s.strip() for s in sql.split(";") if s.strip()]


def classify_statement(stmt: str) -> str:
    """Classify a SQL statement by its leading keyword.

    Args:
        stmt: A single SQL statement (no leading comments).

    Returns:
        One of "create", "insert", "merge", "drop", "declare", "other".
    """
    keyword_map = {
        "CREATE": "create",
        "INSERT": "insert",
        "MERGE": "merge",
        "DROP": "drop",
        "DECLARE": "declare",
    }
    words = stmt.split()
    if not words:
        return "other"
    first = words[0].upper()
    return keyword_map.get(first, "other")


def extract_target(stmt: str, statement_type: str) -> str | None:
    """Extract the target table from a DDL/DML statement.

    Args:
        stmt: SQL statement text.
        statement_type: Result of classify_statement().

    Returns:
        Fully qualified table name, or None if not found.
    """
    patterns = {
        "create": r"CREATE\s+(?:OR\s+REPLACE\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`([^`]+)`",
        "insert": r"INSERT\s+INTO\s+`([^`]+)`",
        "merge": r"MERGE\s+`([^`]+)`",
    }
    pattern = patterns.get(statement_type)
    if pattern is None:
        return None
    match = re.search(pattern, stmt, re.IGNORECASE)
    return match.group(1) if match else None


def extract_all_tables(stmt: str) -> list[str]:
    """Extract all fully qualified table references from a statement.

    Args:
        stmt: SQL statement text.

    Returns:
        List of fully qualified table names (may contain duplicates).
    """
    return [m.group(1) for m in TABLE_RE.finditer(stmt)]


def compute_sources(all_tables: list[str], target: str) -> list[str]:
    """Compute source tables by removing the target from all references.

    Args:
        all_tables: Every table reference found in the statement.
        target: The target table to exclude.

    Returns:
        Deduplicated list of source table names.
    """
    seen: set[str] = set()
    sources: list[str] = []
    for t in all_tables:
        if t != target and t not in seen:
            seen.add(t)
            sources.append(t)
    return sources


# ═════════════════════════════════════════════════════════════════════════════
# 3. Graph Building
# ═════════════════════════════════════════════════════════════════════════════


class DependencyGraphBuilder:
    """Builds a DependencyGraph from parsed statements."""

    def __init__(self, sql_root: Path | None = None):
        """Initialize the builder.

        Args:
            sql_root: Root path of the SQL tables directory, used for
                layer/subgroup inference from file paths.
        """
        self._sql_root = sql_root

    def build(self, statements: list[ParsedStatement]) -> DependencyGraph:
        """Aggregate statements into a dependency graph.

        Args:
            statements: All parsed statements from all SQL files.

        Returns:
            Graph with nodes and edges.
        """
        graph = DependencyGraph()
        target_files = _build_target_files(statements)
        seen_edges: set[tuple[str, str, str]] = set()
        for ps in statements:
            if ps.target_table is None:
                continue
            self._ensure_node(graph, ps.target_table, target_files)
            for src in ps.source_tables:
                self._ensure_node(graph, src, target_files)
                edge_key = (src, ps.target_table, ps.statement_type)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    graph.edges.append(DependencyEdge(
                        source=src,
                        target=ps.target_table,
                        edge_type=ps.statement_type,
                    ))
        return graph

    def _ensure_node(
        self,
        graph: DependencyGraph,
        full_name: str,
        target_files: dict[str, Path],
    ) -> None:
        """Add a TableNode to the graph if not already present.

        Args:
            graph: Graph to add the node to.
            full_name: Fully qualified table name.
            target_files: Mapping of table names to their creating SQL file.
        """
        if full_name in graph.nodes:
            return
        parts = full_name.split(".")
        dataset = parts[1] if len(parts) >= 3 else ""
        short_name = parts[2] if len(parts) >= 3 else full_name
        source_file = target_files.get(full_name)
        layer = infer_layer(short_name, source_file, self._sql_root)
        subgroup = infer_subgroup(layer, dataset, source_file, self._sql_root)
        graph.nodes[full_name] = TableNode(
            full_name=full_name,
            short_name=short_name,
            dataset=dataset,
            layer=layer,
            subgroup=subgroup,
            is_tmp=dataset.endswith("_tmp"),
        )


def _build_target_files(
    statements: list[ParsedStatement],
) -> dict[str, Path]:
    """Map each table to the SQL file that defines it.

    CREATE statements take priority over INSERT/MERGE so that the
    originating file (not a downstream inserter) drives classification.

    Args:
        statements: All parsed statements.

    Returns:
        Mapping of fully qualified table name to source file path.
    """
    target_files: dict[str, Path] = {}
    create_seen: set[str] = set()
    for ps in statements:
        if ps.target_table is None:
            continue
        if ps.statement_type == "create":
            target_files[ps.target_table] = ps.source_file
            create_seen.add(ps.target_table)
        elif ps.target_table not in create_seen:
            target_files.setdefault(ps.target_table, ps.source_file)
    return target_files


# ─── Classification helpers ─────────────────────────────────────────────────


def infer_layer(
    short_name: str,
    source_file: Path | None,
    sql_root: Path | None,
) -> str:
    """Determine the medallion layer of a table.

    Priority: (1) directory path of creating SQL file, (2) table name prefix,
    (3) fallback to "raw".

    Args:
        short_name: Table name without project/dataset prefix.
        source_file: Path to the SQL file that creates this table, if any.
        sql_root: Root of the SQL tables directory tree.

    Returns:
        Layer string: "raw", "bronze", "silver", "gold", or "platinum".
    """
    if source_file is not None:
        rel = _relative_parts(source_file, sql_root)
        for layer_dir in LAYER_DIRS:
            if layer_dir in rel:
                return layer_dir
    for prefix in LAYER_PREFIXES:
        if short_name.startswith(prefix):
            return prefix.rstrip("_")
    return "raw"


def infer_subgroup(
    layer: str,
    dataset: str,
    source_file: Path | None,
    sql_root: Path | None,
) -> str:
    """Determine the subgroup within a layer.

    Args:
        layer: Medallion layer (from infer_layer).
        dataset: BigQuery dataset name.
        source_file: Path to the creating SQL file, if any.
        sql_root: Root of the SQL tables directory tree.

    Returns:
        Subgroup string (e.g. "tmp", "persistent", "core", "pipeline_1").
    """
    rel = _relative_parts(source_file, sql_root) if source_file else ()

    if layer == "bronze":
        return "tmp" if dataset.endswith("_tmp") else "persistent"

    if layer == "silver":
        if "ml_model" in rel:
            return "ml_model"
        return "core"

    if layer == "gold":
        for sub in ("pipeline_1", "pipeline_2", "pipeline_3", "ml_model"):
            if sub in rel:
                return sub
        return "other"

    if layer == "platinum":
        for sub in ("pipeline_1", "pipeline_2", "pipeline_4"):
            if sub in rel:
                return sub
        return "shared"

    return "default"


def _relative_parts(
    file_path: Path | None,
    sql_root: Path | None,
) -> tuple[str, ...]:
    """Get path parts relative to sql_root.

    Args:
        file_path: Absolute file path.
        sql_root: Root directory to compute relative path from.

    Returns:
        Tuple of path component strings, or empty tuple.
    """
    if file_path is None or sql_root is None:
        return ()
    try:
        return file_path.relative_to(sql_root).parts
    except ValueError:
        return file_path.parts
