"""Interactive CLI prompts for the curation workflow."""

from __future__ import annotations

from pathlib import Path

from ..domain import CATEGORIES, CATEGORIES_SET, Link, Tab


class CliPrompter:
    """Terminal-based user interaction."""

    def show_existing(self, links: list[dict]) -> None:
        print(f"\n{len(links)} link(s) already in Supabase.\n")

    def present_tab(self, tab: Tab, index: int, total: int, already_saved: bool) -> None:
        flag = " (already saved)" if already_saved else ""
        print(f"\n[{index}/{total}]{flag}")
        print(f"  {tab.title}")
        print(f"  {tab.url}")

    def ask_include(self) -> bool:
        return input("  Include? [y/N] ").strip().lower() == "y"

    def ask_category(self, suggestion: str) -> str:
        print(f"  Suggested category: \033[1m{suggestion}\033[0m")
        print(f"  Options: {', '.join(CATEGORIES)}")
        override = input(f"  Category [{suggestion}]: ").strip().lower()
        if override and override in CATEGORIES_SET:
            return override
        if override and override not in CATEGORIES_SET:
            print(f"  Unknown '{override}', using '{suggestion}'")
        return suggestion

    def confirm_batch(self, links: list[Link]) -> bool:
        print(f"\n{len(links)} link(s) ready to POST:")
        for link in links:
            print(f"  {link.category:25s} {link.url}")
        return input("\n  POST to Supabase? [y/N] ").strip().lower() == "y"

    def report_saved_json(self, path: Path) -> None:
        print(f"\nJSON saved to {path}")

    def report_posted(self, count: int) -> None:
        print(f"{count} link(s) posted to Supabase.")

    def report_skip(self) -> None:
        print("Nothing to save.")
