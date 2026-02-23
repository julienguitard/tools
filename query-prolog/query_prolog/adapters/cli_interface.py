"""Terminal-based REPL interface."""

from __future__ import annotations

from ..domain import FactFile, QueryResult


class CliInterface:
    """Interactive terminal UI for the Prolog query REPL."""

    def show_fact_file(self, fact_file: FactFile) -> None:
        print(f"\n{fact_file.summary()}")

    def read_input(self) -> str | None:
        try:
            return input("\n?- ")
        except (EOFError, KeyboardInterrupt):
            print()
            return None

    def show_translation(self, prolog_query: str) -> None:
        print(f"   -> {prolog_query}")

    def show_result(self, result: QueryResult) -> None:
        print(result.display())

    def show_message(self, msg: str) -> None:
        print(msg)
