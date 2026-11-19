"""Freeze preflight evidence before the future catalog enters the scorer."""
from collections import Counter
from functools import lru_cache
from hashlib import sha256

from predict import predicted_fields

METHODS = ("diff", "coverage", "source", "rehearsal")
CAPS = (0, 1, 2, 4, 8, None)


@lru_cache(maxsize=16384)
def digest(field):
    return sha256(field.encode()).hexdigest()


def policies(names, before, universe, predictions, frequency):
    base = frozenset().union(*(before[n] for n in names)) & universe
    tables = {f.rsplit(".", 1)[0] for f in base}
    result = {"retain": base}
    for method in METHODS:
        votes = Counter(f for n in names for f in predictions[n][method]["added"] if f not in base)
        order = sorted(votes, key=lambda f: (-votes[f], digest(f)))
        for cap in CAPS:
            label = "all" if cap is None else str(cap)
            result[f"{method}/{label}"] = base.union(order[:cap])
        if method in ("diff", "rehearsal"):
            ranked = sorted(universe-base, key=lambda f: (-votes[f], f.rsplit(".",1)[0] not in tables,
                                                          -frequency[f], digest(f)))
            result[method+"/padded4"] = base.union(ranked[:4])
    return result


def fit(old, planned):
    predictions = predicted_fields(old, planned)
    frequency = Counter(f for reads in old.reads.values() for f in reads)
    grouped = {}
    for name, query in old.queries.items():
        grouped.setdefault(query.family, Counter()).update(old.reads[name])
    individual = {n: policies([n], old.reads, planned.universe, predictions, frequency-grouped[q.family])
                  for n,q in old.queries.items()}
    shared = policies(sorted(old.queries), old.reads, planned.universe, predictions, frequency)
    return predictions, individual, shared


def assess(old, new, fitted):
    preds, individual, shared = fitted
    common = sorted(old.queries.keys() & new.queries.keys())
    introduced = sorted(new.queries.keys()-old.queries.keys())
    retired = sorted(old.queries.keys()-new.queries.keys())
    next_contract = frozenset().union(*new.reads.values())
    pool, ids, native = [], {}, {}

    def policy_id(grants):
        if grants not in ids:
            ids[grants] = len(pool)
            pool.append(sorted(grants))
        return ids[grants]

    def admit(q, grants):
        key = (q, policy_id(grants))
        if key not in native:
            query = new.queries[q]
            actual,_ = new.db.execute(query.sql, grants, bindings=query.bindings)
            if actual != (new.reads[q] <= grants):
                raise ValueError(f"Native disagreement for {q}")
            native[key] = actual
        return native[key]

    def score(choices, names, contract):
        base = choices["retain"]
        return {method: {"policy": policy_id(grants),
                         "denied": [q for q in names if not admit(q,grants)],
                         "unused_new": len(grants-base-contract),
                         "unused_old": len(base-contract)}
                for method, grants in choices.items()}

    rows = {q: {"missing": sorted(new.reads[q]-old.reads[q]),
                "edited": new.queries[q].digest != old.queries[q].digest,
                "policies": score(individual[q], [q], new.reads[q])} for q in common}
    account = score(shared, sorted(new.queries), next_contract)
    return {"predictions":preds, "rows":rows,"shared":account,"grants":pool,
            "introduced":introduced,"retired":retired,"native":len(native),
            "next_reads":{q:sorted(fs) for q,fs in sorted(new.reads.items())},
            "old_reads":{q:sorted(fs) for q,fs in sorted(old.reads.items())},
            "schema_added":sorted(new.db.universe-old.db.universe),
            "schema_removed":sorted(old.db.universe-new.db.universe)}
