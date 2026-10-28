"""
Collect every number the report quotes into report/report_data.json.

    python report/prepare_data.py && node report/build_report.js portfolio docs/FALCON_Technical_Report.docx

Numbers come from the live rule engine and from outputs/ (written by run_all.py
and falcon.benchmark), so the report cannot drift from the system it describes.
"""
import json
import statistics
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from falcon import competency, edge_cases, rules_catalog, schema  # noqa: E402
from falcon.config import OUTPUT_DIR  # noqa: E402
from falcon.engine_bridge import build_rules, make_prover, run_engine  # noqa: E402
from falcon.kb_loader import load_kb  # noqa: E402


def load(name):
    path = OUTPUT_DIR / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def headline(cq_id, a):
    rows = a["rows"]
    if cq_id in ("CQ01", "CQ03", "CQ08", "CQ13"):
        return a["note"]
    if cq_id == "CQ02":
        return "; ".join("%s via %s%s" % (r["allergen"], r["via ingredient"], " (hidden)" if r["hidden from shoppers"] else "")
                         for r in rows)
    if cq_id == "CQ04":
        return "; ".join("%s: %s claim vs. 'may contain %s'" % (r["product"], r["claim"], r["'may contain'"].lower()) for r in rows)
    if cq_id == "CQ05":
        c = Counter(r["status"] for r in rows)
        return "%d unsafe, %d caution, %d uncertain" % (c["UNSAFE"], c["CAUTION"], c["UNCERTAIN"])
    if cq_id == "CQ06":
        return "%d products confirmed safe; Dark Chocolate 70%% blocked by its hazelnut warning" % len(rows)
    if cq_id == "CQ07":
        n = sum(1 for r in rows if r["inferred classes"] != "(none)")
        return "%d of %d products placed in at least one defined class" % (n, len(rows))
    if cq_id == "CQ09":
        return "%d hidden allergens in %d products (e.g., caseinate, tahini, surimi)" % (len(rows), len({r["product"] for r in rows}))
    if cq_id == "CQ10":
        return "%d incomplete records; neither can be confirmed safe for any consumer" % len(rows)
    if cq_id == "CQ11":
        c = Counter(r["verdict"] for r in rows)
        return "%d claims: %s" % (len(rows), ", ".join("%d %s" % (v, k.lower()) for k, v in c.most_common()))
    if cq_id == "CQ12":
        d = {r["aspect"]: r["result"] for r in rows}
        return "NonVeganProduct; vegan claim contradicted; wheat undeclared (%s)" % d["undeclared allergens"].replace("Wheat ", "")
    if cq_id == "CQ14":
        return ", ".join("%d %s" % (v, k.lower()) for k, v in sorted(a["counts"].items(), key=lambda kv: -kv[1]))
    return ""


def main():
    kb = load_kb()
    rules = build_rules(kb)
    _, res = run_engine(kb, rules=rules)
    ctx = competency.EngineContext(kb, res, make_prover(kb, rules), rules)
    answers = competency.answer_all(ctx)
    ec = edge_cases.run_all(ctx)
    insights = load("insights.json") or {}
    bench = load("benchmark.json") or {}
    owl = load("owl_results.json") or {}
    proofs = load("proofs.json") or {"proofs": []}
    saved_cases = load("edge_cases.json") or {}
    by_id = {r.rule_id: r for r in rules}
    by_source = Counter(r.source for r in rules)
    tests = unittest.TestLoader().discover(str(ROOT / "tests"), top_level_dir=str(ROOT)).countTestCases()
    false_safe = sum(x["falsely 'safe' for"] for x in ec["EC1"]["false_assurances"])
    false_vegan = sum(1 for x in ec["EC1"]["false_assurances"] if x["falsely 'vegan'"])
    cats = sum(1 for a in kb.allergens.values() if a["kind"] == "category")
    product_classes = sum(1 for a in kb.allergens.values() if a.get("product_class"))

    earlier_file = ROOT / "report" / "colab_runs" / "run1_benchmark_uncapped.json"
    earlier_owl = json.loads(earlier_file.read_text(encoding="utf-8")).get("owl", []) if earlier_file.exists() else []
    data = {
        "kb": kb.summary(),
        "allergen_categories": cats, "allergen_specific": len(kb.allergens) - cats,
        "classes_named": len(schema.CLASSES), "classes_defined": len(schema.DEFINED_CLASSES) + product_classes,
        "object_properties": len(schema.OBJECT_PROPERTIES), "data_properties": len(schema.DATA_PROPERTIES),
        "annotation_properties": len(schema.ANNOTATION_PROPERTIES),
        "transitive": sum(1 for s in schema.OBJECT_PROPERTIES.values() if "transitive" in s.get("characteristics", [])),
        "subproperties": sum(1 for s in schema.OBJECT_PROPERTIES.values() if s.get("parent")),
        "chains": len(schema.PROPERTY_CHAINS), "gcis": len(schema.GCIS),
        "restrictions": len(schema.RESTRICTIONS) + len(schema.HAS_VALUE_AXIOMS), "disjoint": len(schema.DISJOINT_GROUPS),
        "individuals": sum(len(t) for t in (kb.products, kb.ingredients, kb.allergens, kb.jurisdictions, kb.claims,
                                            kb.categories, kb.consumers, kb.exemptions)),
        "swrl": len(rules_catalog.SWRL_RULES), "swrl_no_builtins": sum(1 for r in rules_catalog.SWRL_RULES if not r.get("builtins")),
        "engine_rules": len(rules_catalog.ENGINE_RULES), "integrity_rules": by_source["integrity"],
        "tbox_rules": by_source["tbox"] + by_source["tbox-typing"], "rules_total": len(rules),
        "engine": res.summary(), "tests": tests, "n_cq": len(answers),
        "insights": insights,
        "ec1": {"naive_safe": ec["EC1"]["rows"][1]["product-consumer pairs confirmed safe"],
                "lcwa_safe": ec["EC1"]["rows"][2]["product-consumer pairs confirmed safe"],
                "naive_vegan": ec["EC1"]["rows"][1]["products confirmed vegan"],
                "lcwa_vegan": ec["EC1"]["rows"][2]["products confirmed vegan"],
                "false_safe": false_safe, "false_vegan": false_vegan},
        "ec4_unsafe": ec["EC4"]["unsafe_verdicts_after"],
        "ec8": {k: ec["EC8"][k] for k in ("precision", "recall", "f1", "true_positives", "false_positives", "false_negatives")},
        "showcase": len(proofs["proofs"]),
        "backward_ms": round(statistics.mean(p["backward_ms"] for p in proofs["proofs"]), 2) if proofs["proofs"] else None,
        "cq_table": [{"id": k, "question": a["question"], "kind": a["kind"], "answer": headline(k, a)} for k, a in answers.items()],
        "rule_table": [{"id": i, "name": by_id[i].name, "fol": by_id[i].to_fol()}
                       for i in ("R01", "R02", "R03", "R07", "R13", "R14", "R17", "E04", "E08", "E10", "E13", "E21")],
        "swrl_table": [{"id": r["id"], "name": r["name"], "fol": by_id[r["id"]].to_fol()} for r in rules_catalog.SWRL_RULES],
        "bench": bench,
        "owl": {"status": owl.get("status", "not run"), "pellet": owl.get("pellet"), "hermit": owl.get("hermit"),
                "facts_inferred": owl.get("facts_inferred", owl.get("facts_inferred_by_pellet")),
                "triples": owl.get("triples_asserted"), "materializer": owl.get("materializer"),
                "crossval_predicates": len(owl.get("crossval", [])),
                "crossval_agree": sum(r["agree"] for r in owl.get("crossval", [])),
                "crossval_total": sum(r["agree"] + len(r["only_engine"]) + len(r.get("only_owl", r.get("only_pellet", []))) for r in owl.get("crossval", [])),
                "ec2": saved_cases.get("EC2"), "ec3": saved_cases.get("EC3_owl"), "ec4": saved_cases.get("EC4_owl"),
                "cq12": owl.get("cq12_owl")},
        "owl_timeout_s": bench.get("owl_timeout_s") or 150,
        "bench_earlier": [r for r in earlier_owl if r.get("status") == "consistent"],
    }
    out = ROOT / "report" / "report_data.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", out.relative_to(ROOT), "| OWL results:", data["owl"]["status"], "| tests:", tests)


if __name__ == "__main__":
    main()
