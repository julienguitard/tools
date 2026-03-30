"""Random closed-term generator."""

from __future__ import annotations

import random

from ..domain import Abs, App, Term, Var


class RandomTermGenerator:
    """Generates random closed lambda terms via recursive construction.

    Guarantees that every generated term is closed (no free variables)
    by tracking in-scope bindings and forcing abstractions when the
    scope is empty.
    """

    def generate(self, max_depth: int) -> Term:
        """Produce a random closed term with AST depth at most max_depth.

        Args:
            max_depth: Maximum nesting depth of the generated AST.

        Returns:
            A closed Term.
        """
        return self._gen(max_depth, [])

    def _gen(self, depth: int, scope: list[Var]) -> Term:
        """Recursively build a random term.

        Args:
            depth: Remaining depth budget.
            scope: Variables currently in scope (available for Var nodes).

        Returns:
            A Term whose free variables are a subset of scope.
        """
        if not scope:
            # No variables in scope — must introduce one via Abs.
            fresh = self._fresh_param(scope)
            return Abs(fresh, self._gen(depth - 1, scope + [fresh]))

        if depth <= 0:
            # Depth exhausted — return a variable from scope.
            return random.choice(scope)

        # Weighted choice: bias toward Var as depth decreases.
        var_weight = 3
        abs_weight = 2
        app_weight = 2
        roll = random.random() * (var_weight + abs_weight + app_weight)

        if roll < var_weight:
            return random.choice(scope)
        elif roll < var_weight + abs_weight:
            fresh = self._fresh_param(scope)
            return Abs(fresh, self._gen(depth - 1, scope + [fresh]))
        else:
            return App(
                self._gen(depth - 1, scope),
                self._gen(depth - 1, scope),
            )

    @staticmethod
    def _fresh_param(scope: list[Var]) -> Var:
        """Pick a fresh variable name not in scope.

        Args:
            scope: Currently in-scope variables.

        Returns:
            A Var with a name not used in scope.
        """
        used = {v.name for v in scope}
        # Try single letters first, then primed versions.
        for suffix_count in range(10):
            suffix = "'" * suffix_count
            for ch in "abcdefghijklmnopqrstuvwxyz":
                name = ch + suffix
                if name not in used:
                    return Var(name)
        # Fallback — should never be reached in practice.
        return Var(f"v{len(scope)}")
