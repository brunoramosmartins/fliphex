"""GameState: the immutable, hashable search state.

Per adr-003, the state used for search stores only:

- a colour (``EMPTY``/``PURPLE``/``GREEN``) per cell,
- a hand bitmask per player over the 13 tiles (12 archetypes + joker),
- whose turn it is.

It does **not** store which tile sits on which cell, nor any rotation — a placed
tile is inert (adr-006), so its identity cannot affect future play. Placement
identity lives in a separate append-only ``history`` for notation, replay, and
the Phase 6 archetype analysis (H5); nothing in search reads it.

A Zobrist hash is maintained incrementally so transposition tables (Phase 3)
are O(1) to key. Two states reached by different move orders with the same
colouring, hands, and turn share a Zobrist value and compare equal on
:meth:`GameState.key` — that is the transposition the small state space buys.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum
from random import Random

from fliphex.piece import DECK, JOKER, Piece


class Colour(IntEnum):
    """Cell / player colour. ``EMPTY`` is the unplayed cell."""

    EMPTY = 0
    PURPLE = 1
    GREEN = 2


#: The two playing colours, in bit order.
PLAYERS: tuple[Colour, Colour] = (Colour.PURPLE, Colour.GREEN)

#: All tiles, index 0..12: the 12 archetypes then the joker.
TILES: tuple[Piece, ...] = (*DECK, JOKER)

#: Index of the joker in :data:`TILES` (and in a hand bitmask).
JOKER_INDEX: int = len(DECK)

#: Archetype name -> tile index, matching :data:`TILES` order.
TILE_INDEX: dict[str, int] = {piece.archetype: i for i, piece in enumerate(TILES)}

#: Hand bitmask for a player who holds every archetype but not the joker.
_DECK_MASK: int = (1 << len(DECK)) - 1

#: Hand bitmask that additionally holds the joker (the first player's hand).
_DECK_WITH_JOKER_MASK: int = (1 << len(TILES)) - 1


def other(colour: Colour) -> Colour:
    """Return the opposing playing colour."""
    return Colour.GREEN if colour == Colour.PURPLE else Colour.PURPLE


def tiles_in(hand: int):
    """Yield the tile indices present in a hand bitmask, ascending."""
    for i in range(len(TILES)):
        if hand >> i & 1:
            yield i


# -- Zobrist tables (cached per board size, deterministic) --------------------

#: cell_hashes, tile_hashes, turn_hash — see _tables().
_ZobristTables = tuple[
    tuple[tuple[int, int], ...], tuple[tuple[int, ...], tuple[int, ...]], int
]
_TABLES: dict[int, _ZobristTables] = {}


def _tables(n_cells: int):
    """Return (cell_hashes, tile_hashes, turn_hash) for a board of ``n_cells``.

    Deterministic: seeded from the board size, so runs and machines agree.
    ``cell_hashes[cell]`` is a pair for (PURPLE, GREEN); EMPTY hashes to 0.
    ``tile_hashes[player]`` is one word per tile. ``turn_hash`` is XORed in
    while GREEN is to move.
    """
    cached = _TABLES.get(n_cells)
    if cached is not None:
        return cached
    rng = Random(0xF11F_0000 ^ n_cells)
    cell_hashes = tuple(
        (rng.getrandbits(64), rng.getrandbits(64)) for _ in range(n_cells)
    )
    tile_hashes = (
        tuple(rng.getrandbits(64) for _ in range(len(TILES))),
        tuple(rng.getrandbits(64) for _ in range(len(TILES))),
    )
    turn_hash = rng.getrandbits(64)
    cached = (cell_hashes, tile_hashes, turn_hash)
    _TABLES[n_cells] = cached
    return cached


def _cell_hash(n_cells: int, cell: int, colour: Colour) -> int:
    if colour == Colour.EMPTY:
        return 0
    return _tables(n_cells)[0][cell][colour - 1]


def _tile_hash(n_cells: int, colour: Colour, tile: int) -> int:
    return _tables(n_cells)[1][colour - 1][tile]


@dataclass(frozen=True, slots=True)
class GameState:
    """An immutable FLIPHEX position.

    Attributes:
        n_cells: Board size (25 for the full game).
        colours: One :class:`Colour` per cell.
        hands: Hand bitmask per player, indexed ``[PURPLE-1, GREEN-1]``.
        to_move: The colour to move.
        history: Append-only ``(cell, tile_index, rotation)`` per ply. Metadata
            only — never read by search.
        zobrist: Incrementally maintained hash of the search-relevant state.
    """

    n_cells: int
    colours: tuple[Colour, ...]
    hands: tuple[int, int]
    to_move: Colour
    history: tuple[tuple[int, int, int], ...]
    zobrist: int

    # -- construction ---------------------------------------------------------

    @classmethod
    def initial(cls, n_cells: int = 25, first: Colour = Colour.PURPLE) -> GameState:
        """Return the opening position.

        The ``first`` player moves first and holds the joker (13 tiles); the
        other holds 12. The board starts empty.
        """
        hands = [_DECK_MASK, _DECK_MASK]
        hands[first - 1] = _DECK_WITH_JOKER_MASK
        colours = (Colour.EMPTY,) * n_cells

        z = 0
        for player in PLAYERS:
            for tile in tiles_in(hands[player - 1]):
                z ^= _tile_hash(n_cells, player, tile)
        if first == Colour.GREEN:
            z ^= _tables(n_cells)[2]

        return cls(n_cells, colours, (hands[0], hands[1]), first, (), z)

    @classmethod
    def build(
        cls,
        colours: tuple[Colour, ...],
        hands: tuple[int, int],
        to_move: Colour,
    ) -> GameState:
        """Return a state with these parts and a freshly computed Zobrist hash.

        History is empty. Used to reconstruct a position from notation; the
        resulting hash equals that of any state reached by play with the same
        colouring, hands, and turn.
        """
        n_cells = len(colours)
        z = 0
        for cell, colour in enumerate(colours):
            z ^= _cell_hash(n_cells, cell, colour)
        for player in PLAYERS:
            for tile in tiles_in(hands[player - 1]):
                z ^= _tile_hash(n_cells, player, tile)
        if to_move == Colour.GREEN:
            z ^= _tables(n_cells)[2]
        return cls(n_cells, tuple(colours), hands, to_move, (), z)

    # -- primitive transitions (used by moves.py) -----------------------------

    def with_colour(self, cell: int, colour: Colour) -> GameState:
        """Return a copy with ``cell`` set to ``colour`` (used for place + flip)."""
        old = self.colours[cell]
        if old == colour:
            return self
        colours = self.colours[:cell] + (colour,) + self.colours[cell + 1 :]
        z = (
            self.zobrist
            ^ _cell_hash(self.n_cells, cell, old)
            ^ _cell_hash(self.n_cells, cell, colour)
        )
        return replace(self, colours=colours, zobrist=z)

    def without_tile(self, colour: Colour, tile: int) -> GameState:
        """Return a copy with ``tile`` removed from ``colour``'s hand."""
        idx = colour - 1
        if not self.hands[idx] >> tile & 1:
            raise ValueError(f"{colour.name} does not hold tile {tile}")
        hands = list(self.hands)
        hands[idx] &= ~(1 << tile)
        z = self.zobrist ^ _tile_hash(self.n_cells, colour, tile)
        return replace(self, hands=(hands[0], hands[1]), zobrist=z)

    def switched(self) -> GameState:
        """Return a copy with the turn passed to the other colour."""
        z = self.zobrist ^ _tables(self.n_cells)[2]
        return replace(self, to_move=other(self.to_move), zobrist=z)

    def with_history(self, cell: int, tile: int, rotation: int) -> GameState:
        """Return a copy with a placement appended to ``history``.

        History is metadata; it does not change the Zobrist hash.
        """
        return replace(self, history=self.history + ((cell, tile, rotation),))

    # -- queries --------------------------------------------------------------

    def hand(self, colour: Colour) -> int:
        """Return ``colour``'s hand bitmask."""
        return self.hands[colour - 1]

    def ply(self) -> int:
        """Return how many tiles have been placed."""
        return self.n_cells - self.colours.count(Colour.EMPTY)

    def is_terminal(self) -> bool:
        """Return whether the board is full."""
        return Colour.EMPTY not in self.colours

    def score(self) -> tuple[int, int]:
        """Return ``(purple, green)`` cell counts."""
        return (self.colours.count(Colour.PURPLE), self.colours.count(Colour.GREEN))

    def key(self) -> tuple[tuple[Colour, ...], int, int, Colour]:
        """Return the transposition key: search-relevant state without history."""
        return (self.colours, self.hands[0], self.hands[1], self.to_move)
