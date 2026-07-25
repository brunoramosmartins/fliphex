"""Text interface to play or watch FLIPHEX.

Run from the repo root::

    python -m ui.cli                     # you (purple) vs the heuristic
    python -m ui.cli --mode human-human
    python -m ui.cli --mode ai-ai --seed 1

Moves are typed in notation ``CELL:ARCHETYPE:ROTATION`` (e.g. ``C3:P1:0``); the
rotation may be omitted for the pieces that only have one orientation. Type
``help`` at the prompt for the full command list.
"""

from __future__ import annotations

import argparse

from agents.base import Agent
from agents.heuristic_agent import HeuristicAgent
from agents.random_agent import RandomAgent
from fliphex.board import Board
from fliphex.moves import Move, apply_move, legal_moves
from fliphex.notation import decode_move, encode_move
from fliphex.piece import DIRECTION_NAMES
from fliphex.rules import is_terminal, winner
from fliphex.state import TILES, Colour, GameState, tiles_in

_MARK = {Colour.EMPTY: "·", Colour.PURPLE: "P", Colour.GREEN: "G"}


def render_board(board: Board, state: GameState) -> str:
    """Return a multi-line ASCII picture of the board.

    Flat-top hexes in columns, odd columns dropped half a row (matching
    docs/board-geometry.md). Each cell shows its name and colour mark.
    """
    tokens: dict[tuple[int, int], str] = {}
    for cid in board.cells:
        col, row = divmod(cid, board.n_rows)
        band = 2 * row + (col & 1)
        tokens[(col, band)] = f"{board.cell_name(cid)}{_MARK[state.colours[cid]]}"

    lines: list[str] = []
    for band in range(2 * board.n_rows + 1):
        row_tokens = [tokens.get((col, band), "") for col in range(board.n_cols)]
        if any(row_tokens):
            lines.append("  ".join(f"{tok:<3}" if tok else "   " for tok in row_tokens))
    return "\n".join(lines)


def render_hand(state: GameState) -> str:
    """Return the side-to-move's remaining tiles as archetype names."""
    names = [TILES[t].archetype for t in tiles_in(state.hand(state.to_move))]
    return ", ".join(names)


_HELP = """\
Commands:
  CELL:ARCHETYPE:ROTATION   play a move, e.g. C3:P1:0 or C2:P2-opp:3
  hand                      list your remaining pieces
  moves                     list legal moves for the piece you name next
  board                     redraw the board
  help                      this help
  quit                      abandon the game

Directions (arrow slots), clockwise from North, rotation shifts them:
  """ + "  ".join(f"{i}={n}" for i, n in enumerate(DIRECTION_NAMES))


def _prompt_human(board: Board, state: GameState) -> Move | None:
    """Read a human move; return None if the player quits."""
    legal = set(legal_moves(board, state))
    while True:
        raw = input(f"{state.to_move.name} > ").strip()
        if not raw:
            continue
        low = raw.lower()
        if low in {"quit", "q", "exit"}:
            return None
        if low in {"help", "h", "?"}:
            print(_HELP)
            continue
        if low == "hand":
            print("  hand:", render_hand(state))
            continue
        if low == "board":
            print(render_board(board, state))
            continue
        if low == "moves":
            print("  legal:", ", ".join(encode_move(board, m) for m in sorted(legal)))
            continue
        move = _parse_move(board, raw)
        if move is None:
            print("  ? couldn't parse — try e.g. C3:P1:0, or 'help'")
        elif move not in legal:
            print("  ✗ illegal move (occupied cell, piece not in hand, or bad rotation)")
        else:
            return move


def _parse_move(board: Board, raw: str) -> Move | None:
    """Parse a move, tolerating an omitted rotation (defaults to 0)."""
    text = raw if raw.count(":") == 2 else f"{raw}:0"
    try:
        return decode_move(board, text)
    except (ValueError, KeyError):
        return None


def play(
    board: Board,
    purple: Agent | None,
    green: Agent | None,
    first: Colour = Colour.PURPLE,
) -> Colour:
    """Run one game. A ``None`` agent means a human plays that colour.

    Returns the winning colour.
    """
    agents = {Colour.PURPLE: purple, Colour.GREEN: green}
    state = GameState.initial(board.n_cells, first)

    print(render_board(board, state))
    while not is_terminal(state):
        agent = agents[state.to_move]
        if agent is None:
            move = _prompt_human(board, state)
            if move is None:
                print("abandoned.")
                raise SystemExit(0)
        else:
            move = agent.select(board, state)
            print(f"{state.to_move.name} ({agent}) plays {encode_move(board, move)}")
        state = apply_move(board, state, move)
        print(render_board(board, state))
        purple_score, green_score = state.score()
        print(f"score  P {purple_score} - {green_score} G\n")

    win = winner(state)
    print(f"== {win.name} wins ==")
    return win


def _make_agent(kind: str, seed: int | None) -> Agent | None:
    if kind == "human":
        return None
    if kind == "heuristic":
        return HeuristicAgent(seed=seed)
    if kind == "random":
        return RandomAgent(seed=seed)
    raise ValueError(f"unknown agent: {kind}")


def main(argv: list[str] | None = None) -> None:
    """Parse arguments and run a game."""
    parser = argparse.ArgumentParser(description="Play or watch FLIPHEX.")
    parser.add_argument(
        "--mode",
        choices=["human-ai", "human-human", "ai-ai"],
        default="human-ai",
    )
    parser.add_argument(
        "--first", choices=["purple", "green"], default="purple",
        help="which colour moves first and holds the joker",
    )
    parser.add_argument("--ai", choices=["heuristic", "random"], default="heuristic")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args(argv)

    purple: Agent | None
    green: Agent | None
    if args.mode == "human-human":
        purple = green = None
    elif args.mode == "ai-ai":
        purple = _make_agent(args.ai, args.seed)
        green = _make_agent(args.ai, None if args.seed is None else args.seed + 1)
    else:  # human-ai: human is purple, AI is green
        purple = None
        green = _make_agent(args.ai, args.seed)

    first = Colour.PURPLE if args.first == "purple" else Colour.GREEN
    play(Board(), purple, green, first)


if __name__ == "__main__":
    main()
