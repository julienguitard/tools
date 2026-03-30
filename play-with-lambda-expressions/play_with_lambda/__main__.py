"""CLI entry point — python -m play_with_lambda."""

from __future__ import annotations

import argparse
from pathlib import Path

from .service import make_repl, make_script_repl


def main() -> None:
    """Parse CLI arguments and start the lambda calculus REPL."""
    parser = argparse.ArgumentParser(
        description="Interactive untyped lambda calculus REPL.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=100,
        help="Maximum beta-reduction steps before stopping (default: 100)",
    )
    parser.add_argument(
        "--random-depth",
        type=int,
        default=3,
        help="Default AST depth for :random (default: 3)",
    )
    parser.add_argument(
        "--script",
        type=Path,
        default=None,
        help="Run a script file instead of the interactive REPL",
    )
    args = parser.parse_args()

    if args.script is not None:
        if not args.script.exists():
            print(f"File not found: {args.script}")
            raise SystemExit(1)
        lines = args.script.read_text().splitlines()
        repl = make_script_repl(
            lines,
            max_steps=args.max_steps,
            random_depth=args.random_depth,
        )
    else:
        repl = make_repl(
            max_steps=args.max_steps,
            random_depth=args.random_depth,
        )
    repl.run()


if __name__ == "__main__":
    main()
