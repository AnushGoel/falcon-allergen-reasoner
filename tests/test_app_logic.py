"""Tests for the app logic: label parsing, live analysis and the Myth-or-Fact game."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from falcon import app_logic as logic  # noqa: E402


class AppLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb, cls.rules, cls.ctx = logic.load_engine()
        cls.lexicon = logic.build_lexicon(cls.kb)

    def test_parser_avoids_lexical_traps(self):
        parsed = logic.parse_label(self.kb, "Cocoa butter, coconut milk, eggplant, cream of tartar, peanut butter", self.lexicon)
        self.assertEqual(parsed["ingredients"], ["ing_cocoa_butter", "ing_coconut_milk", "ing_eggplant",
                                                 "ing_cream_of_tartar", "ing_peanut_butter"])
        self.assertEqual(parsed["unknown"], [])

    def test_parser_reads_may_contain_and_unknowns(self):
        parsed = logic.parse_label(self.kb, "Ingredients: rice flour, unicorn dust. May contain: hazelnuts.", self.lexicon)
        self.assertIn("ing_rice_flour", parsed["ingredients"])
        self.assertEqual(parsed["unknown"], ["unicorn dust"])
        self.assertEqual(parsed["may_contain"], ["alg_hazelnut"])

    def test_live_analysis_finds_hidden_fish(self):
        parsed = logic.parse_label(self.kb, "Tomato, spirit vinegar, sugar, Worcestershire sauce, onion, salt", self.lexicon)
        ctx = logic.analyse_label(self.kb, self.rules, "Test sauce", parsed["ingredients"], ["claim_vegan"], ["jur_us"])
        summary = logic.summarise(ctx, logic.CUSTOM_ID)
        fish = [a for a in summary["allergens"] if a["id"] == "alg_fish"][0]
        self.assertTrue(fish["hidden"])
        self.assertEqual(summary["claims"][0]["status"], "CONTRADICTED")
        self.assertIn("Fish", summary["markets"][0]["undeclared"])

    def test_every_myth_is_decided_by_reasoning(self):
        expected_facts = {"tahini", "darkchoc", "coleslaw"}
        for myth in logic.MYTHS:
            verdict = logic.check_myth(self.ctx, myth)
            self.assertEqual(verdict["is_fact"], myth["key"] in expected_facts, myth["key"])
            self.assertTrue(verdict["proof"] is not None or verdict["why_not"], myth["key"])

    def test_plain_english_explanation(self):
        proof = self.ctx.prover.prove(logic.MYTHS[0]["goal"])
        plain = logic.explain_plain(self.kb, proof)
        self.assertIn("unsafe for", plain["conclusion"])
        self.assertTrue(any("must avoid" in f for f in plain["facts"]))

    def test_chart_data(self):
        sankey = logic.sankey_data(self.ctx)
        self.assertEqual(len(sankey["source"]), len(sankey["value"]))
        self.assertIn("market", sankey["kinds"])
        products, consumers, statuses = logic.consumer_matrix(self.ctx)
        self.assertEqual((len(consumers), len(products)), (len(statuses), len(statuses[0])))


if __name__ == "__main__":
    unittest.main()
