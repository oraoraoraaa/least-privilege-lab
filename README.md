# Least Privilege Lab

**面向最小权限原则的访问控制策略优化设计与实现**

Bachelor’s graduation project · Design and implementation of least-privilege access-control policy optimization

An administrator preparing a policy change needs to know which permissions it removes, which workflows depend on them, and which grants reappear in a later revision. The goal is a local tool that answers those questions with a policy diff and evidence for each recommendation.

The starter compares a snapshot of effective grants with a historical decision log. It runs offline and writes a TSV report. Rule inference, automatic tightening and revision monitoring are the next stages. The [milestone plan](docs/ROADMAP.md) gives each stage a demonstration and a completion criterion. The [original project brief](docs/brief/课题附件.pdf) is included in Chinese.

## Try the review

From the repository root, run these commands with Make and a JDK that supports Java 17 as a compilation target.

```sh
make demo
make test
```

The synthetic example follows service accounts in a model registry. The inference service read the stable model twice. The recovery service still has access to the archive, yet the log contains no restore. Before proposing removal, a reviewer would need evidence about the restore workflow. The mirror account recorded a denial for a permission that appears in the current grant snapshot. Policy version or request context could explain that discrepancy.

To review your own normalized inputs, build the JAR once. The report goes to standard output.

```sh
make build
java -jar build/least-privilege-lab.jar review examples/registry/grants.tsv examples/registry/events.tsv > build/review.tsv
```

### Input contract

| File | UTF-8 TSV header, in order | Interpretation |
| --- | --- | --- |
| Grant snapshot | `principal`, `action`, `resource` | One concrete, effective allow per tuple. Repeated rows represent one grant. An absent tuple has no grant in this snapshot. |
| Event log | `timestamp`, `principal`, `action`, `resource`, `decision` | One event per row. Use an ISO-8601 instant such as `2026-10-01T09:00:00Z` and `ALLOW` or `DENY`. Repeated events count separately. |

Supply the header even for an empty file. Identifiers are case-sensitive. Use exact identifiers without wildcards, surrounding whitespace, or embedded tabs or newlines. The caller supplies a finite snapshot with policy conditions already evaluated for the chosen context. The report counts events across the supplied window and includes historical tuples absent from the snapshot. A granted request records an observed decision. Business intent requires separate evidence.

## Work in the repository

| Location | Start here for |
| --- | --- |
| [Java source](src/main/java/leastprivilege/) | `Inputs` reads files, `Permission` identifies a tuple, `Review` joins the evidence, and `Main` exposes the CLI. |
| [Registry example](examples/registry/) | A small hand-auditable case and its expected report. |
| [Smoke test](tests/review.sh) | The CLI contract, duplicate grants and rejection of malformed evidence. |
| [Milestones](docs/ROADMAP.md) | Advisor decisions, what to build, and what evidence closes each milestone. |
| [Evaluation protocol](experiments/README.md) | Comparison methods, ground truth, metrics and a reproducible path to a paper. |
