# extract-from-chrome-to-supabase

Interactive CLI to curate open Chrome tabs, categorize them (keyword heuristic + AI fallback), and save to Supabase.

## Setup

```bash
cd extract-from-chrome-to-supabase

# Create venv + install deps
make setup

# Edit .env with your Supabase keys (or keep MOCK=true for testing)
$EDITOR .env
```

## Usage

```bash
make run          # Full run: curate tabs, save JSON, POST to Supabase
make dry-run      # Preview: curate tabs, print JSON to stdout, skip writes
```

The interactive workflow:

1. Fetches existing links from Supabase (to flag duplicates)
2. Walks through each open Chrome tab — asks Y/N, suggests a category
3. Saves collected links as local JSON, then optionally POSTs to Supabase

## Files

```
extract-from-chrome-to-supabase/
├── .env.example              # Template — copy to .env
├── Makefile                  # setup / run / clean targets
├── requirements.txt
├── ux-flow.mmd               # UX flow diagram (Mermaid)
└── chrome_to_supabase/       # Python package
    ├── __init__.py
    ├── __main__.py           # CLI entry point
    ├── domain.py             # Tab, Link, CATEGORIES
    ├── ports.py              # TabSource, LinkRepository, CategorySuggester, UserPrompter
    ├── service.py            # CurateTabsUseCase + make_curator() factory
    └── adapters/
        ├── __init__.py
        ├── tab_source.py     # ChromeAppleScriptSource (osascript)
        ├── categorizer.py    # KeywordCategorizer, AiCategorizer, ChainedCategorizer
        ├── repository.py     # SupabaseLinkRepository, MockLinkRepository
        └── prompter.py       # CliPrompter
```

## Protocols

### TabSource

```python
class TabSource(Protocol):
    def fetch_tabs(self) -> list[Tab]: ...
```

### LinkRepository

```python
class LinkRepository(Protocol):
    def fetch_existing(self) -> list[dict]: ...
    def save_links(self, links: list[Link]) -> None: ...
```

### CategorySuggester

```python
class CategorySuggester(Protocol):
    def suggest(self, tab: Tab) -> str: ...
```

### UserPrompter

```python
class UserPrompter(Protocol):
    def show_existing(self, links: list[dict]) -> None: ...
    def present_tab(self, tab: Tab, index: int, total: int, already_saved: bool) -> None: ...
    def ask_include(self) -> bool: ...
    def ask_category(self, suggestion: str) -> str: ...
    def confirm_batch(self, links: list[Link]) -> bool: ...
    def report_saved_json(self, path: Path) -> None: ...
    def report_posted(self, count: int) -> None: ...
    def report_skip(self) -> None: ...
```

## Types

### Tab

- `title: str` — Page title
- `url: str` — Page URL

### Link

- `url: str` — Categorized URL
- `category: str` — One of 26 predefined categories

## Implementations

| Adapter | Protocol | Description |
|---------|----------|-------------|
| `ChromeAppleScriptSource` | `TabSource` | Reads Chrome tabs via macOS osascript |
| `KeywordCategorizer` | `CategorySuggester` | Offline keyword matching (25 rule sets) |
| `AiCategorizer` | `CategorySuggester` | OpenAI / Anthropic API fallback |
| `ChainedCategorizer` | `CategorySuggester` | Keyword first, AI fallback if "other" |
| `SupabaseLinkRepository` | `LinkRepository` | HTTP calls to Supabase edge functions |
| `MockLinkRepository` | `LinkRepository` | Fake implementation for local testing |
| `CliPrompter` | `UserPrompter` | Terminal-based interactive prompts |

## UX Flow

```mermaid
flowchart TD
    Start([Start]) --> LoadEnv[Load .env config]
    LoadEnv --> Wire[make_curator:<br/>ChromeAppleScriptSource · ChainedCategorizer<br/>SupabaseLinkRepository / Mock · CliPrompter]

    subgraph Step1 ["Step 1 — Fetch existing links"]
        direction TB
        FetchExisting[[LinkRepository.fetch_existing<br/>Supabase GET / Mock]]
        FetchExisting --> ShowExisting[Print: N links already in Supabase]
    end

    Wire --> FetchExisting

    subgraph Step2 ["Step 2 — Walk Chrome tabs"]
        direction TB
        FetchTabs[[ChromeAppleScriptSource.fetch_tabs<br/>osascript subprocess]]
        FetchTabs --> HasTabs{Tabs found?}
        HasTabs -- No --> NoTabs[Print: No Chrome tabs found] --> EarlyExit([Exit])

        HasTabs -- Yes --> TabLoop{{For each tab}}
        TabLoop --> PresentTab[Present tab<br/>index · title · URL · duplicate flag]
        PresentTab --> AskInclude([Include? Y/N])

        AskInclude -- No --> TabLoop
        AskInclude -- Yes --> Categorize

        subgraph Categorize ["Chained categorizer"]
            direction TB
            Keyword[KeywordCategorizer<br/>25 rule sets · offline]
            Keyword --> IsOther{Result is<br/>other?}
            IsOther -- No --> UseSuggestion[Use keyword match]
            IsOther -- Yes --> HasAI{AI configured?}
            HasAI -- No --> FallbackOther[Default: other]
            HasAI -- Yes --> AskAI[[AiCategorizer<br/>LLM API · 15s timeout]]
            AskAI --> ValidCat{Valid<br/>category?}
            ValidCat -- Yes --> UseAI[Use AI suggestion]
            ValidCat -- No --> FallbackOther
        end

        UseSuggestion --> ShowSuggestion
        UseAI --> ShowSuggestion
        FallbackOther --> ShowSuggestion

        ShowSuggestion[Show suggested category<br/>list 26 options]
        ShowSuggestion --> AskCategory([Category override?])

        AskCategory -- Enter --> AcceptSuggestion[Accept suggestion]
        AskCategory -- valid input --> OverrideCat[Use override]
        AskCategory -- invalid input --> WarnInvalid[Warn · use suggestion]

        AcceptSuggestion --> CollectLink[Collect Link<br/>url + category]
        OverrideCat --> CollectLink
        WarnInvalid --> CollectLink
        CollectLink --> TabLoop
    end

    ShowExisting --> FetchTabs

    subgraph Step3 ["Step 3 — Save & POST"]
        direction TB
        HasLinks{Links<br/>collected?}
        HasLinks -- No --> NothingToSave[Print: Nothing to save] --> Done([Exit])

        HasLinks -- Yes --> SaveJSON[Save JSON locally<br/>output/links_TIMESTAMP.json]
        SaveJSON --> PrintJSON[Print: JSON saved to path]
        PrintJSON --> ShowBatch[Show batch summary<br/>category · URL for each link]
        ShowBatch --> ConfirmPost([POST to Supabase? Y/N])

        ConfirmPost -- No --> SkipPost([Exit · JSON preserved])
        ConfirmPost -- Yes --> PostLinks[[LinkRepository.save_links<br/>Supabase POST / Mock]]
        PostLinks --> ReportPosted[Print: N links posted]
        ReportPosted --> Done
    end

    TabLoop -- Done --> HasLinks

    classDef error fill:#ffebee,stroke:#c62828
```

## Dependencies

- `httpx` — HTTP client for Supabase and LLM API calls
- `python-dotenv` — `.env` file loading
