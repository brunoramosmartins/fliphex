"""Tests for EXP-015's analysis, ``scripts/exp015_analysis.py``.

The run itself is 146 hours and cannot be a test fixture. What is tested here is
the scaffolding that decides *what the run means*, and each of these pins a way
the analysis could quietly say the wrong thing:

- **The bar is computed, not quoted.** The registration says the criterion is
  "entirely above 50%" and that the effective bar is "around 58%". A test pins
  the exact count, so a change to the interval cannot move the bar silently.
- **The guards must actually reject.** An artefact whose stored ``win_rate``,
  seat split, interval or ``clears_floor`` disagrees with its own win count is a
  corrupted record, and analysing it as if it matched is worse than crashing.
- **Cross-seed reads are refused while the set is incomplete.** H3's clause 1 is
  about stability; the mean of an incomplete set satisfies nothing, and the
  failure mode is that it gets quoted anyway.
- **A failing seed is never averaged away.** The registration's falsifiability
  clause is one branch of one ``if``; this pins it.
- **A completed seed's history is immutable.** The consolidated snapshot is the
  only tracked copy, so a disagreement with the live file must stop the script
  rather than pick a winner.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


exp015 = _load("exp015_analysis")


# -- fixtures -----------------------------------------------------------------


def _match(wins: int, *, uct: int = 400) -> dict:
    low, high = exp015.wilson(wins, exp015.FLOOR_GAMES)
    return {
        "label": "x",
        "games": exp015.FLOOR_GAMES,
        "wins": wins,
        "win_rate": wins / exp015.FLOOR_GAMES,
        "ci": [low, high],
        "as_first": wins // 2 + wins % 2,
        "as_second": wins // 2,
        "net_simulations": 400,
        "uct_simulations": uct,
        "clears_floor": low > 0.5,
        "seconds": 1.0,
    }


def _seed_entry(seed: int, wins: int, *, uct: int = 411) -> dict:
    return {
        "seed": seed,
        "floors": {
            "equal_simulations": _match(wins),
            "generation_0": _match(25),
            "equal_time": _match(max(0, wins - 6), uct=uct),
        },
        "equal_time_budget": {
            "moves_sampled": 30,
            "net_seconds_per_move": 1.2,
            "uct_seconds_per_move_at_400": 1.17,
            "ratio": uct / 400,
            "uct_simulations": uct,
        },
    }


def _artefact(wins_by_seed: dict[int, int]) -> dict:
    return {
        "experiment": "EXP-015",
        "schedule": {
            "seeds": list(exp015.SEEDS),
            "generations": exp015.GENERATIONS,
            "games": exp015.GAMES,
            "simulations": exp015.SIMULATIONS,
            "buffer_capacity": exp015.BUFFER_CAPACITY,
            "gate_every": exp015.GATE_EVERY,
            "gate_games": exp015.GATE_GAMES,
            "gate_threshold": exp015.GATE_THRESHOLD,
            "floor_games": exp015.FLOOR_GAMES,
        },
        "seeds": {str(s): _seed_entry(s, w) for s, w in wins_by_seed.items()},
    }


def _history(generations: int = exp015.GENERATIONS) -> list[dict]:
    rows = []
    for generation in range(generations):
        gated = (generation + 1) % exp015.GATE_EVERY == 0
        row = {
            "generation": generation,
            "samples": exp015.SAMPLES_PER_GENERATION,
            "buffer": exp015.BUFFER_CAPACITY,
            "refresh_fraction": 0.25,
            "policy_loss": 5.0 - generation * 0.04,
            "value_loss": 0.5,
            "gated": gated,
            "seconds": 2000.0,
        }
        if gated:
            wins = 240
            low, high = exp015.wilson(wins, exp015.GATE_GAMES)
            row |= {
                "gate_win_rate": wins / exp015.GATE_GAMES,
                "gate_ci": [low, high],
                "gate_as_first": 130,
                "gate_as_second": 110,
                "promoted": True,
            }
        rows.append(row)
    return rows


def _write_run(base: Path, seed: int, rows: list[dict]) -> Path:
    path = base / f"h3-seed{seed}" / "history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return path


def _run(tmp_path: Path, artefact: dict, histories: dict[int, list[dict]]) -> Path:
    out = tmp_path / "exp015.json"
    out.write_text(json.dumps(artefact))
    base = tmp_path / "az-runs"
    for seed, rows in histories.items():
        _write_run(base, seed, rows)
    return out


def _flat(text: str) -> str:
    """Prose is wrapped to a fixed width, so phrases straddle line breaks."""
    return " ".join(text.split())


def _main(tmp_path: Path, artefact: dict, histories: dict[int, list[dict]]) -> int:
    out = _run(tmp_path, artefact, histories)
    sys.argv = [
        "exp015_analysis.py",
        "--artefact",
        str(out),
        "--base",
        str(tmp_path / "az-runs"),
        "--histories",
        str(tmp_path / "histories.json"),
    ]
    return exp015.main()


# -- the bar ------------------------------------------------------------------


def test_the_bar_is_computed_and_is_not_50_percent():
    """The criterion reads "above 50%" and costs 57%. Pin the count."""
    bar = exp015.smallest_clearing(exp015.FLOOR_GAMES)

    assert bar == 114
    assert exp015.wilson(bar, 200)[0] > 0.5
    assert exp015.wilson(bar - 1, 200)[0] <= 0.5


def test_a_true_55_percent_seed_would_fail_the_floor():
    """Recorded in the registration as the reason the wording understates it."""
    assert exp015.wilson(110, 200)[0] < 0.5


def test_wilson_agrees_with_the_gate_that_produced_the_stored_intervals():
    """The reimplementation exists to check ``az.gate``; keep the two honest.

    If this ever fails, one of the two is wrong and every stored interval in the
    artefact is suspect -- which is exactly what the analysis guard would report
    at runtime, one artefact at a time.
    """
    from az.gate import wilson as gate_wilson

    for n in (200, 400):
        for wins in range(0, n + 1, 7):
            assert exp015.wilson(wins, n) == pytest.approx(gate_wilson(wins, n))


# -- guards -------------------------------------------------------------------


def test_a_tampered_win_rate_is_rejected():
    artefact = _artefact({1: 128})
    artefact["seeds"]["1"]["floors"]["equal_simulations"]["win_rate"] = 0.9

    with pytest.raises(SystemExit, match="stored win_rate"):
        exp015.guard_artefact(artefact)


def test_a_seat_split_that_does_not_sum_to_the_wins_is_rejected():
    artefact = _artefact({1: 128})
    artefact["seeds"]["1"]["floors"]["equal_simulations"]["as_first"] = 3

    with pytest.raises(SystemExit, match="does not sum"):
        exp015.guard_artefact(artefact)


def test_a_clears_floor_flag_contradicting_its_own_interval_is_rejected():
    """The flag is the run's verdict; the interval is the evidence for it."""
    artefact = _artefact({1: 100})
    artefact["seeds"]["1"]["floors"]["equal_simulations"]["clears_floor"] = True

    with pytest.raises(SystemExit, match="contradicts its own interval"):
        exp015.guard_artefact(artefact)


def test_a_stored_interval_that_is_not_the_recomputed_one_is_rejected():
    artefact = _artefact({1: 128})
    artefact["seeds"]["1"]["floors"]["equal_simulations"]["ci"][0] = 0.51

    with pytest.raises(SystemExit, match="lower limit"):
        exp015.guard_artefact(artefact)


def test_a_different_schedule_is_rejected_rather_than_analysed():
    artefact = _artefact({1: 128})
    artefact["schedule"]["gate_threshold"] = 0.6

    with pytest.raises(SystemExit, match="registered as"):
        exp015.guard_artefact(artefact)


def test_an_equal_time_match_that_ignores_its_measured_budget_is_rejected():
    """The ratio must be measured before the match, never inferred after it."""
    artefact = _artefact({1: 128})
    artefact["seeds"]["1"]["floors"]["equal_time"]["uct_simulations"] = 900

    with pytest.raises(SystemExit, match="but the budget recorded"):
        exp015.guard_artefact(artefact)


def test_an_equal_simulations_match_may_not_hand_uct_a_different_budget():
    artefact = _artefact({1: 128})
    artefact["seeds"]["1"]["floors"]["equal_simulations"]["uct_simulations"] = 462

    with pytest.raises(SystemExit, match="equal-simulations match gave UCT"):
        exp015.guard_artefact(artefact)


def test_a_gate_promoted_against_its_own_rate_is_rejected():
    rows = _history(5)
    rows[4]["promoted"] = False  # 60% at a 55% threshold

    with pytest.raises(SystemExit, match="contradicts rate"):
        exp015.guard_history(1, rows)


def test_a_generation_gated_off_schedule_is_rejected():
    rows = _history(5)
    rows[3]["gated"] = True

    with pytest.raises(SystemExit, match="schedule gates every"):
        exp015.guard_history(1, rows)


def test_a_short_generation_is_rejected():
    """Every game fills the board, so a generation is exactly 5000 samples."""
    rows = _history(3)
    rows[1]["samples"] = 4980

    with pytest.raises(SystemExit, match="samples, expected"):
        exp015.guard_history(1, rows)


# -- the durable history ------------------------------------------------------


def test_a_completed_seed_whose_history_changed_is_a_hard_failure(tmp_path):
    base = tmp_path / "az-runs"
    _write_run(base, 1, _history())
    snapshot = tmp_path / "histories.json"
    stale = _history()
    stale[7]["policy_loss"] = 99.0
    snapshot.write_text(json.dumps({"seeds": {"1": stale}}))

    with pytest.raises(SystemExit, match="immutable"):
        exp015.consolidate(base, snapshot, [1])


def test_an_incomplete_seed_may_still_grow(tmp_path):
    """Only a *finished* seed is immutable; a running one gains rows."""
    base = tmp_path / "az-runs"
    _write_run(base, 1, _history(12))
    snapshot = tmp_path / "histories.json"
    snapshot.write_text(json.dumps({"seeds": {"1": _history(7)}}))

    bundle = exp015.consolidate(base, snapshot, [1])

    assert len(bundle["merged"]["1"]) == 12
    assert bundle["sources"][1] == "live"


def test_the_snapshot_is_used_when_the_run_directory_is_gone(tmp_path):
    """The point of tracking it: ``data/az-runs`` is gitignored scratch."""
    snapshot = tmp_path / "histories.json"
    snapshot.write_text(json.dumps({"seeds": {"1": _history()}}))

    bundle = exp015.consolidate(tmp_path / "az-runs", snapshot, [1])

    assert bundle["sources"][1] == "snapshot"
    assert len(bundle["merged"]["1"]) == exp015.GENERATIONS


def test_a_half_written_final_line_is_tolerated(tmp_path):
    """A seed may be running while this is read; the last append can be partial."""
    base = tmp_path / "az-runs"
    path = _write_run(base, 1, _history(4))
    path.write_text(path.read_text() + '{"generation": 4, "samp')

    rows = exp015.read_live(base, 1)

    assert [r["generation"] for r in rows] == [0, 1, 2, 3]


def test_a_corrupt_line_that_is_not_the_last_one_raises(tmp_path):
    base = tmp_path / "az-runs"
    path = _write_run(base, 1, _history(4))
    lines = path.read_text().splitlines()
    lines[1] = '{"generation": 1, "samp'
    path.write_text("\n".join(lines) + "\n")

    with pytest.raises(SystemExit, match="not a mid-append race"):
        exp015.read_live(base, 1)


# -- what the analysis concludes ----------------------------------------------


def test_cross_seed_reads_are_refused_while_the_set_is_incomplete(tmp_path, capsys):
    code = _main(tmp_path, _artefact({1: 128, 2: 152}), {1: _history(), 2: _history()})
    out = capsys.readouterr().out

    assert code == 0
    assert "REFUSED" in out
    assert "INCOMPLETE" in out
    # The per-seed rows are a complete read of each seed and must still appear.
    assert "64.0%" in out and "76.0%" in out
    # Nothing combined: no pooled rate, no spread, no homogeneity.
    assert "chi2" not in out
    assert "observed sd" not in out
    assert "secondary (equal time)" not in out


def test_five_clearing_seeds_give_the_floor_verdict(tmp_path, capsys):
    wins = {1: 128, 2: 152, 3: 130, 4: 140, 5: 135}
    code = _main(tmp_path, _artefact(wins), {s: _history() for s in wins})
    out = capsys.readouterr().out

    assert code == 0
    assert "THE FLOOR HOLDS ON EVERY SEED" in out
    assert "REFUSED" not in out
    assert "chi2" in out


def test_one_failing_seed_is_recorded_and_not_averaged_away(tmp_path, capsys):
    """The mean of these five is 63%, and the run still fails the clause."""
    wins = {1: 128, 2: 152, 3: 130, 4: 140, 5: 80}
    code = _main(tmp_path, _artefact(wins), {s: _history() for s in wins})
    out = capsys.readouterr().out

    assert code == 0
    assert "INSTABILITY RECORDED" in out
    assert "[5]" in out
    assert "THE FLOOR HOLDS" not in out


def test_the_verdict_never_claims_more_than_the_floor(tmp_path, capsys):
    wins = {1: 128, 2: 152, 3: 130, 4: 140, 5: 135}
    _main(tmp_path, _artefact(wins), {s: _history() for s in wins})
    out = _flat(capsys.readouterr().out)

    assert "learner learned something' and nothing more" in out
    assert "EXP-006" in out


def test_the_snapshot_is_written_where_it_can_be_tracked(tmp_path):
    _main(tmp_path, _artefact({1: 128}), {1: _history()})

    written = json.loads((tmp_path / "histories.json").read_text())

    assert written["experiment"] == "EXP-015"
    assert len(written["seeds"]["1"]) == exp015.GENERATIONS
