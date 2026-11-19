# When Does a Sibling Query Preserve Necessary Access?

[Manuscript PDF](paper.pdf) · [LaTeX source](paper.tex) · [Data, methods and worked example](../research/paths/README.md)

The manuscript is an empirical study of column-read policy tightening. Its two principal measurements use the same query assignments. One measures which ranking succeeds at an equal count of excess permissions, using hindsight to set the cutoff. The other tests a policy that could actually be chosen before the hidden query arrives.

## Build

From the repository root, run these commands with uv, Make and pdfLaTeX.

~~~sh
make paper
~~~

The target regenerates two vector figures and three LaTeX table bodies from the committed evidence, compiles until citations and cross-references settle, and writes [paper.pdf](paper.pdf). It uses Python 3.12 and the dependency lock for [figures.py](figures.py). The TeX preamble lists its packages, including Latin Modern, microtype, AMS, booktabs, graphics, geometry, xcolor and hyperref. The PDF and figure assets are included for reading without installing a toolchain.

## Trace an assertion

| Question | Where to check |
| --- | --- |
| Which methods were specified before collection? | [Frozen protocol](../research/paths/PROTOCOL.md) and commit 99f810c. |
| Does the registered comparison change across removal levels? | [Primary summary](../research/paths/results/summary.json), used to produce Figure 2 and Tables 1–2. |
| Why does the JOB advantage disappear at the matched point? | [Footprint audit](../research/paths/results/audit.json) and [fold-level signs](../research/paths/results/manuscript-checks.json). |
| Does another baseline, family definition or native budget change the result? | [Neighbor and join-family checks](../research/paths/results/review-checks.json), [native distinct-footprint scores](../research/paths/results/manuscript-checks.json) and Table 3. |
| How are matched scores derived and verified? | [Exact boundary calculation](../research/paths/evaluate.py), [exhaustive small cases](../research/paths/test_evaluate.py) and Section 4. |
| Where are the earlier policy experiments? | [Classroom replay](../research/classroom/README.md) and [registry pilot](../research/registry/README.md). |

The third SQL query is a retrospective holdout from a public workload. The evidence supports a benchmark measurement of read-level availability. Prospective production availability, row-level policy and automatic discovery of related jobs remain separate research questions. The final section of the manuscript documents research provenance.
