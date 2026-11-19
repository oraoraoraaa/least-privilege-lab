# Which unseen columns should a policy keep?

A reporting account has successfully run one query. A related query is available in staging. This experiment measures whether the staged query helps select the permissions a third query needs. The [paper](../../paper/paper.pdf) reports the results. The [original protocol](PROTOCOL.md) and [subsequent checks](AUDIT.md) record when each comparison was chosen.

The [follow-on study](../selection/README.md) compares two candidate siblings, then tests policies across real application versions and inspects two published package literals.\n\n## Reproduce or inspect a result

Run the SQL study from the repository root with Git, uv and network access for the first download.

~~~sh
sh research/paths/reproduce.sh
~~~

The harness uses Python 3.12 and a locked APSW environment. Input digests are checked on every run. The downloaded inputs stay under the ignored directory `build/path-inputs`. The harness computes results in a temporary directory, compares all eight files against the archive, and compares gzip tables after decompression. Use the root command `sh research/reproduce.sh` to include the Java/Cedar calibration and checked registry prototype.

For a first inspection, follow the permissions in the JOB example from Section 6 of the paper.

~~~sh
python3 - <<'PY'
import json
from pathlib import Path
p = Path("research/paths/results")
queries = json.loads((p / "traces.json").read_text())["corpora"]["JOB"]["queries"]
observed, staged, hidden = (set(queries[q]["reads"]) for q in ("10c", "10a", "10b"))
print("Hidden query still needs", sorted(hidden - observed))
print("Staging provides", sorted((hidden - observed) & staged))
print(json.loads((p / "audit.json").read_text())["JOB"]["examples"]["1"]["four_added"])
PY
~~~

Here the missing read is `role_type.role`. The sibling and table/frequency methods differ on exactly one of four additions. The STATS example in the same file reverses the outcome.

## Measurements and units

| Archive | Contents |
| --- | --- |
| [traces.json](results/traces.json) | SQLite and binding versions, full permission universes and the family, normalized SQL digest and sorted native read set for each statement. |
| [folds.tsv.gz](results/folds.tsv.gz) | One row per ordered observed, sibling and hidden assignment. Counts identify unseen reads, overlap with staging, and staged-only reads. |
| [matched.tsv.gz](results/matched.tsv.gz) | One row per fold, universe, method and removal target. `allowance` is the retained excess count. `success` is a probability over uniformly ordered ties. |
| [enforced.tsv.gz](results/enforced.tsv.gz) | Six native allow/deny decisions per fold. Rows also report policy size, unused grants and unseen reads recovered. |
| [summary.json](results/summary.json) | Coverage, family-averaged outcomes, primary paired differences, family counts, and bootstrap and leave-one-family-out summaries. |
| [audit.json](results/audit.json) | Repeated-footprint cohorts, nearest outside-family donor, 32 placebo masks and concrete gains and losses. |
| [review-checks.json](results/review-checks.json) | Five-neighbor comparisons and a narrower STATS family key based on actual join columns. |
| [manuscript-checks.json](results/manuscript-checks.json) | Native four-grant results after footprint collapse, exercised-permission starting policies, actual integer allowances and fold-level sign counts. |

The two compressed outcome tables join to the folds on `corpus, family, observed, sibling, hidden`. A permission ends in `@row` for a table-only authorizer read. The matched result uses hidden labels only for the scorer's prefix cutoff. The four-grant candidate is fixed before the hidden statement is run. A family counts equally in each corpus mean, so dividing the total number of allowed queries by the total number of folds gives a different statistic.

## Inputs and implementation

[JOB](https://github.com/gregrahn/join-order-benchmark/tree/a39603662e023e449cb2121997a5034df9e02ebf) identifies families in its filenames. [STATS-CEB](https://github.com/Nathaniel-Han/End-to-End-CardEst-Benchmark/tree/670cb8d4bf4cbfa32f94fdf17f33973d3fd67d1b) supplies the simplified schema and 146 cardinality-prefixed statements. The registered STATS family key uses the FROM relations. The audit also uses equality join columns. The collector creates empty schemas locally and executes the SQL through SQLite's [native authorization callback](https://www.sqlite.org/c3ref/set_authorizer.html).

[workloads.py](workloads.py) checks the inputs and captures native read requests. [evaluate.py](evaluate.py) forms rankings, integrates ties and fixes deployable candidate policies. [study.py](study.py) collects the two corpora, executes policies and writes each fold. [summarize.py](summarize.py) computes the family-weighted estimates and paired intervals. [audit.py](audit.py), [review_checks.py](review_checks.py) and [manuscript_checks.py](manuscript_checks.py) run the exploratory checks. Every specification and result remains available in Git history.
