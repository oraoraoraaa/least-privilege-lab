"""Generate the manuscript's migration tables and policy operating points."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator


def build(write_table, save):
    archive = (
        Path(__file__).resolve().parents[1] / "research/migrations/results/summary.json"
    )
    study = json.loads(archive.read_text())
    rows = []
    names = {
        "AChep/keyguard-app": "Keyguard",
        "ZacSweers/CatchUp": "CatchUp",
        "msasikanth/twine": "Twine",
        "prof18/feed-flow": "FeedFlow",
        "shabinder/SpotiFlyer": "SpotiFlyer",
    }

    def fmt(x):
        return f"{x:,}"

    methods = ("diff", "coverage", "source", "rehearsal")
    pooled = study["pooled"]
    for name, result in [
        *((names[k], v) for k, v in study["held_out"].items()),
        ("All", pooled),
    ]:
        c = result["counts"]
        exact = [result["methods"].get(m, {}).get("exact", 0) for m in methods]
        rows.append(
            [
                name,
                *[
                    fmt(c.get(k, 0))
                    for k in ("transitions", "complete", "survivors", "expanded")
                ],
                *(exact if c.get("expanded", 0) else ["--"] * 4),
            ]
        )
    write_table("migrationprojects", rows)
    labels = ["Table diff", "Full coverage", "Projection stars", "Rehearsal"]
    write_table(
        "migrationfields",
        [
            [
                label,
                *[
                    pooled["methods"][m][k]
                    for k in (
                        "exact",
                        "missing_instances",
                        "extra_instances",
                        "flag_expanded",
                        "flag_stable",
                        "retired_alerts",
                    )
                ],
            ]
            for m, label in zip(methods, labels)
        ],
    )
    choices = (
        "retain",
        "diff/all",
        "coverage/all",
        "source/all",
        "rehearsal/all",
        "diff/padded4",
        "rehearsal/padded4",
    )
    labels = (
        "Retain old",
        "Table diff",
        "Full coverage",
        "Projection stars",
        "Rehearsal",
        "Padded diff",
        "Padded rehearsal",
    )
    rows = []
    for m, label in zip(choices, labels):
        a = pooled["shared"][m]
        rows.append(
            [
                label,
                fmt(a["survivor_admitted"]),
                a["introduced_admitted"],
                fmt(a["admitted"]),
                a["unused_new"],
            ]
        )
    write_table("migrationaccounts", rows)

    fig, axes = plt.subplots(1, 2, figsize=(7.05, 2.95))
    colors = ("#265392", "#007762", "#b45e12", "#77428b")
    markers = ("o", "s", "+", "x")
    for ax, boundary, title in zip(
        axes,
        ("individual", "shared"),
        ("One policy per query", "One policy per database"),
    ):
        policies = pooled[boundary]
        ax.set_xscale("symlog", linthresh=1)
        ax.grid(alpha=0.22)
        for m, label, color, marker in zip(
            methods, ("Diff", "Coverage", "Stars", "Rehearsal"), colors, markers
        ):
            series = [
                policies[f"{m}/{cap}"] for cap in ("0", "1", "2", "4", "8", "all")
            ]
            ax.plot(
                [p["unused_new"] for p in series],
                [p["admitted"] for p in series],
                color=color,
                marker=marker,
                fillstyle="none",
                lw=1.2,
                ms=5,
                label=label,
            )
            if m in ("diff", "rehearsal"):
                p = policies[m + "/padded4"]
                ax.plot(
                    p["unused_new"],
                    p["admitted"],
                    marker="D",
                    ms=5,
                    color=color,
                    linestyle="none",
                )
        ticks = (
            [0, 1, 10, 100, 1000, 10000]
            if boundary == "individual"
            else [0, 1, 10, 100]
        )
        ax.xaxis.set_major_locator(FixedLocator(ticks))
        ax.set_xticklabels(
            ["10k" if t == 10000 else "1k" if t == 1000 else str(t) for t in ticks]
        )
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("Unused new grants", fontsize=9)
        ax.tick_params(labelsize=8)
    axes[0].set_ylabel("Complete statements admitted", fontsize=9)
    axes[1].plot(
        [], [], marker="D", color="#404040", ms=4, ls="none", label="Padded four"
    )
    fig.legend(
        *axes[1].get_legend_handles_labels(),
        loc="lower center",
        ncol=5,
        frameon=False,
        fontsize=8,
    )
    fig.subplots_adjust(bottom=0.29, left=0.10, right=0.98, wspace=0.27, top=0.88)
    save(fig, "migration-tradeoff")
