"""Pure data types — no IO, no side effects."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IdPrefix:
    """The numeric identifier extracted from the original filename."""
    value: str       # e.g. "2510.12269v3", "0310054"
    separator: str   # "." for arXiv-style, "_" for bare numeric

    _PATTERNS: tuple = (
        re.compile(r"^(\d{4}\.\d{4,5}v\d+)"),   # arXiv + version
        re.compile(r"^(\d{4}\.\d{4,5})"),         # arXiv
        re.compile(r"^(\d+)"),                     # bare numeric
    )

    @staticmethod
    def parse(filename: str) -> IdPrefix | None:
        """Extract a numeric ID prefix from a PDF filename stem. Pure."""
        stem = Path(filename).stem
        for pat in IdPrefix._PATTERNS:
            m = pat.match(stem)
            if m:
                val = m.group(1)
                sep = "_"
                return IdPrefix(value=val, separator=sep)
        return None


@dataclass(frozen=True)
class Article:
    """The semantic identity of a paper — what the LLM extracts."""
    slug: str   # e.g. "tensor_logic_for_ai"

    @staticmethod
    def sanitize_slug(raw: str) -> str:
        """Normalise an LLM response into a clean snake_case slug. Pure."""
        slug = re.sub(r"[^a-zA-Z0-9_]", "_", raw)
        slug = re.sub(r"_+", "_", slug).strip("_").lower()
        return slug or "unknown_content"


@dataclass(frozen=True)
class PaperFile:
    """A PDF on disk together with its parsed identity."""
    path: Path
    id_prefix: IdPrefix

    @property
    def original_name(self) -> str:
        return self.path.name

    def target_name(self, article: Article) -> str:
        """Build the new filename from prefix + slug. Pure."""
        p = self.id_prefix
        return f"{p.value}{p.separator}{article.slug}.pdf"

    @staticmethod
    def from_path(path: Path) -> PaperFile | None:
        """Try to interpret a Path as a paper with a numeric ID. Pure."""
        prefix = IdPrefix.parse(path.name)
        return PaperFile(path=path, id_prefix=prefix) if prefix else None


@dataclass(frozen=True)
class RenameAction:
    """Immutable description of what to do with one file."""
    source: Path
    new_name: str
    skipped: bool = False
    reason: str = ""

    @staticmethod
    def skip(source: Path, reason: str) -> RenameAction:
        return RenameAction(source=source, new_name="", skipped=True, reason=reason)

    @staticmethod
    def keep(source: Path) -> RenameAction:
        return RenameAction(source=source, new_name=source.name, reason="already correct")

    @property
    def is_noop(self) -> bool:
        return self.skipped or self.new_name == self.source.name
