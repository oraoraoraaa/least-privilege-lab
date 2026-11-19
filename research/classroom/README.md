# Assignment permissions under missing observations

This calibration study replays two course-membership rules from Restricter's generated classroom case. Its finite domain contains every combination of 12 staff, two assignment actions and 13 assignments in one entity snapshot. An administrator facing a quiet posting log would have to decide what permission to preserve. The experiment measures what a simple rule, keeping only exact requests previously allowed, would discard.

## Reproduce the run

From the project root, with Git, Make, a Java 17-compatible JDK and uv installed, run

~~~sh
sh research/classroom/reproduce.sh
~~~

The script fetches the pinned artifact into a temporary directory if needed, runs Java regression tests, runs the locked Python 3.12 environment and compares every output byte with the archive. For a local copy of the upstream Git repository, pass its absolute path as the sole argument. Inputs come from Git objects at the pinned revision. The harness checks five SHA-256 hashes before the first decision. A successful run prints “Verified all archived classroom results.”

To keep a new output directory for inspection, run the following after cloning the [upstream case](https://github.com/REASONERSLab/Restricter/tree/35331c1259d1c04f4f453aab60e9f3f338d9d544) into `build/restricter`.

~~~sh
make build
uv run --locked --script research/classroom/replay.py --artifact build/restricter --output build/my-replay
~~~

## What each implementation sees

The adapter translates the two published loose rules into two relations. Each staff member belongs to the courses listed in its entity record. Each assignment's course receives a grant for each assignment action. The Java `group-grants` command takes tab-separated files with headers `principal, group` and `group, action, resource`, joins on group and emits distinct concrete grants in reviewer format. The projection assumes flat courses, empty context and the two schema-eligible assignment actions. It reconstructs this fixed rule fragment by hand.

Independently, cedarpy executes the complete original Cedar policy and schema against the original entities for every in-scope request. Reference diagnostics and decision differences stop scoring. The same engine evaluates the authors' separate ideal policy to label intended permissions. Those labels are inputs to the scorer. The observed-only method receives the retained log events and the starting grants. This benchmark has no owner-protection overlay.

The source log has 1,744 generated events. Of these, 26 belong to this slice. The other 1,718 grade events are outside the question. The comparison treats an action as a proxy for a workflow and samples source rows without replacement. Event multiplicity is preserved. The ideal policy supplies labels for every request in the finite domain, including those absent from the log. These are permission counts on one generated snapshot. A future-access retention study requires separate time windows.

## Measured results

The Java projection and the Cedar engine agreed on **312/312** decisions. The loose policy granted 60 tuples and the ideal policy granted 26. A deliberate negative control removed one staff-to-course membership from the Java input. Four decisions then disagreed, including TA0 editing assignment T0C0A0. This checks that the comparison can detect a translation error.

| Policy or training condition | Training events | Intended grants retained, out of 26 | Posting retained, out of 13 | Excess grants removed, out of 34 |
| --- | ---: | ---: | ---: | ---: |
| Original policy | — | 26 | 13 | 0 |
| Exact observed grants, full assignment log | 26 | 16 | 9 | 34 |
| Exact observed grants, all posting events omitted | 13 | 7 | 0 | 34 |
| Exact observed grants, 13 random rows kept, mean across seeds 0–29 | 13 | 10.53 | 5.83 | 34 |

The full log contains 13 posting and 13 editing events. Repeated requests leave nine distinct posting tuples and seven distinct editing tuples. Even with the full log, an observed-only policy loses ten intended permissions. With an equal budget of 13 events, omitting the posting action loses all posting permissions. The 30 random samples retain three to eight posting permissions each. The seeds vary the sample from this one snapshot. They do not represent independent classrooms.

## Exact follow-up on duplicated requests

After inspecting the duplicate counts, we calculated the complete random-deletion distribution. Exactly 10,400,600 subsets retain 13 of the 26 event rows. Their mean retention is **10.2722 of 26** intended permissions, including **5.54 of 13** posting permissions. Only one subset retains zero posting permissions. A total of 32,144 subsets (0.3091%) retain seven or fewer intended permissions overall. These are probabilities under uniform row deletion from this fixed log. The structured deletion condition was chosen by design.

The dynamic program groups repeated rows by request. Taking *j* of *m* identical requests contributes the binomial weight C(*m*, *j*). Each retained request counts once toward distinct permissions. Summing the joint distribution recovers C(26, 13). A separate inclusion-probability calculation checks both action means, and direct enumeration checks a small repeated-row fixture for every possible budget. The [exact joint counts](exact-retention.json) and [calculation](exact_retention.py) reproduce alongside the original study.

## Review the evidence

| File | What a reviewer can check |
| --- | --- |
| [decisions.tsv](results/decisions.tsv) | All requests, both loose-policy decisions, the intended-policy decision and full-log count. |
| [events.tsv](results/events.tsv) | All in-scope events, including repeats, with zero-based indices into the upstream JSON array. |
| [runs.tsv](results/runs.tsv) | Per-action and aggregate numerators, denominators and the exact training row indices for each condition. |
| [summary.json](results/summary.json) | Upstream commit, five file digests, engine binding version and deliberate mismatch witness. |
| [Replay harness](replay.py) | The separate paths for the Java projection, reference evaluator, training selection and scoring. |

The classroom policies, rules and synthetic records originate in the authors' [artifact at the pinned revision](https://github.com/REASONERSLab/Restricter/tree/35331c1259d1c04f4f453aab60e9f3f338d9d544). See the [upstream license](https://github.com/REASONERSLab/Restricter/blob/35331c1259d1c04f4f453aab60e9f3f338d9d544/LICENSE) and [TACAS paper](https://doi.org/10.1007/978-3-032-22752-2_6). Native reference decisions use the Rust Cedar engine via [cedarpy](https://pypi.org/project/cedarpy/4.12.2/). This run evaluates published policy decisions. Running Restricter's synthesis algorithm is a separate experiment.
