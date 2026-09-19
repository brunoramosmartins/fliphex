"""Tests for ``complexity/branching.py``.

The one that carries the module is ``test_the_identity_holds_on_every_ply``. The
distribution here is built by enumerating the mover's spent sets and weighting
each by the product of its orbits; ``complexity.game_tree.prefixes`` reaches the
same tree by elementary symmetric polynomials over the whole hand, with no
subsets anywhere. That the node-weighted mean at ply ``t`` equals
``prefixes(t + 1) / prefixes(t)`` -- exactly, as a ratio of integers, on every
ply of every board -- is the only reason to believe the weighting is right.

It is also the test that caught the weighting being wrong the first time. The
original implementation summed only the mover's own spent-set weights, leaving
out the cell arrangement, the play orders and the other player's hand. The mean
was unaffected, because those factors are constant across the loop; the node
count was out by many orders of magnitude, and this identity said so.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from complexity.branching import (
    Branching,
    branching_at,
    cross_check,
    profile,
    self_check,
)
from complexity.game_tree import ORBITS, games, prefixes
from fliphex.variant import Arm, Variant

BOARDS = [(5, 1), (3, 3), (5, 3), (5, 5)]


def _variants() -> list[Variant]:
    out = []
    for cols, rows in BOARDS:
        arms = [Arm.H1] if (cols, rows) == (5, 5) else [Arm.H1, Arm.H2]
        out += [Variant(cols, rows, arm) for arm in arms]
    return out


VARIANTS = _variants()
IDS = [v.name for v in VARIANTS]


# -- the identity -----------------------------------------------------------


@pytest.mark.parametrize("variant", VARIANTS, ids=IDS)
def test_the_identity_holds_on_every_ply(variant):
    """Node-weighted mean == prefixes(t + 1) / prefixes(t), exactly."""
    for ply in profile(variant):
        assert ply.mean_exact == Fraction(
            prefixes(variant, ply.t + 1), prefixes(variant, ply.t)
        )


@pytest.mark.parametrize("variant", VARIANTS, ids=IDS)
def test_node_counts_are_the_prefix_counts(variant):
    """The weighting is a node count, not an unnormalised score."""
    for ply in profile(variant):
        assert ply.nodes == prefixes(variant, ply.t)


@pytest.mark.parametrize("variant", VARIANTS, ids=IDS)
def test_the_means_telescope_to_the_game_tree(variant):
    """No Jensen gap: these are ratios, so the product is exact."""
    product = Fraction(1)
    for ply in profile(variant):
        product *= ply.mean_exact
    assert product == games(variant)


def test_self_check_is_clean():
    assert self_check() == []


@pytest.mark.parametrize("variant", VARIANTS, ids=IDS)
def test_cross_check_is_clean(variant):
    assert cross_check(variant) == []


# -- the shape --------------------------------------------------------------


def test_the_shipped_opening_is_1450_and_uniform():
    ply = branching_at(Variant(5, 5, Arm.H1), 0)
    assert ply.minimum == ply.maximum == 1450
    assert ply.distinct == 1
    assert ply.spread == 1.0


@pytest.mark.parametrize("variant", VARIANTS, ids=IDS)
def test_the_first_two_plies_are_uniform(variant):
    """Neither mover has spent a tile yet, so there is nothing to vary."""
    for t in (0, 1):
        assert branching_at(variant, t).distinct == 1


@pytest.mark.parametrize("variant", VARIANTS, ids=IDS)
def test_the_mean_width_falls_strictly_every_ply(variant):
    """Both factors shrink at once: fewer cells and fewer tiles."""
    means = [ply.mean_exact for ply in profile(variant)]
    assert all(b < a for a, b in zip(means, means[1:], strict=False))


@pytest.mark.parametrize("variant", VARIANTS, ids=IDS)
def test_the_spread_never_narrows_within_one_player_s_plies(variant):
    """Across movers it zigzags, because the two hands differ in size."""
    for start in (0, 1):
        spreads = [ply.spread for ply in profile(variant)[start::2]]
        assert all(b >= a for a, b in zip(spreads, spreads[1:], strict=False))


@pytest.mark.parametrize("variant", VARIANTS, ids=IDS)
def test_the_weighting_never_makes_the_tree_look_wider(variant):
    """The node-weighted mean sits at or below the mean over spent sets.

    Equality only at the two opening plies, where there is one spent set.
    Everywhere else the weighting favours having spent the wide tiles, so the
    typical node is narrower than the hands alone suggest.
    """
    for ply in profile(variant):
        assert ply.mean <= ply.uniform_mean + 1e-9
        if ply.distinct > 1:
            assert ply.mean < ply.uniform_mean


def test_the_gap_to_the_unweighted_mean_grows():
    """8% at t = 8, 19% at t = 16, 36% at the last ply."""
    plies = profile(Variant(5, 5, Arm.H1))
    gaps = [1 - plies[t].mean / plies[t].uniform_mean for t in (8, 16, 24)]
    assert gaps == sorted(gaps)
    assert 0.07 < gaps[0] < 0.09
    assert 0.34 < gaps[2] < 0.38


# -- the extremes -----------------------------------------------------------


@pytest.mark.parametrize("variant", VARIANTS, ids=IDS)
def test_the_extremes_are_the_extreme_spent_sets(variant):
    """Widest node = spent the narrowest tiles; narrowest = spent the widest."""
    for ply in profile(variant):
        hand = variant.deck_names()[0 if ply.mover_is_first else 1]
        orbits = sorted(ORBITS[tile] for tile in hand)
        spent, empty = ply.t // 2, variant.n_cells - ply.t
        available = sum(orbits)
        widest = orbits[len(orbits) - spent :] if spent else []
        assert ply.maximum == empty * (available - sum(orbits[:spent]))
        assert ply.minimum == empty * (available - sum(widest))


@pytest.mark.parametrize("variant", VARIANTS, ids=IDS)
def test_the_last_ply_is_one_cell_times_one_tile_s_orbit(variant):
    """One cell, one tile: the width is that tile's orbit and nothing else."""
    ply = branching_at(variant, variant.n_cells - 1)
    hand = variant.deck_names()[0 if ply.mover_is_first else 1]
    orbits = {ORBITS[tile] for tile in hand}
    assert ply.minimum == min(orbits)
    assert ply.maximum == max(orbits)


def test_the_shipped_last_ply_runs_from_one_to_six():
    """P6 and the joker have one rotation; an ordinary tile has six."""
    ply = branching_at(Variant(5, 5, Arm.H1), 24)
    assert (ply.minimum, ply.maximum) == (1, 6)
    assert ply.spread == 6.0


# -- bookkeeping ------------------------------------------------------------


@pytest.mark.parametrize("variant", VARIANTS, ids=IDS)
def test_the_mover_alternates_and_the_first_player_moves_last(variant):
    """adr-011 gives the first player the extra tile, so it takes ply n - 1."""
    plies = profile(variant)
    assert [ply.mover_is_first for ply in plies][:4] == [True, False, True, False]
    assert plies[-1].mover_is_first


@pytest.mark.parametrize("variant", VARIANTS, ids=IDS)
def test_there_is_one_entry_per_ply_and_no_entry_past_the_board(variant):
    assert len(profile(variant)) == variant.n_cells
    with pytest.raises(ValueError, match="t must be in"):
        branching_at(variant, variant.n_cells)


@pytest.mark.parametrize("t", [-1, 25])
def test_branching_at_rejects_a_ply_off_the_board(t):
    with pytest.raises(ValueError, match="t must be in"):
        branching_at(Variant(5, 5, Arm.H1), t)


@pytest.mark.parametrize("variant", VARIANTS, ids=IDS)
def test_widths_are_sorted_and_positive(variant):
    for ply in profile(variant):
        widths = [moves for moves, _ in ply.width]
        assert widths == sorted(widths)
        assert all(moves > 0 for moves in widths)
        assert all(count > 0 for _, count in ply.width)


def test_as_dict_round_trips_through_json():
    import json

    ply = branching_at(Variant(3, 3, Arm.H1), 4)
    payload = json.loads(json.dumps(ply.as_dict()))
    assert payload["ply"] == 4
    assert payload["mover"] == 1
    assert payload["nodes"] == prefixes(Variant(3, 3, Arm.H1), 4)


def test_branching_is_frozen():
    ply = branching_at(Variant(3, 3, Arm.H1), 0)
    with pytest.raises(AttributeError):
        ply.t = 1  # type: ignore[misc]


def test_uniform_mean_is_a_field_because_width_cannot_recover_it():
    """The collapse to distinct widths loses how many spent sets made each."""
    assert "uniform_mean" in Branching.__dataclass_fields__


def test_imports_nothing_from_solver_or_az():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parent.parent / "complexity" / "branching.py"
    ).read_text()
    for forbidden in ("import solver", "from solver", "import az", "from az"):
        assert forbidden not in source
