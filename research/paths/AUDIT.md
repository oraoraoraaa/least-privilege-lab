# Post-result robustness audit

The registered run found repeated access footprints, especially in JOB, and a low absolute whole-query success rate in STATS. Before computing these additional estimates, fix three follow-ups at the original 95% matched point on informative folds.

1. Collapse each family's SQL IDs with identical column-read footprints to their lexicographically first ID. Keep distinct observed, donor and hidden footprints and recompute family-equal means. Retain the original other-family frequency catalog. This changes family eligibility. Also report the registered data subset with hidden footprint different from donor while retaining original IDs.
2. Add a stronger donor without family membership. Select the outside-family query whose footprint has highest Jaccard similarity to O, breaking ties by query ID. Rank its permissions first, then use the existing table/frequency order. Hold the donor fixed across hidden queries for that observed path. Compare against the true sibling on the same folds.
3. Repeat within-table placebo assignment using 32 deterministic salts. Report the smallest, mean and largest family-weighted success over salts. Report a deterministic example of a gain and a loss (where available) for the practical four-grant comparison, including missing reads and unused additions.

These checks are exploratory. Use them to qualify the paper's conclusions regardless of direction.
