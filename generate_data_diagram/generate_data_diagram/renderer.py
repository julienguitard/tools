"""Mermaid.js diagram renderer — pure formatting, no SQL knowledge."""

from data_types import DependencyGraph, SubgraphConfig, TableNode

# ─── Subgraph layout configuration ──────────────────────────────────────────
# Nesting structure mirrors the medallion architecture.
# Content (which nodes go where) is resolved dynamically from the graph.

SUBGRAPH_CONFIGS: dict[str, SubgraphConfig] = {
    "raw_default": SubgraphConfig(
        "RAW", "Raw Layer \u2014 External Sources", "LR",
        "#e8d5b7", "#b8860b", "#333",
    ),
    "bronze_tmp": SubgraphConfig(
        "BRONZE_TMP", "Intermediate (tmp)", "LR",
        "#f5e6d3", "#cd7f32", "#555",
    ),
    "bronze_persistent": SubgraphConfig(
        "BRONZE_PERSIST", "Persistent", "LR",
        "#cd7f32", "#8b5a2b", "#fff",
    ),
    "silver_core": SubgraphConfig(
        "SILVER_CORE", "Core", "LR",
        "#c0c0c0", "#808080", "#333",
    ),
    "silver_ml_model": SubgraphConfig(
        "SILVER_MLM", "ML Model", "LR",
        "#c0c0c0", "#808080", "#333",
    ),
    "gold_pipeline_1": SubgraphConfig(
        "GOLD_Pipeline 1", "Pipeline 1 \u2014 Market Share Anomalies", "LR",
        "#ffd700", "#daa520", "#333",
    ),
    "gold_pipeline_2": SubgraphConfig(
        "GOLD_Pipeline 2", "Pipeline 2 \u2014 Emerging Trends", "",
        "#ffd700", "#daa520", "#333",
    ),
    "gold_pipeline_3": SubgraphConfig(
        "GOLD_Pipeline 3", "Pipeline 3 \u2014 Seasonality", "",
        "#ffd700", "#daa520", "#333",
    ),
    "gold_ml_model": SubgraphConfig(
        "GOLD_MLM", "ML Model", "",
        "#ffd700", "#daa520", "#333",
    ),
    "platinum_pipeline_1": SubgraphConfig(
        "PLAT_Pipeline 1", "Pipeline 1 Pipeline (tmp)", "LR",
        "#d4edda", "#28a745", "#333",
    ),
    "platinum_pipeline_2": SubgraphConfig(
        "PLAT_Pipeline 2", "Pipeline 2 Pipeline (tmp)", "LR",
        "#d4edda", "#28a745", "#333",
    ),
    "platinum_pipeline_4": SubgraphConfig(
        "PLAT_Pipeline 4", "Pipeline 4 \u2014 Churn", "",
        "#d4edda", "#28a745", "#333",
    ),
    "platinum_shared": SubgraphConfig(
        "PLAT_SHARED", "Shared Opportunity Tables", "LR",
        "#28a745", "#155724", "#fff",
    ),
}

# Ordered nesting: (parent_label, parent_id, children_keys)
NESTING_ORDER: list[tuple[str, str, list[str]]] = [
    ("", "RAW", ["raw_default"]),
    ("Bronze Layer", "BRONZE", ["bronze_tmp", "bronze_persistent"]),
    ("Silver Layer", "SILVER", ["silver_core", "silver_ml_model"]),
    ("Gold Layer", "GOLD", ["gold_pipeline_1", "gold_pipeline_2", "gold_pipeline_3", "gold_ml_model"]),
    (
        "Platinum Layer", "PLAT",
        ["platinum_pipeline_1", "platinum_pipeline_2", "platinum_pipeline_4", "platinum_shared"],
    ),
]


# ═════════════════════════════════════════════════════════════════════════════
# Public API
# ═════════════════════════════════════════════════════════════════════════════


class MermaidRenderer:
    """Renders a DependencyGraph as a Mermaid.js Markdown document."""

    def render(self, graph: DependencyGraph) -> str:
        """Produce the complete Markdown document.

        Args:
            graph: The dependency graph to render.

        Returns:
            Markdown string with embedded Mermaid code block and legend.
        """
        grouped = group_nodes(graph)
        lines: list[str] = []
        lines.append("# Data Pipeline \u2014 Table Dependencies")
        lines.append("")
        lines.append("```mermaid")
        lines.append("graph TD")
        lines.append("")
        lines.extend(render_all_subgraphs(grouped))
        lines.append("")
        lines.extend(render_all_edges(graph))
        lines.append("")
        lines.extend(render_all_styles(grouped))
        lines.append("```")
        lines.append("")
        lines.extend(render_legend())
        return "\n".join(lines) + "\n"


# ═════════════════════════════════════════════════════════════════════════════
# Grouping
# ═════════════════════════════════════════════════════════════════════════════


def group_nodes(
    graph: DependencyGraph,
) -> dict[str, list[TableNode]]:
    """Group graph nodes by their layer_subgroup key.

    Args:
        graph: The dependency graph.

    Returns:
        Mapping of "layer_subgroup" to list of TableNode.
    """
    groups: dict[str, list[TableNode]] = {}
    for node in graph.nodes.values():
        key = f"{node.layer}_{node.subgroup}"
        groups.setdefault(key, []).append(node)
    for nodes in groups.values():
        nodes.sort(key=lambda n: n.short_name)
    return groups


# ═════════════════════════════════════════════════════════════════════════════
# Subgraph rendering
# ═════════════════════════════════════════════════════════════════════════════


def render_all_subgraphs(
    grouped: dict[str, list[TableNode]],
) -> list[str]:
    """Render all subgraph blocks following the nesting order.

    Args:
        grouped: Nodes grouped by layer_subgroup key.

    Returns:
        List of Mermaid lines.
    """
    lines: list[str] = []
    for parent_label, parent_id, children_keys in NESTING_ORDER:
        child_configs = [
            (k, SUBGRAPH_CONFIGS[k])
            for k in children_keys
            if k in grouped
        ]
        if not child_configs:
            continue
        is_raw = parent_id == "RAW"
        if is_raw:
            cfg = SUBGRAPH_CONFIGS[children_keys[0]]
            lines.extend(render_subgraph_open(cfg.id, cfg.title, cfg.direction))
            lines.extend(render_nodes(grouped.get(children_keys[0], [])))
            lines.append(render_subgraph_close())
        else:
            lines.extend(render_subgraph_open(parent_id, parent_label, ""))
            for key, cfg in child_configs:
                lines.append("")
                lines.extend(render_subgraph_open(cfg.id, cfg.title, cfg.direction))
                lines.extend(render_nodes(grouped.get(key, [])))
                lines.append(render_subgraph_close())
            lines.append(render_subgraph_close())
        lines.append("")
    return lines


def render_subgraph_open(sg_id: str, title: str, direction: str) -> list[str]:
    """Emit the opening lines of a Mermaid subgraph.

    Args:
        sg_id: Subgraph identifier.
        title: Display title.
        direction: Layout direction or empty string.

    Returns:
        List of Mermaid lines.
    """
    lines = [f'    subgraph {sg_id}["{title}"]']
    if direction:
        lines.append(f"        direction {direction}")
    return lines


def render_subgraph_close() -> str:
    """Emit the closing line of a Mermaid subgraph.

    Returns:
        Single Mermaid line.
    """
    return "    end"


# ═════════════════════════════════════════════════════════════════════════════
# Node rendering
# ═════════════════════════════════════════════════════════════════════════════


def render_nodes(nodes: list[TableNode]) -> list[str]:
    """Render a list of nodes as Mermaid database (cylinder) shapes.

    Args:
        nodes: List of TableNode to render.

    Returns:
        List of Mermaid lines.
    """
    return [render_db_node(n) for n in nodes]


def render_db_node(node: TableNode) -> str:
    """Render a single database node.

    Args:
        node: The table node.

    Returns:
        Mermaid line: ``node_id[("label")]``.
    """
    node_id = sanitize_id(node.full_name)
    return f'        {node_id}[("{node.short_name}")]'


def sanitize_id(full_name: str) -> str:
    """Convert a fully qualified table name to a valid Mermaid node id.

    Replaces dots and hyphens with underscores.

    Args:
        full_name: Fully qualified table name.

    Returns:
        Sanitized id string.
    """
    return full_name.replace(".", "_").replace("-", "_")


# ═════════════════════════════════════════════════════════════════════════════
# Edge rendering
# ═════════════════════════════════════════════════════════════════════════════


def render_all_edges(graph: DependencyGraph) -> list[str]:
    """Render all edges, grouped by source layer.

    Args:
        graph: The dependency graph.

    Returns:
        List of Mermaid lines.
    """
    lines: list[str] = []
    edges_by_section = _group_edges_by_section(graph)
    for section_label, edges in edges_by_section:
        lines.append(f"    %% {section_label}")
        for edge in edges:
            src_id = sanitize_id(edge.source)
            tgt_id = sanitize_id(edge.target)
            if edge.edge_type == "insert":
                lines.append(render_dashed_edge(src_id, tgt_id, "insert"))
            elif edge.edge_type == "merge":
                lines.append(render_dashed_edge(src_id, tgt_id, "merge"))
            else:
                lines.append(render_solid_edge(src_id, tgt_id))
        lines.append("")
    return lines


def render_solid_edge(source_id: str, target_id: str) -> str:
    """Render a solid arrow (CREATE dependency).

    Args:
        source_id: Sanitized source node id.
        target_id: Sanitized target node id.

    Returns:
        Mermaid line.
    """
    return f"    {source_id} --> {target_id}"


def render_dashed_edge(source_id: str, target_id: str, label: str) -> str:
    """Render a dashed arrow (INSERT/MERGE).

    Args:
        source_id: Sanitized source node id.
        target_id: Sanitized target node id.
        label: Edge label text.

    Returns:
        Mermaid line.
    """
    return f"    {source_id} -.->|{label}| {target_id}"


def _group_edges_by_section(
    graph: DependencyGraph,
) -> list[tuple[str, list]]:
    """Group edges by source-layer to target-layer section.

    Args:
        graph: The dependency graph.

    Returns:
        Ordered list of (section_label, edges) tuples.
    """
    section_map: dict[str, list] = {}
    for edge in graph.edges:
        src_node = graph.nodes.get(edge.source)
        tgt_node = graph.nodes.get(edge.target)
        src_layer = src_node.layer if src_node else "unknown"
        tgt_layer = tgt_node.layer if tgt_node else "unknown"
        label = f"{src_layer} -> {tgt_layer}"
        section_map.setdefault(label, []).append(edge)

    layer_order = {"raw": 0, "bronze": 1, "silver": 2, "gold": 3, "platinum": 4}

    def sort_key(item: tuple[str, list]) -> tuple[int, int]:
        parts = item[0].split(" -> ")
        return (
            layer_order.get(parts[0], 99),
            layer_order.get(parts[1], 99) if len(parts) > 1 else 99,
        )

    return sorted(section_map.items(), key=sort_key)


# ═════════════════════════════════════════════════════════════════════════════
# Style rendering
# ═════════════════════════════════════════════════════════════════════════════


def render_all_styles(
    grouped: dict[str, list[TableNode]],
) -> list[str]:
    """Render classDef and class assignment lines.

    Args:
        grouped: Nodes grouped by layer_subgroup key.

    Returns:
        List of Mermaid lines.
    """
    lines: list[str] = []
    emitted_defs: set[str] = set()
    for key, nodes in grouped.items():
        cfg = SUBGRAPH_CONFIGS.get(key)
        if cfg is None:
            continue
        style_name = _style_name_for(key)
        if style_name not in emitted_defs:
            lines.append(render_class_def(style_name, cfg))
            emitted_defs.add(style_name)
        node_ids = ",".join(sanitize_id(n.full_name) for n in nodes)
        if node_ids:
            lines.append(render_class_assign(style_name, node_ids))
    return lines


def render_class_def(name: str, cfg: SubgraphConfig) -> str:
    """Render a Mermaid classDef line.

    Args:
        name: Style class name.
        cfg: SubgraphConfig with color definitions.

    Returns:
        Mermaid classDef line.
    """
    return f"    classDef {name} fill:{cfg.fill},stroke:{cfg.stroke},color:{cfg.text_color}"


def render_class_assign(class_name: str, node_csv: str) -> str:
    """Render a Mermaid class assignment line.

    Args:
        class_name: Style class name.
        node_csv: Comma-separated node ids.

    Returns:
        Mermaid class line.
    """
    return f"    class {node_csv} {class_name}"


def _style_name_for(group_key: str) -> str:
    """Map a group key to a Mermaid style class name.

    Args:
        group_key: Key like "bronze_tmp", "silver_core".

    Returns:
        Style class name.
    """
    mapping = {
        "raw_default": "rawStyle",
        "bronze_tmp": "bronzeTmpStyle",
        "bronze_persistent": "bronzeStyle",
        "silver_core": "silverStyle",
        "silver_ml_model": "silverStyle",
        "gold_pipeline_1": "goldStyle",
        "gold_pipeline_2": "goldStyle",
        "gold_pipeline_3": "goldStyle",
        "gold_ml_model": "goldStyle",
        "gold_other": "goldStyle",
        "platinum_pipeline_1": "platTmpStyle",
        "platinum_pipeline_2": "platTmpStyle",
        "platinum_pipeline_4": "platTmpStyle",
        "platinum_shared": "platSharedStyle",
    }
    return mapping.get(group_key, "defaultStyle")


# ═════════════════════════════════════════════════════════════════════════════
# Legend
# ═════════════════════════════════════════════════════════════════════════════


def render_legend() -> list[str]:
    """Render the Markdown legend section.

    Returns:
        List of Markdown lines.
    """
    return [
        "## Legend",
        "",
        "| Color | Layer | Description |",
        "|-------|-------|-------------|",
        "| Tan | Raw | External source tables (datasharing) |",
        "| Light bronze | Bronze tmp | Intermediate staging tables (`_tmp` schema) |",
        "| **Bronze** | Bronze | Persistent cleaned/typed tables |",
        "| Silver | Silver | Enriched business logic tables |",
        "| Gold | Gold | Aggregated analytics-ready tables by use case |",
        "| Light green | Platinum tmp | UC-specific intermediate tables |",
        "| **Green** | Platinum shared | Final opportunity EAV tables |",
        "",
        "- **Solid arrows** \u2192 CREATE OR REPLACE (build dependency)",
        "- **Dashed arrows** \u2192 INSERT INTO (append to existing table)",
    ]
