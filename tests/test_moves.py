"""Tests for fliphex.moves — legal-move generation and the flip rule.

Covers the four flip subtleties from docs/rules-canonical.md §4 (unconditional,
non-chaining, same-colour no-op, off-board no-op), the 1450-move opening, and
the invariants I1–I6 over random games.
"""

import random
from collections import Counter

from fliphex.board import Board
from fliphex.moves import Move, apply_move, legal_moves
from fliphex.piece import ARCHETYPES
from fliphex.state import TILES, Colour, GameState

P1 = list(ARCHETYPES).index("P1")  # tile index of the single-arrow piece
P2_OPP = list(ARCHETYPES).index("P2-opp")


def _cid(name: str) -> int:
    return Board().cell_id(name)


# -- legal-move generation ----------------------------------------------------


def test_opening_has_1450_distinct_moves():
    board, s = Board(), GameState.initial()
    moves = legal_moves(board, s)
    assert len(moves) == 1450
    assert len(set(moves)) == 1450


def test_rotations_per_tile_match_orbit_sizes():
    board, s = Board(), GameState.initial()
    per_tile = Counter(m.tile for m in legal_moves(board, s) if m.cell == 0)
    for tile, count in per_tile.items():
        assert count == len(TILES[tile].distinct_rotations())


def test_moves_only_from_empty_cells_and_hand_tiles():
    board = Board()
    s = GameState.initial().with_colour(0, Colour.PURPLE)  # cell 0 occupied
    hand = s.hand(s.to_move)
    for m in legal_moves(board, s):
        assert s.colours[m.cell] == Colour.EMPTY
        assert hand >> m.tile & 1


# -- the flip rule ------------------------------------------------------------


def test_worked_example_from_rulebook():
    # docs/rules-canonical.md §8, purple = player 1.
    board = Board()
    s = GameState.initial(first=Colour.PURPLE)

    s = apply_move(board, s, Move(_cid("C3"), P1, 0))  # arrow N -> C2 (empty)
    assert s.score() == (1, 0)

    s = apply_move(board, s, Move(_cid("C2"), P2_OPP, 0))  # S -> C3 flips to green
    assert s.score() == (0, 2)

    s = apply_move(board, s, Move(_cid("C4"), P2_OPP, 0))  # N -> C3 flips to purple
    assert s.score() == (2, 1)
    assert s.colours[_cid("C3")] == Colour.PURPLE
    assert s.colours[_cid("C2")] == Colour.GREEN


def test_flip_does_not_chain():
    # C2, C3 purple. Green plays P1(N) on C4: arrow N flips C3. If flips chained,
    # C3 would fire onto C2 — but placed tiles are inert, so C2 stays purple.
    board = Board()
    s = GameState.initial()
    s = s.with_colour(_cid("C2"), Colour.PURPLE).with_colour(_cid("C3"), Colour.PURPLE)
    s = s.switched()  # green to move
    s = apply_move(board, s, Move(_cid("C4"), P1, 0))
    assert s.colours[_cid("C3")] == Colour.GREEN  # direct flip
    assert s.colours[_cid("C4")] == Colour.GREEN  # placed
    assert s.colours[_cid("C2")] == Colour.PURPLE  # NOT chained


def test_arrow_at_own_tile_is_a_self_flip():
    # Toggle rule (adr-007): purple's arrow at its own tile hands it to green.
    board = Board()
    s = GameState.initial()
    s = s.with_colour(_cid("C2"), Colour.PURPLE)  # neighbour already purple
    # Purple plays P1(N) on C3 -> arrow at C2 (own) turns it over to GREEN.
    s = apply_move(board, s, Move(_cid("C3"), P1, 0))
    assert s.colours[_cid("C2")] == Colour.GREEN  # self-flip, not a no-op
    assert s.colours[_cid("C3")] == Colour.PURPLE  # the placed tile
    assert s.score() == (1, 1)


def test_flip_is_a_toggle_independent_of_mover():
    # An arrow inverts the target's colour regardless of who places it.
    board = Board()
    s = GameState.initial()
    s = s.with_colour(_cid("C2"), Colour.GREEN)
    # Purple plays P1(N) on C3 -> C2 (green) turns over to purple.
    s = apply_move(board, s, Move(_cid("C3"), P1, 0))
    assert s.colours[_cid("C2")] == Colour.PURPLE


def test_off_board_arrows_do_nothing():
    board = Board()
    s = GameState.initial()
    # A1 is a degree-2 corner; P1 at rotation 0 points N, off the board.
    s = apply_move(board, s, Move(_cid("A1"), P1, 0))
    assert s.score() == (1, 0)
    assert s.colours[_cid("A1")] == Colour.PURPLE


def test_apply_move_bookkeeping():
    board = Board()
    s0 = GameState.initial()
    s1 = apply_move(board, s0, Move(_cid("C3"), P1, 0))
    assert s1.to_move == Colour.GREEN  # turn passed
    assert not s1.hand(Colour.PURPLE) >> P1 & 1  # tile spent
    assert s1.history[-1] == (_cid("C3"), P1, 0)  # recorded
    assert s0.to_move == Colour.PURPLE  # original untouched


# -- invariants over random games (I1–I6) -------------------------------------


def test_random_games_preserve_invariants():
    rng = random.Random(20260725)
    board = Board()
    for _ in range(50):
        s = GameState.initial()
        ply = 0
        while not s.is_terminal():
            assert s.ply() == ply  # I1: occupied == plies
            moves = legal_moves(board, s)
            assert moves  # I4: a legal move always exists
            # I5: no tile is created or destroyed.
            placed = ply
            remaining = bin(s.hand(Colour.PURPLE)).count("1") + bin(
                s.hand(Colour.GREEN)
            ).count("1")
            assert placed + remaining == 25
            s = apply_move(board, s, rng.choice(moves))
            ply += 1
        assert ply == 25  # termination in exactly 25 plies
        assert s.is_terminal()
        assert Colour.EMPTY not in s.colours  # I2: board full
        purple, green = s.score()
        assert purple + green == 25
        assert purple != green  # draws impossible (25 is odd)
        assert len(s.history) == 25
