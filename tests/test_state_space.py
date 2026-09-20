"""Tests for ``complexity/state_space.py``.

Two of these carry more weight than the rest.

``test_agrees_with_the_independent_layer_profile`` asserts that the bound this
module computes equals the one ``scripts/layer_profile.py`` computes. The
duplication is deliberate and load-bearing: ``layer_profile`` imports nothing
from ``fliphex`` on purpose, because adr-010 V1 compares it against the solver's
own enumerator and a comparison is only evidence if the two sides are computed
by different means. Collapsing the two into one implementation would delete the
check, so the test asserts agreement instead.

``test_layer_zero_is_not_an_orphan`` and its companion pin the off-by-one that
the identity invites. The opening position has no predecessor, which is what the
formula detects, and it is reachable, because it is where the game starts.
"""

from __future__ import annotations

import importlib.util
import sys
from math import comb
from pathlib import Path

import pytest

from complexity.state_space import (
    KNOWN,
    configurations,
    orientation_inflated,
    orphans,
    profile,
    self_check,
)
from fliphex.variant import Arm, Variant

_ROOT = Path(__file__).resolve().parent.parent


def _load_layer_profile():
    """Import ``scripts/layer_profile.py`` without putting scripts/ on sys.path.

    The script is not part of a package and its directory holds thirty other
    modules named after experiments; importing it by path keeps all of them out
    of the test session's namespace.
    """
    spec = importlib.util.spec_from_file_location(
        "_layer_profile_under_test", _ROOT / "scripts" / "layer_profile.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BOARDS = [(3, 3), (5, 3), (5, 5)]


def _arms(board: tuple[int, int]) -> list[Arm]:
    # Variant(5, 5, Arm.H2) raises: at capacity 12 there is no next archetype
    # to promote, so the joker is the only tile that can give P1 the extra ply.
    return [Arm.H1] if board == (5, 5) else [Arm.H1, Arm.H2]


# -- the known values -------------------------------------------------------


def test_self_check_is_clean():
    assert self_check() == []


@pytest.mark.parametrize("board", BOARDS)
def test_reproduces_the_recorded_configuration_count(board):
    space = profile(Variant(board[0], board[1], Arm.H1))
    assert space.configurations == KNOWN[board]["configurations"]


@pytest.mark.parametrize("board", BOARDS)
def test_reproduces_the_recorded_orphan_count(board):
    space = profile(Variant(board[0], board[1], Arm.H1))
    assert space.orphans == KNOWN[board]["orphans"]


def test_the_shipped_board_matches_the_locked_research_figures():
    """4.9e17 corrected, 1.4e37 inflated -- the two figures docs/research.md
    names when it says the roadmap's bound was wrong."""
    space = profile(Variant(5, 5, Arm.H1))
    assert f"{space.configurations:.1e}" == "4.9e+17"
    inflated = orientation_inflated(space.n_cells, *space.hands)
    assert f"{inflated:.1e}" == "1.4e+37"


# -- independence from the other implementation -----------------------------


@pytest.mark.parametrize("board", BOARDS)
def test_agrees_with_the_independent_layer_profile(board):
    """Two implementations of one formula, kept apart on purpose."""
    other = _load_layer_profile()
    variant = Variant(board[0], board[1], Arm.H1)
    first, second = (len(names) for names in variant.deck_names())
    for t in range(variant.n_cells + 1):
        assert configurations(variant.n_cells, first, second, t) == other.layer(
            variant.n_cells, first, second, t
        )


# -- the off-by-one ---------------------------------------------------------


@pytest.mark.parametrize("board", BOARDS)
def test_layer_zero_is_not_an_orphan(board):
    """The opening has no predecessor and is reachable anyway."""
    variant = Variant(board[0], board[1], Arm.H1)
    first, second = (len(names) for names in variant.deck_names())
    assert configurations(variant.n_cells, first, second, 0) == 1
    assert orphans(variant.n_cells, first, second, 0) == 0


def test_the_unguarded_sum_is_exactly_one_too_many():
    """Pins the size of the mistake, so a regression is recognisable.

    Without the ``t == 0`` guard the 3x3 reports 23,372 against EXP-005's
    measured 23,371 -- close enough to look right in a percentage and wrong in
    the count.
    """
    variant = Variant(3, 3, Arm.H1)
    first, second = (len(names) for names in variant.deck_names())
    unguarded = sum(
        comb(variant.n_cells, t) * comb(first, (t + 1) // 2) * comb(second, t // 2)
        for t in range(variant.n_cells + 1)
    )
    assert unguarded == profile(variant).orphans + 1
    assert profile(variant).orphans == 23_371


# -- the identity itself ----------------------------------------------------


@pytest.mark.parametrize("board", BOARDS)
def test_orphans_are_exactly_one_colouring_in_two_to_the_t(board):
    """The identity EXP-005's amendment proved, checked layer by layer."""
    variant = Variant(board[0], board[1], Arm.H1)
    first, second = (len(names) for names in variant.deck_names())
    for t in range(1, variant.n_cells + 1):
        assert orphans(variant.n_cells, first, second, t) * 2**t == configurations(
            variant.n_cells, first, second, t
        )


@pytest.mark.parametrize("board", [(3, 3), (5, 3)])
def test_the_orphan_count_does_not_depend_on_the_deck(board):
    """It counts colourings the mover's colour forbids, never an arrow pattern.

    Both arms hold the same number of tiles and different tiles. If these ever
    disagreed, the identity would be wrong -- not the decks interesting.
    """
    counts = {
        arm: profile(Variant(board[0], board[1], arm)).orphans for arm in _arms(board)
    }
    assert len(set(counts.values())) == 1


# -- shape ------------------------------------------------------------------


@pytest.mark.parametrize("board", BOARDS)
def test_the_profile_is_a_hump_not_a_funnel(board):
    """The peak is interior, which is why FLIPHEX does not converge."""
    space = profile(Variant(board[0], board[1], Arm.H1))
    assert 0 < space.peak.t < space.n_cells


@pytest.mark.parametrize("board", BOARDS)
def test_layer_sizes_rise_then_fall_once(board):
    space = profile(Variant(board[0], board[1], Arm.H1))
    sizes = [layer.configurations for layer in space.layers]
    turns = sum(
        1
        for a, b, c in zip(sizes, sizes[1:], sizes[2:], strict=False)
        if (b - a > 0) != (c - b > 0)
    )
    assert turns == 1


@pytest.mark.parametrize("board", BOARDS)
def test_the_orphan_fraction_shrinks_with_every_layer(board):
    space = profile(Variant(board[0], board[1], Arm.H1))
    fractions = [layer.orphan_fraction for layer in space.layers[1:]]
    assert fractions == sorted(fractions, reverse=True)


def test_the_correction_shrinks_by_orders_of_magnitude_with_board_size():
    """3.28% -> 0.343% -> 0.0079%: the reason the closure was not completed."""
    fractions = [
        profile(Variant(cols, rows, Arm.H1)).orphan_fraction for cols, rows in BOARDS
    ]
    assert fractions == sorted(fractions, reverse=True)
    assert fractions[0] / fractions[1] > 5
    assert fractions[1] / fractions[2] > 5


# -- bookkeeping ------------------------------------------------------------


@pytest.mark.parametrize("board", BOARDS)
def test_reachable_plus_orphans_is_the_whole_space(board):
    space = profile(Variant(board[0], board[1], Arm.H1))
    assert space.reachable + space.orphans == space.configurations
    for layer in space.layers:
        assert layer.reachable + layer.orphans == layer.configurations


@pytest.mark.parametrize("board", BOARDS)
def test_the_terminal_layer_is_two_to_the_n(board):
    """Every cell filled, every hand spent: only the colouring is free."""
    space = profile(Variant(board[0], board[1], Arm.H1))
    assert space.layers[-1].configurations == 2**space.n_cells


def test_orientation_inflation_is_exactly_six_to_the_cells():
    space = profile(Variant(3, 3, Arm.H1))
    inflated = orientation_inflated(space.n_cells, *space.hands)
    assert inflated == space.configurations * 6**space.n_cells


@pytest.mark.parametrize("board", BOARDS)
def test_hands_come_from_the_variant_deck_and_exhaust_the_board(board):
    space = profile(Variant(board[0], board[1], Arm.H1))
    assert sum(space.hands) == space.n_cells
    assert space.hands[0] == space.hands[1] + 1


def test_as_dict_round_trips_through_json():
    import json

    space = profile(Variant(3, 3, Arm.H1))
    payload = json.loads(json.dumps(space.as_dict()))
    assert payload["configurations"] == 711_963
    assert payload["orphans"] == 23_371
    assert len(payload["layers"]) == 10


def test_imports_nothing_from_solver_or_az():
    """complexity/ depends on fliphex/ alone -- docs/engineering.md."""
    source = (_ROOT / "complexity" / "state_space.py").read_text()
    for forbidden in ("import solver", "from solver", "import az", "from az"):
        assert forbidden not in source
