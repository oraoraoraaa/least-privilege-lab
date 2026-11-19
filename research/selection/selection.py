"""Source-only selectors and paired comparisons of archived native policies."""
from collections import defaultdict
from fractions import Fraction
from itertools import combinations, permutations
import math
import re
from statistics import fmean

from summarize import paired, rows

# Consume quoted literals and comments before extracting identifier-like tokens.
LEXER = re.compile(r"'(?:''|[^'])*'|--[^\n]*|/\*.*?\*/|[A-Za-z_][A-Za-z_0-9]*", re.S)


def tokens(sql):
    return {token.lower() for token in LEXER.findall(sql) if token[0].isalpha() or token[0] == "_"}


def similarity(left, right):
    return Fraction(len(left & right),len(left | right) or 1)


def ordered_candidates(query, candidates, vocabulary):
    return sorted(candidates, key=lambda d: (-similarity(vocabulary[query], vocabulary[d]), d))


def benchmark(results, corpus, records, queries):
    native = defaultdict(dict)
    for row in rows(results/"enforced.tsv.gz"):
        if row["corpus"] == corpus and row["method"] in ("sibling", "table_freq"):
            native[row["observed"],row["sibling"],row["hidden"]][row["method"]] = int(row["success"])
    reads = {q:frozenset(r["reads"]) for q,r in records.items()}
    vocabulary = {q:tokens(sql) for q,(_,sql) in queries.items()}
    families = defaultdict(list)
    for q, (family, _) in sorted(queries.items()):
        families[family].append(q)
    evidence = []
    out = {}
    for cohort in ("all_ids","distinct_footprints"):
        family_scores = {}
        for family, ids in sorted(families.items()):
            if cohort == "distinct_footprints":
                representatives = {}
                for q in ids:
                    representatives.setdefault(reads[q],q)
                ids = list(representatives.values())
            if len(ids) < 4:
                continue
            values = defaultdict(list)
            for o,h in permutations(ids,2):
                missing = reads[h] - reads[o]
                if not missing:
                    continue
                feasible = int(len(missing) <= 4)
                candidates = ordered_candidates(o,(q for q in ids if q not in (o,h)),vocabulary)
                for near,far in combinations(candidates,2):
                    a,b = (native[o,d,h] for d in (near,far))
                    assert a["table_freq"] == b["table_freq"]
                    n,f = a["sibling"],b["sibling"]
                    best = max(n,f)
                    random = (n+f)/2
                    if best > feasible:
                        raise ValueError("Native policy exceeds the four-grant ceiling")
                    metrics = dict(baseline=a["table_freq"],near=n,far=f,random=random,best=best,
                                   impossible=1-feasible,both_fail=feasible-best,selection_loss=best-random)
                    for metric, score in metrics.items():
                        values[metric].append(score)
                    evidence.append([corpus,cohort,family,o,h,near,far,len(missing),a["table_freq"],n,f])
            if values:
                family_scores[family] = {k:fmean(v) for k,v in values.items()}
        if not family_scores:
            out[cohort] = {"families":0,"comparisons":0}
            continue
        means = {k:fmean(scores[k] for scores in family_scores.values()) for k in next(iter(family_scores.values()))}
        assert math.isclose(sum(means[k] for k in ("impossible","both_fail","selection_loss","random")),1)
        panel = {"families":len(family_scores), "comparisons":sum(r[1]==cohort for r in evidence),
                 "means":means, "family_means":family_scores}
        if len(family_scores)>1:
            panel["near_minus_random"] = paired(family_scores,"near","random")
            panel["random_minus_baseline"] = paired(family_scores,"random","baseline")
        out[cohort] = panel
    return out, evidence
