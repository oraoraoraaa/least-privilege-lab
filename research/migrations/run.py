# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["apsw==3.53.1.0", "sqlglot==27.29.0"]
# ///
"""Regenerate the registered migration study and its development gates."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time
from urllib.parse import quote
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE.parent / "selection"), str(HERE.parent / "paths")]
import apsw
from application import load_snapshot, schema_sql
from inventory import CACHE, PROTOCOL, dump
from policy import assess, fit
from release_check import lookups
from sources import load_sources
from workloads import Instrument, checked_file


def fixture(app):
    reference = json.loads(
        (HERE.parent / "selection/results/release-check.json").read_text()
    )
    db = app.db.db
    db.authorizer = None
    values = {
        "_id": 73,
        "title": "Migration fixture",
        "notes": "A private fixture note",
        "source": 1,
        "url": "fixture/manga",
    }
    for _, name, kind, required, default, _ in db.execute("pragma table_info(mangas)"):
        if required and default is None:
            values.setdefault(name, 0 if kind.upper() == "INTEGER" else "fixture")
    db.execute(
        f"INSERT INTO mangas ({','.join(values)}) VALUES ({','.join('?' for _ in values)})",
        tuple(values.values()),
    )
    db.authorizer = app.db._authorize
    base = set(reference["v0.18.0"]["own_schema_reads"])
    out = {}
    for tag, meta in reference.items():
        cache = ROOT / "build/mihon-releases"
        cache.mkdir(parents=True, exist_ok=True)
        apk = checked_file(cache, tag + ".apk", meta["url"], meta["package_sha256"])
        assert hashlib.sha256(apk).hexdigest() == meta["package_sha256"]
        (sql,) = [
            s
            for s in lookups(apk)
            if hashlib.sha256(s.encode()).hexdigest() == meta["literal_sha256"]
        ]
        for label, policy in (("old", base), ("plus_notes", base | {"mangas.notes"})):
            app.db.allowed = policy
            try:
                c = db.execute(sql, (73,), can_cache=False)
                names = [x[0] for x in c.description]
                (row,) = c.fetchall()
                result = dict(zip(names, row, strict=True))
                assert result["title"] == values["title"]
                assert result.get("notes") == (
                    values["notes"] if tag == "v0.19.0" else None
                )
                out[tag + "/" + label] = {
                    "title": result["title"],
                    "notes": result.get("notes"),
                    "admitted": True,
                }
            except apsw.AuthError:
                out[tag + "/" + label] = {"admitted": False}
            finally:
                app.db.allowed = None
    assert [k for k, v in out.items() if not v["admitted"]] == ["v0.19.0/old"]
    return out


def development():
    out = {}
    for project, options in (
        ("Tivi", ("tivi-sql", "sources.json", "chrisbanes/tivi")),
        ("Mihon", ("mihon-sql", "mihon-sources.json", "mihonapp/mihon")),
    ):
        cache, manifest, upstream = options
        snapshots = load_sources(ROOT / "build" / cache, manifest, upstream)
        previous = None
        series = []
        for meta, files in snapshots:
            if previous:
                planned = Instrument(schema_sql(files), include_views=True)
                model = fit(previous, planned)
                planned.db.close()
            current = load_snapshot(files)
            if previous:
                row = assess(previous, current, model)
                row.update(
                    old=old_tag, new=meta["cutoff"], database=project, complete=True
                )
                series.append(row)
                previous.db.db.close()
            if project == "Mihon" and meta["cutoff"] == "v0.19.0":
                witness = load_snapshot(files)
                out["fixture"] = fixture(witness)
                witness.db.db.close()
            previous, old_tag = current, meta["cutoff"]
        previous.db.db.close()
        out[project] = series
    pairs, stable, unused = [], 0, 0
    for project in ("Tivi", "Mihon"):
        for t in out[project]:
            for name, r in t["rows"].items():
                if r["missing"]:
                    pairs.append(
                        tuple(
                            t["predictions"][name][m]["added"] == r["missing"]
                            for m in ("coverage", "rehearsal")
                        )
                    )
                else:
                    stable += 1
                    unused += r["policies"]["rehearsal/padded4"]["unused_new"]
    assert (
        len(pairs),
        sum(a for a, b in pairs),
        sum(b for a, b in pairs),
        pairs.count((True, True)),
        stable,
        unused,
    ) == (49, 40, 42, 39, 630, 2520)
    return out


def source_blobs(project, manifest):
    store = CACHE / "blobs"
    store.mkdir(exist_ok=True, parents=True)

    def get(item):
        digest, (rev, path) = item
        target = store / digest
        if target.exists():
            data = target.read_bytes()
        else:
            url = f"https://raw.githubusercontent.com/{project}/{rev}/{quote(path)}"
            for attempt in range(4):
                try:
                    with urlopen(url, timeout=45) as response:
                        data = response.read()
                    break
                except OSError:
                    if attempt == 3:
                        raise
                    time.sleep(2**attempt)
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"Input mismatch {project} {path}")
        if not target.exists():
            target.write_bytes(data)
        return digest, data.decode("utf-8-sig")

    with ThreadPoolExecutor(max_workers=8) as workers:
        return dict(workers.map(get, manifest["blobs"].items()))


def verify_compiled_fts(manifest, blobs):
    from observed import schema_only

    rev = "d44be0ecf14894cbe85a8c767f8edc1245ab38fe"
    path = "core/data/src/commonMain/sqldelight/databases/32.db"
    digest = "baeb35b528bf9b74d29b7804c9a20abfef298bf91c48a9aafa20eb228dc92c9a"
    assert rev == manifest["end"]
    raw = checked_file(
        CACHE,
        "twine-schema.db",
        f"https://raw.githubusercontent.com/msasikanth/twine/{rev}/{path}",
        digest,
    )
    compiled = apsw.Connection(":memory:")
    compiled.deserialize("main", raw)
    spec = manifest["events"][-1]["databases"]["core/data/ReaderDatabase"]
    actual = schema_only({p: blobs[d] for p, d in spec["files"].items()}, spec)
    actual.db.authorizer = None
    verified = {}
    for name in ("feed_search", "post_search"):

        def declaration(db):
            (sql,) = db.execute(
                "select sql from sqlite_schema where name=?", (name,)
            ).fetchone()
            return "".join(sql.lower().split()).split("usingfts5", 1)[1]

        expected = declaration(compiled)
        assert declaration(actual.db) == expected
        verified[name] = expected
    actual.db.close()
    compiled.close()
    return {"revision": rev, "path": path, "sha256": digest, "fts5": verified}


def run(out, dev_only):
    from test_migrations import regressions

    regressions()
    dev = development()
    dump(out / "development.json.gz", dict(protocol=PROTOCOL, series=dev))
    print(
        "Verified development gates, populated fixture and regression cases.",
        flush=True,
    )
    if dev_only:
        return
    from observed import evaluate_project

    inventory = json.loads(gzip.decompress((HERE / "manifest.json.gz").read_bytes()))
    assert inventory["protocol"] == PROTOCOL
    for project, manifest in sorted(inventory["projects"].items()):
        blobs = source_blobs(project, manifest)
        results = evaluate_project(project, manifest, blobs)
        if project == "msasikanth/twine":
            results["compiled_schema_witness"] = verify_compiled_fts(manifest, blobs)
        dump(
            out / (project.split("/")[1] + ".json.gz"),
            dict(protocol=PROTOCOL, **results),
        )
        print(
            project,
            len(results["transitions"]),
            "scored database transitions",
            flush=True,
        )

    from migration_summary import generate

    generate(out)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--dev-only", action="store_true")
    args = p.parse_args()
    run(args.out, args.dev_only)
