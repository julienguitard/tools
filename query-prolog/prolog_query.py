#!/usr/bin/env python3
"""
Prolog Fact File Querier.

Interactive REPL that queries .pl fact files from the terminal.
Two input modes:
  - Direct Prolog query   →  executed as-is
  - Natural language       →  AI translates to Prolog query, then executes

Requires SWI-Prolog installed: brew install swi-prolog

Hexagonal architecture:
  Domain  → QueryResult, FactFile
  Ports   → PrologEngine, QueryTranslator, UserInterface
  Adapters→ SwiPrologEngine, AiQueryTranslator, DirectPassthrough, CliInterface
  App     → QueryFactsUseCase
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import httpx
from dotenv import load_dotenv


# ═══════════════════════════════════════════════════════════════════════
# DOMAIN
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class FactFile:
    path: Path
    content: str
    predicates: list[str]  # e.g. ["parent/2", "male/1", "ancestor/2"]

    @classmethod
    def load(cls, path: Path) -> FactFile:
        content = path.read_text()
        predicates = cls._extract_predicates(content)
        return cls(path=path, content=content, predicates=predicates)

    @staticmethod
    def _extract_predicates(content: str) -> list[str]:
        """Extract unique predicate signatures from a .pl file."""
        seen: dict[str, int] = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("%") or line.startswith("/*"):
                continue
            # Match: predicate_name(arg1, arg2, ...).
            # Also match rule heads: predicate_name(args) :-
            match = re.match(r"^(\w+)\(([^)]*)\)", line)
            if match:
                name = match.group(1)
                arity = len([a.strip() for a in match.group(2).split(",") if a.strip()])
                key = f"{name}/{arity}"
                seen[key] = seen.get(key, 0) + 1
        return sorted(seen.keys())

    def summary(self) -> str:
        lines = [f"📄 {self.path.name}"]
        lines.append(f"   Predicates: {', '.join(self.predicates) if self.predicates else '(none detected)'}")
        # Show first few facts as examples
        examples = [l.strip() for l in self.content.splitlines()
                     if l.strip() and not l.strip().startswith("%")][:5]
        lines.append(f"   Sample facts:")
        for ex in examples:
            lines.append(f"     {ex}")
        if len([l for l in self.content.splitlines() if l.strip() and not l.strip().startswith("%")]) > 5:
            lines.append(f"     …")
        return "\n".join(lines)


@dataclass
class QueryResult:
    query: str
    success: bool
    bindings: list[dict[str, str]] = field(default_factory=list)
    error: str = ""

    def display(self) -> str:
        if self.error:
            return f"❌ Error: {self.error}"
        if not self.success:
            return "false."
        if not self.bindings:
            return "true."
        lines = []
        for b in self.bindings:
            parts = [f"{k} = {v}" for k, v in b.items()]
            lines.append(", ".join(parts))
        return "\n".join(lines)


class InputMode:
    PROLOG = "prolog"
    NATURAL = "natural"


# ═══════════════════════════════════════════════════════════════════════
# PORTS
# ═══════════════════════════════════════════════════════════════════════


class PrologEngine(Protocol):
    def query(self, fact_file: FactFile, prolog_query: str) -> QueryResult: ...


class QueryTranslator(Protocol):
    def translate(self, natural_query: str, fact_file: FactFile) -> str: ...


class UserInterface(Protocol):
    def show_fact_file(self, fact_file: FactFile) -> None: ...
    def read_input(self) -> str | None: ...
    def show_translation(self, prolog_query: str) -> None: ...
    def show_result(self, result: QueryResult) -> None: ...
    def show_message(self, msg: str) -> None: ...


# ═══════════════════════════════════════════════════════════════════════
# APPLICATION
# ═══════════════════════════════════════════════════════════════════════


class QueryFactsUseCase:
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
                    self._ui.show_message("⚠️  No AI configured. Use Prolog syntax or set AI_PROVIDER in .env")
                    continue
                self._ui.show_message("🤖 Translating to Prolog…")
                prolog_query = self._translator.translate(text, self._facts)
                self._ui.show_translation(prolog_query)
            else:
                prolog_query = text
                # Strip trailing period if present (we add it in the engine)
                prolog_query = prolog_query.rstrip(".")

            result = self._engine.query(self._facts, prolog_query)
            self._ui.show_result(result)

    @staticmethod
    def _detect_mode(text: str) -> str:
        """Heuristic: if it looks like Prolog syntax, treat as direct query."""
        # Starts with a known Prolog pattern: functor(, findall(, \+, etc.
        if re.match(r"^[a-z_]\w*\s*\(", text):
            return InputMode.PROLOG
        # Contains Prolog operators
        if any(op in text for op in [":-", "\\+", "is ", "=:=", "=\\=", "\\="]):
            return InputMode.PROLOG
        # Explicit prefix
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
                  Who is bob's parent?   Natural language → AI → Prolog
            """))
        elif cmd == ":preds":
            self._ui.show_message(f"Predicates: {', '.join(self._facts.predicates)}")
        elif cmd == ":file":
            self._ui.show_fact_file(self._facts)
        else:
            self._ui.show_message(f"Unknown command: {text}")


# ═══════════════════════════════════════════════════════════════════════
# ADAPTERS — Prolog engine
# ═══════════════════════════════════════════════════════════════════════


class SwiPrologEngine:
    """Executes queries via SWI-Prolog subprocess."""

    def __init__(self, swipl_path: str = "swipl") -> None:
        self._swipl = swipl_path

    def query(self, fact_file: FactFile, prolog_query: str) -> QueryResult:
        # Build a small Prolog script that loads the file, runs the query,
        # and prints variable bindings in a parseable format.
        variables = self._extract_variables(prolog_query)

        if variables:
            # Print each binding set as key=value pairs
            write_parts = []
            for v in variables:
                write_parts.append(f"write('{v}='), write({v})")
            write_goal = ", ".join(write_parts)
            goal = (
                f"(   {prolog_query},\n"
                f"    {write_goal}, nl, fail\n"
                f";   true\n"
                f"), halt."
            )
        else:
            goal = f"( {prolog_query} -> write(true) ; write(false) ), nl, halt."

        script = f":- consult('{fact_file.path.resolve()}').\n:- {goal}\n"

        try:
            result = subprocess.run(
                [self._swipl, "-q", "-t", "halt", "-f", "/dev/null", "-g", f"['{fact_file.path.resolve()}']", "-g", goal],
                capture_output=True, text=True, timeout=10,
            )
        except FileNotFoundError:
            return QueryResult(query=prolog_query, success=False, error="SWI-Prolog not found. Install with: brew install swi-prolog")
        except subprocess.TimeoutExpired:
            return QueryResult(query=prolog_query, success=False, error="Query timed out (10s)")

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # Filter out SWI-Prolog warnings
        stderr_lines = [l for l in stderr.splitlines() if not l.startswith("Warning:")]
        real_errors = "\n".join(stderr_lines).strip()

        if real_errors:
            return QueryResult(query=prolog_query, success=False, error=real_errors)

        if not stdout:
            return QueryResult(query=prolog_query, success=False)

        if stdout == "true":
            return QueryResult(query=prolog_query, success=True)
        if stdout == "false":
            return QueryResult(query=prolog_query, success=False)

        # Parse variable bindings
        bindings = []
        for line in stdout.splitlines():
            if "=" in line:
                pairs = {}
                # Split on variable boundaries: "X=alice Y=bob" or "X=aliceY=bob"
                parts = re.findall(r"([A-Z_]\w*)=([^A-Z\s]+|[^A-Z]*?)(?=\s*[A-Z_]\w*=|$)", line)
                for var, val in parts:
                    pairs[var] = val
                if pairs:
                    bindings.append(pairs)

        return QueryResult(
            query=prolog_query,
            success=bool(bindings),
            bindings=bindings,
        )

    @staticmethod
    def _extract_variables(query: str) -> list[str]:
        """Extract Prolog variables (uppercase identifiers) from a query."""
        # Exclude _ (anonymous) and built-in atoms
        matches = re.findall(r"\b([A-Z][A-Za-z0-9_]*)\b", query)
        # Deduplicate preserving order
        seen: set[str] = set()
        result: list[str] = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                result.append(m)
        return result


# ═══════════════════════════════════════════════════════════════════════
# ADAPTERS — Query translator
# ═══════════════════════════════════════════════════════════════════════


class AiQueryTranslator:
    """Translates natural language → Prolog using an LLM."""

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
            # Clean up common LLM artifacts
            text = text.strip("`").strip()
            text = text.removeprefix("```prolog").removesuffix("```").strip()
            text = text.rstrip(".")
            return text
        except Exception as e:
            return f"_error({e})"

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
                "max_tokens": 150,
                "temperature": 0,
            },
            timeout=15,
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
                "max_tokens": 150,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


# ═══════════════════════════════════════════════════════════════════════
# ADAPTERS — CLI interface
# ═══════════════════════════════════════════════════════════════════════


class CliInterface:
    def show_fact_file(self, fact_file: FactFile) -> None:
        print(f"\n{fact_file.summary()}")

    def read_input(self) -> str | None:
        try:
            return input("\n?- ")
        except (EOFError, KeyboardInterrupt):
            print()
            return None

    def show_translation(self, prolog_query: str) -> None:
        print(f"   → {prolog_query}")

    def show_result(self, result: QueryResult) -> None:
        print(result.display())

    def show_message(self, msg: str) -> None:
        print(msg)


# ═══════════════════════════════════════════════════════════════════════
# COMPOSITION ROOT
# ═══════════════════════════════════════════════════════════════════════


def _build_translator() -> AiQueryTranslator | None:
    ai_provider = os.getenv("AI_PROVIDER", "").lower()
    ai_key = os.getenv("AI_API_KEY", "")
    ai_model = os.getenv("AI_MODEL", "")

    if ai_provider == "openai" and not ai_model:
        ai_model = "gpt-4o-mini"
    elif ai_provider == "anthropic" and not ai_model:
        ai_model = "claude-haiku-4-5-20251001"

    if ai_provider and ai_key:
        return AiQueryTranslator(ai_provider, ai_key, ai_model)
    return None


def main() -> None:
    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python prolog_query.py <file.pl>")
        print("       python prolog_query.py family.pl")
        sys.exit(1)

    pl_path = Path(sys.argv[1])
    if not pl_path.exists():
        print(f"❌ File not found: {pl_path}")
        sys.exit(1)

    fact_file = FactFile.load(pl_path)
    engine = SwiPrologEngine()
    translator = _build_translator()
    ui = CliInterface()

    use_case = QueryFactsUseCase(engine, translator, ui, fact_file)
    use_case.execute()


if __name__ == "__main__":
    main()
