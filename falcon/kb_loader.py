"""
Load and validate the curated JSON knowledge base.

Validation is strict on purpose: a dangling reference (an ingredient that
names an allergen that does not exist) would silently weaken every
inference built on it, so the loader reports it before anything runs.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import schema
from .config import DATA_DIR

INGREDIENT_LISTS = ("classes", "triggers", "retains", "derived_from", "components", "possibly_triggers", "synonyms")
PRODUCT_LISTS = ("ingredients", "claims", "may_contain", "declared", "sold_in")


@dataclass
class KnowledgeBase:
    allergens: Dict[str, dict]
    jurisdictions: Dict[str, dict]
    claims: Dict[str, dict]
    categories: Dict[str, dict]
    consumers: Dict[str, dict]
    exemptions: Dict[str, dict]
    ingredients: Dict[str, dict]
    products: Dict[str, dict]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def label(self, entity_id) -> str:
        for table in (self.products, self.ingredients, self.allergens, self.claims,
                      self.jurisdictions, self.consumers, self.categories, self.exemptions):
            if entity_id in table:
                return table[entity_id].get("label", entity_id)
        return str(entity_id)

    def copy(self) -> "KnowledgeBase":
        return copy.deepcopy(self)

    def add_product(self, product: dict) -> None:
        self.products[product["id"]] = _normalise_product(dict(product), len(self.products) + 1)

    def summary(self) -> dict:
        return {
            "products": len(self.products),
            "ingredients": len(self.ingredients),
            "allergens": len(self.allergens),
            "jurisdictions": len(self.jurisdictions),
            "label_claims": len(self.claims),
            "categories": len(self.categories),
            "consumers": len(self.consumers),
            "exemptions": len(self.exemptions),
            "compound_ingredients": sum(1 for i in self.ingredients.values() if "CompoundIngredient" in i["classes"]),
            "products_with_claims": sum(1 for p in self.products.values() if p["claims"]),
            "incomplete_records": sum(1 for p in self.products.values() if p["status"] != "complete"),
        }


def _read(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _index(items: List[dict], kind: str, errors: List[str]) -> Dict[str, dict]:
    table: Dict[str, dict] = {}
    for item in items:
        if item["id"] in table:
            errors.append("Duplicate %s id: %s" % (kind, item["id"]))
        table[item["id"]] = item
    return table


def _normalise_product(p: dict, number: int) -> dict:
    for key in PRODUCT_LISTS:
        p[key] = list(p.get(key) or [])
    p.setdefault("status", "complete")
    p.setdefault("gluten_ppm", None)
    p.setdefault("sulphite_mg_per_kg", None)
    p.setdefault("barcode", "FALCON-%04d" % number)
    p.setdefault("category", None)
    p.setdefault("scenario", "")
    return p


def load_kb(data_dir: Optional[Path] = None) -> KnowledgeBase:
    data_dir = Path(data_dir or DATA_DIR)
    errors: List[str] = []
    allergens = _index(_read(data_dir / "allergens.json")["allergens"], "allergen", errors)
    jurisdictions = _index(_read(data_dir / "jurisdictions.json")["jurisdictions"], "jurisdiction", errors)
    reference = _read(data_dir / "reference.json")
    claims = _index(reference["claims"], "claim", errors)
    categories = _index(reference["categories"], "category", errors)
    consumers = _index(reference["consumers"], "consumer", errors)
    exemptions = _index(reference["exemptions"], "exemption", errors)
    ingredients = _index(_read(data_dir / "ingredients.json")["ingredients"], "ingredient", errors)
    products = _index(_read(data_dir / "products.json")["products"], "product", errors)

    for item in ingredients.values():
        for key in INGREDIENT_LISTS:
            item[key] = list(item.get(key) or [])
    for number, item in enumerate(products.values(), 1):
        _normalise_product(item, number)

    kb = KnowledgeBase(allergens, jurisdictions, claims, categories, consumers, exemptions, ingredients, products, errors)
    validate(kb)
    return kb


def validate(kb: KnowledgeBase) -> None:
    """Referential integrity, schema conformance and acyclic derivations."""
    err, warn = kb.errors, kb.warnings
    known_classes = set(schema.class_names())
    all_ids: Dict[str, str] = {}
    for kind, table in (("allergen", kb.allergens), ("jurisdiction", kb.jurisdictions), ("claim", kb.claims),
                        ("category", kb.categories), ("consumer", kb.consumers), ("exemption", kb.exemptions),
                        ("ingredient", kb.ingredients), ("product", kb.products)):
        for entity_id in table:
            if entity_id in all_ids:
                err.append("Id %s is used for both a %s and a %s" % (entity_id, all_ids[entity_id], kind))
            all_ids[entity_id] = kind

    def need(ids, table, what, owner):
        for x in ids:
            if x not in table:
                err.append("%s refers to unknown %s '%s'" % (owner, what, x))

    for a in kb.allergens.values():
        if a.get("parent") and a["parent"] not in kb.allergens:
            err.append("Allergen %s has unknown parent %s" % (a["id"], a["parent"]))
        if a.get("kind") not in ("category", "specific"):
            err.append("Allergen %s has invalid kind %r" % (a["id"], a.get("kind")))
    for j in kb.jurisdictions.values():
        if j["class"] not in known_classes:
            err.append("Jurisdiction %s uses unknown class %s" % (j["id"], j["class"]))
        need(j["requires_declaration_of"], kb.allergens, "allergen", j["id"])
    for c in kb.claims.values():
        if c["class"] not in known_classes:
            err.append("Claim %s uses unknown class %s" % (c["id"], c["class"]))
        need(c["excludes"], kb.allergens, "allergen", c["id"])
    for u in kb.consumers.values():
        for cls in u["classes"]:
            if cls not in known_classes:
                err.append("Consumer %s uses unknown class %s" % (u["id"], cls))
        need(u["must_avoid"], kb.allergens, "allergen", u["id"])
    for e in kb.exemptions.values():
        need([e["ingredient"]], kb.ingredients, "ingredient", e["id"])
        need([e["allergen"]], kb.allergens, "allergen", e["id"])
        need([e["jurisdiction"]], kb.jurisdictions, "jurisdiction", e["id"])
    for i in kb.ingredients.values():
        if not i["classes"]:
            err.append("Ingredient %s has no class" % i["id"])
        for cls in i["classes"]:
            if cls not in known_classes:
                err.append("Ingredient %s uses unknown class %s" % (i["id"], cls))
        for key in ("retains", "derived_from", "components"):
            need(i[key], kb.ingredients, "ingredient", i["id"])
        need(i["triggers"] + i["possibly_triggers"], kb.allergens, "allergen", i["id"])
        if "CompoundIngredient" in i["classes"] and not i["components"]:
            warn.append("Compound ingredient %s lists no components" % i["id"])
    for p in kb.products.values():
        need(p["ingredients"], kb.ingredients, "ingredient", p["id"])
        need(p["claims"], kb.claims, "claim", p["id"])
        need(p["may_contain"] + p["declared"], kb.allergens, "allergen", p["id"])
        need(p["sold_in"], kb.jurisdictions, "jurisdiction", p["id"])
        if p["category"] and p["category"] not in kb.categories:
            err.append("Product %s has unknown category %s" % (p["id"], p["category"]))
        if p["status"] not in ("complete", "incomplete"):
            err.append("Product %s has invalid status %r" % (p["id"], p["status"]))
        if p["status"] == "complete" and not p["ingredients"]:
            warn.append("Product %s is marked complete but lists no ingredients" % p["id"])

    # Derivations and compositions must be acyclic, otherwise 'retains' would be meaningless.
    graph = {i["id"]: i["retains"] + i["derived_from"] + i["components"] for i in kb.ingredients.values()}
    state: Dict[str, int] = {}

    def visit(node, path):
        state[node] = 1
        for nxt in graph.get(node, []):
            if state.get(nxt) == 1:
                err.append("Cycle in ingredient derivation: %s" % " -> ".join(path + [nxt]))
            elif state.get(nxt) is None:
                visit(nxt, path + [nxt])
        state[node] = 2

    for node in graph:
        if node not in state:
            visit(node, [node])
