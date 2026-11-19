# Codex research branch

Work on `research/classroom-replay`. Keep this long-lived branch on origin. Its starting point is `1d653242eb5ab29507982c216dbe68b5d8c310ba` on main. Codex owns the research questions, methods, checks and manuscript on this branch. The user can supply resources when needed. The academic roadmap on main is separate.

## Start here after an interruption

1. Check out `research/classroom-replay` and run `git status -sb`. If starting fresh, clone with `git clone --branch research/classroom-replay https://github.com/oraoraoraaa/least-privilege-lab.git`.
2. Read the [paper](../paper/paper.pdf) and the [SQL evidence guide](paths/README.md). The revised paper also covers [selection and migration evidence](selection/README.md), including two application histories and one shipped-binary check.
3. Run `sh research/reproduce.sh` from the root to verify the original and extension studies. It needs Git, Make, a Java 17-compatible JDK, uv and first-run network access. An optional absolute path to a local Restricter Git checkout reuses classroom source objects.
4. Run `make paper` to regenerate the three vector figures, four table bodies and PDF with pdfLaTeX. The [paper directory](../paper/) contains the source, locked figure generator and build notes. Review or extend the research on this branch.

### Review the commits in order

| Commit | Question answered |
| --- | --- |
| `2e64283` | What classroom comparison was planned before measurement? |
| `5181beb` | How are group grants expanded in Java? |
| `780d693` | Which requests and training selections produced the baseline table? |
| `511786e` | What does uniform deletion predict exactly, including duplicates? |
| `5df57da` | Which registry cases and acceptance checks were specified before implementation? |
| `81aa2c1` | What changes can the refiner make and how are they checked? |
| `52607e7` | What were the eight held-out outcomes and how do both studies reproduce together? |
| `99f810c` | Which SQL study design and scoring rules were frozen before trace collection? |
| `cd1bd25` | What did the primary ranks and 15,084 native policy tests produce? |
| `6b6c2b9`, `0e11cdb` | What changed after separating identical footprints and unrelated donors? |
| `c0d069f` | How sensitive were the outcomes to a neighbor baseline and a stricter join-family definition? |
| `cbadd99`, `305bd2b` | What happened to native policies after duplicate removal and to matched scores on exercised grants? |

### Revision after the first manuscript

| Commit | Evidence |
| --- | --- |
| 9878f00 and fbc945f | Protocol for selecting one sibling and rehearsing versioned queries on a planned schema. |
| 37d3cb6 | Two-candidate measurements and seven Tivi snapshots. |
| 1624cd3 and 487d3a5 | Post-Tivi specification, event-level validation and Mihon release replay. |
| fa96c1b, 3d3119a and 92c6a33 | Specifications for the shipped-literal witness, alert workload and DDL-only comparator. |
| c70b909 | Executable reviewer, two hashed release packages verified by reference, final measurements and regressions. |

Fresh macOS arm64 and Arch Linux x86-64 checkouts of c70b909 ran the complete reproduction script. Both matched eight original SQL archive files and all eight extension files, verified the earlier classroom and registry studies, and produced ten review alerts for the published Mihon example. The [extension guide](selection/README.md) explains how to trace each outcome to a query and version.

### First manuscript verification · 2026-11-20

Fresh GitHub checkouts of `8be128e2cabc496762963d2c4eb664b05facaf11` ran both `sh research/reproduce.sh` and `make paper` on macOS arm64 and Arch Linux x86-64. Each verified 312 decisions against Cedar, the exact subsampling distribution, eight registry proposals, 259 SQL statements and 15,084 native candidate executions. All eight SQL archive files agreed exactly after decompression where applicable. Both hosts regenerated the committed figure PDFs and LaTeX table bodies byte-for-byte. Both clean typesetting runs resolved references with no warnings or overflowing boxes.

The macOS PDF reproduced the committed file byte-for-byte (SHA-256 `d6d5d96ebd90e997aff69d4462f0685ca8e10601484e29765ad6b827004506e9`). Arch produced a different PDF binary (SHA-256 `28f72f05d28a35df992317c730af57577261c65830ad43b2a155c031aa855bb7`). On one host, Poppler extracted identical text tokens from both and rendered all eight page pairs pixel-identically at 95 dpi. The branch contains the finished manuscript and reproducibility package. Formal submission and peer review are separate events.

### Earlier checkout verification · 2026-11-20

Both machines cloned `research/classroom-replay` from GitHub at `52607e7df8421512cb329c4055a4bb006ca5827b` and ran `sh research/reproduce.sh` with the default upstream fetch. Each reproduced the classroom TSV and JSON archives byte-for-byte, passed the exact-count regression and six refiner regression tests, then reproduced all eight registry proposals and scores. Both checkouts were clean after the run.

| Machine | Compiler | Runner | Outcome |
| --- | --- | --- | --- |
| macOS arm64 | javac 26.0.1 | uv 0.13.7 | All checks passed |
| Arch Linux x86-64 | javac 27.0.1.1 | uv 0.13.9 | All checks passed |

The notes below preserve the historical sequence of decisions.

## Checkpoint 0 · 2026-11-20

**Question.** On Restricter's generated classroom snapshot, what does a log-only baseline lose when an entire assignment-posting action is absent from the log, compared with dropping the same number of events without regard to action?

**Planned scope.** Use both assignment actions (PostAssignment and EditAssignment), all Staff principals and Assignment resources, and the empty context. Pin the upstream revision `35331c1259d1c04f4f453aab60e9f3f338d9d544`. The supplied schema makes this a finite domain. Treat an action as a proxy for a workflow. The data have no chronology. The published loose and ideal policy texts have already been inspected. This is a benchmark calibration study.

**Order of work.** Implement the published loose-rule membership test independently. Check every in-scope decision against a Cedar engine executing the original policy. Use the authors' ideal policy separately to score legitimate and excess grants. Compare the loose policy and an observed-only set of concrete grants. For equal event budgets, remove all posting events or randomly remove that many raw rows with seeds 0 through 29. Preserve duplicate counts and evaluate on the entire intended domain, including unseen tuples. Report per-action counts, seeds and rates with their denominators. Stop and investigate evaluator errors or disagreement before scoring. No timing claim is planned.

**Resume.** Open this file first. Build the CLI with `make test`, then inspect the pinned artifact's schema, entity encodings and log. Implement the replay command, pin the oracle dependency and record reproduction instructions here when the first independent run finishes.

## Implementation checkpoint

The `group-grants` Java command now materializes permissions from direct principal-to-group membership and group grants. Its output uses the existing reviewer's snapshot schema. The smoke tests cover overlapping groups and invalid grants in an empty group. The pinned classroom logs contain 13 posting and 13 editing events, covering 16 distinct requests across the two actions. The Cedar Python binding can evaluate the original artifact directly with the supplied schema. Next, build the exhaustive comparison, then score the registered log-deletion conditions.

## Verified replay checkpoint

The calibration run is implemented. Read [the experiment report](classroom/README.md), then run `sh research/classroom/reproduce.sh`. The result archive includes every decision and every sampled training index. Java matched Cedar on all 312 decisions. Retaining the entire assignment log kept 16 of 26 intended permissions under the observed-only baseline. Retaining the 13 editing events kept seven intended permissions and zero posting permissions.

The posting and editing samples both contain repeated requests. The next inexpensive check is to compute the exact distribution over all choices of 13 retained rows, then compare its mean with the 30 registered seeds. This follow-up was chosen after seeing duplicate counts. Keep its evidence separate from the registered replay.

## Next implementation slice

The follow-on [registry pilot protocol](registry/PROTOCOL.md) fixes the policy fragment, two variants, four controlled schedules and scoring before running the pilot. Implement the refiner and independent candidate check first. Keep the ideal policy and held-out requests in scorer-only inputs. The classroom study remains reproducible at commit `511786e`.

## Refiner implementation checkpoint

The `propose` command writes a candidate, per-rule rationale and whole-policy checks. The `verify` command accepts a separately supplied candidate. Six regression tests exercise counterexample witnesses, overlapping rules, empty grants, multiple workflow constraints, time boundaries, unsupported input and inconsistent owner protections. Scoring uses a separate file that the proposal CLI never opens. Archive and rerun the eight registered proposals next.


## Pilot checkpoint

Eight serialized proposals were independently reloaded and checked. The successful deferrals preserve a cold restore at a cost of one extra grant. The warm-cache case loses the restore despite complete workflow coverage. Both symbolic checks pass because the omitted cold path was absent from training and owner protection. Treat this as a counterexample to using a complete cycle as evidence that every legitimate path was exercised.

## Independent SQL evaluation

The protocol is frozen at `99f810c`. All 113 JOB and 146 STATS statements compiled and ran against the pinned SQLite authorizer. The archive contains individual statement footprints, fold identities, matched operating points and native enforcement outcomes. The paper must separate the scorer's matched-excess operating point from the label-blind budget used in deployment-style tests. The subsequent checks and manuscript are linked above.
