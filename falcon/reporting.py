"""Writers for JSON, CSV, Markdown and plain-text outputs, plus console helpers."""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, List, Optional

TRACE_PREDICATES = {"triggersAllergen", "NonVeganIngredient", "NonVegetarianIngredient", "AnimalDerivedIngredient",
                    "VeganSafeIngredient", "hasNonVeganSafeComponent", "GlutenSourceIngredient"}


def console_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


class Console:
    def banner(self, title: str) -> None:
        print("=" * 78)
        print(title)
        print("=" * 78)

    def step(self, title: str, data=None) -> None:
        print("\n[%s]" % title)
        if isinstance(data, dict):
            for key, value in data.items():
                print("   %-30s %s" % (key, value))
        elif data is not None:
            print("   %s" % data)

    def warn(self, message: str) -> None:
        print("\n[WARNING] %s" % message)


def _default(obj):
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    return str(obj)


def write_json(path, obj) -> None:
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=_default), encoding="utf-8")


def write_text(path, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def write_csv(path, rows: List[dict], columns: Optional[List[str]] = None) -> None:
    columns = columns or (list(rows[0]) if rows else [])
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def md_table(columns: List[str], rows: List[dict], limit: Optional[int] = None) -> str:
    if not rows:
        return "_(no rows)_\n"

    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    for row in (rows[:limit] if limit else rows):
        lines.append("| " + " | ".join(cell(row.get(c, "")) for c in columns) + " |")
    return "\n".join(lines) + "\n"


def cq_markdown(answers: dict) -> str:
    parts = ["# FALCON competency questions\n"]
    for cq_id, answer in answers.items():
        parts.append("## %s. %s\n" % (cq_id, answer["question"]))
        parts.append("*Type:* %s\n" % answer["kind"])
        if answer.get("note"):
            parts.append("> %s\n" % answer["note"])
        parts.append(md_table(answer["columns"], answer["rows"]))
        if answer.get("counts"):
            parts.append("Counts: " + ", ".join("%s = %d" % kv for kv in sorted(answer["counts"].items())) + "\n")
        if answer.get("proof"):
            parts.append("```\n%s\n```\n" % answer["proof"])
        for product, reasons in (answer.get("why_not") or {}).items():
            parts.append("**Why is '%s' not confirmed safe?**\n\n```\n%s\n```\n" % (product, "\n".join(reasons)))
        if answer.get("sparql"):
            parts.append("SPARQL over the Pellet-materialised ontology:\n\n```sparql\n%s\n```\n" % answer["sparql"])
    return "\n".join(parts)


def rules_markdown(rules) -> str:
    lines = ["# FALCON rule catalogue", "", "Generated from the rule objects used at run time.", ""]
    groups = [("SWRL production rules (run by Pellet and by the FALCON engine)", "swrl"),
              ("Engine-only rules (negation as failure, n-ary, defeasible)", "engine"),
              ("Integrity constraints", "integrity")]
    for title, source in groups:
        lines += ["## %s" % title, "", "| ID | Name | First-order form |", "|---|---|---|"]
        lines += ["| %s | %s | %s |" % (r.rule_id, r.name, r.to_fol().replace("|", "\\|")) for r in rules if r.source == source]
        lines.append("")
    tbox = [r for r in rules if r.source in ("tbox", "tbox-typing")]
    lines += ["## Horn translation of the OWL axioms (%d rules)" % len(tbox), "", "| ID | Axiom | Rule |", "|---|---|---|"]
    lines += ["| %s | %s | %s |" % (r.rule_id, r.name, r.text) for r in tbox]
    return "\n".join(lines) + "\n"


def _split_fact(text: str):
    pred, _, rest = text.partition("(")
    return pred, [a.strip() for a in rest.rstrip(")").split(",")]


def focus_trace(result, kb, product: str) -> str:
    """Forward-chaining narrative restricted to one product and the ingredients inside it."""
    ingredients = set(kb.products[product]["ingredients"])
    ingredients |= {c for i in list(ingredients) for c in kb.ingredients[i]["components"]}
    body = []
    for event in result.trace:
        pred, args = _split_fact(event["fact"])
        if product in args or (args and args[0] in ingredients and pred in TRACE_PREDICATES):
            body.append("step %5d | stratum %d | iteration %d | rule %s" % (event["step"], event["stratum"], event["iteration"], event["rule"]))
            body.append("    derived:  %s" % event["fact"])
            body += ["    because:  %s" % p for p in event["premises"]]
            body += ["    and not:  %s" % a for a in event["absent"]]
            body += ["    test:     %s" % c for c in event["checks"]]
    head = ["Forward-chaining trace for %s (%s)" % (kb.label(product), product),
            "%d derivation steps, in the order the engine produced them." % (len(body) and sum(1 for l in body if l.startswith("step"))), ""]
    return "\n".join(head + body) + "\n"


def insights(ctx, answers: dict, ec: dict) -> dict:
    """Headline domain findings used by the report and the Streamlit app."""
    kb, res = ctx.kb, ctx.result
    undeclared = res.query("undeclaredAllergen", None, None, None)
    allergen_counts = Counter(kb.label(a) for (_, a) in res.query("containsAllergen", None, None)
                              if kb.allergens[a]["kind"] == "category")
    consumers = {}
    for u in kb.consumers:
        consumers[kb.label(u)] = {
            "unsafe": len(res.query("unsafeFor", None, u)),
            "caution": len([p for (p, _) in res.query("cautionFor", None, u) if not res.holds("unsafeFor", p, u)]),
            "uncertain": len(res.query("uncertainFor", None, u)),
            "confirmed safe": len(res.query("confirmedSafeFor", None, u)),
            "unsuitable for diet": len(res.query("unsuitableForDietOf", None, u)),
        }
    hidden = res.query("hiddenAllergenVia", None, None, None)
    return {
        "claims_total": len(res.query("hasLabelClaim", None, None)),
        "claim_audit": answers["CQ14"]["counts"],
        "products_with_undeclared_allergen": len({p for (p, _, _) in undeclared}),
        "undeclared_by_market": dict(Counter(kb.label(j) for (_, _, j) in undeclared)),
        "undeclared_pairs": len(undeclared),
        "supplier_checks": len(res.query("needsSupplierCheck", None, None, None)),
        "hidden_allergen_findings": len(hidden),
        "products_with_hidden_allergen": len({p for (p, _, _) in hidden}),
        "market_disagreements": sum(1 for r in answers["CQ08"]["rows"] if r.get("markets disagree") == "yes"),
        "multi_market_products": len(res.query("MultiMarketProduct", None)),
        "naive_screening": {k: ec["EC8"][k] for k in ("precision", "recall", "f1", "false_positives", "false_negatives")},
        "naive_closed_world_false_assurances": ec["EC1"]["rows"][1]["false assurances"],
        "confirmed_safe_pairs": len(res.query("confirmedSafeFor", None, None)),
        "verified_vegan_products": len(res.query("VerifiedVeganProduct", None)),
        "allergen_prevalence": dict(allergen_counts.most_common()),
        "consumer_outcomes": consumers,
    }
