"""Real filesystem adapter."""

from __future__ import annotations

from pathlib import Path


class LocalFileSystem:
    """Real filesystem adapter."""

    def list_pdfs(self, folder: Path) -> list[Path]:
        return sorted(folder.glob("*.pdf"))

    def rename(self, source: Path, target: Path) -> None:
        source.rename(target)

    def exists(self, path: Path) -> bool:
        return path.exists()
