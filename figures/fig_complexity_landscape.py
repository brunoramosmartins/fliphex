"""FLIPHEX in the two-axis complexity landscape — H4's canonical figure.

Two panels, because the data is shaped that way and pretending otherwise would
be the dishonest option. Only four games in the table have a sourced figure on
*both* axes, so the plane is nearly empty; the state-space axis alone has seven.
Drawing a plane with four points and a strip with seven says what is known.
Drawing a full plane would mean borrowing the missing cells from a table whose
reproductions disagree.

The two facts the figure exists to show:

* **checkers sits to the right of FLIPHEX and was weakly solved anyway** —
  H4's own premise, and it survives;
* **Othello sits almost level with FLIPHEX on the vertical axis and was weakly
  solved in 2023** — which H4's "out of reach" reading does not survive.
"""

from __future__ import annotations

from pathlib import Path

from complexity.comparison import Provenance, reversi_6x6_ceiling, table
from figures import style


def build(path: Path | None = None) -> Path:
    style.apply()
    import matplotlib.pyplot as plt

    rows = table()
    fig, (plane, strip) = plt.subplots(
        2, 1, figsize=(7.8, 8.6), height_ratios=[1.35, 1]
    )

    # -- the plane: games with a sourced figure on both axes ----------------
    both = [r for r in rows if r.state_space.log10 and r.game_tree.log10]
    for row in both:
        fliphex = row.game.startswith("FLIPHEX")
        exact = row.state_space.provenance is Provenance.EXACT
        plane.scatter(
            row.state_space.log10,
            row.game_tree.log10,
            s=150 if fliphex else 110,
            marker="o" if row.solved != "unsolved" else "s",
            facecolor=style.COLOURS["fliphex" if fliphex else "verified"]
            if exact
            else "white",
            edgecolor=style.COLOURS["fliphex" if fliphex else "verified"],
            linewidth=1.8,
            zorder=3,
        )
        plane.annotate(
            f"{row.game}\n{row.solved}",
            (row.state_space.log10, row.game_tree.log10),
            textcoords="offset points",
            xytext=(11, 4 if row.game == "FLIPHEX 5×5" else -4),
            va="bottom" if row.game == "FLIPHEX 5×5" else "top",
            fontsize=7.5,
            color=style.NEUTRAL,
        )

    shipped = next(r for r in rows if r.game == "FLIPHEX 5×5")
    othello = next(r for r in rows if r.game == "Othello 8×8")
    plane.annotate(
        "",
        xy=(othello.state_space.log10, othello.game_tree.log10),
        xytext=(shipped.state_space.log10, shipped.game_tree.log10),
        arrowprops={
            "arrowstyle": "<->",
            "color": style.FAIL,
            "linewidth": 1.1,
            "linestyle": (0, (4, 2)),
        },
    )
    plane.text(
        (shipped.state_space.log10 + othello.state_space.log10) / 2,
        othello.game_tree.log10 - 5.5,
        "4.2× apart on this axis — and Othello\nwas weakly solved in 2023",
        fontsize=7.5,
        color=style.FAIL,
        ha="center",
        va="top",
    )
    plane.set_xlabel("state-space complexity, log₁₀")
    plane.set_ylabel("game-tree complexity, log₁₀")
    plane.set_title(
        f"Only {len(both)} of {len(rows)} games carry a sourced figure on both axes"
    )
    plane.set_xlim(3, 33)
    plane.set_ylim(8, 70)

    # -- the strip: state space alone, where most of the data is ------------
    with_space = sorted(
        (r for r in rows if r.state_space.log10), key=lambda r: r.state_space.log10
    )
    labels, values, colours, edges, solved = [], [], [], [], []
    for row in with_space:
        fliphex = row.game.startswith("FLIPHEX")
        exact = row.state_space.provenance is Provenance.EXACT
        colour = style.COLOURS["fliphex" if fliphex else "verified"]
        labels.append(row.game)
        values.append(row.state_space.log10)
        colours.append(colour if exact else "white")
        edges.append(colour)
        solved.append(row.solved)

    y = range(len(labels))
    strip.barh(
        list(y), values, height=0.62, color=colours, edgecolor=edges, linewidth=1.4
    )
    for i, (value, state) in enumerate(zip(values, solved, strict=True)):
        strip.text(
            value + 0.5,
            i,
            f"{value:.2f}   {state}",
            va="center",
            fontsize=7,
            color=style.NEUTRAL,
        )
    strip.set_yticks(list(y))
    strip.set_yticklabels(labels, fontsize=8)
    strip.invert_yaxis()

    ceiling, ceiling_log = reversi_6x6_ceiling()
    strip.axvline(
        ceiling_log, color=style.COLOURS["refuted"], linewidth=1.2, linestyle=":"
    )
    strip.text(
        ceiling_log + 0.8,
        -0.35,
        f"3³⁶ = {ceiling:.3g}, the hard ceiling for 6×6 Reversi.\n"
        "Its widely cited ~10²⁰ exceeds this by 666×, so that row is refused.",
        fontsize=7,
        color=style.COLOURS["refuted"],
        va="top",
        ha="left",
    )
    strip.set_xlim(0, 58)
    strip.set_xlabel("state-space complexity, log₁₀")
    no_tree = sum(1 for r in rows if r.game_tree.log10 is None)
    strip.set_title(
        f"{len(labels)} games have a sourced state space; "
        f"{no_tree} have nothing on the tree axis"
    )
    strip.grid(axis="y", visible=False)

    handles = [
        plt.Line2D(
            [],
            [],
            marker="o",
            linestyle="",
            markerfacecolor=style.COLOURS["fliphex"],
            markeredgecolor=style.COLOURS["fliphex"],
            markersize=9,
            label="FLIPHEX, computed exactly here",
        ),
        plt.Line2D(
            [],
            [],
            marker="o",
            linestyle="",
            markerfacecolor="white",
            markeredgecolor=style.COLOURS["verified"],
            markersize=9,
            label="published estimate, quote checked against the source",
        ),
        plt.Line2D(
            [],
            [],
            marker="s",
            linestyle="",
            markerfacecolor="white",
            markeredgecolor=style.NEUTRAL,
            markersize=8,
            label="square = unsolved",
        ),
    ]
    plane.legend(handles=handles, loc="upper left")

    style.footer(
        fig,
        "figures/fig_complexity_landscape.py — computed from "
        "complexity/{state_space,game_tree,comparison}.py; "
        "definitions and solved-status taxonomy from Allis 1994 §1.5 and §6.2. "
        "Cells with no sourced figure are absent, not interpolated.",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out = style.save(fig, "complexity-landscape.png")
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(build())
