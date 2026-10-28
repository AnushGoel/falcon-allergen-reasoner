# FALCON rule catalogue

Generated from the rule objects used at run time.

## SWRL production rules (run by Pellet and by the FALCON engine)

| ID | Name | First-order form |
|---|---|---|
| R01 | Product allergen detection | ∀a, i, p: Product(p) ∧ hasIngredient(p, i) ∧ triggersAllergen(i, a) → containsAllergen(p, a) |
| R02 | Free-from claim contradiction | ∀a, c, p: hasLabelClaim(p, c) ∧ excludesAllergen(c, a) ∧ containsAllergen(p, a) → contradictsClaim(p, c) |
| R03 | Vegan claim contradiction | ∀c, p: hasLabelClaim(p, c) ∧ VeganClaim(c) ∧ NonVeganProduct(p) → contradictsClaim(p, c) |
| R04 | Vegetarian claim contradiction | ∀c, p: hasLabelClaim(p, c) ∧ VegetarianClaim(c) ∧ NonVegetarianProduct(p) → contradictsClaim(p, c) |
| R05 | Lactose-free claim contradiction | ∀c, i, p: hasLabelClaim(p, c) ∧ LactoseFreeClaim(c) ∧ hasIngredient(p, i) ∧ LactoseSourceIngredient(i) → contradictsClaim(p, c) |
| R06 | Precautionary label conflict | ∀a, c, p: hasLabelClaim(p, c) ∧ excludesAllergen(c, a) ∧ mayContain(p, a) → precautionaryConflictWith(p, c) |
| R07 | Unsafe for consumer | ∀a, p, u: Consumer(u) ∧ mustAvoid(u, a) ∧ containsAllergen(p, a) → unsafeFor(p, u) |
| R08 | Caution for consumer | ∀a, p, u: Consumer(u) ∧ mustAvoid(u, a) ∧ mayContain(p, a) → cautionFor(p, u) |
| R09 | Unsuitable for vegan diet | ∀p, u: VeganConsumer(u) ∧ NonVeganProduct(p) → unsuitableForDietOf(p, u) |
| R10 | Unsuitable for vegetarian diet | ∀p, u: VegetarianConsumer(u) ∧ NonVegetarianProduct(p) → unsuitableForDietOf(p, u) |
| R11 | US declaration duty | ∀a, j, p: containsAllergen(p, a) ∧ soldIn(p, j) ∧ USJurisdiction(j) ∧ requiresDeclarationOf(j, a) → mustDeclareInUS(p, a) |
| R12 | Canada declaration duty | ∀a, j, p: containsAllergen(p, a) ∧ soldIn(p, j) ∧ CanadaJurisdiction(j) ∧ requiresDeclarationOf(j, a) → mustDeclareInCanada(p, a) |
| R13 | EU declaration duty | ∀a, j, p: containsAllergen(p, a) ∧ soldIn(p, j) ∧ EUJurisdiction(j) ∧ requiresDeclarationOf(j, a) → mustDeclareInEU(p, a) |
| R14 | Gluten-free threshold exceeded | ∀c, p, x: hasLabelClaim(p, c) ∧ GlutenFreeClaim(c) ∧ hasGlutenPPM(p, x) ∧ x ≥ 20.0 → contradictsClaim(p, c) |
| R15 | Gluten-free threshold met | ∀p, x: Product(p) ∧ hasGlutenPPM(p, x) ∧ x < 20.0 → MeetsGlutenFreeThreshold(p) |
| R16 | Sulphites at or above 10 ppm | ∀p, x: Product(p) ∧ hasSulphiteMgPerKg(p, x) ∧ x ≥ 10.0 → SulphiteAtOrAbove10ppm(p) |
| R17 | Sulphites above 10 mg/kg | ∀p, x: Product(p) ∧ hasSulphiteMgPerKg(p, x) ∧ x > 10.0 → SulphiteAbove10ppm(p) |

## Engine-only rules (negation as failure, n-ary, defeasible)

| ID | Name | First-order form |
|---|---|---|
| E01 | Allergen with its source ingredient | ∀a, i, p: Product(p) ∧ hasIngredient(p, i) ∧ triggersAllergen(i, a) → containsVia(p, a, i) |
| E02 | Source-tracked allergen generalisation | ∀a, b, i, p: containsVia(p, a, i) ∧ isSubtypeOf(a, b) → containsVia(p, b, i) |
| E03 | Source-tracked gluten | ∀i, p: Product(p) ∧ hasIngredient(p, i) ∧ GlutenSourceIngredient(i) → containsVia(p, alg_gluten, i) |
| E04 | Declaration duty unless exempt | ∀a, i, j, p: containsVia(p, a, i) ∧ soldIn(p, j) ∧ requiresDeclarationOf(j, a) ∧ not exemptFromDeclaration(i, a, j) → declarationDuty(p, a, j) |
| E05 | US sulphite duty | ∀j, p, x: Product(p) ∧ soldIn(p, j) ∧ USJurisdiction(j) ∧ hasSulphiteMgPerKg(p, x) ∧ x ≥ 10.0 → declarationDuty(p, alg_sulphites, j) |
| E06 | Canada sulphite duty | ∀j, p, x: Product(p) ∧ soldIn(p, j) ∧ CanadaJurisdiction(j) ∧ hasSulphiteMgPerKg(p, x) ∧ x ≥ 10.0 → declarationDuty(p, alg_sulphites, j) |
| E07 | EU sulphite duty | ∀j, p, x: Product(p) ∧ soldIn(p, j) ∧ EUJurisdiction(j) ∧ hasSulphiteMgPerKg(p, x) ∧ x > 10.0 → declarationDuty(p, alg_sulphites, j) |
| E08 | Undeclared allergen | ∀a, j, p: declarationDuty(p, a, j) ∧ not declaresAllergen(p, a) → undeclaredAllergen(p, a, j) |
| E09 | Needs supplier verification | ∀a, i, j, p: hasIngredient(p, i) ∧ possiblyTriggers(i, a) ∧ soldIn(p, j) ∧ requiresDeclarationOf(j, a) ∧ not declaresAllergen(p, a) ∧ not containsAllergen(p, a) → needsSupplierCheck(p, a, j) |
| E10 | Hidden allergen | ∀a, i, p: Product(p) ∧ hasIngredient(p, i) ∧ triggersAllergen(i, a) ∧ not assertedTrigger(i, a) ∧ not mentionsAllergen(i, a) → hiddenAllergenVia(p, a, i) |
| E11 | Has some ingredient | ∀i, p: hasIngredient(p, i) → hasSomeIngredient(p) |
| E12 | Uncertain for consumer | ∀a, i, p, u: Consumer(u) ∧ mustAvoid(u, a) ∧ hasIngredient(p, i) ∧ possiblyTriggers(i, a) ∧ not containsAllergen(p, a) → uncertainFor(p, u) |
| E13 | Confirmed safe for consumer | ∀p, u: Consumer(u) ∧ Product(p) ∧ hasIngredientListStatus(p, complete) ∧ hasSomeIngredient(p) ∧ not unsafeFor(p, u) ∧ not cautionFor(p, u) ∧ not uncertainFor(p, u) → confirmedSafeFor(p, u) |
| E14 | Diet status uncertain (vegan) | ∀p, u: VeganConsumer(u) ∧ OriginUncertainProduct(p) ∧ not NonVeganProduct(p) → dietUncertainFor(p, u) |
| E15 | Diet status uncertain (vegetarian) | ∀p, u: VegetarianConsumer(u) ∧ OriginUncertainProduct(p) ∧ not NonVegetarianProduct(p) → dietUncertainFor(p, u) |
| E16 | Simple vegan-safe (plant) | ∀x: PlantDerivedIngredient(x) → SimpleVeganSafe(x) |
| E17 | Simple vegan-safe (other origin) | ∀x: OtherOriginIngredient(x) → SimpleVeganSafe(x) |
| E18 | Compound has a non-vegan-safe component | ∀c, x: hasComponent(x, c) ∧ not SimpleVeganSafe(c) → hasNonVeganSafeComponent(x) |
| E19 | Vegan-safe compound | ∀x: CompoundIngredient(x) ∧ not hasNonVeganSafeComponent(x) → VeganSafeIngredient(x) |
| E20 | Product has a non-vegan-safe ingredient | ∀i, p: hasIngredient(p, i) ∧ not VeganSafeIngredient(i) → hasNonVeganSafeIngredient(p) |
| E21 | Verified vegan product | ∀p: Product(p) ∧ hasIngredientListStatus(p, complete) ∧ hasSomeIngredient(p) ∧ not hasNonVeganSafeIngredient(p) → VerifiedVeganProduct(p) |
| E22 | Simple vegetarian-safe (vegan-safe) | ∀x: VeganSafeIngredient(x) → SimpleVegetarianSafe(x) |
| E23 | Simple vegetarian-safe (dairy) | ∀x: DairyIngredient(x) → SimpleVegetarianSafe(x) |
| E24 | Simple vegetarian-safe (egg) | ∀x: EggIngredient(x) → SimpleVegetarianSafe(x) |
| E25 | Simple vegetarian-safe (bee product) | ∀x: BeeProduct(x) → SimpleVegetarianSafe(x) |
| E26 | Vegetarian-safe ingredient | ∀x: SimpleVegetarianSafe(x) ∧ not NonVegetarianIngredient(x) → VegetarianSafeIngredient(x) |
| E27 | Compound has a non-vegetarian-safe component | ∀c, x: hasComponent(x, c) ∧ not SimpleVegetarianSafe(c) → hasNonVegetarianSafeComponent(x) |
| E28 | Vegetarian-safe compound | ∀x: CompoundIngredient(x) ∧ not hasNonVegetarianSafeComponent(x) ∧ not NonVegetarianIngredient(x) → VegetarianSafeIngredient(x) |
| E29 | Product has a non-vegetarian-safe ingredient | ∀i, p: hasIngredient(p, i) ∧ not VegetarianSafeIngredient(i) → hasNonVegetarianSafeIngredient(p) |
| E30 | Verified vegetarian product | ∀p: Product(p) ∧ hasIngredientListStatus(p, complete) ∧ hasSomeIngredient(p) ∧ not hasNonVegetarianSafeIngredient(p) → VerifiedVegetarianProduct(p) |
| A01 | Claim doubt from unspecified source | ∀a, c, i, p: hasLabelClaim(p, c) ∧ excludesAllergen(c, a) ∧ hasIngredient(p, i) ∧ possiblyTriggers(i, a) ∧ not containsAllergen(p, a) → claimDoubt(p, c) |
| A02 | Free-from claim verified | ∀c, p: hasLabelClaim(p, c) ∧ FreeFromClaim(c) ∧ hasIngredientListStatus(p, complete) ∧ hasSomeIngredient(p) ∧ not contradictsClaim(p, c) ∧ not precautionaryConflictWith(p, c) ∧ not claimDoubt(p, c) → claimVerified(p, c) |
| A03 | Vegan claim verified | ∀c, p: hasLabelClaim(p, c) ∧ VeganClaim(c) ∧ VerifiedVeganProduct(p) → claimVerified(p, c) |
| A04 | Vegetarian claim verified | ∀c, p: hasLabelClaim(p, c) ∧ VegetarianClaim(c) ∧ VerifiedVegetarianProduct(p) → claimVerified(p, c) |
| A05 | Lactose-free claim verified | ∀c, p: hasLabelClaim(p, c) ∧ LactoseFreeClaim(c) ∧ hasIngredientListStatus(p, complete) ∧ hasSomeIngredient(p) ∧ not contradictsClaim(p, c) → claimVerified(p, c) |
| A06 | Informational term | ∀c, p: hasLabelClaim(p, c) ∧ RegulatedMarketingTerm(c) → claimInformational(p, c) |
| A07 | Claim at risk | ∀c, p: hasLabelClaim(p, c) ∧ precautionaryConflictWith(p, c) ∧ not contradictsClaim(p, c) → claimAtRisk(p, c) |
| A08 | Claim contradicted | ∀c, p: contradictsClaim(p, c) → claimContradicted(p, c) |
| A09 | Claim unverifiable | ∀c, p: hasLabelClaim(p, c) ∧ not claimVerified(p, c) ∧ not contradictsClaim(p, c) ∧ not precautionaryConflictWith(p, c) ∧ not claimInformational(p, c) → claimUnverifiable(p, c) |

## Integrity constraints

| ID | Name | First-order form |
|---|---|---|
| I01 | Has a barcode value | ∀b, p: hasBarcode(p, b) → hasBarcodeValue(p) |
| I02 | Missing barcode | ∀p: Product(p) ∧ not hasBarcodeValue(p) → integrityViolation(p, "missing barcode") |
| I03 | Sold somewhere | ∀j, p: soldIn(p, j) → soldSomewhere(p) |
| I04 | Not sold anywhere | ∀p: Product(p) ∧ not soldSomewhere(p) → integrityViolation(p, "not sold in any jurisdiction") |
| I05 | Complete but empty record | ∀p: Product(p) ∧ hasIngredientListStatus(p, complete) ∧ not hasSomeIngredient(p) → integrityViolation(p, "ingredient list marked complete but empty") |
| I-DJ-1 | PlantDerivedIngredient and AnimalDerivedIngredient are disjoint | ∀x: PlantDerivedIngredient(x) ∧ AnimalDerivedIngredient(x) → disjointnessViolation(x, "PlantDerivedIngredient / AnimalDerivedIngredient") |
| I-DJ-2 | PlantDerivedIngredient and OtherOriginIngredient are disjoint | ∀x: PlantDerivedIngredient(x) ∧ OtherOriginIngredient(x) → disjointnessViolation(x, "PlantDerivedIngredient / OtherOriginIngredient") |
| I-DJ-3 | AnimalDerivedIngredient and OtherOriginIngredient are disjoint | ∀x: AnimalDerivedIngredient(x) ∧ OtherOriginIngredient(x) → disjointnessViolation(x, "AnimalDerivedIngredient / OtherOriginIngredient") |
| I-DJ-4 | CompoundIngredient and AnimalDerivedIngredient are disjoint | ∀x: CompoundIngredient(x) ∧ AnimalDerivedIngredient(x) → disjointnessViolation(x, "CompoundIngredient / AnimalDerivedIngredient") |
| I-DJ-5 | CompoundIngredient and PlantDerivedIngredient are disjoint | ∀x: CompoundIngredient(x) ∧ PlantDerivedIngredient(x) → disjointnessViolation(x, "CompoundIngredient / PlantDerivedIngredient") |

## Horn translation of the OWL axioms (205 rules)

| ID | Axiom | Rule |
|---|---|---|
| T-SC-Product-FoodEntity | Product ⊑ FoodEntity | Product(?x) -> FoodEntity(?x) |
| T-SC-Ingredient-FoodEntity | Ingredient ⊑ FoodEntity | Ingredient(?x) -> FoodEntity(?x) |
| T-SC-PlantDerivedIngredient-Ingredient | PlantDerivedIngredient ⊑ Ingredient | PlantDerivedIngredient(?x) -> Ingredient(?x) |
| T-SC-CerealIngredient-PlantDerivedIngredient | CerealIngredient ⊑ PlantDerivedIngredient | CerealIngredient(?x) -> PlantDerivedIngredient(?x) |
| T-SC-LegumeIngredient-PlantDerivedIngredient | LegumeIngredient ⊑ PlantDerivedIngredient | LegumeIngredient(?x) -> PlantDerivedIngredient(?x) |
| T-SC-TreeNutIngredient-PlantDerivedIngredient | TreeNutIngredient ⊑ PlantDerivedIngredient | TreeNutIngredient(?x) -> PlantDerivedIngredient(?x) |
| T-SC-SeedIngredient-PlantDerivedIngredient | SeedIngredient ⊑ PlantDerivedIngredient | SeedIngredient(?x) -> PlantDerivedIngredient(?x) |
| T-SC-VegetableIngredient-PlantDerivedIngredient | VegetableIngredient ⊑ PlantDerivedIngredient | VegetableIngredient(?x) -> PlantDerivedIngredient(?x) |
| T-SC-FruitIngredient-PlantDerivedIngredient | FruitIngredient ⊑ PlantDerivedIngredient | FruitIngredient(?x) -> PlantDerivedIngredient(?x) |
| T-SC-PlantOilOrFat-PlantDerivedIngredient | PlantOilOrFat ⊑ PlantDerivedIngredient | PlantOilOrFat(?x) -> PlantDerivedIngredient(?x) |
| T-SC-SugarOrSweetener-PlantDerivedIngredient | SugarOrSweetener ⊑ PlantDerivedIngredient | SugarOrSweetener(?x) -> PlantDerivedIngredient(?x) |
| T-SC-HerbOrSpice-PlantDerivedIngredient | HerbOrSpice ⊑ PlantDerivedIngredient | HerbOrSpice(?x) -> PlantDerivedIngredient(?x) |
| T-SC-CocoaIngredient-PlantDerivedIngredient | CocoaIngredient ⊑ PlantDerivedIngredient | CocoaIngredient(?x) -> PlantDerivedIngredient(?x) |
| T-SC-AnimalDerivedIngredient-Ingredient | AnimalDerivedIngredient ⊑ Ingredient | AnimalDerivedIngredient(?x) -> Ingredient(?x) |
| T-SC-VegetarianIncompatibleIngredient-Ingredient | VegetarianIncompatibleIngredient ⊑ Ingredient | VegetarianIncompatibleIngredient(?x) -> Ingredient(?x) |
| T-SC-DairyIngredient-AnimalDerivedIngredient | DairyIngredient ⊑ AnimalDerivedIngredient | DairyIngredient(?x) -> AnimalDerivedIngredient(?x) |
| T-SC-EggIngredient-AnimalDerivedIngredient | EggIngredient ⊑ AnimalDerivedIngredient | EggIngredient(?x) -> AnimalDerivedIngredient(?x) |
| T-SC-FishIngredient-AnimalDerivedIngredient | FishIngredient ⊑ AnimalDerivedIngredient | FishIngredient(?x) -> AnimalDerivedIngredient(?x) |
| T-SC-FishIngredient-VegetarianIncompatibleIngredient | FishIngredient ⊑ VegetarianIncompatibleIngredient | FishIngredient(?x) -> VegetarianIncompatibleIngredient(?x) |
| T-SC-CrustaceanIngredient-AnimalDerivedIngredient | CrustaceanIngredient ⊑ AnimalDerivedIngredient | CrustaceanIngredient(?x) -> AnimalDerivedIngredient(?x) |
| T-SC-CrustaceanIngredient-VegetarianIncompatibleIngredient | CrustaceanIngredient ⊑ VegetarianIncompatibleIngredient | CrustaceanIngredient(?x) -> VegetarianIncompatibleIngredient(?x) |
| T-SC-MolluscIngredient-AnimalDerivedIngredient | MolluscIngredient ⊑ AnimalDerivedIngredient | MolluscIngredient(?x) -> AnimalDerivedIngredient(?x) |
| T-SC-MolluscIngredient-VegetarianIncompatibleIngredient | MolluscIngredient ⊑ VegetarianIncompatibleIngredient | MolluscIngredient(?x) -> VegetarianIncompatibleIngredient(?x) |
| T-SC-MeatIngredient-AnimalDerivedIngredient | MeatIngredient ⊑ AnimalDerivedIngredient | MeatIngredient(?x) -> AnimalDerivedIngredient(?x) |
| T-SC-MeatIngredient-VegetarianIncompatibleIngredient | MeatIngredient ⊑ VegetarianIncompatibleIngredient | MeatIngredient(?x) -> VegetarianIncompatibleIngredient(?x) |
| T-SC-SlaughterByproduct-AnimalDerivedIngredient | SlaughterByproduct ⊑ AnimalDerivedIngredient | SlaughterByproduct(?x) -> AnimalDerivedIngredient(?x) |
| T-SC-SlaughterByproduct-VegetarianIncompatibleIngredient | SlaughterByproduct ⊑ VegetarianIncompatibleIngredient | SlaughterByproduct(?x) -> VegetarianIncompatibleIngredient(?x) |
| T-SC-InsectDerivedIngredient-AnimalDerivedIngredient | InsectDerivedIngredient ⊑ AnimalDerivedIngredient | InsectDerivedIngredient(?x) -> AnimalDerivedIngredient(?x) |
| T-SC-InsectDerivedIngredient-VegetarianIncompatibleIngredient | InsectDerivedIngredient ⊑ VegetarianIncompatibleIngredient | InsectDerivedIngredient(?x) -> VegetarianIncompatibleIngredient(?x) |
| T-SC-BeeProduct-AnimalDerivedIngredient | BeeProduct ⊑ AnimalDerivedIngredient | BeeProduct(?x) -> AnimalDerivedIngredient(?x) |
| T-SC-OtherOriginIngredient-Ingredient | OtherOriginIngredient ⊑ Ingredient | OtherOriginIngredient(?x) -> Ingredient(?x) |
| T-SC-MineralOrSyntheticIngredient-OtherOriginIngredient | MineralOrSyntheticIngredient ⊑ OtherOriginIngredient | MineralOrSyntheticIngredient(?x) -> OtherOriginIngredient(?x) |
| T-SC-MicrobialIngredient-OtherOriginIngredient | MicrobialIngredient ⊑ OtherOriginIngredient | MicrobialIngredient(?x) -> OtherOriginIngredient(?x) |
| T-SC-CompoundIngredient-Ingredient | CompoundIngredient ⊑ Ingredient | CompoundIngredient(?x) -> Ingredient(?x) |
| T-SC-UnspecifiedOriginIngredient-Ingredient | UnspecifiedOriginIngredient ⊑ Ingredient | UnspecifiedOriginIngredient(?x) -> Ingredient(?x) |
| T-SC-GlutenSourceIngredient-Ingredient | GlutenSourceIngredient ⊑ Ingredient | GlutenSourceIngredient(?x) -> Ingredient(?x) |
| T-SC-LactoseSourceIngredient-Ingredient | LactoseSourceIngredient ⊑ Ingredient | LactoseSourceIngredient(?x) -> Ingredient(?x) |
| T-SC-AllergenCategory-Allergen | AllergenCategory ⊑ Allergen | AllergenCategory(?x) -> Allergen(?x) |
| T-SC-SpecificAllergen-Allergen | SpecificAllergen ⊑ Allergen | SpecificAllergen(?x) -> Allergen(?x) |
| T-SC-DietClaim-LabelClaim | DietClaim ⊑ LabelClaim | DietClaim(?x) -> LabelClaim(?x) |
| T-SC-VeganClaim-DietClaim | VeganClaim ⊑ DietClaim | VeganClaim(?x) -> DietClaim(?x) |
| T-SC-VegetarianClaim-DietClaim | VegetarianClaim ⊑ DietClaim | VegetarianClaim(?x) -> DietClaim(?x) |
| T-SC-FreeFromClaim-LabelClaim | FreeFromClaim ⊑ LabelClaim | FreeFromClaim(?x) -> LabelClaim(?x) |
| T-SC-GlutenFreeClaim-FreeFromClaim | GlutenFreeClaim ⊑ FreeFromClaim | GlutenFreeClaim(?x) -> FreeFromClaim(?x) |
| T-SC-DairyFreeClaim-FreeFromClaim | DairyFreeClaim ⊑ FreeFromClaim | DairyFreeClaim(?x) -> FreeFromClaim(?x) |
| T-SC-NutFreeClaim-FreeFromClaim | NutFreeClaim ⊑ FreeFromClaim | NutFreeClaim(?x) -> FreeFromClaim(?x) |
| T-SC-PeanutFreeClaim-FreeFromClaim | PeanutFreeClaim ⊑ FreeFromClaim | PeanutFreeClaim(?x) -> FreeFromClaim(?x) |
| T-SC-EggFreeClaim-FreeFromClaim | EggFreeClaim ⊑ FreeFromClaim | EggFreeClaim(?x) -> FreeFromClaim(?x) |
| T-SC-SoyFreeClaim-FreeFromClaim | SoyFreeClaim ⊑ FreeFromClaim | SoyFreeClaim(?x) -> FreeFromClaim(?x) |
| T-SC-IntoleranceClaim-LabelClaim | IntoleranceClaim ⊑ LabelClaim | IntoleranceClaim(?x) -> LabelClaim(?x) |
| T-SC-LactoseFreeClaim-IntoleranceClaim | LactoseFreeClaim ⊑ IntoleranceClaim | LactoseFreeClaim(?x) -> IntoleranceClaim(?x) |
| T-SC-RegulatedMarketingTerm-LabelClaim | RegulatedMarketingTerm ⊑ LabelClaim | RegulatedMarketingTerm(?x) -> LabelClaim(?x) |
| T-SC-NonDairyClaim-RegulatedMarketingTerm | NonDairyClaim ⊑ RegulatedMarketingTerm | NonDairyClaim(?x) -> RegulatedMarketingTerm(?x) |
| T-SC-USJurisdiction-Jurisdiction | USJurisdiction ⊑ Jurisdiction | USJurisdiction(?x) -> Jurisdiction(?x) |
| T-SC-CanadaJurisdiction-Jurisdiction | CanadaJurisdiction ⊑ Jurisdiction | CanadaJurisdiction(?x) -> Jurisdiction(?x) |
| T-SC-EUJurisdiction-Jurisdiction | EUJurisdiction ⊑ Jurisdiction | EUJurisdiction(?x) -> Jurisdiction(?x) |
| T-SC-VegetarianConsumer-Consumer | VegetarianConsumer ⊑ Consumer | VegetarianConsumer(?x) -> Consumer(?x) |
| T-SC-VeganConsumer-VegetarianConsumer | VeganConsumer ⊑ VegetarianConsumer | VeganConsumer(?x) -> VegetarianConsumer(?x) |
| T-SC-MeetsGlutenFreeThreshold-Product | MeetsGlutenFreeThreshold ⊑ Product | MeetsGlutenFreeThreshold(?x) -> Product(?x) |
| T-SC-SulphiteAtOrAbove10ppm-Product | SulphiteAtOrAbove10ppm ⊑ Product | SulphiteAtOrAbove10ppm(?x) -> Product(?x) |
| T-SC-SulphiteAbove10ppm-SulphiteAtOrAbove10ppm | SulphiteAbove10ppm ⊑ SulphiteAtOrAbove10ppm | SulphiteAbove10ppm(?x) -> SulphiteAtOrAbove10ppm(?x) |
| T-SC-NonVeganIngredient-Ingredient | NonVeganIngredient ⊑ Ingredient | NonVeganIngredient(?x) -> Ingredient(?x) |
| T-DEF-NonVeganIngredient-1 | Definition of NonVeganIngredient (case 1) | AnimalDerivedIngredient(?i) -> NonVeganIngredient(?i) |
| T-DEF-NonVeganIngredient-2 | Definition of NonVeganIngredient (case 2) | hasComponent(?i, ?c), AnimalDerivedIngredient(?c) -> NonVeganIngredient(?i) |
| T-SC-NonVegetarianIngredient-Ingredient | NonVegetarianIngredient ⊑ Ingredient | NonVegetarianIngredient(?x) -> Ingredient(?x) |
| T-DEF-NonVegetarianIngredient-1 | Definition of NonVegetarianIngredient (case 1) | VegetarianIncompatibleIngredient(?i) -> NonVegetarianIngredient(?i) |
| T-DEF-NonVegetarianIngredient-2 | Definition of NonVegetarianIngredient (case 2) | hasComponent(?i, ?c), VegetarianIncompatibleIngredient(?c) -> NonVegetarianIngredient(?i) |
| T-DEF-NonVegetarianIngredient-3 | Definition of NonVegetarianIngredient (case 3) | derivedFrom(?i, ?c), VegetarianIncompatibleIngredient(?c) -> NonVegetarianIngredient(?i) |
| T-SC-VeganSafeIngredient-Ingredient | VeganSafeIngredient ⊑ Ingredient | VeganSafeIngredient(?x) -> Ingredient(?x) |
| T-DEF-VeganSafeIngredient-1 | Definition of VeganSafeIngredient (case 1) | PlantDerivedIngredient(?i) -> VeganSafeIngredient(?i) |
| T-DEF-VeganSafeIngredient-2 | Definition of VeganSafeIngredient (case 2) | OtherOriginIngredient(?i) -> VeganSafeIngredient(?i) |
| T-SC-NonVeganProduct-Product | NonVeganProduct ⊑ Product | NonVeganProduct(?x) -> Product(?x) |
| T-DEF-NonVeganProduct-1 | Definition of NonVeganProduct (case 1) | Product(?p), hasIngredient(?p, ?i), NonVeganIngredient(?i) -> NonVeganProduct(?p) |
| T-SC-NonVegetarianProduct-Product | NonVegetarianProduct ⊑ Product | NonVegetarianProduct(?x) -> Product(?x) |
| T-DEF-NonVegetarianProduct-1 | Definition of NonVegetarianProduct (case 1) | Product(?p), hasIngredient(?p, ?i), NonVegetarianIngredient(?i) -> NonVegetarianProduct(?p) |
| T-SC-OriginUncertainProduct-Product | OriginUncertainProduct ⊑ Product | OriginUncertainProduct(?x) -> Product(?x) |
| T-DEF-OriginUncertainProduct-1 | Definition of OriginUncertainProduct (case 1) | Product(?p), hasIngredient(?p, ?i), UnspecifiedOriginIngredient(?i) -> OriginUncertainProduct(?p) |
| T-DEF-OriginUncertainProduct-2 | Definition of OriginUncertainProduct (case 2) | Product(?p), hasIngredient(?p, ?i), hasComponent(?i, ?c), UnspecifiedOriginIngredient(?c) -> OriginUncertainProduct(?p) |
| T-SC-VeganCompatibleProduct-Product | VeganCompatibleProduct ⊑ Product | VeganCompatibleProduct(?x) -> Product(?x) |
| T-SC-GlutenContainingProduct-Product | GlutenContainingProduct ⊑ Product | GlutenContainingProduct(?x) -> Product(?x) |
| T-DEF-GlutenContainingProduct-1 | Definition of GlutenContainingProduct (case 1) | Product(?p), hasIngredient(?p, ?i), GlutenSourceIngredient(?i) -> GlutenContainingProduct(?p) |
| T-SC-AllergenContainingProduct-Product | AllergenContainingProduct ⊑ Product | AllergenContainingProduct(?x) -> Product(?x) |
| T-DEF-AllergenContainingProduct-1 | Definition of AllergenContainingProduct (case 1) | Product(?p), containsAllergen(?p, ?a) -> AllergenContainingProduct(?p) |
| T-SC-PrecautionaryLabelledProduct-Product | PrecautionaryLabelledProduct ⊑ Product | PrecautionaryLabelledProduct(?x) -> Product(?x) |
| T-DEF-PrecautionaryLabelledProduct-1 | Definition of PrecautionaryLabelledProduct (case 1) | Product(?p), mayContain(?p, ?a) -> PrecautionaryLabelledProduct(?p) |
| T-SC-ClaimConflictProduct-Product | ClaimConflictProduct ⊑ Product | ClaimConflictProduct(?x) -> Product(?x) |
| T-DEF-ClaimConflictProduct-1 | Definition of ClaimConflictProduct (case 1) | Product(?p), contradictsClaim(?p, ?c) -> ClaimConflictProduct(?p) |
| T-SC-PrecautionaryConflictProduct-Product | PrecautionaryConflictProduct ⊑ Product | PrecautionaryConflictProduct(?x) -> Product(?x) |
| T-DEF-PrecautionaryConflictProduct-1 | Definition of PrecautionaryConflictProduct (case 1) | Product(?p), precautionaryConflictWith(?p, ?c) -> PrecautionaryConflictProduct(?p) |
| T-SC-MultiMarketProduct-Product | MultiMarketProduct ⊑ Product | MultiMarketProduct(?x) -> Product(?x) |
| T-DEF-MultiMarketProduct-1 | Definition of MultiMarketProduct (case 1) | Product(?p), soldIn(?p, ?j1), soldIn(?p, ?j2), notEqual(?j1, ?j2) -> MultiMarketProduct(?p) |
| T-SC-IncompleteRecordProduct-Product | IncompleteRecordProduct ⊑ Product | IncompleteRecordProduct(?x) -> Product(?x) |
| T-DEF-IncompleteRecordProduct-1 | Definition of IncompleteRecordProduct (case 1) | Product(?p), hasIngredientListStatus(?p, "incomplete") -> IncompleteRecordProduct(?p) |
| T-GCI-1 | General axiom: ... ⊑ AnimalDerivedIngredient | derivedFrom(?i, ?j), AnimalDerivedIngredient(?j) -> AnimalDerivedIngredient(?i) |
| T-GCI-2 | General axiom: ... ⊑ GlutenSourceIngredient | hasComponent(?i, ?c), GlutenSourceIngredient(?c) -> GlutenSourceIngredient(?i) |
| T-GCI-3 | General axiom: ... ⊑ LactoseSourceIngredient | hasComponent(?i, ?c), LactoseSourceIngredient(?c) -> LactoseSourceIngredient(?i) |
| T-HV-1 | GlutenContainingProduct ⊑ containsAllergen value alg_gluten | GlutenContainingProduct(?p) -> containsAllergen(?p, alg_gluten) |
| T-DOM-hasIngredient | domain(hasIngredient) = Product | hasIngredient(?x, ?y) -> Product(?x) |
| T-RNG-hasIngredient | range(hasIngredient) = Ingredient | hasIngredient(?x, ?y) -> Ingredient(?y) |
| T-INV-isIngredientOf | isIngredientOf is the inverse of hasIngredient | hasIngredient(?x, ?y) -> isIngredientOf(?y, ?x) |
| T-INV-hasIngredient | hasIngredient is the inverse of isIngredientOf | isIngredientOf(?x, ?y) -> hasIngredient(?y, ?x) |
| T-DOM-isIngredientOf | domain(isIngredientOf) = Ingredient | isIngredientOf(?x, ?y) -> Ingredient(?x) |
| T-RNG-isIngredientOf | range(isIngredientOf) = Product | isIngredientOf(?x, ?y) -> Product(?y) |
| T-TR-hasComponent | hasComponent is transitive | hasComponent(?x, ?y), hasComponent(?y, ?z) -> hasComponent(?x, ?z) |
| T-DOM-hasComponent | domain(hasComponent) = Ingredient | hasComponent(?x, ?y) -> Ingredient(?x) |
| T-RNG-hasComponent | range(hasComponent) = Ingredient | hasComponent(?x, ?y) -> Ingredient(?y) |
| T-TR-derivedFrom | derivedFrom is transitive | derivedFrom(?x, ?y), derivedFrom(?y, ?z) -> derivedFrom(?x, ?z) |
| T-DOM-derivedFrom | domain(derivedFrom) = Ingredient | derivedFrom(?x, ?y) -> Ingredient(?x) |
| T-RNG-derivedFrom | range(derivedFrom) = Ingredient | derivedFrom(?x, ?y) -> Ingredient(?y) |
| T-TR-retainsAllergensOf | retainsAllergensOf is transitive | retainsAllergensOf(?x, ?y), retainsAllergensOf(?y, ?z) -> retainsAllergensOf(?x, ?z) |
| T-SP-retainsAllergensOf | retainsAllergensOf ⊑ derivedFrom | retainsAllergensOf(?x, ?y) -> derivedFrom(?x, ?y) |
| T-DOM-retainsAllergensOf | domain(retainsAllergensOf) = Ingredient | retainsAllergensOf(?x, ?y) -> Ingredient(?x) |
| T-RNG-retainsAllergensOf | range(retainsAllergensOf) = Ingredient | retainsAllergensOf(?x, ?y) -> Ingredient(?y) |
| T-DOM-triggersAllergen | domain(triggersAllergen) = Ingredient | triggersAllergen(?x, ?y) -> Ingredient(?x) |
| T-RNG-triggersAllergen | range(triggersAllergen) = Allergen | triggersAllergen(?x, ?y) -> Allergen(?y) |
| T-DOM-possiblyTriggers | domain(possiblyTriggers) = Ingredient | possiblyTriggers(?x, ?y) -> Ingredient(?x) |
| T-RNG-possiblyTriggers | range(possiblyTriggers) = Allergen | possiblyTriggers(?x, ?y) -> Allergen(?y) |
| T-TR-isSubtypeOf | isSubtypeOf is transitive | isSubtypeOf(?x, ?y), isSubtypeOf(?y, ?z) -> isSubtypeOf(?x, ?z) |
| T-DOM-isSubtypeOf | domain(isSubtypeOf) = Allergen | isSubtypeOf(?x, ?y) -> Allergen(?x) |
| T-RNG-isSubtypeOf | range(isSubtypeOf) = Allergen | isSubtypeOf(?x, ?y) -> Allergen(?y) |
| T-DOM-containsAllergen | domain(containsAllergen) = Product | containsAllergen(?x, ?y) -> Product(?x) |
| T-RNG-containsAllergen | range(containsAllergen) = Allergen | containsAllergen(?x, ?y) -> Allergen(?y) |
| T-DOM-mayContain | domain(mayContain) = Product | mayContain(?x, ?y) -> Product(?x) |
| T-RNG-mayContain | range(mayContain) = Allergen | mayContain(?x, ?y) -> Allergen(?y) |
| T-DOM-hasLabelClaim | domain(hasLabelClaim) = Product | hasLabelClaim(?x, ?y) -> Product(?x) |
| T-RNG-hasLabelClaim | range(hasLabelClaim) = LabelClaim | hasLabelClaim(?x, ?y) -> LabelClaim(?y) |
| T-DOM-excludesAllergen | domain(excludesAllergen) = LabelClaim | excludesAllergen(?x, ?y) -> LabelClaim(?x) |
| T-RNG-excludesAllergen | range(excludesAllergen) = Allergen | excludesAllergen(?x, ?y) -> Allergen(?y) |
| T-DOM-contradictsClaim | domain(contradictsClaim) = Product | contradictsClaim(?x, ?y) -> Product(?x) |
| T-RNG-contradictsClaim | range(contradictsClaim) = LabelClaim | contradictsClaim(?x, ?y) -> LabelClaim(?y) |
| T-DOM-precautionaryConflictWith | domain(precautionaryConflictWith) = Product | precautionaryConflictWith(?x, ?y) -> Product(?x) |
| T-RNG-precautionaryConflictWith | range(precautionaryConflictWith) = LabelClaim | precautionaryConflictWith(?x, ?y) -> LabelClaim(?y) |
| T-DOM-soldIn | domain(soldIn) = Product | soldIn(?x, ?y) -> Product(?x) |
| T-RNG-soldIn | range(soldIn) = Jurisdiction | soldIn(?x, ?y) -> Jurisdiction(?y) |
| T-DOM-requiresDeclarationOf | domain(requiresDeclarationOf) = Jurisdiction | requiresDeclarationOf(?x, ?y) -> Jurisdiction(?x) |
| T-RNG-requiresDeclarationOf | range(requiresDeclarationOf) = Allergen | requiresDeclarationOf(?x, ?y) -> Allergen(?y) |
| T-DOM-mustDeclare | domain(mustDeclare) = Product | mustDeclare(?x, ?y) -> Product(?x) |
| T-RNG-mustDeclare | range(mustDeclare) = Allergen | mustDeclare(?x, ?y) -> Allergen(?y) |
| T-SP-mustDeclareInUS | mustDeclareInUS ⊑ mustDeclare | mustDeclareInUS(?x, ?y) -> mustDeclare(?x, ?y) |
| T-DOM-mustDeclareInUS | domain(mustDeclareInUS) = Product | mustDeclareInUS(?x, ?y) -> Product(?x) |
| T-RNG-mustDeclareInUS | range(mustDeclareInUS) = Allergen | mustDeclareInUS(?x, ?y) -> Allergen(?y) |
| T-SP-mustDeclareInCanada | mustDeclareInCanada ⊑ mustDeclare | mustDeclareInCanada(?x, ?y) -> mustDeclare(?x, ?y) |
| T-DOM-mustDeclareInCanada | domain(mustDeclareInCanada) = Product | mustDeclareInCanada(?x, ?y) -> Product(?x) |
| T-RNG-mustDeclareInCanada | range(mustDeclareInCanada) = Allergen | mustDeclareInCanada(?x, ?y) -> Allergen(?y) |
| T-SP-mustDeclareInEU | mustDeclareInEU ⊑ mustDeclare | mustDeclareInEU(?x, ?y) -> mustDeclare(?x, ?y) |
| T-DOM-mustDeclareInEU | domain(mustDeclareInEU) = Product | mustDeclareInEU(?x, ?y) -> Product(?x) |
| T-RNG-mustDeclareInEU | range(mustDeclareInEU) = Allergen | mustDeclareInEU(?x, ?y) -> Allergen(?y) |
| T-DOM-declaresAllergen | domain(declaresAllergen) = Product | declaresAllergen(?x, ?y) -> Product(?x) |
| T-RNG-declaresAllergen | range(declaresAllergen) = Allergen | declaresAllergen(?x, ?y) -> Allergen(?y) |
| T-DOM-mustAvoid | domain(mustAvoid) = Consumer | mustAvoid(?x, ?y) -> Consumer(?x) |
| T-RNG-mustAvoid | range(mustAvoid) = Allergen | mustAvoid(?x, ?y) -> Allergen(?y) |
| T-DOM-unsafeFor | domain(unsafeFor) = Product | unsafeFor(?x, ?y) -> Product(?x) |
| T-RNG-unsafeFor | range(unsafeFor) = Consumer | unsafeFor(?x, ?y) -> Consumer(?y) |
| T-DOM-cautionFor | domain(cautionFor) = Product | cautionFor(?x, ?y) -> Product(?x) |
| T-RNG-cautionFor | range(cautionFor) = Consumer | cautionFor(?x, ?y) -> Consumer(?y) |
| T-DOM-unsuitableForDietOf | domain(unsuitableForDietOf) = Product | unsuitableForDietOf(?x, ?y) -> Product(?x) |
| T-RNG-unsuitableForDietOf | range(unsuitableForDietOf) = Consumer | unsuitableForDietOf(?x, ?y) -> Consumer(?y) |
| T-DOM-inCategory | domain(inCategory) = Product | inCategory(?x, ?y) -> Product(?x) |
| T-RNG-inCategory | range(inCategory) = ProductCategory | inCategory(?x, ?y) -> ProductCategory(?y) |
| T-DOM-exemptIngredient | domain(exemptIngredient) = DeclarationExemption | exemptIngredient(?x, ?y) -> DeclarationExemption(?x) |
| T-RNG-exemptIngredient | range(exemptIngredient) = Ingredient | exemptIngredient(?x, ?y) -> Ingredient(?y) |
| T-DOM-exemptAllergen | domain(exemptAllergen) = DeclarationExemption | exemptAllergen(?x, ?y) -> DeclarationExemption(?x) |
| T-RNG-exemptAllergen | range(exemptAllergen) = Allergen | exemptAllergen(?x, ?y) -> Allergen(?y) |
| T-DOM-exemptJurisdiction | domain(exemptJurisdiction) = DeclarationExemption | exemptJurisdiction(?x, ?y) -> DeclarationExemption(?x) |
| T-RNG-exemptJurisdiction | range(exemptJurisdiction) = Jurisdiction | exemptJurisdiction(?x, ?y) -> Jurisdiction(?y) |
| T-DOM-hasBarcode | domain(hasBarcode) = Product | hasBarcode(?x, ?v) -> Product(?x) |
| T-DOM-hasIngredientListStatus | domain(hasIngredientListStatus) = Product | hasIngredientListStatus(?x, ?v) -> Product(?x) |
| T-DOM-hasGlutenPPM | domain(hasGlutenPPM) = Product | hasGlutenPPM(?x, ?v) -> Product(?x) |
| T-DOM-hasSulphiteMgPerKg | domain(hasSulphiteMgPerKg) = Product | hasSulphiteMgPerKg(?x, ?v) -> Product(?x) |
| T-CH-1 | retainsAllergensOf ∘ triggersAllergen ⊑ triggersAllergen | retainsAllergensOf(?x, ?y), triggersAllergen(?y, ?z) -> triggersAllergen(?x, ?z) |
| T-CH-2 | hasComponent ∘ triggersAllergen ⊑ triggersAllergen | hasComponent(?x, ?y), triggersAllergen(?y, ?z) -> triggersAllergen(?x, ?z) |
| T-CH-3 | containsAllergen ∘ isSubtypeOf ⊑ containsAllergen | containsAllergen(?x, ?y), isSubtypeOf(?y, ?z) -> containsAllergen(?x, ?z) |
| T-CH-4 | mayContain ∘ isSubtypeOf ⊑ mayContain | mayContain(?x, ?y), isSubtypeOf(?y, ?z) -> mayContain(?x, ?z) |
| T-DEF-ContainsMilkProduct | ContainsMilkProduct ≡ Product ⊓ containsAllergen value alg_milk | Product(?p), containsAllergen(?p, alg_milk) -> ContainsMilkProduct(?p) |
| T-SC-ContainsMilkProduct-Product | ContainsMilkProduct ⊑ Product | ContainsMilkProduct(?x) -> Product(?x) |
| T-DEF-ContainsEggProduct | ContainsEggProduct ≡ Product ⊓ containsAllergen value alg_egg | Product(?p), containsAllergen(?p, alg_egg) -> ContainsEggProduct(?p) |
| T-SC-ContainsEggProduct-Product | ContainsEggProduct ⊑ Product | ContainsEggProduct(?x) -> Product(?x) |
| T-DEF-ContainsFishProduct | ContainsFishProduct ≡ Product ⊓ containsAllergen value alg_fish | Product(?p), containsAllergen(?p, alg_fish) -> ContainsFishProduct(?p) |
| T-SC-ContainsFishProduct-Product | ContainsFishProduct ⊑ Product | ContainsFishProduct(?x) -> Product(?x) |
| T-DEF-ContainsCrustaceanProduct | ContainsCrustaceanProduct ≡ Product ⊓ containsAllergen value alg_crustacean | Product(?p), containsAllergen(?p, alg_crustacean) -> ContainsCrustaceanProduct(?p) |
| T-SC-ContainsCrustaceanProduct-Product | ContainsCrustaceanProduct ⊑ Product | ContainsCrustaceanProduct(?x) -> Product(?x) |
| T-DEF-ContainsMolluscProduct | ContainsMolluscProduct ≡ Product ⊓ containsAllergen value alg_mollusc | Product(?p), containsAllergen(?p, alg_mollusc) -> ContainsMolluscProduct(?p) |
| T-SC-ContainsMolluscProduct-Product | ContainsMolluscProduct ⊑ Product | ContainsMolluscProduct(?x) -> Product(?x) |
| T-DEF-ContainsTreeNutsProduct | ContainsTreeNutsProduct ≡ Product ⊓ containsAllergen value alg_tree_nuts | Product(?p), containsAllergen(?p, alg_tree_nuts) -> ContainsTreeNutsProduct(?p) |
| T-SC-ContainsTreeNutsProduct-Product | ContainsTreeNutsProduct ⊑ Product | ContainsTreeNutsProduct(?x) -> Product(?x) |
| T-DEF-ContainsPeanutProduct | ContainsPeanutProduct ≡ Product ⊓ containsAllergen value alg_peanut | Product(?p), containsAllergen(?p, alg_peanut) -> ContainsPeanutProduct(?p) |
| T-SC-ContainsPeanutProduct-Product | ContainsPeanutProduct ⊑ Product | ContainsPeanutProduct(?x) -> Product(?x) |
| T-DEF-ContainsSoyProduct | ContainsSoyProduct ≡ Product ⊓ containsAllergen value alg_soy | Product(?p), containsAllergen(?p, alg_soy) -> ContainsSoyProduct(?p) |
| T-SC-ContainsSoyProduct-Product | ContainsSoyProduct ⊑ Product | ContainsSoyProduct(?x) -> Product(?x) |
| T-DEF-ContainsSesameProduct | ContainsSesameProduct ≡ Product ⊓ containsAllergen value alg_sesame | Product(?p), containsAllergen(?p, alg_sesame) -> ContainsSesameProduct(?p) |
| T-SC-ContainsSesameProduct-Product | ContainsSesameProduct ⊑ Product | ContainsSesameProduct(?x) -> Product(?x) |
| T-DEF-ContainsMustardProduct | ContainsMustardProduct ≡ Product ⊓ containsAllergen value alg_mustard | Product(?p), containsAllergen(?p, alg_mustard) -> ContainsMustardProduct(?p) |
| T-SC-ContainsMustardProduct-Product | ContainsMustardProduct ⊑ Product | ContainsMustardProduct(?x) -> Product(?x) |
| T-DEF-ContainsCeleryProduct | ContainsCeleryProduct ≡ Product ⊓ containsAllergen value alg_celery | Product(?p), containsAllergen(?p, alg_celery) -> ContainsCeleryProduct(?p) |
| T-SC-ContainsCeleryProduct-Product | ContainsCeleryProduct ⊑ Product | ContainsCeleryProduct(?x) -> Product(?x) |
| T-DEF-ContainsLupinProduct | ContainsLupinProduct ≡ Product ⊓ containsAllergen value alg_lupin | Product(?p), containsAllergen(?p, alg_lupin) -> ContainsLupinProduct(?p) |
| T-SC-ContainsLupinProduct-Product | ContainsLupinProduct ⊑ Product | ContainsLupinProduct(?x) -> Product(?x) |
| T-DEF-ContainsSulphitesProduct | ContainsSulphitesProduct ≡ Product ⊓ containsAllergen value alg_sulphites | Product(?p), containsAllergen(?p, alg_sulphites) -> ContainsSulphitesProduct(?p) |
| T-SC-ContainsSulphitesProduct-Product | ContainsSulphitesProduct ⊑ Product | ContainsSulphitesProduct(?x) -> Product(?x) |
| T-DEF-ContainsGlutenCerealsProduct | ContainsGlutenCerealsProduct ≡ Product ⊓ containsAllergen value alg_gluten_cereals | Product(?p), containsAllergen(?p, alg_gluten_cereals) -> ContainsGlutenCerealsProduct(?p) |
| T-SC-ContainsGlutenCerealsProduct-Product | ContainsGlutenCerealsProduct ⊑ Product | ContainsGlutenCerealsProduct(?x) -> Product(?x) |
| T-DEF-ContainsWheatProduct | ContainsWheatProduct ≡ Product ⊓ containsAllergen value alg_wheat | Product(?p), containsAllergen(?p, alg_wheat) -> ContainsWheatProduct(?p) |
| T-SC-ContainsWheatProduct-Product | ContainsWheatProduct ⊑ Product | ContainsWheatProduct(?x) -> Product(?x) |
| T-DEF-ContainsGlutenProduct | ContainsGlutenProduct ≡ Product ⊓ containsAllergen value alg_gluten | Product(?p), containsAllergen(?p, alg_gluten) -> ContainsGlutenProduct(?p) |
| T-SC-ContainsGlutenProduct-Product | ContainsGlutenProduct ⊑ Product | ContainsGlutenProduct(?x) -> Product(?x) |
