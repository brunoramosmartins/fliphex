"""EXP-002's recurrence check — verify the sweep's layers against each other.

**Register this before running it.** See the amendment of 2026-08-26 under
EXP-002 in ``experiments/registry.md``.

What it checks
--------------
For every reachable position at layer ``t``, the value the sweep stored must
follow from the values it stored at layer ``t + 1``:

    value(s) == WIN   iff   some child of s is stored LOSS

That is the minimax recurrence itself, read back off the artefact. No search is
involved — only move generation and table lookups — so the cost is linear in
(positions × branching) rather than exponential in remaining depth.

Why this and not more of the PV audit's part 2
----------------------------------------------
Part 2 re-derives each opening by *forward search*, which is a full subgame
proof per opening. Measured on the h2 arm: 30 of 540 openings took 9.7 h of CPU
and the marginal cost was rising steeply — 10 openings in 20 minutes, then the
next 10 in 8.3 hours. Extrapolating the observed slope put the remainder past
**400 hours**, and the run was stopped at opening 34 on 2026-08-26.

This instrument targets the same claim from the other side. Part 2 asks "is the
sweep right about each opening?"; the recurrence check asks "is the sweep
self-consistent across the layer boundary?", exhaustively rather than one
opening at a time. Layers 0-3 hold 737,204 configurations in total, so the whole
opening can be covered rather than sampled.

What it does **not** cover, stated plainly
------------------------------------------
The check shares ``fliphex.legal_moves``/``apply_move`` with the sweep — but so
does the PV audit's forward searcher, so neither instrument verifies the rules.
What it *additionally* shares, and the PV audit does not, is ``LayerIndex``: a
bug in the ranking function could in principle appear identically on both sides
of the comparison.

Two things bound that. The check reaches positions by walking **forward** with
``apply_move`` and then encoding them, where the sweep built layers by decoding
rank indices — so the two exercise the bijection in opposite directions, and
``--verify-roundtrip`` asserts ``decode(encode(s)) == s`` on every position
visited. And the PV audit's part 1, which shares no ranking code at all, already
passes 15 of 15 on this arm. The instruments are complementary; neither is
sufficient alone, and this file does not claim otherwise.

    ~/pypy3.11-v7.3.23-linux64/bin/pypy scripts/exp002_recurrence_check.py \\
        --board 5 3 --arm h2 --max-layer 3
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fliphex.moves import apply_move, legal_moves  # noqa: E402
from fliphex.variant import Arm, Variant  # noqa: E402
from solver.checkpoint import Checkpoint, atomic_write  # noqa: E402
from solver.minimax import LOSS, WIN  # noqa: E402
from solver.sweep_reader import SweepReader  # noqa: E402


def check_layer(board, reader: SweepReader, frontier: list, t: int, roundtrip: bool):
    """Check every position in ``frontier`` against layer ``t + 1``.

    Returns ``(problems, next_frontier, children_examined)``. The next frontier
    is keyed by **layer index**, never by ``GameState``: ``history`` is part of
    the dataclass's ``__eq__``, so a set of states deduplicates *paths* rather
    than positions and grows without bound. An earlier throwaway probe made
    exactly that mistake and reached 12.5 GiB before it was killed.
    """
    problems: list[dict] = []
    nxt: dict[int, object] = {}
    children = 0
    index_below = reader.index[t + 1]

    for state in frontier:
        stored = reader.value(state)
        found_losing_child = False
        for move in legal_moves(board, state):
            child = apply_move(board, state, move)
            children += 1
            key = index_below.encode(child)
            if key not in nxt:
                nxt[key] = child
                if roundtrip and index_below.decode(key).key() != child.key():
                    problems.append(
                        {
                            "kind": "roundtrip",
                            "layer": t + 1,
                            "index": key,
                            "detail": "decode(encode(s)) != s",
                        }
                    )
            if reader.value(child) == LOSS:
                found_losing_child = True

        expected = WIN if found_losing_child else LOSS
        if stored != expected:
            problems.append(
                {
                    "kind": "recurrence",
                    "layer": t,
                    "index": reader.index[t].encode(state),
                    "stored": stored,
                    "from_children": expected,
                }
            )

    return problems, list(nxt.values()), children


def run(variant: Variant, args) -> dict:
    board = variant.board()
    reader = SweepReader(variant, Checkpoint(args.checkpoint / variant.name))
    root = variant.initial_state()

    print(f"\n  === EXP-002 recurrence check — {variant.name} ===")
    print(f"  database: {args.checkpoint / variant.name}")
    print(f"  interpreter: {sys.implementation.name} {sys.version.split()[0]}")
    print(f"  layers 0..{args.max_layer}, exhaustive over the reachable set")
    print(
        f"  index round-trip: {'on' if args.verify_roundtrip else 'off'}\n", flush=True
    )

    started = time.perf_counter()
    frontier = [root]
    layers: list[dict] = []
    all_problems: list[dict] = []

    for t in range(args.max_layer + 1):
        if not frontier:
            break
        t0 = time.perf_counter()
        problems, nxt, children = check_layer(
            board, reader, frontier, t, args.verify_roundtrip
        )
        dt = time.perf_counter() - t0
        all_problems.extend(problems)

        closed_form = reader.index[t].size
        layers.append(
            {
                "layer": t,
                "reachable_checked": len(frontier),
                "closed_form_size": closed_form,
                "children_examined": children,
                "problems": len(problems),
                "seconds": dt,
            }
        )
        print(
            f"    layer {t:2d}  {len(frontier):>10,} reachable of "
            f"{closed_form:>12,} ({100 * len(frontier) / closed_form:5.1f}%)  "
            f"{children:>12,} child lookups  "
            f"{len(problems)} problems  {dt:8.1f}s",
            flush=True,
        )
        # Layer t is finished with; only t+1 and t+2 are wanted next.
        reader.release()
        frontier = nxt

    elapsed = time.perf_counter() - started
    artefact = {
        "experiment": "EXP-002",
        "check": "layer-to-layer recurrence",
        "variant": variant.name,
        "max_layer": args.max_layer,
        "verify_roundtrip": args.verify_roundtrip,
        "interpreter": f"{sys.implementation.name} {sys.version.split()[0]}",
        "layers": layers,
        "positions_checked": sum(row["reachable_checked"] for row in layers),
        "children_examined": sum(row["children_examined"] for row in layers),
        "problems": all_problems[:100],
        "problem_count": len(all_problems),
        "passed": not all_problems,
        "seconds": elapsed,
    }

    print()
    print(f"    positions checked ..... {artefact['positions_checked']:,}")
    print(f"    child lookups ......... {artefact['children_examined']:,}")
    print(f"    problems .............. {artefact['problem_count']}")
    print(f"    elapsed ............... {elapsed:,.1f}s")
    print()
    if artefact["passed"]:
        print(
            f"    {variant.name}: layers 0..{args.max_layer} are internally "
            f"consistent — every stored value follows from the layer below."
        )
    else:
        print(f"    {variant.name}: FAILED — {len(all_problems)} problems")
        for problem in all_problems[:5]:
            print(f"      {problem}")
    print(flush=True)
    return artefact


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--board", type=int, nargs=2, default=[5, 3], metavar=("COLS", "ROWS")
    )
    p.add_argument("--arm", choices=["h1", "h2"], default="h2")
    p.add_argument("--checkpoint", type=Path, default=Path("data/checkpoints"))
    p.add_argument(
        "--max-layer",
        type=int,
        default=3,
        help=(
            "deepest layer to check exhaustively. Layer sizes grow ~18x per "
            "level on the 5x3, so raise this one step at a time and read the "
            "measured cost before going further."
        ),
    )
    p.add_argument(
        "--verify-roundtrip",
        action="store_true",
        default=True,
        help="assert decode(encode(s)) == s on every position visited",
    )
    p.add_argument(
        "--no-verify-roundtrip", dest="verify_roundtrip", action="store_false"
    )
    p.add_argument("--out", type=Path, default=Path("results"))
    p.add_argument("--no-write", action="store_true")
    args = p.parse_args()

    variant = Variant(args.board[0], args.board[1], Arm(args.arm))
    artefact = run(variant, args)

    if not args.no_write:
        path = args.out / f"exp002-recurrence-{variant.name}.json"
        atomic_write(path, json.dumps(artefact, indent=2).encode())
        print(f"    artefact -> {path}\n")
    return 0 if artefact["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
