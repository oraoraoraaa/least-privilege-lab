# Codex research branch

Work on `research/classroom-replay`. Keep this long-lived branch on origin. Its starting point is `1d653242eb5ab29507982c216dbe68b5d8c310ba` on main. This is assistant-produced reference work.

## Start here after an interruption

1. Check out `research/classroom-replay` and run `git status -sb`. If starting fresh, clone with `git clone --branch research/classroom-replay https://github.com/oraoraoraaa/least-privilege-lab.git`.
2. Run `sh research/reproduce.sh` from its root. It verifies the Java CLI, all 312 published-case decisions, the sampling distribution, the registry checks and all eight stored proposals. It needs Git, Make, a Java 17-compatible JDK and uv. A first run downloads pinned public inputs and Python packages. Pass an absolute path to a local Restricter checkout to reuse its Git objects.
3. Read the [classroom results](classroom/README.md) and [registry results](registry/README.md). The work to date establishes baseline behavior and a checked prototype on the documented fragments.
4. **Next research decision.** Freeze a new protocol for a matched-removal comparison on independent workloads. Include jobs with both warm and cold execution paths, define path coverage using evidence available before the cutoff, and include an equally conservative comparison that has no path labels. Keep these pilot cases for regression. Pick the external case or generator and scoring rules before looking at its outcomes. The department's translation assignment and deadlines remain advisor decisions.

### Review the commits in order

| Commit | Question answered |
| --- | --- |
| `2e64283` | What classroom comparison was planned before measurement? |
| `5181beb` | How are group grants expanded in Java? |
| `780d693` | Which requests and training selections produced the baseline table? |
| `511786e` | What does uniform deletion predict exactly, including duplicates? |
| `5df57da` | Which registry cases and acceptance checks were specified before implementation? |
| `81aa2c1` | What changes can the refiner make and how are they checked? |

The branch tip contains the registry pilot outputs, combined reproduction command and follow-up handoff. The notes below preserve the historical sequence of decisions.

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
