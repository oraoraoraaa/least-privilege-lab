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

from review import migration_report
from release_check import DIGESTS, verify
from application import added_on_touched_relations, aggregate, introductions, load_snapshot, transition
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
    mihon_sources = load_sources(cache/"mihon-sql","mihon-sources.json","mihonapp/mihon")
    app_series(out,mihon_sources,"mihon","mihon-snapshots")
    apk_apps = {m["cutoff"]:load_snapshot(files) for m,files in mihon_sources if m["cutoff"] in DIGESTS}
    write_json(out/"release-check.json",verify(cache/"mihon-releases",apk_apps))
    for app in apk_apps.values():
        app.db.db.close()
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
            review = migration_report(previous,current.db)
            held_out = {r["query"]:bool(r["missing"]) for r in outcome["outcomes"]}
            diff_flags = {q for q,reads in previous.reads.items()
                          if reads-current.db.universe or added_on_touched_relations(
                              reads,previous.db.universe,current.db.universe)}
            for record,alerts in ((review,set(review["alerts"])),(outcome.setdefault("ddl_review",{}),diff_flags)):
                record["confusion"] = {k:0 for k in ("flag_expanded","flag_stable","quiet_expanded","quiet_stable")}
                for q,expanded in held_out.items():
                    flag = "flag" if q in alerts else "quiet"
                    record["confusion"][flag+("_expanded" if expanded else "_stable")] += 1
                record["flagged_retired"] = sorted(alerts-held_out.keys())
            outcome["review"] = review
            outcome["ddl_review"]["flagged_ids"] = sorted(diff_flags)
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
