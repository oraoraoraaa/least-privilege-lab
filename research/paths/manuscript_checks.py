"""Check the manuscript against archived native outcomes and an exercised-grant universe."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import fmean

from evaluate import matched, rankings
from summarize import paired, rows


def check(path):
    traces = json.loads((path/"traces.json").read_text())["corpora"]
    fixed = defaultdict(dict)
    for row in rows(path/"enforced.tsv.gz"):
        if row["method"] in ("sibling", "table_freq"):
            key = tuple(row[k] for k in ("corpus","observed","sibling","hidden"))
            fixed[key][row["method"]] = int(row["success"])
    registered = defaultdict(dict)
    for row in rows(path/"matched.tsv.gz"):
        if (row["method"] in ("sibling","table_freq") and row["removal"] == "95"
                and row["universe"] == "full"):
            key = tuple(row[k] for k in ("corpus","observed","sibling","hidden"))
            registered[key][row["method"]] = float(row["success"])
    folds = list(rows(path/"folds.tsv.gz"))
    output = {}
    for corpus, data in traces.items():
        query = data["queries"]
        reads = {q: frozenset(rec["reads"]) for q,rec in query.items()}
        reps = {}
        for q in sorted(query):
            reps.setdefault((query[q]["family"], reads[q]), q)
        unique = set(reps.values())
        methods = ("table_freq", "sibling")
        native, restricted = defaultdict(list), defaultdict(list)
        spans, missing_counts, signs = [], Counter(), Counter()
        frequency = {}
        for family in {rec["family"] for rec in query.values()}:
            frequency[family] = Counter(c for q in query if query[q]["family"] != family for c in reads[q])
        for row in folds:
            if row["corpus"] != corpus or int(row["novel_reads"]) == 0:
                continue
            o,d,h = (row[k] for k in ("observed","sibling","hidden"))
            key = corpus,o,d,h
            family = row["family"]
            full = set(data["universe"])
            observed, donor, hidden = (reads[q] for q in (o,d,h))
            missing = hidden - observed
            missing_counts[len(missing)] += 1
            spans.append(len(full-observed-hidden)//20)
            if donor != hidden:
                delta = registered[key]["sibling"] - registered[key]["table_freq"]
                signs["gain" if delta > 0 else "loss" if delta < 0 else "tie"] += 1
            if {o,d,h} <= unique:
                native[family].append(fixed[key])
            freq = frequency[family]
            pool = set(freq) | observed | donor
            ranks = rankings(pool, observed, donor, freq, "|".join((corpus,family,o,d)))
            limit = len(pool-observed-hidden)//20
            restricted[family].append({m: matched(ranks[m],missing,limit)[1] for m in methods})
        panels = {}
        for name, groups in (("native_distinct",native),("exercised_universe",restricted)):
            by_family = {f:{m:fmean(row[m] for row in xs) for m in methods} for f,xs in groups.items()}
            panels[name] = {"folds":sum(map(len,groups.values())), "families":len(groups),
                            "means":{m:fmean(v[m] for v in by_family.values()) for m in methods},
                            "paired":paired(by_family, "sibling","table_freq")}
        output[corpus] = {"registered_allowance_range":[min(spans),max(spans)],
                          "missing_read_counts":dict(missing_counts),
                          "hidden_differs_registered_fold_signs":dict(signs),**panels}
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    print(json.dumps(check(parser.parse_args().results),indent=2,sort_keys=True))
