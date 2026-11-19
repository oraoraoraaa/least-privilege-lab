"""Run both refiner variants through the CLI and score the returned policies."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
DATA = HERE / "fixtures"
ENGINE = ["uv", "run", "--locked", "--script", str(HERE / "refine.py")]
CASES = ("before-first-drill", "recorded-restore", "logging-gap", "warm-cache")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def expand(policy):
    return {(r["principal"], r["action"], value) for r in policy["rules"] for value in r["resources"]}


def run():
    policy = DATA / "policy.json"
    scoring = read(DATA / "score-only.json")
    intended = {tuple(k) for k in scoring["intended"]}
    cold = tuple(scoring["cold_restore"]["request"])
    original = expand(read(policy))
    if cold not in intended or not intended <= original:
        raise ValueError("Scoring fixture has inconsistent intended permissions")

    runs = []
    with tempfile.TemporaryDirectory() as temporary:
        proposed = Path(temporary) / "proposal.json"
        for case in CASES:
            evidence = DATA / (case + ".json")
            if datetime.fromisoformat(scoring["cold_restore"]["at"]) < datetime.fromisoformat(read(evidence)["cutoff"]):
                raise ValueError("Restore is inside the training window")
            for cycles in (0, 1):
                output = subprocess.check_output([*ENGINE, "propose", policy, evidence, "--cycles", str(cycles)])
                result = json.loads(output)
                proposed.write_text(json.dumps(result["candidate"]))
                verified = json.loads(subprocess.check_output([*ENGINE, "verify", policy, evidence, proposed]))
                if not verified["accepted"] or result["checks"] != verified["checks"]:
                    raise ValueError("Serialized proposal failed independent verification")
                retained = expand(result["candidate"])
                runs.append({"case": case, "cycles": cycles, "legitimate_retained": len(retained & intended),
                             "legitimate_total": len(intended), "excess_removed": len((original - intended) - retained),
                             "excess_total": len(original - intended), "cold_restore_allowed": cold in retained,
                             "deferred_rules": sum(r["reason"].startswith("keep-") for r in result["rule_decisions"]),
                             "proposal": result})
    return runs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", type=Path, help="compare results with a committed archive")
    args = parser.parse_args()
    report = json.dumps(run(), sort_keys=True, indent=2) + "\n"
    if args.check:
        if report != args.check.read_text(encoding="utf-8"):
            raise SystemExit("Pilot results differ from archive")
        print("Verified 8 registry proposals and their held-out scores.")
    else:
        print(report, end="")
