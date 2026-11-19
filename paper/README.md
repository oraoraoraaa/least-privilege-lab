# Which Preflight Preserves Query Access?

[Manuscript PDF](paper.pdf) · [LaTeX source](paper.tex) · [Benchmark evidence](../research/paths/README.md) · [Application histories and runnable reviewer](../research/selection/README.md)

The manuscript compares sibling-query preflight on a fixed schema with old-query rehearsal across a migration. A rule using cached column footprints matched every rehearsal alert in the two application histories. A pair of released Android packages confirms a case where identical source text compiled to different permissions. The release-level results distinguish finding queries for review from predicting grants that admit the whole next query.

## Build

From the repository root, run these commands with uv, Make and pdfLaTeX.

~~~sh
make paper
~~~

The target regenerates three vector figures and five LaTeX table bodies from the committed evidence, compiles until citations and cross-references settle, and writes [paper.pdf](paper.pdf). It uses Python 3.12 and the dependency lock for [figures.py](figures.py). The TeX preamble lists its packages, including Latin Modern, microtype, AMS, booktabs, graphics, geometry, xcolor and hyperref. The PDF and figure assets are included for reading without installing a toolchain.

## Trace an assertion

| Question | Where to check |
| --- | --- |
| Which methods were specified before collection? | [Frozen protocol](../research/paths/PROTOCOL.md) and commit 99f810c. |
| Does the registered comparison change across removal levels? | [Primary summary](../research/paths/results/summary.json), used to produce Figure 2 and Tables 1–2. |
| Why does the JOB advantage disappear at the matched point? | [Footprint audit](../research/paths/results/audit.json) and [fold-level signs](../research/paths/results/manuscript-checks.json). |
| Does another baseline, family definition or native budget change the result? | [Neighbor and join-family checks](../research/paths/results/review-checks.json), [native distinct-footprint scores](../research/paths/results/manuscript-checks.json) and Table 3. |
| How are matched scores derived and verified? | [Exact boundary calculation](../research/paths/evaluate.py), [exhaustive small cases](../research/paths/test_evaluate.py) and Section 4. |
| Where are the earlier policy experiments? | [Classroom replay](../research/classroom/README.md) and [registry pilot](../research/registry/README.md). |
| How much could better sibling selection help? | [Paired candidate outcomes](../research/selection/results/selection.json) and Figure 3. |
| Why did the same source start reading notes? | [Release-package witness](../research/selection/results/release-check.json) and Section 8. |
| Does the queue require rehearsing queries? | [Per-query comparison](../research/selection/results/column-coverage.json), Table 5 and the explicit-list/wildcard example in Section 8. |
| What did the migration checker flag? | [Mihon replay](../research/selection/results/mihon.json), [Tivi replay](../research/selection/results/application.json), and the [guide to running the reviewer](../research/selection/README.md). |

The benchmark hidden query is a retrospective holdout. The application histories use ordered snapshots or release tags. Both measure native read authorization. Production invocation frequency, human review time and the business need for a newly read column require separate evidence.
