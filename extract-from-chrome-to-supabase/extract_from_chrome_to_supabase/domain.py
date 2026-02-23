"""Pure data types — no IO, no side effects."""

from __future__ import annotations

from dataclasses import dataclass

CATEGORIES = [
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

CATEGORIES_SET = set(CATEGORIES)


@dataclass(frozen=True)
class Tab:
    """A single Chrome browser tab."""

    title: str
    url: str


@dataclass(frozen=True)
class Link:
    """A categorized URL ready for persistence."""

    url: str
    category: str

    def to_dict(self) -> dict:
        return {"url": self.url, "category": self.category}
