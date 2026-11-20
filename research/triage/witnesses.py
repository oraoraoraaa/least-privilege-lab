"""Verify shipped JVM SQL and the maintained Android export projection."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from base64 import b64decode

from discover import CACHE, HERE, download
from fresh import schema_only, snapshot
from inventory import dump

SPEC = {"unsupported": None, "migration_schema": False}


def inputs():
    records = json.loads((HERE / "case-inputs.json").read_text())
    folder = CACHE / "case-files"
    folder.mkdir(parents=True, exist_ok=True)

    def get(item):
        name, record = item
        dest = folder / name
        data = dest.read_bytes() if dest.exists() else download(record["url"])
        if sha256(data).hexdigest() != record["sha256"]:
            raise ValueError(name)
        if not dest.exists():
            dest.write_bytes(data)
        return name, dest

    with ThreadPoolExecutor(8) as pool:
        return dict(pool.map(get, records.items()))


def class_queries(paths, version):
    cp = os.pathsep.join(
        str(paths[k])
        for k in ["zipline-" + version + ".jar", "runtime-jvm.jar", "kotlin-stdlib.jar"]
    )
    with TemporaryDirectory() as temp:
        subprocess.run(
            ["javac", "-cp", cp, "-d", temp, str(HERE / "ReleaseQueries.java")],
            check=True,
        )
        output = subprocess.check_output(
            [
                "java",
                "-cp",
                temp + os.pathsep + cp,
                "app.cash.zipline.loader.internal.cache.ziplineloader.ReleaseQueries",
            ],
            text=True,
        )
    result = {}
    for line in output.splitlines():
        name, encoded, params = line.split("\t")
        values = []
        for arg in params.split(",") if params else ():
            values.append(
                None
                if arg == "N"
                else int(arg[1:])
                if arg[0] == "I"
                else b64decode(arg[1:]).decode()
            )
        result[name] = (b64decode(encoded).decode(), values)
    return result


def zipline(paths, version):
    files = {p: paths[version + "-" + p].read_text() for p in ("Files.sq", "Pins.sq")}
    db = schema_only(files, SPEC)
    snap, errors = snapshot(files, db)
    compiled = class_queries(paths, version)
    rows = {}
    for shape, (sql, args) in compiled.items():
        q = shape.split("/")[0]
        literal = sql
        _, reads = db.execute(sql, bindings=args)
        source = snap.reads.get(q)
        # Install the candidate from source and also test each single omitted resource.
        allow = (
            db.execute(sql, source, bindings=args)[0] if source is not None else None
        )
        required = [
            f
            for f in sorted(reads)
            if not db.execute(sql, reads - {f}, bindings=args)[0]
        ]
        assert set(required) == reads
        rows[shape] = dict(
            bindings=args,
            literal=literal,
            literal_sha256=sha256(literal.encode()).hexdigest(),
            reads=sorted(reads),
            source=sorted(source) if source is not None else None,
            admitted_by_source=allow,
        )
    db.db.close()
    return dict(
        source_names=sorted(snap.reads),
        unmapped=sorted(snap.queries.keys() - {k.split("/")[0] for k in compiled}),
        errors=errors,
        methods=rows,
    )


def projection(paths, description, note):
    writer = paths["WalletPaymentCsvWriter.kt"].read_text()
    match = re.search(
        r'(if \(configuration.includesDescription\) listOf\(.*?else "")\s*,',
        writer,
        re.S,
    )
    if not match:
        raise ValueError("Unknown writer projection")
    # Compile the exact released expression. Supply only its input properties in the harness.
    template = """
data class Configuration(val includesDescription: Boolean, val includesNotes: Boolean)
data class Details(val description: String?)
data class Metadata(val userDescription: String?, val userNotes: String?, val lnurl: Lnurl?)
data class Lnurl(val pay: Pay?)
data class Pay(val metadata: Extra?)
data class Extra(val longDesc: String?)
fun project(configuration: Configuration, details: Details, metadata: Metadata?): String =
EXPRESSION
fun main(args: Array<String>) {
    val enabled = args[0].toBooleanStrict()
    print(project(Configuration(enabled, enabled), Details(null), Metadata(args[1], args[2], null)))
}
"""
    jars = [
        str(p)
        for n, p in paths.items()
        if n.endswith(".jar")
        and not n.startswith("zipline-")
        and n != "runtime-jvm.jar"
    ]
    with TemporaryDirectory() as temp:
        src = Path(temp) / "Projection.kt"
        src.write_text(template.replace("EXPRESSION", match[1]))
        cp = str(paths["kotlin-stdlib.jar"])
        subprocess.run(
            [
                "java",
                "-cp",
                os.pathsep.join(sorted(jars)),
                "org.jetbrains.kotlin.cli.jvm.K2JVMCompiler",
                "-no-stdlib",
                "-no-reflect",
                "-jvm-target",
                "17",
                "-classpath",
                cp,
                "-d",
                temp,
                str(src),
            ],
            check=True,
        )
        outputs = {}
        for enabled in ("false", "true"):
            rendered = subprocess.check_output(
                [
                    "java",
                    "-cp",
                    temp + os.pathsep + cp,
                    "ProjectionKt",
                    enabled,
                    description,
                    note,
                ],
                text=True,
            )
            assert (note in rendered) == (enabled == "true") and (
                description in rendered
            ) == (enabled == "true")
            outputs[enabled] = rendered
    return {
        "outputs": outputs,
        "expression_sha256": sha256(match[1].encode()).hexdigest(),
    }


def phoenix(paths):
    contracts = {
        "PaymentsExportView.kt": [
            "vm.includesDescription = it",
            "vm.includesNotes = it",
        ],
        "PaymentsExportViewModel.kt": [
            "includesNotes = includesNotes",
            "dbManager.paymentsDb().listCompletedPayments(",
            "csvWriter.add(it.payment, it.metadata)",
        ],
        "SqlitePaymentsDb.kt": [
            "database.paymentsQueries.listSuccessful(",
            "user_notes = user_notes",
        ],
        "CsvWriterTests.kt": ["includesNotes = true", "assertEquals(expected, actual)"],
    }
    for file, markers in contracts.items():
        for marker in markers:
            assert marker in paths[file].read_text(), (file, marker)
    files = {
        name.removeprefix("phoenix-"): p.read_text()
        for name, p in paths.items()
        if name.startswith("phoenix-")
    }
    db = schema_only(files, SPEC)
    snap, _ = snapshot(files, db)
    q = snap.queries["Payments.listSuccessful"]
    data = db.db
    data.authorizer = None
    data.execute(
        "INSERT INTO payments_incoming(id,created_at,received_at,data) VALUES(x'01',1,2,x'42')"
    )
    data.execute(
        "INSERT INTO payments_metadata(payment_id,user_description,user_notes) VALUES(x'01','fixture description','fixture note')"
    )
    data.authorizer = db._authorize
    bindings = dict(zip(q.bindings, [0, 3, 32, 0], strict=True))
    cur = data.execute(q.sql, bindings, can_cache=False)
    names = [c[0] for c in cur.description]
    (row,) = cur.fetchall()
    values = dict(zip(names, row, strict=True))
    reads = snap.reads["Payments.listSuccessful"]
    field = "payments_metadata.user_notes"
    assert (
        field in reads and not db.execute(q.sql, reads - {field}, bindings=bindings)[0]
    )
    assert db.execute(q.sql, reads, bindings=bindings)[0]
    out = projection(paths, values["user_description"], values["user_notes"])
    db.db.close()
    return dict(
        android_tag="android-v2.6.2",
        caller="Payments.listSuccessful",
        db_reads=sorted(reads),
        admitted_with_notes=True,
        admitted_without_notes=False,
        **out,
    )


def main(out):
    paths = inputs()
    import gzip

    feed = json.loads(
        gzip.decompress(
            (HERE.parent / "migrations/results/feed-flow.json.gz").read_bytes()
        )
    )
    dates = [
        "4916711df767bef323740134d66b1ce141258edd",
        "379e6ad8338023226c7a5113e78d9325d3702e0d",
    ]
    name = "FeedItem.countUnreadFeeds"
    history = []
    for rev in dates:
        (step,) = [t for t in feed["transitions"] if t["new"] == rev]
        row = step["rows"][name]
        history.append(
            dict(
                revision=rev,
                old=step["old"],
                query=name,
                edited=row["edited"],
                target=row["missing"],
                predictions=step["predictions"][name],
            )
        )
    result = dict(
        design_history=history,
        zipline={v: zipline(paths, v) for v in ("1.1.0", "1.2.0")},
        phoenix=phoenix(paths),
    )
    dump(out, result)
    for v, r in result["zipline"].items():
        print(v, len(r["methods"]), r["unmapped"], r["errors"])
    print("Android CSV projection", result["phoenix"]["outputs"])


if __name__ == "__main__":
    main(Path(sys.argv[1]))
