"""Text interface to play or watch FLIPHEX.

Run from the repo root::

    python -m ui.cli                              # two humans, hotseat
    python -m ui.cli --green heuristic            # you (purple) vs the heuristic
    python -m ui.cli --green solver --variant 3x3 # vs perfect play
    python -m ui.cli --green az                   # vs the trained champion
    python -m ui.cli --purple az --green solver   # watch two agents

Built for rule validation: every move is explained (which arrows fired and what
flipped), you can preview all rotations before committing, and ``undo`` takes a
move back. Moves may be typed directly as ``CELL:ARCHETYPE:ROTATION`` (e.g.
``C3:P1:0``) or chosen step by step. Type ``help`` at the prompt.

Seats, not modes
----------------
Each colour is named independently — ``--purple`` and ``--green``, from
:data:`ui.seats.SEAT_KINDS` — rather than picked from a fixed list of
matchups. The old ``--mode`` spellings still work and are mapped onto seats.

Reduced boards get reduced decks
--------------------------------
``--variant`` goes through :class:`~fliphex.variant.Variant`, so a 3x3 is
played with the 5 + 4 hands adr-009 and adr-011 define. Building the opening
from the board's cell count alone would deal the full 13 + 12 deck onto nine
cells, which is a different game and not one the solved artefacts describe.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agents.base import Agent
from agents.solver_agent import SolverAgent
from fliphex.board import OFF_BOARD, Board
from fliphex.moves import Move, apply_move, legal_moves
from fliphex.notation import decode_move
from fliphex.piece import DIRECTION_NAMES, N_SLOTS
from fliphex.rules import winner
from fliphex.state import TILES, Colour, GameState, other, tiles_in
from fliphex.variant import Arm, Variant
from ui.seats import (
    DEFAULT_RUN_ROOT,
    DEFAULT_SIMULATIONS,
    SEAT_KINDS,
    ChampionUnavailableError,
    build_seat,
    describe_seat,
)

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
    """Return a one-line account of a move and every flip it causes.

    Flips are toggles (adr-007): an arrow at an own tile is a self-flip that
    hands it to the opponent.
    """
    mover = before.to_move
    opponent = other(mover)
    parts = []
    for name, target, colour in arrow_targets(board, before, move):
        cell = board.cell_name(target) if target != OFF_BOARD else None
        if target == OFF_BOARD:
            parts.append(f"{name}→edge")
        elif colour == Colour.EMPTY:
            parts.append(f"{name}→{cell} empty")
        elif colour == opponent:
            parts.append(f"{name}→{cell} {colour.name}→{mover.name} FLIP")
        else:  # own tile — self-flip
            parts.append(f"{name}→{cell} {colour.name}→{opponent.name} self-FLIP!")
    arrows = "; ".join(parts) if parts else "no arrows"
    return (
        f"{mover.name} plays {TILES[move.tile].archetype} at "
        f"{board.cell_name(move.cell)} rot {move.rotation}  |  {arrows}"
    )


def _net_flips(board: Board, state: GameState, move: Move) -> int:
    """Net colour swing for the side to move (opponent flips minus self-flips)."""
    mover = state.to_move
    opponent = other(mover)
    net = 0
    for _, _, colour in arrow_targets(board, state, move):
        if colour == opponent:
            net += 1
        elif colour == mover:
            net -= 1
    return net


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
        net = _net_flips(board, state, Move(cell, tile, r))
        print(f"    {r}: net {net:+d}  |  {preview.split('|', 1)[1].strip()}")
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


def header(variant: Variant, purple: Agent | None, green: Agent | None) -> str:
    """Name the board, the decks and who is sitting where.

    The deck is printed because adr-004 R3 requires it of every artefact: a
    bare "5x3 game" is ambiguous, since the deck a reduced board is played with
    is a modeling choice rather than a consequence of its size.
    """
    first_deck, second_deck = variant.deck_names()
    larger = "PURPLE" if variant.first == Colour.PURPLE else "GREEN"
    return "\n".join(
        [
            f"  board    {variant.n_cols}x{variant.n_rows} "
            f"({variant.n_cells} cells), arm {variant.arm.value}",
            f"  PURPLE   {describe_seat(purple)}",
            f"  GREEN    {describe_seat(green)}",
            f"  {larger} moves first and holds {len(first_deck)} tiles: "
            f"{', '.join(first_deck)}",
            f"  the other holds {len(second_deck)}: {', '.join(second_deck)}",
        ]
    )


def _report_solver(colour: Colour, agent: Agent | None) -> None:
    """Print a solver seat's proved rate, which no result may be quoted without.

    A solver that fell back to its heuristic for most of a game played mostly
    heuristic moves, and the win says correspondingly little. EXP-017 records
    the same number for the same reason.
    """
    if not isinstance(agent, SolverAgent):
        return
    stats = agent.stats()
    print(
        f"  {colour.name} solver: {stats['proved']}/{stats['moves']} moves proved "
        f"({stats['proved_rate']:.0%}), {stats['delegated_unattempted']} not "
        f"attempted, {stats['delegated_over_budget']} over budget"
    )


def play(
    variant: Variant,
    purple: Agent | None,
    green: Agent | None,
    color: bool = False,
) -> Colour:
    """Run one game on ``variant``. A ``None`` agent means a human plays it.

    Returns the winning colour.
    """
    board = variant.board()
    agents = {Colour.PURPLE: purple, Colour.GREEN: green}
    stack = [variant.initial_state()]

    print(header(variant, purple, green))
    print()
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
    _report_solver(Colour.PURPLE, purple)
    _report_solver(Colour.GREEN, green)
    return win


#: The pre-seat spellings, kept working. Each maps to a ``(purple, green)``
#: pair, with ``None`` meaning "whatever ``--ai`` says".
_LEGACY_MODES: dict[str, tuple[str | None, str | None]] = {
    "human-human": ("human", "human"),
    "human-ai": ("human", None),
    "ai-ai": (None, None),
}


def resolve_kinds(
    purple: str | None, green: str | None, mode: str | None, ai: str
) -> dict[Colour, str]:
    """Decide who plays each colour from the flags given.

    Explicit ``--purple`` / ``--green`` always win. A legacy ``--mode`` fills
    the seats it names, and a ``None`` inside it means "the agent ``--ai``
    selects". With nothing given at all the game is hotseat.

    Separate from :func:`main` because it is the one piece of argument handling
    worth testing without starting a game — and the piece another interface
    would reuse rather than re-derive.
    """
    legacy = _LEGACY_MODES.get(mode or "", ("human", "human"))
    return {
        Colour.PURPLE: purple or legacy[0] or ai,
        Colour.GREEN: green or legacy[1] or ai,
    }


def _variant_from(spec: str, arm: str, first: str) -> Variant:
    """Parse ``5x3`` into a :class:`~fliphex.variant.Variant`.

    ``Variant`` enforces adr-011's odd cell count and adr-009's anchors, so a
    bad size is refused here with its own explanation rather than producing a
    board that cannot be scored.
    """
    cols, _, rows = spec.lower().partition("x")
    try:
        n_cols, n_rows = int(cols), int(rows)
    except ValueError:
        raise SystemExit(
            f"  ✗ --variant wants COLSxROWS, e.g. 5x3 — got {spec!r}"
        ) from None
    try:
        return Variant(
            n_cols,
            n_rows,
            Arm(arm),
            Colour.PURPLE if first == "purple" else Colour.GREEN,
        )
    except ValueError as exc:
        raise SystemExit(f"  ✗ {exc}") from None


def main(argv: list[str] | None = None) -> None:
    """Parse arguments and run a game."""
    parser = argparse.ArgumentParser(description="Play or watch FLIPHEX.")
    parser.add_argument("--purple", choices=SEAT_KINDS, help="who plays purple")
    parser.add_argument("--green", choices=SEAT_KINDS, help="who plays green")
    parser.add_argument(
        "--variant",
        default="5x5",
        help="board as COLSxROWS (default 5x5). Reduced boards use reduced decks",
    )
    parser.add_argument(
        "--arm",
        choices=[a.value for a in Arm],
        default=Arm.H1.value,
        help="h1 gives player one the joker; h2 swaps it for the next archetype",
    )
    parser.add_argument(
        "--first",
        choices=["purple", "green"],
        default="purple",
        help="which colour moves first and holds the larger hand",
    )
    parser.add_argument(
        "--mode",
        choices=sorted(_LEGACY_MODES),
        help="the pre-seat spelling; --purple/--green supersede it",
    )
    parser.add_argument("--ai", choices=SEAT_KINDS, default="heuristic")
    parser.add_argument(
        "--az-run",
        type=Path,
        default=DEFAULT_RUN_ROOT,
        help="training run directory holding the champion, for the az seat",
    )
    parser.add_argument(
        "--simulations",
        type=int,
        default=DEFAULT_SIMULATIONS,
        help="PUCT simulations per move for the az and uct seats",
    )
    parser.add_argument(
        "--solver-nodes",
        type=int,
        default=None,
        help="override the solver's node budget (default is per board size)",
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colour")
    args = parser.parse_args(argv)

    kinds = resolve_kinds(args.purple, args.green, args.mode, args.ai)
    variant = _variant_from(args.variant, args.arm, args.first)
    seats: dict[Colour, Agent | None] = {}
    for offset, (colour, kind) in enumerate(kinds.items()):
        # Distinct seeds per seat: one seed shared by two stochastic agents
        # replays the same stream on both sides of the board.
        seat_seed = None if args.seed is None else args.seed + offset
        try:
            seats[colour] = build_seat(
                kind,
                variant=variant,
                seed=seat_seed,
                run_root=args.az_run,
                simulations=args.simulations,
                max_nodes=args.solver_nodes,
            )
        except ChampionUnavailableError as exc:
            raise SystemExit(f"  ✗ {colour.name} seat: {exc}") from None

    color = not args.no_color and sys.stdout.isatty()
    play(variant, seats[Colour.PURPLE], seats[Colour.GREEN], color)


if __name__ == "__main__":
    main()
