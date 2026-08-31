"""Game generation: play, record, label.

One game is at most 25 plies and always ends decided, so a generation's
arithmetic has no tail in it: ``n_games`` games yield at most ``25 * n_games``
samples, exactly.

The temperature schedule
------------------------
Moves are drawn from the visit counts at temperature 1 for the opening
:data:`TEMPERATURE_PLIES` plies, then taken greedily. Temperature is where the
opening diversity comes from, and this game has less of it available than the
games the schedule is borrowed from:

- There is **no data augmentation**. The board's mirror is only a partial
  symmetry — a chiral tile breaks it while that tile is in hand — so unlike Go's
  8x or Connect Four's 2x there is no free multiplication of positions.
- A game is 25 plies. AlphaGo Zero sampled the first 30 of a game several
  hundred long; AlphaZero's chess run, 15 of roughly 80. Both are 15-20%.

Taking 15-20% of 25 plies literally would give four. That is set to **8** here,
about a third, precisely because the two sources of variety those runs had — a
long game and augmentation — are both absent. This is a knob, not a finding; it
is stated so that changing it is a decision rather than a drift.

Reproducibility across workers
------------------------------
Self-play parallelises across processes, and the obvious way to collect results
— take them as they finish — would make a generation depend on scheduling. Each
game's seed is instead a pure function of ``(seed, generation, index)``, and
results are returned in index order. A generation is then the same set of games
whatever the worker count, which is what lets a resumed run be indistinguishable
from an uninterrupted one rather than merely a valid continuation.

Each worker also pins torch to a single thread. Without that, eight workers each
spawning six BLAS threads oversubscribe six physical cores and the measured
speedup collapses.
"""

from __future__ import annotations

import multiprocessing as mp
import random
from dataclasses import dataclass, field

import torch

from az.encoding import encode
from az.mcts import MCTS, ExpansionMode, policy_target
from az.network import FlipHexNet, NetworkEvaluator
from az.replay_buffer import Sample, samples_from_game
from fliphex.moves import Move, apply_move
from fliphex.rules import is_terminal, outcome
from fliphex.state import Colour, GameState
from fliphex.variant import Variant

#: Opening plies played at temperature 1 before the search goes greedy.
TEMPERATURE_PLIES = 8

#: adr-005's Dirichlet noise at the root. The weight is the standard 0.25; the
#: alpha is 0.3, which the literature scales by branching factor -- noted rather
#: than tuned, since tuning it is a separate experiment.
DIRICHLET_ALPHA = 0.3
DIRICHLET_WEIGHT = 0.25


@dataclass
class GameRecord:
    """One finished game, before it is labelled with its outcome.

    Attributes:
        positions: ``(planes, pi, mover)`` per ply, in play order.
        winner: The colour that won. Never ``EMPTY`` — draws are impossible.
        moves: The moves actually played, for replay and debugging.
        search_seeds: The seed each ply's search ran under. Kept so one ply can
            be replayed exactly without re-running the game up to it, and so
            that seed reuse across games is observable rather than assumed.
    """

    positions: list[tuple[bytes, dict[Move, float], Colour]] = field(
        default_factory=list
    )
    winner: Colour = Colour.EMPTY
    moves: list[Move] = field(default_factory=list)
    search_seeds: list[int] = field(default_factory=list)

    def samples(self) -> list[Sample]:
        """Label every position with the outcome, from its own mover's side."""
        return samples_from_game(self.positions, self.winner)


def game_seed(seed: int, generation: int, index: int) -> int:
    """A game's seed, as a pure function of where it sits in the run.

    Deterministic and independent of worker scheduling, so a generation is the
    same set of games at any worker count. Derived rather than drawn: drawing
    from a shared stream would make game ``k`` depend on how many games had been
    started before it, which is exactly what parallelism makes unpredictable.
    """
    return (seed * 1_000_003 + generation * 10_007 + index) % (2**31 - 1)


def play_game(
    variant: Variant,
    net: FlipHexNet | None,
    *,
    simulations: int,
    seed: int,
    temperature_plies: int = TEMPERATURE_PLIES,
    mode: ExpansionMode = ExpansionMode.POSITION,
) -> GameRecord:
    """Play one self-play game and record every position.

    Args:
        variant: Board and hands.
        net: The network generating the data. ``None`` runs the search on a
            uniform prior with random rollouts, which is the plain-UCT floor the
            learned agent must beat before any result is reported.
        simulations: PUCT simulations per move.
        seed: Seeds this game's search and move sampling.
        temperature_plies: Opening plies sampled at temperature 1.
        mode: Child expansion. ``POSITION`` is mandatory for training; the other
            modes exist for the aliasing experiment.

    Returns:
        A :class:`GameRecord` with one position per ply.
    """
    board = variant.board()
    state = variant.initial_state()
    rng = random.Random(seed)
    record = GameRecord()
    evaluator = NetworkEvaluator(net, board) if net is not None else None

    ply = 0
    while not is_terminal(state):
        # Drawn from this game's own stream, never ``seed + ply``. Game seeds
        # from consecutive indices are themselves consecutive, so adding the ply
        # would give game i at ply 1 the same search seed as game i+1 at ply 0 —
        # correlating their Dirichlet noise across what are meant to be
        # independent games.
        search_seed = rng.randrange(2**31)
        record.search_seeds.append(search_seed)
        search = MCTS(
            board,
            mode=mode,
            prior=evaluator.prior if evaluator else None,
            evaluate=evaluator.evaluate if evaluator else None,
            dirichlet_alpha=DIRICHLET_ALPHA,
            dirichlet_weight=DIRICHLET_WEIGHT,
            seed=search_seed,
        )
        root = search.run(state, simulations)

        # pi is always recorded at temperature 1: it is the training target, and
        # a greedy target would throw away the search's own uncertainty. Only
        # the move *played* goes greedy after the opening.
        pi = policy_target(root, temperature=1.0)
        record.positions.append((encode(board, state), pi, state.to_move))

        move = _choose(pi, rng, explore=ply < temperature_plies)
        record.moves.append(move)
        state = apply_move(board, state, move)
        ply += 1

    record.winner = _winner(state)
    return record


def _choose(pi: dict[Move, float], rng: random.Random, *, explore: bool) -> Move:
    """Sample from ``pi`` in the opening, take its argmax afterwards."""
    if not explore:
        return max(pi, key=lambda m: (pi[m], m))
    moves = sorted(pi)
    return rng.choices(moves, weights=[pi[m] for m in moves], k=1)[0]


def _winner(state: GameState) -> Colour:
    """The colour that won a terminal position.

    Raises:
        ValueError: If the position is drawn. An odd cell count makes that
            impossible, so it means the outcome was computed wrongly.
    """
    for colour in (Colour.PURPLE, Colour.GREEN):
        if outcome(state, colour) > 0:
            return colour
    raise ValueError(
        "terminal position with no winner: the board has an odd cell count, so "
        "this is a bug in scoring rather than a drawn game"
    )


# -- parallel generation ------------------------------------------------------

#: Set once per worker process by :func:`_init_worker`.
_WORKER: dict = {}


def _init_worker(variant: Variant, weights: dict | None, simulations: int) -> None:
    """Build one network per worker, not one per game.

    Also pins torch to a single thread. Eight workers each spawning six BLAS
    threads oversubscribe six physical cores, and the measured 4.31x speedup
    does not survive it.
    """
    torch.set_num_threads(1)
    net = None
    if weights is not None:
        net = FlipHexNet(variant.n_cols, variant.n_rows)
        net.load_state_dict(weights)
        net.eval()
    _WORKER.update(variant=variant, net=net, simulations=simulations)


def _play_one(args: tuple[int, int, int]) -> GameRecord:
    seed, generation, index = args
    return play_game(
        _WORKER["variant"],
        _WORKER["net"],
        simulations=_WORKER["simulations"],
        seed=game_seed(seed, generation, index),
    )


def generate(
    variant: Variant,
    net: FlipHexNet | None,
    *,
    n_games: int,
    simulations: int,
    seed: int,
    generation: int = 0,
    workers: int = 1,
) -> list[Sample]:
    """Play ``n_games`` and return every labelled sample.

    Args:
        variant: Board and hands.
        net: The champion generating the data, or ``None`` for the UCT floor.
        n_games: Games in this generation.
        simulations: PUCT simulations per move.
        seed: The run's seed. Combined with ``generation`` and the game index.
        generation: Which generation this is, so successive generations of one
            run do not replay the same games.
        workers: Processes. One runs in-process, which keeps debugging simple
            and is what the tests use.

    Returns:
        Samples in game order, then ply order — never completion order.
    """
    if workers <= 1:
        records = [
            play_game(
                variant,
                net,
                simulations=simulations,
                seed=game_seed(seed, generation, i),
            )
            for i in range(n_games)
        ]
    else:
        weights = net.state_dict() if net is not None else None
        tasks = [(seed, generation, i) for i in range(n_games)]
        # "spawn", not the default "fork" on Linux. torch runs threads, and
        # forking a multi-threaded process can leave a lock held in the child
        # with no thread alive to release it. The failure is a hang, not a
        # crash, and a hang in generation 12 of 30 costs the whole run. Spawn
        # pays a fresh interpreter per worker -- a second or two, amortised over
        # a generation's games -- to make that impossible.
        with mp.get_context("spawn").Pool(
            workers,
            initializer=_init_worker,
            initargs=(variant, weights, simulations),
        ) as pool:
            # map, not imap_unordered: the order of a generation must not depend
            # on which worker happened to finish first.
            records = pool.map(_play_one, tasks)

    return [sample for record in records for sample in record.samples()]
