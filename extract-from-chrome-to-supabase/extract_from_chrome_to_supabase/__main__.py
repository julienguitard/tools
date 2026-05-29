"""CLI entry point — python -m extract_from_chrome_to_supabase."""

from __future__ import annotations

import argparse
from pathlib import Path

import dotenv

from .service import make_curator

_TOOL_ENV = Path(__file__).resolve().parent.parent / ".env"
_MONOREPO_ENV = Path(__file__).resolve().parent.parent.parent / ".env"
# Tool-local .env wins; fall back to the shared monorepo-root .env.
dotenv.load_dotenv(_TOOL_ENV)
dotenv.load_dotenv(_MONOREPO_ENV)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract Chrome tabs, categorize, and POST to Supabase.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files or posting.")
    args = parser.parse_args()

    output_dir = Path(__file__).resolve().parent.parent / ".data"
    output_dir.mkdir(exist_ok=True)

    use_case = make_curator(output_dir=output_dir, dry_run=args.dry_run)
    use_case.execute(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
