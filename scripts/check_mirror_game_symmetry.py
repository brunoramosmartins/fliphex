"""Test whether the board's Z/2 mirror is also a symmetry of the *game*.

``scripts/check_symmetry.py`` establishes that the board graph has a single
non-trivial automorphism: a left-right **mirror** across column C, acting on
directions by ``NE<->NW``, ``SE<->SW`` (``adr-008``). That is a statement about
geometry and the flip rule only.

A *game* symmetry is stronger. Writing ``M`` for the mirror, it requires that
for every state ``s`` and every move ``a``::

    a is legal in s   <=>   M(a) is legal in M(s)
    M(RESULT(s, a))    ==   RESULT(M(s), M(a))

The first line is where FLIPHEX fails, and this script exhibits exactly why and
exactly when it recovers.

The mechanism: a hex tile on the board may be **rotated** but never reflected
(turning it over would change its colour), so the patterns a tile can present
are its *rotation orbit*. The mirror reflects patterns. For a tile whose orbit
is closed under reflection this is harmless -- the mirrored pattern is just
another rotation of the same tile. ``P3-y`` is **chiral**: its reflection is a
different rotation orbit, and no tile in the deck can produce it. So a move that
plays ``P3-y`` has no mirror image among the legal moves.

Consequence, and it is the one the synthesis note (S3) turns on: the mirror is a
*partial*, endgame-restricted symmetry. It becomes a genuine game symmetry only
once **both** copies of ``P3-y`` have been placed and gone inert.

    python scripts/check_mirror_game_symmetry.py

Exits non-zero if any claim fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_symmetry import board_automorphisms  # noqa: E402

from fliphex.board import Board  # noqa: E402
from fliphex.moves import Move, apply_move, legal_moves  # noqa: E402
from fliphex.piece import N_SLOTS, mask_to_slots  # noqa: E402
from fliphex.state import (  # noqa: E402
    TILE_INDEX,
    TILES,
    Colour,
    GameState,
    tiles_in,
)

CHIRAL = "P3-y"


# -- the mirror, derived from the board rather than hard-coded ----------------


def mirror_of(board: Board) -> tuple[tuple[int, ...], dict[int, int]]:
    """Return the board's non-identity automorphism as ``(cells, directions)``.

    ``board_automorphisms`` yields ``(name, direction_permutation, cell_map)``
    where ``cell_map`` is a *dict*. Identity is filtered on the permutation
    itself, not on the action name -- several named actions can induce it.
    """
    identity = tuple(range(board.n_cells))
    autos = []
    for _name, rho, cell_map in board_automorphisms(board):
        perm = tuple(cell_map[c] for c in range(board.n_cells))
        if perm != identity:
            autos.append((perm, {d: rho[d] for d in range(N_SLOTS)}))
    if len(autos) != 1:
        raise AssertionError(
            f"expected exactly one non-trivial automorphism, got {len(autos)}"
        )
    return autos[0]


def mirror_mask(mask: int, rho: dict[int, int]) -> int:
    """Reflect an arrow pattern: arrow in slot ``i`` moves to slot ``rho[i]``."""
    out = 0
    for i in range(N_SLOTS):
        if mask >> i & 1:
            out |= 1 << rho[i]
    return out


def orbit(tile: int) -> set[int]:
    """Every arrow pattern this tile can present, over its distinct rotations."""
    return {TILES[tile].rotated(r) for r in TILES[tile].distinct_rotations()}


def find_placement(hand: int, pattern: int) -> tuple[int, int] | None:
    """Return a ``(tile, rotation)`` in ``hand`` presenting ``pattern``, if any."""
    for tile in tiles_in(hand):
        for rotation in TILES[tile].distinct_rotations():
            if TILES[tile].rotated(rotation) == pattern:
                return tile, rotation
    return None


def mirror_move(
    move: Move, hand: int, pi: tuple[int, ...], rho: dict[int, int]
) -> Move | None:
    """Return the mirror image of ``move``, or ``None`` if no tile can play it.

    The mirrored move must land on the mirrored cell and present the mirrored
    arrow pattern. Which *tile* realises it is not fixed in advance -- we ask
    the hand.
    """
    pattern = mirror_mask(TILES[move.tile].rotated(move.rotation), rho)
    found = find_placement(hand, pattern)
    if found is None:
        return None
    tile, rotation = found
    return Move(pi[move.cell], tile, rotation)


def mirror_state(state: GameState, pi: tuple[int, ...]) -> GameState:
    """Mirror a position. Hands are unchanged -- you hold the same tiles."""
    colours = [Colour.EMPTY] * state.n_cells
    for cell, colour in enumerate(state.colours):
        colours[pi[cell]] = colour
    return GameState.build(tuple(colours), state.hands, state.to_move)


def fmt(mask: int) -> str:
    names = ("N", "NE", "SE", "S", "SW", "NW")
    return "{" + ",".join(names[s] for s in mask_to_slots(mask)) + "}"


# -- part A: which archetypes survive reflection ------------------------------


def part_a(rho: dict[int, int]) -> list[str]:
    print("=" * 74)
    print("A. Is each tile's rotation orbit closed under the mirror?")
    print("=" * 74)
    moved = ", ".join(f"{d}->{rho[d]}" for d in range(N_SLOTS))
    print(f"   mirror on directions: {moved}")
    print(f"   {'tile':<9} {'rotations':>9}  {'orbit closed?':<14} mirror of canonical")
    broken = []
    for tile, piece in enumerate(TILES):
        orb = orbit(tile)
        mirrored = {mirror_mask(m, rho) for m in orb}
        closed = mirrored == orb
        if not closed:
            broken.append(piece.archetype)
            if mirrored & orb:
                raise AssertionError("partial overlap is impossible for a group action")
        flag = "yes" if closed else "NO  <-- chiral"
        print(
            f"   {piece.archetype:<9} {len(orb):>9}  {flag:<14} "
            f"{fmt(piece.mask)} -> {fmt(mirror_mask(piece.mask, rho))}"
        )
    print(f"\n   -> chiral tiles: {broken or 'none'}")
    assert broken == [CHIRAL], f"expected only {CHIRAL} to be chiral, got {broken}"
    return broken


# -- part B: what that costs at the move level --------------------------------


def part_b(board: Board, pi: tuple[int, ...], rho: dict[int, int]) -> None:
    print("\n" + "=" * 74)
    print("B. Opening ply: how many of the 1450 legal moves have a legal mirror?")
    print("=" * 74)
    state = GameState.initial(board.n_cells)
    hand = state.hand(state.to_move)
    moves = legal_moves(board, state)
    without = [m for m in moves if mirror_move(m, hand, pi, rho) is None]
    chiral_idx = TILE_INDEX[CHIRAL]

    print(f"   legal moves on ply 1 .................. {len(moves)}")
    print(f"   moves whose mirror is NOT legal ....... {len(without)}")
    all_chiral = all(m.tile == chiral_idx for m in without)
    print(f"   ... all of them play {CHIRAL}? ......... {all_chiral}")
    print(f"   = 25 cells x {len(orbit(chiral_idx))} rotations ............... "
          f"{board.n_cells * len(orbit(chiral_idx))}")
    assert all(m.tile == chiral_idx for m in without)
    assert len(without) == board.n_cells * len(orbit(chiral_idx))

    bad = without[0]
    pattern = TILES[bad.tile].rotated(bad.rotation)
    print(f"\n   witness: play {CHIRAL} on cell {board.cell_name(bad.cell)} at "
          f"rotation {bad.rotation}, arrows {fmt(pattern)}")
    print(f"            its mirror needs arrows {fmt(mirror_mask(pattern, rho))} "
          f"on cell {board.cell_name(pi[bad.cell])}")
    print("            no tile in the deck presents that pattern at any rotation.")


# -- part C: the scenario, before and after both P3-y are spent ---------------


def _twin_positions(board: Board, chiral_in_hand: bool) -> GameState:
    """A small hand-built position; both players hold the same tiles."""
    colours = [Colour.EMPTY] * board.n_cells
    for name, colour in (("B2", Colour.PURPLE), ("D4", Colour.GREEN)):
        colours[board.cell_id(name)] = colour
    keep = ["P1", "P2-adj", "P6"] + ([CHIRAL] if chiral_in_hand else [])
    hand = 0
    for name in keep:
        hand |= 1 << TILE_INDEX[name]
    return GameState.build(tuple(colours), (hand, hand), Colour.PURPLE)


def part_c(board: Board, pi: tuple[int, ...], rho: dict[int, int]) -> None:
    print("\n" + "=" * 74)
    print("C. The same position, with and without P3-y in hand")
    print("=" * 74)
    for chiral_in_hand in (True, False):
        state = _twin_positions(board, chiral_in_hand)
        hand = state.hand(state.to_move)
        held = ", ".join(TILES[t].archetype for t in tiles_in(hand))
        moves = legal_moves(board, state)
        mirrored = [mirror_move(m, hand, pi, rho) for m in moves]
        missing = sum(1 for m in mirrored if m is None)

        # Where a mirror image exists, does the diagram commute?
        ms = mirror_state(state, pi)
        legal_after = set(legal_moves(board, ms))
        commutes = True
        for move, mm in zip(moves, mirrored, strict=True):
            if mm is None:
                continue
            if mm not in legal_after:
                commutes = False
                break
            lhs = mirror_state(apply_move(board, state, move), pi)
            rhs = apply_move(board, ms, mm)
            if lhs.colours != rhs.colours:
                commutes = False
                break

        print(f"\n   hand = {held}")
        print(f"     legal moves ......................... {len(moves)}")
        print(f"     without a legal mirror image ........ {missing}")
        print(f"     M(RESULT(s,a)) == RESULT(M(s),M(a)) . {commutes} (where defined)")
        print(f"     => mirror is a game symmetry here ... {missing == 0 and commutes}")
        assert commutes, "the flip rule itself must commute with the mirror"
        if chiral_in_hand:
            assert missing > 0, "expected the chiral tile to break the mirror"
        else:
            assert missing == 0, "expected the mirror to hold once P3-y is spent"


def main() -> int:
    board = Board()
    pi, rho = mirror_of(board)
    part_a(rho)
    part_b(board, pi, rho)
    part_c(board, pi, rho)
    print("\n" + "=" * 74)
    print("VERDICT: the mirror preserves the board, the arrow structure and the")
    print("flip rule -- but not the *move set*, while a P3-y is in either hand.")
    print("It is a full game symmetry only after both copies are placed, i.e.")
    print("in the endgame, which is where the retrograde databases live.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
