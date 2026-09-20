"""H5's canonical figure: a chart of two quantities that could not have varied.

An unusual figure, because what it shows is the *absence* of variation. Both
halves of H5's locked measure are fixed by the rules, and the only honest way to
draw that is a flat line with the mechanism written beside it.

Left panel: placement frequency. Twenty-five cells, no passing, both hands
exhausting exactly, so every game plays each archetype twice and the joker once.
The bar chart is `[2]×12 + [1]` and it is the same in all 5,000 games.

Middle panel: win contribution. The same exhaustion gives each player one of each
archetype, so each is played once by the winner and once by the loser — a flat
100%. The joker is the exception and is worse than flat: only P1 holds it, so
the "contribution" tally reproduces the first-player split exactly. A measure
that is a second name for a quantity reported elsewhere.

Right panel: the unforced alternative, and why it is not registered. Placement
timing genuinely varies, and a uniform-random null shows it stratifies almost
entirely by rotation-orbit size. The residual is confounded by the recording
agent's own objective, so the panel is drawn in the refused colour.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from complexity.game_tree import ORBITS
from figures import style

_MOVE = re.compile(r"cell=(\d+), tile=(\d+), rotation=(\d+)")

#: Mean ply per archetype under uniform-random play, 4,000 games, seed 20260919.
#: Recomputing it here would need the engine and several minutes; the figure
#: carries the measured values and the orbit that explains them.
RANDOM_NULL: dict[str, float] = {
    "P1": 9.73,
    "P2-adj": 9.76,
    "P2-skip": 9.70,
    "P2-opp": 13.61,
    "P3-fan": 9.87,
    "P3-y": 9.82,
    "P3-tri": 16.07,
    "P4-adj": 9.64,
    "P4-skip": 9.58,
    "P4-opp": 13.81,
    "P5": 9.84,
    "P6": 19.02,
    "JOKER": 19.10,
}

_JSONL = "results/exp017-first-player-5x5.jsonl"


def _observed_plies() -> tuple[dict[str, float], int] | None:
    """Mean ply per archetype from the recorded games, if they are present.

    ``results/*.jsonl`` is gitignored, so a fresh clone does not have it. The
    figure degrades to the null-and-orbit panel rather than failing, and says
    which half is missing.
    """
    from fliphex import TILES

    path = style.ROOT / _JSONL
    if not path.exists():
        return None
    names = [t.archetype for t in TILES]
    total, count = defaultdict(int), defaultdict(int)
    games = 0
    with path.open() as handle:
        for line in handle:
            record = json.loads(line)
            if "moves" not in record:
                continue
            games += 1
            for ply, move in enumerate(record["moves"]):
                tile = int(_MOVE.search(move).group(2))
                total[names[tile]] += ply
                count[names[tile]] += 1
    return {a: total[a] / count[a] for a in count}, games


def build(path: Path | None = None) -> Path:
    style.apply()
    import matplotlib.pyplot as plt

    exp017 = style.load("results/exp017-first-player-5x5.json")
    order = [a for a in RANDOM_NULL if a != "JOKER"] + ["JOKER"]

    fig, (freq, contrib, timing) = plt.subplots(
        1, 3, figsize=(13.2, 4.4), width_ratios=[1, 1, 1.35]
    )

    counts = [2] * 12 + [1]
    freq.bar(range(13), counts, color=style.COLOURS["absent"], width=0.7)
    freq.set_xticks(range(13))
    freq.set_xticklabels(order, rotation=60, ha="right", fontsize=7)
    freq.set_ylabel("placements per game")
    freq.set_yticks([0, 1, 2])
    freq.set_title("Frequency: `[2]×12 + [1]`, every game")
    freq.text(
        0.5,
        0.82,
        "25 cells · no passing · both hands exhaust\n⟹ a constant, for any agent",
        transform=freq.transAxes,
        ha="center",
        fontsize=8,
        color=style.COLOURS["refuted"],
    )

    contrib.bar(range(12), [1.0] * 12, color=style.COLOURS["absent"], width=0.7)
    contrib.bar([12], [exp017["first_player_rate"]], color=style.FAIL, width=0.7)
    contrib.set_xticks(range(13))
    contrib.set_xticklabels(order, rotation=60, ha="right", fontsize=7)
    contrib.set_ylabel("fraction of games played by the winner")
    contrib.set_ylim(0, 1.5)
    contrib.set_title("Win contribution: flat at 1.0 — and the joker is an alias")
    contrib.annotate(
        f"{exp017['first_player_wins']:,}/{exp017['games']:,} = "
        f"{exp017['first_player_rate']:.1%}\n= the first-player rate, exactly",
        xy=(12, exp017["first_player_rate"]),
        xytext=(6.0, 1.30),
        fontsize=7.8,
        color=style.FAIL,
        arrowprops={"arrowstyle": "->", "color": style.FAIL, "linewidth": 0.9},
    )

    observed = _observed_plies()
    nulls = [RANDOM_NULL[a] for a in order]
    timing.scatter(
        range(13),
        nulls,
        marker="_",
        s=340,
        linewidths=2.4,
        color=style.NEUTRAL,
        label="uniform-random null",
    )
    for i, archetype in enumerate(order):
        timing.annotate(
            f"orbit {ORBITS[archetype]}",
            (i, RANDOM_NULL[archetype]),
            textcoords="offset points",
            xytext=(0, 7),
            fontsize=6.2,
            ha="center",
            color=style.NEUTRAL,
        )
    if observed is not None:
        means, games = observed
        timing.scatter(
            range(13),
            [means[a] for a in order],
            marker="o",
            s=52,
            color=style.COLOURS["refuted"],
            zorder=3,
            label=f"observed, {games:,} recorded games",
        )
        for i, archetype in enumerate(order):
            timing.plot(
                [i, i],
                [RANDOM_NULL[archetype], means[archetype]],
                color=style.COLOURS["refuted"],
                linewidth=1.0,
                alpha=0.5,
            )
        note = (
            "Residual is monotone in arrow count, r = −0.855.\n"
            "And it is confounded: the recording agent's objective is net flips,\n"
            "and a flip-maximiser avoids many-arrowed tiles late. Not registered."
        )
    else:
        note = (
            "Observed means need results/exp017-*.jsonl, which is gitignored.\n"
            "The null and the orbits are what a fresh clone can draw."
        )
    timing.set_xticks(range(13))
    timing.set_xticklabels(order, rotation=60, ha="right", fontsize=7)
    timing.set_ylabel("mean ply of placement")
    timing.set_title("Timing does vary — and the null is pure orbit size")
    timing.legend(loc="lower left", fontsize=7.5)
    timing.set_ylim(3, 30)
    timing.text(
        0.5,
        0.985,
        note,
        transform=timing.transAxes,
        ha="center",
        va="top",
        fontsize=7.4,
        color=style.COLOURS["refuted"],
    )

    style.footer(
        fig,
        "figures/fig_h5_forced.py — from results/exp017-first-player-5x5.json and "
        "complexity/game_tree.py for the orbits; null measured over 4,000 "
        "uniform-random "
        "games, seed 20260919. Both halves of the locked measure are forced; the third "
        "panel is drawn to explain why nothing replaced them.",
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    out = style.save(fig, "h5-forced-measures.png")
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(build())
