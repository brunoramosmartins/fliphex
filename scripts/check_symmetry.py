"""Compute the automorphism group of the FLIPHEX board as a directed hex graph.

A board *symmetry* is a pair ``(pi, rho)`` where ``pi`` permutes the cells and
``rho`` is one of the twelve dihedral (``D6``) actions on the six arrow
directions, such that for every cell ``u`` and direction ``d``::

    neighbour(pi(u), rho(d)) == pi(neighbour(u, d))

with :data:`~fliphex.board.OFF_BOARD` mapping to itself. This is exactly a
relabelling that preserves both adjacency *and* the arrow-direction structure
the flip rule depends on — i.e. a symmetry a solver or self-play pipeline could
legitimately exploit for canonicalisation or data augmentation.

Result on the full 5x5 board: the group has order 2 — the identity and a single
left-right **mirror** across column C. 180-degree rotation is *not* a symmetry.
See ``docs/adr/adr-008-board-mirror-symmetry.md``.

    python scripts/check_symmetry.py          # full board
    python scripts/check_symmetry.py 3 3      # a reduced variant

Note: this is a symmetry of the board geometry and the flip rule only. Whether
the *game* inherits it depends on the chiral ``P3-y`` tile (OPEN-2), since the
mirror reflects arrow patterns and the deck is closed under reflection except
for that one chiral piece.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fliphex.board import DIRECTION_NAMES, OFF_BOARD, Board  # noqa: E402

#: A cell permutation together with the direction action that induces it.
Automorphism = tuple[str, tuple[int, ...], dict[int, int]]


def _dihedral_direction_actions() -> list[tuple[str, tuple[int, ...]]]:
    """The twelve D6 actions on directions 0..5: 6 rotations + 6 reflections."""
    actions: list[tuple[str, tuple[int, ...]]] = []
    for k in range(6):
        actions.append((f"rot{k * 60}", tuple((d + k) % 6 for d in range(6))))
    for k in range(6):
        actions.append((f"refl{k}", tuple((k - d) % 6 for d in range(6))))
    return actions


def board_automorphisms(board: Board) -> list[Automorphism]:
    """Return every automorphism of the directed board graph.

    Each is ``(action_name, direction_permutation, cell_permutation)``, one per
    distinct cell permutation. The identity is always included.
    """
    n = board.n_cells
    nb = [board.neighbours(c) for c in range(n)]
    found: dict[tuple[int, ...], Automorphism] = {}

    for name, rho in _dihedral_direction_actions():
        # rho fixes the direction action; try every image of an anchor cell and
        # propagate pi across the (connected) board, checking consistency.
        for image in range(n):
            pi: dict[int, int] = {0: image}
            stack = [0]
            ok = True
            while stack and ok:
                u = stack.pop()
                pu = pi[u]
                for d in range(6):
                    v, w = nb[u][d], nb[pu][rho[d]]
                    if (v == OFF_BOARD) != (w == OFF_BOARD):
                        ok = False
                        break
                    if v == OFF_BOARD:
                        continue
                    if v in pi:
                        if pi[v] != w:
                            ok = False
                            break
                    else:
                        pi[v] = w
                        stack.append(v)
            if ok and len(pi) == n and len(set(pi.values())) == n:
                key = tuple(pi[c] for c in range(n))
                found.setdefault(key, (name, rho, pi))

    return list(found.values())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Board automorphism group.")
    parser.add_argument("n_cols", type=int, nargs="?", default=5)
    parser.add_argument("n_rows", type=int, nargs="?", default=5)
    args = parser.parse_args(argv)

    board = Board(args.n_cols, args.n_rows)
    autos = board_automorphisms(board)

    print(f"|Aut| ({board.n_cols}x{board.n_rows} directed graph) = {len(autos)}\n")
    for name, rho, pi in autos:
        moved = [c for c in range(board.n_cells) if pi[c] != c]
        dirs = " ".join(
            f"{DIRECTION_NAMES[d]}->{DIRECTION_NAMES[rho[d]]}" for d in range(6)
        )
        if not moved:
            print(f"[{name}] identity")
        else:
            swaps = ", ".join(
                f"{board.cell_name(c)}->{board.cell_name(pi[c])}" for c in moved
            )
            fixed = [board.cell_name(c) for c in board.cells if pi[c] == c]
            print(f"[{name}] mirror — directions: {dirs}")
            print(f"  fixed: {fixed}")
            print(f"  swaps: {swaps}")
        print()


if __name__ == "__main__":
    main()
