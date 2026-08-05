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
    mirror_state,
)

from fliphex.board import DIRECTION_NAMES, OFF_BOARD, Board  # noqa: E402
from fliphex.moves import Move, apply_move  # noqa: E402
from fliphex.state import TILE_INDEX, TILES, Colour, GameState  # noqa: E402

GLYPH = {Colour.EMPTY: "·", Colour.PURPLE: "P", Colour.GREEN: "G"}
CELL_W = 6
N_LINES = 10

_ANSI = {"reset": "", "purple": "", "green": "", "empty": "", "mark": ""}


def enable_colour(on: bool) -> None:
    """Turn ANSI colour on or off for the whole renderer."""
    _ANSI.update(
        {
            "reset": "\033[0m" if on else "",
            "purple": "\033[1;95m" if on else "",  # bright magenta
            "green": "\033[1;92m" if on else "",  # bright green
            "empty": "\033[90m" if on else "",  # dim
            "mark": "\033[1;93m" if on else "",  # yellow, for * and !
        }
    )


_KEY = {Colour.PURPLE: "purple", Colour.GREEN: "green", Colour.EMPTY: "empty"}


# -- rendering ----------------------------------------------------------------


def render(board: Board, colours, marks: dict[int, str], title: str) -> list[str]:
    """Return the board as text lines, B/D columns offset by half a row.

    ``marks`` overlays one character per cell: ``*`` placed, ``!`` flipped.
    Tokens are padded on their *plain* width, so ANSI codes never disturb the
    column alignment.
    """
    placed: list[dict[int, str]] = [{} for _ in range(N_LINES)]
    for cid in board.cells:
        name = board.cell_name(cid)
        col = ord(name[0]) - ord("A")
        row = int(name[1])
        line = 2 * (row - 1) + (1 if col % 2 else 0)
        mark = marks.get(cid, " ")
        body = f"{name}{GLYPH[colours[cid]]}"
        tail = f"{_ANSI['mark']}{mark}{_ANSI['reset']}" if mark != " " else " "
        placed[line][col] = f"{_ANSI[_KEY[colours[cid]]]}{body}{_ANSI['reset']}{tail}"

    body_lines = []
    for row_cells in placed:
        out = ""
        for col in range(5):
            token = row_cells.get(col)
            out += (token + " " * (CELL_W - 4)) if token else " " * CELL_W
        body_lines.append(out.rstrip())

    header = "".join(f"{chr(ord('A') + c):^{CELL_W}}" for c in range(5))
    return [title, header, *body_lines]


def vlen(s: str) -> int:
    """Visible width, ignoring ANSI escape sequences."""
    out, i = 0, 0
    while i < len(s):
        if s[i] == "\033":
            while i < len(s) and s[i] != "m":
                i += 1
            i += 1
        else:
            out += 1
            i += 1
    return out


def side_by_side(left: list[str], right: list[str], gap: int = 6) -> str:
    width = max((vlen(x) for x in left), default=0)
    n = max(len(left), len(right))
    out = []
    for i in range(n):
        lhs = left[i] if i < len(left) else ""
        rhs = right[i] if i < len(right) else ""
        out.append((lhs + " " * (width - vlen(lhs) + gap) + rhs).rstrip())
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


def _hits(board: Board, cell: int, pattern: int) -> str:
    return ", ".join(
        f"{DIRECTION_NAMES[d]}->{board.cell_name(nb)}"
        for d, nb in arrow_targets(board, cell, pattern)
    )


def show_case(board: Board, pi, rho, archetype: str, rotation: int, cell_name: str) -> None:
    """Walk one placement through the mirror, step by step.

    Told as a narrative rather than a picture, because the *position* on the
    right always looks symmetric -- what is missing is the **move**, and a
    board diagram cannot show a move that does not exist.
    """
    tile = TILE_INDEX[archetype]
    cell = board.cell_id(cell_name)
    pattern = TILES[tile].rotated(rotation)
    m_cell, m_pattern = pi[cell], mirror_mask(pattern, rho)
    found = find_placement((1 << len(TILES)) - 1, m_pattern)

    print("\n" + "=" * 78)
    verdict = "the mirror BREAKS" if found is None else "the mirror HOLDS"
    kind = "chiral" if found is None else "achiral"
    print(f"CASE — {archetype} ({kind}): {verdict}")
    print("=" * 78)

    before = setup(board, cell, pattern, Colour.PURPLE)
    m_before = mirror_state(before, pi)

    print("\nSTEP 1 — a position, and its mirror. These two ARE mirror images of")
    print("         each other; nothing is wrong yet.\n")
    print(side_by_side(
        render(board, before.colours, {}, "position  s"),
        render(board, m_before.colours, {}, "mirrored position  M(s)"),
    ))

    after = apply_move(board, before, Move(cell, tile, rotation))
    flipped = [c for c in board.cells if before.colours[c] != after.colours[c] and c != cell]
    print(f"\nSTEP 2 — purple plays {archetype} on {cell_name} (rotation {rotation}).")
    print(f"         Arrows {fmt(pattern)} fire once: {_hits(board, cell, pattern)}")
    print(f"         Flipped: {', '.join(board.cell_name(c) for c in flipped)}\n")
    print("\n".join(render(
        board, after.colours,
        {cell: "*", **{c: "!" for c in flipped}}, "after the move",
    )))

    print("\nSTEP 3 — for the mirror to keep in step, purple must now play the")
    print(f"         mirrored move: on {board.cell_name(m_cell)} with arrows "
          f"{fmt(m_pattern)}")
    print(f"         (which would hit {_hits(board, m_cell, m_pattern)}).")
    print(f"\n         Is that move available? Every rotation of {archetype}:")
    for r in TILES[tile].distinct_rotations():
        got = TILES[tile].rotated(r)
        flag = "  <== the one needed" if got == m_pattern else ""
        print(f"           rot {r}: {fmt(got):<24}{flag}")

    if found is None:
        print(f"\n         >> NONE match {fmt(m_pattern)}, and no other tile in the deck")
        print(f"            produces it either. {archetype} is CHIRAL: a hex tile can be")
        print("            rotated but never turned face-down, so its own reflection is")
        print("            not among the patterns it can present.")
        print("\n         >> There is NO legal move from M(s) giving the mirrored result.")
        print("            The position on the right of STEP 1 is fine. The *move* is")
        print("            what has no mirror image — and that is the whole break.")
        return

    m_tile, m_rot = found
    m_after = apply_move(board, m_before, Move(m_cell, m_tile, m_rot))
    m_flipped = [c for c in board.cells if m_before.colours[c] != m_after.colours[c]
                 and c != m_cell]
    same = TILES[m_tile].archetype == archetype
    note = ("same archetype, rotated" if same and m_rot != rotation
            else "same archetype, same rotation — mirror-invariant" if same
            else f"a different archetype, {TILES[m_tile].archetype}")
    print(f"\n         >> YES: rotation {m_rot} ({note}). Purple plays it on "
          f"{board.cell_name(m_cell)}.\n")
    print("\n".join(render(
        board, m_after.colours,
        {m_cell: "*", **{c: "!" for c in m_flipped}}, "mirrored board after the mirrored move",
    )))
    assert mirror_state(after, pi).colours == m_after.colours
    print("\n         >> And this equals M(result of STEP 2), checked exactly.")
    print("            Both the position and the move mirror. Symmetry holds.")


def show_inertness(board: Board) -> None:
    """Demonstrate adr-003/adr-006: a placed tile is a colour, nothing more.

    The ``*`` in the diagrams above is *presentation only* — it is taken from
    the move we just applied, not read back from the state. Once placed, a tile
    keeps no arrows, no rotation and no identity.
    """
    print("\n" + "=" * 78)
    print("ASIDE — a placed tile keeps no arrows (adr-003, adr-006)")
    print("=" * 78)

    tile, rotation, cell = TILE_INDEX["P3-y"], 0, board.cell_id("B2")
    pattern = TILES[tile].rotated(rotation)
    state = setup(board, cell, pattern, Colour.PURPLE)
    after = apply_move(board, state, Move(cell, tile, rotation))

    print("  after playing P3-y on B2, this is *everything* the state records for B2:")
    print(f"      colours[B2] = {after.colours[cell].name}")
    print("  there is no tile field and no rotation field — see fliphex/state.py.")
    print("  P3-y is now gone from the hand and B2 is a purple cell like any other.\n")

    # Green replies next to it with a tile whose arrow points back at B2.
    # If B2 still had arrows, they would re-fire. They do not.
    reply_cell = board.cell_id("B3")
    back = next(d for d in range(6) if board.neighbour(reply_cell, d) == cell)
    reply_tile = TILE_INDEX["P1"]
    reply_rot = next(
        r for r in TILES[reply_tile].distinct_rotations()
        if TILES[reply_tile].rotated(r) == 1 << back
    )
    final = apply_move(board, after, Move(reply_cell, reply_tile, reply_rot))

    changed = [board.cell_name(c) for c in board.cells if after.colours[c] != final.colours[c]]
    print("  NOTE: the two boards below are NOT a mirror pair — they are the SAME")
    print("        board, one ply apart. Only one tile is ever played per cell.\n")
    left = render(board, after.colours, {cell: "*"}, "ply n   — purple has just played B2")
    right = render(
        board, final.colours, {reply_cell: "*", cell: "!"},
        f"ply n+1 — green plays B3, arrow {DIRECTION_NAMES[back]} flips B2",
    )
    print(side_by_side(left, right))
    print(f"\n  cells that changed between the two: {', '.join(changed)}")
    print("  B2 did not receive a second tile. It was purple; green's single arrow")
    print("  flipped it, so it now reads G. That is the flip rule, not a placement.")
    print("\n  The point: B2's OWN arrows {N,NE,S} did not re-fire when it flipped —")
    print("  B1 and C2 are untouched. Once placed, a tile is only a colour: no")
    print("  arrows, no rotation, no identity (adr-003), and flips never chain")
    print("  (adr-006). The '*' in these diagrams is drawn from the move we just")
    print("  applied; the state itself does not record where anything was placed.")


def main() -> int:
    board = Board()
    enable_colour(sys.stdout.isatty() or "--color" in sys.argv)
    pi, rho = mirror_of(board)

    print("Legend:  · empty   P purple   G green   * tile placed   ! flipped by an arrow")
    print("Columns B and D are drawn half a row lower — the board's real geometry.")
    print("(pipe the output somewhere? pass --color to keep the colours)")

    show_case(board, pi, rho, "P3-y", 0, "B2")      # the break
    show_case(board, pi, rho, "P2-adj", 0, "B2")    # control: achiral, mirrors fine
    show_case(board, pi, rho, "P3-tri", 0, "B2")    # control: mirror-invariant
    show_inertness(board)

    print("\n" + "=" * 78)
    print("Only P3-y fails. Once both copies are placed and inert, every remaining")
    print("move mirrors, and the Z/2 symmetry is fully available — which is exactly")
    print("the endgame region the retrograde databases cover (adr-008).")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
