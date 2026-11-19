# Registry pilot protocol · 2026-11-20

**Question.** When an archive restore first occurs after the training cutoff, what does a policy reviewer gain and what excess privileges does it retain by deferring edits to rules with incomplete workflow coverage?

**Implementation target.** Use explicit permit rules with a principal, action and finite resource list. A rule can match several workflows. For a fixed policy version and training interval, keep resources required by an owner or by a reviewed successful event. In the coverage variant, keep the original rule when any mapped workflow lacks the required number of complete, most recent due cycles. Defer unmapped rules. The ablation uses the same policy and evidence and disables this check. For this pilot set the threshold to one. Record a reason for each rule. Check the full policy for newly allowed requests and lost requirements using independent enumeration and SMT queries.

**Cases fixed before running.** (1) The first restore falls after the training cutoff. (2) A restore is due and completes with a recorded archive read. (3) A due restore has incomplete telemetry. (4) A due restore completes on a warm cache and makes no archive read. Hold out a later cold restore in all four. Include a separate owner-protected operation absent from training. The warm-cache case tests whether a complete workflow cycle suffices to cover every legitimate branch.

**Report.** Score intended grants retained, excess grants removed, deferred rule count, and held-out cold-restore success separately for both variants. Archive the policy, training evidence, independent intended set, held-out request, candidate rules and check results. This designed fixture tests the mechanism and its failure mode. A deployment-level accuracy estimate needs independent workloads.

**Next decision.** If deferral preserves a restore by retaining its whole rule, quantify the excess retained. If a complete warm-cache run loses the restore, document the exact witness before changing the method. Reserve any modified method for a separately registered study.
