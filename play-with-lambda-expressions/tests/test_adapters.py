"""Tests for adapters — random generator closure guarantee, name registry."""

from __future__ import annotations

import unittest

from play_with_lambda.adapters import InMemoryNameRegistry, RandomTermGenerator
from play_with_lambda.domain import Abs, ParseError, Var, is_closed, stringify, parse


class TestRandomTermGenerator(unittest.TestCase):
    """Random generator must produce closed terms within depth bounds."""

    def test_all_closed(self) -> None:
        gen = RandomTermGenerator()
        for depth in range(1, 6):
            for _ in range(20):
                term = gen.generate(depth)
                assert is_closed(term), (
                    f"Open term at depth={depth}: {stringify(term)}"
                )

    def test_depth_zero(self) -> None:
        gen = RandomTermGenerator()
        # depth=0 with empty scope must still produce a valid closed term
        for _ in range(10):
            term = gen.generate(0)
            assert is_closed(term)


class TestInMemoryNameRegistry(unittest.TestCase):
    """Name registry loads standard library and supports bind/lookup."""

    def test_standard_library_loaded(self) -> None:
        reg = InMemoryNameRegistry()
        names = reg.all_names()
        expected = {
            "I", "K", "S", "Y", "OMEGA",
            "TRUE", "FALSE", "AND", "OR", "NOT",
            "ZERO", "SUCC", "PLUS", "MULT",
        }
        assert set(names.keys()) == expected

    def test_standard_library_parseable(self) -> None:
        reg = InMemoryNameRegistry()
        for name, term in reg.all_names().items():
            s = stringify(term)
            reparsed = parse(s)
            assert not isinstance(reparsed, ParseError), (
                f"{name} round-trip failed: {s}"
            )

    def test_bind_and_lookup(self) -> None:
        reg = InMemoryNameRegistry()
        term = Abs(Var("x"), Var("x"))
        reg.bind("MY_ID", term)
        assert reg.lookup("MY_ID") == term

    def test_lookup_missing(self) -> None:
        reg = InMemoryNameRegistry()
        assert reg.lookup("NONEXISTENT") is None

    def test_bind_overwrites(self) -> None:
        reg = InMemoryNameRegistry()
        t1 = Abs(Var("x"), Var("x"))
        t2 = Abs(Var("y"), Var("y"))
        reg.bind("T", t1)
        reg.bind("T", t2)
        assert reg.lookup("T") == t2

    def test_all_names_is_copy(self) -> None:
        reg = InMemoryNameRegistry()
        names = reg.all_names()
        names["HACK"] = Var("x")
        assert reg.lookup("HACK") is None


if __name__ == "__main__":
    unittest.main()
