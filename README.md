# Least Privilege Lab

This branch studies least-privilege database policies across query variants and application upgrades. It contains a Java grant reviewer, a checked policy refiner, a SQL migration reviewer, and the source and evidence for the research paper.

**[Read the paper (PDF)](paper/paper.pdf)** · [LaTeX source](paper/paper.tex) · [Try the migration reviewer](research/selection/README.md) · [Research history and handoff](research/STATE.md)

The revised [five-project study](research/migrations/README.md) measures which new database reads a reviewer can predict before seeing the next query. In 157 held-out expansions a table diff named all and only the needed fields 106 times, full-column coverage 71 times, and old-query rehearsal 42 times. Rehearsal uniquely recovered a new filter dependency for two FeedFlow queries using changed views. On 77 complete database transitions, keeping old access admitted 991 of 1,023 statements. An uncapped table diff admitted 1,006 with one unused new grant. Padding the diff to four admitted 1,010 with 222 unused additions. The [protocol](research/migrations/PROTOCOL.md), [coverage ledger and decisions](research/migrations/results/) and [import corrections](research/migrations/CORRECTIONS.md) accompany the paper.

**面向最小权限原则的访问控制策略优化设计与实现**

Bachelor’s graduation project · Design and implementation of least-privilege access-control policy optimization

A Java reviewer for access grants and usage logs, and a research project on tightening policies while preserving rare workflows.

The current CLI reads a grant snapshot and a decision log, then reports what happened to each permission. The branch also includes a checked policy-tightening prototype. The graduation roadmap describes a revision monitor as a separate project milestone.

**New here?** Open the [research guidebook (PDF)](docs/guidebook/guidebook.pdf). Start with the model registry, run the demo, and make a small, testable contribution. The later chapters walk through the three research papers, the design of a comparative experiment and a hands-on replay of a database migration. The [milestone plan](docs/ROADMAP.md) and [original Chinese project brief](docs/brief/课题附件.pdf) describe the graduation deliverables.

## Reproduce the research

Run `sh research/reproduce.sh` with Git, Make, uv and a JDK supporting Java 17. A first run downloads pinned inputs and Python packages. To rebuild the figures, tables and PDF, run `make paper` with pdfLaTeX installed. The [manuscript build notes](paper/README.md) map each result to its source.

## Try the review

From the repository root, run these commands with Make and a JDK that supports Java 17 as a compilation target.

```sh
make demo
make test
```

The synthetic example follows service accounts in a model registry. The inference service read the stable model twice. The recovery service has access to the archive and no recorded restore. Its restore schedule would help a reviewer decide whether it still needs the grant. For the mirror account, compare the recorded denial with the policy version and request context in effect at the time.

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

### Rebuild the book

Edit the [LaTeX source](docs/guidebook/guidebook.tex) and run `make guidebook` from the repository root. A TeX Live installation with pdfLaTeX and the packages listed in the source preamble can build the book. The target resolves the table of contents and cross-references, then writes `docs/guidebook/guidebook.pdf`. The Java build and tests run independently.
