"""
Build the FALCON OWL 2 ontology with owlready2.

The builder reads schema.py (classes, properties, axioms) and the curated
knowledge base (individuals), then adds the SWRL rules from rules_catalog.py.
The result is a standard RDF/XML .owl file that opens in Protégé 5.

Expressivity: the axioms used here (intersection, union, complement,
existential and universal restrictions, a role hierarchy, transitive and
inverse roles, nominals via hasValue/OneOf, qualified cardinality, property
chains and datatypes) place the ontology in SROIQ(D), i.e. full OWL 2 DL.
"""
from __future__ import annotations

import types
from dataclasses import asdict, dataclass, field
from typing import List, Optional

from . import rules_catalog, schema
from .config import ONTOLOGY_IRI

try:
    import owlready2 as owl
except ImportError:          # the engine-only pipeline does not need owlready2
    owl = None

PY_TYPES = {"str": str, "float": float, "int": int, "bool": bool}


@dataclass
class BuildReport:
    classes: int = 0
    defined_classes: int = 0
    object_properties: int = 0
    data_properties: int = 0
    annotation_properties: int = 0
    individuals: int = 0
    property_chains: int = 0
    general_class_axioms: int = 0
    restrictions: int = 0
    disjointness_axioms: int = 0
    swrl_rules: int = 0
    swrl_fallbacks: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def require_owlready2() -> None:
    if owl is None:
        raise ImportError("owlready2 is not installed. Run:  pip install owlready2")


def _humanise(name: str) -> str:
    out = []
    for ch in name:
        if ch.isupper() and out and not out[-1].isupper():
            out.append(" ")
        out.append(ch)
    return "".join(out)


def build_ontology(kb, world=None, iri: str = ONTOLOGY_IRI, swrl: str = "all",
                   strict_claims: bool = False):
    """Create the ontology in ``world`` (a fresh owlready2 World if omitted).

    swrl:          'all' (Pellet), 'no-builtins' (safe for HermiT) or 'none'.
    strict_claims: also assert vegan claims as axioms (edge case EC3).
    Returns (ontology, BuildReport).
    """
    require_owlready2()
    world = world if world is not None else owl.World()
    onto = world.get_ontology(iri)
    report = BuildReport()
    with onto:
        _annotation_properties(report)
        _classes(onto, report)
        _properties(onto, report)
        _property_chains(onto, report)
        _defined_classes(onto, report)
        _general_class_axioms(onto, report)
        _restrictions(onto, report)
        _disjointness(onto, report)
        made = _individuals(onto, kb, report)
        _late_axioms(onto, kb, made, report)
        if swrl != "none":
            _swrl_rules(report, allow_builtins=(swrl == "all"))
        if strict_claims:
            _strict_claim_axioms(onto)
        _metadata(onto, kb)
    return onto, report


# ---------------------------------------------------------------------------
# TBox and RBox
# ---------------------------------------------------------------------------

def _get(onto, name):
    entity = getattr(onto, name)
    if entity is None:
        raise KeyError("Entity %s is not defined in the ontology" % name)
    return entity


def _annotation_properties(report):
    for name in schema.ANNOTATION_PROPERTIES:
        types.new_class(name, (owl.AnnotationProperty,))
        report.annotation_properties += 1


def _classes(onto, report):
    for name, parents, comment in schema.CLASSES:       # listed parents-first
        bases = tuple(_get(onto, p) for p in parents) or (owl.Thing,)
        cls = types.new_class(name, bases)
        cls.label = [_humanise(name)]
        if comment:
            cls.comment = [comment]
        report.classes += 1


def _properties(onto, report):
    pending_inverse = []
    # create parent properties before their sub-properties
    ordered = sorted(schema.OBJECT_PROPERTIES.items(), key=lambda item: 1 if item[1].get("parent") else 0)
    for name, spec in ordered:
        bases = [_get(onto, spec["parent"])] if spec.get("parent") else [owl.ObjectProperty]
        if "transitive" in spec.get("characteristics", []):
            bases.append(owl.TransitiveProperty)
        prop = types.new_class(name, tuple(bases))
        prop.domain = [_get(onto, c) for c in spec["domain"]]
        prop.range = [_get(onto, c) for c in spec["range"]]
        if spec.get("comment"):
            prop.comment = [spec["comment"]]
        if spec.get("inverse"):
            pending_inverse.append((prop, spec["inverse"]))
        report.object_properties += 1
    for prop, inverse in pending_inverse:
        prop.inverse_property = _get(onto, inverse)
    for name, spec in schema.DATA_PROPERTIES.items():
        bases = [owl.DataProperty] + ([owl.FunctionalProperty] if spec.get("functional") else [])
        prop = types.new_class(name, tuple(bases))
        prop.domain = [_get(onto, c) for c in spec["domain"]]
        prop.range = [PY_TYPES[spec["range"]]]
        if spec.get("comment"):
            prop.comment = [spec["comment"]]
        report.data_properties += 1


def _property_chains(onto, report):
    for chain in schema.PROPERTY_CHAINS:
        target = _get(onto, chain["super"])
        try:
            target.property_chain.append(owl.PropertyChain([_get(onto, p) for p in chain["chain"]]))
            report.property_chains += 1
        except Exception as exc:  # older owlready2 versions: express the chain as a SWRL rule instead
            p1, p2 = chain["chain"]
            report.swrl_fallbacks.append("%s(?x, ?y), %s(?y, ?z) -> %s(?x, ?z)" % (p1, p2, chain["super"]))
            report.warnings.append("Property chain %s used a SWRL fallback (%s)" % ("o".join(chain["chain"]), exc))


def _defined_classes(onto, report):
    for d in schema.DEFINED_CLASSES:
        cls = types.new_class(d["name"], tuple(_get(onto, p) for p in d["parents"]))
        cls.label = [_humanise(d["name"])]
        if d.get("comment"):
            cls.comment = [d["comment"]]
        report.defined_classes += 1
    for d in schema.DEFINED_CLASSES:                    # second pass: definitions may refer to each other
        _get(onto, d["name"]).equivalent_to.append(d["owl"](onto))


def _general_class_axioms(onto, report):
    for gci in schema.GCIS:
        try:
            axiom = owl.GeneralClassAxiom(gci["left"](onto))
            axiom.is_a.append(_get(onto, gci["right"]))
            report.general_class_axioms += 1
        except Exception as exc:
            report.swrl_fallbacks.append(gci["horn"])
            report.warnings.append("General class axiom for %s used a SWRL fallback (%s)" % (gci["right"], exc))


def _restrictions(onto, report):
    for r in schema.RESTRICTIONS:
        _get(onto, r["cls"]).is_a.append(r["owl"](onto))
        report.restrictions += 1


def _disjointness(onto, report):
    for group in schema.DISJOINT_GROUPS:
        owl.AllDisjoint([_get(onto, name) for name in group])
        report.disjointness_axioms += 1


# ---------------------------------------------------------------------------
# ABox
# ---------------------------------------------------------------------------

def _individuals(onto, kb, report):
    made = {}

    def make(entity_id, class_names, label):
        classes = [_get(onto, c) for c in class_names]
        individual = classes[0](entity_id)
        for extra in classes[1:]:
            individual.is_a.append(extra)
        individual.label = [label]
        made[entity_id] = individual
        return individual

    for a in kb.allergens.values():
        make(a["id"], ["AllergenCategory" if a["kind"] == "category" else "SpecificAllergen"], a["label"])
    for j in kb.jurisdictions.values():
        make(j["id"], [j["class"]], j["label"]).regulatoryBasis = [j["regulatory_basis"]]
    for c in kb.claims.values():
        claim = make(c["id"], [c["class"]], c["label"])
        if c.get("note"):
            claim.curatorNote = [c["note"]]
    for c in kb.categories.values():
        make(c["id"], ["ProductCategory"], c["label"])
    for u in kb.consumers.values():
        make(u["id"], u["classes"], u["label"])
    for i in kb.ingredients.values():
        ingredient = make(i["id"], i["classes"], i["label"])
        if i["synonyms"]:
            ingredient.synonym = list(i["synonyms"])
        if i.get("note"):
            ingredient.curatorNote = [i["note"]]
    for p in kb.products.values():
        product = make(p["id"], ["Product"], p["label"])
        if p.get("scenario"):
            product.scenarioNote = [p["scenario"]]
    for e in kb.exemptions.values():
        make(e["id"], ["DeclarationExemption"], e["id"]).regulatoryBasis = [e["basis"]]
    report.individuals = len(made)

    def refs(ids):
        return [made[x] for x in ids]

    for a in kb.allergens.values():
        if a.get("parent"):
            made[a["id"]].isSubtypeOf = refs([a["parent"]])
    for j in kb.jurisdictions.values():
        made[j["id"]].requiresDeclarationOf = refs(j["requires_declaration_of"])
    for c in kb.claims.values():
        if c["excludes"]:
            made[c["id"]].excludesAllergen = refs(c["excludes"])
    for u in kb.consumers.values():
        if u["must_avoid"]:
            made[u["id"]].mustAvoid = refs(u["must_avoid"])
    for i in kb.ingredients.values():
        ingredient = made[i["id"]]
        if i["retains"]:
            ingredient.retainsAllergensOf = refs(i["retains"])
        if i["derived_from"]:
            ingredient.derivedFrom = refs(i["derived_from"])
        if i["components"]:
            ingredient.hasComponent = refs(i["components"])
        if i["triggers"]:
            ingredient.triggersAllergen = refs(i["triggers"])
        if i["possibly_triggers"]:
            ingredient.possiblyTriggers = refs(i["possibly_triggers"])
    for p in kb.products.values():
        product = made[p["id"]]
        product.hasBarcode = p["barcode"]
        product.hasIngredientListStatus = p["status"]
        if p["ingredients"]:
            product.hasIngredient = refs(p["ingredients"])
        if p["claims"]:
            product.hasLabelClaim = refs(p["claims"])
        if p["may_contain"]:
            product.mayContain = refs(p["may_contain"])
        if p["declared"]:
            product.declaresAllergen = refs(p["declared"])
        if p["sold_in"]:
            product.soldIn = refs(p["sold_in"])
        if p.get("category"):
            product.inCategory = refs([p["category"]])
        if p.get("gluten_ppm") is not None:
            product.hasGlutenPPM = float(p["gluten_ppm"])
        if p.get("sulphite_mg_per_kg") is not None:
            product.hasSulphiteMgPerKg = float(p["sulphite_mg_per_kg"])
    for e in kb.exemptions.values():
        exemption = made[e["id"]]
        exemption.exemptIngredient = refs([e["ingredient"]])
        exemption.exemptAllergen = refs([e["allergen"]])
        exemption.exemptJurisdiction = refs([e["jurisdiction"]])

    # OWL has no unique name assumption. Cardinality reasoning (MultiMarketProduct,
    # 'max 1 category') needs to know that these individuals are distinct.
    for table in (kb.allergens, kb.jurisdictions, kb.claims, kb.categories, kb.consumers):
        if len(table) > 1:
            owl.AllDifferent(refs(list(table)))
    return made


def _late_axioms(onto, kb, made, report):
    """Axioms that mention individuals, so they can only be added after the ABox."""
    for h in schema.HAS_VALUE_AXIOMS:
        _get(onto, h["cls"]).is_a.append(_get(onto, h["prop"]).value(made[h["value"]]))
        report.restrictions += 1
    for a in kb.allergens.values():
        name = a.get("product_class")
        if not name:
            continue
        cls = types.new_class(name, (onto.Product,))
        cls.label = [_humanise(name)]
        cls.equivalent_to.append(onto.Product & onto.containsAllergen.value(made[a["id"]]))
        report.defined_classes += 1


def _swrl_rules(report, allow_builtins: bool):
    rules = [(r["id"], r["name"], r["swrl"]) for r in rules_catalog.SWRL_RULES
             if allow_builtins or not r.get("builtins")]
    rules += [("FB%02d" % k, "fallback", text) for k, text in enumerate(report.swrl_fallbacks, 1)]
    for rule_id, name, text in rules:
        try:
            imp = owl.Imp()
            imp.set_as_rule(text)
            try:
                imp.label = ["%s %s" % (rule_id, name)]
            except Exception:
                pass
            report.swrl_rules += 1
        except Exception as exc:
            report.warnings.append("SWRL rule %s could not be loaded: %s" % (rule_id, exc))


def _strict_claim_axioms(onto):
    """EC3: treat 'vegan' labels as axioms instead of data."""
    strict = types.new_class("VeganLabelledProduct", (onto.Product,))
    strict.equivalent_to.append(onto.Product & onto.hasLabelClaim.some(onto.VeganClaim))
    strict.is_a.append(owl.Not(onto.NonVeganProduct))


def _metadata(onto, kb):
    try:
        onto.metadata.comment.append(
            "FALCON: Food Allergen and Label COmpliance ONtology. %d products, %d ingredients, %d allergens, "
            "3 jurisdictions (US, Canada, EU)." % (len(kb.products), len(kb.ingredients), len(kb.allergens)))
    except Exception:
        pass


def save(onto, path) -> None:
    onto.save(file=str(path), format="rdfxml")
