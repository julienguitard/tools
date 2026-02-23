"""Abstract protocols for IO boundaries."""

from __future__ import annotations

from typing import Protocol

from .domain import FactFile, QueryResult


class PrologEngine(Protocol):
    """Executes Prolog queries against a fact file."""

    def query(self, fact_file: FactFile, prolog_query: str) -> QueryResult: ...


class QueryTranslator(Protocol):
    """Translates natural language to Prolog queries."""

    def translate(self, natural_query: str, fact_file: FactFile) -> str: ...


class UserInterface(Protocol):
    """REPL user interaction."""

    def show_fact_file(self, fact_file: FactFile) -> None: ...
    def read_input(self) -> str | None: ...
    def show_translation(self, prolog_query: str) -> None: ...
    def show_result(self, result: QueryResult) -> None: ...
    def show_message(self, msg: str) -> None: ...
