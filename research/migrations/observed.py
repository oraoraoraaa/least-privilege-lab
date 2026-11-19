"""Load production SQLDelight snapshots and evaluate adjacent database changes."""

from pathlib import Path
import re

import apsw
from application import LABEL, Query, Snapshot, strip_comments
from policy import assess, fit
from workloads import Instrument

# Shield quoted tokens while adapting SQLDelight collection and scalar binds.
TOKEN = re.compile(
    r"""'(?:''|[^'])*'|"(?:""|[^"])*"|\[[^\]]*\]|\?[0-9]*|[:@$][A-Za-z_]\w*"""
)
TYPE = re.compile(r"\b(INTEGER|TEXT|REAL|BLOB|INT)\s+AS\s+[\w.]+(?:<[\w., ?]+>)?", re.I)
WRITE = re.compile(r"^(?:INSERT|REPLACE|UPDATE|DELETE|PRAGMA)\b", re.I)
CREATE = re.compile(r"^CREATE\b", re.I)
EXPECTED = (apsw.Error, ValueError)


def statements(text):
    start = 0
    for m in re.finditer(";", text):
        if apsw.complete(text[start : m.end()]):
            yield text[start : m.end()].strip()
            start = m.end()
    if text[start:].strip():
        yield text[start:].strip()


def prepared(sql):
    parts = []
    bindings = {}
    end = 0
    for m in TOKEN.finditer(sql):
        parts.append(sql[end : m.start()])
        raw = m[0].strip()
        if raw[0] in "?$@:":
            name = "arg" + str(len(bindings))
            bindings[name] = 1
            # SQLDelight permits IN ? and IN :list without parentheses.
            is_list = re.search(r"\bIN\s*$", sql[: m.start()], re.I)
            parts.append("(:" + name + ")" if is_list else ":" + name)
        else:
            parts.append(m[0])
        end = m.end()
    return "".join(parts) + sql[end:], bindings


def native_ddl(sql):
    sql = TYPE.sub(r"\1", sql)
    if re.match(r"CREATE\s+VIRTUAL\s+TABLE\b", sql, re.I) and re.search(
        r"\bUSING\s+fts5\s*\(", sql, re.I
    ):
        sql = re.sub(
            r"(\b\w+)\s+(?:TEXT|INTEGER)\b(?:\s+(?:NOT NULL|PRIMARY KEY))*",
            r"\1",
            sql,
            flags=re.I,
        )
    return sql


def sections(files, *, ddl_only=False):
    ddl, queries, errors = [], {}, {}
    for path, text in sorted(files.items()):
        if not path.endswith(".sq"):
            continue
        family = Path(path).stem
        text = re.sub(r"(?m)^\s*import\s+[\w.]+;\s*$", "", strip_comments(text))
        text = re.sub(
            r"(?m)^(\w+)\((?:\w+\s*:\s*\w+(?:\s*,\s*)?)+\)\s*:\s*$", r"\1:", text
        )
        fields = LABEL.split(text)
        ddl.extend(native_ddl(stmt) for stmt in statements(fields[0]))
        for name, delimiter, body in zip(fields[1::3], fields[2::3], fields[3::3]):
            key = family + "." + name
            if delimiter == "{":
                # Multi-statement groups may return a read; keep ambiguous groups visible.
                if re.search(r"(?im)^\s*(SELECT|WITH)\b", body):
                    errors[key] = "mixed or grouped statement"
                continue
            seq = list(statements(body))
            if not seq:
                errors[key] = "empty statement"
                continue
            first, *trailing = seq
            for stmt in trailing:
                if CREATE.match(stmt):
                    ddl.append(native_ddl(stmt))
                else:
                    errors[key] = "unclassified trailing statement"
            if ddl_only or WRITE.match(first):
                continue
            if key in queries:
                raise ValueError("duplicate query identifier " + key)
            if not re.match(r"^(SELECT|WITH)\b", first, re.I):
                errors[key] = "unsupported statement form"
                continue
            sql, bindings = prepared(first)
            queries[key] = Query(family, sql, bindings)

    # SQLite resolves indexes and triggers at creation; install referenced tables first.
    def priority(sql):
        if re.match(r"CREATE\s+(VIRTUAL\s+)?TABLE", sql, re.I):
            return 0
        if re.match(r"CREATE\s+VIEW", sql, re.I):
            return 1
        return 2

    return "\n".join(sorted(ddl, key=priority)), queries, errors


def schema_only(files, spec):
    if spec["unsupported"]:
        raise ValueError(spec["unsupported"])
    if spec["migration_schema"]:
        raise ValueError("schema derived from migration scripts")
    if not any(p.endswith(".sq") for p in files):
        raise ValueError("no declarative .sq files")
    # Parse only for DDL and statement boundaries. Predictor receives just this database.
    ddl, _, _ = sections(files, ddl_only=True)
    return Instrument(ddl, include_views=True)


def snapshot(files, db):
    _, queries, errors = sections(files)
    reads, resolved = {}, {}
    for name, q in queries.items():
        if name in errors:
            continue
        try:
            ok, trace = db.execute(q.sql, bindings=q.bindings)
            if not ok:
                raise ValueError("unrestricted read denied")
            reads[name], resolved[name] = trace, q
        except EXPECTED as exc:
            errors[name] = str(exc)
    return Snapshot(db, resolved, reads, {}, set()), errors


def evaluate_project(project, manifest, blobs):
    states, ledger, transitions = {}, [], []
    for event in manifest["events"]:
        revision = event["revision"]
        for key in sorted(states.keys() - event["databases"].keys()):
            previous = states.pop(key)
            ledger.append(
                dict(
                    revision=revision,
                    database=key,
                    status="database_departure",
                    names=sorted(previous["names"]),
                )
            )
            if previous["snap"]:
                previous["snap"].db.db.close()
        for key, spec in sorted(event["databases"].items()):
            signature = (spec["files"], spec["block"], spec["unsupported"])
            prev = states.get(key)
            if prev and prev["signature"] == signature:
                continue
            files = {p: blobs[d] for p, d in spec["files"].items()}
            problems = {}
            current = None
            try:
                planned = schema_only(files, spec)
            except EXPECTED as exc:
                problems["<schema>"] = str(exc)
            else:
                if prev and prev["snap"]:
                    fitted = fit(prev["snap"], planned)
                current, problems = snapshot(files, planned)
            names = set(current.queries if current else ()) | {
                n for n in problems if n != "<schema>"
            }
            state = dict(
                revision=revision,
                database=key,
                status="catalog" if current else "unsupported",
                supported=len(current.queries) if current else 0,
                errors=problems,
            )
            if not prev:
                state["first_catalog_names"] = sorted(names)
            ledger.append(state)
            if prev and prev["snap"] and current:
                r = assess(prev["snap"], current, fitted)
                r["introduced"] = sorted(names - prev["names"])
                r["retired"] = sorted(prev["names"] - names)
                r["unscored_survivors"] = sorted(
                    (prev["names"] & names) - r["rows"].keys()
                )
                r.update(
                    database=key,
                    old=prev["revision"],
                    new=revision,
                    complete=not (prev["errors"] or problems),
                )
                transitions.append(r)
            if prev and prev["snap"]:
                prev["snap"].db.db.close()
            states[key] = dict(
                snap=current,
                errors=problems,
                signature=signature,
                revision=revision,
                names=names,
            )
    for state in states.values():
        if state["snap"]:
            state["snap"].db.db.close()
    return dict(project=project, ledger=ledger, transitions=transitions)
