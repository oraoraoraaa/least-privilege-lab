# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["z3-solver==5.4.1.0"]
# ///
"""Propose or independently check a local tightening of finite permit rules."""
import argparse
from dataclasses import asdict, dataclass, replace
from datetime import datetime
import json
from pathlib import Path
import re
import sys

from checks import grants, verify


def fields(value, *names):
    if not isinstance(value, dict) or set(value) != set(names):
        raise ValueError(f"Expected exactly these fields: {', '.join(names)}")
    return value


def sequence(value):
    if not isinstance(value, list):
        raise ValueError("Expected a JSON array")
    return value


def name(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]+", value):
        raise ValueError(f"Expected a concrete identifier, got {value!r}")
    return value


def names(values):
    result = tuple(name(v) for v in sequence(values))
    if len(set(result)) != len(result):
        raise ValueError(f"Repeated identifier: {result}")
    return result


def request(row):
    if len(sequence(row)) != 3:
        raise ValueError("A request needs a principal, an action and a resource")
    return tuple(name(part) for part in row)


@dataclass(frozen=True)
class Rule:
    id: str
    principal: str
    action: str
    resources: tuple


def read_policy(raw):
    fields(raw, "snapshot", "rules")
    rules = []
    ids = set()
    for row in sequence(raw["rules"]):
        fields(row, "id", "principal", "action", "resources")
        rule = Rule(name(row["id"]), name(row["principal"]), name(row["action"]), names(row["resources"]))
        if rule.id in ids:
            raise ValueError(f"Repeated rule {rule.id}")
        ids.add(rule.id)
        rules.append(rule)
    return name(raw["snapshot"]), rules


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Expected a timestamp string")
    t = datetime.fromisoformat(value)
    if t.utcoffset() is None:
        raise ValueError(f"Expected a timestamp with an offset: {value}")
    return t


def read_evidence(raw, snapshot, rules):
    fields(raw, "snapshot", "start", "cutoff", "protected", "reviewed_allows", "cycles", "rule_workflows")
    if raw["snapshot"] != snapshot:
        raise ValueError("Evidence belongs to another policy snapshot")
    start, cutoff = instant(raw["start"]), instant(raw["cutoff"])
    if start >= cutoff:
        raise ValueError("Training start must precede cutoff")

    def in_window(value):
        t = instant(value)
        if not start <= t < cutoff:
            raise ValueError(f"Timestamp outside the training window: {value}")
        return t

    required = {request(row) for row in sequence(raw["protected"])}
    for event in sequence(raw["reviewed_allows"]):
        fields(event, "at", "request")
        in_window(event["at"])
        required.add(request(event["request"]))
    if missing := required - grants(rules):
        raise ValueError(f"Starting policy already denies a required request: {min(missing)}")

    if not isinstance(raw["cycles"], dict) or not isinstance(raw["rule_workflows"], dict):
        raise ValueError("Expected workflow maps")
    cycles = {}
    for workflow, rows in raw["cycles"].items():
        due = {}
        for row in sequence(rows):
            fields(row, "due", "complete")
            t = in_window(row["due"])
            if t in due or type(row["complete"]) is not bool:
                raise ValueError(f"Duplicate due time or invalid completeness for {workflow}")
            due[t] = row["complete"]
        cycles[name(workflow)] = [due[t] for t in sorted(due, reverse=True)]
    mapping = {name(rule): names(workflows) for rule, workflows in raw["rule_workflows"].items()}
    if set(mapping) - {rule.id for rule in rules}:
        raise ValueError("Unknown rule in workflow mapping")
    if any(workflow not in cycles for workflows in mapping.values() for workflow in workflows):
        raise ValueError("Mapped workflow is missing its expected-cycle inventory")
    return required, cycles, mapping


def propose(rules, required, cycles, mapping, threshold):
    if threshold < 0:
        raise ValueError("Coverage threshold must be nonnegative")
    candidate, decisions = [], []
    for rule in rules:
        workflows = mapping.get(rule.id, ())
        insufficient = [workflow for workflow in workflows
                        if len(cycles[workflow]) < threshold or not all(cycles[workflow][:threshold])]
        deferred = bool(threshold and (not workflows or insufficient))
        reason = "fit-requirements"
        if deferred:
            reason = "keep-incomplete-coverage" if workflows else "keep-unmapped"
        kept = tuple(r for r in rule.resources if deferred or (rule.principal, rule.action, r) in required)
        if kept:
            candidate.append(replace(rule, resources=kept))
        decisions.append({"rule": rule.id, "reason": reason, "insufficient_workflows": insufficient,
                          "removed_resources": sorted(set(rule.resources) - set(kept))})
    return candidate, decisions


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("propose", "verify"):
        sub = commands.add_parser(command)
        sub.add_argument("policy", type=Path)
        sub.add_argument("evidence", type=Path)
        if command == "propose":
            sub.add_argument("--cycles", type=int, default=1)
        else:
            sub.add_argument("candidate", type=Path)
    args = parser.parse_args()
    snapshot, rules = read_policy(read(args.policy))
    required, cycles, mapping = read_evidence(read(args.evidence), snapshot, rules)
    if args.command == "verify":
        base, candidate = read_policy(read(args.candidate))
        if base != snapshot:
            raise ValueError("Candidate belongs to a different snapshot")
        report = verify(rules, candidate, required)
    else:
        candidate, decisions = propose(rules, required, cycles, mapping, args.cycles)
        report = verify(rules, candidate, required)
        if not report["accepted"]:
            raise ValueError(f"Internal proposal failed verification: {report}")
        report.update({"candidate": {"snapshot": snapshot, "rules": [asdict(r) for r in candidate]},
                       "rule_decisions": decisions, "cycle_threshold": args.cycles})
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        sys.exit(f"Refinement failed: {error}")
