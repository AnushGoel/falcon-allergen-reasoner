"""
FALCON Label X-ray: an interactive front end to the knowledge representation system.

    streamlit run app/streamlit_app.py

The rule engine is pure Python, so the app reasons live (no Java needed).
Pellet/HermiT results are shown from outputs/ when a full run has produced them.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from falcon import app_logic as logic  # noqa: E402
from falcon import competency, edge_cases, viz  # noqa: E402
from falcon.config import OUTPUT_DIR  # noqa: E402
from falcon.rule_engine import Atom  # noqa: E402

INK, VIOLET, TEAL, RED, MUSTARD, GREEN, GREY = "#1C2541", "#6C4BD8", "#2B7A9B", "#C8382E", "#D9A21B", "#2F7D4F", "#8A94A6"
STATUS = {"VERIFIED": ("Verified", GREEN), "CONTRADICTED": ("Contradicted", RED), "AT RISK": ("At risk", MUSTARD),
          "UNVERIFIABLE": ("Unverifiable", VIOLET), "INFORMATIONAL": ("Informational", GREY), "UNSAFE": ("Unsafe", RED),
          "CAUTION": ("Caution", MUSTARD), "UNCERTAIN": ("Uncertain", VIOLET), "SAFE": ("Safe", GREEN),
          "NOT CONFIRMED": ("Not confirmed", GREY)}
SAMPLES = {
    "Steakhouse sauce": ("Tomato, spirit vinegar, sugar, Worcestershire sauce, onion, salt, paprika",
                         ["claim_vegan"], ["jur_us", "jur_canada"]),
    "Coffee whitener": ("Corn syrup solids, coconut oil, sodium caseinate, dipotassium phosphate (E340), "
                        "mono- and diglycerides (E471), natural flavouring", ["claim_non_dairy"], ["jur_us"]),
    "Pesto": ("Basil, sunflower oil, parmesan cheese, cashew nuts, pine nuts, garlic, salt",
              ["claim_vegetarian"], ["jur_us", "jur_canada", "jur_eu"]),
    "Write your own": ("", [], ["jur_us", "jur_canada", "jur_eu"]),
}
PLOT_FONT = dict(family="Archivo, Helvetica Neue, Arial, sans-serif", color=INK, size=12)

st.set_page_config(page_title="FALCON Label X-ray", page_icon="\U0001F52C", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,300..900&display=swap');
html, body, .stApp, .stMarkdown, p, li, label, input, textarea, button, h1, h2, h3, h4 {
  font-family: 'Archivo', 'Helvetica Neue', Arial, sans-serif;
}
.stApp { color: #1C2541; }
h2, h3, h4 { letter-spacing: -0.01em; }
.falcon-title { font-size: 3.2rem; font-weight: 900; font-stretch: 86%; line-height: 0.95; margin: 0.4rem 0 0.7rem 0; }
.falcon-lede { font-size: 1.07rem; line-height: 1.6; max-width: 36rem; color: #33405A; }
.panel { border: 2.5px solid #1C2541; background: #FFFFFF; padding: 0.95rem 1.15rem 0.85rem; }
.panel h4 { font-weight: 900; font-stretch: 78%; font-size: 1.5rem; margin: 0 0 0.4rem 0; padding: 0 0 0.35rem 0;
            border-bottom: 7px solid #1C2541; }
.panel .ingredients { font-stretch: 84%; font-size: 1.03rem; line-height: 1.65; }
.panel .lead, .panel .allergen { font-weight: 800; }
.panel .xray { background: rgba(108,75,216,0.13); border-bottom: 2px solid #6C4BD8; padding: 0 0.12rem; transition: background 320ms ease; }
.panel .xnote { color: #6C4BD8; font-weight: 700; font-size: 0.8rem; white-space: nowrap; }
.panel .row { border-top: 1px solid #1C2541; margin-top: 0.6rem; padding-top: 0.45rem; font-size: 0.93rem; }
.tag { display: inline-block; padding: 0.05rem 0.45rem; border-radius: 2px; font-weight: 700; font-size: 0.8rem;
       margin: 0.1rem 0.2rem 0.1rem 0; border: 1px solid currentColor; background: #FFFFFF; }
.chip { display: inline-block; padding: 0.12rem 0.55rem; margin: 0.15rem 0.25rem 0.15rem 0; border: 1px solid #DDE2EA;
        border-radius: 999px; font-size: 0.86rem; background: #FFFFFF; }
.chip.hidden { border-color: #6C4BD8; background: rgba(108,75,216,0.08); }
.chip.unknown { border-style: dashed; color: #5B6577; }
.chain { color: #6C4BD8; font-size: 0.88rem; margin: 0.15rem 0; }
.small { color: #5B6577; font-size: 0.86rem; }
@media (prefers-reduced-motion: reduce) { .panel .xray { transition: none; } }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Cached resources
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Running the reasoner over the knowledge base...")

def _duration(seconds):
    """Reasoner time as seconds, or as minutes once it passes two minutes."""
    return "%.1f min" % (seconds / 60) if seconds >= 120 else "%.2f s" % seconds

def engine():
    return logic.load_engine()


@st.cache_resource(show_spinner=False)
def lexicon():
    return logic.build_lexicon(engine()[0])


@st.cache_resource(show_spinner=False, max_entries=64)
def analysis(name, ingredients, claims, markets, may_contain, declared, complete):
    kb, rules, _ = engine()
    return logic.analyse_label(kb, rules, name, ingredients, claims, markets, may_contain, declared, complete)


@st.cache_resource(show_spinner=False)
def answers():
    return competency.answer_all(engine()[2])


@st.cache_resource(show_spinner=False)
def cases():
    return edge_cases.run_all(engine()[2])


def read_output(name):
    path = OUTPUT_DIR / name
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except Exception:
        return None


def tag(status):
    text, color = STATUS[status]
    return '<span class="tag" style="color:%s">%s</span>' % (color, text)


def show_fig(fig):
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


def styled(fig, height):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), font=PLOT_FONT,
                      paper_bgcolor="white", plot_bgcolor="white")
    return fig


def explain(kb, proof):
    plain = logic.explain_plain(kb, proof)
    st.markdown("**%s**, because:" % (plain["conclusion"][0].upper() + plain["conclusion"][1:]))
    st.markdown("\n".join("- %s" % f for f in plain["facts"]))
    if plain["tests"]:
        st.caption("Numeric tests: " + "; ".join(plain["tests"]))
    st.caption("Rules applied: " + "; ".join(plain["rules"]))


# ---------------------------------------------------------------------------
# Hero: the label, and what it hides
# ---------------------------------------------------------------------------

def label_panel(kb, ctx, pid, xray):
    p, res = kb.products[pid], ctx.result
    hidden = {}
    for (_, a, i) in res.query("hiddenAllergenVia", pid, None, None):
        hidden.setdefault(i, []).append(kb.label(a).lower())
    declared = set(p["declared"])
    parts = []
    for i in p["ingredients"]:
        name = kb.ingredients[i]["label"]
        carries = {a for (_, a) in res.query("triggersAllergen", i, None)}
        if xray and i in hidden:
            parts.append('<span class="xray">%s</span> <span class="xnote">hides %s</span>' % (name, ", ".join(hidden[i])))
        elif carries & declared:
            parts.append('<span class="allergen">%s</span>' % name)
        else:
            parts.append(name)
    html = ['<div class="panel"><h4>%s</h4><div class="ingredients"><span class="lead">Ingredients:</span> %s.'
            % (p["label"], ", ".join(parts) or "(no ingredient data)")]
    if p["may_contain"]:
        html.append(' <span class="lead">May contain:</span> %s.' % ", ".join(kb.label(a) for a in p["may_contain"]))
    html.append("</div>")
    if p["claims"]:
        claims = ["%s %s" % (kb.label(c), tag(competency.claim_status(ctx, pid, c)) if xray else "") for c in p["claims"]]
        html.append('<div class="row"><span class="lead">On the pack:</span> %s</div>' % " &nbsp; ".join(claims))
    if xray:
        markets = []
        for m in p["sold_in"]:
            missing = [kb.label(a) for (_, a, _) in res.query("undeclaredAllergen", pid, None, m)]
            markets.append("%s %s" % (kb.label(m), '<span class="tag" style="color:%s">%s</span>'
                                      % ((RED, "missing " + ", ".join(missing)) if missing else (GREEN, "compliant"))))
        html.append('<div class="row"><span class="lead">Markets:</span> %s</div>' % " &nbsp; ".join(markets))
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)
    if xray:
        for allergen in logic.summarise(ctx, pid)["allergens"]:
            for h in allergen["hidden"]:
                st.markdown('<div class="chain">%s</div>' % h["chain"], unsafe_allow_html=True)


def hero(kb, ctx):
    left, right = st.columns([5, 6], gap="large")
    products = sorted(kb.products, key=kb.label)
    with left:
        st.markdown('<div class="falcon-title">FALCON</div>', unsafe_allow_html=True)
        st.markdown('<p class="falcon-lede">A food label shows what a manufacturer chose to print. FALCON reads it the '
                    'way a regulator would: it follows every ingredient back to its source, checks each claim, and works '
                    'out which market would reject the product. Every verdict comes with a proof.</p>', unsafe_allow_html=True)
        pid = st.selectbox("Pick a product", products, index=products.index("prod_steakhouse_sauce"), format_func=kb.label)
        xray = st.toggle("X-ray the label", value=False, help="Show what the reasoner inferred that the label does not say.")
        st.caption("%d products, %d ingredients and %d rules; %s facts inferred in %.2f s."
                   % (len(kb.products), len(kb.ingredients), len(ctx.rules), format(len(ctx.result.derived), ","), ctx.result.elapsed_s))
    with right:
        label_panel(kb, ctx, pid, xray)
        if not xray:
            st.caption("Switch on X-ray to see what this label does not tell you.")


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

def tab_check_label(kb):
    st.subheader("Check any ingredient list")
    st.write("Paste a list the way it appears on a pack. FALCON matches each item to the ontology, then reasons about "
             "allergens, claims and markets from scratch.")
    choice = st.radio("Start from", list(SAMPLES), horizontal=True)
    text_default, claims_default, markets_default = SAMPLES[choice]
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        text = st.text_area("Ingredient list (a 'May contain:' sentence is understood too)", value=text_default,
                            height=130, key="text_%s" % choice)
        name = st.text_input("Product name", value=choice if choice != "Write your own" else "My product", key="name_%s" % choice)
    with c2:
        claims = st.multiselect("Claims printed on the pack", list(kb.claims), default=claims_default,
                                format_func=kb.label, key="claims_%s" % choice)
        markets = st.multiselect("Markets", list(kb.jurisdictions), default=markets_default, format_func=kb.label,
                                 key="markets_%s" % choice)
        complete = st.toggle("This is the complete ingredient list", value=True, key="complete_%s" % choice)
    parsed = logic.parse_label(kb, text, lexicon())
    chips = ['<span class="chip">%s</span>' % kb.label(i) for i in parsed["ingredients"]]
    chips += ['<span class="chip unknown">%s ?</span>' % u for u in parsed["unknown"]]
    if chips:
        st.markdown("Recognised: " + "".join(chips), unsafe_allow_html=True)
    effective_complete = complete and not parsed["unknown"]
    if parsed["unknown"] and complete:
        st.warning("%d item(s) are not in the knowledge base, so this record is treated as incomplete and nothing can be "
                   "confirmed safe. That is the local closed-world assumption at work." % len(parsed["unknown"]))
    if not parsed["ingredients"]:
        st.info("Add at least one ingredient to start the analysis.")
        return
    actx = analysis(name, tuple(parsed["ingredients"]), tuple(claims), tuple(markets), tuple(parsed["may_contain"]),
                    tuple(parsed["declared"]), effective_complete)
    summary = logic.summarise(actx, logic.CUSTOM_ID)

    st.markdown("#### What it contains")
    chips = []
    for entry in summary["allergens"]:
        if entry["hidden"]:
            chips.append('<span class="chip hidden">%s, hidden in %s</span>'
                         % (entry["allergen"], ", ".join(h["ingredient"] for h in entry["hidden"])))
        else:
            chips.append('<span class="chip">%s</span>' % entry["allergen"])
    st.markdown("".join(chips) or "No regulated allergens found.", unsafe_allow_html=True)
    for entry in summary["allergens"]:
        for h in entry["hidden"]:
            st.markdown('<div class="chain">%s</div>' % h["chain"], unsafe_allow_html=True)

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("#### Claims")
        if not summary["claims"]:
            st.caption("No claims selected.")
        for c in summary["claims"]:
            st.markdown("%s **%s**: %s" % (tag(c["status"]), c["claim"], c["why"]), unsafe_allow_html=True)
    with right:
        st.markdown("#### Markets")
        if summary["markets"]:
            st.dataframe(pd.DataFrame(summary["markets"]), hide_index=True)
        else:
            st.caption("Pick at least one market.")

    st.markdown("#### Who can eat it")
    cols = st.columns(3)
    for k, c in enumerate(summary["consumers"]):
        with cols[k % 3]:
            diet = ' <span class="small">diet: %s</span>' % c["diet"] if c["diet"] else ""
            st.markdown("%s %s%s" % (tag(c["status"]), c["consumer"], diet), unsafe_allow_html=True)

    st.markdown("#### Ask why")
    options = logic.conclusions(actx, logic.CUSTOM_ID)
    if options:
        pick = st.selectbox("Pick a conclusion to justify", range(len(options)), format_func=lambda k: options[k][0])
        proof = actx.prover.prove(options[pick][1])
        if proof is not None:
            explain(actx.kb, proof)
            with st.expander("Proof tree (backward chaining)"):
                show_fig(viz.fig_proof_tree(actx.kb, proof))
                st.code(proof.render(), language="text")
    events = logic.replay(actx, logic.CUSTOM_ID)
    if events:
        with st.expander("Replay the forward-chaining run (%d derivations about this label)" % len(events)):
            step = st.slider("Step", 1, len(events), len(events)) if len(events) > 1 else 1
            for e in events[max(0, step - 10):step]:
                st.markdown("`%s` derived **%s**  \n<span class='small'>from %s</span>"
                            % (e["rule"], e["fact"], "; ".join(e["premises"][:3]) or "no premises"), unsafe_allow_html=True)
    st.download_button("Download this analysis as JSON", data=json.dumps(summary, indent=2),
                       file_name="falcon_label_analysis.json", mime="application/json")


def tab_myths(ctx):
    st.subheader("Myth or fact?")
    st.write("Twelve things people believe about food labels. Make your call, then let the reasoner settle it. "
             "Nothing here is a lookup table: each answer is proved, or refuted, from the knowledge base.")
    state = st.session_state.setdefault("myths", {})
    done = [m for m in logic.MYTHS if m["key"] in state]
    right = sum(1 for m in done if state[m["key"]]["correct"])
    st.progress(len(done) / len(logic.MYTHS), text="Score: %d correct out of %d checked" % (right, len(done)))
    for n, myth in enumerate(logic.MYTHS, 1):
        with st.container(border=True):
            st.markdown("**%d. %s**" % (n, myth["statement"]))
            guess = st.radio("Your call", ["Myth", "Fact"], index=None, horizontal=True, key="guess_" + myth["key"],
                             label_visibility="collapsed")
            if st.button("Check with the reasoner", key="check_" + myth["key"], disabled=guess is None):
                verdict = logic.check_myth(ctx, myth)
                answer = "Fact" if verdict["is_fact"] else "Myth"
                state[myth["key"]] = {"answer": answer, "correct": guess == answer}
                st.rerun()
            if myth["key"] in state:
                result = state[myth["key"]]
                verdict = logic.check_myth(ctx, myth)
                badge = ('<span class="tag" style="color:%s">%s</span>'
                         % ((GREEN, "You got it") if result["correct"] else (RED, "Not quite")))
                st.markdown("%s The reasoner says **%s**. %s" % (badge, result["answer"].lower(), myth["lesson"]),
                            unsafe_allow_html=True)
                with st.expander("See how it decided"):
                    if verdict["proof"] is not None:
                        explain(ctx.kb, verdict["proof"])
                        st.code(verdict["proof"].render(), language="text")
                    else:
                        st.write("The goal %s could not be derived. What blocked each rule:" % myth["goal"])
                        st.code("\n".join(verdict["why_not"]), language="text")


def tab_graph(kb, ctx):
    st.subheader("Product knowledge graph")
    pid = st.selectbox("Product", sorted(kb.products, key=kb.label), format_func=kb.label, key="graph_product")
    show_fig(viz.fig_product_graph(kb, ctx, pid))
    st.markdown("Classified automatically as " + ", ".join("`%s`" % c for c in logic.summarise(ctx, pid)["classes"]))
    st.markdown("#### The ontology")
    data = logic.hierarchy_data(kb)
    fig = go.Figure(go.Sunburst(ids=data["ids"], labels=data["ids"], parents=data["parents"], values=data["values"],
                                branchvalues="remainder", maxdepth=3, insidetextorientation="radial",
                                hovertemplate="%{label}<br>%{value} individuals (incl. 1 for the class)<extra></extra>"))
    st.plotly_chart(styled(fig, 560))
    st.caption("Segment size reflects how many individuals each class holds. Click a segment to zoom in.")


def tab_atlas(kb, ctx):
    st.subheader("Compliance atlas")
    labels, markets, z = logic.market_matrix(kb)
    fig = go.Figure(go.Heatmap(z=z, x=markets, y=labels, colorscale=[[0, "#FFFFFF"], [1, INK]], showscale=False,
                               xgap=3, ygap=3, customdata=[["must be declared" if v else "not a declarable allergen" for v in row] for row in z],
                               hovertemplate="%{y} in %{x}: %{customdata}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    left, right = st.columns([2, 3], gap="large")
    with left:
        st.markdown("**What each market makes you declare**")
        st.plotly_chart(styled(fig, 720))
        st.caption("Sulphites are declared at 10 ppm or more in the US and Canada, but only above 10 mg/kg in the EU.")
    with right:
        st.markdown("**From ingredient, to allergen, to the market that wants it declared**")
        data = logic.sankey_data(ctx)
        colors = {"ingredient": TEAL, "allergen": VIOLET, "market": INK}
        fig = go.Figure(go.Sankey(arrangement="snap",
                                  node=dict(label=data["labels"], color=[colors[k] for k in data["kinds"]], pad=9, thickness=12),
                                  link=dict(source=data["source"], target=data["target"], value=data["value"],
                                            color="rgba(108,75,216,0.18)")))
        st.plotly_chart(styled(fig, 720))
    st.markdown("**Undeclared allergens and supplier checks**")
    st.dataframe(pd.DataFrame(answers()["CQ13"]["rows"]), hide_index=True)
    st.markdown("**Who can eat what**")
    products, consumers, statuses = logic.consumer_matrix(ctx)
    codes = {"UNSAFE": 0, "CAUTION": 1, "UNCERTAIN": 2, "NOT CONFIRMED": 3, "SAFE": 4}
    scale = [[0, RED], [0.125, RED], [0.125, MUSTARD], [0.375, MUSTARD], [0.375, VIOLET], [0.625, VIOLET],
             [0.625, "#C9CFD9"], [0.875, "#C9CFD9"], [0.875, GREEN], [1, GREEN]]
    fig = go.Figure(go.Heatmap(z=[[codes[s] for s in row] for row in statuses], x=products, y=consumers, zmin=0, zmax=4,
                               colorscale=scale, showscale=False, xgap=1, ygap=1,
                               customdata=[[STATUS[s][0] for s in row] for row in statuses],
                               hovertemplate="%{y}<br>%{x}: %{customdata}<extra></extra>"))
    fig.update_xaxes(tickangle=-60, tickfont=dict(size=9))
    st.plotly_chart(styled(fig, 470))
    st.caption("Red unsafe, yellow caution ('may contain'), violet uncertain source, grey not confirmable "
               "(incomplete record), green confirmed safe.")


def tab_lab(kb, ctx):
    st.subheader("Reasoning lab")
    st.write("Pose a question and the backward chainer works from the goal down to the facts. If it fails, it shows "
             "which condition blocked each rule.")
    templates = {
        "Does a product contain an allergen?": ("containsAllergen", ["product", "allergen"]),
        "Does a product contradict one of its claims?": ("contradictsClaim", ["product", "claim"]),
        "Must a product declare an allergen in a market?": ("declarationDuty", ["product", "allergen", "market"]),
        "Is a product unsafe for a consumer?": ("unsafeFor", ["product", "consumer"]),
        "Can a product be confirmed safe for a consumer?": ("confirmedSafeFor", ["product", "consumer"]),
        "Is a product verified vegan?": ("VerifiedVeganProduct", ["product"]),
    }
    question = st.selectbox("Question", list(templates))
    pred, slots = templates[question]
    pools = {"product": sorted(kb.products, key=kb.label), "allergen": sorted(kb.allergens, key=kb.label),
             "claim": list(kb.claims), "market": list(kb.jurisdictions), "consumer": list(kb.consumers)}
    cols = st.columns(len(slots))
    args = []
    for col, slot in zip(cols, slots):
        with col:
            args.append(st.selectbox(slot.capitalize(), pools[slot], format_func=kb.label, key="lab_%s_%s" % (pred, slot)))
    goal = Atom(pred, tuple(args))
    proof = ctx.prover.prove(goal)
    if proof is not None:
        st.success("Yes. Here is the proof the backward chainer found.")
        explain(kb, proof)
        show_fig(viz.fig_proof_tree(kb, proof))
        with st.expander("Proof as text"):
            st.code(proof.render(), language="text")
    else:
        st.error("No. The reasoner cannot derive it. What blocked each rule:")
        st.code("\n".join(ctx.prover.why_not(goal)), language="text")
    st.markdown("#### Where the forward chainer spent its effort")
    show_fig(viz.fig_inference_profile(ctx.result))


def tab_questions():
    st.subheader("Competency questions")
    ans = answers()
    cq_id = st.selectbox("Question", list(ans), format_func=lambda k: "%s. %s" % (k, ans[k]["question"]))
    a = ans[cq_id]
    st.caption(a["kind"])
    if a.get("note"):
        st.info(a["note"])
    st.dataframe(pd.DataFrame(a["rows"], columns=a["columns"]), hide_index=True)
    if a.get("proof"):
        st.code(a["proof"], language="text")
    for product, reasons in (a.get("why_not") or {}).items():
        st.markdown("**Why is %s not confirmed safe?**" % product)
        st.code("\n".join(reasons), language="text")
    if a.get("sparql"):
        st.markdown("SPARQL, run against the Pellet-materialised ontology")
        st.code(a["sparql"], language="sql")


def tab_limits():
    st.subheader("Edge cases and scale")
    ec = cases()
    show_fig(viz.fig_world_assumptions(ec))
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("**False assurances a naive closed-world system would give**")
        st.dataframe(pd.DataFrame(ec["EC1"]["false_assurances"]), hide_index=True)
    with c2:
        st.markdown("**Keyword traps**")
        st.dataframe(pd.DataFrame(ec["EC8"]["false_positive_examples"]), hide_index=True)
    st.markdown("**Where monotonic SWRL and the defeasible engine disagree**")
    st.dataframe(pd.DataFrame(ec["EC6"]["rows"]), hide_index=True)
    st.markdown("**Exactly 10 mg/kg of sulphites**")
    st.dataframe(pd.DataFrame(ec["EC7"]["rows"]), hide_index=True)
    bench = read_output("benchmark.json")
    if bench:
        show_fig(viz.fig_scalability(bench))
    owl = read_output("owl_results.json")
    if owl and owl.get("status") == "ok":
        cols = st.columns(3)
        cols[0].metric("Pellet", _duration(owl["pellet"]["seconds"]), owl["pellet"]["status"])
        if "hermit" in owl:
            cols[1].metric("HermiT", _duration(owl["hermit"]["seconds"]), owl["hermit"]["status"])
        who = (owl.get("materializer") or "pellet").capitalize().replace("Hermit", "HermiT")
        cols[2].metric("Facts inferred by %s" % who, format(owl.get("facts_inferred", owl.get("facts_inferred_by_pellet")) or 0, ","))
        if owl.get("crossval"):
            st.markdown("**%s vs FALCON engine**" % who)
            cv = pd.DataFrame(owl["crossval"])
            st.dataframe(cv[["predicate", "engine", "owl" if "owl" in cv else "pellet", "agree", "jaccard"]], hide_index=True)
    else:
        st.info("Pellet and HermiT results appear here once `python run_all.py` (or the GitHub Actions run) has written "
                "outputs/owl_results.json.")


def tab_about(kb, ctx):
    st.subheader("How it works")
    show_fig(viz.fig_architecture())
    show_fig(viz.fig_conceptual_model(kb))
    st.markdown("""
- **One schema, two reasoners.** The same class and property definitions build the OWL ontology (checked by HermiT and
  Pellet) and the rule base of a Datalog-style engine; the two are cross-validated.
- **Open world where it is safe, closed world where it is justified.** OWL never treats missing data as proof. The engine
  applies negation as failure only to records marked complete.
- **Provenance first.** Every conclusion can be traced to the facts and rules behind it, forwards or backwards.
- **Market-specific law.** Pine nut, mustard, celery, lupin, molluscs and sulphite thresholds differ between the US,
  Canada and the EU; the rules follow each market's own list.
""")
    rules = [{"id": r.rule_id, "name": r.name, "kind": r.source, "rule": r.to_fol()} for r in ctx.rules
             if r.source in ("swrl", "engine", "integrity")]
    st.markdown("**Rule catalogue**")
    st.dataframe(pd.DataFrame(rules), hide_index=True)


# ---------------------------------------------------------------------------

kb, rules, ctx = engine()
hero(kb, ctx)
st.write("")
tabs = st.tabs(["Check a label", "Myth or fact?", "Product graph", "Compliance atlas", "Reasoning lab",
                "Competency questions", "Edge cases and scale", "How it works"])
with tabs[0]:
    tab_check_label(kb)
with tabs[1]:
    tab_myths(ctx)
with tabs[2]:
    tab_graph(kb, ctx)
with tabs[3]:
    tab_atlas(kb, ctx)
with tabs[4]:
    tab_lab(kb, ctx)
with tabs[5]:
    tab_questions()
with tabs[6]:
    tab_limits()
with tabs[7]:
    tab_about(kb, ctx)
st.caption("FALCON reasons over a curated knowledge base of 45 products. It demonstrates a method; it is not a substitute "
           "for reading the actual label or for professional advice.")
