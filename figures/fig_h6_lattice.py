"""H6's canonical figure: the whole perturbation set, drawn to scale.

H6 asks whether the design's balance is robust to bounded counterfactual
variation, and names two families: board size, and deck swaps. The figure draws
every cell either family can reach, and the point is how few there are and why.

The board axis is constrained by **adr-011**: every legal board has an odd cell
count and gives the first player the extra tile, so P1 moves last on all of them,
shipped board included. The 4×4 — the one board that would have broken that
pattern — is withdrawn, and its cell is drawn struck through.

The deck axis has exactly two positions, because ``Variant`` has no deck lever
at all: ``archetypes_for`` is deterministic in capacity, so the only reachable
deck perturbation is the ``arm`` swap, which is H2. The named example, removing
the chiral ``P3-y``, is outside the lattice entirely — **adr-009 clause 1
requires it in every variant, and was ratified five days before the hypotheses
locked.**
"""

from __future__ import annotations

from pathlib import Path

from figures import style
from fliphex.variant import ANCHORS, Arm, Variant

BOARDS = [(3, 3), (5, 3), (4, 4), (5, 5)]


def build(path: Path | None = None) -> Path:
    style.apply()
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig, ax = plt.subplots(figsize=(8.8, 4.8))

    for col, (cols, rows) in enumerate(BOARDS):
        for row, arm in enumerate((Arm.H1, Arm.H2)):
            withdrawn = (cols, rows) == (4, 4)
            try:
                Variant(cols, rows, arm)
                constructible = True
            except ValueError:
                constructible = False

            if withdrawn:
                face, edge, label = (
                    "white",
                    style.COLOURS["refuted"],
                    "withdrawn\nadr-011",
                )
            elif not constructible:
                face, edge, label = (
                    "white",
                    style.COLOURS["absent"],
                    "cannot exist\nno tile to promote",
                )
            elif (cols, rows) == (5, 5):
                face, edge, label = (
                    "white",
                    style.COLOURS["reported"],
                    "not decidable\n54.2% corroborative",
                )
            else:
                face, edge, label = (
                    style.COLOURS["exact"],
                    style.COLOURS["exact"],
                    "P1\nexhausted",
                )

            ax.add_patch(
                Rectangle(
                    (col - 0.42, row - 0.36),
                    0.84,
                    0.72,
                    facecolor=face,
                    edgecolor=edge,
                    linewidth=1.8,
                )
            )
            ax.text(
                col,
                row,
                label,
                ha="center",
                va="center",
                fontsize=8,
                color="white" if face != "white" else edge,
                fontweight="bold" if face != "white" else "normal",
            )
            if withdrawn:
                ax.plot(
                    [col - 0.42, col + 0.42],
                    [row - 0.36, row + 0.36],
                    color=style.COLOURS["refuted"],
                    linewidth=1.4,
                )

    ax.set_xticks(range(len(BOARDS)))
    ax.set_xticklabels([f"{c}×{r}\n{c * r} cells" for c, r in BOARDS], fontsize=8.5)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(
        ["h1\nextra tile = joker", "h2\nextra tile = next archetype"], fontsize=8.5
    )
    ax.set_xlim(-0.65, len(BOARDS) - 0.35)
    ax.set_ylim(-1.55, 1.95)
    ax.grid(visible=False)
    ax.set_title("Every perturbation H6 can reach — and the ones it cannot")

    ax.text(
        -0.6,
        1.58,
        "adr-011 holds the mechanism constant across the whole board axis:\n"
        "odd cell count, first player takes the extra tile, so P1 moves last on every "
        "legal board.",
        fontsize=8,
        color=style.NEUTRAL,
        va="center",
    )
    ax.text(
        len(BOARDS) - 0.4,
        -1.45,
        f"The named deck swap — removing the chiral `P3-y` — is off this lattice.\n"
        f"adr-009 clause 1: always include {' and '.join(f'`{a}`' for a in ANCHORS)}.\n"
        "Ratified 2026-07-31; the hypotheses locked 2026-08-05.",
        fontsize=8,
        color=style.COLOURS["refuted"],
        ha="right",
        va="bottom",
    )

    style.footer(
        fig,
        "figures/fig_h6_lattice.py — constructibility probed against "
        "fliphex/variant.py; "
        "verdicts from EXP-001, EXP-002 and EXP-017 as recorded in "
        "experiments/registry.md. "
        "Every exact cell is one H1 and H2 already used; H6 adds no new computation.",
    )
    fig.tight_layout(rect=(0, 0.045, 1, 1))
    out = style.save(fig, "h6-perturbation-lattice.png")
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(build())
