# Choosing a preflight and reviewing a schema migration

A reviewer can ask two different questions. Which of two existing queries should be staged to help select grants for an unknown variant? Which existing queries will read new fields when the service is rebuilt against a planned schema? The [manuscript](../../paper/paper.pdf) answers the first with query benchmarks and the second with versioned application SQL.

## Try the migration reviewer

With uv installed, run the published Mihon example from the repository root.

~~~sh
uv run --locked --script research/selection/review.py --example
~~~

The command reads the v0.18.0 query sources and v0.19.0 schema definitions. It checks 42 old named reads and reports 10 alerts. For **mangas.getMangaById** the added read is **mangas.notes**. The developer's source still selects the complete row. SQLDelight can compile that projection to a list of column names. The release packages contain two different lists. The older list omits notes even on the new schema.

For a second way to build the queue, append **--method coverage**. This rule flags a previously read field that disappears or a growing relation whose old columns were all read. On the example it flags the same ten names, identifying **mangas** as a growing relation. It uses the old footprints and the schema inventories without executing the old SQL against the planned schema. An explicitly enumerated projection can cover all old fields yet ignore a later addition. The executable pair in **test_review.py** shows this limit.

For an application using the same named SQLDelight read conventions, point the reviewer at its old source directory and a file containing the planned SQLite DDL.

~~~sh
uv run --locked --script research/selection/review.py \
  --old-dir /path/to/old/sqldelight --next-ddl /path/to/planned-schema.sql
~~~

Alternatively supply **--next-dir** with SQLDelight definitions. The reviewer uses only their schema headers. Supply trusted definitions suitable for an empty local database. The report lists new read resources or the native preparation error for each flagged old query. It emits a JSON review queue and makes no policy edits. An added read calls for a decision about whether this query ought to expose the field. A preparation error calls for checking the replacement query or confirming the old name's retirement. New query names enter review separately.

The loader supports the named SELECT and WITH programs, Kotlin type adapters and bound parameter shapes exercised by these applications. It skips named writes, binds values to one, and uses one element for collection parameters. A closed per-query permission set covers table and view reads reported by SQLite. A deployed application may use a different compiler, parameter shape or enforcement boundary. An edit confined to the next version's SQL can introduce a read while rehearsal stays quiet.

## Reproduce and audit

Run **sh research/selection/reproduce.sh** for the extension. It checks reviewer regressions, fetches digest-pinned source files and two x86-64 release packages, prepares all in-scope queries, and compares every evidence file. The published packages total about 54 MiB. Inputs stay in the ignored build directory. To retain a separate output directory, run the following.

~~~sh
uv run --locked --script research/selection/run.py --out build/my-selection-run
~~~

| Evidence | Unit and use |
| --- | --- |
| [Study design](PROTOCOL.md) and [follow-ups](FOLLOWUP.md) | The two-candidate and quarterly designs were fixed before their results. The event-level check and second application were selected after seeing Tivi. Later checks are marked in the follow-up record. |
| [Choice rows](results/choices.tsv.gz) and [family summaries](results/selection.json) | One row per observed ID, hidden ID and unordered candidate pair, ordered by old-source similarity. Native decisions come from the original study. The decomposition separates an insufficient budget, two unsuccessful candidates and losses attributable to selection. |
| [Tivi snapshots](results/snapshots.json) and [decisions](results/application.json) | Named reads, resource universes, prospective policies, old-catalog alerts, held-out outcomes and introductions across six quarterly transitions. |
| [Tivi event history](results/tivi-history.json) | Every in-scope source-changing first-parent commit during the same window. A date can contain multiple commits. Revision identifies the exact event. |
| [Mihon snapshots](results/mihon-snapshots.json) and [decisions](results/mihon.json) | Five adjacent release transitions. Each record includes the alternative policies, preparation errors, unused additions, DDL and rehearsal alerts, and flags on old names that subsequently retired. |
| [Full-column review comparison](results/column-coverage.json) | Per-transition flagged, missed and retired names, with both directions of disagreement against rehearsal. The two flag lists match by identity across all 717 old-name comparisons. |
| [Release literal check](results/release-check.json) | SHA-256 values for two official packages and their matched embedded SQL strings, unique match counts, projected columns and the old literal's reads on the new schema. |

The old-catalog reviewer and retrospective scorer have different inputs. **review.py** needs only old SQL and planned DDL. **run.py** evaluates its alerts against new queries and reports name churn. For the five Mihon transitions, the 201 older name instances comprised 163 survivors and 38 retirements. Rehearsal raised 83 alerts, including 34 subsequently retired names. The DDL comparator raised 108. Both detected all 49 expansions on surviving names. The four-grant results in the paper compare enforceable policies and use the separate denominator of 49.

The [quarterly](sources.json), [event](event-sources.json) and [release](mihon-sources.json) manifests pin commits, paths and file hashes. To reconstruct any manifest from a local upstream Git history, run **python3 research/selection/sources.py REPOSITORY --series quarterly**, replacing the series with **events** or **mihon** as appropriate. Sources come from [Tivi](https://github.com/chrisbanes/tivi) and [Mihon](https://github.com/mihonapp/mihon). The release check reads SQL strings from the [v0.18.0](https://github.com/mihonapp/mihon/releases/tag/v0.18.0) and [v0.19.0](https://github.com/mihonapp/mihon/releases/tag/v0.19.0) packages as data.
