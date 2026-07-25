"""Tests for fliphex.rules — winner, score, outcome."""

import random

import pytest

from fliphex.board import Board
from fliphex.moves import apply_move, legal_moves
from fliphex.rules import is_terminal, margin, outcome, score, winner
from fliphex.state import Colour, GameState


def _full_board(colour: Colour) -> GameState:
    """A terminal state with every cell one colour (via primitives)."""
    s = GameState.initial()
    for cell in range(s.n_cells):
        s = s.with_colour(cell, colour)
    return s


def test_winner_is_none_before_terminal():
    s = GameState.initial()
    assert winner(s) is None
    assert not is_terminal(s)


def test_all_purple_board_purple_wins():
    s = _full_board(Colour.PURPLE)
    assert is_terminal(s)
    assert score(s) == (25, 0)
    assert winner(s) == Colour.PURPLE
    assert margin(s) == 25


def test_outcome_is_zero_sum():
    s = _full_board(Colour.GREEN)
    assert winner(s) == Colour.GREEN
    assert outcome(s, Colour.GREEN) == 1
    assert outcome(s, Colour.PURPLE) == -1


def test_outcome_undefined_before_end():
    with pytest.raises(ValueError):
        outcome(GameState.initial(), Colour.PURPLE)


def test_random_game_has_a_clean_winner():
    rng = random.Random(7)
    board = Board()
    for _ in range(30):
        s = GameState.initial()
        while not is_terminal(s):
            s = apply_move(board, s, rng.choice(legal_moves(board, s)))
        purple, green = score(s)
        assert purple + green == 25
        assert purple != green  # no draws
        expected = Colour.PURPLE if purple > green else Colour.GREEN
        assert winner(s) == expected
        assert outcome(s, expected) == 1
        assert outcome(s, expected) + outcome(s, Colour(3 - expected)) == 0
