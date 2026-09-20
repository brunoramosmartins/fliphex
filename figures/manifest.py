"""What each figure is, and which tracked artefact it regenerates from.

**This module imports nothing but the standard library.** That is deliberate.
``matplotlib`` lives in the ``figures`` extra, not in ``dev``, so CI does not
have it — and the check that matters here is not whether a plot renders but
whether every figure has a source that a fresh clone actually contains.
``tests/test_figures.py`` reads this manifest and never imports a plotting
library.

Why the manifest exists at all
------------------------------
Phase 5 planned ``figures/`` as a replacement for three dropped notebooks and
then shipped nothing — recorded as that phase's failed attempt 7. Phase 6 made
``figures/`` a *named exit criterion* with a clause attached: **every figure
regenerates from a tracked artefact.** A clause that is not checkable is a
wish, so each entry below names its sources by repository path, and a test
asserts that each one exists *and is tracked by git*.

The last part is the one with teeth. ``results/*.jsonl`` and ``data/`` and
``notes/sources/`` are all gitignored in this project, and a figure drawn from
any of them would render on this machine and nowhere else.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Figure:
    """One canonical figure."""

    #: Output file, written into ``figures/``.
    name: str
    #: Which hypothesis it is the canonical figure for; ``None`` for support.
    hypothesis: str | None
    #: Module under ``figures`` holding a ``build(path)`` function.
    builder: str
    #: One line, for the gallery and the writeup caption.
    caption: str
    #: Repository-relative paths this figure reads. Every one must be tracked.
    sources: tuple[str, ...] = ()
    #: Modules it computes from instead of reading, when the source is code.
    computed_from: tuple[str, ...] = ()


FIGURES: tuple[Figure, ...] = (
    Figure(
        name="complexity-landscape.png",
        hypothesis="H4",
        builder="figures.fig_complexity_landscape",
        caption=(
            "FLIPHEX in the state-space / game-tree plane, with every cell "
            "graded by provenance and the unsourced ones left off rather than "
            "filled in."
        ),
        computed_from=(
            "complexity/state_space.py",
            "complexity/game_tree.py",
            "complexity/comparison.py",
        ),
    ),
    Figure(
        name="state-space-and-branching.png",
        hypothesis=None,
        builder="figures.fig_state_space_and_branching",
        caption=(
            "The layer profile is a hump; the branching profile falls "
            "monotonically. The hump is a cell-count effect, not a width one."
        ),
        computed_from=("complexity/state_space.py", "complexity/branching.py"),
    ),
    Figure(
        name="h1-first-player.png",
        hypothesis="H1",
        builder="figures.fig_h1_first_player",
        caption=(
            "Four exhaustive solves all return P1; the shipped board is not "
            "decidable and contributes one corroborative interval."
        ),
        sources=("results/exp017-first-player-5x5.json",),
    ),
    Figure(
        name="h2-extra-tile-criticality.png",
        hypothesis="H2",
        builder="figures.fig_h2_criticality",
        caption=(
            "Extra-tile criticality by layer on the 5x3. A magnitude with no "
            "registered threshold, shown as one."
        ),
        sources=("results/exp002-criticality-5x3.json",),
    ),
    Figure(
        name="h3-seeds-and-agreement.png",
        hypothesis="H3",
        builder="figures.fig_h3_seeds",
        caption=(
            "Both clauses of H3, side by side: five seeds against the "
            "prior-free UCT floor, and five champions against the 0.90 bar."
        ),
        sources=(
            "results/exp015-h3-training-5x5.json",
            "results/exp006-agreement-5x5.json",
        ),
    ),
    Figure(
        name="h5-forced-measures.png",
        hypothesis="H5",
        builder="figures.fig_h5_forced",
        caption=(
            "Both halves of H5's locked measure are fixed by the rules, and "
            "the unforced alternative is stratified by rotation-orbit size."
        ),
        sources=("results/exp017-first-player-5x5.json",),
        computed_from=("complexity/game_tree.py",),
    ),
    Figure(
        name="h6-perturbation-lattice.png",
        hypothesis="H6",
        builder="figures.fig_h6_lattice",
        caption=(
            "Every perturbation H6 names, and what the project's own decision "
            "records permit. The set is smaller than the claim."
        ),
        computed_from=("fliphex/variant.py",),
    ),
)

#: Hypotheses that must each have a canonical figure, per Phase 6's exit
#: criterion. Every one of these has a written verdict in ``docs/research.md``.
HYPOTHESES_WITH_VERDICTS: tuple[str, ...] = ("H1", "H2", "H3", "H4", "H5", "H6")


def by_name(name: str) -> Figure:
    """Look one up, raising rather than returning ``None``."""
    for figure in FIGURES:
        if figure.name == name:
            return figure
    raise KeyError(f"no figure named {name!r}; have {[f.name for f in FIGURES]}")


def covered() -> set[str]:
    """Hypotheses that have a canonical figure."""
    return {f.hypothesis for f in FIGURES if f.hypothesis is not None}


def uncovered() -> list[str]:
    """Hypotheses with a verdict and no figure. Should be empty."""
    return [h for h in HYPOTHESES_WITH_VERDICTS if h not in covered()]
