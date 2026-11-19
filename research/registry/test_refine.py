import json
from pathlib import Path
import unittest

from checks import verify
from refine import Rule, propose, read_evidence, read_policy

DATA = Path(__file__).resolve().parent / "fixtures"


class RefinementTest(unittest.TestCase):
    def setUp(self):
        self.snapshot, self.rules = read_policy(json.loads((DATA / "policy.json").read_text()))
        self.evidence = json.loads((DATA / "logging-gap.json").read_text())

    def test_widening_and_loss_return_real_witnesses(self):
        bad = [Rule("unexpected", "other", "read", ("secret",))]
        report = verify(self.rules, bad, {("auditor", "read", "manifest")})
        self.assertFalse(report["accepted"])
        self.assertEqual(report["checks"]["new_grant"],
                         {"smt": "sat", "count": 1, "first_witness": ("other", "read", "secret")})
        self.assertEqual(report["checks"]["lost_requirement"],
                         {"smt": "sat", "count": 1, "first_witness": ("auditor", "read", "manifest")})

    def test_overlap_can_preserve_requirement_through_another_rule(self):
        a = Rule("a", "p", "read", ("x", "y"))
        b = Rule("b", "p", "read", ("x",))
        self.assertTrue(verify([a,b], [b], {("p","read","x")})["accepted"])
        self.assertTrue(verify([a,b], [], set())["accepted"])

    def test_all_mapped_workflows_need_recent_complete_cycles(self):
        rule = self.rules[0]
        required = {("serve","read","stable")}
        mapping = {rule.id: ["a","b"]}
        for cycles in ({"a":[True,True], "b":[False,True]},
                       {"a":[True,True], "b":[True]}):
            candidate, reasons = propose([rule], required, cycles, mapping, 2)
            self.assertEqual(candidate,[rule])
            self.assertEqual(reasons[0]["insufficient_workflows"],["b"])
        candidate, _ = propose([rule], required, {"a":[True,True],"b":[True,True]}, mapping, 2)
        self.assertEqual(candidate[0].resources, ("stable",))

    def test_unmapped_rule_and_latest_gap_are_deferred(self):
        self.evidence["rule_workflows"].pop("serving")
        self.evidence["cycles"]["restore-drill"].append({"due":"2026-02-02T12:00:00Z","complete":True})
        required, cycles, mapping = read_evidence(self.evidence, self.snapshot, self.rules)
        _, reasons = propose(self.rules, required, cycles, mapping, 1)
        self.assertEqual({r["rule"]:r["reason"] for r in reasons},
                         {"serving":"keep-unmapped", "recovery":"keep-incomplete-coverage", "audit":"fit-requirements"})

    def test_cutoff_and_snapshot_isolate_training(self):
        with self.assertRaisesRegex(ValueError, "another policy snapshot"):
            read_evidence(self.evidence, "v2", self.rules)
        self.evidence["reviewed_allows"][0]["at"] = self.evidence["cutoff"]
        with self.assertRaisesRegex(ValueError, "outside the training window"):
            read_evidence(self.evidence, self.snapshot, self.rules)

    def test_inputs_reject_unsupported_policy_and_broken_protection(self):
        with self.assertRaisesRegex(ValueError, "exactly these fields"):
            read_policy({"snapshot":"snap", "rules":[{"effect":"deny"}]})
        self.evidence["protected"].append(["auditor","read","unknown"])
        with self.assertRaisesRegex(ValueError, "already denies"):
            read_evidence(self.evidence, self.snapshot, self.rules)


if __name__ == "__main__":
    unittest.main()
