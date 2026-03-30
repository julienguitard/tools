"""Abstract protocols for IO boundaries."""

from __future__ import annotations

from typing import Protocol

from .domain import Term


class TermGenerator(Protocol):
    """Generates lambda terms (e.g., randomly)."""

    def generate(self, max_depth: int) -> Term:
        """Produce a term with AST depth at most max_depth."""
        ...


class NameRegistry(Protocol):
    """Session-scoped named term storage."""

    def bind(self, name: str, term: Term) -> None:
        """Associate a name with a term (overwrites if exists)."""
        ...

    def lookup(self, name: str) -> Term | None:
        """Return the term bound to name, or None."""
        ...

    def all_names(self) -> dict[str, Term]:
        """Return all name-term bindings."""
        ...


class UserInterface(Protocol):
    """REPL interaction abstraction."""

    def read_input(self) -> str | None:
        """Read one line from the user. Return None on EOF."""
        ...

    def display(self, text: str) -> None:
        """Show output to the user."""
        ...

    def display_error(self, text: str) -> None:
        """Show an error message to the user."""
        ...
