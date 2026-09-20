"""H2's canonical figure: a magnitude, drawn as a magnitude.

**There is no threshold line on this chart, and that is the point.** H2's
registered measure is extra-tile criticality — the fraction of solved positions
whose value changes when P1's extra tile is swapped — and it came out at
17.07%. No bar for it was ever registered, so the EXP-002 amendment of
2026-09-18 deferred its interpretation rather than reading it as a verdict. A
horizontal reference line here would manufacture the threshold the registry
declined to invent.

What decides H2 is the other layer of the chart: both deck arms return **P1** on
both solvable boards, at `termination: exhausted`. That is drawn as an
annotation rather than a curve, because it is a fact with no y-value.
"""

from __future__ import annotations

from pathlib import Path

from figures import style


def build(path: Path | None = None) -> Path:
    style.apply()
    import matplotlib.pyplot as plt

    data = style.load("results/exp002-criticality-5x3.json")
    layers = [row for row in data["layers"] if row["in_hand"]]
    ts = [row["layer"] for row in layers]
    frac = [row["critical"] / row["in_hand"] for row in layers]
    pooled = data["criticality"]

    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.bar(ts, frac, color=style.COLOURS["exact"], width=0.72)
    ax.axhline(
        pooled,
        color=style.COLOURS["fliphex"],
        linewidth=1.6,
        linestyle="-",
    )
    ax.text(
        0.2,
        pooled + 0.010,
        f"pooled {pooled:.2%}  ({data['criticality_numerator']:,} of "
        f"{data['criticality_denominator']:,} positions)",
        fontsize=8,
        ha="left",
        color=style.COLOURS["fliphex"],
    )
    ax.set_xlabel(
        "filled cells, t — over positions where the extra tile is still in hand"
    )
    ax.set_ylabel("fraction whose value changes when the tile is swapped")
    ax.set_title("Extra-tile criticality on the 5×3, by layer")
    ax.set_ylim(0, max(frac) * 2.25)

    ax.text(
        0.015,
        0.97,
        "No threshold line is drawn.\n"
        "None was ever registered, and a line here would invent one.\n"
        "Interpretation is deferred to the per-archetype reference distribution\n"
        "— see the EXP-002 amendment of 2026-09-18.",
        transform=ax.transAxes,
        fontsize=7.6,
        va="top",
        color=style.COLOURS["refuted"],
    )
    ax.text(
        0.015,
        0.775,
        "What decides H2 is not on this axis:\n"
        "both arms return P1 on 3×3 and 5×3, `termination: exhausted`,\n"
        f"with {data['verification_compared']:,} cross-arm positions compared "
        f"and {data['verification_mismatches']} mismatches where the tile is spent.",
        transform=ax.transAxes,
        fontsize=7.6,
        va="top",
        color=style.PASS,
    )

    style.footer(
        fig,
        "figures/fig_h2_criticality.py — from results/exp002-criticality-5x3.json. "
        "The 17.07% measures positional sensitivity across the tree; H2 asserts a root "
        "property. They are different claims and the chart does not merge them.",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    out = style.save(fig, "h2-extra-tile-criticality.png")
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(build())
