"""EXP-011 — is the factored policy head too costly in the pipeline? (risk R5)

Registered in ``experiments/registry.md`` on 2026-08-30, revised the same day
after red-team, and amended 2026-08-31 when the network as built turned out not
to have the logit counts the arms named. Read the entry before reading this file;
every constant below is pinned there.

What this measures, and what it deliberately does not
-----------------------------------------------------
The architecture record lists three mitigations **in order**, and the first is
"rely on MCTS to correct the prior, which is exactly what MCTS is for". A purely
supervised comparison contains no MCTS, so it cannot speak to that defence while
still being empowered to fire the second. The **primary** metric is therefore
top-1 optimality *after 400 PUCT simulations* with each head supplying the prior.
The supervised numbers are secondary and reported beside it.

Both arms span the same action space
------------------------------------
The flat head is ``n_cells x 13 x 6`` — the full triple space — not the tiles this
deck happens to hold. Sizing it to the deck would give it a fact the factored arm
is not given, biasing the comparison toward the arm whose win amends the
architecture.

The unit is the position, not the action label
----------------------------------------------
Targets and metrics aggregate aliased actions. A target defined over optimal
*moves* would hand up to six times the mass to a position reachable by six
rotations, so the flat head would be scored partly on reproducing alias
multiplicity — the very phenomenon EXP-010 exists to remove.

Statistics are duplicated from EXP-010's script rather than shared with it. A
finished experiment's script is the record of what was run; editing it later
would make the code no longer the code that produced the artefact.
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
from az.mcts import (  # noqa: E402
    MCTS,
    ExpansionMode,
    best_move,
    group_by_position,
)
from az.network import (  # noqa: E402
    FlatHeadNet,
    FlatNetworkEvaluator,
    FlipHexNet,
    NetworkEvaluator,
    flat_masked_log_policy,
    masked_log_policy,
    to_tensor,
)
from az.replay_buffer import Sample, pack_policy  # noqa: E402
from az.train import make_batch, train_step  # noqa: E402
from fliphex.moves import apply_move, legal_moves  # noqa: E402
from fliphex.piece import N_SLOTS  # noqa: E402
from fliphex.state import TILES  # noqa: E402
from fliphex.variant import Arm, Variant  # noqa: E402
from solver.checkpoint import Checkpoint  # noqa: E402
from solver.retrograde import SLOT_LOSS, SLOT_WIN  # noqa: E402
from solver.sweep_reader import SweepReader  # noqa: E402

# -- everything below is pinned by the registry -------------------------------

EXPECTED_V5 = "51192b4d403ac1cb45c22d92ce58bab215843f457f245e7aca6d18744f8a3f43"

assert N_SLOTS == 6, "the flat head's index arithmetic assumes six rotation slots"

SEED = 23
LAYERS = tuple(range(5, 15))
PER_LAYER = 250
TRAIN_SIZE = 2000
HELDOUT_SIZE = 500
ARM_SEEDS = (0, 1, 2, 3, 4)
PUCT_SIMULATIONS = 400
MARGIN = 0.05

#: Not pinned by the registry, which requires only that the arms match. Recorded
#: here and in the artefact so the choice is inspectable.
EPOCHS = 40
BATCH_SIZE = 64
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-4


# -- provenance ---------------------------------------------------------------


def verify_ground_truth(path: Path) -> dict:
    """Refuse to run against anything but the registered artefact."""
    artefact = json.loads(path.read_text())
    digest = artefact.get("verification", {}).get("V5_checksum_sha256")
    if digest != EXPECTED_V5:
        raise SystemExit(
            f"digest mismatch: {path} reports {digest}, registry pins {EXPECTED_V5}"
        )
    if artefact.get("termination") != "exhausted":
        raise SystemExit(
            f"R1: {path} terminated as {artefact.get('termination')!r}, not "
            f"'exhausted'; a truncated search may not ground an axis"
        )
    return artefact


# -- statistics ---------------------------------------------------------------


def wilson(hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval. Never report a bare proportion."""
    if n == 0:
        return 0.0, 0.0
    p = hits / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def mcnemar(a_hits: list[bool], b_hits: list[bool]) -> dict:
    """Paired comparison, signed so that ``b`` beating ``a`` is positive."""
    a_only = sum(1 for a, b in zip(a_hits, b_hits, strict=True) if a and not b)
    b_only = sum(1 for a, b in zip(a_hits, b_hits, strict=True) if b and not a)
    n = len(a_hits)
    discordant = a_only + b_only
    difference = (b_only - a_only) / n if n else 0.0
    if discordant == 0:
        return {
            "a_only": 0,
            "b_only": 0,
            "discordant": 0,
            "difference": 0.0,
            "ci_low": 0.0,
            "ci_high": 0.0,
        }
    half = 1.96 * math.sqrt(discordant) / n
    return {
        "a_only": a_only,
        "b_only": b_only,
        "discordant": discordant,
        "difference": difference,
        "ci_low": difference - half,
        "ci_high": difference + half,
    }


def paired_t(a: list[float], b: list[float]) -> dict:
    """Paired t on seed means. Returns the difference ``b - a`` and its interval."""
    diffs = [x - y for y, x in zip(a, b, strict=True)]
    n = len(diffs)
    mean = statistics.fmean(diffs)
    if n < 2:
        return {"difference": mean, "ci_low": mean, "ci_high": mean, "n": n}
    spread = statistics.stdev(diffs) / math.sqrt(n)
    # t(4) two-sided 95% = 2.776; the registered design is 5 seeds.
    critical = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776}.get(n, 1.96)
    return {
        "difference": mean,
        "ci_low": mean - critical * spread,
        "ci_high": mean + critical * spread,
        "n": n,
    }


# -- the sample ---------------------------------------------------------------


def draw_layer(reader: SweepReader, t: int, count: int, rng: random.Random):
    """Draw ``count`` distinct WIN positions from layer ``t`` by rejection."""
    index = reader.index[t]
    size = index.size
    layer = reader.layer(t)
    seen: set[int] = set()
    drawn = []
    attempts = 0
    while len(drawn) < count:
        attempts += 1
        if attempts > count * 5000:
            raise SystemExit(f"layer {t}: could not draw {count} WIN positions")
        i = rng.randrange(size)
        if i in seen:
            continue
        seen.add(i)
        if reader.sweep.get(layer, i) != SLOT_WIN:
            continue
        drawn.append(index.decode(i))
    return drawn


def optimal_classes(board, reader: SweepReader, state):
    """Group the legal moves by resulting position and mark the optimal ones.

    Returns ``(classes, optimal)`` where ``classes`` is the list of alias groups
    and ``optimal`` holds the indices of those whose resulting position the
    database calls a loss for the opponent.
    """
    moves = legal_moves(board, state)
    classes = group_by_position(board, state, moves)
    optimal = [
        i
        for i, group in enumerate(classes)
        if reader.slot(apply_move(board, state, group[0])) == SLOT_LOSS
    ]
    return classes, optimal


def build_sample(board, reader: SweepReader, state) -> Sample | None:
    """Supervised target: uniform mass over optimal **positions**.

    Mass ``1/k`` goes to each of the ``k`` optimal position classes and is then
    split evenly among that class's aliased action labels, so the distribution is
    position-level while still living in action space where the heads do.

    Returns ``None`` if the position has no optimal move, which cannot happen for
    a WIN position and is checked rather than assumed.
    """
    classes, optimal = optimal_classes(board, reader, state)
    if not optimal:
        return None
    pi: dict = {}
    share = 1.0 / len(optimal)
    for i in optimal:
        group = classes[i]
        for move in group:
            pi[move] = share / len(group)
    moves, probs = pack_policy(pi)
    return Sample(planes=encode(board, state), moves=moves, probs=probs, value=1.0)


def rotation_inertness(board, state) -> tuple[int, int, int, int]:
    """How often rotation does not change the resulting position.

    A ``(cell, tile)`` pair counts as **inert** when all of that tile's distinct
    rotations reach the *same* resulting position — that is, when the pair forms
    exactly one alias class.

    Returns ``(inert, total, inert_multi, total_multi)``, the second pair
    excluding tiles whose rotation orbit is 1. For those, "rotation changes
    nothing" is vacuously true **by orbit rather than by the inertness mechanism
    the architecture record describes**, so including them inflates the headline
    with a definitional artefact. The multi-orbit figure is the one that supports
    the claim; both are reported so nobody recomputes this later and gets a
    different answer.
    """
    classes = group_by_position(board, state, legal_moves(board, state))
    class_count: dict[tuple[int, int], int] = {}
    for group in classes:
        key = (group[0].cell, group[0].tile)
        class_count[key] = class_count.get(key, 0) + 1

    inert = total = inert_multi = total_multi = 0
    for (_, tile), count in class_count.items():
        is_inert = count == 1
        total += 1
        inert += is_inert
        if len(TILES[tile].distinct_rotations()) > 1:
            total_multi += 1
            inert_multi += is_inert
    return inert, total, inert_multi, total_multi


# -- the arms -----------------------------------------------------------------


def train_arm(variant: Variant, flat: bool, samples: list[Sample], seed: int):
    """Train one arm. Identical schedule, batch order and optimiser both ways."""
    torch.manual_seed(seed)
    net = (
        FlatHeadNet(variant.n_cols, variant.n_rows)
        if flat
        else FlipHexNet(variant.n_cols, variant.n_rows)
    )
    optimiser = torch.optim.Adam(
        net.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
    )
    order = random.Random(seed)
    history = []
    for epoch in range(EPOCHS):
        shuffled = list(samples)
        order.shuffle(shuffled)
        losses = []
        for start in range(0, len(shuffled), BATCH_SIZE):
            batch = make_batch(
                shuffled[start : start + BATCH_SIZE], variant.n_cols, variant.n_rows
            )
            losses.append(train_step(net, optimiser, batch)["policy"])
        history.append({"epoch": epoch, "policy": statistics.fmean(losses)})
    net.eval()
    return net, history


def supervised_scores(net, variant: Variant, board, states, reader) -> dict:
    """Top-1 agreement at the position level, and cross-entropy against the target."""
    flat = isinstance(net, FlatHeadNet)
    hits, entropies = [], []
    with torch.no_grad():
        for state in states:
            classes, optimal = optimal_classes(board, reader, state)
            moves = [m for group in classes for m in group]
            x = to_tensor(encode(board, state), variant.n_cols, variant.n_rows)
            if flat:
                logits, _ = net(x)
                log_p = flat_masked_log_policy(logits[0], moves)
            else:
                cell, tile, rotation, _ = net(x)
                log_p = masked_log_policy(cell[0], tile[0], rotation[0], moves)

            # Aggregate to positions before scoring: the unit is the position.
            per_class, offset = [], 0
            for group in classes:
                per_class.append(
                    torch.logsumexp(log_p[offset : offset + len(group)], dim=0)
                )
                offset += len(group)
            stacked = torch.stack(per_class)
            hits.append(int(stacked.argmax()) in optimal)

            target = torch.zeros(len(classes))
            for i in optimal:
                target[i] = 1.0 / len(optimal)
            entropies.append(float(-(target * stacked).sum()))

    low, high = wilson(sum(hits), len(hits))
    return {
        "top1": sum(hits) / len(hits),
        "ci": [low, high],
        "cross_entropy": statistics.fmean(entropies),
        "hits": hits,
    }


def search_scores(net, variant: Variant, board, states, reader, seed: int) -> dict:
    """Primary metric: top-1 optimality after PUCT, with the head as prior."""
    flat = isinstance(net, FlatHeadNet)
    hits = []
    for offset, state in enumerate(states):
        evaluator = (
            FlatNetworkEvaluator(net, board) if flat else NetworkEvaluator(net, board)
        )
        search = MCTS(
            board,
            mode=ExpansionMode.POSITION,
            prior=evaluator.prior,
            evaluate=evaluator.evaluate,
            dirichlet_weight=0.0,
            seed=seed * 100_003 + offset,
        )
        root = search.run(state, PUCT_SIMULATIONS)
        chosen = best_move(root)
        hits.append(reader.slot(apply_move(board, state, chosen)) == SLOT_LOSS)

    low, high = wilson(sum(hits), len(hits))
    return {"top1": sum(hits) / len(hits), "ci": [low, high], "hits": hits}


def random_floor(board, reader, states, rng: random.Random) -> float:
    """What a uniform-random legal move scores, per the registered design."""
    hits = 0
    for state in states:
        move = rng.choice(legal_moves(board, state))
        hits += reader.slot(apply_move(board, state, move)) == SLOT_LOSS
    return hits / len(states)


# -- the run ------------------------------------------------------------------


def run(args) -> dict:
    started = time.time()
    variant = Variant(5, 3, Arm("h2"))
    board = variant.board()
    artefact = verify_ground_truth(Path(args.database))
    reader = SweepReader(variant, Checkpoint(Path(args.checkpoint) / variant.name))

    rng = random.Random(SEED)
    states, layer_of = [], []
    for t in LAYERS:
        for state in draw_layer(reader, t, args.per_layer, rng):
            states.append(state)
            layer_of.append(t)

    rng.shuffle(states)
    train_states = states[: args.train_size]
    heldout_states = states[args.train_size : args.train_size + args.heldout_size]

    print(f"drew {len(states)} WIN positions over layers {LAYERS[0]}..{LAYERS[-1]}")
    print(f"train {len(train_states)}  held-out {len(heldout_states)}", flush=True)

    # -- the number that needs no training ------------------------------------
    inert = total = inert_multi = total_multi = 0
    for state in states:
        a, b, c, d = rotation_inertness(board, state)
        inert += a
        total += b
        inert_multi += c
        total_multi += d
    inertness = {
        "all_tiles": inert / total,
        "multi_orbit_tiles_only": inert_multi / total_multi,
        "pairs": total,
        "pairs_multi_orbit": total_multi,
    }
    print(
        f"rotation inert on {inertness['all_tiles']:.1%} of (cell, tile) pairs; "
        f"{inertness['multi_orbit_tiles_only']:.1%} excluding single-orbit tiles",
        flush=True,
    )

    train_samples = []
    for state in train_states:
        sample = build_sample(board, reader, state)
        if sample is None:
            raise SystemExit("a WIN position with no optimal move: ground truth is bad")
        train_samples.append(sample)

    results = {"factored": [], "flat": []}
    for arm, flat in (("factored", False), ("flat", True)):
        for seed in ARM_SEEDS[: args.seeds]:
            net, history = train_arm(variant, flat, train_samples, seed)
            supervised = supervised_scores(net, variant, board, heldout_states, reader)
            search = search_scores(
                net, variant, board, heldout_states, reader, seed=seed
            )
            results[arm].append(
                {
                    "seed": seed,
                    "parameters": net.count_parameters(),
                    "final_train_policy_loss": history[-1]["policy"],
                    "supervised": supervised,
                    "search": search,
                }
            )
            print(
                f"  {arm:>8} seed {seed}: search {search['top1']:.1%} "
                f"[{search['ci'][0]:.1%}, {search['ci'][1]:.1%}]  "
                f"supervised {supervised['top1']:.1%}  "
                f"xent {supervised['cross_entropy']:.4f}",
                flush=True,
            )

    floor = random_floor(board, reader, heldout_states, random.Random(SEED + 1))
    return summarise(results, inertness, floor, artefact, args, time.time() - started)


def summarise(results, inertness, floor, artefact, args, elapsed) -> dict:
    factored = [row["search"]["top1"] for row in results["factored"]]
    flat = [row["search"]["top1"] for row in results["flat"]]

    seed_spread = max(
        statistics.stdev(factored) if len(factored) > 1 else 0.0,
        statistics.stdev(flat) if len(flat) > 1 else 0.0,
    )
    gap = statistics.fmean(flat) - statistics.fmean(factored)

    # The decision rule, applied rather than described.
    #
    # It is *refused* below the registered seed count. The rule compares the gap
    # against the between-seed spread, and with one seed that spread is
    # undefined rather than zero -- computing it as zero makes any gap look
    # decisive, so a smoke run would return "register fallback (b)": a verdict
    # to amend the architecture, from one training run.
    if len(factored) < len(ARM_SEEDS):
        verdict = (
            f"NOT APPLICABLE: the rule needs {len(ARM_SEEDS)} seeds per arm and "
            f"this run has {len(factored)}; the between-seed spread is undefined"
        )
    elif abs(gap) <= MARGIN and abs(gap) <= seed_spread:
        verdict = "assumption accepted for v1; the architecture record stands"
    elif gap > MARGIN and gap > seed_spread:
        verdict = "mitigation (a) failed on its own terms; register fallback (b)"
    elif gap > MARGIN:
        verdict = "gap exceeds the margin but not the seed spread: not a result"
    else:
        verdict = "assumption accepted for v1; the architecture record stands"

    paired = mcnemar(
        [h for row in results["factored"] for h in row["supervised"]["hits"]],
        [h for row in results["flat"] for h in row["supervised"]["hits"]],
    )

    return {
        "experiment": "EXP-011",
        "registered": "experiments/registry.md",
        "variant": "5x3-h2",
        "ground_truth_v5": EXPECTED_V5,
        "ground_truth_value": artefact.get("value"),
        "seed": SEED,
        "layers": list(LAYERS),
        "per_layer": args.per_layer,
        "train_size": args.train_size,
        "heldout_size": args.heldout_size,
        "arm_seeds": list(ARM_SEEDS[: args.seeds]),
        "schedule": {
            "epochs": EPOCHS,
            "batch_size": BATCH_SIZE,
            "learning_rate": LEARNING_RATE,
            "weight_decay": WEIGHT_DECAY,
        },
        "puct_simulations": PUCT_SIMULATIONS,
        "margin": MARGIN,
        "rotation_inertness": inertness,
        "random_floor": floor,
        "primary": {
            "factored_mean": statistics.fmean(factored),
            "flat_mean": statistics.fmean(flat),
            "gap_flat_minus_factored": gap,
            "between_seed_spread": seed_spread,
            "per_seed": {"factored": factored, "flat": flat},
            "paired_t": paired_t(factored, flat),
        },
        "secondary_supervised_mcnemar": paired,
        "verdict": verdict,
        "elapsed_seconds": elapsed,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="data/subgame-solutions/5x3-h2.json")
    parser.add_argument("--checkpoint", default="data/checkpoints")
    parser.add_argument("--per-layer", type=int, default=PER_LAYER)
    parser.add_argument("--train-size", type=int, default=TRAIN_SIZE)
    parser.add_argument("--heldout-size", type=int, default=HELDOUT_SIZE)
    parser.add_argument("--seeds", type=int, default=len(ARM_SEEDS))
    parser.add_argument("--out", default="results/exp011-factored-head-5x3-h2.json")
    args = parser.parse_args()

    summary = run(args)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(summary, indent=2))

    print()
    print(f"factored {summary['primary']['factored_mean']:.1%}")
    print(f"flat     {summary['primary']['flat_mean']:.1%}")
    print(f"gap      {summary['primary']['gap_flat_minus_factored']:+.1%}")
    print(f"spread   {summary['primary']['between_seed_spread']:.1%}")
    print(f"floor    {summary['random_floor']:.1%}")
    print(f"verdict  {summary['verdict']}")
    print(f"written  {args.out}  ({summary['elapsed_seconds']:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
