"""Category suggestion adapters: keyword heuristic and AI fallback."""

from __future__ import annotations

from ..domain import CATEGORIES, CATEGORIES_SET, Tab


class KeywordCategorizer:
    """Fast, offline keyword matching. Returns 'other' when unsure."""

    _RULES: list[tuple[list[str], str]] = [
        (["llm", "gpt", "openai", "anthropic", "gemini", "llama", "mistral", "genai", "chatgpt", "copilot", "prompt engineer"], "generative_ai"),
        (["deep learning", "pytorch", "tensorflow", "neural net", "cnn", "rnn", "transformer architecture"], "deep_learning"),
        (["mlflow", "sklearn", "scikit", "xgboost", "reinforcement", "ml ", "machine learning", "feature store"], "machine_learning"),
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
            print(f"  AI categorization failed: {e}")
            return "other"

    def _call_llm(self, prompt: str) -> str:
        import httpx

        if self._provider == "openai":
            return self._call_openai(httpx, prompt)
        elif self._provider == "anthropic":
            return self._call_anthropic(httpx, prompt)
        raise ValueError(f"Unknown AI provider: {self._provider}")

    def _call_openai(self, httpx: object, prompt: str) -> str:
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

    def _call_anthropic(self, httpx: object, prompt: str) -> str:
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
        print("  Asking AI for category...")
        return self._ai.suggest(tab)
