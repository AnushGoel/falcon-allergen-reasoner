"""
FALCON · Label compliance intelligence.

One control panel in the sidebar (markets, shopper, categories, issue type, product in focus) drives every
view. All verdicts are derived live by the FALCON rule engine, which is pure Python, so the app needs no Java.
The Pellet and HermiT figures on the Validation tab come from the saved full run in outputs/.

Run locally:  streamlit run streamlit_app.py
"""
from __future__ import annotations

import html
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from falcon import app_logic as logic  # noqa: E402
from falcon import competency, edge_cases, viz  # noqa: E402
from falcon.competency import MARKETS  # noqa: E402
from falcon.config import OUTPUT_DIR  # noqa: E402
from falcon.rule_engine import Atom  # noqa: E402

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

INK, BODY, MUTED, LINE, SURFACE = "#0F172A", "#334155", "#64748B", "#E2E8F0", "#F8FAFC"
ACCENT, TEAL = "#6C4BD8", "#0E7490"
GOOD, BAD, WARN, INFO, NEUTRAL, ROSE = "#15803D", "#DC2626", "#D97706", "#7C3AED", "#94A3B8", "#BE123C"
CLAIM_STATUS = {"VERIFIED": ("Verified", GOOD), "CONTRADICTED": ("Contradicted", BAD), "AT RISK": ("At risk", WARN),
                "UNVERIFIABLE": ("Unverifiable", INFO), "INFORMATIONAL": ("Informational", NEUTRAL)}
VERDICTS = [("Safe", GOOD), ("Not confirmed", NEUTRAL), ("Uncertain", INFO), ("Caution", WARN),
            ("Unsuitable for diet", ROSE), ("Unsafe", BAD)]
VERDICT_COLOR = dict(VERDICTS)
MARKET_IDS = [m for m, _ in MARKETS]
SHORT = dict(MARKETS)
MARKET_COLOR = {"jur_us": "#2563EB", "jur_canada": "#DC2626", "jur_eu": "#0E7490"}
ISSUES = ["All products", "Any issue", "Contradicted claims", "Undeclared allergens", "Hidden allergens",
          "Markets disagree", "Not safe for the selected shopper"]
SAMPLES = {
    "Steakhouse sauce": ("Tomato, spirit vinegar, sugar, Worcestershire sauce, onion, salt, paprika", ["claim_vegan"]),
    "Coffee whitener": ("Corn syrup solids, coconut oil, sodium caseinate, dipotassium phosphate (E340), "
                        "mono- and diglycerides (E471), natural flavouring", ["claim_non_dairy"]),
    "Pesto": ("Basil, sunflower oil, parmesan cheese, cashew nuts, pine nuts, garlic, salt", ["claim_vegetarian"]),
    "Write your own": ("", []),
}

st.set_page_config(page_title="FALCON · Label compliance intelligence", page_icon="\U0001F6E1\ufe0f", layout="wide",
                   initial_sidebar_state="expanded")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .stApp, .stMarkdown, p, li, label, input, textarea, button, h1, h2, h3, h4, h5 {
font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; }
.stApp { background: #F8FAFC; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1340px; }
#MainMenu, footer { visibility: hidden; }
[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E2E8F0; }
h1, h2, h3, h4 { color: #0F172A; letter-spacing: -0.015em; }
.fx-brand { display: flex; align-items: center; gap: .6rem; margin: .2rem 0 1rem; }
.fx-logo { width: 2.1rem; height: 2.1rem; border-radius: .6rem; background: linear-gradient(135deg, #6C4BD8, #0E7490);
color: #FFFFFF; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.05rem; }
.fx-brand b { font-size: 1.05rem; color: #0F172A; } .fx-brand span { display: block; font-size: .72rem; color: #64748B; }
.fx-side-note { font-size: .76rem; color: #64748B; line-height: 1.5; border-top: 1px solid #E2E8F0; padding-top: .8rem; margin-top: 1rem; }
.fx-eyebrow { font-size: .74rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: #6C4BD8; }
.fx-title { font-size: 1.95rem; font-weight: 800; color: #0F172A; margin: .15rem 0 .25rem; letter-spacing: -0.02em; }
.fx-sub { color: #475569; font-size: .97rem; max-width: 54rem; line-height: 1.55; }
.fx-scope { display: flex; flex-wrap: wrap; gap: .4rem; margin: .8rem 0 1.1rem; }
.fx-chip { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 999px; padding: .22rem .7rem; font-size: .8rem; color: #475569; }
.fx-chip b { color: #0F172A; font-weight: 600; }
.fx-kpis { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: .8rem; margin: .2rem 0 1.3rem; }
@media (max-width: 1100px) { .fx-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.fx-kpi { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: .9rem 1rem .85rem;
box-shadow: 0 1px 2px rgba(15, 23, 42, .04); }
.fx-kpi .k { font-size: .7rem; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; color: #64748B; }
.fx-kpi .v { font-size: 1.8rem; font-weight: 800; color: #0F172A; line-height: 1.15; margin-top: .3rem; font-variant-numeric: tabular-nums; }
.fx-kpi .d { font-size: .78rem; color: #64748B; margin-top: .15rem; }
.fx-kpi.bad .v { color: #DC2626; } .fx-kpi.warn .v { color: #D97706; } .fx-kpi.info .v { color: #6C4BD8; } .fx-kpi.good .v { color: #15803D; }
.fx-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1rem 1.1rem .7rem; margin-bottom: .8rem; }
.fx-card h4 { margin: 0 0 .5rem; font-size: .8rem; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; color: #64748B; }
.fx-pill { display: inline-block; border-radius: 999px; padding: .1rem .55rem; font-size: .74rem; font-weight: 600; white-space: nowrap; }
.fx-list { margin: 0; padding: 0; list-style: none; }
.fx-list li { padding: .45rem 0; border-bottom: 1px solid #F1F5F9; font-size: .88rem; color: #334155; }
.fx-list li:last-child { border-bottom: none; }
.fx-row { display: flex; justify-content: space-between; align-items: center; gap: .6rem; }
.fx-why { color: #64748B; font-size: .79rem; margin-top: .1rem; }
.fx-bad { color: #DC2626; font-weight: 600; } .fx-warn { color: #B45309; font-weight: 600; }
.fx-label { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 14px; padding: 1.1rem 1.25rem; }
.fx-label .name { font-weight: 800; font-size: 1.2rem; color: #0F172A; }
.fx-label .meta { color: #64748B; font-size: .8rem; margin: .1rem 0 .7rem; }
.fx-label .stamps { margin-bottom: .7rem; }
.fx-stamp { display: inline-block; border: 1.5px solid #0F172A; border-radius: 6px; padding: .05rem .45rem; margin: 0 .3rem .3rem 0;
font-size: .7rem; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; color: #0F172A; }
.fx-label .h { font-size: .7rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; color: #334155; margin-bottom: .2rem; }
.fx-label .ing { font-size: .95rem; line-height: 1.75; color: #1E293B; }
.fx-label .hl { background: rgba(108, 75, 216, .12); border-bottom: 2px solid #6C4BD8; border-radius: 3px; padding: 0 .15rem; }
.fx-label .hl small { color: #6C4BD8; font-weight: 700; margin-left: .25rem; }
.fx-label .row { border-top: 1px solid #E2E8F0; margin-top: .7rem; padding-top: .55rem; font-size: .86rem; color: #334155; }
.fx-callout { background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid #DC2626; border-radius: 12px; padding: .75rem .9rem; height: 100%; }
.fx-callout b { color: #0F172A; } .fx-callout div { color: #475569; font-size: .84rem; margin-top: .25rem; line-height: 1.45; }
.fx-section { font-size: .76rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: #64748B; margin: 1.3rem 0 .5rem; }
.fx-legend { display: flex; flex-wrap: wrap; gap: .9rem; font-size: .78rem; color: #475569; margin: .2rem 0 .6rem; }
.fx-legend i { display: inline-block; width: .7rem; height: .7rem; border-radius: 3px; margin-right: .3rem; vertical-align: -1px; }
.fx-chips span { display: inline-block; border: 1px solid #E2E8F0; border-radius: 999px; padding: .12rem .55rem; margin: .12rem .2rem .12rem 0;
font-size: .82rem; background: #FFFFFF; }
.fx-chips span.unknown { border-style: dashed; color: #64748B; }
.stTabs [data-baseweb="tab-list"] { gap: .2rem; border-bottom: 1px solid #E2E8F0; }
.stTabs [data-baseweb="tab"] { height: 2.7rem; padding: 0 .95rem; font-weight: 600; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Small rendering helpers
# ---------------------------------------------------------------------------

def esc(text) -> str:
    return html.escape(str(text))


def show_html(markup: str) -> None:
    """Render HTML without letting Markdown turn indented lines into code blocks."""
    st.markdown("".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


def tint(hex_color: str, alpha: float = 0.12) -> str:
    h = hex_color.lstrip("#")
    return "rgba(%d,%d,%d,%.2f)" % (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def pill(text: str, color: str) -> str:
    return '<span class="fx-pill" style="color:%s;background:%s">%s</span>' % (color, tint(color), esc(text))


def section(title: str) -> None:
    show_html('<div class="fx-section">%s</div>' % esc(title))


def plot(fig, height: int = 360, legend: bool = True) -> None:
    fig.update_layout(height=height, margin=dict(l=8, r=8, t=30 if legend else 10, b=8),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, system-ui, sans-serif", size=12, color=BODY), showlegend=legend,
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
                      hoverlabel=dict(bgcolor="#FFFFFF", font_size=12, font_family="Inter, sans-serif"))
    fig.update_xaxes(gridcolor="#EEF2F7", zeroline=False, linecolor=LINE)
    fig.update_yaxes(gridcolor="#EEF2F7", zeroline=False, linecolor=LINE)
    st.plotly_chart(fig, theme=None)


def show_figure(fig) -> None:
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


def legend(items) -> None:
    show_html('<div class="fx-legend">%s</div>' % "".join('<span><i style="background:%s"></i>%s</span>' % (c, esc(n)) for n, c in items))


def duration(seconds: float) -> str:
    return "%.1f min" % (seconds / 60) if seconds >= 120 else "%.2f s" % seconds


# ---------------------------------------------------------------------------
# Data: computed once, then filtered on every interaction
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Loading the knowledge base and running the reasoner...")
def engine():
    return logic.load_engine()                     # (knowledge base, rules, engine context)


@st.cache_resource(show_spinner=False)
def summaries():
    kb, _, ctx = engine()
    return {pid: logic.summarise(ctx, pid) for pid in kb.products}


@st.cache_resource(show_spinner=False)
def lexicon():
    return logic.build_lexicon(engine()[0])


@st.cache_resource(show_spinner=False, max_entries=64)
def analysis(name, ingredients, claims, markets, may_contain, declared, complete):
    kb, rules, _ = engine()
    return logic.analyse_label(kb, rules, name, list(ingredients), list(claims), list(markets), list(may_contain),
                               list(declared), complete)


@st.cache_resource(show_spinner=False)
def answers():
    return competency.answer_all(engine()[2])


@st.cache_resource(show_spinner=False)
def cases():
    return edge_cases.run_all(engine()[2])


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except Exception:
        return None


def verdict_of(entry: dict) -> str:
    if entry["status"] == "UNSAFE":
        return "Unsafe"
    if entry["diet"] == "unsuitable":
        return "Unsuitable for diet"
    if entry["status"] == "CAUTION":
        return "Caution"
    if entry["status"] == "UNCERTAIN" or entry["diet"] == "uncertain":
        return "Uncertain"
    return "Safe" if entry["status"] == "SAFE" else "Not confirmed"


def disagreements(kb, res, pid, markets) -> list:
    """Allergens whose declaration duty differs between the selected markets that sell the product."""
    sold = [m for m in kb.products[pid]["sold_in"] if m in markets]
    if len(sold) < 2:
        return []
    out = set()
    for (_, a) in res.query("containsAllergen", pid, None):
        duty = {j for (_, _, j) in res.query("declarationDuty", pid, a, None)}
        if 0 < sum(1 for m in sold if m in duty) < len(sold):
            out.add(kb.label(a))
    return sorted(out)


def record(kb, ctx, pid, summary, markets, shopper) -> dict:
    res = ctx.result
    contradicted = [c["claim"] for c in summary["claims"] if c["status"] == "CONTRADICTED"]
    at_risk = [c["claim"] for c in summary["claims"] if c["status"] == "AT RISK"]
    undeclared = sorted({(kb.label(a), j) for (_, a, j) in res.query("undeclaredAllergen", pid, None, None) if j in markets})
    hidden = sorted({e["allergen"] for e in summary["allergens"] if e["hidden"]})
    entry = next((c for c in summary["consumers"] if c["consumer"] == shopper), None) if shopper else None
    return {"pid": pid, "contradicted": contradicted, "at_risk": at_risk, "undeclared": undeclared, "hidden": hidden,
            "disagree": disagreements(kb, res, pid, markets), "verdict": verdict_of(entry) if entry else None,
            "score": 3 * len(contradicted) + 2 * len(undeclared) + len(hidden) + len(at_risk)}


def matches(kb, rec, filters) -> bool:
    p = kb.products[rec["pid"]]
    if filters["categories"] and kb.label(p["category"]) not in filters["categories"]:
        return False
    if not any(m in p["sold_in"] for m in filters["markets"]):
        return False
    issue = filters["issue"]
    if issue == "Any issue":
        return rec["score"] > 0
    if issue == "Contradicted claims":
        return bool(rec["contradicted"])
    if issue == "Undeclared allergens":
        return bool(rec["undeclared"])
    if issue == "Hidden allergens":
        return bool(rec["hidden"])
    if issue == "Markets disagree":
        return bool(rec["disagree"])
    if issue == "Not safe for the selected shopper":
        return rec["verdict"] is not None and rec["verdict"] != "Safe"
    return True


def undeclared_text(rec) -> str:
    by_allergen = {}
    for allergen, market in rec["undeclared"]:
        by_allergen.setdefault(allergen, []).append(SHORT[market])
    return "; ".join("%s (%s)" % (a, ", ".join(ms)) for a, ms in sorted(by_allergen.items()))


# ---------------------------------------------------------------------------
# Shared views: label card, verdict cards, allergen trace
# ---------------------------------------------------------------------------

def label_card(kb, product, summary, xray: bool) -> None:
    hidden = {}
    for entry in summary["allergens"]:
        for h in entry["hidden"]:
            hidden.setdefault(h["ingredient"], set()).add(entry["allergen"])
    parts = []
    for iid in product["ingredients"]:
        name = kb.ingredients[iid]["label"]
        if xray and name in hidden:
            parts.append('<span class="hl">%s<small>&rarr; %s</small></span>' % (esc(name), esc(", ".join(sorted(hidden[name])))))
        else:
            parts.append(esc(name))
    meta = []
    if product.get("category"):
        meta.append(esc(kb.label(product["category"])))
    meta.append("Sold in " + esc(", ".join(SHORT[m] for m in MARKET_IDS if m in product["sold_in"])))
    if product.get("status") != "complete":
        meta.append('<span class="fx-warn">ingredient record incomplete</span>')
    stamps = "".join('<span class="fx-stamp">%s</span>' % esc(kb.label(c)) for c in product["claims"])
    rows = ""
    if product.get("declared"):
        rows += '<div class="row"><b>Contains:</b> %s</div>' % esc(", ".join(kb.label(a) for a in product["declared"]))
    if product.get("may_contain"):
        rows += '<div class="row"><b>May contain:</b> %s</div>' % esc(", ".join(kb.label(a) for a in product["may_contain"]))
    show_html('<div class="fx-label"><div class="name">%s</div><div class="meta">%s</div><div class="stamps">%s</div>'
              '<div class="h">Ingredients</div><div class="ing">%s</div>%s</div>'
              % (esc(product["label"]), " &middot; ".join(meta), stamps, ", ".join(parts) or "<i>none recognised</i>", rows))


def claims_card(summary) -> None:
    if not summary["claims"]:
        items = '<li class="fx-why">No claims on this label.</li>'
    else:
        items = "".join('<li><div class="fx-row"><b>%s</b>%s</div><div class="fx-why">%s</div></li>'
                        % (esc(c["claim"]), pill(*CLAIM_STATUS.get(c["status"], (c["status"], NEUTRAL))), esc(c["why"]))
                        for c in summary["claims"])
    show_html('<div class="fx-card"><h4>Claims on the pack</h4><ul class="fx-list">%s</ul></div>' % items)


def markets_card(kb, product, summary, markets) -> None:
    by_label = {m["market"]: m for m in summary["markets"]}
    items = []
    for mid in markets:
        entry = by_label.get(kb.label(mid))
        if mid not in product["sold_in"] or entry is None:
            items.append('<li><div class="fx-row"><b>%s</b>%s</div></li>' % (esc(SHORT[mid]), pill("Not sold here", NEUTRAL)))
            continue
        status = pill("Undeclared allergen", BAD) if entry["undeclared"] else pill("Compliant", GOOD)
        lines = '<div class="fx-why">Must declare: %s</div>' % esc(entry["must declare"])
        if entry["undeclared"]:
            lines += '<div class="fx-why"><span class="fx-bad">Not declared: %s</span></div>' % esc(entry["undeclared"])
        if entry["check with supplier"]:
            lines += '<div class="fx-why"><span class="fx-warn">Check with supplier: %s</span></div>' % esc(entry["check with supplier"])
        items.append('<li><div class="fx-row"><b>%s</b>%s</div>%s</li>' % (esc(SHORT[mid]), status, lines))
    show_html('<div class="fx-card"><h4>Market compliance</h4><ul class="fx-list">%s</ul></div>' % "".join(items))


def shoppers_card(summary, shopper) -> None:
    entries = [c for c in summary["consumers"] if not shopper or c["consumer"] == shopper]
    items = "".join('<li><div class="fx-row"><span>%s</span>%s</div></li>'
                    % (esc(c["consumer"]), pill(verdict_of(c), VERDICT_COLOR[verdict_of(c)])) for c in entries)
    show_html('<div class="fx-card"><h4>%s</h4><ul class="fx-list">%s</ul></div>'
              % ("Verdict for the selected shopper" if shopper else "Verdict for each shopper", items))


def allergen_table(summary) -> None:
    rows = [{"Allergen": e["allergen"], "Type": "group" if e["kind"] == "category" else "specific",
             "Found through": ", ".join(e["via"]), "Hidden route": "; ".join(h["chain"] for h in e["hidden"])}
            for e in summary["allergens"]]
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True)
    else:
        st.caption("No allergens found.")


def verdict_panel(kb, product, summary, markets, shopper) -> None:
    left, right = st.columns(2)
    with left:
        claims_card(summary)
        shoppers_card(summary, shopper)
    with right:
        markets_card(kb, product, summary, markets)


# ---------------------------------------------------------------------------
# Sidebar: the one control panel
# ---------------------------------------------------------------------------

kb, rules, ctx = engine()
res = ctx.result
SUMMARIES = summaries()
consumer_labels = [kb.label(u) for u in kb.consumers]
category_labels = sorted({kb.label(p["category"]) for p in kb.products.values() if p.get("category")})


def reset_filters() -> None:
    for key in ("f_markets", "f_shopper", "f_categories", "f_issue", "focus_pid"):
        st.session_state.pop(key, None)


with st.sidebar:
    show_html('<div class="fx-brand"><div class="fx-logo">F</div><div><b>FALCON</b>'
              '<span>Food allergen and label compliance</span></div></div>')
    options = [SHORT[m] for m in MARKET_IDS]
    if hasattr(st, "pills"):
        picked = st.pills("Markets", options, selection_mode="multi", default=options, key="f_markets",
                          help="Which markets' labelling law to apply.")
    else:
        picked = st.multiselect("Markets", options, default=options, key="f_markets")
    picked = list(picked or [])
    if not picked:
        st.caption("No market selected, so all three are used.")
        picked = options
    markets = [m for m in MARKET_IDS if SHORT[m] in picked]
    shopper_choice = st.selectbox("Shopper profile", ["Everyone"] + consumer_labels, key="f_shopper",
                                  help="Show verdicts for one person's allergies and diet.")
    shopper = None if shopper_choice == "Everyone" else shopper_choice
    categories = st.multiselect("Product categories", category_labels, key="f_categories", placeholder="All categories")
    issue = st.selectbox("Show products with", ISSUES, key="f_issue")
    filters = {"markets": markets, "categories": categories, "issue": issue}

    records = {pid: record(kb, ctx, pid, SUMMARIES[pid], markets, shopper) for pid in kb.products}
    scope = sorted((pid for pid, r in records.items() if matches(kb, r, filters)),
                   key=lambda pid: (-records[pid]["score"], kb.label(pid)))
    focus = None
    if scope:
        previous = st.session_state.get("focus_pid")
        focus = st.selectbox("Product in focus", scope, index=scope.index(previous) if previous in scope else 0,
                             format_func=kb.label, help="Ranked by risk score. Used by the explorer and the reasoning lab.")
        st.session_state["focus_pid"] = focus
    st.button("Reset filters", on_click=reset_filters)
    show_html('<div class="fx-side-note">Knowledge base: %d products, %d ingredients, %d allergens, 3 markets, %d rules. '
              'Every verdict is derived live by the FALCON rule engine and can be explained step by step.</div>'
              % (len(kb.products), len(kb.ingredients), len(kb.allergens), len(rules)))


# ---------------------------------------------------------------------------
# Header and KPIs
# ---------------------------------------------------------------------------

in_scope = [records[pid] for pid in scope]
claims_in_scope = [c for pid in scope for c in SUMMARIES[pid]["claims"]]
contradicted = sum(len(r["contradicted"]) for r in in_scope)
at_risk = sum(len(r["at_risk"]) for r in in_scope)
undeclared = sum(len(r["undeclared"]) for r in in_scope)
undeclared_products = sum(1 for r in in_scope if r["undeclared"])
hidden = sum(len(r["hidden"]) for r in in_scope)
disagree = sum(len(r["disagree"]) for r in in_scope)
KPI = {"products": len(scope), "contradicted": contradicted, "claims": len(claims_in_scope), "undeclared": undeclared,
       "undeclared_products": undeclared_products, "hidden": hidden, "disagreements": disagree}

show_html('<div class="fx-eyebrow">FALCON &middot; Food Allergen and Label Compliance Ontology</div>'
          '<div class="fx-title">Label compliance intelligence</div>'
          '<div class="fx-sub">An OWL 2 DL ontology and a rule engine read each label the way a regulator would: they follow every '
          'ingredient to its source, test every claim against the recipe, and apply each market\'s allergen law. '
          'Every verdict below comes with a proof.</div>')
chips = ['<span class="fx-chip">Markets: <b>%s</b></span>' % esc(", ".join(SHORT[m] for m in markets)),
         '<span class="fx-chip">Shopper: <b>%s</b></span>' % esc(shopper or "Everyone"),
         '<span class="fx-chip">Categories: <b>%s</b></span>' % esc(", ".join(categories) if categories else "All"),
         '<span class="fx-chip">Showing: <b>%s</b></span>' % esc(issue),
         '<span class="fx-chip"><b>%d</b> of %d products</span>' % (len(scope), len(kb.products))]
show_html('<div class="fx-scope">%s</div>' % "".join(chips))

if shopper:
    not_safe = sum(1 for r in in_scope if r["verdict"] != "Safe")
    fifth = ("bad" if not_safe else "good", "Not safe for %s" % shopper.split(" ")[0], not_safe,
             "%d confirmed safe" % (len(scope) - not_safe))
else:
    fifth = ("info", "Market disagreements", disagree, "allergens the selected markets treat differently")
cards = [("", "Products in scope", len(scope), "of %d in the knowledge base" % len(kb.products)),
         ("bad", "Claims contradicted", contradicted, "of %d claims; %d more at risk" % (len(claims_in_scope), at_risk)),
         ("bad", "Undeclared allergens", undeclared, "in %d products, selected markets" % undeclared_products),
         ("warn", "Hidden allergens", hidden, "inside other ingredients"), fifth]
show_html('<div class="fx-kpis">%s</div>' % "".join('<div class="fx-kpi %s"><div class="k">%s</div><div class="v">%s</div>'
                                                    '<div class="d">%s</div></div>' % (cls, esc(k), v, esc(d))
                                                    for cls, k, v, d in cards))

tabs = st.tabs(["Overview", "Product explorer", "Label checker", "Markets", "Shoppers", "Reasoning lab", "Validation & method"])


# ---------------------------------------------------------------------------
# 1. Overview
# ---------------------------------------------------------------------------

with tabs[0]:
    if not scope:
        st.info("No products match these filters. Widen the filters in the sidebar, or choose Reset filters.")
    else:
        top = [r for r in in_scope if r["score"] > 0][:3]
        if top:
            section("Highest-risk products")
            cols = st.columns(len(top))
            for col, r in zip(cols, top):
                reasons = []
                if r["contradicted"]:
                    reasons.append("claim contradicted: " + ", ".join(r["contradicted"]))
                if r["undeclared"]:
                    reasons.append("not declared: " + undeclared_text(r))
                if r["hidden"]:
                    reasons.append("hidden: " + ", ".join(r["hidden"]))
                if r["at_risk"]:
                    reasons.append("claim at risk: " + ", ".join(r["at_risk"]))
                with col:
                    show_html('<div class="fx-callout"><b>%s</b><div>%s</div></div>'
                              % (esc(kb.label(r["pid"])), esc("; ".join(reasons).capitalize())))
        left, right = st.columns([7, 5])
        with left:
            section("Claim audit")
            counts = Counter((c["claim"], c["status"]) for c in claims_in_scope)
            claim_names = sorted({c for c, _ in counts}, key=lambda c: sum(v for (n, _), v in counts.items() if n == c))
            fig = go.Figure()
            for status, (name, color) in CLAIM_STATUS.items():
                fig.add_trace(go.Bar(y=claim_names, x=[counts.get((c, status), 0) for c in claim_names], name=name,
                                     orientation="h", marker_color=color,
                                     hovertemplate="%{y}: %{x} " + name.lower() + "<extra></extra>"))
            fig.update_layout(barmode="stack")
            fig.update_xaxes(title_text="claims", dtick=1 if len(claims_in_scope) < 12 else None)
            plot(fig, height=max(240, 40 * len(claim_names) + 80))
        with right:
            section("Undeclared allergens by market")
            cells = Counter((allergen, market) for r in in_scope for allergen, market in r["undeclared"])
            if cells:
                allergens = sorted({a for a, _ in cells})
                z = [[cells.get((a, m), 0) for m in markets] for a in allergens]
                fig = go.Figure(go.Heatmap(z=z, x=[SHORT[m] for m in markets], y=allergens, text=z, texttemplate="%{text}",
                                           colorscale=[[0, "#F8FAFC"], [1, BAD]], showscale=False, xgap=3, ygap=3,
                                           hovertemplate="%{y} undeclared in %{x}: %{z} product(s)<extra></extra>"))
                fig.update_yaxes(autorange="reversed")
                plot(fig, height=max(220, 36 * len(allergens) + 70), legend=False)
            else:
                st.success("No undeclared allergens among these products in the selected markets.")
        section("Risk register")
        table = []
        for r in in_scope:
            p = kb.products[r["pid"]]
            row = {"Product": kb.label(r["pid"]), "Category": kb.label(p["category"]) if p.get("category") else "",
                   "Markets": ", ".join(SHORT[m] for m in MARKET_IDS if m in p["sold_in"]), "Risk": r["score"],
                   "Contradicted claims": ", ".join(r["contradicted"]), "Undeclared": undeclared_text(r),
                   "Hidden allergens": ", ".join(r["hidden"]), "Claims at risk": ", ".join(r["at_risk"]),
                   "Markets disagree on": ", ".join(r["disagree"])}
            if shopper:
                row["Verdict for %s" % shopper.split(" ")[0]] = r["verdict"]
            row["Record"] = p.get("status", "")
            table.append(row)
        frame = pd.DataFrame(table)
        st.dataframe(frame, hide_index=True, column_config={
            "Risk": st.column_config.ProgressColumn("Risk score", min_value=0, max_value=max(1, max(r["score"] for r in in_scope)),
                                                    format="%d", help="3 per contradicted claim, 2 per undeclared allergen, "
                                                                      "1 per hidden allergen or claim at risk")})
        st.download_button("Download the risk register (CSV)", frame.to_csv(index=False).encode("utf-8"),
                           "falcon_risk_register.csv", "text/csv")
        st.caption("The 45 products form a curated test portfolio: each one exists to test a specific question, so these counts "
                   "show what the method detects, not how often problems occur in shops.")


# ---------------------------------------------------------------------------
# 2. Product explorer
# ---------------------------------------------------------------------------

with tabs[1]:
    if not focus:
        st.info("No product in focus. Widen the filters in the sidebar.")
    else:
        product, summary = kb.products[focus], SUMMARIES[focus]
        left, right = st.columns([5, 7])
        with left:
            xray = st.toggle("X-ray the label: show allergens hidden inside ingredients", value=True)
            label_card(kb, product, summary, xray)
            if product.get("scenario"):
                st.caption("Why this product is in the portfolio: " + product["scenario"])
        with right:
            verdict_panel(kb, product, summary, markets, shopper)
        section("Where each allergen comes from")
        allergen_table(summary)
        with st.expander("Knowledge graph of this product"):
            show_figure(viz.fig_product_graph(kb, ctx, focus))


# ---------------------------------------------------------------------------
# 3. Label checker
# ---------------------------------------------------------------------------

with tabs[2]:
    st.markdown("Paste any ingredient list. The reasoner analyses it live for the markets and shopper chosen in the sidebar.")
    left, right = st.columns([5, 7])
    with left:
        sample = st.selectbox("Start from an example", list(SAMPLES), key="sample")
        default_text, default_claims = SAMPLES[sample]
        name = st.text_input("Product name", value="" if sample == "Write your own" else sample, key="lc_name_" + sample)
        text = st.text_area("Ingredients, exactly as printed", value=default_text, height=150, key="lc_text_" + sample,
                            help="'Contains:' and 'May contain:' statements are recognised too.")
        claim_ids = list(kb.claims)
        claims = st.multiselect("Claims printed on the pack", claim_ids, default=default_claims, format_func=kb.label,
                                key="lc_claims_" + sample)
        complete = st.toggle("This is the complete ingredient list", value=True, key="lc_complete")
    with right:
        if not text.strip():
            st.info("Paste an ingredient list to analyse it.")
        else:
            parsed = logic.parse_label(kb, text, lexicon())
            actx = analysis(name or "Your label", tuple(parsed["ingredients"]), tuple(claims), tuple(markets),
                            tuple(parsed["may_contain"]), tuple(parsed["declared"]), complete)
            asummary = logic.summarise(actx, logic.CUSTOM_ID)
            product = actx.kb.products[logic.CUSTOM_ID]
            chips_html = "".join("<span>%s</span>" % esc(kb.ingredients[i]["label"]) for i in parsed["ingredients"])
            chips_html += "".join('<span class="unknown">%s ?</span>' % esc(t) for t in parsed["unknown"])
            show_html('<div class="fx-card"><h4>Recognised ingredients</h4><div class="fx-chips">%s</div>%s</div>'
                      % (chips_html, '<div class="fx-why">Dashed items are not in the knowledge base, so the record is treated '
                                     'as incomplete for closed-world verdicts.</div>' if parsed["unknown"] else ""))
            label_card(actx.kb, product, asummary, True)
            st.write("")
            verdict_panel(actx.kb, product, asummary, markets, shopper)
            with st.expander("Where each allergen comes from"):
                allergen_table(asummary)


# ---------------------------------------------------------------------------
# 4. Markets
# ---------------------------------------------------------------------------

with tabs[3]:
    labels, market_labels, matrix = logic.market_matrix(kb)
    cols = [k for k, m in enumerate(kb.jurisdictions) if m in markets]
    rows = []
    for allergen, values in zip(labels, matrix):
        picked_values = [values[k] for k in cols]
        rows.append((allergen, picked_values, len(set(picked_values)) > 1))
    rows.sort(key=lambda r: (not r[2], r[0]))
    left, right = st.columns([5, 7])
    with left:
        section("Which allergens each market requires on the label")
        fig = go.Figure(go.Heatmap(
            z=[r[1] for r in rows], x=[SHORT[m] for m in kb.jurisdictions if m in markets],
            y=[("\u2260 " if r[2] else "") + r[0] for r in rows], text=[["declare" if v else "" for v in r[1]] for r in rows],
            texttemplate="%{text}", colorscale=[[0, "#F1F5F9"], [1, ACCENT]], zmin=0, zmax=1, showscale=False, xgap=3, ygap=2,
            hovertemplate="%{y} in %{x}: %{text}<extra></extra>"))
        fig.update_yaxes(autorange="reversed")
        plot(fig, height=max(360, 22 * len(rows) + 60), legend=False)
        st.caption("\u2260 marks allergens on which the selected markets disagree.")
    with right:
        section("From ingredient to allergen to market")
        links = Counter()
        for pid in scope:
            for (_, a, i) in res.query("containsVia", pid, None, None):
                if kb.allergens[a]["kind"] == "category" and a != "alg_gluten":
                    links[(("ingredient", kb.ingredients[i]["label"]), ("allergen", kb.label(a)))] += 1
            for (_, a, j) in res.query("declarationDuty", pid, None, None):
                if j in markets:
                    group = a if kb.allergens[a]["kind"] == "category" else kb.allergens[a]["parent"]
                    links[(("allergen", kb.label(group)), ("market", SHORT[j]))] += 1
        if links:
            order = {"ingredient": 0, "allergen": 1, "market": 2}
            nodes = sorted({n for pair in links for n in pair}, key=lambda n: (order[n[0]], n[1]))
            index = {n: k for k, n in enumerate(nodes)}
            node_color = {"ingredient": "#94A3B8", "allergen": BAD, "market": ACCENT}
            fig = go.Figure(go.Sankey(
                arrangement="snap",
                node=dict(label=[n[1] for n in nodes], color=[node_color[n[0]] for n in nodes], pad=10, thickness=12,
                          line=dict(width=0)),
                link=dict(source=[index[a] for a, _ in links], target=[index[b] for _, b in links], value=list(links.values()),
                          color=[tint(node_color[b[0]], 0.25) for _, b in links])))
            plot(fig, height=max(420, 9 * len(nodes)), legend=False)
        else:
            st.caption("No allergens among the products in scope.")
        section("Where the selected markets disagree")
        diff_rows = []
        for r in in_scope:
            for allergen in r["disagree"]:
                aid = next(a for a in kb.allergens if kb.label(a) == allergen)
                duty = {SHORT[j] for (_, _, j) in res.query("declarationDuty", r["pid"], aid, None) if j in markets}
                sold = [SHORT[m] for m in markets if m in kb.products[r["pid"]]["sold_in"]]
                diff_rows.append({"Product": kb.label(r["pid"]), "Allergen": allergen,
                                  "Must declare in": ", ".join(m for m in sold if m in duty),
                                  "No duty in": ", ".join(m for m in sold if m not in duty)})
        if diff_rows:
            st.dataframe(pd.DataFrame(diff_rows), hide_index=True)
        else:
            st.caption("No disagreements: choose at least two markets, or widen the product filters.")


# ---------------------------------------------------------------------------
# 5. Shoppers
# ---------------------------------------------------------------------------

with tabs[4]:
    if not scope:
        st.info("No products match these filters.")
    else:
        people = [shopper] + [c for c in consumer_labels if c != shopper] if shopper else consumer_labels
        names = [kb.label(pid) for pid in scope]
        order = [v for v, _ in VERDICTS]
        z, hover = [], []
        for person in people:
            row_z, row_h = [], []
            for pid in scope:
                entry = next(c for c in SUMMARIES[pid]["consumers"] if c["consumer"] == person)
                v = verdict_of(entry)
                row_z.append(order.index(v))
                row_h.append(v)
            z.append(row_z)
            hover.append(row_h)
        n = len(order)
        scale = []
        for k, (_, color) in enumerate(VERDICTS):
            scale += [[k / n, color], [(k + 1) / n, color]]
        section("Verdict for every shopper and product")
        legend(VERDICTS)
        fig = go.Figure(go.Heatmap(z=z, x=names, y=people, customdata=hover, colorscale=scale, zmin=-0.5, zmax=n - 0.5,
                                   showscale=False, xgap=2, ygap=2,
                                   hovertemplate="%{y}<br>%{x}<br><b>%{customdata}</b><extra></extra>"))
        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(tickangle=-50, tickfont=dict(size=10))
        plot(fig, height=max(330, 34 * len(people) + 190), legend=False)
        if shopper:
            section("Products that are not safe for %s" % shopper)
            flagged = [{"Product": kb.label(r["pid"]), "Verdict": r["verdict"],
                        "Allergens in the product": ", ".join(e["allergen"] for e in SUMMARIES[r["pid"]]["allergens"]) or "none"}
                       for r in in_scope if r["verdict"] != "Safe"]
            if flagged:
                st.dataframe(pd.DataFrame(flagged), hide_index=True)
            else:
                st.success("Every product in scope is confirmed safe for %s." % shopper)
        st.caption("'Not confirmed' means the record is incomplete or an ingredient's origin is unknown, so the reasoner refuses "
                   "to call it safe.")


# ---------------------------------------------------------------------------
# 6. Reasoning lab
# ---------------------------------------------------------------------------

with tabs[5]:
    if focus:
        section("Why? Ask the reasoner to justify a conclusion about %s" % kb.label(focus))
        options = logic.conclusions(ctx, focus)
        if options:
            choice = st.selectbox("Conclusion", range(len(options)), format_func=lambda k: options[k][0], key="why_choice")
            proof = ctx.prover.prove(options[choice][1])
            if proof is not None:
                plain = logic.explain_plain(kb, proof)
                left, right = st.columns(2)
                with left:
                    show_html('<div class="fx-card"><h4>Because these facts hold</h4><ul class="fx-list">%s</ul></div>'
                              % "".join("<li>%s</li>" % esc(f) for f in plain["facts"]))
                with right:
                    show_html('<div class="fx-card"><h4>And these rules apply</h4><ul class="fx-list">%s</ul></div>'
                              % "".join("<li>%s</li>" % esc(r) for r in plain["rules"] + plain["tests"]))
                with st.expander("Full proof tree (backward chaining)"):
                    show_figure(viz.fig_proof_tree(kb, proof))
        else:
            st.caption("No conclusions to explain for this product.")
        section("Why not? Find out what blocks a conclusion")
        goals = {"Verified vegan": "VerifiedVeganProduct(%s)" % focus, "Verified vegetarian": "VerifiedVegetarianProduct(%s)" % focus}
        for u in kb.consumers:
            if not shopper or kb.label(u) == shopper:
                goals["Confirmed safe for %s" % kb.label(u)] = "confirmedSafeFor(%s, %s)" % (focus, u)
        goal_name = st.selectbox("Conclusion that does not hold", list(goals), key="whynot_choice")
        goal = goals[goal_name]
        if ctx.prover.prove(goal) is not None:
            st.success("It does hold, so there is nothing blocking it. Choose another conclusion.")
        else:
            show_html('<div class="fx-card"><h4>What blocks each rule</h4><ul class="fx-list">%s</ul></div>'
                      % "".join("<li>%s</li>" % esc(line) for line in ctx.prover.why_not(goal)))
    left, right = st.columns(2)
    with left:
        section("Myth or fact?")
        myths = logic.MYTHS
        k = st.selectbox("Statement", range(len(myths)), format_func=lambda i: myths[i]["statement"], key="myth_choice")
        b1, b2 = st.columns(2)
        if b1.button("It's a myth", key="myth_no"):
            st.session_state["myth_answer"] = (k, False)
        if b2.button("It's a fact", key="myth_yes"):
            st.session_state["myth_answer"] = (k, True)
        answer = st.session_state.get("myth_answer")
        if answer and answer[0] == k:
            outcome = logic.check_myth(ctx, myths[k])
            right_answer = answer[1] == outcome["is_fact"]
            (st.success if right_answer else st.error)("%s It's a %s. %s" % ("Correct.", "fact" if outcome["is_fact"] else "myth",
                                                                              myths[k]["lesson"]) if right_answer else
                                                       "Not quite: it's a %s. %s" % ("fact" if outcome["is_fact"] else "myth",
                                                                                     myths[k]["lesson"]))
            if outcome["proof"] is not None:
                st.caption("The reasoner's evidence: " + "; ".join(logic.explain_plain(kb, outcome["proof"])["facts"][:4]))
    with right:
        section("Competency questions")
        qa = answers()
        cq = st.selectbox("Question", list(qa), format_func=lambda q: "%s  %s" % (q, qa[q]["question"]), key="cq_choice")
        a = qa[cq]
        show_html("%s <span class='fx-why'>%s</span>" % (pill(a["kind"], ACCENT), esc(a.get("note") or "")))
        st.dataframe(pd.DataFrame(a["rows"], columns=a["columns"]), hide_index=True)
        with st.expander("The same question in SPARQL"):
            st.code(a["sparql"], language="sparql")


# ---------------------------------------------------------------------------
# 7. Validation and method
# ---------------------------------------------------------------------------

with tabs[6]:
    owl = read_json(OUTPUT_DIR / "owl_results.json") or {}
    bench = read_json(OUTPUT_DIR / "benchmark.json") or {}
    earlier = read_json(ROOT / "report" / "colab_runs" / "run1_benchmark_uncapped.json") or {}
    engine_s = res.summary().get("elapsed_s", 0.0)
    section("Two reasoners, one answer")
    if owl.get("pellet"):
        cv = owl.get("crossval", [])
        agree = sum(r["agree"] for r in cv)
        total = sum(r["agree"] + len(r["only_engine"]) + len(r.get("only_owl", r.get("only_pellet", []))) for r in cv)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pellet, 17 SWRL rules: %s" % owl["pellet"]["status"], duration(owl["pellet"]["seconds"]))
        if owl.get("hermit"):
            c2.metric("HermiT, 13 rules: %s" % owl["hermit"]["status"], duration(owl["hermit"]["seconds"]))
        c3.metric("FALCON engine, live in this app", duration(engine_s))
        c4.metric("Facts agreeing, across %d predicates" % len(cv), "%d of %d" % (agree, total))
        st.caption("Pellet and HermiT ran once on Google Colab (Python 3.13, owlready2 0.51, Java 25); their results are read "
                   "from outputs/owl_results.json. The engine runs live in this app.")
    else:
        st.info("The OWL reasoner results appear here after a full run (python run_all.py), which writes outputs/owl_results.json.")
    if bench.get("engine"):
        section("Runtime against knowledge-base size")
        fig = go.Figure()
        eng = bench["engine"]
        fig.add_trace(go.Scatter(x=[r["products"] for r in eng], y=[r["seconds_min"] for r in eng], mode="lines+markers",
                                 name="FALCON engine (slope %.2f)" % bench.get("engine_slope", 0),
                                 line=dict(color=ACCENT, width=3), marker=dict(size=7)))
        hermit = [r for r in bench.get("owl", []) if r["reasoner"] == "hermit" and r["status"] == "consistent"]
        if hermit:
            fig.add_trace(go.Scatter(x=[r["products"] for r in hermit], y=[r["reasoning_seconds"] for r in hermit],
                                     mode="lines+markers", name="HermiT (slope %s)" % bench.get("hermit_slope", "?"),
                                     line=dict(color=TEAL, width=2, dash="dash"), marker=dict(size=7, symbol="square")))
        done = {r["products"] for r in hermit}
        extra = [r for r in earlier.get("owl", []) if r["reasoner"] == "hermit" and r["status"] == "consistent"
                 and r["products"] not in done]
        if extra:
            fig.add_trace(go.Scatter(x=[r["products"] for r in extra], y=[r["reasoning_seconds"] for r in extra], mode="markers",
                                     name="HermiT, earlier uncapped run",
                                     marker=dict(size=10, symbol="square-open", color=TEAL, line=dict(width=2))))
        if owl.get("pellet", {}).get("status") == "consistent":
            fig.add_trace(go.Scatter(x=[len(kb.products)], y=[owl["pellet"]["seconds"]], mode="markers",
                                     name="Pellet, full run (uncapped)",
                                     marker=dict(size=11, symbol="square-open", color=BAD, line=dict(width=2))))
        stopped = [r for r in bench.get("owl", []) if r["reasoner"] == "pellet" and r["status"] == "timeout"]
        if stopped:
            cap = bench.get("owl_timeout_s") or 150
            fig.add_trace(go.Scatter(x=[r["products"] for r in stopped], y=[cap] * len(stopped), mode="markers",
                                     name="Pellet, stopped at %d s" % cap, marker=dict(size=11, symbol="x", color=BAD)))
        fig.update_xaxes(type="log", title_text="products in the knowledge base")
        fig.update_yaxes(type="log", title_text="seconds (log scale)")
        plot(fig, height=400)
        st.caption("A slope of 1 on these log-log axes means linear growth. The engine scales linearly; HermiT grows about "
                   "quadratically; Pellet needs 25 to 36 minutes for every complete run.")
    if owl.get("crossval"):
        with st.expander("Cross-validation by predicate"):
            cv = pd.DataFrame(owl["crossval"])
            st.dataframe(cv[["predicate", "engine", "owl" if "owl" in cv else "pellet", "agree", "jaccard"]], hide_index=True)
    ec = cases()
    left, right = st.columns(2)
    with left:
        section("Incomplete information under three assumptions")
        st.dataframe(pd.DataFrame(ec["EC1"]["rows"]), hide_index=True)
        st.caption("Treating missing data as good news gives false assurances; FALCON draws closed-world conclusions only for "
                   "records marked complete.")
    with right:
        section("Keyword screening against the ontology")
        k1, k2, k3 = st.columns(3)
        k1.metric("Precision", "%.2f" % ec["EC8"]["precision"])
        k2.metric("Recall", "%.2f" % ec["EC8"]["recall"])
        k3.metric("F1", "%.2f" % ec["EC8"]["f1"])
        st.caption("Substring matching flags cocoa butter as dairy and misses caseinate, tahini and surimi.")
    section("How FALCON works")
    build = owl.get("build_report", {})
    st.markdown(
        "- **Ontology.** An OWL 2 DL ontology in SROIQ(D), built with owlready2: %d classes, %d properties, property chains "
        "and disjointness axioms, and %d individuals.\n"
        "- **Rules.** 17 SWRL rules run in Pellet and in FALCON's own engine, which adds negation as failure, three-place "
        "relations and defeasible exemptions: %d rules in total.\n"
        "- **Reasoning.** Forward chaining derives every conclusion with its provenance; backward chaining answers questions "
        "with proof trees and explains why a conclusion does not hold.\n"
        "- **Closed world, locally.** 'Safe' and 'vegan' verdicts are drawn only for records marked complete, so missing "
        "data never becomes a false assurance."
        % (build.get("classes", 62) + build.get("defined_classes", 30), build.get("object_properties", 29) + build.get("data_properties", 4),
           build.get("individuals", 262), len(rules)))
    architecture = ROOT / "docs" / "figures" / "fig03_architecture.png"
    if architecture.exists():
        with st.expander("System architecture"):
            st.image(str(architecture))
