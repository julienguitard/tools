# generate_data_diagram

Scan SQL files for BigQuery table references and render a Mermaid dependency diagram showing the full data pipeline architecture.

```
*.sql files  →  parse dependencies  →  diagram_tables.md (Mermaid)
```

## Setup

```bash
cd generate_data_diagram

# Create venv + install deps
make setup
```

## Usage

```bash
# Default paths (sql-root and output configured in script)
make run

# Preview: print Mermaid to stdout without writing the output file
make dry-run

# Custom paths
python generate_data_diagram/generate.py --sql-root /path/to/sql --output diagram.md
python generate_data_diagram/generate.py --sql-root /path/to/sql --dry-run
```

## UX Flow

```mermaid
flowchart TD
    Start([Start]) --> ParseArgs[Parse CLI arguments<br/>--sql-root, --output]
    ParseArgs --> Wire[Wire adapters<br/>Discoverer · Parser · Builder · Renderer]

    Wire --> Discover[[GlobSqlFileDiscoverer.discover]]
    Discover --> ExclFilter{Excluded dir?<br/>shared · mockup · deprecated}

    ExclFilter -- Yes --> Skip1[Skip file]
    ExclFilter -- No --> Collect[Collect .sql path]
    Skip1 --> ExclFilter
    Collect --> ExclFilter

    ExclFilter -- Done --> HasFiles{Files found?}
    HasFiles -- No --> NoWork([No SQL files found])
    HasFiles -- Yes --> PrintDisc[Print: Discovered N files]

    PrintDisc --> ParseLoop{{For each SQL file}}
    ParseLoop --> ReadFile[Read file content]
    ReadFile --> StripComments[Strip SQL comments]
    StripComments --> SplitStmts[Split on semicolons]
    SplitStmts --> Classify{Statement type?}

    Classify -- DROP / DECLARE / OTHER --> SkipStmt[Skip statement]
    Classify -- CREATE / INSERT / MERGE --> ExtractTarget[Extract target table]
    ExtractTarget --> HasTarget{Target found?}

    HasTarget -- No --> SkipStmt
    HasTarget -- Yes --> ExtractSources[Extract source tables<br/>via regex on backtick refs]
    ExtractSources --> EmitStmt[Emit ParsedStatement]

    SkipStmt --> ParseLoop
    EmitStmt --> ParseLoop

    ParseLoop -- Done --> PrintParsed[Print: Parsed N statements]

    PrintParsed --> BuildGraph[[DependencyGraphBuilder.build]]
    BuildGraph --> MapTargets[Map tables → source files<br/>CREATE takes priority]
    MapTargets --> BuildNodes[Create TableNodes<br/>infer layer + subgroup]
    BuildNodes --> BuildEdges[Create DependencyEdges<br/>deduplicate by src·tgt·type]
    BuildEdges --> PrintGraph[Print: Graph N nodes, N edges]

    PrintGraph --> Render[[MermaidRenderer.render]]
    Render --> GroupNodes[Group nodes by layer_subgroup]
    GroupNodes --> RenderSub[Render nested subgraphs<br/>Raw → Bronze → Silver → Gold → Platinum]
    RenderSub --> RenderEdges[Render edges<br/>solid = CREATE · dashed = INSERT/MERGE]
    RenderEdges --> RenderStyles[Render classDef styles<br/>color per layer]
    RenderStyles --> RenderLegend[Append legend table]

    RenderLegend --> WriteFile[Write Markdown to output path]
    WriteFile --> Done([Done])

    classDef error fill:#ffebee,stroke:#c62828
```

### Phase summary

| Phase | Adapter | Input | Output |
|-------|---------|-------|--------|
| Discovery | `GlobSqlFileDiscoverer` | `sql_root` directory | Sorted `list[Path]` |
| Parsing | `RegexSqlParser` | SQL file content | `list[ParsedStatement]` |
| Graph building | `DependencyGraphBuilder` | Parsed statements | `DependencyGraph` (nodes + edges) |
| Rendering | `MermaidRenderer` | Dependency graph | Markdown string with Mermaid diagram |
