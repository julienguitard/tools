"""Tests for domain.py — parser, substitution, reduction, variable analysis."""

from __future__ import annotations

import unittest

from play_with_lambda.domain import (
    Abs,
    App,
    ParseError,
    Term,
    Var,
    beta_reduce,
    beta_reduce_step,
    binding_vars,
    bound_vars,
    free_vars,
    is_closed,
    is_normal_form,
    parse,
    stringify,
    substitute,
)


# -- Parser tests -------------------------------------------------------------


class TestParse(unittest.TestCase):
    """Parser tests: valid input, error cases, round-trips."""

    def test_variable(self) -> None:
        assert parse("x") == Var("x")

    def test_variable_multichar(self) -> None:
        assert parse("foo") == Var("foo")

    def test_abstraction_backslash(self) -> None:
        assert parse(r"\x.x") == Abs(Var("x"), Var("x"))

    def test_abstraction_lambda(self) -> None:
        assert parse("λx.x") == Abs(Var("x"), Var("x"))

    def test_application(self) -> None:
        assert parse("(f x)") == App(Var("f"), Var("x"))

    def test_nested_abstraction(self) -> None:
        assert parse(r"\x.\y.x") == Abs(Var("x"), Abs(Var("y"), Var("x")))

    def test_nested_application(self) -> None:
        result = parse("((f x) y)")
        assert result == App(App(Var("f"), Var("x")), Var("y"))

    def test_grouping_parens(self) -> None:
        result = parse(r"(\x.x)")
        assert result == Abs(Var("x"), Var("x"))

    def test_app_with_abs(self) -> None:
        result = parse(r"(\x.x y)")
        assert result == App(Abs(Var("x"), Var("x")), Var("y"))

    def test_complex_nested(self) -> None:
        result = parse(r"((\x.\y.x a) b)")
        expected = App(
            App(Abs(Var("x"), Abs(Var("y"), Var("x"))), Var("a")),
            Var("b"),
        )
        assert result == expected

    def test_name_resolution(self) -> None:
        names = {"I": Abs(Var("x"), Var("x"))}
        result = parse("I", names)
        assert result == Abs(Var("x"), Var("x"))

    def test_name_in_application(self) -> None:
        names = {"I": Abs(Var("x"), Var("x"))}
        result = parse("(I a)", names)
        assert result == App(Abs(Var("x"), Var("x")), Var("a"))

    def test_error_empty(self) -> None:
        result = parse("")
        assert isinstance(result, ParseError)

    def test_error_unclosed_paren(self) -> None:
        result = parse("(x y")
        assert isinstance(result, ParseError)

    def test_error_missing_dot(self) -> None:
        result = parse(r"\x x")
        assert isinstance(result, ParseError)

    def test_error_trailing_content(self) -> None:
        result = parse("x y")
        assert isinstance(result, ParseError)

    def test_whitespace_handling(self) -> None:
        assert parse("  x  ") == Var("x")
        assert parse(r"  \x . x  ") == Abs(Var("x"), Var("x"))


class TestRoundTrip(unittest.TestCase):
    """parse(stringify(t)) == t for valid terms."""

    def _check(self, term: Term) -> None:
        s = stringify(term)
        reparsed = parse(s)
        assert reparsed == term, f"{term} -> '{s}' -> {reparsed}"

    def test_var(self) -> None:
        self._check(Var("x"))

    def test_abs(self) -> None:
        self._check(Abs(Var("x"), Var("x")))

    def test_app(self) -> None:
        self._check(App(Var("f"), Var("x")))

    def test_nested_abs(self) -> None:
        self._check(Abs(Var("x"), Abs(Var("y"), App(Var("x"), Var("y")))))

    def test_nested_app(self) -> None:
        self._check(App(App(Var("a"), Var("b")), Var("c")))

    def test_abs_over_app(self) -> None:
        self._check(Abs(Var("f"), App(Var("f"), Var("x"))))

    def test_deeply_nested(self) -> None:
        # S combinator
        s = Abs(
            Var("x"),
            Abs(
                Var("y"),
                Abs(
                    Var("z"),
                    App(
                        App(Var("x"), Var("z")),
                        App(Var("y"), Var("z")),
                    ),
                ),
            ),
        )
        self._check(s)


class TestStringify(unittest.TestCase):
    """stringify produces expected output."""

    def test_var(self) -> None:
        assert stringify(Var("x")) == "x"

    def test_abs_uses_lambda(self) -> None:
        s = stringify(Abs(Var("x"), Var("x")))
        assert s == "λx.x"

    def test_app_uses_parens(self) -> None:
        s = stringify(App(Var("f"), Var("x")))
        assert s == "(f x)"


# -- Variable analysis tests --------------------------------------------------


class TestFreeVars(unittest.TestCase):
    def test_var(self) -> None:
        assert free_vars(Var("x")) == {Var("x")}

    def test_abs_binds(self) -> None:
        assert free_vars(Abs(Var("x"), Var("x"))) == set()

    def test_abs_free(self) -> None:
        assert free_vars(Abs(Var("x"), Var("y"))) == {Var("y")}

    def test_app(self) -> None:
        t = App(Var("x"), Var("y"))
        assert free_vars(t) == {Var("x"), Var("y")}

    def test_nested(self) -> None:
        t = parse(r"\x.(x y)")
        assert free_vars(t) == {Var("y")}


class TestBoundVars(unittest.TestCase):
    def test_var_not_bound(self) -> None:
        assert bound_vars(Var("x")) == set()

    def test_abs_binds(self) -> None:
        assert bound_vars(Abs(Var("x"), Var("x"))) == {Var("x")}

    def test_abs_not_used(self) -> None:
        # x is a binding var but not a bound var (y is free, x not used as Var)
        assert bound_vars(Abs(Var("x"), Var("y"))) == set()

    def test_nested(self) -> None:
        t = parse(r"\x.\y.(x y)")
        assert bound_vars(t) == {Var("x"), Var("y")}


class TestBindingVars(unittest.TestCase):
    def test_var(self) -> None:
        assert binding_vars(Var("x")) == set()

    def test_abs(self) -> None:
        assert binding_vars(Abs(Var("x"), Var("x"))) == {Var("x")}

    def test_nested_abs(self) -> None:
        t = parse(r"\x.\y.x")
        assert binding_vars(t) == {Var("x"), Var("y")}


class TestIsClosed(unittest.TestCase):
    def test_closed(self) -> None:
        assert is_closed(Abs(Var("x"), Var("x")))

    def test_open(self) -> None:
        assert not is_closed(Var("x"))


# -- Substitution tests -------------------------------------------------------


class TestSubstitute(unittest.TestCase):
    def test_identity(self) -> None:
        # x[y:=N] = x (no change)
        t = substitute(Var("x"), Var("y"), Var("z"))
        assert t == Var("x")

    def test_simple(self) -> None:
        # x[x:=y] = y
        t = substitute(Var("x"), Var("x"), Var("y"))
        assert t == Var("y")

    def test_app(self) -> None:
        t = substitute(
            App(Var("x"), Var("y")), Var("x"), Var("z"),
        )
        assert t == App(Var("z"), Var("y"))

    def test_shadowed(self) -> None:
        # (λx.x)[x:=y] = λx.x (x is rebound)
        t = substitute(Abs(Var("x"), Var("x")), Var("x"), Var("y"))
        assert t == Abs(Var("x"), Var("x"))

    def test_no_capture(self) -> None:
        # (λx.y)[y:=z] = λx.z (no capture, x != z)
        t = substitute(Abs(Var("x"), Var("y")), Var("y"), Var("z"))
        assert t == Abs(Var("x"), Var("z"))

    def test_capture_avoidance(self) -> None:
        # (λy.x)[x:=y] must alpha-rename y to avoid capture
        t = substitute(Abs(Var("y"), Var("x")), Var("x"), Var("y"))
        # Result should be λy'.y (param renamed, body substituted)
        assert t.param != Var("y"), "Capture not avoided!"
        assert t.body == Var("y"), "Substitution not applied in body"

    def test_capture_avoidance_nested(self) -> None:
        # (λy.λz.x)[x:=y] — both y and z in body
        inner = Abs(Var("z"), Var("x"))
        outer = Abs(Var("y"), inner)
        result = substitute(outer, Var("x"), Var("y"))
        assert result.param != Var("y")
        # The inner body should now contain Var("y") for the substituted x
        assert result.body.body == Var("y")


# -- Reduction tests ----------------------------------------------------------


class TestBetaReduceStep(unittest.TestCase):
    def test_redex(self) -> None:
        # (λx.x) a → a
        t = App(Abs(Var("x"), Var("x")), Var("a"))
        assert beta_reduce_step(t) == Var("a")

    def test_normal_form_var(self) -> None:
        assert beta_reduce_step(Var("x")) is None

    def test_normal_form_abs(self) -> None:
        assert beta_reduce_step(Abs(Var("x"), Var("x"))) is None

    def test_normal_form_app_no_redex(self) -> None:
        assert beta_reduce_step(App(Var("f"), Var("x"))) is None

    def test_reduce_inside_abs(self) -> None:
        # λx.(λy.y x) → λx.x
        inner = App(Abs(Var("y"), Var("y")), Var("x"))
        t = Abs(Var("x"), inner)
        result = beta_reduce_step(t)
        assert result == Abs(Var("x"), Var("x"))

    def test_reduce_func_first(self) -> None:
        # ((λx.x) a b) — reduce the function first
        t = App(App(Abs(Var("x"), Var("x")), Var("a")), Var("b"))
        result = beta_reduce_step(t)
        assert result == App(Var("a"), Var("b"))


class TestBetaReduce(unittest.TestCase):
    def test_identity(self) -> None:
        # I a → a
        t = App(Abs(Var("x"), Var("x")), Var("a"))
        final, trace, reached = beta_reduce(t)
        assert final == Var("a")
        assert reached
        assert len(trace) == 2

    def test_k_combinator(self) -> None:
        # K a b → a (two steps)
        k = Abs(Var("x"), Abs(Var("y"), Var("x")))
        t = App(App(k, Var("a")), Var("b"))
        final, trace, reached = beta_reduce(t)
        assert final == Var("a")
        assert reached

    def test_skk_is_identity(self) -> None:
        # S K K a → a
        s = parse(r"\x.\y.\z.((x z) (y z))")
        k = parse(r"\x.\y.x")
        skk_a = parse("(((S K) K) a)", {"S": s, "K": k})
        final, trace, reached = beta_reduce(skk_a, max_steps=20)
        assert final == Var("a"), f"SKK a = {stringify(final)}, expected a"
        assert reached

    def test_omega_diverges(self) -> None:
        omega = parse(r"(\x.(x x) \x.(x x))")
        final, trace, reached = beta_reduce(omega, max_steps=5)
        assert not reached
        assert len(trace) == 6  # original + 5 steps

    def test_already_normal(self) -> None:
        t = Var("x")
        final, trace, reached = beta_reduce(t)
        assert final == t
        assert reached
        assert len(trace) == 1


class TestIsNormalForm(unittest.TestCase):
    def test_var(self) -> None:
        assert is_normal_form(Var("x"))

    def test_abs_nf(self) -> None:
        assert is_normal_form(Abs(Var("x"), Var("x")))

    def test_app_no_redex(self) -> None:
        assert is_normal_form(App(Var("f"), Var("x")))

    def test_redex_not_nf(self) -> None:
        assert not is_normal_form(
            App(Abs(Var("x"), Var("x")), Var("a")),
        )


if __name__ == "__main__":
    unittest.main()
