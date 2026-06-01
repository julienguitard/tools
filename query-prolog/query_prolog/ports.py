"""Abstract protocols for IO boundaries."""

from __future__ import annotations

from typing import Protocol

from .domain import FactFile, NaturalQuery, PrologQuery, QueryResult


class PrologEngine(Protocol):
    """Executes Prolog queries against a fact file."""

    def query(self, fact_file: FactFile, prolog_query: PrologQuery) -> QueryResult:
        """Execute a Prolog query against a fact file."""
        ...


class QueryTranslator(Protocol):
    """Translates natural language to Prolog queries."""

    def translate(self, natural_query: NaturalQuery, fact_file: FactFile) -> PrologQuery:
        """Translate a natural language question into a Prolog query."""
        ...


class UserInterface(Protocol):
    """REPL user interaction."""

    def show_fact_file(self, fact_file: FactFile) -> None:
        """Display the loaded fact file summary."""
        ...

    def read_input(self) -> str | None:
        """Read raw input from the user, or None on EOF.

        Returns unparsed text — a meta-command, a Prolog query, or a natural
        language question — so it stays ``str`` until the service classifies it.
        """
        ...

    def show_translation(self, prolog_query: PrologQuery) -> None:
        """Display the translated Prolog query."""
        ...

    def show_result(self, result: QueryResult) -> None:
        """Display the query execution result."""
        ...

    def show_message(self, msg: str) -> None:
        """Display an informational message."""
        ...
