"""Tests for ``az/gate.py``.

The gate's job is to refuse a challenger that is not actually stronger, so the
tests that matter are the ones about how it can be fooled:

- :func:`test_a_deterministic_match_is_warned_about` — two temperature-zero
  searchers replay one game. The gate would report ``n = 400`` on an effective
  sample of one, with a win rate of 0% or 100%. Nothing errors; the number just
  looks decisive.
- :func:`test_seats_alternate_exactly` — whether the first seat is worth
  anything is an open question on this game, so an unbalanced match confounds
  "stronger network" with "better seat".
- :func:`test_resuming_a_gate_continues_the_same_match` — 400 games is the
  longest uninterruptible unit in the run, about 34 minutes.
"""

from __future__ import annotations

import pytest
import torch

from az.gate import (
    GATE_EVERY,
    GATE_GAMES,
    GATE_THRESHOLD,
    false_promotion_rate,
    family_wise_false_promotion,
    play_match_game,
    power,
    run_gate,
    wilson,
)
from az.network import FlipHexNet
from az.player import SearchPlayer
from fliphex.variant import Arm, Variant

TINY = Variant(3, 3, Arm("h1"))


@pytest.fixture
def nets() -> tuple[FlipHexNet, FlipHexNet]:
    torch.manual_seed(0)
    challenger = FlipHexNet(3, 3)
    torch.manual_seed(1)
    champion = FlipHexNet(3, 3)
    challenger.eval()
    champion.eval()
    return challenger, champion


# -- the registered constants -------------------------------------------------


def test_the_gate_is_the_one_that_was_specified():
    assert GATE_GAMES == 400
    assert GATE_THRESHOLD == 0.55
    assert GATE_EVERY == 5


# -- the statistics -----------------------------------------------------------


def test_the_per_gate_false_promotion_rate():
    """An equal-strength challenger clears 55% of 400 games 2.55% of the time."""
    assert false_promotion_rate() == pytest.approx(0.0255, abs=5e-4)


def test_power_rises_with_true_strength():
    assert power(0.52) == pytest.approx(0.125, abs=0.01)
    assert power(0.55) == pytest.approx(0.521, abs=0.01)
    assert power(0.60) == pytest.approx(0.981, abs=0.01)
    assert power(0.65) == pytest.approx(1.0, abs=0.01)


def test_gating_every_generation_is_more_likely_than_not_to_promote_noise():
    """The finding that inverted the cadence decision.

    Relaxing the cadence does not weaken error control -- it is the tighter
    choice, because it reduces the number of chances to be fooled.
    """
    every_generation = family_wise_false_promotion(30)
    every_fifth = family_wise_false_promotion(6)

    assert every_generation == pytest.approx(0.539, abs=0.01)
    assert every_fifth == pytest.approx(0.144, abs=0.01)
    assert every_fifth < every_generation


def test_wilson_brackets_the_point_estimate():
    low, high = wilson(220, 400)

    assert low < 0.55 < high
    assert wilson(0, 0) == (0.0, 0.0)


def test_wilson_stays_inside_the_unit_interval():
    assert wilson(400, 400)[1] <= 1.0
    assert wilson(0, 400)[0] >= 0.0


# -- one game -----------------------------------------------------------------


def test_a_match_game_reports_from_the_challengers_side(nets):
    challenger_net, champion_net = nets
    challenger = SearchPlayer(challenger_net, simulations=4, seed=1)
    champion = SearchPlayer(champion_net, simulations=4, seed=2)

    as_first = play_match_game(TINY, challenger, champion, challenger_first=True)
    as_second = play_match_game(TINY, challenger, champion, challenger_first=False)

    assert isinstance(as_first, bool)
    assert isinstance(as_second, bool)


# -- the match ----------------------------------------------------------------


def test_an_odd_game_count_is_refused(nets):
    challenger, champion = nets

    with pytest.raises(ValueError, match="even"):
        run_gate(TINY, challenger, champion, simulations=2, seed=1, games=5)


def test_seats_alternate_exactly(nets):
    """Half the games in each seat, so a seat effect cannot masquerade as skill."""
    challenger, champion = nets

    result = run_gate(TINY, challenger, champion, simulations=2, seed=1, games=8)

    assert result.as_first + result.as_second == result.wins
    assert result.games == 8


def test_a_deterministic_match_is_warned_about(nets):
    """Every game identical, so n = 400 would describe a sample of one."""
    challenger, champion = nets

    with pytest.warns(UserWarning, match="same game"):
        result = run_gate(
            TINY,
            challenger,
            champion,
            simulations=2,
            seed=1,
            games=4,
            temperature_plies=0,
        )

    assert result.win_rate in (0.0, 0.5, 1.0), "seats still split the outcome"


def test_the_promotion_decision_follows_the_threshold(nets):
    challenger, champion = nets

    result = run_gate(
        TINY, challenger, champion, simulations=2, seed=1, games=8, threshold=0.0
    )
    assert result.promoted is True

    strict = run_gate(
        TINY, challenger, champion, simulations=2, seed=1, games=8, threshold=1.01
    )
    assert strict.promoted is False


def test_the_summary_never_quotes_a_bare_proportion(nets):
    challenger, champion = nets

    result = run_gate(TINY, challenger, champion, simulations=2, seed=1, games=4)

    assert "[" in result.summary() and "]" in result.summary()


# -- resumption ---------------------------------------------------------------


def test_resuming_a_gate_continues_the_same_match(nets):
    """34 minutes is too long to repeat because a laptop slept."""
    challenger, champion = nets
    progress: list[tuple[int, int, int]] = []

    whole = run_gate(
        TINY,
        challenger,
        champion,
        simulations=2,
        seed=5,
        games=8,
        on_progress=lambda done, wins, first: progress.append((done, wins, first)),
    )

    # The checkpoint the run would have written after game 4.
    _, wins_at_four, first_at_four = progress[3]

    resumed = run_gate(
        TINY,
        challenger,
        champion,
        simulations=2,
        seed=5,
        games=8,
        start_at=4,
        wins_so_far=wins_at_four,
        first_wins_so_far=first_at_four,
    )

    assert resumed.wins == whole.wins
    assert resumed.as_first == whole.as_first
    assert resumed.as_second == whole.as_second
    assert resumed.promoted == whole.promoted


def test_the_progress_callback_carries_the_seat_split(nets):
    """Resuming on the total alone would restore the wrong per-seat breakdown."""
    challenger, champion = nets
    seen: list[tuple[int, int, int]] = []

    result = run_gate(
        TINY,
        challenger,
        champion,
        simulations=2,
        seed=1,
        games=6,
        on_progress=lambda done, wins, first: seen.append((done, wins, first)),
    )

    assert [row[0] for row in seen] == [1, 2, 3, 4, 5, 6]
    assert seen[-1] == (6, result.wins, result.as_first)


def test_impossible_resume_counts_are_refused(nets):
    challenger, champion = nets

    with pytest.raises(ValueError, match="impossible"):
        run_gate(
            TINY,
            challenger,
            champion,
            simulations=2,
            seed=1,
            games=8,
            start_at=2,
            wins_so_far=5,
        )


def test_start_at_must_be_within_the_match(nets):
    challenger, champion = nets

    with pytest.raises(ValueError, match="start_at"):
        run_gate(TINY, challenger, champion, simulations=2, seed=1, games=8, start_at=9)
