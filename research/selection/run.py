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

from application import aggregate, introductions, load_snapshot, transition
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
    app_series(out,load_sources(cache/"tivi-sql"),"application","snapshots")
    app_series(out,load_sources(cache/"mihon-sql","mihon-sources.json","mihonapp/mihon"),"mihon","mihon-snapshots")
    events = load_sources(cache/"tivi-sql","event-sources.json")
    previous = None
    history = []
    for manifest,files in events:
        current = load_snapshot(files)
        if previous is not None:
            common = sorted(current.queries.keys() & previous.queries.keys())
            history.append({"old":previous_rev,"new":manifest["revision"],"date":manifest["cutoff"],
                            "surviving":len(common),"new_names":introductions(previous,current),
                            "retired_names":sorted(previous.queries.keys()-current.queries.keys()),
                            "text_changed":[q for q in common if previous.queries[q].digest != current.queries[q].digest],
                            "expansions":{q:sorted(current.reads[q]-previous.reads[q]) for q in common
                                          if current.reads[q]-previous.reads[q]}})
            previous.db.db.close()
        previous,previous_rev = current,manifest["revision"]
    previous.db.db.close()
    write_json(out/"tivi-history.json",history)


def app_series(out, sources, name, snapshot_name):
    snapshots, transitions = [], []
    previous = None
    for manifest, files in sources:
        current = load_snapshot(files)
        snapshots.append({"cutoff":manifest["cutoff"],"revision":manifest["revision"],
                          "universe":sorted(current.db.universe),"inventory":current.inventory,
                          "queries":{q:{"digest":query.digest,"reads":sorted(current.reads[q])}
                                     for q,query in current.queries.items()}})
        if previous is not None:
            outcome = transition(previous,current)
            outcome.update(old=snapshots[-2]["cutoff"],new=manifest["cutoff"],
                           introductions=introductions(previous,current))
            transitions.append(outcome)
            previous.db.db.close()
        previous = current
    previous.db.db.close()
    write_json(out/(name+".json"),{"summary":aggregate(transitions),"transitions":transitions})
    write_json(out/(snapshot_name+".json"),snapshots)


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
