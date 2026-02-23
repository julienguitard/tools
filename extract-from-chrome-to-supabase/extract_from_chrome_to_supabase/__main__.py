"""CLI entry point — python -m extract_from_chrome_to_supabase."""

from __future__ import annotations

from pathlib import Path

import dotenv

from .service import make_curator

dotenv.load_dotenv()


def main() -> None:
    output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    use_case = make_curator(output_dir=output_dir)
    use_case.execute()


if __name__ == "__main__":
    main()
