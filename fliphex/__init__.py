"""FLIPHEX game engine.

This package is the game itself and imports nothing else from the project
(see docs/engineering.md). Coordinates, directions, and adjacency follow
docs/adr/adr-002-coordinate-system.md.
"""

from fliphex.board import Board

__all__ = ["Board"]
