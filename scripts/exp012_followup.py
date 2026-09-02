"""EXP-012 follow-up: the convergence read, and the one bounded extension.

Two obligations the main run left open, in the order they have to happen.

**Leg 1 -- convergence.** ``experiments/registry.md`` pins the convergence
criterion to the training-loss trajectory and requires *one seed per arm re-run
at 80 epochs, paired on the same 500 positions and the same seed* (McNemar on
per-position hits). The instrument never implemented it. This reports it; it
does **not** gate anything. An earlier draft of the entry triggered on "the
held-out primary moves by more than 2 points" *unpaired*, which is inside noise
in both directions, and the registered replacement deliberately has no
threshold: convergence is reported, not asserted.

**Leg 2 -- the bounded extension.** The adoption read came back ``D - B = +3.76
[+1.78, +5.74]``, spanning the 5-point margin. The rule permits **exactly one**
extension to 12 seeds, re-read **once**, at Bonferroni alpha = 0.025. Seeds 5-11
are trained for arms **B and D only**: adoption is read on ``D - B``, and the
mechanism contrasts are already void because the ``C - A`` equivalence
precondition failed. Extending arms whose contrasts cannot be read would be
spending compute to make a void number look precise.

Why leg 1 runs first: leg 2 spends three hours sharpening the precision of
``D - B``. If the arms are still descending at 40 epochs -- and the trajectory
says every one of them is -- that estimate may sit in the wrong place, and
measuring an optimisation-budget-limited estimator more precisely is the wrong
order of operations.

**The reproduction guard.** Leg 2 merges new seeds with the five rows already in
the artefact, which is only legitimate if the pipeline still produces those rows.
One cell (``B_cell`` seed 0, the conditioned path with the nested normaliser --
the most fragile piece and present in both legs) is retrained at 40 epochs and
its per-position hit vector compared **element-wise** against the artefact. Not
"the mean is close": the mean can match while the positions differ. A receipt is
written recording the commit and the reproduced digest, so the second leg does
not pay for the guard twice unless the tree moved.

**Why this imports the instrument instead of duplicating it.** The instrument's
docstring states the house convention -- a finished experiment's script is the
record of what was run, so statistics are duplicated rather than shared. This
file departs from that deliberately and in one direction only: it *reads* the
instrument and modifies nothing in it. Leg 2 merges seeds 5-11 with rows 0-4 that
already exist, and that merge is only sound if the new rows come from literally
the same code, not from a copy that has drifted. Duplication here would be the
riskier choice, and the reproduction guard is what checks the claim.

Usage::

    .venv/bin/python scripts/exp012_followup.py --leg convergence
    .venv/bin/python scripts/exp012_followup.py --leg extension
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fliphex.variant import Arm, Variant  # noqa: E402
from scripts.exp012_conditioned_head import (  # noqa: E402
    ARM_SEEDS,
    EPOCHS,
    HELDOUT_SIZE,
    LAYERS,
    MARGIN,
    PER_LAYER,
    SEED,
    TRAIN_SIZE,
    build_sample,
    draw_layer,
    mcnemar,
    search_scores,
    supervised_scores,
    train_arm,
    verify_ground_truth,
)
from solver.checkpoint import Checkpoint  # noqa: E402
from solver.sweep_reader import SweepReader  # noqa: E402

#: Leg 1: the registered re-run is one seed per arm. Seed 0 is the first
#: registered seed; the registry does not name one, so it is named here.
CONVERGENCE_SEED = 0
CONVERGENCE_EPOCHS = 80

#: Leg 2: exactly one extension, to 12 seeds, re-read once.
EXTENSION_SEEDS = tuple(range(len(ARM_SEEDS), 12))  # 5..11
EXTENSION_ARMS = ("B_cell", "D_flat")
T_EXTENSION = 2.593  # t(11), two-sided 97.5% -- Bonferroni for the single re-read

ALL_ARMS = ("A_factored", "B_cell", "C_pooled", "E_tile", "D_flat")

GUARD_ARM = "B_cell"
GUARD_SEED = 0
RECEIPT = Path("results/exp012-guard-receipt.json")


# --------------------------------------------------------------------------
# The sample, redrawn exactly as the instrument drew it
# --------------------------------------------------------------------------


def draw_sample(reader: SweepReader, board):
    """Reproduce the instrument's draw bit for bit.

    Same seed, same layer order, same shuffle, same split. If this diverges the
    reproduction guard below catches it -- which is the point of running the
    guard rather than trusting this comment.
    """
    rng = random.Random(SEED)
    drawn = []
    for t in LAYERS:
        drawn += [(t, s) for s in draw_layer(reader, t, PER_LAYER, rng)]
    rng.shuffle(drawn)
    states = [s for _, s in drawn]
    train_states = states[:TRAIN_SIZE]
    heldout = states[TRAIN_SIZE : TRAIN_SIZE + HELDOUT_SIZE]

    train_samples = []
    for state in train_states:
        sample = build_sample(board, reader, state)
        if sample is None:
            raise SystemExit("a WIN position with no optimal move: ground truth is bad")
        train_samples.append(sample)
    return train_samples, heldout


# --------------------------------------------------------------------------
# The reproduction guard
# --------------------------------------------------------------------------


def tree_state() -> dict:
    """The commit, and whether anything this run depends on is uncommitted."""
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "az", "scripts/exp012_conditioned_head.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return {"head": head, "dirty": bool(dirty), "dirty_paths": dirty}


def digest_hits(hits) -> str:
    return hashlib.sha256(bytes(bool(h) for h in hits)).hexdigest()


def reproduction_guard(variant, board, reader, artefact, train_samples, heldout) -> str:
    """Retrain one measured cell and require the hit vector to match exactly.

    A mean that matches is not evidence: two runs can score 74.8% on different
    positions. The comparison is element-wise, and it asserts positive evidence
    -- the vector exists, has the registered length, and is not degenerate --
    rather than merely failing to raise.
    """
    row = next(r for r in artefact["results"][GUARD_ARM] if r["seed"] == GUARD_SEED)
    expected = [bool(h) for h in row["search"]["hits"]]
    if len(expected) != HELDOUT_SIZE:
        raise SystemExit(f"artefact hit vector is {len(expected)}, not {HELDOUT_SIZE}")
    if len(set(expected)) < 2:
        raise SystemExit(
            "artefact hit vector is constant; the guard would pass on a broken "
            "pipeline that scored everything or nothing"
        )

    print(
        f"guard: retraining {GUARD_ARM} seed {GUARD_SEED} at {EPOCHS} epochs "
        "and comparing hits element-wise",
        flush=True,
    )
    started = time.monotonic()
    net, history = train_arm(variant, GUARD_ARM, train_samples, GUARD_SEED)
    scores = search_scores(net, variant, board, heldout, reader, GUARD_SEED)
    actual = [bool(h) for h in scores["hits"]]

    pairs = zip(expected, actual, strict=True)
    mismatches = [i for i, (a, b) in enumerate(pairs) if a != b]
    if mismatches:
        raise SystemExit(
            f"REPRODUCTION FAILED: {len(mismatches)} of {HELDOUT_SIZE} positions "
            f"differ (first at index {mismatches[0]}).\n"
            f"  artefact top1 {row['search']['top1']:.4f}, rerun {scores['top1']:.4f}\n"
            "  The sample draw, the network, or the training path has moved since "
            "the run. New seeds may not be merged with the artefact's rows."
        )
    loss_drift = abs(history[-1] - row["final_train_loss"])
    if loss_drift > 1e-9:
        raise SystemExit(
            f"REPRODUCTION FAILED on training loss: artefact "
            f"{row['final_train_loss']:.10f}, rerun {history[-1]:.10f}"
        )

    digest = digest_hits(actual)
    print(
        f"guard passed in {time.monotonic() - started:.0f}s: "
        f"{HELDOUT_SIZE}/{HELDOUT_SIZE} positions identical, "
        f"loss {history[-1]:.6f}, digest {digest[:12]}",
        flush=True,
    )
    return digest


def guard_once(variant, board, reader, artefact, train_samples, heldout) -> dict:
    """Run the guard, or accept a receipt written by an identical tree."""
    state = tree_state()
    if RECEIPT.exists() and not state["dirty"]:
        receipt = json.loads(RECEIPT.read_text())
        if receipt.get("head") == state["head"] and not receipt.get("dirty"):
            print(
                f"guard: receipt from commit {state['head'][:12]} accepted "
                f"(digest {receipt['digest'][:12]})",
                flush=True,
            )
            return receipt
    if state["dirty"]:
        print(
            "guard: tree is dirty in az/ or the instrument, so the receipt is "
            f"not reusable ({state['dirty_paths'].splitlines()[:3]})",
            flush=True,
        )
    digest = reproduction_guard(
        variant, board, reader, artefact, train_samples, heldout
    )
    receipt = {**state, "arm": GUARD_ARM, "seed": GUARD_SEED, "digest": digest}
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, indent=2))
    return receipt


# --------------------------------------------------------------------------
# Leg 1 -- convergence
# --------------------------------------------------------------------------


def final_five(history: list[float]) -> tuple[float, float]:
    """Improvement over the final five epochs, as a total and per epoch.

    The registered criterion is the *mean per-epoch* improvement over the final
    five epochs; the instrument logged only the four-step total under the name
    ``last_five_improvement``. Both are returned so the two artefacts stay
    comparable and the registered quantity is the one that gets read.
    """
    window = history[-5:]
    if len(window) < 2:
        return 0.0, 0.0
    total = window[0] - window[-1]
    return total, total / (len(window) - 1)


def leg_convergence(variant, board, reader, artefact, train_samples, heldout) -> dict:
    """One seed per arm at 80 epochs, paired against the 40-epoch row."""
    rows = {}
    for arm in ALL_ARMS:
        baseline = next(
            r for r in artefact["results"][arm] if r["seed"] == CONVERGENCE_SEED
        )
        started = time.monotonic()
        net, history = train_arm(
            variant, arm, train_samples, CONVERGENCE_SEED, epochs=CONVERGENCE_EPOCHS
        )
        scores = search_scores(net, variant, board, heldout, reader, CONVERGENCE_SEED)
        sup = supervised_scores(net, variant, board, heldout, reader)
        paired = mcnemar(
            [bool(h) for h in baseline["search"]["hits"]],
            [bool(h) for h in scores["hits"]],
        )
        total_80, per_epoch_80 = final_five(history)
        rows[arm] = {
            "seed": CONVERGENCE_SEED,
            "epochs": CONVERGENCE_EPOCHS,
            "top1_40": baseline["search"]["top1"],
            "top1_80": scores["top1"],
            "supervised_40": baseline["supervised"]["top1"],
            "supervised_80": sup["top1"],
            "loss_40": baseline["final_train_loss"],
            "loss_80": history[-1],
            "last_five_improvement_40": baseline["last_five_improvement"],
            "last_five_improvement_80": total_80,
            "per_epoch_improvement_40": baseline["last_five_improvement"] / 4,
            "per_epoch_improvement_80": per_epoch_80,
            "mcnemar": paired,
            "hits": scores["hits"],
            "seconds": time.monotonic() - started,
        }
        print(
            f"  {arm:>11}  40ep {rows[arm]['top1_40']:.1%} -> "
            f"80ep {rows[arm]['top1_80']:.1%}   "
            f"McNemar {paired['difference']:+.1%} "
            f"[{paired['ci_low']:+.1%}, {paired['ci_high']:+.1%}] "
            f"({paired['discordant']} discordant)   "
            f"loss {rows[arm]['loss_40']:.4f} -> {rows[arm]['loss_80']:.4f}  "
            f"({rows[arm]['seconds']:.0f}s)",
            flush=True,
        )
    return rows


# --------------------------------------------------------------------------
# Leg 2 -- the bounded extension
# --------------------------------------------------------------------------


def paired_interval(baseline: list[float], arm: list[float], critical: float) -> dict:
    diffs = [x - y for y, x in zip(baseline, arm, strict=True)]
    n = len(diffs)
    mean = statistics.fmean(diffs)
    sd = statistics.stdev(diffs)
    half = critical * sd / math.sqrt(n)
    return {
        "difference": mean,
        "ci_low": mean - half,
        "ci_high": mean + half,
        "half_width": half,
        "sd_differences": sd,
        "n": n,
    }


def adoption_branch(interval: dict) -> str:
    if interval["half_width"] <= 0.0:
        return "REFUSED: zero-width interval; every seed gave the identical difference"
    if interval["ci_high"] < MARGIN:
        return "ADOPT (b): the conditioned head reaches the flat head"
    if interval["ci_low"] > MARGIN:
        return "REFUTE (b), ADOPT (c): the flat head leads by more than the margin"
    return (
        "STILL NOT A RESULT: the interval spans the margin at 12 seeds. The "
        "extension is spent -- no further seeds. Recorded as undecided."
    )


def leg_extension(variant, board, reader, artefact, train_samples, heldout) -> dict:
    """Seeds 5-11 for B and D, merged with the artefact's 0-4 and read once."""
    new_rows: dict[str, list] = {arm: [] for arm in EXTENSION_ARMS}
    for arm in EXTENSION_ARMS:
        for seed in EXTENSION_SEEDS:
            started = time.monotonic()
            net, history = train_arm(variant, arm, train_samples, seed)
            scores = search_scores(net, variant, board, heldout, reader, seed)
            sup = supervised_scores(net, variant, board, heldout, reader)
            new_rows[arm].append(
                {
                    "seed": seed,
                    "final_train_loss": history[-1],
                    "last_five_improvement": history[-5] - history[-1],
                    "supervised": {"top1": sup["top1"]},
                    "search": {"top1": scores["top1"], "hits": scores["hits"]},
                }
            )
            print(
                f"  {arm:>11} seed {seed}: search {scores['top1']:.1%}  "
                f"supervised {sup['top1']:.1%}  loss {history[-1]:.4f}  "
                f"({time.monotonic() - started:.0f}s)",
                flush=True,
            )

    merged = {}
    for arm in EXTENSION_ARMS:
        original = [r["search"]["top1"] for r in artefact["results"][arm]]
        merged[arm] = original + [r["search"]["top1"] for r in new_rows[arm]]
        expected = len(ARM_SEEDS) + len(EXTENSION_SEEDS)
        if len(merged[arm]) != expected:
            raise SystemExit(
                f"{arm} merged to {len(merged[arm])} seeds, expected {expected}"
            )

    interval = paired_interval(merged["B_cell"], merged["D_flat"], T_EXTENSION)
    return {
        "new_rows": new_rows,
        "merged_means": merged,
        "D_minus_B": interval,
        "verdict": adoption_branch(interval),
    }


# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--leg", required=True, choices=("convergence", "extension"))
    parser.add_argument("--database", default="data/subgame-solutions/5x3-h2.json")
    parser.add_argument("--checkpoint", default="data/checkpoints")
    parser.add_argument(
        "--artefact", default="results/exp012-conditioned-head-5x3-h2.json"
    )
    parser.add_argument("--out", default=None)
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "overwrite an existing output. The extension is permitted ONCE; "
            "re-running it and keeping the better read is optional stopping."
        ),
    )
    args = parser.parse_args()

    out = Path(args.out or f"results/exp012-{args.leg}-5x3-h2.json")
    if out.exists() and not args.force:
        raise SystemExit(
            f"{out} already exists. The rule permits one extension, read once; "
            "re-running and keeping the better read is optional stopping. "
            "Pass --force only to repair a crashed run."
        )

    started = time.monotonic()
    variant = Variant(5, 3, Arm("h2"))
    board = variant.board()
    ground_truth = verify_ground_truth(Path(args.database))
    reader = SweepReader(variant, Checkpoint(Path(args.checkpoint) / variant.name))
    artefact = json.loads(Path(args.artefact).read_text())
    if artefact.get("experiment") != "EXP-012":
        raise SystemExit(f"not an EXP-012 artefact: {args.artefact}")

    train_samples, heldout = draw_sample(reader, board)
    print(f"drew train {len(train_samples)}, held out {len(heldout)}", flush=True)

    receipt = guard_once(variant, board, reader, artefact, train_samples, heldout)

    if args.leg == "convergence":
        print(
            f"leg 1: convergence, seed {CONVERGENCE_SEED} per arm at "
            f"{CONVERGENCE_EPOCHS} epochs, paired by McNemar against the "
            f"{EPOCHS}-epoch row",
            flush=True,
        )
        payload = {
            "leg": "convergence",
            "note": (
                "Reported, not asserted. The registered criterion is the "
                "training-loss trajectory; this paired re-run says whether 40 "
                "epochs left anything on the table. It gates nothing."
            ),
            "arms": leg_convergence(
                variant, board, reader, artefact, train_samples, heldout
            ),
        }
    else:
        print(
            f"leg 2: the single bounded extension, seeds "
            f"{EXTENSION_SEEDS[0]}-{EXTENSION_SEEDS[-1]} for "
            f"{', '.join(EXTENSION_ARMS)}",
            flush=True,
        )
        payload = {
            "leg": "extension",
            "note": (
                "The one extension the rule permits, read once at t(11), "
                "alpha = 0.025. Arms A, C and E are not extended: the mechanism "
                "contrasts are void because the C - A precondition failed, and "
                "sharpening a void number is not a use of compute."
            ),
            **leg_extension(variant, board, reader, artefact, train_samples, heldout),
        }

    payload |= {
        "experiment": "EXP-012",
        "variant": variant.name,
        "ground_truth_v5": ground_truth["verification"]["V5_checksum_sha256"],
        "reproduction_guard": receipt,
        "elapsed_seconds": time.monotonic() - started,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))

    if args.leg == "extension":
        interval = payload["D_minus_B"]
        print()
        print(
            f"D - B at 12 seeds  {interval['difference']:+.2%} "
            f"[{interval['ci_low']:+.2%}, {interval['ci_high']:+.2%}]  "
            f"hw {interval['half_width']:.2%}"
        )
        print(f"VERDICT  {payload['verdict']}")
    print(f"written  {out}  ({payload['elapsed_seconds']:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
