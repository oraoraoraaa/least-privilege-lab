# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["apsw==3.53.1.0"]
# ///
"""Regenerate the preflight-selection and forward-replay evidence in a new directory."""
import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"paths"))

from application import aggregate, load_snapshot, transition
from selection import benchmark
from sources import load_sources
from study import write_tsv
from workloads import load_corpora


def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")


def run(out,cache):
    out.mkdir()
    archive = HERE.parent/"paths/results"
    traces = json.loads((archive/"traces.json").read_text())["corpora"]
    comparisons = []
    panels = {}
    for corpus,_,queries in load_corpora(cache/"path-inputs"):
        panels[corpus], rows = benchmark(archive,corpus,traces[corpus]["queries"],queries)
        comparisons.extend(rows)
    write_json(out/"selection.json",panels)
    write_tsv(out/"choices.tsv.gz",["corpus","cohort","family","observed","hidden","near","far",
                                    "unseen_reads","baseline_success","near_success","far_success"],comparisons)
    applications, snapshots, transitions = [], [], []
    for manifest, files in load_sources(cache/"tivi-sql"):
        current = load_snapshot(files)
        snapshots.append({"cutoff":manifest["cutoff"],"revision":manifest["revision"],
                          "universe":sorted(current.db.universe),"inventory":current.inventory,
                          "queries":{q:{"digest":query.digest,"reads":sorted(current.reads[q])}
                                     for q,query in current.queries.items()}})
        if applications:
            outcome=transition(applications[-1],current)
            outcome.update(old=snapshots[-2]["cutoff"],new=manifest["cutoff"])
            transitions.append(outcome)
        applications.append(current)
    write_json(out/"application.json",{"summary":aggregate(transitions),"transitions":transitions})
    write_json(out/"snapshots.json",snapshots)
    for app in applications:
        app.db.db.close()


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--cache",type=Path,default=ROOT/"build")
    args=parser.parse_args()
    if args.out.exists():
        parser.error("--out must be a new directory")
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(dir=args.out.parent) as tmp:
        path=Path(tmp)/"results"
        run(path,args.cache)
        path.rename(args.out)
