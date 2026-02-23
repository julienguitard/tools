---
name: docstring
description: "Generate and maintain Python docstrings using Google style format. Use when: adding documentation to functions/classes, updating docstrings after signature changes, checking docstring coverage, improving code documentation quality."
---

# Python Docstring Skill

## Purpose

This skill generates and maintains Python docstrings throughout a codebase. It ensures consistent documentation style, accurate type information, and helpful examples for all public interfaces.

## Scope

This skill operates on all `.py` files and manages docstrings for:

- Module-level docstrings
- Class docstrings
- Method and function docstrings
- Protocol method docstrings

## Docstring Style

Use **Google-style docstrings** for consistency and readability.

## Common Improvement Patterns

### Protocol Docstrings

**Before (minimal):**
```python
class DataReaderWriter(Protocol):
    """Abstract data source."""
    def read(self, query: str) -> pd.DataFrame:
        pass
    def write(self, df: pd.DataFrame, destination: str) -> None:
        pass
```

**After (complete):**
```python
class DataReaderWriter(Protocol):
    """Protocol for data read/write operations.

    Abstracts data access to enable multiple backend implementations.
    Implementations must provide both read and write capabilities.
    """

    def read(self, query: str) -> pd.DataFrame:
        """Execute a query and return results as DataFrame.

        Args:
            query: Query string or data source identifier.

        Returns:
            DataFrame containing query results.
        """
        ...

    def write(self, df: pd.DataFrame, destination: str) -> None:
        """Write DataFrame to destination.

        Args:
            df: DataFrame to write.
            destination: Target location (table name, file path, etc.).
        """
        ...
```

### Implementation Docstrings

**Before (minimal):**
```python
class MockReaderWriter(DataReaderWriter):
    """A way to mock a reader/writer"""

    def __init__(self):
        """Initialize the MockReader/Writer"""
        pass
```

**After (complete):**
```python
class MockReaderWriter(DataReaderWriter):
    """Mock implementation of DataReaderWriter for testing.

    Generates random data for reads and writes to local files.
    Use for unit tests and local development without external dependencies.

    Example:
        >>> reader = MockReaderWriter()
        >>> df = reader.read("col1, col2, col3")
        >>> len(df)
        10
    """

    def __init__(self):
        """Initialize the MockReaderWriter with no external dependencies."""
        pass
```

### Dataclass Docstrings

**Before (minimal):**
```python
@dataclass
class IOConfig:
    """A dataclass to configure I/O"""
    start_date: str
    end_date: str
```

**After (complete):**
```python
@dataclass
class IOConfig:
    """Configuration for data pipeline I/O.

    Defines source/target locations, date ranges for cost control,
    and column specifications for features and predictions.

    Attributes:
        start_date: Start date filter (YYYY-MM-DD) for query cost control.
        end_date: End date filter (YYYY-MM-DD) for query cost control.
        source_table: Fully qualified table for input data.
        target_table: Fully qualified table for output.
        feature_columns: Input columns for model.
        target_columns: Columns to predict.

    Example:
        >>> config = IOConfig(
        ...     start_date="2024-01-01",
        ...     end_date="2024-12-31",
        ...     source_table="project.dataset.transactions",
        ...     target_table="project.dataset.predictions",
        ... )
    """
    start_date: str
    end_date: str
```

### Decorator Docstrings

**Before (minimal):**
```python
def log_it(logger: Callable[[str], None] = print) -> Callable:
    """Decorator factory with configurable logger"""
```

**After (complete):**
```python
def log_it(logger: Callable[[str], None] = print) -> Callable:
    """Decorator factory for function call logging.

    Logs function entry with arguments and exit with return value.
    Supports both simple callables (like print) and Logger protocol.

    Args:
        logger: Logging function or Logger protocol instance.
            Defaults to print for simple console output.

    Returns:
        Decorator function that wraps the target.

    Example:
        >>> @log_it()
        ... def my_function(x):
        ...     return x * 2
        >>> my_function(5)
        Calling my_function with args: (5,), kwargs: {}
        my_function returned: 10
        10
    """
```

### Pipeline / Orchestration Docstrings

**Before (minimal):**
```python
class Pipeline[T: Runnable](NamedEntity, Runnable):
    """Our concrete implementation of the Pipeline"""
```

**After (complete):**
```python
class Pipeline[T: Runnable](NamedEntity, Runnable):
    """Generic pipeline that executes a sequence of Runnable steps.

    Implements both NamedEntity (for identification) and Runnable (for execution).
    Steps are executed sequentially via their run() methods.

    Type Parameters:
        T: Type of steps, must implement Runnable protocol.

    Attributes:
        name: Pipeline identifier.
        steps: Iterable of Runnable steps to execute.

    Example:
        >>> steps = [Step1(), Step2(), Step3()]
        >>> pipeline = Pipeline("my_pipeline", steps)
        >>> pipeline.run()  # Executes Step1, Step2, Step3 in order
    """
```

## Google-Style Docstring Reference

### Module Docstring

```python
"""Module purpose in one line.

Longer description explaining the module's role in the architecture.

Example:
    >>> from src.module import function
    >>> result = function(arg)

Attributes:
    MODULE_CONSTANT: Description of module-level constant.
"""
```

### Function/Method Docstring

```python
def function_name(param1: str, param2: int, optional: str = None) -> ReturnType:
    """One-line summary of what the function does.

    Longer description if needed.

    Args:
        param1: Description of param1.
        param2: Description of param2.
        optional: Description. Defaults to None.

    Returns:
        Description of return value.

    Raises:
        ValueError: When param1 is invalid.

    Example:
        >>> result = function_name("test", 42)
        >>> print(result)
    """
```

### Class Docstring

```python
class MyClass:
    """One-line summary of the class.

    Longer description explaining purpose and usage.

    Attributes:
        attr1: Description.
        attr2: Description.

    Example:
        >>> obj = MyClass(config)
        >>> obj.method()
    """
```

## Activation Triggers

Invoke this skill when:

1. New functions or classes are created
2. Function signatures change
3. Code review identifies missing/outdated docs
4. User requests docstring generation
5. Refactoring changes behavior

## Quality Rules

### Required Sections

| Element | Required Sections |
|---------|-------------------|
| Module | Summary |
| Class | Summary, Attributes (if any) |
| Public function | Summary, Args, Returns |
| Protocol method | Summary, Args, Returns |
| Dataclass | Summary, Attributes |

### Formatting Rules

1. **First line** — Complete sentence, imperative mood
2. **Args** — One line per argument, description after colon
3. **Returns** — Describe what, not just type
4. **Line length** — Max 79 characters
5. **Blank lines** — One between sections

## Special Cases

### Decorated Methods

Document the method's behavior, note decorators in description:

```python
@log_it()
@retry_it()
def run(self) -> None:
    """Execute the pipeline with automatic logging and retry.

    Decorated with @log_it for call tracing and @retry_it for
    transient failure handling.
    """
```

### Factory Functions

Emphasize what they create:

```python
def create_pipeline(source: str, task: str, client, **kwargs):
    """Create appropriate pipeline based on task type.

    Factory function that returns the correct pipeline variant
    depending on the task argument.

    Args:
        source: Data source identifier.
        task: Pipeline type ('etl', 'ml', 'mock', etc.).
        client: Database client instance (required for non-mock tasks).
        **kwargs: Additional arguments (start_date, end_date, etc.).

    Returns:
        Configured pipeline instance ready for execution.

    Raises:
        ValueError: If task is unknown or client is None for DB tasks.
    """
```

### Protocol Methods

Document the contract, not implementation:

```python
def run(self) -> None:
    """Execute the runnable's operation.

    Implementations should perform their designated task.
    May be called multiple times if idempotent.
    """
    ...
```

## Command Examples

```
# Generate docstrings for a file
"Add docstrings to src/io/implementations.py"

# Update docstrings after signature change
"Update docstrings in src/models/ to match current signatures"

# Check docstring coverage
"Which public functions are missing docstrings?"

# Fix specific class
"Add proper docstring to DatabaseReaderWriter class"

# Batch update
"Add Args and Returns sections to all functions in src/pipelines/implementations.py"
```

## Validation Checklist

Before committing docstring changes:

- [ ] All public functions have docstrings
- [ ] Args match function signature exactly
- [ ] Return description matches actual return
- [ ] Raises section lists actual exceptions
- [ ] Examples are syntactically correct
- [ ] No duplicate type information (already in signature)
- [ ] Line length ≤ 79 characters
