# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["cedarpy==4.12.2"]
# ///
"""Replay the pinned classroom assignment policies and score exact observed grants."""
import argparse
import csv
import errno
import hashlib
import io
import itertools
import json
import random
import subprocess
import tempfile
from collections import Counter
from importlib.metadata import version
from pathlib import Path

import cedarpy

ROOT = Path(__file__).resolve().parents[2]
REVISION = "35331c1259d1c04f4f453aab60e9f3f338d9d544"
FILES = {
    "gclassroom.schema.json": "517b907120b3818f6012a23406a88880582425a47dc6be495d8aac06d0e80ab5",
    "gclass_entities.60.json": "d317ea90d0a880ef7320e652bf931d9f27501e5918296938a411bf980f38f303",
    "gclass_logs.60.json": "909fbf34c3709c0291b78b003553a341362d512b90c4b1c1fa1c7f02e3fd2e8d",
    "gclassroom_policies.cedar": "5b2f208c5381328fe96adb25de3c8f58bf07b1f17ba73dc21b9de7a5a39fd249",
    "cedar-restrict-case-studies/assets/GClassroom/policies.ideal.cedar":
        "b7da785d3059f2bc93f49c9b65d43c198a898a87f6f2d6646366b7e53e249511",
}
IDEAL = "cedar-restrict-case-studies/assets/GClassroom/policies.ideal.cedar"
POST = 'Action::"PostAssignment"'
EDIT = 'Action::"EditAssignment"'
ACTIONS = (POST, EDIT)
TRIPLE = ("principal", "action", "resource")


def load_inputs(repo):
    inputs = {}
    for filename, digest in FILES.items():
        data = subprocess.check_output(["git", "-C", repo, "show", f"{REVISION}:{filename}"])
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"Unexpected content for {filename}")
        inputs[filename] = data.decode("utf-8")
    return inputs


def uid(reference):
    entity = reference["__entity"]
    return entity["type"] + "::" + json.dumps(entity["id"], ensure_ascii=False)


def project_entities(entities):
    staff, assignments, courses = set(), {}, set()
    memberships = set()
    for entity in entities:
        name = uid(entity["uid"])
        kind = entity["uid"]["__entity"]["type"]
        if kind == "Staff":
            staff.add(name)
            memberships.update((name, uid(parent)) for parent in entity["parents"])
        elif kind == "Assignment":
            assignments[name] = uid(entity["attrs"]["course"])
        elif kind == "Course":
            if entity["parents"]:
                raise ValueError("The direct-membership projection requires flat courses")
            courses.add(name)
    if not (set(assignments.values()) | {g for _, g in memberships}) <= courses:
        raise ValueError("The projection references an entity outside the course inventory")
    universe = sorted(itertools.product(staff, ACTIONS, assignments))
    rules = sorted((group, action, resource) for resource, group in assignments.items()
                   for action in ACTIONS)
    return universe, sorted(memberships), rules


def write_tsv(path, header, rows):
    # Typed Cedar IDs contain double quotes. The Java format uses literal TSV fields.
    with path.open("w", encoding="utf-8", newline="") as out:
        for row in itertools.chain([header], rows):
            fields = [str(value) for value in row]
            if any(any(c in value for c in "\t\r\n") for value in fields):
                raise ValueError(f"Unsupported delimiter in fields: {fields}")
            out.write("\t".join(fields) + "\n")


def java_grants(directory, memberships, rules):
    member_file, rule_file = directory / "members.tsv", directory / "group_grants.tsv"
    write_tsv(member_file, ("principal", "group"), memberships)
    write_tsv(rule_file, ("group", "action", "resource"), rules)
    text = subprocess.check_output(
        ["java", "-jar", ROOT / "build/least-privilege-lab.jar",
         "group-grants", member_file, rule_file], encoding="utf-8")
    rows = csv.reader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE)
    if tuple(next(rows)) != TRIPLE:
        raise ValueError("Unexpected Java snapshot header")
    return {tuple(row) for row in rows}


def cedar_grants(universe, policy, entities, schema):
    requests = [dict(zip(TRIPLE, key), context={}) for key in universe]
    results = cedarpy.is_authorized_batch(requests, policy, entities, schema=schema)
    grants = set()
    for key, decision in zip(universe, results, strict=True):
        if decision.diagnostics.errors:
            raise ValueError(f"Cedar diagnostic at {key}: {decision.diagnostics.errors}")
        if decision.allowed:
            grants.add(key)
    return grants


def scoped_events(log, domain, loose):
    events = []
    for index, row in enumerate(log):
        request = row["request"]
        if request["action"] not in ACTIONS:
            continue
        key = tuple(request[field] for field in TRIPLE)
        if request["context"] or key not in domain:
            raise ValueError(f"Unaccounted assignment request at source index {index}")
        if row["result"] != ("ALLOW" if key in loose else "DENY"):
            raise ValueError(f"Log and original policy disagree at source index {index}")
        events.append((index, key, row["result"]))
    return events


def observed_policy(sample, loose):
    return loose & {key for _, key, decision in sample if decision == "ALLOW"}


def replay(directory, scratch, inputs):
    entities = json.loads(inputs["gclass_entities.60.json"])
    schema = json.loads(inputs["gclassroom.schema.json"])
    log = json.loads(inputs["gclass_logs.60.json"])
    universe, memberships, rules = project_entities(entities)
    domain = set(universe)
    loose = cedar_grants(universe, inputs["gclassroom_policies.cedar"], entities, schema)
    actual = java_grants(scratch, memberships, rules)
    differences = sorted(actual ^ loose)
    if differences:
        raise ValueError(f"Java/Cedar disagreement on {len(differences)} tuples; first: {differences[0]}")

    ideal = cedar_grants(universe, inputs[IDEAL], entities, schema)
    if not ideal <= loose:
        raise ValueError("The intended policy grants requests outside the starting policy")
    # A second Java run deliberately omits an active membership to test mismatch detection.
    active_groups = {group for group, _, _ in rules}
    omitted = next(edge for edge in memberships if edge[1] in active_groups)
    mutant = java_grants(scratch, [edge for edge in memberships if edge != omitted], rules)
    witness = sorted(mutant ^ loose)
    if not witness:
        raise ValueError("Negative control failed to expose the omitted membership")

    events = scoped_events(log, domain, loose)
    counts = Counter(key for _, key, _ in events)
    write_tsv(directory / "decisions.tsv", (*TRIPLE, "java_loose", "cedar_loose", "cedar_ideal", "logged_events"),
              [(*key, int(key in actual), int(key in loose), int(key in ideal), counts[key]) for key in universe])
    write_tsv(directory / "events.tsv", ("source_index", *TRIPLE, "decision"),
              [(index, *key, decision) for index, key, decision in events])

    retained = [event for event in events if event[1][1] != POST]
    conditions = [("original", "-", [], loose),
                  ("full_log", "-", events, observed_policy(events, loose)),
                  ("omit_post", "-", retained, observed_policy(retained, loose))]
    for seed in range(30):
        sample = random.Random(seed).sample(events, len(retained))
        conditions.append(("random_drop", seed, sample, observed_policy(sample, loose)))

    scores = []
    for condition, seed, sample, grants in conditions:
        selection = ",".join(str(i) for i, _, _ in sorted(sample)) or "-"
        for action in (*ACTIONS, "ALL"):
            relevant = domain if action == "ALL" else {key for key in domain if key[1] == action}
            legitimate, excess = ideal & relevant, (loose - ideal) & relevant
            scores.append((condition, seed, action, len(sample), len(relevant & grants),
                           len(legitimate & grants), len(legitimate), len(excess - grants),
                           len(excess), selection))
    write_tsv(directory / "runs.tsv",
              ("condition", "seed", "scope", "training_events_total", "effective_grants",
               "legitimate_retained", "legitimate_total", "excess_removed", "excess_total",
               "training_source_indices"), scores)
    summary = {
        "artifact_revision": REVISION, "input_sha256": FILES, "cedarpy_version": version("cedarpy"),
        "domain": len(domain), "java_cedar_mismatches": len(differences),
        "loose_grants": len(loose), "intended_grants": len(ideal),
        "source_rows": len(log), "scoped_rows": len(events), "distinct_scoped_tuples": len(counts),
        "control": {"omitted_membership": omitted, "changed_decisions": len(witness),
                    "first_difference": witness[0], "original_allow": witness[0] in loose,
                    "mutant_allow": witness[0] in mutant},
    }
    (directory / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path, help="Git checkout containing the pinned object")
    parser.add_argument("--output", type=Path, default=ROOT / "build/classroom")
    args = parser.parse_args()
    inputs = load_inputs(args.artifact)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as temporary:
        scratch = Path(temporary)
        results = scratch / "results"
        results.mkdir()
        summary = replay(results, scratch, inputs)
        try:
            results.rename(args.output)
        except OSError as error:
            if error.errno not in (errno.ENOTEMPTY, errno.EEXIST):
                raise
            # An existing run is immutable. Allow an identical repeat, including parallel runs.
            if (set(p.name for p in results.iterdir()) != set(p.name for p in args.output.iterdir())
                    or any(p.read_bytes() != (args.output / p.name).read_bytes() for p in results.iterdir())):
                raise ValueError(f"Different results already exist at {args.output}; choose a fresh --output") from error
    print(f"{summary['domain']} decisions compared; {summary['java_cedar_mismatches']} mismatches.")
    print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()
