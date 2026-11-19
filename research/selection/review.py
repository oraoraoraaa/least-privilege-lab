# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["apsw==3.53.1.0"]
# ///
"""List old named reads that need review under a planned SQLite schema."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"paths"))
from application import load_snapshot, preview_query, schema_sql
from sources import load_sources
from workloads import Instrument


def migration_report(old, planned):
    alerts = {}
    for q,query in sorted(old.queries.items()):
        reads,error = preview_query(planned,query)
        added = reads-old.reads[q]
        if error:
            alerts[q] = {"reason":"prepare_failed","error":error}
        elif added:
            alerts[q] = {"reason":"expanded_reads","added_reads":sorted(added)}
    return {"old_named_reads":len(old.queries),"alerts":alerts}


def local_files(directory):
    files = {str(path.relative_to(directory)):path.read_text() for path in sorted(directory.rglob("*.sq"))}
    if not files:
        raise ValueError(f"No SQLDelight files under {directory}")
    return files


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--example",action="store_true",help="Mihon v0.18.0 old queries and v0.19.0 schema")
    p.add_argument("--old-dir",type=Path,help="Old SQLDelight source directory")
    schema = p.add_mutually_exclusive_group()
    schema.add_argument("--next-ddl",type=Path,help="Planned SQLite DDL file")
    schema.add_argument("--next-dir",type=Path,help="Planned SQLDelight definitions (schema sections only)")
    args=p.parse_args()
    if args.example:
        if args.old_dir or args.next_ddl or args.next_dir:
            p.error("--example supplies its own inputs")
        cases = dict((m["cutoff"],files) for m,files in load_sources(
            HERE.parents[1]/"build/mihon-sql","mihon-sources.json","mihonapp/mihon"))
        files,ddl = cases["v0.18.0"],schema_sql(cases["v0.19.0"])
    else:
        if not args.old_dir or not (args.next_dir or args.next_ddl):
            p.error("provide --old-dir and either --next-dir or --next-ddl, or use --example")
        files=local_files(args.old_dir)
        ddl=args.next_ddl.read_text() if args.next_ddl else schema_sql(local_files(args.next_dir))
    old=load_snapshot(files)
    planned=Instrument(ddl,include_views=True)
    print(json.dumps(migration_report(old,planned),indent=2,sort_keys=True))
    old.db.db.close()
    planned.db.close()


if __name__ == "__main__":
    main()
