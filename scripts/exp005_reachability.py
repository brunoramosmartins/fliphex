"""EXP-005 — don't-care yield, and the gap between the bound and reachability.

Registered in ``experiments/registry.md`` before this script existed.
`adr-012 <../docs/adr/adr-012-endgame-database-storage.md>`_ decision 7 allows
exactly **one** source of don't-cares in a FLIPHEX database: a configuration with
no legal predecessor. Nothing else is free, because nothing else is recoverable
once the table is filled. This measures how many there are.

The decision rule, pre-registered
---------------------------------
If the yield is under **20%**, don't-cares are dropped from the adr-012 design
entirely. The rule is applied mechanically below; it is not restated in prose and
then eyeballed.

**The count is recorded before any filling.** Filling destroys the distinction
between "unreachable" and "computed" and it cannot be recovered afterwards, which
is why this is a separate experiment and not a flag on the sweep.

What is measured, precisely
---------------------------
Configurations with **no legal predecessor** — one step back. That is the
registered quantity and it is *weaker* than "unreachable from the opening": a
configuration whose only predecessors are themselves unreachable is also
unvisitable, but proving that needs the transitive closure. The number reported
here is therefore a **lower bound** on the true don't-care set, which is the safe
direction for a rule that fires on being *large*.

Relation to adr-010 V1
----------------------
V1 is exact per-layer equality against the closed form — a genuine ``perft``, and
EXP-001 passed it. It gates the *bound*. This measures the *reachable set*, which
is a different quantity: at ``t = 1`` the bound counts both colourings of the
single placed cell while only the mover's colour can occur, so exactly half of
layer 1 has no predecessor. That 2× is checked here as a calibration anchor
rather than assumed — if it ever comes out otherwise, the index has drifted and
no other number on the page is worth reading.

    python scripts/exp005_reachability.py --board 3 3
    ~/pypy3.11-v7.3.23-linux64/bin/pypy scripts/exp005_reachability.py

Cost: this walks every configuration and every legal move, so on the 5×3 it is
the same order of work as the sweep itself — hours, not minutes, and PyPy is not
optional. Layers are independent, so the artefact is written after each one and a
run that is stopped early still reports every layer it finished.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from layer_profile import layer as closed_form_layer  # noqa: E402

from fliphex.variant import Arm, Variant  # noqa: E402
from solver.reachable import Reachability  # noqa: E402

#: The configuration EXP-005 is registered against. Anything else is a smoke
#: test and may not produce a verdict — see :func:`verdict`.
REGISTERED = (5, 3)

#: adr-012 decision 7, as registered. Below this, don't-cares are dropped.
THRESHOLD = 0.20


def verdict(variant: Variant, fraction: float, complete: bool) -> tuple[str, str]:
    """Map the measured yield onto the pre-committed branches. No new rules here."""
    if (variant.n_cols, variant.n_rows) != REGISTERED:
        return (
            "descriptive-only",
            f"{variant.name} is not the registered configuration "
            f"({REGISTERED[0]}x{REGISTERED[1]}); this is a smoke test and the "
            f"pre-registered rule is not applied to it",
        )
    if not complete:
        return (
            "descriptive-only",
            "the run did not finish every layer; the rule runs on the complete "
            "design only",
        )
    if fraction < THRESHOLD:
        return (
            "drop don't-cares",
            f"yield {fraction:.1%} is below the pre-registered {THRESHOLD:.0%}, "
            f"so don't-cares leave the adr-012 design entirely",
        )
    return (
        "keep don't-cares",
        f"yield {fraction:.1%} is at or above the pre-registered "
        f"{THRESHOLD:.0%}; adr-012 keeps the don't-care path and EXP-004 "
        f"measures what it is worth after compression",
    )


def check_v1(variant: Variant, layers) -> list[str]:
    """The layer totals must still be the closed form. Free, so always checked."""
    first, second = (len(hand) for hand in variant.deck_names())
    problems = []
    for layer in layers:
        expected = closed_form_layer(variant.n_cells, first, second, layer.t)
        if layer.total != expected:
            problems.append(f"layer {layer.t}: {layer.total:,} vs formula {expected:,}")
    return problems


def check_calibration(layers) -> list[str]:
    """Layer 1 must be exactly half reachable. The anchor, not a nicety."""
    for layer in layers:
        if layer.t != 1:
            continue
        if layer.total != 2 * layer.with_predecessor:
            return [
                f"layer 1 is {layer.with_predecessor:,} of {layer.total:,}, "
                f"not exactly half — the index has drifted"
            ]
    return []


def run(variant: Variant, out: Path | None) -> dict:
    hands = "+".join(str(len(hand)) for hand in variant.deck_names())
    reach = Reachability(variant)
    total = sum(reach.layer_size(t) for t in range(variant.n_cells + 1))

    print(
        f"\n  === EXP-005 — {variant.name}, {variant.n_cells} cells, hands {hands} ==="
    )
    print(f"  {total:,} configurations, one-step-back predecessors")
    print(
        f"  interpreter: {sys.implementation.name} {sys.version.split()[0]}",
        flush=True,
    )
    print()
    print("    layer            total    with pred.          orphans   frac      time")

    started = time.perf_counter()
    layers = []
    artefact: dict = {}

    for t in range(variant.n_cells + 1):
        at = time.perf_counter()
        layer = reach.layer(t)
        layers.append(layer)
        print(
            f"    {layer.t:5d} {layer.total:>16,} {layer.with_predecessor:>13,} "
            f"{layer.orphans:>16,} {layer.orphan_fraction:>6.1%} "
            f"{time.perf_counter() - at:>8.1f}s",
            flush=True,
        )
        artefact = _artefact(variant, layers, total, started, complete=False)
        if out:
            _write(out, variant, artefact)

    artefact = _artefact(variant, layers, total, started, complete=True)

    orphans = artefact["orphans"]
    fraction = artefact["orphan_fraction"]
    print()
    print(f"    orphans ............... {orphans:,} of {total:,} ({fraction:.2%})")
    v1_state = "ok" if not artefact["v1_problems"] else "FAILED"
    print(f"    V1 layer totals ....... {v1_state}")
    for problem in artefact["v1_problems"]:
        print(f"       {problem}")
    print(
        f"    calibration (t=1 half)  "
        f"{'ok' if not artefact['calibration_problems'] else 'FAILED'}"
    )
    for problem in artefact["calibration_problems"]:
        print(f"       {problem}")
    print(f"    elapsed ............... {artefact['seconds']:,.1f}s")
    print()
    print(f"    VERDICT ............... {artefact['verdict']}")
    print(f"      {artefact['verdict_reason']}")

    if out:
        path = _write(out, variant, artefact)
        print(f"\n    artefact -> {path}")
    return artefact


def _artefact(variant, layers, total, started, complete: bool) -> dict:
    orphans = sum(layer.orphans for layer in layers)
    seen = sum(layer.total for layer in layers)
    fraction = orphans / seen if seen else 0.0
    v1 = check_v1(variant, layers)
    calibration = check_calibration(layers)
    branch, reason = verdict(variant, fraction, complete and not v1 and not calibration)
    return {
        "experiment": "EXP-005",
        "variant": variant.name,
        "board": [variant.n_cols, variant.n_rows],
        "cells": variant.n_cells,
        "hands": [list(hand) for hand in variant.deck_names()],
        "measured": "configurations with no legal predecessor, one step back",
        "complete": complete,
        "configurations_total": total,
        "configurations_measured": seen,
        "orphans": orphans,
        "orphan_fraction": round(fraction, 6),
        "threshold": THRESHOLD,
        "layers": [layer.as_dict() for layer in layers],
        "v1_problems": v1,
        "calibration_problems": calibration,
        "verdict": branch,
        "verdict_reason": reason,
        "interpreter": f"{sys.implementation.name} {sys.version.split()[0]}",
        "seconds": time.perf_counter() - started,
    }


def _write(out: Path, variant: Variant, artefact: dict) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"exp005-{variant.name}.json"
    path.write_text(json.dumps(artefact, indent=2))
    return path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--board",
        nargs=2,
        type=int,
        default=list(REGISTERED),
        metavar=("COLS", "ROWS"),
    )
    p.add_argument("--arm", choices=["h1", "h2"], default="h1")
    p.add_argument("--out", type=Path, default=Path("results"))
    p.add_argument("--no-write", action="store_true", help="print only")
    args = p.parse_args()

    variant = Variant(args.board[0], args.board[1], Arm(args.arm))
    artefact = run(variant, None if args.no_write else args.out)
    clean = not artefact["v1_problems"] and not artefact["calibration_problems"]
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
