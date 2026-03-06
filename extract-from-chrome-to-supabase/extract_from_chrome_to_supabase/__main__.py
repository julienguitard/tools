"""CLI entry point — python -m extract_from_chrome_to_supabase."""

from __future__ import annotations

import argparse
from pathlib import Path

import dotenv

from .service import make_curator

_ROOT_ENV = Path(__file__).resolve().parent.parent.parent / ".env"
dotenv.load_dotenv(_ROOT_ENV)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract Chrome tabs, categorize, and POST to Supabase.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files or posting.")
    args = parser.parse_args()

    output_dir = Path(__file__).resolve().parent.parent / ".data"
    output_dir.mkdir(exist_ok=True)

    use_case = make_curator(output_dir=output_dir)
    use_case.execute(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
