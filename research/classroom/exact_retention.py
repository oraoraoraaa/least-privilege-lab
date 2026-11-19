"""Exact sampling distribution for the archived classroom observed-only baseline."""
import argparse
import csv
import json
from collections import Counter
from fractions import Fraction
from math import comb
from pathlib import Path

POST = 'Action::"PostAssignment"'
EDIT = 'Action::"EditAssignment"'


def distribution(multiplicities, budget):
    """Count samples by (posting, editing) distinct tuples, weighting rows as distinguishable."""
    ways = Counter({(0, 0, 0): 1})
    for action, copies in multiplicities:
        if action not in (POST, EDIT) or copies < 1:
            raise ValueError("Expected a positive multiplicity for a registered assignment action")
        next_ways = Counter()
        for (used, post, edit), weight in ways.items():
            for take in range(min(copies, budget - used) + 1):
                new_post = post + int(take > 0 and action == POST)
                new_edit = edit + int(take > 0 and action == EDIT)
                next_ways[used + take, new_post, new_edit] += weight * comb(copies, take)
        ways = next_ways
    return {(post, edit): count for (used, post, edit), count in ways.items() if used == budget}


def table(path):
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file, delimiter="\t", quoting=csv.QUOTE_NONE))


def analyze(directory):
    events = table(directory / "events.tsv")
    scored = table(directory / "decisions.tsv")
    key_fields = ("principal", "action", "resource")
    def key(row):
        return tuple(row[field] for field in key_fields)

    ideal = {key(row) for row in scored if row["cedar_ideal"] == "1"}
    if any(row["decision"] != "ALLOW" or key(row) not in ideal for row in events):
        raise ValueError("This calculation assumes each training row exercises an intended permission")
    multiplicities = Counter(key(row) for row in events)
    n = len(events)
    budget = sum(row["action"] != POST for row in events)
    histogram = distribution([(action, m) for (_, action, _), m in multiplicities.items()], budget)
    total = comb(n, budget)
    if sum(histogram.values()) != total:
        raise ValueError("Joint histogram does not account for every sample")
    means = [Fraction(sum(pair[i] * weight for pair, weight in histogram.items()), total) for i in (0, 1)]

    # Independent expectation: each distinct tuple survives if at least one of its rows is kept.
    for i, target in enumerate((POST, EDIT)):
        mean = sum((1 - Fraction(comb(n - m, budget), total))
                   for (_, action, _), m in multiplicities.items() if action == target)
        if mean != means[i]:
            raise ValueError("Marginal expectation and dynamic program disagree")

    blocked_edit = len({key(row) for row in events if row["action"] == EDIT})
    below = sum(weight for (post, edit), weight in histogram.items() if post + edit <= blocked_edit)
    zero_post = sum(weight for (post, _), weight in histogram.items() if post == 0)
    return {
        "total_rows": n, "sample_rows": budget, "equally_likely_row_subsets": total,
        "expected_distinct_as_fractions": {POST: str(means[0]), EDIT: str(means[1]),
                                            "ALL": str(sum(means))},
        "subsets_with_zero_posting": zero_post,
        "structured_omission_distinct": blocked_edit,
        "subsets_with_total_at_or_below_structured_omission": below,
        "joint_counts": [{"post_distinct": p, "edit_distinct": e, "row_subsets": count}
                         for (p, e), count in sorted(histogram.items())],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, help="directory with replay decisions.tsv and events.tsv")
    print(json.dumps(analyze(parser.parse_args().results), indent=2, sort_keys=True))
