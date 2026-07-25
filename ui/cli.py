"""Text interface to play or watch FLIPHEX.

Run from the repo root::

    python -m ui.cli                     # two humans, hotseat (default)
    python -m ui.cli --mode human-ai     # you (purple) vs the heuristic
    python -m ui.cli --mode ai-ai --seed 1

Built for rule validation: every move is explained (which arrows fired and what
flipped), you can preview all rotations before committing, and ``undo`` takes a
move back. Moves may be typed directly as ``CELL:ARCHETYPE:ROTATION`` (e.g.
``C3:P1:0``) or chosen step by step. Type ``help`` at the prompt.
"""

from __future__ import annotations

import argparse
import sys

from agents.base import Agent
from agents.heuristic_agent import HeuristicAgent
from agents.random_agent import RandomAgent
from fliphex.board import OFF_BOARD, Board
from fliphex.moves import Move, apply_move, legal_moves
from fliphex.notation import decode_move, encode_move
from fliphex.piece import DIRECTION_NAMES, N_SLOTS
from fliphex.rules import winner
from fliphex.state import TILES, Colour, GameState, other, tiles_in

_MARK = {Colour.EMPTY: "·", Colour.PURPLE: "P", Colour.GREEN: "G"}
_ANSI = {Colour.PURPLE: "\033[35m", Colour.GREEN: "\033[32m", Colour.EMPTY: "\033[2m"}
_RESET = "\033[0m"

# Sentinels returned by the human prompt in place of a Move.
QUIT = "quit"
UNDO = "undo"


# -- rendering ----------------------------------------------------------------


def _paint(text: str, colour: Colour, color: bool) -> str:
    return f"{_ANSI[colour]}{text}{_RESET}" if color else text


def render_board(board: Board, state: GameState, color: bool = False) -> str:
    """Return a multi-line ASCII picture of the board.

    Flat-top hexes in columns, odd columns dropped half a row (matching
    docs/board-geometry.md). Each cell shows its name and colour mark.
    """
    tokens: dict[tuple[int, int], str] = {}
    for cid in board.cells:
        col, row = divmod(cid, board.n_rows)
        band = 2 * row + (col & 1)
        colour = state.colours[cid]
        tokens[(col, band)] = _paint(
            f"{board.cell_name(cid)}{_MARK[colour]}", colour, color
        )

    lines: list[str] = []
    plain_width = 3
    for band in range(2 * board.n_rows + 1):
        cells = [tokens.get((col, band)) for col in range(board.n_cols)]
        if any(cells):
            lines.append(
                "  ".join(
                    tok if tok else " " * plain_width for tok in _padded(cells, color)
                )
            )
    return "\n".join(lines)


def _padded(cells: list[str | None], color: bool) -> list[str | None]:
    """Pad tokens to a common visible width (ANSI codes are zero-width)."""
    pad = 3 + (len(_ANSI[Colour.PURPLE]) + len(_RESET) if color else 0)
    return [None if c is None else f"{c:<{pad}}" for c in cells]


def describe_piece(tile: int) -> str:
    """Return e.g. ``"P2-opp (N,S)"`` — the archetype and its arrow directions."""
    piece = TILES[tile]
    dirs = ",".join(DIRECTION_NAMES[s] for s in piece.slots) or "no arrows"
    return f"{piece.archetype} ({dirs})"


def render_hand(state: GameState) -> str:
    """Return the side-to-move's remaining pieces, numbered, with their arrows."""
    tiles = list(tiles_in(state.hand(state.to_move)))
    return "\n".join(f"  {i + 1:2}. {describe_piece(t)}" for i, t in enumerate(tiles))


# -- move description ----------------------------------------------------------


def arrow_targets(
    board: Board, state: GameState, move: Move
) -> list[tuple[str, int, Colour]]:
    """Return ``(direction_name, target_cell, colour_before)`` per arrow.

    ``target_cell`` is :data:`~fliphex.board.OFF_BOARD` for an arrow leaving the
    board.
    """
    rotated = TILES[move.tile].rotated(move.rotation)
    out: list[tuple[str, int, Colour]] = []
    for direction in range(N_SLOTS):
        if rotated >> direction & 1:
            target = board.neighbour(move.cell, direction)
            colour = Colour.EMPTY if target == OFF_BOARD else state.colours[target]
            out.append((DIRECTION_NAMES[direction], target, colour))
    return out


def explain_move(board: Board, before: GameState, move: Move) -> str:
    """Return a one-line account of a move and every flip it causes."""
    mover = before.to_move
    parts = []
    for name, target, colour in arrow_targets(board, before, move):
        if target == OFF_BOARD:
            parts.append(f"{name}→edge")
        elif colour == Colour.EMPTY:
            parts.append(f"{name}→{board.cell_name(target)} empty")
        elif colour == mover:
            parts.append(f"{name}→{board.cell_name(target)} own")
        else:
            parts.append(
                f"{name}→{board.cell_name(target)} {colour.name}→{mover.name} FLIP"
            )
    arrows = "; ".join(parts) if parts else "no arrows"
    return (
        f"{mover.name} plays {TILES[move.tile].archetype} at "
        f"{board.cell_name(move.cell)} rot {move.rotation}  |  {arrows}"
    )


def _flip_count(board: Board, state: GameState, move: Move) -> int:
    opponent = other(state.to_move)
    return sum(
        colour == opponent for _, _, colour in arrow_targets(board, state, move)
    )


# -- human input ---------------------------------------------------------------

_HELP = """\
Commands:
  play                      choose a piece, cell, and rotation step by step
  CELL:ARCHETYPE:ROTATION   play directly, e.g. C3:P1:0  (rotation optional)
  hand                      list your remaining pieces and their arrows
  arrows                    show the arrows of every piece already on the board
  board                     redraw the board
  undo                      take back the last move
  help / quit
Arrow slots clockwise from North (rotation shifts them):
  """ + "  ".join(f"{i}={n}" for i, n in enumerate(DIRECTION_NAMES))


def _render_placed_arrows(board: Board, state: GameState) -> str:
    if not state.history:
        return "  (board empty)"
    lines = []
    for cell, tile, rot in state.history:
        rotated = TILES[tile].rotated(rot)
        dirs = ",".join(DIRECTION_NAMES[d] for d in range(N_SLOTS) if rotated >> d & 1)
        lines.append(
            f"  {board.cell_name(cell):3} {TILES[tile].archetype:8} → {dirs or '—'}"
        )
    return "\n".join(lines)


def _choose_piece(board: Board, state: GameState) -> int | None:
    tiles = list(tiles_in(state.hand(state.to_move)))
    print(render_hand(state))
    while True:
        raw = input("  piece (number/name, or 'back') > ").strip()
        if raw.lower() in {"back", "b", ""}:
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(tiles):
            return tiles[int(raw) - 1]
        for t in tiles:
            if TILES[t].archetype.lower() == raw.lower():
                return t
        print("  ? not one of your pieces")


def _choose_cell(board: Board, state: GameState) -> int | None:
    while True:
        raw = input("  cell (e.g. C3, or 'back') > ").strip()
        if raw.lower() in {"back", "b", ""}:
            return None
        try:
            cid = board.cell_id(raw)
        except ValueError:
            print("  ? no such cell")
            continue
        if state.colours[cid] != Colour.EMPTY:
            print("  ✗ that cell is occupied")
            continue
        return cid


def _choose_rotation(
    board: Board, state: GameState, cell: int, tile: int
) -> int | None:
    rotations = TILES[tile].distinct_rotations()
    print(f"  rotations for {TILES[tile].archetype} at {board.cell_name(cell)}:")
    for r in rotations:
        preview = explain_move(board, state, Move(cell, tile, r))
        flips = _flip_count(board, state, Move(cell, tile, r))
        print(f"    {r}: flips {flips}  |  {preview.split('|', 1)[1].strip()}")
    while True:
        raw = input("  rotation (or 'back') > ").strip()
        if raw.lower() in {"back", "b", ""}:
            return None
        if raw.isdigit() and int(raw) in rotations:
            return int(raw)
        print(f"  ? pick one of {list(rotations)}")


def _guided_move(board: Board, state: GameState) -> Move | None:
    tile = _choose_piece(board, state)
    if tile is None:
        return None
    cell = _choose_cell(board, state)
    if cell is None:
        return None
    rot = _choose_rotation(board, state, cell, tile)
    if rot is None:
        return None
    return Move(cell, tile, rot)


def _parse_move(board: Board, raw: str) -> Move | None:
    """Parse a direct move, tolerating an omitted rotation (defaults to 0)."""
    text = raw if raw.count(":") == 2 else f"{raw}:0"
    try:
        return decode_move(board, text)
    except (ValueError, KeyError):
        return None


def _prompt_human(board: Board, state: GameState, color: bool) -> Move | str:
    """Read a human move; return a Move, or the QUIT / UNDO sentinel."""
    legal = set(legal_moves(board, state))
    while True:
        raw = input(f"{state.to_move.name} > ").strip()
        low = raw.lower()
        if not raw:
            continue
        if low in {"quit", "q", "exit"}:
            return QUIT
        if low in {"undo", "u"}:
            return UNDO
        if low in {"help", "h", "?"}:
            print(_HELP)
            continue
        if low == "hand":
            print(render_hand(state))
            continue
        if low == "arrows":
            print(_render_placed_arrows(board, state))
            continue
        if low == "board":
            print(render_board(board, state, color))
            continue
        move = _guided_move(board, state) if low == "play" else _parse_move(board, raw)
        if move is None:
            if low != "play":
                print("  ? couldn't parse — try C3:P1:0, or 'play', or 'help'")
            continue
        if move not in legal:
            print("  ✗ illegal (occupied cell, piece not in hand, or bad rotation)")
            continue
        return move


# -- game loop -----------------------------------------------------------------


def play(
    board: Board,
    purple: Agent | None,
    green: Agent | None,
    first: Colour = Colour.PURPLE,
    color: bool = False,
) -> Colour:
    """Run one game. A ``None`` agent means a human plays that colour.

    Returns the winning colour.
    """
    agents = {Colour.PURPLE: purple, Colour.GREEN: green}
    stack = [GameState.initial(board.n_cells, first)]

    print(render_board(board, stack[-1], color))
    while not stack[-1].is_terminal():
        state = stack[-1]
        agent = agents[state.to_move]
        if agent is None:
            choice = _prompt_human(board, state, color)
            if choice == QUIT:
                print("abandoned.")
                raise SystemExit(0)
            if choice == UNDO:
                if len(stack) > 1:
                    stack.pop()
                    print("(undone)")
                    print(render_board(board, stack[-1], color))
                else:
                    print("  nothing to undo")
                continue
            move = choice
        else:
            move = agent.select(board, state)

        print(explain_move(board, state, move))
        stack.append(apply_move(board, state, move))
        print(render_board(board, stack[-1], color))
        purple_score, green_score = stack[-1].score()
        print(f"score  P {purple_score} - {green_score} G\n")

    win = winner(stack[-1])
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
        choices=["human-human", "human-ai", "ai-ai"],
        default="human-human",
        help="human-human is hotseat (default); human-ai puts you as purple",
    )
    parser.add_argument(
        "--first",
        choices=["purple", "green"],
        default="purple",
        help="which colour moves first and holds the joker",
    )
    parser.add_argument("--ai", choices=["heuristic", "random"], default="heuristic")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colour")
    args = parser.parse_args(argv)

    if args.mode == "human-human":
        purple = green = None
    elif args.mode == "ai-ai":
        purple = _make_agent(args.ai, args.seed)
        green = _make_agent(args.ai, None if args.seed is None else args.seed + 1)
    else:  # human-ai
        purple, green = None, _make_agent(args.ai, args.seed)

    first = Colour.PURPLE if args.first == "purple" else Colour.GREEN
    color = not args.no_color and sys.stdout.isatty()
    play(Board(), purple, green, first, color)


if __name__ == "__main__":
    main()
