/*
 * Builds the FALCON technical report (APA 7 student paper) from report/report_data.json.
 *
 *   node report/build_report.js portfolio  docs/FALCON_Technical_Report.docx
 *   node report/build_report.js submission FALCON_Report_Submission.docx
 *
 * "submission" adds the course cover page; "portfolio" is the public version.
 * Text between ⟦ and ⟧ is highlighted yellow: it marks numbers that only a full
 * run with Java (Pellet/HermiT) can supply.
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Header, PageNumber,
  ImageRun, Table, TableRow, TableCell, WidthType, BorderStyle,
} = require("docx");

const variant = process.argv[2] || "portfolio";
const outFile = process.argv[3] || "FALCON_Technical_Report.docx";
const ROOT = path.resolve(__dirname, "..");
const d = JSON.parse(fs.readFileSync(path.join(__dirname, "report_data.json"), "utf8"));
const fig = (name) => path.join(ROOT, "docs", "figures", name);
const fmt = (n) => Number(n).toLocaleString("en-US");
const dur = (s) => (s >= 120 ? `${fmt(Math.round(s))} seconds (about ${Math.round(s / 60)} minutes)` : `${s.toFixed(1)} seconds`);
const durShort = (s) => (s >= 120 ? `${fmt(Math.round(s))} s (${(s / 60).toFixed(1)} min)` : `${s.toFixed(2)} s`);
const ins = d.insights;
const audit = ins.claim_audit || {};
const owlOk = d.owl.status === "ok" && d.owl.pellet && d.owl.pellet.status === "consistent";

// ---------------------------------------------------------------- helpers
let counting = false;
let bodyWords = 0;
const wordsIn = (t) => (t.replace(/[⟦⟧*]/g, "").match(/\S+/g) || []).length;

function runs(text, base = {}) {
  const out = [];
  text.split(/(⟦[^⟧]*⟧)/).forEach((chunk) => {
    if (!chunk) return;
    const highlighted = chunk.startsWith("⟦");
    const body = highlighted ? chunk.slice(1, -1) : chunk;
    body.split("*").forEach((seg, k) => {
      if (!seg) return;
      const opts = Object.assign({ text: seg }, base);
      if (k % 2 === 1) opts.italics = true;
      if (highlighted) opts.highlight = "yellow";
      out.push(new TextRun(opts));
    });
  });
  return out;
}
function P(text) {
  if (counting) bodyWords += wordsIn(text);
  return new Paragraph({ indent: { firstLine: 720 }, children: runs(text) });
}
function Pn(text, opts = {}) {
  if (counting && !opts.nocount) bodyWords += wordsIn(text);
  return new Paragraph({ children: runs(text), keepNext: !!opts.keepNext });
}
const H1 = (text, pageBreak = false) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: pageBreak, children: [new TextRun(text)] });
const H2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, children: [new TextRun(text)] });
const C = (text, bold = false) => new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text, bold })] });
const blank = () => new Paragraph({ children: [] });

function pngSize(file) {
  const b = fs.readFileSync(file);
  return [b.readUInt32BE(16), b.readUInt32BE(20)];
}
let figNo = 0;
function figure(file, title, note, maxH = 560) {
  figNo += 1;
  const [w, h] = pngSize(fig(file));
  let width = 624;
  let height = Math.round((width * h) / w);
  if (height > maxH) { height = maxH; width = Math.round((maxH * w) / h); }
  return [
    new Paragraph({ keepNext: true, spacing: { before: 240 }, children: [new TextRun({ text: `Figure ${figNo}`, bold: true })] }),
    new Paragraph({ keepNext: true, children: [new TextRun({ text: title, italics: true })] }),
    new Paragraph({ keepNext: true, alignment: AlignmentType.CENTER, spacing: { line: 240, lineRule: "auto" },
      children: [new ImageRun({ type: "png", data: fs.readFileSync(fig(file)), transformation: { width, height } })] }),
    new Paragraph({ spacing: { after: 240 }, children: [new TextRun({ text: "Note.", italics: true }), ...runs(" " + note)] }),
  ];
}
let tabNo = 0;
const LINE = { style: BorderStyle.SINGLE, size: 6, color: "000000" };
const NONE = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
function table(title, columns, widths, rows, note, label) {
  if (!label) tabNo += 1;
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (text, w, top, bottom, bold) => new TableCell({
    width: { size: w, type: WidthType.DXA },
    borders: { top: top ? LINE : NONE, bottom: bottom ? LINE : NONE, left: NONE, right: NONE },
    margins: { top: 40, bottom: 40, left: 70, right: 70 },
    children: [new Paragraph({ spacing: { line: 240, lineRule: "auto" }, children: runs(String(text), Object.assign({ size: 20 }, bold ? { bold: true } : {})) })],
  });
  const header = new TableRow({ tableHeader: true, children: columns.map((c, k) => cell(c, widths[k], true, true, true)) });
  const body = rows.map((r, n) => new TableRow({ cantSplit: true,
    children: r.map((v, k) => cell(v, widths[k], false, n === rows.length - 1, false)) }));
  const parts = [
    new Paragraph({ keepNext: true, spacing: { before: 240 }, children: [new TextRun({ text: label || `Table ${tabNo}`, bold: true })] }),
    new Paragraph({ keepNext: true, children: [new TextRun({ text: title, italics: true })] }),
    new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths, rows: [header, ...body] }),
  ];
  if (note) parts.push(new Paragraph({ spacing: { after: 240 }, children: [new TextRun({ text: "Note.", italics: true }), ...runs(" " + note)] }));
  else parts.push(blank());
  return parts;
}

// ---------------------------------------------------------------- numbers
const kb = d.kb;
const eng = d.engine;
const ec1 = d.ec1;
const prec = d.ec8.precision.toFixed(2);
const recall = d.ec8.recall.toFixed(2);
const bench = d.bench.engine || [];
const bmin = bench.length ? bench[0] : null;
const bmax = bench.length ? bench[bench.length - 1] : null;
const benchOwl = (d.bench.owl || []).filter((r) => r.status === "consistent");
const pending = (what) => `⟦${what}: insert from the full run⟧`;

const engineSeconds = eng.elapsed_s;   // the pipeline's forward-chaining run, as in Table 4
const pelletRuns = [d.owl.pellet && d.owl.pellet.seconds,
  d.owl.ec2 && d.owl.ec2.open && d.owl.ec2.open.reasoner.seconds, d.owl.ec2 && d.owl.ec2.closed && d.owl.ec2.closed.reasoner.seconds,
  d.owl.cq12 && d.owl.cq12.reasoner && d.owl.cq12.reasoner.seconds].filter((x) => x && x > 1);
const pelletSpan = pelletRuns.length ? `${Math.round(Math.min(...pelletRuns) / 60)} to ${Math.round(Math.max(...pelletRuns) / 60)} minutes` : null;
const allAgree = owlOk && d.owl.crossval_agree === d.owl.crossval_total;

const owlConsistency = owlOk
  ? `Pellet reasoned over the complete ontology, including all ${d.swrl} SWRL rules, found it consistent, and inferred ${fmt(d.owl.facts_inferred)} facts; materialising them took ${dur(d.owl.pellet.seconds)}. HermiT, given the ${d.swrl_no_builtins} rules without built-ins, ${d.owl.hermit ? `reported "${d.owl.hermit.status}" in ${dur(d.owl.hermit.seconds)}` : "was not run"}. Neither found an unsatisfiable class. Cross-validation compared ${d.owl.crossval_predicates} predicates and found ${allAgree ? `all ${fmt(d.owl.crossval_agree)}` : `${fmt(d.owl.crossval_agree)} of ${fmt(d.owl.crossval_total)}`} facts in agreement between Pellet and the rule engine, which derives them in ${engineSeconds.toFixed(2)} seconds.`
  : `⟦Pellet and HermiT consistency results and the Pellet–engine cross-validation will be inserted here from outputs/owl_results.json after the full run.⟧`;
const ec2Agree = d.owl.ec2 && d.owl.ec2.agreement_with_engine;
const ec2 = d.owl.ec2 && d.owl.ec2.closed && ec2Agree
  ? (ec2Agree.only_owl.length === 0 && ec2Agree.only_engine.length === 0
      ? `; once closure axioms were added to the complete records, Pellet classified exactly the ${ec2Agree.both} products as vegan-compatible that the engine verifies`
      : `; once closure axioms were added to the complete records, Pellet classified ${d.owl.ec2.closed.VeganCompatibleProduct.length} products as vegan-compatible, against ${d.owl.ec2.engine_VerifiedVeganProduct.length} verified by the engine`)
  : `, and the closure-axiom experiment that restores the classification is part of the reasoner results`;
const ec3 = d.owl.ec3 && d.owl.ec3.reasoner
  ? (d.owl.ec3.reasoner.status === "inconsistent" ? ` (Pellet detected the inconsistency in ${d.owl.ec3.reasoner.seconds.toFixed(1)} seconds)` : ` (Pellet reported: ${d.owl.ec3.reasoner.status})`)
  : "";
const ec4owl = d.owl.ec4 && d.owl.ec4.reasoner && d.owl.ec4.reasoner.status === "inconsistent"
  ? `; in the ontology the same error is a contradiction, which Pellet reported in ${d.owl.ec4.reasoner.seconds.toFixed(1)} seconds`
  : "";
const owlScaling = (() => {
  const h = (d.bench.owl || []).filter((r) => r.reasoner === "hermit" && r.status === "consistent");
  const pDone = (d.bench.owl || []).filter((r) => r.reasoner === "pellet" && r.status === "consistent");
  const pStop = (d.bench.owl || []).filter((r) => r.reasoner === "pellet" && r.status === "timeout");
  if (!h.length && !pDone.length && !pStop.length) return `⟦HermiT and Pellet timings at increasing sizes will be added from outputs/benchmark.json after the full run.⟧`;
  const list = (rows) => rows.map((r) => r.reasoning_seconds.toFixed(1)).join(", ").replace(/, ([^,]*)$/, " and $1");
  const sizes = (rows) => rows.map((r) => fmt(r.products)).join(", ").replace(/, ([^,]*)$/, " and $1");
  const earlier = (d.bench_earlier || []).filter((r) => r.reasoner === "hermit" && !h.some((x) => x.products === r.products));
  const parts = [];
  if (h.length) parts.push(`On the same synthetic data, HermiT needed ${list(h)} seconds at ${sizes(h)} products${d.bench.hermit_slope ? ` (fitted exponent ${d.bench.hermit_slope})` : ""}${earlier.length ? `, and an earlier uncapped run took ${fmt(Math.round(earlier[earlier.length - 1].reasoning_seconds))} seconds at ${fmt(earlier[earlier.length - 1].products)} products` : ""}.`);
  if (pDone.length) parts.push(`Pellet needed ${list(pDone)} seconds at ${sizes(pDone)} products.`);
  else if (pStop.length) parts.push(`Pellet could not finish even the ${fmt(pStop[0].products)}-product knowledge base within the ${d.owl_timeout_s}-second limit; its full run on the curated data took ${dur(d.owl.pellet.seconds)}, against ${engineSeconds.toFixed(2)} seconds for the engine.`);
  return parts.join(" ");
})();

// ---------------------------------------------------------------- document
const children = [];
const title = "FALCON: Ontology-Based Reasoning for Food Allergen and Label Compliance Across Three Regulatory Markets";

// Title page
for (let k = 0; k < 3; k += 1) children.push(blank());
children.push(new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: title, bold: true })] }));
children.push(blank());
const coverLines = variant === "submission"
  ? ["Anush Goel", ...(process.env.FALCON_NUID ? ["NUID: " + process.env.FALCON_NUID] : []), "Northeastern University",
     process.env.FALCON_COURSE || "⟦Course number: Course name⟧", process.env.FALCON_INSTRUCTOR || "⟦Instructor name⟧",
     process.env.FALCON_DUE || "⟦Due date⟧"]
  : ["Anush Goel", "Northeastern University", "October 2026"];
coverLines.forEach((l) => children.push(new Paragraph({ alignment: AlignmentType.CENTER, children: runs(l) })));

// Abstract
children.push(H1("Abstract", true));
const abstract = `Undeclared allergens remain a persistent cause of packaged-food recalls, and the rules that decide what a label must declare differ between markets. This report presents FALCON, a knowledge representation system that reasons about allergens, diet claims, and labelling duties for products sold in the United States, Canada, and the European Union. The domain is modelled as an OWL 2 DL ontology in SROIQ(D), built with owlready2: ${d.classes_named + d.classes_defined} classes, ${d.object_properties + d.data_properties} properties, ${d.chains} property chains, and ${d.individuals} individuals describing ${kb.products} products and ${kb.ingredients} ingredients. Seventeen SWRL rules run in the Pellet reasoner and in a purpose-built engine that adds forward and backward chaining with proof trees, negation as failure under a local closed-world assumption, and defeasible regulatory exemptions. The system answers ${d.n_cq} competency questions. On the curated knowledge base it contradicted ${audit.CONTRADICTED} of ${ins.claims_total} label claims, found ${ins.undeclared_pairs} undeclared allergen obligations across ${ins.products_with_undeclared_allergen} products, and exposed ${ins.hidden_allergen_findings} hidden allergens. A naive closed-world reading would have issued ${ins.naive_closed_world_false_assurances} false assurances (${ec1.false_safe} on safety, ${ec1.false_vegan} on vegan status), and keyword screening reached a precision of only ${prec}.${owlOk && allAgree ? ` Pellet agreed with the engine on all ${fmt(d.owl.crossval_agree)} facts it inferred but needed about ${Math.round(d.owl.pellet.seconds / 60)} minutes, against ${engineSeconds.toFixed(2)} seconds.` : ""}`;
children.push(Pn(abstract, { nocount: true }));
children.push(new Paragraph({ indent: { firstLine: 720 }, children: [new TextRun({ text: "Keywords: ", italics: true }),
  new TextRun("knowledge representation, OWL 2, SWRL, food allergens, label compliance, closed-world assumption")] }));

// Body
children.push(new Paragraph({ pageBreakBefore: true, alignment: AlignmentType.CENTER, children: [new TextRun({ text: title, bold: true })] }));
counting = true;
children.push(H1("Introduction"));
children.push(P(`About one in ten adults in the United States reports a food allergy with convincing symptoms (Gupta et al., 2019), and for these consumers the ingredient list is the main safety control. When that control fails, the usual result is a recall: after the Food Allergen Labeling and Consumer Protection Act took effect, undeclared allergens, most often milk, remained a persistent cause of FDA allergen recalls (Gendel & Zhu, 2013).`));
children.push(P(`Part of the difficulty is that allergen knowledge is relational. Whey is milk, Worcestershire sauce is traditionally made with anchovies, and the lysozyme that preserves some hard cheeses comes from egg white, yet none of this is visible in the ingredient name. The rules are also jurisdictional. Pine nuts are a declarable tree nut in the United States and Canada but not in the European Union; mustard, celery, and lupin are regulated in the EU but not by the FDA; and exactly 10 mg/kg of sulphites requires a declaration in North America but not in Europe (European Parliament & Council of the European Union, 2011; Food: Exemptions From Labeling, 2025; Health Canada, n.d.; U.S. Food and Drug Administration [FDA], 2025).`));
children.push(P(`This makes labelling a natural fit for knowledge representation. The concepts form hierarchies, the relationships chain (an ingredient keeps the allergens of whatever it was made from), and the regulations read as rules with thresholds and exceptions. FALCON, the Food Allergen and Label Compliance Ontology, encodes this knowledge and reasons over it.`));
children.push(H2("Scope and Boundaries"));
children.push(P(`FALCON covers packaged foods sold in three markets, ${kb.allergens} allergens (${d.allergen_categories} regulated groups and ${d.allergen_specific} named members such as individual tree nuts), ingredient provenance and composition, ${kb.label_claims} label claims, and ${kb.consumers} consumer profiles. It leaves out nutrition labelling, the probability of cross-contact, and quantitative thresholds other than those for gluten and sulphites. The knowledge base is curated rather than scraped: each of its ${kb.products} products exists to exercise a particular question or edge case, so the counts reported here describe what the system can detect, not how often problems occur in the market.`));
children.push(H2("Competency Questions"));
children.push(P(`Following Grüninger and Fox (1995), the requirements were written as questions the system must answer. The ${d.n_cq} questions range from lookups ("which ingredients are made from milk?") through rule-based inference (which claims are false, and which allergens are undeclared in which market) to questions that need negation ("which products can be confirmed safe for this consumer?") and the classification of a product the system has never seen. They are listed with their answers in the Evaluation section.`));

children.push(H1("Background and Literature Review"));
children.push(P(`An ontology is an explicit specification of a shared conceptualization (Gruber, 1993). In the food domain the most developed example is FoodOn, which harmonizes food sources, processes, and products under the OBO Foundry principles (Dooley et al., 2018; Smith et al., 2007). FoodOn describes what foods are and how they are made, but it does not encode labelling duties. FoodKG links recipes, ingredients, and nutrient data in a knowledge graph for food recommendation (Haussmann et al., 2019); it treats ingredients as graph nodes, as FALCON does, but answers questions by retrieval rather than inference. Neither resource represents market-specific allergen law, which is the gap FALCON fills. Its ingredient classes follow conventions that would allow later alignment with FoodOn through MIREOT (Courtot et al., 2011), and its data files are documented and machine-readable in line with the FAIR principles (Wilkinson et al., 2016).`));
children.push(P(`OWL 2 DL rests on the description logic SROIQ(D) (Horrocks et al., 2006). It provides the hierarchies, defined classes, and property chains this domain needs, and reasoners such as HermiT (Glimm et al., 2014) and Pellet (Sirin et al., 2007) classify ontologies soundly and completely. Rules that OWL cannot express are added with SWRL (Horrocks et al., 2004), and decidability is kept by applying rules only to named individuals, the DL-safety condition (Motik et al., 2005).`));
children.push(P(`Two features of the domain fall outside both formalisms. OWL makes the open-world assumption, so the absence of an allergen from the data never proves that a product is free of it (Rector et al., 2004). Regulatory exemptions are defeasible: a duty holds unless an exception applies, and a monotonic logic cannot withdraw a conclusion once drawn (Antoniou et al., 2001). Logic programming handles both through negation as failure under the closed-world assumption (Reiter, 1978), with a clear semantics for stratified programs (Apt et al., 1988), and the overlap between description logics and Horn rules is well understood (Grosof et al., 2003).`));
children.push(H2("Choice of Methodology"));
children.push(P(`I therefore chose a hybrid design, developed iteratively from the competency questions as Noy and McGuinness (2001) recommend. The ontology, built with owlready2 (Lamy, 2017), carries the terminology and the monotonic rules and is checked by both reasoners. A separate Datalog-style engine runs the same SWRL rules and adds negation as failure, but only under a local closed-world assumption (Etzioni et al., 1997): closed-world conclusions are drawn only for records marked complete. Running the same rules in two independent engines gives each an external check. Claude (Anthropic, 2026) assisted with design discussions, code drafting, debugging, and editing; every source, rule, and result was checked independently.`));

children.push(H1("Methodology and System Design"));
children.push(H2("Domain Analysis"));
children.push(P(`The domain has six kinds of entity: products, ingredient kinds, allergens, label claims, markets, and consumers. Their relationships come from three bodies of knowledge. Ingredient knowledge records what an ingredient is made from and whether processing keeps the source's proteins: whey keeps those of milk, while fully refined soybean oil, though made from soybeans, does not. Regulatory knowledge records which allergens each market requires to be declared, with thresholds and exemptions. Claim knowledge records what each claim rules out, and here the domain is full of traps. "Non-dairy" is a US regulatory term that permits caseinate, a milk protein (Food; Designation of Ingredients, 2025; Food Allergy Research & Resource Program [FARRP], n.d.); "lactose-free" says nothing about milk protein; and "gluten-free" does not mean wheat-free when Codex wheat starch is used (Codex Alimentarius Commission, 2008).`));
children.push(H2("Conceptual Model"));
children.push(P(`Figure 1 shows the core concepts. Solid edges are asserted in the data and dashed edges are inferred. The product is the hub: everything the system concludes about it, from its allergens to the status of its claims, its duties in each market, and its safety for each consumer, is derived from its ingredients, its claims, and where it is sold.`));
children.push(...figure("fig01_conceptual_model.png", "Conceptual Model of FALCON",
  "Boxes are top-level classes; edges are object properties. Dashed edges are never asserted and are produced only by reasoning."));
children.push(H2("Knowledge Representation Framework"));
children.push(P(`Option C, Python with owlready2, is the primary implementation. The ontology is generated from one Python specification, so it can be rebuilt and tested on every change; owlready2 runs HermiT and Pellet, executes SPARQL, and saves RDF/XML that opens in Protégé 5; and because the specification is ordinary Python, it can also drive a second reasoner. A Protégé-only build would have produced the same ontology without automated tests, and the OBO-format tools (pronto, OAK) lack the property chains and universal restrictions the model depends on.`));
children.push(H2("Ontology Design Patterns"));
children.push(P(`Six patterns shaped the model. Ingredient kinds are individuals rather than classes, because SWRL rules bind only named individuals. Provenance and allergen retention are separate properties: retainsAllergensOf is a sub-property of derivedFrom, and only it carries allergens through a property chain, which reproduces the refined-oil exemption without an exception rule. Gluten is a hazard separate from the wheat allergen, so a coeliac consumer and a wheat-allergic consumer get different answers for the same loaf. The three-way fact "this ingredient is exempt from declaring this allergen in this market" uses the W3C n-ary relation pattern (Noy & Rector, 2006). Label claims are data rather than axioms, so a false claim is reported instead of making the ontology inconsistent. And allergen-group membership is recorded per market, because the markets disagree about what counts as a tree nut.`));
children.push(H2("System Design Principles"));
children.push(P(`Four engineering principles run through the system (Figure 2). One schema module is the single source of truth for both the OWL builder and the rule engine. The knowledge base is validated on load for dangling references and circular derivations. Conclusions are explainable by construction, because the engine stores the premises of every fact it derives. And the pipeline is reproducible: one command regenerates every output, ${d.tests} automated tests pin down the behaviour this report relies on, and a continuous-integration workflow repeats the full run, Pellet and HermiT included, on every commit (the Pellet bundled with owlready2 0.51 needs Java 25, which the setup installs).`));
children.push(...figure("fig03_architecture.png", "System Architecture",
  "Arrows show data flow. The same schema and rule catalogue feed both the OWL ontology and the rule engine, and every figure and table in this report is generated from the outputs folder."));

children.push(H1("Implementation"));
children.push(H2("Ontology Structure"));
children.push(P(`Table 1 summarizes the ontology. Its class hierarchy (Figure 3) has four origin branches for ingredients (plant, animal, other, and compound), with VegetarianIncompatibleIngredient as a second parent for fish, shellfish, meat, slaughter by-products, and insect-derived additives. Defined classes do most of the classification. For example, NonVeganIngredient ≡ AnimalDerivedIngredient ⊔ ∃hasComponent.AnimalDerivedIngredient, and because hasComponent is transitive, an anchovy two levels inside a compound ingredient is enough. Four property chains propagate allergens: retainsAllergensOf ∘ triggersAllergen ⊑ triggersAllergen and hasComponent ∘ triggersAllergen ⊑ triggersAllergen move them up through ingredients, and two further chains lift containsAllergen and mayContain through the allergen hierarchy. A general class axiom, ∃derivedFrom.AnimalDerivedIngredient ⊑ AnimalDerivedIngredient, passes animal origin through any derivation. Restrictions include an exact cardinality (every product has exactly one barcode) and a qualified one, MultiMarketProduct ≡ Product ⊓ ≥2 soldIn.Jurisdiction, which depends on AllDifferent assertions because OWL makes no unique-name assumption.`));
children.push(...table("Ontology Metrics", ["Element", "Count", "Notes"], [2900, 1100, 5360], [
  ["Named classes", d.classes_named, "Asserted hierarchy, including two classes with multiple parents"],
  ["Defined classes (owl:equivalentClass)", d.classes_defined, `${d.classes_defined - 14} allergen-specific product classes plus 14 others`],
  ["Object properties", d.object_properties, `${d.transitive} transitive, ${d.subproperties} sub-properties, 1 inverse pair`],
  ["Data properties", d.data_properties, "All functional"],
  ["Property chains", d.chains, "Allergen propagation through ingredients and allergen groups"],
  ["General class axioms", d.gcis, "Origin and gluten/lactose inheritance"],
  ["Cardinality and value restrictions", d.restrictions, "Exact, minimum, maximum and hasValue"],
  ["Disjointness axioms", d.disjoint, "Top-level kinds, ingredient origins, animal sources, markets, claims"],
  ["Individuals", d.individuals, `${kb.products} products, ${kb.ingredients} ingredients, ${kb.allergens} allergens and reference data`],
  ["SWRL rules", d.swrl, `${d.swrl - d.swrl_no_builtins} use comparison built-ins`],
  ["Expressivity", "SROIQ(D)", "Full OWL 2 DL"],
], null));
children.push(...figure("fig02_class_hierarchy.png", "Class Hierarchy",
  "Numbers in parentheses count asserted ingredient individuals. Classes marked ≡ are defined classes that the reasoner populates; dotted lines show second parents.", 600));
children.push(P(`Figure 4 shows what this structure does for one product. Smoky Steakhouse Sauce lists seven ingredients and claims to be vegan. Nothing on its label says fish, but the reasoner follows Worcestershire sauce to its anchovy component, concludes that the sauce contains fish and is not vegan, and finds that both of its markets require fish to be declared.`));
children.push(...figure("fig04_product_graph.png", "Knowledge Graph Around One Product",
  "Solid arrows are asserted; dashed arrows are inferred. The highlighted ingredient hides an allergen that its name does not reveal."));
children.push(H2("Rule Design"));
children.push(P(`The rule base has three layers (Table 2). ${d.swrl} SWRL production rules cover allergen detection, claim checking, consumer safety, declaration duties, and numeric thresholds. ${d.engine_rules} engine-only rules add what SWRL cannot express: three-place relations linking an allergen, the ingredient that carries it, and the market that cares; defeasible duties that an exemption can switch off; and negation as failure for verdicts such as "confirmed safe." ${d.integrity_rules} integrity rules treat selected OWL axioms as constraints, the job SHACL would do in production (Knublauch & Kontokostas, 2017). The threshold rules show why exact formulation matters: the EU rule tests greaterThan(x, 10) where the North American rule tests greaterThanOrEqual(x, 10), and a product at exactly 10 mg/kg falls between them.`));
children.push(...table("Selected Rules in First-Order Form", ["ID", "Rule", "Purpose"], [700, 6260, 2400],
  d.rule_table.map((r) => [r.id, r.fol, r.name]),
  `R rules are SWRL and run in both Pellet and the engine; E rules run in the engine only. "not" denotes negation as failure. The full SWRL catalogue is in Appendix B.`));
children.push(H2("Technical Architecture"));
children.push(P(`The loader validates the JSON knowledge base (Figure 2). The ontology builder turns the schema and data into OWL, and the engine bridge translates the Horn-expressible part of the same schema (sub-class and sub-property axioms, inverses, transitivity, chains, and the sufficient conditions of defined classes, ${d.tbox_rules} rules in all) into engine rules, which is essentially the OWL 2 RL reading of the axioms (Motik et al., 2012). The forward chainer uses semi-naive evaluation over stratified rules. The backward chainer uses SLD resolution with loop checking and, when a goal fails, names the first condition that blocked each rule. Competency questions, edge-case experiments, and the cross-validation draw on both reasoners, and their results are written to one folder from which this report's figures and tables, and an interactive Streamlit application, are generated.`));

children.push(H1("Evaluation and Results"));
children.push(H2("Reasoning Performance"));
children.push(P(`From ${fmt(eng.base_facts)} asserted facts, forward chaining derived ${fmt(eng.derived_facts)} facts across ${eng.strata} strata in ${eng.elapsed_s.toFixed(2)} seconds. Figure 5 shows the backward-chaining proof that the steakhouse sauce's vegan claim is false; it reaches down through four rule applications to the asserted fact that anchovy is a fish ingredient. On all ${d.showcase} showcase goals, backward chaining reached the same verdict as forward chaining, in ${d.backward_ms} ms per goal on average. Table 3 lists each competency question with its answer.`));
children.push(...figure("fig05_proof_tree.png", "Backward-Chaining Proof That the Steakhouse Sauce's Vegan Claim Is False",
  "Each box is a goal; violet boxes name the rule applied and blue boxes are asserted facts. The same derivation is recorded, in reverse order, by the forward chainer."));
children.push(...table("Competency Questions and Answers", ["ID", "Question", "Answer"], [700, 4560, 4100],
  d.cq_table.map((c) => [c.id, c.question, c.answer]),
  "Answers come from the rule engine; SPARQL versions of CQ01 to CQ11, CQ13, and CQ14 run against the Pellet-materialized ontology."));
children.push(P(`The claim audit is the clearest result (Figure 6). Of ${ins.claims_total} claims, ${audit.VERIFIED} were verified, ${audit.CONTRADICTED} were contradicted by the product's own composition, ${audit["AT RISK"]} were undermined by a "may contain" warning, and ${audit.UNVERIFIABLE} could be neither confirmed nor refuted; the US term "non-dairy" is informational only. Contradictions arrived through every route the model encodes: insects (carmine in "vegan" gummies), honey, animal rennet inside parmesan, barley malt in "gluten-free" flakes, and egg yolk inside the mayonnaise of an "egg-free" coleslaw. On compliance, ${ins.undeclared_pairs} undeclared allergen obligations appeared in ${ins.products_with_undeclared_allergen} products, and ${ins.market_disagreements} product–allergen pairs were treated differently by markets that sell the same product (Figure 7). Figure 8 shows the consequence for each of the nine consumer profiles.`));
children.push(...figure("fig06_claim_audit.png", "Audit of Every Label Claim in the Knowledge Base",
  "Verified claims hold under the local closed-world assumption; unverifiable claims are not contradicted but depend on missing or ambiguous data."));
children.push(...figure("fig07_market_grid.png", "Allergens Each Market Requires to Be Declared",
  "Shaded rows are where the three markets disagree. Sulphite thresholds differ in their comparison operator, not their value.", 520));
children.push(...figure("fig08_consumer_matrix.png", "Safety Verdict for Every Product and Consumer Profile",
  "Grey columns are the two incomplete records, which can never be confirmed safe. A cross marks a diet the product does not suit."));
children.push(H2("Consistency and Completeness"));
children.push(P(`${owlConsistency} Table 4 compares the reasoner runs. Within the engine, the integrity rules found no violations in the curated data, and all ${d.tests} tests pass. Completeness was judged against the requirements: every competency question is answered, every edge case behaves as expected, and every product exercises at least one rule. The engine's closed-world classes are deliberately not derivable in OWL; under the open-world assumption VeganCompatibleProduct has no members${ec2}.`));
children.push(...table("Reasoner Runs on the Curated Knowledge Base", ["Run", "Result", "Time"], [3800, 3560, 2000], [
  ["FALCON engine, forward chaining", `${fmt(eng.derived_facts)} facts derived, ${eng.strata} strata`, `${eng.elapsed_s.toFixed(2)} s`],
  ["FALCON engine, backward chaining", `${d.showcase} showcase goals, all agree with forward`, `${d.backward_ms} ms per goal`],
  ["Pellet (OWL 2 DL + 17 SWRL rules)", owlOk ? `${d.owl.pellet.status}; ${fmt(d.owl.facts_inferred || 0)} facts inferred` : pending("status"), owlOk ? durShort(d.owl.pellet.seconds) : pending("time")],
  ["HermiT (OWL 2 DL + DL-safe rules)", owlOk && d.owl.hermit ? d.owl.hermit.status : pending("status"), owlOk && d.owl.hermit ? durShort(d.owl.hermit.seconds) : pending("time")],
  ["Pellet vs engine cross-validation", owlOk ? `${fmt(d.owl.crossval_agree)} of ${fmt(d.owl.crossval_total)} facts agree; ${d.owl.crossval_predicates} predicates compared` : pending("agreement"), ""],
], "All figures come from one complete run on Google Colab (Python 3.13, owlready2 0.51, Java 25); see outputs/owl_results.json."));
children.push(H2("Edge Cases"));
children.push(P(`Incomplete information was tested under three assumptions (Figure 9, left). Under the open-world assumption no product could be confirmed safe or vegan. A naive closed-world reading, in which absence of evidence counts as safety, confirmed ${ec1.naive_safe} product–consumer pairs, ${ec1.false_safe} of them wrongly, and gave ${ec1.false_vegan} false vegan verdicts, all from the two incomplete records or from ingredients of unstated origin. The local closed-world assumption confirmed ${ec1.lcwa_safe} pairs with no false assurances. Conflicting data behaved as designed: asserting vegan claims as axioms makes the ontology inconsistent${ec3}, whereas the engine reports each contradiction and keeps every unrelated conclusion. An injected error, honey typed as plant-derived, was caught by a disjointness rule while all ${d.ec4_unsafe} unsafe verdicts stayed unchanged${ec4owl}. Unspecified lecithin produced "uncertain" verdicts and ${ins.supplier_checks} supplier checks rather than guesses. Finally, a keyword screener reached a precision and recall of ${prec} (Figure 9, right). It flagged cocoa butter as dairy and Codex wheat starch as fish (because of the letters "cod"), and it missed caseinate, tahini, and surimi.`));
children.push(...figure("fig09_world_assumptions.png", "Incomplete Records Under Three Assumptions, and Keyword Screening Versus the Ontology",
  "Left: product–consumer pairs confirmed safe; red marks false assurances. Right: allergen detections by substring matching, scored against the ontology's conclusions."));
children.push(H2("Limitations Identified"));
children.push(P(`The system cannot represent ingredient quantities, so percentage thresholds and dose are out of reach. It has no model of cross-contact probability, so precautionary labels are taken at face value. It has no notion of time, so a recipe change or regulatory update overwrites the old knowledge instead of coexisting with it. Three-place relations exist in OWL only as reified individuals, SWRL can neither create individuals nor retract conclusions, and the regulatory lists are simplified; Canada's rule that directly added sulphites must be declared at any level, for example, is not modelled. The knowledge base is small, and matching free-text labels relies on a hand-built lexicon.`));

children.push(H1("Critical Analysis"));
children.push(H2("Expressiveness Versus Computational Complexity"));
children.push(P(`The ontology uses intersection, union, complement, existential and universal restrictions, a property hierarchy, transitive and inverse properties, nominals, qualified cardinality, property chains, and datatypes, which places it in SROIQ(D), the full OWL 2 DL. Consistency checking there is N2ExpTime-complete in the worst case (Kazakov, 2008). Even this small ontology made the practical cost visible${pelletSpan ? `: with hasValue nominals, SWRL rules, and full property-value inference all in play, every complete Pellet run took ${pelletSpan}, although Pellet detected each injected contradiction in about a second` : ""}. The engine sits at the other end of the trade-off: Datalog with stratified negation has polynomial data complexity, so its runtime grows predictably with the number of products. The price is expressiveness. The engine sees only the Horn part of the axioms, so a universal restriction such as VeganCompatibleProduct must be rewritten as an explicitly closed-world rule. The OWL 2 RL profile would give polynomial reasoning inside OWL (Motik et al., 2012), but it gives up the universal restrictions and unions on which vegan classification depends.`));
children.push(H2("Alternative Approaches"));
children.push(P(`Three alternatives were weighed. A Protégé-only build (Option A) would have produced the same ontology but no tests, no negation as failure, and no readable proofs, and every edge case in Figure 9 would collapse to the open-world row. A pure logic program would have made exemptions and closed-world verification easier but lost open-world classification and the standard tooling that lets others reuse the ontology. Knowledge-graph embeddings (Option B), such as TransE (Bordes et al., 2013) trained with pykg2vec (Yu et al., 2021), would learn to rank likely missing links, such as a probable "may contain" warning for a product made on shared lines (Hogan et al., 2021). That suits triage, but it replaces a proof with a score: every result in this report would become a probability, and a hidden allergen would be flagged only if similar products had been labelled the same way. For a safety question that is unacceptable as the primary method, though useful as a secondary one.`));
children.push(H2("Scalability Considerations"));
children.push(P(`The engine was benchmarked on synthetic knowledge bases that replicate the curated products with one random ingredient swapped per copy (Figure 10). From ${bmin ? fmt(bmin.products) : "?"} to ${bmax ? fmt(bmax.products) : "?"} products, runtime grew in proportion to size (fitted exponent ${d.bench.engine_slope}), reaching ${bmax ? bmax.seconds_min.toFixed(1) : "?"} seconds for ${bmax ? fmt(bmax.derived_facts) : "?"} derived facts, while backward queries stayed near ${bmax ? bmax.backward_ms_per_query.toFixed(1) : "?"} ms. ${owlScaling} Because products are independent of one another, a production system could classify the shared terminology once and partition the product records, keeping description-logic reasoning for the ontology and a Datalog or OWL 2 RL engine for the millions of records in open food databases.`));
children.push(...figure("fig10_scalability.png", "Scalability of Reasoning With Knowledge-Base Size",
  "Left: wall-clock time on log–log axes, where a slope of 1 means linear growth. Hollow markers are uncapped runs; a cross marks a run stopped at the 150-second limit. Right: derived facts and the median time of a backward-chaining query."));

children.push(H1("Conclusion"));
children.push(P(`The conclusion is written as a briefing to the head of a food company's regulatory team.`));
children.push(Pn(`*To:* Director of Food Safety and Regulatory Affairs`));
children.push(Pn(`*From:* Knowledge Engineering, FALCON project`));
children.push(Pn(`*Re:* What the allergen knowledge model tells us about labelling risk`));
children.push(P(`Market rules differ in ways that matter. Pine nuts must be declared as a tree nut in the United States and Canada but not in the EU; mustard is declarable in Canada and the EU but not the United States; celery and lupin are EU-only; and at exactly 10 mg/kg of sulphites a product needs a declaration in North America but not in Europe. In our test portfolio, ${ins.market_disagreements} product–allergen pairs were handled differently by markets selling the same product. A single global checklist cannot catch these; compliance has to be checked market by market.`));
children.push(P(`Hidden allergens arrive through ingredients made from, or containing, other ingredients: caseinate in a "non-dairy" whitener, anchovy in Worcestershire sauce, egg-white lysozyme in cheese, tahini in hummus. The model found ${ins.hidden_allergen_findings} such cases. Keyword screening both misses these and raises false alarms (precision and recall of ${prec}), so ingredient data should be mapped to a structured ontology rather than matched as text.`));
children.push(P(`Several claims do not mean what customers assume. "Non-dairy" permits milk protein, "lactose-free" says nothing about milk allergy, "gluten-free" is not wheat-free, and "dairy-free" next to "may contain milk" sends two opposite messages. Claims and precautionary statements should be reviewed together, against the recipe, before a label is approved.`));
children.push(P(`Data completeness is a safety issue. Treating missing information as good news produced ${ins.naive_closed_world_false_assurances} false assurances in our tests. Only records with complete ingredient specifications should receive a "safe" or "vegan" verdict, and ingredients of unstated origin, such as lecithin and E471, need supplier statements; the model raised ${ins.supplier_checks} such requests.`));
if (owlOk && allAgree) children.push(P(`Formal reasoning and fast checking can work together. The OWL reasoner and the rule engine reached the same conclusions on all ${fmt(d.owl.crossval_agree)} facts the reasoner inferred, but the reasoner needed about ${Math.round(d.owl.pellet.seconds / 60)} minutes where the engine needed ${engineSeconds.toFixed(2)} seconds. The reasoner should validate the terminology whenever it changes; the engine should run the day-to-day label checks.`));
children.push(P(`These figures come from a curated test portfolio, so they show what the method can detect rather than how often problems occur. The next phase should load real product data from an open food database, align ingredient classes with FoodOn, add SHACL validation at data entry, model cross-contact risk explicitly, and test knowledge-graph embeddings as a triage tool that suggests which products to review first.`));
counting = false;

// References
children.push(H1("References", true));
const refs = [
  "Anthropic. (2026). *Claude* (Opus 5.5 version) [Large language model]. https://claude.ai",
  "Antoniou, G., Billington, D., Governatori, G., & Maher, M. J. (2001). Representation results for defeasible logic. *ACM Transactions on Computational Logic, 2*(2), 255–287. https://doi.org/10.1145/371316.371517",
  "Apt, K. R., Blair, H. A., & Walker, A. (1988). Towards a theory of declarative knowledge. In J. Minker (Ed.), *Foundations of deductive databases and logic programming* (pp. 89–148). Morgan Kaufmann.",
  "Bordes, A., Usunier, N., Garcia-Durán, A., Weston, J., & Yakhnenko, O. (2013). Translating embeddings for modeling multi-relational data. In *Advances in Neural Information Processing Systems 26* (pp. 2787–2795). Curran Associates.",
  "Codex Alimentarius Commission. (2008). *Standard for foods for special dietary use for persons intolerant to gluten* (CXS 118-1979, revised 2008). Food and Agriculture Organization of the United Nations & World Health Organization.",
  "Courtot, M., Gibson, F., Lister, A. L., Malone, J., Schober, D., Brinkman, R. R., & Ruttenberg, A. (2011). MIREOT: The minimum information to reference an external ontology term. *Applied Ontology, 6*(1), 23–33. https://doi.org/10.3233/AO-2011-0087",
  "Dooley, D. M., Griffiths, E. J., Gosal, G. S., Buttigieg, P. L., Hoehndorf, R., Lange, M. C., Schriml, L. M., Brinkman, F. S. L., & Hsiao, W. W. L. (2018). FoodOn: A harmonized food ontology to increase global food traceability, quality control and data integration. *npj Science of Food, 2*, Article 23. https://doi.org/10.1038/s41538-018-0032-6",
  "Etzioni, O., Golden, K., & Weld, D. S. (1997). Sound and efficient closed-world reasoning for planning. *Artificial Intelligence, 89*(1–2), 113–148. https://doi.org/10.1016/S0004-3702(96)00026-4",
  "European Parliament & Council of the European Union. (2011). Regulation (EU) No 1169/2011 of 25 October 2011 on the provision of food information to consumers. *Official Journal of the European Union, L 304*, 18–63. https://eur-lex.europa.eu/eli/reg/2011/1169/oj",
  "Food Allergy Research & Resource Program. (n.d.). *Dairy free and non-dairy*. University of Nebraska–Lincoln. Retrieved October 27, 2026, from https://farrp.unl.edu/resources/gi-fas/opinion-and-summaries/dairy-free-and-non-dairy",
  "Food; Designation of Ingredients, 21 C.F.R. § 101.4 (2025).",
  "Food: Exemptions From Labeling, 21 C.F.R. § 101.100 (2025).",
  "Gendel, S. M., & Zhu, J. (2013). Analysis of U.S. Food and Drug Administration food allergen recalls after implementation of the Food Allergen Labeling and Consumer Protection Act. *Journal of Food Protection, 76*(11), 1933–1938. https://doi.org/10.4315/0362-028X.JFP-13-096",
  "Glimm, B., Horrocks, I., Motik, B., Stoilos, G., & Wang, Z. (2014). HermiT: An OWL 2 reasoner. *Journal of Automated Reasoning, 53*(3), 245–269. https://doi.org/10.1007/s10817-014-9305-1",
  "Grosof, B. N., Horrocks, I., Volz, R., & Decker, S. (2003). Description logic programs: Combining logic programs with description logic. In *Proceedings of the 12th International Conference on World Wide Web* (pp. 48–57). ACM. https://doi.org/10.1145/775152.775160",
  "Gruber, T. R. (1993). A translation approach to portable ontology specifications. *Knowledge Acquisition, 5*(2), 199–220. https://doi.org/10.1006/knac.1993.1008",
  "Grüninger, M., & Fox, M. S. (1995). Methodology for the design and evaluation of ontologies. In *Proceedings of the Workshop on Basic Ontological Issues in Knowledge Sharing, IJCAI-95*. Montréal, Canada.",
  "Gupta, R. S., Warren, C. M., Smith, B. M., Jiang, J., Blumenstock, J. A., Davis, M. M., Schleimer, R. P., & Nadeau, K. C. (2019). Prevalence and severity of food allergies among US adults. *JAMA Network Open, 2*(1), Article e185630. https://doi.org/10.1001/jamanetworkopen.2018.5630",
  "Haussmann, S., Seneviratne, O., Chen, Y., Ne'eman, Y., Codella, J., Chen, C.-H., McGuinness, D. L., & Zaki, M. J. (2019). FoodKG: A semantics-driven knowledge graph for food recommendation. In *The Semantic Web – ISWC 2019* (Lecture Notes in Computer Science, Vol. 11779, pp. 146–162). Springer. https://doi.org/10.1007/978-3-030-30796-7_10",
  "Health Canada. (n.d.). *Questions and answers about the new regulations to enhance the labelling of food allergens, gluten and added sulphites*. Government of Canada. Retrieved October 27, 2026, from https://www.canada.ca/en/health-canada/services/food-nutrition/food-labelling/allergen-labelling/questions-answers-about-new-regulations-enhance-labelling-food-allergens-gluten-added-sulphites.html",
  "Hogan, A., Blomqvist, E., Cochez, M., d'Amato, C., de Melo, G., Gutierrez, C., Kirrane, S., Labra Gayo, J. E., Navigli, R., Neumaier, S., Ngonga Ngomo, A.-C., Polleres, A., Rashid, S. M., Rula, A., Schmelzeisen, L., Sequeda, J., Staab, S., & Zimmermann, A. (2021). Knowledge graphs. *ACM Computing Surveys, 54*(4), Article 71. https://doi.org/10.1145/3447772",
  "Horrocks, I., Kutz, O., & Sattler, U. (2006). The even more irresistible SROIQ. In *Proceedings of the 10th International Conference on Principles of Knowledge Representation and Reasoning* (pp. 57–67). AAAI Press.",
  "Horrocks, I., Patel-Schneider, P. F., Boley, H., Tabet, S., Grosof, B., & Dean, M. (2004). *SWRL: A semantic web rule language combining OWL and RuleML* (W3C Member Submission). World Wide Web Consortium. https://www.w3.org/Submission/SWRL/",
  "Kazakov, Y. (2008). RIQ and SROIQ are harder than SHOIQ. In *Proceedings of the 11th International Conference on Principles of Knowledge Representation and Reasoning* (pp. 274–284). AAAI Press.",
  "Knublauch, H., & Kontokostas, D. (Eds.). (2017). *Shapes constraint language (SHACL)* (W3C Recommendation). World Wide Web Consortium. https://www.w3.org/TR/shacl/",
  "Lamy, J.-B. (2017). Owlready: Ontology-oriented programming in Python with automatic classification and high level constructs for biomedical ontologies. *Artificial Intelligence in Medicine, 80*, 11–28. https://doi.org/10.1016/j.artmed.2017.07.002",
  "Motik, B., Cuenca Grau, B., Horrocks, I., Wu, Z., Fokoue, A., & Lutz, C. (Eds.). (2012). *OWL 2 Web Ontology Language profiles* (2nd ed., W3C Recommendation). World Wide Web Consortium. https://www.w3.org/TR/owl2-profiles/",
  "Motik, B., Sattler, U., & Studer, R. (2005). Query answering for OWL-DL with rules. *Journal of Web Semantics, 3*(1), 41–60. https://doi.org/10.1016/j.websem.2005.05.001",
  "Noy, N., & Rector, A. (2006). *Defining n-ary relations on the Semantic Web* (W3C Working Group Note). World Wide Web Consortium. https://www.w3.org/TR/swbp-n-aryRelations/",
  "Noy, N. F., & McGuinness, D. L. (2001). *Ontology development 101: A guide to creating your first ontology* (Technical Report KSL-01-05). Stanford Knowledge Systems Laboratory.",
  "Rector, A., Drummond, N., Horridge, M., Rogers, J., Knublauch, H., Stevens, R., Wang, H., & Wroe, C. (2004). OWL pizzas: Practical experience of teaching OWL-DL: Common errors and common patterns. In E. Motta, N. R. Shadbolt, A. Stutt, & N. Gibbins (Eds.), *Engineering knowledge in the age of the Semantic Web* (Lecture Notes in Computer Science, Vol. 3257, pp. 63–81). Springer. https://doi.org/10.1007/978-3-540-30202-5_5",
  "Reiter, R. (1978). On closed world data bases. In H. Gallaire & J. Minker (Eds.), *Logic and data bases* (pp. 55–76). Plenum Press.",
  "Sirin, E., Parsia, B., Cuenca Grau, B., Kalyanpur, A., & Katz, Y. (2007). Pellet: A practical OWL-DL reasoner. *Journal of Web Semantics, 5*(2), 51–53. https://doi.org/10.1016/j.websem.2007.03.004",
  "Smith, B., Ashburner, M., Rosse, C., Bard, J., Bug, W., Ceusters, W., Goldberg, L. J., Eilbeck, K., Ireland, A., Mungall, C. J., Leontis, N., Rocca-Serra, P., Ruttenberg, A., Sansone, S.-A., Scheuermann, R. H., Shah, N., Whetzel, P. L., & Lewis, S. (2007). The OBO Foundry: Coordinated evolution of ontologies to support biomedical data integration. *Nature Biotechnology, 25*(11), 1251–1255. https://doi.org/10.1038/nbt1346",
  "U.S. Food and Drug Administration. (2025). *Questions and answers regarding food allergens, including the food allergen labeling requirements of the Federal Food, Drug, and Cosmetic Act (Edition 5): Guidance for industry*. https://www.fda.gov/regulatory-information/search-fda-guidance-documents",
  "Wilkinson, M. D., Dumontier, M., Aalbersberg, I. J., Appleton, G., Axton, M., Baak, A., Blomberg, N., Boiten, J.-W., da Silva Santos, L. B., Bourne, P. E., Bouwman, J., Brookes, A. J., Clark, T., Crosas, M., Dillo, I., Dumon, O., Edmunds, S., Evelo, C. T., Finkers, R., . . . Mons, B. (2016). The FAIR guiding principles for scientific data management and stewardship. *Scientific Data, 3*, Article 160018. https://doi.org/10.1038/sdata.2016.18",
  "Yu, S.-Y., Rokka Chhetri, S., Canedo, A., Goyal, P., & Al Faruque, M. A. (2021). Pykg2vec: A Python library for knowledge graph embedding. *Journal of Machine Learning Research, 22*(16), 1–6.",
];
refs.forEach((r) => children.push(new Paragraph({ indent: { left: 720, hanging: 720 }, children: runs(r) })));

// Appendix A: reproduction
children.push(H1("Appendix A", true));
children.push(C("Reproducing the Results", true));
children.push(P(`All code, data, and outputs are in the project repository. The commands below rebuild every number in this report; the continuous-integration workflow runs the same steps on every commit and publishes the outputs folder as a downloadable artifact.`));
children.push(...table("Commands", ["Step", "Command"], [3200, 6160], [
  ["Install (Windows)", "setup_windows.ps1 (creates .venv, installs Java if missing)"],
  ["Check environment", "python check_environment.py"],
  ["Run the tests", "python -m unittest discover -s tests -t ."],
  ["Full pipeline", "python run_all.py"],
  ["Scalability benchmark", "python -m falcon.benchmark --owl"],
  ["Figures", "python -m falcon.viz"],
  ["Interactive app", "streamlit run app/streamlit_app.py"],
  ["Rebuild this report", "python report/prepare_data.py; node report/build_report.js"],
], null, "Table A1"));

// Appendix B: SWRL catalogue
children.push(H1("Appendix B", true));
children.push(C("SWRL Rule Catalogue", true));
children.push(...table("All SWRL Production Rules", ["ID", "Name", "Rule"], [700, 2500, 6160],
  d.swrl_table.map((r) => [r.id, r.name, r.fol]),
  "Rules R14 to R17 use SWRL comparison built-ins and are therefore executed by Pellet but not by HermiT.", "Table B1"));

// ---------------------------------------------------------------- assemble
const doc = new Document({
  creator: "Anush Goel",
  title,
  description: "FALCON technical report",
  styles: {
    default: { document: { run: { font: "Times New Roman", size: 24 }, paragraph: { spacing: { line: 480, lineRule: "auto", before: 0, after: 0 } } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Times New Roman", size: 24, bold: true, color: "000000" },
        paragraph: { alignment: AlignmentType.CENTER, spacing: { line: 480, lineRule: "auto", before: 0, after: 0 }, outlineLevel: 0, keepNext: true } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Times New Roman", size: 24, bold: true, color: "000000" },
        paragraph: { alignment: AlignmentType.LEFT, spacing: { line: 480, lineRule: "auto", before: 0, after: 0 }, outlineLevel: 1, keepNext: true } },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ children: [PageNumber.CURRENT] })] })] }) },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(outFile, buf);
  console.log(`wrote ${outFile} (${variant}); body words (Introduction to Conclusion): ${bodyWords}; abstract words: ${wordsIn(abstract)}; figures: ${figNo}; tables: ${tabNo}`);
});
