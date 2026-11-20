# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["apsw==3.53.1.0", "sqlglot==27.29.0"]
# ///
"""Fit on old SQL and planned DDL, then open the next named reads for scoring."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import platform
from statistics import median
import sys
from time import perf_counter_ns

from discover import HERE, fetch
sys.path[:0] = [str(HERE.parent / d) for d in ("migrations", "selection", "paths")]
import apsw
from inventory import dump
from observed import EXPECTED, schema_only, snapshot
from predict import predicted_fields, wildcard_relations

METHODS = ("diff", "source", "rehearsal", "selective")


def prepare_error(row):
    return bool(row["error"]) and not row["error"].startswith(("unsupported callback", "abstain:"))


def evaluate_project(project, manifest, bench):
    with ThreadPoolExecutor(8) as pool:
        blobs = dict(pool.map(lambda item: fetch(project, item), manifest["inputs"].items()))
    steps, ledger, timings, staged = [], [], [], []
    for database, history in manifest["databases"].items():
        old = None
        awaiting = {}
        for state in history:
            rev = state["revision"]
            files = {p: blobs[h] for p,h in state["files"].items()}
            try:
                plan = schema_only(files, {"unsupported": None, "migration_schema": False})
            except EXPECTED as exc:
                ledger.append(dict(database=database, revision=rev, schema_error=str(exc)))
                if old is not None:
                    old.db.db.close()
                old = None
                awaiting.clear()
                continue
            if old is not None:
                forecasts = predicted_fields(old, plan, METHODS)
                if bench:
                    samples = {m: [] for m in ("rehearsal", "selective")}
                    for rep in range(6):
                        order = list(samples)
                        if (rep + len(steps)) % 2:
                            order.reverse()
                        for m in order:
                            wildcard_relations.cache_clear()
                            start = perf_counter_ns()
                            result = predicted_fields(old, plan, (m,))
                            elapsed = perf_counter_ns() - start
                            assert all(row[m] == forecasts[q][m] for q,row in result.items())
                            if rep:
                                samples[m].append(elapsed)
                    timings.append(dict(database=database, new=rev, nanoseconds=samples))
            current, errors = snapshot(files, plan)
            ledger.append(dict(database=database, revision=rev, supported=len(current.queries), errors=errors))
            if old is not None:
                rows = {}
                schema_changed = old.db.universe != plan.universe or old.db.view_definitions != plan.view_definitions
                for q, preds in forecasts.items():
                    actual = current.reads.get(q)
                    rows[q] = dict(predictions=preds,
                        status=("survives" if actual is not None else "unsupported" if q in errors else "retired"),
                        target=sorted(actual-old.reads[q]) if actual is not None else None,
                        edited=current.queries[q].digest != old.queries[q].digest if actual is not None else None)
                # A later observed use is evidence only when no unknown catalog lay between.
                if schema_changed or errors or previous_errors:
                    awaiting.clear()
                for q, r in rows.items():
                    for field in r["target"] or ():
                        if field in awaiting:
                            staged.append(dict(database=database, field=field, query=q,
                                               design=awaiting[field], consumer=rev))
                if not errors and not previous_errors:
                    used = set().union(*current.reads.values())
                    for field in plan.universe - old.db.universe - used:
                        if not field.endswith(".@row"):
                            awaiting[field] = rev
                steps.append(dict(database=database, old=previous, new=rev, rows=rows,
                                  complete=not (previous_errors or errors),
                                  introduced=sorted((current.queries.keys() | errors.keys()) -
                                                    (old.queries.keys() | previous_errors.keys()))))
                old.db.db.close()
            previous, previous_errors, old = rev, errors, current
        if old is not None:
            old.db.db.close()
    return dict(steps=steps, ledger=ledger, staged=staged), timings


def summarize(evidence):
    counts = Counter()
    for step in evidence["steps"]:
        counts.update(steps=1, complete=int(step["complete"]))
        for r in step["rows"].values():
            p = r["predictions"]
            full, selective = p["rehearsal"], p["selective"]
            counts.update(old=1, selected=int(selective["route"] == "rehearsal"),
                          list_disagreements=int(full["added"] != selective["added"]),
                          queue_disagreements=int(full["flag"] != selective["flag"]),
                          full_errors=int(prepare_error(full)), selective_errors=int(prepare_error(selective)),
                          missed_errors=int(prepare_error(full) and not prepare_error(selective)),
                          unsupported_previews=int((full["error"] or "").startswith("unsupported callback")),
                          source_abstentions=int((selective["error"] or "").startswith("abstain:")))
            counts[r["status"]] += 1
            if r["target"]:
                counts["expansions"] += 1
                for m in METHODS:
                    counts[m+"_exact"] += p[m]["added"] == r["target"]
                counts["rehearsal_exact_beyond_diff"] += full["added"] == r["target"] and p["diff"]["added"] != r["target"]
            if r["target"] is not None:
                for m in METHODS:
                    counts[m+"_extras"] += len(set(p[m]["added"])-set(r["target"]))
                    counts[m+"_missing"] += len(set(r["target"])-set(p[m]["added"]))
    return dict(counts)


def main(out, timing):
    manifest = json.loads((HERE/"manifest.json").read_text())
    results, times = {}, {}
    for project, spec in sorted(manifest.items()):
        details, samples = evaluate_project(project, spec, timing is not None)
        results[project] = dict(counts=summarize(details), **details)
        times[project] = samples
        print(project, results[project]["counts"], flush=True)
    dump(out,results)
    if timing:
        record = dict(platform=platform.platform(), machine=platform.machine(), python=platform.python_version(),
                      sqlite=apsw.sqlitelibversion(), projects=times)
        for project, samples in times.items():
            print(project, {m: sum(median(i["nanoseconds"][m]) for i in samples)/1e6
                            for m in ("selective","rehearsal")}, "ms (sum of transition medians)")
        timing.write_text(json.dumps(record,sort_keys=True,indent=2)+"\n")


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    p.add_argument("--timing", type=Path)
    args=p.parse_args()
    main(args.output, args.timing)
