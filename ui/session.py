"""One game, as every interface sees it. Plain dicts in, plain dicts out.

This is the Python surface the *graphical* interfaces share — the browser page
and the pygame window both drive it, and neither one holds a rule. It started
life as ``ui/web_bridge.py``, named for its only caller; the name was wrong as
soon as a second interface wanted the same thing, which is why it is
:mod:`ui.session` now.

It is deliberately small and deliberately **testable natively**: every function
here runs under CPython in the test suite, under Pyodide in the page and under
CPython again behind pygame, and nothing in it touches a display. When a board
looks wrong, the question "is it the rules or is it the drawing?" has to be
answerable, and it is only answerable if this half can be exercised without
either.

Per [adr-013](../docs/adr/adr-013-interface-targets.md) clause 2, the rules are
**never reimplemented** outside the engine. The interface draws; this decides.
Every move an interface can offer is one ``fliphex.legal_moves`` returned, and
every flip it animates is one ``fliphex.apply_move`` produced.

The layout is here rather than in the interface
-----------------------------------------------
:func:`layout` computes each cell's centre in hex-radius units. It lives on this
side because no interface may invent a second geometry — ``docs/board-geometry.md``
is generated from the engine, and a hand-placed board would be a third
description able to disagree with both. Two renderers making the same mistake
independently is worse than one making it, so neither is allowed to try:
:func:`layout` is checked against ``Board.neighbour`` by test, and both the SVG
page and the pygame window scale its output rather than recomputing it.
"""

from __future__ import annotations

from math import sqrt
from typing import Any

from agents.base import Agent
from fliphex.board import OFF_BOARD, Board
from fliphex.moves import Move, apply_move, legal_moves
from fliphex.piece import DIRECTION_NAMES, N_SLOTS
from fliphex.rules import winner
from fliphex.state import TILES, Colour, GameState, other, tiles_in
from fliphex.variant import Arm, Variant

#: Vertical step between two cells in the same column, in hex-radius units.
#: Flat-top hexagons tile with a vertical pitch of ``sqrt(3) * R``.
ROW_PITCH = sqrt(3.0)

#: Horizontal step between adjacent columns. Flat-top hexagons interlock, so
#: columns sit at ``1.5 * R`` rather than at ``2 * R``.
COL_PITCH = 1.5


def layout(board: Board) -> list[dict[str, Any]]:
    """Return one record per cell: id, name, column, row and centre.

    Flat-top hexagons in columns, odd columns dropped half a row — the same
    arrangement ``ui.cli.render_board`` draws in text and the one
    ``docs/board-geometry.md`` describes. ``band = 2 * row + (col & 1)`` is the
    half-row index, and the centre follows from it directly.
    """
    cells = []
    for cid in board.cells:
        col, row = divmod(cid, board.n_rows)
        band = 2 * row + (col & 1)
        cells.append(
            {
                "id": cid,
                "name": board.cell_name(cid),
                "col": col,
                "row": row,
                "x": col * COL_PITCH,
                "y": band * ROW_PITCH / 2.0,
            }
        )
    return cells


def arrows_of(tile: int, rotation: int) -> list[int]:
    """Return the slot indices carrying an arrow, clockwise from North."""
    rotated = TILES[tile].rotated(rotation)
    return [slot for slot in range(N_SLOTS) if rotated >> slot & 1]


def _effects(board: Board, state: GameState, move: Move) -> list[dict[str, Any]]:
    """What each arrow of ``move`` does, for the page to animate.

    ``kind`` is one of ``edge``, ``empty``, ``flip`` or ``self-flip``. The last
    is not a curiosity: a flip is a toggle (adr-007), so an arrow pointing at
    your own tile hands it to the opponent, and a player who cannot see that
    happen cannot learn the rule.
    """
    mover, opponent = state.to_move, other(state.to_move)
    out = []
    for slot in arrows_of(move.tile, move.rotation):
        target = board.neighbour(move.cell, slot)
        if target == OFF_BOARD:
            kind, colour = "edge", None
        else:
            colour = state.colours[target]
            if colour == Colour.EMPTY:
                kind = "empty"
            elif colour == opponent:
                kind = "flip"
            else:
                kind = "self-flip"
        out.append(
            {
                "slot": slot,
                "direction": DIRECTION_NAMES[slot],
                "target": None if target == OFF_BOARD else target,
                "kind": kind,
                "becomes": (
                    None
                    if kind in ("edge", "empty")
                    else (mover.name if kind == "flip" else opponent.name)
                ),
            }
        )
    return out


def _net_flips(effects: list[dict[str, Any]]) -> int:
    """Colour swing for the mover: gains minus the tiles handed back."""
    return sum(1 for e in effects if e["kind"] == "flip") - sum(
        1 for e in effects if e["kind"] == "self-flip"
    )


class GameSession:
    """One game, with an undo stack. Everything the page needs is a method here.

    Holds no agent. The page names a seat per move instead, so a visitor can
    change their mind about who they are playing without restarting — and so
    that constructing a learner, which is expensive, never happens for a game
    that does not use one.
    """

    def __init__(
        self,
        n_cols: int = 5,
        n_rows: int = 5,
        arm: str = "h1",
        first: str = "purple",
    ) -> None:
        self.variant = Variant(
            n_cols,
            n_rows,
            Arm(arm),
            Colour.PURPLE if first == "purple" else Colour.GREEN,
        )
        self.board = self.variant.board()
        self.stack: list[GameState] = [self.variant.initial_state()]

    # -- reading ---------------------------------------------------------------

    @property
    def state(self) -> GameState:
        return self.stack[-1]

    def geometry(self) -> dict[str, Any]:
        """The board's shape and decks. Sent once, when a game starts."""
        first_deck, second_deck = self.variant.deck_names()
        return {
            "n_cols": self.variant.n_cols,
            "n_rows": self.variant.n_rows,
            "n_cells": self.variant.n_cells,
            "arm": self.variant.arm.value,
            "first": self.variant.first.name,
            "cells": layout(self.board),
            "directions": list(DIRECTION_NAMES),
            "decks": {"first": list(first_deck), "second": list(second_deck)},
        }

    def hand(self, colour: str) -> list[dict[str, Any]]:
        """The named colour's remaining pieces, with their arrows at rotation 0."""
        player = Colour.PURPLE if colour == "PURPLE" else Colour.GREEN
        return [
            {
                "tile": tile,
                "archetype": TILES[tile].archetype,
                "rotations": list(TILES[tile].distinct_rotations()),
                "arrows": arrows_of(tile, 0),
            }
            for tile in tiles_in(self.state.hand(player))
        ]

    def snapshot(self) -> dict[str, Any]:
        """Everything that changes ply to ply."""
        state = self.state
        purple, green = state.score()
        terminal = state.is_terminal()
        return {
            "colours": [c.name for c in state.colours],
            "to_move": state.to_move.name,
            "ply": len(state.history),
            "score": {"PURPLE": purple, "GREEN": green},
            "terminal": terminal,
            "winner": winner(state).name if terminal else None,
            "can_undo": len(self.stack) > 1,
            "hands": {
                "PURPLE": self.hand("PURPLE"),
                "GREEN": self.hand("GREEN"),
            },
        }

    def options(self, cell: int, tile: int) -> list[dict[str, Any]]:
        """Every distinct rotation of ``tile`` at ``cell``, with its consequences.

        This is the rotation preview. It is the one affordance the text CLI has
        that a board game normally does not, and it is what makes the arrows
        learnable: you see what a rotation would do before committing to it.
        """
        legal = set(legal_moves(self.board, self.state))
        out = []
        for rotation in TILES[tile].distinct_rotations():
            move = Move(cell, tile, rotation)
            if move not in legal:
                continue
            effects = _effects(self.board, self.state, move)
            out.append(
                {
                    "rotation": rotation,
                    "arrows": arrows_of(tile, rotation),
                    "effects": effects,
                    "net": _net_flips(effects),
                }
            )
        return out

    def playable_cells(self, tile: int) -> list[int]:
        """Cells ``tile`` may be placed on. Empty ones, but asked of the engine."""
        return sorted(
            {m.cell for m in legal_moves(self.board, self.state) if m.tile == tile}
        )

    # -- writing ---------------------------------------------------------------

    def play(self, cell: int, tile: int, rotation: int) -> dict[str, Any]:
        """Apply a move and return what happened, for the page to animate.

        Raises:
            ValueError: If the move is not legal. The page is expected to offer
                only legal moves, so this firing means the two halves disagree
                and the rules win.
        """
        move = Move(cell, tile, rotation)
        if move not in set(legal_moves(self.board, self.state)):
            raise ValueError(f"illegal move: {move}")
        before = self.state
        effects = _effects(self.board, before, move)
        self.stack.append(apply_move(self.board, before, move))
        return {
            "move": {"cell": cell, "tile": tile, "rotation": rotation},
            "archetype": TILES[move.tile].archetype,
            "placed_as": before.to_move.name,
            "effects": effects,
            "flipped": [
                e["target"] for e in effects if e["kind"] in ("flip", "self-flip")
            ],
            "net": _net_flips(effects),
            "snapshot": self.snapshot(),
        }

    def undo(self) -> dict[str, Any]:
        """Take back one ply. A no-op at the opening rather than an error."""
        if len(self.stack) > 1:
            self.stack.pop()
        return self.snapshot()

    def agent_move(self, agent: Agent) -> dict[str, Any]:
        """Let ``agent`` choose and play. The page builds the agent via ui.seats."""
        move = agent.select(self.board, self.state)
        return self.play(move.cell, move.tile, move.rotation)

    def agent_move_by_name(self, kind: str, seed: int | None = None) -> dict[str, Any]:
        """Build a seat by name and play one move with it.

        Built fresh each time rather than held, because the page lets a visitor
        change opponent mid-game and because a seat nobody selects should never
        be constructed — for the learner that would mean loading torch.
        """
        from ui.seats import build_seat

        agent = build_seat(kind, variant=self.variant, seed=seed)
        if agent is None:
            raise ValueError(f"{kind!r} is a human seat, so it has no move to make")
        return self.agent_move(agent)

    # -- redrawing -------------------------------------------------------------

    def history_for_drawing(self) -> list[dict[str, Any]]:
        """Every placed tile with the arrows it fired, in order.

        Placed tiles are inert (adr-003) — the search state keeps only a colour
        per cell, and these arrows can never fire again. They are drawn anyway,
        because a player who cannot see what a tile did cannot learn what the
        next one will do, and reconstructing them from ``state.history`` is the
        only place that information survives.
        """
        return [
            {
                "cell": cell,
                "tile": tile,
                "rotation": rotation,
                "arrows": arrows_of(tile, rotation),
            }
            for cell, tile, rotation in self.state.history
        ]
