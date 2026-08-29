"""EXP-002 — replay a finished arm's V4/V6 sampling to recover its coverage.

**Register this before running it.** See the amendment of 2026-08-27 under
EXP-002 in ``experiments/registry.md``.

Why this exists
---------------
The 2026-08-09 amendment found that V4 and V6 report a verdict without a
coverage figure, and filed the fix for "the instrument's next revision, after h2
completes". h2 has completed — but so has the h2 *arm*, under the old
instrument, and re-sweeping it to recover a number the sweep never needed would
cost 34 hours to compute nothing new about the game.

It does not have to. The sampling is a pure function of the seed and the layer
sizes, and h2's layers are still on disk, so the arm's V4/V6 draws can be
replayed exactly as they happened.

How it stays honest
-------------------
This script does **not** reimplement the sampling. It constructs the real
:class:`~exp002_solve_5x3.Checks` observer and calls it with the stored layers,
in sweep order, exactly as ``PackedSweep`` would have. Same object, same RNG,
same draw sequence — so agreement with the archived artefact is a check on the
replay, and once it agrees, the coverage breakdown it adds is the arm's own.

An earlier draft of this file did reimplement the draws, and reproduced h2's
518 checked / 4,768 ineligible on the first try. That was reassuring and it was
the wrong design: two implementations of one sampling rule drift, and the one
that drifts silently is the audit.

What it recovers, and what it cannot
------------------------------------
Recovered exactly, because they need no search: the per-layer V4 sample
distribution, how many draws were terminal, the full V6 per-layer breakdown
including eligibility and mirror-fixed pairs, and the V5 digest.

**Not** recovered by default: which individual V4 samples were affordable. That
is the forward search, ~20 h on the 5×3, and it is the one number the archived
artefact already reports in aggregate. Pass ``--v4-budget`` to run it anyway.

    pypy scripts/exp002_coverage_replay.py --arm h2
    pypy scripts/exp002_coverage_replay.py --arm h2 --v4-budget 2000000
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from exp002_solve_5x3 import Checks, run_v4, v6_coverage  # noqa: E402

from fliphex.variant import Arm, Variant  # noqa: E402
from solver.checkpoint import Checkpoint, atomic_write  # noqa: E402
from solver.sweep_reader import SweepReader  # noqa: E402


def replay(variant: Variant, args) -> dict:
    reader = SweepReader(variant, Checkpoint(args.checkpoint / variant.name))
    checks = Checks(variant, args.v4_per_layer, args.v6_per_layer, args.seed)

    print(f"\n  === EXP-002 coverage replay — {variant.name} ===")
    print(f"  database: {args.checkpoint / variant.name}")
    print(f"  interpreter: {sys.implementation.name} {sys.version.split()[0]}")
    print(f"  seed {args.seed}, {args.v4_per_layer} V4 and {args.v6_per_layer} V6")
    print("  driving the real Checks observer over the stored layers\n", flush=True)

    started = time.perf_counter()
    # Sweep order — terminal layer first, then downwards. The RNG stream and the
    # V5 digest both depend on this order, so getting it wrong would show up as
    # a checksum mismatch rather than as a wrong coverage number.
    for t in range(variant.n_cells, -1, -1):
        checks(t, reader.layer(t), reader.sweep)
        # Nothing is ever revisited, and layer 9 alone is 1.17 GB.
        reader.release()

    v4 = run_v4(variant, checks, args.v4_budget) if args.v4_budget else None
    v6 = v6_coverage(checks, variant)
    elapsed = time.perf_counter() - started
    checksum = checks.digest.hexdigest()

    print()
    print(f"    V5 checksum ........... {checksum}")
    print(f"    V1 per-layer counts ... {'ok' if not checks.v1_problems else 'FAILED'}")
    print(f"    V4 samples drawn ...... {len(checks.v4_samples):,}")
    terminal = sum(
        1
        for t, _i, _s in checks.v4_samples
        if t == variant.n_cells  # the only layer where the board is full
    )
    print(f"       terminal draws ..... {terminal:,} (silently dropped before today)")
    print(f"    V6 pairs checked ...... {v6['pairs_checked']:,}")
    print(f"       eligibility ........ {100 * v6['eligible_fraction']:.1f}%")
    print(f"       mirror-fixed ....... {v6['self_mirror']:,} (vacuous comparisons)")
    print(f"       non-trivial ........ {v6['non_trivial']:,}")
    print(f"       differ ............. {len(checks.v6_problems)}")
    if v6["layers_without_coverage"]:
        print(
            "       no coverage at ..... t = "
            + ", ".join(str(t) for t in v6["layers_without_coverage"])
        )
    if v4 is not None:
        cov = v4["coverage"]
        print(
            f"    V4 re-derivation ...... {v4['agreed']:,} agree, "
            f"{v4['disagreed']} disagree, {v4['unaffordable']} over budget"
        )
        print(f"       coverage ........... {100 * cov['verified_fraction']:.1f}%")
    print(f"\n    elapsed ............... {elapsed:,.1f}s\n", flush=True)

    return {
        "experiment": "EXP-002",
        "check": "V4/V6 coverage replay",
        "variant": variant.name,
        "seed": args.seed,
        "interpreter": f"{sys.implementation.name} {sys.version.split()[0]}",
        "v5_checksum_sha256": checksum,
        "v1_problems": checks.v1_problems,
        "v4_samples_drawn": len(checks.v4_samples),
        "v4_terminal_draws": terminal,
        "v4_per_layer_draws": _draws_per_layer(checks),
        "V4_sampled_rederivation": v4,
        "V6_coverage": v6,
        "v6_problems": checks.v6_problems[:20],
        "seconds": elapsed,
    }


def _draws_per_layer(checks: Checks) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t, _index, _slot in checks.v4_samples:
        counts[str(t)] = counts.get(str(t), 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: int(kv[0])))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--board", type=int, nargs=2, default=[5, 3], metavar=("COLS", "ROWS")
    )
    p.add_argument("--arm", choices=["h1", "h2"], default="h2")
    p.add_argument("--checkpoint", type=Path, default=Path("data/checkpoints"))
    p.add_argument("--seed", type=int, default=3, help="must match the arm's run")
    p.add_argument("--v4-per-layer", type=int, default=40)
    p.add_argument("--v6-per-layer", type=int, default=40)
    p.add_argument(
        "--v4-budget",
        type=int,
        default=0,
        help=(
            "node budget for re-running V4's forward searches. 0 (the default) "
            "skips them and recovers only what needs no search — the searches "
            "are ~20 h on the 5x3 and the archived artefact already reports "
            "their aggregate."
        ),
    )
    p.add_argument("--out", type=Path, default=Path("results"))
    p.add_argument("--no-write", action="store_true")
    args = p.parse_args()

    variant = Variant(args.board[0], args.board[1], Arm(args.arm))
    artefact = replay(variant, args)

    if not args.no_write:
        path = args.out / f"exp002-coverage-{variant.name}.json"
        atomic_write(path, json.dumps(artefact, indent=2).encode())
        print(f"    artefact -> {path}\n")
    return 0 if not artefact["v1_problems"] and not artefact["v6_problems"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
