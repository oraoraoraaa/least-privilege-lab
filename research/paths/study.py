# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["apsw==3.53.1.0"]
# ///
"""Collect independent native authorization traces and evaluate the frozen study."""
import argparse
from collections import Counter, defaultdict
import csv
import gzip
import io
import json
from pathlib import Path
import tempfile

import apsw
from evaluate import deploy, family_folds, matched, rankings, stable
from workloads import Instrument, load_corpora

ROOT = Path(__file__).resolve().parents[2]
METHODS = ("uniform","table_freq","sibling","placebo")
REMOVALS = (100,95,90,75)


def write_tsv(path, fields, rows):
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf8", newline="") as text:
                writer = csv.writer(text, delimiter="\t", lineterminator="\n")
                writer.writerow(fields)
                writer.writerows(rows)


def run(cache, out):
    trace_archive, folds, measurements, fixed = {}, [], [], []
    for corpus, schema, queries in load_corpora(cache):
        instrument = Instrument(schema)
        footprints, families = {}, defaultdict(list)
        for qid,(family, sql) in sorted(queries.items()):
            ok, footprint = instrument.execute(sql)
            if not ok or not footprint:
                raise ValueError(f"Incomplete reference for {corpus} {qid}")
            footprints[qid] = footprint
            families[family].append(qid)
        trace_archive[corpus] = {
            "universe": sorted(instrument.universe),
            "queries": {qid: {"family": family, "sql_sha256": stable(sql), "reads": sorted(footprints[qid])}
                        for qid,(family, sql) in sorted(queries.items())},
        }
        for family, ids in sorted(families.items()):
            popularity = Counter(c for qid, fp in footprints.items() if queries[qid][0] != family for c in fp)
            for o,d,h in family_folds(ids):
                observed, sibling, hidden = (footprints[key] for key in (o,d,h))
                uid = [corpus, family, o, d, h]
                missing = hidden - observed
                # The placebo assignment is reused for every held-out variant of the same visible pair.
                tiers = rankings(instrument.universe, observed, sibling, popularity, "|".join(uid[:4]))
                known_tables = {c.split(".")[0] for c in observed | sibling}
                limited = {c for c in instrument.universe if c.split(".")[0] in known_tables}
                folds.append([*uid,len(observed),len(sibling),len(hidden),len(missing),
                              len(sibling & missing),len(sibling - observed - hidden)])
                for scope, pool in (("full", instrument.universe), ("visible_tables", limited)):
                    excess = len(pool - observed - hidden)
                    for method, groups in tiers.items():
                        groups = groups if scope == "full" else [g & pool for g in groups]
                        for removal in REMOVALS:
                            allowance = (100-removal)*excess//100
                            retained, success = matched(groups, missing, allowance)
                            measurements.append([*uid,scope,method,removal,excess,allowance,len(missing),
                                                 f"{retained:.12g}", f"{success:.12g}"])
                policies = {m: deploy(t, observed, 4) for m,t in tiers.items()}
                policies.update({"observed":observed,"union":observed | sibling})
                for method, allowed in policies.items():
                    ok, _ = instrument.execute(queries[h][1], allowed)
                    if ok != (hidden <= allowed):
                        raise ValueError(f"Containment/enforcement mismatch for {uid}, {method}")
                    fixed.append([*uid,method,int(ok),len(allowed - observed - hidden),
                                  len(allowed & missing),len(missing),len(allowed)])
        print(f"{corpus}: {len(queries)} native queries, {len(families)} families", flush=True)
    out.mkdir(parents=True, exist_ok=True)
    info = {"sqlite":apsw.sqlitelibversion(), "apsw":apsw.apswversion(), "corpora":trace_archive}
    (out/"traces.json").write_text(json.dumps(info, sort_keys=True, indent=2)+"\n", encoding="utf8")
    ids = ["corpus","family","observed","sibling","hidden"]
    write_tsv(out/"folds.tsv.gz", ids+["observed_reads","sibling_reads","hidden_reads","novel_reads",
                                       "novel_in_sibling","excess_in_sibling"],folds)
    write_tsv(out/"matched.tsv.gz",ids+["universe","method","removal","excess","allowance","novel_reads",
                                        "retained_novel","success"],measurements)
    write_tsv(out/"enforced.tsv.gz",ids+["method","success","excess_kept","retained_novel","novel_reads",
                                         "grants"],fixed)
    print(f"{len(folds)} folds; {len(fixed)} native candidate executions.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache",type=Path,default=ROOT/"build/path-inputs")
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():
        parser.error("--out must be a new directory")
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.out.parent) as tmp:
        result=Path(tmp)/"results"
        run(args.cache,result)
        result.rename(args.out)
