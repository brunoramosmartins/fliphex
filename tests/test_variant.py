"""Tests for fliphex.variant.

Focus on the adr-011 guarantees: variants have an odd cell count, both hands are
exactly exhausted, Player 1 moves last, and the reduced-deck rule reproduces the
shipped 5×5 rather than special-casing it.

The state-space figures asserted here come from ``scripts/layer_profile.py``,
which imports nothing from this package. Keeping them as literals is deliberate:
adr-010 V1 compares the solver's enumeration against that closed form, and a
comparison is only evidence if the two sides are computed by different means.
"""

import pytest

from fliphex.board import Board
from fliphex.piece import DECK
from fliphex.state import JOKER_INDEX, Colour, GameState, tiles_in
from fliphex.variant import (
    FIVE_BY_THREE,
    FULL_GAME,
    THREE_BY_THREE,
    Arm,
    Variant,
    archetypes_for,
)

#: Boards where both arms exist. The H2 arm needs a 13th archetype to stand in
#: for the joker, so it does not exist on the shipped 5×5 (capacity 12 = the
#: whole deck) — see ``test_h2_arm_does_not_exist_on_the_full_deck``.
REDUCED = [THREE_BY_THREE, FIVE_BY_THREE]
ALL_VARIANTS = [*REDUCED, FULL_GAME]


# -- parity: the guard that keeps the 4×4 class of bug out --------------------


@pytest.mark.parametrize("n_cols,n_rows", [(4, 4), (5, 4), (2, 3), (4, 5)])
def test_even_boards_are_rejected(n_cols, n_rows):
    with pytest.raises(ValueError, match="odd cell count"):
        Variant(n_cols, n_rows)


@pytest.mark.parametrize("n_cols,n_rows", [(3, 3), (5, 3), (3, 5), (5, 5), (5, 7)])
def test_odd_boards_are_accepted(n_cols, n_rows):
    assert Variant(n_cols, n_rows).n_cells % 2 == 1


def test_board_itself_still_accepts_even_sizes():
    """The 4×4 must remain constructible as a *graph*.

    ``scripts/check_symmetry.py 4 4`` is how the 4×4's automorphism was measured
    and found to be a 180° rotation rather than a mirror. The parity rule
    forbids playing a game on an even board, not building one.
    """
    assert Board(4, 4).n_cells == 16
    assert Variant(5, 3).board().n_cells == 15
    assert Variant(5, 5).board().n_cells == 25


def test_boards_too_small_for_the_anchors_are_rejected():
    with pytest.raises(ValueError, match="at least 5 cells"):
        Variant(1, 3)


# -- the deck rule ------------------------------------------------------------


def test_anchors_come_first_at_every_capacity():
    for a in range(2, len(DECK) + 1):
        names = archetypes_for(a)
        assert len(names) == a
        assert len(set(names)) == a
        assert {"P6", "P3-y"} <= set(names)


def test_fill_is_by_ascending_arrow_count():
    arrows = {p.archetype: p.n_arrows for p in DECK}
    filler = [n for n in archetypes_for(8) if n not in ("P6", "P3-y")]
    assert filler == sorted(filler, key=lambda n: arrows[n])


def test_capacity_out_of_range_is_rejected():
    with pytest.raises(ValueError, match="capacity must be"):
        archetypes_for(1)
    with pytest.raises(ValueError, match="capacity must be"):
        archetypes_for(len(DECK) + 1)


def test_worked_examples_match_adr_011():
    """The two decks adr-011 writes out by hand."""
    assert archetypes_for(4) == ("P6", "P3-y", "P1", "P2-adj")
    assert archetypes_for(7) == (
        "P6",
        "P3-y",
        "P1",
        "P2-adj",
        "P2-skip",
        "P2-opp",
        "P3-fan",
    )


# -- hands: exactly exhausting, and P1 moves last -----------------------------


@pytest.mark.parametrize("variant", REDUCED)
@pytest.mark.parametrize("arm", [Arm.H1, Arm.H2])
def test_hands_exactly_fill_the_board(variant, arm):
    v = Variant(variant.n_cols, variant.n_rows, arm)
    first, second = v.deck_names()
    assert len(first) == v.capacity + 1
    assert len(second) == v.capacity
    assert len(first) + len(second) == v.n_cells


@pytest.mark.parametrize("variant", REDUCED)
@pytest.mark.parametrize("arm", [Arm.H1, Arm.H2])
def test_first_player_moves_last(variant, arm):
    """Play alternates for exactly N plies, so an odd N ends on Player 1.

    Player 1 takes plies 1, 3, ..., N — that is ``(N + 1) / 2`` placements —
    and must hold exactly that many tiles for the board to fill without either
    hand running short or running over.
    """
    v = Variant(variant.n_cols, variant.n_rows, arm)
    first, second = v.deck_names()
    plies = range(1, v.n_cells + 1)
    assert len(first) == sum(1 for p in plies if p % 2 == 1)
    assert len(second) == sum(1 for p in plies if p % 2 == 0)
    assert v.n_cells % 2 == 1  # so the last ply is odd, i.e. Player 1's


@pytest.mark.parametrize("variant", ALL_VARIANTS)
def test_h1_arm_gives_player_one_the_joker(variant):
    v = Variant(variant.n_cols, variant.n_rows, Arm.H1)
    first, second = v.deck_names()
    assert first[-1] == "JOKER"
    assert "JOKER" not in second
    assert set(first[:-1]) == set(second)


@pytest.mark.parametrize("variant", REDUCED)
def test_h2_arm_swaps_the_joker_for_an_archetype(variant):
    v = Variant(variant.n_cols, variant.n_rows, Arm.H2)
    first, second = v.deck_names()
    assert "JOKER" not in first
    assert "JOKER" not in second
    assert set(second) < set(first)


def test_the_two_arms_have_the_same_hand_sizes():
    """Matched design: only *what* P1's extra tile is varies, not how many."""
    for n_cols, n_rows in ((3, 3), (5, 3)):
        h1 = Variant(n_cols, n_rows, Arm.H1)
        h2 = Variant(n_cols, n_rows, Arm.H2)
        assert [len(d) for d in h1.deck_names()] == [len(d) for d in h2.deck_names()]


def test_h2_extra_tile_matches_adr_011():
    assert Variant(3, 3, Arm.H2).deck_names()[0][-1] == "P2-skip"
    assert Variant(5, 3, Arm.H2).deck_names()[0][-1] == "P3-tri"


def test_h2_arm_does_not_exist_on_the_full_deck():
    """On the shipped 5×5 the joker is not a design choice.

    The H2 arm replaces Player 1's joker with the next archetype by ascending
    arrow count. At capacity 12 there is no next archetype — the deck is
    exhausted — so on the 5×5 the joker is the *only* tile that can give Player 1
    the extra ply. That is why H2 is exact on the reduced boards and statistical
    on the shipped one. The variant must refuse at construction rather than
    failing later inside ``deck_names``.
    """
    with pytest.raises(ValueError, match="H2 arm does not exist"):
        Variant(5, 5, Arm.H2)
    # Below the ceiling there is a next archetype, so H2 is available.
    assert Variant(7, 3, Arm.H2).capacity == 10


# -- the shipped game is not a special case -----------------------------------


def test_full_variant_reproduces_the_shipped_initial_state():
    """``Variant(5, 5)`` is what the reduced-deck rule reduces *from*."""
    assert FULL_GAME.capacity == 12
    v = FULL_GAME.initial_state()
    s = GameState.initial(25, Colour.PURPLE)
    assert v.hands == s.hands
    assert v.colours == s.colours
    assert v.to_move == s.to_move


def test_full_variant_hand_sizes_are_13_and_12():
    purple, green = FULL_GAME.hands()
    assert bin(purple).count("1") == 13
    assert bin(green).count("1") == 12
    assert purple >> JOKER_INDEX & 1
    assert not green >> JOKER_INDEX & 1


def test_reduced_variant_hand_sizes():
    assert [bin(h).count("1") for h in THREE_BY_THREE.hands()] == [5, 4]
    assert [bin(h).count("1") for h in FIVE_BY_THREE.hands()] == [8, 7]


def test_green_first_holds_the_larger_hand():
    v = Variant(5, 3, Arm.H1, Colour.GREEN)
    purple, green = v.hands()
    assert bin(green).count("1") == 8
    assert bin(purple).count("1") == 7
    assert green >> JOKER_INDEX & 1


# -- initial state ------------------------------------------------------------


@pytest.mark.parametrize("variant", ALL_VARIANTS)
def test_initial_state_is_empty_and_consistent(variant):
    s = variant.initial_state()
    assert s.n_cells == variant.n_cells
    assert s.ply() == 0
    assert not s.is_terminal()
    assert all(c == Colour.EMPTY for c in s.colours)
    held = sum(len(tuple(tiles_in(h))) for h in s.hands)
    assert held == variant.n_cells


def test_names_are_stable_for_artefact_headers():
    assert THREE_BY_THREE.name == "3x3-h1"
    assert FIVE_BY_THREE.name == "5x3-h1"
    assert Variant(5, 3, Arm.H2).name == "5x3-h2"
