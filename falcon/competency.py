"""
Competency questions (CQs).

Competency questions state what the knowledge base must be able to answer
(Gruninger & Fox, 1995). Each FALCON CQ is answered by the rule engine over
its forward-chained closure, and, where SPARQL can express it, also by a
query over the Pellet-materialised OWL ontology (see owl_reasoning.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from . import schema
from .config import GLUTEN_FREE_LIMIT_PPM, ONTOLOGY_IRI
from .engine_bridge import run_engine
from .kb_loader import KnowledgeBase
from .rule_engine import Atom, BackwardChainer, ForwardResult

MARKETS = [("jur_us", "US"), ("jur_canada", "Canada"), ("jur_eu", "EU")]
ENGINE_ONLY_CLASSES = ["VerifiedVeganProduct", "VerifiedVegetarianProduct"]

NEW_PRODUCT = {
    "id": "prod_sesame_honey_snaps", "label": "Sesame Honey Snaps (new, unseen product)", "category": "cat_snacks",
    "ingredients": ["ing_sesame_seed", "ing_honey", "ing_glucose_syrup", "ing_wheat_flour"],
    "claims": ["claim_vegan"], "may_contain": [], "declared": ["alg_sesame"],
    "sold_in": ["jur_eu", "jur_canada"], "status": "complete",
    "scenario": "Not part of the curated data; used to show classification of a new instance.",
}


@dataclass
class EngineContext:
    kb: KnowledgeBase
    result: ForwardResult
    prover: BackwardChainer
    rules: list

    def lab(self, x) -> str:
        return self.kb.label(x)

    def holds(self, pred, *args) -> bool:
        return self.result.holds(pred, *args)

    def q(self, pred, *pattern):
        return self.result.query(pred, *pattern)


@dataclass
class CompetencyQuestion:
    cq_id: str
    question: str
    kind: str
    engine: Callable[[EngineContext], dict]
    sparql: Optional[str] = None


def product_classes(kb: KnowledgeBase) -> List[str]:
    names = [d["name"] for d in schema.DEFINED_CLASSES if "Product" in d["parents"]]
    names += ["MeetsGlutenFreeThreshold", "SulphiteAtOrAbove10ppm", "SulphiteAbove10ppm"]
    names += [a["product_class"] for a in kb.allergens.values() if a.get("product_class")]
    return names


def claim_status(ctx: EngineContext, product: str, claim: str) -> str:
    if ctx.holds("contradictsClaim", product, claim):
        return "CONTRADICTED"
    if ctx.holds("precautionaryConflictWith", product, claim):
        return "AT RISK"
    if ctx.holds("claimVerified", product, claim):
        return "VERIFIED"
    if ctx.holds("claimInformational", product, claim):
        return "INFORMATIONAL"
    return "UNVERIFIABLE"


def _with_components(ctx, ingredient, component_class) -> str:
    parts = [ctx.lab(c) for (_, c) in ctx.q("hasComponent", ingredient, None) if ctx.holds(component_class, c)]
    return "%s (contains %s)" % (ctx.lab(ingredient), ", ".join(parts)) if parts else ctx.lab(ingredient)


def contradiction_evidence(ctx: EngineContext, product: str, claim: str) -> str:
    kb = ctx.kb
    cls = kb.claims[claim]["class"]
    reasons = []
    for allergen in kb.claims[claim]["excludes"]:
        for (_, _, ingredient) in ctx.q("containsVia", product, allergen, None):
            reasons.append("%s via %s" % (ctx.lab(allergen), ctx.lab(ingredient)))
    ingredients = [i for (_, i) in ctx.q("hasIngredient", product, None)]
    if cls == "VeganClaim":
        reasons += [_with_components(ctx, i, "AnimalDerivedIngredient") for i in ingredients if ctx.holds("NonVeganIngredient", i)]
    if cls == "VegetarianClaim":
        reasons += [_with_components(ctx, i, "VegetarianIncompatibleIngredient") for i in ingredients
                    if ctx.holds("NonVegetarianIngredient", i)]
    if cls == "LactoseFreeClaim":
        reasons += [ctx.lab(i) + " (lactose source)" for i in ingredients if ctx.holds("LactoseSourceIngredient", i)]
    if cls == "GlutenFreeClaim":
        ppm = kb.products[product].get("gluten_ppm")
        if ppm is not None and ppm >= GLUTEN_FREE_LIMIT_PPM:
            reasons.append("lab result %.0f ppm is not below %.0f ppm" % (ppm, GLUTEN_FREE_LIMIT_PPM))
    return "; ".join(dict.fromkeys(reasons)) or "see proof"


def derivation_chain(ctx: EngineContext, ingredient: str, allergen: str) -> str:
    """Shortest path of asserted retention/composition links from a label ingredient to the root allergen source."""
    base = ctx.result.base
    edges = {}
    for pred in ("retainsAllergensOf", "hasComponent"):
        for (src, dst) in base.match(pred, (None, None)):
            edges.setdefault(src, []).append(dst)
    frontier, seen = [[ingredient]], {ingredient}
    while frontier:
        path = frontier.pop(0)
        if base.has("assertedTrigger", (path[-1], allergen)):
            return "%s  =>  %s allergen" % (" -> ".join(ctx.lab(x) for x in path), ctx.lab(allergen))
        for nxt in edges.get(path[-1], []):
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(path + [nxt])
    return "%s  =>  %s allergen" % (ctx.lab(ingredient), ctx.lab(allergen))


# ---------------------------------------------------------------------------
# The questions
# ---------------------------------------------------------------------------

def cq01(ctx):
    asserted = {a[0] for a in ctx.result.base.match("retainsAllergensOf", (None, "ing_milk"))}
    asserted |= {a[0] for a in ctx.result.base.match("derivedFrom", (None, "ing_milk"))}
    rows = [{"ingredient": ctx.lab(i), "how it is known": "asserted" if i in asserted else "inferred (sub-property + transitivity)"}
            for (i, _) in ctx.q("derivedFrom", None, "ing_milk")]
    rows.sort(key=lambda r: (r["how it is known"], r["ingredient"]))
    return dict(columns=["ingredient", "how it is known"], rows=rows,
                note="%d ingredients asserted as made directly from milk; reasoning finds %d in total."
                     % (len(asserted), len(rows)))


def cq02(ctx, product="prod_steakhouse_sauce"):
    rows = [{"allergen": ctx.lab(a), "via ingredient": ctx.lab(i),
             "hidden from shoppers": "yes" if ctx.holds("hiddenAllergenVia", product, a, i) else ""}
            for (_, a, i) in ctx.q("containsVia", product, None, None)]
    proof = ctx.prover.prove(Atom("containsAllergen", (product, "alg_fish")))
    return dict(columns=["allergen", "via ingredient", "hidden from shoppers"], rows=rows,
                proof=proof.render() if proof else "", proof_tree=proof.to_dict() if proof else None,
                note="Backward chaining proves containsAllergen(%s, alg_fish) from asserted facts only." % product)


def cq03(ctx):
    rows = []
    for (p, c) in ctx.q("contradictsClaim", None, None):
        derivation = ctx.result.derived.get(("contradictsClaim", (p, c)))
        rows.append({"product": ctx.lab(p), "claim": ctx.lab(c), "rule": derivation.rule_id if derivation else "",
                     "evidence": contradiction_evidence(ctx, p, c)})
    return dict(columns=["product", "claim", "rule", "evidence"], rows=rows,
                note="%d of %d claims are contradicted by the products' own composition."
                     % (len(rows), len(ctx.q("hasLabelClaim", None, None))))


def cq04(ctx):
    rows = []
    for (p, c) in ctx.q("precautionaryConflictWith", None, None):
        allergens = [ctx.lab(a) for (_, a) in ctx.q("excludesAllergen", c, None) if ctx.holds("mayContain", p, a)]
        rows.append({"product": ctx.lab(p), "claim": ctx.lab(c), "'may contain'": ", ".join(allergens)})
    return dict(columns=["product", "claim", "'may contain'"], rows=rows)


def _consumer_rows(ctx, consumer):
    avoid = {a for (_, a) in ctx.q("mustAvoid", consumer, None)}
    rows = []
    for product in ctx.kb.products:
        if ctx.holds("unsafeFor", product, consumer):
            status, why = "UNSAFE", [a for (_, a) in ctx.q("containsAllergen", product, None) if a in avoid]
        elif ctx.holds("cautionFor", product, consumer):
            status, why = "CAUTION", [a for (_, a) in ctx.q("mayContain", product, None) if a in avoid]
        elif ctx.holds("uncertainFor", product, consumer):
            status, why = "UNCERTAIN", [i for (_, i) in ctx.q("hasIngredient", product, None)
                                        if any(ctx.holds("possiblyTriggers", i, a) for a in avoid)]
        else:
            continue
        rows.append({"product": ctx.lab(product), "status": status, "because": ", ".join(ctx.lab(x) for x in why)})
    order = {"UNSAFE": 0, "CAUTION": 1, "UNCERTAIN": 2}
    return sorted(rows, key=lambda r: (order[r["status"]], r["product"]))


def cq05(ctx):
    rows = _consumer_rows(ctx, "cons_liam")
    return dict(columns=["product", "status", "because"], rows=rows,
                note="Liam avoids peanut and tree nuts; isSubtypeOf lets 'tree nuts' match almond, hazelnut and pine nut.")


def cq06(ctx):
    rows = [{"product": ctx.lab(p)} for (p, _) in ctx.q("confirmedSafeFor", None, "cons_liam")]
    why = {}
    for product in ("prod_dark_chocolate", "prod_rice_puffs_incomplete"):
        why[ctx.lab(product)] = ctx.prover.why_not(Atom("confirmedSafeFor", (product, "cons_liam")))
    return dict(columns=["product"], rows=rows, why_not=why,
                note="Only possible with negation as failure; OWL alone can never conclude that a product is safe.")


def cq07(ctx):
    classes = product_classes(ctx.kb) + ENGINE_ONLY_CLASSES
    rows = []
    for product in ctx.kb.products:
        found = [c + ("*" if c in ENGINE_ONLY_CLASSES else "") for c in classes if ctx.holds(c, product)]
        rows.append({"product": ctx.lab(product), "inferred classes": ", ".join(found) or "(none)"})
    return dict(columns=["product", "inferred classes"], rows=rows,
                note="* = closed-world class computed by the engine; all others are OWL defined classes.")


def cq08(ctx):
    rows, disagreements = [], 0
    for product, p in ctx.kb.products.items():
        allergens = sorted({a for (_, a, _) in ctx.q("declarationDuty", product, None, None)})
        for allergen in allergens:
            row = {"product": ctx.lab(product), "allergen": ctx.lab(allergen)}
            values = []
            for market, name in MARKETS:
                if market not in p["sold_in"]:
                    row[name] = "not sold"
                    continue
                duty = ctx.holds("declarationDuty", product, allergen, market)
                row[name] = "must declare" if duty else "not required"
                values.append(duty)
            row["markets disagree"] = "yes" if len(set(values)) > 1 else ""
            disagreements += row["markets disagree"] == "yes"
            rows.append(row)
    return dict(columns=["product", "allergen", "US", "Canada", "EU", "markets disagree"], rows=rows,
                note="%d product-allergen pairs are treated differently by markets the product is sold in." % disagreements)


def cq09(ctx):
    rows = [{"product": ctx.lab(p), "allergen": ctx.lab(a), "ingredient on label": ctx.lab(i),
             "derivation": derivation_chain(ctx, i, a)}
            for (p, a, i) in ctx.q("hiddenAllergenVia", None, None, None)]
    return dict(columns=["product", "allergen", "ingredient on label", "derivation"], rows=rows)


def cq10(ctx):
    rows = []
    for (p,) in ctx.q("IncompleteRecordProduct", None):
        confirmed = len(ctx.q("confirmedSafeFor", p, None))
        claims = [ctx.lab(c) + " -> " + claim_status(ctx, p, c) for (_, c) in ctx.q("hasLabelClaim", p, None)]
        rows.append({"product": ctx.lab(p), "ingredients known": len(ctx.q("hasIngredient", p, None)),
                     "consumers confirmed safe": "%d of %d" % (confirmed, len(ctx.kb.consumers)),
                     "claims": "; ".join(claims) or "(none)"})
    return dict(columns=["product", "ingredients known", "consumers confirmed safe", "claims"], rows=rows)


def cq11(ctx):
    rows = []
    for (p, _) in ctx.q("hasLabelClaim", None, "claim_gluten_free"):
        ppm = ctx.kb.products[p].get("gluten_ppm")
        lab_status = "untested" if ppm is None else ("meets limit" if ppm < GLUTEN_FREE_LIMIT_PPM else "exceeds limit")
        sources = [ctx.lab(i) for (_, i) in ctx.q("hasIngredient", p, None) if ctx.holds("GlutenSourceIngredient", i)]
        rows.append({"product": ctx.lab(p), "gluten (ppm)": "" if ppm is None else ppm, "lab result": lab_status,
                     "gluten sources in recipe": ", ".join(sources) or "none",
                     "verdict": claim_status(ctx, p, "claim_gluten_free"),
                     "contains wheat": "yes" if ctx.holds("containsAllergen", p, "alg_wheat") else ""})
    return dict(columns=["product", "gluten (ppm)", "lab result", "gluten sources in recipe", "verdict", "contains wheat"],
                rows=rows, note="Gluten-free and wheat-free are different claims: see the Codex wheat starch loaf.")


def cq12(ctx, new_product=None):
    new_product = dict(new_product or NEW_PRODUCT)
    kb2 = ctx.kb.copy()
    kb2.add_product(new_product)
    _, res = run_engine(kb2, rules=ctx.rules)
    pid = new_product["id"]
    classes = [c + ("*" if c in ENGINE_ONLY_CLASSES else "")
               for c in product_classes(kb2) + ENGINE_ONLY_CLASSES if res.holds(c, pid)]
    sub = EngineContext(kb2, res, ctx.prover, ctx.rules)
    rows = [
        {"aspect": "ingredients", "result": ", ".join(kb2.label(i) for i in new_product["ingredients"])},
        {"aspect": "inferred classes", "result": ", ".join(classes)},
        {"aspect": "allergens", "result": ", ".join(kb2.label(a) for (_, a) in res.query("containsAllergen", pid, None))},
        {"aspect": "claim audit", "result": "; ".join("%s -> %s" % (kb2.label(c), claim_status(sub, pid, c))
                                                       for (_, c) in res.query("hasLabelClaim", pid, None))},
        {"aspect": "undeclared allergens", "result": ", ".join("%s (%s)" % (kb2.label(a), kb2.label(j))
                                                                for (_, a, j) in res.query("undeclaredAllergen", pid, None, None)) or "none"},
        {"aspect": "unsafe for", "result": ", ".join(kb2.label(u) for (_, u) in res.query("unsafeFor", pid, None)) or "nobody"},
        {"aspect": "unsuitable for diet of", "result": ", ".join(kb2.label(u) for (_, u) in res.query("unsuitableForDietOf", pid, None)) or "nobody"},
    ]
    return dict(columns=["aspect", "result"], rows=rows, new_product=new_product)


def cq13(ctx):
    rows = [{"product": ctx.lab(p), "allergen": ctx.lab(a), "market": ctx.lab(j), "finding": "undeclared"}
            for (p, a, j) in ctx.q("undeclaredAllergen", None, None, None)]
    rows += [{"product": ctx.lab(p), "allergen": ctx.lab(a), "market": ctx.lab(j), "finding": "verify with supplier"}
             for (p, a, j) in ctx.q("needsSupplierCheck", None, None, None)]
    products = {r["product"] for r in rows if r["finding"] == "undeclared"}
    return dict(columns=["product", "allergen", "market", "finding"], rows=rows,
                note="%d products carry at least one undeclared allergen in a market where they are sold." % len(products))


def cq14(ctx):
    rows, counts = [], {}
    for (p, c) in ctx.q("hasLabelClaim", None, None):
        status = claim_status(ctx, p, c)
        counts[status] = counts.get(status, 0) + 1
        rows.append({"product": ctx.lab(p), "claim": ctx.lab(c), "status": status})
    order = {"CONTRADICTED": 0, "AT RISK": 1, "UNVERIFIABLE": 2, "INFORMATIONAL": 3, "VERIFIED": 4}
    rows.sort(key=lambda r: (order[r["status"]], r["product"]))
    return dict(columns=["product", "claim", "status"], rows=rows, counts=counts)


_P = "falcon:"
CQS: List[CompetencyQuestion] = [
    CompetencyQuestion("CQ01", "Which ingredients are made from milk, directly or indirectly?", "lookup + transitive reasoning", cq01,
                       "SELECT DISTINCT ?ingredient WHERE { ?ingredient falcon:derivedFrom falcon:ing_milk . }"),
    CompetencyQuestion("CQ02", "Which allergens does Smoky Steakhouse Sauce contain, and through which ingredient?", "complex reasoning + proof", cq02,
                       "SELECT DISTINCT ?allergen WHERE { falcon:prod_steakhouse_sauce falcon:containsAllergen ?allergen . }"),
    CompetencyQuestion("CQ03", "Which products contradict their own label claims, and why?", "rule-based inference", cq03,
                       "SELECT ?product ?claim WHERE { ?product falcon:contradictsClaim ?claim . } ORDER BY ?product"),
    CompetencyQuestion("CQ04", "Which free-from claims are undermined by a 'may contain' warning?", "rule-based inference", cq04,
                       "SELECT ?product ?claim ?allergen WHERE { ?product falcon:precautionaryConflictWith ?claim . "
                       "?claim falcon:excludesAllergen ?allergen . ?product falcon:mayContain ?allergen . }"),
    CompetencyQuestion("CQ05", "Which products are unsafe, or need caution, for Liam (peanut and tree nut allergy)?", "personalised reasoning", cq05,
                       "SELECT ?product ?status WHERE { { ?product falcon:unsafeFor falcon:cons_liam . BIND(\"UNSAFE\" AS ?status) } "
                       "UNION { ?product falcon:cautionFor falcon:cons_liam . FILTER NOT EXISTS { ?product falcon:unsafeFor falcon:cons_liam } "
                       "BIND(\"CAUTION\" AS ?status) } }"),
    CompetencyQuestion("CQ06", "Which products can be confirmed safe for Liam, and why are others excluded?", "negation as failure", cq06,
                       "SELECT ?product WHERE { ?product a falcon:Product ; falcon:hasIngredientListStatus \"complete\" . "
                       "FILTER NOT EXISTS { ?product falcon:unsafeFor falcon:cons_liam } "
                       "FILTER NOT EXISTS { ?product falcon:cautionFor falcon:cons_liam } "
                       "FILTER NOT EXISTS { ?product falcon:hasIngredient ?i . ?i falcon:possiblyTriggers ?a . falcon:cons_liam falcon:mustAvoid ?a } }"),
    CompetencyQuestion("CQ07", "How is each product classified automatically?", "classification", cq07,
                       "SELECT ?product ?class WHERE { ?product a falcon:Product . ?product a ?class . "
                       "?class rdfs:subClassOf* falcon:Product . FILTER(?class != falcon:Product) }"),
    CompetencyQuestion("CQ08", "Which allergens must each product declare in the US, Canada and the EU, and where do the markets disagree?",
                       "jurisdiction-aware reasoning", cq08,
                       "SELECT ?product ?allergen ?market WHERE { { ?product falcon:mustDeclareInUS ?allergen . BIND(\"US\" AS ?market) } "
                       "UNION { ?product falcon:mustDeclareInCanada ?allergen . BIND(\"Canada\" AS ?market) } "
                       "UNION { ?product falcon:mustDeclareInEU ?allergen . BIND(\"EU\" AS ?market) } }"),
    CompetencyQuestion("CQ09", "Which products contain an allergen that the ingredient names do not reveal?", "hidden-allergen reasoning", cq09,
                       "SELECT ?product ?allergen ?ingredient WHERE { ?product falcon:hasIngredient ?ingredient . "
                       "?ingredient falcon:triggersAllergen ?allergen . FILTER NOT EXISTS { GRAPH <%s> { ?ingredient falcon:triggersAllergen ?allergen } } }"
                       % ONTOLOGY_IRI),
    CompetencyQuestion("CQ10", "Which products cannot be assessed because their ingredient information is incomplete?", "incomplete information", cq10,
                       "SELECT ?product WHERE { ?product a falcon:IncompleteRecordProduct . }"),
    CompetencyQuestion("CQ11", "Which gluten-free products meet the 20 ppm limit, which exceed it, and which rely on the recipe alone?",
                       "numeric reasoning", cq11,
                       "SELECT ?product ?ppm ?status WHERE { ?product falcon:hasLabelClaim ?claim . ?claim a falcon:GlutenFreeClaim . "
                       "OPTIONAL { ?product falcon:hasGlutenPPM ?ppm } "
                       "BIND(IF(!BOUND(?ppm), \"UNTESTED\", IF(?ppm < 20, \"MEETS\", \"EXCEEDS\")) AS ?status) }"),
    CompetencyQuestion("CQ12", "How is a new, previously unseen product classified?", "classification of a new instance", cq12, None),
    CompetencyQuestion("CQ13", "Which products have allergens that a market requires but the label does not declare?", "compliance (recall risk)", cq13,
                       "SELECT ?product ?allergen ?market WHERE { { ?product falcon:mustDeclareInUS ?allergen . BIND(\"US\" AS ?market) } "
                       "UNION { ?product falcon:mustDeclareInCanada ?allergen . BIND(\"Canada\" AS ?market) } "
                       "UNION { ?product falcon:mustDeclareInEU ?allergen . BIND(\"EU\" AS ?market) } "
                       "FILTER NOT EXISTS { ?product falcon:declaresAllergen ?allergen } }"),
    CompetencyQuestion("CQ14", "Which label claims are verified, contradicted, at risk or unverifiable?", "three-valued claim audit", cq14,
                       "SELECT ?product ?claim WHERE { ?product falcon:hasLabelClaim ?claim . "
                       "FILTER NOT EXISTS { ?product falcon:contradictsClaim ?claim } }"),
]


def answer_all(ctx: EngineContext) -> Dict[str, dict]:
    answers = {}
    for cq in CQS:
        result = cq.engine(ctx)
        result.update(question=cq.question, kind=cq.kind, sparql=cq.sparql)
        answers[cq.cq_id] = result
    return answers
