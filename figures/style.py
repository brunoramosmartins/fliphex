"""Shared look, and the two conventions the figures use to stay honest.

**Provenance is drawn, not annotated.** A number this project computed exactly
and a number lifted from a paper should not look alike on a chart any more than
they do in ``complexity/comparison.py``'s table. Filled markers are exact,
hollow ones are cited, and a cell nobody could source is simply absent — never
interpolated to keep a line continuous.

**A threshold is drawn only if it was registered.** Where a magnitude has no
pre-declared bar — H2's extra-tile criticality is the standing example — the
axis carries no reference line, because a line on a chart reads as a threshold
whether or not one was ever declared.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

FIGURES_DIR = Path(__file__).resolve().parent
ROOT = FIGURES_DIR.parent

#: Exact, verified, cited-but-unopened, refused. Mirrors Provenance in
#: ``complexity/comparison.py`` so the two never drift apart visually.
COLOURS: dict[str, str] = {
    "exact": "#1b3a6b",
    "verified": "#2e7d5b",
    "reported": "#b07d2b",
    "refuted": "#a33a3a",
    "absent": "#9aa0a6",
    "fliphex": "#7b2d8e",
}

#: Verdict shading, used where a figure shows a pass/fail against a bar.
PASS = "#2e7d5b"
FAIL = "#a33a3a"
NEUTRAL = "#5a6370"
GRID = "#d8dbe0"


def apply() -> None:
    """Set the rcParams. Called by every builder before it draws."""
    import matplotlib

    matplotlib.use("Agg")  # no display in CI, on a server, or over ssh
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "figure.dpi": 140,
            "savefig.dpi": 140,
            "savefig.bbox": "tight",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.titleweight": "bold",
            "axes.labelsize": 9,
            "axes.edgecolor": "#5a6370",
            "axes.linewidth": 0.8,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "legend.frameon": False,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def footer(fig: Any, text: str) -> None:
    """Stamp the provenance line every figure carries.

    A figure that leaves the repository without saying what produced it is a
    picture, not a result.
    """
    fig.text(
        0.005,
        0.005,
        text,
        fontsize=6.5,
        color=NEUTRAL,
        ha="left",
        va="bottom",
    )


def save(fig: Any, name: str) -> Path:
    """Write into ``figures/`` and return the path."""
    path = FIGURES_DIR / name
    fig.savefig(path)
    return path


def load(relative: str) -> Any:
    """Read a tracked JSON artefact by repository-relative path."""
    import json

    return json.loads((ROOT / relative).read_text())
