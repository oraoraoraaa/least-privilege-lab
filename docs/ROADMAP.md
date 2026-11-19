# Graduation project milestones

**First checkpoint · by 4 December 2026.** Take the registry example to the advisor. Agree on one policy fragment, identify the designated translation paper, request any departmental PolicyRefiner materials, and check the actual submission calendar. Leave the meeting with one external case to reproduce and a written definition of a legitimate request.

The dates below are proposed working windows from November 2026 to June 2027. The brief specifies deliverables and length requirements. The department sets the deadlines. At each checkpoint, record the date, Git revision, command or figure demonstrated, and one decision for the next period.

## Product and research question

The user is a service owner reviewing a policy revision. Give them the proposed rule change, the effective grants it removes, the evidence for keeping or reviewing a permission, and the grants a later revision reintroduces. The minimum useful release works on versioned files on a laptop. A single service, its operator and its recovery job make a good first deployment scenario.

The paper question is narrower. **When entire workflows are absent from the log, can a tightener that defers changes for poorly observed workflows preserve more rare legitimate access at a comparable reduction in excess grants?** A scheduled recovery job motivates the question. A signed-off workflow inventory or schedule can tell us it exists even when its next run falls outside the observation window. Measuring the cost of retaining those permissions is part of the result.

## Checkpoints

| Target | Achievement | Evidence to show before moving on |
| --- | --- | --- |
| **1 · Nov 20–Dec 4, 2026** | Settle the scope and research inputs. Read the three assigned papers and trace how one open implementation proposes a tighter rule. | One page mapping paper ideas to modules, one worked example, a pinned external case, and an advisor decision on the language fragment, artifact access and translation. |
| **2 · Dec 2026–Jan 2027** | Build a replayable baseline. Evaluate a small permit-rule fragment with role membership and one resource attribute. Parse versioned logs and represent observed, owner-protected and uncertain access separately. | Replay one public case or a documented supported slice. Compare its decisions with the source evaluator on the same finite requests. Show a mismatch test, a rare legitimate workflow, and reference results for the original policy and the observed-only baseline. |
| **3 · Feb 2027** | Produce the first checked policy change. Generate local rule strengthenings, use a bounded constraint check on the whole policy, and defer changes when workflow evidence is insufficient. | A before/after rule diff, removed grant count and review reason. On a small fixed universe, exhaustive enumeration and the solver agree that the proposal introduces zero grants and preserves every protected request. Show a rejected candidate and its witness. |
| **4 · Mar 2027** | Deliver the full review loop. Compare successive policy revisions against a frozen, versioned requirement baseline and surface newly granted access outside it. | In one command, replay a legitimate expansion, a seeded redundant expansion and an unchanged revision. Relate each alert to a rule and tuple. Compare alerts with independent labels. Record review feedback from a walkthrough if an operator is available. |
| **5 · Apr–early May 2027** | Freeze the tool and run the study. Compare the candidate, simple baselines and an external baseline where semantics match. Vary log coverage, policy size and rare-workflow frequency. | One clean run regenerates the table of effective grants, held-out retention, alert precision/recall, review workload and runtime. Include an ablation, timing spread and a case where the method loses. Decide with the advisor whether the evidence supports a paper. |
| **6 · May–Jun 2027** | Finish the academic submission and package the work for reuse. Reserve the final two weeks before the confirmed deadline for revisions and defense rehearsal. | School-format thesis of **15,000 字 or more**, translation of the assigned English paper (**2,000–3,000 字**), complete commented source, run instructions, test scripts and experimental data. A second person can reproduce a main result from a clean checkout. Prepare a paper draft if the evidence warrants the claim. |

Draft the semantics and related-work sections during checkpoint 2, the design chapter during checkpoint 3, and the translation by checkpoint 4. This leaves the final writing window for the results that actually emerge.

## Design decisions to test

| Component | Contract to build |
| --- | --- |
| Policy and log adapters | Map native rules, entity snapshots and decisions into a versioned, finite request universe. Publish the supported syntax and reject unsupported conditions. Retain rule IDs so a result can point back to its source. |
| Requirement inference | Aggregate grants by principal, resource, operation and time window. An owner-approved requirement can protect a rare action. Conflicting decisions, suspect activity and incomplete observation carry an explicit reason for review. |
| Tightening and constraints | Generate a small set of readable local restrictions, such as replacing a broad resource match with a permitted attribute value. Keep the least-permissive admissible candidates under set inclusion. Check that the candidate grants are a subset of the original and that protected access survives. A timeout, unresolved assumption or insufficient evidence leaves the affected rule in place. |
| Revision monitor | For each committed revision, compare effective grants with the preceding revision on the same entity snapshot. Intersect newly added grants with the complement of the frozen baseline. An alert is a request for review. Update baseline versions only with reviewed evidence. |

**Scope if time gets tight.** Keep one policy fragment, one external case, one controlled generator, one solver-backed strengthening and the revision monitor. Use full recomputation per revision first. Defer incremental indexing and additional policy languages until the measured runtime justifies them. If observational logs are unavailable, report results as controlled case studies and describe the gap to production use.

## Reading and code reuse

- **PolicyRefiner** gives a precise model of allowable local edits and evaluates on held-out requests. Reconstruct a small worked example before implementing its ideas. The brief lists source code and data. A public release was not verified, and the Restricter authors report difficulty obtaining earlier tools. Ask the advisor about local access at checkpoint 1. Label any independent implementation by its actual scope. [OOPSLA paper](https://doi.org/10.1145/3689738) · [Restricter evaluation, §7](https://link.springer.com/chapter/10.1007/978-3-032-22752-2_6)
- **Restricter** provides an executable comparison and a source of policies, entities and generated logs. Start with its classroom case. Trace one permit rule through the synthesis code and reuse the upstream case generator or evaluator for the supported slice. Record the input conversion, revision and environment. [TACAS paper](https://doi.org/10.1007/978-3-032-22752-2_6) · [Pinned upstream code and cases](https://github.com/REASONERSLab/Restricter/tree/35331c1259d1c04f4f453aab60e9f3f338d9d544)
- **OPMonitor** motivates inferring a granting baseline and maintaining it as policies evolve. Compare the simplest revision-by-revision implementation with its monitoring model. Profile replay before deciding whether a tree index is worth implementing. [Computers & Security paper](https://doi.org/10.1016/j.cose.2025.104623)

For a systems portfolio, keep an overlapping-rule example that defeated a local check, a profile that changed an implementation decision, and a figure you can regenerate from the tagged code. These give you concrete engineering decisions to discuss at a whiteboard.
