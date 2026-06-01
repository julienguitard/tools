"""Abstract protocols for IO boundaries."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .domain import Category, Link, Tab


class TabSource(Protocol):
    """Fetches open browser tabs."""

    def fetch_tabs(self) -> list[Tab]: ...


class LinkRepository(Protocol):
    """Reads and writes categorized links."""

    def fetch_existing(self) -> list[dict]: ...
    def save_links(self, links: list[Link]) -> None: ...


class CategorySuggester(Protocol):
    """Suggests a category for a given tab."""

    def suggest(self, tab: Tab) -> Category: ...


class UserPrompter(Protocol):
    """Interactive CLI prompts for the curation workflow."""

    def show_existing(self, links: list[dict]) -> None: ...
    def present_tab(self, tab: Tab, index: int, total: int, already_saved: bool) -> None: ...
    def ask_include(self) -> bool: ...
    def ask_category(self, suggestion: Category) -> Category: ...
    def confirm_batch(self, links: list[Link]) -> bool: ...
    def report_saved_json(self, path: Path) -> None: ...
    def report_posted(self, count: int) -> None: ...
    def report_skip(self) -> None: ...
