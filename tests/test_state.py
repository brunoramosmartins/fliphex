"""Tests for fliphex.state.

Focus on the adr-003 guarantees: the search state is colours + hand masks +
turn only, it is immutable, and the Zobrist hash is incremental and transposes.
"""

import pytest

from fliphex.state import (
    JOKER_INDEX,
    PLAYERS,
    Colour,
    GameState,
    other,
    tiles_in,
)

# -- initial position ---------------------------------------------------------


def test_initial_hands_and_turn():
    s = GameState.initial(first=Colour.PURPLE)
    assert s.to_move == Colour.PURPLE
    # Player 1 (purple) holds 13 tiles incl. the joker; player 2 holds 12.
    assert bin(s.hand(Colour.PURPLE)).count("1") == 13
    assert bin(s.hand(Colour.GREEN)).count("1") == 12
    assert s.hand(Colour.PURPLE) >> JOKER_INDEX & 1
    assert not s.hand(Colour.GREEN) >> JOKER_INDEX & 1


def test_initial_board_is_empty():
    s = GameState.initial()
    assert s.ply() == 0
    assert not s.is_terminal()
    assert s.score() == (0, 0)
    assert all(c == Colour.EMPTY for c in s.colours)


def test_green_first_holds_joker():
    s = GameState.initial(first=Colour.GREEN)
    assert s.to_move == Colour.GREEN
    assert s.hand(Colour.GREEN) >> JOKER_INDEX & 1
    assert bin(s.hand(Colour.GREEN)).count("1") == 13


# -- immutability -------------------------------------------------------------


def test_transitions_do_not_mutate_original():
    s = GameState.initial()
    s.with_colour(0, Colour.PURPLE)
    s.without_tile(Colour.PURPLE, 0)
    s.switched()
    # Original is untouched.
    assert s.colours[0] == Colour.EMPTY
    assert s.hand(Colour.PURPLE) >> 0 & 1
    assert s.to_move == Colour.PURPLE


# -- colours, score, ply ------------------------------------------------------


def test_with_colour_updates_score_and_ply():
    s = GameState.initial().with_colour(3, Colour.GREEN).with_colour(7, Colour.PURPLE)
    assert s.score() == (1, 1)
    assert s.ply() == 2


def test_with_colour_noop_when_unchanged_returns_self():
    s = GameState.initial()
    assert s.with_colour(0, Colour.EMPTY) is s


# -- Zobrist ------------------------------------------------------------------


def test_zobrist_involution_on_cell():
    s = GameState.initial()
    z0 = s.zobrist
    # Empty -> purple -> empty restores the hash.
    back = s.with_colour(5, Colour.PURPLE).with_colour(5, Colour.EMPTY)
    assert back.zobrist == z0


def test_switch_turn_is_involution():
    s = GameState.initial()
    assert s.switched().switched().zobrist == s.zobrist
    assert s.switched().to_move == Colour.GREEN


def test_history_does_not_change_zobrist():
    s = GameState.initial()
    assert s.with_history(0, 0, 0).zobrist == s.zobrist


def test_two_initial_states_agree():
    a, b = GameState.initial(), GameState.initial()
    assert a.zobrist == b.zobrist
    assert a.key() == b.key()


def test_transposition_same_key_and_hash_regardless_of_order():
    # Two move orders reaching the same colouring, hands, and turn.
    base = GameState.initial()
    a = (
        base.with_colour(0, Colour.PURPLE)
        .without_tile(Colour.PURPLE, 0)
        .with_colour(1, Colour.GREEN)
        .without_tile(Colour.GREEN, 1)
    )
    b = (
        base.with_colour(1, Colour.GREEN)
        .without_tile(Colour.GREEN, 1)
        .with_colour(0, Colour.PURPLE)
        .without_tile(Colour.PURPLE, 0)
    )
    assert a.key() == b.key()
    assert a.zobrist == b.zobrist


def test_history_distinguishes_otherwise_equal_states():
    # Same search state, different placement history: transposition key agrees,
    # but the full states are not identical objects/values.
    base = GameState.initial().with_colour(0, Colour.PURPLE)
    a = base.with_history(0, 0, 0)
    b = base.with_history(0, 5, 3)
    assert a.key() == b.key()
    assert a.zobrist == b.zobrist
    assert a != b


# -- hand bookkeeping ---------------------------------------------------------


def test_without_tile_clears_bit_and_rejects_missing():
    s = GameState.initial()
    s2 = s.without_tile(Colour.PURPLE, 0)
    assert not s2.hand(Colour.PURPLE) >> 0 & 1
    with pytest.raises(ValueError):
        s2.without_tile(Colour.PURPLE, 0)


def test_tiles_in_lists_hand_contents():
    s = GameState.initial(first=Colour.PURPLE)
    assert set(tiles_in(s.hand(Colour.PURPLE))) == set(range(13))
    assert set(tiles_in(s.hand(Colour.GREEN))) == set(range(12))


def test_other_swaps_players():
    assert other(Colour.PURPLE) == Colour.GREEN
    assert other(Colour.GREEN) == Colour.PURPLE
    assert PLAYERS == (Colour.PURPLE, Colour.GREEN)
