"""FLIPHEX game engine.

This package is the game itself and imports nothing else from the project
(see docs/engineering.md). Coordinates, directions, and adjacency follow
docs/adr/adr-002-coordinate-system.md.

The names below are the package's **public surface** — the seam that `solver/`,
`az/`, `complexity/`, `agents/` and `ui/` import across. That seam is not
cosmetic: the dependency rule (those packages import `fliphex/` and never each
other) is what keeps the Phase 5 cross-axis verification honest, so it is worth
stating what crossing it is allowed to reach. Anything not listed here is an
implementation detail and may change without an ADR.

Two rules keep this file safe:

- **Consumers** may import either from here or from the submodule; both are
  supported and equivalent.
- **Modules inside `fliphex/` must never do `from fliphex import X`.** They
  import each other directly (`from fliphex.board import Board`). Importing
  through the package root from inside the package is what turns a clean tree
  into an import cycle.
"""

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
from fliphex.piece import ARCHETYPES, DECK, JOKER, N_SLOTS, Piece
from fliphex.rules import is_terminal, margin, outcome, score, winner
from fliphex.state import (
    JOKER_INDEX,
    PLAYERS,
    TILE_INDEX,
    TILES,
    Colour,
    GameState,
    other,
    tiles_in,
)
from fliphex.variant import (
    FIVE_BY_THREE,
    FULL_GAME,
    THREE_BY_THREE,
    Arm,
    Variant,
    archetypes_for,
)

__all__ = [
    # board
    "Board",
    # pieces
    "ARCHETYPES",
    "DECK",
    "JOKER",
    "N_SLOTS",
    "Piece",
    # state
    "Colour",
    "GameState",
    "JOKER_INDEX",
    "PLAYERS",
    "TILES",
    "TILE_INDEX",
    "other",
    "tiles_in",
    # moves
    "Move",
    "apply_move",
    "legal_moves",
    # rules
    "is_terminal",
    "margin",
    "outcome",
    "score",
    "winner",
    # variants (adr-009, adr-011)
    "Arm",
    "Variant",
    "archetypes_for",
    "FULL_GAME",
    "FIVE_BY_THREE",
    "THREE_BY_THREE",
    # notation
    "decode_game",
    "decode_move",
    "decode_state",
    "encode_game",
    "encode_move",
    "encode_state",
    "replay",
]
