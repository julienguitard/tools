"""Data structures for the SQL dependency diagram generator."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedStatement:
    """One SQL statement extracted from a file.

    Attributes:
        statement_type: Kind of statement ("create", "insert", "merge",
            "drop", "declare", "other").
        target_table: Fully qualified table written to, or None.
        source_tables: Fully qualified tables read from.
        source_file: Path to the SQL file this came from.
    """

    statement_type: str
    target_table: str | None
    source_tables: list[str]
    source_file: Path


@dataclass
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

    full_name: str
    short_name: str
    dataset: str
    layer: str
    subgroup: str
    is_tmp: bool


@dataclass
class DependencyEdge:
    """A directed dependency between two tables.

    Attributes:
        source: Full name of the table read from.
        target: Full name of the table written to.
        edge_type: How the target is written ("create", "insert", "merge").
    """

    source: str
    target: str
    edge_type: str


@dataclass
class DependencyGraph:
    """Complete dependency graph of the pipeline.

    Attributes:
        nodes: Mapping of full_name to TableNode.
        edges: List of directed dependency edges.
    """

    nodes: dict[str, TableNode] = field(default_factory=dict)
    edges: list[DependencyEdge] = field(default_factory=list)


@dataclass
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
    direction: str
    fill: str
    stroke: str
    text_color: str
