"""Forward-only replay of named read programs on the corresponding Tivi schemas."""
from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
from statistics import fmean

import apsw
from evaluate import deploy, rankings
from selection import ordered_candidates, tokens
from workloads import Instrument


@dataclass
class Query:
    family: str
    sql: str
    bindings: dict

    @property
    def digest(self):
        return sha256(self.sql.encode()).hexdigest()


@dataclass
class Snapshot:
    db: Instrument
    queries: dict
    reads: dict
    inventory: dict


def strip_comments(text):
    return re.sub(r"'(?:''|[^'])*'|--[^\n]*|/\*.*?\*/",
                  lambda m: m[0] if m[0].startswith("'") else " ", text, flags=re.S)


def load_snapshot(files):
    ddl, queries = [], {}
    inventory = Counter()
    for path, source in sorted(files.items()):
        family = Path(path).stem
        sections = re.split(r"^\s*([A-Za-z_]\w*)\s*:\s*$",strip_comments(source),flags=re.M)
        schema = re.sub(r"\b(INTEGER|TEXT|REAL|BLOB)\s+AS\s+[\w.]+",r"\1",sections[0],flags=re.I)
        ddl.append(schema)
        for name, statement in zip(sections[1::2],sections[2::2]):
            sql = statement.strip()
            op = sql.split()[0].upper()
            inventory[op] += 1
            if op in ("DELETE","INSERT","UPDATE"):
                continue
            if op not in ("SELECT","WITH") or sql.count(";") != 1 or not sql.endswith(";"):
                raise ValueError(f"Unclassified statement {path} {name}")
            sql = re.sub(r"\bIN\s+(:\w+)",r"IN (\1)",sql,flags=re.I)
            # Ignore literal colons, e.g. timestamps in expressions.
            params = re.findall(r":([a-zA-Z_]\w*)",re.sub(r"'(?:''|[^'])*'", "", sql))
            key = family+"."+name
            if key in queries:
                raise ValueError(f"Duplicate query ID {key}")
            queries[key] = Query(family,sql,dict.fromkeys(params,1))
    db = Instrument("\n".join(ddl),include_views=True)
    reads = {}
    for q,query in queries.items():
        ok, reads[q] = db.execute(query.sql,bindings=query.bindings)
        if not ok:
            raise ValueError(f"Reference denied for {q}")
    return Snapshot(db, queries, reads, dict(inventory))


def fit_catalog(old):
    families = defaultdict(list)
    for q, query in old.queries.items():
        families[query.family].append(q)
    vocabulary = {q:tokens(query.sql) for q,query in old.queries.items()}
    fitted = {}
    for family, ids in sorted(families.items()):
        frequency = Counter(c for q, resources in old.reads.items() if old.queries[q].family != family for c in resources)
        for o in ids:
            observed = old.reads[o]
            candidates = ordered_candidates(o,(q for q in ids if q != o),vocabulary)
            base = rankings(old.db.universe,observed,set(),frequency,o)["table_freq"]
            policies = {}
            for donor in candidates:
                order = rankings(old.db.universe,observed,old.reads[donor],frequency,o)["sibling"]
                policies[donor] = deploy(order,observed,4)
            fitted[o] = (frequency,candidates,deploy(base,observed,4),policies)
    return fitted


def rehearse(old, db, fitted):
    """This step receives the next schema and old query text only."""
    prepared = {}
    for q,query in old.queries.items():
        err = None
        try:
            _, preview = db.execute(query.sql,bindings=query.bindings)
        except apsw.SQLError as exc:
            preview, err = frozenset(), str(exc)
        observed = old.reads[q] & db.universe
        orders = rankings(db.universe,observed,preview,fitted[q][0],q)
        prepared[q] = (preview,err,deploy(orders["table_freq"],observed,4),
                       deploy(orders["sibling"],observed,4),observed|preview)
    return prepared


def transition(old,new):
    fitted = fit_catalog(old)
    prepared = rehearse(old,new.db,fitted)
    surviving = sorted(old.queries.keys() & new.queries.keys())
    native_count = 0
    outcomes = []
    for q in surviving:
        actual = new.queries[q]
        hidden = new.reads[q]
        observed = old.reads[q]
        _,candidates,base,catalog = fitted[q]
        preview,err,schema_base,replay,literal = prepared[q]
        policies = {"observed":observed, "baseline":base, "near":catalog[candidates[0]] if candidates else base,
                    "schema_baseline":schema_base, "rehearsal":replay,"literal":literal}
        # Each candidate and each named policy goes through the authorizer.
        def enforce(policy):
            nonlocal native_count
            ok,_ = new.db.execute(actual.sql,policy,bindings=actual.bindings)
            native_count += 1
            if ok != (hidden <= policy):
                raise ValueError(f"Set/native disagreement for {q}")
            return int(ok)
        scores = {method:enforce(policy) for method,policy in policies.items()}
        donor_scores = {d:enforce(policy) for d,policy in catalog.items()}
        scores["random"] = fmean(donor_scores.values()) if candidates else scores["baseline"]
        scores["best"] = max(donor_scores.values()) if candidates else scores["baseline"]
        missing = hidden-observed
        if not missing:
            cause = "already_covered"
        elif missing-old.db.universe:
            cause = "absent_from_old_schema"
        elif len(missing)>4:
            cause = "over_budget"
        else:
            cause = "feasible"
        outcomes.append({"query":q,"old_digest":old.queries[q].digest,"new_digest":actual.digest,
                         "missing":sorted(missing),"outside_old_schema":sorted(missing-old.db.universe),
                         "class":cause,"nearest":candidates[0] if candidates else None,
                         "candidate_outcomes":donor_scores,"scores":scores,
                         "rehearsal_missing_recovered":sorted(preview & missing),"rehearsal_error":err,
                         "rehearsal_reads":sorted(preview),
                         "unused_additions":{m:len((p & new.db.universe) - observed - hidden) for m,p in policies.items()},
                         "added_grants":{m:sorted(p-observed) for m,p in policies.items()}})
    return {"new_names":sorted(new.queries.keys()-old.queries.keys()),"retired_names":sorted(old.queries.keys()-new.queries.keys()),
            "native_decisions":native_count,"outcomes":outcomes}


def aggregate(transitions):
    records=[row for t in transitions for row in t["outcomes"]]
    info=[r for r in records if r["missing"]]
    def score(rows):
        return {m:sum(r["scores"][m] for r in rows) for m in records[0]["scores"]}
    return {"surviving":len(records),"informative":len(info),"all_success_counts":score(records),
            "informative_success_counts":score(info),"causes":dict(Counter(r["class"] for r in records)),
            "informative_ids":sorted({r["query"] for r in info}),
            "informative_same_text":sum(r["old_digest"] == r["new_digest"] for r in info),
            "missing_rehearsals":sum(r["rehearsal_error"] is not None for r in records),
            "no_candidate":sum(r["nearest"] is None for r in records),
            "new_names":sum(len(t["new_names"]) for t in transitions),
            "retired_names":sum(len(t["retired_names"]) for t in transitions),
            "native_decisions":sum(t["native_decisions"] for t in transitions)}
