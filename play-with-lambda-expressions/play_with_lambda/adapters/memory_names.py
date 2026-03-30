"""In-memory named term registry with standard library preloaded."""

from __future__ import annotations

from ..domain import Term, parse, ParseError


STANDARD_LIBRARY: dict[str, str] = {
    "I": r"\x.x",
    "K": r"\x.\y.x",
    "S": r"\x.\y.\z.((x z) (y z))",
    "Y": r"\f.(\x.(f (x x)) \x.(f (x x)))",
    "OMEGA": r"(\x.(x x) \x.(x x))",
    "TRUE": r"\x.\y.x",
    "FALSE": r"\x.\y.y",
    "AND": r"\p.\q.((p q) p)",
    "OR": r"\p.\q.((p p) q)",
    "NOT": r"\p.((p \x.\y.y) \x.\y.x)",
    "ZERO": r"\f.\x.x",
    "SUCC": r"\n.\f.\x.(f ((n f) x))",
    "PLUS": r"\m.\n.\f.\x.((m f) ((n f) x))",
    "MULT": r"\m.\n.\f.(m (n f))",
}


class InMemoryNameRegistry:
    """Dict-backed name registry, preloaded with standard combinators.

    Implements the NameRegistry protocol.
    """

    def __init__(self) -> None:
        self._names: dict[str, Term] = {}
        for name, source in STANDARD_LIBRARY.items():
            result = parse(source)
            if isinstance(result, ParseError):
                continue
            self._names[name] = result

    def bind(self, name: str, term: Term) -> None:
        """Associate a name with a term (overwrites if exists).

        Args:
            name: The name to bind.
            term: The term to associate.
        """
        self._names[name] = term

    def lookup(self, name: str) -> Term | None:
        """Return the term bound to name, or None.

        Args:
            name: The name to look up.

        Returns:
            The bound term, or None if not found.
        """
        return self._names.get(name)

    def all_names(self) -> dict[str, Term]:
        """Return all name-term bindings.

        Returns:
            A shallow copy of the internal name registry.
        """
        return dict(self._names)
