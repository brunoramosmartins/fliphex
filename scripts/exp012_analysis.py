"""EXP-012 analysis: apply the registered decision rule to the saved artefact.

The instrument (``scripts/exp012_conditioned_head.py``) already prints a verdict.
This script exists so the verdict is reproducible from the raw result file rather
than from a run that took 8.8 hours, and so that three reads registered in
``experiments/registry.md`` but absent from the instrument are recovered:

1. **The clustered bootstrap.** The registry names two intervals -- a paired *t*
   over the five seed means (training-seed variance, conditional on the fixed
   held-out set) and a bootstrap clustered on the 500 held-out positions
   (position-sampling variance) -- and requires the write-up to quote **the wider
   of the two**. The instrument wrote only the first. The second is recoverable
   offline because per-position hits were saved.
2. **``sd(differences)`` and the implied between-arm correlation.** Registered in
   the power section, to keep the design from being described as
   paired-and-therefore-powered when EXP-011 measured the pairing to be worth
   nothing.
3. **The convergence read.** The registry pins the criterion to the training-loss
   trajectory over the final five epochs. That is recoverable. The 80-epoch
   re-run paired by McNemar is **not** -- it was never implemented, and this
   script reports it as an outstanding registered obligation rather than
   quietly omitting it.

Outcome encoding, read from the producer rather than assumed
(``exp012_conditioned_head.py:406``)::

    hits.append(reader.slot(apply_move(board, state, best_move(root))) == SLOT_LOSS)

A ``hit`` is therefore True when the move the arm chose leaves the *opponent* in a
LOSS slot -- that is, the move is optimal for the mover. There are no draws on an
odd-celled board, so the encoding is binary with no third state to misfile.

Usage::

    .venv/bin/python scripts/exp012_analysis.py
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from pathlib import Path

#: Arms, in the order the registry lists them.
ARMS = ("A_factored", "B_cell", "C_pooled", "E_tile", "D_flat")
FROZEN_ARMS = ("B_cell", "C_pooled", "E_tile")

#: Registered design constants. Restated here so this script fails loudly if the
#: artefact was produced under a different configuration.
SEEDS = 5
HELDOUT = 500
MARGIN = 0.05
DELTA = 0.02
T_ADOPT = 2.776  # t(4), alpha = 0.05, two-sided
T_MECHANISM = 3.169  # t(4), alpha = 0.025 -- Bonferroni over the two independent
#: contrasts, since B - E = (B - C) - (E - C) exactly.

#: The bounded extension the rule permits: exactly one, to 12 seeds, re-read once.
EXTENSION_SEEDS = 12
T_EXTENSION_ADOPT = 2.593  # t(11), alpha = 0.025

BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 29


# --------------------------------------------------------------------------
# Validity guards. Nothing is printed before these pass.
# --------------------------------------------------------------------------


def guard(artefact: dict, database: Path) -> None:
    """Hard-fail on anything that would make a printed number quotable but wrong."""
    if artefact.get("experiment") != "EXP-012":
        raise SystemExit(f"not an EXP-012 artefact: {artefact.get('experiment')!r}")

    if not database.exists():
        raise SystemExit(f"ground-truth database missing: {database}")
    # Provenance is the V5 checksum the solver recorded *inside* the artefact,
    # not a hash of the file bytes: the solution artefact is rewritten with fresh
    # timestamps and progress metadata on every resume, so a byte hash would
    # report drift where the solved values are identical. Read from the same
    # field the instrument read (`exp012_conditioned_head.py` ->
    # `verify_ground_truth`), or this guard checks a different thing than the run.
    solution = json.loads(database.read_text())
    digest = solution["verification"]["V5_checksum_sha256"]
    if digest != artefact["ground_truth_v5"]:
        raise SystemExit(
            "ground truth has changed since the run:\n"
            f"  artefact {artefact['ground_truth_v5']}\n"
            f"  on disk  {digest}"
        )
    if solution.get("termination") != "exhausted":
        raise SystemExit(
            f"R1: {database} terminated as {solution.get('termination')!r}, "
            "not 'exhausted'; a truncated search may not ground an axis"
        )

    schedule = artefact["schedule"]
    if artefact["margin"] != MARGIN or artefact["delta"] != DELTA:
        raise SystemExit(
            f"artefact ran at margin={artefact['margin']} delta={artefact['delta']}; "
            f"the registered rule is margin={MARGIN} delta={DELTA}"
        )

    for arm in ARMS:
        rows = artefact["results"].get(arm, [])
        if len(rows) != SEEDS:
            raise SystemExit(f"arm {arm} has {len(rows)} seeds, expected {SEEDS}")
        for row in rows:
            for source in ("search", "supervised"):
                hits = row[source]["hits"]
                if len(hits) != HELDOUT:
                    raise SystemExit(
                        f"{arm} seed {row['seed']} {source}: {len(hits)} hits, "
                        f"expected {HELDOUT}"
                    )

    for arm in FROZEN_ARMS:
        rows = artefact["frozen"].get(arm, [])
        if len(rows) != SEEDS:
            raise SystemExit(
                f"frozen-tower arm {arm} has {len(rows)} seeds, expected {SEEDS}; "
                "the mechanism read at head level is incomplete"
            )

    # Every arm must have been evaluated on the *same* held-out positions, or the
    # pairing is a fiction. The instrument does not record position ids, but a
    # shared held-out set implies every hits vector has the same length and the
    # per-position bootstrap below resamples one index set across all arms -- so
    # the check that matters is that the lengths agree, which is asserted above.
    seeds_seen = {tuple(r["seed"] for r in artefact["results"][arm]) for arm in ARMS}
    if len(seeds_seen) != 1:
        raise SystemExit(f"arms do not share a seed set: {seeds_seen}")

    print(
        f"guards passed: {len(ARMS)} arms x {SEEDS} seeds x {HELDOUT} positions, "
        f"ground truth {digest[:12]}, "
        f"{schedule['epochs']} epochs @ lr {schedule['learning_rate']}"
    )


# --------------------------------------------------------------------------
# Intervals
# --------------------------------------------------------------------------


def wilson(hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = hits / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def seed_contrast(baseline: list[float], arm: list[float], critical: float) -> dict:
    """Paired *t* over seed means -- the registered primary interval."""
    diffs = [x - y for y, x in zip(baseline, arm, strict=True)]
    n = len(diffs)
    mean = statistics.fmean(diffs)
    sd = statistics.stdev(diffs)
    half = critical * sd / math.sqrt(n)
    sd_a, sd_b = statistics.stdev(baseline), statistics.stdev(arm)
    # Backing the correlation out of the variances:
    #   var(d) = var(a) + var(b) - 2 * rho * sd_a * sd_b
    rho = (sd_a**2 + sd_b**2 - sd**2) / (2 * sd_a * sd_b)
    return {
        "difference": mean,
        "ci_low": mean - half,
        "ci_high": mean + half,
        "half_width": half,
        "sd_differences": sd,
        "implied_correlation": rho,
        "n": n,
    }


def clustered_bootstrap(
    baseline_hits: list[list[bool]],
    arm_hits: list[list[bool]],
    alpha: float,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> dict:
    """Bootstrap clustered on the held-out positions.

    The cluster is the position: one index set is drawn and applied to every seed
    of both arms, so the resample perturbs *which positions were sampled* while
    holding the training seeds fixed. That is the complement of the seed-mean
    interval, which holds positions fixed and perturbs the seeds.
    """
    n_positions = len(baseline_hits[0])
    rng = random.Random(BOOTSTRAP_SEED)
    point = statistics.fmean(statistics.fmean(a) for a in arm_hits) - statistics.fmean(
        statistics.fmean(b) for b in baseline_hits
    )

    draws = []
    for _ in range(resamples):
        idx = [rng.randrange(n_positions) for _ in range(n_positions)]
        arm_mean = statistics.fmean(
            statistics.fmean(hits[i] for i in idx) for hits in arm_hits
        )
        base_mean = statistics.fmean(
            statistics.fmean(hits[i] for i in idx) for hits in baseline_hits
        )
        draws.append(arm_mean - base_mean)
    draws.sort()
    lo = draws[int(alpha / 2 * resamples)]
    hi = draws[min(resamples - 1, int((1 - alpha / 2) * resamples))]
    return {
        "difference": point,
        "ci_low": lo,
        "ci_high": hi,
        "half_width": (hi - lo) / 2,
        "resamples": resamples,
    }


def wider(seed_iv: dict, boot_iv: dict) -> str:
    return (
        "clustered bootstrap"
        if boot_iv["half_width"] > seed_iv["half_width"]
        else "seed means"
    )


# --------------------------------------------------------------------------
# The registered rule
# --------------------------------------------------------------------------


def adoption_branch(interval: dict) -> str:
    """``D - B`` against the 5-point margin. adr-005's order decides ties in name."""
    if interval["ci_high"] < MARGIN:
        return "ADOPT (b): the conditioned head reaches the flat head"
    if interval["ci_low"] > MARGIN:
        return "REFUTE (b), ADOPT (c): the flat head is better by more than the margin"
    return "NOT A RESULT: the interval spans the margin; one bounded extension is due"


def tost(interval: dict, delta: float = DELTA) -> bool:
    """The entire interval must lie strictly inside +/-delta."""
    if interval["half_width"] <= 0.0:
        return False
    return interval["ci_low"] > -delta and interval["ci_high"] < delta


def tost_feasible(interval: dict, delta: float = DELTA) -> bool:
    """Could this test have passed at all, at this half-width?

    If the half-width alone exceeds delta, no point estimate whatsoever clears
    the gate -- the test was unpassable before the data existed. That is a
    property of the design, not of the result, and it changes how the failure
    should be read.
    """
    return interval["half_width"] < delta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artefact", default="results/exp012-conditioned-head-5x3-h2.json"
    )
    parser.add_argument("--database", default="data/subgame-solutions/5x3-h2.json")
    parser.add_argument("--resamples", type=int, default=BOOTSTRAP_RESAMPLES)
    args = parser.parse_args()

    path = Path(args.artefact)
    if not path.exists():
        raise SystemExit(f"artefact not found: {path}")
    artefact = json.loads(path.read_text())
    guard(artefact, Path(args.database))

    results = artefact["results"]
    means = {arm: [r["search"]["top1"] for r in results[arm]] for arm in ARMS}
    hits = {arm: [r["search"]["hits"] for r in results[arm]] for arm in ARMS}
    floor = artefact["random_floor"]

    # ---- descriptives -----------------------------------------------------
    # Wilson raw and Bonferroni-corrected for the five arms (z at 0.05/5).
    print("\n== descriptives (primary: top-1 after 400 PUCT simulations) ==")
    print(
        f"{'arm':<12} {'params':>8} {'mean':>7} {'sd':>6} "
        f"{'Wilson (pooled)':>20} {'Bonf x5':>18} {'sup':>7} {'loss':>7}"
    )
    for arm in ARMS:
        pooled_hits = sum(sum(h) for h in hits[arm])
        pooled_n = sum(len(h) for h in hits[arm])
        lo, hi = wilson(pooled_hits, pooled_n)
        blo, bhi = wilson(pooled_hits, pooled_n, z=2.576)
        sup = statistics.fmean(r["supervised"]["top1"] for r in results[arm])
        loss = statistics.fmean(r["final_train_loss"] for r in results[arm])
        print(
            f"{arm:<12} {results[arm][0]['parameters']:>8} "
            f"{statistics.fmean(means[arm]):>6.1%} "
            f"{statistics.stdev(means[arm]):>5.1%} "
            f"[{lo:>6.1%},{hi:>6.1%}] [{blo:>6.1%},{bhi:>6.1%}] "
            f"{sup:>6.1%} {loss:>7.4f}"
        )
    print(f"{'floor':<12} {'':>8} {floor:>6.1%}   (uniform random legal move)")

    print("\n== convergence: training-loss improvement over the final five epochs ==")
    for arm in ARMS:
        imp = [r["last_five_improvement"] for r in results[arm]]
        print(
            f"{arm:<12} total {statistics.fmean(imp):.5f}  "
            f"per epoch {statistics.fmean(imp) / 4:.5f}  max {max(imp):.5f}"
        )
    print(
        "  OUTSTANDING: the registered 80-epoch re-run (one seed per arm, paired by\n"
        "  McNemar on the same 500 positions) was not implemented and did not run.\n"
        "  Convergence is therefore reported on the trajectory criterion only."
    )

    print("\n== layer parity (pre-registered stratified read) ==")
    for arm in ARMS:
        row = artefact["layer_parity"][arm]
        print(f"{arm:<12} odd {row['odd']:>6.1%}   even {row['even']:>6.1%}")

    # ---- the two intervals, side by side ----------------------------------
    print("\n== adoption: D - B, alpha = 0.05, margin 5.0 pts ==")
    gap = seed_contrast(means["B_cell"], means["D_flat"], T_ADOPT)
    boot = clustered_bootstrap(
        hits["B_cell"], hits["D_flat"], 0.05, resamples=args.resamples
    )
    for label, iv in (("seed means (paired t)", gap), ("positions (bootstrap)", boot)):
        print(
            f"  {label:<24} {iv['difference']:+.2%} "
            f"[{iv['ci_low']:+.2%}, {iv['ci_high']:+.2%}]  hw {iv['half_width']:.2%}"
        )
    print(f"  wider interval: {wider(gap, boot)}")
    print(
        f"  sd(differences) {gap['sd_differences']:.2%}, "
        f"implied between-arm correlation {gap['implied_correlation']:+.3f}"
    )
    branch = adoption_branch(gap)
    print(f"  VERDICT  {branch}")

    # ---- the validity precondition ----------------------------------------
    print("\n== precondition: C - A, TOST at +/-2.0 pts ==")
    pre = seed_contrast(means["A_factored"], means["C_pooled"], T_ADOPT)
    pre_boot = clustered_bootstrap(
        hits["A_factored"], hits["C_pooled"], 0.05, resamples=args.resamples
    )
    for label, iv in (
        ("seed means (paired t)", pre),
        ("positions (bootstrap)", pre_boot),
    ):
        print(
            f"  {label:<24} {iv['difference']:+.2%} "
            f"[{iv['ci_low']:+.2%}, {iv['ci_high']:+.2%}]  hw {iv['half_width']:.2%}"
        )
    passed = tost(pre)
    print(f"  TOST: {'PASS' if passed else 'FAIL'}")
    if not tost_feasible(pre):
        print(
            f"  NOTE: the half-width alone ({pre['half_width']:.2%}) exceeds "
            f"delta ({DELTA:.1%}).\n"
            "  No point estimate could have cleared this gate at 5 seeds. The gate\n"
            "  was unpassable by construction, which is a defect in the design and\n"
            "  not a property of the arms."
        )
    print(
        f"  sd(differences) {pre['sd_differences']:.2%}, "
        f"implied correlation {pre['implied_correlation']:+.3f}"
    )

    # ---- mechanism, void unless the precondition passed --------------------
    print("\n== mechanism contrasts, alpha = 0.025 (Bonferroni over 2 independent) ==")
    if not passed:
        print("  PRECONDITION FAILED -> every contrast below is UNRESOLVED,")
        print("  regardless of what it shows. Printed for the record only.")
    pairs = (
        ("B - C", "C_pooled", "B_cell"),
        ("E - C", "C_pooled", "E_tile"),
        ("B - E", "E_tile", "B_cell"),
    )
    for label, base, arm in pairs:
        joint = seed_contrast(means[base], means[arm], T_MECHANISM)
        frozen_means = {
            a: [r["search"]["top1"] for r in artefact["frozen"][a]] for a in FROZEN_ARMS
        }
        froz = seed_contrast(frozen_means[base], frozen_means[arm], T_MECHANISM)
        print(
            f"  {label}  joint  {joint['difference']:+.2%} "
            f"[{joint['ci_low']:+.2%}, {joint['ci_high']:+.2%}]   "
            f"frozen {froz['difference']:+.2%} "
            f"[{froz['ci_low']:+.2%}, {froz['ci_high']:+.2%}]"
        )
    print(
        "  Reporting rule (registered): a null mechanism contrast is 'NOT DETECTED',\n"
        "  never 'absent'. Four properties of this design push these toward zero."
    )

    # ---- what the bounded extension would need -----------------------------
    print("\n== the bounded extension, as a plan and not as a result ==")
    print(
        f"  The rule permits exactly one extension to {EXTENSION_SEEDS} seeds,\n"
        f"  re-read once at Bonferroni alpha = 0.025.\n"
        f"  Projecting the observed sd forward:"
    )
    proj_hw = T_EXTENSION_ADOPT * gap["sd_differences"] / math.sqrt(EXTENSION_SEEDS)
    lo, hi = gap["difference"] - proj_hw, gap["difference"] + proj_hw
    print(
        f"    D - B  hw {proj_hw:.2%} -> [{lo:+.2%}, {hi:+.2%}]  "
        f"({'adopt (b)' if hi < MARGIN else 'still spans the margin'})"
    )
    print(
        f"    indecision band at n={EXTENSION_SEEDS}: "
        f"{MARGIN - proj_hw:.2%} to {MARGIN + proj_hw:.2%}; "
        f"the observed point estimate is {gap['difference']:.2%}"
    )
    print(
        "    This is a projection under the observed variance, not a verdict. The\n"
        "    point estimate will move with seven new seeds, and it sits close\n"
        "    enough to the band edge that the extension is genuinely two-sided."
    )
    proj_pre = T_ADOPT * pre["sd_differences"] / math.sqrt(EXTENSION_SEEDS)
    need = DELTA - proj_pre
    print(
        f"    C - A  hw would fall to {proj_pre:.2%}; TOST would then need\n"
        f"    |C - A| < {need:.2%}, against {pre['difference']:+.2%} observed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
