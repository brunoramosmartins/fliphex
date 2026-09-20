"""Tests for ``complexity/game_tree.py``.

The load-bearing one is ``test_closed_form_matches_exhaustive_enumeration``: it
walks the real engine's move generator to three plies and counts, then compares
against the closed form. Everything else in the module rests on the claim that
the game tree is a product of three independent choices, and that test is the
only thing that checks the claim against the rules rather than against itself.

Three plies is the shallowest depth that tests it properly. At two plies each
player has spent one tile and the count is a plain sum over orbits; at three the
first player has spent two, so the elementary symmetric term ``e_2`` is
exercised and a naive ``sum(orbits) ** 2 / 2`` would be caught.
"""

from __future__ import annotations

from math import factorial, isqrt, log10, prod

import pytest

from complexity.game_tree import (
    KNOWN,
    KNOWN_GAMES,
    ORBITS,
    SHIPPED_OPENING_MOVES,
    effective_branching,
    elementary_symmetric,
    games,
    minimal_tree,
    prefixes,
    rollout_estimate,
    self_check,
)
from fliphex import apply_move, legal_moves
from fliphex.variant import Arm, Variant

BOARDS = [(3, 3), (5, 3), (5, 5)]
REDUCED = [(3, 3), (5, 3)]


def _variant(name: str) -> Variant:
    board, arm = name.rsplit("-", 1)
    cols, rows = (int(x) for x in board.split("x"))
    return Variant(cols, rows, Arm(arm))


def _enumerate(variant: Variant, depth: int) -> int:
    """Count distinct ``depth``-ply prefixes by exhaustive engine walk."""
    board = variant.board()

    def walk(state, remaining: int) -> int:
        if remaining == 0:
            return 1
        return sum(
            walk(apply_move(board, state, move), remaining - 1)
            for move in legal_moves(board, state)
        )

    return walk(variant.initial_state(), depth)


# -- the claim the module rests on ------------------------------------------


@pytest.mark.parametrize("name", sorted(KNOWN_GAMES))
def test_games_matches_exhaustive_enumeration_at_full_depth(name):
    """The strongest check in the package, and the slowest: ~10 s for the pair.

    The 5x1 is the smallest board adr-011 admits, and small enough to walk to
    the last ply. Every other test compares the closed form against a prefix or
    against itself; this one compares :func:`games` against the rules.
    """
    variant = _variant(name)
    assert _enumerate(variant, variant.n_cells) == games(variant)
    assert games(variant) == KNOWN_GAMES[name]


@pytest.mark.parametrize("name", sorted(KNOWN))
def test_closed_form_matches_exhaustive_enumeration(name):
    """Two plies on the larger boards, walked rather than recalled.

    Depth is capped at 2 because the 5x3's third ply has 95,975,880 leaves and
    the suite is not the place to enumerate them. The depth-3 values were walked
    once, offline, and are pinned in :data:`KNOWN` -- which is what a gate-7
    reference is for.
    """
    variant = _variant(name)
    for depth in range(3):
        assert _enumerate(variant, depth) == prefixes(variant, depth)


@pytest.mark.parametrize("name", sorted(KNOWN))
def test_reproduces_the_recorded_prefix_counts(name):
    """The same values, without paying for the walk."""
    variant = _variant(name)
    assert tuple(prefixes(variant, k) for k in range(4)) == KNOWN[name]


def test_self_check_is_clean():
    assert self_check() == []


def test_the_shipped_opening_has_1450_moves():
    """25 cells x 58 distinct (tile, rotation) pairs, from the engine's own
    docstring and the project notes."""
    assert prefixes(Variant(5, 5, Arm.H1), 1) == SHIPPED_OPENING_MOVES
    assert sum(ORBITS[t] for t in Variant(5, 5, Arm.H1).deck_names()[0]) == 58


# -- the orbit sizes --------------------------------------------------------


def test_orbit_sizes_are_not_all_six():
    """P6 has one, P3-tri two, the opposite-pair tiles three. Assuming six
    everywhere would overcount the tree by 6**3 / (1 * 2 * 3 * 3)."""
    assert ORBITS["P6"] == 1
    assert ORBITS["P3-tri"] == 2
    assert ORBITS["P2-opp"] == 3
    assert ORBITS["P4-opp"] == 3
    assert ORBITS["JOKER"] == 1
    assert sorted(set(ORBITS.values())) == [1, 2, 3, 6]


def test_orbit_sizes_divide_six():
    """A rotation orbit is an orbit of the cyclic group of order six."""
    for size in ORBITS.values():
        assert 6 % size == 0


# -- elementary symmetric polynomials ---------------------------------------


def test_elementary_symmetric_on_a_hand_by_hand_case():
    assert elementary_symmetric([2, 3, 5]) == [1, 10, 31, 30]


def test_elementary_symmetric_top_term_is_the_product():
    values = [6, 6, 3, 2, 1]
    assert elementary_symmetric(values)[-1] == prod(values)


def test_elementary_symmetric_first_term_is_the_sum():
    values = [6, 6, 3, 2, 1]
    assert elementary_symmetric(values)[1] == sum(values)


def test_a_naive_power_would_differ_from_the_symmetric_term():
    """Pins that the distinction is real on a hand this project actually deals.

    If tiles could repeat, two plies would give ``sum ** 2``; they cannot, so
    the count is ``2! * e_2``.
    """
    hand = [ORBITS[t] for t in Variant(5, 3, Arm.H1).deck_names()[0]]
    assert 2 * elementary_symmetric(hand)[2] != sum(hand) ** 2


# -- the full count ---------------------------------------------------------


@pytest.mark.parametrize("board", BOARDS)
def test_games_is_the_prefix_count_at_full_depth(board):
    variant = Variant(board[0], board[1], Arm.H1)
    assert games(variant) == prefixes(variant, variant.n_cells)


@pytest.mark.parametrize("board", BOARDS)
def test_games_equals_the_three_factor_product(board):
    """n! x d1! x prod(orbits) x d2! x prod(orbits), written out."""
    variant = Variant(board[0], board[1], Arm.H1)
    first, second = variant.deck_names()
    expected = (
        factorial(variant.n_cells)
        * factorial(len(first))
        * prod(ORBITS[t] for t in first)
        * factorial(len(second))
        * prod(ORBITS[t] for t in second)
    )
    assert games(variant) == expected


def test_the_shipped_game_tree_is_ten_to_the_58_point_6():
    """4.229e58, not the 1e61 the locked H4 statement cites."""
    total = games(Variant(5, 5, Arm.H1))
    assert round(log10(total), 2) == 58.63
    assert f"{total:.3e}" == "4.229e+58"


def test_the_locked_minimal_tree_figure_is_the_consistent_one():
    """H4 cites ~1e61 full and ~1e30.5 minimal. Only the second survives.

    b**13 at b recovered from 1e30.5 implies a full tree of 1e58.6, which is the
    exact count -- so the pair is internally inconsistent and the full-tree
    figure is the outlier.
    """
    variant = Variant(5, 5, Arm.H1)
    assert round(log10(minimal_tree(variant)), 1) == 30.5
    b = 10 ** (30.49 / ((variant.n_cells + 1) // 2))
    assert round(log10(b**variant.n_cells), 1) == round(log10(games(variant)), 1)


@pytest.mark.parametrize("board", BOARDS)
def test_the_minimal_tree_exceeds_the_square_root_on_odd_depth(board):
    """Depth is odd on every legal board (adr-011), so it is b**ceil(d/2)."""
    variant = Variant(board[0], board[1], Arm.H1)
    assert variant.n_cells % 2 == 1
    assert minimal_tree(variant) > isqrt(games(variant))


@pytest.mark.parametrize("board", BOARDS)
def test_effective_branching_reproduces_the_leaf_count(board):
    variant = Variant(board[0], board[1], Arm.H1)
    b = effective_branching(variant)
    assert round(log10(b**variant.n_cells), 6) == round(log10(games(variant)), 6)


@pytest.mark.parametrize("board", BOARDS)
def test_effective_branching_is_below_the_opening_width(board):
    """The opening is the widest ply: cells and hands only shrink."""
    variant = Variant(board[0], board[1], Arm.H1)
    assert effective_branching(variant) < prefixes(variant, 1)


# -- the arms ---------------------------------------------------------------


@pytest.mark.parametrize("board", REDUCED)
def test_the_two_arms_differ_by_exactly_the_extra_tile_s_orbit(board):
    """Unlike the orphan count, this one does depend on the deck.

    The two arms differ in one tile: H1 gives the first player the joker, whose
    orbit is 1, and H2 gives it the next archetype instead. Everything else --
    cells, hand sizes, the other eleven tiles -- is identical, so the whole
    difference is the ratio of the two orbits. It is 2 on the 5x3, where the
    promoted tile is P3-tri, and 6 on the 3x3, where it is an ordinary tile.
    """
    h1, h2 = (Variant(board[0], board[1], arm) for arm in (Arm.H1, Arm.H2))
    extra_h1 = h1.deck_names()[0][-1]
    extra_h2 = h2.deck_names()[0][-1]
    assert extra_h1 == "JOKER"
    assert set(h1.deck_names()[0][:-1]) == set(h2.deck_names()[0][:-1])
    assert games(h2) * ORBITS[extra_h1] == games(h1) * ORBITS[extra_h2]
    assert games(h1) != games(h2)


# -- the estimator ----------------------------------------------------------


def test_rollout_estimate_lands_in_the_right_order_of_magnitude():
    """Unbiased, so it should not be wildly off even at modest samples."""
    estimate = rollout_estimate(Variant(3, 3, Arm.H1), samples=400, seed=3)
    assert 0.3 < estimate.ratio < 3.0


def test_rollout_variance_is_large_enough_to_matter():
    """The point of keeping the estimator: it argues against itself.

    A single rollout's spread is several times the quantity estimated, so the
    standard error of the mean falls as ``relative_sd / sqrt(n)`` and 1% needs
    on the order of 1e5 rollouts.
    """
    estimate = rollout_estimate(Variant(3, 3, Arm.H1), samples=400, seed=3)
    assert estimate.relative_sd > 1.0


def test_rollout_is_reproducible_under_a_seed():
    a = rollout_estimate(Variant(3, 3, Arm.H1), samples=50, seed=11)
    b = rollout_estimate(Variant(3, 3, Arm.H1), samples=50, seed=11)
    assert a.mean == b.mean
    assert a.sd == b.sd


def test_different_seeds_give_different_estimates():
    a = rollout_estimate(Variant(3, 3, Arm.H1), samples=50, seed=11)
    b = rollout_estimate(Variant(3, 3, Arm.H1), samples=50, seed=12)
    assert a.mean != b.mean


def test_a_single_rollout_reports_zero_spread_not_a_crash():
    estimate = rollout_estimate(Variant(3, 3, Arm.H1), samples=1, seed=5)
    assert estimate.sd == 0.0
    assert estimate.samples == 1


def test_rollout_rejects_a_zero_sample_count():
    with pytest.raises(ValueError, match="at least 1"):
        rollout_estimate(Variant(3, 3, Arm.H1), samples=0)


def test_rollout_carries_the_exact_answer_alongside():
    """An estimate published without the exact value it is checked against
    would be the thing this module exists to avoid."""
    variant = Variant(3, 3, Arm.H1)
    assert rollout_estimate(variant, samples=10, seed=1).exact == games(variant)


# -- argument checking ------------------------------------------------------


@pytest.mark.parametrize("k", [-1, 26])
def test_prefixes_rejects_a_depth_off_the_board(k):
    with pytest.raises(ValueError, match="k must be in"):
        prefixes(Variant(5, 5, Arm.H1), k)


def test_prefixes_at_zero_is_the_opening_alone():
    assert prefixes(Variant(5, 5, Arm.H1), 0) == 1


@pytest.mark.parametrize("board", BOARDS)
def test_prefix_counts_are_strictly_increasing(board):
    variant = Variant(board[0], board[1], Arm.H1)
    counts = [prefixes(variant, k) for k in range(variant.n_cells + 1)]
    assert all(b > a for a, b in zip(counts, counts[1:], strict=False))


def test_imports_nothing_from_solver_or_az():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parent.parent / "complexity" / "game_tree.py"
    ).read_text()
    for forbidden in ("import solver", "from solver", "import az", "from az"):
        assert forbidden not in source
