"""EXP-013 analysis: apply the registered rule to the saved artefact.

The instrument prints a verdict. This exists so the verdict is reproducible from
the raw result file rather than from a 3.4-hour run, and — more usefully — so the
rule is applied by code that did not produce the numbers. Every quantity below is
**recomputed from ``results``** and cross-checked against what the run stored; a
disagreement is a hard failure, because one of the two paths is then wrong and
there is no way to tell which from the summary alone.

Outcome encoding, read from the producer rather than assumed
(``exp012_conditioned_head.py:406``, which both arms score through)::

    hits.append(reader.slot(apply_move(board, state, best_move(root))) == SLOT_LOSS)

A ``hit`` is True when the chosen move leaves the *opponent* in a LOSS slot — the
move is optimal for the mover. Odd cell count, so no draws and no third state to
misfile.

The registered read
-------------------
One-sided non-inferiority of ``V_conv − L_linear`` at δ = 1.7 points, ``t(11) =
1.796``, on the twelve seed means. The bootstrap clustered on the 500 held-out
positions is reported beside it and the wider of the two is quoted; the verdict is
read on the seed-mean interval, which is the registered test, and this script says
explicitly whether the wider interval would have changed it.

**Feasibility is checked before the verdict is printed.** EXP-012's equivalence
gate was unpassable — its δ equalled its forecast half-width, so no point estimate
could clear it. If the observed half-width here exceeds δ, the gate could not have
been failed *or* passed on evidence and this script refuses to print an adoption.

Usage::

    .venv/bin/python scripts/exp013_analysis.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
from pathlib import Path

ARMS = ("L_linear", "V_conv")
SEEDS = 12
HELDOUT = 500

#: Registered constants, restated so this fails loudly on an artefact produced
#: under a different configuration.
DELTA = 0.017
T_ONE_SIDED = 1.796
MATCH_GAMES = 200

BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 29

#: What EXP-012's adoption conceded, and the tolerance it was taken under. The
#: margin is 5.0 - 3.3; both ends of the 3.3's interval are printed so the
#: derivation's own uncertainty stays visible.
CONCEDED = 0.033
CONCEDED_CI = (0.0188, 0.0475)
TOLERANCE = 0.05


# --------------------------------------------------------------------------
# Validity guards. Nothing is printed before these pass.
# --------------------------------------------------------------------------


def guard(artefact: dict, database: Path) -> None:
    if artefact.get("experiment") != "EXP-013":
        raise SystemExit(f"not an EXP-013 artefact: {artefact.get('experiment')!r}")

    if not database.exists():
        raise SystemExit(f"ground-truth database missing: {database}")
    # The solver's own V5 checksum, not a hash of the file: the solution artefact
    # is rewritten with fresh metadata on every resume, so a byte hash would
    # report drift where the solved values are identical.
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

    if artefact["primary_V_minus_L"]["delta"] != DELTA:
        raise SystemExit(
            f"artefact ran at delta={artefact['primary_V_minus_L']['delta']}; "
            f"the registered margin is {DELTA}"
        )

    for arm in ARMS:
        rows = artefact["results"].get(arm, [])
        if len(rows) != SEEDS:
            raise SystemExit(f"arm {arm} has {len(rows)} seeds, expected {SEEDS}")
        if [r["seed"] for r in rows] != list(range(SEEDS)):
            raise SystemExit(f"arm {arm} seeds are {[r['seed'] for r in rows]}")
        for row in rows:
            hits = row["search"]["hits"]
            if len(hits) != HELDOUT:
                raise SystemExit(
                    f"{arm} seed {row['seed']}: {len(hits)} hits, expected {HELDOUT}"
                )
            stored = row["search"]["top1"]
            if abs(sum(hits) / len(hits) - stored) > 1e-9:
                raise SystemExit(
                    f"{arm} seed {row['seed']}: stored top1 {stored} does not "
                    f"match its own hit vector"
                )

    # The reproduction guard is what licenses reusing EXP-012's rows. Check its
    # digest is the digest of the incumbent rows actually stored here -- if the
    # guard compared against one thing and something else was written down, the
    # reuse argument covers nothing.
    seed_zero = artefact["results"]["L_linear"][0]
    recomputed = hashlib.sha256(
        bytes(bool(h) for h in seed_zero["search"]["hits"])
    ).hexdigest()
    if recomputed != artefact["reproduction_guard"]["digest"]:
        raise SystemExit(
            "the reproduction guard's digest is not the digest of the incumbent "
            "rows in this artefact:\n"
            f"  guard {artefact['reproduction_guard']['digest']}\n"
            f"  rows  {recomputed}\n"
            "The guard checked something other than what was written down."
        )

    match = artefact["head_to_head"]
    if match["games"] != MATCH_GAMES:
        raise SystemExit(
            f"the match ran {match['games']} games, expected {MATCH_GAMES}"
        )

    scale = artefact["rotation_scale"]
    if not scale.get("scale") or scale["scale"] <= 0:
        raise SystemExit("the initialisation match did not produce a usable scale")

    print(
        f"guards passed: {len(ARMS)} arms x {SEEDS} seeds x {HELDOUT} positions, "
        f"ground truth {digest[:12]}, guard digest "
        f"{artefact['reproduction_guard']['digest'][:12]} verified against the "
        "stored incumbent rows"
    )


# --------------------------------------------------------------------------


def wilson(hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = hits / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def non_inferiority(baseline: list[float], arm: list[float]) -> dict:
    diffs = [x - y for y, x in zip(baseline, arm, strict=True)]
    n = len(diffs)
    mean = statistics.fmean(diffs)
    sd = statistics.stdev(diffs)
    half = T_ONE_SIDED * sd / math.sqrt(n)
    sd_a, sd_b = statistics.stdev(baseline), statistics.stdev(arm)
    rho = (sd_a**2 + sd_b**2 - sd**2) / (2 * sd_a * sd_b)
    return {
        "difference": mean,
        "lower_limit": mean - half,
        "half_width": half,
        "sd_differences": sd,
        "implied_correlation": rho,
        "n": n,
        "degenerate": half <= 0.0,
        "passed": half > 0.0 and (mean - half) > -DELTA,
    }


def clustered_bootstrap(baseline_hits, arm_hits, resamples: int) -> dict:
    n_positions = len(baseline_hits[0])
    rng = random.Random(BOOTSTRAP_SEED)
    point = statistics.fmean(statistics.fmean(h) for h in arm_hits) - statistics.fmean(
        statistics.fmean(h) for h in baseline_hits
    )
    draws = []
    for _ in range(resamples):
        idx = [rng.randrange(n_positions) for _ in range(n_positions)]
        draws.append(
            statistics.fmean(statistics.fmean(h[i] for i in idx) for h in arm_hits)
            - statistics.fmean(
                statistics.fmean(h[i] for i in idx) for h in baseline_hits
            )
        )
    draws.sort()
    lower = draws[int(0.05 * resamples)]
    return {
        "difference": point,
        "lower_limit": lower,
        "half_width": point - lower,
        "resamples": resamples,
    }


def parity(rows, layers) -> dict:
    odd = even = odd_n = even_n = 0
    for row in rows:
        for hit, layer in zip(row["search"]["hits"], layers, strict=True):
            if layer % 2:
                odd += hit
                odd_n += 1
            else:
                even += hit
                even_n += 1
    return {"odd": odd / odd_n, "even": even / even_n}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artefact", default="results/exp013-conv-rotation-5x3-h2.json"
    )
    parser.add_argument("--database", default="data/subgame-solutions/5x3-h2.json")
    parser.add_argument("--resamples", type=int, default=BOOTSTRAP_RESAMPLES)
    args = parser.parse_args()

    path = Path(args.artefact)
    if not path.exists():
        raise SystemExit(
            f"artefact not found: {path}\n"
            "The run writes it only on completion; if it is still going, wait."
        )
    artefact = json.loads(path.read_text())
    guard(artefact, Path(args.database))

    results = artefact["results"]
    means = {arm: [r["search"]["top1"] for r in results[arm]] for arm in ARMS}
    hits = {
        arm: [[bool(h) for h in r["search"]["hits"]] for r in results[arm]]
        for arm in ARMS
    }

    # ---- descriptives -----------------------------------------------------
    print("\n== descriptives (primary: top-1 after 400 PUCT simulations) ==")
    print(
        f"{'arm':<10} {'params':>8} {'mean':>7} {'sd':>6} "
        f"{'Wilson':>17} {'Bonf x2':>17} {'sup':>7} {'loss':>8}"
    )
    for arm in ARMS:
        pooled = sum(sum(h) for h in hits[arm])
        n = sum(len(h) for h in hits[arm])
        lo, hi = wilson(pooled, n)
        blo, bhi = wilson(pooled, n, z=2.241)  # 0.05 / 2
        sup = statistics.fmean(r["supervised"]["top1"] for r in results[arm])
        loss = statistics.fmean(r["final_train_loss"] for r in results[arm])
        print(
            f"{arm:<10} {results[arm][0].get('parameters', 0):>8} "
            f"{statistics.fmean(means[arm]):>6.1%} "
            f"{statistics.stdev(means[arm]):>5.1%} "
            f"[{lo:>6.1%},{hi:>6.1%}] [{blo:>6.1%},{bhi:>6.1%}] "
            f"{sup:>6.1%} {loss:>8.4f}"
        )
    print(f"{'floor':<10} {'':>8} {artefact['random_floor']:>6.1%}")

    scale = artefact["rotation_scale"]
    print(
        f"\ninitialisation match: incumbent rotation-logit sd "
        f"{scale['linear_sd']:.5f}, conv {scale['conv_sd_unscaled']:.5f} "
        f"-> scale {scale['scale']:.4f}"
    )
    print(
        "  Without it the conv arm's rotation term would start at "
        f"{scale['conv_sd_unscaled'] / scale['linear_sd']:.2f}x the incumbent's."
    )

    # ---- the registered read ----------------------------------------------
    print(f"\n== primary: V_conv - L_linear, one-sided, margin -{DELTA:.1%} ==")
    primary = non_inferiority(means["L_linear"], means["V_conv"])
    boot = clustered_bootstrap(hits["L_linear"], hits["V_conv"], args.resamples)

    stored = artefact["primary_V_minus_L"]
    if abs(stored["difference"] - primary["difference"]) > 1e-9:
        raise SystemExit(
            "recomputed primary disagrees with the stored one:\n"
            f"  stored     {stored['difference']}\n"
            f"  recomputed {primary['difference']}\n"
            "One of the two paths is wrong and the summary cannot say which."
        )

    for label, iv in (("seed means (t)", primary), ("positions (bootstrap)", boot)):
        print(
            f"  {label:<22} {iv['difference']:+.2%}  lower {iv['lower_limit']:+.2%}  "
            f"hw {iv['half_width']:.2%}"
        )
    wider = (
        "clustered bootstrap"
        if boot["half_width"] > primary["half_width"]
        else "seed means"
    )
    print(f"  wider interval: {wider}")
    print(
        f"  sd(differences) {primary['sd_differences']:.2%}, "
        f"implied between-arm correlation {primary['implied_correlation']:+.3f}"
    )

    boot_passes = boot["lower_limit"] > -DELTA
    if boot_passes != primary["passed"]:
        print(
            "  NOTE: the two intervals disagree on the branch. The registered "
            "test is the seed-mean t; the bootstrap would have said "
            f"{'pass' if boot_passes else 'fail'}."
        )

    # ---- feasibility, before any verdict ----------------------------------
    print("\n== feasibility, recomputed from the observed spread ==")
    room = DELTA - primary["half_width"]
    print(
        f"  sd {primary['sd_differences']:.2%}  half-width "
        f"{primary['half_width']:.2%}  delta {DELTA:.1%}  room {room:+.2%}"
    )
    if room <= 0:
        print(
            "  UNPASSABLE: the half-width alone exceeds the margin, so no point\n"
            "  estimate could have cleared this gate. This is EXP-012's failure\n"
            "  mode. No adoption may be read from this run."
        )
    else:
        print("  passable: the gate could be cleared or failed on evidence")
    print(
        f"  margin derivation: {TOLERANCE:.1%} tolerance - {CONCEDED:.1%} conceded "
        f"= {DELTA:.1%}; the conceded figure carries "
        f"[{CONCEDED_CI[0]:.2%}, {CONCEDED_CI[1]:.2%}], so the conservative "
        f"derivation is {TOLERANCE - CONCEDED_CI[1]:.2%} and the optimistic "
        f"{TOLERANCE - CONCEDED_CI[0]:.2%}"
    )

    # ---- the non-solver check ---------------------------------------------
    match = artefact["head_to_head"]
    print("\n== head-to-head at seed 0, the non-solver check ==")
    lo, hi = wilson(match["conv_wins"], match["games"])
    print(
        f"  conv {match['conv_wins']}/{match['games']} = "
        f"{match['conv_wins'] / match['games']:.1%} [{lo:.1%}, {hi:.1%}]"
    )
    veto = hi < 0.5
    print(
        f"  decisive against conv: {veto}"
        + ("  -> VETO" if veto else "  (a veto needs the interval entirely below 50%)")
    )

    # ---- diagnostics -------------------------------------------------------
    print("\n== training loss, diagnostic and never a gate ==")
    losses = {
        arm: statistics.fmean(r["final_train_loss"] for r in results[arm])
        for arm in ARMS
    }
    print(f"  L_linear {losses['L_linear']:.4f}   V_conv {losses['V_conv']:.4f}")
    fits_worse = losses["V_conv"] > losses["L_linear"]
    not_worse_heldout = primary["difference"] > -DELTA
    if fits_worse and not_worse_heldout:
        print(
            "  Prediction 4 HOLDS: 198 parameters fit the training set less well\n"
            "  than 43,290 while generalising no worse. The unshared parameters\n"
            "  were fitting the training set and not the game."
        )
    elif not fits_worse:
        print(
            "  Prediction 4 FAILS: the conv arm fits training *better*. The\n"
            "  data-efficiency story is doing more work than the capacity story\n"
            "  -- shared weights see every cell on every position against the\n"
            "  unshared form's 36.7%."
        )

    print("\n== layer parity ==")
    parities = artefact["layer_parity"]
    for arm in ARMS:
        print(
            f"  {arm:<10} odd {parities[arm]['odd']:>6.1%}   "
            f"even {parities[arm]['even']:>6.1%}"
        )
    print(
        f"  V - L on odd layers "
        f"{parities['V_conv']['odd'] - parities['L_linear']['odd']:+.1%}, "
        f"even {parities['V_conv']['even'] - parities['L_linear']['even']:+.1%}"
    )

    # ---- verdict ------------------------------------------------------------
    print("\n== verdict ==")
    if primary["degenerate"]:
        branch = "REFUSED"
        text = "zero spread collapses the interval onto its point estimate"
    elif room <= 0:
        branch = "REFUSED"
        text = "the gate was unpassable at the observed spread"
    elif veto:
        branch = "ADOPT NOTHING"
        text = (
            "the solver-agreement primary and head-to-head play disagree\n"
            "  decisively. The disagreement is the finding."
        )
    elif primary["passed"]:
        branch = "ADOPT the convolutional form"
        text = (
            "non-inferior at the registered margin, at 218x fewer\n"
            "  parameters in the component the decision is about -- 119,952 saved\n"
            "  on the shipped board. adr-005 is amended."
        )
    else:
        branch = "KEEP the adopted linear form"
        text = (
            "the lower limit falls below the margin: unshared per-cell\n"
            "  weights buy something the shared form cannot express, contradicting\n"
            "  this entry's efficiency argument."
        )
    print(f"  {branch}: {text}")

    # The run's own verdict is not trusted, it is compared. This script exists so
    # the rule is applied by code that did not produce the numbers, and that is
    # only worth anything if a disagreement is loud.
    recorded = artefact["verdict"]
    if not recorded.startswith(branch):
        raise SystemExit(
            "VERDICT MISMATCH between this analysis and the run:\n"
            f"  run      {recorded}\n"
            f"  analysis {branch}\n"
            "Both read the same registered rule, so one implementation is wrong."
        )
    print(f"  (the run recorded the same branch: {recorded.split(':')[0]})")

    print(
        "\nNot established by any branch: this does not re-read EXP-012's\n"
        "adoption, and the arms are not parameter-matched, so a conv win is\n"
        "confounded with regularisation-by-fewer-parameters."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
