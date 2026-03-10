"""CLI entry point — python -m query_prolog."""

from __future__ import annotations

import sys
from pathlib import Path

import dotenv

from .service import make_query_repl

_ROOT_ENV = Path(__file__).resolve().parent.parent.parent / ".env"
dotenv.load_dotenv(_ROOT_ENV)


def main() -> None:
    """Parse CLI arguments and start the Prolog query REPL."""
    if len(sys.argv) < 2:
        print("Usage: python -m query_prolog <file.pl>")
        print("       python -m query_prolog family.pl")
        sys.exit(1)

    pl_path = Path(sys.argv[1])
    if not pl_path.exists():
        print(f"File not found: {pl_path}")
        sys.exit(1)

    use_case = make_query_repl(pl_path)
    use_case.execute()


if __name__ == "__main__":
    main()
