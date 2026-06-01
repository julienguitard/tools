"""Data structures for the SQL dependency diagram generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

type TableName = str
"""A fully qualified BigQuery table name, e.g. ``project.dataset.table``."""

type Dataset = str
"""A BigQuery dataset name, e.g. ``atacadao`` or ``atacadao_tmp``."""

type SqlText = str
"""The raw text content of a ``.sql`` file."""

type Markdown = str
"""A Markdown document — the rendered diagram output."""

StatementType = Literal["create", "insert", "merge", "drop", "declare", "other"]
"""A SQL statement kind, classified from its leading keyword."""

WriteStatementType = Literal["create", "insert", "merge"]
"""The subset of statements that write a table and thus produce graph edges."""

Layer = Literal["raw", "bronze", "silver", "gold", "platinum", "operations"]
"""A medallion layer, inferred from a table's source path or name prefix."""

Subgroup = Literal[
    "tmp", "persistent", "core", "ml_model",
    "pipeline_1", "pipeline_2", "pipeline_3", "pipeline_4",
    "shared", "other", "default",
]
"""A sub-classification within a layer."""

Direction = Literal["LR", ""]
"""A Mermaid subgraph layout direction (``""`` inherits the parent's)."""


@dataclass(frozen=True)
class ParsedStatement:
    """One SQL statement extracted from a file.

    Attributes:
        statement_type: Kind of statement. Always a write
            ("create", "insert", "merge") — the parser drops the rest.
        target_table: Fully qualified table written to, or None.
        source_tables: Fully qualified tables read from.
        source_file: Path to the SQL file this came from.
    """

    statement_type: WriteStatementType
    target_table: TableName | None
    source_tables: list[TableName]
    source_file: Path


@dataclass(frozen=True)
class TableNode:
    """A table in the dependency graph.

    Attributes:
        full_name: Fully qualified name
            (e.g. "insight-factory-478617.atacadao.bronze_dim_products").
        short_name: Table name without project/dataset
            (e.g. "bronze_dim_products").
        dataset: BigQuery dataset (e.g. "atacadao", "atacadao_tmp").
        layer: Medallion layer ("raw", "bronze", "silver", "gold",
            "platinum").
        subgroup: Sub-classification within a layer ("tmp", "persistent",
            "core", "ml_model", "pipeline_1", "pipeline_2", "pipeline_3",
            "pipeline_4", "shared").
        is_tmp: True when dataset ends with "_tmp".
    """

    full_name: TableName
    short_name: str
    dataset: Dataset
    layer: Layer
    subgroup: Subgroup
    is_tmp: bool


@dataclass(frozen=True)
class DependencyEdge:
    """A directed dependency between two tables.

    Attributes:
        source: Full name of the table read from.
        target: Full name of the table written to.
        edge_type: How the target is written ("create", "insert", "merge").
    """

    source: TableName
    target: TableName
    edge_type: WriteStatementType


@dataclass(frozen=True)
class DependencyGraph:
    """Complete dependency graph of the pipeline.

    Attributes:
        nodes: Mapping of full_name to TableNode.
        edges: List of directed dependency edges.
    """

    nodes: dict[TableName, TableNode] = field(default_factory=dict)
    edges: list[DependencyEdge] = field(default_factory=list)


@dataclass(frozen=True)
class SubgraphConfig:
    """Rendering configuration for a Mermaid subgraph.

    Attributes:
        id: Mermaid subgraph identifier (e.g. "BRONZE_TMP").
        title: Display title (e.g. "Intermediate (tmp)").
        direction: Layout direction ("LR", "" for default).
        fill: CSS fill color.
        stroke: CSS stroke color.
        text_color: CSS text color.
    """

    id: str
    title: str
    direction: Direction
    fill: str
    stroke: str
    text_color: str
