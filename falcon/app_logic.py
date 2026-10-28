"""
Logic behind the Streamlit app. No Streamlit imports here, so everything is unit-testable.

* parse_label      turns a pasted ingredient list into ontology ingredients
* analyse_label    runs the rule engine on a label the knowledge base has never seen
* explain_plain    turns a proof tree into sentences a shopper can read
* MYTHS            the 'Myth or fact?' game: the reasoner, not a lookup table, decides each answer
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

from . import schema
from .competency import EngineContext, MARKETS, claim_status, contradiction_evidence, derivation_chain, product_classes
from .engine_bridge import build_rules, make_prover, run_engine
from .kb_loader import KnowledgeBase, load_kb
from .rule_engine import Atom, ProofNode
from .viz import consumer_status, humanise_statement

CUSTOM_ID = "prod_custom_label"
EXTRA_PHRASES = {"soy": "ing_soybean", "soya": "ing_soybean", "eggs": "ing_egg", "milk powder": "ing_whole_milk_powder",
                 "skim milk powder": "ing_skimmed_milk_powder", "whey protein": "ing_whey", "canola oil": "ing_rapeseed_oil",
                 "cocoa": "ing_cocoa_powder", "vanilla": "ing_vanilla_extract", "starch": "ing_corn_starch",
                 "flavouring": "ing_natural_flavouring", "flavoring": "ing_natural_flavouring", "natural flavor": "ing_natural_flavouring",
                 "emulsifier": "ing_lecithin", "anchovies": "ing_anchovy", "prawns": "ing_shrimp", "almond": "ing_almond",
                 "hazelnut": "ing_hazelnut", "cashews": "ing_cashew", "peanut": "ing_peanut", "sesame": "ing_sesame_seed",
                 "mustard": "ing_mustard_seed", "oat": "ing_oats", "gelatine": "ing_gelatin",
                 "mono- and diglycerides": "ing_mono_diglycerides", "monoglycerides": "ing_mono_diglycerides",
                 "lecithins": "ing_lecithin", "milk solids": "ing_whole_milk_powder", "cheese": "ing_mozzarella"}
NOISE = re.compile(r"\b(organic|less than \d+% of|contains \d+% or less of|\d+(\.\d+)?\s*%|and/or|ingredients?)\b", re.I)
_PAREN = re.compile(r"\([^)]*\)")


def load_engine():
    kb = load_kb()
    rules = build_rules(kb)
    _, result = run_engine(kb, rules=rules)
    return kb, rules, EngineContext(kb, result, make_prover(kb, rules), rules)


# ---------------------------------------------------------------------------
# Label parsing
# ---------------------------------------------------------------------------

def build_lexicon(kb: KnowledgeBase) -> List[Tuple[str, str]]:
    table: Dict[str, List[str]] = {}
    for iid, item in kb.ingredients.items():
        label = item["label"].lower()
        phrases = {label, _PAREN.sub("", label).strip()} | {s.lower() for s in item.get("synonyms", [])}
        for inner in re.findall(r"\(([^)]*)\)", label):
            phrases |= {p.strip() for p in inner.split(",") if re.fullmatch(r"e\d{3,4}[a-z]?", p.strip())}
        for phrase in phrases:
            if len(phrase) >= 3:
                table.setdefault(phrase, []).append(iid)
    for phrase, iid in EXTRA_PHRASES.items():
        table.setdefault(phrase, []).append(iid)
    lexicon = {}
    for phrase, ids in table.items():
        # when a phrase is ambiguous (E322 = soy lecithin or plain lecithin) prefer the cautious reading
        ids.sort(key=lambda i: (0 if "UnspecifiedOriginIngredient" in kb.ingredients[i]["classes"] else 1, i))
        lexicon[phrase] = ids[0]
    return sorted(lexicon.items(), key=lambda kv: -len(kv[0]))


def allergens_in(kb: KnowledgeBase, text: str) -> List[str]:
    found = []
    lowered = text.lower()
    for aid, allergen in kb.allergens.items():
        if any(re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(k), lowered) for k in allergen.get("keywords", [])):
            found.append(aid)
    specific_parents = {kb.allergens[a].get("parent") for a in found if kb.allergens[a]["kind"] == "specific"}
    return [a for a in found if a not in specific_parents]


def parse_label(kb: KnowledgeBase, text: str, lexicon=None) -> dict:
    lexicon = lexicon or build_lexicon(kb)
    body, may_contain, declared = text, [], []
    match = re.search(r"may contain\s*:?\s*(.+)$", body, re.I | re.S)
    if match:
        may_contain, body = allergens_in(kb, match.group(1)), body[:match.start()]
    match = re.search(r"\bcontains\s*:\s*(.+)$", body, re.I | re.S)
    if match:
        declared, body = allergens_in(kb, match.group(1)), body[:match.start()]
    found, unknown = [], []
    for token in re.split(r"[,;()\[\]\n]", body):
        token = NOISE.sub("", token.lower()).strip(" .:-*\t")
        if not token:
            continue
        hit = next((iid for phrase, iid in lexicon if token == phrase), None)
        if hit is None:
            hit = next((iid for phrase, iid in lexicon if re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(phrase), token)), None)
        if hit is None:
            unknown.append(token)
        elif hit not in found:
            found.append(hit)
    return {"ingredients": found, "unknown": unknown, "may_contain": may_contain, "declared": declared}


def label_text(kb: KnowledgeBase, product_id: str) -> str:
    p = kb.products[product_id]
    text = ", ".join(kb.ingredients[i]["label"] for i in p["ingredients"])
    if p["may_contain"]:
        text += ". May contain: " + ", ".join(kb.label(a) for a in p["may_contain"])
    return text


# ---------------------------------------------------------------------------
# Live analysis of a label
# ---------------------------------------------------------------------------

def analyse_label(kb: KnowledgeBase, rules, name: str, ingredients, claims=(), sold_in=("jur_us",), may_contain=(),
                  declared=(), complete: bool = True) -> EngineContext:
    """Reason about one new label. Only reference data plus this product is loaded, so it runs in milliseconds."""
    small = kb.copy()
    small.products = {}
    small.add_product({"id": CUSTOM_ID, "label": name or "Your label", "category": None,
                       "ingredients": list(ingredients), "claims": list(claims), "may_contain": list(may_contain),
                       "declared": list(declared), "sold_in": list(sold_in),
                       "status": "complete" if complete else "incomplete"})
    _, result = run_engine(small, rules=rules)
    return EngineContext(small, result, make_prover(small, rules), rules)


def summarise(ctx: EngineContext, pid: str) -> dict:
    kb, res = ctx.kb, ctx.result
    hidden = {(a, i) for (_, a, i) in res.query("hiddenAllergenVia", pid, None, None)}
    allergens: Dict[str, dict] = {}
    for (_, a, i) in res.query("containsVia", pid, None, None):
        entry = allergens.setdefault(a, {"id": a, "allergen": kb.label(a), "kind": kb.allergens[a]["kind"], "via": [], "hidden": []})
        entry["via"].append(kb.label(i))
        if (a, i) in hidden:
            entry["hidden"].append({"ingredient": kb.label(i), "chain": derivation_chain(ctx, i, a)})
    claims = []
    for (_, c) in res.query("hasLabelClaim", pid, None):
        status = claim_status(ctx, pid, c)
        if status == "CONTRADICTED":
            why = contradiction_evidence(ctx, pid, c)
        elif status == "AT RISK":
            why = "'may contain' " + ", ".join(kb.label(a) for (_, a) in res.query("excludesAllergen", c, None) if res.holds("mayContain", pid, a))
        elif status == "UNVERIFIABLE":
            if kb.products[pid]["status"] != "complete":
                why = "ingredient record is incomplete"
            else:
                unclear = [kb.label(i) for (_, i) in res.query("hasIngredient", pid, None) if res.holds("UnspecifiedOriginIngredient", i)]
                why = "origin not stated: " + ", ".join(unclear) if unclear else "cannot be confirmed from the data"
        elif status == "INFORMATIONAL":
            why = kb.claims[c].get("note", "regulated term, not a safety claim")
        else:
            why = "nothing in the recipe or warnings contradicts it"
        claims.append({"claim": kb.label(c), "status": status, "why": why})
    markets = []
    for market, name in MARKETS:
        if market not in kb.products[pid]["sold_in"]:
            continue
        duties = sorted({a for (_, a, _) in res.query("declarationDuty", pid, None, market)}, key=kb.label)
        markets.append({"market": kb.label(market), "must declare": ", ".join(kb.label(a) for a in duties) or "nothing",
                        "undeclared": ", ".join(kb.label(a) for (_, a, _) in res.query("undeclaredAllergen", pid, None, market)),
                        "check with supplier": ", ".join(kb.label(a) for (_, a, _) in res.query("needsSupplierCheck", pid, None, market))})
    consumers = []
    for u in kb.consumers:
        diet = "unsuitable" if res.holds("unsuitableForDietOf", pid, u) else ("uncertain" if res.holds("dietUncertainFor", pid, u) else "")
        consumers.append({"consumer": kb.label(u), "status": consumer_status(ctx, pid, u), "diet": diet})
    classes = [c for c in product_classes(kb) + ["VerifiedVeganProduct", "VerifiedVegetarianProduct"] if res.holds(c, pid)]
    return {"allergens": sorted(allergens.values(), key=lambda e: (not e["hidden"], e["kind"] != "category", e["allergen"])),
            "claims": claims, "markets": markets, "consumers": consumers, "classes": classes}


def conclusions(ctx: EngineContext, pid: str) -> List[Tuple[str, Atom]]:
    """Conclusions a user can ask the reasoner to justify."""
    kb, res = ctx.kb, ctx.result
    out = [("Contains %s" % kb.label(a), Atom("containsAllergen", (pid, a))) for (_, a) in res.query("containsAllergen", pid, None)]
    out += [("Contradicts '%s'" % kb.label(c), Atom("contradictsClaim", (pid, c))) for (_, c) in res.query("contradictsClaim", pid, None)]
    out += [("%s must be declared in %s" % (kb.label(a), kb.label(j)), Atom("declarationDuty", (pid, a, j)))
            for (_, a, j) in res.query("declarationDuty", pid, None, None)]
    out += [("Unsafe for %s" % kb.label(u), Atom("unsafeFor", (pid, u))) for (_, u) in res.query("unsafeFor", pid, None)]
    out += [("Confirmed safe for %s" % kb.label(u), Atom("confirmedSafeFor", (pid, u))) for (_, u) in res.query("confirmedSafeFor", pid, None)]
    if res.holds("VerifiedVeganProduct", pid):
        out.append(("Verified vegan", Atom("VerifiedVeganProduct", (pid,))))
    return out


def replay(ctx: EngineContext, pid: str) -> List[dict]:
    """Forward-chaining events that mention the product, in derivation order."""
    return [e for e in ctx.result.trace if ("(%s" % pid) in e["fact"] or (", %s" % pid) in e["fact"]]


# ---------------------------------------------------------------------------
# Plain-English explanations
# ---------------------------------------------------------------------------

PHRASES = {
    "hasIngredient": "{0} lists {1} as an ingredient", "hasComponent": "{0} contains {1}",
    "retainsAllergensOf": "{0} is made from {1} and keeps its proteins", "derivedFrom": "{0} is made from {1}",
    "triggersAllergen": "{0} is a source of {1}", "possiblyTriggers": "{0} may come from a source of {1}",
    "isSubtypeOf": "{0} belongs to the group {1}", "mayContain": "{0} carries a 'may contain {1}' warning",
    "hasLabelClaim": "{0} is labelled '{1}'", "excludesAllergen": "a '{0}' claim rules out {1}",
    "soldIn": "{0} is sold in {1}", "requiresDeclarationOf": "{0} requires {1} to be declared",
    "declaresAllergen": "{0} declares {1}", "mustAvoid": "{0} must avoid {1}",
    "hasIngredientListStatus": "the ingredient record of {0} is {1}", "hasSulphiteMgPerKg": "{0} contains {1} mg/kg of sulphites",
    "hasGlutenPPM": "{0} tested at {1} ppm gluten", "exemptFromDeclaration": "{0} is exempt from declaring {1} in {2}",
    "containsAllergen": "{0} contains {1}", "containsVia": "{0} contains {1} through {2}", "unsafeFor": "{0} is unsafe for {1}",
    "cautionFor": "{0} needs caution for {1}", "uncertainFor": "{0} is uncertain for {1}",
    "contradictsClaim": "{0} contradicts its '{1}' claim", "declarationDuty": "{0} must declare {1} in {2}",
    "undeclaredAllergen": "{0} does not declare {1}, which {2} requires", "confirmedSafeFor": "{0} is confirmed safe for {1}",
    "hasSomeIngredient": "{0} has at least one listed ingredient", "assertedTrigger": "{0} is itself a source of {1}",
    "mentionsAllergen": "the name '{0}' already mentions {1}", "precautionaryConflictWith": "{0} undermines its '{1}' claim",
}
_STMT = re.compile(r"^(not )?(\w+)\((.*)\)$")


def _humanise_class(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", " ", name).lower()


def sentence(kb: KnowledgeBase, statement: str) -> str:
    match = _STMT.match(statement)
    if not match:
        return statement
    negated, pred, args = match.groups()
    labels = [kb.label(a.strip().strip('"')) for a in args.split(",")]
    if pred in PHRASES:
        text = PHRASES[pred].format(*labels + [""] * 3)
    elif pred[0].isupper() and len(labels) == 1:
        text = "%s is a %s" % (labels[0], _humanise_class(pred))
    else:
        text = humanise_statement(kb, statement)
    if negated:
        return "there is no evidence that " + text
    return text


def explain_plain(kb: KnowledgeBase, proof: ProofNode) -> dict:
    facts, rules, tests = [], [], []

    def walk(node):
        if node.how == "FACT":
            facts.append(sentence(kb, node.statement))
        elif node.how == "NAF":
            facts.append(sentence(kb, node.statement))
        elif node.how == "BUILTIN":
            tests.append(node.statement)
        else:
            rules.append("%s: %s" % (node.how, node.rule_name))
        for child in node.children:
            walk(child)

    walk(proof)
    return {"conclusion": sentence(kb, proof.statement), "facts": list(dict.fromkeys(facts)),
            "rules": list(dict.fromkeys(rules)), "tests": list(dict.fromkeys(tests))}


# ---------------------------------------------------------------------------
# Myth or fact? The reasoner proves (or refutes) every answer.
# ---------------------------------------------------------------------------

MYTHS = [
    dict(key="lactose", statement="Lactose-free milk is safe for a child with a milk allergy.",
         goal=Atom("unsafeFor", ("prod_lactose_free_milk", "cons_maya")), true_if_goal=False,
         lesson="Lactose-free is about milk sugar. The milk proteins that cause allergic reactions are still there."),
    dict(key="nondairy", statement="A 'non-dairy' coffee whitener contains no milk protein.",
         goal=Atom("containsAllergen", ("prod_non_dairy_whitener", "alg_milk")), true_if_goal=False,
         lesson="In the US, 'non-dairy' may legally include caseinate, a milk protein (21 CFR 101.4(d))."),
    dict(key="gfwheat", statement="A gluten-free loaf is always safe for someone with a wheat allergy.",
         goal=Atom("unsafeFor", ("prod_gf_bread_codex", "cons_wei")), true_if_goal=False,
         lesson="Codex wheat starch has its gluten removed but it is still wheat."),
    dict(key="oatdrink", statement="An oat drink is safe for someone with coeliac disease.",
         goal=Atom("unsafeFor", ("prod_oat_barista_drink", "cons_sofia")), true_if_goal=False,
         lesson="Ordinary oats count as a gluten source; only specially produced gluten-free oats are safe."),
    dict(key="vegansauce", statement="A sauce labelled vegan cannot contain fish.",
         goal=Atom("containsAllergen", ("prod_steakhouse_sauce", "alg_fish")), true_if_goal=False,
         lesson="Worcestershire sauce is traditionally made with anchovies, so the fish sat one level below the label."),
    dict(key="tahini", statement="Hummus can contain sesame even when the word 'sesame' never appears on the label.",
         goal=Atom("containsAllergen", ("prod_sesame_hummus", "alg_sesame")), true_if_goal=True,
         lesson="Tahini is ground sesame."),
    dict(key="pinenut", statement="Pine nuts must be declared as a tree nut in the EU.",
         goal=Atom("declarationDuty", ("prod_pesto_genovese", "alg_pine_nut", "jur_eu")), true_if_goal=True,
         lesson="The EU list names eight nuts and pine nut is not one of them. The US and Canada do include it."),
    dict(key="sulphite", statement="Dried apricots with exactly 10 mg/kg of sulphites need a sulphite declaration in the EU.",
         goal=Atom("declarationDuty", ("prod_dried_apricots", "alg_sulphites", "jur_eu")), true_if_goal=True,
         lesson="EU law says 'more than 10 mg/kg'. The US and Canada use '10 ppm or more', so the same tin needs a declaration there."),
    dict(key="refined", statement="The fully refined soybean oil is why the cooking spray contains soy.",
         goal=Atom("containsVia", ("prod_cooking_spray", "alg_soy", "ing_refined_soybean_oil")), true_if_goal=True,
         lesson="Highly refined oils are exempt because refining removes the protein. The soy comes from the lecithin."),
    dict(key="darkchoc", statement="Dark chocolate labelled dairy-free can still be risky for a milk allergy.",
         goal=Atom("cautionFor", ("prod_dark_chocolate", "cons_maya")), true_if_goal=True,
         lesson="It carries a 'may contain milk' warning, which undermines the dairy-free claim."),
    dict(key="coleslaw", statement="A coleslaw labelled egg-free can still contain egg.",
         goal=Atom("containsAllergen", ("prod_coleslaw_egg_free", "alg_egg")), true_if_goal=True,
         lesson="The egg is inside the mayonnaise, so the word 'egg' never appears on the list."),
    dict(key="coconut", statement="Coconut is a regulated tree nut allergen in the US.",
         goal=Atom("containsAllergen", ("prod_coconut_drink", "alg_tree_nuts")), true_if_goal=True,
         lesson="FDA removed coconut from its tree nut list in 2025, and neither Canada nor the EU lists it."),
]


def check_myth(ctx: EngineContext, myth: dict) -> dict:
    proof = ctx.prover.prove(myth["goal"])
    holds = proof is not None
    is_fact = holds if myth["true_if_goal"] else not holds
    return {"is_fact": is_fact, "goal_holds": holds, "proof": proof,
            "why_not": [] if holds else ctx.prover.why_not(myth["goal"])}


# ---------------------------------------------------------------------------
# Data for interactive charts
# ---------------------------------------------------------------------------

def sankey_data(ctx: EngineContext) -> dict:
    kb, res = ctx.kb, ctx.result
    links: Counter = Counter()
    for (_, a, i) in res.query("containsVia", None, None, None):
        if kb.allergens[a]["kind"] == "category" and a != "alg_gluten":
            links[(("ingredient", kb.label(i)), ("allergen", kb.label(a)))] += 1
    for (_, a, j) in res.query("declarationDuty", None, None, None):
        group = a if kb.allergens[a]["kind"] == "category" else kb.allergens[a]["parent"]
        links[(("allergen", kb.label(group)), ("market", kb.label(j)))] += 1
    order = {"ingredient": 0, "allergen": 1, "market": 2}
    nodes = sorted({n for pair in links for n in pair}, key=lambda n: (order[n[0]], n[1]))
    index = {n: k for k, n in enumerate(nodes)}
    return {"labels": [n[1] for n in nodes], "kinds": [n[0] for n in nodes],
            "source": [index[a] for a, _ in links], "target": [index[b] for _, b in links], "value": list(links.values())}


def hierarchy_data(kb: KnowledgeBase) -> dict:
    counts = Counter()
    for item in kb.ingredients.values():
        for cls in item["classes"]:
            counts[cls] += 1
    counts["Product"] = len(kb.products)
    counts["Consumer"] = len(kb.consumers)
    counts["ProductCategory"] = len(kb.categories)
    for a in kb.allergens.values():
        counts["AllergenCategory" if a["kind"] == "category" else "SpecificAllergen"] += 1
    for c in kb.claims.values():
        counts[c["class"]] += 1
    for j in kb.jurisdictions.values():
        counts[j["class"]] += 1
    ids, parents, values = [], [], []
    for name, par, _ in schema.CLASSES:
        ids.append(name)
        parents.append(par[0] if par else "")
        values.append(counts.get(name, 0) + 1)
    return {"ids": ids, "parents": parents, "values": values}


def consumer_matrix(ctx: EngineContext):
    kb = ctx.kb
    products = sorted(kb.products, key=kb.label)
    consumers = list(kb.consumers)
    statuses = [[consumer_status(ctx, p, u) for p in products] for u in consumers]
    return [kb.label(p) for p in products], [kb.label(u) for u in consumers], statuses


def market_matrix(kb: KnowledgeBase):
    allergens = [a for a in kb.allergens if any(a in j["requires_declaration_of"] for j in kb.jurisdictions.values())]
    markets = list(kb.jurisdictions)
    return ([kb.label(a) for a in allergens], [kb.label(m) for m in markets],
            [[1 if a in kb.jurisdictions[m]["requires_declaration_of"] else 0 for m in markets] for a in allergens])
