"""Recalculate the two final checks specified in AUDIT.md."""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import json
from pathlib import Path
import re
from statistics import fmean

from evaluate import family_folds, matched
from workloads import load_corpora


def join_family(sql):
    """Parse the flat comma joins and qualified equalities of the pinned STATS input."""
    source, where = re.split(r"\s+where\s+", sql.lower(), flags=re.I)
    declarations = re.split(r"\s+from\s+", source)[1].split(",")
    aliases = {}
    for decl in declarations:
        table, alias = re.fullmatch(r"\s*(\w+)\s+as\s+(\w+)\s*", decl).groups()
        if alias in aliases:
            raise ValueError(decl)
        aliases[alias] = table
    pairs = set()
    for condition in re.split(r"\s+and\s+", where.rstrip(";")):
        pair = re.fullmatch(r"\s*(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)\s*", condition)
        if pair:
            a, x, b, y = pair.groups()
            pairs.add("=".join(sorted((aliases[a]+"."+x, aliases[b]+"."+y))))
        elif len(re.findall(r"\b\w+\.\w+\b", condition)) != 1:
            raise ValueError(condition)
    if len(aliases) > 1 and not pairs:
        raise ValueError(sql)
    return "+".join(sorted(aliases.values())) + "/" + ",".join(sorted(pairs))


def panels(data, group_of, use_neighbors):
    footprints = {q: set(rec["reads"]) for q, rec in data["queries"].items()}
    groups = defaultdict(list)
    for q in sorted(footprints):
        groups[group_of[q]].append(q)
    totals = defaultdict(dict)
    pool = set(data["universe"])
    eligible_ids = 0
    for family, ids in groups.items():
        triples = family_folds(ids)
        if not triples:
            continue
        eligible_ids += len(ids)
        reps = {}
        for q in ids:
            reps.setdefault(frozenset(footprints[q]), q)
        representatives = set(reps.values())
        others = sorted(footprints.keys() - set(ids))
        frequency = Counter(c for q in others for c in footprints[q])
        by_o = {}
        for o in ids:
            observed = footprints[o]
            local = Counter()
            if use_neighbors:
                scores = {q: Fraction(len(observed & footprints[q]), len(observed | footprints[q])) for q in others}
                fifth = sorted(scores.values(), reverse=True)[4]
                local.update(c for q in others if scores[q] >= fifth for c in footprints[q])
            tables = {c.split(".")[0] for c in observed}
            by_o[o] = {c: (local[c], c.split(".")[0] in tables, frequency[c]) for c in pool-observed}
        cached = {}
        for o, d, h in triples:
            missing = footprints[h] - footprints[o]
            if not missing:
                continue
            if (o, d) not in cached:
                alternatives = []
                for use_donor in (False, True):
                    tiers = defaultdict(set)
                    for c, key in by_o[o].items():
                        tiers[(use_donor and c in footprints[d], *key)].add(c)
                    alternatives.append([tiers[k] for k in sorted(tiers, reverse=True)])
                cached[o, d] = alternatives
            budget = len(pool - footprints[o] - footprints[h]) // 20
            blind, sibling = (matched(order, missing, budget)[1] for order in cached[o, d])
            for cohort in ("original", "distinct"):
                if cohort == "distinct" and not {o,d,h} <= representatives:
                    continue
                totals[cohort].setdefault(family, []).append((blind, sibling))
    result = {}
    for cohort, by_family in totals.items():
        blind, sibling = (fmean(fmean(row[i] for row in rows) for rows in by_family.values()) for i in (0, 1))
        result[cohort] = {"families": len(by_family), "folds": sum(map(len, by_family.values())),
                          "blind": blind, "sibling": sibling, "difference": sibling-blind}
    return {"groups": len(groups), "eligible_ids": eligible_ids, "panels": result}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("traces", type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    args = parser.parse_args()
    archive = json.loads(args.traces.read_text())["corpora"]
    report = {}
    for name, _, queries in load_corpora(args.cache):
        data = archive[name]
        registered = {q: rec["family"] for q, rec in data["queries"].items()}
        report[name] = {"neighbors": panels(data, registered, True)}
        if name == "STATS":
            strict = {q: join_family(sql) for q, (_, sql) in queries.items()}
            report[name]["join_families"] = panels(data, strict, False)
    print(json.dumps(report, indent=2, sort_keys=True))
