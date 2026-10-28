"""
Bridge between the knowledge base and the FALCON rule engine.

* ``tbox_rules`` translates the Horn-expressible part of the schema
  (subclasses, sub-properties, inverses, transitivity, property chains,
  domain/range typing, defined-class sufficient conditions, GCIs and
  hasValue axioms) into rules. This is essentially the OWL 2 RL treatment
  of our axioms.
* ``catalog_rules`` parses the shared SWRL rules plus the engine-only rules.
* ``kb_facts`` turns the JSON knowledge base into ground facts.
"""
from __future__ import annotations

import re
from typing import Iterable, List, Optional, Sequence, Tuple

from . import rules_catalog, schema
from .kb_loader import KnowledgeBase
from .rule_engine import (BackwardChainer, FactStore, ForwardChainer, ForwardResult, Rule, parse_rule)

Fact = Tuple[str, Tuple]


def tbox_rules(kb: Optional[KnowledgeBase] = None) -> List[Rule]:
    rules: List[Rule] = []
    add = rules.append
    for name, parents, _ in schema.CLASSES:
        for parent in parents:
            add(parse_rule("%s(?x) -> %s(?x)" % (name, parent), "T-SC-%s-%s" % (name, parent),
                           "%s \u2291 %s" % (name, parent), "tbox"))
    for d in schema.DEFINED_CLASSES:
        for parent in d["parents"]:
            add(parse_rule("%s(?x) -> %s(?x)" % (d["name"], parent), "T-SC-%s-%s" % (d["name"], parent),
                           "%s \u2291 %s" % (d["name"], parent), "tbox"))
        for k, text in enumerate(d["horn"], 1):
            add(parse_rule(text, "T-DEF-%s-%d" % (d["name"], k), "Definition of %s (case %d)" % (d["name"], k), "tbox"))
    for k, g in enumerate(schema.GCIS, 1):
        add(parse_rule(g["horn"], "T-GCI-%d" % k, "General axiom: ... \u2291 %s" % g["right"], "tbox"))
    for k, h in enumerate(schema.HAS_VALUE_AXIOMS, 1):
        add(parse_rule(h["horn"], "T-HV-%d" % k, "%s \u2291 %s value %s" % (h["cls"], h["prop"], h["value"]), "tbox"))
    for name, spec in schema.OBJECT_PROPERTIES.items():
        if "transitive" in spec.get("characteristics", []):
            add(parse_rule("%s(?x, ?y), %s(?y, ?z) -> %s(?x, ?z)" % (name, name, name),
                           "T-TR-%s" % name, "%s is transitive" % name, "tbox"))
        if spec.get("parent"):
            add(parse_rule("%s(?x, ?y) -> %s(?x, ?y)" % (name, spec["parent"]),
                           "T-SP-%s" % name, "%s \u2291 %s" % (name, spec["parent"]), "tbox"))
        if spec.get("inverse"):
            inverse = spec["inverse"]
            add(parse_rule("%s(?x, ?y) -> %s(?y, ?x)" % (inverse, name), "T-INV-%s" % name,
                           "%s is the inverse of %s" % (name, inverse), "tbox"))
            add(parse_rule("%s(?x, ?y) -> %s(?y, ?x)" % (name, inverse), "T-INV-%s" % inverse,
                           "%s is the inverse of %s" % (inverse, name), "tbox"))
        for cls in spec.get("domain", []):
            add(parse_rule("%s(?x, ?y) -> %s(?x)" % (name, cls), "T-DOM-%s" % name,
                           "domain(%s) = %s" % (name, cls), "tbox-typing"))
        for cls in spec.get("range", []):
            add(parse_rule("%s(?x, ?y) -> %s(?y)" % (name, cls), "T-RNG-%s" % name,
                           "range(%s) = %s" % (name, cls), "tbox-typing"))
    for name, spec in schema.DATA_PROPERTIES.items():
        for cls in spec.get("domain", []):
            add(parse_rule("%s(?x, ?v) -> %s(?x)" % (name, cls), "T-DOM-%s" % name,
                           "domain(%s) = %s" % (name, cls), "tbox-typing"))
    for k, chain in enumerate(schema.PROPERTY_CHAINS, 1):
        p1, p2 = chain["chain"]
        add(parse_rule("%s(?x, ?y), %s(?y, ?z) -> %s(?x, ?z)" % (p1, p2, chain["super"]), "T-CH-%d" % k,
                       "%s \u2218 %s \u2291 %s" % (p1, p2, chain["super"]), "tbox"))
    if kb is not None:
        for a in kb.allergens.values():
            cls = a.get("product_class")
            if cls:
                add(parse_rule("Product(?p), containsAllergen(?p, %s) -> %s(?p)" % (a["id"], cls),
                               "T-DEF-%s" % cls, "%s \u2261 Product \u2293 containsAllergen value %s" % (cls, a["id"]), "tbox"))
                add(parse_rule("%s(?x) -> Product(?x)" % cls, "T-SC-%s-Product" % cls, "%s \u2291 Product" % cls, "tbox"))
    return rules


def catalog_rules(include_swrl: bool = True, include_engine: bool = True, include_integrity: bool = True) -> List[Rule]:
    rules: List[Rule] = []
    if include_swrl:
        for r in rules_catalog.SWRL_RULES:
            rules.append(parse_rule(r["swrl"], r["id"], r["name"], "swrl", r.get("rationale", "")))
    if include_engine:
        for r in rules_catalog.ENGINE_RULES:
            rules.append(parse_rule(r["text"], r["id"], r["name"], "engine", r.get("rationale", "")))
    if include_integrity:
        for r in rules_catalog.INTEGRITY_RULES:
            rules.append(parse_rule(r["text"], r["id"], r["name"], "integrity"))
        for k, (a, b) in enumerate(schema.ENGINE_DISJOINTNESS_CHECKS, 1):
            rules.append(parse_rule('%s(?x), %s(?x) -> disjointnessViolation(?x, "%s / %s")' % (a, b, a, b),
                                    "I-DJ-%d" % k, "%s and %s are disjoint" % (a, b), "integrity"))
    return rules


def build_rules(kb: KnowledgeBase, **kwargs) -> List[Rule]:
    return tbox_rules(kb) + catalog_rules(**kwargs)


def _mentions(text: str, keywords: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(k.lower()), lowered) for k in keywords)


def lexical_facts(kb: KnowledgeBase) -> List[Fact]:
    """mentionsAllergen(i, a): the ingredient's printed name already reveals the allergen."""
    facts = []
    for ingredient in kb.ingredients.values():
        for allergen in kb.allergens.values():
            if _mentions(ingredient["label"], allergen.get("keywords", [])):
                facts.append(("mentionsAllergen", (ingredient["id"], allergen["id"])))
    return facts


def kb_facts(kb: KnowledgeBase) -> List[Fact]:
    facts: List[Fact] = []

    def add(pred, *args):
        facts.append((pred, tuple(args)))

    for a in kb.allergens.values():
        add("AllergenCategory" if a["kind"] == "category" else "SpecificAllergen", a["id"])
        if a.get("parent"):
            add("isSubtypeOf", a["id"], a["parent"])
    for j in kb.jurisdictions.values():
        add(j["class"], j["id"])
        for a in j["requires_declaration_of"]:
            add("requiresDeclarationOf", j["id"], a)
    for c in kb.claims.values():
        add(c["class"], c["id"])
        for a in c["excludes"]:
            add("excludesAllergen", c["id"], a)
    for c in kb.categories.values():
        add("ProductCategory", c["id"])
    for u in kb.consumers.values():
        for cls in u["classes"]:
            add(cls, u["id"])
        for a in u["must_avoid"]:
            add("mustAvoid", u["id"], a)
    for e in kb.exemptions.values():
        add("DeclarationExemption", e["id"])
        add("exemptIngredient", e["id"], e["ingredient"])
        add("exemptAllergen", e["id"], e["allergen"])
        add("exemptJurisdiction", e["id"], e["jurisdiction"])
        add("exemptFromDeclaration", e["ingredient"], e["allergen"], e["jurisdiction"])
    for i in kb.ingredients.values():
        for cls in i["classes"]:
            add(cls, i["id"])
        for x in i["retains"]:
            add("retainsAllergensOf", i["id"], x)
        for x in i["derived_from"]:
            add("derivedFrom", i["id"], x)
        for x in i["components"]:
            add("hasComponent", i["id"], x)
        for a in i["triggers"]:
            add("triggersAllergen", i["id"], a)
            add("assertedTrigger", i["id"], a)
        for a in i["possibly_triggers"]:
            add("possiblyTriggers", i["id"], a)
    for p in kb.products.values():
        add("Product", p["id"])
        add("hasBarcode", p["id"], p["barcode"])
        add("hasIngredientListStatus", p["id"], p["status"])
        if p.get("category"):
            add("inCategory", p["id"], p["category"])
        for x in p["ingredients"]:
            add("hasIngredient", p["id"], x)
        for x in p["claims"]:
            add("hasLabelClaim", p["id"], x)
        for x in p["may_contain"]:
            add("mayContain", p["id"], x)
        for x in p["declared"]:
            add("declaresAllergen", p["id"], x)
        for x in p["sold_in"]:
            add("soldIn", p["id"], x)
        if p.get("gluten_ppm") is not None:
            add("hasGlutenPPM", p["id"], float(p["gluten_ppm"]))
        if p.get("sulphite_mg_per_kg") is not None:
            add("hasSulphiteMgPerKg", p["id"], float(p["sulphite_mg_per_kg"]))
    facts.extend(lexical_facts(kb))
    return facts


def run_engine(kb: KnowledgeBase, rules: Optional[Sequence[Rule]] = None, extra_facts: Iterable[Fact] = ()):
    rules = list(rules) if rules is not None else build_rules(kb)
    chainer = ForwardChainer(rules)
    result = chainer.run(list(kb_facts(kb)) + list(extra_facts))
    return chainer, result


def make_prover(kb: KnowledgeBase, rules: Sequence[Rule]) -> BackwardChainer:
    return BackwardChainer(rules, FactStore(kb_facts(kb)))
