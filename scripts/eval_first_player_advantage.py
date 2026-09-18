"""EXP-017 — the first-player rate on the shipped 5×5, under exact endgame play.

Registered in ``experiments/registry.md`` on 2026-09-18, before this file
existed, replacing EXP-016 which was withdrawn the same day by red-team. Read
both entries first; every constant here is pinned there.

What this measures, named honestly
----------------------------------
`SolverAgent` plays **both** seats: `max_nodes = 2,000,000`,
`search_below_k = 8`, falling back to `HeuristicAgent` above that. So this is

    the heuristic for roughly seventeen plies, then perfect play for the last
    eight,

and the measured `proved_rate` is about **31%**. **No rate this script writes may
be quoted without that number** — the requirement is in
``agents/solver_agent.py``'s own docstring and EXP-008 set the precedent.

**This says nothing about perfect play.** H1 is a claim about perfect play and
its evidence is the four exhaustive solves (3×3 and 5×3, both deck arms, all
``termination: exhausted``). What this produces is the first-player rate at a
named, reproducible, imperfect level of play.

Why this agent
--------------
EXP-016 tried prior-free UCT at 400 simulations and was withdrawn: on a root that
deduplicates to 325 children it visited **10–18 of them**, in board-cell order,
and the coverage differed by seat. This agent's move choice is not an artefact of
enumeration order — `HeuristicAgent` takes the maximum net flip and breaks ties
with ``rng.choice`` — and it carries no training seed, so EXP-015's measured
between-seed ``sd`` of 7.3% cannot leak in.

The self-check, which runs before any number is produced
--------------------------------------------------------
Gate 7 of ``docs/measurement-gates.md``: *no instrument produces a number before
it is run against a known answer*. Two probes, and **both assert on the artefact
fields rather than on a return value** — EXP-016's registered probes would have
passed straight through its labelling defect.

1. **Perfect self-play on the 5×1**, where the game is exactly solvable and the
   first player **wins** (216 nodes). Perfect play in both seats must therefore
   produce ``first_player_rate == 1.0`` exactly, for any seed and any game count.
2. **A rigged first player that always throws the game**, which must produce
   ``first_player_rate == 0.0``. That probe is the one that catches a harness
   crediting the *agent* rather than the *seat*.

Interpreter
-----------
Stdlib only — no torch, no numpy, no scipy — so this runs under PyPy, which is
what makes the registered 5,000 games affordable. Measured on twelve games:
**2.16 s/game under PyPy 3.11 against 7.95 under CPython**, a 3.7× speedup, and
both interpreters produced identical games and identical winners.

Deliberately single-process. At 3.0 h there is nothing to buy by parallelising,
and EXP-014 is a record of what parallelising costs to get right.

Usage::

    ~/pypy3.11-v7.3.23-linux64/bin/pypy3.11 scripts/eval_first_player_advantage.py
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.heuristic_agent import HeuristicAgent  # noqa: E402
from agents.solver_agent import SolverAgent  # noqa: E402
from fliphex.moves import apply_move, legal_moves  # noqa: E402
from fliphex.rules import is_terminal  # noqa: E402
from fliphex.state import Colour  # noqa: E402
from fliphex.variant import Arm, Variant  # noqa: E402
from solver.minimax import WIN, Solver  # noqa: E402
from solver.transposition import TranspositionTable  # noqa: E402

# -- pinned by the registry ---------------------------------------------------

VARIANT = Variant(5, 5, Arm("h1"))
GAMES = 5_000
MATCH_SEED = 1
MAX_NODES = 2_000_000
SEARCH_BELOW_K = 8

#: One match seed, not twenty. Twenty buy no independence over a fixed agent and
#: EXP-016's schedule shared 975 of 5,000 player seeds across them.
SEED_BASE = MATCH_SEED * 10_000_000


def seeds_for(index: int) -> tuple[int, int]:
    """The two seats' tie-break seeds for game ``index``.

    Distinct by construction — consecutive integers — rather than by an
    arithmetic coincidence that has to be rechecked whenever a multiplier moves.
    :func:`assert_seeds_distinct` verifies it anyway at startup.
    """
    return SEED_BASE + 2 * index, SEED_BASE + 2 * index + 1


def assert_seeds_distinct(games: int) -> None:
    seeds = [s for i in range(games) for s in seeds_for(i)]
    if len(set(seeds)) != len(seeds):
        raise SystemExit(
            f"{len(seeds) - len(set(seeds))} of {len(seeds)} player seeds collide. "
            "EXP-016 was withdrawn partly for this; the run stops rather than "
            "reporting an interval over games that share a random stream."
        )


# -- statistics (stdlib only, so this runs under PyPy) ------------------------


def wilson(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


# -- one game -----------------------------------------------------------------


def play_game(board, variant: Variant, first_agent, second_agent) -> dict:
    """One game. ``first_agent`` moves first.

    Returns the seat-attributed outcome. **Seat, not agent** — crediting the
    agent is the defect probe 2 exists to catch.
    """
    state = variant.initial_state()
    mover = state.to_move
    moves = []
    while not is_terminal(state):
        agent = first_agent if state.to_move == mover else second_agent
        move = agent.select(board, state)
        moves.append(repr(move))
        state = apply_move(board, state, move)

    purple, green = state.score()
    if purple == green:  # pragma: no cover - odd cell count forbids it
        raise AssertionError(
            f"a drawn game on {variant.name}: {purple}-{green}. Draws are "
            "impossible on an odd cell count; this is an engine defect."
        )
    winner = Colour.PURPLE if purple > green else Colour.GREEN
    return {"first_won": winner == mover, "moves": tuple(moves)}


def solver_pair(seeds: tuple[int, int], *, search_below_k: int | None):
    first, second = seeds
    return (
        SolverAgent(
            seed=first,
            max_nodes=MAX_NODES,
            search_below_k=search_below_k,
            fallback=HeuristicAgent(seed=first),
        ),
        SolverAgent(
            seed=second,
            max_nodes=MAX_NODES,
            search_below_k=search_below_k,
            fallback=HeuristicAgent(seed=second),
        ),
    )


# -- the measurement ----------------------------------------------------------


def measure(
    variant: Variant,
    games: int,
    make_agents,
    *,
    start: int = 0,
    on_game=None,
) -> dict:
    """Play ``games`` games and attribute every win to a seat."""
    board = variant.board()
    wins = 0
    distinct = set()
    proved = unattempted = over_budget = 0
    started = time.monotonic()

    for index in range(start, games):
        first, second = make_agents(index)
        outcome = play_game(board, variant, first, second)
        wins += outcome["first_won"]
        distinct.add(outcome["moves"])
        # Per game, not only in the running totals: a resume rebuilds the
        # artefact from the work file, so a ply count that lives only here is
        # lost at the first interruption — and `proved_rate` is the number no
        # rate may be quoted without.
        outcome["proved"] = sum(getattr(a, "proved", 0) for a in (first, second))
        outcome["unattempted"] = sum(
            getattr(a, "unattempted", 0) for a in (first, second)
        )
        outcome["over_budget"] = sum(
            getattr(a, "over_budget", 0) for a in (first, second)
        )
        proved += outcome["proved"]
        unattempted += outcome["unattempted"]
        over_budget += outcome["over_budget"]
        if on_game is not None:
            on_game(index, outcome)

    played = games - start
    plies = proved + unattempted + over_budget
    low, high = wilson(wins, played)
    return {
        "games": played,
        "first_player_wins": wins,
        "first_player_rate": wins / played if played else 0.0,
        "wilson_low": low,
        "wilson_high": high,
        "distinct_games": len(distinct),
        "proved_plies": proved,
        "unattempted_plies": unattempted,
        "over_budget_plies": over_budget,
        "proved_rate": proved / plies if plies else 0.0,
        "seconds": time.monotonic() - started,
    }


# -- gate 7: the self-check, before any number ---------------------------------


class ThrowingAgent:
    """Picks a move that hands the opponent a win, whenever one exists.

    Only ever used by the self-check. It is the probe that separates "the
    harness credits the seat" from "the harness credits the agent": as the first
    player on a board where a losing move always exists, it must drive
    ``first_player_rate`` to exactly zero.
    """

    def __init__(self, board, seed: int | None = None) -> None:
        self.board = board
        self._rng = random.Random(seed)

    def select(self, board, state):
        moves = legal_moves(board, state)
        table = TranspositionTable(1 << 16)
        losing = [
            move
            for move in moves
            if Solver(board, tt=table).solve(apply_move(board, state, move)).value
            == WIN
        ]
        return self._rng.choice(losing or moves)


def self_check(verbose: bool = True) -> list[dict]:
    """Two known answers. Raises rather than returning a number it cannot back."""
    probes = []
    small = Variant(5, 1)
    board = small.board()

    # Probe 1 -- perfect play in both seats on a board the solver settles: the
    # 5x1's first player wins, so the rate is 1.0 exactly, for any seed.
    perfect = measure(
        small, 8, lambda i: solver_pair(seeds_for(i), search_below_k=None)
    )
    probes.append({"probe": "perfect self-play on 5x1", "expected": 1.0, **perfect})
    if perfect["first_player_rate"] != 1.0:
        raise SystemExit(
            "PROBE 1 FAILED: perfect play in both seats on the 5x1 returned "
            f"{perfect['first_player_rate']:.3f}, not 1.0. The 5x1's first "
            "player wins with perfect play (216 nodes, proved), so either the "
            "seat attribution, the winner rule or the agent is wrong. No "
            "measurement is written."
        )

    # Probe 2 -- the seat, not the agent. A first player that throws every game
    # must read 0.0; a harness crediting the agent would not notice.
    thrown = measure(
        small,
        8,
        lambda i: (
            ThrowingAgent(board, seed=seeds_for(i)[0]),
            solver_pair(seeds_for(i), search_below_k=None)[1],
        ),
    )
    probes.append({"probe": "first player throws, on 5x1", "expected": 0.0, **thrown})
    if thrown["first_player_rate"] != 0.0:
        raise SystemExit(
            "PROBE 2 FAILED: a first player that always hands the opponent a win "
            f"returned {thrown['first_player_rate']:.3f}, not 0.0. The harness is "
            "crediting the agent rather than the seat. No measurement is written."
        )

    if verbose:
        for probe in probes:
            print(
                f"  probe: {probe['probe']:<32} "
                f"rate {probe['first_player_rate']:.1f} "
                f"(expected {probe['expected']:.1f})  PASS",
                flush=True,
            )
    return probes


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=GAMES)
    parser.add_argument("--out", default="results/exp017-first-player-5x5.json")
    parser.add_argument("--work", default="results/exp017-first-player-5x5.jsonl")
    parser.add_argument(
        "--skip-self-check",
        action="store_true",
        help="not for a reported run; the self-check is gate 7",
    )
    args = parser.parse_args()

    print(
        f"interpreter: {platform.python_implementation()} {platform.python_version()}"
    )
    assert_seeds_distinct(args.games)
    print(f"seeds: {2 * args.games} derived, all distinct")

    if not args.skip_self_check:
        print("gate 7 self-check, before any number:")
        probes = self_check()
    else:
        probes = [{"probe": "SKIPPED", "expected": None}]

    work = Path(args.work)
    rows = read_work(work)
    done = len(rows)
    if done:
        print(f"resuming: {done} of {args.games} games already played")

    work.parent.mkdir(parents=True, exist_ok=True)
    handle = work.open("a")

    def record(index: int, outcome: dict) -> None:
        handle.write(
            json.dumps(
                {
                    "index": index,
                    "first_won": outcome["first_won"],
                    "moves": list(outcome["moves"]),
                    "proved": outcome["proved"],
                    "unattempted": outcome["unattempted"],
                    "over_budget": outcome["over_budget"],
                }
            )
            + "\n"
        )
        handle.flush()
        if (index + 1) % 100 == 0:
            print(f"  {index + 1}/{args.games}", flush=True)

    measure(
        VARIANT,
        args.games,
        lambda i: solver_pair(seeds_for(i), search_below_k=SEARCH_BELOW_K),
        start=done,
        on_game=record,
    )
    handle.close()

    rows = read_work(work)
    wins = sum(1 for r in rows if r["first_won"])
    distinct = {tuple(r["moves"]) for r in rows}
    low, high = wilson(wins, len(rows))
    proved = sum(r["proved"] for r in rows)
    unattempted = sum(r["unattempted"] for r in rows)
    over_budget = sum(r["over_budget"] for r in rows)
    plies = proved + unattempted + over_budget

    artefact = {
        "experiment": "EXP-017",
        "registered": "experiments/registry.md",
        "measures": (
            "Fraction of games won by the player who moved first, under "
            "SolverAgent in both seats: the heuristic for roughly seventeen "
            "plies, then perfect play for the last eight."
        ),
        "not_established": (
            "Nothing about perfect play. H1 is a claim about perfect play and "
            "its evidence is the four exhaustive solves. No rate here may be "
            "quoted without proved_rate."
        ),
        "variant": VARIANT.name,
        "deck_arm": VARIANT.arm.value,
        "games": len(rows),
        "first_player_wins": wins,
        "first_player_rate": wins / len(rows) if rows else 0.0,
        "wilson_low": low,
        "wilson_high": high,
        "distinct_games": len(distinct),
        "proved_plies": proved,
        "unattempted_plies": unattempted,
        "over_budget_plies": over_budget,
        "proved_rate": proved / plies if plies else 0.0,
        "match_seed": MATCH_SEED,
        "search_below_k": SEARCH_BELOW_K,
        "max_nodes": MAX_NODES,
        "simulations_not_applicable": (
            "This agent does not search by simulation; search_below_k and "
            "max_nodes are its budget."
        ),
        "workers": 1,
        "interpreter": (
            f"{platform.python_implementation()} {platform.python_version()}"
        ),
        "self_check": probes,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(artefact, indent=2))

    print(
        f"\n  first player {wins}/{len(rows)} = "
        f"{artefact['first_player_rate']:.1%} [{low:.1%}, {high:.1%}]"
    )
    print(f"  distinct games {len(distinct)}/{len(rows)}")
    print(f"\nwritten  {args.out}")
    print("The verdict is applied by scripts/exp017_analysis.py, not by this file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
