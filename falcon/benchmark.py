"""
Scalability benchmark.

Builds synthetic knowledge bases by replicating the curated products with a
seeded random perturbation (one ingredient swapped per copy), then measures:
  * FALCON engine forward chaining and backward-chaining query latency;
  * HermiT and Pellet wall-clock time (with --owl; needs owlready2 and Java).

Each OWL measurement runs in its own process with a hard time limit. Tableau
reasoning grows much faster than linearly, so once a reasoner exceeds the
limit the larger sizes are skipped and the row is recorded as a timeout.

    python -m falcon.benchmark                                  engine only, up to 64x (2,880 products)
    python -m falcon.benchmark --owl --owl-max-factor 4 --owl-timeout 150
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import random
import signal
import statistics
import subprocess
import sys
import time
from pathlib import Path

from .config import OUTPUT_DIR, ROOT
from .engine_bridge import build_rules, kb_facts, make_prover, run_engine
from .kb_loader import load_kb
from .rule_engine import Atom


def synthetic_kb(kb, factor: int, seed: int = 7):
    rng = random.Random(seed)
    pool = [i for i, ing in kb.ingredients.items() if "CompoundIngredient" not in ing["classes"]]
    big = kb.copy()
    big.products = {}
    for k in range(factor):
        for p in kb.products.values():
            q = copy.deepcopy(p)
            q["id"] = p["id"] if k == 0 else "%s__%d" % (p["id"], k)
            q["barcode"] = "SYN-%05d" % (len(big.products) + 1)
            if k > 0 and q["ingredients"]:
                q["ingredients"][rng.randrange(len(q["ingredients"]))] = rng.choice(pool)
                q["ingredients"] = list(dict.fromkeys(q["ingredients"]))
            big.products[q["id"]] = q
    return big


def fit_power_law(xs, ys):
    """Least-squares slope of log(y) on log(x): runtime ~ size^slope."""
    lx, ly = [math.log(x) for x in xs], [math.log(y) for y in ys]
    mx, my = statistics.mean(lx), statistics.mean(ly)
    slope = sum((a - mx) * (b - my) for a, b in zip(lx, ly)) / sum((a - mx) ** 2 for a in lx)
    return round(slope, 3)


def engine_benchmark(kb, factors, repeats=3, queries=40):
    rules = build_rules(kb)
    rows = []
    for factor in factors:
        big = synthetic_kb(kb, factor)
        times, result = [], None
        for _ in range(repeats):
            started = time.perf_counter()
            _, result = run_engine(big, rules=rules)
            times.append(time.perf_counter() - started)
        prover = make_prover(big, rules)
        goals = result.query("containsAllergen", None, None)
        sample = random.Random(1).sample(goals, min(queries, len(goals)))
        if sample:                                   # warm-up, so the first timing excludes start-up costs
            prover.prove(Atom("containsAllergen", sample[0]))
        timings = []
        for p, a in sample:
            started = time.perf_counter()
            prover.prove(Atom("containsAllergen", (p, a)))
            timings.append(time.perf_counter() - started)
        latency = statistics.median(timings) * 1000 if timings else 0.0
        rows.append({"factor": factor, "products": len(big.products), "base_facts": len(kb_facts(big)),
                     "derived_facts": len(result.derived), "seconds_min": round(min(times), 4),
                     "seconds_median": round(statistics.median(times), 4), "backward_ms_per_query": round(latency, 3)})
        print("  engine  %5d products  %7d derived facts  %.3f s" % (rows[-1]["products"], rows[-1]["derived_facts"], rows[-1]["seconds_min"]))
    return rows


# ---------------------------------------------------------------------------
# OWL reasoners, one isolated process per measurement
# ---------------------------------------------------------------------------

def owl_single(factor: int, reasoner: str) -> dict:
    """One measurement (runs inside the worker process)."""
    import owlready2
    from .ontology_builder import build_ontology
    from .owl_reasoning import configure_java, run_reasoner
    configure_java()
    big = synthetic_kb(load_kb(), factor)
    world = owlready2.World()
    started = time.perf_counter()
    onto, _ = build_ontology(big, world=world, swrl="no-builtins" if reasoner == "hermit" else "all")
    built = time.perf_counter() - started
    run, _ = run_reasoner(world, onto, reasoner)
    return {"factor": factor, "products": len(big.products), "reasoner": reasoner, "status": run.status,
            "build_seconds": round(built, 3), "reasoning_seconds": round(run.seconds, 3), "message": run.message[:200]}


def _kill_tree(proc) -> None:
    """Kill the worker and the Java reasoner it started."""
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
    except (ProcessLookupError, OSError):
        pass


def owl_run_isolated(factor: int, reasoner: str, timeout: float, n_products: int) -> dict:
    cmd = [sys.executable, "-m", "falcon.benchmark", "--owl-single", str(factor), reasoner]
    options = dict(cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if os.name == "posix":
        options["start_new_session"] = True              # own process group, so the Java child can be killed too
    else:
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    row = {"factor": factor, "products": n_products * factor, "reasoner": reasoner,
           "build_seconds": None, "reasoning_seconds": None}
    proc = subprocess.Popen(cmd, **options)
    try:
        output, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        proc.communicate()
        return dict(row, status="timeout", message="no result within %d s" % timeout)
    except BaseException:                                # e.g. the user interrupts the notebook cell
        _kill_tree(proc)
        raise
    for line in reversed(output.strip().splitlines()):
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                break
    return dict(row, status="error", message=output[-400:])


def owl_benchmark(kb, factors, timeout: float = 150):
    rows = []
    for reasoner in ("hermit", "pellet"):
        for factor in factors:
            row = owl_run_isolated(factor, reasoner, timeout, len(kb.products))
            rows.append(row)
            seconds = row.get("reasoning_seconds")
            print("  %-6s  %5d products  %-11s %s" % (reasoner, row["products"], row["status"],
                                                     "%.2f s" % seconds if seconds is not None else row.get("message", "")))
            if row["status"] != "consistent":
                print("  %s: larger knowledge bases skipped (they would only take longer)" % reasoner)
                break
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description="FALCON scalability benchmark")
    parser.add_argument("--max-factor", type=int, default=64)
    parser.add_argument("--owl", action="store_true", help="also time HermiT and Pellet")
    parser.add_argument("--owl-max-factor", type=int, default=4)
    parser.add_argument("--owl-timeout", type=float, default=150, help="seconds allowed per OWL reasoner run")
    parser.add_argument("--owl-single", nargs=2, metavar=("FACTOR", "REASONER"), help=argparse.SUPPRESS)
    parser.add_argument("--out", default=str(OUTPUT_DIR / "benchmark.json"))
    args = parser.parse_args(argv)
    if args.owl_single:                                  # worker mode: one measurement, printed as JSON
        print(json.dumps(owl_single(int(args.owl_single[0]), args.owl_single[1])))
        return
    kb = load_kb()
    factors = [f for f in (1, 2, 4, 8, 16, 32, 64, 128) if f <= args.max_factor]
    print("FALCON scalability benchmark")
    out = {"engine": engine_benchmark(kb, factors)}
    out["engine_slope"] = fit_power_law([r["products"] for r in out["engine"]], [r["seconds_min"] for r in out["engine"]])
    if args.owl:
        out["owl"] = owl_benchmark(kb, [f for f in factors if f <= args.owl_max_factor], timeout=args.owl_timeout)
        out["owl_timeout_s"] = args.owl_timeout
        for name in ("hermit", "pellet"):
            ok = [r for r in out["owl"] if r["reasoner"] == name and r["status"] == "consistent" and r["reasoning_seconds"]]
            if len(ok) >= 2:
                out["%s_slope" % name] = fit_power_law([r["products"] for r in ok], [r["reasoning_seconds"] for r in ok])
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("engine runtime grows as products^%.2f; written to %s" % (out["engine_slope"], args.out))


if __name__ == "__main__":
    main()
