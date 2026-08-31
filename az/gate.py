"""The evaluator gate: promote a challenger only if it is actually stronger.

400 games at 55%. The threshold is not negotiable at the sample size it was
chosen for, and the cadence is where the compute decision lives.

What the numbers are
--------------------
Against a champion of genuinely equal strength, at 400 games and a 55% bar:

=========================  =======
per-gate false promotion   2.55%
power at true p = 0.52     12.5%
power at true p = 0.55     52.1%
power at true p = 0.60     98.1%
=========================  =======

Running the gate **every 5 generations rather than every generation** does not
touch the per-gate rate — it reduces the number of gate events, from 30 to 6
over a 30-generation run, and with it the chance of promoting at least one
challenger that is no better than the champion:

=====================  =============  ==================================
cadence                gate events    P(at least one false promotion)
=====================  =============  ==================================
every generation       30             53.9%
every 5 generations    6              14.4%
=====================  =============  ==================================

So the cheaper cadence is also the one that controls the family-wise error. It
buys power too: a challenger judged after five generations of improvement sits in
the ``p >= 0.60`` regime, where the gate catches it 98% of the time, rather than
near ``p = 0.52``, where it catches it 12.5% of the time.

Seats alternate, because the seat may be worth something
--------------------------------------------------------
Whether the first seat carries an advantage is an open question on this game, so
a match that ran the challenger in one seat would confound "stronger network"
with "better seat". Games alternate, and an odd game count is refused rather than
silently favouring one side by one game.

Two deterministic agents replay one game
----------------------------------------
At temperature zero a searcher is a pure function of the position. A gate between
two of them plays the same game 400 times, reports ``n = 400``, and produces a
win rate of 0% or 100% — which reads as a decisive result rather than a broken
measurement. The gate therefore samples the opening by default; see
:data:`az.player.EVALUATION_TEMPERATURE_PLIES`. Passing zero is allowed and
:func:`run_gate` warns about it, because there are legitimate single-position
uses.

Layering
--------
This module plays matches, so it needs move selection — and it takes it from
:mod:`az.player` rather than from ``agents.az_agent``. Writing it against the
agent wrapper made ``az`` import ``agents`` while ``agents`` imports ``az``, a
cycle Python would have tolerated only for as long as the import order happened
to work out. Move selection is search policy and belongs on this side of the
line; the agent classes are adapters onto it.

Statistics note
---------------
:func:`wilson` is duplicated from the completed agent-strength experiment's
script rather than shared with it. A finished experiment's script is a record of
what was run; refactoring it later would make the code no longer the code that
produced the artefact. The consolidation point is a shared statistics module, and
it should happen when a *live* third caller appears, not by editing a closed one.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from dataclasses import dataclass
from math import comb, sqrt

from az.network import FlipHexNet
from az.player import EVALUATION_TEMPERATURE_PLIES, SearchPlayer
from fliphex.moves import apply_move
from fliphex.rules import is_terminal
from fliphex.state import Colour
from fliphex.variant import Variant

#: adr-005's gate. 400 games, promote at 55%.
GATE_GAMES = 400
GATE_THRESHOLD = 0.55

#: Generations between gates. See the module docstring: this is a compute
#: decision that happens to tighten error control rather than loosen it.
GATE_EVERY = 5


@dataclass(frozen=True)
class GateResult:
    """The outcome of a match, and the decision it licenses.

    Attributes:
        games: Games played.
        wins: Challenger wins.
        win_rate: ``wins / games``.
        ci_low, ci_high: Wilson 95% interval. Never quote the rate without it.
        threshold: The bar the rate had to clear.
        promoted: Whether the challenger replaces the champion.
        as_first, as_second: Wins in each seat, so a seat effect is visible
            rather than averaged away.
    """

    games: int
    wins: int
    win_rate: float
    ci_low: float
    ci_high: float
    threshold: float
    promoted: bool
    as_first: int
    as_second: int

    def summary(self) -> str:
        return (
            f"{self.wins}/{self.games} = {self.win_rate:.1%} "
            f"[{self.ci_low:.1%}, {self.ci_high:.1%}] "
            f"(P1 {self.as_first}, P2 {self.as_second}) "
            f"-> {'promote' if self.promoted else 'keep champion'}"
        )


def wilson(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval. Never report a bare proportion."""
    if n == 0:
        return 0.0, 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def _binomial_tail(n: int, p: float, k: int) -> float:
    """``P(X >= k)`` for ``X ~ Binomial(n, p)``."""
    return sum(comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def false_promotion_rate(
    n: int = GATE_GAMES, threshold: float = GATE_THRESHOLD
) -> float:
    """Chance of promoting a challenger of exactly equal strength."""
    return _binomial_tail(n, 0.5, _wins_needed(n, threshold))


def power(
    true_rate: float, n: int = GATE_GAMES, threshold: float = GATE_THRESHOLD
) -> float:
    """Chance of promoting a challenger whose true win rate is ``true_rate``."""
    return _binomial_tail(n, true_rate, _wins_needed(n, threshold))


def family_wise_false_promotion(gates: int, per_gate: float | None = None) -> float:
    """``P(at least one false promotion)`` over ``gates`` independent gates."""
    rate = false_promotion_rate() if per_gate is None else per_gate
    return 1 - (1 - rate) ** gates


def _wins_needed(n: int, threshold: float) -> int:
    """Smallest win count that clears ``threshold``."""
    needed = int(n * threshold)
    while needed / n < threshold:
        needed += 1
    return needed


def play_match_game(
    variant: Variant,
    challenger: SearchPlayer,
    champion: SearchPlayer,
    *,
    challenger_first: bool,
) -> bool:
    """Play one game. Returns whether the challenger won.

    Raises:
        ValueError: If the game ends level, which an odd cell count forbids.
    """
    board, state = variant.board(), variant.initial_state()
    first = variant.first
    second = Colour(3 - first)
    seats = (
        {first: challenger, second: champion}
        if challenger_first
        else {first: champion, second: challenger}
    )
    challenger_colour = first if challenger_first else second

    while not is_terminal(state):
        state = apply_move(board, state, seats[state.to_move].select(board, state))

    purple, green = state.score()
    if purple == green:
        raise ValueError("a level game is impossible on an odd cell count")
    winner = Colour.PURPLE if purple > green else Colour.GREEN
    return winner == challenger_colour


def run_gate(
    variant: Variant,
    challenger_net: FlipHexNet,
    champion_net: FlipHexNet,
    *,
    simulations: int,
    seed: int,
    games: int = GATE_GAMES,
    threshold: float = GATE_THRESHOLD,
    temperature_plies: int = EVALUATION_TEMPERATURE_PLIES,
    start_at: int = 0,
    wins_so_far: int = 0,
    first_wins_so_far: int = 0,
    on_progress: Callable[[int, int, int], None] | None = None,
) -> GateResult:
    """Play the match and decide.

    Args:
        variant: Board and hands.
        challenger_net: The network under test.
        champion_net: The incumbent.
        simulations: PUCT simulations per move, matching deployment.
        seed: Base seed. Each game's seed is derived from it and the game index,
            so the match is the same set of games however it is interrupted.
        games: Match length. Must be even so the seats balance.
        threshold: Win rate the challenger must clear.
        temperature_plies: Opening plies sampled rather than taken greedily.
            Zero makes every game identical; a warning is issued.
        start_at: Resume from this game index.
        wins_so_far: Challenger wins already recorded before ``start_at``.
        first_wins_so_far: Of those, how many came in the first seat.
        on_progress: Called with ``(games_done, wins, first_seat_wins)`` after
            every game, so a caller can checkpoint a part-finished gate — 400
            games is about 34 minutes, the longest uninterruptible unit in the
            run. All three are needed: resuming without the seat split would
            restore the right total and the wrong per-seat breakdown, and the
            seat split is what shows a seat effect rather than averaging it
            away.

    Returns:
        The match result and the promotion decision.

    Raises:
        ValueError: If ``games`` is odd, or the resume arguments are impossible.
    """
    if games % 2:
        raise ValueError(
            f"games must be even so each side plays each seat equally, got {games}"
        )
    if not 0 <= start_at <= games:
        raise ValueError(f"start_at must be in 0..{games}, got {start_at}")
    if wins_so_far > start_at or first_wins_so_far > wins_so_far:
        raise ValueError("resume counts are impossible for the games played")
    if temperature_plies == 0:
        warnings.warn(
            "temperature_plies=0 makes both agents deterministic, so every game "
            "of the match is the same game: the win rate will be 0% or 100% and "
            "the interval will be computed on an effective sample of one",
            stacklevel=2,
        )

    wins = wins_so_far
    first_wins = first_wins_so_far

    for index in range(start_at, games):
        challenger_first = index % 2 == 0
        challenger = SearchPlayer(
            challenger_net,
            simulations=simulations,
            seed=seed * 2_000_003 + index,
            temperature_plies=temperature_plies,
        )
        champion = SearchPlayer(
            champion_net,
            simulations=simulations,
            seed=seed * 3_000_017 + index,
            temperature_plies=temperature_plies,
        )
        won = play_match_game(
            variant, challenger, champion, challenger_first=challenger_first
        )
        wins += won
        first_wins += won and challenger_first
        if on_progress is not None:
            on_progress(index + 1, wins, first_wins)

    low, high = wilson(wins, games)
    rate = wins / games if games else 0.0
    return GateResult(
        games=games,
        wins=wins,
        win_rate=rate,
        ci_low=low,
        ci_high=high,
        threshold=threshold,
        promoted=rate >= threshold,
        as_first=first_wins,
        as_second=wins - first_wins,
    )
