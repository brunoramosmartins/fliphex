"""EXP-006 agreement: the five EXP-015 champions against exact ground truth.

Registered in ``experiments/registry.md`` on 2026-08-05, amended 2026-08-07 and
2026-09-16. This is the second half of the entry: ``exp006_ground_truth.py``
solved the positions, this measures whether the learned policy's move keeps the
win. The halves are separate files because solving took 4.4 h and must not be
repeated when the measurement changes.

What agreement means here
-------------------------
**A move agrees when it preserves the exact value — never when it equals the
solver's move.** A won position usually has several winning moves, and scoring
move identity would measure imitation of one arbitrary principal variation
rather than play. So for each position the chosen move is applied and the
resulting child is **solved exactly**; the move agrees when the child is a loss
for the opponent.

The denominator, and why it is not the sample
---------------------------------------------
**Positions the mover wins.** From a lost position every legal move preserves the
value — the opponent wins whatever is played — so those positions score a hit for
free and measure the sample's loss fraction rather than the learner. The
2026-09-16 amendment made the denominator the won positions after measuring how
large the effect is; in the shipped sample **148 of the registered stratum's 500
positions are lost**, so the original rule would have handed out 29.6% of its
rate before the learner moved.

The floor this rate sits on is **not zero** and must be quoted with it: the
ground truth's calibration sweep measured a median of 78.1% of legal moves
throwing the win away, so a random mover agrees on about 21.9% of won positions.

Arms
----
**Search, 400 simulations — the decision rule.** What EXP-015's floor matches and
self-play both used, so this is the agent as deployed rather than a configuration
invented for this table. ``dirichlet_weight = 0``, and every position is at ply
17 to 19, far past ``EVALUATION_TEMPERATURE_PLIES``, so selection is a
deterministic ``argmax`` over visit counts.

**Raw prior, descriptive.** One forward pass, ``argmax`` over the masked policy,
no search. It is nearly free and it is the quantity EXP-011, EXP-012 and EXP-013
all measured on the 5×3, so it is the only figure here that reads against the
architecture decisions. **It gates nothing.**

The rule
--------
**Every seed's Wilson 95% lower bound on the registered stratum must exceed
0.90.** A seed that fails is recorded, never averaged away — the same
falsifiability structure EXP-015's clause 1 uses, and for the same reason: five
champions of one pipeline are not interchangeable, and EXP-015 measured that
directly (one of five failed its floor, ``χ² = 18.52`` on 4 df).

``layer_uniform`` is reported beside it and **pooling the two strata is
forbidden**. A gap between them is the finding — it is this project's measurement
of Takizawa 2023 §5, that an evaluator's errors concentrate where play does not
go.

Anti-circularity
----------------
This reads Axis 1 ground truth and Axis 2 champions together, which is the
comparison H3 is about, so it must gate nothing in either direction. It does not:
EXP-015 is finished and its champions are frozen, the ground truth was sampled
from seeds fixed before Axis 2 existed, and nothing here can be re-run to change
an architecture, a hyperparameter or a stopping rule. Under adr-004 R1 the filter
is the artefact's ``termination`` field, checked before any rate is computed.

Usage::

    .venv/bin/python scripts/exp006_agreement.py
    .venv/bin/python scripts/exp006_agreement.py --seed 1 --seed 2
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from az.checkpoint import Checkpoint  # noqa: E402
from az.network import build_net, evaluator_for  # noqa: E402
from az.player import SearchPlayer  # noqa: E402
from fliphex.moves import apply_move, legal_moves  # noqa: E402
from fliphex.state import Colour, GameState  # noqa: E402
from fliphex.variant import Arm, Variant  # noqa: E402
from solver.minimax import WIN, BudgetExceededError, Solver  # noqa: E402
from solver.transposition import TranspositionTable  # noqa: E402

VARIANT = Variant(5, 5, Arm("h1"))

#: EXP-015's five champions, and the budget its floor matches used.
SEEDS = (1, 2, 3, 4, 5)
SIMULATIONS = 400

#: The registered threshold. The rule is the Wilson **lower bound**, per seed.
THRESHOLD = 0.90

#: Reused from the ground-truth generator, which proved 749 of 750 positions
#: inside it.
MAX_NODES = 20_000_000
TT_BITS = 20

ARMS = ("search", "prior")
DECISION_ARM = "search"
DECISION_STRATUM = "registered"


# -- statistics ---------------------------------------------------------------


def wilson(hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = hits / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


# -- ground truth -------------------------------------------------------------


def load_ground_truth(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(
            f"ground truth not found: {path}\n"
            "Run scripts/exp006_ground_truth.py first; it takes about 4.4 hours "
            "and is resumable."
        )
    truth = json.loads(path.read_text())
    if truth.get("experiment") != "EXP-006":
        raise SystemExit(f"not an EXP-006 artefact: {truth.get('experiment')!r}")
    # adr-004 R1: the filter is applied *before* any comparison is computed.
    if truth.get("termination") != "exhausted":
        raise SystemExit(
            f"termination is {truth.get('termination')!r}, not 'exhausted'; "
            "a truncated search may not ground an axis"
        )
    if truth.get("ordering") != "internal":
        raise SystemExit(
            f"ordering is {truth.get('ordering')!r}; adr-004 R2 restricts a "
            "proof-producing run to Axis-1-internal ordering"
        )
    return truth


def denominator(truth: dict) -> list[dict]:
    """The positions the rule runs on: proved, and won by the mover.

    Ordered by ``(stratum, k, index)`` so the ordinal used to seed each search is
    stable across invocations and across seeds.
    """
    rows = [r for r in truth["positions"] if r["proved"] and r["value"] == "WIN"]
    return sorted(rows, key=lambda r: (r["stratum"], r["k"], r["index"]))


def decode_state(record: dict) -> GameState:
    return GameState.build(
        tuple(Colour(c) for c in record["colours"]),
        tuple(record["hands"]),
        Colour(record["to_move"]),
    )


# -- the champions ------------------------------------------------------------


def champion(seed: int, base: Path):
    root = base / f"h3-seed{seed}"
    if not (root / "manifest.json").exists():
        raise SystemExit(
            f"no EXP-015 checkpoint at {root}. The five champions are the "
            "measurement's subject; this cannot run without them."
        )
    state = Checkpoint(root).load()
    net = build_net(state.meta["net_spec"])
    net.load_state_dict(state.champion)
    net.eval()
    return net


def choose(net, board, state: GameState, arm: str, search_seed: int):
    """The champion's move under one arm."""
    if arm == "search":
        player = SearchPlayer(net, simulations=SIMULATIONS, seed=search_seed)
        return player.select(board, state)

    # Raw prior: one forward pass, argmax over the masked policy. The tie-break
    # matches SearchPlayer's -- (score, move) -- so the two arms differ in the
    # quantity they maximise and in nothing else.
    moves = legal_moves(board, state)
    priors = evaluator_for(net, board).prior(board, state, moves)
    return max(zip(moves, priors, strict=True), key=lambda pair: (pair[1], pair[0]))[0]


# -- scoring ------------------------------------------------------------------


def preserves(board, state: GameState, move, cache: dict) -> dict:
    """Whether ``move`` keeps the win, by solving the child exactly.

    Cached on the child position: different champions land on the same move
    often, and at ``k = 8`` a child solve is a ``k = 7`` proof.
    """
    child = apply_move(board, state, move)
    key = child.key()
    if key in cache:
        return cache[key]

    table = TranspositionTable(1 << TT_BITS)
    solver = Solver(board, tt=table, max_nodes=MAX_NODES)
    started = time.monotonic()
    try:
        value = solver.solve(child).value
    except BudgetExceededError:
        result = {"proved": False, "seconds": time.monotonic() - started}
    else:
        # The child's value is for the *opponent*, who is now to move. The move
        # keeps the win exactly when the opponent is lost.
        result = {
            "proved": True,
            "agrees": value != WIN,
            "nodes": solver.stats.nodes,
            "seconds": time.monotonic() - started,
        }
    cache[key] = result
    return result


# -- the work file ------------------------------------------------------------


def read_work(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            raise SystemExit(
                f"{path}: line {number} is not JSON. A kill truncates the last "
                "line; anything earlier is corruption."
            ) from None
    return rows


def append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(row) + "\n")
        handle.flush()


# -- the run ------------------------------------------------------------------


def measure(
    seed: int,
    arm: str,
    positions: list[dict],
    board,
    base: Path,
    work: Path,
    done: set,
    cache: dict,
) -> None:
    pending = [
        (ordinal, row)
        for ordinal, row in enumerate(positions)
        if (seed, arm, ordinal) not in done
    ]
    if not pending:
        print(f"seed {seed} / {arm}: complete", flush=True)
        return

    net = champion(seed, base)
    print(
        f"seed {seed} / {arm}: {len(pending)} of {len(positions)} positions left",
        flush=True,
    )
    started = time.monotonic()
    for count, (ordinal, row) in enumerate(pending, start=1):
        state = decode_state(row)
        # Deterministic per (champion, position): a resume reproduces the run.
        search_seed = seed * 1_000_003 + ordinal
        chosen = choose(net, board, state, arm, search_seed)
        verdict = preserves(board, state, chosen, cache)
        append(
            work,
            {
                "seed": seed,
                "arm": arm,
                "ordinal": ordinal,
                "stratum": row["stratum"],
                "k": row["k"],
                "index": row["index"],
                "move": repr(chosen),
                **verdict,
            },
        )
        done.add((seed, arm, ordinal))
        if count % 50 == 0 or count == len(pending):
            elapsed = time.monotonic() - started
            print(
                f"  {count}/{len(pending)}  {elapsed / 60:.1f} min  "
                f"({elapsed / count:.2f} s/position)",
                flush=True,
            )


# -- reporting ----------------------------------------------------------------


def rate(rows: list[dict]) -> dict:
    scored = [r for r in rows if r["proved"]]
    hits = sum(1 for r in scored if r["agrees"])
    low, high = wilson(hits, len(scored))
    return {
        "n": len(scored),
        "hits": hits,
        "rate": hits / len(scored) if scored else 0.0,
        "ci": [low, high],
        "unscored_at_budget": len(rows) - len(scored),
        "clears": low > THRESHOLD,
    }


def assemble(rows: list[dict], truth: dict, out: Path, seconds: float) -> dict:
    per_seed: dict = {}
    for seed in SEEDS:
        per_arm: dict = {}
        for arm in ARMS:
            subset = [r for r in rows if r["seed"] == seed and r["arm"] == arm]
            if not subset:
                continue
            strata = {}
            for stratum in sorted({r["stratum"] for r in subset}):
                here = [r for r in subset if r["stratum"] == stratum]
                strata[stratum] = {
                    "pooled": rate(here),
                    "per_k": {
                        str(k): rate([r for r in here if r["k"] == k])
                        for k in sorted({r["k"] for r in here})
                    },
                }
            per_arm[arm] = strata
        if per_arm:
            per_seed[str(seed)] = per_arm

    artefact = {
        "experiment": "EXP-006",
        "registered": "experiments/registry.md",
        "measures": (
            "Whether the champion's move preserves the exact value. Never move "
            "identity with the solver: a won position usually has several "
            "winning moves."
        ),
        "denominator": (
            "Positions the mover wins. From a lost position every move "
            "preserves the value (amendment 2026-09-16)."
        ),
        "rule": (
            f"Every seed's Wilson 95% lower bound on the '{DECISION_STRATUM}' "
            f"stratum, '{DECISION_ARM}' arm, must exceed {THRESHOLD}. A seed "
            "that fails is recorded, never averaged away."
        ),
        "pooling": "Forbidden across strata; layer_uniform is descriptive.",
        "simulations": SIMULATIONS,
        "threshold": THRESHOLD,
        "ground_truth": {
            "variant": truth["variant"],
            "ordering": truth["ordering"],
            "termination": truth["termination"],
            "excluded_at_budget": truth.get("excluded_at_budget"),
            "generated": truth.get("generated"),
        },
        "random_move_baseline": truth["calibration"]["random_move_agreement_on_won"],
        "seconds": seconds,
        "seeds": per_seed,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artefact, indent=2))
    return artefact


def report(artefact: dict) -> None:
    baseline = artefact["random_move_baseline"]
    print(
        f"\nrandom-move baseline on won positions: {baseline:.1%}. "
        "No rate below may be quoted without it."
    )

    for arm in ARMS:
        label = "DECISION RULE" if arm == DECISION_ARM else "descriptive, gates nothing"
        print(f"\n== arm: {arm} ({label}) ==")
        print(
            f"  {'seed':<5} {'stratum':<14} {'hits':>9} {'rate':>7} "
            f"{'Wilson 95%':>17}  verdict"
        )
        for seed in SEEDS:
            entry = artefact["seeds"].get(str(seed), {}).get(arm)
            if not entry:
                continue
            for stratum, block in entry.items():
                p = block["pooled"]
                if arm == DECISION_ARM and stratum == DECISION_STRATUM:
                    verdict = "CLEARS" if p["clears"] else "FAILS"
                else:
                    verdict = "(not the rule)"
                print(
                    f"  {seed:<5} {stratum:<14} {p['hits']:>4}/{p['n']:<4} "
                    f"{p['rate']:>6.1%} [{p['ci'][0]:>6.1%},{p['ci'][1]:>6.1%}]  "
                    f"{verdict}"
                )
            print()

    decision = {
        seed: artefact["seeds"][str(seed)][DECISION_ARM][DECISION_STRATUM]["pooled"]
        for seed in SEEDS
        if str(seed) in artefact["seeds"]
        and DECISION_ARM in artefact["seeds"][str(seed)]
        and DECISION_STRATUM in artefact["seeds"][str(seed)][DECISION_ARM]
    }
    print("== the rule ==")
    if len(decision) < len(SEEDS):
        missing = [s for s in SEEDS if s not in decision]
        print(
            f"  INCOMPLETE: seeds {missing} have no rows on the "
            f"'{DECISION_STRATUM}' stratum. H3's clause on this member needs all "
            "five; nothing is read until they exist."
        )
        return

    failures = [seed for seed, p in decision.items() if not p["clears"]]
    rates = [p["rate"] for p in decision.values()]
    print(
        "  rates    "
        + "  ".join(f"{r:.1%}" for r in rates)
        + f"\n  mean {statistics.fmean(rates):.1%}   sd {statistics.stdev(rates):.1%}"
        f"   range {min(rates):.1%}-{max(rates):.1%}"
    )
    if failures:
        print(
            f"\n  H3 FAILS ON THE SHIPPED GAME: seeds {failures} do not clear "
            f"{THRESHOLD:.0%}.\n"
            "  Per the registration the reduced boards cannot rescue this — "
            "carrying the\n  shipped game is the entire reason this member "
            "exists — and a failing seed\n  is recorded, not averaged away."
        )
    else:
        print(
            f"\n  EVERY SEED CLEARS {THRESHOLD:.0%}. H3's clause on this member "
            "is satisfied.\n  It is one member of three: 3x3 and 5x3 are read "
            "separately, and clause 1\n  was already recorded as failing in "
            "EXP-015."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--truth", default="data/ground-truth/5x5-endgame-seed2.json")
    parser.add_argument("--base", default="data/az-runs")
    parser.add_argument("--out", default="results/exp006-agreement-5x5.json")
    parser.add_argument("--work", default="results/exp006-agreement-5x5.jsonl")
    parser.add_argument("--seed", type=int, action="append", choices=SEEDS)
    parser.add_argument("--arm", action="append", choices=ARMS)
    parser.add_argument("--assemble-only", action="store_true")
    args = parser.parse_args()

    truth = load_ground_truth(Path(args.truth))
    positions = denominator(truth)
    board = VARIANT.board()
    work = Path(args.work)
    rows = read_work(work)

    print(
        f"ground truth: {len(truth['positions'])} positions, "
        f"{len(positions)} won by the mover and therefore scorable "
        f"({len(positions) / len(truth['positions']):.1%})"
    )
    for stratum in sorted({r["stratum"] for r in positions}):
        n = sum(1 for r in positions if r["stratum"] == stratum)
        print(f"  {stratum:<14} {n}")

    started = time.monotonic()
    if not args.assemble_only:
        done = {(r["seed"], r["arm"], r["ordinal"]) for r in rows}
        cache: dict = {}
        for seed in args.seed or SEEDS:
            for arm in args.arm or ARMS:
                measure(seed, arm, positions, board, Path(args.base), work, done, cache)
        rows = read_work(work)

    artefact = assemble(rows, truth, Path(args.out), time.monotonic() - started)
    report(artefact)
    print(f"\nwritten  {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
