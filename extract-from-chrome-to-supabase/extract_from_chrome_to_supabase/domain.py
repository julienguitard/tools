"""Pure data types — no IO, no side effects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args

type Url = str

Category = Literal[
    "artificial_intelligence",
    "clojure",
    "computer_science",
    "database",
    "deep_learning",
    "documentation",
    "effect_ts",
    "functional_programming",
    "generative_ai",
    "graphic_design",
    "javascript",
    "knowledge_graphs",
    "linguistic_resources",
    "linguistics",
    "machine_learning",
    "mathematics",
    "ontologies",
    "purescript",
    "react",
    "reference",
    "rust",
    "semantic_web",
    "taxonomies",
    "typescript",
    "zod",
    "other",
]
"""The fixed taxonomy of labels a link may be filed under."""

DEFAULT_CATEGORY: Category = "other"
"""Fallback label used when no category can be confidently assigned."""

# Runtime views derived from the ``Category`` type — single source of truth.
CATEGORIES: tuple[Category, ...] = get_args(Category)
CATEGORIES_SET: frozenset[Category] = frozenset(CATEGORIES)


def parse_category(value: str) -> Category | None:
    """Narrow an arbitrary string to a ``Category``.

    Args:
        value: A candidate label, e.g. raw user or LLM input.

    Returns:
        The matching ``Category`` literal, or ``None`` if ``value`` is not a
        known label.
    """
    for category in CATEGORIES:
        if value == category:
            return category
    return None


@dataclass(frozen=True)
class Tab:
    """A single Chrome browser tab."""

    title: str
    url: Url


@dataclass(frozen=True)
class Link:
    """A categorized URL ready for persistence."""

    url: Url
    category: Category

    def to_dict(self) -> dict[str, str]:
        return {"url": self.url, "category": self.category}
