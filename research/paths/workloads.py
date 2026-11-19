"""Load pinned query corpora and measure SQLite authorization footprints."""
import hashlib
import io
from pathlib import Path
import re
import tarfile
import urllib.request

import apsw

JOB = "a39603662e023e449cb2121997a5034df9e02ebf"
STATS = "670cb8d4bf4cbfa32f94fdf17f33973d3fd67d1b"
STATS_RAW = f"https://raw.githubusercontent.com/Nathaniel-Han/End-to-End-CardEst-Benchmark/{STATS}/"


def checked_file(cache, name, url, digest):
    path = cache / name
    if path.exists():
        data = path.read_bytes()
    else:
        with urllib.request.urlopen(url, timeout=90) as reply:
            data = reply.read()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"Input checksum mismatch: {name}")
    if not path.exists():
        path.write_bytes(data)
    return data


def load_corpora(cache):
    cache.mkdir(parents=True, exist_ok=True)
    data = checked_file(cache, "job.tgz", f"https://codeload.github.com/gregrahn/join-order-benchmark/tar.gz/{JOB}",
                        "6a57357a67950dbd507f8a7cebdbed1d0a3806b3de445b8dd20f82f0d4aa7593")
    queries = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        schema = tar.extractfile(f"join-order-benchmark-{JOB}/schema.sql").read().decode()
        for entry in tar:
            if match := re.fullmatch(r"(\d+)[a-z]+[.]sql", Path(entry.name).name):
                sql = tar.extractfile(entry).read().decode()
                queries[Path(entry.name).stem] = (match[1], sql)
    yield "JOB", schema, queries
    schema = checked_file(cache, "stats-schema.sql", STATS_RAW + "datasets/stats_simplified/stats.sql",
                          "adb88e0ab3640fa75bfb4eb67cf128742c0559fb5d0c26aa6e41243ee765b291").decode()
    raw = checked_file(cache, "stats-queries.sql", STATS_RAW + "workloads/stats_CEB/stats_CEB.sql",
                       "8c4f9dca3e4aef8f7d86a3662739e3c2bfa3caec01b23f30b143325a306f86a3").decode()
    queries = {}
    for i, line in enumerate(raw.splitlines(), 1):
        _, sql = line.split("||", 1)
        sql = re.sub(r"('[^']*')::timestamp\b", r"\1", sql, flags=re.I)
        relations = re.search(r"\bfrom\s+(.+?)\s+where\b", sql, re.I)[1].split(",")
        family = "+".join(sorted({r.split()[0].lower() for r in relations}))
        queries[f"q{i:03}"] = (family, sql)
    yield "STATS", schema, queries


class Instrument:
    def __init__(self, schema, *, include_views=False):
        self.db = apsw.Connection(":memory:", statementcachesize=0)
        self.db.execute(schema)
        relations = "select name from sqlite_schema where type='table'"
        if include_views:
            relations = "select name from sqlite_schema where type in ('table','view') and name not glob 'sqlite_*'"
        tables = [r[0] for r in self.db.execute(relations)]
        self.universe = {t.lower() + "." + c[1].lower() for t in tables
                         for c in self.db.execute("select * from pragma_table_info(?)", (t,))}
        self.universe.update(t.lower() + ".@row" for t in tables)
        self.allowed = None
        self.trace = set()
        self.db.authorizer = self._authorize

    def _authorize(self, operation, table, column, database, trigger):
        if operation == apsw.SQLITE_READ:
            resource = table.lower() + "." + (column.lower() if column else "@row")
            self.trace.add(resource)
            if resource not in self.universe:
                raise ValueError(f"Unmodeled resource {resource}")
            if self.allowed is not None and resource not in self.allowed:
                return apsw.SQLITE_DENY
        elif operation not in (apsw.SQLITE_SELECT, apsw.SQLITE_FUNCTION):
            raise ValueError(f"Unexpected authorizer operation {operation}")
        return apsw.SQLITE_OK

    def execute(self, sql, policy=None, *, bindings=None):
        self.allowed = policy
        self.trace = set()
        try:
            self.db.execute(sql, bindings, can_cache=False).fetchall()
            return True, frozenset(self.trace)
        except apsw.AuthError:
            if policy is None:
                raise
            return False, frozenset(self.trace)
        finally:
            self.allowed = None
