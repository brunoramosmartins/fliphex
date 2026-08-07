"""Tests for solver.reachable — the EXP-005 instrument.

The module counts configurations with **no legal predecessor**, and it does so
by marking successors forward rather than by inverting the flip rule. So the
test that matters is the one that checks the marking against the reference's own
move generation: if ``solver/reachable.py`` ever grew its own idea of what a
legal move produces, this is where it would show.

The 3×3 tests here only touch layers small enough to be free (711,963
configurations is ``EXP-001``'s budget, not the suite's).
"""

import pytest

from fliphex.moves import apply_move, legal_moves
from fliphex.variant import Arm, Variant
from solver.reachable import Reachability, measure
from solver.retrograde import LayerIndex

#: Boards where the reference can enumerate every layer in test time.
SMALL = [Variant(5, 1), Variant(5, 1, Arm.H2)]


def reference_reachable(variant, t: int) -> set[int]:
    """Indices in layer ``t`` that some layer ``t-1`` move produces.

    Built entirely through ``legal_moves``/``apply_move``/``LayerIndex`` — the
    legible path, with no bit twiddling — so agreement is evidence rather than
    a restatement.
    """
    board = variant.board()
    below = LayerIndex(variant, t - 1)
    above = LayerIndex(variant, t)
    marked = set()
    for index in range(below.size):
        state = below.decode(index)
        for move in legal_moves(board, state):
            marked.add(above.encode(apply_move(board, state, move)))
    return marked


def bits_to_set(marks: bytearray, size: int) -> set[int]:
    return {i for i in range(size) if marks[i >> 3] >> (i & 7) & 1}


# -- the equivalence, which is the whole contract -----------------------------


@pytest.mark.parametrize("variant", SMALL)
def test_marking_matches_the_reference_move_generation(variant):
    reach = Reachability(variant)
    for t in range(1, variant.n_cells + 1):
        expected = reference_reachable(variant, t)
        actual = bits_to_set(reach.predecessor_bits(t), reach.layer_size(t))
        assert actual == expected, f"layer {t} differs"


@pytest.mark.parametrize("variant", SMALL)
def test_counts_agree_with_the_marked_set(variant):
    reach = Reachability(variant)
    for t in range(1, variant.n_cells + 1):
        layer = reach.layer(t)
        assert layer.total == reach.layer_size(t)
        assert layer.with_predecessor == len(reference_reachable(variant, t))
        assert layer.orphans == layer.total - layer.with_predecessor


# -- structure ----------------------------------------------------------------


def test_layer_zero_is_reachable_by_definition():
    """The opening has no predecessor and needs none."""
    reach = Reachability(Variant(5, 1))
    layer = reach.layer(0)
    assert layer.total == 1
    assert layer.orphans == 0
    with pytest.raises(ValueError):
        reach.predecessor_bits(0)


@pytest.mark.parametrize("variant", [Variant(5, 1), Variant(3, 3)])
def test_layer_one_is_exactly_half(variant):
    """The calibration figure adr-010's Phase 3 amendment turns on.

    At ``t = 1`` the closed form counts both colourings of the single placed
    cell, but only the first player's colour can occur — so exactly half of
    layer 1 has no predecessor. This is the concrete case behind "a correct
    reachable-closure enumerator disagrees with the bound by exactly 2× at
    layer 1", and it is the cheapest place to notice the index drifting.
    """
    reach = Reachability(variant)
    layer = reach.layer(1)
    assert layer.total == 2 * layer.with_predecessor
    assert layer.orphan_fraction == pytest.approx(0.5)


def test_the_full_measurement_reports_every_layer():
    variant = Variant(5, 1)
    result = measure(variant)
    assert [layer.t for layer in result.layers] == list(range(variant.n_cells + 1))
    assert result.total == sum(
        Reachability(variant).layer_size(t) for t in range(variant.n_cells + 1)
    )
    assert 0.0 <= result.orphan_fraction <= 1.0
    assert result.as_dict()["orphans"] == result.orphans


def test_every_layer_has_something_reachable():
    """A floor that follows from the rules, so it can be asserted without a run.

    A real game passes through every layer, so each one has at least one
    configuration with a predecessor. A layer marked empty would mean the child
    index landed somewhere the enumeration never visits — the failure mode most
    likely to look plausible in an aggregate.
    """
    variant = Variant(5, 1)
    reach = Reachability(variant)
    for t in range(1, variant.n_cells + 1):
        assert reach.layer(t).with_predecessor > 0, f"layer {t} marked nothing"
