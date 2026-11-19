# Migration prediction and shared read accounts

This is the five-project held-out evaluation for [Which SQL Migrations Need Rehearsal?](../../paper/paper.pdf). The [published protocol](PROTOCOL.md) fixes the information available at prediction time. The [correction record](CORRECTIONS.md) identifies import repairs made after the first run. Tivi, Mihon and the one populated APK-literal fixture are development evidence.

## Reproduce

From the repository root run `sh research/reproduce.sh` for all generations of the study, then `make paper`. For this extension alone, run `sh research/migrations/reproduce.sh`. Git, uv and first-run network access are required. The extension pins Python 3.12, SQLite through APSW, and SQLGlot. Sources are fetched by pinned revision and checked by SHA-256. Old and new APKs are read as data. All native decisions use local in-memory databases. No application or production database is modified.

To retain a new set of results, run `uv run --locked --script research/migrations/run.py --out build/my-migration-run`. Add `--dev-only` for the regression cases, the four known discordances, the stable-query grant cost and the populated fixture. The full run performs those gates first. Every supported SQL and unique candidate policy pair is checked against SQLite before its admission outcome is reused.

The archived [manifest](manifest.json.gz) is sufficient for ordinary reproduction. To audit discovery, run `uv run --python 3.12 python research/migrations/inventory.py build/rebuilt-manifest.json.gz` and compare both manifests after decompression. The collector walks the five pinned first-parent histories, including database configuration changes in modules with production SQL. Histories and blob caches live under `build/migration-inputs`. SQLDelight definitions in .sq files supply the planned schema for these declarations. A .sqm change also creates a review opportunity. This study measures declarative source snapshots.

## Trace the evidence

| File in results/ | Units and contents |
| --- | --- |
| [summary.json](results/summary.json) | Counts by project, paired exact-field outcomes, individual and shared policy tradeoffs, edited-query mechanisms, the complete-catalog sensitivity analysis and development results. |
| [by-transition.json.gz](results/by-transition.json.gz) | The same summaries by project, database and exact revisions. Each changed schema field maps to the query names that newly require it. A single query may appear with several changed fields. |
| Five project JSON gzip files | The ledger records initial/departing databases, unsupported queries and reasons. Each transition records old and new read sets, per-name predictions, eligible survivors, introductions and retirements, policy definitions and native outcomes. The Twine file also records the compiled FTS5 schema witness. |
| [development.json.gz](results/development.json.gz) | Identical evidence format for Tivi and Mihon, plus returned title, note and denial for each of the four shipped-literal fixture runs. |

In a transition, a policy index refers to its sorted grant list in `grants`. A name absent from a policy's `denied` list was admitted if evaluated. Individual evaluations cover supported survivors. Shared evaluations cover supported names in the next database. Only rows marked `complete` enter the primary shared-account totals. Empty support, abstentions, retirements and unknown outcomes have distinct representations. The project ledgers include CatchUp's build-time generator for audit. The main analysis excludes its transitions. Database-boundary changes and module renames can create new initial catalogs.

For example, inspect the predicates underlying the two exclusive rehearsal successes against coverage.

~~~sh
python3 - <<'PY'
import gzip, json
with gzip.open("research/migrations/results/feed-flow.json.gz", "rt") as stream:
    project = json.load(stream)
step = next(t for t in project["transitions"] if t["new"].startswith("0a459537"))
for name in ("View.getCategoriesWithUnreadCount", "View.getFeedSourcesWithUnreadCount"):
    print(name, step["rows"][name]["missing"], step["predictions"][name])
PY
~~~

The broad diff, coverage, source-star and rehearsal predictions can also be tried through the [migration reviewer](../selection/README.md). A newly granted field counts as unused if the evaluated next catalog never requests it at the chosen account boundary. This metric has no independent label for business authorization, and query counts have no production frequency weights.
