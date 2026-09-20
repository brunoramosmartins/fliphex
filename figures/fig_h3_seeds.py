"""H3's canonical figure: both clauses, and both of them failing.

Left, the stability clause. Five independently trained seeds against the
prior-free UCT floor, with the registered bar drawn because this one *was*
registered — 114 of 200 games, the smallest count whose Wilson lower bound
clears 50%. Seed 4 misses it by two games, and per the pre-registered
falsifiability clause a failing seed is recorded, never averaged away.

Right, the agreement clause. The same five champions against the 0.90 bar
pre-declared on 2026-08-05, on the shipped-5×5 endgame member. The gap is wide
enough that the threshold's weak derivation did not matter here — which is a
statement about luck, not about design, and the bar is drawn dashed to say so.

Two context marks the rates may not be quoted without: a random mover, and the
champions' own raw policy head with no search.
"""

from __future__ import annotations

from pathlib import Path

from figures import style


def build(path: Path | None = None) -> Path:
    style.apply()
    import matplotlib.pyplot as plt

    training = style.load("results/exp015-h3-training-5x5.json")
    agreement = style.load("results/exp006-agreement-5x5.json")

    seeds = sorted(training["seeds"], key=int)
    floors = [training["seeds"][s]["floors"]["equal_simulations"] for s in seeds]
    rates = [f["win_rate"] for f in floors]
    lows = [f["ci"][0] for f in floors]
    highs = [f["ci"][1] for f in floors]
    clears = [f["clears_floor"] for f in floors]
    games = floors[0]["games"]
    bar = 114 / games

    fig, (left, right) = plt.subplots(1, 2, figsize=(10.0, 4.3))

    xs = range(len(seeds))
    for i, (rate, low, high, ok) in enumerate(
        zip(rates, lows, highs, clears, strict=True)
    ):
        colour = style.PASS if ok else style.FAIL
        left.errorbar(
            [i],
            [rate],
            yerr=[[rate - low], [high - rate]],
            fmt="o",
            markersize=8,
            color=colour,
            ecolor=colour,
            elinewidth=2.0,
            capsize=4,
        )
    left.axhline(bar, color=style.NEUTRAL, linewidth=1.3)
    left.text(
        len(seeds) - 0.55,
        bar + 0.006,
        f"registered floor: {114}/{games} = {bar:.1%}",
        fontsize=7.6,
        ha="right",
        color=style.NEUTRAL,
    )
    left.axhline(0.5, color=style.GRID, linewidth=1.0, linestyle=":")
    worst = min(range(len(rates)), key=lambda i: rates[i])
    left.annotate(
        f"seed {seeds[worst]}: {rates[worst]:.1%}\ntwo games short",
        xy=(worst, rates[worst]),
        xytext=(worst + 0.35, rates[worst] - 0.075),
        fontsize=7.8,
        color=style.FAIL,
        arrowprops={"arrowstyle": "->", "color": style.FAIL, "linewidth": 0.9},
    )
    left.set_xticks(list(xs))
    left.set_xticklabels([f"seed {s}" for s in seeds], fontsize=8)
    left.set_ylabel("win rate vs prior-free UCT, 400 simulations each")
    left.set_title("Clause 1 — stability: four clear the floor, one does not")
    left.set_ylim(0.44, 0.88)

    champions = [
        agreement["seeds"][s]["search"]["registered"]
        for s in sorted(agreement["seeds"], key=int)
    ]
    crates = [c["pooled"]["rate"] for c in champions]
    clows = [c["pooled"]["ci"][0] for c in champions]
    chighs = [c["pooled"]["ci"][1] for c in champions]
    priors = [
        agreement["seeds"][s]["prior"]["registered"]["pooled"]["rate"]
        for s in sorted(agreement["seeds"], key=int)
    ]
    threshold = agreement["threshold"]
    random_rate = agreement["random_move_baseline"]

    for i, (rate, low, high) in enumerate(zip(crates, clows, chighs, strict=True)):
        right.errorbar(
            [i],
            [rate],
            yerr=[[rate - low], [high - rate]],
            fmt="o",
            markersize=8,
            color=style.FAIL,
            ecolor=style.FAIL,
            elinewidth=2.0,
            capsize=4,
        )
    right.scatter(
        list(range(len(priors))),
        priors,
        marker="_",
        s=180,
        color=style.COLOURS["reported"],
        linewidths=2.0,
        label="raw policy head, no search",
    )
    right.axhline(threshold, color=style.NEUTRAL, linewidth=1.3, linestyle="--")
    right.text(
        len(crates) - 0.55,
        threshold + 0.008,
        f"pre-declared bar {threshold:.2f} — never derived",
        fontsize=7.6,
        ha="right",
        color=style.NEUTRAL,
    )
    right.axhline(random_rate, color=style.GRID, linewidth=1.2, linestyle=":")
    right.text(
        -0.45,
        random_rate + 0.008,
        f"random mover {random_rate:.1%}",
        fontsize=7.6,
        color=style.NEUTRAL,
    )
    right.set_xticks(list(range(len(crates))))
    right.set_xticklabels(
        [f"seed {s}" for s in sorted(agreement["seeds"], key=int)], fontsize=8
    )
    right.set_ylabel("value-preservation agreement on won positions")
    right.set_title("Clause 2 — agreement: the best upper limit is 14 points short")
    right.set_ylim(0.15, 0.98)
    right.legend(loc="lower right")

    style.footer(
        fig,
        "figures/fig_h3_seeds.py — from results/exp015-h3-training-5x5.json and "
        "results/exp006-agreement-5x5.json. Both clauses are rejected independently; "
        "no cause for either failure is established, and nothing here varies "
        "architecture, "
        "budget or training length.",
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    out = style.save(fig, "h3-seeds-and-agreement.png")
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(build())
