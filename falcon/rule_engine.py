"""
FALCON rule engine.

Why write a rule engine when Pellet and HermiT already exist?

1. OWL reasoners report *conclusions*. They do not show which rule fired on
   which facts, and the assignment asks for step-by-step reasoning traces.
   This engine records the provenance of every derived fact.
2. OWL is monotonic and open-world. Questions such as "is this product
   confirmed safe?" or "is this allergen undeclared?" need negation-as-failure
   under a *local* closed-world assumption, which OWL and SWRL cannot express.
3. Running the same production rules through a second, independent engine
   gives a cross-check on the reasoner (see crossval.py).

The language is Datalog with stratified negation (Apt, Blair & Walker, 1988)
plus SWRL-style comparison built-ins. Forward chaining uses semi-naive
evaluation; backward chaining is SLD-style resolution with loop checking.

Rule syntax (a superset of the SWRL human-readable syntax):

    Product(?p), hasIngredient(?p, ?i), not VeganSafeIngredient(?i) -> hasNonVeganSafeIngredient(?p)

Arguments are ?variables, bare identifiers (constants), "quoted strings" or numbers.
"""
from __future__ import annotations

import itertools
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple

Fact = Tuple[str, Tuple[Any, ...]]

# ---------------------------------------------------------------------------
# Terms and atoms
# ---------------------------------------------------------------------------


class Var:
    """A logic variable, written ``?name`` in rule text."""

    __slots__ = ("name",)

    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return "?" + self.name

    def __eq__(self, other) -> bool:
        return isinstance(other, Var) and other.name == self.name

    def __hash__(self) -> int:
        return hash(("?", self.name))


_IDENT = re.compile(r"^[A-Za-z_][\w]*$")


def format_term(term: Any) -> str:
    if isinstance(term, Var):
        return repr(term)
    if isinstance(term, str):
        return term if _IDENT.match(term) else '"%s"' % term
    return repr(term)


def format_fact(pred: str, args: Sequence[Any]) -> str:
    return "%s(%s)" % (pred, ", ".join(format_term(a) for a in args))


@dataclass(frozen=True)
class Atom:
    pred: str
    args: Tuple[Any, ...]
    negated: bool = False

    def variables(self) -> Set[Var]:
        return {a for a in self.args if isinstance(a, Var)}

    def substitute(self, binding: Dict[Var, Any]) -> "Atom":
        return Atom(self.pred, tuple(binding.get(a, a) if isinstance(a, Var) else a for a in self.args), self.negated)

    def is_ground(self) -> bool:
        return not any(isinstance(a, Var) for a in self.args)

    def positive(self) -> "Atom":
        return Atom(self.pred, self.args, False)

    def __str__(self) -> str:
        text = format_fact(self.pred, self.args)
        return "not " + text if self.negated else text


# ---------------------------------------------------------------------------
# Built-ins (the SWRL comparison subset). They test bound values only.
# ---------------------------------------------------------------------------


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


BUILTINS: Dict[str, Callable[..., bool]] = {
    "greaterThan": lambda a, b: _is_number(a) and _is_number(b) and a > b,
    "greaterThanOrEqual": lambda a, b: _is_number(a) and _is_number(b) and a >= b,
    "lessThan": lambda a, b: _is_number(a) and _is_number(b) and a < b,
    "lessThanOrEqual": lambda a, b: _is_number(a) and _is_number(b) and a <= b,
    "equal": lambda a, b: a == b,
    "notEqual": lambda a, b: a != b,
}

BUILTIN_SYMBOLS = {"greaterThan": ">", "greaterThanOrEqual": "\u2265", "lessThan": "<",
                   "lessThanOrEqual": "\u2264", "equal": "=", "notEqual": "\u2260"}


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


@dataclass
class Rule:
    rule_id: str
    name: str
    body: Tuple[Atom, ...]
    head: Atom
    source: str = "engine"      # 'swrl', 'engine', 'integrity', 'tbox' or 'tbox-typing'
    description: str = ""
    text: str = ""
    stratum: int = 0

    def __post_init__(self):
        self.body = tuple(self.body)
        if self.head.negated:
            raise ValueError("Rule %s: the head cannot be negated" % self.rule_id)
        if self.head.pred in BUILTINS:
            raise ValueError("Rule %s: a built-in cannot be a rule head" % self.rule_id)
        # Safety: every variable in the head, in a negated atom or in a built-in
        # must be bound by some positive atom, otherwise the rule is not range-restricted.
        bound: Set[Var] = set()
        for lit in self.body:
            if not lit.negated and lit.pred not in BUILTINS:
                bound |= lit.variables()
        needed = set(self.head.variables())
        for lit in self.body:
            if lit.negated or lit.pred in BUILTINS:
                needed |= lit.variables()
        missing = needed - bound
        if missing:
            raise ValueError("Rule %s is not safe: %s must appear in a positive body atom"
                             % (self.rule_id, ", ".join(sorted(repr(v) for v in missing))))

    def to_fol(self) -> str:
        """First-order rendering used in the report ('not' marks negation as failure)."""
        variables = sorted({v.name for lit in self.body for v in lit.variables()} | {v.name for v in self.head.variables()})

        def term(t):
            return t.name if isinstance(t, Var) else format_term(t)

        def lit_text(lit):
            if lit.pred in BUILTIN_SYMBOLS:
                return "%s %s %s" % (term(lit.args[0]), BUILTIN_SYMBOLS[lit.pred], term(lit.args[1]))
            text = "%s(%s)" % (lit.pred, ", ".join(term(a) for a in lit.args))
            return "not " + text if lit.negated else text

        quantifier = "\u2200%s: " % ", ".join(variables) if variables else ""
        return "%s%s \u2192 %s" % (quantifier, " \u2227 ".join(lit_text(l) for l in self.body), lit_text(self.head))

    def __str__(self) -> str:
        return "%s -> %s" % (", ".join(str(b) for b in self.body), self.head)


_ATOM = re.compile(r"^(not\s+)?([A-Za-z_][\w]*)\s*\((.*)\)$", re.S)
_INT = re.compile(r"^-?\d+$")
_FLOAT = re.compile(r"^-?(\d+\.\d*|\.\d+)([eE]-?\d+)?$")


def _split_top(text: str, sep: str = ",") -> List[str]:
    """Split on separators that are outside parentheses and quotes."""
    parts, buf, depth, quote = [], [], 0, None
    for ch in text:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def parse_term(token: str) -> Any:
    token = token.strip()
    if not token:
        raise ValueError("empty argument")
    if token.startswith("?"):
        return Var(token[1:])
    if len(token) >= 2 and token[0] in "\"'" and token[-1] == token[0]:
        return token[1:-1]
    if token == "true":
        return True
    if token == "false":
        return False
    if _INT.match(token):
        return int(token)
    if _FLOAT.match(token):
        return float(token)
    return token


def parse_atom(text: str) -> Atom:
    match = _ATOM.match(text.strip())
    if not match:
        raise ValueError("Cannot parse atom: %r" % text)
    negation, pred, args = match.groups()
    return Atom(pred, tuple(parse_term(a) for a in _split_top(args)), negated=bool(negation))


def parse_rule(text: str, rule_id: str, name: str = "", source: str = "engine", description: str = "") -> Rule:
    if text.count("->") != 1:
        raise ValueError("Rule %s must contain exactly one '->'" % rule_id)
    body_text, head_text = text.split("->")
    heads = _split_top(head_text)
    if len(heads) != 1:
        raise ValueError("Rule %s must have exactly one head atom" % rule_id)
    body = tuple(parse_atom(a) for a in _split_top(body_text))
    return Rule(rule_id, name or rule_id, body, parse_atom(heads[0]), source, description, " ".join(text.split()))


# ---------------------------------------------------------------------------
# Fact store with simple argument indexes
# ---------------------------------------------------------------------------


def _sort_key(args: Tuple[Any, ...]) -> Tuple[str, ...]:
    return tuple(str(a) for a in args)


class FactStore:
    """Ground facts indexed by predicate and by (predicate, position, value)."""

    def __init__(self, facts: Iterable[Fact] = ()):
        self._by_pred: Dict[str, Set[Tuple[Any, ...]]] = defaultdict(set)
        self._index: Dict[Tuple[str, int, Any], Set[Tuple[Any, ...]]] = defaultdict(set)
        for pred, args in facts:
            self.add(pred, args)

    def add(self, pred: str, args: Sequence[Any]) -> bool:
        args = tuple(args)
        bucket = self._by_pred[pred]
        if args in bucket:
            return False
        bucket.add(args)
        for position, value in enumerate(args):
            self._index[(pred, position, value)].add(args)
        return True

    def has(self, pred: str, args: Sequence[Any]) -> bool:
        bucket = self._by_pred.get(pred)
        return bucket is not None and tuple(args) in bucket

    def has_pred(self, pred: str) -> bool:
        return bool(self._by_pred.get(pred))

    def match(self, pred: str, pattern: Sequence[Any]) -> List[Tuple[Any, ...]]:
        """Facts of ``pred`` matching ``pattern``; ``None`` in the pattern matches anything."""
        bucket = self._by_pred.get(pred)
        if not bucket:
            return []
        best = None
        for position, value in enumerate(pattern):
            if value is not None:
                candidates = self._index.get((pred, position, value))
                if not candidates:
                    return []
                if best is None or len(candidates) < len(best):
                    best = candidates
        size = len(pattern)
        if best is None:
            return [a for a in bucket if len(a) == size]
        return [a for a in best
                if len(a) == size and all(p is None or a[i] == p for i, p in enumerate(pattern))]

    def facts(self, pred: Optional[str] = None) -> List[Fact]:
        if pred is not None:
            return [(pred, a) for a in sorted(self._by_pred.get(pred, ()), key=_sort_key)]
        return [(p, a) for p in sorted(self._by_pred) for a in sorted(self._by_pred[p], key=_sort_key)]

    def predicates(self) -> List[str]:
        return sorted(p for p, bucket in self._by_pred.items() if bucket)

    def count(self, pred: str) -> int:
        return len(self._by_pred.get(pred, ()))

    def __len__(self) -> int:
        return sum(len(b) for b in self._by_pred.values())


_UNBOUND = object()


def _match(store: FactStore, atom: Atom, binding: Dict[Var, Any]) -> Iterator[Tuple[Dict[Var, Any], Tuple[Any, ...]]]:
    pattern = tuple(binding.get(a) if isinstance(a, Var) else a for a in atom.args)
    for args in store.match(atom.pred, pattern):
        extended = None
        consistent = True
        for term, value in zip(atom.args, args):
            if isinstance(term, Var):
                current = (extended if extended is not None else binding).get(term, _UNBOUND)
                if current is _UNBOUND:
                    if extended is None:
                        extended = dict(binding)
                    extended[term] = value
                elif current != value:          # same variable twice, e.g. p(?x, ?x)
                    consistent = False
                    break
        if consistent:
            yield (extended if extended is not None else binding), args


# ---------------------------------------------------------------------------
# Proof objects
# ---------------------------------------------------------------------------


@dataclass
class Derivation:
    rule_id: str
    premises: Tuple[Fact, ...]
    absent: Tuple[Fact, ...]
    checks: Tuple[str, ...]
    stratum: int
    iteration: int


@dataclass
class ProofNode:
    statement: str
    how: str                       # 'FACT', 'BUILTIN', 'NAF' or a rule id
    rule_name: str = ""
    children: List["ProofNode"] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict:
        return {"statement": self.statement, "how": self.how, "rule_name": self.rule_name,
                "note": self.note, "children": [c.to_dict() for c in self.children]}

    def size(self) -> int:
        return 1 + sum(c.size() for c in self.children)

    def depth(self) -> int:
        return 1 + max((c.depth() for c in self.children), default=0)

    def rules_used(self) -> List[str]:
        found = [] if self.how in ("FACT", "BUILTIN", "NAF") else [self.how]
        for child in self.children:
            found.extend(child.rules_used())
        return found

    def render(self) -> str:
        """ASCII tree, safe for any Windows console code page."""
        lines: List[str] = []
        self._render(lines, "", True, True)
        return "\n".join(lines)

    def _render(self, lines: List[str], prefix: str, last: bool, root: bool) -> None:
        if self.how == "FACT":
            tag = "asserted fact"
        elif self.how == "BUILTIN":
            tag = "built-in test"
        elif self.how == "NAF":
            tag = "negation as failure"
        else:
            tag = "%s: %s" % (self.how, self.rule_name) if self.rule_name else self.how
        connector = "" if root else ("`-- " if last else "|-- ")
        line = "%s%s%s   [%s]" % (prefix, connector, self.statement, tag)
        if self.note:
            line += "  (%s)" % self.note
        lines.append(line)
        child_prefix = prefix if root else prefix + ("    " if last else "|   ")
        for i, child in enumerate(self.children):
            child._render(lines, child_prefix, i == len(self.children) - 1, False)


# ---------------------------------------------------------------------------
# Stratification
# ---------------------------------------------------------------------------


def stratify(rules: Sequence[Rule]) -> Dict[str, int]:
    """Assign each predicate a stratum so that negation only looks downwards.

    Raises ValueError when a predicate depends negatively on itself through
    recursion (such programs have no unique stratified model).
    """
    edges, preds = [], set()
    for rule in rules:
        preds.add(rule.head.pred)
        for lit in rule.body:
            if lit.pred in BUILTINS:
                continue
            preds.add(lit.pred)
            edges.append((lit.pred, rule.head.pred, lit.negated))
    level = {p: 0 for p in preds}
    limit = len(preds) + 1
    changed = True
    while changed:
        changed = False
        for src, dst, negative in edges:
            need = level[src] + (1 if negative else 0)
            if level[dst] < need:
                if need > limit:
                    raise ValueError("Rules are not stratifiable: '%s' depends negatively on itself" % dst)
                level[dst] = need
                changed = True
    return level


# ---------------------------------------------------------------------------
# Forward chaining
# ---------------------------------------------------------------------------


@dataclass
class ForwardResult:
    store: FactStore
    base: FactStore
    derived: Dict[Fact, Derivation]
    rules: Dict[str, Rule]
    trace: List[dict]
    firings: Counter
    strata: Dict[str, int]
    iterations: Dict[int, int]
    elapsed_s: float

    def holds(self, pred: str, *args: Any) -> bool:
        return self.store.has(pred, args)

    def query(self, pred: str, *pattern: Any) -> List[Tuple[Any, ...]]:
        return sorted(self.store.match(pred, pattern), key=_sort_key)

    def derived_facts(self, pred: Optional[str] = None) -> List[Fact]:
        facts = [f for f in self.derived if pred is None or f[0] == pred]
        return sorted(facts, key=lambda f: (f[0], _sort_key(f[1])))

    def explain(self, pred: str, *args: Any, max_depth: int = 25) -> Optional[ProofNode]:
        fact = (pred, tuple(args))
        if not self.store.has(*fact):
            return None
        return self._explain(fact, max_depth, frozenset())

    def _explain(self, fact: Fact, depth: int, path: frozenset) -> ProofNode:
        text = format_fact(*fact)
        derivation = self.derived.get(fact)
        if derivation is None:
            return ProofNode(text, "FACT")
        rule = self.rules.get(derivation.rule_id)
        node = ProofNode(text, derivation.rule_id, rule.name if rule else "")
        if depth <= 0 or fact in path:
            node.note = "depth limit" if depth <= 0 else "see above"
            return node
        path = path | {fact}
        for premise in derivation.premises:
            node.children.append(self._explain(premise, depth - 1, path))
        for absent in derivation.absent:
            node.children.append(ProofNode("not " + format_fact(*absent), "NAF", note="not derivable"))
        for check in derivation.checks:
            node.children.append(ProofNode(check, "BUILTIN"))
        return node

    def summary(self) -> dict:
        by_source = Counter()
        for rule_id, n in self.firings.items():
            rule = self.rules.get(rule_id)
            by_source[rule.source if rule else "?"] += n
        return {
            "base_facts": len(self.base),
            "total_facts": len(self.store),
            "derived_facts": len(self.derived),
            "rules": len(self.rules),
            "rules_that_fired": len(self.firings),
            "strata": max(self.iterations) + 1 if self.iterations else 0,
            "iterations_per_stratum": {str(k): v for k, v in sorted(self.iterations.items())},
            "derived_by_rule_source": dict(by_source),
            "elapsed_s": round(self.elapsed_s, 4),
        }


class ForwardChainer:
    """Data-driven inference: apply every rule until nothing new can be derived."""

    def __init__(self, rules: Sequence[Rule], trace_limit: int = 60000):
        self.rules = list(rules)
        duplicates = [rid for rid, n in Counter(r.rule_id for r in self.rules).items() if n > 1]
        if duplicates:
            raise ValueError("Duplicate rule ids: %s" % ", ".join(sorted(duplicates)))
        self.strata = stratify(self.rules)
        for rule in self.rules:
            rule.stratum = self.strata[rule.head.pred]
        self.trace_limit = trace_limit
        self._plans: Dict[Tuple[str, Optional[int]], List[int]] = {}

    def run(self, facts: Iterable[Fact], max_iterations: int = 1000) -> ForwardResult:
        started = time.perf_counter()
        base = FactStore(facts)
        store = FactStore(base.facts())
        derived: Dict[Fact, Derivation] = {}
        trace: List[dict] = []
        firings: Counter = Counter()
        iterations: Dict[int, int] = {}
        by_stratum: Dict[int, List[Rule]] = defaultdict(list)
        for rule in self.rules:
            by_stratum[rule.stratum].append(rule)

        step = 0
        for stratum in sorted(by_stratum):
            rules = by_stratum[stratum]
            delta: Optional[FactStore] = None          # None = first, full round
            iteration = 0
            while True:
                iteration += 1
                if iteration > max_iterations:
                    raise RuntimeError("No fixpoint after %d iterations in stratum %d" % (max_iterations, stratum))
                fresh: Dict[Fact, Derivation] = {}
                for rule in rules:
                    for binding, premises, absent, checks in self._fire(rule, store, delta):
                        head = rule.head.substitute(binding)
                        fact = (head.pred, head.args)
                        if fact in fresh or store.has(head.pred, head.args):
                            continue
                        fresh[fact] = Derivation(rule.rule_id, premises, absent, checks, stratum, iteration)
                if not fresh:
                    break
                delta = FactStore()
                for fact, derivation in fresh.items():
                    store.add(*fact)
                    delta.add(*fact)
                    derived[fact] = derivation
                    firings[derivation.rule_id] += 1
                    step += 1
                    if len(trace) < self.trace_limit:
                        trace.append({
                            "step": step, "stratum": stratum, "iteration": iteration,
                            "rule": derivation.rule_id, "fact": format_fact(*fact),
                            "premises": [format_fact(*p) for p in derivation.premises],
                            "absent": [format_fact(*a) for a in derivation.absent],
                            "checks": list(derivation.checks),
                        })
            iterations[stratum] = iteration

        return ForwardResult(store, base, derived, {r.rule_id: r for r in self.rules}, trace, firings,
                             self.strata, iterations, time.perf_counter() - started)

    # -- semi-naive evaluation ------------------------------------------------

    def _fire(self, rule: Rule, store: FactStore, delta: Optional[FactStore]):
        if delta is None:
            yield from self._evaluate(rule, store, None, None)
            return
        # Later rounds: at least one positive atom must use a fact that is new
        # in the previous round, otherwise the same derivation is just repeated.
        for k, lit in enumerate(rule.body):
            if not lit.negated and lit.pred not in BUILTINS and delta.has_pred(lit.pred):
                yield from self._evaluate(rule, store, delta, k)

    def _plan(self, rule: Rule, k: Optional[int]) -> List[int]:
        key = (rule.rule_id, k)
        if key in self._plans:
            return self._plans[key]
        body = rule.body
        positives = [i for i, lit in enumerate(body) if not lit.negated and lit.pred not in BUILTINS]
        pending = [i for i in range(len(body)) if i not in positives]
        if k is not None:
            positives.remove(k)
            positives.insert(0, k)
        plan: List[int] = [j for j in pending if not body[j].variables()]
        pending = [j for j in pending if j not in plan]
        bound: Set[Var] = set()
        for i in positives:
            plan.append(i)
            bound |= body[i].variables()
            ready = [j for j in pending if body[j].variables() <= bound]   # test as early as possible
            plan.extend(ready)
            pending = [j for j in pending if j not in ready]
        plan.extend(pending)
        self._plans[key] = plan
        return plan

    def _evaluate(self, rule: Rule, store: FactStore, delta: Optional[FactStore], k: Optional[int]):
        plan = self._plan(rule, k)
        body = rule.body
        size = len(plan)
        premises: List[Fact] = []
        absent: List[Fact] = []
        checks: List[str] = []

        def step(index: int, binding: Dict[Var, Any]):
            if index == size:
                yield binding, tuple(premises), tuple(absent), tuple(checks)
                return
            position = plan[index]
            lit = body[position]
            if lit.pred in BUILTINS:
                values = [binding[a] if isinstance(a, Var) else a for a in lit.args]
                if BUILTINS[lit.pred](*values):
                    checks.append(format_fact(lit.pred, values))
                    yield from step(index + 1, binding)
                    checks.pop()
                return
            if lit.negated:
                ground = lit.substitute(binding)
                if not store.has(ground.pred, ground.args):
                    absent.append((ground.pred, ground.args))
                    yield from step(index + 1, binding)
                    absent.pop()
                return
            source = delta if (delta is not None and position == k) else store
            for new_binding, args in _match(source, lit, binding):
                premises.append((lit.pred, args))
                yield from step(index + 1, new_binding)
                premises.pop()

        yield from step(0, {})


# ---------------------------------------------------------------------------
# Backward chaining
# ---------------------------------------------------------------------------


def _indent(text: str, prefix: str) -> str:
    return "\n".join(prefix + line for line in text.splitlines())


_TEST_SYMBOLS = {"greaterThan": ">", "greaterThanOrEqual": "\u2265", "lessThan": "<", "lessThanOrEqual": "\u2264",
                 "equal": "=", "notEqual": "\u2260"}


def _readable_test(atom: Atom) -> str:
    symbol = _TEST_SYMBOLS.get(atom.pred)
    if symbol and len(atom.args) == 2 and atom.is_ground():
        return "%s %s %s is false" % (atom.args[0], symbol, atom.args[1])
    return str(atom)


class BackwardChainer:
    """Goal-driven inference: start from a question and work back to facts.

    SLD-style resolution over the same rules, with answer tables (tabling).
    A goal that is a variant of one of its ancestors is not expanded again,
    which stops left-recursive rules (transitivity) from looping; instead it
    consumes the answers already proved for that goal pattern, and ask()
    repeats the search until no table grows. This makes open queries complete
    even for derived-only recursive predicates such as containsAllergen.
    Negated goals are decided by an independent, complete sub-proof (negation
    as failure); this is sound because the rule set is stratified.
    """

    def __init__(self, rules: Sequence[Rule], facts, max_depth: int = 40,
                 exclude_sources: Sequence[str] = ("tbox-typing",)):
        self.facts = facts if isinstance(facts, FactStore) else FactStore(facts)
        self.by_head: Dict[str, List[Rule]] = defaultdict(list)
        for rule in rules:
            if rule.source not in exclude_sources:
                self.by_head[rule.head.pred].append(rule)
        self.max_depth = max_depth
        self._fresh = itertools.count()
        self._proved: Dict[Fact, ProofNode] = {}
        self._naf: Dict[Fact, bool] = {}
        self._table: Dict[Tuple, Dict[Tuple, ProofNode]] = defaultdict(dict)   # goal pattern -> answers
        self.stats: Counter = Counter()

    # -- public API -------------------------------------------------------------

    def ask(self, goal, limit: Optional[int] = None) -> List[Tuple[Dict[str, Any], ProofNode]]:
        """All distinct answers to ``goal`` (text or Atom), each with one proof tree."""
        atom = parse_atom(goal) if isinstance(goal, str) else goal
        variables = sorted(atom.variables(), key=lambda v: v.name)
        while True:
            before = self._table_size()
            answers, seen = [], set()
            for binding, proof in self._prove(atom, {}, 0, frozenset()):
                values = tuple(self._walk(v, binding) for v in variables)
                if values in seen:
                    continue
                seen.add(values)
                answers.append(({v.name: value for v, value in zip(variables, values)}, proof))
                if limit and len(answers) >= limit:
                    return answers
            if self._table_size() == before:          # fixpoint: another pass cannot add answers
                return answers
            self.stats["tabling_passes"] += 1

    def _table_size(self) -> int:
        return sum(len(answers) for answers in self._table.values())

    def prove(self, goal) -> Optional[ProofNode]:
        answers = self.ask(goal, limit=1)
        return answers[0][1] if answers else None

    def why_not(self, goal, max_reasons: int = 6) -> List[str]:
        """Explain why a ground goal cannot be derived: the first blocking condition per rule."""
        atom = parse_atom(goal) if isinstance(goal, str) else goal
        if not atom.is_ground():
            raise ValueError("why_not needs a ground goal")
        if self.prove(atom) is not None:
            return ["%s actually holds." % atom]
        rules = self.by_head.get(atom.pred, [])
        if not rules:
            return ["%s is not asserted and no rule concludes '%s'." % (atom, atom.pred)]
        reasons = []
        for rule in rules:
            head, body = self._rename(rule)
            binding = self._unify_args(head.args, atom.args, {})
            if binding is None:
                continue
            reasons.append("[%s] %s: %s" % (rule.rule_id, rule.name, self._first_blocker(body, binding)))
            if len(reasons) >= max_reasons:
                break
        return reasons or ["No rule for '%s' matches %s." % (atom.pred, atom)]

    # -- internals ----------------------------------------------------------------

    @staticmethod
    def _walk(term: Any, binding: Dict[Var, Any]) -> Any:
        while isinstance(term, Var) and term in binding:
            term = binding[term]
        return term

    def _unify(self, x: Any, y: Any, binding: Dict[Var, Any]) -> Optional[Dict[Var, Any]]:
        x, y = self._walk(x, binding), self._walk(y, binding)
        if isinstance(x, Var):
            if isinstance(y, Var) and x == y:
                return binding
            new = dict(binding)
            new[x] = y
            return new
        if isinstance(y, Var):
            new = dict(binding)
            new[y] = x
            return new
        return binding if x == y else None

    def _unify_args(self, xs: Sequence[Any], ys: Sequence[Any], binding: Dict[Var, Any]):
        if len(xs) != len(ys):
            return None
        for x, y in zip(xs, ys):
            binding = self._unify(x, y, binding)
            if binding is None:
                return None
        return binding

    def _resolve(self, atom: Atom, binding: Dict[Var, Any]) -> Atom:
        return Atom(atom.pred, tuple(self._walk(a, binding) for a in atom.args), atom.negated)

    def _rename(self, rule: Rule) -> Tuple[Atom, List[Atom]]:
        """Fresh copy of a rule; positive atoms first so tests see bound variables."""
        n = next(self._fresh)
        mapping: Dict[Var, Var] = {}

        def rename(term):
            if isinstance(term, Var):
                if term not in mapping:
                    mapping[term] = Var("%s_%d" % (term.name, n))
                return mapping[term]
            return term

        head = Atom(rule.head.pred, tuple(rename(a) for a in rule.head.args))
        positives = [l for l in rule.body if not l.negated and l.pred not in BUILTINS]
        tests = [l for l in rule.body if l.negated or l.pred in BUILTINS]
        body = [Atom(l.pred, tuple(rename(a) for a in l.args), l.negated) for l in positives + tests]
        return head, body

    @staticmethod
    def _variant_key(atom: Atom):
        names: Dict[Var, int] = {}
        shape = []
        for a in atom.args:
            if isinstance(a, Var):
                names.setdefault(a, len(names))
                shape.append(("v", names[a]))
            else:
                shape.append(("c", a))
        return atom.pred, tuple(shape)

    def _prove(self, goal: Atom, binding: Dict[Var, Any], depth: int, ancestors: frozenset):
        g = self._resolve(goal, binding)
        self.stats["goals"] += 1
        if depth > self.max_depth:
            self.stats["depth_cutoffs"] += 1
            return
        if g.pred in BUILTINS:
            if g.is_ground() and BUILTINS[g.pred](*g.args):
                yield binding, ProofNode(str(g), "BUILTIN")
            return
        if g.negated:
            positive = g.positive()
            if positive.is_ground() and not self._provable(positive):
                yield binding, ProofNode(str(g), "NAF", note="no proof of %s" % positive)
            return

        ground = g.is_ground()
        if ground:
            fact = (g.pred, g.args)
            if self.facts.has(*fact):
                yield binding, ProofNode(str(g), "FACT")
                return
            cached = self._proved.get(fact)
            if cached is not None:
                yield binding, cached
                return
        else:
            pattern = tuple(None if isinstance(a, Var) else a for a in g.args)
            for args in self.facts.match(g.pred, pattern):
                new = self._unify_args(g.args, args, binding)
                if new is not None:
                    yield new, ProofNode(format_fact(g.pred, args), "FACT")

        key = self._variant_key(g)
        if key in ancestors:                          # a loop: reuse answers proved so far, do not recurse
            self.stats["loop_checks"] += 1
            for args, node in list(self._table.get(key, {}).items()):
                new = self._unify_args(g.args, args, binding)
                if new is not None:
                    yield new, node
            return
        ancestors = ancestors | {key}
        for rule in self.by_head.get(g.pred, ()):
            head, body = self._rename(rule)
            new = self._unify_args(head.args, g.args, binding)
            if new is None:
                continue
            for solved, proofs in self._prove_all(body, new, depth + 1, ancestors):
                resolved = self._resolve(head, solved)
                node = ProofNode(str(resolved), rule.rule_id, rule.name, proofs)
                if resolved.is_ground():
                    self._table[key].setdefault(resolved.args, node)
                if ground:                      # one proof is enough for a yes/no goal
                    self._proved[(g.pred, g.args)] = node
                    yield solved, node
                    return
                yield solved, node

    def _prove_all(self, goals: List[Atom], binding: Dict[Var, Any], depth: int, ancestors: frozenset):
        if not goals:
            yield binding, []
            return
        first, rest = goals[0], goals[1:]
        for b1, p1 in self._prove(first, binding, depth, ancestors):
            for b2, ps in self._prove_all(rest, b1, depth, ancestors):
                yield b2, [p1] + ps

    def _provable(self, atom: Atom) -> bool:
        fact = (atom.pred, atom.args)
        if fact not in self._naf:
            self.stats["naf_subproofs"] += 1
            self._naf[fact] = bool(self.ask(atom, limit=1))      # complete search, so NAF stays sound
        return self._naf[fact]

    def _first_blocker(self, body: List[Atom], binding: Dict[Var, Any]) -> str:
        for lit in body:
            goal = self._resolve(lit, binding)
            if goal.pred in BUILTINS and not goal.negated:
                if goal.is_ground() and BUILTINS[goal.pred](*goal.args):
                    continue
                return "test failed: %s" % _readable_test(goal)
            if goal.negated:
                positive = goal.positive()
                if not positive.is_ground():
                    return "cannot test %s (unbound variable)" % goal
                proof = self.prove(positive)
                if proof is not None:
                    return "blocked because %s holds:\n%s" % (positive, _indent(proof.render(), "      "))
                continue
            answers = self.ask(goal, limit=1)
            if not answers:
                return "no evidence for %s" % goal
            binding = dict(binding)
            for var in goal.variables():
                binding[var] = answers[0][0][var.name]
        return "all conditions hold"
