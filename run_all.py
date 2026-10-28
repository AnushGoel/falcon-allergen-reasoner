"""
FALCON: run the complete pipeline and write every artefact to ./outputs

    python run_all.py                 rule engine + OWL reasoning (needs owlready2 and Java)
    python run_all.py --engine-only   rule engine only (no Java needed)

"""
import argparse
import sys
import time
from pathlib import Path

from falcon import __version__, competency, edge_cases, reporting
from falcon.config import OUTPUT_DIR
from falcon.engine_bridge import build_rules, make_prover, run_engine
from falcon.kb_loader import load_kb
from falcon.rule_engine import Atom

SHOWCASE_PROOFS = [
    ("containsAllergen", ("prod_steakhouse_sauce", "alg_fish"), "Hidden fish two steps down a compound ingredient"),
    ("contradictsClaim", ("prod_steakhouse_sauce", "claim_vegan"), "Why the vegan claim on the steakhouse sauce is false"),
    ("undeclaredAllergen", ("prod_pesto_genovese", "alg_pine_nut", "jur_us"), "Pine nut must be declared in the US (not in the EU)"),
    ("unsafeFor", ("prod_gf_bread_codex", "cons_wei"), "A valid gluten-free loaf that is unsafe for a wheat allergy"),
    ("containsAllergen", ("prod_cooking_spray", "alg_soy"), "Soy comes from the lecithin, not the exempt refined oil"),
    ("hiddenAllergenVia", ("prod_aged_cheese_lysozyme", "alg_egg", "ing_lysozyme"), "Egg hidden in a cheese preservative"),
    ("confirmedSafeFor", ("prod_tamari", "cons_liam"), "A positive safety verdict needs negation as failure"),
    ("declarationDuty", ("prod_dried_apricots", "alg_sulphites", "jur_canada"), "Numeric threshold at exactly 10 ppm"),
]
WHY_NOT = [
    ("confirmedSafeFor", ("prod_dark_chocolate", "cons_maya")),
    ("VerifiedVeganProduct", ("prod_plant_protein_bar",)),
    ("declarationDuty", ("prod_wheat_glucose_candy", "alg_wheat", "jur_eu")),
    ("declarationDuty", ("prod_dried_apricots", "alg_sulphites", "jur_eu")),
]
FOCUS_PRODUCT = "prod_steakhouse_sauce"


def run_owl(kb, result, out, say, skip_hermit=False):
    from falcon import owl_reasoning as orz
    if not orz.available():
        say.warn("owlready2 is not installed, so OWL reasoning was skipped (pip install -r requirements.txt).")
        return {"status": "owlready2 not installed"}
    import owlready2
    from falcon.ontology_builder import build_ontology, save

    java = orz.configure_java()
    say.step("Java", {k: java.get(k) for k in ("java", "source", "version")})
    if not java["java"]:
        say.warn("Java was not found. Install Java 25 (see README) or set FALCON_JAVA to the full path of java.exe.")
        return {"status": "java not found", "java": java}
    results = {"status": "ok", "java": java, "owlready2_version": str(getattr(owlready2, "VERSION", "unknown"))}

    world = owlready2.World()
    started = time.perf_counter()
    onto, build = build_ontology(kb, world=world, swrl="all")
    results["build_seconds"] = round(time.perf_counter() - started, 3)
    results["build_report"] = build.to_dict()
    save(onto, out / "falcon.owl")
    results["triples_asserted"] = orz.triple_count(world)
    say.step("Ontology built", build.to_dict())

    materialised = {}       # reasoner -> (world, ontology, inferred ontology, facts before, SPARQL rows before)
    before = (orz.extract_facts(onto), orz.sparql_row_counts(world))
    pellet, inferred = orz.run_reasoner(world, onto, "pellet")
    results["pellet"] = pellet.to_dict()
    say.step("Pellet (OWL 2 DL + SWRL)", pellet.to_dict())
    if pellet.status == "consistent":
        materialised["pellet"] = (world, onto, inferred) + before
    if not skip_hermit:
        try:
            world_h = owlready2.World()
            onto_h, _ = build_ontology(kb, world=world_h, swrl="no-builtins")
            before_h = (orz.extract_facts(onto_h), orz.sparql_row_counts(world_h))
            hermit, inferred_h = orz.run_reasoner(world_h, onto_h, "hermit")
            results["hermit"] = hermit.to_dict()
            say.step("HermiT (OWL 2 DL + DL-safe SWRL)", hermit.to_dict())
            if hermit.status == "consistent":
                materialised["hermit"] = (world_h, onto_h, inferred_h) + before_h
        except Exception as exc:
            results["hermit"] = {"reasoner": "hermit", "status": "error", "seconds": 0.0,
                                 "message": "%s: %s" % (type(exc).__name__, exc)}

    # Materialised inferences come from Pellet. If Pellet cannot run, HermiT stands in; it has no SWRL
    # built-ins, so the threshold rules R14-R17 are missing from its side of the comparison.
    name = "pellet" if "pellet" in materialised else ("hermit" if "hermit" in materialised else None)
    results["materializer"] = name
    if name == "hermit":
        say.warn("Pellet could not run, so HermiT supplies the materialised inferences. " + pellet.message[:240])
    if name:
        w, o, inferred_o, facts_before, rows_before = materialised[name]
        after = orz.extract_facts(o)
        new = sorted(after - facts_before)
        results["facts_inferred"] = len(new)
        results["triples_after_reasoning"] = orz.triple_count(w)
        save(inferred_o, out / "falcon_inferred.owl")
        results["sparql_rows_before_after"] = orz.before_after_reasoning_counts(rows_before, orz.sparql_row_counts(w))
        results["sparql_answers"] = orz.sparql_answers(w, kb)
        results["crossval"] = orz.cross_validate(result, after, kb)
        reporting.write_csv(out / ("inferred_facts_%s.csv" % name),
                            [{"predicate": p, "subject": a[0], "object": a[1] if len(a) > 1 else ""} for p, a in new],
                            ["predicate", "subject", "object"])
        agree = sum(r["agree"] for r in results["crossval"])
        total = sum(r["agree"] + len(r["only_engine"]) + len(r["only_owl"]) for r in results["crossval"])
        say.step("Cross-validation (%s vs engine)" % name, {"predicates compared": len(results["crossval"]),
                                                            "facts agreeing": "%d of %d" % (agree, total)})

    reasoner = name or "pellet"
    owl_cases = {}
    for key, title, job in [
        ("EC2", "Closure axioms make vegan classification possible", lambda: orz.ec2_closure_axioms(kb, result, reasoner)),
        ("EC3_owl", "Claims as axioms: one false claim makes the ontology inconsistent", lambda: orz.ec3_strict_claims(kb, reasoner)),
        ("EC4_owl", "A data-entry error makes the ontology inconsistent", lambda: orz.ec4_disjointness_error(kb, reasoner)),
    ]:
        try:
            owl_cases[key] = dict(title=title, **job())
        except Exception as exc:
            owl_cases[key] = {"title": title, "error": "%s: %s" % (type(exc).__name__, exc)}
    try:
        results["cq12_owl"] = orz.cq12_classify_new_product(kb, reasoner)
    except Exception as exc:
        results["cq12_owl"] = {"error": "%s: %s" % (type(exc).__name__, exc)}
    results["edge_cases"] = owl_cases
    return results

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run the FALCON knowledge representation pipeline.")
    parser.add_argument("--engine-only", action="store_true", help="skip owlready2/Java reasoning")
    parser.add_argument("--skip-hermit", action="store_true", help="run Pellet only")
    parser.add_argument("--out", default=str(OUTPUT_DIR), help="output folder (default: ./outputs)")
    args = parser.parse_args(argv)

    reporting.console_utf8()
    say = reporting.Console()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    say.banner("FALCON %s - Food Allergen and Label Compliance Ontology" % __version__)

    kb = load_kb()
    if kb.errors:
        say.warn("Knowledge base has %d errors:\n  %s" % (len(kb.errors), "\n  ".join(kb.errors)))
        return 1
    say.step("Knowledge base", kb.summary())

    rules = build_rules(kb)
    _, result = run_engine(kb, rules=rules)
    prover = make_prover(kb, rules)
    ctx = competency.EngineContext(kb, result, prover, rules)
    say.step("Forward chaining (FALCON engine)", result.summary())

    proofs, text = [], []
    for pred, args_, title in SHOWCASE_PROOFS:
        atom = Atom(pred, args_)
        t0 = time.perf_counter()
        backward = prover.prove(atom)
        elapsed = (time.perf_counter() - t0) * 1000
        forward = result.explain(pred, *args_)
        proofs.append({"goal": str(atom), "title": title, "holds_forward": forward is not None,
                       "holds_backward": backward is not None, "backward_ms": round(elapsed, 2),
                       "proof_size": backward.size() if backward else 0, "proof_depth": backward.depth() if backward else 0,
                       "rules_used": sorted(set(backward.rules_used())) if backward else [],
                       "backward_proof": backward.to_dict() if backward else None})
        text += ["=" * 78, title, "Goal: %s" % atom, "-" * 78, "Backward chaining (goal-driven):",
                 backward.render() if backward else "  (no proof)", "", "Forward chaining (data-driven derivation):",
                 forward.render() if forward else "  (not derived)", ""]
    why_not = []
    for pred, args_ in WHY_NOT:
        atom = Atom(pred, args_)
        reasons = prover.why_not(atom)
        why_not.append({"goal": str(atom), "reasons": reasons})
        text += ["=" * 78, "WHY NOT  %s" % atom, "-" * 78] + reasons + [""]
    reporting.write_text(out / "reasoning_traces.txt", "\n".join(text))
    reporting.write_json(out / "proofs.json", {"proofs": proofs, "why_not": why_not})
    reporting.write_json(out / "forward_trace.json", {"summary": result.summary(), "events": result.trace})
    reporting.write_text(out / "forward_trace_focus.txt", reporting.focus_trace(result, kb, FOCUS_PRODUCT))
    agree = sum(1 for p in proofs if p["holds_forward"] == p["holds_backward"])
    say.step("Backward chaining", {"showcase goals proved": sum(p["holds_backward"] for p in proofs),
                                   "agreement with forward": "%d of %d" % (agree, len(proofs))})

    answers = competency.answer_all(ctx)
    reporting.write_json(out / "cq_results.json", answers)
    reporting.write_text(out / "cq_results.md", reporting.cq_markdown(answers))
    say.step("Competency questions", {cq: "%d rows" % len(a["rows"]) for cq, a in answers.items()})

    cases = edge_cases.run_all(ctx)
    owl_results = {"status": "skipped (--engine-only)"}
    if not args.engine_only:
        try:
            owl_results = run_owl(kb, result, out, say, skip_hermit=args.skip_hermit)
        except Exception as exc:  # keep every engine result and record exactly what went wrong
            import traceback
            owl_results = {"status": "error", "error": "%s: %s" % (type(exc).__name__, exc), "traceback": traceback.format_exc()}
            say.warn("OWL reasoning failed (%s). Engine results are complete; details are in outputs/owl_results.json." % exc)
        cases.update(owl_results.pop("edge_cases", {}))
    reporting.write_json(out / "edge_cases.json", cases)
    reporting.write_json(out / "owl_results.json", owl_results)

    reporting.write_text(out / "rules_catalog.md", reporting.rules_markdown(rules))
    reporting.write_csv(out / "inferred_facts_engine.csv",
                        [{"predicate": p, "arguments": " | ".join(map(str, a)), "rule": result.derived[(p, a)].rule_id}
                         for p, a in result.derived_facts()], ["predicate", "arguments", "rule"])
    findings = reporting.insights(ctx, answers, cases)
    reporting.write_json(out / "insights.json", findings)
    summary = {
        "falcon_version": __version__, "knowledge_base": kb.summary(),
        "engine": result.summary(),
        "rules_by_source": {s: sum(1 for r in rules if r.source == s) for s in sorted({r.source for r in rules})},
        "backward_chaining": {"showcase": [{k: p[k] for k in ("goal", "holds_backward", "backward_ms", "proof_size", "proof_depth")} for p in proofs],
                              "stats": dict(prover.stats)},
        "competency_questions": {cq: len(a["rows"]) for cq, a in answers.items()},
        "insights": findings,
        "owl": {k: v for k, v in owl_results.items() if k not in ("crossval", "sparql_answers")},
        "runtime_s": round(time.perf_counter() - started, 2),
    }
    reporting.write_json(out / "results_summary.json", summary)
    say.step("Headline findings", {k: findings[k] for k in ("claim_audit", "products_with_undeclared_allergen",
                                                            "hidden_allergen_findings", "market_disagreements",
                                                            "naive_closed_world_false_assurances")})
    say.step("Done", "All outputs written to %s in %.1f s; results_summary.json lists the headline numbers." % (out.resolve(), time.perf_counter() - started))
    return 0


if __name__ == "__main__":
    sys.exit(main())
