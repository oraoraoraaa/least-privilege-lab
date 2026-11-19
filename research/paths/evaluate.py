"""Label-blind ranking and exact evaluation for matched excess permissions."""
from collections import Counter, defaultdict
import hashlib
import itertools
from math import comb


def stable(value):
    return hashlib.sha256(value.encode()).hexdigest()


def family_folds(ids):
    triples = itertools.permutations(sorted(ids), 3)
    if len(ids) * (len(ids)-1) * (len(ids)-2) <= 512:
        return list(triples)
    return sorted(triples, key=lambda x: stable("|".join(x)))[:512]


def rankings(universe, observed, sibling, popularity, fold_salt):
    """Inputs to fitting contain only observation, sibling evidence and other-family counts."""
    remaining = universe - observed
    observed_tables = {c.split(".")[0] for c in observed}
    by_table = defaultdict(list)
    for c in remaining:
        by_table[c.split(".")[0]].append(c)
    mask_counts = Counter(c.split(".")[0] for c in sibling - observed)
    placebo = {c for t, pool in by_table.items()
               for c in sorted(pool, key=lambda c: stable(fold_salt + "/" + c))[:mask_counts[t]]}
    tiers = {method: defaultdict(set) for method in ("uniform","table_freq","sibling","placebo")}
    for c in sorted(remaining):
        base = (c.split(".")[0] in observed_tables, popularity[c])
        tiers["uniform"][(0,)].add(c)
        tiers["table_freq"][base].add(c)
        tiers["sibling"][(c in sibling, *base)].add(c)
        tiers["placebo"][(c in placebo, *base)].add(c)
    return {method: [groups[key] for key in sorted(groups, reverse=True)] for method, groups in tiers.items()}


def matched(tiers, missing, allowance):
    """Expected newly retained reads and complete success, with uniform ties at maximal feasible prefix."""
    kept = 0
    for tier in tiers:
        good = len(tier & missing)
        bad = len(tier) - good
        if bad <= allowance:
            kept += good
            allowance -= bad
            continue
        read_count = kept + good * (allowance + 1) / (bad + 1)
        success = comb(good + allowance, good) / comb(good + bad, good) if kept + good == len(missing) else 0.
        return read_count, success
    return kept, float(kept == len(missing))


def deploy(tiers, observed, budget):
    prefix = itertools.chain.from_iterable(sorted(t, key=stable) for t in tiers)
    return observed | set(itertools.islice(prefix, budget))
