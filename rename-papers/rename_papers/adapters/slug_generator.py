"""Slug generation backed by the OpenAI chat completions API."""

from __future__ import annotations
import os
from ..domain import Article


class OpenAiSlugGenerator:
    """Slug generation backed by the OpenAI chat completions API."""

    SYSTEM_PROMPT = (
        "You are a research-paper librarian. Given the opening text of a PDF, "
        "produce a SHORT descriptive filename slug (3-6 words, snake_case, "
        "lowercase, ASCII only). Capture the core topic -- not authors, not "
        "'a study of'.\n\n"
        "Reply with ONLY the slug, nothing else.\n\n"
        "Good examples:\n"
        "  tensor_logic_for_ai\n"
        "  reversible_computing\n"
        "  kleene_algebra_domain\n"
        "  mathematical_model_of_oop\n"
        "  quantifying_human_ai_synergy\n"
        "  moore_law_for_slacking\n"
    )

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        from openai import OpenAI  # lazy import

        self._client = OpenAI(api_key=os.getenv("AI_API_KEY"))
        self._model = model

    def generate(self, text: str) -> str:
        if not text.strip():
            return "unknown_content"

        resp = self._client.chat.completions.create(
            model=self._model,
            temperature=0.2,
            max_tokens=60,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        raw = resp.choices[0].message.content.strip()
        return Article.sanitize_slug(raw)
