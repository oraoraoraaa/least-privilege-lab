"""Manuscript tables computed directly from per-query and per-database evidence."""

from collections import Counter
import gzip
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "research/triage/results"


def read(name):
    return json.loads(gzip.decompress((RESULTS / name).read_bytes()))


def build(write_table):
    studies = read("fresh.json.gz")
    rows = []
    total = Counter()
    keys = (
        "steps",
        "old",
        "selected",
        "list_disagreements",
        "full_errors",
        "expansions",
        "diff_exact",
        "selective_exact",
        "rehearsal_exact",
    )
    for project, label in (
        ("ACINQ/phoenix", "Phoenix"),
        ("saket/press", "Press"),
        ("cashapp/zipline", "Zipline"),
    ):
        counts = studies[project]["counts"]
        total.update(counts)
        rows.append([label, *[counts.get(k, 0) for k in keys]])
    write_table("freshtriage", rows + [["All", *[total[k] for k in keys]]])
    audit = read("audit.json.gz")
    rows = []
    for method, label in (
        ("retain", "Retain old"),
        ("coverage/all", "Full coverage"),
        ("diff/all", "Table diff"),
        ("rehearsal/all", "Rehearsal"),
        ("diff/padded4", "Padded diff"),
    ):
        row = [label]
        for group in ("original", "recovered"):
            sums = Counter()
            for p in audit["projects"].values():
                for t in p[group]:
                    record = t["outcomes"][method]
                    sums.update({k: v for k, v in record.items() if isinstance(v, int)})
            row.extend(f"{sums[k]:,}" for k in ("admitted", "all_admitted", "unused"))
        rows.append(row)
    write_table("upgradecosts", rows)
