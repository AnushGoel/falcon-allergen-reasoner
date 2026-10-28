"""
Figures shared by the technical report and the Streamlit app (matplotlib only).

    python -m falcon.viz          writes docs/figures/fig01..fig10 as PNG

Every chart is drawn from live engine results or from files in outputs/, so
the figures can never disagree with the numbers in the report.
"""
from __future__ import annotations

import json
import re
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import to_rgb  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch  # noqa: E402

from . import schema  # noqa: E402
from .config import OUTPUT_DIR, ROOT  # noqa: E402

INK, MUTED, GRID, PANEL = "#1C2541", "#5B6577", "#DDE2EA", "#F3F5F8"
ASSERTED, INFERRED = "#2B7A9B", "#6C4BD8"
SAFE, UNSAFE, CAUTION, UNCERTAIN, UNKNOWN, INFO = "#2F7D4F", "#C8382E", "#D9A21B", "#6C4BD8", "#C9CFD9", "#8A94A6"
STATUS_COLORS = {"VERIFIED": SAFE, "CONTRADICTED": UNSAFE, "AT RISK": CAUTION, "UNVERIFIABLE": UNCERTAIN,
                 "INFORMATIONAL": INFO, "UNSAFE": UNSAFE, "CAUTION": CAUTION, "UNCERTAIN": UNCERTAIN,
                 "SAFE": SAFE, "NOT CONFIRMED": UNKNOWN}
FIG_DIR = ROOT / "docs" / "figures"
WIDTH = 6.5


def _style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "axes.titleweight": "bold", "axes.titlesize": 9,
        "axes.titlecolor": INK, "axes.spines.top": False, "axes.spines.right": False,
        "savefig.dpi": 200, "figure.dpi": 100, "legend.frameon": False,
    })


_style()


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _box(ax, x, y, w, h, title, lines=(), fc="white", ec=INK, title_color=INK, lw=1.2, fontsize=8.5, z=3):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                fc=fc, ec=ec, lw=lw, zorder=z))
    if lines:
        ax.text(x, y + h / 2 - 0.17, title, ha="center", va="top", fontsize=fontsize, fontweight="bold",
                color=title_color, zorder=z + 1)
        ax.text(x, y + h / 2 - 0.42, "\n".join(lines), ha="center", va="top", fontsize=fontsize - 1.8,
                color=MUTED, zorder=z + 1, linespacing=1.25)
    else:
        ax.text(x, y, title, ha="center", va="center", fontsize=fontsize, fontweight="bold", color=title_color, zorder=z + 1)


def _edge_point(cx, cy, hw, hh, tx, ty):
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    t = min(hw / abs(dx) if dx else 1e9, hh / abs(dy) if dy else 1e9)
    return cx + dx * t, cy + dy * t


def _connect(ax, a, b, label="", color=ASSERTED, dashed=False, rad=0.0, lw=1.1, fontsize=6.6, label_shift=(0, 0), z=2, label_xy=None):
    (ax_, ay, aw, ah), (bx, by, bw, bh) = a, b
    start = _edge_point(ax_, ay, aw / 2 + 0.03, ah / 2 + 0.03, bx, by)
    end = _edge_point(bx, by, bw / 2 + 0.05, bh / 2 + 0.05, ax_, ay)
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=8, lw=lw, color=color,
                                 linestyle=(0, (4, 2.5)) if dashed else "-", connectionstyle="arc3,rad=%s" % rad, zorder=z))
    if label:
        mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
        nx, ny = -(end[1] - start[1]), end[0] - start[0]
        mx += nx * rad * 0.5 + label_shift[0]
        my += ny * rad * 0.5 + label_shift[1]
        if label_xy is not None:
            mx, my = label_xy
        ax.text(mx, my, label, ha="center", va="center", fontsize=fontsize, color=color, zorder=z + 2,
                style="italic" if dashed else "normal",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.92))


def _loop(ax, x, y, side, label, color=ASSERTED, label_xy=None):
    sign = -1 if side == "left" else 1
    ax.add_patch(FancyArrowPatch((x, y + 0.22), (x, y - 0.22), arrowstyle="-|>", mutation_scale=8, lw=1.1, color=color,
                                 connectionstyle="arc3,rad=%s" % (1.8 * -sign), zorder=2))
    lx, ly = label_xy if label_xy else (x + sign * 0.55, y)
    ax.text(lx, ly, label, ha=("center" if label_xy else ("right" if sign < 0 else "left")), va="center", fontsize=6.6, color=color,
            zorder=4, bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9))


def _legend_lines(ax, loc="lower left", extra=()):
    handles = [Line2D([0], [0], color=ASSERTED, lw=1.4, label="asserted"),
               Line2D([0], [0], color=INFERRED, lw=1.4, linestyle=(0, (4, 2.5)), label="inferred by reasoning")]
    ax.legend(handles=list(handles) + list(extra), loc=loc, fontsize=7)


def _label(kb, entity):
    return kb.label(entity) if kb is not None else str(entity)


def _wrap(text, width):
    return "\n".join(textwrap.wrap(text, width)) or text


def save(fig, name):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / name
    fig.savefig(path, bbox_inches="tight", facecolor="white", pad_inches=0.06)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Figure 1: conceptual model
# ---------------------------------------------------------------------------

def fig_conceptual_model(kb):
    fig, ax = plt.subplots(figsize=(WIDTH, 4.9))
    ax.set_xlim(-0.6, 10.6)
    ax.set_ylim(-0.15, 7.15)
    ax.axis("off")
    n_cat = sum(a["kind"] == "category" for a in kb.allergens.values())
    n_ing_classes = sum(1 for n, parents, _ in schema.CLASSES if n.endswith("Ingredient") or "Ingredient" in parents)
    B = {"cat": (1.0, 6.5, 1.9, 0.55), "prod": (2.6, 4.35, 2.5, 1.6), "claim": (5.7, 6.35, 2.1, 0.85),
         "jur": (9.15, 6.35, 2.0, 0.85), "alg": (7.9, 3.3, 2.2, 0.95), "ing": (2.6, 1.15, 2.5, 0.95),
         "cons": (9.15, 0.75, 2.0, 0.85), "ex": (5.6, 0.4, 2.75, 0.7)}
    _box(ax, *B["cat"], "ProductCategory", fc=PANEL)
    _box(ax, *B["prod"], "Product", ["hasBarcode (exactly 1)", "hasIngredientListStatus", "hasGlutenPPM",
                                     "hasSulphiteMgPerKg", "%d individuals" % len(kb.products)], fc="#EEF4F8")
    _box(ax, *B["claim"], "LabelClaim", ["vegan, gluten-free, nut-free...", "%d individuals" % len(kb.claims)], fc=PANEL)
    _box(ax, *B["jur"], "Jurisdiction", ["US, Canada, EU"], fc=PANEL)
    _box(ax, *B["alg"], "Allergen", ["%d categories, %d named" % (n_cat, len(kb.allergens) - n_cat)], fc="#F6F1FD", ec=INFERRED)
    _box(ax, *B["ing"], "Ingredient", ["%d kinds in %d classes" % (len(kb.ingredients), n_ing_classes)], fc="#EEF4F8")
    _box(ax, *B["cons"], "Consumer", ["%d profiles" % len(kb.consumers)], fc=PANEL)
    _box(ax, *B["ex"], "DeclarationExemption", ["ingredient x allergen x market"], fc=PANEL)
    edges = [
        ("prod", "cat", "inCategory", False, 0.0, (1.0, 5.62)),
        ("prod", "ing", "hasIngredient", False, 0.0, (3.3, 2.6)),
        ("ing", "alg", "triggersAllergen\npossiblyTriggers", False, 0.08, (4.55, 1.95)),
        ("prod", "alg", "mayContain, declaresAllergen", False, 0.0, (5.25, 4.12)),
        ("prod", "alg", "containsAllergen,\nmustDeclareIn{US, Canada, EU}", True, 0.22, (4.95, 2.85)),
        ("prod", "claim", "hasLabelClaim", False, 0.0, (3.55, 5.78)),
        ("prod", "claim", "contradictsClaim,\nprecautionaryConflictWith", True, -0.32, (4.75, 5.3)),
        ("claim", "alg", "excludesAllergen", False, 0.0, (7.45, 4.7)),
        ("prod", "jur", "soldIn", False, 0.0, (7.75, 5.72)),
        ("jur", "alg", "requiresDeclarationOf", False, 0.0, (9.55, 4.85)),
        ("cons", "alg", "mustAvoid", False, 0.0, (9.55, 2.05)),
        ("prod", "cons", "unsafeFor, cautionFor,\nunsuitableForDietOf", True, 0.0, (7.15, 1.45)),
        ("ex", "ing", "exemptIngredient", False, 0.0, (3.2, 0.2)),
        ("ex", "alg", "exemptAllergen", False, 0.0, (6.95, 1.05)),
    ]
    for a, b, label, dashed, rad, xy in edges:
        _connect(ax, B[a], B[b], label, color=INFERRED if dashed else ASSERTED, dashed=dashed, rad=rad, label_xy=xy)
    _loop(ax, B["ing"][0] - B["ing"][2] / 2, B["ing"][1], "left", "hasComponent\nderivedFrom\nretainsAllergensOf",
          label_xy=(0.3, 0.22))
    _loop(ax, B["alg"][0] + B["alg"][2] / 2, B["alg"][1], "right", "isSubtypeOf", label_xy=(10.05, 3.3))
    _legend_lines(ax, loc="center left")
    ax.legend_.set_bbox_to_anchor((-0.02, 0.42))
    return fig


# ---------------------------------------------------------------------------
# Figure 2: class hierarchy
# ---------------------------------------------------------------------------

def fig_class_hierarchy(kb):
    parents = {name: list(par) for name, par, _ in schema.CLASSES}
    defined = {d["name"]: d["parents"][0] for d in schema.DEFINED_CLASSES}
    defined["Contains<Allergen>Product (x%d)" % sum(1 for a in kb.allergens.values() if a.get("product_class"))] = "Product"
    children = defaultdict(list)
    for name, par in parents.items():
        if par:
            children[par[0]].append(name)
    for name, par in defined.items():
        children[par].append(name)
    roots = [n for n, par in parents.items() if not par]
    counts = Counter()
    for item in kb.ingredients.values():
        for cls in item["classes"]:
            counts[cls] += 1
    positions, order = {}, []

    def walk(node, depth):
        kids = children.get(node, [])
        if not kids:
            positions[node] = (depth, len(order))
            order.append(node)
            return positions[node][1]
        ys = [walk(k, depth + 1) for k in kids]
        positions[node] = (depth, (min(ys) + max(ys)) / 2)
        return positions[node][1]

    for r in roots:
        walk(r, 0)
    n = len(order)
    fig, ax = plt.subplots(figsize=(WIDTH, 0.13 * n + 0.6))
    ax.set_xlim(-0.2, 6.25)
    ax.set_ylim(n, -1)
    ax.axis("off")
    xs = {0: 0.0, 1: 0.9, 2: 2.6, 3: 4.0, 4: 5.05}
    for node, (depth, y) in positions.items():
        x = xs.get(depth, depth * 1.2)
        par = (parents.get(node) or [defined.get(node)])[0] if (parents.get(node) or node in defined) else None
        if par in positions:
            px_, py = xs.get(positions[par][0]), positions[par][1]
            ax.plot([px_ + 0.03, x - 0.05], [py, y], color=GRID, lw=0.8, zorder=1)
        is_defined = node in defined
        label = node + ("  (%d)" % counts[node] if counts.get(node) else "")
        ax.text(x, y, ("\u2261 " if is_defined else "") + label, va="center", ha="left", fontsize=6.3,
                color=INFERRED if is_defined else INK, style="italic" if is_defined else "normal",
                fontweight="bold" if depth == 0 else "normal", zorder=3,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none"))
    for node, par in parents.items():                       # secondary parents (multiple inheritance)
        for extra in par[1:]:
            (d1, y1), (d2, y2) = positions[node], positions[extra]
            ax.plot([xs[d2] + 1.3, xs[d1] - 0.05], [y2, y1], color=CAUTION, lw=0.6, linestyle=":", zorder=1)
    ax.legend(handles=[Line2D([0], [0], color=GRID, lw=2, label="subclass of (primary parent)"),
                       Line2D([0], [0], color=CAUTION, lw=1, linestyle=":", label="second parent (multiple inheritance)"),
                       Line2D([0], [0], color="none", marker="$\u2261$", markersize=7, markeredgecolor=INFERRED,
                              label="defined class (reasoner classifies into it)")],
              loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=3, fontsize=6.5)
    return fig


# ---------------------------------------------------------------------------
# Figure 3: architecture
# ---------------------------------------------------------------------------

def fig_architecture():
    fig, ax = plt.subplots(figsize=(WIDTH, 3.7))
    ax.set_xlim(-0.15, 10.6)
    ax.set_ylim(0.1, 6.3)
    ax.axis("off")
    cols = [("Knowledge", 0.9, "#EEF4F8", [("Curated KB", "data/*.json"), ("Schema", "TBox + RBox"), ("Rule catalogue", "SWRL + engine rules")]),
            ("Build", 3.05, "#F3F5F8", [("Loader", "validation"), ("Ontology builder", "owlready2 -> OWL"), ("Engine bridge", "Horn translation")]),
            ("Reason", 5.2, "#F6F1FD", [("HermiT", "OWL 2 DL"), ("Pellet", "OWL 2 DL + SWRL"), ("Forward chainer", "semi-naive, NAF"), ("Backward chainer", "SLD + proofs")]),
            ("Analyse", 7.35, "#F3F5F8", [("SPARQL", "over inferred graph"), ("Competency Qs", "14 questions"), ("Edge cases", "8 experiments"), ("Cross-validation", "Pellet vs engine")]),
            ("Deliver", 9.5, "#EEF4F8", [("outputs/", "JSON, OWL, traces"), ("Report", "built from outputs"), ("Streamlit app", "Label X-ray"), ("CI", "GitHub Actions")])]
    centers = {}
    for title, x, fc, items in cols:
        ax.text(x, 6.05, title, ha="center", va="center", fontsize=8.5, fontweight="bold", color=INK)
        step = 5.2 / len(items)
        for k, (name, sub) in enumerate(items):
            y = 5.3 - k * step - (0.2 if len(items) == 3 else 0)
            _box(ax, x, y, 1.98, 0.8, name, [sub], fc=fc, ec=INFERRED if title == "Reason" else INK, fontsize=7.2)
            centers[name] = (x, y, 1.98, 0.8)
    links = [("Curated KB", "Loader"), ("Schema", "Ontology builder"), ("Schema", "Engine bridge"),
             ("Rule catalogue", "Ontology builder"), ("Rule catalogue", "Engine bridge"), ("Loader", "Ontology builder"),
             ("Loader", "Engine bridge"), ("Ontology builder", "HermiT"), ("Ontology builder", "Pellet"),
             ("Engine bridge", "Forward chainer"), ("Engine bridge", "Backward chainer"), ("Pellet", "SPARQL"),
             ("Pellet", "Cross-validation"), ("Forward chainer", "Cross-validation"), ("Forward chainer", "Competency Qs"),
             ("Backward chainer", "Competency Qs"), ("Forward chainer", "Edge cases"), ("SPARQL", "outputs/"),
             ("Competency Qs", "outputs/"), ("Edge cases", "outputs/"), ("Cross-validation", "outputs/"),
             ("outputs/", "Report"), ("outputs/", "Streamlit app")]
    for a, b in links:
        _connect(ax, centers[a], centers[b], color=MUTED, lw=0.7, rad=0.0)
    ax.text(5.2, 0.28, "One schema drives both reasoners; every number in the report is read from outputs/.",
            ha="center", fontsize=7, color=MUTED, style="italic")
    return fig


# ---------------------------------------------------------------------------
# Figure 4: knowledge graph around one product
# ---------------------------------------------------------------------------

def _root_paths(kb, base, ingredient):
    """Shortest asserted retain/compose paths from an ingredient to each allergen root it reaches."""
    edges = defaultdict(list)
    for pred in ("retainsAllergensOf", "hasComponent"):
        for s, d in base.match(pred, (None, None)):
            edges[s].append(d)
    paths, frontier, seen = {}, [[ingredient]], {ingredient}
    while frontier:
        path = frontier.pop(0)
        for (_, a) in base.match("assertedTrigger", (path[-1], None)):
            paths.setdefault(a, path)
        for nxt in edges.get(path[-1], []):
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(path + [nxt])
    return paths


def fig_product_graph(kb, ctx, product):
    from .competency import claim_status
    res, base = ctx.result, ctx.result.base
    p = kb.products[product]
    ingredients = p["ingredients"]
    paths = {i: _root_paths(kb, base, i) for i in ingredients}
    sources = []
    for i in ingredients:
        for allergen, path in paths[i].items():
            for node in path[1:]:
                if node not in sources and node not in ingredients:
                    sources.append(node)
    allergens = sorted({a for i in ingredients for a in paths[i]}, key=kb.label)
    if res.holds("GlutenContainingProduct", product):
        allergens.append("alg_gluten")
    claims, markets = p["claims"], p["sold_in"]
    right = [("claim", c) for c in claims] + [("market", m) for m in markets]
    height = max(len(ingredients), len(sources), len(allergens), len(right), 4) * 0.52 + 0.9
    fig, ax = plt.subplots(figsize=(WIDTH, max(3.2, height)))
    ymax = max(len(ingredients), len(sources), len(allergens), len(right), 4)
    ax.set_xlim(-0.6, 9.9)
    ax.set_ylim(-0.9, ymax + 0.2)
    ax.axis("off")

    def column(items, x):
        n = len(items)
        return {item: (x, ymax - (k + 0.5) * ymax / max(n, 1)) for k, item in enumerate(items)}

    pos = {product: (0.35, ymax / 2)}
    pos.update(column(ingredients, 2.25))
    pos.update(column(sources, 4.35))
    pos.update(column(allergens, 6.25))
    right_pos = column(right, 8.6)
    W, H = 1.86, 0.4

    def node(key, xy, text, fc, ec, bold=False, color=INK):
        ax.add_patch(FancyBboxPatch((xy[0] - W / 2, xy[1] - H / 2), W, H, boxstyle="round,pad=0.02,rounding_size=0.05",
                                    fc=fc, ec=ec, lw=1.0, zorder=3))
        ax.text(xy[0], xy[1], _wrap(text, 19), ha="center", va="center", fontsize=5.8, color=color,
                fontweight="bold" if bold else "normal", zorder=4)

    def arrow(a, b, color=ASSERTED, dashed=False, lw=0.9, rad=0.0):
        ax.add_patch(FancyArrowPatch((a[0] + W / 2, a[1]), (b[0] - W / 2, b[1]), arrowstyle="-|>", mutation_scale=7,
                                     color=color, lw=lw, linestyle=(0, (4, 2.5)) if dashed else "-",
                                     connectionstyle="arc3,rad=%s" % rad, zorder=2))

    hidden = {(a, i) for (_, a, i) in res.query("hiddenAllergenVia", product, None, None)}
    node(product, pos[product], kb.label(product), "#EEF4F8", INK, bold=True)
    for i in ingredients:
        is_hidden = any(h[1] == i for h in hidden)
        node(i, pos[i], kb.label(i), "#F6F1FD" if is_hidden else "white", INFERRED if is_hidden else MUTED)
        arrow(pos[product], pos[i])
    for s in sources:
        node(s, pos[s], kb.label(s), "white", MUTED)
    for a in allergens:
        node(a, pos[a], kb.label(a), "#FBEDEC", UNSAFE, bold=True, color=UNSAFE)
    for i in ingredients:
        for allergen, path in paths[i].items():
            chain = [i] + [x for x in path[1:]]
            for u, v in zip(chain, chain[1:]):
                if u in pos and v in pos:
                    arrow(pos[u], pos[v])
            last = chain[-1]
            arrow(pos[last], pos[allergen], color=ASSERTED)
            if len(chain) > 1:                                     # inherited trigger: inferred shortcut
                arrow(pos[i], pos[allergen], color=INFERRED, dashed=True, lw=1.4 if (allergen, i) in hidden else 0.8, rad=-0.18)
        if res.holds("GlutenSourceIngredient", i) and "alg_gluten" in pos:
            arrow(pos[i], pos["alg_gluten"], color=INFERRED, dashed=True, lw=0.8, rad=0.12)
    for kind, item in right:
        xy = right_pos[(kind, item)]
        if kind == "claim":
            status = claim_status(ctx, product, item)
            node(item, xy, "%s claim: %s" % (kb.label(item), status.lower()), "white", STATUS_COLORS[status],
                 bold=True, color=STATUS_COLORS[status])
        else:
            missing = [kb.label(a) for (_, a, m) in res.query("undeclaredAllergen", product, None, item)]
            text = "%s: %s" % (kb.label(item), ("undeclared " + ", ".join(missing)) if missing else "compliant")
            node(item, xy, text, "#FBEDEC" if missing else "white", UNSAFE if missing else SAFE,
                 bold=bool(missing), color=UNSAFE if missing else SAFE)
        ax.add_patch(FancyArrowPatch((pos[product][0] + W / 2, pos[product][1]), (xy[0] - W / 2, xy[1]),
                                     arrowstyle="-|>", mutation_scale=7, color=MUTED, lw=0.6,
                                     connectionstyle="arc3,rad=-0.08", zorder=1, alpha=0.6))
    for x, title in ((0.35, "Product"), (2.25, "Ingredients"), (4.35, "Sources"),
                     (6.25, "Allergens"), (8.6, "Claims and markets")):
        ax.text(x, ymax + 0.05, title, ha="center", va="bottom", fontsize=7.2, fontweight="bold", color=INK)
    _legend_lines(ax, loc="lower left", extra=[Patch(fc="#F6F1FD", ec=INFERRED, label="ingredient hiding an allergen")])
    ax.legend_.set_bbox_to_anchor((0.0, -0.02))
    return fig


# ---------------------------------------------------------------------------
# Figure 5: proof tree
# ---------------------------------------------------------------------------

_ARGS = re.compile(r"^(not )?(\w+)\((.*)\)$")


def humanise_statement(kb, statement):
    match = _ARGS.match(statement)
    if not match:
        return statement
    neg, pred, args = match.groups()
    labels = []
    for arg in [a.strip() for a in args.split(",")]:
        labels.append(kb.label(arg) if arg in kb.products or arg in kb.ingredients or arg in kb.allergens
                      or arg in kb.claims or arg in kb.consumers or arg in kb.jurisdictions else arg.strip('"'))
    return "%s%s(%s)" % (neg or "", pred, ", ".join(labels))


_AXIOM_KINDS = {"T-SC": "subclass axiom", "T-SP": "sub-property axiom", "T-DEF": "class definition", "T-CH": "property chain",
                "T-INV": "inverse property", "T-TR": "transitive property", "T-SYM": "symmetric property",
                "T-DOM": "domain axiom", "T-RAN": "range axiom"}


def _proof_tag(node) -> str:
    if node.how == "FACT":
        return "asserted fact"
    if node.how == "NAF":
        return "negation as failure"
    if node.how == "BUILTIN":
        return "numeric test"
    if node.how.startswith("T-"):
        kind = _AXIOM_KINDS.get("-".join(node.how.split("-")[:2]), "OWL axiom")
        if not node.rule_name:
            return kind
        return node.rule_name if node.rule_name.split()[0].lower() in kind else "%s: %s" % (kind, node.rule_name)
    return "%s: %s" % (node.how, node.rule_name) if node.rule_name else node.how


def fig_proof_tree(kb, proof, max_nodes=26):
    """A proof as an indented outline: one node per row, so labels never collide however the tree branches."""
    rows = []

    def collect(n, depth=0, parent=None):
        if len(rows) >= max_nodes:
            return
        idx = len(rows)
        rows.append((n, depth, parent))
        for child in n.children:
            collect(child, depth + 1, idx)

    collect(proof)
    n = len(rows)
    fig, ax = plt.subplots(figsize=(WIDTH, 0.3 * n + 0.75))
    ax.set_xlim(0, 100)
    ax.set_ylim(n - 0.35, -1.35)
    ax.axis("off")
    indent = 4.2
    styles = {"FACT": ("#EEF4F8", ASSERTED), "NAF": ("#FBF5E6", CAUTION), "BUILTIN": (PANEL, INFO)}
    placed = []
    for i, (node, depth, parent) in enumerate(rows):
        fc, ec = styles.get(node.how, ("#F6F1FD", INFERRED))
        x = 1 + depth * indent
        if parent is not None:
            px = 1 + rows[parent][1] * indent + 1.3
            ax.plot([px, px, x - 0.5], [parent + 0.3, i, i], color="#B9C0CC", lw=0.8, zorder=1)
        text = ax.text(x, i, humanise_statement(kb, node.statement), ha="left", va="center", fontsize=6.8, color=INK,
                       zorder=3, bbox=dict(boxstyle="round,pad=0.28", fc=fc, ec=ec, lw=0.9))
        placed.append((text, node, ec))
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    to_data = ax.transData.inverted()
    for text, node, ec in placed:              # each rule label sits just right of its box, shrunk if needed
        right = to_data.transform((text.get_bbox_patch().get_window_extent(renderer).x1, 0))[0]
        tag, end = _proof_tag(node), None
        for size in (6.2, 5.6, 5.0):
            label = ax.text(right + 1.2, text.get_position()[1], tag, ha="left", va="center", fontsize=size, color=ec,
                            fontweight="bold", zorder=3)
            end = to_data.transform((label.get_window_extent(renderer).x1, 0))[0]
            if end <= 99.5:
                break
            label.remove()
        else:
            room = max(10, int(len(tag) * (99.5 - right - 1.2) / max(end - right - 1.2, 1)) - 1)
            ax.text(right + 1.2, text.get_position()[1], tag[:room] + "\u2026", ha="left", va="center", fontsize=5.0,
                    color=ec, fontweight="bold", zorder=3)
    ax.legend(handles=[Patch(fc="#F6F1FD", ec=INFERRED, label="rule or axiom applied"),
                       Patch(fc="#EEF4F8", ec=ASSERTED, label="asserted fact"),
                       Patch(fc="#FBF5E6", ec=CAUTION, label="negation as failure")],
              loc="upper left", fontsize=6.3, ncol=3, bbox_to_anchor=(0.0, 1.02), frameon=False)
    return fig


# ---------------------------------------------------------------------------
# Figures 6-8: claim audit, markets, consumers
# ---------------------------------------------------------------------------

def fig_claim_audit(kb, ctx):
    from .competency import claim_status
    statuses = ["VERIFIED", "CONTRADICTED", "AT RISK", "UNVERIFIABLE", "INFORMATIONAL"]
    table = defaultdict(Counter)
    for (p, c) in ctx.result.query("hasLabelClaim", None, None):
        table[kb.label(c)][claim_status(ctx, p, c)] += 1
    claims = sorted(table, key=lambda c: sum(table[c].values()))
    fig, ax = plt.subplots(figsize=(WIDTH, 2.6))
    left = [0] * len(claims)
    for status in statuses:
        values = [table[c][status] for c in claims]
        ax.barh(claims, values, left=left, color=STATUS_COLORS[status], label=status.lower(), height=0.62, edgecolor="white")
        for k, v in enumerate(values):
            if v:
                ax.text(left[k] + v / 2, k, str(v), ha="center", va="center", fontsize=7, color="white", fontweight="bold")
        left = [a + b for a, b in zip(left, values)]
    ax.set_xlabel("number of products carrying the claim")
    ax.legend(ncol=5, fontsize=7, loc="lower right", bbox_to_anchor=(1.0, 1.0))
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    return fig


def fig_market_grid(kb, ctx):
    order = ["alg_milk", "alg_egg", "alg_fish", "alg_crustacean", "alg_mollusc", "alg_peanut", "alg_soy", "alg_sesame",
             "alg_mustard", "alg_celery", "alg_lupin", "alg_almond", "alg_hazelnut", "alg_walnut", "alg_cashew",
             "alg_pecan", "alg_pistachio", "alg_brazil_nut", "alg_macadamia", "alg_pine_nut", "alg_wheat",
             "alg_barley", "alg_rye", "alg_oats", "alg_sulphites"]
    markets = [("jur_us", "United States"), ("jur_canada", "Canada"), ("jur_eu", "European Union")]
    fig, ax = plt.subplots(figsize=(4.6, 5.4))
    differ_rows = 0
    for r, allergen in enumerate(order):
        if allergen == "alg_sulphites":
            texts = ["\u2265 10 ppm", "\u2265 10 ppm", "> 10 mg/kg"]
            ax.axhspan(r - 0.45, r + 0.45, color="#F6F1FD", zorder=0)
            for c, t in enumerate(texts):
                ax.text(c, r, t, ha="center", va="center", fontsize=6.8, color=INFERRED, fontweight="bold")
            differ_rows += 1
            continue
        required = [allergen in kb.jurisdictions[m]["requires_declaration_of"] for m, _ in markets]
        if len(set(required)) > 1:
            ax.axhspan(r - 0.45, r + 0.45, color="#F6F1FD", zorder=0)
            differ_rows += 1
        for c, req in enumerate(required):
            ax.scatter(c, r, s=70, color=INK if req else "white", edgecolor=INK, lw=0.9, zorder=2)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([kb.label(a) for a in order], fontsize=7)
    ax.set_xticks(range(3))
    ax.set_xticklabels([m for _, m in markets], fontsize=7.5)
    ax.xaxis.tick_top()
    ax.set_xlim(-0.6, 2.6)
    ax.set_ylim(len(order) - 0.5, -0.5)
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)
    ax.legend(handles=[Line2D([0], [0], marker="o", color="none", markerfacecolor=INK, markeredgecolor=INK, label="must be declared"),
                       Line2D([0], [0], marker="o", color="none", markerfacecolor="white", markeredgecolor=INK, label="not a declarable allergen"),
                       Patch(fc="#F6F1FD", label="markets disagree (%d rows)" % differ_rows)],
              loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=1, fontsize=6.8)
    return fig


def consumer_status(ctx, product, consumer):
    if ctx.holds("unsafeFor", product, consumer):
        return "UNSAFE"
    if ctx.holds("cautionFor", product, consumer):
        return "CAUTION"
    if ctx.holds("uncertainFor", product, consumer):
        return "UNCERTAIN"
    if ctx.holds("confirmedSafeFor", product, consumer):
        return "SAFE"
    return "NOT CONFIRMED"


def fig_consumer_matrix(kb, ctx):
    consumers = list(kb.consumers)
    severity = {"UNSAFE": 3, "CAUTION": 2, "UNCERTAIN": 1, "NOT CONFIRMED": 0.5, "SAFE": 0}
    products = sorted(kb.products, key=lambda p: (-sum(severity[consumer_status(ctx, p, u)] for u in consumers), kb.label(p)))
    grid = [[to_rgb(STATUS_COLORS[consumer_status(ctx, p, u)]) for p in products] for u in consumers]
    fig, ax = plt.subplots(figsize=(WIDTH, 3.6))
    ax.imshow(grid, aspect="auto", interpolation="nearest")
    for r, u in enumerate(consumers):
        for c, p in enumerate(products):
            if ctx.holds("unsuitableForDietOf", p, u):
                ax.text(c, r, "\u00d7", ha="center", va="center", fontsize=7, color="white", fontweight="bold")
            elif ctx.holds("dietUncertainFor", p, u):
                ax.text(c, r, "?", ha="center", va="center", fontsize=6.5, color=INK, fontweight="bold")
    ax.set_yticks(range(len(consumers)))
    ax.set_yticklabels([_wrap(kb.label(u), 30) for u in consumers], fontsize=6.3)
    ax.set_xticks(range(len(products)))
    ax.set_xticklabels([kb.label(p) for p in products], rotation=90, fontsize=5.2)
    ax.set_xticks([x - 0.5 for x in range(1, len(products))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(consumers))], minor=True)
    ax.grid(which="minor", color="white", lw=0.7)
    ax.tick_params(which="both", length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    handles = [Patch(fc=STATUS_COLORS[s], label=s.lower()) for s in ("UNSAFE", "CAUTION", "UNCERTAIN", "SAFE", "NOT CONFIRMED")]
    handles += [Line2D([0], [0], color="none", marker="$\u00d7$", markeredgecolor=INK, markersize=6, label="unsuitable for diet"),
                Line2D([0], [0], color="none", marker="$?$", markeredgecolor=INK, markersize=6, label="diet uncertain")]
    ax.legend(handles=handles, ncol=7, fontsize=6, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    return fig


# ---------------------------------------------------------------------------
# Figures 9-10: assumptions, lexical baseline, scalability
# ---------------------------------------------------------------------------

def fig_world_assumptions(ec):
    rows = ec["EC1"]["rows"]
    false_safe = sum(x["falsely 'safe' for"] for x in ec["EC1"]["false_assurances"])
    naive, lcwa = rows[1]["product-consumer pairs confirmed safe"], rows[2]["product-consumer pairs confirmed safe"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(WIDTH, 2.7), gridspec_kw={"width_ratios": [1.15, 1]})
    names = ["Open world\n(OWL only)", "Naive closed\nworld", "Local closed\nworld (FALCON)"]
    correct = [0, naive - false_safe, lcwa]
    wrong = [0, false_safe, 0]
    a1.bar(names, correct, color=SAFE, width=0.6, label="justified 'safe' verdicts")
    a1.bar(names, wrong, bottom=correct, color=UNSAFE, width=0.6, label="false assurances")
    for k, (c, w) in enumerate(zip(correct, wrong)):
        a1.text(k, c + w + 6, str(c + w) + ("\n(%d false)" % w if w else ""), ha="center", va="bottom", fontsize=7, color=INK)
    a1.set_ylim(0, max(naive, 1) * 1.28)
    a1.set_ylabel("product-consumer pairs confirmed safe")
    a1.set_title("Incomplete records under three assumptions", loc="left")
    a1.legend(fontsize=6.6, loc="upper left")
    e8 = ec["EC8"]
    a2.bar(["correct\nflags", "false\nalarms", "missed\nallergens"], [e8["true_positives"], e8["false_positives"], e8["false_negatives"]],
           color=[SAFE, CAUTION, UNSAFE], width=0.6)
    for k, v in enumerate([e8["true_positives"], e8["false_positives"], e8["false_negatives"]]):
        a2.text(k, v + 1, str(v), ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    a2.set_title("Keyword screening vs ontology", loc="left")
    a2.set_ylim(0, e8["true_positives"] * 1.35)
    fp = "; ".join("%s -> %s" % (x["triggered by"], x["flagged as"].lower()) for x in e8["false_positive_examples"][:2])
    fn = "; ".join("%s (%s)" % (x["hidden in"], x["missed"].lower()) for x in e8["false_negative_examples"][:2])
    a2.text(0.98, 0.97, "precision %.2f, recall %.2f" % (e8["precision"], e8["recall"]), transform=a2.transAxes,
            ha="right", va="top", fontsize=7, color=INK, fontweight="bold")
    a2.text(0.98, 0.86, _wrap("e.g. " + fp, 44) + "\n" + _wrap("missed: " + fn, 44), transform=a2.transAxes, ha="right",
            va="top", fontsize=5.6, color=MUTED)
    for a in (a1, a2):
        a.grid(axis="y", color=GRID, lw=0.6)
        a.set_axisbelow(True)
    fig.tight_layout()
    return fig


OWL_NAMES = {"hermit": "HermiT", "pellet": "Pellet"}


def fig_scalability(bench, extra=None):
    """Engine vs OWL reasoners. ``extra``: rows from an earlier, uncapped run, drawn as hollow markers."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(WIDTH, 2.6))
    eng = bench["engine"]
    xs = [r["products"] for r in eng]
    a1.loglog(xs, [r["seconds_min"] for r in eng], "o-", color=INFERRED, lw=1.5, ms=4,
              label="FALCON engine (slope %.2f)" % bench["engine_slope"])
    top = max(r["seconds_min"] for r in eng)
    cap = bench.get("owl_timeout_s") or 150
    for name, color in (("hermit", ASSERTED), ("pellet", UNSAFE)):
        pretty = OWL_NAMES[name]
        rows = [r for r in bench.get("owl", []) if r["reasoner"] == name and r["status"] == "consistent" and r.get("reasoning_seconds")]
        if rows:
            slope = bench.get("%s_slope" % name)
            px, py = [r["products"] for r in rows], [r["reasoning_seconds"] for r in rows]
            a1.loglog(px, py, "s--", color=color, lw=1.2, ms=4,
                      label="%s (slope %.2f)" % (pretty, slope) if slope is not None else pretty)
            a1.annotate("%.0f s" % py[-1], (px[-1], py[-1]), textcoords="offset points", xytext=(5, -3), fontsize=6.0, color=color)
            top = max(top, max(py))
        stopped = [r for r in bench.get("owl", []) if r["reasoner"] == name and r["status"] == "timeout"]
        if stopped:
            a1.plot([r["products"] for r in stopped], [cap] * len(stopped), marker="x", color=color, ms=6, mew=1.4, ls="none",
                    label="%s, stopped at %d s" % (pretty, cap))
            top = max(top, cap)
        covered = {r["products"] for r in rows}
        earlier = [r for r in (extra or []) if r["reasoner"] == name and r["status"] == "consistent"
                   and r.get("reasoning_seconds") and r["products"] not in covered]
        for note in sorted({r.get("note", "uncapped run") for r in earlier}):
            group = [r for r in earlier if r.get("note", "uncapped run") == note]
            ex, ey = [r["products"] for r in group], [r["reasoning_seconds"] for r in group]
            a1.loglog(ex, ey, "s", mfc="white", mec=color, mew=1.2, ms=4.5, ls="none", label="%s, %s" % (pretty, note))
            a1.annotate("{:,.0f} s".format(ey[-1]), (ex[-1], ey[-1]), textcoords="offset points", xytext=(5, -3), fontsize=6.0, color=color)
            top = max(top, max(ey))
    low = min(r["seconds_min"] for r in eng)
    a1.set_ylim(bottom=low / 400, top=top * 4)           # empty band at the bottom holds the legend
    a1.set_xlabel("products in knowledge base")
    a1.set_ylabel("reasoning time (s)")
    a1.set_title("Runtime vs knowledge-base size", loc="left")
    a1.legend(fontsize=5.8, loc="lower right", framealpha=0.92)
    a1.grid(which="both", color=GRID, lw=0.5)
    a2.plot(xs, [r["derived_facts"] / 1000 for r in eng], "o-", color=SAFE, lw=1.5, ms=4, label="derived facts (thousands)")
    a3 = a2.twinx()
    a3.plot(xs, [r["backward_ms_per_query"] for r in eng], "^--", color=CAUTION, lw=1.2, ms=4, label="backward query (ms)")
    a3.spines["right"].set_visible(True)
    a2.set_xlabel("products in knowledge base")
    a2.set_ylabel("derived facts (thousands)")
    a3.set_ylabel("ms per backward query")
    a2.set_title("Inference volume and query latency", loc="left")
    h1, l1 = a2.get_legend_handles_labels()
    h2, l2 = a3.get_legend_handles_labels()
    a2.legend(h1 + h2, l1 + l2, fontsize=6.6, loc="upper left")
    a2.grid(color=GRID, lw=0.5)
    fig.tight_layout()
    return fig


def fig_inference_profile(result):
    by_stratum, by_source = Counter(), Counter()
    for derivation in result.derived.values():
        by_stratum[derivation.stratum] += 1
        rule = result.rules.get(derivation.rule_id)
        by_source[rule.source if rule else "?"] += 1
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(WIDTH, 2.3))
    strata = sorted(by_stratum)
    a1.bar([str(s) for s in strata], [by_stratum[s] for s in strata], color=INFERRED)
    a1.set_xlabel("stratum")
    a1.set_ylabel("facts derived")
    a1.set_title("Derivations per stratum", loc="left")
    names = {"tbox": "OWL axioms\n(Horn part)", "tbox-typing": "domain/range", "swrl": "SWRL rules",
             "engine": "closed-world &\nn-ary rules", "integrity": "integrity"}
    keys = sorted(by_source, key=lambda k: -by_source[k])
    a2.barh([names.get(k, k) for k in keys], [by_source[k] for k in keys], color=ASSERTED)
    a2.invert_yaxis()
    a2.set_title("Derivations by rule source", loc="left")
    for a in (a1, a2):
        a.grid(axis="x" if a is a2 else "y", color=GRID, lw=0.6)
        a.set_axisbelow(True)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_context():
    from .competency import EngineContext
    from .engine_bridge import build_rules, make_prover, run_engine
    from .kb_loader import load_kb
    kb = load_kb()
    rules = build_rules(kb)
    _, result = run_engine(kb, rules=rules)
    return kb, EngineContext(kb, result, make_prover(kb, rules), rules)


def main():
    from .edge_cases import run_all as run_edge_cases
    from .rule_engine import Atom
    kb, ctx = build_context()
    ec = run_edge_cases(ctx)
    bench_path = OUTPUT_DIR / "benchmark.json"
    bench = json.loads(bench_path.read_text(encoding="utf-8")) if bench_path.exists() else None
    proof = ctx.prover.prove(Atom("contradictsClaim", ("prod_steakhouse_sauce", "claim_vegan")))
    made = [
        save(fig_conceptual_model(kb), "fig01_conceptual_model.png"),
        save(fig_class_hierarchy(kb), "fig02_class_hierarchy.png"),
        save(fig_architecture(), "fig03_architecture.png"),
        save(fig_product_graph(kb, ctx, "prod_steakhouse_sauce"), "fig04_product_graph.png"),
        save(fig_proof_tree(kb, proof), "fig05_proof_tree.png"),
        save(fig_claim_audit(kb, ctx), "fig06_claim_audit.png"),
        save(fig_market_grid(kb, ctx), "fig07_market_grid.png"),
        save(fig_consumer_matrix(kb, ctx), "fig08_consumer_matrix.png"),
        save(fig_world_assumptions(ec), "fig09_world_assumptions.png"),
        save(fig_inference_profile(ctx.result), "fig11_inference_profile.png"),
    ]
    if bench:
        extra = []
        earlier = ROOT / "report" / "colab_runs" / "run1_benchmark_uncapped.json"
        if earlier.exists():                        # HermiT beyond the capped sizes, from an earlier uncapped run
            extra += [dict(r, note="earlier uncapped run") for r in json.loads(earlier.read_text(encoding="utf-8")).get("owl", [])
                      if r["reasoner"] == "hermit"]
        owl_file = OUTPUT_DIR / "owl_results.json"
        if owl_file.exists():                       # Pellet's complete run on the curated data, from the pipeline
            pellet = json.loads(owl_file.read_text(encoding="utf-8")).get("pellet") or {}
            if pellet.get("status") == "consistent" and pellet.get("seconds"):
                extra.append({"reasoner": "pellet", "products": len(kb.products), "status": "consistent",
                              "reasoning_seconds": pellet["seconds"], "note": "full run, uncapped"})
        made.append(save(fig_scalability(bench, extra=extra), "fig10_scalability.png"))
    for path in made:
        print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
