#!/usr/bin/env python3
"""
Chrome Tabs → Supabase links curator.

Three-step workflow:
  1. Fetch existing links from Supabase (to avoid duplicates)
  2. Walk through Chrome tabs, ask Y/N + category → build JSON
  3. POST collected links to Supabase

Category suggestion: keyword heuristic → AI fallback (OpenAI or Anthropic)

Hexagonal architecture:
  Domain  → Link, Tab, CATEGORIES
  Ports   → TabSource, LinkRepository, CategorySuggester, UserPrompter
  Adapters→ ChromeAppleScript, SupabaseLinks, MockLinks,
             KeywordCategorizer, AiCategorizer, CliPrompter
  App     → CurateTabsUseCase
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import httpx
from dotenv import load_dotenv


# ═══════════════════════════════════════════════════════════════════════
# DOMAIN
# ═══════════════════════════════════════════════════════════════════════

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
    title: str
    url: str


@dataclass(frozen=True)
class Link:
    url: str
    category: str

    def to_dict(self) -> dict:
        return {"url": self.url, "category": self.category}


# ═══════════════════════════════════════════════════════════════════════
# PORTS
# ═══════════════════════════════════════════════════════════════════════


class TabSource(Protocol):
    def fetch_tabs(self) -> list[Tab]: ...


class LinkRepository(Protocol):
    def fetch_existing(self) -> list[dict]: ...
    def save_links(self, links: list[Link]) -> None: ...


class CategorySuggester(Protocol):
    def suggest(self, tab: Tab) -> str: ...


class UserPrompter(Protocol):
    def show_existing(self, links: list[dict]) -> None: ...
    def present_tab(self, tab: Tab, index: int, total: int, already_saved: bool) -> None: ...
    def ask_include(self) -> bool: ...
    def ask_category(self, suggestion: str) -> str: ...
    def confirm_batch(self, links: list[Link]) -> bool: ...
    def report_saved_json(self, path: Path) -> None: ...
    def report_posted(self, count: int) -> None: ...
    def report_skip(self) -> None: ...


# ═══════════════════════════════════════════════════════════════════════
# APPLICATION
# ═══════════════════════════════════════════════════════════════════════


class CurateTabsUseCase:
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

    def execute(self) -> None:
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

        # Save JSON locally
        out_path = self._output_dir / f"links_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        payload = [link.to_dict() for link in collected]
        out_path.write_text(json.dumps(payload, indent=2))
        self._ui.report_saved_json(out_path)

        # ── Step 3: POST to Supabase ────────────────────────────────
        if self._ui.confirm_batch(collected):
            self._repo.save_links(collected)
            self._ui.report_posted(len(collected))


# ═══════════════════════════════════════════════════════════════════════
# ADAPTERS — Tab source
# ═══════════════════════════════════════════════════════════════════════


class ChromeAppleScriptSource:
    _SCRIPT = """
    set output to ""
    tell application "Google Chrome"
        repeat with w in every window
            repeat with t in every tab of w
                set output to output & title of t & "||" & URL of t & linefeed
            end repeat
        end repeat
    end tell
    return output
    """

    def fetch_tabs(self) -> list[Tab]:
        result = subprocess.run(
            ["osascript", "-e", self._SCRIPT],
            capture_output=True, text=True, check=True,
        )
        tabs: list[Tab] = []
        for line in result.stdout.strip().splitlines():
            if "||" in line:
                title, url = line.split("||", 1)
                tabs.append(Tab(title=title.strip(), url=url.strip()))
        return tabs


# ═══════════════════════════════════════════════════════════════════════
# ADAPTERS — Category suggesters
# ═══════════════════════════════════════════════════════════════════════


class KeywordCategorizer:
    """Fast, offline keyword matching. Returns 'other' when unsure."""

    _RULES: list[tuple[list[str], str]] = [
        (["llm", "gpt", "openai", "anthropic", "gemini", "llama", "mistral", "genai", "chatgpt", "copilot", "prompt engineer"], "generative_ai"),
        (["deep learning", "pytorch", "tensorflow", "neural net", "cnn", "rnn", "transformer architecture"], "deep_learning"),
        (["mlflow", "sklearn", "scikit", "ml_model", "reinforcement", "ml ", "machine learning", "feature store"], "machine_learning"),
        (["artificial intelligence", " ai ", "ai-", "agi"], "artificial_intelligence"),
        (["postgres", "sql", "database", "supabase", "redis", "mongo", "duckdb", "clickhouse", "sqlite"], "database"),
        (["ontolog", "owl ", "rdf", "protégé"], "ontologies"),
        (["knowledge graph", "neo4j", "wikidata"], "knowledge_graphs"),
        (["semantic web", "linked data", "sparql", "json-ld"], "semantic_web"),
        (["taxonom", "classification scheme", "skos"], "taxonomies"),
        (["linguist", "nlp", "morpholog", "syntax", "phonolog", "corpus"], "linguistics"),
        (["linguistic resource", "wordnet", "framenet", "lexicon"], "linguistic_resources"),
        (["clojure", "clojurescript", "reagent", "re-frame", "babashka"], "clojure"),
        (["purescript", "halogen"], "purescript"),
        (["effect-ts", "effect/", "@effect", "effect ts"], "effect_ts"),
        (["zod", "zod.dev"], "zod"),
        (["react", "next.js", "nextjs", "remix"], "react"),
        (["javascript", "node.js", "nodejs", "deno ", "bun "], "javascript"),
        (["typescript", "ts ", ".ts "], "typescript"),
        (["rust", "cargo", "crates.io", "tokio", "wasm"], "rust"),
        (["haskell", "ocaml", "scala", "category theory", "monad", "functor", "functional programming", "fp ", "lambda calculus"], "functional_programming"),
        (["math", "theorem", "algebra", "topology", "calculus", "statistics", "probability", "combinatorics"], "mathematics"),
        (["algorithm", "data structure", "complexity", "compiler", "operating system", "distributed system", "computer science"], "computer_science"),
        (["figma", "design system", "typography", "color palette", "graphic design", "illustration", "svg"], "graphic_design"),
        (["documentation", "docs", "readme", "wiki", "api reference", "man page"], "documentation"),
        (["reference", "cheatsheet", "cheat sheet", "awesome-", "curated list"], "reference"),
    ]

    def suggest(self, tab: Tab) -> str:
        text = (tab.title + " " + tab.url).lower()
        for keywords, category in self._RULES:
            if any(kw in text for kw in keywords):
                return category
        return "other"


class AiCategorizer:
    """Calls an LLM to categorize when keywords fail. Supports OpenAI and Anthropic."""

    def __init__(self, provider: str, api_key: str, model: str) -> None:
        self._provider = provider  # "openai" or "anthropic"
        self._api_key = api_key
        self._model = model

    def suggest(self, tab: Tab) -> str:
        categories_str = ", ".join(CATEGORIES)
        prompt = (
            f"Classify this web page into exactly one category.\n"
            f"Title: {tab.title}\n"
            f"URL: {tab.url}\n\n"
            f"Categories: {categories_str}\n\n"
            f"Reply with ONLY the category name, nothing else."
        )
        try:
            text = self._call_llm(prompt).strip().lower().replace(" ", "_")
            return text if text in CATEGORIES_SET else "other"
        except Exception as e:
            print(f"  ⚠️  AI categorization failed: {e}")
            return "other"

    def _call_llm(self, prompt: str) -> str:
        if self._provider == "openai":
            return self._call_openai(prompt)
        elif self._provider == "anthropic":
            return self._call_anthropic(prompt)
        raise ValueError(f"Unknown AI provider: {self._provider}")

    def _call_openai(self, prompt: str) -> str:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 20,
                "temperature": 0,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _call_anthropic(self, prompt: str) -> str:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 20,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


class ChainedCategorizer:
    """Tries keyword first, falls back to AI if result is 'other'."""

    def __init__(self, keyword: KeywordCategorizer, ai: AiCategorizer | None) -> None:
        self._keyword = keyword
        self._ai = ai

    def suggest(self, tab: Tab) -> str:
        result = self._keyword.suggest(tab)
        if result != "other" or self._ai is None:
            return result
        print("  🤖 Asking AI for category…")
        return self._ai.suggest(tab)


# ═══════════════════════════════════════════════════════════════════════
# ADAPTERS — Link repository
# ═══════════════════════════════════════════════════════════════════════


class SupabaseLinkRepository:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def fetch_existing(self) -> list[dict]:
        resp = httpx.get(
            f"{self._base_url}/functions/v1/select-table",
            params={"table": "links"},
            headers=self._headers,
        )
        resp.raise_for_status()
        return resp.json()

    def save_links(self, links: list[Link]) -> None:
        payload = [link.to_dict() for link in links]
        resp = httpx.post(
            f"{self._base_url}/functions/v1/insert-links",
            headers=self._headers,
            json=payload,
        )
        resp.raise_for_status()


class MockLinkRepository:
    def fetch_existing(self) -> list[dict]:
        return [
            {"url": "https://example.com/already-saved", "category": "other"},
        ]

    def save_links(self, links: list[Link]) -> None:
        print(f"\n  [MOCK POST] {json.dumps([l.to_dict() for l in links], indent=2)}")


# ═══════════════════════════════════════════════════════════════════════
# ADAPTERS — CLI prompter
# ═══════════════════════════════════════════════════════════════════════


class CliPrompter:
    def show_existing(self, links: list[dict]) -> None:
        print(f"\n📚 {len(links)} link(s) already in Supabase.\n")

    def present_tab(self, tab: Tab, index: int, total: int, already_saved: bool) -> None:
        flag = " ⚠️  (already saved)" if already_saved else ""
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
            print(f"  ⚠️  Unknown '{override}', using '{suggestion}'")
        return suggestion

    def confirm_batch(self, links: list[Link]) -> bool:
        print(f"\n📦 {len(links)} link(s) ready to POST:")
        for link in links:
            print(f"  • {link.category:25s} {link.url}")
        return input("\n  POST to Supabase? [y/N] ").strip().lower() == "y"

    def report_saved_json(self, path: Path) -> None:
        print(f"\n💾 JSON saved to {path}")

    def report_posted(self, count: int) -> None:
        print(f"✅ {count} link(s) posted to Supabase.")

    def report_skip(self) -> None:
        print("Nothing to save.")


# ═══════════════════════════════════════════════════════════════════════
# COMPOSITION ROOT
# ═══════════════════════════════════════════════════════════════════════


def _build_categorizer() -> CategorySuggester:
    """keyword heuristic → AI fallback (if an API key is configured)."""
    keyword = KeywordCategorizer()

    ai_provider = os.getenv("AI_PROVIDER", "").lower()          # "openai" or "anthropic"
    ai_key = os.getenv("AI_API_KEY", "")
    ai_model = os.getenv("AI_MODEL", "")

    # sensible defaults per provider
    if ai_provider == "openai" and not ai_model:
        ai_model = "gpt-4o-mini"
    elif ai_provider == "anthropic" and not ai_model:
        ai_model = "claude-haiku-4-5-20251001"

    if ai_provider and ai_key:
        ai = AiCategorizer(ai_provider, ai_key, ai_model)
        return ChainedCategorizer(keyword, ai)

    return ChainedCategorizer(keyword, ai=None)


def main() -> None:
    load_dotenv()

    base_url = os.getenv("SUPABASE_URL", "https://YOUR_PROJECT_ID.supabase.co")
    api_key = os.getenv("SUPABASE_KEY", "")
    mock = os.getenv("MOCK", "true").lower() == "true"

    tab_source = ChromeAppleScriptSource()

    repository: LinkRepository
    if mock:
        repository = MockLinkRepository()
    else:
        if not api_key:
            print("❌ SUPABASE_KEY must be set in .env when MOCK=false")
            sys.exit(1)
        repository = SupabaseLinkRepository(base_url, api_key)

    categorizer = _build_categorizer()
    prompter = CliPrompter()
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    use_case = CurateTabsUseCase(tab_source, repository, categorizer, prompter, output_dir)
    use_case.execute()


if __name__ == "__main__":
    main()
