---
name: subfolder-doc
description: "Create and maintain README.md files in project subfolders. Use when: generating module documentation, creating README for a directory, documenting folder structure, updating subfolder docs after code changes."
---

# Subfolder Documentation Skill

## Purpose

This skill creates and maintains `README.md` files in each subfolder of a codebase. These README files serve as local documentation explaining the purpose, contents, and usage patterns of each module.

## Scope

This skill operates on all directories under `src/` and creates/updates README.md files that document:

- Module purpose and responsibility
- Key files and their roles
- Protocols/interfaces defined
- Types/dataclasses defined
- Usage examples
- Dependencies and relationships

## Activation Triggers

Invoke this skill when:

1. A new subfolder is created under `src/`
2. Significant changes are made to a module's structure
3. New protocols or types are added
4. The user requests documentation refresh
5. Code review reveals documentation gaps

## README.md Template

Each subfolder README should follow this structure:

```markdown
# {Module Name}

## Purpose

{One paragraph explaining what this module does and its role in the architecture}

## Responsibility

Following the project architecture, this module is responsible for:
- {Bullet points of specific responsibilities}

## Files

| File | Purpose |
|------|---------|
| `protocols.py` | {Interface definitions} |
| `types.py` | {Configuration dataclasses} |
| `implementations.py` | {Concrete implementations} |

## Protocols

{List each protocol with method signatures}

### {ProtocolName}

```python
class {ProtocolName}(Protocol):
    def method_name(self, param: Type) -> ReturnType: ...
```

## Types

{List each dataclass with fields}

### {TypeName}

- `field1: Type` — Description
- `field2: Type` — Description

## Implementations

{List concrete classes}

### {ClassName}

Brief description of the implementation.

## Usage

```python
# Example usage code
from src.{module}.implementations import ClassName
```

## Dependencies

- **Depends on:** `src.{other_module}` — reason
- **Used by:** `src.{consumer_module}` — reason
```

## Module-Specific Template Examples

### For an I/O Module

```markdown
# IO Module

## Purpose

The IO module provides the data access layer, abstracting database operations behind protocol-based interfaces.

## Responsibility

- Define data read/write contracts via protocol
- Implement database data access
- Provide mock implementations for testing
- Handle query templating and partitioning

## Files

| File | Purpose |
|------|---------|
| `protocols.py` | `DataReaderWriter` protocol |
| `implementations.py` | Database and mock implementations |
| `types.py` | I/O configuration dataclasses |
| `utils.py` | Query templates, utilities |

## Protocol

### DataReaderWriter

```python
class DataReaderWriter(Protocol):
    def read(self, query: str) -> pd.DataFrame: ...
    def write(self, df: pd.DataFrame, destination: str) -> None: ...
```

## Dependencies

- **Depends on:** database client library, `pandas`
- **Used by:** `src.pipelines`
```

### For a Models Module

```markdown
# Models Module

## Purpose

The models module provides ML model abstractions and implementations, enabling consistent training and prediction interfaces.

## Responsibility

- Define model contracts via `Model` and `DataFrameProcessor` protocols
- Implement ML model wrappers
- Handle DataFrame preprocessing for ML

## Protocols

### Model

```python
class Model(Protocol):
    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> None: ...
    def predict(self, X: pd.DataFrame) -> pd.Series: ...
```

### DataFrameProcessor

```python
class DataFrameProcessor(Protocol):
    def transform(self, X: pd.DataFrame) -> pd.DataFrame: ...
```
```

### For a Pipelines / Orchestration Module

```markdown
# Pipelines Module

## Purpose

The pipelines module orchestrates data processing workflows, composing runnables into executable pipelines.

## Responsibility

- Define pipeline structure via generic `Pipeline[T: Runnable]`
- Implement SQL and ML pipeline variants
- Provide runnable wrappers for SQL files and queries

## Key Classes

### Pipeline[T: Runnable]

Generic base class for all pipelines with iterable steps.

### SqlPipeline

Executes a sequence of SQL files via runnable wrappers.

### MLPipeline

ML pipeline with training and prediction steps.
```

### For a Shared / Utilities Module

```markdown
# Shared Module

## Purpose

Cross-cutting utilities used across all modules: decorators, protocols, context managers.

## Responsibility

- Define base protocols (`Runnable`, `Logger`, `NamedEntity`)
- Provide decorator factories (`@log_it`, `@retry_it`, `@time_it`)
- Manage database connection lifecycle

## Key Components

### Decorators

```python
@log_it()       # Configurable logging
@retry_it()     # Exponential backoff
@time_it        # Execution timing
```

### Context Managers

```python
with DatabaseConnector() as db:
    client = db.client
```

### Protocols

- `Runnable` — Objects with `run()` method
- `Logger` — Logging interface with `span`, `info`, `error`
- `NamedEntity` — Objects with `name` property
```

## Workflow

### Creating New Documentation

1. **Scan the folder** — List all `.py` files
2. **Parse key elements**:
   - Protocols (classes with `Protocol` base)
   - Dataclasses (decorated with `@dataclass`)
   - Public classes and functions
3. **Determine relationships** — Check imports
4. **Generate README** — Fill template
5. **Write file** — Save as `README.md`

### Updating Documentation

1. **Read existing README** — Preserve custom sections
2. **Re-scan folder** — Detect changes
3. **Diff content** — Identify changes
4. **Update sections** — Only modify auto-generated parts
5. **Preserve manual content** — Keep `<!-- MANUAL -->` sections

## Conventions

### Section Markers

```markdown
<!-- AUTO-GENERATED: START -->
{Content that will be regenerated}
<!-- AUTO-GENERATED: END -->

<!-- MANUAL: START -->
{Content preserved across regenerations}
<!-- MANUAL: END -->
```

### Standard File Descriptions

| Filename | Standard Description |
|----------|---------------------|
| `protocols.py` | Interface definitions using `typing.Protocol` |
| `types.py` | Configuration dataclasses |
| `implementations.py` | Concrete implementations of protocols |
| `factory.py` | Factory functions for easy instantiation |
| `decorators.py` | Decorator functions for cross-cutting concerns |
| `utils.py` | Utility/helper functions |
| `context_managers.py` | Context manager classes |

### Module Categories

| Category | Layer |
|----------|-------|
| **Infrastructure** (I/O, databases) | Adapter |
| **Domain** (models, agents) | Core |
| **Application** (pipelines) | Orchestration |
| **Cross-cutting** (shared, transformations) | Utilities |
| **Presentation** (front, dashboards) | Output |

## Quality Checks

Before finalizing a README, verify:

- [ ] Purpose is clear in one paragraph
- [ ] All `.py` files are documented
- [ ] Protocols have method signatures
- [ ] Dataclasses have field descriptions
- [ ] Usage example is runnable
- [ ] Dependencies are accurate

## Command Examples

```
# Create README for a specific folder
"Create README.md for src/io/"

# Update all READMEs
"Update documentation for all subfolders"

# Check documentation coverage
"Which folders are missing README files?"

# Generate for a specific layer
"Create README for src/databases/tables/bronze/"
```
