"""Pure data types — no IO, no side effects."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

type PaperId = str
"""A paper's numeric identifier, e.g. ``2510.12269v3`` or ``0310054``."""

type Slug = str
"""A snake_case topic slug, e.g. ``tensor_logic_for_ai``."""

type Filename = str
"""A bare file name (no directory), e.g. ``2510.12269v3_tensor_logic.pdf``."""

type DocumentText = str
"""Raw text extracted from a PDF, fed to the slug generator."""


@dataclass(frozen=True)
class IdPrefix:
    """The numeric identifier extracted from the original filename."""
    value: PaperId   # e.g. "2510.12269v3", "0310054"
    separator: Literal[".", "_"]   # "." for arXiv-style, "_" for bare numeric

    _PATTERNS: tuple[re.Pattern[str], ...] = (
        re.compile(r"^(\d{4}\.\d{4,5}v\d+)"),   # arXiv + version
        re.compile(r"^(\d{4}\.\d{4,5})"),         # arXiv
        re.compile(r"^(\d+)"),                     # bare numeric
    )

    @staticmethod
    def parse(filename: Filename) -> IdPrefix | None:
        """Extract a numeric ID prefix from a PDF filename stem. Pure."""
        stem = Path(filename).stem
        for pat in IdPrefix._PATTERNS:
            m = pat.match(stem)
            if m:
                return IdPrefix(value=m.group(1), separator="_")
        return None


@dataclass(frozen=True)
class Article:
    """The semantic identity of a paper — what the LLM extracts."""
    slug: Slug   # e.g. "tensor_logic_for_ai"

    @staticmethod
    def sanitize_slug(raw: str) -> Slug:
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
    def original_name(self) -> Filename:
        return self.path.name

    def target_name(self, article: Article) -> Filename:
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
    new_name: Filename
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
