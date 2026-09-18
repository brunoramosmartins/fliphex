"""EXP-013 — the efficient parameterisation of (b).

Registered in ``experiments/registry.md`` on 2026-09-03, before this file
existed, and amended on 2026-09-03 before it ran — see "the secondary was
broken" below. Read the entry first; every constant here is pinned there.

The question
------------
adr-005 adopted a conditioned policy head, in the implementation both the ADR and
EXP-012 record as the inefficient one: ``Linear(32 * n_cells, n_cells * 6)``, as
many unshared maps as there are cells — 43,290 parameters on the 5×3 and 120,150
on the 5×5. ``policy_conv`` already produces a ``(32, n_cols, n_rows)`` map before
its flatten, so a 1×1 convolution from 32 to 6 channels gives per-cell rotation
logits from shared weights in **198 parameters on every board**.

Both arms compute the same score under the same nested normaliser and differ only
in how ``rotation[c, r]`` is produced. The arms are deliberately **not**
parameter-matched: the 218× difference is the treatment.

What this instrument does that EXP-011 and EXP-012 did not
---------------------------------------------------------
**The test is one-sided.** Non-inferiority at δ = 1.7 points, derived rather than
reused: adr-005 adopted a head conceding 3.3 points under a 5.0 tolerance, so
giving back more than the remaining 1.7 leaves the tolerance the adoption was
taken under. The derivation imports the 3.3's own interval [1.88, 4.75].

**Feasibility is recomputed, not assumed.** EXP-012's equivalence gate was
unpassable because its δ equalled its forecast half-width. :func:`feasibility`
recomputes the room from the *observed* spread and the artefact records whether
the gate could have been cleared at all.

**The guard runs after the network change, not before.** The incumbent's twelve
rows are reused rather than retrained, and the guard exists to catch this file's
change to ``az/network.py`` perturbing them. It compares hit vectors
**element-wise**: a mean comparison is not evidence, since two runs can score the
same on different positions. The guard's trained net is then kept and used for
the head-to-head below, so the check costs no extra training.

The secondary was broken and is amended
---------------------------------------
The registration named **final training loss** as a non-solver secondary, to be
compared in direction with the held-out primary, adopting nothing if they
disagreed. Building this exposed two defects, both before any data existed:

1. **Training loss here is not a non-solver quantity.** The targets are optimal
   moves read from the exact solver. A loss against solver labels cannot check a
   solver-selected decision; it is the same evidence in another unit.
2. **Direction agreement between training loss and held-out accuracy is not a
   coherent check.** The entry's own prediction 4 expects the conv arm to fit
   training *worse* (198 parameters against 43,290) while generalising no worse
   — which is the textbook good outcome and which the rule as written would have
   scored as "disagreement, adopt nothing". The registered rule contradicted the
   registered prediction.

The amended secondary is **head-to-head play**: the two arms at seed 0 play a
match, and the winner is decided by the game rather than by agreement with the
solver. That is genuinely outside Axis 1. It costs no extra training because the
guard already trains the incumbent at seed 0, and it fires only on a decisive
result — the conv arm's Wilson interval lying entirely below 50% — so a single
seed pair cannot veto the primary on noise.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch  # noqa: E402

from az.encoding import encode  # noqa: E402
from az.gate import play_match_game  # noqa: E402
from az.network import (  # noqa: E402
    ConditionedHeadNet,
    ConvRotationNet,
    RotationReadout,
    to_tensor,
)
from az.player import SearchPlayer  # noqa: E402
from az.train import make_batch, train_step  # noqa: E402
from fliphex.variant import Arm, Variant  # noqa: E402
from scripts.exp012_conditioned_head import (  # noqa: E402
    BATCH_SIZE,
    EPOCHS,
    LEARNING_RATE,
    PUCT_SIMULATIONS,
    SEED,
    WEIGHT_DECAY,
    optimiser_for,
    random_floor,
    search_scores,
    supervised_scores,
    train_arm,
    verify_ground_truth,
    wilson,
)
from scripts.exp012_followup import draw_sample  # noqa: E402
from solver.checkpoint import Checkpoint  # noqa: E402
from solver.sweep_reader import SweepReader  # noqa: E402

# -- pinned by the registry ---------------------------------------------------

ARM_SEEDS = tuple(range(12))

#: Non-inferiority margin, in points. Derived: adr-005 adopted a head conceding
#: 3.3 points under a 5.0 tolerance, so 5.0 - 3.3 = 1.7 is what a parameterisation
#: may give back before the architecture leaves the tolerance it was adopted
#: under. The 3.3 carries [1.88, 4.75], so the conservative derivation is 0.25 and
#: the optimistic 3.12; 1.7 is the point-estimate derivation and inherits that.
DELTA = 0.017

#: One-sided t(11) at alpha = 0.05.
T_ONE_SIDED = 1.796

#: The largest between-arm sd(differences) measured on this pipeline (EXP-012
#: reported 1.60 at 5 seeds, 1.92 at 12, and 1.95 on its C - A contrast). Used
#: for the forecast printed beside the observed spread.
FORECAST_SD = 0.0195

#: Positions sampled when matching the two arms' initial rotation-logit scale.
SCALE_POSITIONS = 500
SCALE_SEEDS = (0, 1, 2)

#: The amended secondary: head-to-head play at seed 0, outside solver agreement.
MATCH_GAMES = 200
MATCH_SIMULATIONS = 400
MATCH_TEMPERATURE_PLIES = 4
GUARD_ARM = "B_cell"
GUARD_SEED = 0


# -- precondition 1: the reproduction guard, after the network change ---------


def reproduction_guard(variant, board, reader, main, train_samples, heldout):
    """Retrain the incumbent at seed 0 and require an element-wise match.

    EXP-013 reuses EXP-012's ``B_cell`` rows instead of retraining twelve seeds,
    which is only legitimate if this file's change to ``az/network.py`` left them
    alone. A mean comparison would not be evidence: two runs can score 74.8% on
    different positions. The check is positional and it asserts positive
    evidence — the vector exists, is the registered length, and is not constant.

    Returns the trained net as well as the digest, because the head-to-head
    secondary needs an incumbent to play against and this is already it.
    """
    row = next(r for r in main["results"][GUARD_ARM] if r["seed"] == GUARD_SEED)
    expected = [bool(h) for h in row["search"]["hits"]]
    if len(expected) != len(heldout):
        raise SystemExit(f"artefact hit vector is {len(expected)}, not {len(heldout)}")
    if len(set(expected)) < 2:
        raise SystemExit(
            "artefact hit vector is constant; the guard would pass on a broken "
            "pipeline that scored everything or nothing"
        )

    print(
        f"guard: retraining {GUARD_ARM} seed {GUARD_SEED} after the network "
        "change, comparing hits element-wise",
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
            f"REPRODUCTION FAILED: {len(mismatches)} of {len(expected)} positions "
            f"differ (first at index {mismatches[0]}).\n"
            f"  artefact top1 {row['search']['top1']:.4f}, rerun {scores['top1']:.4f}\n"
            "  The change to az/network.py perturbed the incumbent arm. Its rows "
            "may not be reused and it must be retrained in full."
        )
    if abs(history[-1] - row["final_train_loss"]) > 1e-9:
        raise SystemExit(
            f"REPRODUCTION FAILED on training loss: artefact "
            f"{row['final_train_loss']:.10f}, rerun {history[-1]:.10f}"
        )

    import hashlib

    digest = hashlib.sha256(bytes(actual)).hexdigest()
    print(
        f"guard passed in {time.monotonic() - started:.0f}s: "
        f"{len(expected)}/{len(expected)} positions identical, digest {digest[:12]}",
        flush=True,
    )
    return digest, net


# -- precondition 2 is a unit test; see tests/test_az_train.py ----------------
# ``test_the_conv_rotation_normaliser_equals_brute_force`` checks the nested
# closed form against logsumexp over generated moves on three variants and three
# depths. A wrong normaliser does not raise -- it optimises the wrong
# distribution and would land on the treatment arm, keeping the incumbent.


# -- the initialisation match -------------------------------------------------


def rotation_logit_sd(net, planes_batch: torch.Tensor) -> float:
    """Standard deviation of the rotation logits this head emits at init.

    Measured on the *rows*, not the weights: the arms differ in input
    dimensionality (480 features against 32) and default bounds go as
    ``1/sqrt(fan_in)``, so equal weight scales still give unequal logit scales.
    What has to match is the term that enters the score.
    """
    with torch.no_grad():
        _, _, rows, _ = net(planes_batch)
        return float(rows.std())


def measure_rotation_scale(variant: Variant, planes_batch: torch.Tensor) -> dict:
    """The constant putting the conv arm's rotation logits at the incumbent's scale.

    EXP-012's pooled control needed a ``sqrt(n_cells)`` correction for the same
    class of reason, and that entry records the lesson: identical function class
    does not imply identical initial *function*. Scaling the output leaves the
    function class untouched. Measured over several seeds so the constant is a
    property of the architectures rather than of one draw.
    """
    linear, conv = [], []
    for seed in SCALE_SEEDS:
        torch.manual_seed(seed)
        left = ConditionedHeadNet(
            variant.n_cols, variant.n_rows, readout=RotationReadout.CELL
        ).eval()
        torch.manual_seed(seed)
        right = ConvRotationNet(
            variant.n_cols, variant.n_rows, rotation_scale=1.0
        ).eval()
        linear.append(rotation_logit_sd(left, planes_batch))
        conv.append(rotation_logit_sd(right, planes_batch))

    linear_sd = statistics.fmean(linear)
    conv_sd = statistics.fmean(conv)
    if conv_sd <= 0.0:
        raise SystemExit("the conv arm's rotation logits are constant at init")
    return {
        "linear_sd": linear_sd,
        "conv_sd_unscaled": conv_sd,
        "scale": linear_sd / conv_sd,
        "per_seed_linear": linear,
        "per_seed_conv": conv,
        "positions": int(planes_batch.shape[0]),
        "seeds": list(SCALE_SEEDS),
    }


# -- training -----------------------------------------------------------------


def train_conv_arm(variant: Variant, samples, seed: int, scale: float):
    """Train the convolutional arm. Same schedule and batch order as EXP-012."""
    torch.manual_seed(seed)
    net = ConvRotationNet(variant.n_cols, variant.n_rows, rotation_scale=scale)
    optimiser = optimiser_for(net)
    order = random.Random(seed)
    history = []
    for _ in range(EPOCHS):
        shuffled = list(samples)
        order.shuffle(shuffled)
        losses = []
        for start in range(0, len(shuffled), BATCH_SIZE):
            batch = make_batch(
                shuffled[start : start + BATCH_SIZE], variant.n_cols, variant.n_rows
            )
            losses.append(train_step(net, optimiser, batch)["policy"])
        history.append(statistics.fmean(losses))
    net.eval()
    return net, history


# -- the incumbent's rows, reused rather than retrained -----------------------


def linear_rows(main: dict, extension: dict, heldout_size: int) -> list[dict]:
    """EXP-012's ``B_cell`` at seeds 0-11, assembled from its two artefacts.

    Seeds 0-4 are in the main run, 5-11 in the extension's ``new_rows``. The
    reproduction guard licenses using them; this assembles them and checks the
    seed set is exactly the registered one.
    """
    rows = list(main["results"]["B_cell"]) + list(extension["new_rows"]["B_cell"])
    seeds = [row["seed"] for row in rows]
    if seeds != list(ARM_SEEDS):
        raise SystemExit(
            f"the incumbent's seeds are {seeds}, expected {list(ARM_SEEDS)}; "
            "the reuse is not the registered one"
        )
    for row in rows:
        if len(row["search"]["hits"]) != heldout_size:
            raise SystemExit(
                f"seed {row['seed']}: hit vector is {len(row['search']['hits'])}, "
                f"not the {heldout_size} positions this run holds out -- the "
                "reused rows were measured on a different sample"
            )
    return rows


# -- the amended secondary: head-to-head, outside solver agreement ------------


def head_to_head(variant: Variant, conv_net, linear_net) -> dict:
    """Play the two arms against each other and let the game decide.

    This is the anti-circularity check the registration wanted and mis-specified.
    Training loss is computed against solver labels, so it cannot check a
    solver-selected decision; a match outcome can.

    Seats alternate, so the first-player advantage falls equally on both. It is
    one seed pair and therefore weak, which is why it is used only as a veto and
    only when decisive: the check fires when the conv arm's Wilson interval lies
    entirely below 50%.
    """
    conv_wins = 0
    for game in range(MATCH_GAMES):
        challenger = SearchPlayer(
            conv_net,
            simulations=MATCH_SIMULATIONS,
            seed=SEED * 1_000_003 + game,
            temperature_plies=MATCH_TEMPERATURE_PLIES,
        )
        champion = SearchPlayer(
            linear_net,
            simulations=MATCH_SIMULATIONS,
            seed=SEED * 2_000_003 + game,
            temperature_plies=MATCH_TEMPERATURE_PLIES,
        )
        conv_wins += play_match_game(
            variant, challenger, champion, challenger_first=game % 2 == 0
        )
        if (game + 1) % 25 == 0:
            print(
                f"    match {game + 1}/{MATCH_GAMES}: conv {conv_wins}",
                flush=True,
            )

    low, high = wilson(conv_wins, MATCH_GAMES)
    return {
        "games": MATCH_GAMES,
        "conv_wins": conv_wins,
        "conv_rate": conv_wins / MATCH_GAMES,
        "ci": [low, high],
        "decisively_against_conv": high < 0.5,
        "seed_pair": GUARD_SEED,
        "note": (
            "One seed pair, used as a veto and only when decisive. It replaces "
            "the registration's training-loss secondary, which was not a "
            "non-solver quantity and whose direction rule contradicted the "
            "entry's own prediction 4."
        ),
    }


# -- statistics ---------------------------------------------------------------


def non_inferiority(baseline: list[float], arm: list[float], delta: float) -> dict:
    """One-sided test of ``arm - baseline > -delta``.

    The hypothesis is directional: the convolutional form must not be materially
    *worse*. An equivalence test would spend power ruling out the arm being
    better, which is an outcome nobody needs protection from.
    """
    diffs = [x - y for y, x in zip(baseline, arm, strict=True)]
    n = len(diffs)
    if n < len(ARM_SEEDS):
        raise SystemExit(
            f"the rule is an interval on {len(ARM_SEEDS)} seed means and this run "
            f"has {n}; below the registered count it is not the registered rule"
        )
    mean = statistics.fmean(diffs)
    sd = statistics.stdev(diffs)
    half = T_ONE_SIDED * sd / math.sqrt(n)
    return {
        "difference": mean,
        "lower_limit": mean - half,
        "half_width": half,
        "sd_differences": sd,
        "n": n,
        "delta": delta,
        # A zero spread collapses the interval onto its point estimate and would
        # clear any margin with apparent certainty. EXP-012 shipped this defect
        # and had to repair it after a smoke run; it is refused here.
        "degenerate": half <= 0.0,
        "passed": half > 0.0 and (mean - half) > -delta,
    }


def feasibility(sd: float, n: int, delta: float) -> dict:
    """Could this test have passed at all, at this spread?

    EXP-012's validity gate was unpassable: its delta equalled its forecast
    half-width, so no point estimate could clear it. The registry now carries a
    standing rule that no such test may be registered without tabulating the
    *room* — delta minus the half-width — and this recomputes it from what was
    observed rather than what was forecast.
    """
    half = T_ONE_SIDED * sd / math.sqrt(n)
    return {
        "sd": sd,
        "half_width": half,
        "delta": delta,
        "room": delta - half,
        "feasible": delta > half,
    }


def clustered_bootstrap(
    baseline_hits: list[list[bool]],
    arm_hits: list[list[bool]],
    resamples: int = 10_000,
    seed: int = SEED,
) -> dict:
    """One-sided lower limit from a bootstrap clustered on the held-out positions.

    The registry requires both intervals and the wider quoted. EXP-012's
    instrument omitted this and it had to be recovered offline; it is written
    here.
    """
    n_positions = len(baseline_hits[0])
    rng = random.Random(seed)
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


def verdict(primary: dict, match: dict) -> str:
    """The registered branches, read on the one-sided interval."""
    if primary["degenerate"]:
        return (
            "REFUSED: zero spread across seeds collapses the interval onto its "
            "point estimate; any margin would clear with apparent certainty"
        )
    if match["decisively_against_conv"]:
        return (
            "ADOPT NOTHING: the solver-agreement primary and head-to-head play "
            "disagree decisively. The disagreement is the finding"
        )
    if primary["passed"]:
        return (
            "ADOPT the convolutional form: non-inferior at the registered "
            "margin, at 218x fewer parameters in the component the decision is "
            "about. adr-005 is amended again"
        )
    return (
        "KEEP the adopted linear form: the lower limit falls below the margin. "
        "Unshared per-cell weights buy something the shared form cannot express, "
        "which contradicts the efficiency argument this entry was built on"
    )


# -- the run ------------------------------------------------------------------


def run(args) -> dict:
    started = time.monotonic()
    variant = Variant(5, 3, Arm("h2"))
    board = variant.board()
    ground_truth = verify_ground_truth(Path(args.database))
    reader = SweepReader(variant, Checkpoint(Path(args.checkpoint) / variant.name))

    main = json.loads(Path(args.main).read_text())
    extension = json.loads(Path(args.extension).read_text())
    for name, artefact in (("main", main), ("extension", extension)):
        if artefact.get("experiment") != "EXP-012":
            raise SystemExit(f"the {name} artefact is not EXP-012")

    train_samples, heldout = draw_sample(reader, board)
    heldout_layers = [state.ply() for state in heldout]
    print(f"drew train {len(train_samples)}, held out {len(heldout)}", flush=True)

    guard_digest, incumbent_net = reproduction_guard(
        variant, board, reader, main, train_samples, heldout
    )
    incumbent = linear_rows(main, extension, len(heldout))
    print(f"incumbent rows reused: seeds {[r['seed'] for r in incumbent]}", flush=True)

    planes_batch = to_tensor(
        [encode(board, state) for state in heldout[:SCALE_POSITIONS]],
        variant.n_cols,
        variant.n_rows,
    )
    scale = measure_rotation_scale(variant, planes_batch)
    print(
        f"rotation scale: incumbent sd {scale['linear_sd']:.5f}, "
        f"conv sd {scale['conv_sd_unscaled']:.5f} -> scale {scale['scale']:.5f}",
        flush=True,
    )

    conv_rows, conv_nets = [], {}
    for seed in ARM_SEEDS:
        cell_started = time.monotonic()
        net, history = train_conv_arm(variant, train_samples, seed, scale["scale"])
        scores = search_scores(net, variant, board, heldout, reader, seed)
        sup = supervised_scores(net, variant, board, heldout, reader)
        if seed == GUARD_SEED:
            conv_nets[seed] = net
        conv_rows.append(
            {
                "seed": seed,
                "parameters": net.count_parameters(),
                "final_train_loss": history[-1],
                "last_five_improvement": history[-5] - history[-1],
                "supervised": {"top1": sup["top1"]},
                "search": {"top1": scores["top1"], "hits": scores["hits"]},
            }
        )
        print(
            f"  V_conv seed {seed}: search {scores['top1']:.1%}  "
            f"supervised {sup['top1']:.1%}  loss {history[-1]:.4f}  "
            f"({time.monotonic() - cell_started:.0f}s)",
            flush=True,
        )

    print(
        f"head-to-head at seed {GUARD_SEED}: {MATCH_GAMES} games, seats alternating",
        flush=True,
    )
    match = head_to_head(variant, conv_nets[GUARD_SEED], incumbent_net)
    print(
        f"  conv {match['conv_wins']}/{MATCH_GAMES} = {match['conv_rate']:.1%} "
        f"[{match['ci'][0]:.1%}, {match['ci'][1]:.1%}]",
        flush=True,
    )

    floor = random_floor(board, reader, heldout, random.Random(SEED + 1))
    return summarise(
        incumbent,
        conv_rows,
        scale,
        guard_digest,
        match,
        floor,
        heldout_layers,
        ground_truth,
        time.monotonic() - started,
    )


def parity(rows, heldout_layers) -> dict:
    odd = even = odd_n = even_n = 0
    for row in rows:
        for hit, layer in zip(row["search"]["hits"], heldout_layers, strict=True):
            if layer % 2:
                odd += hit
                odd_n += 1
            else:
                even += hit
                even_n += 1
    return {
        "odd": odd / odd_n if odd_n else None,
        "even": even / even_n if even_n else None,
    }


def summarise(
    incumbent,
    conv_rows,
    scale,
    guard_digest,
    match,
    floor,
    heldout_layers,
    ground_truth,
    elapsed,
) -> dict:
    left = [r["search"]["top1"] for r in incumbent]
    right = [r["search"]["top1"] for r in conv_rows]

    primary = non_inferiority(left, right, DELTA)
    boot = clustered_bootstrap(
        [[bool(h) for h in r["search"]["hits"]] for r in incumbent],
        [[bool(h) for h in r["search"]["hits"]] for r in conv_rows],
    )
    n_pooled = len(ARM_SEEDS) * len(incumbent[0]["search"]["hits"])
    pooled = {
        "L_linear": sum(sum(r["search"]["hits"]) for r in incumbent),
        "V_conv": sum(sum(r["search"]["hits"]) for r in conv_rows),
    }

    return {
        "experiment": "EXP-013",
        "registered": "experiments/registry.md",
        "variant": "5x3-h2",
        "ground_truth_v5": ground_truth["verification"]["V5_checksum_sha256"],
        "arm_seeds": list(ARM_SEEDS),
        "schedule": {
            "epochs": EPOCHS,
            "batch_size": BATCH_SIZE,
            "learning_rate": LEARNING_RATE,
            "weight_decay": WEIGHT_DECAY,
            "rotation_head_weight_decay": 0.0,
        },
        "puct_simulations": PUCT_SIMULATIONS,
        "reproduction_guard": {
            "arm": GUARD_ARM,
            "seed": GUARD_SEED,
            "digest": guard_digest,
        },
        "rotation_scale": scale,
        "random_floor": floor,
        "arm_means": {
            "L_linear": statistics.fmean(left),
            "V_conv": statistics.fmean(right),
        },
        "wilson_pooled": {
            arm: list(wilson(hits, n_pooled)) for arm, hits in pooled.items()
        },
        "primary_V_minus_L": primary,
        "clustered_bootstrap": boot,
        "wider_interval": (
            "clustered bootstrap"
            if boot["half_width"] > primary["half_width"]
            else "seed means"
        ),
        "feasibility": {
            "observed": feasibility(primary["sd_differences"], len(ARM_SEEDS), DELTA),
            "forecast": feasibility(FORECAST_SD, len(ARM_SEEDS), DELTA),
        },
        "head_to_head": match,
        "train_loss": {
            "L_linear": statistics.fmean(r["final_train_loss"] for r in incumbent),
            "V_conv": statistics.fmean(r["final_train_loss"] for r in conv_rows),
            "note": (
                "Reported as a diagnostic, never as a gate. Prediction 4 expects "
                "the conv arm to fit training worse while generalising no worse; "
                "that pair is the clean statement of the entry, and a rule that "
                "read it as disagreement would have contradicted the prediction."
            ),
        },
        "layer_parity": {
            "L_linear": parity(incumbent, heldout_layers),
            "V_conv": parity(conv_rows, heldout_layers),
        },
        "verdict": verdict(primary, match),
        "does_not_reread": (
            "This entry does not re-read EXP-012's adoption. That rule permitted "
            "one extension and it is spent. A materially better conv form means "
            "the 3.3-point gap to the flat head was measured against a "
            "parameterisation that is no longer shipped, and a fresh adoption "
            "entry is required."
        ),
        "not_parameter_matched": (
            "The arms are deliberately not parameter-matched -- the 218x "
            "difference is the treatment. A conv win is therefore confounded "
            "with regularisation-by-fewer-parameters, and this entry cannot "
            "separate 'sharing is the right inductive bias' from '43,290 "
            "parameters was too many'."
        ),
        "elapsed_seconds": elapsed,
        "results": {"L_linear": incumbent, "V_conv": conv_rows},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="data/subgame-solutions/5x3-h2.json")
    parser.add_argument("--checkpoint", default="data/checkpoints")
    parser.add_argument("--main", default="results/exp012-conditioned-head-5x3-h2.json")
    parser.add_argument("--extension", default="results/exp012-extension-5x3-h2.json")
    parser.add_argument("--out", default="results/exp013-conv-rotation-5x3-h2.json")
    args = parser.parse_args()

    out = Path(args.out)
    if out.exists():
        raise SystemExit(
            f"{out} already exists. Twelve seeds and no extension is the "
            "registered design; re-running and keeping the better read is "
            "optional stopping."
        )

    summary = run(args)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))

    print()
    for arm, mean in summary["arm_means"].items():
        print(f"  {arm:>9} {mean:.1%}")
    print(f"  {'floor':>9} {summary['random_floor']:.1%}")
    print()
    p = summary["primary_V_minus_L"]
    print(
        f"V - L  {p['difference']:+.2%}  lower limit {p['lower_limit']:+.2%}  "
        f"vs margin {-DELTA:+.2%}"
    )
    obs = summary["feasibility"]["observed"]
    print(
        f"feasibility  half-width {obs['half_width']:.2%}, room {obs['room']:+.2%}, "
        f"{'passable' if obs['feasible'] else 'UNPASSABLE'}"
    )
    print(f"wider interval  {summary['wider_interval']}")
    print(
        f"head-to-head  conv {summary['head_to_head']['conv_rate']:.1%} "
        f"[{summary['head_to_head']['ci'][0]:.1%}, "
        f"{summary['head_to_head']['ci'][1]:.1%}]"
    )
    print(
        f"train loss  L {summary['train_loss']['L_linear']:.4f}  "
        f"V {summary['train_loss']['V_conv']:.4f}  (diagnostic, not a gate)"
    )
    print(f"VERDICT  {summary['verdict']}")
    print(f"written  {args.out}  ({summary['elapsed_seconds']:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
