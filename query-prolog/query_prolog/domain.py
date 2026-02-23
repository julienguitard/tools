"""Pure data types — no IO, no side effects."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FactFile:
    """A loaded Prolog fact file with extracted predicate signatures."""

    path: Path
    content: str
    predicates: list[str]  # e.g. ["parent/2", "male/1", "ancestor/2"]

    @classmethod
    def load(cls, path: Path) -> FactFile:
        content = path.read_text()
        predicates = cls._extract_predicates(content)
        return cls(path=path, content=content, predicates=predicates)

    @staticmethod
    def _extract_predicates(content: str) -> list[str]:
        """Extract unique predicate signatures from a .pl file."""
        seen: dict[str, int] = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("%") or line.startswith("/*"):
                continue
            match = re.match(r"^(\w+)\(([^)]*)\)", line)
            if match:
                name = match.group(1)
                arity = len([a.strip() for a in match.group(2).split(",") if a.strip()])
                key = f"{name}/{arity}"
                seen[key] = seen.get(key, 0) + 1
        return sorted(seen.keys())

    def summary(self) -> str:
        lines = [f"{self.path.name}"]
        lines.append(f"   Predicates: {', '.join(self.predicates) if self.predicates else '(none detected)'}")
        examples = [l.strip() for l in self.content.splitlines()
                     if l.strip() and not l.strip().startswith("%")][:5]
        lines.append("   Sample facts:")
        for ex in examples:
            lines.append(f"     {ex}")
        if len([l for l in self.content.splitlines() if l.strip() and not l.strip().startswith("%")]) > 5:
            lines.append("     ...")
        return "\n".join(lines)


@dataclass
class QueryResult:
    """Result of executing a Prolog query."""

    query: str
    success: bool
    bindings: list[dict[str, str]] = field(default_factory=list)
    error: str = ""

    def display(self) -> str:
        if self.error:
            return f"Error: {self.error}"
        if not self.success:
            return "false."
        if not self.bindings:
            return "true."
        lines = []
        for b in self.bindings:
            parts = [f"{k} = {v}" for k, v in b.items()]
            lines.append(", ".join(parts))
        return "\n".join(lines)


class InputMode:
    """Constants for input mode detection."""

    PROLOG = "prolog"
    NATURAL = "natural"
