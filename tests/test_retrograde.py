"""Tests for solver.retrograde.

The load-bearing test is :func:`test_retrograde_agrees_with_forward_search` —
that is adr-010 **V3**, the same variant solved twice by fundamentally different
methods, and it is the entire reason both a forward searcher and a backward
sweep exist in this package.

Everything runs on ``Variant(5, 1)``: 5 cells, 1023 configurations across all
layers, so a full sweep is instant. The 3×3 (711,963 configurations) is
``EXP-001``'s job, not the test suite's.
"""

import pytest

from fliphex.state import Colour, GameState
from fliphex.variant import Arm, Variant
from solver.minimax import LOSS, WIN
from solver.minimax import solve as forward_solve
from solver.retrograde import (
    LayerIndex,
    rank_subset,
    solve,
    unrank_subset,
)

TINY = Variant(5, 1)


# -- the combinatorial number system ------------------------------------------


@pytest.mark.parametrize("k", [0, 1, 2, 3, 4])
def test_rank_and_unrank_are_inverse(k):
    from math import comb

    for rank in range(comb(8, k)):
        items = unrank_subset(rank, k)
        assert rank_subset(items) == rank
        assert list(items) == sorted(items)
        assert len(set(items)) == k


def test_rank_is_dense_from_zero():
    """A gap or a duplicate would silently corrupt a whole layer."""
    from math import comb

    ranks = {rank_subset(unrank_subset(r, 3)) for r in range(comb(7, 3))}
    assert ranks == set(range(comb(7, 3)))


# -- the layer index ----------------------------------------------------------


@pytest.mark.parametrize("t", range(TINY.n_cells + 1))
def test_index_round_trips_at_every_layer(t):
    layer = LayerIndex(TINY, t)
    for index in range(layer.size):
        assert layer.encode(layer.decode(index)) == index


@pytest.mark.parametrize("t", range(TINY.n_cells + 1))
def test_the_index_is_injective_onto_distinct_configurations(t):
    """Counted by enumeration, not by re-deriving the formula.

    ``LayerIndex.size`` is a product of binomials, so comparing it against
    another product of binomials proves nothing. Collecting the decoded keys
    and counting them does: it shows the index really is a bijection onto that
    many *distinct* configurations, which is what adr-010 V1's per-layer
    equality is a statement about.
    """
    layer = LayerIndex(TINY, t)
    keys = {layer.decode(i).key() for i in range(layer.size)}
    assert len(keys) == layer.size


@pytest.mark.parametrize("t", range(TINY.n_cells + 1))
def test_decoded_states_have_exactly_t_filled_cells(t):
    layer = LayerIndex(TINY, t)
    for index in range(0, layer.size, max(1, layer.size // 25)):
        state = layer.decode(index)
        filled = sum(1 for c in state.colours if c != Colour.EMPTY)
        assert filled == t


def test_side_to_move_is_a_function_of_the_layer():
    """Which is why it is not stored in the index."""
    for t in range(TINY.n_cells + 1):
        layer = LayerIndex(TINY, t)
        expected = TINY.first if t % 2 == 0 else Colour.GREEN
        assert layer.to_move == expected
        assert layer.decode(0).to_move == expected


def test_terminal_layer_is_two_to_the_n():
    """adr-010 V0: the base case is closed-form and exhaustively checkable."""
    layer = LayerIndex(TINY, TINY.n_cells)
    assert layer.size == 2**TINY.n_cells
    assert LayerIndex(Variant(3, 3), 9).size == 512
    assert LayerIndex(Variant(5, 3), 15).size == 32_768


def test_spent_counts_follow_alternation():
    for t in range(TINY.n_cells + 1):
        layer = LayerIndex(TINY, t)
        assert layer.first_spent + layer.second_spent == t
        assert layer.first_spent == (t + 1) // 2


def test_the_root_layer_is_the_opening_position():
    layer = LayerIndex(TINY, 0)
    assert layer.size == 1
    assert layer.decode(0).key() == TINY.initial_state().key()


# -- adr-010 V3: two methods must agree ---------------------------------------


@pytest.mark.parametrize("arm", [Arm.H1, Arm.H2])
def test_retrograde_agrees_with_forward_search(arm):
    """adr-010 V3, in miniature.

    Forward alpha-beta walks the game tree with pruning and a transposition
    table; the retrograde sweep enumerates the configuration space backwards
    with neither. They share the rules and nothing else, which is what makes
    their agreement evidence rather than a tautology.

    A plain equality, deliberately: ``RetrogradeResult.value`` speaks the same
    WIN/LOSS constants the forward searcher does, so this comparison cannot be
    written backwards. The slot encoding stays inside the sweep's storage.
    """
    variant = Variant(5, 1, arm)
    backward = solve(variant)
    forward = forward_solve(variant.board(), variant.initial_state())
    assert backward.value == forward.value


def test_the_sweep_leaves_no_unset_value():
    variant = Variant(5, 1)
    result = solve(variant)
    assert result.value in (WIN, LOSS)


def test_every_layer_is_counted():
    result = solve(TINY)
    assert set(result.stats.layer_counts) == set(range(TINY.n_cells + 1))
    for t, count in result.stats.layer_counts.items():
        assert count == LayerIndex(TINY, t).size


def test_stats_report_provenance():
    stats = solve(TINY).stats
    assert stats.ordering == "internal"
    assert stats.termination == "exhausted"
    assert 0 < stats.terminal_wins < 2**TINY.n_cells
    assert set(stats.as_dict()) >= {"layer_counts", "ordering", "termination"}


# -- a tie anywhere is a bug, asserted rather than sampled --------------------


def test_a_tied_terminal_would_raise():
    """adr-010 V2. Odd N makes this unreachable, which is the point.

    Constructed by hand on an even board, which ``Variant`` refuses precisely
    so this cannot arise from a legal configuration.
    """
    from fliphex.rules import winner

    colours = (Colour.PURPLE, Colour.PURPLE, Colour.GREEN, Colour.GREEN)
    tied = GameState.build(colours, (0, 0), Colour.PURPLE)
    with pytest.raises(ValueError, match="impossible"):
        winner(tied)
