"""AI-powered natural language to Prolog query translation."""

from __future__ import annotations

from ..domain import FactFile


class AiQueryTranslator:
    """Translates natural language to Prolog using an LLM."""

    def __init__(self, provider: str, api_key: str, model: str) -> None:
        self._provider = provider
        self._api_key = api_key
        self._model = model

    def translate(self, natural_query: str, fact_file: FactFile) -> str:
        prompt = (
            f"You are a Prolog expert. Given the following Prolog fact file, "
            f"translate the natural language query into a valid SWI-Prolog query.\n\n"
            f"=== FACT FILE ({fact_file.path.name}) ===\n"
            f"{fact_file.content}\n"
            f"=== PREDICATES ===\n"
            f"{', '.join(fact_file.predicates)}\n\n"
            f"=== NATURAL LANGUAGE QUERY ===\n"
            f"{natural_query}\n\n"
            f"Reply with ONLY the Prolog query (no period at the end, no explanation, no markdown).\n"
            f"Use variables (uppercase) where appropriate for unknowns.\n"
            f"Examples of valid output: parent(X, bob)  |  ancestor(alice, Y)  |  findall(X, parent(X, bob), L)"
        )
        try:
            text = self._call_llm(prompt).strip()
            text = text.strip("`").strip()
            text = text.removeprefix("```prolog").removesuffix("```").strip()
            text = text.rstrip(".")
            return text
        except Exception as e:
            return f"_error({e})"

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
                "max_tokens": 150,
                "temperature": 0,
            },
            timeout=15,
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
                "max_tokens": 150,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]
