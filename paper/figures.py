# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["matplotlib==3.10.8"]
# ///
"""Build the manuscript figures and table bodies from the committed measurements."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

PAPER = Path(__file__).resolve().parent
RESULTS = PAPER.parent / "research/paths/results"
summary = json.loads((RESULTS/"summary.json").read_text())
audit = json.loads((RESULTS/"audit.json").read_text())
review = json.loads((RESULTS/"review-checks.json").read_text())
plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "font.family": "DejaVu Sans",
                     "axes.spines.top": False, "axes.spines.right": False})


def save(fig, name):
    fig.savefig(PAPER/"figures"/(name+".pdf"), bbox_inches="tight", pad_inches=.05,
                metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)


def panel(corpus, level, metric="success"):
    return next(p for p in summary["panels"] if p["corpus"] == corpus and p["metric"] == metric
                and p["cohort"] == "informative" and p["universe"] == "full" and p["level"] == level)


def write_table(name, rows):
    with (PAPER/"tables"/(name+".tex")).open("w") as out:
        print(r"\newcommand{"+chr(92)+name+"rows}{%", file=out)
        for row in rows:
            print(" & ".join(map(str, row)) + r" \\", file=out)
        print("}", file=out)


def rate(x):
    return f"{100*x:.1f}"


def design():
    fig, ax = plt.subplots(figsize=(7.35, 2.16))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    def box(x,y,w,h,title,subtitle,color):
        ax.add_patch(FancyBboxPatch((x,y), w,h,boxstyle="round,pad=0.009,rounding_size=0.018",
                                    fc=color, ec="#657582", linewidth=.8))
        ax.text(x+w/2,y+h*.68,title,ha="center",va="center",fontweight="bold",fontsize=9)
        ax.text(x+w/2,y+h*.28,subtitle,ha="center",va="center",fontsize=8)
    def arrow(a,b):
        ax.annotate("",xy=b,xytext=a,arrowprops={"arrowstyle":"->","color":"#42525e","lw":1.05})
    box(.01,.66,.27,.25,"Visible evidence","Observed O + staged D","#e6f3ee")
    box(.37,.66,.24,.25,"Rank permissions","Keep O, rank the rest","#e6f3ee")
    box(.70,.66,.28,.25,"Four extra grants","Choose before seeing H","#e6f3ee")
    box(.01,.10,.27,.25,"Hidden query H","Held out from ranking","#f2f2f4")
    box(.37,.10,.24,.25,"Matched excess","Use O ∪ H to stop","#f2f2f4")
    box(.70,.10,.28,.25,"Native enforcement","Run H with fixed grants","#f2f2f4")
    arrow((.29,.79),(.36,.79)); arrow((.62,.79),(.69,.79)); arrow((.49,.65),(.49,.36))
    arrow((.29,.22),(.36,.22)); arrow((.84,.65),(.84,.36))
    ax.plot([.145,.145,.84],[.09,.015,.015],color="#42525e",lw=1)
    arrow((.84,.01),(.84,.09))
    save(fig,"design")


def results():
    fig, axes = plt.subplots(1,2,figsize=(7.45,2.75),sharey=True)
    styles = [("sibling","Sibling","o","#126652",1.7),("table_freq","Table / frequency","s","#294c80",1.5),
              ("placebo","Within-table mask","^","#a05321",1.3),("uniform","Uniform","x","#62686e",1.0)]
    levels = [75,90,95,100]
    for ax, corpus in zip(axes, ("JOB","STATS")):
        for method,label,marker,color,line in styles:
            ax.plot(levels, [100*panel(corpus,str(x))["means"][method] for x in levels],
                    label=label,marker=marker,color=color,ls={"uniform":":","placebo":"--"}.get(method,"-"),
                    ms=4.8, lw=line, markerfacecolor="white" if method!="sibling" else color)
        ax.set(title=corpus, xticks=levels, ylim=(-3,104), xlabel="Target excess removal (%)")
        ax.grid(axis="y",color="#dbe0e3",lw=.6)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Whole-query success (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="lower center",ncol=4,frameon=False,fontsize=8)
    fig.subplots_adjust(bottom=.31,top=.89,wspace=.15)
    save(fig,"operating-points")


def tables():
    coverage, primary, sensitivity = [], [], []
    for c in ("JOB","STATS"):
        d=summary["coverage"][c]
        coverage.append([c, d["universe"], d["queries"], f'{d["eligible_families"]}/{d["families"]}',
                         f'{d["eligible_queries"]}', f'{d["informative_families"]}', f'{d["informative_folds"]:,}/{d["folds"]:,}'])
        for key,label in (("95","95\\% matched"),("four","Four grants")):
            p=panel(c,key)
            m=p["means"]
            delta=p["paired_vs_table"]
            low,high=delta["bootstrap95"]
            primary.append([c,label,rate(m["table_freq"]),rate(m["sibling"]),rate(m["placebo"]),
                            rate(delta["difference"]), f"[{rate(low)}, {rate(high)}]"])
        for key,label in (("original","All informative"),("hidden_differs_from_donor",r"$H\ne D$"),
                          ("distinct_footprints","Three distinct footprints")):
            g=audit[c][key]
            b,s=(g["means"][name] for name in ("table_freq","sibling"))
            sensitivity.append([c,label,g["families"],f'{g["folds"]:,}',rate(b),rate(s),rate(s-b)])
        for key, label in (("original","Five-neighbor ranking"),("distinct","Five-neighbor, distinct")):
            g=review[c]["neighbors"]["panels"][key]
            sensitivity.append([c,label,g["families"],f'{g["folds"]:,}',rate(g["blind"]),rate(g["sibling"]),rate(g["difference"])])
        if c=="STATS":
            for key,label in (("original","Join-based families"),("distinct","Join-based, distinct")):
                g=review[c]["join_families"]["panels"][key]
                sensitivity.append([c,label,g["families"],f'{g["folds"]:,}',rate(g["blind"]),rate(g["sibling"]),rate(g["difference"])])
    write_table("coverage",coverage)
    write_table("primary",primary)
    write_table("sensitivity",sensitivity)


def selection_results():
    folder = RESULTS.parents[1]/"selection/results"
    panels = json.loads((folder/"selection.json").read_text())
    app = json.loads((folder/"mihon.json").read_text())
    fig, ax = plt.subplots(figsize=(7.0,2.35))
    segments = [("random","Query succeeds","#18735f"),("selection_loss","Other choice succeeds","#5b85ab"),
                ("both_fail","Both policies fail","#d49b4d"),("impossible","Budget too small","#b8bec4")]
    left = [0.,0.]
    for key, label, color in segments:
        widths = [100*panels[c]["all_ids"]["means"][key] for c in ("JOB","STATS")]
        ax.barh([1,0],widths,left=left,height=.44,color=color,label=label,edgecolor="white")
        for i,(x,w) in enumerate(zip(left,widths)):
            if w >= 5:
                ax.text(x+w/2,1-i,f"{w:.1f}",ha="center",va="center",fontsize=8,
                        color="white" if key in ("random","selection_loss") else "#232323")
        left=[a+b for a,b in zip(left,widths)]
    ax.set(xlim=(0,100),ylim=(-.45,1.45),yticks=[0,1],yticklabels=["STATS","JOB"],
           xlabel="Share of informative comparisons, equal weight per family (%)")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y",length=0)
    fig.legend(*ax.get_legend_handles_labels(),loc="lower center",ncol=4,frameon=False,fontsize=8)
    fig.subplots_adjust(left=.09,right=.99,top=.97,bottom=.41)
    save(fig,"selection-limits")
    changes=[]
    for t in app["transitions"]:
        expanded=[r for r in t["outcomes"] if r["missing"]]
        scores=[sum(r["scores"][m] for r in expanded) for m in ("schema_baseline","ddl_diff","rehearsal","literal")]
        changes.append([t["new"].removeprefix("v"),len(t["outcomes"]),len(expanded),
                        sum(r["old_digest"]==r["new_digest"] for r in expanded),*scores])
    changes.append(["All",*[sum(r[i] for r in changes) for i in range(1,len(changes[0]))]])
    write_table("releases",changes)

    rows = []
    def alert_row(label, counts):
        rows.append([label, *counts, sum(counts)])
    for key, label in (("ddl_review", "Table-level diff"), ("review", "Source rehearsal")):
        reports = [t[key] for t in app["transitions"]]
        counts = [sum(r["confusion"][c] for r in reports) for c in ("flag_expanded", "flag_stable")]
        alert_row(label, [*counts, sum(len(r["flagged_retired"]) for r in reports)])
    coverage = json.loads((folder/"column-coverage.json").read_text())["mihon"]
    alert_row("Full-column coverage", [sum(len(r[c]) for r in coverage)
                                       for c in ("flagged_expanded", "flagged_stable", "flagged_retired")])
    write_table("alerts", rows)


if __name__ == "__main__":
    design()
    results()
    tables()
    selection_results()
    from migration_figures import build
    build(write_table, save)
    from triage_tables import build as triage_tables
    triage_tables(write_table)
