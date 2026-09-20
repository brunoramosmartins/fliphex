"""The layer profile is a hump; the branching profile is not. Support for H4.

These two panels exist together because reading either alone invites the wrong
conclusion. The state-space profile peaks in the middle, which looks like "the
game gets more complex in the middlegame". The branching profile falls
*strictly* at every ply. The hump is therefore a ``C(n, t)`` cell-count effect
and not a width effect, and the two charts side by side are the cheapest way to
say so.
"""

from __future__ import annotations

from pathlib import Path

from complexity.branching import profile as branching_profile
from complexity.state_space import profile as space_profile
from figures import style
from fliphex.variant import Arm, Variant


def build(path: Path | None = None) -> Path:
    style.apply()
    import matplotlib.pyplot as plt

    variant = Variant(5, 5, Arm.H1)
    space = space_profile(variant)
    plies = branching_profile(variant)

    fig, (left, right) = plt.subplots(1, 2, figsize=(9.6, 4.1))

    ts = [layer.t for layer in space.layers]
    sizes = [layer.configurations for layer in space.layers]
    left.bar(ts, sizes, color=style.COLOURS["fliphex"], width=0.72)
    left.set_yscale("log")
    left.set_xlabel("filled cells, t")
    left.set_ylabel("configurations in the layer")
    left.set_title(f"State space: a hump, peaking at t = {space.peak.t}")
    left.axvline(space.peak.t, color=style.NEUTRAL, linewidth=1.0, linestyle=":")
    left.text(
        0.03,
        0.965,
        f"peak layer holds {space.peak.configurations:.3g}\n"
        f"whole space {space.configurations:.4g}\n"
        f"reachable {space.reachable:.4g} ({space.orphan_fraction:.4%} orphans)",
        transform=left.transAxes,
        fontsize=7.5,
        va="top",
        color=style.NEUTRAL,
    )

    xs = [ply.t for ply in plies]
    right.fill_between(
        xs,
        [ply.minimum for ply in plies],
        [ply.maximum for ply in plies],
        color=style.COLOURS["fliphex"],
        alpha=0.16,
        label="narrowest to widest node",
    )
    right.plot(
        xs,
        [ply.mean for ply in plies],
        color=style.COLOURS["fliphex"],
        linewidth=2.0,
        label="node-weighted mean",
    )
    right.plot(
        xs,
        [ply.uniform_mean for ply in plies],
        color=style.COLOURS["reported"],
        linewidth=1.4,
        linestyle="--",
        label="mean over spent sets, unweighted",
    )
    right.set_xlabel("ply, t")
    right.set_ylabel("legal moves")
    right.set_title("Branching: falls strictly, every ply")
    right.legend(loc="upper right")
    last = plies[-1]
    right.annotate(
        f"last ply: {last.minimum}–{last.maximum} moves,\njust the final tile's orbit",
        xy=(last.t, last.mean),
        xytext=(last.t - 8.5, 230),
        fontsize=7.5,
        color=style.NEUTRAL,
        arrowprops={"arrowstyle": "->", "color": style.NEUTRAL, "linewidth": 0.8},
    )

    style.footer(
        fig,
        "figures/fig_state_space_and_branching.py — computed from "
        "complexity/state_space.py and complexity/branching.py. The weighted mean "
        "is prefixes(t+1)/prefixes(t) exactly, and the means telescope to the game "
        "tree.",
    )
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    out = style.save(fig, "state-space-and-branching.png")
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(build())
