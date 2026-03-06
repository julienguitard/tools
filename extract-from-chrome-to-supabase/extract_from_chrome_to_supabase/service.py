"""Orchestration: depends only on ports, never on adapters."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .domain import Link
from .ports import CategorySuggester, LinkRepository, TabSource, UserPrompter


class CurateTabsUseCase:
    """Three-step workflow: fetch existing, walk tabs, POST collected links."""

    def __init__(
        self,
        tab_source: TabSource,
        repository: LinkRepository,
        categorizer: CategorySuggester,
        prompter: UserPrompter,
        output_dir: Path,
    ) -> None:
        self._tabs = tab_source
        self._repo = repository
        self._categorizer = categorizer
        self._ui = prompter
        self._output_dir = output_dir

    # -- execution (writes) --------------------------------------------------

    def execute(self, *, dry_run: bool = False) -> None:
        # ── Step 1: fetch existing links ─────────────────────────────
        existing = self._repo.fetch_existing()
        self._ui.show_existing(existing)
        existing_urls = {link.get("url", "") for link in existing}

        # ── Step 2: walk tabs, collect choices ───────────────────────
        tabs = self._tabs.fetch_tabs()
        if not tabs:
            print("No Chrome tabs found.")
            return

        collected: list[Link] = []
        for i, tab in enumerate(tabs, 1):
            already_saved = tab.url in existing_urls
            self._ui.present_tab(tab, i, len(tabs), already_saved)

            if not self._ui.ask_include():
                continue

            suggestion = self._categorizer.suggest(tab)
            category = self._ui.ask_category(suggestion)
            collected.append(Link(url=tab.url, category=category))

        if not collected:
            self._ui.report_skip()
            return

        # -- write phase (skipped in dry-run) ─────────────────────────
        payload = [link.to_dict() for link in collected]

        if dry_run:
            print("\n(dry-run) Would save JSON:\n")
            print(json.dumps(payload, indent=2))
            print(f"\n(dry-run) {len(collected)} link(s) collected. "
                  "Skipping file write and Supabase POST.")
            return

        # Save JSON locally
        out_path = self._output_dir / f"links_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        out_path.write_text(json.dumps(payload, indent=2))
        self._ui.report_saved_json(out_path)

        # ── Step 3: POST to Supabase ────────────────────────────────
        if self._ui.confirm_batch(collected):
            self._repo.save_links(collected)
            self._ui.report_posted(len(collected))


def make_curator(output_dir: Path, *, dry_run: bool = False) -> CurateTabsUseCase:
    """Wire concrete adapters into the service."""
    import sys

    from .adapters import (
        ChainedCategorizer,
        CliPrompter,
        ChromeAppleScriptSource,
        MockLinkRepository,
        SupabaseLinkRepository,
    )
    from .adapters.categorizer import AiCategorizer, KeywordCategorizer

    base_url = os.getenv("SUPABASE_URL", "")
    api_key = os.getenv("SUPABASE_API_KEY", "")
    mock = dry_run or os.getenv("MOCK", "true").lower() == "true"

    tab_source = ChromeAppleScriptSource()

    repository: LinkRepository
    if mock:
        repository = MockLinkRepository()
    else:
        if not base_url or not api_key:
            print("SUPABASE_URL and SUPABASE_API_KEY must be set in .env when MOCK=false")
            sys.exit(1)
        repository = SupabaseLinkRepository(base_url, api_key)

    # Build categorizer: keyword heuristic → AI fallback
    keyword = KeywordCategorizer()
    ai_provider = os.getenv("AI_PROVIDER", "").lower()
    ai_key = os.getenv("AI_API_KEY", "")
    ai_model = os.getenv("AI_MODEL", "")

    if ai_provider == "openai" and not ai_model:
        ai_model = "gpt-4o-mini"
    elif ai_provider == "anthropic" and not ai_model:
        ai_model = "claude-haiku-4-5-20251001"

    ai = AiCategorizer(ai_provider, ai_key, ai_model) if ai_provider and ai_key else None
    categorizer = ChainedCategorizer(keyword, ai)

    prompter = CliPrompter()

    return CurateTabsUseCase(tab_source, repository, categorizer, prompter, output_dir)
