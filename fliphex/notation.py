"""String encoding of moves, games, and positions.

All human-facing; cells are ``A1``–``E5`` (adr-002). Two round-trippable forms:

- **Move / game** — a move is ``CELL:ARCHETYPE:ROTATION`` (e.g. ``C3:P1:0``,
  ``C2:P2-opp:0``); a game is the starting colour followed by its moves, so it
  replays exactly.
- **Position** — the board colouring, the side to move, and both hand bitmasks,
  enough to reconstruct the search state (history is not recoverable and is
  left empty on decode).
"""

from __future__ import annotations

from fliphex.board import Board
from fliphex.moves import Move, apply_move
from fliphex.state import TILE_INDEX, TILES, Colour, GameState

_COLOUR_CHAR: dict[Colour, str] = {
    Colour.EMPTY: ".",
    Colour.PURPLE: "P",
    Colour.GREEN: "G",
}
_CHAR_COLOUR: dict[str, Colour] = {v: k for k, v in _COLOUR_CHAR.items()}


# -- moves and games ----------------------------------------------------------


def encode_move(board: Board, move: Move) -> str:
    """Return e.g. ``"C3:P1:0"`` for a move."""
    return f"{board.cell_name(move.cell)}:{TILES[move.tile].archetype}:{move.rotation}"


def decode_move(board: Board, text: str) -> Move:
    """Parse ``"C3:P1:0"`` back into a :class:`~fliphex.moves.Move`."""
    name, archetype, rotation = text.split(":")
    return Move(board.cell_id(name), TILE_INDEX[archetype], int(rotation))


def encode_game(board: Board, first: Colour, moves: list[Move]) -> str:
    """Encode a game as ``"<FIRST> <move> <move> ..."``."""
    tokens = [first.name] + [encode_move(board, m) for m in moves]
    return " ".join(tokens)


def decode_game(board: Board, text: str) -> tuple[Colour, list[Move]]:
    """Parse a game string into ``(first_colour, moves)``."""
    tokens = text.split()
    first = Colour[tokens[0]]
    moves = [decode_move(board, tok) for tok in tokens[1:]]
    return first, moves


def replay(board: Board, first: Colour, moves: list[Move]) -> GameState:
    """Apply ``moves`` from the opening position and return the final state."""
    state = GameState.initial(board.n_cells, first)
    for move in moves:
        state = apply_move(board, state, move)
    return state


# -- positions ----------------------------------------------------------------


def encode_state(state: GameState) -> str:
    """Encode the search state as ``"<colours> <to_move> <hp> <hg>"``.

    ``colours`` is one char per cell (``.PG``); hands are hex bitmasks.
    """
    colours = "".join(_COLOUR_CHAR[c] for c in state.colours)
    return (
        f"{colours} {_COLOUR_CHAR[state.to_move]} "
        f"{state.hands[0]:x} {state.hands[1]:x}"
    )


def decode_state(text: str) -> GameState:
    """Reconstruct a search state from :func:`encode_state` output.

    History is not encoded, so the returned state has an empty history; its
    Zobrist hash still matches the original.
    """
    colours_str, to_move, hp, hg = text.split()
    colours = tuple(_CHAR_COLOUR[ch] for ch in colours_str)
    return GameState.build(colours, (int(hp, 16), int(hg, 16)), _CHAR_COLOUR[to_move])
