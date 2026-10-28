# FALCON competency questions

## CQ01. Which ingredients are made from milk, directly or indirectly?

*Type:* lookup + transitive reasoning

> 9 ingredients asserted as made directly from milk; reasoning finds 14 in total.

| ingredient | how it is known |
|---|---|
| Buttermilk | asserted |
| Casein | asserted |
| Cream | asserted |
| Lactose-free milk | asserted |
| Mozzarella cheese | asserted |
| Parmesan cheese | asserted |
| Skimmed milk powder | asserted |
| Whey | asserted |
| Whole milk powder | asserted |
| Butter | inferred (sub-property + transitivity) |
| Ghee (clarified butter) | inferred (sub-property + transitivity) |
| Lactose | inferred (sub-property + transitivity) |
| Sodium caseinate | inferred (sub-property + transitivity) |
| Whey powder | inferred (sub-property + transitivity) |

SPARQL over the Pellet-materialised ontology:

```sparql
SELECT DISTINCT ?ingredient WHERE { ?ingredient falcon:derivedFrom falcon:ing_milk . }
```

## CQ02. Which allergens does Smoky Steakhouse Sauce contain, and through which ingredient?

*Type:* complex reasoning + proof

> Backward chaining proves containsAllergen(prod_steakhouse_sauce, alg_fish) from asserted facts only.

| allergen | via ingredient | hidden from shoppers |
|---|---|---|
| Fish | Worcestershire sauce | yes |

```
containsAllergen(prod_steakhouse_sauce, alg_fish)   [R01: Product allergen detection]
|-- Product(prod_steakhouse_sauce)   [asserted fact]
|-- hasIngredient(prod_steakhouse_sauce, ing_worcestershire_sauce)   [asserted fact]
`-- triggersAllergen(ing_worcestershire_sauce, alg_fish)   [T-CH-2: hasComponent ∘ triggersAllergen ⊑ triggersAllergen]
    |-- hasComponent(ing_worcestershire_sauce, ing_anchovy)   [asserted fact]
    `-- triggersAllergen(ing_anchovy, alg_fish)   [asserted fact]
```

SPARQL over the Pellet-materialised ontology:

```sparql
SELECT DISTINCT ?allergen WHERE { falcon:prod_steakhouse_sauce falcon:containsAllergen ?allergen . }
```

## CQ03. Which products contradict their own label claims, and why?

*Type:* rule-based inference

> 10 of 45 claims are contradicted by the products' own composition.

| product | claim | rule | evidence |
|---|---|---|---|
| Creamy Coleslaw | Egg-free | R02 | Egg via Mayonnaise |
| Crispy Malt Flakes | Gluten-free | R14 | Gluten (coeliac hazard) via Barley malt extract; lab result 45 ppm is not below 20 ppm |
| Eggplant Parmigiana | Vegetarian | R04 | Parmesan cheese (contains Animal rennet) |
| Fruit Gummies | Vegetarian | R04 | Carmine (E120); Gelatin (pork or beef) |
| Green Curry Paste | Vegetarian | R04 | Shrimp paste |
| Honey Oat Bar | Vegan | R03 | Honey |
| Pesto Genovese | Vegetarian | R04 | Parmesan cheese (contains Animal rennet) |
| Brewed Soy Sauce | Gluten-free | R02 | Gluten (coeliac hazard) via Wheat |
| Smoky Steakhouse Sauce | Vegan | R03 | Worcestershire sauce (contains Anchovy) |
| Vegan Berry Gummies | Vegan | R03 | Carmine (E120) |

SPARQL over the Pellet-materialised ontology:

```sparql
SELECT ?product ?claim WHERE { ?product falcon:contradictsClaim ?claim . } ORDER BY ?product
```

## CQ04. Which free-from claims are undermined by a 'may contain' warning?

*Type:* rule-based inference

| product | claim | 'may contain' |
|---|---|---|
| Dark Chocolate 70% | Dairy-free | Milk |
| Nut-Free Granola Bar | Nut-free | Tree nuts |

SPARQL over the Pellet-materialised ontology:

```sparql
SELECT ?product ?claim ?allergen WHERE { ?product falcon:precautionaryConflictWith ?claim . ?claim falcon:excludesAllergen ?allergen . ?product falcon:mayContain ?allergen . }
```

## CQ05. Which products are unsafe, or need caution, for Liam (peanut and tree nut allergy)?

*Type:* personalised reasoning

> Liam avoids peanut and tree nuts; isSubtypeOf lets 'tree nuts' match almond, hazelnut and pine nut.

| product | status | because |
|---|---|---|
| Almond Butter Cookies | UNSAFE | Tree nuts |
| Classic Trail Mix | UNSAFE | Peanut, Tree nuts |
| Hazelnut Cocoa Spread | UNSAFE | Tree nuts |
| Honey Oat Bar | UNSAFE | Tree nuts |
| Peanut Butter Cups | UNSAFE | Peanut |
| Pesto Genovese | UNSAFE | Tree nuts |
| Smooth Peanut Butter | UNSAFE | Peanut |
| Dark Chocolate 70% | CAUTION | Tree nuts |
| Nut-Free Granola Bar | CAUTION | Tree nuts |

SPARQL over the Pellet-materialised ontology:

```sparql
SELECT ?product ?status WHERE { { ?product falcon:unsafeFor falcon:cons_liam . BIND("UNSAFE" AS ?status) } UNION { ?product falcon:cautionFor falcon:cons_liam . FILTER NOT EXISTS { ?product falcon:unsafeFor falcon:cons_liam } BIND("CAUTION" AS ?status) } }
```

## CQ06. Which products can be confirmed safe for Liam, and why are others excluded?

*Type:* negation as failure

> Only possible with negation as failure; OWL alone can never conclude that a product is safe.

| product |
|---|
| Aged Hard Cheese |
| Baking Powder |
| Roasted Butternut Soup |
| Classic Caesar Dressing |
| Celery Salt |
| Classic Mayonnaise |
| Coconut Drink |
| Creamy Coleslaw |
| Cooking Spray |
| Crispy Malt Flakes |
| Dijon Mustard |
| Dried Apricots |
| Eggplant Parmigiana |
| Fruit Gummies |
| Gluten-Free White Loaf |
| Gluten-Free Sesame Crackers |
| Pure Ghee |
| Green Curry Paste |
| Imitation Crab Sticks |
| Lactose-Free Milk |
| High-Protein Lupin Pasta |
| Non-Dairy Coffee Whitener |
| Oat Barista Drink |
| Plant Protein Bar |
| Rye Sourdough |
| Seafood Paella Kit |
| Classic Hummus |
| Brewed Soy Sauce |
| Smoky Steakhouse Sauce |
| Tamari |
| Vegan Berry Gummies |
| Vitamin D Gummies |
| Cocoa Wafer Biscuits |
| Fruit Drops |

**Why is 'Dark Chocolate 70%' not confirmed safe?**

```
[E13] Confirmed safe for consumer: blocked because cautionFor(prod_dark_chocolate, cons_liam) holds:
      cautionFor(prod_dark_chocolate, cons_liam)   [R08: Caution for consumer]
      |-- Consumer(cons_liam)   [asserted fact]
      |-- mustAvoid(cons_liam, alg_tree_nuts)   [asserted fact]
      `-- mayContain(prod_dark_chocolate, alg_tree_nuts)   [T-CH-4: mayContain ∘ isSubtypeOf ⊑ mayContain]
          |-- mayContain(prod_dark_chocolate, alg_hazelnut)   [asserted fact]
          `-- isSubtypeOf(alg_hazelnut, alg_tree_nuts)   [asserted fact]
```

**Why is 'Rice Puffs (record incomplete)' not confirmed safe?**

```
[E13] Confirmed safe for consumer: no evidence for hasIngredientListStatus(prod_rice_puffs_incomplete, complete)
```

SPARQL over the Pellet-materialised ontology:

```sparql
SELECT ?product WHERE { ?product a falcon:Product ; falcon:hasIngredientListStatus "complete" . FILTER NOT EXISTS { ?product falcon:unsafeFor falcon:cons_liam } FILTER NOT EXISTS { ?product falcon:cautionFor falcon:cons_liam } FILTER NOT EXISTS { ?product falcon:hasIngredient ?i . ?i falcon:possiblyTriggers ?a . falcon:cons_liam falcon:mustAvoid ?a } }
```

## CQ07. How is each product classified automatically?

*Type:* classification

> * = closed-world class computed by the engine; all others are OWL defined classes.

| product | inferred classes |
|---|---|
| Hazelnut Cocoa Spread | NonVeganProduct, AllergenContainingProduct, MultiMarketProduct, ContainsMilkProduct, ContainsTreeNutsProduct, ContainsSoyProduct, VerifiedVegetarianProduct* |
| Oat Barista Drink | GlutenContainingProduct, AllergenContainingProduct, MultiMarketProduct, ContainsGlutenCerealsProduct, ContainsGlutenProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Classic Caesar Dressing | NonVeganProduct, NonVegetarianProduct, AllergenContainingProduct, MultiMarketProduct, ContainsMilkProduct, ContainsEggProduct, ContainsFishProduct |
| Smoky Steakhouse Sauce | NonVeganProduct, NonVegetarianProduct, AllergenContainingProduct, ClaimConflictProduct, MultiMarketProduct, ContainsFishProduct |
| Non-Dairy Coffee Whitener | NonVeganProduct, OriginUncertainProduct, AllergenContainingProduct, ContainsMilkProduct |
| Lactose-Free Milk | NonVeganProduct, AllergenContainingProduct, MultiMarketProduct, ContainsMilkProduct, VerifiedVegetarianProduct* |
| Gluten-Free Sesame Crackers | AllergenContainingProduct, MultiMarketProduct, MeetsGlutenFreeThreshold, ContainsSesameProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Gluten-Free White Loaf | AllergenContainingProduct, MeetsGlutenFreeThreshold, ContainsGlutenCerealsProduct, ContainsWheatProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Rye Sourdough | GlutenContainingProduct, AllergenContainingProduct, MultiMarketProduct, ContainsGlutenCerealsProduct, ContainsWheatProduct, ContainsGlutenProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Crispy Malt Flakes | GlutenContainingProduct, AllergenContainingProduct, ClaimConflictProduct, MultiMarketProduct, ContainsGlutenCerealsProduct, ContainsGlutenProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Peanut Butter Cups | NonVeganProduct, AllergenContainingProduct, PrecautionaryLabelledProduct, MultiMarketProduct, ContainsMilkProduct, ContainsPeanutProduct, ContainsSoyProduct, VerifiedVegetarianProduct* |
| Nut-Free Granola Bar | GlutenContainingProduct, AllergenContainingProduct, PrecautionaryLabelledProduct, PrecautionaryConflictProduct, MultiMarketProduct, ContainsGlutenCerealsProduct, ContainsGlutenProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Almond Butter Cookies | NonVeganProduct, AllergenContainingProduct, PrecautionaryLabelledProduct, MultiMarketProduct, MeetsGlutenFreeThreshold, ContainsMilkProduct, ContainsEggProduct, ContainsTreeNutsProduct, VerifiedVegetarianProduct* |
| Fruit Gummies | NonVeganProduct, NonVegetarianProduct, OriginUncertainProduct, ClaimConflictProduct, MultiMarketProduct |
| Vegan Berry Gummies | NonVeganProduct, NonVegetarianProduct, ClaimConflictProduct, MultiMarketProduct |
| Honey Oat Bar | NonVeganProduct, GlutenContainingProduct, AllergenContainingProduct, ClaimConflictProduct, MultiMarketProduct, ContainsTreeNutsProduct, ContainsGlutenCerealsProduct, ContainsGlutenProduct, VerifiedVegetarianProduct* |
| Plant Protein Bar | OriginUncertainProduct, MultiMarketProduct |
| Classic Hummus | AllergenContainingProduct, MultiMarketProduct, ContainsSesameProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Celery Salt | AllergenContainingProduct, MultiMarketProduct, ContainsCeleryProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Dijon Mustard | AllergenContainingProduct, MultiMarketProduct, SulphiteAtOrAbove10ppm, SulphiteAbove10ppm, ContainsMustardProduct, ContainsSulphitesProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Dried Apricots | AllergenContainingProduct, MultiMarketProduct, SulphiteAtOrAbove10ppm, ContainsSulphitesProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| High-Protein Lupin Pasta | GlutenContainingProduct, AllergenContainingProduct, MultiMarketProduct, ContainsLupinProduct, ContainsGlutenCerealsProduct, ContainsWheatProduct, ContainsGlutenProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Seafood Paella Kit | NonVeganProduct, NonVegetarianProduct, AllergenContainingProduct, MultiMarketProduct, ContainsCrustaceanProduct, ContainsMolluscProduct |
| Imitation Crab Sticks | NonVeganProduct, NonVegetarianProduct, GlutenContainingProduct, AllergenContainingProduct, MultiMarketProduct, ContainsEggProduct, ContainsFishProduct, ContainsCrustaceanProduct, ContainsGlutenCerealsProduct, ContainsWheatProduct, ContainsGlutenProduct |
| Dark Chocolate 70% | AllergenContainingProduct, PrecautionaryLabelledProduct, PrecautionaryConflictProduct, MultiMarketProduct, ContainsSoyProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Coconut Drink | MultiMarketProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Eggplant Parmigiana | NonVeganProduct, NonVegetarianProduct, GlutenContainingProduct, AllergenContainingProduct, ClaimConflictProduct, MultiMarketProduct, ContainsMilkProduct, ContainsGlutenCerealsProduct, ContainsWheatProduct, ContainsGlutenProduct |
| Baking Powder | MultiMarketProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Smooth Peanut Butter | AllergenContainingProduct, MultiMarketProduct, ContainsPeanutProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Pure Ghee | NonVeganProduct, AllergenContainingProduct, MultiMarketProduct, ContainsMilkProduct, VerifiedVegetarianProduct* |
| Roasted Butternut Soup | NonVeganProduct, AllergenContainingProduct, MultiMarketProduct, ContainsMilkProduct, ContainsCeleryProduct, VerifiedVegetarianProduct* |
| Classic Trail Mix | AllergenContainingProduct, MultiMarketProduct, ContainsTreeNutsProduct, ContainsPeanutProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Pesto Genovese | NonVeganProduct, NonVegetarianProduct, AllergenContainingProduct, ClaimConflictProduct, MultiMarketProduct, ContainsMilkProduct, ContainsTreeNutsProduct |
| Green Curry Paste | NonVeganProduct, NonVegetarianProduct, AllergenContainingProduct, ClaimConflictProduct, MultiMarketProduct, ContainsCrustaceanProduct |
| Vitamin D Gummies | NonVeganProduct, NonVegetarianProduct, OriginUncertainProduct |
| Rice Puffs (record incomplete) | IncompleteRecordProduct |
| Mystery Snack (no ingredient data) | MultiMarketProduct, IncompleteRecordProduct |
| Brewed Soy Sauce | GlutenContainingProduct, AllergenContainingProduct, ClaimConflictProduct, MultiMarketProduct, ContainsSoyProduct, ContainsGlutenCerealsProduct, ContainsWheatProduct, ContainsGlutenProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Tamari | AllergenContainingProduct, MultiMarketProduct, MeetsGlutenFreeThreshold, ContainsSoyProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Cooking Spray | AllergenContainingProduct, MultiMarketProduct, ContainsSoyProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Fruit Drops | AllergenContainingProduct, ContainsGlutenCerealsProduct, ContainsWheatProduct, VerifiedVeganProduct*, VerifiedVegetarianProduct* |
| Aged Hard Cheese | NonVeganProduct, AllergenContainingProduct, MultiMarketProduct, ContainsMilkProduct, ContainsEggProduct, VerifiedVegetarianProduct* |
| Classic Mayonnaise | NonVeganProduct, AllergenContainingProduct, MultiMarketProduct, ContainsEggProduct, ContainsMustardProduct, VerifiedVegetarianProduct* |
| Creamy Coleslaw | NonVeganProduct, AllergenContainingProduct, ClaimConflictProduct, MultiMarketProduct, ContainsEggProduct, ContainsMustardProduct, VerifiedVegetarianProduct* |
| Cocoa Wafer Biscuits | OriginUncertainProduct, GlutenContainingProduct, AllergenContainingProduct, MultiMarketProduct, ContainsGlutenCerealsProduct, ContainsWheatProduct, ContainsGlutenProduct |

SPARQL over the Pellet-materialised ontology:

```sparql
SELECT ?product ?class WHERE { ?product a falcon:Product . ?product a ?class . ?class rdfs:subClassOf* falcon:Product . FILTER(?class != falcon:Product) }
```

## CQ08. Which allergens must each product declare in the US, Canada and the EU, and where do the markets disagree?

*Type:* jurisdiction-aware reasoning

> 11 product-allergen pairs are treated differently by markets the product is sold in.

| product | allergen | US | Canada | EU | markets disagree |
|---|---|---|---|---|---|
| Hazelnut Cocoa Spread | Hazelnut | must declare | must declare | must declare |  |
| Hazelnut Cocoa Spread | Milk | must declare | must declare | must declare |  |
| Hazelnut Cocoa Spread | Soybean | must declare | must declare | must declare |  |
| Oat Barista Drink | Oats | not sold | must declare | must declare |  |
| Classic Caesar Dressing | Egg | must declare | not sold | must declare |  |
| Classic Caesar Dressing | Fish | must declare | not sold | must declare |  |
| Classic Caesar Dressing | Milk | must declare | not sold | must declare |  |
| Smoky Steakhouse Sauce | Fish | must declare | must declare | not sold |  |
| Non-Dairy Coffee Whitener | Milk | must declare | not sold | not sold |  |
| Lactose-Free Milk | Milk | must declare | must declare | must declare |  |
| Gluten-Free Sesame Crackers | Sesame | must declare | must declare | must declare |  |
| Gluten-Free White Loaf | Wheat | not sold | not sold | must declare |  |
| Rye Sourdough | Rye | not sold | must declare | must declare |  |
| Rye Sourdough | Wheat | not sold | must declare | must declare |  |
| Crispy Malt Flakes | Barley | not required | must declare | not sold | yes |
| Peanut Butter Cups | Milk | must declare | must declare | not sold |  |
| Peanut Butter Cups | Peanut | must declare | must declare | not sold |  |
| Peanut Butter Cups | Soybean | must declare | must declare | not sold |  |
| Nut-Free Granola Bar | Oats | not sold | must declare | must declare |  |
| Almond Butter Cookies | Almond | must declare | must declare | must declare |  |
| Almond Butter Cookies | Egg | must declare | must declare | must declare |  |
| Almond Butter Cookies | Milk | must declare | must declare | must declare |  |
| Honey Oat Bar | Almond | must declare | must declare | must declare |  |
| Honey Oat Bar | Oats | not required | must declare | must declare | yes |
| Classic Hummus | Sesame | must declare | must declare | must declare |  |
| Celery Salt | Celery | not required | not sold | must declare | yes |
| Dijon Mustard | Mustard | not required | must declare | must declare | yes |
| Dijon Mustard | Sulphur dioxide and sulphites | must declare | must declare | must declare |  |
| Dried Apricots | Sulphur dioxide and sulphites | must declare | must declare | not required | yes |
| High-Protein Lupin Pasta | Lupin | not required | not sold | must declare | yes |
| High-Protein Lupin Pasta | Wheat | must declare | not sold | must declare |  |
| Seafood Paella Kit | Crustacean shellfish | must declare | must declare | must declare |  |
| Seafood Paella Kit | Molluscs | not required | must declare | must declare | yes |
| Imitation Crab Sticks | Crustacean shellfish | must declare | must declare | not sold |  |
| Imitation Crab Sticks | Egg | must declare | must declare | not sold |  |
| Imitation Crab Sticks | Fish | must declare | must declare | not sold |  |
| Imitation Crab Sticks | Wheat | must declare | must declare | not sold |  |
| Dark Chocolate 70% | Soybean | must declare | must declare | must declare |  |
| Eggplant Parmigiana | Milk | must declare | must declare | must declare |  |
| Eggplant Parmigiana | Wheat | must declare | must declare | must declare |  |
| Smooth Peanut Butter | Peanut | must declare | must declare | must declare |  |
| Pure Ghee | Milk | must declare | not sold | must declare |  |
| Roasted Butternut Soup | Celery | not sold | not required | must declare | yes |
| Roasted Butternut Soup | Milk | not sold | must declare | must declare |  |
| Classic Trail Mix | Almond | must declare | must declare | must declare |  |
| Classic Trail Mix | Cashew | must declare | must declare | must declare |  |
| Classic Trail Mix | Peanut | must declare | must declare | must declare |  |
| Pesto Genovese | Cashew | must declare | must declare | must declare |  |
| Pesto Genovese | Milk | must declare | must declare | must declare |  |
| Pesto Genovese | Pine nut | must declare | must declare | not required | yes |
| Green Curry Paste | Crustacean shellfish | must declare | must declare | must declare |  |
| Brewed Soy Sauce | Soybean | must declare | must declare | must declare |  |
| Brewed Soy Sauce | Wheat | must declare | must declare | must declare |  |
| Tamari | Soybean | must declare | must declare | must declare |  |
| Cooking Spray | Soybean | must declare | not sold | must declare |  |
| Aged Hard Cheese | Egg | not sold | must declare | must declare |  |
| Aged Hard Cheese | Milk | not sold | must declare | must declare |  |
| Classic Mayonnaise | Egg | must declare | must declare | must declare |  |
| Classic Mayonnaise | Mustard | not required | must declare | must declare | yes |
| Creamy Coleslaw | Egg | must declare | must declare | not sold |  |
| Creamy Coleslaw | Mustard | not required | must declare | not sold | yes |
| Cocoa Wafer Biscuits | Wheat | must declare | must declare | not sold |  |

SPARQL over the Pellet-materialised ontology:

```sparql
SELECT ?product ?allergen ?market WHERE { { ?product falcon:mustDeclareInUS ?allergen . BIND("US" AS ?market) } UNION { ?product falcon:mustDeclareInCanada ?allergen . BIND("Canada" AS ?market) } UNION { ?product falcon:mustDeclareInEU ?allergen . BIND("EU" AS ?market) } }
```

## CQ09. Which products contain an allergen that the ingredient names do not reveal?

*Type:* hidden-allergen reasoning

| product | allergen | ingredient on label | derivation |
|---|---|---|---|
| Aged Hard Cheese | Egg | Lysozyme (E1105) | Lysozyme (E1105) -> Egg white -> Egg  =>  Egg allergen |
| Creamy Coleslaw | Egg | Mayonnaise | Mayonnaise -> Egg yolk -> Egg  =>  Egg allergen |
| Creamy Coleslaw | Mustard | Mayonnaise | Mayonnaise -> Mustard seed  =>  Mustard allergen |
| Eggplant Parmigiana | Wheat | Breadcrumbs | Breadcrumbs -> Wheat flour -> Wheat  =>  Wheat allergen |
| Imitation Crab Sticks | Fish | Surimi | Surimi -> Fish  =>  Fish allergen |
| High-Protein Lupin Pasta | Wheat | Semolina | Semolina -> Wheat  =>  Wheat allergen |
| Non-Dairy Coffee Whitener | Milk | Sodium caseinate | Sodium caseinate -> Casein -> Milk  =>  Milk allergen |
| Peanut Butter Cups | Soybean | Milk chocolate | Milk chocolate -> Soy lecithin (E322) -> Soybeans  =>  Soybean allergen |
| Classic Hummus | Sesame | Tahini | Tahini -> Sesame seeds  =>  Sesame allergen |
| Smoky Steakhouse Sauce | Fish | Worcestershire sauce | Worcestershire sauce -> Anchovy  =>  Fish allergen |

SPARQL over the Pellet-materialised ontology:

```sparql
SELECT ?product ?allergen ?ingredient WHERE { ?product falcon:hasIngredient ?ingredient . ?ingredient falcon:triggersAllergen ?allergen . FILTER NOT EXISTS { GRAPH <http://www.semanticweb.org/anushgoel/ontologies/2026/falcon.owl> { ?ingredient falcon:triggersAllergen ?allergen } } }
```

## CQ10. Which products cannot be assessed because their ingredient information is incomplete?

*Type:* incomplete information

| product | ingredients known | consumers confirmed safe | claims |
|---|---|---|---|
| Mystery Snack (no ingredient data) | 0 | 0 of 9 | (none) |
| Rice Puffs (record incomplete) | 2 | 0 of 9 | Nut-free -> UNVERIFIABLE |

SPARQL over the Pellet-materialised ontology:

```sparql
SELECT ?product WHERE { ?product a falcon:IncompleteRecordProduct . }
```

## CQ11. Which gluten-free products meet the 20 ppm limit, which exceed it, and which rely on the recipe alone?

*Type:* numeric reasoning

> Gluten-free and wheat-free are different claims: see the Codex wheat starch loaf.

| product | gluten (ppm) | lab result | gluten sources in recipe | verdict | contains wheat |
|---|---|---|---|---|---|
| Almond Butter Cookies | 8.0 | meets limit | none | VERIFIED |  |
| Baking Powder |  | untested | none | VERIFIED |  |
| Roasted Butternut Soup |  | untested | none | VERIFIED |  |
| Classic Mayonnaise |  | untested | none | VERIFIED |  |
| Crispy Malt Flakes | 45.0 | exceeds limit | Barley malt extract | CONTRADICTED |  |
| Gluten-Free White Loaf | 12.0 | meets limit | none | VERIFIED | yes |
| Gluten-Free Sesame Crackers | 5.0 | meets limit | none | VERIFIED |  |
| Classic Hummus |  | untested | none | VERIFIED |  |
| Brewed Soy Sauce |  | untested | Wheat | CONTRADICTED | yes |
| Tamari | 3.0 | meets limit | none | VERIFIED |  |

SPARQL over the Pellet-materialised ontology:

```sparql
SELECT ?product ?ppm ?status WHERE { ?product falcon:hasLabelClaim ?claim . ?claim a falcon:GlutenFreeClaim . OPTIONAL { ?product falcon:hasGlutenPPM ?ppm } BIND(IF(!BOUND(?ppm), "UNTESTED", IF(?ppm < 20, "MEETS", "EXCEEDS")) AS ?status) }
```

## CQ12. How is a new, previously unseen product classified?

*Type:* classification of a new instance

| aspect | result |
|---|---|
| ingredients | Sesame seeds, Honey, Glucose syrup, Wheat flour |
| inferred classes | NonVeganProduct, GlutenContainingProduct, AllergenContainingProduct, ClaimConflictProduct, MultiMarketProduct, ContainsSesameProduct, ContainsGlutenCerealsProduct, ContainsWheatProduct, ContainsGlutenProduct, VerifiedVegetarianProduct* |
| allergens | Gluten (coeliac hazard), Cereals containing gluten, Sesame, Wheat |
| claim audit | Vegan -> CONTRADICTED |
| undeclared allergens | Wheat (Canada), Wheat (European Union) |
| unsafe for | Emma (vegetarian, sesame allergy), Sofia (coeliac disease), Wei (wheat allergy, not coeliac) |
| unsuitable for diet of | Arjun (vegan) |

## CQ13. Which products have allergens that a market requires but the label does not declare?

*Type:* compliance (recall risk)

> 10 products carry at least one undeclared allergen in a market where they are sold.

| product | allergen | market | finding |
|---|---|---|---|
| Aged Hard Cheese | Egg | Canada | undeclared |
| Aged Hard Cheese | Egg | European Union | undeclared |
| Roasted Butternut Soup | Celery | European Union | undeclared |
| Celery Salt | Celery | European Union | undeclared |
| Classic Mayonnaise | Mustard | Canada | undeclared |
| Classic Mayonnaise | Mustard | European Union | undeclared |
| Creamy Coleslaw | Egg | Canada | undeclared |
| Creamy Coleslaw | Egg | United States | undeclared |
| Creamy Coleslaw | Mustard | Canada | undeclared |
| Crispy Malt Flakes | Barley | Canada | undeclared |
| Dried Apricots | Sulphur dioxide and sulphites | Canada | undeclared |
| Dried Apricots | Sulphur dioxide and sulphites | United States | undeclared |
| High-Protein Lupin Pasta | Lupin | European Union | undeclared |
| Pesto Genovese | Pine nut | Canada | undeclared |
| Pesto Genovese | Pine nut | United States | undeclared |
| Smoky Steakhouse Sauce | Fish | Canada | undeclared |
| Smoky Steakhouse Sauce | Fish | United States | undeclared |
| Cocoa Wafer Biscuits | Egg | Canada | verify with supplier |
| Cocoa Wafer Biscuits | Egg | United States | verify with supplier |
| Cocoa Wafer Biscuits | Soybean | Canada | verify with supplier |
| Cocoa Wafer Biscuits | Soybean | United States | verify with supplier |

SPARQL over the Pellet-materialised ontology:

```sparql
SELECT ?product ?allergen ?market WHERE { { ?product falcon:mustDeclareInUS ?allergen . BIND("US" AS ?market) } UNION { ?product falcon:mustDeclareInCanada ?allergen . BIND("Canada" AS ?market) } UNION { ?product falcon:mustDeclareInEU ?allergen . BIND("EU" AS ?market) } FILTER NOT EXISTS { ?product falcon:declaresAllergen ?allergen } }
```

## CQ14. Which label claims are verified, contradicted, at risk or unverifiable?

*Type:* three-valued claim audit

| product | claim | status |
|---|---|---|
| Brewed Soy Sauce | Gluten-free | CONTRADICTED |
| Creamy Coleslaw | Egg-free | CONTRADICTED |
| Crispy Malt Flakes | Gluten-free | CONTRADICTED |
| Eggplant Parmigiana | Vegetarian | CONTRADICTED |
| Fruit Gummies | Vegetarian | CONTRADICTED |
| Green Curry Paste | Vegetarian | CONTRADICTED |
| Honey Oat Bar | Vegan | CONTRADICTED |
| Pesto Genovese | Vegetarian | CONTRADICTED |
| Smoky Steakhouse Sauce | Vegan | CONTRADICTED |
| Vegan Berry Gummies | Vegan | CONTRADICTED |
| Dark Chocolate 70% | Dairy-free | AT RISK |
| Nut-Free Granola Bar | Nut-free | AT RISK |
| Plant Protein Bar | Vegan | UNVERIFIABLE |
| Rice Puffs (record incomplete) | Nut-free | UNVERIFIABLE |
| Non-Dairy Coffee Whitener | Non-dairy (US term) | INFORMATIONAL |
| Aged Hard Cheese | Vegetarian | VERIFIED |
| Almond Butter Cookies | Gluten-free | VERIFIED |
| Baking Powder | Dairy-free | VERIFIED |
| Baking Powder | Gluten-free | VERIFIED |
| Baking Powder | Vegan | VERIFIED |
| Celery Salt | Vegan | VERIFIED |
| Classic Hummus | Gluten-free | VERIFIED |
| Classic Hummus | Vegan | VERIFIED |
| Classic Mayonnaise | Dairy-free | VERIFIED |
| Classic Mayonnaise | Gluten-free | VERIFIED |
| Classic Trail Mix | Vegan | VERIFIED |
| Coconut Drink | Dairy-free | VERIFIED |
| Coconut Drink | Vegan | VERIFIED |
| Cooking Spray | Vegan | VERIFIED |
| Dark Chocolate 70% | Vegan | VERIFIED |
| Dijon Mustard | Vegan | VERIFIED |
| Dried Apricots | Vegan | VERIFIED |
| Fruit Drops | Vegan | VERIFIED |
| Gluten-Free Sesame Crackers | Gluten-free | VERIFIED |
| Gluten-Free Sesame Crackers | Vegan | VERIFIED |
| Gluten-Free White Loaf | Gluten-free | VERIFIED |
| Lactose-Free Milk | Lactose-free | VERIFIED |
| Nut-Free Granola Bar | Vegan | VERIFIED |
| Oat Barista Drink | Dairy-free | VERIFIED |
| Oat Barista Drink | Vegan | VERIFIED |
| Pure Ghee | Lactose-free | VERIFIED |
| Roasted Butternut Soup | Gluten-free | VERIFIED |
| Smooth Peanut Butter | Vegan | VERIFIED |
| Tamari | Gluten-free | VERIFIED |
| Tamari | Vegan | VERIFIED |

Counts: AT RISK = 2, CONTRADICTED = 10, INFORMATIONAL = 1, UNVERIFIABLE = 2, VERIFIED = 30

SPARQL over the Pellet-materialised ontology:

```sparql
SELECT ?product ?claim WHERE { ?product falcon:hasLabelClaim ?claim . FILTER NOT EXISTS { ?product falcon:contradictsClaim ?claim } }
```
