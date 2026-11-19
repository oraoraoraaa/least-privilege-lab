# Evaluation protocol

**Primary comparison.** With a fixed policy, finite entity inventory and the same training log, count how many excess grants each method removes and how many legitimate requests it would break. Report a trade-off curve over review thresholds. The unchanged policy anchors the curve at full retention and zero excess grants removed.

## Cases and comparisons

1. Use the [pinned Restricter classroom case](https://github.com/REASONERSLab/Restricter/tree/35331c1259d1c04f4f453aab60e9f3f338d9d544) as an independently authored structured workload. First check that both evaluators agree on the chosen fragment. Record excluded rules and requests. Label generated traces as synthetic.
2. Build a seeded service-registry case with independently specified intended permissions, a broader starting policy and timestamps. Include common reads, infrequent releases and a periodic restore. Give each method the same owner-protected requirements and reserve the full intent labels for evaluation. Leave some rare legitimate grants outside the protected list to measure generalization.
3. Fit on an earlier window, choose thresholds on a later validation window, and evaluate once on a final held-out window. Match two training logs on event count. Drop individual events randomly in one and all events from selected workflows in the other. Keep test events and intended-policy labels out of fitting. Use disjoint development and evaluation seeds for generated cases. For an unordered external case, disclose the sampling scheme and restrict temporal claims to the timestamped study.
4. Run the unchanged policy, an observed-only allowlist, the same local tightener without workflow deferral, and the proposed method. Use the same owner-protection overlay for the three changing methods. Supply workflow metadata equally to variants capable of using it. Run upstream Restricter on compatible inputs and report the native configuration and any input differences. Document any decision mismatch with its rule and request. Restrict the head-to-head comparison to cases with matching semantics.

**Candidate to test.** Map grants to workflows using a declared inventory. Permit a candidate removal only after observing a predeclared number of complete expected workflow cycles with usable telemetry. Keep unmapped grants and incomplete cycles for review. Vary the threshold on validation data and compare the candidate with the same tightener with the check disabled. Record the inventory each run requires and the rules the owner must review. Compare retention at matched excess-grant removal so a policy that defers every change is visible in the results.

## What to measure

| Outcome | Definition |
| --- | --- |
| Effective permissions | Count distinct allowed request tuples on the **same fixed universe** before and after. With an independent intended policy, report the fraction of original excess grants removed and the number of legitimate grants lost. Also report rule count for readability. |
| Normal access retained | Fraction of independently labeled legitimate held-out requests originally granted that remain granted. Report both event-weighted and distinct-tuple retention, plus the rare-workflow subset and its denominator. |
| Monitoring quality | Seed broad, narrow, redundant and approved policy edits. Label the actual new excess tuples using independent intent. Score alerts per revision against those tuples with precision, recall and raw TP/FP/FN counts. |
| Runtime and review cost | Vary entity, rule and log counts separately. Report wall time by stage, monitor time per revision, timeouts, and rules deferred for human review. Show the absolute counts beside rates. |

For zero denominators report `N/A`. Pair methods by case and seed. Record input hashes, code revisions, thresholds, seeds, tool versions, hardware and JVM warm-up policy. Repeat timed runs and report their median and spread. Retain a command that rebuilds each figure from raw results.

**Publication decision.** Bring the advisor a trade-off plot, a labeled failure example and reproduction instructions. Compare the finding with the three assigned papers, including their existing work on held-out access and log density. Advance a method claim only if the advantage survives matched comparisons and ablation. A reproducible characterization of when tightening fails under missing workflows is a narrower paper candidate. Use the same measurements and reproduction package in the thesis.
