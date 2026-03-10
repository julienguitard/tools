"""Terminal-based REPL interface."""

from __future__ import annotations

from ..domain import FactFile, QueryResult


class CliInterface:
    """Interactive terminal UI for the Prolog query REPL."""

    def show_fact_file(self, fact_file: FactFile) -> None:
        """Display the loaded fact file summary."""
        print(f"\n{fact_file.summary()}")

    def read_input(self) -> str | None:
        """Read a query from the user, or None on EOF."""
        try:
            return input("\n?- ")
        except (EOFError, KeyboardInterrupt):
            print()
            return None

    def show_translation(self, prolog_query: str) -> None:
        """Display the translated Prolog query."""
        print(f"   -> {prolog_query}")

    def show_result(self, result: QueryResult) -> None:
        """Display the query execution result."""
        print(result.display())

    def show_message(self, msg: str) -> None:
        """Display an informational message."""
        print(msg)
