# When does old-query rehearsal help?

Read the [five-page paper](../../paper/paper.pdf), [frozen research plan](PLAN.md) and [prior five-project protocol](../migrations/PROTOCOL.md). Commit 8ac30a2 published the rule, three fresh project pins and analysis order. Commit d872bbc published the implementation before fresh scoring. The old five-project cohort is discovery evidence for selective rehearsal. Tivi and Mihon remain development evidence.

## Prospective result

On Phoenix, Press and Zipline the selective rule routed zero of 425 old name instances to the native authorizer. Its added list agreed with full rehearsal in 421 cases. In the four disagreements, across three Press commits, the edited next query read exactly the fields predicted by the old wildcard. The old query failed to prepare. Across 27 expansions, broad table diff, selective and full rehearsal were exact 26, 22 and 18 times. Full rehearsal gave 18 preparation errors. Selective flagged all 18 names for other reasons and supplied zero native diagnostics. Twelve of those names later retired, five survived and one became unsupported. No fresh case exercised the changed-view route. The smallest units here are query names at a database revision.

The original five projects gave 7 routed calls out of 3,756 with identical added lists throughout and 28 lost native errors. In those projects every exact success for full rehearsal was also exact for diff. Rehearsal contributed zero correct fields beyond diff while avoiding 178 extra instances. The original [per-transition archive](../migrations/results/) retains every forecast.

## Operating costs

| Policy | Original complete upgrades / 77 | Original unused | Recovered complete upgrades / 148 | Recovered unused |
|---|---:|---:|---:|---:|
| Retain old | 59 | 0 | 106 | 0 |
| Full-column coverage | 66 | 0 | 126 | 1 |
| Table diff | 68 | 1 | 126 | 1 |
| Full rehearsal | 64 | 0 | 116 | 0 |
| Padded table diff | 70 | 222 | 127 | 548 |

The original 222 comprise 198 table-only markers and 24 column instances. On recovered catalogs the 548 comprise 186 hidden, 183 table-only, 176 row-identifier, two ordinary-column and one shadow-table grant. Coverage and diff installed the identical policy at every recovered transition. Under the original schema model diff and padding admitted 1,006 and 1,010 statements out of 1,023. Under the extended model on the recovered catalogs they admitted 3,234 and 3,235 out of 3,269. Separate the two universes when interpreting padded rankings. The archive includes the overlap of 48 formerly complete search-project transitions evaluated again with the extended model.

The extension gives every native execution its own freshly constructed empty SQLite database. Use the populated FTS fixture to inspect the engine's first-use shadow-table reads. Row identifiers enter the candidate universe only when the engine reports that identifier. Hidden fields come from SQLite's inventory. The FTS data-version query is represented as an enforceable auxiliary resource. Each distinct policy and new-query pair is validated natively. Permission costs count resources at a query or account boundary in a snapshot. They have no common unit of data sensitivity.

## Two review points and an authorization decision

* FeedFlow introduced a bookmark field [in 2024](https://github.com/prof18/feed-flow/commit/4916711df767bef323740134d66b1ce141258edd). For the unchanged unread-count query diff suggested it and rehearsal found no new read. [The 2025 badge edit](https://github.com/prof18/feed-flow/commit/379e6ad8338023226c7a5113e78d9325d3702e0d) made it a required existing field. All four old-SQL forecasts then proposed nothing. Across the fresh cohorts the stricter screen for an entirely unused schema addition followed by a consumer edit before any further DDL change found zero cases.
* For both Zipline releases the harness invokes all ten shipped named reads. Two nullable methods have two SQL shapes. A recording driver captures emitted SQL and actual bind values. SQLite matched the source footprint in all 24 shape-by-release executions. Deleting each required grant in turn denied the statement. The source files are identical across these two tags. Release validation of an actual changed lookup remains the [Mihon fixture](../migrations/README.md).
* Phoenix's published [export decision](https://github.com/ACINQ/phoenix/pull/337) and [tagged Android control](https://github.com/ACINQ/phoenix/blob/3d6da2b5b17c297fe8b177304df6f4adff86763e/phoenix-android/src/main/kotlin/fr/acinq/phoenix/android/payments/history/PaymentsExportView.kt) establish the CSV recipient's two reachable states. A joined metadata read supplies the internal caller in both states. The measured public behavior is the exact description expression compiled from the [release writer](https://github.com/ACINQ/phoenix/blob/3d6da2b5b17c297fe8b177304df6f4adff86763e/phoenix-shared/src/commonMain/kotlin/fr.acinq.phoenix/csv/WalletPaymentCsvWriter.kt), evaluated on values read from a synthetic payment. In the enabled state both description and notes are exportable. In the disabled state neither is exportable. The harness exercises the SQL and this Kotlin expression with small value types. There was no participant assessment or Android UI run.

## Reproduce and inspect

Run from the repository root with Git, uv, a JDK with javac, and first-run network access. The root reproduction command includes this extension. Kotlin compilation uses digest-pinned Maven dependencies downloaded to the ignored build directory.

~~~sh
sh research/triage/reproduce.sh
make paper
uv run --locked --script research/selection/review.py --example --method selective
~~~

The [source manifest](manifest.json) records each SQL-changing revision, Gradle configuration and input digest within the specified roots. Rebuild the manifest from the pinned Git histories with the first command below. The second repeats the cold-cache benchmark. The JSON contains five observations for each method and transition, their order is specified in the runner. The paper sums the transition medians for each method. Raw elapsed times are machine observations and deterministic replay compares the decisions. The archived runs used an Apple M4 and an AMD Ryzen 9 7945HX. The sums were 4.1/80.9 ms and 6.6/100.3 ms for full/selective respectively.

~~~sh
python3 research/triage/discover.py build/triage/rebuilt-manifest.json
uv run --locked --script research/triage/fresh.py build/triage/run.json.gz --timing build/triage/local-timing.json
~~~

| Archived evidence | How to audit a claim |
|---|---|
| [Fresh decisions](results/fresh.json.gz) | Each database transition records every old name, route, field forecast, message, next status and observed additions. The ledger includes unsupported endpoints. |
| [Discovery and grant costs](results/audit.json.gz) | Original, recovered and overlapping cohorts, grants by type, the populated FTS fixture and per-project totals. |
| [Twine](results/twine-extended.json.gz) and [FeedFlow](results/feed-flow-extended.json.gz) | Extended model inventories, per-query predictions, native denials and installed grants for every transition. |
| [Release and recipient witnesses](results/witnesses.json.gz) | Generated SQL and binds, exact release/source reads, the two Android switch settings and the two FeedFlow commits. [Input digests](case-inputs.json) identify the exact artifacts. |
| [macOS](results/timing-macos.json) and [Arch](results/timing-arch.json) | Five paired observations per method and transition, platform and runtime versions. |

## Implementation notes

During discovery, Git emitted patch text for a merge. Explicitly requesting revision IDs without patches fixed the collector before the first fresh score. A later check used the full declarative DDL text for the temporal screen, covering changes that preserve the column inventory. The fresh evidence was byte-identical. The expanded search analysis is a sensitivity study on the known cohort. It was refined against a populated SQLite fixture and distinguishes native-visible row identifiers from aliases already represented by named columns. An initial literal scan found only eight of ten Zipline query names. Invoking the published methods also captures dynamically constructed SQL and null binds. These changes did not alter the registered predictor or the three project pins.
