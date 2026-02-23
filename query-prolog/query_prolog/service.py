"""Orchestration: depends only on ports, never on adapters."""

from __future__ import annotations

import os
import re
import textwrap
from pathlib import Path

from .domain import FactFile, InputMode
from .ports import PrologEngine, QueryTranslator, UserInterface


class QueryFactsUseCase:
    """Interactive REPL for querying Prolog fact files."""

    def __init__(
        self,
        engine: PrologEngine,
        translator: QueryTranslator | None,
        ui: UserInterface,
        fact_file: FactFile,
    ) -> None:
        self._engine = engine
        self._translator = translator
        self._ui = ui
        self._facts = fact_file

    # -- execution (writes) --------------------------------------------------

    def execute(self) -> None:
        self._ui.show_fact_file(self._facts)

        ai_available = self._translator is not None
        mode_hint = "Prolog query or natural language" if ai_available else "Prolog query"
        self._ui.show_message(f"\nEnter a {mode_hint}. Commands: :quit :mode :help\n")

        while True:
            raw = self._ui.read_input()
            if raw is None:
                break

            text = raw.strip()
            if not text:
                continue

            # ── Meta commands ────────────────────────────────────────
            if text.startswith(":"):
                self._handle_command(text)
                continue

            # ── Detect mode ──────────────────────────────────────────
            mode = self._detect_mode(text)

            if mode == InputMode.NATURAL:
                if not self._translator:
                    self._ui.show_message("No AI configured. Use Prolog syntax or set AI_PROVIDER in .env")
                    continue
                self._ui.show_message("Translating to Prolog...")
                prolog_query = self._translator.translate(text, self._facts)
                self._ui.show_translation(prolog_query)
            else:
                prolog_query = text
                prolog_query = prolog_query.rstrip(".")

            result = self._engine.query(self._facts, prolog_query)
            self._ui.show_result(result)

    @staticmethod
    def _detect_mode(text: str) -> str:
        """Heuristic: if it looks like Prolog syntax, treat as direct query."""
        if re.match(r"^[a-z_]\w*\s*\(", text):
            return InputMode.PROLOG
        if any(op in text for op in [":-", "\\+", "is ", "=:=", "=\\=", "\\="]):
            return InputMode.PROLOG
        if text.startswith("?-"):
            return InputMode.PROLOG
        return InputMode.NATURAL

    def _handle_command(self, text: str) -> None:
        cmd = text.lower()
        if cmd in (":quit", ":q", ":exit"):
            raise SystemExit(0)
        elif cmd in (":help", ":h"):
            self._ui.show_message(textwrap.dedent("""
                Commands:
                  :quit / :q       Exit
                  :preds            Show predicates
                  :file             Show file summary
                  :help / :h        This help

                Input:
                  parent(X, bob).   Direct Prolog query
                  Who is bob's parent?   Natural language -> AI -> Prolog
            """))
        elif cmd == ":preds":
            self._ui.show_message(f"Predicates: {', '.join(self._facts.predicates)}")
        elif cmd == ":file":
            self._ui.show_fact_file(self._facts)
        else:
            self._ui.show_message(f"Unknown command: {text}")


def make_query_repl(pl_path: Path) -> QueryFactsUseCase:
    """Wire concrete adapters into the service."""
    from .adapters import AiQueryTranslator, CliInterface, SwiPrologEngine

    fact_file = FactFile.load(pl_path)
    engine = SwiPrologEngine()

    # Build translator if AI is configured
    ai_provider = os.getenv("AI_PROVIDER", "").lower()
    ai_key = os.getenv("AI_API_KEY", "")
    ai_model = os.getenv("AI_MODEL", "")

    if ai_provider == "openai" and not ai_model:
        ai_model = "gpt-4o-mini"
    elif ai_provider == "anthropic" and not ai_model:
        ai_model = "claude-haiku-4-5-20251001"

    translator = AiQueryTranslator(ai_provider, ai_key, ai_model) if ai_provider and ai_key else None
    ui = CliInterface()

    return QueryFactsUseCase(engine, translator, ui, fact_file)
