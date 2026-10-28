"""Behavioural tests: each one pins down a domain conclusion the report relies on."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from falcon import competency  # noqa: E402
from falcon.engine_bridge import build_rules, make_prover, run_engine  # noqa: E402
from falcon.kb_loader import load_kb  # noqa: E402
from falcon.rule_engine import Atom  # noqa: E402


class KnowledgeBaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = load_kb()
        cls.rules = build_rules(cls.kb)
        _, cls.r = run_engine(cls.kb, rules=cls.rules)
        cls.prover = make_prover(cls.kb, cls.rules)

    def test_open_queries_match_forward_chaining(self):
        """Regression test for the Colab run: open questions must return every forward-derived answer."""
        for p in self.kb.products:
            back = {ans["a"] for ans, _ in self.prover.ask("containsAllergen(%s, ?a)" % p)}
            self.assertEqual(back, {a for _, a in self.r.query("containsAllergen", p, None)}, p)

    def test_loads_cleanly(self):
        self.assertEqual(self.kb.errors, [])
        self.assertEqual(len(self.kb.products), 45)

    def test_hidden_fish_breaks_vegan_claim(self):
        p = "prod_steakhouse_sauce"
        self.assertTrue(self.r.holds("containsAllergen", p, "alg_fish"))
        self.assertTrue(self.r.holds("contradictsClaim", p, "claim_vegan"))
        self.assertTrue(self.r.holds("undeclaredAllergen", p, "alg_fish", "jur_us"))
        self.assertTrue(self.r.holds("hiddenAllergenVia", p, "alg_fish", "ing_worcestershire_sauce"))

    def test_gluten_free_is_not_wheat_free(self):
        p = "prod_gf_bread_codex"
        self.assertFalse(self.r.holds("contradictsClaim", p, "claim_gluten_free"))
        self.assertTrue(self.r.holds("containsAllergen", p, "alg_wheat"))
        self.assertTrue(self.r.holds("unsafeFor", p, "cons_wei"))
        self.assertFalse(self.r.holds("unsafeFor", p, "cons_sofia"))

    def test_sulphite_boundary_differs_by_market(self):
        p = "prod_dried_apricots"
        self.assertTrue(self.r.holds("declarationDuty", p, "alg_sulphites", "jur_us"))
        self.assertTrue(self.r.holds("declarationDuty", p, "alg_sulphites", "jur_canada"))
        self.assertFalse(self.r.holds("declarationDuty", p, "alg_sulphites", "jur_eu"))

    def test_pine_nut_depends_on_market(self):
        p = "prod_pesto_genovese"
        self.assertTrue(self.r.holds("undeclaredAllergen", p, "alg_pine_nut", "jur_us"))
        self.assertTrue(self.r.holds("undeclaredAllergen", p, "alg_pine_nut", "jur_canada"))
        self.assertFalse(self.r.holds("declarationDuty", p, "alg_pine_nut", "jur_eu"))

    def test_eu_exemption_is_defeasible(self):
        p = "prod_wheat_glucose_candy"
        self.assertTrue(self.r.holds("mustDeclareInEU", p, "alg_wheat"))            # monotonic SWRL
        self.assertFalse(self.r.holds("declarationDuty", p, "alg_wheat", "jur_eu"))  # exemption applied

    def test_incomplete_records_are_never_confirmed(self):
        for p in ("prod_mystery_snack", "prod_rice_puffs_incomplete"):
            self.assertEqual(self.r.query("confirmedSafeFor", p, None), [])
        self.assertTrue(self.r.holds("claimUnverifiable", "prod_rice_puffs_incomplete", "claim_nut_free"))

    def test_precautionary_conflict(self):
        self.assertTrue(self.r.holds("precautionaryConflictWith", "prod_dark_chocolate", "claim_dairy_free"))
        self.assertTrue(self.r.holds("claimVerified", "prod_dark_chocolate", "claim_vegan"))

    def test_non_dairy_still_contains_milk(self):
        p = "prod_non_dairy_whitener"
        self.assertTrue(self.r.holds("containsAllergen", p, "alg_milk"))
        self.assertFalse(self.r.holds("contradictsClaim", p, "claim_non_dairy"))
        self.assertTrue(self.r.holds("unsafeFor", p, "cons_maya"))

    def test_refined_oil_is_not_an_allergen_source(self):
        p = "prod_cooking_spray"
        self.assertTrue(self.r.holds("containsVia", p, "alg_soy", "ing_soy_lecithin"))
        self.assertFalse(self.r.holds("containsVia", p, "alg_soy", "ing_refined_soybean_oil"))

    def test_backward_proves_what_forward_derives(self):
        for (p, a) in self.r.query("containsAllergen", None, None)[:60]:
            self.assertIsNotNone(self.prover.prove(Atom("containsAllergen", (p, a))), (p, a))

    def test_no_integrity_violations(self):
        self.assertEqual(self.r.query("integrityViolation", None, None), [])
        self.assertEqual(self.r.query("disjointnessViolation", None, None), [])

    def test_new_product_is_classified(self):
        ctx = competency.EngineContext(self.kb, self.r, self.prover, self.rules)
        rows = {row["aspect"]: row["result"] for row in competency.cq12(ctx)["rows"]}
        self.assertIn("NonVeganProduct", rows["inferred classes"])
        self.assertIn("Vegan -> CONTRADICTED", rows["claim audit"])


if __name__ == "__main__":
    unittest.main()
