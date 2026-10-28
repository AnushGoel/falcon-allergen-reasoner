"""
OWL reasoning with owlready2 (HermiT and Pellet), SPARQL answers to the
competency questions, the OWL half of the edge cases, and cross-validation
of Pellet's conclusions against the FALCON rule engine.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from . import schema
from .competency import CQS, NEW_PRODUCT, product_classes
from .config import INFERRED_IRI, JAVA_MEMORY_MB, SPARQL_PREFIX
from .ontology_builder import build_ontology

try:
    import owlready2 as owl
except ImportError:
    owl = None

COMPARED_PROPERTIES = ["containsAllergen", "mayContain", "triggersAllergen", "contradictsClaim",
                       "precautionaryConflictWith", "unsafeFor", "cautionFor", "unsuitableForDietOf",
                       "mustDeclare", "mustDeclareInUS", "mustDeclareInCanada", "mustDeclareInEU", "derivedFrom"]
COMPARED_INGREDIENT_CLASSES = ["AnimalDerivedIngredient", "NonVeganIngredient", "NonVegetarianIngredient",
                               "GlutenSourceIngredient", "LactoseSourceIngredient"]


def available() -> bool:
    return owl is not None


# ---------------------------------------------------------------------------
# Java
# ---------------------------------------------------------------------------

MIN_JAVA_FOR_PELLET = 25        # the Pellet bundled with owlready2 0.51+ is compiled for Java 25 (class file 69)


def java_major(path: str) -> int:
    """Major version of a Java runtime (8, 17, 21, 25 ...); 0 if it cannot be run."""
    try:
        out = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=30)
        match = re.search(r'version "(\d+)(?:\.(\d+))?', out.stderr or out.stdout)
        if not match:
            return 0
        major = int(match.group(1))
        return int(match.group(2) or 0) if major == 1 else major          # "1.8.0" means Java 8
    except Exception:
        return 0


def configure_java() -> dict:
    """Point owlready2 at a Java runtime; HermiT and Pellet are Java programs.

    FALCON_JAVA wins when set. Otherwise every runtime found (JAVA_HOME, PATH and
    the usual install folders) is checked and the newest one is used, because the
    Pellet bundled with recent owlready2 needs a recent Java.
    """
    info = {"java": None, "source": None, "version": None, "major": 0, "found": []}
    if owl is None:
        return info
    exe = "java.exe" if os.name == "nt" else "java"
    candidates = []
    if os.environ.get("FALCON_JAVA"):
        candidates.append(("FALCON_JAVA", os.environ["FALCON_JAVA"]))
    if os.environ.get("JAVA_HOME"):
        candidates.append(("JAVA_HOME", str(Path(os.environ["JAVA_HOME"]) / "bin" / exe)))
    on_path = shutil.which("java")
    if on_path:
        candidates.append(("PATH", on_path))
    roots = ([r"C:\Program Files\Eclipse Adoptium", r"C:\Program Files\Java", r"C:\Program Files\Microsoft",
              r"C:\Program Files\Amazon Corretto", r"C:\Program Files\Zulu"] if os.name == "nt"
             else ["/opt", "/usr/lib/jvm", "/Library/Java/JavaVirtualMachines"])
    for base in roots:
        root = Path(base)
        if root.exists():
            for pattern in ("*/bin/" + exe, "*/Contents/Home/bin/" + exe):
                candidates += [("search", str(p)) for p in sorted(root.glob(pattern))]
    found, seen = [], set()
    for source, path in candidates:
        if not path or not Path(path).exists():
            continue
        real = os.path.realpath(path)
        if real in seen:
            continue
        seen.add(real)
        found.append({"source": source, "java": path, "major": java_major(path)})
    info["found"] = [(f["major"], f["java"]) for f in found]
    explicit = [f for f in found if f["source"] == "FALCON_JAVA"]
    chosen = explicit[0] if explicit else (max(found, key=lambda f: f["major"]) if found else None)
    if chosen:
        owl.JAVA_EXE = chosen["java"]
        info.update(java=chosen["java"], source=chosen["source"], major=chosen["major"])
    try:
        owl.reasoning.JAVA_MEMORY = JAVA_MEMORY_MB
    except Exception:
        pass
    if info["java"]:
        try:
            out = subprocess.run([info["java"], "-version"], capture_output=True, text=True, timeout=30)
            info["version"] = (out.stderr or out.stdout).splitlines()[0].strip()
        except Exception as exc:
            info["version"] = "unknown (%s)" % exc
    return info


def explain_java_error(message: str) -> str:
    """Turn Java's class-version error into a plain instruction."""
    match = re.search(r"class file version (\d+)\.\d+\).*?up to (\d+)\.\d+", message, re.S)
    if not match:
        return message
    needed, running = int(match.group(1)) - 44, int(match.group(2)) - 44      # class file 69 = Java 25
    return ("This reasoner needs Java %d or newer, but Java %d is running. Install Java %d (for example Eclipse "
            "Temurin) or set FALCON_JAVA to its java executable. Original error: %s" % (needed, running, needed, message))


# ---------------------------------------------------------------------------
# Reasoning
# ---------------------------------------------------------------------------

@dataclass
class ReasonerRun:
    reasoner: str
    status: str                  # 'consistent', 'inconsistent' or 'error'
    seconds: float
    message: str = ""
    unsatisfiable_classes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        out = asdict(self)
        out["seconds"] = round(out["seconds"], 3)
        return out


def run_reasoner(world, onto, reasoner: str = "pellet", inferred_iri: str = INFERRED_IRI):
    """Run HermiT or Pellet; inferred facts go into a separate ontology so they can be saved apart."""
    inferred = world.get_ontology(inferred_iri)
    started = time.perf_counter()
    try:
        with inferred:
            if reasoner == "pellet":
                owl.sync_reasoner_pellet([onto], infer_property_values=True, infer_data_property_values=True, debug=0)
            else:
                hermit = getattr(owl, "sync_reasoner_hermit", owl.sync_reasoner)
                try:
                    hermit([onto], infer_property_values=True, debug=0, ignore_unsupported_datatypes=True)
                except TypeError:
                    hermit([onto], infer_property_values=True, debug=0)
        seconds = time.perf_counter() - started
        unsat = [c.name for c in world.inconsistent_classes()]
        return ReasonerRun(reasoner, "consistent", seconds, unsatisfiable_classes=unsat), inferred
    except owl.OwlReadyInconsistentOntologyError as exc:
        return ReasonerRun(reasoner, "inconsistent", time.perf_counter() - started, str(exc)[:500]), inferred
    except Exception as exc:
        message = explain_java_error("%s: %s" % (type(exc).__name__, str(exc)[:500]))
        return ReasonerRun(reasoner, "error", time.perf_counter() - started, message), inferred


def extract_facts(onto) -> Set[Tuple[str, Tuple]]:
    """Class memberships and property values, as engine-style facts, for every individual."""
    facts = set()
    base = onto.base_iri
    for individual in onto.individuals():
        name = individual.name
        for cls in individual.INDIRECT_is_a:
            if isinstance(cls, owl.ThingClass) and cls.iri.startswith(base):
                facts.add((cls.name, (name,)))
        for prop in COMPARED_PROPERTIES:
            for value in getattr(individual, prop, []) or []:
                if hasattr(value, "name"):
                    facts.add((prop, (name, value.name)))
    return facts


def triple_count(world) -> Optional[int]:
    try:
        return int(list(world.sparql("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o . }"))[0][0])
    except Exception:
        return None


def run_sparql(world, query: str) -> List[list]:
    rows = []
    for row in world.sparql(SPARQL_PREFIX + query):
        rows.append([getattr(v, "name", v) for v in row])
    return rows


def sparql_answers(world, kb) -> Dict[str, dict]:
    answers = {}
    for cq in CQS:
        if not cq.sparql:
            continue
        try:
            rows = run_sparql(world, cq.sparql)
            labelled = [[kb.label(v) if isinstance(v, str) else v for v in row] for row in rows]
            answers[cq.cq_id] = {"status": "ok", "rows": len(rows), "sample": labelled[:12]}
        except Exception as exc:
            answers[cq.cq_id] = {"status": "error", "message": "%s: %s" % (type(exc).__name__, str(exc)[:300])}
    return answers


def before_after_reasoning_counts(world_before_rows: Dict[str, int], world_after_rows: Dict[str, int]) -> List[dict]:
    rows = []
    for cq_id in sorted(world_after_rows):
        rows.append({"cq": cq_id, "rows before reasoning": world_before_rows.get(cq_id), "rows after reasoning": world_after_rows[cq_id]})
    return rows


def sparql_row_counts(world) -> Dict[str, int]:
    counts = {}
    for cq in CQS:
        if cq.sparql:
            try:
                counts[cq.cq_id] = len(run_sparql(world, cq.sparql))
            except Exception:
                counts[cq.cq_id] = None
    return counts


# ---------------------------------------------------------------------------
# Cross-validation: OWL reasoner (Pellet, or HermiT as fallback) vs the FALCON engine
# ---------------------------------------------------------------------------

def cross_validate(engine_result, owl_facts, kb) -> List[dict]:
    predicates = COMPARED_PROPERTIES + product_classes(kb) + COMPARED_INGREDIENT_CLASSES
    rows = []
    for pred in predicates:
        if pred == "VeganCompatibleProduct":       # needs closure axioms in OWL; compared in EC2 instead
            continue
        engine = {args for (_, args) in engine_result.store.facts(pred)}
        reasoner = {args for (p, args) in owl_facts if p == pred}
        union = engine | reasoner
        rows.append({"predicate": pred, "engine": len(engine), "owl": len(reasoner), "agree": len(engine & reasoner),
                     "jaccard": round(len(engine & reasoner) / len(union), 3) if union else 1.0,
                     "only_engine": [list(a) for a in sorted(engine - reasoner)][:8],
                     "only_owl": [list(a) for a in sorted(reasoner - engine)][:8]})
    return rows


# ---------------------------------------------------------------------------
# OWL edge cases
# ---------------------------------------------------------------------------

def _rules_for(reasoner: str) -> str:
    return "all" if reasoner == "pellet" else "no-builtins"


def ec2_closure_axioms(kb, engine_result, reasoner: str = "pellet") -> dict:
    """Without closure no product is VeganCompatible; with closure on complete records the reasoner agrees with the engine."""
    out = {"reasoner_used": reasoner}
    for closed in (False, True):
        world = owl.World()
        onto, _ = build_ontology(kb, world=world, swrl=_rules_for(reasoner))
        if closed:
            for p in kb.products.values():
                if p["status"] == "complete" and p["ingredients"]:
                    owl.close_world(getattr(onto, p["id"]), Properties=[onto.hasIngredient])
            for i in kb.ingredients.values():
                if "CompoundIngredient" in i["classes"]:
                    owl.close_world(getattr(onto, i["id"]), Properties=[onto.hasComponent])
        run, _ = run_reasoner(world, onto, reasoner)
        members = sorted(x.name for x in onto.VeganCompatibleProduct.instances()) if run.status == "consistent" else []
        out["closed" if closed else "open"] = {"reasoner": run.to_dict(), "VeganCompatibleProduct": members}
    engine = sorted(p for (p,) in engine_result.query("VerifiedVeganProduct", None))
    closed_members = set(out["closed"]["VeganCompatibleProduct"])
    out["engine_VerifiedVeganProduct"] = engine
    out["agreement_with_engine"] = {"both": len(closed_members & set(engine)),
                                    "only_owl": sorted(closed_members - set(engine)),
                                    "only_engine": sorted(set(engine) - closed_members)}
    return out


def ec3_strict_claims(kb, reasoner: str = "pellet") -> dict:
    world = owl.World()
    onto, _ = build_ontology(kb, world=world, swrl=_rules_for(reasoner), strict_claims=True)
    run, _ = run_reasoner(world, onto, reasoner)
    return {"reasoner": run.to_dict(), "reasoner_used": reasoner,
            "explanation": "VeganLabelledProduct is declared disjoint from NonVeganProduct. Products such as Smoky "
                           "Steakhouse Sauce are both, so no model exists and every query becomes meaningless."}


def ec4_disjointness_error(kb, reasoner: str = "pellet") -> dict:
    world = owl.World()
    onto, _ = build_ontology(kb, world=world, swrl=_rules_for(reasoner))
    onto.ing_honey.is_a.append(onto.PlantDerivedIngredient)
    run, _ = run_reasoner(world, onto, reasoner)
    return {"reasoner": run.to_dict(), "reasoner_used": reasoner, "injected_error": "ing_honey typed as PlantDerivedIngredient as well as BeeProduct"}


def cq12_classify_new_product(kb, reasoner: str = "pellet") -> dict:
    kb2 = kb.copy()
    kb2.add_product(NEW_PRODUCT)
    world = owl.World()
    onto, _ = build_ontology(kb2, world=world, swrl=_rules_for(reasoner))
    product = getattr(onto, NEW_PRODUCT["id"])
    owl.close_world(product, Properties=[onto.hasIngredient])
    run, _ = run_reasoner(world, onto, reasoner)
    if run.status != "consistent":
        return {"reasoner": run.to_dict(), "reasoner_used": reasoner}
    classes = sorted(c.name for c in product.INDIRECT_is_a
                     if isinstance(c, owl.ThingClass) and c.iri.startswith(onto.base_iri) and c.name != "Product")
    return {"reasoner": run.to_dict(), "reasoner_used": reasoner, "inferred_classes": classes,
            "containsAllergen": sorted(a.name for a in product.containsAllergen),
            "contradictsClaim": sorted(c.name for c in product.contradictsClaim),
            "mustDeclareInEU": sorted(a.name for a in product.mustDeclareInEU),
            "mustDeclareInCanada": sorted(a.name for a in product.mustDeclareInCanada)}
