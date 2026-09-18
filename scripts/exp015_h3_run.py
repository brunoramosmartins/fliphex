"""EXP-015 — the H3 training run: one seed per invocation, then the floor.

Registered in ``experiments/registry.md`` on 2026-09-04, before this file
existed. Read the entry first; every constant here is pinned there.

**One seed per invocation, by design.** The five seeds are independent and the
machine saturates at six workers, so running two at once would only halve each.
Sequential also makes the first seed a go/no-go for the remaining 110 hours
rather than a fifth of a result — and that check is registered as a *floor-only*
check, so it cannot become optional stopping.

What this produces
------------------
For each seed: 30 generations of self-play, training and gating, then the floor
matches that decide whether the run counts as evidence at all.

**Primary — equal simulations.** The trained champion against prior-free UCT,
both at 400 simulations, 200 games, seats alternating. The criterion is that the
Wilson 95% interval lies **entirely above 50%**. The wording understates the bar:
at 200 games a true 55% gives [48.1%, 61.7%] and fails, so the effective bar is
near 58%.

**Secondary — equal time.** The same match with UCT given the simulation count it
can complete in the network agent's measured per-move wall clock. The ratio is
measured before the match and recorded. This is the harder bar and it is
secondary deliberately: equal-simulations asks whether the prior is worth
anything, equal-time asks whether the network is worth what it costs. Both go in
the artefact; registering only the flattering one is how a floor becomes
decoration.

**Reference — generation 0.** The randomly initialised champion plays the same
equal-simulations match, to say where the seed started. Nothing branches on it.
It needs no storage: ``az.loop`` seeds initialisation from the run seed, so the
network is reconstructed exactly rather than kept.

Resumability
------------
Training resumes from its checkpoint, which EXP-014 verified byte-exact under a
real ``SIGKILL``. The floor matches are not checkpointed, but each is written to
the artefact as it completes and a re-run skips what is already there, so a kill
costs at most one match rather than the seed.

What this may not do
--------------------
It never reads solver ground truth. Under adr-004 R1 neither axis may terminate
the other along the dimension of their later comparison, and H3 *is* the
comparison on solver agreement — so the success criterion is the UCT floor, which
contains no solver information, and the agreement rates are a separate read
afterwards that gates nothing.

Usage::

    .venv/bin/python scripts/exp015_h3_run.py --seed 1
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch  # noqa: E402

from az.checkpoint import Checkpoint  # noqa: E402
from az.gate import run_gate, wilson  # noqa: E402
from az.loop import LoopConfig, run  # noqa: E402
from az.network import ConvRotationNet, build_net  # noqa: E402
from az.player import EVALUATION_TEMPERATURE_PLIES, SearchPlayer  # noqa: E402
from fliphex.moves import apply_move, legal_moves  # noqa: E402
from fliphex.rules import is_terminal  # noqa: E402
from fliphex.variant import Arm, Variant  # noqa: E402

# -- pinned by the registry ---------------------------------------------------

VARIANT = Variant(5, 5, Arm("h1"))
SEEDS = (1, 2, 3, 4, 5)
GENERATIONS = 30
GAMES = 200
SIMULATIONS = 400
STEPS = 400
BATCH_SIZE = 64
BUFFER_CAPACITY = 20_000
GATE_EVERY = 5
GATE_GAMES = 400
GATE_THRESHOLD = 0.55

#: EXP-014's measured optima, which differ by activity: self-play saturates at
#: six with eight within 1%, the gate peaks at four and loses 33% at eight,
#: because a gate worker holds two networks against self-play's one.
WORKERS = 6
GATE_WORKERS = 4

#: A multiple of GATE_WORKERS that divides GATE_GAMES, so no chunk leaves workers
#: idle and a kill costs at most 20 games.
GATE_CHECKPOINT_EVERY = 20

#: The floor.
FLOOR_GAMES = 200
FLOOR_TEMPERATURE_PLIES = EVALUATION_TEMPERATURE_PLIES

#: Moves sampled when measuring each agent's per-move cost for the equal-time arm.
COST_MOVES = 30


def config_for(seed: int, root: Path) -> LoopConfig:
    return LoopConfig(
        variant=VARIANT,
        seed=seed,
        generations=GENERATIONS,
        games=GAMES,
        simulations=SIMULATIONS,
        steps=STEPS,
        batch_size=BATCH_SIZE,
        buffer_capacity=BUFFER_CAPACITY,
        gate_every=GATE_EVERY,
        gate_games=GATE_GAMES,
        gate_threshold=GATE_THRESHOLD,
        gate_simulations=SIMULATIONS,
        gate_checkpoint_every=GATE_CHECKPOINT_EVERY,
        workers=WORKERS,
        gate_workers=GATE_WORKERS,
        root=root,
    )


def initial_net(seed: int) -> ConvRotationNet:
    """Generation 0's champion, reconstructed rather than stored.

    ``az.loop`` seeds initialisation from the run seed and starts the champion
    and challenger from identical weights, so this is exactly the network the
    seed began with.
    """
    torch.manual_seed(seed)
    net = ConvRotationNet(VARIANT.n_cols, VARIANT.n_rows)
    net.eval()
    return net


def trained_net(root: Path):
    state = Checkpoint(root).load()
    net = build_net(state.meta["net_spec"])
    net.load_state_dict(state.champion)
    net.eval()
    return net


# -- the equal-time ratio -----------------------------------------------------


def sample_positions(seed: int, count: int) -> list:
    """Positions from a random playout, so the cost is measured mid-game."""
    board = VARIANT.board()
    state = VARIANT.initial_state()
    rng = torch.Generator().manual_seed(seed)
    states = []
    while not is_terminal(state) and len(states) < count:
        states.append(state)
        moves = legal_moves(board, state)
        index = int(torch.randint(len(moves), (1,), generator=rng))
        state = apply_move(board, state, moves[index])
    return states


def seconds_per_move(net, states, *, simulations: int, seed: int) -> float:
    board = VARIANT.board()
    player = SearchPlayer(net, simulations=simulations, seed=seed)
    started = time.monotonic()
    for state in states:
        player.select(board, state)
    return (time.monotonic() - started) / len(states)


def equal_time_simulations(net, seed: int) -> dict:
    """How many simulations UCT can afford in the network agent's move time.

    Measured before the match rather than assumed, because the whole point of the
    secondary is that the two agents' per-move costs differ by a large factor and
    the equal-simulations comparison does not charge for it.
    """
    states = sample_positions(seed, COST_MOVES)
    net_cost = seconds_per_move(net, states, simulations=SIMULATIONS, seed=seed)
    uct_cost = seconds_per_move(None, states, simulations=SIMULATIONS, seed=seed)
    ratio = net_cost / uct_cost
    return {
        "moves_sampled": len(states),
        "net_seconds_per_move": net_cost,
        "uct_seconds_per_move_at_400": uct_cost,
        "ratio": ratio,
        "uct_simulations": max(SIMULATIONS, int(round(SIMULATIONS * ratio))),
    }


# -- the floor ----------------------------------------------------------------


def floor_match(net, seed: int, *, label: str, uct_simulations: int | None) -> dict:
    """The learned champion against prior-free UCT.

    ``run_gate`` supplies the mechanics -- alternating seats, an even game count,
    a Wilson interval and a seat split. Its ``promoted`` field is **not** the
    criterion here and is ignored: promotion is a point-estimate rule calibrated
    for the evaluator gate, and this entry's criterion is that the *interval*
    lies entirely above 50%.
    """
    started = time.monotonic()
    result = run_gate(
        VARIANT,
        net,
        None,  # prior-free UCT
        simulations=SIMULATIONS,
        seed=seed * 7_000_003,
        games=FLOOR_GAMES,
        threshold=0.5,
        temperature_plies=FLOOR_TEMPERATURE_PLIES,
        workers=GATE_WORKERS,
        chunk=GATE_CHECKPOINT_EVERY,
        champion_simulations=uct_simulations,
    )
    low, high = wilson(result.wins, result.games)
    return {
        "label": label,
        "games": result.games,
        "wins": result.wins,
        "win_rate": result.win_rate,
        "ci": [low, high],
        "as_first": result.as_first,
        "as_second": result.as_second,
        "net_simulations": SIMULATIONS,
        "uct_simulations": uct_simulations or SIMULATIONS,
        "clears_floor": low > 0.5,
        "seconds": time.monotonic() - started,
    }


# -- artefact -----------------------------------------------------------------


def load_artefact(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {
        "experiment": "EXP-015",
        "registered": "experiments/registry.md",
        "variant": VARIANT.name,
        "architecture": "ConvRotationNet",
        "criterion": (
            "Every seed's Wilson 95% interval against prior-free UCT at equal "
            "simulations must lie entirely above 50%. A seed that fails is "
            "recorded as instability, never averaged away."
        ),
        "not_established": (
            "Beating prior-free UCT licenses 'the learner learned something' and "
            "nothing more. How good it is comes from H3's solver-agreement "
            "clause, which is a measurement and gates nothing here."
        ),
        "schedule": {
            "seeds": list(SEEDS),
            "generations": GENERATIONS,
            "games": GAMES,
            "simulations": SIMULATIONS,
            "steps": STEPS,
            "batch_size": BATCH_SIZE,
            "buffer_capacity": BUFFER_CAPACITY,
            "gate_every": GATE_EVERY,
            "gate_games": GATE_GAMES,
            "gate_threshold": GATE_THRESHOLD,
            "workers": WORKERS,
            "gate_workers": GATE_WORKERS,
            "floor_games": FLOOR_GAMES,
        },
        "seeds": {},
    }


def save_artefact(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


# -- one seed -----------------------------------------------------------------


def run_seed(seed: int, base: Path, out: Path) -> dict:
    root = base / f"h3-seed{seed}"
    config = config_for(seed, root)

    artefact = load_artefact(out)
    entry = artefact["seeds"].setdefault(str(seed), {"seed": seed, "floors": {}})

    started = time.monotonic()
    resume = Checkpoint(root).resume_point()
    print(
        f"seed {seed}: "
        + (f"resuming at generation {resume}" if resume else "starting fresh"),
        flush=True,
    )
    rows = run(
        config,
        (lambda: ConvRotationNet(VARIANT.n_cols, VARIANT.n_rows))
        if resume is None
        else None,
        on_generation=lambda row: print(
            f"  gen {row['generation']:2}  {row['seconds']:6.0f}s  "
            f"buffer {row['buffer']:5}  policy {row['policy_loss']:.4f}"
            + (
                f"  GATE {row['gate_win_rate']:.1%} promoted={row['promoted']}"
                if row["gated"]
                else ""
            ),
            flush=True,
        ),
    )
    entry["training_seconds"] = time.monotonic() - started
    entry["generations_run_this_invocation"] = len(rows)
    entry["history_path"] = str(config.history_path)
    save_artefact(out, artefact)

    net = trained_net(root)

    # Each match is written as it completes, so a kill costs one match, not the
    # seed. A re-run skips what is already recorded.
    if "equal_simulations" not in entry["floors"]:
        print(f"seed {seed}: floor, equal simulations", flush=True)
        entry["floors"]["equal_simulations"] = floor_match(
            net, seed, label="equal simulations", uct_simulations=None
        )
        save_artefact(out, artefact)
        _report(entry["floors"]["equal_simulations"])

    if "generation_0" not in entry["floors"]:
        print(f"seed {seed}: reference, generation 0", flush=True)
        entry["floors"]["generation_0"] = floor_match(
            initial_net(seed), seed, label="generation 0", uct_simulations=None
        )
        save_artefact(out, artefact)
        _report(entry["floors"]["generation_0"])

    if "equal_time" not in entry["floors"]:
        print(f"seed {seed}: measuring the equal-time ratio", flush=True)
        budget = equal_time_simulations(net, seed)
        print(
            f"  net {budget['net_seconds_per_move']:.3f} s/move, "
            f"UCT {budget['uct_seconds_per_move_at_400']:.3f} s/move at 400 "
            f"-> ratio {budget['ratio']:.2f}, UCT gets "
            f"{budget['uct_simulations']} simulations",
            flush=True,
        )
        entry["equal_time_budget"] = budget
        entry["floors"]["equal_time"] = floor_match(
            net, seed, label="equal time", uct_simulations=budget["uct_simulations"]
        )
        save_artefact(out, artefact)
        _report(entry["floors"]["equal_time"])

    entry["seconds_total"] = time.monotonic() - started
    save_artefact(out, artefact)
    return entry


def _report(match: dict) -> None:
    print(
        f"  {match['label']:20} {match['wins']}/{match['games']} = "
        f"{match['win_rate']:.1%} [{match['ci'][0]:.1%}, {match['ci'][1]:.1%}]  "
        f"seats {match['as_first']}/{match['as_second']}  "
        f"UCT sims {match['uct_simulations']}  "
        f"{'CLEARS' if match['clears_floor'] else 'FAILS'} the floor",
        flush=True,
    )


def summarise(artefact: dict) -> None:
    done = sorted(artefact["seeds"], key=int)
    rates = [
        artefact["seeds"][s]["floors"]["equal_simulations"]["win_rate"]
        for s in done
        if "equal_simulations" in artefact["seeds"][s]["floors"]
    ]
    print()
    print(f"seeds complete: {done} of {SEEDS}")
    if rates:
        print(
            "equal-simulations floor: "
            + "  ".join(f"{r:.1%}" for r in rates)
            + (
                f"   spread {statistics.stdev(rates):.1%}"
                if len(rates) > 1
                else "   spread needs 2+ seeds"
            )
        )
    if len(done) < len(SEEDS):
        print(
            "H3's stability clause needs all five. Nothing is read across seeds "
            "until they are done."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True, choices=SEEDS)
    parser.add_argument("--base", default="data/az-runs")
    parser.add_argument("--out", default="results/exp015-h3-training-5x5.json")
    args = parser.parse_args()

    out = Path(args.out)
    entry = run_seed(args.seed, Path(args.base), out)

    print()
    for match in entry["floors"].values():
        _report(match)
    primary = entry["floors"].get("equal_simulations")
    if primary and not primary["clears_floor"]:
        print()
        print(
            "THIS SEED FAILS THE FLOOR. Per the registration, if this is seed 1 "
            "the run stops here and the entry reports a failure. A restart with "
            "different hyperparameters needs a new registered entry -- "
            "retraining until it works selects on the outcome."
        )
    summarise(load_artefact(out))
    print(f"\nwritten  {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
