"""Tests for service.py — REPL command dispatch with mock ports."""

from __future__ import annotations

import unittest

from play_with_lambda.domain import Abs, App, Term, Var
from play_with_lambda.service import ReplConfig, ReplService


class FakeUI:
    """Mock UserInterface with scripted inputs and captured outputs."""

    def __init__(self, inputs: list[str]) -> None:
        self._inputs = iter(inputs)
        self.outputs: list[str] = []
        self.errors: list[str] = []

    def read_input(self) -> str | None:
        return next(self._inputs, None)

    def display(self, text: str) -> None:
        self.outputs.append(text)

    def display_error(self, text: str) -> None:
        self.errors.append(text)


class FakeGenerator:
    """Mock TermGenerator returning a fixed term."""

    def __init__(self, term: Term) -> None:
        self._term = term

    def generate(self, max_depth: int) -> Term:
        return self._term


class FakeRegistry:
    """Mock NameRegistry backed by a simple dict."""

    def __init__(self, names: dict[str, Term] | None = None) -> None:
        self._names: dict[str, Term] = dict(names or {})

    def bind(self, name: str, term: Term) -> None:
        self._names[name] = term

    def lookup(self, name: str) -> Term | None:
        return self._names.get(name)

    def all_names(self) -> dict[str, Term]:
        return dict(self._names)


def _make_service(
    inputs: list[str],
    names: dict[str, Term] | None = None,
    gen_term: Term | None = None,
    max_steps: int = 100,
) -> tuple[ReplService, FakeUI]:
    """Build a ReplService with fake ports."""
    ui = FakeUI(inputs)
    generator = FakeGenerator(gen_term or Abs(Var("x"), Var("x")))
    registry = FakeRegistry(names)
    config = ReplConfig(max_steps=max_steps, random_depth=3)
    svc = ReplService(ui=ui, generator=generator, registry=registry, config=config)
    return svc, ui


class TestDispatch(unittest.TestCase):
    def test_expression(self) -> None:
        svc, ui = _make_service([r"\x.x"])
        svc.run()
        assert "λx.x" in ui.outputs

    def test_quit(self) -> None:
        svc, ui = _make_service([":quit"])
        with self.assertRaises(SystemExit):
            svc.run()

    def test_unknown_command(self) -> None:
        svc, ui = _make_service([":foobar"])
        svc.run()
        assert any("unknown command" in e for e in ui.errors)


class TestReduce(unittest.TestCase):
    def test_reduce_identity(self) -> None:
        svc, ui = _make_service([r":reduce (\x.x y)"])
        svc.run()
        assert "y" in ui.outputs

    def test_reduce_no_arg(self) -> None:
        svc, ui = _make_service([":reduce"])
        svc.run()
        assert any(":reduce requires" in e for e in ui.errors)

    def test_reduce_limit(self) -> None:
        svc, ui = _make_service(
            [r":reduce (\x.(x x) \x.(x x))"], max_steps=3,
        )
        svc.run()
        assert any("stopped after" in o for o in ui.outputs)


class TestStep(unittest.TestCase):
    def test_step_redex(self) -> None:
        svc, ui = _make_service([r":step (\x.x y)"])
        svc.run()
        assert "y" in ui.outputs

    def test_step_normal_form(self) -> None:
        svc, ui = _make_service([":step x"])
        svc.run()
        assert any("normal form" in o.lower() for o in ui.outputs)


class TestTrace(unittest.TestCase):
    def test_trace(self) -> None:
        svc, ui = _make_service([r":trace ((\x.\y.x a) b)"])
        svc.run()
        # Should have numbered steps
        assert any("0:" in o for o in ui.outputs)
        assert any("a" in o for o in ui.outputs)


class TestVars(unittest.TestCase):
    def test_free(self) -> None:
        svc, ui = _make_service([r":free \x.(x y)"])
        svc.run()
        assert any("y" in o for o in ui.outputs)

    def test_bound(self) -> None:
        svc, ui = _make_service([r":bound \x.(x y)"])
        svc.run()
        assert any("x" in o for o in ui.outputs)

    def test_binding(self) -> None:
        svc, ui = _make_service([r":binding \x.\y.x"])
        svc.run()
        assert any("x" in o and "y" in o for o in ui.outputs)


class TestLet(unittest.TestCase):
    def test_let_and_resolve(self) -> None:
        svc, ui = _make_service([
            r":let ID = \x.x",
            r":reduce (ID a)",
        ])
        svc.run()
        # ID should be bound and :reduce (ID a) should give a
        assert "a" in ui.outputs

    def test_let_no_eq(self) -> None:
        svc, ui = _make_service([":let foo"])
        svc.run()
        assert any("requires" in e for e in ui.errors)


class TestRandom(unittest.TestCase):
    def test_random_default(self) -> None:
        fixed = Abs(Var("a"), Var("a"))
        svc, ui = _make_service([":random"], gen_term=fixed)
        svc.run()
        assert "λa.a" in ui.outputs

    def test_random_with_depth(self) -> None:
        fixed = Abs(Var("a"), Var("a"))
        svc, ui = _make_service([":random 5"], gen_term=fixed)
        svc.run()
        assert "λa.a" in ui.outputs

    def test_random_bad_depth(self) -> None:
        svc, ui = _make_service([":random abc"])
        svc.run()
        assert any("invalid depth" in e for e in ui.errors)


class TestList(unittest.TestCase):
    def test_list_empty(self) -> None:
        svc, ui = _make_service([":list"])
        svc.run()
        assert any("no named" in o.lower() for o in ui.outputs)

    def test_list_with_names(self) -> None:
        names = {"I": Abs(Var("x"), Var("x"))}
        svc, ui = _make_service([":list"], names=names)
        svc.run()
        assert any("I" in o and "λx.x" in o for o in ui.outputs)


class TestHelp(unittest.TestCase):
    def test_help(self) -> None:
        svc, ui = _make_service([":help"])
        svc.run()
        assert any(":reduce" in o for o in ui.outputs)


class TestParseError(unittest.TestCase):
    def test_invalid_expression(self) -> None:
        svc, ui = _make_service(["(x y"])
        svc.run()
        assert ui.errors  # At least one error shown


# -- Pipe tests ---------------------------------------------------------------


class TestPipe(unittest.TestCase):
    def test_simple_pipe(self) -> None:
        svc, ui = _make_service([r"(\x.x a) |> :reduce"])
        svc.run()
        assert "a" in ui.outputs

    def test_multi_pipe(self) -> None:
        svc, ui = _make_service([r"((\x.\y.x a) b) |> :step |> :reduce"])
        svc.run()
        assert "a" in ui.outputs

    def test_pipe_to_free(self) -> None:
        svc, ui = _make_service([r"\x.(x y) |> :free"])
        svc.run()
        assert any("{y}" in o for o in ui.outputs)

    def test_pipe_to_bound(self) -> None:
        svc, ui = _make_service([r"\x.(x y) |> :bound"])
        svc.run()
        assert any("{x}" in o for o in ui.outputs)

    def test_pipe_to_binding(self) -> None:
        svc, ui = _make_service([r"\x.\y.x |> :binding"])
        svc.run()
        assert any("x" in o and "y" in o for o in ui.outputs)

    def test_pipe_trace_passthrough(self) -> None:
        """Trace displays steps AND passes final term through."""
        svc, ui = _make_service([r"(\x.x a) |> :trace |> :free"])
        svc.run()
        # Trace steps displayed
        assert any("0:" in o for o in ui.outputs)
        # Then :free displayed on the final term
        assert any("{a}" in o for o in ui.outputs)

    def test_pipe_from_random(self) -> None:
        fixed = Abs(Var("a"), Var("a"))
        svc, ui = _make_service([":random 3 |> :reduce"], gen_term=fixed)
        svc.run()
        assert "λa.a" in ui.outputs

    def test_pipe_error_bad_source(self) -> None:
        svc, ui = _make_service([":list |> :reduce"])
        svc.run()
        assert any("cannot start pipe" in e for e in ui.errors)

    def test_pipe_error_bad_segment(self) -> None:
        svc, ui = _make_service([r"\x.x |> :quit"])
        svc.run()
        assert any("cannot pipe" in e for e in ui.errors)

    def test_pipe_error_non_command_segment(self) -> None:
        svc, ui = _make_service([r"\x.x |> foo"])
        svc.run()
        assert any("expected :command" in e for e in ui.errors)

    def test_pipe_parse_error_short_circuits(self) -> None:
        svc, ui = _make_service(["(x y |> :reduce"])
        svc.run()
        assert ui.errors


class TestLetPipe(unittest.TestCase):
    def test_let_with_pipe(self) -> None:
        names = {
            "SUCC": Abs(Var("n"), Abs(Var("f"), Abs(Var("x"),
                App(Var("f"), App(App(Var("n"), Var("f")), Var("x")))))),
            "ZERO": Abs(Var("f"), Abs(Var("x"), Var("x"))),
        }
        svc, ui = _make_service(
            [":let ONE = (SUCC ZERO) |> :reduce", "ONE"], names=names,
        )
        svc.run()
        # ONE should be bound and displayable
        assert any("ONE" in o for o in ui.outputs)

    def test_let_without_pipe(self) -> None:
        svc, ui = _make_service([r":let ID = \x.x", "ID"])
        svc.run()
        assert any("λx.x" in o for o in ui.outputs)


class TestAssertEq(unittest.TestCase):
    def test_assert_pass(self) -> None:
        svc, ui = _make_service([r"(\x.x a) |> :reduce |> :assert_eq a"])
        svc.run()
        assert "  ok" in ui.outputs

    def test_assert_fail(self) -> None:
        svc, ui = _make_service([r"(\x.x a) |> :assert_eq a"])
        svc.run()
        assert any("assertion failed" in e for e in ui.errors)

    def test_assert_no_arg(self) -> None:
        svc, ui = _make_service([r"\x.x |> :assert_eq"])
        svc.run()
        assert any("requires" in e for e in ui.errors)

    def test_assert_bad_parse(self) -> None:
        svc, ui = _make_service([r"\x.x |> :assert_eq (bad"])
        svc.run()
        assert ui.errors


if __name__ == "__main__":
    unittest.main()
