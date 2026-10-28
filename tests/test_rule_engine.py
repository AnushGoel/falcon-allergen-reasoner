"""Unit tests for the FALCON rule engine (no knowledge base needed)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from falcon.rule_engine import Atom, BackwardChainer, FactStore, ForwardChainer, Var, parse_rule  # noqa: E402


class ParsingTests(unittest.TestCase):
    def test_round_trip(self):
        rule = parse_rule('A(?x), b(?x, "complete"), not C(?x), d(?x, ?v), greaterThan(?v, 10.5) -> E(?x)', "T1")
        self.assertEqual(len(rule.body), 5)
        self.assertTrue(rule.body[2].negated)
        self.assertEqual(rule.body[1].args[1], "complete")
        self.assertEqual(rule.body[4].args[1], 10.5)
        self.assertIn("\u2192", rule.to_fol())

    def test_unsafe_rules_rejected(self):
        with self.assertRaises(ValueError):
            parse_rule("A(?x) -> B(?y)", "head-variable-unbound")
        with self.assertRaises(ValueError):
            parse_rule("A(?x), not B(?y) -> C(?x)", "negated-variable-unbound")

    def test_negation_through_recursion_rejected(self):
        with self.assertRaises(ValueError):
            ForwardChainer([parse_rule("A(?x), not B(?x) -> B(?x)", "loop")])


class ForwardTests(unittest.TestCase):
    def test_transitive_closure(self):
        rules = [parse_rule("p(?x, ?y), p(?y, ?z) -> p(?x, ?z)", "TR")]
        result = ForwardChainer(rules).run([("p", ("a", "b")), ("p", ("b", "c")), ("p", ("c", "d"))])
        self.assertTrue(result.holds("p", "a", "d"))
        self.assertEqual(result.store.count("p"), 6)

    def test_negation_as_failure(self):
        rules = [parse_rule("Bird(?x), not Penguin(?x) -> Flies(?x)", "N1"),
                 parse_rule("Emperor(?x) -> Penguin(?x)", "N2")]
        result = ForwardChainer(rules).run([("Bird", ("tweety",)), ("Bird", ("pingu",)), ("Emperor", ("pingu",))])
        self.assertTrue(result.holds("Flies", "tweety"))
        self.assertFalse(result.holds("Flies", "pingu"))

    def test_builtin_boundary(self):
        rules = [parse_rule("ppm(?p, ?x), greaterThanOrEqual(?x, 10.0) -> Declare(?p)", "B1"),
                 parse_rule("ppm(?p, ?x), greaterThan(?x, 10.0) -> DeclareEU(?p)", "B2")]
        result = ForwardChainer(rules).run([("ppm", ("a", 10.0)), ("ppm", ("b", 9.99))])
        self.assertTrue(result.holds("Declare", "a"))
        self.assertFalse(result.holds("DeclareEU", "a"))
        self.assertFalse(result.holds("Declare", "b"))

    def test_explanation_tree(self):
        result = ForwardChainer([parse_rule("p(?x, ?y), p(?y, ?z) -> p(?x, ?z)", "TR")]).run(
            [("p", ("a", "b")), ("p", ("b", "c"))])
        proof = result.explain("p", "a", "c")
        self.assertEqual(proof.how, "TR")
        self.assertEqual(len(proof.children), 2)


class BackwardTests(unittest.TestCase):
    def setUp(self):
        self.rules = [parse_rule("p(?x, ?y), p(?y, ?z) -> p(?x, ?z)", "TR"),
                      parse_rule("p(?x, ?y), not Blocked(?y) -> reach(?x, ?y)", "RE")]
        self.facts = [("p", ("a", "b")), ("p", ("b", "c")), ("p", ("c", "d")), ("Blocked", ("c",))]

    def test_backward_matches_forward(self):
        forward = ForwardChainer(self.rules).run(self.facts)
        prover = BackwardChainer(self.rules, FactStore(self.facts))
        for pred in ("p", "reach"):
            backward = {(ans["x"], ans["y"]) for ans, _ in prover.ask(Atom(pred, (Var("x"), Var("y"))))}
            self.assertEqual(backward, set(forward.store.match(pred, (None, None))), pred)

    def test_why_not(self):
        prover = BackwardChainer(self.rules, FactStore(self.facts))
        reasons = " ".join(prover.why_not(Atom("reach", ("a", "c"))))
        self.assertIn("Blocked(c) holds", reasons)


class TestTabling(unittest.TestCase):
    def test_open_query_on_derived_only_left_recursion(self):
        """r has no stored facts and a left-recursive rule; plain loop checking loses c and d."""
        rules = [parse_rule("e(?x, ?y) -> r(?x, ?y)", "R1"), parse_rule("r(?x, ?y), e(?y, ?z) -> r(?x, ?z)", "R2")]
        facts = [("e", ("a", "b")), ("e", ("b", "c")), ("e", ("c", "d"))]
        forward = {args[1] for args in ForwardChainer(rules).run(facts).store.match("r", ("a", None))}
        prover = BackwardChainer(rules, FactStore(facts))
        self.assertEqual({ans["y"] for ans, _ in prover.ask(Atom("r", ("a", Var("y"))))}, forward)
        self.assertEqual(forward, {"b", "c", "d"})

    def test_negation_uses_complete_search(self):
        rules = [parse_rule("e(?x, ?y) -> r(?x, ?y)", "R1"), parse_rule("r(?x, ?y), e(?y, ?z) -> r(?x, ?z)", "R2"),
                 parse_rule("node(?x), not r(a, ?x) -> unreachable(?x)", "R3")]
        facts = [("e", ("a", "b")), ("e", ("b", "c")), ("node", ("c",)), ("node", ("z",))]
        prover = BackwardChainer(rules, FactStore(facts))
        self.assertIsNone(prover.prove(Atom("unreachable", ("c",))))     # c is reachable through recursion
        self.assertIsNotNone(prover.prove(Atom("unreachable", ("z",))))


if __name__ == "__main__":
    unittest.main()
