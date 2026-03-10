"""SWI-Prolog subprocess adapter."""

from __future__ import annotations

import re
import subprocess

from ..domain import FactFile, QueryResult


class SwiPrologEngine:
    """Executes queries via SWI-Prolog subprocess."""

    def __init__(self, swipl_path: str = "swipl") -> None:
        self._swipl = swipl_path

    def query(self, fact_file: FactFile, prolog_query: str) -> QueryResult:
        """Execute a Prolog query via SWI-Prolog subprocess."""
        variables = self._extract_variables(prolog_query)

        if variables:
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

        try:
            result = subprocess.run(
                [self._swipl, "-q", "-t", "halt", "-f", "/dev/null",
                 "-g", f"['{fact_file.path.resolve()}']", "-g", goal],
                capture_output=True, text=True, timeout=10,
            )
        except FileNotFoundError:
            return QueryResult(query=prolog_query, success=False,
                               error="SWI-Prolog not found. Install with: brew install swi-prolog")
        except subprocess.TimeoutExpired:
            return QueryResult(query=prolog_query, success=False,
                               error="Query timed out (10s)")

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

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
                parts = re.findall(
                    r"([A-Z_]\w*)=([^A-Z\s]+|[^A-Z]*?)(?=\s*[A-Z_]\w*=|$)", line
                )
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
        matches = re.findall(r"\b([A-Z][A-Za-z0-9_]*)\b", query)
        seen: set[str] = set()
        result: list[str] = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                result.append(m)
        return result
