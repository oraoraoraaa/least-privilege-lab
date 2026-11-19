# Checking a policy change before a cold restore

The prototype narrows finite permit rules using reviewed successful accesses, owner-protected requests and workflow-cycle evidence. Its output gives a reviewer a proposed policy, the resources removed from each rule, the reason for deferral, and two whole-policy checks. The prototype runs locally without credentials for an authorization service.

## Try it

From the repository root, propose a change with one complete cycle required per workflow.

~~~sh
mkdir -p build
tool=research/registry/refine.py
case_dir=research/registry/fixtures
uv run --locked --script "$tool" propose \
  "$case_dir/policy.json" "$case_dir/before-first-drill.json" \
  --cycles 1 > build/proposal.json
python3 -c 'import json; print(json.load(open("build/proposal.json"))["rule_decisions"])'
~~~

For the recovery rule, the reason is `keep-incomplete-coverage` and the removed-resource list is empty. The serving rule loses `candidate` and `retired`. To check a proposal independently after editing its policy, extract the candidate and pass it to the verifier.

~~~sh
python3 -c 'import json; print(json.dumps(json.load(open("build/proposal.json"))["candidate"]))' > build/candidate.json
uv run --locked --script "$tool" verify \
  "$case_dir/policy.json" "$case_dir/before-first-drill.json" build/candidate.json
~~~

A rejected candidate returns a nonzero exit status with a concrete witness for each violated property. To exercise a failure, remove the auditor's manifest grant from your local candidate and repeat the verification. The required request `(auditor, read, manifest)` appears in the report.

## Inputs and guarantees

The policy names the base snapshot and lists rules by ID, principal, action and explicit resources. An allowed request must match at least one rule. IDs use ASCII letters, numbers, underscores, periods, colons and hyphens. A tightening restricts a rule's resources or drops an empty rule. Overlapping rules are evaluated as a union. The fitter preserves each matching requirement on every applicable rule, so redundant rules may remain.

Training evidence uses the same snapshot and a half-open interval `[start, cutoff)`. It contains owner-protected tuples, timestamped reviewed allows, the rule-to-workflow mapping and the due-cycle inventory. Each due entry identifies whether the workflow ran with usable telemetry. A missing execution or logging interruption belongs in that inventory as an incomplete cycle. The caller supplies the expected schedule. A silently omitted due cycle could make coverage look better than it was.

With threshold zero, the fitter retains only resources needed for the supplied requirements. With a positive threshold, every workflow mapped to a rule must have that many recent due cycles, all complete. An unmapped rule or a coverage shortfall keeps the original rule. Cases with future training timestamps, unknown policy fields or protected requests already denied by the base policy fail input validation.

For each proposal the verifier enumerates effective grants and independently encodes both policies as predicates over a symbolic principal, action and resource. Z3 checks for a request newly allowed by the candidate and a required request denied by it. A satisfying assignment supplies a counterexample. Verification fails on solver uncertainty or disagreement with enumeration. These checks cover this finite permit language and the explicitly supplied requirements.

## Controlled pilot

The [protocol](PROTOCOL.md) specified four cases before running the implementation. Each starts with seven effective grants, three intended grants and four excess grants. An owner protects the auditor's manifest access, which is absent from the training records. The scorer separately holds a later archive read by the recovery account. No policy was deployed. Each outcome below is the evaluator's decision on that held-out request.

| Training case | Cycle threshold | Held-out cold restore | Intended grants kept / 3 | Excess grants removed / 4 | Rules deferred |
| --- | ---: | --- | ---: | ---: | ---: |
| Before first drill | 0 | Deny | 2 | 4 | 0 |
| Before first drill | 1 | Allow | 3 | 3 | 1 |
| Recorded archive restore | 0 | Allow | 3 | 4 | 0 |
| Recorded archive restore | 1 | Allow | 3 | 4 | 0 |
| Due drill, logging gap | 0 | Deny | 2 | 4 | 0 |
| Due drill, logging gap | 1 | Allow | 3 | 3 | 1 |
| Complete drill, warm cache | 0 | Deny | 2 | 4 | 0 |
| Complete drill, warm cache | 1 | Deny | 2 | 4 | 0 |

Before the first drill and during the logging gap, deferring the recovery rule preserves the archive read and one excess `old-archive` grant. Once training includes a restore from archive, both variants keep only the intended permissions. In the warm-cache case, the drill completes without a registry read. Coverage reaches the threshold, both variants drop the recovery rule, and the later cold restore loses access. All eight candidates preserve the supplied requirements and introduce zero new grants.

The two improvements occur at different excess-removal levels (3/4 versus 4/4). Comparing retention at matched removal is a separate research question. These four constructed cases isolate mechanisms and failure conditions. They provide no estimate of how often real deployments encounter those conditions.

The [complete proposals and scores](pilot-results.json), [inputs](fixtures/) and [scorer](run_pilot.py) are committed. Run the pilot on its own with `python3 research/registry/run_pilot.py --check research/registry/pilot-results.json`. The branch-wide check also exercises rejection cases, overlapping rules, multiple workflows and training-window boundaries.
