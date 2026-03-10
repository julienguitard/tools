"""PDF text extraction via PyMuPDF (fitz)."""

from __future__ import annotations

import sys
from pathlib import Path


class PyMuPdfReader:
    """PDF text extraction via PyMuPDF (fitz)."""

    def __init__(self, max_pages: int = 5, max_chars: int = 4000) -> None:
        self._max_pages = max_pages
        self._max_chars = max_chars

    def extract_text(self, path: Path) -> str:
        import fitz  # lazy import keeps domain pure at module level

        try:
            doc = fitz.open(path)
            parts: list[str] = []
            total = 0
            for page in doc[: self._max_pages]:
                chunk = page.get_text()
                parts.append(chunk)
                total += len(chunk)
                if total >= self._max_chars:
                    break
            doc.close()
            return "\n".join(parts)[: self._max_chars]
        except Exception as e:
            print(f"  Warning: could not read {path.name}: {e}", file=sys.stderr)
            return ""
