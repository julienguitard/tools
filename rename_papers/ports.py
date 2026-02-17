"""Abstract protocols for IO boundaries."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class FileSystem(Protocol):
    """Abstraction over the local filesystem."""

    def list_pdfs(self, folder: Path) -> list[Path]: ...
    def rename(self, source: Path, target: Path) -> None: ...
    def exists(self, path: Path) -> bool: ...


class PdfReader(Protocol):
    """Abstraction over PDF text extraction."""

    def extract_text(self, path: Path) -> str: ...


class SlugGenerator(Protocol):
    """Abstraction over the LLM-based slug generation."""

    def generate(self, text: str) -> str: ...
