"""Canonical descriptive totals with explicit eligibility, denominators and paired outcomes."""

from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path

from inventory import PROTOCOL, dump

METHODS = ("diff", "coverage", "source", "rehearsal")


def read(p):
    return json.loads(gzip.decompress(p.read_bytes()))


def counts(transitions):
    n, pairs = Counter(), Counter()
    fields, shared, unit = (defaultdict(Counter) for _ in range(3))
    discordant = []
    mechanisms = defaultdict(Counter)
    for t in transitions:
        n.update(
            transitions=1,
            complete=int(t["complete"]),
            survivors=len(t["rows"]),
            introductions=len(t["introduced"]),
            retirements=len(t["retired"]),
            unsupported_survivors=len(t.get("unscored_survivors", [])),
            native=t["native"],
        )
        introduced, retired = set(t["introduced"]), set(t["retired"])
        schema = set(t["schema_added"])
        clusters = defaultdict(list)
        for q, r in t["rows"].items():
            needed = set(r["missing"])
            if needed:
                n["expanded"] += 1
                n["edited_expanded"] += r["edited"]
                additions = needed & schema
                mechanism = ("edited" if r["edited"] else "unchanged") + (
                    "_new_resource" if additions else "_existing_only"
                )
                mechanisms[mechanism]["expanded"] += 1
                for key in additions:
                    clusters[key].append(q)
            predictions = t["predictions"][q]
            success = {}
            for m in METHODS:
                pred = predictions[m]
                added = set(pred["added"])
                f = fields[m]
                f["required_instances"] += len(needed)
                f["missing_instances"] += len(needed - added)
                f["extra_instances"] += len(added - needed)
                if needed:
                    success[m] = needed == added
                    f["exact"] += success[m]
                    f["flag_expanded"] += pred["flag"]
                    f["missed_expansions"] += not pred["flag"]
                    mechanisms[mechanism][m] += success[m]
                else:
                    f["flag_stable"] += pred["flag"]
            if needed:
                a, b = success["coverage"], success["rehearsal"]
                pairs[
                    (
                        "both"
                        if a and b
                        else "coverage_only"
                        if a
                        else "rehearsal_only"
                        if b
                        else "neither"
                    )
                ] += 1
                if a != b:
                    discordant.append(
                        {
                            "new": t["new"],
                            "database": t["database"],
                            "query": q,
                            "exact": "coverage" if a else "rehearsal",
                            "missing": r["missing"],
                        }
                    )
            for m, p in r["policies"].items():
                unit[m].update(
                    queries=1,
                    admitted=int(not p["denied"]),
                    unused_new=p["unused_new"],
                    unused_old=p["unused_old"],
                )
        for q, methods in t["predictions"].items():
            for m, p in methods.items():
                fields[m]["queue"] += p["flag"]
                fields[m]["retired_alerts"] += q in retired and p["flag"]
                fields[m]["diagnostics"] += bool(p["error"])
        n["changed_field_clusters"] += len(clusters)
        if t["complete"]:
            for m, p in t["shared"].items():
                denied = set(p["denied"])
                new_count = len(t["next_reads"])
                shared[m].update(
                    queries=new_count,
                    admitted=new_count - len(denied),
                    survivor_total=new_count - len(introduced),
                    survivor_admitted=new_count
                    - len(introduced)
                    - len(denied - introduced),
                    introduced_total=len(introduced),
                    introduced_admitted=len(introduced - denied),
                    unused_new=p["unused_new"],
                    unused_old=p["unused_old"],
                )
    return dict(
        counts=n,
        paired=pairs,
        methods=fields,
        shared=shared,
        individual=unit,
        discordances=discordant,
        mechanisms=mechanisms,
    )


def generate(folder):
    dev = read(folder / "development.json.gz")["series"]
    projects = {}
    all_rows = []
    migrations = []
    for path in sorted(folder.glob("*.json.gz")):
        if path.name in ("development.json.gz", "by-transition.json.gz"):
            continue
        entry = read(path)
        eligible = [
            t for t in entry["transitions"] if "/generator/" not in t["database"]
        ]
        project = entry["project"]
        projects[project] = counts(eligible)
        projects[project]["coverage"] = dict(
            database_states=len(entry["ledger"]),
            build_tool_transitions=len(entry["transitions"]) - len(eligible),
            first_catalog_names=sum(
                len(s.get("first_catalog_names", [])) for s in entry["ledger"]
            ),
            departing_catalog_names=sum(
                len(s.get("names", [])) for s in entry["ledger"]
            ),
            errors=dict(
                Counter(
                    err for s in entry["ledger"] for err in s.get("errors", {}).values()
                )
            ),
        )
        all_rows.extend(eligible)
        for t in eligible:
            clusters = defaultdict(list)
            for q, r in t["rows"].items():
                for field in sorted(set(r["missing"]) & set(t["schema_added"])):
                    clusters[field].append(q)
            migrations.append(
                dict(
                    project=project,
                    database=t["database"],
                    old=t["old"],
                    new=t["new"],
                    changed_resource_queries=clusters,
                    **counts([t]),
                )
            )
    out = dict(
        protocol=PROTOCOL,
        development={p: counts(dev[p]) for p in ("Tivi", "Mihon")},
        held_out=projects,
        pooled=counts(all_rows),
        complete_catalog_sensitivity=counts([t for t in all_rows if t["complete"]]),
    )
    (folder / "summary.json").write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n"
    )
    dump(
        folder / "by-transition.json.gz",
        dict(protocol=PROTOCOL, transitions=migrations),
    )


if __name__ == "__main__":
    import sys

    generate(Path(sys.argv[1]))
