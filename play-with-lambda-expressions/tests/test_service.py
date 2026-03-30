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


if __name__ == "__main__":
    unittest.main()
