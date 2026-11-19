# Post-result robustness audit

The registered run found repeated access footprints, especially in JOB, and a low absolute whole-query success rate in STATS. Before computing these additional estimates, fix three follow-ups at the original 95% matched point on informative folds.

1. Collapse each family's SQL IDs with identical column-read footprints to their lexicographically first ID. Keep distinct observed, donor and hidden footprints and recompute family-equal means. Retain the original other-family frequency catalog. This changes family eligibility. Also report the registered data subset with hidden footprint different from donor while retaining original IDs.
2. Add a stronger donor without family membership. Select the outside-family query whose footprint has highest Jaccard similarity to O, breaking ties by query ID. Rank its permissions first, then use the existing table/frequency order. Hold the donor fixed across hidden queries for that observed path. Compare against the true sibling on the same folds.
3. Repeat within-table placebo assignment using 32 deterministic salts. Report the smallest, mean and largest family-weighted success over salts. Report a deterministic example of a gain and a loss (where available) for the practical four-grant comparison, including missing reads and unused additions.

These checks are exploratory. Use them to qualify the paper's conclusions regardless of direction.

### Final reviewer checks

The first audit found that JOB's aggregate gain disappeared when donor and hidden footprints differed. Before computing two final checks, fix their specifications. (1) Rank unseen columns by frequency among the five closest other-family SQL IDs to O under Jaccard similarity. Include all ties at the fifth neighbor. Break score ties with the registered table/frequency keys. Compare this stronger path-blind ranker to the same ranker with D as its first key on both original informative folds and distinct-footprint folds. (2) Repeat the published STATS comparison using sorted relations plus the sorted set of equijoin column pairs as the family key. Resolve SQL aliases to table names. This narrower definition tests sensitivity to treating unrelated joins over the same tables as sibling workflows. Report coverage as well as outcomes. The published family rule remains primary.
