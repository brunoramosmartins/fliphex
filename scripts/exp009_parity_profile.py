"""EXP-009 — the WIN/LOSS mix per layer, which four instruments have circled.

**Register this before running it.** See EXP-009 in ``experiments/registry.md``.

Four measurements in Phase 3 split cleanly on the parity of ``t``, and each time
the split was explained by guessing at the value mix rather than measuring it:

* **Sweep runtime.** 785k cfg/s at ``t = 10`` against 84.9k at ``t = 9``; the
  gap widens to 166× by ``t = 3``. The child scan
  (``solver/packed_sweep.py:385``) exits at the first losing child, so a WIN is
  cheap and a LOSS pays the full enumeration.
* **Criticality.** 35.37% at ``t = 9`` against 11.00% at ``t = 10``.
* **Compressibility.** Block-RLE gets 120× on even layers and 1.2–3.2× on odd
  ones — homogeneous against mixed.
* **A notebook cell**, which showed layers 0 and 2 are **100% WIN** and layers 1
  and 3 **100% LOSS** — not "mostly", every configuration.

Those last two do not fit together, which is the point of this experiment. A
uniformly-LOSS layer is as homogeneous as a uniformly-WIN one and would compress
just as well. Odd layers near the opening are uniform and odd layers deeper in
are not, and nobody has measured where the change happens.

This counts. It does not explain — the mechanism is a separate question and this
instrument deliberately does not speculate about it.

    pypy scripts/exp009_parity_profile.py --arm h1
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fliphex.variant import Arm, Variant  # noqa: E402
from solver.checkpoint import Checkpoint, atomic_write  # noqa: E402
from solver.retrograde import LayerIndex  # noqa: E402
from solver.sweep_reader import SweepReader  # noqa: E402

CHUNK = 1 << 22  # bytes


def count_wins(values: bytearray, size: int) -> tuple[int, int]:
    """Return ``(wins, losses)`` over the layer's ``size`` entries.

    ``SLOT_WIN`` is ``0b01`` and ``SLOT_LOSS`` is ``0b10``, so with
    ``lo = v & 0x55…`` and ``hi = (v >> 1) & 0x55…`` a field is a WIN exactly
    where ``lo`` is set and ``hi`` is not. ``SLOT_UNSET`` would be neither and is
    asserted against: in a complete layer every field is one or the other, so
    ``lo ^ hi`` must be set in all of them.
    """
    n_bytes = size >> 2
    tail = size & 3
    wins = valid = 0

    for offset in range(0, n_bytes, CHUNK):
        span = min(CHUNK, n_bytes - offset)
        chunk = int.from_bytes(values[offset : offset + span], "big")
        mask = int.from_bytes(b"\x55" * span, "big")
        lo = chunk & mask
        hi = (chunk >> 1) & mask
        if (lo ^ hi).bit_count() != span * 4:
            raise SystemExit(
                f"a slot is neither WIN nor LOSS near byte {offset} — the layer "
                f"is incomplete or corrupt"
            )
        wins += (lo & ~hi & mask).bit_count()
        valid += span * 4

    for i in range(n_bytes << 2, (n_bytes << 2) + tail):
        slot = (values[i >> 2] >> ((i & 3) << 1)) & 3
        wins += slot == 1
        valid += 1

    return wins, valid - wins


def run(args) -> dict:
    variant = Variant(args.board[0], args.board[1], Arm(args.arm))
    reader = SweepReader(variant, Checkpoint(args.checkpoint / variant.name))

    print(f"\n  === EXP-009 — WIN/LOSS mix per layer, {variant.name} ===")
    print(
        f"  interpreter: {sys.implementation.name} {sys.version.split()[0]}\n",
        flush=True,
    )
    print(f"  {'t':>3} {'size':>15} {'WIN':>15} {'WIN %':>8}  mover")

    started = time.perf_counter()
    rows = []
    for t in range(variant.n_cells + 1):
        size = LayerIndex(variant, t).size
        wins, losses = count_wins(reader.layer(t), size)
        mover = "P1" if t % 2 == 0 else "P2"
        rows.append(
            {
                "layer": t,
                "size": size,
                "wins": wins,
                "losses": losses,
                "win_fraction": wins / size,
                "mover": mover,
                # 0 or 1 means every configuration in the layer shares a value.
                "uniform": wins == 0 or wins == size,
            }
        )
        print(
            f"  {t:>3} {size:>15,} {wins:>15,} {100 * wins / size:7.2f}%  {mover}",
            flush=True,
        )
        reader.release()

    elapsed = time.perf_counter() - started
    uniform = [r["layer"] for r in rows if r["uniform"]]
    print()
    print(f"    uniform layers ........ {uniform}")
    print(f"    elapsed ............... {elapsed:,.1f}s\n", flush=True)

    return {
        "experiment": "EXP-009",
        "variant": variant.name,
        "interpreter": f"{sys.implementation.name} {sys.version.split()[0]}",
        "layers": rows,
        "uniform_layers": uniform,
        "seconds": elapsed,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--board", type=int, nargs=2, default=[5, 3], metavar=("COLS", "ROWS")
    )
    p.add_argument("--arm", choices=["h1", "h2"], default="h1")
    p.add_argument("--checkpoint", type=Path, default=Path("data/checkpoints"))
    p.add_argument("--out", type=Path, default=Path("results"))
    p.add_argument("--no-write", action="store_true")
    args = p.parse_args()

    artefact = run(args)

    if not args.no_write:
        path = (
            args.out / f"exp009-parity-{args.board[0]}x{args.board[1]}-{args.arm}.json"
        )
        atomic_write(path, json.dumps(artefact, indent=2).encode())
        print(f"    artefact -> {path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
