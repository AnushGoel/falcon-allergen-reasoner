"""
FALCON schema: the terminological part of the knowledge base.

Everything the ontology says *about classes and properties* lives here, in
plain Python data. Two consumers read it:

* ``ontology_builder`` turns it into OWL 2 axioms with owlready2;
* ``engine_bridge`` turns the Horn-expressible part into rules for the
  FALCON rule engine.

Keeping one specification means the OWL reasoner and the rule engine cannot
silently drift apart, which is what makes the cross-validation in
``crossval.py`` meaningful. Where an OWL axiom has no Horn equivalent (for
example a universal restriction), the entry says so and the engine uses an
explicitly closed-world rule instead.

OWL class expressions are written as small lambdas that receive the
owlready2 ontology ``o`` and return the expression. They are only evaluated
by the builder, so this module does not import owlready2.
"""

# ---------------------------------------------------------------------------
# Classes: (name, [parents], comment)
# ---------------------------------------------------------------------------
CLASSES = [
    ("FoodEntity", [], "Anything that appears on a food label: finished products and the ingredients in them."),
    ("Product", ["FoodEntity"], "A packaged food product as offered to consumers."),
    ("Ingredient", ["FoodEntity"],
     "An ingredient kind such as whey or tahini. Kinds are individuals, not classes, so that SWRL rules "
     "(which only bind named individuals) can reason about them."),

    # origin hierarchy
    ("PlantDerivedIngredient", ["Ingredient"], "Ingredient obtained from plants."),
    ("CerealIngredient", ["PlantDerivedIngredient"], "Cereal grains and products made from them."),
    ("LegumeIngredient", ["PlantDerivedIngredient"], "Legumes such as soy, peanut, lupin, pea and chickpea."),
    ("TreeNutIngredient", ["PlantDerivedIngredient"], "Tree nuts and nut products."),
    ("SeedIngredient", ["PlantDerivedIngredient"], "Seeds such as sesame, mustard and sunflower."),
    ("VegetableIngredient", ["PlantDerivedIngredient"], "Vegetables."),
    ("FruitIngredient", ["PlantDerivedIngredient"], "Fruits and fruit-derived ingredients."),
    ("PlantOilOrFat", ["PlantDerivedIngredient"], "Vegetable oils and fats."),
    ("SugarOrSweetener", ["PlantDerivedIngredient"], "Sugars and syrups."),
    ("HerbOrSpice", ["PlantDerivedIngredient"], "Herbs, spices and extracts."),
    ("CocoaIngredient", ["PlantDerivedIngredient"], "Cocoa mass, powder and butter."),

    ("AnimalDerivedIngredient", ["Ingredient"], "Ingredient obtained from animals."),
    ("VegetarianIncompatibleIngredient", ["Ingredient"],
     "Ingredient vegetarians avoid: meat, fish, shellfish, slaughter by-products and insect-derived additives."),
    ("DairyIngredient", ["AnimalDerivedIngredient"], "Milk and milk-derived ingredients."),
    ("EggIngredient", ["AnimalDerivedIngredient"], "Eggs and egg-derived ingredients."),
    ("FishIngredient", ["AnimalDerivedIngredient", "VegetarianIncompatibleIngredient"], "Fish and fish products."),
    ("CrustaceanIngredient", ["AnimalDerivedIngredient", "VegetarianIncompatibleIngredient"], "Crustaceans."),
    ("MolluscIngredient", ["AnimalDerivedIngredient", "VegetarianIncompatibleIngredient"], "Molluscs."),
    ("MeatIngredient", ["AnimalDerivedIngredient", "VegetarianIncompatibleIngredient"], "Meat."),
    ("SlaughterByproduct", ["AnimalDerivedIngredient", "VegetarianIncompatibleIngredient"],
     "Gelatin, lard, animal rennet and similar by-products of slaughter."),
    ("InsectDerivedIngredient", ["AnimalDerivedIngredient", "VegetarianIncompatibleIngredient"],
     "Additives made from insects, e.g. carmine (E120) and shellac (E904)."),
    ("BeeProduct", ["AnimalDerivedIngredient"], "Honey, beeswax and other bee products (vegetarian, not vegan)."),

    ("OtherOriginIngredient", ["Ingredient"], "Ingredients that are neither plant nor animal derived."),
    ("MineralOrSyntheticIngredient", ["OtherOriginIngredient"], "Water, salt, minerals and synthetic additives."),
    ("MicrobialIngredient", ["OtherOriginIngredient"], "Yeast and ingredients made by microbial fermentation."),

    ("CompoundIngredient", ["Ingredient"], "An ingredient that is itself a recipe, e.g. mayonnaise or milk chocolate."),
    ("UnspecifiedOriginIngredient", ["Ingredient"],
     "An ingredient whose source a label does not reveal (e.g. 'lecithin', E471). Deliberately NOT disjoint "
     "from the origin classes: the origin is unknown, not absent."),
    ("GlutenSourceIngredient", ["Ingredient"], "Ingredient that delivers gluten to the finished food."),
    ("LactoseSourceIngredient", ["Ingredient"], "Ingredient that delivers lactose to the finished food."),

    # allergens
    ("Allergen", [], "A food allergen or hazard that some consumers must avoid."),
    ("AllergenCategory", ["Allergen"], "A regulated allergen group, e.g. milk, tree nuts."),
    ("SpecificAllergen", ["Allergen"], "A named member of a group, e.g. hazelnut, rye."),

    # label claims
    ("LabelClaim", [], "A statement printed on a label."),
    ("DietClaim", ["LabelClaim"], "Diet suitability claim."),
    ("VeganClaim", ["DietClaim"], ""),
    ("VegetarianClaim", ["DietClaim"], ""),
    ("FreeFromClaim", ["LabelClaim"], "Claim that the product is free of named allergens."),
    ("GlutenFreeClaim", ["FreeFromClaim"], ""),
    ("DairyFreeClaim", ["FreeFromClaim"], ""),
    ("NutFreeClaim", ["FreeFromClaim"], ""),
    ("PeanutFreeClaim", ["FreeFromClaim"], ""),
    ("EggFreeClaim", ["FreeFromClaim"], ""),
    ("SoyFreeClaim", ["FreeFromClaim"], ""),
    ("IntoleranceClaim", ["LabelClaim"], "Claim aimed at an intolerance rather than an allergy."),
    ("LactoseFreeClaim", ["IntoleranceClaim"], ""),
    ("RegulatedMarketingTerm", ["LabelClaim"], "A term with a legal definition that is not a safety claim."),
    ("NonDairyClaim", ["RegulatedMarketingTerm"], "US 'non-dairy' (21 CFR 101.4(d)); may contain caseinate."),

    # context
    ("Jurisdiction", [], "A regulatory market."),
    ("USJurisdiction", ["Jurisdiction"], ""),
    ("CanadaJurisdiction", ["Jurisdiction"], ""),
    ("EUJurisdiction", ["Jurisdiction"], ""),
    ("Consumer", [], "A consumer profile with allergies or dietary choices."),
    ("VegetarianConsumer", ["Consumer"], ""),
    ("VeganConsumer", ["VegetarianConsumer"], ""),
    ("ProductCategory", [], "Retail category used for grouping analyses."),
    ("DeclarationExemption", [],
     "Reified n-ary relation (ingredient, allergen, jurisdiction). OWL properties are binary, so a three-way "
     "fact needs its own individual (W3C N-ary Relations pattern)."),

    # product classes that only SWRL rules populate
    ("MeetsGlutenFreeThreshold", ["Product"], "Lab result below 20 ppm gluten."),
    ("SulphiteAtOrAbove10ppm", ["Product"], "Total sulphites of 10 ppm or more (US and Canada trigger)."),
    ("SulphiteAbove10ppm", ["SulphiteAtOrAbove10ppm"], "Total sulphites above 10 mg/kg (EU trigger)."),
]

# ---------------------------------------------------------------------------
# Object properties
# ---------------------------------------------------------------------------
OBJECT_PROPERTIES = {
    "hasIngredient": dict(domain=["Product"], range=["Ingredient"],
                          comment="Ingredient appearing in a product's (flattened) ingredient list."),
    "isIngredientOf": dict(domain=["Ingredient"], range=["Product"], inverse="hasIngredient", comment="Inverse of hasIngredient."),
    "hasComponent": dict(domain=["Ingredient"], range=["Ingredient"], characteristics=["transitive"],
                         comment="Component of a compound ingredient (mayonnaise has component egg yolk)."),
    "derivedFrom": dict(domain=["Ingredient"], range=["Ingredient"], characteristics=["transitive"],
                        comment="Provenance: the raw material an ingredient was made from."),
    "retainsAllergensOf": dict(domain=["Ingredient"], range=["Ingredient"], characteristics=["transitive"], parent="derivedFrom",
                               comment="Derivation that keeps the source's allergenic proteins. Highly refined oils are "
                                       "derivedFrom soybean but do not retainAllergensOf it."),
    "triggersAllergen": dict(domain=["Ingredient"], range=["Allergen"], comment="Ingredient carries this allergen."),
    "possiblyTriggers": dict(domain=["Ingredient"], range=["Allergen"],
                             comment="Allergen the ingredient may carry depending on an unstated source."),
    "isSubtypeOf": dict(domain=["Allergen"], range=["Allergen"], characteristics=["transitive"],
                        comment="Allergen grouping, e.g. hazelnut isSubtypeOf tree nuts."),
    "containsAllergen": dict(domain=["Product"], range=["Allergen"], comment="Inferred: the product contains the allergen."),
    "mayContain": dict(domain=["Product"], range=["Allergen"], comment="Precautionary ('may contain') labelling."),
    "hasLabelClaim": dict(domain=["Product"], range=["LabelClaim"]),
    "excludesAllergen": dict(domain=["LabelClaim"], range=["Allergen"], comment="Allergen a free-from claim rules out."),
    "contradictsClaim": dict(domain=["Product"], range=["LabelClaim"], comment="Inferred: composition contradicts the claim."),
    "precautionaryConflictWith": dict(domain=["Product"], range=["LabelClaim"],
                                      comment="Inferred: a 'may contain' statement undermines the claim."),
    "soldIn": dict(domain=["Product"], range=["Jurisdiction"]),
    "requiresDeclarationOf": dict(domain=["Jurisdiction"], range=["Allergen"]),
    "mustDeclare": dict(domain=["Product"], range=["Allergen"], comment="Inferred declaration duty in at least one market."),
    "mustDeclareInUS": dict(domain=["Product"], range=["Allergen"], parent="mustDeclare"),
    "mustDeclareInCanada": dict(domain=["Product"], range=["Allergen"], parent="mustDeclare"),
    "mustDeclareInEU": dict(domain=["Product"], range=["Allergen"], parent="mustDeclare"),
    "declaresAllergen": dict(domain=["Product"], range=["Allergen"], comment="Allergen the printed label actually declares."),
    "mustAvoid": dict(domain=["Consumer"], range=["Allergen"]),
    "unsafeFor": dict(domain=["Product"], range=["Consumer"], comment="Inferred: contains something the consumer must avoid."),
    "cautionFor": dict(domain=["Product"], range=["Consumer"], comment="Inferred: may contain something the consumer must avoid."),
    "unsuitableForDietOf": dict(domain=["Product"], range=["Consumer"]),
    "inCategory": dict(domain=["Product"], range=["ProductCategory"]),
    "exemptIngredient": dict(domain=["DeclarationExemption"], range=["Ingredient"]),
    "exemptAllergen": dict(domain=["DeclarationExemption"], range=["Allergen"]),
    "exemptJurisdiction": dict(domain=["DeclarationExemption"], range=["Jurisdiction"]),
}

# ---------------------------------------------------------------------------
# Data properties
# ---------------------------------------------------------------------------
DATA_PROPERTIES = {
    "hasBarcode": dict(domain=["Product"], range="str", functional=True),
    "hasIngredientListStatus": dict(domain=["Product"], range="str", functional=True,
                                    comment="'complete' or 'incomplete'; decides where closed-world reasoning is allowed."),
    "hasGlutenPPM": dict(domain=["Product"], range="float", functional=True, comment="Lab-measured gluten, mg/kg."),
    "hasSulphiteMgPerKg": dict(domain=["Product"], range="float", functional=True, comment="Total SO2, mg/kg."),
}

ANNOTATION_PROPERTIES = ["regulatoryBasis", "scenarioNote", "synonym", "curatorNote"]

# ---------------------------------------------------------------------------
# OWL 2 property chains (complex role inclusions)
# ---------------------------------------------------------------------------
PROPERTY_CHAINS = [
    dict(chain=["retainsAllergensOf", "triggersAllergen"], super="triggersAllergen",
         comment="Whey retains the allergens of milk, milk triggers milk allergen, so whey triggers milk allergen."),
    dict(chain=["hasComponent", "triggersAllergen"], super="triggersAllergen",
         comment="A compound ingredient carries the allergens of its components."),
    dict(chain=["containsAllergen", "isSubtypeOf"], super="containsAllergen",
         comment="A product containing hazelnut contains tree nuts."),
    dict(chain=["mayContain", "isSubtypeOf"], super="mayContain",
         comment="'May contain hazelnut' implies 'may contain tree nuts'."),
]

# ---------------------------------------------------------------------------
# Defined classes (owl:equivalentClass) and their Horn translations
# ---------------------------------------------------------------------------
# 'horn' holds the sufficient-condition rules the engine can run. An empty list
# means the definition needs a universal restriction, which the engine handles
# with closed-world rules in rules_catalog.py instead.
DEFINED_CLASSES = [
    dict(name="NonVeganIngredient", parents=["Ingredient"],
         owl=lambda o: o.AnimalDerivedIngredient | o.hasComponent.some(o.AnimalDerivedIngredient),
         horn=["AnimalDerivedIngredient(?i) -> NonVeganIngredient(?i)",
               "hasComponent(?i, ?c), AnimalDerivedIngredient(?c) -> NonVeganIngredient(?i)"],
         comment="Animal-derived, or a compound with an animal-derived component (at any depth, since hasComponent is transitive)."),
    dict(name="NonVegetarianIngredient", parents=["Ingredient"],
         owl=lambda o: (o.VegetarianIncompatibleIngredient
                        | o.hasComponent.some(o.VegetarianIncompatibleIngredient)
                        | o.derivedFrom.some(o.VegetarianIncompatibleIngredient)),
         horn=["VegetarianIncompatibleIngredient(?i) -> NonVegetarianIngredient(?i)",
               "hasComponent(?i, ?c), VegetarianIncompatibleIngredient(?c) -> NonVegetarianIngredient(?i)",
               "derivedFrom(?i, ?c), VegetarianIncompatibleIngredient(?c) -> NonVegetarianIngredient(?i)"],
         comment="Covers hidden cases such as parmesan made with animal rennet."),
    dict(name="VeganSafeIngredient", parents=["Ingredient"],
         owl=lambda o: (o.PlantDerivedIngredient | o.OtherOriginIngredient
                        | (o.CompoundIngredient & o.hasComponent.only(o.PlantDerivedIngredient | o.OtherOriginIngredient))),
         horn=["PlantDerivedIngredient(?i) -> VeganSafeIngredient(?i)",
               "OtherOriginIngredient(?i) -> VeganSafeIngredient(?i)"],
         comment="The compound case uses 'only' (a universal restriction): OWL can conclude it only after the compound's "
                 "component list is closed."),
    dict(name="NonVeganProduct", parents=["Product"],
         owl=lambda o: o.Product & o.hasIngredient.some(o.NonVeganIngredient),
         horn=["Product(?p), hasIngredient(?p, ?i), NonVeganIngredient(?i) -> NonVeganProduct(?p)"]),
    dict(name="NonVegetarianProduct", parents=["Product"],
         owl=lambda o: o.Product & o.hasIngredient.some(o.NonVegetarianIngredient),
         horn=["Product(?p), hasIngredient(?p, ?i), NonVegetarianIngredient(?i) -> NonVegetarianProduct(?p)"]),
    dict(name="OriginUncertainProduct", parents=["Product"],
         owl=lambda o: o.Product & o.hasIngredient.some(
             o.UnspecifiedOriginIngredient | o.hasComponent.some(o.UnspecifiedOriginIngredient)),
         horn=["Product(?p), hasIngredient(?p, ?i), UnspecifiedOriginIngredient(?i) -> OriginUncertainProduct(?p)",
               "Product(?p), hasIngredient(?p, ?i), hasComponent(?i, ?c), UnspecifiedOriginIngredient(?c) -> OriginUncertainProduct(?p)"]),
    dict(name="VeganCompatibleProduct", parents=["Product"],
         owl=lambda o: o.Product & o.hasIngredient.some(o.Ingredient) & o.hasIngredient.only(o.VeganSafeIngredient),
         horn=[],
         comment="Universal restriction: under the open-world assumption no product is ever classified here unless its "
                 "ingredient list is closed. The engine's VerifiedVeganProduct is the closed-world counterpart."),
    dict(name="GlutenContainingProduct", parents=["Product"],
         owl=lambda o: o.Product & o.hasIngredient.some(o.GlutenSourceIngredient),
         horn=["Product(?p), hasIngredient(?p, ?i), GlutenSourceIngredient(?i) -> GlutenContainingProduct(?p)"]),
    dict(name="AllergenContainingProduct", parents=["Product"],
         owl=lambda o: o.Product & o.containsAllergen.some(o.Allergen),
         horn=["Product(?p), containsAllergen(?p, ?a) -> AllergenContainingProduct(?p)"]),
    dict(name="PrecautionaryLabelledProduct", parents=["Product"],
         owl=lambda o: o.Product & o.mayContain.some(o.Allergen),
         horn=["Product(?p), mayContain(?p, ?a) -> PrecautionaryLabelledProduct(?p)"]),
    dict(name="ClaimConflictProduct", parents=["Product"],
         owl=lambda o: o.Product & o.contradictsClaim.some(o.LabelClaim),
         horn=["Product(?p), contradictsClaim(?p, ?c) -> ClaimConflictProduct(?p)"]),
    dict(name="PrecautionaryConflictProduct", parents=["Product"],
         owl=lambda o: o.Product & o.precautionaryConflictWith.some(o.LabelClaim),
         horn=["Product(?p), precautionaryConflictWith(?p, ?c) -> PrecautionaryConflictProduct(?p)"]),
    dict(name="MultiMarketProduct", parents=["Product"],
         owl=lambda o: o.Product & o.soldIn.min(2, o.Jurisdiction),
         horn=["Product(?p), soldIn(?p, ?j1), soldIn(?p, ?j2), notEqual(?j1, ?j2) -> MultiMarketProduct(?p)"],
         comment="Qualified cardinality; relies on AllDifferent over jurisdictions because OWL has no unique name assumption."),
    dict(name="IncompleteRecordProduct", parents=["Product"],
         owl=lambda o: o.Product & o.hasIngredientListStatus.value("incomplete"),
         horn=['Product(?p), hasIngredientListStatus(?p, "incomplete") -> IncompleteRecordProduct(?p)']),
]

# ---------------------------------------------------------------------------
# General class inclusion axioms (left side is a class expression)
# ---------------------------------------------------------------------------
GCIS = [
    dict(left=lambda o: o.derivedFrom.some(o.AnimalDerivedIngredient), right="AnimalDerivedIngredient",
         horn="derivedFrom(?i, ?j), AnimalDerivedIngredient(?j) -> AnimalDerivedIngredient(?i)",
         comment="Animal origin is inherited through any derivation, refined or not."),
    dict(left=lambda o: o.hasComponent.some(o.GlutenSourceIngredient), right="GlutenSourceIngredient",
         horn="hasComponent(?i, ?c), GlutenSourceIngredient(?c) -> GlutenSourceIngredient(?i)",
         comment="Soy sauce has component wheat, so soy sauce is a gluten source."),
    dict(left=lambda o: o.hasComponent.some(o.LactoseSourceIngredient), right="LactoseSourceIngredient",
         horn="hasComponent(?i, ?c), LactoseSourceIngredient(?c) -> LactoseSourceIngredient(?i)"),
]

# ---------------------------------------------------------------------------
# Value restrictions that mention individuals (added after the ABox exists)
# ---------------------------------------------------------------------------
HAS_VALUE_AXIOMS = [
    dict(cls="GlutenContainingProduct", prop="containsAllergen", value="alg_gluten",
         horn="GlutenContainingProduct(?p) -> containsAllergen(?p, alg_gluten)",
         comment="Gluten is asserted per ingredient, not inherited, because processing can remove it."),
]

# ---------------------------------------------------------------------------
# Necessary conditions (rdfs:subClassOf restrictions). Under the open-world
# assumption these never flag missing data; the engine checks them as
# integrity constraints instead (see rules_catalog.INTEGRITY_RULES).
# ---------------------------------------------------------------------------
RESTRICTIONS = [
    dict(cls="Product", owl=lambda o: o.hasBarcode.exactly(1), comment="Every product has exactly one barcode."),
    dict(cls="Product", owl=lambda o: o.soldIn.min(1, o.Jurisdiction), comment="Every product is sold somewhere."),
    dict(cls="Product", owl=lambda o: o.inCategory.max(1, o.ProductCategory), comment="At most one retail category."),
    dict(cls="FreeFromClaim", owl=lambda o: o.excludesAllergen.min(1, o.Allergen), comment="A free-from claim names an allergen."),
    dict(cls="DeclarationExemption", owl=lambda o: o.exemptIngredient.exactly(1, o.Ingredient)),
    dict(cls="DeclarationExemption", owl=lambda o: o.exemptAllergen.exactly(1, o.Allergen)),
    dict(cls="DeclarationExemption", owl=lambda o: o.exemptJurisdiction.exactly(1, o.Jurisdiction)),
]

# ---------------------------------------------------------------------------
# Disjointness
# ---------------------------------------------------------------------------
DISJOINT_GROUPS = [
    ["Product", "Ingredient", "Allergen", "LabelClaim", "Jurisdiction", "Consumer", "ProductCategory", "DeclarationExemption"],
    ["PlantDerivedIngredient", "AnimalDerivedIngredient", "OtherOriginIngredient", "CompoundIngredient"],
    ["DairyIngredient", "EggIngredient", "FishIngredient", "CrustaceanIngredient", "MolluscIngredient",
     "MeatIngredient", "BeeProduct", "InsectDerivedIngredient"],
    ["AllergenCategory", "SpecificAllergen"],
    ["USJurisdiction", "CanadaJurisdiction", "EUJurisdiction"],
    ["DietClaim", "FreeFromClaim", "IntoleranceClaim", "RegulatedMarketingTerm"],
]

# Pairs the engine checks explicitly (OWL would report an inconsistent ontology)
ENGINE_DISJOINTNESS_CHECKS = [
    ("PlantDerivedIngredient", "AnimalDerivedIngredient"),
    ("PlantDerivedIngredient", "OtherOriginIngredient"),
    ("AnimalDerivedIngredient", "OtherOriginIngredient"),
    ("CompoundIngredient", "AnimalDerivedIngredient"),
    ("CompoundIngredient", "PlantDerivedIngredient"),
]


def class_names():
    """All named classes, including defined ones."""
    return [c[0] for c in CLASSES] + [d["name"] for d in DEFINED_CLASSES]


def parents_of(name):
    for c in CLASSES:
        if c[0] == name:
            return list(c[1])
    for d in DEFINED_CLASSES:
        if d["name"] == name:
            return list(d["parents"])
    return []
