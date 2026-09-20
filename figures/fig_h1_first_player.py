"""H1's canonical figure: where the claim is decided, and where it is not.

The four exact solves are not points on the same scale as the fifth reading,
and the figure refuses to draw them as if they were. An exhaustive solve returns
*which player wins*, with no interval and no sampling; EXP-017 returns a rate
under play that is heuristic for roughly seventeen plies and exact for the last
eight. Putting a Wilson interval next to four certainties is the one thing this
chart must not do by accident, so the two live in separate panels with different
axes.
"""

from __future__ import annotations

from pathlib import Path

from figures import style


def build(path: Path | None = None) -> Path:
    style.apply()
    import matplotlib.pyplot as plt

    exp017 = style.load("results/exp017-first-player-5x5.json")

    solves = [
        ("3×3 · h1", "P1"),
        ("3×3 · h2", "P1"),
        ("5×3 · h1", "P1"),
        ("5×3 · h2", "P1"),
    ]

    fig, (left, right) = plt.subplots(1, 2, figsize=(9.4, 3.9), width_ratios=[1, 1.25])

    ys = range(len(solves))
    left.barh(
        list(ys),
        [1] * len(solves),
        height=0.6,
        color=style.COLOURS["exact"],
        edgecolor=style.COLOURS["exact"],
    )
    for i, (_, winner) in enumerate(solves):
        left.text(
            0.5,
            i,
            winner,
            ha="center",
            va="center",
            color="white",
            fontsize=11,
            fontweight="bold",
        )
    left.set_yticks(list(ys))
    left.set_yticklabels([name for name, _ in solves], fontsize=8.5)
    left.invert_yaxis()
    left.set_xticks([])
    left.set_xlim(0, 1)
    left.grid(visible=False)
    left.set_title("Exact: four exhaustive solves,\nall `termination: exhausted`")
    left.set_xlabel("no interval — the value is proved, not estimated")

    rate = exp017["first_player_rate"]
    low, high = exp017["wilson_low"], exp017["wilson_high"]
    right.axvline(0.5, color=style.NEUTRAL, linewidth=1.1, linestyle="--")
    right.text(0.5, 0.62, " even", fontsize=8, color=style.NEUTRAL, va="bottom")
    right.errorbar(
        [rate],
        [0],
        xerr=[[rate - low], [high - rate]],
        fmt="o",
        markersize=9,
        color=style.COLOURS["reported"],
        ecolor=style.COLOURS["reported"],
        elinewidth=2.2,
        capsize=5,
    )
    right.annotate(
        f"{rate:.1%}  [{low:.1%}, {high:.1%}]\n"
        f"{exp017['games']:,} games, all distinct\n"
        f"proved_rate {exp017['proved_rate']:.1%} — the rate may not be quoted "
        f"without it",
        xy=(rate, 0),
        xytext=(rate, 0.30),
        fontsize=8,
        ha="center",
        color=style.COLOURS["reported"],
    )
    right.set_ylim(-0.55, 0.85)
    right.set_yticks([])
    right.set_xlim(0.46, 0.60)
    right.grid(axis="y", visible=False)
    right.set_title(
        "Statistical: the shipped 5×5, where no solve is reachable\n"
        "corroborates the direction, says nothing about perfect play"
    )
    right.set_xlabel("first-player win rate under SolverAgent in both seats")

    style.footer(
        fig,
        "figures/fig_h1_first_player.py — left panel from EXP-001 and EXP-002 as "
        "recorded in "
        "experiments/registry.md; right panel from "
        "results/exp017-first-player-5x5.json. "
        "The two panels carry different axes because an exhaustive solve and a "
        "sampled rate "
        "are not the same kind of evidence.",
    )
    fig.tight_layout(rect=(0, 0.045, 1, 1))
    out = style.save(fig, "h1-first-player.png")
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(build())
