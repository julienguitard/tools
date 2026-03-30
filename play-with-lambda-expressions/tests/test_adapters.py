"""Tests for adapters — random generator closure guarantee, name registry."""

from __future__ import annotations

import unittest

from play_with_lambda.adapters import (
    InMemoryNameRegistry,
    RandomTermGenerator,
    ScriptUI,
)
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


class TestScriptUI(unittest.TestCase):
    """ScriptUI reads lines, skips comments and blanks."""

    def test_reads_lines(self) -> None:
        ui = ScriptUI(["x", "y"])
        assert ui.read_input() == "x"
        assert ui.read_input() == "y"
        assert ui.read_input() is None

    def test_skips_comments(self) -> None:
        ui = ScriptUI(["# comment", "x", "  # indented comment", "y"])
        assert ui.read_input() == "x"
        assert ui.read_input() == "y"
        assert ui.read_input() is None

    def test_skips_blanks(self) -> None:
        ui = ScriptUI(["", "  ", "x", ""])
        assert ui.read_input() == "x"
        assert ui.read_input() is None

    def test_strips_whitespace(self) -> None:
        ui = ScriptUI(["  :reduce x  "])
        assert ui.read_input() == ":reduce x"


class TestScriptExecution(unittest.TestCase):
    """End-to-end script execution via make_script_repl."""

    def test_script_with_pipes_and_assert(self) -> None:
        from play_with_lambda.service import make_script_repl

        lines = [
            "# Church numerals exercise",
            r":let ONE = (SUCC ZERO) |> :reduce",
            r":let TWO = (SUCC ONE) |> :reduce",
            r"(PLUS ONE TWO) |> :reduce |> :assert_eq \f.\x.(f (f (f x)))",
        ]
        repl = make_script_repl(lines)
        # Should not raise — all assertions pass
        repl.run()

    def test_script_assert_failure(self) -> None:
        import io
        import contextlib

        from play_with_lambda.service import make_script_repl

        lines = [
            r"(\x.x a) |> :assert_eq b",
        ]
        repl = make_script_repl(lines)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            repl.run()
        assert "assertion failed" in output.getvalue()


if __name__ == "__main__":
    unittest.main()
