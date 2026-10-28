"""
Edge-case experiments (engine side). The OWL side of EC2-EC4 lives in
owl_reasoning.py because it needs owlready2 and Java.

EC1  Incomplete information: open world vs naive closed world vs local closed world
EC2  Closure axioms (OWL only; engine counterpart = VerifiedVeganProduct)
EC3  Conflicting data: a false claim is flagged without making everything inconsistent
EC4  A data-entry error (honey typed as plant-derived) is isolated, not explosive
EC5  Ambiguous sources (lecithin, E471, 'natural flavouring')
EC6  Defeasible exemption and threshold rules vs monotonic SWRL duties
EC7  Numeric boundary: exactly 10 mg/kg sulphites
EC8  Lexical traps: naive keyword screening vs ontology-based reasoning
"""
from __future__ import annotations

from typing import Dict, List

from .competency import MARKETS, EngineContext
from .engine_bridge import run_engine

MONOTONIC_DUTY = {"jur_us": "mustDeclareInUS", "jur_canada": "mustDeclareInCanada", "jur_eu": "mustDeclareInEU"}
NAIVE_ALLERGENS = ["alg_milk", "alg_egg", "alg_fish", "alg_crustacean", "alg_mollusc", "alg_tree_nuts", "alg_peanut",
                   "alg_soy", "alg_sesame", "alg_mustard", "alg_celery", "alg_lupin", "alg_sulphites", "alg_wheat"]


def ec1_open_vs_closed_world(ctx: EngineContext) -> dict:
    kb, res = ctx.kb, ctx.result
    products, consumers = list(kb.products), list(kb.consumers)
    lcwa_safe = set(res.query("confirmedSafeFor", None, None))
    naive_safe = {(p, u) for p in products for u in consumers
                  if not res.holds("unsafeFor", p, u) and not res.holds("cautionFor", p, u)}
    lcwa_vegan = {p for (p,) in res.query("VerifiedVeganProduct", None)}
    naive_vegan = {p for p in products if not res.holds("NonVeganProduct", p)}
    false_safe = sorted(naive_safe - lcwa_safe)
    false_vegan = sorted(naive_vegan - lcwa_vegan)

    def reason(p):
        if kb.products[p]["status"] != "complete":
            return "ingredient record incomplete"
        if res.holds("OriginUncertainProduct", p):
            return "ingredient of unstated origin"
        return "possible allergen source not resolved"

    details: Dict[str, dict] = {}
    for p, u in false_safe:
        entry = details.setdefault(p, {"product": kb.label(p), "falsely 'safe' for": 0, "falsely 'vegan'": "", "reason": reason(p)})
        entry["falsely 'safe' for"] += 1
    for p in false_vegan:
        entry = details.setdefault(p, {"product": kb.label(p), "falsely 'safe' for": 0, "falsely 'vegan'": "", "reason": reason(p)})
        entry["falsely 'vegan'"] = "yes"
    rows = [
        {"assumption": "Open world (OWL, Pellet, no closure axioms)", "product-consumer pairs confirmed safe": 0,
         "products confirmed vegan": 0, "false assurances": 0,
         "comment": "Sound but silent: absence of information never becomes a conclusion."},
        {"assumption": "Naive closed world (absence of evidence = safe)", "product-consumer pairs confirmed safe": len(naive_safe),
         "products confirmed vegan": len(naive_vegan), "false assurances": len(false_safe) + len(false_vegan),
         "comment": "Answers everything, including questions the data cannot support."},
        {"assumption": "Local closed world (FALCON: only complete records)", "product-consumer pairs confirmed safe": len(lcwa_safe),
         "products confirmed vegan": len(lcwa_vegan), "false assurances": 0,
         "comment": "Closes the world only where the record is known to be complete."},
    ]
    return dict(columns=list(rows[0]), rows=rows, false_assurances=list(details.values()))


def ec3_conflicts_without_explosion(ctx: EngineContext) -> dict:
    res = ctx.result
    contradictions = res.query("contradictsClaim", None, None)
    return dict(
        contradictions=len(contradictions),
        derived_facts_still_available=len(res.derived),
        unsafe_verdicts_still_available=len(res.query("unsafeFor", None, None)),
        note="Claims are modelled as data, so a false claim produces a contradictsClaim fact. In strict OWL mode the "
             "same claims are axioms and one false claim makes the whole ontology inconsistent (see the OWL results).")


def ec4_data_error_is_isolated(ctx: EngineContext) -> dict:
    broken = ctx.kb.copy()
    broken.ingredients["ing_honey"]["classes"].append("PlantDerivedIngredient")
    _, res = run_engine(broken, rules=ctx.rules)
    violations = [{"entity": broken.label(x), "violated axiom": why} for (x, why) in res.query("disjointnessViolation", None, None)]
    return dict(
        injected_error="ing_honey typed as both BeeProduct (animal-derived) and PlantDerivedIngredient",
        violations=violations,
        unsafe_verdicts_before=len(ctx.result.query("unsafeFor", None, None)),
        unsafe_verdicts_after=len(res.query("unsafeFor", None, None)),
        note="The engine reports the violation and keeps every unrelated conclusion. OWL is classical: an inconsistent "
             "ontology entails everything, so the reasoner refuses to answer anything until the error is fixed.")


def ec5_ambiguous_sources(ctx: EngineContext) -> dict:
    rows = []
    for (p,) in ctx.q("OriginUncertainProduct", None):
        unclear = [ctx.lab(i) for (_, i) in ctx.q("hasIngredient", p, None) if ctx.holds("UnspecifiedOriginIngredient", i)]
        rows.append({
            "product": ctx.lab(p),
            "unclear ingredients": ", ".join(unclear),
            "diet uncertain for": ", ".join(ctx.lab(u) for (_, u) in ctx.q("dietUncertainFor", p, None)) or "",
            "allergen uncertain for": ", ".join(ctx.lab(u) for (_, u) in ctx.q("uncertainFor", p, None)) or "",
            "supplier checks": ", ".join(sorted({ctx.lab(a) for (_, a, _) in ctx.q("needsSupplierCheck", p, None, None)})) or "",
        })
    return dict(columns=list(rows[0]) if rows else [], rows=rows)


def ec6_defeasible_vs_monotonic(ctx: EngineContext) -> dict:
    rows = []
    for product in ctx.kb.products:
        for market, name in MARKETS:
            monotonic = {a for (_, a) in ctx.q(MONOTONIC_DUTY[market], product, None)}
            refined = {a for (_, a, _) in ctx.q("declarationDuty", product, None, market)}
            for allergen in sorted(monotonic ^ refined):
                if allergen in monotonic:
                    why = "exempt under " + "; ".join(
                        e["basis"] for e in ctx.kb.exemptions.values()
                        if e["allergen"] == allergen and e["jurisdiction"] == market)
                else:
                    why = "numeric threshold rule (sulphites)"
                rows.append({"product": ctx.lab(product), "market": name, "allergen": ctx.lab(allergen),
                             "monotonic SWRL duty": "yes" if allergen in monotonic else "no",
                             "defeasible engine duty": "yes" if allergen in refined else "no", "why they differ": why})
    return dict(columns=list(rows[0]) if rows else [], rows=rows,
                note="SWRL cannot retract a conclusion when an exception applies; the engine's 'not exemptFromDeclaration' can.")


def ec7_numeric_boundary(ctx: EngineContext) -> dict:
    rows = []
    for product, p in ctx.kb.products.items():
        value = p.get("sulphite_mg_per_kg")
        if value is None:
            continue
        row = {"product": ctx.lab(product), "sulphites (mg/kg)": value,
               ">= 10 (US/Canada)": "yes" if ctx.holds("SulphiteAtOrAbove10ppm", product) else "no",
               "> 10 (EU)": "yes" if ctx.holds("SulphiteAbove10ppm", product) else "no"}
        for market, name in MARKETS:
            if market in p["sold_in"]:
                duty = ctx.holds("declarationDuty", product, "alg_sulphites", market)
                undeclared = ctx.holds("undeclaredAllergen", product, "alg_sulphites", market)
                row[name] = ("must declare" if duty else "not required") + (" (UNDECLARED)" if undeclared else "")
            else:
                row[name] = "not sold"
        rows.append(row)
    return dict(columns=list(rows[0]) if rows else [], rows=rows)


def naive_keyword_detection(kb, product_id: str) -> Dict[str, List[str]]:
    """What a simple substring screener finds: allergen -> ingredient labels that matched."""
    found: Dict[str, List[str]] = {}
    for ingredient in kb.products[product_id]["ingredients"]:
        text = kb.ingredients[ingredient]["label"].lower()
        for allergen in NAIVE_ALLERGENS:
            if any(keyword in text for keyword in kb.allergens[allergen]["keywords"]):
                found.setdefault(allergen, []).append(kb.ingredients[ingredient]["label"])
    return found


def ec8_lexical_traps(ctx: EngineContext) -> dict:
    kb = ctx.kb
    tp = fp = fn = 0
    false_pos, false_neg = [], []
    for product in kb.products:
        naive = naive_keyword_detection(kb, product)
        reference = {a for a in NAIVE_ALLERGENS if ctx.holds("containsAllergen", product, a)}
        for allergen in set(naive) | reference:
            if allergen in naive and allergen in reference:
                tp += 1
            elif allergen in naive:
                fp += 1
                false_pos.append({"product": kb.label(product), "flagged as": kb.label(allergen),
                                  "triggered by": ", ".join(naive[allergen])})
            else:
                fn += 1
                sources = [kb.label(i) for (_, _, i) in ctx.q("containsVia", product, allergen, None)]
                false_neg.append({"product": kb.label(product), "missed": kb.label(allergen), "hidden in": ", ".join(sources)})
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return dict(true_positives=tp, false_positives=fp, false_negatives=fn,
                precision=round(precision, 3), recall=round(recall, 3), f1=round(f1, 3),
                false_positive_examples=false_pos, false_negative_examples=false_neg,
                note="Reference = the ontology's containsAllergen conclusions over 14 regulated allergen groups. "
                     "The naive screener matches allergen keywords as substrings of printed ingredient names.")


def run_all(ctx: EngineContext) -> Dict[str, dict]:
    return {
        "EC1": dict(title="Incomplete information: open, naive closed and local closed world", **ec1_open_vs_closed_world(ctx)),
        "EC3": dict(title="Conflicting data handled without explosion", **ec3_conflicts_without_explosion(ctx)),
        "EC4": dict(title="Data-entry error isolated by integrity rules", **ec4_data_error_is_isolated(ctx)),
        "EC5": dict(title="Ingredients of unstated origin", **ec5_ambiguous_sources(ctx)),
        "EC6": dict(title="Defeasible exemption and thresholds vs monotonic SWRL", **ec6_defeasible_vs_monotonic(ctx)),
        "EC7": dict(title="Numeric boundary at exactly 10 mg/kg sulphites", **ec7_numeric_boundary(ctx)),
        "EC8": dict(title="Lexical traps: keyword screening vs ontology", **ec8_lexical_traps(ctx)),
    }
