---
name: commit
description: "Generate well-formatted, self-sufficient git commit messages and then commit. Use when: commiting, writing commit messages, improving commit message quality, following conventional commit format, documenting code changes for git history."
---

# Commit Message and Commit Skill

## Purpose

This skill generates well-formatted, readable, and self-sufficient commit messages and then commit. A good commit message tells the story of a change without requiring the reader to examine the diff.

## Core Principles

### 1. Self-Sufficiency

The commit message must stand alone. A reader should understand:
- **What** changed
- **Why** it changed
- **Impact** on the codebase

Without opening the diff, without context from Slack, without asking the author.

### 2. Readability

Commit messages are read far more often than they are written. Optimize for the reader:
- Clear, direct language
- Logical structure
- No jargon without context

### 3. Consistency

Follow a predictable format so readers know where to find information.

## Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type (Required)

| Type | Use When |
|------|----------|
| `feat` | Adding new functionality |
| `fix` | Fixing a bug |
| `refactor` | Code change that neither fixes nor adds features |
| `docs` | Documentation only |
| `style` | Formatting, whitespace (no code change) |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks, dependencies |
| `perf` | Performance improvement |
| `build` | Build system, CI/CD changes |

### Scope (Recommended)

Module or area affected. Adapt to the project's module structure (e.g., `api`, `auth`, `db`, `models`, `ui`, `config`, etc.).

### Subject Line (Required)

- **Maximum 50 characters** (hard limit: 72)
- Imperative mood: "Add" not "Added" or "Adds"
- No period at the end
- Lowercase after type

### Body (Required for non-trivial changes)

- Wrap at 72 characters
- Explain **what** and **why**, not **how** (the diff shows how)
- Use bullet points for multiple changes
- Separate from subject with blank line

### Footer (Optional)

- Breaking changes: `BREAKING CHANGE: description`
- Issue references: `Closes #123`, `Fixes #456`
- Co-authors: `Co-authored-by: Name <email>`

## Self-Sufficiency Rules

### Rule 1: No Pronouns Without Antecedents

```
❌ Bad:  "Fix it"
❌ Bad:  "Update this to work better"
✅ Good: "Fix database connection leak in ReaderWriter"
✅ Good: "Update Pipeline to handle empty step lists"
```

### Rule 2: Name the Affected Components

```
❌ Bad:  "Add new protocol"
❌ Bad:  "Fix bug in pipeline"
✅ Good: "Add DataProcessor protocol to models module"
✅ Good: "Fix null pointer in ModelRunner.read_and_split_data"
```

### Rule 3: Explain the Why

```
❌ Bad:  "Change retry count to 5"
✅ Good: "Increase retry count to 5 for transient API errors

        The API occasionally returns 503 errors during high-load
        periods. The previous retry count of 3 was insufficient
        for overnight batch jobs."
```

### Rule 4: State the Impact

```
❌ Bad:  "Refactor factory module"
✅ Good: "Refactor factory module to support new data source

        - Add create_pipeline case for new source type
        - Extract source-specific config into separate functions
        - No breaking changes to existing API"
```

### Rule 5: Quantify When Possible

```
❌ Bad:  "Improve query performance"
✅ Good: "Reduce aggregation query time from 45min to 12min

        Replace correlated subquery with window function.
        Tested on production dataset (2024-01-01 to 2024-06-30)."
```

## Example Patterns

### SQL / Data Pipeline Changes

```
feat(data): Add customer filtering step to pipeline

Add identify_customers_to_filter.sql to remove
invalid records before downstream processing.

Pipeline order:
1. build_customers_unfiltered
2. identify_customers_to_filter (NEW)
3. build_customers_filtered

Reduces downstream data volume by ~15%.
```

### Protocol / Interface Changes

```
feat(models): Add batch_predict method to Model protocol

Extend Model protocol with optional batch_predict() for
large-scale inference without memory issues.

- Add batch_predict(X, batch_size) -> Iterator[pd.Series]
- Default implementation in ML ModelModel (1000 rows/batch)
- MockModel returns random batches for testing

Backward compatible: batch_predict has default None implementation.
```

### Configuration Changes

```
feat(config): Add source_predict_table to IOConfig

Support separate tables for training vs prediction data.
Required for restricted model training scenarios.

New field:
- source_predict_table: Optional[str] = None

When None, uses source_table for both training and prediction.
```

### Decorator / Utility Changes

```
feat(shared): Add exponential backoff to retry decorator

Replace fixed delay with exponential backoff (delay * 2^attempt).
Prevents thundering herd on API rate limits.

Before: 1s, 1s, 1s (fixed)
After:  1s, 2s, 4s (exponential)

Configurable via new 'backoff_factor' parameter (default: 2).
```

### Factory Changes

```
feat(factory): Support new pipeline variant

Add case for 'new_variant' task in create_pipeline_from_arg.
Loads pipeline config from config/new_variant_pipeline.json.

Usage:
  python src/main.py source_name new_variant 2024-01-01 2024-12-31
```

### Bug Fixes

```
fix(pipelines): Handle empty DataFrame in ModelRunner.write_data

ModelRunner.write_data crashed when prediction DataFrame was empty
due to all rows being filtered by date range.

- Add empty check before writing output
- Log warning instead of writing empty table
- Return early to avoid unnecessary API call

Fixes production failure on 2024-01-15 nightly run.
```

### Refactoring

```
refactor(db): Extract pattern constants to utils.py

Move regex patterns from implementations.py to utils.py:
- start_date_pattern
- end_date_pattern
- dataset_pattern

Preparation for adding new patterns (source, project_id).
No functional changes.
```

## Anti-Patterns

### ❌ Lazy Messages

```
"Fix bug"
"Update code"
"WIP"
"Changes"
"Misc improvements"
```

### ❌ Diff Descriptions

```
"Change line 45 in implementations.py"
"Remove unused import"  # (alone, without context)
"Add semicolon"
```

### ❌ Future Tense

```
"This will add support for..."
"Going to fix the issue where..."
```

### ❌ Emotional Messages

```
"Finally fix this annoying bug"
"Ugh, revert broken changes"
"Quick hack to make it work"
```

### ❌ External References Only

```
"See Slack thread"
"As discussed in meeting"
"Per John's request"  # (without explaining what)
```

## Commit Message Checklist

Before committing, verify:

- [ ] **Type is accurate** — Is this really a `feat` or actually a `fix`?
- [ ] **Scope is specific** — Does it name the affected module?
- [ ] **Subject is imperative** — "Add" not "Added"?
- [ ] **Subject ≤ 50 chars** — Can it be read in git log --oneline?
- [ ] **Body explains why** — Would a new team member understand?
- [ ] **Components are named** — No vague "it" or "this"?
- [ ] **Impact is stated** — What does this change for users/developers?
- [ ] **No jargon** — Or jargon is explained?
- [ ] **Wrapped at 72 chars** — Readable in terminal?
- [ ] **Footer if needed** — Breaking changes? Issue refs?

## Multi-File Commits

When a commit touches multiple files, structure the body:

```
refactor(pipelines): Consolidate runnable implementations

Merge redundant code between RunnableFromFile and
RunnableFromQuery into shared base behavior.

Changes:
- Extract _execute_query() to base class
- RunnableFromFile now inherits resolution logic
- RunnableFromQuery simplified to 15 lines
- Remove duplicate logging decorators

Files:
- src/db/implementations.py (base _execute_query)
- src/pipelines/implementations.py (simplified runnables)

No API changes. All existing pipelines work unchanged.
```

## Integration with Git Workflow

### Commit Template

Save to `.gitmessage`:

```
# <type>(<scope>): <subject>
#
# <body>
#
# <footer>
#
# Types: feat|fix|refactor|docs|style|test|chore|perf|build
# Scopes: adapt to your project modules
#
# Subject: imperative, lowercase, no period, max 50 chars
# Body: wrap at 72 chars, explain what and why
# Footer: BREAKING CHANGE, Closes #issue
```

Configure:
```bash
git config --local commit.template .gitmessage
```

### Pre-Commit Hook

Optional validation in `.git/hooks/commit-msg`:

```bash
#!/bin/bash
# Validate commit message format

MSG_FILE=$1
MSG=$(cat "$MSG_FILE")

# Check subject line length
SUBJECT=$(echo "$MSG" | head -1)
if [ ${#SUBJECT} -gt 72 ]; then
    echo "ERROR: Subject line exceeds 72 characters"
    exit 1
fi

# Check for type prefix
if ! echo "$SUBJECT" | grep -qE "^(feat|fix|refactor|docs|style|test|chore|perf|build)(\(.+\))?:"; then
    echo "ERROR: Subject must start with type (feat|fix|refactor|...)"
    exit 1
fi

exit 0
```
