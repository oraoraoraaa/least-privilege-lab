"""Diagnose which migration alerts require more than old column coverage."""
from collections import defaultdict


def coverage_alerts(old_schema, next_schema, old_reads):
    """Use only the two resource catalogs and previously measured footprints."""
    columns = defaultdict(set)
    for resource in old_schema:
        relation, column = resource.rsplit(".", 1)
        if column != "@row":
            columns[relation].add(resource)
    growing = set()
    for resource in next_schema - old_schema:
        relation, column = resource.rsplit(".", 1)
        if column != "@row" and relation in columns:
            growing.add(relation)
    alerts = {}
    for name, reads in old_reads.items():
        removed = sorted(reads - next_schema)
        full = sorted(relation for relation in growing if columns[relation] <= reads)
        if removed or full:
            alerts[name] = {"removed_reads": removed, "growing_full_relations": full}
    return alerts


def compare_series(snapshots, transitions):
    rows = []
    for old, new, outcome in zip(snapshots[:-1], snapshots[1:], transitions, strict=True):
        assert (old["cutoff"], new["cutoff"]) == (outcome["old"], outcome["new"])
        reads = {q: set(v["reads"]) for q, v in old["queries"].items()}
        flagged = set(coverage_alerts(set(old["universe"]), set(new["universe"]), reads))
        rehearsal = set(outcome["review"]["alerts"])
        expanded = {r["query"] for r in outcome["outcomes"] if r["missing"]}
        retired = set(outcome["retired_names"])
        stable = reads.keys() - expanded - retired
        rows.append({"old": old["cutoff"], "new": new["cutoff"], "old_names": len(reads),
                     "flagged_expanded": sorted(flagged & expanded),
                     "missed_expanded": sorted(expanded - flagged),
                     "flagged_stable": sorted(flagged & stable),
                     "flagged_retired": sorted(flagged & retired),
                     "only_coverage": sorted(flagged - rehearsal),
                     "only_rehearsal": sorted(rehearsal - flagged)})
    return rows
