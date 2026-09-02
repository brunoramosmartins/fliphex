"""EXP-012 — fallback (b), and whether the cell is what rotation depends on.

Registered in ``experiments/registry.md`` on 2026-09-01 and revised twice after
`experiment-redteam`, both times before this file existed. Read the entry first;
every constant here is pinned there.

What this does and does not ask
-------------------------------
EXP-011 could not separate "cell, tile and rotation are not conditionally
independent" from "34 logits is not enough capacity", and EXP-012 establishes
that **no head-factorisation experiment can**: relaxing the factorisation *is*
adding output width, so the two are one axis. The question is therefore the one
adr-005 actually asserts — **"the best rotation depends heavily on the cell"** —
which is testable at fixed capacity.

Arms B, C and E share one rotation tensor and differ only in the index used to
read a row: by cell, pooled, and by tile. They are identical in parameter count
and tensor shape. A is the incumbent factored head; D is the flat fallback.

The design leans toward its own predictions
-------------------------------------------
Three forces push the mechanism contrasts toward zero even if the mechanism is
real: B's rotation row for a cell gets gradient only when that cell is empty
(~37% of positions against the pooled arm's 100%), B has 15 live rows to fit
against E's 8, and Bonferroni widens the intervals. The frozen-tower condition
removes a fourth. **A null is therefore reported as "not detected", never as
"absent"**, and per-arm training loss is reported beside the held-out primary,
because that is what distinguishes "no mechanism" from "not enough data".

Statistics are duplicated from EXP-011's script rather than shared with it. A
finished experiment's script is the record of what was run.
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
from az.mcts import MCTS, ExpansionMode, best_move, group_by_position  # noqa: E402
from az.network import (  # noqa: E402
    ConditionedHeadNet,
    FlatHeadNet,
    FlipHexNet,
    NetworkEvaluator,
    RotationReadout,
    flat_masked_log_policy,
    masked_log_policy,
    to_tensor,
)
from az.replay_buffer import Sample, pack_policy  # noqa: E402
from az.train import make_batch, train_step  # noqa: E402
from fliphex.moves import apply_move, legal_moves  # noqa: E402
from fliphex.variant import Arm, Variant  # noqa: E402
from solver.checkpoint import Checkpoint  # noqa: E402
from solver.retrograde import SLOT_LOSS, SLOT_WIN  # noqa: E402
from solver.sweep_reader import SweepReader  # noqa: E402

# -- pinned by the registry ---------------------------------------------------

EXPECTED_V5 = "51192b4d403ac1cb45c22d92ce58bab215843f457f245e7aca6d18744f8a3f43"

SEED = 29
LAYERS = tuple(range(5, 15))
PER_LAYER = 250
TRAIN_SIZE = 2000
HELDOUT_SIZE = 500
ARM_SEEDS = (0, 1, 2, 3, 4)
PUCT_SIMULATIONS = 400

#: Adoption margin, read on the interval. Mechanism contrasts use Bonferroni for
#: a family of two -- only two of the three are independent, since
#: B - E = (B - C) - (E - C) exactly.
MARGIN = 0.05
T_ADOPT = 2.776  # t(4), two-sided 95%
T_MECHANISM = 3.169  # t(4), two-sided 97.5% -- Bonferroni over two contrasts

#: The C - A equivalence test (TOST). The whole interval must lie within +/-DELTA.
DELTA = 0.02

#: Schedule, pinned here because the arms' head sizes differ by 35x.
EPOCHS = 40
BATCH_SIZE = 64
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-4

ARMS = {
    "A_factored": None,
    "B_cell": RotationReadout.CELL,
    "C_pooled": RotationReadout.POOLED,
    "E_tile": RotationReadout.TILE,
    "D_flat": "flat",
}


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


def build_net(variant: Variant, arm: str):
    """Construct one arm. The seed is set by the caller, before this is called."""
    spec = ARMS[arm]
    if spec is None:
        return FlipHexNet(variant.n_cols, variant.n_rows)
    if spec == "flat":
        return FlatHeadNet(variant.n_cols, variant.n_rows)
    return ConditionedHeadNet(variant.n_cols, variant.n_rows, readout=spec)


def optimiser_for(net) -> torch.optim.Optimizer:
    """Adam, with the rotation tensor exempt from weight decay.

    The pooled control's equivalence to the factored head relies on Adam's
    scale invariance, and decay on a 43k rotation head is doing nothing useful
    while making the decay-to-signal ratio differ across parameterisations.
    """
    decayed, undecayed = [], []
    for name, parameter in net.named_parameters():
        (undecayed if "rotation_head" in name else decayed).append(parameter)
    return torch.optim.Adam(
        [
            {"params": decayed, "weight_decay": WEIGHT_DECAY},
            {"params": undecayed, "weight_decay": 0.0},
        ],
        lr=LEARNING_RATE,
    )


def train_arm(
    variant: Variant,
    arm: str,
    samples: list[Sample],
    seed: int,
    *,
    epochs: int = EPOCHS,
    frozen_from=None,
):
    """Train one arm. Identical schedule and batch order across arms.

    ``frozen_from`` supplies a trained network whose stem, tower and policy_conv
    are copied and frozen, so only the head is fitted. That is the head-level
    diagnostic: all arms then see literally the same tower.
    """
    torch.manual_seed(seed)
    net = build_net(variant, arm)
    if frozen_from is not None:
        for module in ("stem", "tower", "policy_conv", "value_head"):
            getattr(net, module).load_state_dict(
                getattr(frozen_from, module).state_dict()
            )
            for parameter in getattr(net, module).parameters():
                parameter.requires_grad_(False)

    optimiser = optimiser_for(net)
    order = random.Random(seed)
    history = []
    for _ in range(epochs):
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


def move_log_policy(net, variant: Variant, board, state, moves):
    """Log-probabilities over ``moves`` for whichever head ``net`` carries."""
    x = to_tensor(encode(board, state), variant.n_cols, variant.n_rows)
    if isinstance(net, FlatHeadNet):
        logits, _ = net(x)
        return flat_masked_log_policy(logits[0], moves)
    if isinstance(net, ConditionedHeadNet):
        cell, tile, rows, _ = net(x)
        index = torch.zeros(len(moves), dtype=torch.long)
        cells = torch.tensor([m.cell for m in moves])
        tiles = torch.tensor([m.tile for m in moves])
        rotations = torch.tensor([m.rotation for m in moves])
        rotation = net.reduce_rows(rows, index, cells, tiles)[
            torch.arange(len(moves)), rotations
        ]
        scores = cell[0, cells] + tile[0, tiles] + rotation
        return torch.log_softmax(scores, dim=0)
    cell, tile, rotation, _ = net(x)
    return masked_log_policy(cell[0], tile[0], rotation[0], moves)


def supervised_scores(net, variant, board, states, reader) -> dict:
    """Top-1 agreement and cross-entropy, aggregated to positions."""
    hits, entropies = [], []
    with torch.no_grad():
        for state in states:
            classes, optimal = optimal_classes(board, reader, state)
            moves = [m for group in classes for m in group]
            log_p = move_log_policy(net, variant, board, state, moves)

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


class _ArmEvaluator(NetworkEvaluator):
    """Search adapter that works for any of the five heads."""

    def __init__(self, net, board, variant):
        super().__init__(net, board)
        self.variant = variant

    def prior(self, board, state, moves):
        self._ensure_generic(state)
        return (
            move_log_policy(self.net, self.variant, board, state, moves).exp().tolist()
        )

    def _ensure_generic(self, state):
        if self._state is state:
            return
        x = to_tensor(encode(self.board, state), self.board.n_cols, self.board.n_rows)
        with torch.no_grad():
            out = self.net(x)
        self._value = float(out[-1][0])
        self._state = state
        self.forwards += 1

    def evaluate(self, board, state):
        self._ensure_generic(state)
        return self._value


def search_scores(net, variant, board, states, reader, seed: int) -> dict:
    """Primary metric: top-1 optimality after PUCT, with the head as prior."""
    hits = []
    for offset, state in enumerate(states):
        evaluator = _ArmEvaluator(net, board, variant)
        search = MCTS(
            board,
            mode=ExpansionMode.POSITION,
            prior=evaluator.prior,
            evaluate=evaluator.evaluate,
            dirichlet_weight=0.0,
            seed=seed * 100_003 + offset,
        )
        root = search.run(state, PUCT_SIMULATIONS)
        hits.append(reader.slot(apply_move(board, state, best_move(root))) == SLOT_LOSS)
    low, high = wilson(sum(hits), len(hits))
    return {"top1": sum(hits) / len(hits), "ci": [low, high], "hits": hits}


def contrast(a: list[float], b: list[float], critical: float) -> dict:
    """Paired difference ``b - a`` over seed means, at the given critical value."""
    diffs = [x - y for y, x in zip(a, b, strict=True)]
    n = len(diffs)
    mean = statistics.fmean(diffs)
    if n < 2:
        return {"difference": mean, "ci_low": mean, "ci_high": mean, "n": n}
    half = critical * statistics.stdev(diffs) / math.sqrt(n)
    return {
        "difference": mean,
        "ci_low": mean - half,
        "ci_high": mean + half,
        "half_width": half,
        "n": n,
        # A zero-width interval is not a precise measurement, it is a degenerate
        # one: every seed produced the identical difference, so the spread is 0
        # and the interval collapses onto its point estimate. Flagged here so it
        # cannot be read as a clean result further downstream -- the adoption
        # rule and the equivalence test both refuse it, but a mechanism contrast
        # would otherwise print as though it had measured something.
        "degenerate": half <= 0.0,
    }


def equivalence(interval: dict, delta: float = DELTA) -> bool:
    """TOST: the whole interval must lie within +/-delta.

    Not "the interval contains zero" -- that passes whenever the run is
    underpowered, which is a validity gate satisfied by failing to measure.

    A zero-width interval does not pass either. If every seed gives the same
    difference the spread is 0 and the interval collapses to its point estimate,
    which would declare equivalence on no evidence at all -- the mirror of the
    defect the TOST form exists to remove.
    """
    if interval.get("half_width", 0.0) <= 0.0:
        return False
    return interval["ci_low"] > -delta and interval["ci_high"] < delta


def adoption_verdict(gap: dict, seeds: int) -> str:
    """Read ``D - B`` against the margin, on the interval.

    Refused in two degenerate cases, both of which otherwise produce a confident
    instruction to change the architecture from data that cannot support one:

    - **Fewer than the registered seeds.** The rule is an interval on seed means;
      below the registered count it is not the registered rule. EXP-011 shipped
      this defect and had to be repaired after a smoke run returned "register
      fallback (b)" from a single training run.
    - **Zero-variance interval.** If every seed produces the identical
      difference, ``stdev`` is 0, the interval collapses to a point and *any*
      threshold is cleared with apparent certainty. On small held-out sets ties
      across seeds are common, so this is a live failure and not a curiosity.
    """
    if seeds < len(ARM_SEEDS):
        return (
            f"NOT APPLICABLE: the rule needs {len(ARM_SEEDS)} seeds per arm and "
            f"this run has {seeds}; the interval is not the registered one"
        )
    if gap.get("half_width", 0.0) <= 0.0:
        return (
            "NOT APPLICABLE: every seed gave the same difference, so the "
            "interval has zero width and would clear any threshold"
        )
    if gap["ci_high"] < MARGIN:
        return "adopt (b): the conditioned head reaches the flat head"
    if gap["ci_low"] > MARGIN:
        return "(b) refuted; adopt (c), the flat head -- which does NOT fix aliasing"
    return "not a result: the interval spans the margin; one bounded extension is due"


def run(args) -> dict:
    started = time.time()
    variant = Variant(5, 3, Arm("h2"))
    board = variant.board()
    artefact = verify_ground_truth(Path(args.database))
    reader = SweepReader(variant, Checkpoint(Path(args.checkpoint) / variant.name))

    rng = random.Random(SEED)
    drawn = []
    for t in LAYERS:
        drawn += [(t, s) for s in draw_layer(reader, t, args.per_layer, rng)]
    rng.shuffle(drawn)
    states = [s for _, s in drawn]
    train_states = states[: args.train_size]
    heldout = states[args.train_size : args.train_size + args.heldout_size]
    heldout_layers = [t for t, _ in drawn][
        args.train_size : args.train_size + args.heldout_size
    ]

    print(
        f"drew {len(states)}; train {len(train_states)}, held out {len(heldout)}",
        flush=True,
    )

    train_samples = []
    for state in train_states:
        sample = build_sample(board, reader, state)
        if sample is None:
            raise SystemExit("a WIN position with no optimal move: ground truth is bad")
        train_samples.append(sample)

    seeds = list(ARM_SEEDS[: args.seeds])
    results: dict[str, list] = {arm: [] for arm in ARMS}
    frozen: dict[str, list] = {arm: [] for arm in ARMS if arm != "A_factored"}

    for arm in ARMS:
        for seed in seeds:
            net, history = train_arm(variant, arm, train_samples, seed)
            row = {
                "seed": seed,
                "parameters": net.count_parameters(),
                "final_train_loss": history[-1],
                "last_five_improvement": history[-5] - history[-1],
                "supervised": supervised_scores(net, variant, board, heldout, reader),
                "search": search_scores(net, variant, board, heldout, reader, seed),
            }
            results[arm].append(row)
            print(
                f"  {arm:>11} seed {seed}: search {row['search']['top1']:.1%}  "
                f"supervised {row['supervised']['top1']:.1%}  "
                f"train loss {row['final_train_loss']:.4f}",
                flush=True,
            )

    # -- the frozen-tower condition, for the mechanism contrasts only ----------
    if not args.no_frozen:
        print("frozen-tower condition (B, C, E on A's tower)", flush=True)
        for seed in seeds:
            torch.manual_seed(seed)
            base, _ = train_arm(variant, "A_factored", train_samples, seed)
            for arm in ("B_cell", "C_pooled", "E_tile"):
                net, history = train_arm(
                    variant, arm, train_samples, seed, frozen_from=base
                )
                frozen[arm].append(
                    {
                        "seed": seed,
                        "final_train_loss": history[-1],
                        "search": search_scores(
                            net, variant, board, heldout, reader, seed
                        ),
                    }
                )
                print(
                    f"  frozen {arm:>8} seed {seed}: "
                    f"search {frozen[arm][-1]['search']['top1']:.1%}",
                    flush=True,
                )

    floor = random_floor(board, reader, heldout, random.Random(SEED + 1))
    return summarise(
        results,
        frozen,
        floor,
        heldout_layers,
        artefact,
        args,
        time.time() - started,
    )


def random_floor(board, reader, states, rng: random.Random) -> float:
    """What a uniform-random legal move scores."""
    hits = sum(
        reader.slot(apply_move(board, state, rng.choice(legal_moves(board, state))))
        == SLOT_LOSS
        for state in states
    )
    return hits / len(states)


def summarise(results, frozen, floor, heldout_layers, artefact, args, elapsed) -> dict:
    def primary(arm, source=None):
        rows = (source or results)[arm]
        return [row["search"]["top1"] for row in rows]

    a, b, c, e, d = (
        primary(k) for k in ("A_factored", "B_cell", "C_pooled", "E_tile", "D_flat")
    )

    # Adoption reads D - B at alpha = 0.05.
    gap = contrast(b, d, T_ADOPT)
    verdict = adoption_verdict(gap, len(a))

    # Validity precondition: C - A must be *equivalent* to zero, not merely
    # consistent with it.
    precondition = contrast(a, c, T_ADOPT)
    precondition_passed = equivalence(precondition)

    mechanism = {
        "B_minus_C": contrast(c, b, T_MECHANISM),
        "E_minus_C": contrast(c, e, T_MECHANISM),
        "B_minus_E": contrast(e, b, T_MECHANISM),
    }
    frozen_mechanism = None
    if frozen["B_cell"]:
        fb = [r["search"]["top1"] for r in frozen["B_cell"]]
        fc = [r["search"]["top1"] for r in frozen["C_pooled"]]
        fe = [r["search"]["top1"] for r in frozen["E_tile"]]
        frozen_mechanism = {
            "B_minus_C": contrast(fc, fb, T_MECHANISM),
            "E_minus_C": contrast(fc, fe, T_MECHANISM),
            "B_minus_E": contrast(fe, fb, T_MECHANISM),
        }

    # The layer-parity split EXP-010 showed the signal lives in.
    parity = {}
    for arm in ARMS:
        odd = even = odd_n = even_n = 0
        for row in results[arm]:
            for hit, layer in zip(row["search"]["hits"], heldout_layers, strict=True):
                if layer % 2:
                    odd += hit
                    odd_n += 1
                else:
                    even += hit
                    even_n += 1
        parity[arm] = {
            "odd": odd / odd_n if odd_n else None,
            "even": even / even_n if even_n else None,
        }

    return {
        "experiment": "EXP-012",
        "registered": "experiments/registry.md",
        "variant": "5x3-h2",
        "ground_truth_v5": EXPECTED_V5,
        "ground_truth_value": artefact.get("value"),
        "seed": SEED,
        "arm_seeds": list(ARM_SEEDS[: args.seeds]),
        "schedule": {
            "epochs": EPOCHS,
            "batch_size": BATCH_SIZE,
            "learning_rate": LEARNING_RATE,
            "weight_decay": WEIGHT_DECAY,
            "rotation_head_weight_decay": 0.0,
        },
        "puct_simulations": PUCT_SIMULATIONS,
        "margin": MARGIN,
        "delta": DELTA,
        "random_floor": floor,
        "arm_means": {
            "A_factored": statistics.fmean(a),
            "B_cell": statistics.fmean(b),
            "C_pooled": statistics.fmean(c),
            "E_tile": statistics.fmean(e),
            "D_flat": statistics.fmean(d),
        },
        "per_seed": {"A": a, "B": b, "C": c, "E": e, "D": d},
        "adoption": {"D_minus_B": gap, "verdict": verdict},
        "precondition_C_minus_A": {
            **precondition,
            "delta": DELTA,
            "passed": precondition_passed,
            "note": (
                "TOST. If this fails, every mechanism contrast below is "
                "recorded as unresolved regardless of what it shows."
            ),
        },
        "mechanism_joint": mechanism,
        "mechanism_frozen_tower": frozen_mechanism,
        "mechanism_readable": precondition_passed,
        "train_loss": {
            arm: [row["final_train_loss"] for row in results[arm]] for arm in ARMS
        },
        "layer_parity": parity,
        "reporting_rule": (
            "A null mechanism contrast is reported as NOT DETECTED, never as "
            "absent. Three properties of this design push the contrasts toward "
            "zero even if the mechanism is real; see the registry entry."
        ),
        "elapsed_seconds": elapsed,
        "results": results,
        "frozen": frozen,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="data/subgame-solutions/5x3-h2.json")
    parser.add_argument("--checkpoint", default="data/checkpoints")
    parser.add_argument("--per-layer", type=int, default=PER_LAYER)
    parser.add_argument("--train-size", type=int, default=TRAIN_SIZE)
    parser.add_argument("--heldout-size", type=int, default=HELDOUT_SIZE)
    parser.add_argument("--seeds", type=int, default=len(ARM_SEEDS))
    parser.add_argument("--no-frozen", action="store_true")
    parser.add_argument("--out", default="results/exp012-conditioned-head-5x3-h2.json")
    args = parser.parse_args()

    summary = run(args)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(summary, indent=2))

    print()
    for arm, mean in summary["arm_means"].items():
        print(f"  {arm:>11} {mean:.1%}")
    print(f"  {'floor':>11} {summary['random_floor']:.1%}")
    print()
    gap = summary["adoption"]["D_minus_B"]
    print(
        f"D - B  {gap['difference']:+.1%} [{gap['ci_low']:+.1%}, {gap['ci_high']:+.1%}]"
    )
    print(f"verdict  {summary['adoption']['verdict']}")
    pre = summary["precondition_C_minus_A"]
    print(
        f"C - A  {pre['difference']:+.1%} "
        f"[{pre['ci_low']:+.1%}, {pre['ci_high']:+.1%}]  "
        f"TOST at +/-{DELTA:.0%}: {'PASS' if pre['passed'] else 'FAIL'}"
    )
    if not pre["passed"]:
        print("  -> mechanism contrasts are UNRESOLVED regardless of value")
    for name, row in summary["mechanism_joint"].items():
        print(
            f"  {name:>10} {row['difference']:+.1%} "
            f"[{row['ci_low']:+.1%}, {row['ci_high']:+.1%}]"
        )
    print(f"written  {args.out}  ({summary['elapsed_seconds']:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
