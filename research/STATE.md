# Codex research branch

Work on `research/classroom-replay`. Keep this long-lived branch on origin. Its starting point is `1d653242eb5ab29507982c216dbe68b5d8c310ba` on main. This is assistant-produced reference work.

## Checkpoint 0 · 2026-11-20

**Question.** On Restricter's generated classroom snapshot, what does a log-only baseline lose when an entire assignment-posting action is absent from the log, compared with dropping the same number of events without regard to action?

**Planned scope.** Use both assignment actions (PostAssignment and EditAssignment), all Staff principals and Assignment resources, and the empty context. Pin the upstream revision `35331c1259d1c04f4f453aab60e9f3f338d9d544`. The supplied schema makes this a finite domain. Treat an action as a proxy for a workflow. The data have no chronology. The published loose and ideal policy texts have already been inspected. This is a benchmark calibration study.

**Order of work.** Implement the published loose-rule membership test independently. Check every in-scope decision against a Cedar engine executing the original policy. Use the authors' ideal policy separately to score legitimate and excess grants. Compare the loose policy and an observed-only set of concrete grants. For equal event budgets, remove all posting events or randomly remove that many raw rows with seeds 0 through 29. Preserve duplicate counts and evaluate on the entire intended domain, including unseen tuples. Report per-action counts, seeds and rates with their denominators. Stop and investigate evaluator errors or disagreement before scoring. No timing claim is planned.

**Resume.** Open this file first. Build the CLI with `make test`, then inspect the pinned artifact's schema, entity encodings and log. Implement the replay command, pin the oracle dependency and record reproduction instructions here when the first independent run finishes.
