"""Post-result donor and duplication checks defined in AUDIT.md."""
from collections import Counter, defaultdict
from fractions import Fraction
import argparse
import json
from pathlib import Path
from statistics import fmean

from evaluate import deploy, family_folds, matched, rankings


def analyze(data, corpus):
    fp = {q: frozenset(r["reads"]) for q,r in data["queries"].items()}
    groups = defaultdict(list)
    for q,r in data["queries"].items():
        groups[r["family"]].append(q)
    pool = set(data["universe"])
    values = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    examples = {}
    for family, ids in sorted(groups.items()):
        eligible = family_folds(ids)
        if not eligible:
            continue
        representatives = {}
        for q in sorted(ids):
            representatives.setdefault(fp[q], q)
        reps = set(representatives.values())
        others = sorted(set(fp)-set(ids))
        freq = Counter(c for q in others for c in fp[q])
        nearest = {o: min(others, key=lambda q: (-Fraction(len(fp[q]&fp[o]),len(fp[q]|fp[o])),q)) for o in ids}
        pair_cache = {}
        for o,d,h in eligible:
            novel=fp[h]-fp[o]
            if not novel:
                continue
            if (o,d) not in pair_cache:
                salt="|".join([corpus,family,o,d])
                base=rankings(pool,fp[o],fp[d],freq,salt)
                outside=rankings(pool,fp[o],fp[nearest[o]],freq,salt)["sibling"]
                masks=[rankings(pool,fp[o],fp[d],freq,salt+f"/{i}")["placebo"] for i in range(32)]
                pair_cache[o,d] = base,outside,masks
            base,outside,masks=pair_cache[o,d]
            allowance=len(pool-fp[o]-fp[h])//20
            methods={m:matched(base[m],novel,allowance)[1] for m in ("table_freq","sibling")}
            methods["nearest"]=matched(outside,novel,allowance)[1]
            cohorts=["original"]
            if fp[h]!=fp[d]:
                cohorts.append("hidden_differs_from_donor")
            if {o,d,h}<=reps and len({fp[o],fp[d],fp[h]})==3:
                cohorts.append("distinct_footprints")
            for cohort in cohorts:
                for method,x in methods.items():
                    values[cohort][family][method].append(x)
            for i,mask in enumerate(masks):
                values["placebo_salts"][family][f"salt_{i:02}"].append(matched(mask,novel,allowance)[1])
            fixed={m:deploy(base[m],fp[o],4) for m in ("table_freq","sibling")}
            diff=int(fp[h]<=fixed["sibling"])-int(fp[h]<=fixed["table_freq"])
            if diff and str(diff) not in examples:
                examples[str(diff)]={"family":family,"observed":o,"donor":d,"hidden":h,"novel":sorted(novel),
                    "four_added":{m:sorted(a-fp[o]) for m,a in fixed.items()},
                    "unused_added":{m:sorted(a-fp[o]-fp[h]) for m,a in fixed.items()}}
    result={"examples":examples}
    for cohort,by in values.items():
        family={f:{m:fmean(xs) for m,xs in d.items()} for f,d in by.items()}
        means={m:fmean(d[m] for d in family.values()) for m in next(iter(family.values()))}
        result[cohort]={"families":len(by),"folds":sum(len(next(iter(d.values()))) for d in by.values()),"means":means}
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("traces",type=Path)
    args=parser.parse_args()
    d=json.loads(args.traces.read_text())["corpora"]
    print(json.dumps({k:analyze(v,k) for k,v in d.items()},indent=2,sort_keys=True))
