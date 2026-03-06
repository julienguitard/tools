"""CLI entry point — python -m rename_papers."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import dotenv

from .service import make_renamer

dotenv.load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rename research-paper PDFs using OpenAI content analysis."
    )
    parser.add_argument("folder", type=Path, help="Directory containing PDF files.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without renaming.")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model (default: gpt-4o-mini).")
    args = parser.parse_args()

    if not args.folder.is_dir():
        print(f"Error: {args.folder} is not a directory.", file=sys.stderr)
        sys.exit(1)
    if not os.environ.get("AI_API_KEY"):
        print("Error: AI_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    renamer = make_renamer(model=args.model)

    paths = renamer._fs.list_pdfs(args.folder)
    print(f"Found {len(paths)} PDF(s) in {args.folder}\n")

    actions = renamer.plan(args.folder)
    renamer.execute(actions, dry_run=args.dry_run)
    print("\nDone.")


if __name__ == "__main__":
    main()
