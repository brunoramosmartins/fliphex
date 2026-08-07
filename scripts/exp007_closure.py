"""EXP-007 — the true reachable closure, and what one-step-back misses.

Registered in ``experiments/registry.md`` before this script existed, as a **new
ID rather than an amendment to EXP-005**. The two experiments measure different
quantities and their yields can fall on opposite sides of the same 20% threshold,
so redefining EXP-005's measured quantity mid-flight would be the anti-pattern
`adr-010 <../docs/adr/adr-010-solver-correctness.md>`_ was already amended once to
avoid.

The difference, in one sentence
-------------------------------
EXP-005 counts configurations with no legal **predecessor**; this counts
configurations no **game** reaches. A configuration whose every predecessor is
itself unreachable passes the one-step test and is still unvisitable, so the
closure is strictly the smaller reachable set — and it is the one adr-012
decision 7 needs.

Why EXP-005's number could not carry the decision
--------------------------------------------------
Its yield turned out to be a counting identity: ``orphans(t) = layer_size(t) /
2**t`` exactly, because a configuration has no predecessor precisely when every
occupied cell carries the colour of the player who did *not* just move. It does
not depend on the arrow patterns at all, which is why both 3×3 arms returned
identical counts from different decks. The closure does depend on them, and the
3×3 arms disagree — 3.9131% against 3.8866%.

The decision rule, pre-registered
---------------------------------
If the unreachable fraction is under **20%**, don't-cares are dropped from the
adr-012 design entirely. Applied mechanically below, on the registered 5×3 only,
and only on a complete run.

    python scripts/exp007_closure.py --board 3 3
    ~/pypy3.11-v7.3.23-linux64/bin/pypy scripts/exp007_closure.py --arm h1

Cost: one full forward pass per layer, so the 5×3 is the same order of work as
the sweep — hours, and PyPy is not optional. Peak memory is two adjacent layer
bitsets, 1.08 GB. Unlike EXP-005 the layers are **not** independent: layer ``t``
is expanded from layer ``t-1``'s marks, so an interrupted run reports a prefix,
which is still meaningful and is written after each layer.
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

#: The configuration EXP-007 is registered against.
REGISTERED = (5, 3)

#: adr-012 decision 7, as registered. Below this, don't-cares are dropped.
THRESHOLD = 0.20


def verdict(variant: Variant, fraction: float, complete: bool) -> tuple[str, str]:
    """Map the measured fraction onto the pre-committed branches."""
    if (variant.n_cols, variant.n_rows) != REGISTERED:
        return (
            "descriptive-only",
            f"{variant.name} is not the registered configuration "
            f"({REGISTERED[0]}x{REGISTERED[1]}); the pre-registered rule is not "
            f"applied to it",
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
            f"unreachable {fraction:.2%} is below the pre-registered "
            f"{THRESHOLD:.0%}, so don't-cares leave the adr-012 design entirely",
        )
    return (
        "keep don't-cares",
        f"unreachable {fraction:.2%} is at or above the pre-registered "
        f"{THRESHOLD:.0%}; adr-012 keeps the don't-care path and EXP-004 "
        f"measures what it is worth after compression",
    )


def check_v1(variant: Variant, layers) -> list[str]:
    """Layer totals must still be the closed form. Free, so always checked."""
    first, second = (len(hand) for hand in variant.deck_names())
    problems = []
    for layer in layers:
        expected = closed_form_layer(variant.n_cells, first, second, layer.t)
        if layer.total != expected:
            problems.append(f"layer {layer.t}: {layer.total:,} vs formula {expected:,}")
    return problems


def check_falsifier(layers) -> list[str]:
    """The closure must **not** obey ``unreachable(t) = layer(t) / 2**t``.

    That identity is EXP-005's quantity. If the closure reproduced it, this
    instrument would be measuring one-step-back again under a different name, and
    the whole reason EXP-007 exists as a separate ID would be gone.
    """
    interior = [layer for layer in layers if layer.t >= 1]
    if interior and all(
        layer.unreachable * 2**layer.t == layer.total for layer in interior
    ):
        return ["the closure reproduced the one-step identity exactly"]
    return []


def run(variant: Variant, out: Path | None) -> dict:
    hands = "+".join(str(len(hand)) for hand in variant.deck_names())
    reach = Reachability(variant)
    total = sum(reach.layer_size(t) for t in range(variant.n_cells + 1))

    print(
        f"\n  === EXP-007 — {variant.name}, {variant.n_cells} cells, hands {hands} ==="
    )
    print(f"  {total:,} configurations, transitive closure from the opening")
    print(
        f"  interpreter: {sys.implementation.name} {sys.version.split()[0]}",
        flush=True,
    )
    print()
    print("    layer            total     reachable      unreachable   frac      time")

    started = time.perf_counter()
    layers: list = []
    state = {"at": time.perf_counter()}

    def report(layer) -> None:
        now = time.perf_counter()
        layers.append(layer)
        print(
            f"    {layer.t:5d} {layer.total:>16,} {layer.reachable:>13,} "
            f"{layer.unreachable:>16,} {layer.unreachable_fraction:>6.1%} "
            f"{now - state['at']:>8.1f}s",
            flush=True,
        )
        state["at"] = now
        if out:
            _write(out, variant, _artefact(variant, layers, total, started, False))

    reach.closure(observer=report)
    artefact = _artefact(variant, layers, total, started, complete=True)

    print()
    print(
        f"    unreachable ........... {artefact['unreachable']:,} of {total:,} "
        f"({artefact['unreachable_fraction']:.4%})"
    )
    v1_state = "ok" if not artefact["v1_problems"] else "FAILED"
    print(f"    V1 layer totals ....... {v1_state}")
    for problem in artefact["v1_problems"]:
        print(f"       {problem}")
    falsifier = "ok (differs from one-step)" if not artefact["falsifier"] else "FAILED"
    print(f"    falsifier ............. {falsifier}")
    for problem in artefact["falsifier"]:
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
    unreachable = sum(layer.unreachable for layer in layers)
    seen = sum(layer.total for layer in layers)
    fraction = unreachable / seen if seen else 0.0
    v1 = check_v1(variant, layers)
    falsifier = check_falsifier(layers) if complete else []
    branch, reason = verdict(variant, fraction, complete and not v1 and not falsifier)
    return {
        "experiment": "EXP-007",
        "variant": variant.name,
        "board": [variant.n_cols, variant.n_rows],
        "cells": variant.n_cells,
        "hands": [list(hand) for hand in variant.deck_names()],
        "measured": "transitive reachable closure from the opening position",
        "complete": complete,
        "configurations_total": total,
        "configurations_measured": seen,
        "unreachable": unreachable,
        "unreachable_fraction": round(fraction, 8),
        "threshold": THRESHOLD,
        "layers": [layer.as_dict() for layer in layers],
        "v1_problems": v1,
        "falsifier": falsifier,
        "verdict": branch,
        "verdict_reason": reason,
        "interpreter": f"{sys.implementation.name} {sys.version.split()[0]}",
        "seconds": time.perf_counter() - started,
    }


def _write(out: Path, variant: Variant, artefact: dict) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"exp007-{variant.name}.json"
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
    clean = not artefact["v1_problems"] and not artefact["falsifier"]
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
