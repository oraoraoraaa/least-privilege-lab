"""Aggregate archived fold measurements with the family as the weighting unit."""
import argparse
from collections import Counter, defaultdict
import csv
import gzip
import json
import math
from pathlib import Path
import random
from statistics import fmean

HERE = Path(__file__).resolve().parent


def rows(path):
    with gzip.open(path,"rt",encoding="utf8") as file:
        yield from csv.DictReader(file,delimiter="\t")


def percentile(values, p):
    k=(len(values)-1)*p
    i=int(k)
    return values[i] + (k-i)*(values[min(i+1,len(values)-1)]-values[i])


def paired(by_family, left, right):
    differences = [methods[left]-methods[right] for _,methods in sorted(by_family.items())]
    rng = random.Random(20261120)
    boots = sorted(fmean(rng.choices(differences,k=len(differences))) for _ in range(2000))
    return {"difference":fmean(differences),"bootstrap95":[percentile(boots,.025),percentile(boots,.975)],
            "positive":sum(v>1e-10 for v in differences),"ties":sum(abs(v)<=1e-10 for v in differences),
            "negative":sum(v < -1e-10 for v in differences),
            "leave_one_out":[min((sum(differences)-x)/(len(differences)-1) for x in differences),
                             max((sum(differences)-x)/(len(differences)-1) for x in differences)]}


def summarize(path):
    traces = json.loads((path/"traces.json").read_text())["corpora"]
    report = {}
    for corpus, data in sorted(traces.items()):
        q = data["queries"]; counts = Counter(v["family"] for v in q.values())
        eligible = {family for family,n in counts.items() if n>=3}
        folds=[r for r in rows(path/"folds.tsv.gz") if r["corpus"]==corpus]
        info=[r for r in folds if int(r["novel_reads"])]
        report[corpus] = {
            "queries":len(q),"universe":len(data["universe"]),"families":len(counts),
            "eligible_families":len(eligible),"eligible_queries":sum(counts[f] for f in eligible),
            "informative_families":len({r["family"] for r in info}),"folds":len(folds),"informative_folds":len(info),
            "duplicate_footprints_within_families":sum(n-len({tuple(x["reads"]) for x in q.values() if x["family"]==f}) for f,n in counts.items()),
            "capped_families":sum(n*(n-1)*(n-2)>512 for n in counts.values()),
        }
    bins = defaultdict(lambda:defaultdict(lambda:defaultdict(list)))
    for file,instrument in [("matched","matched"),("enforced","fixed")]:
        for r in rows(path/(file+".tsv.gz")):
            scope = r.get("universe","full")
            level = r.get("removal","four")
            n = int(r["novel_reads"])
            for cohort in (("all","informative") if n else ("all",)):
                base=(r["corpus"],instrument,scope,level,cohort)
                metrics={"success":float(r["success"])}
                if n: metrics["novel_retention"]=float(r["retained_novel"])/n
                if instrument=="fixed":metrics["excess_kept"]=int(r["excess_kept"])
                for metric,value in metrics.items():
                    bins[(*base,metric)][r["family"]][r["method"]].append(value)
    panels=[]
    for (corpus,instrument,scope,level,cohort,metric),by in sorted(bins.items()):
        family={f:{m:fmean(vals) for m,vals in methods.items()} for f,methods in by.items()}
        methods=next(iter(family.values())).keys()
        panel={"corpus":corpus,"instrument":instrument,"universe":scope,"level":level,"cohort":cohort,
               "metric":metric,"families":len(family),
               "means":{m:fmean(values[m] for values in family.values()) for m in methods}}
        if scope=="full" and cohort=="informative" and metric=="success" and (level=="95" or instrument=="fixed"):
            panel["paired_vs_table"]=paired(family,"sibling","table_freq")
            panel["paired_vs_placebo"]=paired(family,"sibling","placebo")
            panel["family_means"]=family
        panels.append(panel)
    return {"coverage":report,"panels":panels}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results",type=Path)
    args=parser.parse_args()
    print(json.dumps(summarize(args.results),sort_keys=True,indent=2))
