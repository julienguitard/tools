# rename-papers

Rename research paper PDFs based on their content using OpenAI.

```
2510.12269v3.pdf  →  2510.12269v3_tensor_logic_for_ai.pdf
0310054.pdf       →  0310054_kleene_algebra_domain.pdf
```

## Setup

```bash
cd rename-papers

# Create venv + install deps
make setup

# Add your API key
$EDITOR .env
```

## Usage

```bash
# Preview (recommended first)
make dry-run FOLDER=~/Downloads/papers

# Apply renames
make run FOLDER=~/Downloads/papers
```

### Global access (optional)

```bash
# Symlink the wrapper into your PATH
ln -s ~/tools/rename-papers/rename-papers.sh ~/.local/bin/rename-papers

# Then from anywhere:
rename-papers ~/Downloads/papers --dry-run
rename-papers ~/Downloads/papers
rename-papers ~/Downloads/papers --model gpt-4o
```

## Files

```
rename-papers/
├── .env.example              # Template — copy to .env
├── Makefile                  # setup / run / dry-run / clean targets
├── requirements.txt
├── rename-papers.sh          # Shell wrapper for global PATH access
└── rename_papers/            # Python package
    ├── __init__.py
    ├── __main__.py           # CLI entry point (argparse)
    ├── domain.py             # IdPrefix, Article, PaperFile, RenameAction
    ├── ports.py              # FileSystem, PdfReader, SlugGenerator
    ├── service.py            # PaperRenamer + make_renamer() factory
    └── adapters/
        ├── __init__.py
        ├── filesystem.py     # LocalFileSystem
        ├── pdf_reader.py     # PyMuPdfReader
        └── slug_generator.py # OpenAiSlugGenerator
```

## Protocols

### FileSystem

```python
class FileSystem(Protocol):
    def list_pdfs(self, folder: Path) -> list[Path]: ...
    def rename(self, source: Path, target: Path) -> None: ...
    def exists(self, path: Path) -> bool: ...
```

### PdfReader

```python
class PdfReader(Protocol):
    def extract_text(self, path: Path) -> str: ...
```

### SlugGenerator

```python
class SlugGenerator(Protocol):
    def generate(self, text: str) -> str: ...
```

## Types

### IdPrefix

- `value: str` — Numeric identifier (e.g. `"2510.12269v3"`)
- `separator: str` — Separator character (`"_"`)

### Article

- `slug: str` — Semantic slug (e.g. `"tensor_logic_for_ai"`)

### PaperFile

- `path: Path` — PDF file path
- `id_prefix: IdPrefix` — Parsed numeric ID

### RenameAction

- `source: Path` — Original file path
- `new_name: str` — Target filename
- `skipped: bool` — Whether this file is skipped
- `reason: str` — Reason for skip/keep

## Implementations

| Adapter | Protocol | Description |
|---------|----------|-------------|
| `LocalFileSystem` | `FileSystem` | Real filesystem operations |
| `PyMuPdfReader` | `PdfReader` | Text extraction via PyMuPDF (first N pages) |
| `OpenAiSlugGenerator` | `SlugGenerator` | Slug generation via OpenAI chat completions |

## UX Flow

```mermaid
flowchart TD
    Start([Start]) --> ParseArgs[Parse CLI arguments<br/>folder · --dry-run · --model]
    ParseArgs --> LoadEnv[Load .env config]
    LoadEnv --> ValidDir{folder is<br/>a directory?}

    ValidDir -- No --> ErrDir[Print error]:::error --> Exit1([Exit 1])
    ValidDir -- Yes --> HasKey{OPENAI_API_KEY<br/>set?}

    HasKey -- No --> ErrKey[Print error]:::error --> Exit1
    HasKey -- Yes --> Wire[make_renamer:<br/>LocalFileSystem · PyMuPdfReader · OpenAiSlugGenerator]

    Wire --> ListPDFs[[FileSystem.list_pdfs]]
    ListPDFs --> PrintFound[Print: Found N PDF·s]

    subgraph Plan ["plan() — read-only"]
        direction TB
        PlanLoop{{For each PDF}}

        PlanLoop --> ParseID{ID prefix<br/>matches?}
        ParseID -- No --> Skip1[RenameAction.skip<br/>no numeric ID]
        ParseID -- Yes --> ExtractText[[PdfReader.extract_text<br/>max 5 pages · 4000 chars]]

        ExtractText --> HasText{Text<br/>extracted?}
        HasText -- No --> Skip2[RenameAction.skip<br/>no text extracted]
        HasText -- Yes --> GenSlug[[SlugGenerator.generate<br/>OpenAI chat completions]]

        GenSlug --> Sanitize[Article.sanitize_slug<br/>lowercase · snake_case · strip]
        Sanitize --> BuildName[PaperFile.target_name<br/>ID_slug.pdf]
        BuildName --> Dedup{Name<br/>already used?}

        Dedup -- Yes --> AddCounter[Append _N suffix]
        Dedup -- No --> Changed{New name !=<br/>original?}
        AddCounter --> Changed

        Changed -- Same --> Keep[RenameAction.keep<br/>already correct]
        Changed -- Different --> Rename[RenameAction<br/>source + new_name]

        Skip1 --> PlanLoop
        Skip2 --> PlanLoop
        Keep --> PlanLoop
        Rename --> PlanLoop
    end

    PrintFound --> PlanLoop

    subgraph Exec ["execute() — side effects"]
        direction TB
        ExecLoop{{For each action}}

        ExecLoop --> IsSkipped{Skipped?}
        IsSkipped -- Yes --> PrintSkip[Print skip reason]

        IsSkipped -- No --> IsNoop{Is no-op?}
        IsNoop -- Yes --> PrintNoop[Print: already correct]

        IsNoop -- No --> DryRun{--dry-run?}
        DryRun -- Yes --> PrintDry[Print: new_name ·dry-run·]

        DryRun -- No --> Exists{Target exists<br/>on disk?}
        Exists -- Yes --> PrintExists[Print: target exists, skip]
        Exists -- No --> DoRename[[FileSystem.rename]]
        DoRename --> PrintDone[Print: => new_name]

        PrintSkip --> ExecLoop
        PrintNoop --> ExecLoop
        PrintDry --> ExecLoop
        PrintExists --> ExecLoop
        PrintDone --> ExecLoop
    end

    PlanLoop -- Done --> ExecLoop
    ExecLoop -- Done --> Done[Print: Done.]
    Done --> Exit0([Exit 0])

    classDef error fill:#ffebee,stroke:#c62828
```

## Dependencies

- `openai` — OpenAI Python SDK
- `pymupdf` — PDF text extraction
- `python-dotenv` — `.env` file loading
