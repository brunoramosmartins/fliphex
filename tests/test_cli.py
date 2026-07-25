"""Tests for the pure parts of ui.cli (render + parse) and an AI-vs-AI game."""

from agents.heuristic_agent import HeuristicAgent
from agents.random_agent import RandomAgent
from fliphex.board import Board
from fliphex.state import Colour, GameState
from ui.cli import _parse_move, play, render_board


def test_render_shows_names_and_marks():
    board = Board()
    s = GameState.initial().with_colour(board.cell_id("A1"), Colour.PURPLE)
    text = render_board(board, s)
    assert "A1P" in text  # purple on A1
    assert "E5·" in text  # empty elsewhere
    assert len(text.splitlines()) == 10  # five columns, offset into ten bands


def test_parse_move_with_and_without_rotation():
    board = Board()
    assert _parse_move(board, "C3:P1:0") == _parse_move(board, "C3:P1")
    assert _parse_move(board, "C3:P1:0").rotation == 0


def test_parse_move_rejects_garbage():
    board = Board()
    assert _parse_move(board, "not a move") is None
    assert _parse_move(board, "Z9:P1:0") is None


def test_ai_vs_ai_runs_to_a_winner(capsys):
    board = Board()
    win = play(board, HeuristicAgent(seed=0), RandomAgent(seed=0), Colour.PURPLE)
    assert win in (Colour.PURPLE, Colour.GREEN)
    assert "wins" in capsys.readouterr().out
