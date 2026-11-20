"""Recount the registered archive and independently replay formerly excluded catalogs."""
from collections import Counter, defaultdict
from pathlib import Path
import gzip
import json
import sys
from fresh import HERE
import apsw
from inventory import dump
from observed import evaluate_project
from workloads import Instrument
from run import source_blobs
from predict import predicted_fields
from observed import schema_only, snapshot

def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


class ColdInstrument(Instrument):
    """Measure a cold statement on a fresh database so FTS's internal cache cannot hide reads."""
    def __init__(self, schema, *, include_views=True):
        super().__init__(schema, include_views=include_views)
        self.ddl = schema
        self.declared = self.universe.copy()
        self.db.authorizer = None
        self.extra_kind = {}
        shadow = set()
        for _, table, kind, _, without_rowid, _ in self.db.execute("pragma table_list"):
            if table.lower().startswith("sqlite_"):
                continue
            if kind == "shadow":
                shadow.add(table.lower())
            for _, name, _, _, _, _, hidden in self.db.execute("select * from pragma_table_xinfo(?)", (table,)):
                if hidden:
                    self.extra_kind[f"{table}.{name}".lower()] = "hidden"
            if kind in ("table", "virtual", "shadow") and not without_rowid:
                observed = set()
                def probe(op, rel, col, dbname, trigger):
                    if op == apsw.SQLITE_READ:
                        observed.add((rel.lower(), (col or "").lower()))
                    return apsw.SQLITE_OK
                self.db.authorizer = probe
                quoted = table.replace('"', '""')
                try:
                    self.db.execute(f'SELECT rowid FROM "{quoted}" LIMIT 0', can_cache=False).fetchall()
                finally:
                    self.db.authorizer = None
                key = table.lower()+".rowid"
                if (table.lower(), "rowid") in observed and key not in self.declared:
                    self.extra_kind[key] = "row identifier"
        self.extra_kind["@sqlite.data_version"] = "read-only pragma"
        self.universe.update(self.extra_kind)
        self.resource_kinds = {}
        for f in self.universe:
            rel,col=f.rsplit(".",1)
            self.resource_kinds[f] = ("table_only" if col=="@row" else "shadow" if rel in shadow
                                      else self.extra_kind.get(f,"column"))

    def _authorize(self, operation, table, column, database, trigger):
        if operation == apsw.SQLITE_PRAGMA and table == "data_version" and column is None:
            key = "@sqlite.data_version"
            self.trace.add(key)
            return apsw.SQLITE_OK if self.allowed is None or key in self.allowed else apsw.SQLITE_DENY
        return super()._authorize(operation, table, column, database, trigger)

    def execute(self, sql, policy=None, *, bindings=None):
        anchor = self.db
        self.db = apsw.Connection(":memory:", statementcachesize=0)
        try:
            self.db.execute(self.ddl)
            self.db.authorizer = self._authorize
            return super().execute(sql, policy, bindings=bindings)
        finally:
            self.db.close()
            self.db = anchor


def fixture():
    schema = """CREATE TABLE ordinary(value TEXT);
        CREATE TABLE keyed(id TEXT PRIMARY KEY) WITHOUT ROWID;
        CREATE VIRTUAL TABLE search USING fts5(body);
        INSERT INTO search VALUES ('sample token'); INSERT INTO ordinary VALUES ('sample');"""
    db = ColdInstrument(schema)
    tests = {}
    for sql, key in [("SELECT rowid FROM ordinary", "ordinary.rowid"),
                     ("SELECT body FROM search WHERE search MATCH 'token'", "search.search")]:
        ok, reads = db.execute(sql)
        assert ok and key in reads and db.execute(sql)[1] == reads
        assert db.execute(sql, reads)[0] and not db.execute(sql, reads-{key})[0]
        tests[key] = sorted(reads)
    assert "keyed.rowid" not in db.universe
    assert not db.execute("SELECT body FROM search WHERE search MATCH 'token'", set(tests["search.search"])-{"@sqlite.data_version"})[0]
    db.db.close()
    return tests


def group_cost(t):
    contract = set().union(*t["next_reads"].values())
    shared = t["shared"]
    grants = lambda m: set(t["grants"][shared[m]["policy"]])
    base = grants("retain")
    out = {}
    for m, policy in shared.items():
        unused = grants(m)-base-contract
        assert len(unused) == policy["unused_new"]
        rows = sum(f.endswith(".@row") for f in unused)
        kinds = Counter(t.get("resource_kinds", {}).get(f, "table_only" if f.endswith(".@row") else "column") for f in unused)
        out[m] = dict(kinds=kinds, steps=1, all_admitted=int(not policy["denied"]),
                      queries=len(t["next_reads"]), admitted=len(t["next_reads"])-len(policy["denied"]),
                      unused=len(unused), table_only=rows,
                      other_resources=sorted(unused-{x for x in unused if x.endswith(".@row")}))
    return out


def main(out):
    migration = HERE.parent/"migrations"
    manifest = read(migration/"manifest.json.gz")["projects"]
    result = dict(fixture=fixture(), projects={})
    for project, meta in sorted(manifest.items()):
        name = project.split("/")[1]
        original = read(migration/"results"/(name+".json.gz"))
        lookup = {(t["database"],t["new"]): t for t in original["transitions"] if "/generator/" not in t["database"]}
        details = {}
        mechanisms = Counter()
        old_cost, recovered_cost, overlap = [], [], []
        # Reconstruct the discovery rule from only the available old reads and planned DDL.
        blobs = source_blobs(project, meta)
        frames = {e["revision"]: e["databases"] for e in meta["events"]}
        for (database,rev), t in lookup.items():
            def make(revision):
                spec = frames[revision][database]
                files = {p:blobs[h] for p,h in spec["files"].items()}
                return files, schema_only(files, spec)
            files, olddb = make(t["old"])
            _, planned = make(rev)
            old, _ = snapshot(files, olddb)
            selected = predicted_fields(old, planned, ("selective",))
            for q,p in t["predictions"].items():
                hybrid = selected[q]["selective"]
                full = p["rehearsal"]
                mechanisms.update(old=1, selected=int(hybrid["route"]=="rehearsal"),
                                  list_disagreements=int(hybrid["added"]!=full["added"]),
                                  full_errors=int(bool(full["error"])), selected_errors=int(bool(hybrid["error"])))
                if q in t["rows"]:
                    target=t["rows"][q]["missing"]
                    if target and full["added"]==target:
                        mechanisms["rehearsal_exact"]+=1
                        mechanisms["also_diff_exact"]+=p["diff"]["added"]==target
                    mechanisms["correct_fields_beyond_diff"]+=len((set(full["added"])-set(p["diff"]["added"]))&set(target))
            olddb.db.close()
            planned.db.close()
            if t["complete"]:
                old_cost.append(dict(database=database, new=rev, outcomes=group_cost(t)))
        if name in ("twine","feed-flow"):
            extended = evaluate_project(project,meta,blobs,ColdInstrument)
            remaining = Counter()
            for t in extended["transitions"]:
                original_t=lookup[t["database"],t["new"]]
                if t["complete"]:
                    group = overlap if original_t["complete"] else recovered_cost
                    group.append(dict(database=t["database"],new=t["new"],outcomes=group_cost(t)))
                elif original_t["complete"]:
                    raise ValueError("Lost previously complete catalog")
            for state in extended["ledger"]:
                remaining.update(state.get("errors",{}).values())
            details=dict(remaining_errors=remaining,ledger=extended["ledger"])
            dump(out/(name+"-extended.json.gz"),extended)
        result["projects"][project]=dict(original=old_cost,recovered=recovered_cost,overlap=overlap,mechanisms=mechanisms,**details)
        print(project,len(old_cost),len(recovered_cost),details.get("remaining_errors"),flush=True)
    dump(out/"audit.json.gz",result)


if __name__=="__main__":
    main(Path(sys.argv[1]))
