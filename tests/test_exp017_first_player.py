"""Tests for EXP-017's instrument and its analysis.

The registered run is 5,000 games and ~3 hours; these run on the 5×1, where the
game is exactly solvable in 216 nodes. Each pins something that EXP-016's
red-team found, or would have found:

- **The harness must credit the seat, not the agent.** A first player that
  throws every game must read 0%. This is the defect a self-play harness built
  on ``run_gate`` would have had, because ``GateResult`` counts *challenger*
  wins and prints them labelled "P1".
- **The self-check must be able to fail.** Gate 7 says no instrument produces a
  number before it is run against a known answer; a check that passes on a
  broken harness is decoration.
- **Player seeds must be distinct.** EXP-016's schedule shared 975 of 5,000
  across its twenty match seeds, so games that looked independent replayed one
  player's whole random stream.
- **The denominator must be the games actually distinguished.** A deterministic
  agent replays one game while the artefact reports ``n = 5,000``; the analysis
  recomputes against the distinct count rather than quoting the nominal one.
- **No rate without ``proved_rate``.** The agent proves about a third of its
  plies, and the counts must survive a resume — they live in the work file, not
  only in a running total.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest

from fliphex.variant import Variant

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


evaluator = _load("eval_first_player_advantage", "eval_first_player_advantage.py")
analysis = _load("exp017_analysis", "exp017_analysis.py")

SMALL = Variant(5, 1)


# -- the registration, restated -----------------------------------------------


def test_the_constants_match_what_was_registered():
    assert evaluator.GAMES == 5_000
    assert evaluator.MATCH_SEED == 1
    assert evaluator.SEARCH_BELOW_K == 8
    assert evaluator.MAX_NODES == 2_000_000
    assert analysis.GAMES == 5_000
    assert analysis.MDE == 0.02


def test_the_two_scripts_agree_on_wilson():
    """The analysis recomputes the instrument's interval; they must not drift."""
    for n in (200, 5_000):
        for wins in range(0, n + 1, max(1, n // 13)):
            assert evaluator.wilson(wins, n) == pytest.approx(analysis.wilson(wins, n))


# -- seeds --------------------------------------------------------------------


def test_every_derived_player_seed_is_distinct():
    evaluator.assert_seeds_distinct(5_000)  # must not raise
    seeds = [s for i in range(5_000) for s in evaluator.seeds_for(i)]
    assert len(set(seeds)) == 10_000


def test_the_collision_guard_can_fail(monkeypatch):
    """EXP-016's schedule. If the guard cannot catch it, it is not a guard."""
    monkeypatch.setattr(
        evaluator, "seeds_for", lambda i: (2_000_003 + i, 3_000_017 + i)
    )
    monkeypatch.setattr(evaluator, "SEED_BASE", 0)

    # Two families that overlap once the index range is wide enough.
    with pytest.raises(SystemExit, match="collide"):
        evaluator.assert_seeds_distinct(1_500_000)


# -- the seat, not the agent --------------------------------------------------


def _perfect(index):
    return evaluator.solver_pair(evaluator.seeds_for(index), search_below_k=None)


def test_perfect_self_play_on_the_5x1_gives_exactly_one():
    """The 5×1's first player wins with perfect play, proved in 216 nodes."""
    result = evaluator.measure(SMALL, 6, _perfect)

    assert result["first_player_rate"] == 1.0
    assert result["first_player_wins"] == result["games"] == 6


def test_a_first_player_that_throws_reads_exactly_zero():
    """The probe that separates crediting the seat from crediting the agent."""
    board = SMALL.board()

    result = evaluator.measure(
        SMALL,
        6,
        lambda i: (
            evaluator.ThrowingAgent(board, seed=i),
            _perfect(i)[1],
        ),
    )

    assert result["first_player_rate"] == 0.0


def test_swapping_which_agent_sits_first_moves_the_rate():
    """If the harness credited the agent, these two would be equal."""
    board = SMALL.board()
    throws_first = evaluator.measure(
        SMALL, 6, lambda i: (evaluator.ThrowingAgent(board, seed=i), _perfect(i)[1])
    )
    throws_second = evaluator.measure(
        SMALL, 6, lambda i: (_perfect(i)[0], evaluator.ThrowingAgent(board, seed=i))
    )

    assert throws_first["first_player_rate"] == 0.0
    assert throws_second["first_player_rate"] == 1.0


# -- the self-check -----------------------------------------------------------


def test_the_self_check_passes_on_the_real_harness():
    probes = evaluator.self_check(verbose=False)

    assert len(probes) == 2
    assert [p["expected"] for p in probes] == [1.0, 0.0]
    assert all(p["first_player_rate"] == p["expected"] for p in probes)


def test_the_self_check_fails_when_the_seat_attribution_is_broken(monkeypatch):
    """Gate 7: a check that cannot fail verifies nothing.

    Break the thing probe 2 exists to catch — credit the win to a fixed seat —
    and the self-check must refuse to let the run proceed.
    """
    original = evaluator.play_game

    def crediting_the_agent(board, variant, first_agent, second_agent):
        outcome = original(board, variant, first_agent, second_agent)
        return {**outcome, "first_won": True}

    monkeypatch.setattr(evaluator, "play_game", crediting_the_agent)

    with pytest.raises(SystemExit, match="PROBE 2 FAILED"):
        evaluator.self_check(verbose=False)


# -- resume -------------------------------------------------------------------


def _run(tmp_path, games, extra=()):
    import subprocess

    out, work = tmp_path / "a.json", tmp_path / "a.jsonl"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "eval_first_player_advantage.py"),
            "--games",
            str(games),
            "--out",
            str(out),
            "--work",
            str(work),
            *extra,
        ],
        check=True,
        capture_output=True,
    )
    return json.loads(out.read_text())


def test_an_interrupted_run_resumes_to_the_same_artefact(tmp_path):
    """A resume must be the same experiment, not merely a continuation."""
    whole = _run(tmp_path / "whole", 4, ("--skip-self-check",))
    part = tmp_path / "part"
    _run(part, 2, ("--skip-self-check",))
    resumed = _run(part, 4, ("--skip-self-check",))

    for field in ("games", "first_player_wins", "distinct_games", "proved_plies"):
        assert whole[field] == resumed[field], field


def test_the_ply_counts_survive_a_resume(tmp_path):
    """They live in the work file, not only in a running total."""
    part = tmp_path / "p"
    _run(part, 2, ("--skip-self-check",))
    resumed = _run(part, 4, ("--skip-self-check",))

    assert resumed["proved_plies"] > 0
    assert 0.0 < resumed["proved_rate"] <= 1.0


# -- the analysis -------------------------------------------------------------


def _artefact(**overrides) -> dict:
    wins, games = 2600, 5000
    low, high = analysis.wilson(wins, games)
    base = {
        "experiment": "EXP-017",
        "games": games,
        "first_player_wins": wins,
        "first_player_rate": wins / games,
        "wilson_low": low,
        "wilson_high": high,
        "distinct_games": games,
        "proved_plies": 40_000,
        "unattempted_plies": 85_000,
        "over_budget_plies": 0,
        "proved_rate": 40_000 / 125_000,
        "self_check": [
            {
                "probe": "perfect self-play on 5x1",
                "expected": 1.0,
                "first_player_rate": 1.0,
            },
            {
                "probe": "first player throws, on 5x1",
                "expected": 0.0,
                "first_player_rate": 0.0,
            },
        ],
    }
    return base | overrides


def test_a_run_that_skipped_its_self_check_gets_no_verdict():
    artefact = _artefact(self_check=[{"probe": "SKIPPED", "expected": None}])

    with pytest.raises(SystemExit, match="never met a known answer"):
        analysis.guard(artefact)


def test_a_self_check_that_recorded_a_failure_gets_no_verdict():
    probes = _artefact()["self_check"]
    probes[1] = {**probes[1], "first_player_rate": 0.5}

    with pytest.raises(SystemExit, match="instrument check contradicts"):
        analysis.guard(_artefact(self_check=probes))


def test_a_tampered_rate_is_rejected():
    with pytest.raises(SystemExit, match="is not"):
        analysis.guard(_artefact(first_player_rate=0.9))


def test_a_stored_interval_that_is_not_the_recomputed_one_is_rejected():
    with pytest.raises(SystemExit, match="not the recomputed one"):
        analysis.guard(_artefact(wilson_low=0.6))


def test_a_clean_artefact_passes(capsys):
    analysis.guard(_artefact())

    assert "guards passed" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("wins", "expected"),
    [
        (2800, "ABOVE 50%"),  # 56.0%, interval clears
        (2200, "BELOW 50%"),  # 44.0%, interval entirely below
        (2510, "NO DETECTED DIRECTION"),  # 50.2%, straddles
    ],
)
def test_the_three_verdict_branches(tmp_path, capsys, wins, expected):
    low, high = analysis.wilson(wins, 5000)
    path = tmp_path / "a.json"
    path.write_text(
        json.dumps(
            _artefact(
                first_player_wins=wins,
                first_player_rate=wins / 5000,
                wilson_low=low,
                wilson_high=high,
            )
        )
    )
    sys.argv = ["exp017_analysis.py", "--artefact", str(path)]

    analysis.main()

    assert expected in capsys.readouterr().out


def test_a_shortfall_recomputes_against_the_distinct_count(tmp_path, capsys):
    """A repeated game is not a second observation."""
    path = tmp_path / "a.json"
    path.write_text(json.dumps(_artefact(distinct_games=500)))
    sys.argv = ["exp017_analysis.py", "--artefact", str(path)]

    analysis.main()
    out = " ".join(capsys.readouterr().out.split())

    assert "SHORTFALL" in out
    assert "/500 =" in out
    # A tenth of the games means a wider interval, not the nominal one.
    assert f"{analysis.wilson(260, 500)[0]:.1%}" in out


def test_the_rate_is_never_printed_without_proved_rate(tmp_path, capsys):
    path = tmp_path / "a.json"
    path.write_text(json.dumps(_artefact()))
    sys.argv = ["exp017_analysis.py", "--artefact", str(path)]

    analysis.main()
    out = capsys.readouterr().out

    assert "proved_rate" in out
    assert "32.0%" in out
    assert "seventeen plies" in out
    assert "Not established: anything about perfect play" in out


def test_the_analysis_imports_no_engine(tmp_path):
    """It must run where nothing can be trained or solved."""
    source = (ROOT / "scripts" / "exp017_analysis.py").read_text()

    for forbidden in (
        "import agents",
        "from agents",
        "import az",
        "from az",
        "import solver",
        "from solver",
        "import torch",
    ):
        assert forbidden not in source, forbidden


def test_wilson_is_not_a_normal_approximation():
    """At the extremes the two differ, and Wilson is the one that stays in range."""
    low, high = analysis.wilson(0, 100)

    assert low == 0.0
    assert 0.0 < high < 0.1
    naive = 1.96 * math.sqrt(0.0 * 1.0 / 100)
    assert high > naive  # the normal approximation collapses to zero width
