"""
Build the full FALCON notebook: a narrated, runnable walk-through of the whole system.

    python notebooks/make_notebook.py                                  -> notebooks/FALCON_Notebook.ipynb (public)
    python notebooks/make_notebook.py --submission OUT.ipynb           -> course version with the cover details

The project's code and data are embedded, so the notebook runs in Google Colab
(Runtime > Run all) or in local Jupyter with nothing else to upload.
"""
import os
import argparse
import base64
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INCLUDE = ["falcon", "data", "tests", "run_all.py", "check_environment.py", "requirements.txt"]


def snapshot() -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in INCLUDE:
            path = ROOT / item
            files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
            for f in files:
                archive.write(f, "falcon_kr/" + f.relative_to(ROOT).as_posix())
    return base64.b64encode(buffer.getvalue()).decode("ascii")


# Cover details for the submission copy come from environment variables, so no student ID is stored in the repository:
#   FALCON_NUID, FALCON_COURSE, FALCON_INSTRUCTOR, FALCON_DUE
COVER_SUBMISSION = """# FALCON: Ontology-Based Reasoning for Food Allergen and Label Compliance

**Anush Goel**  
""" + ("NUID: %s  \n" % os.environ["FALCON_NUID"] if os.environ.get("FALCON_NUID") else "") + """Northeastern University  
""" + os.environ.get("FALCON_COURSE", "[Course number: Course name]") + """  
""" + os.environ.get("FALCON_INSTRUCTOR", "[Instructor name]") + """  
""" + os.environ.get("FALCON_DUE", "[Due date]") + """

Companion notebook to the technical report *FALCON: Ontology-Based Reasoning for Food Allergen and Label Compliance Across Three Regulatory Markets*."""

COVER_PUBLIC = """# FALCON: Ontology-Based Reasoning for Food Allergen and Label Compliance

A knowledge representation system that reads food labels the way a regulator would. It follows every ingredient back to its source, checks every claim on the pack, and works out which market (United States, Canada or European Union) would reject the product. Every verdict comes with a proof."""

INTRO = """## About this notebook

This notebook demonstrates the complete system end to end. Every table, trace and figure below is produced live by the code. Nothing is pasted in.

| Requirement | Where it is shown |
|---|---|
| Domain selection and scope | Section 1 |
| Classes, hierarchy, object and data properties | Sections 2 and 3 |
| Domain/range, cardinality and disjointness axioms | Sections 2.4 and 3 |
| Individuals (knowledge base population) | Sections 1 and 3.2 |
| At least five production rules | Section 5.1: 17 SWRL rules, plus 49 engine rules |
| Forward and backward chaining, with step-by-step traces | Sections 5.3 to 5.6 |
| Consistency checking | Sections 4.1, 8.3 and 9 |
| At least eight competency questions (lookup, reasoning, classification) | Section 6: 14 questions, each with SPARQL |
| Automatic classification of new instances | Sections 4.3 and 7 |
| Incomplete information and conflicting data | Section 8 |
| Ontology tool (owlready2, HermiT, Pellet) | Sections 3 and 4 |
| Expressiveness, alternatives and scalability | Sections 11 and 13 |

**How to run.** In Google Colab choose *Runtime > Run all*. A GPU or TPU does not help: the rule engine is pure Python, and HermiT and Pellet are Java programs that use one processor core. Setup installs Java 25 automatically, which the Pellet bundled with owlready2 0.51 needs. A full run took about 4.5 hours on Colab, almost all of it in Pellet: each complete Pellet run takes 25 to 36 minutes, and Section 12 repeats them to write every result file in one pass. The rule engine sections take seconds. Keep the browser tab open so that Colab does not disconnect the session. In local Jupyter, run the cells in order. The final cells write the `outputs/` folder and download it as `falcon_results.zip`; to keep the executed notebook with all its outputs, use *File > Download > .ipynb*.

If a step that needs Java cannot run, the notebook prints the reason and carries on, and if Pellet cannot run, HermiT supplies the inferred facts. The rule engine sections never need Java."""

UNPACK = r'''#@title Setup 1: unpack the project (embedded in this notebook) { display-mode: "form" }
PAYLOAD = "__PAYLOAD__"
import base64, glob, io, os, sys, zipfile
IN_COLAB = "google.colab" in sys.modules
here = os.path.abspath(os.getcwd())
project = next((c for c in (here, os.path.dirname(here))
                if os.path.exists(os.path.join(c, "run_all.py")) and os.path.isdir(os.path.join(c, "falcon"))), None)
if project is None:
    base = "/content" if IN_COLAB else here
    uploaded = [z for z in glob.glob(os.path.join(base, "*.zip"))
                if "falcon" in os.path.basename(z).lower() and "results" not in os.path.basename(z).lower()]
    source = uploaded[0] if uploaded else io.BytesIO(base64.b64decode(PAYLOAD))
    with zipfile.ZipFile(source) as archive:
        archive.extractall(base)
    print("Unpacked", os.path.basename(uploaded[0]) if uploaded else "the snapshot embedded in this notebook")
    project = os.path.dirname(sorted(glob.glob(os.path.join(base, "**", "run_all.py"), recursive=True), key=len)[0])
os.chdir(project)
if project not in sys.path:
    sys.path.insert(0, project)
os.makedirs("outputs", exist_ok=True)
print("Project folder:", project)
'''

INSTALL = r'''#@title Setup 2: Java 25 (for HermiT and Pellet) and owlready2 { display-mode: "form" }
import importlib, platform, re, shutil, subprocess

def java_major(exe):
    try:
        text = subprocess.run([exe, "-version"], capture_output=True, text=True).stderr
        m = re.search(r'version "(\d+)(?:\.(\d+))?', text)
        return (int(m.group(2) or 0) if m.group(1) == "1" else int(m.group(1))) if m else 0
    except Exception:
        return 0

# The Pellet bundled with owlready2 0.51+ is compiled for Java 25, and Colab ships Java 21.
JAVA25 = "/opt/java25/bin/java"
if IN_COLAB and not os.path.exists(JAVA25) and java_major(shutil.which("java") or "java") < 25:
    print("Installing Java 25 (Eclipse Temurin, about 30 seconds)...")
    for image in ("jre", "jdk"):                 # the full JDK is the fallback if the JRE download fails
        subprocess.run("rm -rf /opt/java25 && mkdir -p /opt/java25 && curl -fsSL "
                       "'https://api.adoptium.net/v3/binary/latest/25/ga/linux/x64/%s/hotspot/normal/eclipse' "
                       "| tar -xz -C /opt/java25 --strip-components=1" % image, shell=True)
        if os.path.exists(JAVA25):
            break
    if not os.path.exists(JAVA25):
        print("Java 25 could not be downloaded; HermiT will stand in for Pellet.")
if os.path.exists(JAVA25):
    os.environ["FALCON_JAVA"] = JAVA25          # FALCON uses this Java for HermiT and Pellet
elif IN_COLAB and shutil.which("java") is None:
    subprocess.run("apt-get -qq update && apt-get -qq install -y openjdk-21-jre-headless", shell=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    import owlready2
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "owlready2>=0.45"], check=False)
    importlib.invalidate_caches()
    try:
        import owlready2
    except ImportError:
        owlready2 = None
java = os.environ.get("FALCON_JAVA") or shutil.which("java")
java_version = subprocess.run([java, "-version"], capture_output=True, text=True).stderr.splitlines()[0] if java else "not found"
print("Python     ", platform.python_version())
print("owlready2  ", getattr(owlready2, "VERSION", "not installed"))
print("Java       ", java_version)
'''

IMPORTS = r'''import contextlib, inspect, json, time, traceback, warnings
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import Markdown, display

from falcon import app_logic, benchmark, competency, edge_cases, reporting, rules_catalog, schema, viz
from falcon import owl_reasoning as orz
from falcon import rule_engine
from falcon.engine_bridge import build_rules, kb_facts, make_prover, run_engine
from falcon.kb_loader import load_kb
from falcon.rule_engine import Atom

pd.set_option("display.max_colwidth", 140)
pd.set_option("display.max_rows", 120)
warnings.filterwarnings("ignore")


def show(fig):
    """Display a matplotlib figure inline and free its memory."""
    display(fig)
    plt.close(fig)


def md(text):
    display(Markdown(text))


@contextlib.contextmanager
def guarded(step):
    """Report a failure clearly and let the rest of the notebook continue."""
    try:
        yield
    except Exception:
        print("[%s] did not complete; the notebook continues. Details:" % step)
        traceback.print_exc()


OWL_AVAILABLE = orz.available() and orz.configure_java()["java"] is not None
owl_ok, MATERIALIZER, OWL_REASONER = False, None, "pellet"   # set in Section 4
print("OWL reasoning available:", OWL_AVAILABLE)
'''

S1_MD = """## 1. Domain selection and scope

**Domain: food allergen and label compliance.** About one adult in ten in the United States has a food allergy. Undeclared allergens remain a leading reason packaged foods are recalled. The domain fits knowledge representation well for three reasons.

- **It is relational.** Whey is milk. Worcestershire sauce is made with anchovy. The lysozyme used in some cheeses comes from egg white.
- **It is rule-based.** Thresholds and exemptions decide what must be declared.
- **It is jurisdictional.** Pine nuts must be declared in the US and Canada but not in the EU. At exactly 10 mg/kg of sulphites, a declaration is required in North America but not in Europe.

**Scope.** The system covers packaged products sold in the US, Canada and the EU, regulated allergens (groups and their named members), ingredient provenance and composition, label claims, and consumer profiles. It leaves out nutrition panels, cross-contact probabilities and recipes' quantities.

The knowledge base is curated rather than scraped. Every product is there to exercise a specific competency question or edge case, so the counts below describe the system's capabilities, not market prevalence."""

S1_LOAD = r'''kb = load_kb()     # loads data/*.json and validates every cross-reference
print("Validation errors:", kb.errors or "none", "| warnings:", kb.warnings or "none")
pd.DataFrame([kb.summary()]).T.rename(columns={0: "count"})
'''

S1_PRODUCTS = r'''pd.DataFrame([{
    "product": p["label"], "category": kb.label(p["category"]), "ingredients": len(p["ingredients"]),
    "claims on pack": ", ".join(kb.label(c) for c in p["claims"]),
    "may contain": ", ".join(kb.label(a) for a in p["may_contain"]),
    "markets": ", ".join(kb.label(j) for j in p["sold_in"]), "record": p["status"], "what it tests": p["scenario"],
} for p in kb.products.values()])
'''

S1_MARKETS = r'''# What each market requires to be declared (from data/jurisdictions.json)
rows = []
for a in kb.allergens.values():
    marks = {kb.label(j): ("must declare" if a["id"] in j_data["requires_declaration_of"] else "")
             for j, j_data in kb.jurisdictions.items()}
    if any(marks.values()):
        rows.append(dict({"allergen": a["label"], "kind": a["kind"]}, **marks))
display(pd.DataFrame(rows))
show(viz.fig_market_grid(kb, None))
'''

S2_MD = """## 2. Conceptual model and ontology design

The product is the hub of the model. Everything the system concludes about a product is derived from three things: its ingredients, the claims on its pack, and the markets where it is sold. Those conclusions cover its allergens, whether its claims hold, its declaration duties in each market, and its safety for each consumer.

**Design patterns used**
- **Ingredient kinds are individuals**, because SWRL rules can only bind named individuals (DL safety).
- **Provenance is separate from allergen retention.** `retainsAllergensOf` is a sub-property of `derivedFrom`, and only `retainsAllergensOf` carries allergens through a property chain. So fully refined soybean oil is made from soy but carries no soy allergen.
- **Gluten is a separate hazard from wheat.** Codex wheat starch is gluten-free but still wheat.
- **N-ary relations use reification.** An exemption involves an ingredient, an allergen and a market, so it is modelled as its own `DeclarationExemption` individual.
- **Claims are data, not axioms.** A false claim is reported as a finding instead of making the whole ontology inconsistent.
- **Allergen-group membership is per market**, because the markets disagree about which nuts count as tree nuts.

A single specification, `falcon/schema.py`, drives both the OWL ontology and the rule engine."""

S2_CONCEPT = r'''show(viz.fig_conceptual_model(kb))   # solid = asserted, dashed = inferred by reasoning
'''

S2_CLASSES = r'''classes = pd.DataFrame([{"class": n, "parents": ", ".join(p) or "(top level)", "meaning": c}
                        for n, p, c in schema.CLASSES])
print(len(schema.CLASSES), "named classes and", len(schema.DEFINED_CLASSES), "defined classes",
      "(plus one allergen-specific product class per allergen group)")
display(classes)
show(viz.fig_class_hierarchy(kb))
'''

S2_PROPS = r'''object_props = pd.DataFrame([{
    "object property": name, "domain": ", ".join(s["domain"]), "range": ", ".join(s["range"]),
    "characteristics": ", ".join(s.get("characteristics", [])), "sub-property of": s.get("parent", ""),
    "inverse of": s.get("inverse", ""), "meaning": s.get("comment", "")} for name, s in schema.OBJECT_PROPERTIES.items()])
data_props = pd.DataFrame([{"data property": name, "domain": ", ".join(s["domain"]), "range": s["range"],
                            "functional": s.get("functional", False), "meaning": s.get("comment", "")}
                           for name, s in schema.DATA_PROPERTIES.items()])
display(object_props)
display(data_props)
'''

S2_AXIOMS = r'''md("**Property chains (OWL 2 complex role inclusions)**")
display(pd.DataFrame([{"axiom": " \u2218 ".join(c["chain"]) + " \u2291 " + c["super"], "meaning": c["comment"]}
                      for c in schema.PROPERTY_CHAINS]))
md("**Defined classes** (the reasoner classifies individuals into these automatically)")
display(pd.DataFrame([{"defined class": d["name"], "sub-class of": ", ".join(d["parents"]),
                       "Horn translation used by the engine": " | ".join(d["horn"]) or "universal restriction: closed-world rule instead",
                       "note": d.get("comment", "")} for d in schema.DEFINED_CLASSES]))
md("**General class axioms, restrictions and disjointness**")
display(pd.DataFrame([{"axiom": "GCI: ... \u2291 " + g["right"], "Horn form": g["horn"], "meaning": g.get("comment", "")}
                      for g in schema.GCIS]))
display(pd.DataFrame([{"class": r["cls"], "restriction": r.get("comment", "")} for r in schema.RESTRICTIONS]))
display(pd.DataFrame([{"pairwise disjoint classes": ", ".join(g)} for g in schema.DISJOINT_GROUPS]))
'''

S3_MD = """## 3. Building the OWL ontology with owlready2

`falcon/ontology_builder.py` turns the schema and the data into an OWL 2 DL ontology in SROIQ(D), adds the 17 SWRL rules, and saves standard RDF/XML. The file `outputs/falcon.owl` opens in Protégé 5."""

S3_BUILD = r'''world = onto = None
with guarded("ontology build"):
    if OWL_AVAILABLE:
        import owlready2
        from falcon.ontology_builder import build_ontology, save
        world = owlready2.World()
        started = time.perf_counter()
        onto, build_report = build_ontology(kb, world=world, swrl="all")
        print("Built in %.2f s; asserted triples: %s" % (time.perf_counter() - started, orz.triple_count(world)))
        save(onto, "outputs/falcon.owl")
        display(pd.DataFrame([build_report.to_dict()]).T.rename(columns={0: "value"}))
    else:
        print("owlready2 or Java is missing, so the OWL sections are skipped.")
'''

S3_SHOW = r'''with guarded("ontology inspection"):
    if onto is not None:
        md("**3.1 Defined classes as owlready2 stores them**")
        for d in schema.DEFINED_CLASSES:
            print("%-28s \u2261 %s" % (d["name"], getattr(onto, d["name"]).equivalent_to[0]))
        md("**Property chains**")
        for name in ("triggersAllergen", "containsAllergen", "mayContain"):
            print("%-18s %s" % (name, list(getattr(onto, name).property_chain)))
        md("**3.2 One individual and its asserted facts**")
        p = onto.prod_steakhouse_sauce
        print("label         ", p.label[0])
        print("is_a          ", p.is_a)
        print("hasIngredient ", [i.label[0] for i in p.hasIngredient])
        print("hasLabelClaim ", [c.label[0] for c in p.hasLabelClaim])
        print("soldIn        ", [j.label[0] for j in p.soldIn])
        print("containsAllergen before reasoning:", list(p.containsAllergen))
        md("**3.3 SWRL rules loaded into the ontology** (as owlready2 stores them, matched to their catalogue IDs)")
        try:
            import re as _re
            signature = lambda text: tuple(sorted(_re.findall(r"([A-Za-z]+)\(", str(text))))
            catalogue = {signature(r["swrl"]): r["id"] for r in rules_catalog.SWRL_RULES}
            stored = sorted(onto.rules(), key=lambda rule: catalogue.get(signature(rule), "R99"))
            for rule in stored:
                print("  %s  %s" % (catalogue.get(signature(rule), "R??"), rule))
            print("%d SWRL rules stored in the ontology" % len(stored))
        except Exception:
            for r in rules_catalog.SWRL_RULES:
                print(" %s  %s" % (r["id"], r["swrl"]))
        md("**3.4 The first lines of falcon.owl (RDF/XML)**")
        print("".join(open("outputs/falcon.owl", encoding="utf-8").readlines()[:30]))
'''

S4_MD = """## 4. Reasoning with HermiT and Pellet

- **HermiT** checks the consistency of the OWL axioms and classifies them. It does not support SWRL built-ins, so it gets the 13 rules that have none.
- **Pellet** runs everything, including the four numeric threshold rules. Its inferred facts are saved separately from the asserted ones, in `outputs/falcon_inferred.owl`.
- If Pellet cannot run (it needs Java 25), HermiT supplies the inferred facts instead, without the four built-in rules, and every later section says which reasoner was used."""

S4_HERMIT = r'''with guarded("HermiT"):
    if OWL_AVAILABLE:
        hermit_world = owlready2.World()
        onto_h, _ = build_ontology(kb, world=hermit_world, swrl="no-builtins")
        hermit_run, _ = orz.run_reasoner(hermit_world, onto_h, "hermit")
        print("HermiT:", hermit_run.status, "in %.2f s" % hermit_run.seconds, hermit_run.message[:300])
        print("Unsatisfiable classes:", hermit_run.unsatisfiable_classes or "none")
'''

S4_PELLET = r'''after_facts = set()
with guarded("Pellet"):
    if onto is not None:
        before_facts = orz.extract_facts(onto)
        before_rows = orz.sparql_row_counts(world)
        pellet_run, inferred = orz.run_reasoner(world, onto, "pellet")
        print("Pellet:", pellet_run.status, "in %.2f s" % pellet_run.seconds, pellet_run.message[:400])
        if pellet_run.status == "consistent":
            owl_ok, MATERIALIZER, OWL_REASONER = True, "Pellet", "pellet"
with guarded("HermiT fallback"):
    if onto is not None and not owl_ok:
        print("Pellet could not run, so HermiT supplies the inferred facts (13 rules; built-in rules R14-R17 are skipped).")
        world = owlready2.World()
        onto, _ = build_ontology(kb, world=world, swrl="no-builtins")
        before_facts, before_rows = orz.extract_facts(onto), orz.sparql_row_counts(world)
        fallback_run, inferred = orz.run_reasoner(world, onto, "hermit")
        print("HermiT:", fallback_run.status, "in %.2f s" % fallback_run.seconds)
        if fallback_run.status == "consistent":
            owl_ok, MATERIALIZER, OWL_REASONER = True, "HermiT", "hermit"
with guarded("inferred facts"):
    if owl_ok:
        after_facts = orz.extract_facts(onto)
        new = sorted(after_facts - before_facts)
        inferred.save(file="outputs/falcon_inferred.owl", format="rdfxml")
        print("Facts inferred by %s:" % MATERIALIZER, len(new))
        sauce = [(pred, args) for pred, args in new if args[0] == "prod_steakhouse_sauce"]
        md("**What %s inferred about Smoky Steakhouse Sauce**" % MATERIALIZER)
        display(pd.DataFrame([{"inferred": pred, "value": kb.label(args[1]) if len(args) > 1 else "(class membership)"}
                              for pred, args in sauce]))
        counts = pd.DataFrame([{"question": k, "before reasoning": before_rows.get(k), "after reasoning": v}
                               for k, v in orz.sparql_row_counts(world).items()])
        md("**SPARQL answers before and after reasoning** (the asserted data alone answers almost nothing)")
        display(counts)
        ax = counts.set_index("question").plot.bar(figsize=(9, 3), color=["#C9CFD9", "#6C4BD8"], rot=0)
        ax.set_ylabel("rows returned")
        show(ax.figure)
'''

S4_CLASSIFY = r'''with guarded("OWL classification"):
    if owl_ok:
        names = set(competency.product_classes(kb))
        display(pd.DataFrame([{"product": kb.label(p), "classes inferred by %s" % MATERIALIZER: ", ".join(sorted(
            cls for (cls, args) in after_facts if len(args) == 1 and args[0] == p and cls in names))}
            for p in kb.products]))
'''

S5_MD = """## 5. Rule-based reasoning: forward and backward chaining

OWL reasoners report conclusions but not how they were reached, and they cannot express negation as failure. The FALCON engine (`falcon/rule_engine.py`) is a Datalog engine with stratified negation. It runs **the same 17 SWRL rules** plus:

- 39 engine rules for three-place relations, defeasible exemptions and closed-world verification;
- 10 integrity rules;
- a Horn translation of the OWL axioms.

It records the premises of every fact it derives, so it can explain each conclusion in either direction."""

S5_RULES = r'''rules = build_rules(kb)
print("Rules by source:", dict(pd.Series([r.source for r in rules]).value_counts()))
md("**5.1 The production rules, in first-order form** ('not' is negation as failure)")
pd.DataFrame([{"id": r.rule_id, "name": r.name, "kind": r.source, "rule": r.to_fol()}
              for r in rules if r.source in ("swrl", "engine", "integrity")])
'''

S5_SOURCE = r'''md("**5.2 How the engine works: stratification and semi-naive evaluation** (source excerpts)")
print(inspect.getsource(rule_engine.stratify))
print(inspect.getsource(rule_engine.ForwardChainer._fire))
'''

S5_FORWARD = r'''chainer, result = run_engine(kb, rules=rules)        # forward chaining (data-driven)
prover = make_prover(kb, rules)                       # backward chaining (goal-driven)
ctx = competency.EngineContext(kb, result, prover, rules)
md("**5.3 Forward chaining run**")
display(pd.DataFrame([result.summary()]).T.rename(columns={0: "value"}))
show(viz.fig_inference_profile(result))
'''

S5_TRACE = r'''md("**5.4 Step-by-step forward trace for Smoky Steakhouse Sauce** (first 60 lines)")
print("\n".join(reporting.focus_trace(result, kb, "prod_steakhouse_sauce").splitlines()[:60]))
'''

S5_BACKWARD = r'''md("**5.5 Backward chaining: proving goals from the facts up**")
goals = [
    ("Hidden fish inside a compound ingredient", Atom("containsAllergen", ("prod_steakhouse_sauce", "alg_fish"))),
    ("Why the vegan claim is false", Atom("contradictsClaim", ("prod_steakhouse_sauce", "claim_vegan"))),
    ("A positive safety verdict, via negation as failure", Atom("confirmedSafeFor", ("prod_tamari", "cons_liam"))),
    ("Exactly 10 ppm of sulphites in Canada", Atom("declarationDuty", ("prod_dried_apricots", "alg_sulphites", "jur_canada"))),
]
for title, goal in goals:
    proof = prover.prove(goal)
    print("=" * 100 + "\n" + title + "\n" + proof.render() + "\n")
show(viz.fig_proof_tree(kb, prover.prove(goals[1][1])))
'''

S5_WHYNOT = r'''md("**5.6 'Why not?': explaining a goal that cannot be proved**")
for goal in (Atom("confirmedSafeFor", ("prod_dark_chocolate", "cons_maya")),
             Atom("declarationDuty", ("prod_wheat_glucose_candy", "alg_wheat", "jur_eu")),
             Atom("declarationDuty", ("prod_dried_apricots", "alg_sulphites", "jur_eu"))):
    print("WHY NOT", goal)
    print("\n".join(prover.why_not(goal)[:4]), "\n")
'''

S5_AGREE = r'''# Do the two directions of reasoning agree? Prove every allergen fact the forward chainer derived.
facts = result.query("containsAllergen", None, None)
proved = sum(1 for p, a in facts if prover.prove(Atom("containsAllergen", (p, a))) is not None)
answers = {ans["a"] for ans, _ in prover.ask("containsAllergen(prod_pesto_genovese, ?a)")}
print("Backward chaining proved %d of %d forward-derived containsAllergen facts." % (proved, len(facts)))
print("Open query containsAllergen(pesto, ?a):", sorted(kb.label(a) for a in answers))
print("Same answers as forward chaining:", answers == {a for _, a in result.query("containsAllergen", "prod_pesto_genovese", None)})
'''

S6_MD = """## 6. Competency questions

There are 14 questions in all. The types are simple lookup (CQ01), complex reasoning (CQ02, CQ03, CQ09), personalised reasoning (CQ05), negation (CQ06), classification (CQ07, CQ12), jurisdictional reasoning (CQ08, CQ13), incomplete information (CQ10), numeric thresholds (CQ11) and a three-valued claim audit (CQ14).

Each question shows the rule engine's answer. Where SPARQL can express the question, it also shows the query run against the Pellet-materialized ontology."""

S6_CQS = r'''cq_answers = competency.answer_all(ctx)
display(pd.DataFrame([{"id": k, "question": a["question"], "type": a["kind"], "rows": len(a["rows"])}
                      for k, a in cq_answers.items()]))
for cq_id, a in cq_answers.items():
    md("### %s. %s\n*%s*%s" % (cq_id, a["question"], a["kind"], "\n\n> " + a["note"] if a.get("note") else ""))
    display(pd.DataFrame(a["rows"], columns=a["columns"]).head(12))
    if a.get("proof"):
        print(a["proof"])
    for product, reasons in (a.get("why_not") or {}).items():
        print("Why is %s not confirmed safe?\n%s\n" % (product, "\n".join(reasons)))
    if a.get("sparql"):
        md("SPARQL:\n```sparql\n%s\n```" % a["sparql"])
        if owl_ok:
            try:
                rows = orz.run_sparql(world, a["sparql"])
                print("%s-materialised ontology returned %d rows" % (MATERIALIZER, len(rows)))
                display(pd.DataFrame([[kb.label(v) if isinstance(v, str) else v for v in row] for row in rows]).head(8))
            except Exception as exc:
                print("owlready2's SPARQL engine does not support this query form:", exc)
'''

S7_MD = """## 7. Classifying new instances

A product the system has never seen is added and classified. The rule engine does this through its Horn rules. The OWL reasoner (Pellet, or HermiT if Pellet cannot run) does it through the OWL definitions, after a closure axiom states that the ingredient list is complete."""

S7_NEW = r'''new_product = competency.NEW_PRODUCT
print("New product:", new_product["label"], "| ingredients:", [kb.label(i) for i in new_product["ingredients"]],
      "| claims:", [kb.label(c) for c in new_product["claims"]], "| markets:", [kb.label(j) for j in new_product["sold_in"]])
display(pd.DataFrame(competency.cq12(ctx)["rows"]))
with guarded("OWL classification of the new product"):
    if OWL_AVAILABLE:
        owl_new = orz.cq12_classify_new_product(kb, OWL_REASONER)
        run = owl_new["reasoner"]
        print("%s: %s in %.2f s %s" % (MATERIALIZER or "Pellet", run["status"], run["seconds"], run.get("message", "")[:300]))
        rows = [{"aspect": k, "answer from the OWL reasoner": ", ".join(kb.label(v) for v in vals) or "(none)"}
                for k, vals in owl_new.items() if isinstance(vals, list)]
        if rows:
            display(pd.DataFrame(rows))
'''

S7_XRAY = r'''md("**Label X-ray: reasoning over a label pasted as free text**")
label = ("Corn syrup solids, coconut oil, sodium caseinate, dipotassium phosphate (E340), "
         "mono- and diglycerides (E471), natural flavouring")
parsed = app_logic.parse_label(kb, label, app_logic.build_lexicon(kb))
print("Recognised:", [kb.label(i) for i in parsed["ingredients"]], "| unknown:", parsed["unknown"])
xctx = app_logic.analyse_label(kb, rules, "Coffee whitener", parsed["ingredients"], ["claim_non_dairy"], ["jur_us"],
                               parsed["may_contain"], parsed["declared"], complete=not parsed["unknown"])
xs = app_logic.summarise(xctx, app_logic.CUSTOM_ID)
display(pd.DataFrame([{"allergen": e["allergen"], "via": ", ".join(e["via"]),
                       "hidden": "; ".join(h["chain"] for h in e["hidden"])} for e in xs["allergens"]]))
display(pd.DataFrame(xs["claims"]))
display(pd.DataFrame(xs["consumers"]))
'''

S8_MD = """## 8. Edge cases: incomplete information and conflicting data

- **EC1 Incomplete records.** Compares the open-world assumption, a naive closed-world assumption, and FALCON's local closed-world assumption, which closes the world only for records marked complete.
- **EC2 Closure axioms.** Shows how they let OWL classify vegan products.
- **EC3 and EC4 Conflicting data.** Covers false claims and an injected data error. OWL explodes; the engine isolates the problem.
- **EC5 Ambiguous sources.** For example, plain "lecithin".
- **EC6 Defeasible exemptions and thresholds.**
- **EC7 The exact 10 mg/kg boundary.**
- **EC8 Lexical traps.** Compares keyword screening with ontology reasoning."""

S8_EC1 = r'''ec = edge_cases.run_all(ctx)
md("**EC1: incomplete information under three assumptions**")
display(pd.DataFrame(ec["EC1"]["rows"]))
md("Where the naive closed-world assumption gives false assurances:")
display(pd.DataFrame(ec["EC1"]["false_assurances"]))
show(viz.fig_world_assumptions(ec))
'''

S8_EC2 = r'''md("**EC2: closure axioms (OWL)**. Without closure no product is VeganCompatible; with closure on complete records, the OWL reasoner can classify them.")
with guarded("EC2"):
    if OWL_AVAILABLE:
        ec2 = orz.ec2_closure_axioms(kb, result, OWL_REASONER)
        print("Reasoner:", MATERIALIZER or "Pellet")
        print("Open world  :", len(ec2["open"]["VeganCompatibleProduct"]), "VeganCompatibleProduct members")
        print("With closure:", len(ec2["closed"]["VeganCompatibleProduct"]), "members")
        print("Engine VerifiedVeganProduct:", len(ec2["engine_VerifiedVeganProduct"]), "| agreement:", ec2["agreement_with_engine"])
'''

S8_EC34 = r'''md("**EC3 and EC4: conflicting data.** The engine flags problems and keeps working:")
e3, e4 = ec["EC3"], ec["EC4"]
display(pd.DataFrame([
    {"experiment": "EC3: false claims kept as data",
     "engine result": "%d contradictions reported; %d derived facts and %d unsafe verdicts still available"
                      % (e3["contradictions"], e3["derived_facts_still_available"], e3["unsafe_verdicts_still_available"])},
    {"experiment": "EC4: " + e4["injected_error"],
     "engine result": "%d violation reported (%s); unsafe verdicts %d before, %d after"
                      % (len(e4["violations"]), "; ".join("%s: %s" % (v["entity"], v["violated axiom"]) for v in e4["violations"]),
                         e4["unsafe_verdicts_before"], e4["unsafe_verdicts_after"])}]))
print(e3["note"])
print(e4["note"])
with guarded("EC3/EC4 in OWL"):
    if OWL_AVAILABLE:
        print("OWL (%s), vegan claims asserted as axioms ->" % (MATERIALIZER or "Pellet"), orz.ec3_strict_claims(kb, OWL_REASONER)["reasoner"]["status"])
        print("OWL (%s), honey typed as plant-derived    ->" % (MATERIALIZER or "Pellet"), orz.ec4_disjointness_error(kb, OWL_REASONER)["reasoner"]["status"])
'''

S8_EC57 = r'''md("**EC5: ingredients of unstated origin**")
display(pd.DataFrame(ec["EC5"]["rows"]))
md("**EC6: where monotonic SWRL duties and the defeasible engine disagree**")
display(pd.DataFrame(ec["EC6"]["rows"]))
md("**EC7: the exact 10 mg/kg sulphite boundary**")
display(pd.DataFrame(ec["EC7"]["rows"]))
'''

S8_EC8 = r'''e8 = ec["EC8"]
print("Keyword screening vs ontology: precision %.2f, recall %.2f, F1 %.2f (%d false alarms, %d missed)" % (
    e8["precision"], e8["recall"], e8["f1"], e8["false_positives"], e8["false_negatives"]))
display(pd.DataFrame(e8["false_positive_examples"]))
display(pd.DataFrame(e8["false_negative_examples"]))
'''

S9_MD = """## 9. Consistency, completeness and cross-validation"""

S9_CHECK = r'''violations = result.query("integrityViolation", None, None) + result.query("disjointnessViolation", None, None)
print("Engine integrity violations in the curated data:", violations or "none")
with guarded("cross-validation"):
    if owl_ok:
        cv = pd.DataFrame(orz.cross_validate(result, after_facts, kb))
        print("%s vs engine: %d facts agree; %d of %d predicates identical" % (
            MATERIALIZER, cv["agree"].sum(), (cv["jaccard"] == 1).sum(), len(cv)))
        if MATERIALIZER == "HermiT":
            print("(HermiT has no SWRL built-ins, so the threshold classes from R14-R17 exist only on the engine side.)")
        display(cv[["predicate", "engine", "owl", "agree", "jaccard", "only_engine", "only_owl"]])
        ax = cv.set_index("predicate")["jaccard"].plot.barh(figsize=(8, 9), color="#2B7A9B")
        ax.set_xlabel("Jaccard agreement (1 = identical)")
        show(ax.figure)
'''

S9_TESTS = r'''import io, unittest
stream = io.StringIO()
outcome = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestLoader().discover("tests", top_level_dir="."))
print(stream.getvalue()[-2200:])
print("Tests run: %d, failures: %d, errors: %d" % (outcome.testsRun, len(outcome.failures), len(outcome.errors)))
'''

S10_MD = """## 10. Results"""

S10_RESULTS = r'''insights = reporting.insights(ctx, cq_answers, ec)
display(pd.DataFrame([{"finding": k, "value": v} for k, v in insights.items() if k not in ("allergen_prevalence", "consumer_outcomes")]))
show(viz.fig_claim_audit(kb, ctx))
show(viz.fig_product_graph(kb, ctx, "prod_steakhouse_sauce"))
show(viz.fig_product_graph(kb, ctx, "prod_pesto_genovese"))
show(viz.fig_consumer_matrix(kb, ctx))
display(pd.DataFrame(insights["consumer_outcomes"]).T)
'''

S11_MD = """## 11. Scalability

Synthetic knowledge bases are built by replicating the curated products, swapping one random ingredient in each copy. The engine is measured from 45 to 2,880 products. HermiT and Pellet are measured from 45 to 180 products. Their cost grows much faster than linearly (an uncapped HermiT run at 360 products took 789 s on Colab), so each reasoner run is capped at 150 seconds; once a reasoner hits the cap, larger sizes are skipped and recorded as a timeout. That cap is itself a result. A slope of 1 on the log-log plot means linear growth."""

S11_BENCH = r'''bench = {"engine": benchmark.engine_benchmark(kb, [1, 2, 4, 8, 16, 32, 64], repeats=2)}
bench["engine_slope"] = benchmark.fit_power_law([r["products"] for r in bench["engine"]], [r["seconds_min"] for r in bench["engine"]])
with guarded("OWL benchmark"):
    if OWL_AVAILABLE:
        bench["owl"] = benchmark.owl_benchmark(kb, [1, 2, 4], timeout=150)
        for name in ("hermit", "pellet"):
            ok = [r for r in bench["owl"] if r["reasoner"] == name and r["status"] == "consistent" and r["reasoning_seconds"] > 0]
            if len(ok) >= 2:
                bench["%s_slope" % name] = benchmark.fit_power_law([r["products"] for r in ok], [r["reasoning_seconds"] for r in ok])
json.dump(bench, open("outputs/benchmark.json", "w"), indent=2)
display(pd.DataFrame(bench["engine"]))
if bench.get("owl"):
    display(pd.DataFrame(bench["owl"]))
print({k: v for k, v in bench.items() if k.endswith("slope")})
show(viz.fig_scalability(bench))
'''

S12_MD = """## 12. Save every output (for the report, GitHub and the Streamlit app)

`run_all.py` writes the complete `outputs/` folder: the OWL files, traces, competency answers, edge cases, reasoner results, cross-validation and insights. `viz.py` then regenerates every figure in `docs/figures/`. The last cell downloads both folders as `falcon_results.zip`."""

S12_SAVE = r'''import run_all
run_all.main([])
viz.main()
'''

S12_ZIP = r'''import os, zipfile
with zipfile.ZipFile("falcon_results.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for folder in ("outputs", "docs/figures"):
        for root, _, names in os.walk(folder):
            for name in names:
                archive.write(os.path.join(root, name))
print("falcon_results.zip: %.1f MB in %s" % (os.path.getsize("falcon_results.zip") / 1e6, os.getcwd()))
if IN_COLAB:
    from google.colab import files
    files.download("falcon_results.zip")
'''

S13_MD = """## 13. Conclusions

**What the knowledge model reveals about the domain**
- **Market rules differ in ways a single checklist misses.** The differences cover pine nuts, mustard, celery, lupin, molluscs and the exact sulphite threshold. In the test portfolio, product–allergen pairs were treated differently by markets selling the same product (CQ08).
- **Hidden allergens arrive through derived and compound ingredients.** Examples are caseinate in "non-dairy" whitener, anchovy in Worcestershire sauce, egg-white lysozyme in cheese and tahini in hummus (CQ09). Keyword screening misses them and raises false alarms (EC8).
- **Common claims mislead.** "Non-dairy" allows milk protein, "lactose-free" is not milk-free, "gluten-free" is not wheat-free, and "dairy-free" next to "may contain milk" undermines itself (CQ03, CQ04, CQ14).
- **Missing data is a safety issue.** A naive closed-world reading gives false assurances. FALCON confirms safety only for complete records (EC1).

**Expressiveness versus complexity.** The ontology is in SROIQ(D), which is N2ExpTime-complete in the worst case but fast at this size. The engine is Datalog with stratified negation, which has polynomial data complexity and scales linearly in Section 11. Universal restrictions need a closed-world rule in the engine.

**Alternatives.** A Protégé-only build would lack tests and negation as failure. SHACL would suit integrity constraints. Knowledge-graph embeddings could rank likely missing "may contain" links for triage, but they replace proofs with scores.

**Next steps.** Load real product data, align with FoodOn, validate with SHACL at data entry, model cross-contact risk, and test embeddings as a triage tool.

The full discussion, with APA citations, is in the accompanying technical report."""


def md_cell(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text}


def code_cell(text, form=False):
    return {"cell_type": "code", "metadata": {"cellView": "form"} if form else {}, "execution_count": None,
            "outputs": [], "source": text}


def build(submission: bool) -> dict:
    cells = [
        md_cell(COVER_SUBMISSION if submission else COVER_PUBLIC), md_cell(INTRO),
        code_cell(UNPACK.replace("__PAYLOAD__", snapshot()), form=True), code_cell(INSTALL, form=True), code_cell(IMPORTS),
        md_cell(S1_MD), code_cell(S1_LOAD), code_cell(S1_PRODUCTS), code_cell(S1_MARKETS),
        md_cell(S2_MD), code_cell(S2_CONCEPT), code_cell(S2_CLASSES), code_cell(S2_PROPS), code_cell(S2_AXIOMS),
        md_cell(S3_MD), code_cell(S3_BUILD), code_cell(S3_SHOW),
        md_cell(S4_MD), code_cell(S4_HERMIT), code_cell(S4_PELLET), code_cell(S4_CLASSIFY),
        md_cell(S5_MD), code_cell(S5_RULES), code_cell(S5_SOURCE), code_cell(S5_FORWARD), code_cell(S5_TRACE),
        code_cell(S5_BACKWARD), code_cell(S5_WHYNOT), code_cell(S5_AGREE),
        md_cell(S6_MD), code_cell(S6_CQS),
        md_cell(S7_MD), code_cell(S7_NEW), code_cell(S7_XRAY),
        md_cell(S8_MD), code_cell(S8_EC1), code_cell(S8_EC2), code_cell(S8_EC34), code_cell(S8_EC57), code_cell(S8_EC8),
        md_cell(S9_MD), code_cell(S9_CHECK), code_cell(S9_TESTS),
        md_cell(S10_MD), code_cell(S10_RESULTS),
        md_cell(S11_MD), code_cell(S11_BENCH),
        md_cell(S12_MD), code_cell(S12_SAVE), code_cell(S12_ZIP),
        md_cell(S13_MD),
    ]
    return {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                         "language_info": {"name": "python"}, "colab": {"provenance": [], "toc_visible": True}},
            "nbformat": 4, "nbformat_minor": 5}


def main():
    parser = argparse.ArgumentParser(description="Build the FALCON notebook")
    parser.add_argument("--submission", metavar="PATH", help="also write the course version (cover page details) to PATH")
    args = parser.parse_args()
    public = ROOT / "notebooks" / "FALCON_Notebook.ipynb"
    public.write_text(json.dumps(build(False), indent=1), encoding="utf-8")
    print("wrote %s (%.0f KB)" % (public.relative_to(ROOT), public.stat().st_size / 1024))
    if args.submission:
        path = Path(args.submission)
        path.write_text(json.dumps(build(True), indent=1), encoding="utf-8")
        print("wrote %s (%.0f KB)" % (path, path.stat().st_size / 1024))


if __name__ == "__main__":
    main()
