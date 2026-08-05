"""Draw, side by side, a position and its mirror image -- and where it breaks.

Companion to ``scripts/check_mirror_game_symmetry.py``, which *proves* that the
board's Z/2 mirror is only a partial game symmetry. This one *shows* it.

Each case places one tile, fires its arrows, and then asks the same question of
the mirrored board: is there a tile in the deck that produces the mirrored
arrow pattern on the mirrored cell? For every achiral tile the answer is yes
(the same archetype, a different rotation). For the chiral ``P3-y`` it is no,
and the right-hand board simply cannot be drawn.

    python scripts/show_mirror_break.py

Boards are flat-top hexagons in five vertical columns of five; columns B and D
sit half a cell lower than A, C and E, which is why they are drawn offset.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_mirror_game_symmetry import (  # noqa: E402
    find_placement,
    fmt,
    mirror_mask,
    mirror_of,
)

from fliphex.board import DIRECTION_NAMES, OFF_BOARD, Board  # noqa: E402
from fliphex.moves import Move, apply_move  # noqa: E402
from fliphex.state import TILE_INDEX, TILES, Colour, GameState  # noqa: E402

GLYPH = {Colour.EMPTY: "·", Colour.PURPLE: "P", Colour.GREEN: "G"}
CELL_W = 6
N_LINES = 10


# -- rendering ----------------------------------------------------------------


def render(board: Board, colours, marks: dict[int, str], title: str) -> list[str]:
    """Return the board as text lines, B/D columns offset by half a row.

    ``marks`` overlays one character per cell: ``*`` placed, ``!`` flipped,
    ``?`` a cell the mirrored arrows would have hit.
    """
    grid = [[" "] * (5 * CELL_W) for _ in range(N_LINES)]
    for cid in board.cells:
        name = board.cell_name(cid)
        col = ord(name[0]) - ord("A")
        row = int(name[1])
        line = 2 * (row - 1) + (1 if col % 2 else 0)
        token = f"{name}{GLYPH[colours[cid]]}{marks.get(cid, ' ')}"
        for i, ch in enumerate(token):
            grid[line][col * CELL_W + i] = ch

    header = "".join(f"{chr(ord('A') + c):^{CELL_W}}" for c in range(5))
    body = ["".join(row).rstrip() for row in grid]
    return [title, header, *body]


def side_by_side(left: list[str], right: list[str], gap: int = 6) -> str:
    width = max((len(x) for x in left), default=0)
    n = max(len(left), len(right))
    out = []
    for i in range(n):
        lhs = (left[i] if i < len(left) else "").ljust(width)
        rhs = right[i] if i < len(right) else ""
        out.append((lhs + " " * gap + rhs).rstrip())
    return "\n".join(out)


# -- one case -----------------------------------------------------------------


def arrow_targets(board: Board, cell: int, pattern: int) -> list[tuple[int, int]]:
    """Return ``(direction, neighbour)`` for each arrow that lands on the board."""
    hits = []
    for d in range(6):
        if pattern >> d & 1:
            nb = board.neighbour(cell, d)
            if nb != OFF_BOARD:
                hits.append((d, nb))
    return hits


def setup(board: Board, cell: int, pattern: int, mover: Colour) -> GameState:
    """A position where every arrow of ``pattern`` has an enemy tile to flip."""
    colours = [Colour.EMPTY] * board.n_cells
    for _d, nb in arrow_targets(board, cell, pattern):
        colours[nb] = Colour.GREEN if mover == Colour.PURPLE else Colour.PURPLE
    hand = (1 << len(TILES)) - 1
    return GameState.build(tuple(colours), (hand, hand), mover)


def show_case(board: Board, pi, rho, archetype: str, rotation: int, cell_name: str) -> None:
    tile = TILE_INDEX[archetype]
    cell = board.cell_id(cell_name)
    pattern = TILES[tile].rotated(rotation)
    m_cell = pi[cell]
    m_pattern = mirror_mask(pattern, rho)

    print("\n" + "=" * 78)
    print(f"CASE — {archetype} on {cell_name}, rotation {rotation}, arrows {fmt(pattern)}")
    print("=" * 78)

    # left: the real position, before and after the flip
    state = setup(board, cell, pattern, Colour.PURPLE)
    after = apply_move(board, state, Move(cell, tile, rotation))
    flipped = {c for c in board.cells if state.colours[c] != after.colours[c] and c != cell}
    marks = {cell: "*", **{c: "!" for c in flipped}}
    left = render(board, after.colours, marks, f"original — play {archetype} on {cell_name}")

    # right: the mirror. Can any tile in a full deck produce the mirrored pattern?
    found = find_placement((1 << len(TILES)) - 1, m_pattern)
    m_colours = [Colour.EMPTY] * board.n_cells
    for c in board.cells:
        m_colours[pi[c]] = after.colours[c]
    m_marks = {pi[c]: mk for c, mk in marks.items()}

    if found is None:
        title = f"mirror — needs {fmt(m_pattern)} on {board.cell_name(m_cell)}: IMPOSSIBLE"
        right = render(board, tuple(m_colours), m_marks, title)
    else:
        m_tile, m_rot = found
        title = (
            f"mirror — play {TILES[m_tile].archetype} on "
            f"{board.cell_name(m_cell)}, rotation {m_rot}"
        )
        right = render(board, tuple(m_colours), m_marks, title)

    print(side_by_side(left, right))

    dirs = ", ".join(f"{DIRECTION_NAMES[d]}->{board.cell_name(nb)}" for d, nb in
                     arrow_targets(board, cell, pattern))
    m_dirs = ", ".join(f"{DIRECTION_NAMES[d]}->{board.cell_name(nb)}" for d, nb in
                       arrow_targets(board, m_cell, m_pattern))
    print(f"\n  arrows hit : {dirs}")
    print(f"  mirror hits: {m_dirs}")
    if found is None:
        print(f"\n  >> The mirror needs {fmt(m_pattern)}. Every rotation of {archetype}:")
        for r in TILES[tile].distinct_rotations():
            got = TILES[tile].rotated(r)
            print(f"       rot {r}: {fmt(got):<22} {'== needed' if got == m_pattern else '!='}")
        print(f"     None match, and no other tile in the deck does either. {archetype} is")
        print("     CHIRAL — a hex tile can be rotated but never turned over, so its own")
        print("     reflection is simply not one of the patterns it can present.")
        print("     The right-hand board is a position no legal move can reach.")
    else:
        m_tile, m_rot = found
        same = TILES[m_tile].archetype == archetype
        how = " (same archetype, rotated)" if same and m_rot != rotation else (
            " (same archetype, same rotation — mirror-invariant)" if same else "")
        print(f"\n  >> Mirrored by {TILES[m_tile].archetype} at rotation {m_rot}{how}."
              " Symmetry holds.")


def main() -> int:
    board = Board()
    pi, rho = mirror_of(board)

    print("Legend:  · empty   P purple   G green   * tile placed   ! flipped by an arrow")
    print("Columns B and D are drawn half a row lower — the board's real geometry.")

    show_case(board, pi, rho, "P3-y", 0, "B2")      # the break
    show_case(board, pi, rho, "P2-adj", 0, "B2")    # control: achiral, mirrors fine
    show_case(board, pi, rho, "P3-tri", 0, "B2")    # control: mirror-invariant

    print("\n" + "=" * 78)
    print("Only P3-y fails. Once both copies are placed and inert, every remaining")
    print("move mirrors, and the Z/2 symmetry is fully available — which is exactly")
    print("the endgame region the retrograde databases cover (adr-008).")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
