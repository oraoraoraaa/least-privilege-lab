# Which SQL Migrations Need Rehearsal?

[Read the manuscript](paper.pdf) or inspect its [LaTeX source](paper.tex). Run `sh research/reproduce.sh` followed by `make paper` at the repository root. The build uses the committed measurements, locked Python plotting environment and pdfLaTeX.

The five held-out application histories, development calibration, native decisions, schema compatibility corrections and complete-catalog sensitivity are in the [migration study](../research/migrations/README.md). Its [summary](../research/migrations/results/summary.json) feeds all three migration tables and the access-versus-unused-grants figure. The per-transition archive joins changed fields to affected queries and records both sides of every discordance.

The [preceding manuscript](https://github.com/oraoraoraaa/least-privilege-lab/blob/4a0eeee2ca8e873ef8c86b7a3c4150513e19f4c5/paper/paper.pdf) gives the full fixed-schema benchmark design, original release comparisons, supporting figures and references. Its [fixed-schema evidence](../research/paths/README.md), [two-candidate selector and release inputs](../research/selection/README.md), [classroom calibration](../research/classroom/README.md) and [registry drill](../research/registry/README.md) still reproduce in the full command.
