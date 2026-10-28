"""
FALCON rule catalogue.

SWRL_RULES are monotonic Horn rules written in the SWRL human-readable syntax.
They are loaded into the OWL ontology (executed by Pellet) *and* parsed by the
FALCON engine, so both implementations run exactly the same text.

ENGINE_RULES need features SWRL lacks:
  * negation as failure under a local closed-world assumption ('not ...'),
  * predicates with three arguments (OWL properties are binary),
  * defeasible exceptions (an EU exemption that switches a duty off).

INTEGRITY_RULES treat some OWL axioms as constraints. Under the open-world
assumption an OWL 'exactly 1' restriction never flags a missing barcode; in a
data-quality setting we want it flagged, which is what SHACL would do.
"""

SWRL_RULES = [
    # --- allergen detection ------------------------------------------------------
    dict(id="R01", name="Product allergen detection", group="Allergen propagation",
         swrl="Product(?p), hasIngredient(?p, ?i), triggersAllergen(?i, ?a) -> containsAllergen(?p, ?a)",
         rationale="An ingredient's allergens, including those it inherits through derivation and composition "
                   "(property chains), pass to every product that uses it."),

    # --- label claims --------------------------------------------------------------
    dict(id="R02", name="Free-from claim contradiction", group="Claim checking",
         swrl="hasLabelClaim(?p, ?c), excludesAllergen(?c, ?a), containsAllergen(?p, ?a) -> contradictsClaim(?p, ?c)",
         rationale="A free-from claim is false if the product contains an allergen the claim excludes."),
    dict(id="R03", name="Vegan claim contradiction", group="Claim checking",
         swrl="hasLabelClaim(?p, ?c), VeganClaim(?c), NonVeganProduct(?p) -> contradictsClaim(?p, ?c)",
         rationale="NonVeganProduct is a defined class, so the reasoner classifies first and the rule then fires."),
    dict(id="R04", name="Vegetarian claim contradiction", group="Claim checking",
         swrl="hasLabelClaim(?p, ?c), VegetarianClaim(?c), NonVegetarianProduct(?p) -> contradictsClaim(?p, ?c)",
         rationale="Catches hidden cases such as parmesan made with animal rennet."),
    dict(id="R05", name="Lactose-free claim contradiction", group="Claim checking",
         swrl="hasLabelClaim(?p, ?c), LactoseFreeClaim(?c), hasIngredient(?p, ?i), LactoseSourceIngredient(?i) -> contradictsClaim(?p, ?c)",
         rationale="Lactose-free is about milk sugar; it is contradicted by lactose-bearing ingredients only."),
    dict(id="R06", name="Precautionary label conflict", group="Claim checking",
         swrl="hasLabelClaim(?p, ?c), excludesAllergen(?c, ?a), mayContain(?p, ?a) -> precautionaryConflictWith(?p, ?c)",
         rationale="'Nut-free' printed next to 'may contain hazelnut' sends the consumer two opposite messages."),

    # --- consumer safety -------------------------------------------------------------
    dict(id="R07", name="Unsafe for consumer", group="Consumer safety",
         swrl="Consumer(?u), mustAvoid(?u, ?a), containsAllergen(?p, ?a) -> unsafeFor(?p, ?u)",
         rationale="Because containsAllergen is closed under isSubtypeOf, a tree-nut allergy matches hazelnut."),
    dict(id="R08", name="Caution for consumer", group="Consumer safety",
         swrl="Consumer(?u), mustAvoid(?u, ?a), mayContain(?p, ?a) -> cautionFor(?p, ?u)",
         rationale="Precautionary labelling is advisory, so it produces a caution rather than an unsafe verdict."),
    dict(id="R09", name="Unsuitable for vegan diet", group="Consumer safety",
         swrl="VeganConsumer(?u), NonVeganProduct(?p) -> unsuitableForDietOf(?p, ?u)"),
    dict(id="R10", name="Unsuitable for vegetarian diet", group="Consumer safety",
         swrl="VegetarianConsumer(?u), NonVegetarianProduct(?p) -> unsuitableForDietOf(?p, ?u)",
         rationale="VeganConsumer is a subclass of VegetarianConsumer, so vegans inherit this rule too."),

    # --- declaration duties (binary projections of a three-way relation) --------------
    dict(id="R11", name="US declaration duty", group="Regulatory compliance",
         swrl="containsAllergen(?p, ?a), soldIn(?p, ?j), USJurisdiction(?j), requiresDeclarationOf(?j, ?a) -> mustDeclareInUS(?p, ?a)"),
    dict(id="R12", name="Canada declaration duty", group="Regulatory compliance",
         swrl="containsAllergen(?p, ?a), soldIn(?p, ?j), CanadaJurisdiction(?j), requiresDeclarationOf(?j, ?a) -> mustDeclareInCanada(?p, ?a)"),
    dict(id="R13", name="EU declaration duty", group="Regulatory compliance",
         swrl="containsAllergen(?p, ?a), soldIn(?p, ?j), EUJurisdiction(?j), requiresDeclarationOf(?j, ?a) -> mustDeclareInEU(?p, ?a)",
         rationale="Monotonic: it cannot honour the Annex II exemption for wheat glucose syrup (see engine rule E04)."),

    # --- numeric thresholds (SWRL built-ins; Pellet only) ------------------------------
    dict(id="R14", name="Gluten-free threshold exceeded", group="Numeric thresholds", builtins=True,
         swrl="hasLabelClaim(?p, ?c), GlutenFreeClaim(?c), hasGlutenPPM(?p, ?x), greaterThanOrEqual(?x, 20.0) -> contradictsClaim(?p, ?c)",
         rationale="US, Canadian and EU gluten-free rules all use a limit of below 20 ppm."),
    dict(id="R15", name="Gluten-free threshold met", group="Numeric thresholds", builtins=True,
         swrl="Product(?p), hasGlutenPPM(?p, ?x), lessThan(?x, 20.0) -> MeetsGlutenFreeThreshold(?p)"),
    dict(id="R16", name="Sulphites at or above 10 ppm", group="Numeric thresholds", builtins=True,
         swrl="Product(?p), hasSulphiteMgPerKg(?p, ?x), greaterThanOrEqual(?x, 10.0) -> SulphiteAtOrAbove10ppm(?p)",
         rationale="US (21 CFR 101.100(a)(4)) and Canada use 10 ppm or more."),
    dict(id="R17", name="Sulphites above 10 mg/kg", group="Numeric thresholds", builtins=True,
         swrl="Product(?p), hasSulphiteMgPerKg(?p, ?x), greaterThan(?x, 10.0) -> SulphiteAbove10ppm(?p)",
         rationale="EU Annex II point 12 uses 'more than 10 mg/kg': exactly 10 is not declarable in the EU."),
]

ENGINE_RULES = [
    # --- provenance-aware allergen relation (three arguments) --------------------------
    dict(id="E01", name="Allergen with its source ingredient", group="Allergen propagation",
         text="Product(?p), hasIngredient(?p, ?i), triggersAllergen(?i, ?a) -> containsVia(?p, ?a, ?i)"),
    dict(id="E02", name="Source-tracked allergen generalisation", group="Allergen propagation",
         text="containsVia(?p, ?a, ?i), isSubtypeOf(?a, ?b) -> containsVia(?p, ?b, ?i)"),
    dict(id="E03", name="Source-tracked gluten", group="Allergen propagation",
         text="Product(?p), hasIngredient(?p, ?i), GlutenSourceIngredient(?i) -> containsVia(?p, alg_gluten, ?i)"),

    # --- defeasible, jurisdiction-aware declaration duties ------------------------------
    dict(id="E04", name="Declaration duty unless exempt", group="Regulatory compliance",
         text="containsVia(?p, ?a, ?i), soldIn(?p, ?j), requiresDeclarationOf(?j, ?a), not exemptFromDeclaration(?i, ?a, ?j) -> declarationDuty(?p, ?a, ?j)",
         rationale="Defeasible: the duty holds unless an exemption is known for that ingredient in that market."),
    dict(id="E05", name="US sulphite duty", group="Regulatory compliance",
         text="Product(?p), soldIn(?p, ?j), USJurisdiction(?j), hasSulphiteMgPerKg(?p, ?x), greaterThanOrEqual(?x, 10.0) -> declarationDuty(?p, alg_sulphites, ?j)"),
    dict(id="E06", name="Canada sulphite duty", group="Regulatory compliance",
         text="Product(?p), soldIn(?p, ?j), CanadaJurisdiction(?j), hasSulphiteMgPerKg(?p, ?x), greaterThanOrEqual(?x, 10.0) -> declarationDuty(?p, alg_sulphites, ?j)"),
    dict(id="E07", name="EU sulphite duty", group="Regulatory compliance",
         text="Product(?p), soldIn(?p, ?j), EUJurisdiction(?j), hasSulphiteMgPerKg(?p, ?x), greaterThan(?x, 10.0) -> declarationDuty(?p, alg_sulphites, ?j)"),
    dict(id="E08", name="Undeclared allergen", group="Regulatory compliance",
         text="declarationDuty(?p, ?a, ?j), not declaresAllergen(?p, ?a) -> undeclaredAllergen(?p, ?a, ?j)",
         rationale="Undeclared allergens are the leading cause of food recalls; this is the recall-risk signal."),
    dict(id="E09", name="Needs supplier verification", group="Regulatory compliance",
         text="hasIngredient(?p, ?i), possiblyTriggers(?i, ?a), soldIn(?p, ?j), requiresDeclarationOf(?j, ?a), not declaresAllergen(?p, ?a), not containsAllergen(?p, ?a) -> needsSupplierCheck(?p, ?a, ?j)",
         rationale="Unspecified lecithin might be soy or egg; only the supplier can say."),

    # --- hidden allergens -----------------------------------------------------------------
    dict(id="E10", name="Hidden allergen", group="Hidden allergens",
         text="Product(?p), hasIngredient(?p, ?i), triggersAllergen(?i, ?a), not assertedTrigger(?i, ?a), not mentionsAllergen(?i, ?a) -> hiddenAllergenVia(?p, ?a, ?i)",
         rationale="The allergen was inferred through derivation or composition and the ingredient's name does not mention it."),

    # --- three-valued consumer safety (local closed world) ---------------------------------
    dict(id="E11", name="Has some ingredient", group="Closed-world helpers",
         text="hasIngredient(?p, ?i) -> hasSomeIngredient(?p)"),
    dict(id="E12", name="Uncertain for consumer", group="Consumer safety",
         text="Consumer(?u), mustAvoid(?u, ?a), hasIngredient(?p, ?i), possiblyTriggers(?i, ?a), not containsAllergen(?p, ?a) -> uncertainFor(?p, ?u)"),
    dict(id="E13", name="Confirmed safe for consumer", group="Consumer safety",
         text='Consumer(?u), Product(?p), hasIngredientListStatus(?p, "complete"), hasSomeIngredient(?p), not unsafeFor(?p, ?u), not cautionFor(?p, ?u), not uncertainFor(?p, ?u) -> confirmedSafeFor(?p, ?u)',
         rationale="Negation as failure is only trusted on records marked complete (local closed-world assumption)."),
    dict(id="E14", name="Diet status uncertain (vegan)", group="Consumer safety",
         text="VeganConsumer(?u), OriginUncertainProduct(?p), not NonVeganProduct(?p) -> dietUncertainFor(?p, ?u)"),
    dict(id="E15", name="Diet status uncertain (vegetarian)", group="Consumer safety",
         text="VegetarianConsumer(?u), OriginUncertainProduct(?p), not NonVegetarianProduct(?p) -> dietUncertainFor(?p, ?u)"),

    # --- vegan verification: the closed-world counterpart of an OWL 'only' restriction ------
    dict(id="E16", name="Simple vegan-safe (plant)", group="Diet verification",
         text="PlantDerivedIngredient(?x) -> SimpleVeganSafe(?x)"),
    dict(id="E17", name="Simple vegan-safe (other origin)", group="Diet verification",
         text="OtherOriginIngredient(?x) -> SimpleVeganSafe(?x)"),
    dict(id="E18", name="Compound has a non-vegan-safe component", group="Diet verification",
         text="hasComponent(?x, ?c), not SimpleVeganSafe(?c) -> hasNonVeganSafeComponent(?x)"),
    dict(id="E19", name="Vegan-safe compound", group="Diet verification",
         text="CompoundIngredient(?x), not hasNonVeganSafeComponent(?x) -> VeganSafeIngredient(?x)"),
    dict(id="E20", name="Product has a non-vegan-safe ingredient", group="Diet verification",
         text="hasIngredient(?p, ?i), not VeganSafeIngredient(?i) -> hasNonVeganSafeIngredient(?p)"),
    dict(id="E21", name="Verified vegan product", group="Diet verification",
         text='Product(?p), hasIngredientListStatus(?p, "complete"), hasSomeIngredient(?p), not hasNonVeganSafeIngredient(?p) -> VerifiedVeganProduct(?p)'),
    dict(id="E22", name="Simple vegetarian-safe (vegan-safe)", group="Diet verification",
         text="VeganSafeIngredient(?x) -> SimpleVegetarianSafe(?x)"),
    dict(id="E23", name="Simple vegetarian-safe (dairy)", group="Diet verification",
         text="DairyIngredient(?x) -> SimpleVegetarianSafe(?x)"),
    dict(id="E24", name="Simple vegetarian-safe (egg)", group="Diet verification",
         text="EggIngredient(?x) -> SimpleVegetarianSafe(?x)"),
    dict(id="E25", name="Simple vegetarian-safe (bee product)", group="Diet verification",
         text="BeeProduct(?x) -> SimpleVegetarianSafe(?x)"),
    dict(id="E26", name="Vegetarian-safe ingredient", group="Diet verification",
         text="SimpleVegetarianSafe(?x), not NonVegetarianIngredient(?x) -> VegetarianSafeIngredient(?x)"),
    dict(id="E27", name="Compound has a non-vegetarian-safe component", group="Diet verification",
         text="hasComponent(?x, ?c), not SimpleVegetarianSafe(?c) -> hasNonVegetarianSafeComponent(?x)"),
    dict(id="E28", name="Vegetarian-safe compound", group="Diet verification",
         text="CompoundIngredient(?x), not hasNonVegetarianSafeComponent(?x), not NonVegetarianIngredient(?x) -> VegetarianSafeIngredient(?x)"),
    dict(id="E29", name="Product has a non-vegetarian-safe ingredient", group="Diet verification",
         text="hasIngredient(?p, ?i), not VegetarianSafeIngredient(?i) -> hasNonVegetarianSafeIngredient(?p)"),
    dict(id="E30", name="Verified vegetarian product", group="Diet verification",
         text='Product(?p), hasIngredientListStatus(?p, "complete"), hasSomeIngredient(?p), not hasNonVegetarianSafeIngredient(?p) -> VerifiedVegetarianProduct(?p)'),

    # --- claim audit: verified / contradicted / at risk / unverifiable ----------------------
    dict(id="A01", name="Claim doubt from unspecified source", group="Claim audit",
         text="hasLabelClaim(?p, ?c), excludesAllergen(?c, ?a), hasIngredient(?p, ?i), possiblyTriggers(?i, ?a), not containsAllergen(?p, ?a) -> claimDoubt(?p, ?c)"),
    dict(id="A02", name="Free-from claim verified", group="Claim audit",
         text='hasLabelClaim(?p, ?c), FreeFromClaim(?c), hasIngredientListStatus(?p, "complete"), hasSomeIngredient(?p), not contradictsClaim(?p, ?c), not precautionaryConflictWith(?p, ?c), not claimDoubt(?p, ?c) -> claimVerified(?p, ?c)'),
    dict(id="A03", name="Vegan claim verified", group="Claim audit",
         text="hasLabelClaim(?p, ?c), VeganClaim(?c), VerifiedVeganProduct(?p) -> claimVerified(?p, ?c)"),
    dict(id="A04", name="Vegetarian claim verified", group="Claim audit",
         text="hasLabelClaim(?p, ?c), VegetarianClaim(?c), VerifiedVegetarianProduct(?p) -> claimVerified(?p, ?c)"),
    dict(id="A05", name="Lactose-free claim verified", group="Claim audit",
         text='hasLabelClaim(?p, ?c), LactoseFreeClaim(?c), hasIngredientListStatus(?p, "complete"), hasSomeIngredient(?p), not contradictsClaim(?p, ?c) -> claimVerified(?p, ?c)'),
    dict(id="A06", name="Informational term", group="Claim audit",
         text="hasLabelClaim(?p, ?c), RegulatedMarketingTerm(?c) -> claimInformational(?p, ?c)"),
    dict(id="A07", name="Claim at risk", group="Claim audit",
         text="hasLabelClaim(?p, ?c), precautionaryConflictWith(?p, ?c), not contradictsClaim(?p, ?c) -> claimAtRisk(?p, ?c)"),
    dict(id="A08", name="Claim contradicted", group="Claim audit",
         text="contradictsClaim(?p, ?c) -> claimContradicted(?p, ?c)"),
    dict(id="A09", name="Claim unverifiable", group="Claim audit",
         text="hasLabelClaim(?p, ?c), not claimVerified(?p, ?c), not contradictsClaim(?p, ?c), not precautionaryConflictWith(?p, ?c), not claimInformational(?p, ?c) -> claimUnverifiable(?p, ?c)",
         rationale="Nothing contradicts the claim, but the data cannot confirm it either."),
]

INTEGRITY_RULES = [
    dict(id="I01", name="Has a barcode value", text="hasBarcode(?p, ?b) -> hasBarcodeValue(?p)"),
    dict(id="I02", name="Missing barcode", text='Product(?p), not hasBarcodeValue(?p) -> integrityViolation(?p, "missing barcode")'),
    dict(id="I03", name="Sold somewhere", text="soldIn(?p, ?j) -> soldSomewhere(?p)"),
    dict(id="I04", name="Not sold anywhere", text='Product(?p), not soldSomewhere(?p) -> integrityViolation(?p, "not sold in any jurisdiction")'),
    dict(id="I05", name="Complete but empty record",
         text='Product(?p), hasIngredientListStatus(?p, "complete"), not hasSomeIngredient(?p) -> integrityViolation(?p, "ingredient list marked complete but empty")'),
]
