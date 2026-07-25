"""Tests for fliphex.notation — round-trips for moves, games, and positions."""

import random

from fliphex.board import Board
from fliphex.moves import Move, apply_move, legal_moves
from fliphex.notation import (
    decode_game,
    decode_move,
    decode_state,
    encode_game,
    encode_move,
    encode_state,
    replay,
)
from fliphex.rules import is_terminal
from fliphex.state import Colour, GameState


def test_move_roundtrip_readable():
    board = Board()
    move = Move(board.cell_id("C2"), 3, 0)  # tile 3 = P2-opp
    assert encode_move(board, move) == "C2:P2-opp:0"
    assert decode_move(board, "C2:P2-opp:0") == move


def _record_random_game(seed: int) -> tuple[Colour, list[Move], GameState]:
    rng = random.Random(seed)
    board = Board()
    first = rng.choice((Colour.PURPLE, Colour.GREEN))
    state = GameState.initial(board.n_cells, first)
    moves: list[Move] = []
    while not is_terminal(state):
        move = rng.choice(legal_moves(board, state))
        moves.append(move)
        state = apply_move(board, state, move)
    return first, moves, state


def test_game_roundtrip_replays_identically():
    board = Board()
    for seed in range(10):
        first, moves, final = _record_random_game(seed)
        text = encode_game(board, first, moves)
        first2, moves2 = decode_game(board, text)
        assert first2 == first
        assert moves2 == moves
        replayed = replay(board, first2, moves2)
        assert replayed.key() == final.key()
        assert replayed.zobrist == final.zobrist
        assert replayed.score() == final.score()


def test_state_roundtrip_preserves_key_and_hash():
    board = Board()
    # Take a mid-game snapshot.
    _, moves, _ = _record_random_game(99)
    state = GameState.initial(board.n_cells, Colour.PURPLE)
    for move in moves[:12]:
        state = apply_move(board, state, move)

    restored = decode_state(encode_state(state))
    assert restored.key() == state.key()
    assert restored.zobrist == state.zobrist
    assert restored.colours == state.colours
    assert restored.hands == state.hands
    assert restored.to_move == state.to_move


def test_encode_state_shape():
    s = GameState.initial(first=Colour.PURPLE)
    colours, to_move, hp, hg = encode_state(s).split()
    assert colours == "." * 25
    assert to_move == "P"
    assert int(hp, 16) == s.hands[0]
    assert int(hg, 16) == s.hands[1]
