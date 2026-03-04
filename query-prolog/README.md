# query-prolog

Interactive REPL for querying Prolog fact files. Supports direct Prolog syntax and natural language (translated to Prolog via AI).

Requires SWI-Prolog: `brew install swi-prolog`

## Setup

```bash
cd query-prolog

# Create venv + install deps
make setup

# Edit .env with AI keys (optional — Prolog-only mode works without)
$EDITOR .env
```

## Usage

```bash
# Query the included example file
make run FILE=.data/family.pl

# Query any .pl file
make run FILE=/path/to/facts.pl
```

### REPL examples

```
?- parent(X, bob)
X = alice

?- Who is bob's parent?
   -> parent(X, bob)
X = alice

?- :preds
Predicates: ancestor/2, father/2, female/1, grandparent/2, male/1, mother/2, parent/2, sibling/2

?- :quit
```

## Files

```
query-prolog/
├── .env.example              # Template — copy to .env
├── Makefile                  # setup / run / clean targets
├── requirements.txt
├── family.pl                 # Example Prolog fact file
├── ux-flow.mmd               # UX flow diagram (Mermaid)
└── query_prolog/             # Python package
    ├── __init__.py
    ├── __main__.py           # CLI entry point (argparse)
    ├── domain.py             # FactFile, QueryResult, InputMode
    ├── ports.py              # PrologEngine, QueryTranslator, UserInterface
    ├── service.py            # QueryFactsUseCase + make_query_repl() factory
    └── adapters/
        ├── __init__.py
        ├── prolog_engine.py  # SwiPrologEngine (subprocess)
        ├── query_translator.py # AiQueryTranslator (OpenAI / Anthropic)
        └── cli_interface.py  # CliInterface (terminal REPL)
```

## Protocols

### PrologEngine

```python
class PrologEngine(Protocol):
    def query(self, fact_file: FactFile, prolog_query: str) -> QueryResult: ...
```

### QueryTranslator

```python
class QueryTranslator(Protocol):
    def translate(self, natural_query: str, fact_file: FactFile) -> str: ...
```

### UserInterface

```python
class UserInterface(Protocol):
    def show_fact_file(self, fact_file: FactFile) -> None: ...
    def read_input(self) -> str | None: ...
    def show_translation(self, prolog_query: str) -> None: ...
    def show_result(self, result: QueryResult) -> None: ...
    def show_message(self, msg: str) -> None: ...
```

## Types

### FactFile

- `path: Path` — Path to the `.pl` file
- `content: str` — Full file content
- `predicates: list[str]` — Extracted signatures (e.g. `["parent/2", "male/1"]`)

### QueryResult

- `query: str` — The executed query
- `success: bool` — Whether the query succeeded
- `bindings: list[dict[str, str]]` — Variable bindings from solutions
- `error: str` — Error message if any

## Implementations

| Adapter | Protocol | Description |
|---------|----------|-------------|
| `SwiPrologEngine` | `PrologEngine` | Executes queries via `swipl` subprocess |
| `AiQueryTranslator` | `QueryTranslator` | Natural language to Prolog via OpenAI / Anthropic |
| `CliInterface` | `UserInterface` | Terminal-based REPL with `?-` prompt |

## UX Flow

```mermaid
flowchart TD
    Start([Start]) --> LoadEnv[Load .env config]
    LoadEnv --> ValidFile{.pl file<br/>exists?}

    ValidFile -- No --> ErrFile[Print error]:::error --> Exit1([Exit 1])
    ValidFile -- Yes --> Wire[make_query_repl:<br/>SwiPrologEngine · AiQueryTranslator? · CliInterface]

    Wire --> LoadPL[FactFile.load<br/>parse predicates & sample facts]
    LoadPL --> ShowSummary[Show file summary<br/>predicates · sample facts · mode hint]

    subgraph REPL ["REPL loop"]
        direction TB
        Prompt{{?- prompt}} --> ReadInput([Read user input])

        ReadInput --> IsCmd{Starts with :?}

        IsCmd -- Yes --> CmdDispatch{Which command?}
        CmdDispatch -- :quit / :q / :exit --> ExitCmd[Raise SystemExit]
        CmdDispatch -- :help / :h --> ShowHelp[Show command reference] --> Prompt
        CmdDispatch -- :preds --> ShowPreds[Show predicates] --> Prompt
        CmdDispatch -- :file --> ShowFile[Re-display fact file] --> Prompt
        CmdDispatch -- other --> Unknown[Show: Unknown command] --> Prompt

        IsCmd -- No --> StripInput[Strip ?- prefix and trailing .]
        StripInput --> TryProlog[[SwiPrologEngine.query<br/>swipl subprocess · 10s timeout]]

        TryProlog --> SyntaxErr{Syntax error<br/>in result?}

        SyntaxErr -- No --> ShowResult
        SyntaxErr -- Yes --> HasAI{AI translator<br/>configured?}

        HasAI -- No --> NoAI[Show: No AI configured<br/>use Prolog syntax] --> Prompt
        HasAI -- Yes --> Translate[[AiQueryTranslator.translate<br/>LLM API · 15s timeout]]
        Translate --> ShowTranslation[Show: -> translated_query]
        ShowTranslation --> RetryQuery[[SwiPrologEngine.query<br/>translated query]]
        RetryQuery --> ShowResult

        ShowResult{Result type?}
        ShowResult -- bindings --> ShowBindings[Display variable bindings<br/>X = alice] --> Prompt
        ShowResult -- true / false --> ShowBool[Display: true. / false.] --> Prompt
        ShowResult -- error --> ShowError[Display error message]:::error --> Prompt
    end

    ShowSummary --> Prompt
    ReadInput -- EOF / Ctrl+C --> Exit0([Exit 0])
    ExitCmd --> Exit0

    classDef error fill:#ffebee,stroke:#c62828
```

## Dependencies

- `httpx` — HTTP client for LLM API calls (lazy-loaded)
- `python-dotenv` — `.env` file loading
- **System:** `swipl` (SWI-Prolog) must be on PATH
